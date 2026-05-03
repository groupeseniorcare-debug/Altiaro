"""Admin endpoint : approbation d'un site pour le push Google Ads.

Ne peut passer que si :
  1. `qa.ready=true` (= score >= 70 + aucun fail dont domain_configured)
  2. `site.custom_domain` est set ET `custom_domain_verified=true`

Sinon → HTTP 409 avec message explicite (le concepteur doit retourner à
l'étape 6 ou compléter les checks rouges étape 10).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException

from deps import db, get_current_user
from services.site_qa_checklist import compute

router = APIRouter(tags=["admin-approve-ads"])
logger = logging.getLogger("altiaro.admin_approve_ads")


def _require_admin(user: dict):
    if user.get("role") != "admin":
        raise HTTPException(403, "Admin only")


@router.post("/admin/sites/{site_id}/approve-for-ads")
async def approve_for_ads(site_id: str, user: dict = Depends(get_current_user)):
    _require_admin(user)
    site = await db.sites.find_one(
        {"id": site_id},
        {"_id": 0, "id": 1, "name": 1, "custom_domain": 1,
         "custom_domain_verified": 1, "domain_skipped": 1, "status": 1},
    )
    if not site:
        raise HTTPException(404, "Site introuvable")

    if not site.get("custom_domain") or not site.get("custom_domain_verified"):
        raise HTTPException(
            status_code=409,
            detail={
                "error": "domain_required_for_ads",
                "message": (
                    "Impossible de pousser ce site vers Google Ads : un domaine "
                    "personnalisé vérifié est requis. "
                    + ("L'étape 6 a été skippée — elle doit être reprise."
                       if site.get("domain_skipped")
                       else "Aucun domaine custom n'est configuré.")
                ),
                "redirect_step": "domain",
            },
        )

    cl = await compute(site_id)
    if not cl.get("ready"):
        failed = [c for c in cl.get("checks", []) if c.get("status") == "fail"]
        raise HTTPException(
            status_code=409,
            detail={
                "error": "qa_not_ready",
                "message": (
                    f"Site non prêt (score {cl.get('score')}/100). "
                    f"{len(failed)} check(s) en échec — corrige-les puis recommence."
                ),
                "failed_checks": [
                    {"id": c["id"], "label": c["label"], "detail": c["detail"]}
                    for c in failed
                ],
                "redirect_step": "qa",
            },
        )

    now = datetime.now(timezone.utc).isoformat()
    await db.sites.update_one(
        {"id": site_id},
        {"$set": {
            "ads_approved": True,
            "ads_approved_at": now,
            "ads_approved_by": user.get("email"),
        }},
    )
    logger.info(f"[approve-ads] site={site_id[:8]} approved by {user.get('email')}")
    return {
        "ok": True,
        "site_id": site_id,
        "approved_at": now,
        "domain": site.get("custom_domain"),
        "qa_score": cl.get("score"),
    }
