"""
Blog posts CRUD on site.design.blog_posts — no separate collection,
just embedded in the site's design document.

Optional AI generation endpoint to auto-draft SEO articles.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel

from deps import db, get_current_user

logger = logging.getLogger("conceptfactory.blog_posts")
EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")

router = APIRouter()

_JSON_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```\s*$", re.MULTILINE)


def _strip_json_fence(text: str) -> str:
    return _JSON_FENCE_RE.sub("", (text or "").strip()).strip()


def _slugify(text: str) -> str:
    s = re.sub(r"[^\w\s-]", "", (text or "").lower())
    s = re.sub(r"[\s_-]+", "-", s).strip("-")
    return s[:70] or f"article-{uuid.uuid4().hex[:6]}"


class BlogPostInput(BaseModel):
    slug: Optional[str] = None
    title: str
    category: Optional[str] = ""
    excerpt: Optional[str] = ""
    body: Optional[str] = ""
    image: Optional[str] = ""
    read_minutes: Optional[int] = 4
    author: Optional[str] = ""
    published_at: Optional[str] = None
    # Chantier 5 — traductions multi-langue optionnelles
    # Structure : {"de": {"title":"...", "excerpt":"...", "body":"..."},
    #              "en": {...}, "nl": {...}, "it": {...}, "es": {...}}
    # La langue source n'est PAS dans ce dict (title/excerpt/body au top-level).
    translations: Optional[dict] = None


class AIDraftInput(BaseModel):
    keyword: str
    angle: Optional[str] = ""    # ex: "guide d'achat", "tendance", "FAQ approfondie"
    length: Optional[str] = "long"  # short | medium | long


class TranslateInput(BaseModel):
    """Chantier 5 — Cible optionnelle, sinon toutes les langues seo_countries manquantes."""
    langs: Optional[List[str]] = None
    overwrite: Optional[bool] = False  # si True, re-traduire les langues déjà présentes


def _ensure_site(site_id: str):
    return db.sites.find_one({"id": site_id}, {"_id": 0})


@router.get("/sites/{site_id}/blog-posts")
async def list_blog_posts(site_id: str, user=Depends(get_current_user)):
    """Liste les articles d'un site.

    Source de vérité (2026-04-29) : la **collection `db.blog_posts`** (où
    le worker async pousse les articles générés par la factory). On y ajoute
    les articles "manuels" stockés historiquement dans `site.design.blog_posts`
    (CRUD direct), avec dédoublonnage par slug. Avant ce fix, l'endpoint
    retournait UNIQUEMENT l'array embarqué dans le site → la liste était vide
    alors que la collection contenait 3 articles publiés (incohérence avec
    `automation/status::blog_total`).
    """
    site = await _ensure_site(site_id)
    if not site:
        raise HTTPException(404, "Site introuvable")
    out: list[dict] = []
    seen_slugs: set[str] = set()

    # 1) Articles générés / publiés en collection (source de vérité worker async)
    cursor = db.blog_posts.find({"site_id": site_id}, {"_id": 0}).sort(
        [("published_at", -1), ("created_at", -1)]
    )
    async for p in cursor:
        slug = p.get("slug") or p.get("id")
        if not slug:
            continue
        # Normalise les champs pour le frontend (le doc collection peut
        # avoir `title` en dict i18n {"fr": "..."}). On garde la version FR
        # par défaut, fallback 1ère valeur disponible, fallback slug.
        title = p.get("title")
        if isinstance(title, dict):
            title = title.get("fr") or title.get("en") or next(iter(title.values()), None) or slug
        excerpt = p.get("excerpt") or p.get("summary")
        if isinstance(excerpt, dict):
            excerpt = excerpt.get("fr") or excerpt.get("en") or next(iter(excerpt.values()), None)
        norm = {
            "id": p.get("id") or slug,
            "slug": slug,
            "title": title or slug,
            "excerpt": excerpt or "",
            "language": p.get("language") or p.get("lang") or "fr",
            "type": p.get("type") or p.get("role") or "article",
            "status": p.get("status") or "published",
            "published_at": p.get("published_at") or p.get("created_at"),
            "created_at": p.get("created_at"),
            "cover_image": p.get("cover_image") or p.get("hero_image") or p.get("image_url"),
        }
        out.append(norm)
        seen_slugs.add(slug)

    # 2) Articles manuels (legacy, stockés dans le doc site)
    embedded = (site.get("design") or {}).get("blog_posts") or []
    for p in embedded:
        slug = p.get("slug") or p.get("id")
        if not slug or slug in seen_slugs:
            continue
        out.append(p)
    return out


@router.post("/sites/{site_id}/blog-posts")
async def create_blog_post(
    site_id: str,
    body: BlogPostInput,
    background: BackgroundTasks,
    user=Depends(get_current_user),
):
    site = await _ensure_site(site_id)
    if not site:
        raise HTTPException(404, "Site introuvable")
    post = body.model_dump()
    post["slug"] = _slugify(post.get("slug") or post["title"])
    post["published_at"] = post.get("published_at") or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    post["id"] = str(uuid.uuid4())
    # check slug uniqueness
    existing = (site.get("design") or {}).get("blog_posts") or []
    if any(p.get("slug") == post["slug"] for p in existing):
        post["slug"] = f"{post['slug']}-{uuid.uuid4().hex[:4]}"
    await db.sites.update_one(
        {"id": site_id},
        {"$push": {"design.blog_posts": post}},
    )
    # Chantier 5 — Auto-translate en background pour toutes les langues seo_countries
    # manquantes. Si pas de EMERGENT_LLM_KEY → skip silencieux.
    background.add_task(_bg_auto_translate_post, site_id, post["slug"])
    # Phase 6 — marque sitemap dirty pour re-submit auto (cron 10min)
    try:
        from routes.seo_automation import mark_sitemap_dirty
        background.add_task(mark_sitemap_dirty, site_id)
    except Exception:
        pass
    return post


@router.patch("/sites/{site_id}/blog-posts/{slug}")
async def update_blog_post(
    site_id: str,
    slug: str,
    body: BlogPostInput,
    background: BackgroundTasks,
    user=Depends(get_current_user),
):
    site = await _ensure_site(site_id)
    if not site:
        raise HTTPException(404, "Site introuvable")
    posts = (site.get("design") or {}).get("blog_posts") or []
    found = None
    for p in posts:
        if p.get("slug") == slug:
            found = p
            break
    if not found:
        raise HTTPException(404, "Article introuvable")
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    # don't change slug via this endpoint (would break URLs)
    updates.pop("slug", None)
    # Si le body source change, les translations existantes deviennent obsolètes
    content_changed = any(
        k in updates and updates[k] != found.get(k) for k in ("title", "excerpt", "body")
    )
    if content_changed:
        found["translations"] = {}  # invalider, la background task va retraduire
    found.update(updates)
    await db.sites.update_one({"id": site_id}, {"$set": {"design.blog_posts": posts}})
    if content_changed:
        background.add_task(_bg_auto_translate_post, site_id, slug)
    # Phase 6 — sitemap dirty
    try:
        from routes.seo_automation import mark_sitemap_dirty
        background.add_task(mark_sitemap_dirty, site_id)
    except Exception:
        pass
    return found


@router.delete("/sites/{site_id}/blog-posts/{slug}")
async def delete_blog_post(site_id: str, slug: str, user=Depends(get_current_user)):
    site = await _ensure_site(site_id)
    if not site:
        raise HTTPException(404, "Site introuvable")
    await db.sites.update_one(
        {"id": site_id},
        {"$pull": {"design.blog_posts": {"slug": slug}}},
    )
    return {"status": "ok"}


# ---------------------------------------------------------------
# Chantier 5 — Traductions multi-langue des articles blog
# ---------------------------------------------------------------

_LANG_NAMES = {
    "fr": "French (senior-friendly, rassurant, jamais de jargon US)",
    "de": "German (clear, precise, professional)",
    "en": "English (UK, clean, benefit-focused)",
    "nl": "Dutch (direct, friendly)",
    "it": "Italian (warm, persuasive)",
    "es": "Spanish (Spain, cordial, clear)",
}

# Chantier 5 — throttling auto-translate : 1 traduction à la fois pour éviter
# d'exploser les quotas LiteLLM / Claude (les traductions sont fire-and-forget,
# pas bloquantes pour le user).
_TRANSLATE_SEMA = asyncio.Semaphore(1)


async def _bg_auto_translate_post(site_id: str, slug: str) -> None:
    """BackgroundTask : traduit un article dans toutes les langues seo_countries
    manquantes. Tolérant aux erreurs (log + exit) car c'est du best-effort.
    """
    if not EMERGENT_LLM_KEY:
        logger.info(f"[bg-translate] SKIP {site_id}/{slug} — no EMERGENT_LLM_KEY")
        return
    async with _TRANSLATE_SEMA:
        try:
            from seo_constants import get_seo_langs, ALL_SUPPORTED_LANGS
            site = await db.sites.find_one({"id": site_id}, {"_id": 0})
            if not site:
                return
            posts = (site.get("design") or {}).get("blog_posts") or []
            post = next((p for p in posts if p.get("slug") == slug), None)
            if not post or not (post.get("body") or "").strip():
                return
            source_lang = (post.get("source_lang") or "fr").lower()
            existing = post.get("translations") or {}
            target_langs = [lg for lg in get_seo_langs(site) if lg != source_lang and lg not in existing]
            target_langs = [lg for lg in target_langs if lg in ALL_SUPPORTED_LANGS]
            if not target_langs:
                return

            title = post.get("title") or ""
            excerpt = post.get("excerpt") or ""
            body = post.get("body") or ""
            body_trimmed = body[:12000] if len(body) > 12000 else body
            langs_desc = ", ".join(_LANG_NAMES.get(lg, lg) for lg in target_langs)
            system = (
                "You are a senior e-commerce editorial translator. Output STRICT JSON "
                "only. Preserve markdown structure (headings, lists). Never invent "
                "facts. Adapt culturally, don't literal-translate."
            )
            user_prompt = f"""Translate and adapt this article from {source_lang.upper()} into: {langs_desc}.

