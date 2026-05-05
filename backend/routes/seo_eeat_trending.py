"""TÂCHE 3.6 + 3.7 — Endpoints admin pour E-E-A-T refresh + trending topics."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from deps import get_current_user

router = APIRouter()


def _require_admin(user: dict):
    if not user or user.get("role") != "admin":
        raise HTTPException(403, "Admin required")


@router.post("/admin/sites/{site_id}/seo/eeat-refresh",
              tags=["seo-eeat"])
async def admin_eeat_refresh(
    site_id: str,
    age_days_threshold: int = 60,
    limit: int = 50,
    concurrency: int = 2,
    dry_run: bool = False,
    user: dict = Depends(get_current_user),
):
    """Sprint 5 TÂCHE 3.6 — Refresh E-E-A-T des articles >age_days_threshold."""
    _require_admin(user)
    from services.eeat_refresh import refresh_old_blog_posts
    return await refresh_old_blog_posts(
        site_id, age_days_threshold=age_days_threshold,
        limit=limit, concurrency=concurrency, dry_run=dry_run,
    )


@router.post("/admin/sites/{site_id}/seo/trending-articles",
              tags=["seo-trending"])
async def admin_trending_articles(
    site_id: str,
    max_articles: int = 3,
    user: dict = Depends(get_current_user),
):
    """Sprint 5 TÂCHE 3.7 — Génère articles timely sur trending topics."""
    _require_admin(user)
    from services.trending_topics import generate_trending_articles_for_site
    return await generate_trending_articles_for_site(
        site_id, max_articles=max_articles,
    )
