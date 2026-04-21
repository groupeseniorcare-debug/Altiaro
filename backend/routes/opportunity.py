"""Sprint 21 — Alertes "Nouvelle Opportunité" (Admin only).

Cron hebdo (lundi matin UTC) : re-scanne les top-10 mots-clés transactionnels
de chaque analyse archivée. Si le volume mensuel a grimpé de +30% (ou plus)
vs la valeur stockée, une alerte est créée dans db.opportunity_alerts pour
que l'Admin puisse la voir dans son Dashboard.

Requiert : au moins 1 Admin connecté à Google Ads (sinon skip).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from deps import db, get_current_user

logger = logging.getLogger("conceptfactory.opportunity")
router = APIRouter()

SPIKE_THRESHOLD_PCT = 30.0  # +30% → alert
MIN_VOLUME_FOR_ALERT = 500   # ignore les micro-niches


def _require_admin(user: dict):
    if user.get("role") != "admin":
        raise HTTPException(403, "Alertes opportunités réservées aux Admins.")


async def scan_opportunities() -> dict:
    """Scan toutes les analyses avec google_keyword_planner, refresh les volumes
    via Google Ads, et crée une alerte si spike détecté.
    """
    from routes.google_ads import fetch_keyword_volumes

    results = {
        "scanned": 0,
        "new_alerts": 0,
        "errors": 0,
        "skipped_no_google": 0,
        "started_at": datetime.now(timezone.utc).isoformat(),
    }

    analyses = await db.niche_analyses.find(
        {},
        {"_id": 0, "id": 1, "product_input": 1, "analysis": 1, "user_id": 1}
    ).sort("created_at", -1).to_list(50)

    for a in analyses:
        results["scanned"] += 1
        aid = a.get("id")
        ax = a.get("analysis") or {}
        countries = ax.get("countries") or []
        if not countries:
            continue
        prev_kp = ax.get("google_keyword_planner") or {}
        prev_by_country = prev_kp.get("by_country") or {}

        # Prepare input for re-fetch
        kw_input = {}
        for c in countries:
            block = (ax.get("keywords_by_country") or {}).get(c) or {}
            merged = (block.get("transactional", []) or [])[:10]
            if merged:
                kw_input[c] = merged
        if not kw_input:
            continue

        try:
            new_data = await fetch_keyword_volumes(kw_input)
        except Exception as e:
            logger.warning(f"[opp-scan] {aid} error: {e}")
            results["errors"] += 1
            continue

        if not new_data.get("available"):
            results["skipped_no_google"] += 1
            continue

        # Diff by country
        for c, new_block in (new_data.get("by_country") or {}).items():
            new_vol = new_block.get("total_volume_monthly", 0)
            if new_vol < MIN_VOLUME_FOR_ALERT:
                continue
            prev_vol = (prev_by_country.get(c) or {}).get("total_volume_monthly") or \
                       (ax.get("country_sizing") or {}).get(c, {}).get("monthly_search_volume") or 0
            prev_vol = int(prev_vol or 0)
            if prev_vol <= 0:
                continue
            change_pct = ((new_vol - prev_vol) / prev_vol) * 100
            if change_pct >= SPIKE_THRESHOLD_PCT:
                # Avoid duplicates on same day
                already = await db.opportunity_alerts.find_one({
                    "analysis_id": aid,
                    "country": c,
                    "detected_at": {
                        "$gte": datetime.now(timezone.utc).strftime("%Y-%m-%d")
                    }
                })
                if already:
                    continue
                top_kws = sorted(new_block.get("keywords", []),
                                 key=lambda x: x["volume"], reverse=True)[:5]
                await db.opportunity_alerts.insert_one({
                    "id": f"opp-{aid[:8]}-{c}-{datetime.now(timezone.utc).strftime('%Y%m%d')}",
                    "analysis_id": aid,
                    "product_input": a.get("product_input"),
                    "country": c,
                    "volume_before": prev_vol,
                    "volume_now": new_vol,
                    "change_pct": round(change_pct, 1),
                    "avg_cpc_eur": new_block.get("avg_cpc_eur", 0),
                    "top_keywords": top_kws,
                    "detected_at": datetime.now(timezone.utc).isoformat(),
                    "acknowledged": False,
                    "user_id": a.get("user_id"),
                })
                results["new_alerts"] += 1
                logger.info(f"[opp] {a.get('product_input')} / {c}: "
                            f"{prev_vol} → {new_vol} ({change_pct:+.1f}%)")

    results["finished_at"] = datetime.now(timezone.utc).isoformat()
    await db.opportunity_scans.insert_one(dict(results))
    logger.info(f"[opp-scan] done: {results}")
    return results


# ====================== ROUTES ====================== #
@router.get("/opportunities/alerts")
async def list_alerts(user: dict = Depends(get_current_user),
                      limit: int = 50, unread_only: bool = False):
    _require_admin(user)
    q = {}
    if unread_only:
        q["acknowledged"] = False
    cursor = db.opportunity_alerts.find(q, {"_id": 0}).sort("detected_at", -1).limit(limit)
    alerts = await cursor.to_list(limit)
    unread = await db.opportunity_alerts.count_documents({"acknowledged": False})
    return {"alerts": alerts, "unread_count": unread}


class AckInput(BaseModel):
    acknowledged: bool = True


@router.post("/opportunities/alerts/{alert_id}/ack")
async def ack_alert(alert_id: str, data: AckInput,
                    user: dict = Depends(get_current_user)):
    _require_admin(user)
    await db.opportunity_alerts.update_one(
        {"id": alert_id},
        {"$set": {"acknowledged": data.acknowledged,
                  "acknowledged_at": datetime.now(timezone.utc).isoformat()
                  if data.acknowledged else None}},
    )
    return {"ok": True}


@router.post("/opportunities/scan-now")
async def run_scan_now(user: dict = Depends(get_current_user)):
    """Déclenche un scan immédiat (utile pour tester + démo)."""
    _require_admin(user)
    result = await scan_opportunities()
    return result


@router.get("/opportunities/scan-history")
async def scan_history(user: dict = Depends(get_current_user), limit: int = 10):
    _require_admin(user)
    cursor = db.opportunity_scans.find({}, {"_id": 0}).sort("started_at", -1).limit(limit)
    return {"history": await cursor.to_list(limit)}
