"""TÂCHE 3.1 — Endpoints programmatic SEO (Sprint 5 SEO).

Endpoints :
    POST /api/admin/sites/{site_id}/seo/programmatic/generate
        ?max_per_product=30 & dry_run=false
    GET  /api/admin/sites/{site_id}/seo/programmatic/stats
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from deps import db, get_current_user

router = APIRouter()


def _require_admin(user: dict):
    if not user or user.get("role") != "admin":
        raise HTTPException(403, "Admin required")


@router.post("/admin/sites/{site_id}/seo/programmatic/generate",
              tags=["seo-programmatic"])
async def admin_programmatic_generate(
    site_id: str,
    max_per_product: int = 30,
    concurrency: int = 4,
    dry_run: bool = False,
    skip_if_exists: bool = True,
    user: dict = Depends(get_current_user),
):
    """Génère des landing pages programmatic (produit × intent × segment)."""
    _require_admin(user)
    from services.programmatic_seo import generate_programmatic_landings_for_site
    return await generate_programmatic_landings_for_site(
        site_id,
        max_per_product=max_per_product,
        concurrency=concurrency,
        skip_if_exists=skip_if_exists,
        dry_run=dry_run,
    )


@router.get("/admin/sites/{site_id}/seo/programmatic/stats",
             tags=["seo-programmatic"])
async def admin_programmatic_stats(
    site_id: str,
    user: dict = Depends(get_current_user),
):
    _require_admin(user)
    longtail_count = await db.landing_pages.count_documents(
        {"site_id": site_id, "kind": "longtail"}
    )
    prog_count = await db.landing_pages.count_documents(
        {"site_id": site_id, "kind": "longtail", "source": "programmatic_seo_v1"}
    )
    return {
        "site_id": site_id,
        "landings_longtail_total": longtail_count,
        "landings_programmatic_v1": prog_count,
    }
