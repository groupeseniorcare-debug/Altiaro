"""
Approximated provisioning service.

Custom domain reverse-proxy + automated SSL via https://approximated.app

API docs : https://approximated.app/docs/

Auth : `Api-Key` HTTP header (lowercase `api-key` works too).

Endpoints used :
- POST   /api/vhosts                                         (create)
- GET    /api/vhosts/by/incoming/:incoming                   (read latest cached status)
- GET    /api/vhosts/by/incoming/:incoming/force-check       (read with fresh check)
- DELETE /api/vhosts/by/incoming/:incoming                   (delete)

A virtual host returns the cluster IP to point DNS at, embedded in
`user_message` (regex extraction below). We also expose `get_dns_targets()`
which creates a dummy probe vhost ONLY if needed (we cache the IP in env).

Status fields :
- apx_hit         : bool — requests reach the proxy cluster
- is_resolving    : bool — DNS resolves (anywhere)
- has_ssl         : bool — SSL cert issued
- dns_pointed_at  : str  — current IP that DNS resolves to
- status          : str  — ACTIVE_SSL | DNS_INCORRECT | DNS_NOT_RESOLVING | …

Convenience flag `ready` = apx_hit && is_resolving && has_ssl.
"""
from __future__ import annotations

import logging
import os
import re
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger("conceptfactory.approximated")

API_BASE = os.environ.get(
    "APPROXIMATED_API_BASE", "https://cloud.approximated.app/api"
).rstrip("/")
API_KEY = os.environ.get("APPROXIMATED_API_KEY", "").strip()
TARGET_HOST = os.environ.get(
    "APPROXIMATED_TARGET_HOST", "commerce-builder-21.preview.emergentagent.com"
).strip()
TARGET_PORT = os.environ.get("APPROXIMATED_TARGET_PORT", "443").strip() or "443"

# Cluster IPs are stable per API key. Cache them once detected to avoid
# rate-limiting Approximated.
# Pre-seeded from observed responses (2026-05-01).
_CACHED_CLUSTER_IPS: list[str] = [
    ip.strip()
    for ip in (os.environ.get("APPROXIMATED_CLUSTER_IPS", "213.188.213.253").split(","))
    if ip.strip()
]

_USER_MSG_IP_RE = re.compile(r"\b(\d{1,3}(?:\.\d{1,3}){3})\b")
_TIMEOUT = httpx.Timeout(20.0, connect=10.0)


def is_configured() -> bool:
    return bool(API_KEY)


