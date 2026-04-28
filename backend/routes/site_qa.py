"""Phase C — Endpoints QA + Go Live."""
from __future__ import annotations
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from deps import db, get_current_user
from services.site_qa_checklist import compute

router = APIRouter(tags=["site-qa"])
logger = logging.getLogger("altiaro.site_qa")


async def _check(site_id: str, user: dict):
    s = await db.sites.find_one({"id": site_id}, {"_id": 0, "operator_id": 1, "id": 1, "name": 1, "status": 1})
    if not s:
        raise HTTPException(404, "Site introuvable")
    if user.get("role") != "admin" and s.get("operator_id") != user.get("id"):
        raise HTTPException(403, "Accès interdit")
    return s


@router.get("/sites/{site_id}/qa/checklist")
async def qa_checklist(site_id: str, user: dict = Depends(get_current_user)):
    await _check(site_id, user)
    return await compute(site_id)


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
        from routes.indexnow import push_urls_for_site  # type: ignore
        await push_urls_for_site(site_id)
    except Exception:
        logger.exception("[go-live] indexnow push failed (non-blocking)")
    try:
        from routes.emails import send_email  # type: ignore
        await send_email(
            to=site.get("operator_email") or "",
            subject=f"🚀 {site.get('name','Site')} est en ligne",
            html=f"<p>Votre site <strong>{site.get('name')}</strong> est désormais public. Bonnes ventes ✨</p>",
        )
    except Exception:
        pass
    logger.info(f"[go-live] site {site_id[:8]} → status=live")
    await db.sites.update_one({"id": site_id}, {"$set": {"last_indexnow_at": now}})
    return {"ok": True, "site_id": site_id, "status": "live", "went_live_at": now, "checklist": cl}
