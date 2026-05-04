"""GMC onboarding admin endpoints — status + relance + domain verify."""
from __future__ import annotations

import logging
from fastapi import APIRouter, Depends, HTTPException

from deps import db, get_current_user

router = APIRouter(tags=["merchant-onboarding-status"])
logger = logging.getLogger("altiaro.gmc_status")


async def _check(site_id: str, user: dict):
    s = await db.sites.find_one({"id": site_id}, {"_id": 0, "id": 1, "operator_id": 1, "merchant": 1, "custom_domain": 1, "custom_domain_verified": 1, "gmc_domain_verified": 1, "design": 1, "name": 1})
    if not s:
        raise HTTPException(404, "Site introuvable")
    if user.get("role") != "admin" and s.get("operator_id") != user.get("id"):
        raise HTTPException(403, "Accès interdit")
    return s


@router.get("/admin/sites/{site_id}/merchant/onboarding-status")
async def gmc_onboarding_status(site_id: str, user: dict = Depends(get_current_user)):
    """Renvoie un check-list booléen par champ GMC (debug visuel pour UI)."""
    site = await _check(site_id, user)
    merchant = site.get("merchant") or {}
    sub_id = merchant.get("sub_account_id")
    feed_url = merchant.get("feed_url")
    domain = site.get("custom_domain") or ""

    checks = {
        "sub_account_created": bool(sub_id),
        "business_info_pushed": bool(merchant.get("business_info_pushed")),
        "shipping_settings_pushed": bool(merchant.get("shipping_settings_ok")),
        "tax_settings_pushed": bool(merchant.get("tax_ok")),
        "return_policy_pushed": bool(merchant.get("return_policy_ok")),
        "feed_url_set": bool(feed_url),
        "domain_attached": bool(domain and site.get("custom_domain_verified")),
        "google_domain_verified": bool(site.get("gmc_domain_verified")),
        "manual_steps_required": merchant.get("manual_steps_required") or [],
    }
    all_green = all(
        v for k, v in checks.items()
        if k != "manual_steps_required"
    )
    return {
        "site_id": site_id,
        "merchant_id": sub_id,
        "mca_id": merchant.get("mca_id"),
        "feed_url": feed_url,
        "checks": checks,
        "all_green": all_green,
        "last_onboarding_at": merchant.get("last_onboarding_at"),
    }


@router.post("/admin/sites/{site_id}/merchant/verify-domain")
async def verify_domain_endpoint(site_id: str, user: dict = Depends(get_current_user)):
    """Lance la vérification automatique du domaine via OVH TXT + Google API."""
    await _check(site_id, user)
    from services.gmc_domain_verify import verify_domain_for_site
    return await verify_domain_for_site(site_id)
