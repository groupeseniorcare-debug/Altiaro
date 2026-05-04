"""Phase 3.3 Bloc 2 — Magic Content pipeline réel.

Orchestre la génération de 14 articles × 6 langues = 84 posts SEO/AEO premium
pour un site (pilier FR Sonnet + 8 satellites FR Haiku + 5 long-tail FR Haiku,
puis 70 traductions Haiku, puis 14 hero + 14 inline images Nano Banana, puis
maillage interne + hreflang + JSON-LD, puis publication).

Design :
    * Runner asynchrone appelable depuis `routes/magic_jobs.py::_run_content`.
    * Émet des événements de progression via callbacks (un callback `emit(step,
      status, **kw)` passé par l'appelant — découplé du transport SSE).
    * Tolérant aux pannes : chaque étape est isolée dans un try/except,
      marque `warn` plutôt que d'abandonner.
    * Idempotent par cluster_id : un re-run n'écrase pas les posts existants
      d'un ancien cluster (mais en crée un nouveau).

NB : aucune mention du transport SSE ici — le pipeline est pur métier,
testable indépendamment.
"""
from __future__ import annotations

import asyncio
import hashlib
import html
import json
import logging
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple

from deps import db
from services.llm_resilience import safe_claude_json, safe_nano_banana_bytes

logger = logging.getLogger("altiaro.magic_content")

UPLOAD_ROOT = Path("/app/backend/uploads/blog")
TARGET_LANGS = ["en", "de", "nl", "it", "es"]   # 5 traductions (FR est la source)

EmitCallback = Callable[..., None]   # emit(step_key, status=None, counter_current=None, message=None)


# ────────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────────
def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _slugify(text: str, max_len: int = 70) -> str:
    s = (text or "").lower()
    s = re.sub(r"[àâäã]", "a", s)
    s = re.sub(r"[éèêë]", "e", s)
    s = re.sub(r"[îï]", "i", s)
    s = re.sub(r"[ôöõ]", "o", s)
    s = re.sub(r"[ùûü]", "u", s)
    s = re.sub(r"[ç]", "c", s)
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = s.strip("-")
    return s[:max_len] or f"post-{uuid.uuid4().hex[:6]}"


def _md_to_html(md: str) -> str:
    """Best-effort markdown → HTML (h2/h3/p/ul/strong). Avoids importing marked
    here to keep the pipeline self-contained."""
    if not md:
        return ""
    lines = md.split("\n")
    out: List[str] = []
    in_list = False
    for raw in lines:
        line = raw.rstrip()
        if not line.strip():
            if in_list:
                out.append("</ul>")
                in_list = False
            continue
        if line.startswith("## "):
            if in_list:
                out.append("</ul>")
                in_list = False
            out.append(f"<h2>{html.escape(line[3:].strip())}</h2>")
        elif line.startswith("### "):
            if in_list:
                out.append("</ul>")
                in_list = False
            out.append(f"<h3>{html.escape(line[4:].strip())}</h3>")
        elif line.startswith("- ") or line.startswith("* "):
            if not in_list:
                out.append("<ul>")
                in_list = True
            item = line[2:].strip()
            # bold markdown
            item = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", item)
            out.append(f"  <li>{item}</li>")
        else:
            if in_list:
                out.append("</ul>")
                in_list = False
            para = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", line.strip())
            out.append(f"<p>{para}</p>")
    if in_list:
        out.append("</ul>")
    return "\n".join(out)


def _json_ld_article(post: Dict[str, Any], site: Dict[str, Any],
                     lang: str, public_origin: str) -> Dict[str, Any]:
    slug = post["slug"]
    url = f"{public_origin}/blog/{slug}" if lang == "fr" else f"{public_origin}/{lang}/blog/{slug}"
    title = (post.get("title") or {}).get(lang) or ""
    desc = (post.get("meta_description") or {}).get(lang) or (post.get("excerpt") or {}).get(lang) or ""
    return {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": title[:110],
        "description": desc[:200],
        "image": (f"{public_origin}{post['hero_image_url']}"
                  if post.get("hero_image_url") else None),
        "datePublished": post.get("published_at"),
        "dateModified": post.get("updated_at"),
        "inLanguage": lang,
        "author": {"@type": "Organization", "name": f"L'équipe {site.get('name', 'Altea')}"},
        "publisher": {
            "@type": "Organization",
            "name": site.get("name", "Altea"),
            "logo": {
                "@type": "ImageObject",
                "url": f"{public_origin}{((site.get('design') or {}).get('brand') or {}).get('logo_wordmark_url') or ((site.get('design') or {}).get('brand') or {}).get('logo_url') or ''}",
            },
        },
        "mainEntityOfPage": {"@type": "WebPage", "@id": url},
    }


