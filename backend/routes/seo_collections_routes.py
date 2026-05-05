"""TÂCHE 3.4 — Endpoint admin pour enrichir les collections SEO."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from deps import db, get_current_user

router = APIRouter()


def _require_admin(user: dict):
    if not user or user.get("role") != "admin":
        raise HTTPException(403, "Admin required")


@router.post("/admin/sites/{site_id}/seo/collections/enrich",
              tags=["seo-collections"])
async def admin_collections_enrich(
    site_id: str,
    generate_derived: bool = True,
    concurrency: int = 2,
    user: dict = Depends(get_current_user),
):
    _require_admin(user)
    from services.seo_collections import enrich_collections_seo
    return await enrich_collections_seo(
        site_id, generate_derived=generate_derived, concurrency=concurrency,
    )


@router.get("/admin/sites/{site_id}/seo/collections/stats",
             tags=["seo-collections"])
async def admin_collections_stats(
    site_id: str,
    user: dict = Depends(get_current_user),
):
    _require_admin(user)
    total = await db.collections.count_documents({"site_id": site_id})
    with_seo = await db.collections.count_documents(
        {"site_id": site_id, "seo_content": {"$exists": True}}
    )
    derived = await db.collections.count_documents(
        {"site_id": site_id, "source": "seo_derived_v1"}
    )
    return {
        "total_collections": total,
        "with_seo_content": with_seo,
        "derived_segmented": derived,
    }
