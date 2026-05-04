"""Google Search Console provisioning automatique.

Quand un site a `custom_domain_verified=true` :
  1. POST /webmasters/v3/sites/sc-domain:{domain}  (Domain property)
  2. PUT  /webmasters/v3/sites/{site_url}/sitemaps/{feedpath}
  3. Persiste `site.gsc_property_created=true` + `gsc_sitemap_submitted_at`.

Endpoints :
  POST /api/admin/sites/{id}/gsc/provision
  GET  /api/admin/sites/{id}/gsc/status
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict
from urllib.parse import quote

from deps import db

logger = logging.getLogger("altiaro.gsc_provisioning")


async def _build_gsc_service():
    from services.gmc_onboarding import _resolve_master_credentials
    creds = await _resolve_master_credentials()
    if not creds:
        return None
    try:
        from googleapiclient.discovery import build
        return build("webmasters", "v3", credentials=creds, cache_discovery=False)
    except Exception as e:
        logger.warning(f"[gsc] sdk init failed: {str(e)[:200]}")
        return None


async def _persist_health(ok: bool, reason: str = "", extra: dict | None = None):
    now = datetime.now(timezone.utc).isoformat()
    await db.platform_health.update_one(
        {"key": "gsc"},
        {"$set": {"last_check_at": now, "ok": ok, "reason": reason, **(extra or {})}},
        upsert=True,
    )


async def provision_for_site(site_id: str) -> Dict[str, Any]:
    out: Dict[str, Any] = {"site_id": site_id, "started_at": datetime.now(timezone.utc).isoformat()}
    site = await db.sites.find_one(
        {"id": site_id},
        {"_id": 0, "id": 1, "custom_domain": 1, "custom_domain_verified": 1,
         "gsc_property_created": 1, "gsc_sitemap_submitted_at": 1},
    )
    if not site:
        return {**out, "ok": False, "reason": "site_not_found"}
    domain = site.get("custom_domain")
    if not domain or not site.get("custom_domain_verified"):
        return {**out, "ok": False, "reason": "domain_not_verified"}

    svc = await _build_gsc_service()
    if not svc:
        await _persist_health(False, "no_credentials")
        return {**out, "ok": False, "reason": "no_credentials"}

    site_url = f"sc-domain:{domain}"  # Domain property — covers www + apex
    out["site_url"] = site_url

    # 1) Add the property (idempotent : Google ignore if already exists)
    try:
        await asyncio.to_thread(svc.sites().add(siteUrl=site_url).execute)
        out["property"] = {"ok": True, "action": "added_or_existing"}
    except Exception as e:
        msg = str(e)
        # 409 "already exists" -> not really an error
        if "already" in msg.lower() or "409" in msg:
            out["property"] = {"ok": True, "action": "already_exists"}
        else:
            await _persist_health(False, "add_property_failed", {"error": msg[:300]})
            return {**out, "ok": False, "reason": "add_property_failed", "error": msg[:300]}

    # 2) Submit sitemap
    feedpath = f"https://{domain}/sitemap.xml"
    try:
        await asyncio.to_thread(
            svc.sitemaps().submit(siteUrl=site_url, feedpath=feedpath).execute,
        )
        out["sitemap"] = {"ok": True, "feedpath": feedpath}
    except Exception as e:
        out["sitemap"] = {"ok": False, "error": str(e)[:300]}

    now = datetime.now(timezone.utc).isoformat()
    await db.sites.update_one(
        {"id": site_id},
        {"$set": {
            "gsc_property_created": True,
            "gsc_property_url": site_url,
            "gsc_sitemap_submitted_at": now if out["sitemap"].get("ok") else None,
        }},
    )
    await _persist_health(True, "", {"last_site": site_id, "last_property": site_url})
    out["ok"] = True
    out["completed_at"] = now
    return out


async def list_properties() -> Dict[str, Any]:
    """Liste les properties accessibles par le master OAuth (debug)."""
    svc = await _build_gsc_service()
    if not svc:
        return {"ok": False, "reason": "no_credentials"}
    try:
        resp = await asyncio.to_thread(svc.sites().list().execute)
        return {"ok": True, "items": resp.get("siteEntry", [])}
    except Exception as e:
        return {"ok": False, "error": str(e)[:300]}
