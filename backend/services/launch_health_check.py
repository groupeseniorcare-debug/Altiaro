"""Sprint 3.4 — Health-check 11-point industriel (requêtes HTTP réelles).

Remplace le health-check partiellement mocké de l'étape 10 du cockpit par
11 vérifications concrètes (HTTP + DB + GSC + GMC + Ads) qui retournent
toutes un `ok` booléen et un `detail`. Le résultat global est stocké sur
`sites.{id}.health_check` avec un `score` 0-11.

Usage :
    from services.launch_health_check import run_health_check
    result = await run_health_check(site_id)
    # result = {"score": 10, "status": "pass", "checks": [...]}
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List

import httpx

from deps import db

logger = logging.getLogger("altiaro.health_check")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _http_check(url: str, *, expect_status: int = 200,
                     expect_contains: str = "",
                     timeout: float = 15.0) -> Dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as cli:
            r = await cli.get(url, headers={"User-Agent": "Altiaro-HealthCheck/1.0"})
        ok = r.status_code == expect_status
        if ok and expect_contains:
            ok = expect_contains in (r.text or "")
        return {"ok": ok, "status": r.status_code, "url": url,
                "detail": "" if ok else r.text[:120]}
    except Exception as e:
        return {"ok": False, "url": url, "error": str(e)[:120]}


async def _check_homepage(site: Dict[str, Any]) -> Dict[str, Any]:
    domain = site.get("custom_domain")
    if not domain:
        return {"name": "homepage_reachable", "ok": False, "skip": True,
                "detail": "no_custom_domain"}
    res = await _http_check(f"https://{domain}/", expect_contains="")
    return {"name": "homepage_reachable", **res}


async def _check_robots(site: Dict[str, Any]) -> Dict[str, Any]:
    domain = site.get("custom_domain")
    if not domain:
        return {"name": "robots_txt_present", "ok": False, "skip": True}
    res = await _http_check(f"https://{domain}/robots.txt", expect_contains="sitemap")
    return {"name": "robots_txt_present", **res}


async def _check_sitemap(site: Dict[str, Any]) -> Dict[str, Any]:
    domain = site.get("custom_domain")
    if not domain:
        return {"name": "sitemap_xml_valid", "ok": False, "skip": True}
    res = await _http_check(f"https://{domain}/sitemap.xml", expect_contains="<urlset")
    return {"name": "sitemap_xml_valid", **res}


async def _check_ssl(site: Dict[str, Any]) -> Dict[str, Any]:
    domain = site.get("custom_domain")
    if not domain:
        return {"name": "ssl_certificate", "ok": False, "skip": True}
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=False) as cli:
            r = await cli.get(f"https://{domain}/")
        return {"name": "ssl_certificate", "ok": r.status_code in (200, 301, 302),
                "status": r.status_code}
    except Exception as e:
        return {"name": "ssl_certificate", "ok": False, "error": str(e)[:120]}


async def _check_noindex(site: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure the storefront does NOT emit X-Robots-Tag: noindex in prod."""
    domain = site.get("custom_domain")
    if not domain:
        return {"name": "no_noindex_header", "ok": False, "skip": True}
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as cli:
            r = await cli.get(f"https://{domain}/",
                              headers={"User-Agent": "Googlebot/2.1"})
        xrt = (r.headers.get("X-Robots-Tag") or "").lower()
        ok = "noindex" not in xrt and "nofollow" not in xrt
        return {"name": "no_noindex_header", "ok": ok, "x_robots_tag": xrt or None}
    except Exception as e:
        return {"name": "no_noindex_header", "ok": False, "error": str(e)[:120]}


async def _check_products(site_id: str) -> Dict[str, Any]:
    count = await db.products.count_documents({"site_id": site_id, "status": "active"})
    return {"name": "products_published", "ok": count >= 3, "count": count}


async def _check_blog(site_id: str) -> Dict[str, Any]:
    count = await db.blog_posts.count_documents({"site_id": site_id,
                                                   "status": "published"})
    return {"name": "blog_posts_published", "ok": count >= 10, "count": count}


async def _check_legal(site_id: str) -> Dict[str, Any]:
    site = await db.sites.find_one({"id": site_id}, {"legal": 1, "_id": 0}) or {}
    legal = site.get("legal") or {}
    required = ["cgv", "mentions", "confidentialite"]
    present = [k for k in required if (legal.get(k) or {}).get("body_md") or legal.get(k)]
    return {"name": "legal_pages", "ok": len(present) >= 3,
            "present": present, "missing": [k for k in required if k not in present]}


async def _check_tracking(site_id: str) -> Dict[str, Any]:
    site = await db.sites.find_one({"id": site_id}, {"tracking": 1, "_id": 0}) or {}
    tracking = site.get("tracking") or {}
    return {"name": "ga4_tracking", "ok": bool(tracking.get("ga4_measurement_id")),
            "ga4": tracking.get("ga4_measurement_id") or None}


async def _check_gsc(site_id: str) -> Dict[str, Any]:
    site = await db.sites.find_one({"id": site_id}, {"google_provisioning": 1, "_id": 0}) or {}
    gsc = ((site.get("google_provisioning") or {}).get("gsc") or {})
    return {"name": "gsc_provisioned", "ok": bool(gsc.get("ok")),
            "detail": gsc.get("error") or ""}


async def _check_gmc(site_id: str) -> Dict[str, Any]:
    site = await db.sites.find_one({"id": site_id}, {"google_provisioning": 1, "_id": 0}) or {}
    gmc = ((site.get("google_provisioning") or {}).get("gmc") or {})
    return {"name": "gmc_provisioned", "ok": bool(gmc.get("ok")),
            "detail": gmc.get("error") or gmc.get("reason") or ""}


async def run_health_check(site_id: str) -> Dict[str, Any]:
    site = await db.sites.find_one({"id": site_id}) or {}
    if not site:
        return {"ok": False, "reason": "site_not_found"}

    checks: List[Dict[str, Any]] = await asyncio.gather(
        _check_homepage(site),
        _check_robots(site),
        _check_sitemap(site),
        _check_ssl(site),
        _check_noindex(site),
        _check_products(site_id),
        _check_blog(site_id),
        _check_legal(site_id),
        _check_tracking(site_id),
        _check_gsc(site_id),
        _check_gmc(site_id),
    )
    score = sum(1 for c in checks if c.get("ok"))
    status = "pass" if score >= 9 else ("warn" if score >= 6 else "fail")
    result = {
        "ok": status == "pass",
        "score": score,
        "total": len(checks),
        "status": status,
        "checks": checks,
        "checked_at": _now_iso(),
    }
    await db.sites.update_one({"id": site_id}, {"$set": {"health_check": result}})
    return result
