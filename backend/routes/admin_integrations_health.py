"""Admin token-swap endpoints + health-checks d'integrations.

POST /api/admin/integrations/pinterest/update-token
POST /api/admin/integrations/featured/update-key
GET  /api/admin/integrations/health
"""
from __future__ import annotations

import asyncio
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from deps import db, get_current_user

router = APIRouter(tags=["admin-integrations"])

ENV_PATH = "/app/backend/.env"


def _require_admin(user: dict):
    if user.get("role") != "admin":
        raise HTTPException(403, "Admin only")


def _set_env_var(key: str, value: str) -> bool:
    """Met a jour ou ajoute KEY=VALUE dans /app/backend/.env. Live-reload os.environ."""
    try:
        with open(ENV_PATH, "r") as f:
            content = f.read()
    except Exception:
        content = ""
    pattern = re.compile(rf"^{re.escape(key)}=.*$", re.MULTILINE)
    line = f"{key}={value}"
    if pattern.search(content):
        new = pattern.sub(line, content)
    else:
        sep = "" if content.endswith("\n") or not content else "\n"
        new = content + sep + line + "\n"
    try:
        with open(ENV_PATH, "w") as f:
            f.write(new)
        os.environ[key] = value  # live reload sans restart
        return True
    except Exception:
        return False


# ---- Pinterest ----------------------------------------------------------
class PinterestTokenIn(BaseModel):
    access_token: str


