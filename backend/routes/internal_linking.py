"""Internal Linking Automatique — scanne les articles de blog et les
descriptions produits pour injecter des liens internes markdown vers les
produits, collections et autres articles du site. 100 % déterministe,
zéro coût LLM.

Logic :
1. Build une map `keyword → url` depuis les produits, collections, articles.
2. Pour chaque post, scan le body markdown et insert `[keyword](url)` sur la
   première occurrence non déjà liée (skip code-blocks, existing anchors, h1).
3. Persist les modifications + retourne les stats (liens ajoutés, pages
   orphelines, link density moyen).

Entrypoints :
- POST /api/sites/{id}/internal-linking/auto-inject   (force?: bool)
- GET  /api/sites/{id}/internal-linking/stats         (audit sans modif)
"""
from __future__ import annotations
import logging
import re
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from deps import db, get_current_user

router = APIRouter()
logger = logging.getLogger("conceptfactory.internal_linking")


# --- Helpers ---------------------------------------------------------------

_STOP_WORDS_FR = {
    "le", "la", "les", "un", "une", "des", "et", "ou", "de", "du", "à", "au",
    "aux", "en", "pour", "par", "sur", "sous", "dans", "avec", "sans", "ce",
    "ces", "se", "sa", "son", "ses", "plus", "mais", "non", "pas", "très",
    "être", "avoir", "que", "qui", "quoi", "dont", "où",
}


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text or "")


def _normalize_keyword(kw: str) -> str:
    """Lowercase + strip accents? We keep accents for regex matching since
    we anchor on word boundaries. Just strip + lowercase the surface."""
    return (kw or "").strip().lower()


def _pick_text(val) -> str:
    """Pydantic / Mongo parfois stocke `{fr: ..., en: ...}`."""
    if isinstance(val, dict):
        for k in ("fr", "fr-FR", "en", "en-GB"):
            if val.get(k):
                return str(val[k])
        return str(next(iter(val.values()), ""))
    return str(val or "")


def _escape_regex(text: str) -> str:
    return re.escape(text)


def _build_link_map(site: dict, products: list) -> list[dict]:
    """Retourne une liste d'entrées `{keyword, url, type, priority}` triée
    par priorité décroissante + longueur du keyword (long match d'abord).

    Priority :
    - 10 : article blog (pillar) — maillage vers contenu froid/chaud
    - 8  : produit (conversion directe)
    - 6  : collection (catégorie)
    - 4  : article blog standard
    """
    entries: list[dict] = []
    design = site.get("design") or {}

    # 1. Blog posts
    for post in (design.get("blog_posts") or []):
        slug = post.get("slug") or ""
        title = _pick_text(post.get("title") or "")
        if not slug or not title:
            continue
        is_pillar = bool(post.get("is_pillar") or post.get("pillar"))
        entries.append({
            "keyword": title,
            "url": f"/blog/{slug}",
            "type": "blog_pillar" if is_pillar else "blog",
            "priority": 10 if is_pillar else 4,
            "ref_id": post.get("id") or slug,
        })
        # Also index the first pillar keyword stored on post (if any)
        for extra_kw in (post.get("keywords") or [])[:2]:
            k = _normalize_keyword(extra_kw)
            if len(k) >= 6:
                entries.append({
                    "keyword": extra_kw,
                    "url": f"/blog/{slug}",
                    "type": "blog_kw",
                    "priority": 3,
                    "ref_id": post.get("id") or slug,
                })

    # 2. Collections
    for col in (design.get("collections") or []):
        title = _pick_text(col.get("title") or col.get("name") or "")
        slug = col.get("slug") or ""
        if not slug or not title:
            continue
        entries.append({
            "keyword": title,
            "url": f"/collection/{slug}",
            "type": "collection",
            "priority": 6,
            "ref_id": slug,
        })

    # 3. Products
    for p in products:
        name = _pick_text(p.get("name") or "")
        pid = p.get("id")
        if not name or not pid:
            continue
        if (p.get("role") or "") == "upsell":
            # Upsells linked through product pages only, skip global linking
            continue
        entries.append({
            "keyword": name,
            "url": f"/product/{pid}",
            "type": "product",
            "priority": 8,
            "ref_id": pid,
        })

    # Filter : keyword must be ≥ 5 chars, not a stop word
    filtered = []
    seen = set()
    for e in entries:
        kw = _normalize_keyword(e["keyword"])
        if len(kw) < 5:
            continue
        if kw in _STOP_WORDS_FR:
            continue
        key = (kw, e["url"])
        if key in seen:
            continue
        seen.add(key)
        filtered.append(e)

    # Sort : priority DESC, then length DESC (match "fauteuil releveur" avant "fauteuil")
    filtered.sort(key=lambda x: (-x["priority"], -len(x["keyword"])))
    return filtered


# Matches :
# - Existing markdown links : [...](url)
# - Code blocks : ```...```
# - Inline code : `...`
# - H1 lines : # ...
# - URLs raw
_SKIP_RE = re.compile(
    r"(\[[^\]]+\]\([^)]+\))|(```.+?```)|(`[^`]+`)|(^#\s.+$)|(https?://\S+)",
    re.DOTALL | re.MULTILINE,
)


