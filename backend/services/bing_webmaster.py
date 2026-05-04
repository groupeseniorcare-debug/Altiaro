"""Sprint 3.2 — Bing Webmaster Tools API integration.

Bing Webmaster Tools offre une API REST simple qui accepte une **API key**
(pas d'OAuth requis). Endpoint :
    https://www.bing.com/webmaster/api.svc/json/AddSite?apikey={KEY}
    https://www.bing.com/webmaster/api.svc/json/SubmitUrlBatch?apikey={KEY}
    https://www.bing.com/webmaster/api.svc/json/SubmitSitemap?apikey={KEY}

La clé s'obtient sur :
    https://www.bing.com/webmasters/home/mysites  → Settings → API Access

Ce service fournit 3 fonctions :
    - `add_site(site_url)` : enregistre le site auprès de Bing WMT
    - `submit_sitemap(site_url, sitemap_url)` : indique l'URL du sitemap
    - `submit_urls(site_url, urls)` : ping direct d'URLs individuelles
      (quota : 10 000/mois/site ; cf. doc Bing)

Configurer `BING_WEBMASTER_API_KEY` dans `.env` pour activer.
Sans clé : les appels retournent `{"ok": False, "reason": "no_api_key"}`
sans exception (non bloquant pour le launch).
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, List

import httpx

logger = logging.getLogger("altiaro.bing_webmaster")

BING_API_BASE = "https://ssl.bing.com/webmaster/api.svc/json"
# Note : la doc officielle utilise https://www.bing.com, mais les appels avec
# clef API sont aussi servis sur ssl.bing.com (production stable).


def _get_api_key() -> str:
    return (os.environ.get("BING_WEBMASTER_API_KEY") or "").strip()


async def add_site(site_url: str) -> Dict[str, Any]:
    """Register a site in Bing Webmaster Tools. Idempotent (Bing returns
    an error 'site already added' which we treat as success)."""
    api_key = _get_api_key()
    if not api_key:
        return {"ok": False, "reason": "no_api_key",
                "hint": "set BING_WEBMASTER_API_KEY in .env"}
    url = f"{BING_API_BASE}/AddSite?apikey={api_key}"
    payload = {"siteUrl": site_url}
    try:
        async with httpx.AsyncClient(timeout=30) as cli:
            r = await cli.post(url, json=payload)
        if r.status_code == 200:
            return {"ok": True, "site_url": site_url}
        text = r.text[:200] if r.text else ""
        if "already" in text.lower() or "exists" in text.lower():
            return {"ok": True, "site_url": site_url, "note": "already_added"}
        return {"ok": False, "status": r.status_code, "body": text}
    except Exception as e:
        return {"ok": False, "error": str(e)[:160]}


async def submit_sitemap(site_url: str, sitemap_url: str) -> Dict[str, Any]:
    """Submit a sitemap URL to Bing. Idempotent."""
    api_key = _get_api_key()
    if not api_key:
        return {"ok": False, "reason": "no_api_key"}
    url = f"{BING_API_BASE}/SubmitSitemap?apikey={api_key}"
    payload = {"siteUrl": site_url, "feedUrl": sitemap_url}
    try:
        async with httpx.AsyncClient(timeout=30) as cli:
            r = await cli.post(url, json=payload)
        if r.status_code == 200:
            return {"ok": True, "sitemap_url": sitemap_url}
        text = r.text[:200] if r.text else ""
        if "already" in text.lower() or "exists" in text.lower():
            return {"ok": True, "sitemap_url": sitemap_url, "note": "already_submitted"}
        return {"ok": False, "status": r.status_code, "body": text}
    except Exception as e:
        return {"ok": False, "error": str(e)[:160]}


async def submit_urls(site_url: str, urls: List[str]) -> Dict[str, Any]:
    """Submit a batch of URLs for priority crawl (max 500/call)."""
    api_key = _get_api_key()
    if not api_key:
        return {"ok": False, "reason": "no_api_key"}
    if not urls:
        return {"ok": False, "reason": "empty_urls"}
    api_url = f"{BING_API_BASE}/SubmitUrlBatch?apikey={api_key}"
    payload = {"siteUrl": site_url, "urlList": urls[:500]}
    try:
        async with httpx.AsyncClient(timeout=30) as cli:
            r = await cli.post(api_url, json=payload)
        if r.status_code == 200:
            return {"ok": True, "count": len(urls[:500])}
        return {"ok": False, "status": r.status_code, "body": r.text[:200]}
    except Exception as e:
        return {"ok": False, "error": str(e)[:160]}


async def provision_bing_for_site(site: Dict[str, Any]) -> Dict[str, Any]:
    """Full Bing provisioning : AddSite + SubmitSitemap. Idempotent.

    Meant to be called from `launch.py` stage 10.
    """
    domain = site.get("custom_domain") or ""
    if not domain:
        return {"ok": False, "reason": "no_custom_domain"}
    site_url = f"https://{domain}/"
    sitemap_url = f"https://{domain}/sitemap.xml"
    add_res = await add_site(site_url)
    sm_res = await submit_sitemap(site_url, sitemap_url) if add_res.get("ok") else {"skipped": True}
    return {"ok": bool(add_res.get("ok")),
            "add_site": add_res,
            "submit_sitemap": sm_res}
