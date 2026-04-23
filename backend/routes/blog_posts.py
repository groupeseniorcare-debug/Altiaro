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


class AIDraftInput(BaseModel):
    keyword: str
    angle: Optional[str] = ""    # ex: "guide d'achat", "tendance", "FAQ approfondie"
    length: Optional[str] = "long"  # short | medium | long


def _ensure_site(site_id: str):
    return db.sites.find_one({"id": site_id}, {"_id": 0})


@router.get("/sites/{site_id}/blog-posts")
async def list_blog_posts(site_id: str, user=Depends(get_current_user)):
    site = await _ensure_site(site_id)
    if not site:
        raise HTTPException(404, "Site introuvable")
    posts = (site.get("design") or {}).get("blog_posts") or []
    return posts


@router.post("/sites/{site_id}/blog-posts")
async def create_blog_post(site_id: str, body: BlogPostInput, user=Depends(get_current_user)):
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
    return post


@router.patch("/sites/{site_id}/blog-posts/{slug}")
async def update_blog_post(site_id: str, slug: str, body: BlogPostInput, user=Depends(get_current_user)):
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
    found.update(updates)
    await db.sites.update_one({"id": site_id}, {"$set": {"design.blog_posts": posts}})
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


async def _call_claude_json(system: str, user: str, timeout: int = 120):
    if not EMERGENT_LLM_KEY:
        return None
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        chat = (
            LlmChat(
                api_key=EMERGENT_LLM_KEY,
                session_id=f"blog-{uuid.uuid4().hex[:8]}",
                system_message=system,
            )
            .with_model("anthropic", "claude-sonnet-4-5-20250929")
        )
        raw = await asyncio.wait_for(chat.send_message(UserMessage(text=user)), timeout=timeout)
        text = raw if isinstance(raw, str) else str(raw)
        return json.loads(_strip_json_fence(text))
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
        logger.exception("Blog Claude call failed")
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


def _pick_informational_keywords(site: dict, country: str, limit: int = 8) -> list:
    """Return up to `limit` informational keywords (highest volume first).
    Falls back to neutral+niche if no informational keyword is available."""
    niche_an = (site.get("design") or {}).get("niche_analysis") or {}
    results = niche_an.get("results") or []
    market = next((r for r in results if r.get("country") == country), None)
    kws = (market or {}).get("keywords") or []

    infos, neutrals = [], []
    for k in kws:
        kw = (k.get("keyword") if isinstance(k, dict) else str(k)) or ""
        vol = (k.get("volume_monthly") if isinstance(k, dict) else 0) or 0
        if not kw:
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


def _pillar_prompt(site_name: str, niche: str, pillar_kw: str, satellite_kws: list) -> tuple[str, str]:
    system = (
        "Tu es un rédacteur SEO senior (top 1%) pour le marché français des seniors. "
        "Tu écris des articles PILIERS de référence qui dominent les SERPs Google et sont cités par "
        "ChatGPT/Perplexity. Tu renvoies UNIQUEMENT du JSON valide."
    )
    sat_list = "\n".join(f"- {s}" for s in satellite_kws)
    user = f"""ARTICLE PILIER pour le blog de {site_name} (niche : {niche}).

MOT-CLÉ CIBLE : {pillar_kw}
LONGUEUR : 2200-2800 mots (article de référence, très approfondi)
ARTICLES SATELLITES qui pointeront vers ce pilier :
{sat_list}

RÈGLES :
- Ton expert et rassurant, aucun jargon médical lourd.
- E-E-A-T maximum : données chiffrées, normes (LPPR, CE), mention d'ergothérapeutes.
- Structure markdown riche : H2, H3, listes à puces, **gras** sur faits clés, au moins 1 tableau comparatif sous forme de liste.
- Section "À retenir" en fin d'article + mini-FAQ de 4 questions.
- Dans le corps, inclus 3 à 5 "ancres internes" du style [voir notre guide : SUJET] sur des sujets proches. Liste ces ancres dans `internal_anchors`.
- Meta title 55-60 chars + meta description 140-158 chars.

Retourne EXACTEMENT ce JSON :
{{
  "slug": "slug-kebab-case-court",
  "title": "Titre éditorial 50-70 caractères",
  "meta_title": "Meta titre 55-60 chars",
  "meta_description": "Meta description 140-158 chars",
  "category": "Guide d'achat|Maintien à domicile|Sommeil|Bien-être|Santé",
  "excerpt": "Résumé 2 phrases (max 180 chars)",
  "read_minutes": 9,
  "body": "Article markdown complet — 2200 à 2800 mots",
  "internal_anchors": ["ancre 1", "ancre 2", "ancre 3"]
}}"""
    return system, user


def _satellite_prompt(site_name: str, niche: str, sat_kw: str, pillar_title: str, pillar_slug: str) -> tuple[str, str]:
    system = (
        "Tu es un rédacteur SEO expert pour le marché senior français. Tu écris des articles satellites "
        "précis et actionnables, qui pointent vers un pilier plus complet. Tu renvoies UNIQUEMENT du JSON valide."
    )
    user = f"""ARTICLE SATELLITE pour le blog de {site_name} (niche : {niche}).

MOT-CLÉ CIBLE : {sat_kw}
LONGUEUR : 900-1300 mots
PILIER À CITER : « {pillar_title} » (slug `{pillar_slug}`)

RÈGLES :
- Ton expert-accessible, zéro jargon.
- Structure markdown : H2 + H3, listes, **gras** sur faits clés.
- Tu dois OBLIGATOIREMENT inclure 1 phrase qui renvoie au pilier, sous cette forme exacte :
  *➜ Pour aller plus loin, découvrez notre guide complet : [{pillar_title}](/blog/{pillar_slug})*
- Mini-FAQ de 3 questions en fin d'article.
- Meta title 55-60 chars + meta description 140-158 chars.

Retourne EXACTEMENT ce JSON :
{{
  "slug": "slug-kebab-case-court",
  "title": "Titre 50-70 chars",
  "meta_title": "Meta titre 55-60 chars",
  "meta_description": "Meta description 140-158 chars",
  "category": "Guide d'achat|Maintien à domicile|Sommeil|Bien-être|Santé",
  "excerpt": "Résumé 2 phrases (max 180 chars)",
  "read_minutes": 5,
  "body": "Article markdown 900-1300 mots incluant la phrase de renvoi au pilier"
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