Title: {title}
Excerpt: {excerpt}
Body:
{body_trimmed}

Return STRICT JSON: one key per target language containing {{title, excerpt, body}}.
Languages: {", ".join(target_langs)}"""
            res = await _call_claude_json(system, user_prompt, timeout=180)
            if not isinstance(res, dict):
                logger.warning(f"[bg-translate] {site_id}/{slug} — invalid Claude payload")
                return
            updated = dict(existing)
            now_iso = datetime.now(timezone.utc).isoformat()
            translated: list[str] = []
            for lg in target_langs:
                block = res.get(lg) or {}
                if isinstance(block, dict) and block.get("title") and block.get("body"):
                    updated[lg] = {
                        "title": str(block.get("title"))[:250],
                        "excerpt": str(block.get("excerpt") or "")[:600],
                        "body": str(block.get("body") or "")[:40000],
                        "translated_at": now_iso,
                    }
                    translated.append(lg)
            if not translated:
                logger.warning(f"[bg-translate] {site_id}/{slug} — 0 langs translated")
                return
            # Re-fetch pour éviter les écrasements concurrents
            fresh = await db.sites.find_one({"id": site_id}, {"_id": 0, "design.blog_posts": 1})
            posts2 = ((fresh or {}).get("design") or {}).get("blog_posts") or []
            for p in posts2:
                if p.get("slug") == slug:
                    merged = dict(p.get("translations") or {})
                    merged.update(updated)
                    p["translations"] = merged
                    p["source_lang"] = source_lang
                    break
            await db.sites.update_one(
                {"id": site_id},
                {"$set": {"design.blog_posts": posts2}},
            )
            logger.info(f"[bg-translate] {site_id}/{slug} — translated {translated}")
        except Exception:
            logger.exception(f"[bg-translate] {site_id}/{slug} — unexpected error")


@router.post("/sites/{site_id}/blog-posts/{slug}/translate")
async def translate_blog_post(
    site_id: str,
    slug: str,
    data: "TranslateInput",
    user=Depends(get_current_user),
):
    """Traduit un article dans toutes les langues seo_countries manquantes
    (ou celles explicitement demandées). Appel Claude. Persiste
    `post.translations[lg] = {title, excerpt, body}`.

    - data.langs: ["de","en"] → force ces langues (même si déjà présentes si overwrite=True)
    - data.langs None → auto : langues seo_countries - {source_lang} - {déjà présentes, sauf overwrite}
    """
    from seo_constants import get_seo_langs, ALL_SUPPORTED_LANGS
    site = await _ensure_site(site_id)
    if not site:
        raise HTTPException(404, "Site introuvable")
    posts = (site.get("design") or {}).get("blog_posts") or []
    post = next((p for p in posts if p.get("slug") == slug), None)
    if not post:
        raise HTTPException(404, "Article introuvable")

    # Source language : on assume FR (peut devenir dynamique via post.source_lang plus tard)
    source_lang = (post.get("source_lang") or "fr").lower()
    existing_translations = post.get("translations") or {}

    # Langues cibles
    if data.langs:
        target_langs = [lg.lower() for lg in data.langs if lg.lower() in ALL_SUPPORTED_LANGS]
    else:
        site_langs = get_seo_langs(site)
        target_langs = [lg for lg in site_langs if lg != source_lang]
    if not data.overwrite:
        target_langs = [lg for lg in target_langs if not existing_translations.get(lg)]
    if not target_langs:
        return {"ok": True, "post_slug": slug, "translated": [], "message": "Aucune langue à traduire"}

    if not EMERGENT_LLM_KEY:
        raise HTTPException(503, "Translation service unavailable (EMERGENT_LLM_KEY missing)")

    title = post.get("title") or ""
    excerpt = post.get("excerpt") or ""
    body = post.get("body") or ""
    # Cap body size to respect context window
    body_trimmed = body[:12000] if len(body) > 12000 else body

    langs_desc = ", ".join(_LANG_NAMES.get(lg, lg) for lg in target_langs)
    system = (
        "You are a senior e-commerce editorial translator for a premium Silver-Economy "
        "French brand. You produce fluent, culturally-adapted copy (never literal). "
        "Preserve the original markdown/HTML structure (headings, lists, bold). "
        "Never invent specs or claims. Output STRICT JSON only, no prose."
    )
    user_prompt = f"""Translate and adapt the following blog article from {source_lang.upper()} into these languages: {langs_desc}.

