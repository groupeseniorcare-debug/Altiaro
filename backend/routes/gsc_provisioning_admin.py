"""GSC admin endpoints (provision + status + list)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from deps import db, get_current_user
from services.gsc_provisioning import provision_for_site, list_properties

router = APIRouter(tags=["gsc-provisioning"])


def _require_admin(user: dict):
    if user.get("role") != "admin":
        raise HTTPException(403, "Admin only")


@router.post("/admin/sites/{site_id}/gsc/provision")
async def gsc_provision(site_id: str, user: dict = Depends(get_current_user)):
    _require_admin(user)
    return await provision_for_site(site_id)


@router.get("/admin/sites/{site_id}/gsc/status")
async def gsc_status(site_id: str, user: dict = Depends(get_current_user)):
    _require_admin(user)
    site = await db.sites.find_one(
        {"id": site_id},
        {"_id": 0, "id": 1, "custom_domain": 1, "custom_domain_verified": 1,
         "gsc_property_created": 1, "gsc_property_url": 1, "gsc_sitemap_submitted_at": 1},
    )
    if not site:
        raise HTTPException(404, "Site introuvable")
    health = await db.platform_health.find_one({"key": "gsc"}, {"_id": 0}) or {}
    return {"site": site, "health": health}


@router.get("/admin/integrations/gsc/list-properties")
async def gsc_list(user: dict = Depends(get_current_user)):
    _require_admin(user)
    return await list_properties()
