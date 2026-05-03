"""Admin endpoints for GMC auto-onboarding (Tâche 1)."""
from __future__ import annotations

import logging
from fastapi import APIRouter, Depends, HTTPException

from deps import db, get_current_user
from services.gmc_onboarding import auto_onboard

router = APIRouter(tags=["merchant-onboarding"])
logger = logging.getLogger("altiaro.gmc_onboard_route")


async def _check(site_id: str, user: dict):
    s = await db.sites.find_one({"id": site_id}, {"_id": 0, "id": 1, "operator_id": 1})
    if not s:
        raise HTTPException(404, "Site introuvable")
    if user.get("role") != "admin" and s.get("operator_id") != user.get("id"):
        raise HTTPException(403, "Accès interdit")
    return s


@router.post("/admin/sites/{site_id}/merchant/auto-onboard")
async def admin_auto_onboard(site_id: str, force: bool = False,
                             user: dict = Depends(get_current_user)):
    """Push tous les champs GMC pre-fillables en une passe.

    Renvoie le payload poussé + la liste des actions manuelles restantes
    (KBIS, téléphone SMS, email click) avec liens directs vers Merchants UI.
    """
    await _check(site_id, user)
    return await auto_onboard(site_id, force=force)


@router.post("/sites/{site_id}/merchant/auto-onboard")
async def operator_auto_onboard(site_id: str,
                                user: dict = Depends(get_current_user)):
    """Variante opérateur — même logique, restreinte au propriétaire."""
    await _check(site_id, user)
    return await auto_onboard(site_id, force=False)
