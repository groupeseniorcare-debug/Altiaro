"""Bloc 2 — Public + admin endpoints for legal pages (mentions légales, CGV,
confidentialité, cookies, retours, livraison) generated for any Concepteur
store from the centralized `altiaro_legal.PLATFORM_LEGAL_INFO` source.

Routes (mounted by server.py):
- GET  /api/public/sites/{site_id}/legal/{slug}   → public, used by LegalPage
- GET  /api/admin/legal-settings                  → admin, returns the dict
- PUT  /api/admin/legal-settings                  → admin, persist override
                                                    (DB → .env → constant
                                                    fallback chain)
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException

from deps import db, require_admin
from altiaro_legal import (
    PLATFORM_LEGAL_INFO,
    get_site_legal_page,
)

# ─── Public router ────────────────────────────────────────────────────
public_router = APIRouter(tags=["public-legal"])


@public_router.get("/public/sites/{site_id}/legal/{slug}")
async def public_site_legal_page(site_id: str, slug: str):
    """Return the generated legal page (markdown body) for this Concepteur
    store, from the centralized template.

    `slug` ∈ {mentions-legales, mentions, cgv, confidentialite, privacy,
              cookies, retours, returns, livraison, shipping}.
    """
    site = await db.sites.find_one({"id": site_id}, {"_id": 0})
    if not site:
        raise HTTPException(status_code=404, detail="Site introuvable")
    page = get_site_legal_page(site, slug)
    if not page:
        raise HTTPException(status_code=404, detail=f"Page légale '{slug}' inconnue")
    return {
        "site_id": site_id,
        "slug": slug,
        **page,  # title, updated, body_md
    }


# ─── Admin router ─────────────────────────────────────────────────────
admin_router = APIRouter(prefix="/admin", tags=["admin-legal"])


@admin_router.get("/legal-settings")
async def admin_get_legal_settings(_user=Depends(require_admin)):
    """Return the centralized PLATFORM_LEGAL_INFO snapshot.

    Source priority : DB collection `platform_legal` > .env > hardcoded
    constant. The DB doc (if any) overrides individual fields.
    """
    override: Dict[str, Any] = {}
    try:
        doc = await db.platform_legal.find_one({"key": "info"}, {"_id": 0})
        if doc:
            override = {k: v for k, v in doc.items() if k not in ("key",)}
    except Exception:
        pass
    merged: Dict[str, str] = {**PLATFORM_LEGAL_INFO, **override}
    return {
        "source": "db" if override else "constant",
        "override_keys": list(override.keys()) if override else [],
        "info": merged,
    }


@admin_router.put("/legal-settings")
async def admin_put_legal_settings(payload: Dict[str, Any], _user=Depends(require_admin)):
    """Override one or more keys of PLATFORM_LEGAL_INFO at runtime.

    Only allowed keys are accepted (whitelist below). Unknown keys are
    ignored. Empty strings DELETE the override.
    """
    allowed = set(PLATFORM_LEGAL_INFO.keys())
    clean = {k: str(v).strip() for k, v in (payload or {}).items()
             if k in allowed and v is not None}
    set_ops: Dict[str, Any] = {}
    unset_ops: Dict[str, str] = {}
    for k, v in clean.items():
        if v == "":
            unset_ops[k] = ""
        else:
            set_ops[k] = v
    update: Dict[str, Any] = {}
    if set_ops:
        update["$set"] = {**set_ops, "key": "info"}
    if unset_ops:
        update["$unset"] = unset_ops
    if not update:
        return {"ok": True, "no_changes": True}
    await db.platform_legal.update_one({"key": "info"}, update, upsert=True)
    doc = await db.platform_legal.find_one({"key": "info"}, {"_id": 0}) or {}
    merged: Dict[str, str] = {**PLATFORM_LEGAL_INFO, **{k: v for k, v in doc.items() if k != "key"}}
    return {"ok": True, "info": merged}