def _inject_links_into_body(body: str, link_map: list[dict], self_url: Optional[str] = None, max_links: int = 6) -> tuple[str, list[dict]]:
    """Injecte des liens markdown sur le body. Retourne (new_body, links_added).

    Règles :
    - max `max_links` nouveaux liens par document.
    - chaque keyword n'est lié qu'une fois par document (première occurrence).
    - skip si le keyword est déjà dans un lien existant, code-block ou titre H1.
    - skip si l'URL cible == self_url (pas de lien vers soi-même).
    """
    if not body or not link_map:
        return body, []

    # 1. Collect protected spans (existing links, code, H1) — we won't touch them.
    protected: list[tuple[int, int]] = []
    for m in _SKIP_RE.finditer(body):
        protected.append(m.span())

    def is_protected(pos: int) -> bool:
        for a, b in protected:
            if a <= pos < b:
                return True
        return False

    added: list[dict] = []
    used_keywords: set[str] = set()
    # Build list of candidate matches across all entries (first in body order)
    # We iterate entries by priority, and for each, find the FIRST unprotected
    # occurrence in the current body. We mutate `body` with offset bookkeeping.
    body_mut = body
    for entry in link_map:
        if len(added) >= max_links:
            break
        if entry["url"] == self_url:
            continue
        kw_lower = _normalize_keyword(entry["keyword"])
        if kw_lower in used_keywords:
            continue
        # Also skip if this URL was already used (avoid two links to same page)
        if any(a["url"] == entry["url"] for a in added):
            continue

        # Use word-boundary regex, case-insensitive
        # Use unicode-aware word boundaries: (?<!\w) ... (?!\w)
        pattern = re.compile(
            r"(?<!\w)(" + _escape_regex(entry["keyword"]) + r")(?!\w)",
            flags=re.IGNORECASE,
        )
        # Rebuild protected spans for current body_mut
        protected_now = [m.span() for m in _SKIP_RE.finditer(body_mut)]

        def is_protected_now(pos: int) -> bool:
            for a, b in protected_now:
                if a <= pos < b:
                    return True
            return False

        match = None
        for m in pattern.finditer(body_mut):
            start = m.start()
            # Also skip if previous char is '[' (means we are about to create
            # a link from an existing markdown keyword surface)
            if start > 0 and body_mut[start - 1] == "[":
                continue
            if not is_protected_now(start):
                match = m
                break
        if not match:
            continue

        # Inject markdown link in place of the matched text
        original = match.group(0)
        replacement = f"[{original}]({entry['url']})"
        body_mut = body_mut[: match.start()] + replacement + body_mut[match.end():]
        added.append({
            "keyword": original,
            "url": entry["url"],
            "type": entry["type"],
        })
        used_keywords.add(kw_lower)

    return body_mut, added


# --- Endpoints -------------------------------------------------------------

class AutoInjectInput(BaseModel):
    max_links_per_post: int = 6
    max_links_per_product: int = 3
    dry_run: bool = False


