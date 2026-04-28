"""Phase A2 — File d'attente blog asynchrone.

Plus jamais d'appel HTTP synchrone bloquant : on enqueue un job dans
`db.blog_jobs`, un worker APScheduler le consomme toutes les 30 s.
"""
from __future__ import annotations
import asyncio, logging, uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from deps import db, get_current_user

router = APIRouter(tags=["blog-queue"])
logger = logging.getLogger("altiaro.blog_queue")

MAX_GLOBAL_RUNNING = 3
_LOCKS: dict = {}


class EnqueueInput(BaseModel):
    count: int = Field(1, ge=1, le=50)
    topics: Optional[List[str]] = None
    language: Optional[str] = None
    pillar: Optional[str] = None  # "buying_guide" | "comparison" | "trends"


async def _check_owner(site_id: str, user: dict):
    site = await db.sites.find_one({"id": site_id}, {"_id": 0, "operator_id": 1, "id": 1})
    if not site:
        raise HTTPException(404, "Site introuvable")
    if user.get("role") != "admin" and site.get("operator_id") != user.get("id"):
        raise HTTPException(403, "Accès interdit")
    return site


@router.post("/sites/{site_id}/blog/jobs")
async def enqueue_blog_job(site_id: str, data: EnqueueInput, user: dict = Depends(get_current_user)):
    await _check_owner(site_id, user)
    job = {
        "id": str(uuid.uuid4()),
        "site_id": site_id,
        "status": "queued",
        "progress": 0,
        "articles_planned": data.count,
        "articles_done": 0,
        "briefs": [],
        "topics": data.topics or [],
        "language": data.language,
        "pillar": data.pillar,
        "retries": 0,
        "max_retries": 3,
        "requested_by": user.get("id"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "started_at": None,
        "completed_at": None,
        "error": None,
    }
    await db.blog_jobs.insert_one(job)
    job.pop("_id", None)
    logger.info(f"[blog-queue] enqueued job {job['id'][:8]} site={site_id[:8]} count={data.count}")
    return {"ok": True, "job": job}


@router.get("/sites/{site_id}/blog/jobs")
async def list_blog_jobs(
    site_id: str,
    status: Optional[str] = Query(None, description="Comma-separated: queued,running,completed,failed,cancelled"),
    user: dict = Depends(get_current_user),
):
    await _check_owner(site_id, user)
    q = {"site_id": site_id}
    if status:
        q["status"] = {"$in": [s.strip() for s in status.split(",") if s.strip()]}
    items = await db.blog_jobs.find(q, {"_id": 0}).sort([("created_at", -1)]).limit(200).to_list(length=200)
    return {"items": items, "total": len(items)}


@router.get("/sites/{site_id}/blog/jobs/{job_id}")
async def get_blog_job(site_id: str, job_id: str, user: dict = Depends(get_current_user)):
    await _check_owner(site_id, user)
    job = await db.blog_jobs.find_one({"id": job_id, "site_id": site_id}, {"_id": 0})
    if not job:
        raise HTTPException(404, "Job introuvable")
    return job


@router.delete("/sites/{site_id}/blog/jobs/{job_id}")
async def cancel_blog_job(site_id: str, job_id: str, user: dict = Depends(get_current_user)):
    await _check_owner(site_id, user)
    job = await db.blog_jobs.find_one({"id": job_id, "site_id": site_id})
    if not job:
        raise HTTPException(404, "Job introuvable")
    if job.get("status") != "queued":
        raise HTTPException(400, f"Statut '{job.get('status')}' non annulable")
    await db.blog_jobs.update_one({"id": job_id}, {"$set": {"status": "cancelled", "completed_at": datetime.now(timezone.utc).isoformat()}})
    return {"ok": True}
