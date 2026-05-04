"""Phase 3.2 chantier C+D — wordmark on-demand + liste upsells publique.

Endpoints :
* POST /api/sites/{id}/brand/wordmark/regenerate — régénère le wordmark
  typographique (Pillow, aucun LLM, ~50 ms) et update `design.brand.
  logo_wordmark_url`. Retourne l'URL du fichier.
* GET  /api/public/sites/{id}/upsells?limit=12 — tous les upsells actifs du
  site (pour la section « Accessoires & compléments » de la home).
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from deps import db, get_current_user
from services.wordmark_generator import persist_wordmark_for_site

router = APIRouter(tags=["brand-wordmark"])
logger = logging.getLogger("altiaro.brand_wordmark")


async def _owner_check(site_id: str, user: dict) -> dict:
    site = await db.sites.find_one({"id": site_id})
    if not site:
        raise HTTPException(404, "Site introuvable")
    if user.get("role") != "admin" and site.get("operator_id") != user.get("id"):
        raise HTTPException(403, "Accès interdit")
    return site


@router.post("/sites/{site_id}/brand/wordmark/regenerate")
async def regenerate_wordmark(site_id: str,
                               brand_name: Optional[str] = Query(None,
                                    description="Si vide, utilise design.brand.name du site."),
                               user: dict = Depends(get_current_user)):
    site = await _owner_check(site_id, user)
    design = site.get("design") or {}
    brand = design.get("brand") or {}
    name = (brand_name or brand.get("name") or site.get("name") or "Maison").strip()
    palette = {
        "primary_color": brand.get("primary_color"),
        "accent_color": brand.get("accent_color"),
        "background_color": brand.get("background_color"),
    }
    res = await persist_wordmark_for_site(site_id, name, palette)
    return {"ok": True, **res}


# ---- Public: all upsells for a site (no auth) ----
@router.get("/public/sites/{site_id}/upsells")
async def public_site_upsells(site_id: str, limit: int = 12):
    """Liste tous les upsells actifs du site (pour section home/catalog).

    Le tri par défaut met en avant `featured=true` puis les plus récents.
    Idempotent, no-auth, cache-friendly.
    """
    site = await db.sites.find_one({"id": site_id}, {"_id": 0, "id": 1})
    if not site:
        raise HTTPException(404, "Site introuvable")
    items = await db.products.find(
        {"site_id": site_id, "status": "active", "role": "upsell"},
        {"_id": 0},
    ).sort([("featured", -1), ("created_at", -1)]).limit(max(1, min(limit, 24))).to_list(24)
    return items


# ---- Public: blog posts (Phase 3.3) ----
@router.get("/public/sites/{site_id}/blog-posts")
async def public_site_blog_posts(site_id: str, lang: str = "fr", limit: int = 60):
    """Liste publique des articles de blog du site, filtrés par langue.

    Expose la collection `db.blog_posts` au storefront (Phase 3.3, Magic
    Content). Les champs lourds (body_md, body_html) sont omis de l'index —
    utiliser `GET /public/sites/{id}/blog-posts/{slug}` pour le détail.
    """
    site = await db.sites.find_one({"id": site_id}, {"_id": 0, "id": 1})
    if not site:
        raise HTTPException(404, "Site introuvable")
    items = await db.blog_posts.find(
        {"site_id": site_id, "lang": lang, "status": "published"},
        {"_id": 0, "body_md": 0, "body_html": 0},
    ).sort([("published_at", -1)]).limit(max(1, min(limit, 100))).to_list(100)
    return items


@router.get("/public/sites/{site_id}/blog-posts/{slug}")
async def public_site_blog_post_detail(site_id: str, slug: str, lang: str = "fr"):
    """Article de blog complet par slug + langue."""
    post = await db.blog_posts.find_one(
        {"site_id": site_id, "slug": slug, "lang": lang, "status": "published"},
        {"_id": 0},
    )
    if not post:
        # fallback : tolère la langue absente (ancien format)
        post = await db.blog_posts.find_one(
            {"site_id": site_id, "slug": slug, "status": "published"},
            {"_id": 0},
        )
    if not post:
        raise HTTPException(404, "Article introuvable")
    return post
