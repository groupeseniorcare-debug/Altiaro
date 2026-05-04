"""Sprint 3.5 — Machine d'état pour les soumissions annuaires.

Réécrit `directory_submissions` en machine d'état explicite :
    queued → submitting → pending_review → live | failed

Chaque transition écrit un événement dans `directory_submission_events`
avec timestamp. Un cron follow-up check toutes les 48 h les pending_review
et tente de valider (fetch de l'annuaire à la recherche du backlink).
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import httpx

from deps import db

logger = logging.getLogger("altiaro.directory_fsm")

STATES = ("queued", "submitting", "pending_review", "live", "failed")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def transition(submission_id: str, new_state: str,
                     *, note: Optional[str] = None,
                     detail: Optional[Dict[str, Any]] = None) -> None:
    if new_state not in STATES:
        raise ValueError(f"Invalid state {new_state}")
    prev = await db.directory_submissions.find_one({"id": submission_id},
                                                     {"_id": 0, "state": 1})
    await db.directory_submissions.update_one(
        {"id": submission_id},
        {"$set": {"state": new_state, "updated_at": _now_iso(),
                   "last_note": note, "last_detail": detail}},
    )
    await db.directory_submission_events.insert_one({
        "id": str(uuid.uuid4()),
        "submission_id": submission_id,
        "from_state": (prev or {}).get("state"),
        "to_state": new_state,
        "note": note,
        "detail": detail,
        "created_at": _now_iso(),
    })


async def follow_up_pending_reviews() -> Dict[str, Any]:
    """Cron : for every submission in `pending_review`, fetch the directory
    and look for a backlink to the site domain. Transition to `live` if found,
    otherwise keep pending."""
    docs = await db.directory_submissions.find(
        {"state": "pending_review"}
    ).to_list(500)
    if not docs:
        return {"ok": True, "checked": 0}
    validated = 0
    for sub in docs:
        site_domain = sub.get("site_domain") or ""
        listing_url = sub.get("listing_url") or sub.get("directory_url") or ""
        if not (site_domain and listing_url):
            continue
        try:
            async with httpx.AsyncClient(timeout=15, follow_redirects=True) as cli:
                r = await cli.get(listing_url,
                                   headers={"User-Agent": "Altiaro-DirectoryCheck/1.0"})
            if r.status_code == 200 and site_domain in (r.text or ""):
                await transition(sub["id"], "live", note="backlink_detected",
                                  detail={"http_status": 200})
                validated += 1
        except Exception as e:
            logger.warning(f"[directory_fsm] followup {sub.get('id')} failed: {e}")
    return {"ok": True, "checked": len(docs), "validated": validated}