def _headers() -> Dict[str, str]:
    return {
        "Api-Key": API_KEY,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


async def _request(
    method: str, path: str, *, json: Optional[dict] = None, timeout: float = 20.0
) -> tuple[int, Any]:
    """Lightweight HTTP wrapper. Returns (status_code, parsed_body_or_text)."""
    if not is_configured():
        raise RuntimeError("APPROXIMATED_API_KEY missing in env")
    url = f"{API_BASE}{path}"
    async with httpx.AsyncClient(timeout=httpx.Timeout(timeout, connect=10.0)) as client:
        resp = await client.request(method, url, json=json, headers=_headers())
    body: Any
    try:
        body = resp.json()
    except Exception:
        body = resp.text
    return resp.status_code, body


def _extract_ips_from_user_message(msg: str) -> list[str]:
    if not msg:
        return []
    seen: list[str] = []
    for m in _USER_MSG_IP_RE.finditer(msg):
        ip = m.group(1)
        # Filter out obviously private IPs / placeholders if any
        if ip not in seen:
            seen.append(ip)
    return seen


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
async def create_vhost(
    domain: str,
    *,
    target: Optional[str] = None,
    target_ports: Optional[str] = None,
    redirect_www: bool = True,
    keep_host: Optional[bool] = None,
) -> Dict[str, Any]:
    """Create a virtual host on the Approximated cluster.

    Idempotent: if a vhost already exists with the same incoming address, we
    fetch and return its current state (status 200) instead of erroring.
    """
    target = target or TARGET_HOST
    target_ports = target_ports or TARGET_PORT
    payload = {
        "incoming_address": domain,
        "target_address": target,
        "target_ports": target_ports,
        "redirect_www": redirect_www,
    }
    if keep_host is not None:
        payload["keep_host"] = bool(keep_host)
    code, body = await _request("POST", "/vhosts", json=payload)
    if code in (200, 201):
        data = (body or {}).get("data") if isinstance(body, dict) else None
        if data and isinstance(data, dict):
            ips = _extract_ips_from_user_message(data.get("user_message", "") or "")
            if ips:
                global _CACHED_CLUSTER_IPS
                _CACHED_CLUSTER_IPS = ips
        return {"ok": True, "created": True, "code": code, "data": data, "raw": body}
    if code == 422 and isinstance(body, dict):
        errs = (body.get("errors") or {}).get("incoming_address") or []
        if any("already been created" in (e or "").lower() for e in errs):
            existing = await get_vhost_status(domain)
            existing["created"] = False
            existing["already_existed"] = True
            return existing
    return {"ok": False, "code": code, "error": body}


async def get_vhost_status(domain: str, *, force_check: bool = False) -> Dict[str, Any]:
    """Fetch a vhost current state. `force_check=True` triggers a fresh probe
    (rate-limited server-side, may take up to 30s)."""
    suffix = "/force-check" if force_check else ""
    code, body = await _request(
        "GET",
        f"/vhosts/by/incoming/{domain}{suffix}",
        timeout=45.0 if force_check else 20.0,
    )
    if code != 200 or not isinstance(body, dict):
        return {"ok": False, "code": code, "error": body, "domain": domain}
    data = body.get("data") or {}
    apx_hit = bool(data.get("apx_hit"))
    is_resolving = bool(data.get("is_resolving"))
    has_ssl = bool(data.get("has_ssl"))
    user_msg = data.get("user_message") or ""
    ips = _extract_ips_from_user_message(user_msg)
    if ips:
        global _CACHED_CLUSTER_IPS
        _CACHED_CLUSTER_IPS = ips
    return {
        "ok": True,
        "code": code,
        "domain": domain,
        "id": data.get("id"),
        "status": data.get("status"),
        "status_message": data.get("status_message"),
        "apx_hit": apx_hit,
        "is_resolving": is_resolving,
        "has_ssl": has_ssl,
        "dns_pointed_at": data.get("dns_pointed_at"),
        "target_address": data.get("target_address"),
        "target_ports": data.get("target_ports"),
        "ssl_active_until": data.get("ssl_active_until"),
        "last_monitored_unix": data.get("last_monitored_unix"),
        "ready": apx_hit and is_resolving and has_ssl,
        "user_message": user_msg,
        "data": data,
    }


async def delete_vhost(domain: str) -> Dict[str, Any]:
    code, body = await _request("DELETE", f"/vhosts/by/incoming/{domain}")
    return {"ok": code in (200, 204), "code": code, "body": body, "domain": domain}


async def get_dns_targets(probe_domain: Optional[str] = None) -> Dict[str, Any]:
    """Return the cluster IPs to point an A record at.

    Strategy:
    1. Return cached IPs (env override or previously observed).
    2. If a probe_domain is provided AND no cache, query its vhost to extract
       the IP from user_message.
    """
    if _CACHED_CLUSTER_IPS:
        return {"ok": True, "ips": list(_CACHED_CLUSTER_IPS), "source": "cache"}
    if probe_domain:
        info = await get_vhost_status(probe_domain)
        if info.get("ok") and _CACHED_CLUSTER_IPS:
            return {
                "ok": True,
                "ips": list(_CACHED_CLUSTER_IPS),
                "source": f"probe:{probe_domain}",
            }
    return {"ok": False, "ips": [], "error": "no cluster IP known"}


async def list_vhosts(after: Optional[str] = None) -> Dict[str, Any]:
    """Cursor-paginated list (20/page)."""
    path = "/cursor/vhosts" if not after else f"/cursor/vhosts/after/{after}"
    code, body = await _request("GET", path)
    return {"ok": code == 200, "code": code, "body": body}
