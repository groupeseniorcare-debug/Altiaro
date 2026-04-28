"""Worker async qui consomme `db.blog_jobs` (Phase A2). Appelé toutes
les 30 s via APScheduler ; max 3 jobs concurrents globalement."""
from __future__ import annotations
import asyncio
import logging
from datetime import datetime, timezone
from deps import db
from services.llm_resilience import safe_claude_json

logger = logging.getLogger("altiaro.blog_worker")
MAX_CONCURRENT = 3
_running: set = set()
_lock = asyncio.Lock()


async def _generate_article(site: dict, brief: str, language: str) -> dict | None:
    """Génère 1 article via Haiku (rapide + budget-friendly)."""
    try:
        prompt = (
            f"Tu rédiges un article de blog premium SEO pour la marque {site.get('name','')} "
            f"({site.get('niche','')}). Brief : {brief}. "
            f"Langue : {language}. "
            f"Format JSON: {{title, slug, excerpt, body_html (1200+ mots, h2/h3, listes), "
            f"meta_title, meta_description, tags (array), pillar}}."
        )
        out = await safe_claude_json(
            system="Tu es éditeur SEO expert e-commerce premium. Réponds en JSON strict.",
            user=prompt, quality_tier="speed", request_id=f"blog-{site['id'][:8]}", timeout=120,
        )
        if not isinstance(out, dict) or not out.get("title"):
            return None
        return out
    except Exception as e:
        logger.warning(f"[blog-worker] gen article failed: {str(e)[:120]}")
        return None


async def _process_job(job: dict):
    job_id = job["id"]
    site_id = job["site_id"]
    site = await db.sites.find_one({"id": site_id})
    if not site:
        await db.blog_jobs.update_one({"id": job_id}, {"$set": {"status": "failed", "error": "site missing", "completed_at": datetime.now(timezone.utc).isoformat()}})
        return
    language = job.get("language") or site.get("primary_lang") or "fr"
    count = int(job.get("articles_planned") or 1)
    topics = job.get("topics") or []
    pillar = job.get("pillar") or "buying_guide"
    # Topics auto-générés si manquants
    if len(topics) < count:
        try:
            seed = (
                f"Site: {site.get('name','')} — niche: {site.get('niche','')}. "
                f"Génère {count - len(topics)} sujets d'articles SEO long-tail uniques, intent='{pillar}', "
                f"langue={language}. Format JSON: {{topics: [...]}}"
            )
            seed_out = await safe_claude_json(
                system="Stratège SEO expert. JSON strict.",
                user=seed, quality_tier="speed", request_id=f"blog-seed-{site_id[:8]}", timeout=60,
            )
            if isinstance(seed_out, dict):
                topics = topics + (seed_out.get("topics") or [])
        except Exception:
            pass
    topics = topics[:count] if topics else [f"Article {i+1}" for i in range(count)]

    await db.blog_jobs.update_one({"id": job_id}, {"$set": {"status": "running", "started_at": datetime.now(timezone.utc).isoformat()}})
    done = 0
    for i, brief in enumerate(topics):
        art = await _generate_article(site, brief, language)
        if art:
            from uuid import uuid4
            doc = {
                "id": str(uuid4()),
                "site_id": site_id,
                "title": {language: art.get("title", brief)},
                "slug": art.get("slug") or brief.lower().replace(" ", "-")[:60],
                "excerpt": {language: art.get("excerpt", "")},
                "body": {language: art.get("body_html", "")},
                "meta_title": {language: art.get("meta_title", "")},
                "meta_description": {language: art.get("meta_description", "")},
                "tags": art.get("tags", []),
                "pillar": art.get("pillar") or pillar,
                "language": language,
                "status": "published",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            await db.blog_posts.insert_one(doc)
            done += 1
            await db.blog_jobs.update_one({"id": job_id}, {"$set": {"articles_done": done, "progress": int((done / max(count, 1)) * 100)}})
        else:
            logger.info(f"[blog-worker] skip article {i+1}/{count} (LLM degraded)")
    final_status = "completed" if done > 0 else "failed"
    await db.blog_jobs.update_one(
        {"id": job_id},
        {"$set": {"status": final_status, "articles_done": done, "progress": 100 if done == count else int((done / max(count, 1)) * 100), "completed_at": datetime.now(timezone.utc).isoformat(), "error": None if done > 0 else "all_articles_failed"}},
    )
    logger.info(f"[blog-worker] job {job_id[:8]} → {final_status} ({done}/{count})")


async def tick():
    """Worker tick : lance jusqu'à MAX_CONCURRENT jobs queued."""
    async with _lock:
        if len(_running) >= MAX_CONCURRENT:
            return
        free = MAX_CONCURRENT - len(_running)
        # Pick queued jobs (1 par site, ordre FIFO)
        seen_sites: set = set()
        candidates: list = []
        async for j in db.blog_jobs.find({"status": "queued"}, {"_id": 0}).sort([("created_at", 1)]).limit(20):
            if j["site_id"] in seen_sites:
                continue
            seen_sites.add(j["site_id"])
            candidates.append(j)
            if len(candidates) >= free:
                break
        for j in candidates:
            _running.add(j["id"])
            asyncio.create_task(_run_and_release(j))


async def _run_and_release(job: dict):
    try:
        await _process_job(job)
    finally:
        _running.discard(job["id"])