@router.post("/admin/integrations/pinterest/update-token")
async def pinterest_update_token(body: PinterestTokenIn,
                                  user: dict = Depends(get_current_user)):
    _require_admin(user)
    tok = (body.access_token or "").strip()
    if not tok:
        raise HTTPException(400, "access_token vide")
    headers = {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=20) as cli:
        # 1) Check user_account
        r1 = await cli.get("https://api.pinterest.com/v5/user_account", headers=headers)
        if r1.status_code >= 400:
            return {"valid": False, "step": "user_account", "status": r1.status_code,
                    "error": r1.text[:300]}
        # 2) Probe write scope -> create dummy board, then delete it.
        probe_name = f"_altiaro_probe_{int(datetime.now().timestamp())}"
        r2 = await cli.post(
            "https://api.pinterest.com/v5/boards", headers=headers,
            json={"name": probe_name, "description": "probe", "privacy": "SECRET"},
        )
        if r2.status_code >= 400:
            return {"valid": False, "step": "create_board",
                    "status": r2.status_code, "error": r2.text[:300],
                    "scopes_likely_present": ["user_accounts:read", "boards:read"],
                    "scopes_likely_missing": ["boards:write", "pins:write"]}
        board_id = (r2.json() or {}).get("id")
        if board_id:
            await cli.delete(f"https://api.pinterest.com/v5/boards/{board_id}", headers=headers)
    if not _set_env_var("PINTEREST_APP_SECRET", tok):
        return {"valid": True, "persisted": False, "warning": "env_write_failed"}
    await db.platform_settings.update_one(
        {"key": "pinterest"},
        {"$set": {"connected": True, "last_validated_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True,
    )
    return {"valid": True, "persisted": True,
            "scopes_confirmed": ["user_accounts:read", "boards:write", "pins:write"]}


# ---- Featured.com -------------------------------------------------------
class FeaturedKeyIn(BaseModel):
    api_key: str


@router.post("/admin/integrations/featured/update-key")
async def featured_update_key(body: FeaturedKeyIn,
                               user: dict = Depends(get_current_user)):
    _require_admin(user)
    key = (body.api_key or "").strip()
    if not key:
        raise HTTPException(400, "api_key vide")
    base = os.environ.get("FEATURED_API_BASE", "https://api.featured.com/v1")
    headers = {"Authorization": f"Bearer {key}"}
    valid = False
    error = None
    try:
        async with httpx.AsyncClient(timeout=15) as cli:
            r = await cli.get(f"{base}/queries", headers=headers, params={"limit": 1})
        valid = r.status_code < 400
        if not valid:
            error = r.text[:200]
    except Exception as e:
        error = str(e)[:200]
    if not valid:
        return {"valid": False, "error": error}
    if not _set_env_var("FEATURED_API_KEY", key):
        return {"valid": True, "persisted": False, "warning": "env_write_failed"}
    return {"valid": True, "persisted": True}


# ---- Health overview ----------------------------------------------------
async def _check_pinterest() -> Dict[str, Any]:
    tok = os.environ.get("PINTEREST_APP_SECRET")
    if not tok:
        return {"ok": False, "reason": "missing_token"}
    async with httpx.AsyncClient(timeout=10) as cli:
        try:
            r = await cli.get("https://api.pinterest.com/v5/user_account",
                              headers={"Authorization": f"Bearer {tok}"})
            if r.status_code >= 400:
                return {"ok": False, "reason": f"http_{r.status_code}"}
            return {"ok": True, "username": (r.json() or {}).get("username")}
        except Exception as e:
            return {"ok": False, "reason": "network", "error": str(e)[:120]}


async def _check_featured() -> Dict[str, Any]:
    key = os.environ.get("FEATURED_API_KEY")
    if not key:
        return {"ok": False, "reason": "missing_api_key"}
    base = os.environ.get("FEATURED_API_BASE", "https://api.featured.com/v1")
    async with httpx.AsyncClient(timeout=10) as cli:
        try:
            r = await cli.get(f"{base}/queries",
                              headers={"Authorization": f"Bearer {key}"},
                              params={"limit": 1})
            return {"ok": r.status_code < 400, "status": r.status_code}
        except Exception as e:
            return {"ok": False, "reason": "network", "error": str(e)[:120]}


async def _check_approximated() -> Dict[str, Any]:
    if not os.environ.get("APPROXIMATED_API_KEY"):
        return {"ok": False, "reason": "missing_key"}
    async with httpx.AsyncClient(timeout=10) as cli:
        try:
            r = await cli.get(
                "https://cloud.approximated.app/api/vhosts",
                headers={"api-key": os.environ["APPROXIMATED_API_KEY"]},
            )
            return {"ok": r.status_code < 400, "status": r.status_code}
        except Exception as e:
            return {"ok": False, "reason": "network", "error": str(e)[:120]}


async def _check_ovh() -> Dict[str, Any]:
    try:
        from services import ovh_dns
        return {"ok": ovh_dns.is_configured()}
    except Exception as e:
        return {"ok": False, "error": str(e)[:120]}


async def _check_mollie() -> Dict[str, Any]:
    has_test = bool(os.environ.get("MOLLIE_TEST_KEY"))
    has_live = bool(os.environ.get("MOLLIE_LIVE_KEY"))
    has_oauth = bool(os.environ.get("MOLLIE_CLIENT_ID") and os.environ.get("MOLLIE_CLIENT_SECRET"))
    return {"ok": has_test or has_live or has_oauth,
            "test_key": has_test, "live_key": has_live, "oauth": has_oauth}


async def _check_resend() -> Dict[str, Any]:
    return {"ok": bool(os.environ.get("RESEND_API_KEY"))}


async def _check_google_master() -> Dict[str, Any]:
    h = await db.platform_health.find_one({"key": "google_master_oauth"}, {"_id": 0}) or {}
    if not h:
        return {"ok": False, "reason": "never_checked"}
    return {"ok": bool(h.get("ok")), "reason": h.get("reason"),
            "last_check_at": h.get("last_check_at"),
            "reconnect_url": "/admin/google-master"}


INTEGRATIONS = [
    ("google_master", "Google Master OAuth", _check_google_master, "/admin/google-master"),
    ("pinterest",     "Pinterest",            _check_pinterest,     "/admin/integrations#pinterest"),
    ("featured",      "Featured.com",         _check_featured,      "/admin/integrations#featured"),
    ("approximated",  "Approximated",         _check_approximated,  "/admin/integrations#approximated"),
    ("ovh",           "OVH DNS",              _check_ovh,           "/admin/integrations#ovh"),
    ("mollie",        "Mollie",               _check_mollie,        "/admin/integrations#mollie"),
    ("resend",        "Resend",               _check_resend,        "/admin/integrations#resend"),
]


@router.get("/admin/integrations/health")
async def integrations_health(user: dict = Depends(get_current_user)):
    _require_admin(user)
    out: List[Dict[str, Any]] = []
    for slug, label, fn, url in INTEGRATIONS:
        try:
            res = await fn()
        except Exception as e:
            res = {"ok": False, "error": str(e)[:120]}
        out.append({
            "slug": slug, "label": label,
            "ok": bool(res.get("ok")),
            "detail": res,
            "reconnect_url": url,
        })
    return {"items": out, "checked_at": datetime.now(timezone.utc).isoformat()}
