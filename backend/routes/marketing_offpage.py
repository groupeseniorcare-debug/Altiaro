"""Marketing Off-Page — Pinterest, Annuaires, HARO/PressOutreach.

Endpoints groupes :
  /api/sites/{id}/marketing/pinterest/connect
  /api/sites/{id}/marketing/pinterest/auto-publish
  /api/sites/{id}/marketing/pinterest/status
  /api/sites/{id}/marketing/directories/auto-submit
  /api/sites/{id}/marketing/directories/status
  /api/sites/{id}/marketing/haro/activate
  /api/sites/{id}/marketing/haro/status
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from deps import db, get_current_user
from services import directory_submitter
from services import pinterest_publisher

router = APIRouter(tags=["marketing-offpage"])
logger = logging.getLogger("altiaro.marketing")


async def _check(site_id: str, user: dict):
    s = await db.sites.find_one({"id": site_id}, {"_id": 0, "id": 1, "operator_id": 1, "name": 1, "niche": 1, "custom_domain": 1, "marketing": 1})
    if not s:
        raise HTTPException(404, "Site introuvable")
    if user.get("role") != "admin" and s.get("operator_id") != user.get("id"):
        raise HTTPException(403, "Accès interdit")
    return s


# ────────────────────────────────────────────────────────────────
# DIRECTORIES (annuaires Silver Economy)
# ────────────────────────────────────────────────────────────────
@router.post("/sites/{site_id}/marketing/directories/auto-submit")
async def directories_auto_submit(site_id: str, user: dict = Depends(get_current_user)):
    """Lance les submissions vers les 20 annuaires en parallele (sem=3)."""
    await _check(site_id, user)
    return await directory_submitter.auto_submit_all(site_id)


@router.get("/sites/{site_id}/marketing/directories/status")
async def directories_status(site_id: str, user: dict = Depends(get_current_user)):
    await _check(site_id, user)
    return await directory_submitter.get_status(site_id)


# ────────────────────────────────────────────────────────────────
# PINTEREST (stub activable — OAuth complet en sprint dédié)
# ────────────────────────────────────────────────────────────────
class PinterestActivate(BaseModel):
    enabled: bool = True


@router.get("/sites/{site_id}/marketing/pinterest/status")
async def pinterest_status(site_id: str, user: dict = Depends(get_current_user)):
    site = await _check(site_id, user)
    pl = await db.platform_settings.find_one({"key": "pinterest"}) or {}
    site_pin = (site.get("marketing") or {}).get("pinterest") or {}
    creds_set = bool(os.environ.get("PINTEREST_APP_ID") and os.environ.get("PINTEREST_APP_SECRET"))
    return {
        "site_id": site_id,
        "app_credentials_configured": creds_set,
        "platform_oauth_connected": bool(pl.get("connected")),
        "site_auto_publish": bool(site_pin.get("auto_pin")),
        "board_id": site_pin.get("board_id"),
        "pins_published": site_pin.get("pins_published", 0),
        "last_pin_at": site_pin.get("last_pin_at"),
        "note": (
            "OAuth Pinterest non implementé (stub). Active le toggle pour "
            "persister la préférence ; les pins seront publiés dès que les "
            "vars PINTEREST_APP_ID/APP_SECRET seront set ET que l'OAuth sera "
            "complété dans un futur sprint."
        ) if not creds_set else None,
    }


@router.post("/sites/{site_id}/marketing/pinterest/connect")
async def pinterest_connect(site_id: str, user: dict = Depends(get_current_user)):
    await _check(site_id, user)
    if not (os.environ.get("PINTEREST_APP_ID") and os.environ.get("PINTEREST_APP_SECRET")):
        raise HTTPException(
            424,  # Failed Dependency
            detail={
                "error": "missing_pinterest_credentials",
                "message": "PINTEREST_APP_ID/SECRET non configurés. Voir backend/services/pinterest_publisher.py",
            },
        )
    return {"ok": False, "reason": "oauth_flow_not_implemented", "see": "services/pinterest_publisher.py"}


@router.post("/sites/{site_id}/marketing/pinterest/auto-publish")
async def pinterest_auto_publish(site_id: str, body: PinterestActivate,
                                  user: dict = Depends(get_current_user)):
    await _check(site_id, user)
    now = datetime.now(timezone.utc).isoformat()
    await db.sites.update_one(
        {"id": site_id},
        {"$set": {
            "marketing.pinterest.auto_pin": body.enabled,
            "marketing.pinterest.toggled_at": now,
            "marketing.pinterest.toggled_by": user.get("email"),
        }},
    )
    return {"ok": True, "auto_pin": body.enabled}


# ────────────────────────────────────────────────────────────────
# HARO / Press Outreach (stub activable — source RSS à brancher en sprint dédié)
# ────────────────────────────────────────────────────────────────
class HARoActivate(BaseModel):
    enabled: bool = True
    keywords: list[str] | None = None


@router.post("/sites/{site_id}/marketing/haro/activate")
async def haro_activate(site_id: str, body: HARoActivate, user: dict = Depends(get_current_user)):
    site = await _check(site_id, user)
    keywords = body.keywords or [site.get("niche", "")]
    now = datetime.now(timezone.utc).isoformat()
    await db.sites.update_one(
        {"id": site_id},
        {"$set": {
            "marketing.haro.enabled": body.enabled,
            "marketing.haro.keywords": keywords,
            "marketing.haro.activated_at": now,
        }},
    )
    return {
        "ok": True, "enabled": body.enabled, "keywords": keywords,
        "note": "Worker HARO/PressOutreach non encore wiré (HARO fermé en 2024 — "
                "l'équivalent moderne est Connectively/Featured.com). Préférence persistée.",
    }


@router.get("/sites/{site_id}/marketing/haro/status")
async def haro_status(site_id: str, user: dict = Depends(get_current_user)):
    site = await _check(site_id, user)
    haro = (site.get("marketing") or {}).get("haro") or {}
    responses_n = await db.haro_responses.count_documents({"site_id": site_id})
    return {
        "site_id": site_id,
        "enabled": bool(haro.get("enabled")),
        "keywords": haro.get("keywords") or [],
        "responses_sent": responses_n,
        "backlinks_captured": (haro.get("backlinks_captured") or 0),
        "activated_at": haro.get("activated_at"),
    }
