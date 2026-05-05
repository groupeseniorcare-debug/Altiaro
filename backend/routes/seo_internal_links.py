"""TÂCHE 3.3 — Endpoints internal linking dense (Sprint 5 SEO).

Endpoints :
    POST /api/admin/sites/{site_id}/seo/internal-links/rebuild
        → Recalcule le maillage Product↔Blog↔Landing pour ce site
    GET  /api/admin/sites/{site_id}/seo/internal-links/stats
        → Stats : count of products with related_blog_posts, blogs with related_products
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from deps import db, get_current_user

router = APIRouter()


def _require_admin(user: dict):
    if not user or user.get("role") != "admin":
        raise HTTPException(403, "Admin required")


@router.post("/admin/sites/{site_id}/seo/internal-links/rebuild",
              tags=["seo-internal-links"])
async def admin_rebuild_internal_links(
    site_id: str,
    lang: str = "fr",
    user: dict = Depends(get_current_user),
):
    """Recalcule le maillage Product ↔ Blog ↔ Landing avec scoring Jaccard."""
    _require_admin(user)
    from services.internal_links_dense import rebuild_internal_links
    return await rebuild_internal_links(site_id, lang=lang)


@router.get("/admin/sites/{site_id}/seo/internal-links/stats",
             tags=["seo-internal-links"])
async def admin_internal_links_stats(
    site_id: str,
    user: dict = Depends(get_current_user),
):
    _require_admin(user)
    p_with = await db.products.count_documents(
        {"site_id": site_id, "related_blog_posts": {"$exists": True, "$ne": []}}
    )
    p_total = await db.products.count_documents({"site_id": site_id, "status": "active"})
    b_with = await db.blog_posts.count_documents(
        {"site_id": site_id, "related_products": {"$exists": True, "$ne": []}}
    )
    b_total = await db.blog_posts.count_documents({"site_id": site_id})
    return {
        "products_with_related_blog": p_with,
        "products_total": p_total,
        "blogs_with_related_products": b_with,
        "blogs_total": b_total,
        "coverage_products_pct": round(100 * p_with / max(1, p_total), 1),
        "coverage_blogs_pct": round(100 * b_with / max(1, b_total), 1),
    }
