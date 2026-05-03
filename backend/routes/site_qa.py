"""Phase C — Endpoints QA + Go Live."""
from __future__ import annotations
import logging
import asyncio
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from deps import db, get_current_user
from services.site_qa_checklist import compute

router = APIRouter(tags=["site-qa"])
logger = logging.getLogger("altiaro.site_qa")


async def _check(site_id: str, user: dict):
    s = await db.sites.find_one({"id": site_id}, {"_id": 0, "operator_id": 1, "id": 1, "name": 1, "status": 1, "merchant": 1})
    if not s:
        raise HTTPException(404, "Site introuvable")
    if user.get("role") != "admin" and s.get("operator_id") != user.get("id"):
        raise HTTPException(403, "Accès interdit")
    return s


async def _maybe_auto_onboard_gmc(site: dict) -> None:
    """Auto-trigger GMC onboarding if not already done. Idempotent.

    Lazy + non-blocking : if it fails (no MCA, no creds), QA still proceeds
    with `merchant_connected=warn` instead of erroring out.
    """
    merchant = site.get("merchant") or {}
    if merchant.get("business_info_pushed"):
        return
    try:
        from services.gmc_onboarding import auto_onboard
        # Fire & forget — the QA UI will reflect the result on next refresh.
        asyncio.create_task(auto_onboard(site["id"], force=False))
        logger.info(f"[qa] GMC auto-onboard triggered for site {site['id'][:8]}")
    except Exception:
        logger.exception("[qa] gmc auto-onboard scheduling failed (non-blocking)")


@router.get("/sites/{site_id}/qa/checklist")
async def qa_checklist(site_id: str, user: dict = Depends(get_current_user)):
    site = await _check(site_id, user)
    # Auto-trigger GMC onboarding the first time the operator opens Step 10.
    await _maybe_auto_onboard_gmc(site)
    cl = await compute(site_id)
    # Surface the manual GMC steps so the UI can render them inline.
    merchant = site.get("merchant") or {}
    cl["gmc_manual_steps"] = merchant.get("manual_steps_required") or []
    cl["gmc_sub_account_id"] = merchant.get("sub_account_id") or None
    return cl


@router.post("/sites/{site_id}/go-live")
async def go_live(site_id: str, force: bool = Query(False), user: dict = Depends(get_current_user)):
    site = await _check(site_id, user)
    cl = await compute(site_id)
    if not cl.get("ready") and not (force and user.get("role") == "admin"):
        raise HTTPException(400, f"Site non prêt (score {cl.get('score')}/100). Utilisez force=true admin pour outrepasser.")
    now = datetime.now(timezone.utc).isoformat()
    await db.sites.update_one({"id": site_id}, {"$set": {"status": "live", "went_live_at": now, "updated_at": now}})
    await db.site_snapshots.insert_one({
        "id": f"snap-go-live-{site_id[:8]}-{int(datetime.now(timezone.utc).timestamp())}",
        "site_id": site_id, "kind": "go_live", "created_at": now,
    })
    # IndexNow + sitemap ping (best-effort)
    try:
        from routes.indexnow import notify_indexnow
        public_url = site.get("public_url") or site.get("custom_domain")
        if public_url and not public_url.startswith("http"):
            public_url = f"https://{public_url}"
        if public_url:
            await notify_indexnow([public_url, f"{public_url}/sitemap.xml"])
    except Exception:
        logger.exception("[go-live] indexnow push failed (non-blocking)")
    try:
        from routes.emails import send_email_via_resend
        op = await db.users.find_one({"id": site.get("operator_id")}, {"_id": 0, "email": 1})
        to = (op or {}).get("email") or ""
        if to:
            await send_email_via_resend(
                to=to,
                subject=f"🚀 {site.get('name','Site')} est en ligne",
                html=f"<p>Votre site <strong>{site.get('name')}</strong> est désormais public. Bonnes ventes ✨</p>",
                site=site,
                tags=["go_live"],
            )
    except Exception:
        logger.exception("[go-live] email failed (non-blocking)")
    logger.info(f"[go-live] site {site_id[:8]} → status=live")
    await db.sites.update_one({"id": site_id}, {"$set": {"last_indexnow_at": now}})
    return {"ok": True, "site_id": site_id, "status": "live", "went_live_at": now, "checklist": cl}
