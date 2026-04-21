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

from fastapi import APIRouter, HTTPException, Depends
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
    except Exception:
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
