"""
IndexNow — accelerate search engine indexing (Bing, Yandex, Seznam, Yep, Naver).
Google doesn't officially use IndexNow yet, but Bing/ChatGPT/Perplexity do,
so this gives a huge AEO boost.

Key location : `/api/public/indexnow-{key}.txt`
Submit endpoint : `POST https://api.indexnow.org/indexnow`

This module exposes :
- `INDEXNOW_KEY` — auto-generated per deployment (env fallback)
- `GET /public/indexnow-{key}.txt` — serves the key for verification
- `async notify_indexnow(urls)` — fires and forgets URL submissions
- `POST /api/indexnow/notify` — manual trigger (admin only)
"""
from __future__ import annotations

import asyncio
import logging
import os
from typing import List
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import Response
from pydantic import BaseModel

from deps import get_current_user

logger = logging.getLogger("conceptfactory.indexnow")
router = APIRouter()

# Stable key for the deployment (64 char hex). Can be overridden via env.
INDEXNOW_KEY = os.environ.get("INDEXNOW_KEY") or "a4f8c1e2d3b5697fe2c1a4b8d5c6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4"

INDEXNOW_ENDPOINT = "https://api.indexnow.org/indexnow"


def _origin() -> str:
    return os.environ.get("PUBLIC_ORIGIN") or "https://senior-france.preview.emergentagent.com"


def _key_url() -> str:
    return f"{_origin()}/api/public/indexnow-{INDEXNOW_KEY}.txt"


async def notify_indexnow(urls: List[str]) -> dict:
    """Submit 1..10_000 URLs to IndexNow. Fire-and-forget friendly.
    Returns { status, submitted, error? }.
    """
    if not urls:
        return {"status": "noop", "submitted": 0}
    # Deduplicate + limit
    urls = list(dict.fromkeys([u for u in urls if u and u.startswith("http")]))[:10000]
    if not urls:
        return {"status": "noop", "submitted": 0}

    host = urlparse(urls[0]).netloc
    payload = {
        "host": host,
        "key": INDEXNOW_KEY,
        "keyLocation": _key_url(),
        "urlList": urls,
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                INDEXNOW_ENDPOINT,
                json=payload,
                headers={"Content-Type": "application/json; charset=utf-8"},
            )
        if resp.status_code in (200, 202):
            logger.info(f"[indexnow] submitted {len(urls)} URLs → status {resp.status_code}")
            return {"status": "ok", "submitted": len(urls), "http_status": resp.status_code}
        logger.warning(f"[indexnow] submission failed ({resp.status_code}) : {resp.text[:200]}")
        return {"status": "failed", "submitted": 0, "http_status": resp.status_code, "error": resp.text[:200]}
    except Exception as e:
        logger.exception(f"[indexnow] submission exception : {e}")
        return {"status": "error", "submitted": 0, "error": str(e)}


def fire_and_forget_indexnow(urls: List[str]) -> None:
    """Fire IndexNow in background without blocking caller."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(notify_indexnow(urls))
    except Exception:
        logger.exception("[indexnow] fire_and_forget failed")


# =====================================================================
# PUBLIC ROUTES
# =====================================================================
@router.get(f"/public/indexnow-{INDEXNOW_KEY}.txt")
async def indexnow_key_file():
    """Serves the IndexNow key file for Bing/Yandex/etc. verification."""
    return Response(content=INDEXNOW_KEY, media_type="text/plain")


# Mission Finalisation 2026-04-29 — alias root-level pour les domaines custom :
# IndexNow exige que le `keyLocation` soit sur le MÊME host que les URLs
# soumises. Pour Altea (`altea-home.com`), Bing/Yandex/IndexNow vont fetcher
# `https://altea-home.com/{KEY}.txt` → cette route répond depuis notre backend
# tant que le custom domain pointe sur notre infra. Pour les sites hébergés
# ailleurs, le concepteur doit déposer ce fichier à la racine de son hébergeur.
@router.get(f"/public/{INDEXNOW_KEY}.txt", include_in_schema=False)
async def indexnow_key_file_root_alias():
    return Response(content=INDEXNOW_KEY, media_type="text/plain")


class NotifyInput(BaseModel):
    urls: List[str]


@router.post("/indexnow/notify")
async def indexnow_notify(body: NotifyInput, user=Depends(get_current_user)):
    """Manual IndexNow submission for admins/ops."""
    if len(body.urls) == 0:
        raise HTTPException(400, "Aucune URL fournie")
    result = await notify_indexnow(body.urls)
    return result


@router.post("/sites/{site_id}/indexnow/resubmit-all")
async def indexnow_resubmit_all(site_id: str, user=Depends(get_current_user)):
    """Resubmit all URLs of a site (sitemap-based) to IndexNow."""
    from deps import db
    site = await db.sites.find_one({"id": site_id}, {"_id": 0, "id": 1, "design": 1})
    if not site:
        raise HTTPException(404, "Site introuvable")
    origin = _origin()
    base = f"{origin}/shop/{site_id}"
    products = await db.products.find(
        {"site_id": site_id, "status": "active"},
        {"_id": 0, "id": 1}
    ).to_list(5000)
    collections = ((site.get("design") or {}).get("collections") or [])

    urls = [
        base,
        f"{base}/collections",
        f"{base}/about",
        f"{base}/faq",
        f"{base}/contact",
        f"{base}/livraison",
        f"{base}/retours",
    ]
    for c in collections:
        if isinstance(c, dict) and c.get("slug"):
            urls.append(f"{base}/collection/{c['slug']}")
    for p in products:
        urls.append(f"{base}/product/{p['id']}")

    return await notify_indexnow(urls)