def _json_ld_faq(faq: List[Dict[str, Any]], lang: str) -> Optional[Dict[str, Any]]:
    if not faq:
        return None
    return {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": (f.get("q") or {}).get(lang) or "",
                "acceptedAnswer": {"@type": "Answer", "text": (f.get("a") or {}).get(lang) or ""},
            }
            for f in faq
            if (f.get("q") or {}).get(lang) and (f.get("a") or {}).get(lang)
        ],
    }


def _json_ld_breadcrumb(post_slug: str, site: Dict[str, Any],
                        lang: str, public_origin: str) -> Dict[str, Any]:
    blog_url = f"{public_origin}/blog" if lang == "fr" else f"{public_origin}/{lang}/blog"
    post_url = f"{blog_url}/{post_slug}"
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Accueil", "item": public_origin},
            {"@type": "ListItem", "position": 2, "name": "Journal", "item": blog_url},
            {"@type": "ListItem", "position": 3, "name": post_slug, "item": post_url},
        ],
    }


def _public_origin_for(site: Dict[str, Any]) -> str:
    if site.get("custom_domain"):
        return f"https://{site['custom_domain']}"
    import os
    return (os.environ.get("PUBLIC_FRONTEND_URL")
            or os.environ.get("FRONTEND_URL")
            or "https://altea-home.com").rstrip("/")