@router.post("/sites/{site_id}/internal-linking/auto-inject")
async def auto_inject(site_id: str, body: AutoInjectInput, user=Depends(get_current_user)):
    """Scan tous les blog posts + descriptions produits et injecte des
    liens markdown internes. Déterministe, réversible (stocke un flag
    `internal_linked_at` pour éviter de reboucler inutilement)."""
    site = await db.sites.find_one({"id": site_id}, {"_id": 0})
    if not site:
        raise HTTPException(404, "Site introuvable")

    products = await db.products.find(
        {"site_id": site_id, "status": "active"},
        {"_id": 0},
    ).to_list(500)

    link_map = _build_link_map(site, products)
    if not link_map:
        return {"status": "noop", "message": "Aucune cible interne détectée (0 produit/blog/collection).", "link_map_size": 0}

    stats = {
        "blog_posts_scanned": 0,
        "blog_posts_updated": 0,
        "blog_links_added": 0,
        "products_scanned": 0,
        "products_updated": 0,
        "product_links_added": 0,
        "link_map_size": len(link_map),
    }

    # --- 1. Blog posts ---
    posts = ((site.get("design") or {}).get("blog_posts")) or []
    new_posts = []
    for post in posts:
        stats["blog_posts_scanned"] += 1
        self_url = f"/blog/{post.get('slug','')}"
        body_md = post.get("body") or ""
        new_body, added = _inject_links_into_body(
            body_md, link_map, self_url=self_url, max_links=body.max_links_per_post
        )
        new_post = dict(post)
        if added and not body.dry_run:
            new_post["body"] = new_body
            new_post["internal_links"] = added
            new_post["internal_linked_at"] = datetime.now(timezone.utc).isoformat()
            stats["blog_posts_updated"] += 1
            stats["blog_links_added"] += len(added)
        elif added:
            stats["blog_posts_updated"] += 1
            stats["blog_links_added"] += len(added)
        new_posts.append(new_post)

    if not body.dry_run and stats["blog_posts_updated"] > 0:
        await db.sites.update_one(
            {"id": site_id},
            {"$set": {"design.blog_posts": new_posts}},
        )

    # --- 2. Product descriptions (long text fields) ---
    # Inject only in `description` + narrative sections bodies.
    for p in products:
        stats["products_scanned"] += 1
        self_url = f"/product/{p.get('id')}"
        total_added_for_product = 0
        update_ops = {}

        desc = _pick_text(p.get("description") or "")
        if desc and len(desc) > 120:
            new_desc, added = _inject_links_into_body(
                desc, link_map, self_url=self_url, max_links=body.max_links_per_product
            )
            if added:
                update_ops["description"] = new_desc if isinstance(p.get("description"), str) else {**(p.get("description") or {}), "fr": new_desc}
                total_added_for_product += len(added)

        # Narrative sections (body)
        narrative = p.get("narrative") or {}
        sections = narrative.get("sections") or []
        new_sections = list(sections)
        section_added = 0
        for i, sec in enumerate(new_sections):
            if total_added_for_product + section_added >= body.max_links_per_product:
                break
            sec_body = sec.get("body") or ""
            if not sec_body or len(sec_body) < 80:
                continue
            remaining = body.max_links_per_product - (total_added_for_product + section_added)
            new_sec_body, sec_add = _inject_links_into_body(
                sec_body, link_map, self_url=self_url, max_links=remaining
            )
            if sec_add:
                new_sections[i] = {**sec, "body": new_sec_body}
                section_added += len(sec_add)
        if section_added > 0:
            update_ops["narrative.sections"] = new_sections
            total_added_for_product += section_added

        if total_added_for_product > 0 and not body.dry_run:
            update_ops["narrative.internal_linked_at"] = datetime.now(timezone.utc).isoformat()
            update_ops["narrative.internal_links_count"] = total_added_for_product
            await db.products.update_one({"id": p["id"]}, {"$set": update_ops})
            stats["products_updated"] += 1
            stats["product_links_added"] += total_added_for_product
        elif total_added_for_product > 0:
            stats["products_updated"] += 1
            stats["product_links_added"] += total_added_for_product

    stats["total_links_added"] = stats["blog_links_added"] + stats["product_links_added"]
    stats["finished_at"] = datetime.now(timezone.utc).isoformat()
    stats["dry_run"] = body.dry_run

    # Persist last run on site for UI
    if not body.dry_run:
        await db.sites.update_one(
            {"id": site_id},
            {"$set": {"design.seo_coach.last_internal_linking_at": stats["finished_at"],
                      "design.seo_coach.last_internal_linking_stats": stats}},
        )

    return stats


@router.get("/sites/{site_id}/internal-linking/stats")
async def internal_linking_stats(site_id: str, user=Depends(get_current_user)):
    """Audit : calcule le link density moyen, les pages orphelines (0 lien
    entrant), et le dernier run sans appeler d'IA."""
    site = await db.sites.find_one({"id": site_id}, {"_id": 0})
    if not site:
        raise HTTPException(404, "Site introuvable")

    design = site.get("design") or {}
    posts = design.get("blog_posts") or []
    products = await db.products.find(
        {"site_id": site_id, "status": "active"}, {"_id": 0, "id": 1, "name": 1, "narrative": 1, "description": 1, "role": 1},
    ).to_list(500)

    # Incoming-link map : url → count
    incoming: dict[str, int] = {}
    total_outgoing = 0
    total_scanned = 0

    link_re = re.compile(r"\]\((/[^)\s]+)\)")

    def count_body(text: str):
        nonlocal total_outgoing
        if not text:
            return
        for m in link_re.finditer(text):
            url = m.group(1)
            # only internal (start with / but not //)
            if url.startswith("//"):
                continue
            incoming[url] = incoming.get(url, 0) + 1
            total_outgoing += 1

    for post in posts:
        total_scanned += 1
        count_body(post.get("body") or "")

    for p in products:
        total_scanned += 1
        count_body(_pick_text(p.get("description") or ""))
        for sec in ((p.get("narrative") or {}).get("sections") or []):
            count_body(sec.get("body") or "")

    # Orphan pages = those present in link map but with 0 incoming links
    link_map = _build_link_map(site, products)
    covered_urls = set()
    orphans: list[dict] = []
    for e in link_map:
        if e["url"] in covered_urls:
            continue
        covered_urls.add(e["url"])
        if incoming.get(e["url"], 0) == 0:
            orphans.append({"url": e["url"], "type": e["type"], "keyword": e["keyword"]})

    last_stats = (design.get("seo_coach") or {}).get("last_internal_linking_stats")
    last_run = (design.get("seo_coach") or {}).get("last_internal_linking_at")

    return {
        "total_outgoing_internal_links": total_outgoing,
        "total_documents_scanned": total_scanned,
        "average_links_per_document": round(total_outgoing / max(total_scanned, 1), 2),
        "unique_targets": len(incoming),
        "orphan_pages": orphans[:30],
        "orphan_count": len(orphans),
        "most_linked": sorted(
            [{"url": u, "count": c} for u, c in incoming.items()],
            key=lambda x: -x["count"],
        )[:10],
        "last_run_at": last_run,
        "last_run_stats": last_stats,
    }