SOURCE:
Title: {title}
Excerpt: {excerpt}
Body (markdown/HTML):
{body_trimmed}

Rules:
- Keep title < 80 chars, keyword-friendly for the target locale
- Excerpt: 1-2 short sentences, hook-style
- Body: preserve all headings (##, ###) and lists. Rewrite in the target language's natural style, don't literal-translate.
- Adapt currency mentions (€ → £ for en_UK if present, CHF for Swiss content only if context implies it; keep € otherwise).
- Remove any explicit "en France" / "French" references when translating to non-FR languages; replace with the local equivalent or remove.

Return STRICT JSON with one key per target language:
{{"de": {{"title":"...", "excerpt":"...", "body":"..."}}, "en": {{...}}, ...}}

Languages to produce: {", ".join(target_langs)}
"""
    try:
        res = await _call_claude_json(system, user_prompt, timeout=180)
    except Exception:
        logger.exception("blog translate failed")
        raise HTTPException(502, "Translation IA failed (try again in 30s)")
    if not isinstance(res, dict):
        raise HTTPException(502, "Translation IA returned invalid payload")

    translated_ok: list[str] = []
    for lg in target_langs:
        block = res.get(lg) or {}
        if isinstance(block, dict) and block.get("title") and block.get("body"):
            existing_translations[lg] = {
                "title": str(block.get("title"))[:250],
                "excerpt": str(block.get("excerpt") or "")[:600],
                "body": str(block.get("body") or "")[:40000],
                "translated_at": datetime.now(timezone.utc).isoformat(),
            }
            translated_ok.append(lg)

    if not translated_ok:
        raise HTTPException(502, "No language translated successfully")

    post["translations"] = existing_translations
    post["source_lang"] = source_lang
    await db.sites.update_one(
        {"id": site_id},
        {"$set": {"design.blog_posts": posts}},
    )
    return {
        "ok": True,
        "post_slug": slug,
        "source_lang": source_lang,
        "translated": translated_ok,
        "skipped": [lg for lg in target_langs if lg not in translated_ok],
        "existing_langs": list(existing_translations.keys()),
    }





async def _call_claude_json(system: str, user: str, timeout: int = 120):
    """Phase 0 — délègue à `safe_claude_json` (retry expo + circuit breaker).

    Le wrapper applique déjà : 3 retries exponentiels (2s/8s/32s + jitter)
    sur 502/503/504/timeout/429, et OPEN le circuit après 5 échecs consécutifs.
    Préserve les comportements historiques : retourne `None` si LLM down ou
    parse error, et persiste `platform_health.llm = budget_exhausted` si Claude
    a renvoyé un message de budget épuisé.
    """
    if not EMERGENT_LLM_KEY:
        return None
    from services.llm_resilience import safe_claude_json, LLMUnavailableError
    try:
        return await safe_claude_json(system, user, session_id=f"blog-{uuid.uuid4().hex[:8]}", timeout=timeout)
    except LLMUnavailableError as e:
        logger.warning(f"[blog-claude] LLM unavailable after retries: {e.last_error}")
        return None
    except ValueError as e:
        logger.warning(f"[blog-claude] JSON parse failed: {e}")
        return None
    except Exception as e:
        msg = str(e)
        if "Budget has been exceeded" in msg or ("budget" in msg.lower() and "exceeded" in msg.lower()):
            try:
                await db.platform_health.update_one(
                    {"key": "llm"},
                    {"$set": {"key": "llm", "status": "budget_exhausted",
                              "last_error_at": datetime.now(timezone.utc).isoformat()}},
                    upsert=True,
                )
            except Exception:
                pass
        logger.exception(f"Blog Claude call failed: {msg[:200]}")
        return None


@router.post("/sites/{site_id}/blog-posts/ai-draft")
async def ai_draft_blog_post(site_id: str, body: AIDraftInput, user=Depends(get_current_user)):
    """Generate a SEO-optimized article draft from a keyword + angle."""
    site = await _ensure_site(site_id)
    if not site:
        raise HTTPException(404, "Site introuvable")

    target_words = {"short": "600-800", "medium": "1000-1400", "long": "1800-2400"}.get(body.length, "1800-2400")

    system = (
        "Tu es un rédacteur SEO expert (top 1% mondial) pour le marché senior français. "
        "Tu écris des guides éditoriaux qui rankent organiquement sur Google ET sont cités par ChatGPT/Perplexity. "
        "Tu renvoies UNIQUEMENT du JSON valide, sans commentaire."
    )
    user = f"""Rédige un article SEO premium pour le blog de {site.get('name')} (niche : {site.get('niche')}).

MOT-CLÉ CIBLE : {body.keyword}
ANGLE : {body.angle or "guide d'achat expert"}
LONGUEUR CIBLE : {target_words} mots

RÈGLES :
- Ton expert-et-accessible, aucun jargon médical lourd.
- E-E-A-T maximum : cite des faits, des chiffres, des normes, mentionne l'expertise d'ergothérapeutes.
- Structure markdown : H2 et H3, listes à puces quand utile, **gras** pour les faits clés.
- Ne mentionne JAMAIS explicitement "Je suis une IA" ou des disclaimers génériques.
- Inclus au moins : 1 tableau comparatif sous forme de liste, 1 section "À retenir", 1 mini-FAQ (3 questions).
- Meta title 55-60 chars + meta description 140-158 chars optimisés.

Retourne EXACTEMENT ce JSON :
{{
  "slug": "slug-seo-kebab-case-avec-keyword",
  "title": "Titre éditorial accrocheur 50-70 caractères",
  "meta_title": "Titre SEO 55-60 chars",
  "meta_description": "Meta description 140-158 chars",
  "category": "Guide d'achat|Maintien à domicile|Sommeil|Bien-être|Santé",
  "excerpt": "Résumé de 2 phrases pour les cards (max 180 caractères)",
  "read_minutes": 5,
  "body": "Article markdown complet avec H2, H3, listes, gras — minimum 1500 caractères"
}}"""

    data = await _call_claude_json(system, user)
    if not data or not isinstance(data, dict):
        raise HTTPException(502, "IA indisponible. Réessayez ou rédigez manuellement.")

    post = {
        "id": str(uuid.uuid4()),
        "slug": _slugify(data.get("slug") or data.get("title") or body.keyword),
        "title": str(data.get("title") or body.keyword)[:150],
        "meta_title": str(data.get("meta_title") or "")[:70],
        "meta_description": str(data.get("meta_description") or "")[:180],
        "category": str(data.get("category") or "Guide d'achat")[:60],
        "excerpt": str(data.get("excerpt") or "")[:220],
        "read_minutes": int(data.get("read_minutes") or 5),
        "body": str(data.get("body") or ""),
        "author": f"L'équipe {site.get('name')}",
        "published_at": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "ai_generated": True,
    }
    # Ensure slug unique
    existing = (site.get("design") or {}).get("blog_posts") or []
    if any(p.get("slug") == post["slug"] for p in existing):
        post["slug"] = f"{post['slug']}-{uuid.uuid4().hex[:4]}"

    await db.sites.update_one({"id": site_id}, {"$push": {"design.blog_posts": post}})

    # Fire IndexNow
    try:
        from routes.indexnow import fire_and_forget_indexnow
        origin = os.environ.get("PUBLIC_ORIGIN") or "https://senior-france.preview.emergentagent.com"
        fire_and_forget_indexnow([f"{origin}/shop/{site_id}/blog/{post['slug']}", f"{origin}/shop/{site_id}/blog"])
    except Exception:
        pass

    return post


# =====================================================================
# Auto-plan : génération complète (pilier + satellites) depuis SEO informational kws
# =====================================================================
class AutoPlanInput(BaseModel):
    country: Optional[str] = "FR"
    max_satellites: int = 3   # 1-5
    override_pillar_keyword: Optional[str] = None


_INFO_RE = re.compile(r"\b(comment|pourquoi|guide|choisir|quand|quoi|est-ce|différence|définition|types|bienfaits|avantages|inconvénients)\b", re.I)
_TRANSAC_RE = re.compile(r"\b(acheter|achat|prix|commander|meilleur|pas cher|promo|avis|test)\b", re.I)


def _pick_informational_keywords(site: dict, country: str, limit: int = 8, exclude_used: set | None = None) -> list:
    """Return up to `limit` informational keywords (highest volume first).
    Falls back to neutral+niche if no informational keyword is available.
    If `exclude_used` is provided, keywords already consumed by prior blog
    posts are skipped (used by the monthly cluster generator)."""
    niche_an = (site.get("design") or {}).get("niche_analysis") or {}
    results = niche_an.get("results") or []
    market = next((r for r in results if r.get("country") == country), None)
    kws = (market or {}).get("keywords") or []
    used = {(k or "").lower().strip() for k in (exclude_used or set())}

    infos, neutrals = [], []
    for k in kws:
        kw = (k.get("keyword") if isinstance(k, dict) else str(k)) or ""
        vol = (k.get("volume_monthly") if isinstance(k, dict) else 0) or 0
        if not kw or kw.lower().strip() in used:
            continue
        if _INFO_RE.search(kw):
            infos.append({"keyword": kw, "volume": vol})
        elif not _TRANSAC_RE.search(kw):
            neutrals.append({"keyword": kw, "volume": vol})

    infos.sort(key=lambda x: -x["volume"])
    neutrals.sort(key=lambda x: -x["volume"])
    pool = infos + neutrals
    # Deduplicate preserving order
    seen, out = set(), []
    for k in pool:
        key = k["keyword"].lower().strip()
        if key in seen:
            continue
        seen.add(key)
        out.append(k)
        if len(out) >= limit:
            break
    return out


def _used_keywords_from_posts(posts: list) -> set:
    """Extract all keywords already consumed by existing blog posts so the
    monthly cluster generator doesn't duplicate topics."""
    used = set()
    for p in posts or []:
        for f in ("pillar_keyword", "satellite_keyword"):
            v = p.get(f)
            if v:
                used.add(str(v).lower().strip())
        for v in (p.get("satellite_keywords") or []):
            if v:
                used.add(str(v).lower().strip())
    return used


def _pillar_prompt(site_name: str, niche: str, pillar_kw: str, satellite_kws: list) -> tuple[str, str]:
    system = (
        "Tu es un rédacteur SEO senior (top 1%) pour le marché français des seniors. "
        "Tu écris des articles PILIERS de référence qui dominent les SERPs Google et sont cités par "
        "ChatGPT/Perplexity. Tu renvoies UNIQUEMENT du JSON valide."
    )
    sat_list = "\n".join(f"- {s}" for s in satellite_kws)
    user = f"""ARTICLE PILIER pour le blog de {site_name} (niche : {niche}).

MOT-CLÉ CIBLE : {pillar_kw}
LONGUEUR : 1400-1800 mots (article de référence approfondi mais concis)
ARTICLES SATELLITES qui pointeront vers ce pilier :
{sat_list}

RÈGLES :
- Ton expert et rassurant, aucun jargon médical lourd.
- E-E-A-T : données chiffrées, normes (LPPR, CE), mention d'ergothérapeutes.
- Structure markdown : H2, H3, listes à puces, **gras** sur faits clés, 1 tableau comparatif sous forme de liste.
- Section "À retenir" en fin d'article + mini-FAQ de 3 questions.
- Meta title 55-60 chars + meta description 140-158 chars.

Retourne EXACTEMENT ce JSON :
{{
  "slug": "slug-kebab-case-court",
  "title": "Titre éditorial 50-70 caractères",
  "meta_title": "Meta titre 55-60 chars",
  "meta_description": "Meta description 140-158 chars",
  "category": "Guide d'achat|Maintien à domicile|Sommeil|Bien-être|Santé",
  "excerpt": "Résumé 2 phrases (max 180 chars)",
  "read_minutes": 7,
  "body": "Article markdown 1400-1800 mots"
}}"""
    return system, user


def _satellite_prompt(site_name: str, niche: str, sat_kw: str, pillar_title: str, pillar_slug: str) -> tuple[str, str]:
    system = (
        "Tu es un rédacteur SEO expert pour le marché senior français. Tu écris des articles satellites "
        "précis et actionnables, qui pointent vers un pilier plus complet. Tu renvoies UNIQUEMENT du JSON valide."
    )
    user = f"""ARTICLE SATELLITE pour le blog de {site_name} (niche : {niche}).

MOT-CLÉ CIBLE : {sat_kw}
LONGUEUR : 700-1000 mots
PILIER À CITER : « {pillar_title} » (slug `{pillar_slug}`)

RÈGLES :
- Ton expert-accessible, zéro jargon.
- Structure markdown : H2 + H3, listes, **gras** sur faits clés.
- Inclus 1 phrase exacte qui renvoie au pilier :
  *➜ Pour aller plus loin, découvrez notre guide complet : [{pillar_title}](/blog/{pillar_slug})*
- Mini-FAQ de 2 questions en fin d'article.
- Meta title 55-60 chars + meta description 140-158 chars.

Retourne EXACTEMENT ce JSON :
{{
  "slug": "slug-kebab-case-court",
  "title": "Titre 50-70 chars",
  "meta_title": "Meta titre 55-60 chars",
  "meta_description": "Meta description 140-158 chars",
  "category": "Guide d'achat|Maintien à domicile|Sommeil|Bien-être|Santé",
  "excerpt": "Résumé 2 phrases (max 180 chars)",
  "read_minutes": 4,
  "body": "Article markdown 700-1000 mots incluant la phrase de renvoi au pilier"
}}"""
    return system, user


def _normalize_post(data: dict, site_name: str, extra: dict | None = None) -> dict:
    post = {
        "id": str(uuid.uuid4()),
        "slug": _slugify(data.get("slug") or data.get("title") or uuid.uuid4().hex[:6]),
        "title": str(data.get("title") or "")[:150],
        "meta_title": str(data.get("meta_title") or "")[:70],
        "meta_description": str(data.get("meta_description") or "")[:180],
        "category": str(data.get("category") or "Guide d'achat")[:60],
        "excerpt": str(data.get("excerpt") or "")[:220],
        "read_minutes": int(data.get("read_minutes") or 5),
        "body": str(data.get("body") or ""),
        "author": f"L'équipe {site_name}",
        "published_at": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "ai_generated": True,
    }
    if extra:
        post.update(extra)
    return post


@router.post("/sites/{site_id}/blog-posts/auto-plan")
async def auto_plan_blog(
    site_id: str,
    body: AutoPlanInput,
    background_tasks: BackgroundTasks,
    user=Depends(get_current_user),
):
    """Plan complet (pilier + N satellites). Lance la génération en arrière-plan
    car Claude + 3 satellites dépasse la limite gateway de 60 s.
    Le client recharge la liste `blog-posts` dans 1-3 min."""
    site = await _ensure_site(site_id)
    if not site:
        raise HTTPException(404, "Site introuvable")

    pool = _pick_informational_keywords(site, body.country or "FR", limit=8)
    if not pool and not body.override_pillar_keyword:
        raise HTTPException(400, "Aucun mot-clé informationnel disponible. Lance d'abord l'étape 8 (SEO) ou fournis un keyword.")

    max_sat = max(1, min(5, int(body.max_satellites or 3)))
    pillar_kw = body.override_pillar_keyword or pool[0]["keyword"]
    satellite_kws = [k["keyword"] for k in pool if k["keyword"] != pillar_kw][:max_sat]
    if not satellite_kws:
        base = site.get("niche") or "produits seniors"
        satellite_kws = [
            f"comment choisir {base}",
            f"avantages {base} pour seniors",
            f"guide entretien {base}",
        ][:max_sat]

    job_id = str(uuid.uuid4())
    await db.blog_jobs.insert_one({
        "id": job_id,
        "site_id": site_id,
        "status": "pending",
        "pillar_keyword": pillar_kw,
        "satellite_keywords": satellite_kws,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    background_tasks.add_task(
        _run_auto_plan_job,
        site_id=site_id,
        job_id=job_id,
        site_name=site.get("name") or "",
        niche=site.get("niche") or "",
        pillar_kw=pillar_kw,
        satellite_kws=satellite_kws,
    )

    return {
        "status": "started",
        "job_id": job_id,
        "pillar_keyword": pillar_kw,
        "satellite_keywords": satellite_kws,
        "expected_count": 1 + len(satellite_kws),
        "message": f"Génération lancée ({1 + len(satellite_kws)} articles) — recharge la liste dans 60 à 120 secondes.",
    }


async def _run_auto_plan_job(
    site_id: str,
    job_id: str,
    site_name: str,
    niche: str,
    pillar_kw: str,
    satellite_kws: list,
):
    """Background worker — génère pilier + satellites et persiste."""
    try:
        await db.blog_jobs.update_one({"id": job_id}, {"$set": {"status": "running"}})

        pillar_system, pillar_user = _pillar_prompt(site_name, niche, pillar_kw, satellite_kws)
        pillar_data = await _call_claude_json(pillar_system, pillar_user, timeout=180)
        if not pillar_data:
            await db.blog_jobs.update_one({"id": job_id}, {"$set": {
                "status": "failed", "error": "IA indisponible ou budget épuisé (pilier).",
                "finished_at": datetime.now(timezone.utc).isoformat(),
            }})
            return

        site = await db.sites.find_one({"id": site_id}, {"_id": 0, "design.blog_posts": 1})
        existing = ((site or {}).get("design") or {}).get("blog_posts") or []
        taken_slugs = {p.get("slug") for p in existing}

        pillar = _normalize_post(pillar_data, site_name, extra={
            "type": "pillar",
            "pillar_keyword": pillar_kw,
            "satellite_keywords": satellite_kws,
        })
        while pillar["slug"] in taken_slugs:
            pillar["slug"] = f"{pillar['slug']}-{uuid.uuid4().hex[:4]}"
        taken_slugs.add(pillar["slug"])

        async def _gen_sat(sat_kw: str):
            sys_p, usr_p = _satellite_prompt(site_name, niche, sat_kw, pillar["title"], pillar["slug"])
            return sat_kw, await _call_claude_json(sys_p, usr_p, timeout=150)

        results = await asyncio.gather(*[_gen_sat(k) for k in satellite_kws], return_exceptions=True)
        satellites = []
        for item in results:
            if isinstance(item, Exception) or not item:
                continue
            sat_kw, sat_data = item
            if not sat_data or not isinstance(sat_data, dict):
                continue
            sat = _normalize_post(sat_data, site_name, extra={
                "type": "satellite",
                "pillar_slug": pillar["slug"],
                "satellite_keyword": sat_kw,
            })
            while sat["slug"] in taken_slugs:
                sat["slug"] = f"{sat['slug']}-{uuid.uuid4().hex[:4]}"
            taken_slugs.add(sat["slug"])
            satellites.append(sat)

        if satellites:
            sats_md = "\n\n## Explorez aussi nos guides détaillés\n\n"
            for s in satellites:
                sats_md += f"- [{s['title']}](/blog/{s['slug']}) — {s.get('excerpt', '')}\n"
            pillar["body"] = (pillar.get("body") or "") + sats_md

        all_posts = [pillar] + satellites
        await db.sites.update_one(
            {"id": site_id},
            {"$push": {"design.blog_posts": {"$each": all_posts}}},
        )

        try:
            from routes.indexnow import fire_and_forget_indexnow
            origin = os.environ.get("PUBLIC_ORIGIN") or "https://senior-france.preview.emergentagent.com"
            urls = [f"{origin}/shop/{site_id}/blog"] + [f"{origin}/shop/{site_id}/blog/{p['slug']}" for p in all_posts]
            fire_and_forget_indexnow(urls)
        except Exception:
            pass

        await db.blog_jobs.update_one({"id": job_id}, {"$set": {
            "status": "done",
            "pillar_slug": pillar["slug"],
            "pillar_title": pillar["title"],
            "satellites_count": len(satellites),
            "total_generated": len(all_posts),
            "finished_at": datetime.now(timezone.utc).isoformat(),
        }})
    except Exception as e:
        logger.exception("auto_plan background job crashed")
        await db.blog_jobs.update_one({"id": job_id}, {"$set": {
            "status": "failed", "error": str(e)[:300],
            "finished_at": datetime.now(timezone.utc).isoformat(),
        }})


@router.get("/sites/{site_id}/blog-posts/auto-plan/{job_id}")
async def auto_plan_status(site_id: str, job_id: str, user=Depends(get_current_user)):
    job = await db.blog_jobs.find_one({"id": job_id, "site_id": site_id}, {"_id": 0})
    if not job:
        raise HTTPException(404, "Job introuvable")
    return job


# =====================================================================
# Cluster mensuel — 1 pilier + 4 satellites, déclenché manuellement
# et/ou programmé chaque 1er du mois via APScheduler.
# =====================================================================
class ClusterMonthlyInput(BaseModel):
    country: Optional[str] = "FR"
    satellites: int = 4  # 3-5


class ClusterSettingsInput(BaseModel):
    auto_enabled: bool
    country: Optional[str] = "FR"
    satellites: Optional[int] = 4


async def _launch_cluster_job(
    site: dict,
    country: str,
    satellites_count: int,
    triggered_by: str,
) -> dict:
    """Common helper pour cluster-monthly (manuel ou schedulé).
    Retourne {job_id, pillar_kw, satellite_kws, ...} ou lève une erreur métier."""
    site_id = site["id"]
    posts = ((site.get("design") or {}).get("blog_posts")) or []
    used = _used_keywords_from_posts(posts)
    pool = _pick_informational_keywords(site, country, limit=12, exclude_used=used)

    if not pool:
        # Fallback synthetic based on niche if keyword pool exhausted
        niche = site.get("niche") or "produits seniors"
        synthetic = [
            f"comment choisir {niche}", f"avantages {niche}",
            f"guide entretien {niche}", f"prix moyen {niche} 2026",
            f"meilleurs {niche} pour seniors",
        ]
        pool = [{"keyword": k, "volume": 0} for k in synthetic if k.lower() not in used]

    if not pool:
        raise ValueError("Plus de mots-clés disponibles : tous ont été consommés par les articles existants. Relance l'étape 8 (SEO) pour régénérer.")

    max_sat = max(3, min(5, int(satellites_count or 4)))
    pillar_kw = pool[0]["keyword"]
    satellite_kws = [k["keyword"] for k in pool[1:max_sat + 1]]
    if len(satellite_kws) < max_sat:
        niche = site.get("niche") or "produits seniors"
        extras = [
            f"astuces {niche}",
            f"questions fréquentes sur {niche}",
            f"checklist {niche}",
        ]
        for e in extras:
            if len(satellite_kws) >= max_sat:
                break
            if e.lower().strip() not in used and e not in satellite_kws:
                satellite_kws.append(e)

    job_id = str(uuid.uuid4())
    await db.blog_jobs.insert_one({
        "id": job_id,
        "site_id": site_id,
        "kind": "cluster_monthly",
        "triggered_by": triggered_by,  # "manual" | "schedule"
        "status": "pending",
        "pillar_keyword": pillar_kw,
        "satellite_keywords": satellite_kws,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    # Kick off generation asynchronously (don't await the long LLM work)
    asyncio.create_task(_run_auto_plan_job(
        site_id=site_id,
        job_id=job_id,
        site_name=site.get("name") or "",
        niche=site.get("niche") or "",
        pillar_kw=pillar_kw,
        satellite_kws=satellite_kws,
    ))

    return {
        "job_id": job_id,
        "pillar_keyword": pillar_kw,
        "satellite_keywords": satellite_kws,
        "expected_count": 1 + len(satellite_kws),
    }


@router.post("/sites/{site_id}/blog-posts/cluster-monthly")
async def cluster_monthly(
    site_id: str,
    body: ClusterMonthlyInput,
    user=Depends(get_current_user),
):
    """Déclenchement manuel d'un cluster mensuel (1 pilier + N satellites).
    Évite les keywords déjà utilisés par les articles existants."""
    site = await _ensure_site(site_id)
    if not site:
        raise HTTPException(404, "Site introuvable")
    try:
        result = await _launch_cluster_job(
            site=site,
            country=body.country or "FR",
            satellites_count=body.satellites or 4,
            triggered_by="manual",
        )
    except ValueError as e:
        raise HTTPException(400, str(e))

    # Persist last_manual run on site for UI feedback
    await db.sites.update_one(
        {"id": site_id},
        {"$set": {
            "design.blog_cluster.last_manual_run_at": datetime.now(timezone.utc).isoformat(),
            "design.blog_cluster.last_manual_job_id": result["job_id"],
        }},
    )

    return {
        "status": "started",
        "message": f"Cluster mensuel lancé ({result['expected_count']} articles) — la liste se met à jour dans 1-2 min.",
        **result,
    }


@router.post("/sites/{site_id}/blog-posts/cluster-settings")
async def cluster_settings(
    site_id: str,
    body: ClusterSettingsInput,
    user=Depends(get_current_user),
):
    """Active/désactive la génération automatique mensuelle du cluster SEO."""
    site = await _ensure_site(site_id)
    if not site:
        raise HTTPException(404, "Site introuvable")

    update = {
        "design.blog_cluster.auto_enabled": bool(body.auto_enabled),
        "design.blog_cluster.country": body.country or "FR",
        "design.blog_cluster.satellites": max(3, min(5, int(body.satellites or 4))),
        "design.blog_cluster.updated_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.sites.update_one({"id": site_id}, {"$set": update})
    return {"ok": True, **{k.split(".")[-1]: v for k, v in update.items()}}


@router.get("/sites/{site_id}/blog-posts/cluster-status")
async def cluster_status(site_id: str, user=Depends(get_current_user)):
    """Infos UI : dernier run, prochaine date prévue, settings actuels."""
    site = await _ensure_site(site_id)
    if not site:
        raise HTTPException(404, "Site introuvable")

    bc = ((site.get("design") or {}).get("blog_cluster")) or {}
    now = datetime.now(timezone.utc)
    # Next 1st of next month at 06:00 UTC
    if now.month == 12:
        next_run = now.replace(year=now.year + 1, month=1, day=1, hour=6, minute=0, second=0, microsecond=0)
    else:
        next_run = now.replace(month=now.month + 1, day=1, hour=6, minute=0, second=0, microsecond=0)

    # Latest 5 cluster jobs
    recent = await db.blog_jobs.find(
        {"site_id": site_id, "kind": "cluster_monthly"}, {"_id": 0}
    ).sort("created_at", -1).limit(5).to_list(5)

    return {
        "auto_enabled": bool(bc.get("auto_enabled")),
        "country": bc.get("country") or "FR",
        "satellites": bc.get("satellites") or 4,
        "last_manual_run_at": bc.get("last_manual_run_at"),
        "last_scheduled_run_at": bc.get("last_scheduled_run_at"),
        "next_scheduled_at": next_run.isoformat() if bc.get("auto_enabled") else None,
        "recent_jobs": recent,
    }


async def run_monthly_clusters_for_all_sites() -> dict:
    """APScheduler entry-point — 1er de chaque mois à 06:00 UTC.
    Itère tous les sites avec `design.blog_cluster.auto_enabled == True`
    et déclenche un cluster en background pour chacun."""
    try:
        cursor = db.sites.find(
            {"design.blog_cluster.auto_enabled": True},
            {"_id": 0, "id": 1, "name": 1, "niche": 1, "design.blog_cluster": 1, "design.blog_posts": 1, "design.niche_analysis": 1},
        )
        launched, skipped = 0, 0
        async for site in cursor:
            bc = ((site.get("design") or {}).get("blog_cluster")) or {}
            try:
                await _launch_cluster_job(
                    site=site,
                    country=bc.get("country") or "FR",
                    satellites_count=bc.get("satellites") or 4,
                    triggered_by="schedule",
                )
                await db.sites.update_one(
                    {"id": site["id"]},
                    {"$set": {"design.blog_cluster.last_scheduled_run_at": datetime.now(timezone.utc).isoformat()}},
                )
                launched += 1
            except Exception:
                logger.exception(f"[cluster-monthly] site {site.get('id')} skipped")
                skipped += 1
        logger.info(f"[cluster-monthly] launched={launched} skipped={skipped}")
        return {"launched": launched, "skipped": skipped}
    except Exception:
        logger.exception("[cluster-monthly] scheduler run failed")
        return {"launched": 0, "skipped": 0, "error": True}