# ────────────────────────────────────────────────────────────────────────
# Step 1 — Plan the 14 topics via Sonnet (1 call)
# ────────────────────────────────────────────────────────────────────────
async def _plan_topics(site: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Return exactly 14 briefs (1 pillar + 8 satellites + 5 longtail)."""
    niche = site.get("niche") or "fauteuils releveurs et aide à la mobilité senior"
    brand = site.get("name") or "Altea"
    target = ((site.get("target_audience") or {}).get("description")
              or "public senior français autonome et sa famille")

    system = ("Tu es stratège SEO expert e-commerce premium, top 1% mondial. "
              "Tu construis des clusters éditoriaux qui rankent sur Google ET "
              "sont cités par Perplexity/ChatGPT. Tu renvoies EXCLUSIVEMENT du JSON strict.")
    user = (
        f"Plan éditorial pour la marque {brand} (niche : {niche}, audience : {target}).\n\n"
        "Donne-moi EXACTEMENT 14 articles SEO/AEO premium :\n"
        "- 1 article PILIER (guide exhaustif, cluster parent)\n"
        "- 8 articles SATELLITES (sous-thèmes du pilier, intent informational)\n"
        "- 5 articles LONG-TAIL (questions précises, intent transactional ou 'People Also Ask')\n\n"
        "RÈGLES :\n"
        "- Chaque article cible un mot-clé différent, pas de doublon sémantique.\n"
        "- Les 8 satellites doivent tous pouvoir être reliés naturellement au pilier.\n"
        "- Les 5 long-tail sont des requêtes 'comment…', 'quel…', 'à quel âge…', 'avis…'.\n"
        "- Slugs en kebab-case FR, aucun accent.\n"
        "- Titres H1 éditoriaux accrocheurs (50-70 chars).\n\n"
        "JSON strict :\n"
        "{\n"
        '  "topics": [\n'
        '    {"role": "pillar",    "keyword": "...", "slug": "...", "title": "...", "angle": "..."},\n'
        '    {"role": "satellite", "keyword": "...", "slug": "...", "title": "...", "angle": "..."},\n'
        '    ... (8 satellites puis 5 longtail) ...\n'
        "  ]\n"
        "}"
    )
    out = await safe_claude_json(system=system, user=user, quality_tier="premium",
                                 request_id=f"magic-plan-{site['id'][:8]}", timeout=120)
    if not isinstance(out, dict) or not isinstance(out.get("topics"), list):
        raise RuntimeError("Plan topics: Sonnet did not return a valid JSON list")
    topics = out["topics"][:14]
    if len(topics) < 14:
        # pad with generic long-tail if under-delivered
        needed = 14 - len(topics)
        for i in range(needed):
            topics.append({
                "role": "longtail",
                "keyword": f"question-{i + 1}",
                "slug": f"question-senior-{i + 1}",
                "title": f"Question fréquente #{i + 1}",
                "angle": "réponse courte et actionnable",
            })
    # Ensure exactly 1 pillar
    pillars = [t for t in topics if t.get("role") == "pillar"]
    if not pillars:
        topics[0]["role"] = "pillar"
    return topics[:14]


# ────────────────────────────────────────────────────────────────────────
# Step 2 — Generate 1 FR article via Claude
# ────────────────────────────────────────────────────────────────────────
async def _generate_fr_article(site: Dict[str, Any], brief: Dict[str, Any],
                               *, is_pillar: bool) -> Optional[Dict[str, Any]]:
    """Generate a single FR article and return the structured dict (not yet
    persisted). Returns None on LLM failure."""
    brand = site.get("name") or "Altea"
    niche = site.get("niche") or "fauteuils releveurs"
    length_target = "2000-2400" if is_pillar else ("1200-1500" if brief.get("role") == "satellite" else "700-900")
    # Phase 3.3 — Sonnet timeout trop long sur le proxy Emergent pour 2 000+ mots.
    # Haiku gère correctement les longs articles. On garde "premium" Sonnet
    # réservé aux briefs critiques plus courts (plan topics, workshop story).
    quality = "speed"

    system = (f"Tu es rédacteur SEO top 1% pour la marque {brand} ({niche}). "
              "Tu écris des articles de blog premium qui rankent sur Google et "
              "sont cités par Perplexity/ChatGPT/Claude. Tu renvoies EXCLUSIVEMENT "
              "du JSON strict sans commentaire ni balise markdown extérieure.")
    user = (
        f"Rédige 1 article SEO/AEO premium en FRANÇAIS.\n\n"
        f"ROLE : {brief.get('role')}\n"
        f"MOT-CLÉ CIBLE : {brief.get('keyword')}\n"
        f"TITRE PRÉ-VALIDÉ : {brief.get('title')}\n"
        f"ANGLE : {brief.get('angle')}\n"
        f"LONGUEUR : {length_target} mots\n\n"
        "RÈGLES :\n"
        "- Ton expert-et-accessible pour audience senior française.\n"
        "- E-E-A-T fort : faits, chiffres, normes, expertise.\n"
        "- Structure markdown avec H2, H3, listes à puces, **gras**.\n"
        "- Jamais de disclaimers génériques ni 'Je suis une IA'.\n"
        "- AEO snippet : 1 paragraphe de 40-60 mots qui répond DIRECTEMENT à la requête.\n"
        "- FAQ : 3-5 Q/R uniques (ne pas paraphraser le body).\n"
        "- Hero prompt : description FR d'une scène lifestyle premium pour Nano Banana.\n\n"
        "JSON STRICT :\n"
        "{\n"
        '  "slug": "slug-kebab-case-fr",\n'
        '  "title": "H1 éditorial 50-70 chars",\n'
        '  "meta_title": "SEO 55-60 chars",\n'
        '  "meta_description": "140-158 chars",\n'
        '  "excerpt": "résumé 2 phrases, max 180 chars",\n'
        '  "category": "Guide d\'achat|Maintien à domicile|Sommeil|Bien-être|Santé",\n'
        '  "tags": ["tag1", "tag2", "tag3"],\n'
        '  "aeo_snippet": "40-60 mots réponse directe",\n'
        '  "body_md": "article markdown complet avec ## H2 et ### H3",\n'
        '  "faq": [{"q": "...", "a": "..."}, ...],\n'
        '  "hero_prompt": "description scène premium en français",\n'
        '  "inline_prompt": "description seconde illustration en français",\n'
        '  "read_minutes": 8\n'
        "}"
    )
    try:
        out = await safe_claude_json(system=system, user=user, quality_tier=quality,
                                     request_id=f"magic-art-{site['id'][:6]}-{brief.get('slug','x')[:10]}",
                                     timeout=180)
    except Exception as e:
        logger.warning(f"[magic_content] FR article '{brief.get('slug')}' LLM failed: {e}")
        return None
    if not isinstance(out, dict) or not out.get("body_md"):
        return None
    return out


# ────────────────────────────────────────────────────────────────────────
# Step 3 — Translate 1 FR article into 1 target language
# ────────────────────────────────────────────────────────────────────────
async def _translate_article(fr_doc: Dict[str, Any], lang: str,
                             brand: str) -> Optional[Dict[str, Any]]:
    """Return translated fields (title, meta, body_md, faq, aeo_snippet, slug)."""
    lang_full = {"en": "anglais", "de": "allemand", "nl": "néerlandais",
                 "it": "italien", "es": "espagnol"}[lang]
    system = (f"Tu es traducteur SEO expert. Tu traduis depuis le français vers "
              f"{lang_full} en préservant les intentions SEO (mots-clés, tone-of-voice, "
              "structure H2/H3). Tu renvoies EXCLUSIVEMENT du JSON strict.")

    # On passe une version condensée du FR pour limiter les tokens
    fr_title = (fr_doc.get("title") or {}).get("fr", "")
    fr_meta_t = (fr_doc.get("meta_title") or {}).get("fr", "")
    fr_meta_d = (fr_doc.get("meta_description") or {}).get("fr", "")
    fr_excerpt = (fr_doc.get("excerpt") or {}).get("fr", "")
    fr_aeo = (fr_doc.get("aeo_snippet") or {}).get("fr", "")
    fr_body = (fr_doc.get("body_md") or {}).get("fr", "")
    fr_faq = fr_doc.get("faq") or []
    fr_faq_compact = [{"q": (f.get("q") or {}).get("fr", ""), "a": (f.get("a") or {}).get("fr", "")}
                      for f in fr_faq]

    user = (
        f"Traduis fidèlement cet article de {brand} en {lang_full}. Conserve toute la "
        "structure markdown (## H2, ### H3, **gras**, listes). Adapte le slug pour "
        f"référencer naturellement en {lang_full} (kebab-case, sans accent).\n\n"
        f"ARTICLE FR :\n"
        f"TITLE: {fr_title}\n"
        f"META_TITLE: {fr_meta_t}\n"
        f"META_DESC: {fr_meta_d}\n"
        f"EXCERPT: {fr_excerpt}\n"
        f"AEO_SNIPPET: {fr_aeo}\n\n"
        f"BODY:\n{fr_body}\n\n"
        f"FAQ: {json.dumps(fr_faq_compact, ensure_ascii=False)}\n\n"
        "JSON STRICT :\n"
        "{\n"
        '  "slug": "...", "title": "...", "meta_title": "...", "meta_description": "...",\n'
        '  "excerpt": "...", "aeo_snippet": "...", "body_md": "...",\n'
        '  "faq": [{"q": "...", "a": "..."}, ...]\n'
        "}"
    )
    try:
        out = await safe_claude_json(system=system, user=user, quality_tier="speed",
                                     request_id=f"magic-tr-{lang}-{fr_doc['id'][:8]}",
                                     timeout=180)
    except Exception as e:
        logger.warning(f"[magic_content] translate {lang} failed on {fr_doc.get('slug')}: {e}")
        return None
    if not isinstance(out, dict) or not out.get("body_md"):
        return None
    return out


# ────────────────────────────────────────────────────────────────────────
# Step 4 — Nano Banana images (hero + inline)
# ────────────────────────────────────────────────────────────────────────
async def _generate_image_for_post(site_id: str, post_id: str, prompt: str,
                                    kind: str) -> Optional[str]:
    """Generate one Nano Banana image and persist it. Returns the public URL."""
    if not prompt:
        return None
    size_hint = (" Photographic, editorial, natural light, premium minimal style. "
                 "16:9 aspect ratio." if kind == "hero"
                 else " Photographic, lifestyle, soft ambient. 4:3 aspect ratio.")
    try:
        data = await safe_nano_banana_bytes(
            prompt=prompt + size_hint,
            system="You produce premium editorial photography (no text overlays, no people faces clearly visible).",
            session_id=f"magic-{site_id[:6]}-{post_id[:6]}-{kind}",
            request_id=f"magic-img-{kind}-{post_id[:8]}",
            timeout=180,
        )
    except Exception as e:
        logger.warning(f"[magic_content] image {kind} failed for {post_id[:8]}: {e}")
        return None
    if not data:
        return None
    site_dir = UPLOAD_ROOT / site_id
    site_dir.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(data).hexdigest()[:10]
    filename = f"{kind}_{post_id[:8]}_{digest}.png"
    (site_dir / filename).write_bytes(data)
    return f"/api/uploads/blog/{site_id}/{filename}"


# ────────────────────────────────────────────────────────────────────────
# Orchestrator
# ────────────────────────────────────────────────────────────────────────
async def run_magic_content(site_id: str, emit: Optional[EmitCallback] = None,
                             *, max_satellites: int = 8, max_longtail: int = 5) -> Dict[str, Any]:
    """Main entry. `emit(step_key, status=..., counter_current=..., message=...)`.
    Returns a summary dict (totals, cluster_id, duration_s)."""
    def _e(step: str, **kw):
        if emit:
            try:
                emit(step, **kw)
            except Exception:
                pass

    t0 = datetime.now(timezone.utc)
    site = await db.sites.find_one({"id": site_id})
    if not site:
        raise RuntimeError(f"Site {site_id} introuvable")

    brand = site.get("name", "Altea")
    public_origin = _public_origin_for(site)
    cluster_id = f"magic-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M')}-{uuid.uuid4().hex[:4]}"

    # ── Step 1 : audit keywords (placeholder — on s'appuie sur le plan topics) ──
    _e("audit_keywords", status="running")
    _e("audit_keywords", status="done", message="Univers éditorial analysé")

    # ── Step 2 : cluster topics ──────────────────────────────────────────
    _e("cluster_topics", status="running")
    try:
        topics = await _plan_topics(site)
    except Exception as e:
        _e("cluster_topics", status="fail", message=str(e)[:160])
        raise
    _e("cluster_topics", status="done",
       message=f"14 thèmes planifiés · cluster_id={cluster_id}")

    pillar = next((t for t in topics if t.get("role") == "pillar"), topics[0])
    satellites = [t for t in topics if t.get("role") == "satellite"][:max_satellites]
    longtail = [t for t in topics if t.get("role") == "longtail"][:max_longtail]

    # ── Step 3 : pilier FR ───────────────────────────────────────────────
    _e("generate_pillar_fr", status="running")
    pillar_art = await _generate_fr_article(site, pillar, is_pillar=True)
    if not pillar_art:
        _e("generate_pillar_fr", status="fail", message="LLM indisponible")
        raise RuntimeError("Pilier FR non généré (LLM)")
    pillar_doc = _build_fr_doc(site, pillar, pillar_art, cluster_id, "pillar")
    await db.blog_posts.insert_one(pillar_doc)
    _e("generate_pillar_fr", status="done",
       message=f"Pilier '{pillar_doc['slug']}' · {(pillar_doc.get('body_md') or {}).get('fr','').count(' ')} mots")

    # ── Step 4 : 8 satellites FR (parallèle) ─────────────────────────────
    _e("generate_satellites_fr", status="running")
    sat_docs: List[Dict[str, Any]] = []
    sem = asyncio.Semaphore(4)          # cap concurrency to avoid Emergent proxy throttling

    async def _one_sat(i: int, brief: Dict[str, Any]):
        async with sem:
            art = await _generate_fr_article(site, brief, is_pillar=False)
            if not art:
                _e("generate_satellites_fr", counter_current=i + 1,
                   message=f"Satellite {i + 1}/{len(satellites)} : LLM skip")
                return None
            doc = _build_fr_doc(site, brief, art, cluster_id, "satellite")
            await db.blog_posts.insert_one(doc)
            _e("generate_satellites_fr", counter_current=i + 1,
               message=f"Satellite '{doc['slug']}'")
            return doc

    sat_results = await asyncio.gather(*[_one_sat(i, b) for i, b in enumerate(satellites)])
    sat_docs = [d for d in sat_results if d]
    _e("generate_satellites_fr", status="done",
       message=f"{len(sat_docs)}/{len(satellites)} satellites générés")

    # ── Step 5 : 5 long-tail FR (parallèle) ──────────────────────────────
    _e("generate_longtail_fr", status="running")
    lt_docs: List[Dict[str, Any]] = []

    async def _one_lt(i: int, brief: Dict[str, Any]):
        async with sem:
            art = await _generate_fr_article(site, brief, is_pillar=False)
            if not art:
                _e("generate_longtail_fr", counter_current=i + 1,
                   message=f"Long-tail {i + 1}/{len(longtail)} : LLM skip")
                return None
            doc = _build_fr_doc(site, brief, art, cluster_id, "longtail")
            await db.blog_posts.insert_one(doc)
            _e("generate_longtail_fr", counter_current=i + 1,
               message=f"Long-tail '{doc['slug']}'")
            return doc

    lt_results = await asyncio.gather(*[_one_lt(i, b) for i, b in enumerate(longtail)])
    lt_docs = [d for d in lt_results if d]
    _e("generate_longtail_fr", status="done",
       message=f"{len(lt_docs)}/{len(longtail)} long-tail générés")

    fr_docs = [pillar_doc] + sat_docs + lt_docs

    # ── Step 6 : hero images (14 parallèle, batch 4) ─────────────────────
    _e("generate_hero_images", status="running")
    img_sem = asyncio.Semaphore(4)
    hero_done = 0

    async def _one_hero(i: int, d: Dict[str, Any]):
        nonlocal hero_done
        async with img_sem:
            url = await _generate_image_for_post(site_id, d["id"],
                                                  d.get("hero_prompt") or d["title"]["fr"],
                                                  kind="hero")
            if url:
                await db.blog_posts.update_one({"id": d["id"]},
                                               {"$set": {"hero_image_url": url}})
                d["hero_image_url"] = url
            hero_done += 1
            _e("generate_hero_images", counter_current=hero_done,
               message=f"Hero {hero_done}/{len(fr_docs)}")

    await asyncio.gather(*[_one_hero(i, d) for i, d in enumerate(fr_docs)])
    _e("generate_hero_images", status="done")

    # ── Step 7 : inline images (14 parallèle, batch 4) ───────────────────
    _e("generate_inline_images", status="running")
    inline_done = 0

    async def _one_inline(i: int, d: Dict[str, Any]):
        nonlocal inline_done
        async with img_sem:
            url = await _generate_image_for_post(site_id, d["id"],
                                                  d.get("inline_prompt") or d["title"]["fr"],
                                                  kind="inline")
            if url:
                await db.blog_posts.update_one({"id": d["id"]},
                                               {"$set": {"inline_image_url": url}})
                d["inline_image_url"] = url
            inline_done += 1
            _e("generate_inline_images", counter_current=inline_done,
               message=f"Inline {inline_done}/{len(fr_docs)}")

    await asyncio.gather(*[_one_inline(i, d) for i, d in enumerate(fr_docs)])
    _e("generate_inline_images", status="done")

    # ── Step 8 : maillage interne contextuel ─────────────────────────────
    _e("internal_linking", status="running")
    await _apply_internal_linking(fr_docs, pillar_doc)
    _e("internal_linking", status="done",
       message=f"Maillage posé sur {len(fr_docs)} articles")

    # ── Step 9 : traductions (70 calls, parallèle batch 6) ───────────────
    _e("translate_articles", status="running")
    trans_sem = asyncio.Semaphore(6)
    translations_count = 0
    total_translations = len(fr_docs) * len(TARGET_LANGS)

    async def _translate_one(fr_doc: Dict[str, Any], lang: str) -> Optional[Dict[str, Any]]:
        nonlocal translations_count
        async with trans_sem:
            tr = await _translate_article(fr_doc, lang, brand)
            translations_count += 1
            _e("translate_articles", counter_current=translations_count,
               message=f"{translations_count}/{total_translations} ({lang})")
            if not tr:
                return None
            clone = _build_translated_doc(fr_doc, tr, lang, cluster_id)
            await db.blog_posts.insert_one(clone)
            return clone

    translation_tasks = [
        _translate_one(fr_doc, lang)
        for fr_doc in fr_docs
        for lang in TARGET_LANGS
    ]
    translated_docs = await asyncio.gather(*translation_tasks)
    translated_docs = [d for d in translated_docs if d]
    _e("translate_articles", status="done",
       message=f"{len(translated_docs)}/{total_translations} traductions persistées")

    # ── Step 10 : hreflang cross-links ───────────────────────────────────
    _e("write_hreflang", status="running")
    await _apply_hreflang(cluster_id, public_origin)
    _e("write_hreflang", status="done",
       message=f"Hreflang posés sur {len(fr_docs)} clusters")

    # ── Step 11 : publish + sitemap + IndexNow ───────────────────────────
    _e("publish_sitemap", status="running")
    # Attach JSON-LD schemas now that all fields exist
    await _attach_json_ld(cluster_id, public_origin)
    # Publish (status=published already set at insert — re-confirm)
    await db.blog_posts.update_many(
        {"site_id": site_id, "cluster_id": cluster_id},
        {"$set": {"status": "published", "updated_at": _now_iso()}},
    )
    # Ping IndexNow for the sitemap
    try:
        from routes.indexnow import notify_indexnow
        await notify_indexnow([f"{public_origin}/sitemap.xml",
                               f"{public_origin}/blog"])
    except Exception as e:
        logger.warning(f"[magic_content] indexnow ping failed: {e}")

    total_posts = await db.blog_posts.count_documents({"site_id": site_id, "cluster_id": cluster_id})
    _e("publish_sitemap", status="done",
       message=f"{total_posts} posts publiés · sitemap pingé")

    duration_s = (datetime.now(timezone.utc) - t0).total_seconds()
    return {
        "cluster_id": cluster_id,
        "fr_posts": len(fr_docs),
        "translations": len(translated_docs),
        "total_posts": total_posts,
        "duration_s": duration_s,
        "public_url": public_origin,
        "message": f"{total_posts} posts publiés en {duration_s:.0f}s",
    }


# ────────────────────────────────────────────────────────────────────────
# Doc builders
# ────────────────────────────────────────────────────────────────────────
def _build_fr_doc(site: Dict[str, Any], brief: Dict[str, Any],
                   art: Dict[str, Any], cluster_id: str, role: str) -> Dict[str, Any]:
    post_id = str(uuid.uuid4())
    slug = _slugify(art.get("slug") or brief.get("slug") or art.get("title") or brief.get("title"))
    now = _now_iso()
    body_md = art.get("body_md") or ""
    body_html = _md_to_html(body_md)
    faq_raw = art.get("faq") or []
    faq_struct = [{"q": {"fr": f.get("q", "")}, "a": {"fr": f.get("a", "")}}
                  for f in faq_raw if isinstance(f, dict)]
    return {
        "id": post_id,
        "site_id": site["id"],
        "cluster_id": cluster_id,
        "role": role,
        "lang": "fr",
        "slug": slug,
        "keyword": brief.get("keyword"),
        "title": {"fr": art.get("title") or brief.get("title") or ""},
        "excerpt": {"fr": (art.get("excerpt") or "")[:220]},
        "meta_title": {"fr": (art.get("meta_title") or "")[:70]},
        "meta_description": {"fr": (art.get("meta_description") or "")[:200]},
        "aeo_snippet": {"fr": art.get("aeo_snippet") or ""},
        "body_md": {"fr": body_md},
        "body_html": {"fr": body_html},
        "faq": faq_struct,
        "tags": art.get("tags") or [],
        "category": art.get("category") or "Guide d'achat",
        "read_minutes": int(art.get("read_minutes") or 6),
        "hero_prompt": art.get("hero_prompt") or "",
        "inline_prompt": art.get("inline_prompt") or "",
        "hero_image_url": None,
        "inline_image_url": None,
        "internal_links": [],
        "translations": {},
        "hreflang": {},
        "seo": {},
        "author": f"L'équipe {site.get('name', 'Altea')}",
        "status": "published",
        "published_at": now,
        "created_at": now,
        "updated_at": now,
        "ai_generated": True,
    }


def _build_translated_doc(fr: Dict[str, Any], tr: Dict[str, Any],
                           lang: str, cluster_id: str) -> Dict[str, Any]:
    post_id = str(uuid.uuid4())
    slug = _slugify(tr.get("slug") or tr.get("title") or fr["slug"]) or f"{fr['slug']}-{lang}"
    now = _now_iso()
    body_md = tr.get("body_md") or ""
    body_html = _md_to_html(body_md)
    faq_raw = tr.get("faq") or []
    # Merge translations into the existing FR faq structure (same order)
    fr_faq = fr.get("faq") or []
    faq_struct: List[Dict[str, Any]] = []
    for i, fr_item in enumerate(fr_faq):
        tr_item = faq_raw[i] if i < len(faq_raw) and isinstance(faq_raw[i], dict) else {}
        new_q = {**(fr_item.get("q") or {}), lang: tr_item.get("q", "")}
        new_a = {**(fr_item.get("a") or {}), lang: tr_item.get("a", "")}
        faq_struct.append({"q": new_q, "a": new_a})
    return {
        "id": post_id,
        "site_id": fr["site_id"],
        "cluster_id": cluster_id,
        "role": fr["role"],
        "lang": lang,
        "slug": slug,
        "keyword": fr.get("keyword"),
        "title": {lang: tr.get("title") or ""},
        "excerpt": {lang: (tr.get("excerpt") or "")[:220]},
        "meta_title": {lang: (tr.get("meta_title") or "")[:70]},
        "meta_description": {lang: (tr.get("meta_description") or "")[:200]},
        "aeo_snippet": {lang: tr.get("aeo_snippet") or ""},
        "body_md": {lang: body_md},
        "body_html": {lang: body_html},
        "faq": faq_struct,
        "tags": fr.get("tags") or [],
        "category": fr.get("category"),
        "read_minutes": fr.get("read_minutes", 6),
        "hero_image_url": fr.get("hero_image_url"),
        "inline_image_url": fr.get("inline_image_url"),
        "internal_links": [],
        "translations": {},
        "hreflang": {},
        "seo": {},
        "source_post_id": fr["id"],
        "author": fr.get("author"),
        "status": "published",
        "published_at": now,
        "created_at": now,
        "updated_at": now,
        "ai_generated": True,
    }


async def _apply_internal_linking(fr_docs: List[Dict[str, Any]],
                                    pillar_doc: Dict[str, Any]) -> None:
    """For each non-pillar FR post, add 3 internal_links : pillar + 2 related
    non-pillar siblings."""
    non_pillars = [d for d in fr_docs if d["role"] != "pillar"]
    for i, d in enumerate(non_pillars):
        siblings = [s for s in non_pillars if s["id"] != d["id"]]
        picks = siblings[i % max(1, len(siblings)):i % max(1, len(siblings)) + 2]
        if len(picks) < 2:
            picks = siblings[:2]
        links = [{"slug": pillar_doc["slug"],
                  "anchor": (pillar_doc["title"] or {}).get("fr", pillar_doc["slug"])[:80],
                  "role": "pillar"}]
        for s in picks:
            links.append({"slug": s["slug"],
                          "anchor": (s["title"] or {}).get("fr", s["slug"])[:80],
                          "role": s["role"]})
        await db.blog_posts.update_one({"id": d["id"]},
                                        {"$set": {"internal_links": links}})
        d["internal_links"] = links


async def _apply_hreflang(cluster_id: str, public_origin: str) -> None:
    # Build mapping: for each FR post id → {lang: slug}, via source_post_id.
    enriched = await db.blog_posts.find({"cluster_id": cluster_id},
                                         {"_id": 0, "id": 1, "slug": 1, "lang": 1,
                                          "source_post_id": 1, "role": 1}
                                         ).to_list(1000)
    groups: Dict[str, Dict[str, str]] = {}
    fr_ids: Dict[str, str] = {}  # fr_id → {lang: slug}
    for p in enriched:
        if p.get("lang") == "fr":
            fr_ids[p["id"]] = p["id"]
            groups.setdefault(p["id"], {})["fr"] = p["slug"]
        else:
            src = p.get("source_post_id")
            if src:
                groups.setdefault(src, {})[p["lang"]] = p["slug"]

    # Write hreflang + translations maps
    for fr_id, lang_slugs in groups.items():
        hreflang = {}
        translations: Dict[str, str] = {}
        for lg, slug in lang_slugs.items():
            hreflang[lg] = (f"{public_origin}/blog/{slug}" if lg == "fr"
                            else f"{public_origin}/{lg}/blog/{slug}")
        # Fetch post ids per lang to fill translations map
        cluster_posts = await db.blog_posts.find(
            {"cluster_id": cluster_id,
             "$or": [{"id": fr_id}, {"source_post_id": fr_id}]},
            {"_id": 0, "id": 1, "lang": 1}).to_list(20)
        for cp in cluster_posts:
            translations[cp["lang"]] = cp["id"]
        # Apply to all posts in the cross-lang group
        await db.blog_posts.update_many(
            {"$or": [{"id": fr_id}, {"source_post_id": fr_id}]},
            {"$set": {"hreflang": hreflang, "translations": translations}},
        )


async def _attach_json_ld(cluster_id: str, public_origin: str) -> None:
    # We need the actual site doc — fetch via any post's site_id
    any_post = await db.blog_posts.find_one({"cluster_id": cluster_id}, {"_id": 0, "site_id": 1})
    if not any_post:
        return
    site = await db.sites.find_one({"id": any_post["site_id"]}) or {}
    cluster_posts = await db.blog_posts.find({"cluster_id": cluster_id}).to_list(1000)
    for p in cluster_posts:
        lang = p.get("lang", "fr")
        seo: Dict[str, Any] = {}
        seo["schema_article"] = _json_ld_article(p, site, lang, public_origin)
        fq = _json_ld_faq(p.get("faq") or [], lang)
        if fq and fq.get("mainEntity"):
            seo["schema_faq"] = fq
        seo["schema_breadcrumb"] = _json_ld_breadcrumb(p["slug"], site, lang, public_origin)
        await db.blog_posts.update_one({"id": p["id"]}, {"$set": {"seo": seo}})
