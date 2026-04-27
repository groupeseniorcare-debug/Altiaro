"""Lot E — Mollie Connect OAuth (multi-tenant payments per site).

Permet à chaque concepteur de connecter SON propre compte Mollie à son site.
Les paiements sur la storefront vont alors directement sur le compte Mollie
du concepteur (au lieu du compte plateforme Altiaro), avec son nom commercial
sur la page de paiement hébergée.

Sans split commission pour l'instant (décision user 2026-04-27 — TODO).

Endpoints exposés :
    GET  /api/sites/{site_id}/mollie/oauth/start
         → redirige le concepteur vers Mollie Connect (avec state CSRF token)

    GET  /api/sites/mollie/oauth/callback?code=...&state=...
         → exchange code → access_token + refresh_token, persiste en DB
         → redirige vers /sites/{site_id}/integrations?mollie=connected

    POST /api/sites/{site_id}/mollie/oauth/disconnect
         → révoque le token (best-effort) + clean DB

    GET  /api/sites/{site_id}/mollie/status
         → retourne {connected: bool, organization_id, expires_at}
"""
from __future__ import annotations

import logging
import os
import secrets
import urllib.parse
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse

from deps import db, FRONTEND_URL, get_current_user

logger = logging.getLogger("conceptfactory.mollie_oauth")

router = APIRouter()

MOLLIE_AUTHORIZE_URL = "https://www.mollie.com/oauth2/authorize"
MOLLIE_TOKEN_URL = "https://api.mollie.com/oauth2/tokens"
MOLLIE_REVOKE_URL = "https://api.mollie.com/oauth2/tokens"  # DELETE /:token

DEFAULT_SCOPES = (
    "payments.read payments.write profiles.read profiles.write "
    "customers.read customers.write organizations.read settlements.read "
    "refunds.write balances.read"
)


def _client_creds():
    cid = os.environ.get("MOLLIE_CLIENT_ID")
    cs = os.environ.get("MOLLIE_CLIENT_SECRET")
    if not cid or not cs:
        raise HTTPException(
            status_code=500,
            detail="Mollie Connect non configuré (MOLLIE_CLIENT_ID/SECRET manquants).",
        )
    return cid, cs


def _redirect_uri():
    return os.environ.get(
        "MOLLIE_OAUTH_REDIRECT_URI",
        f"{FRONTEND_URL}/api/sites/mollie/oauth/callback",
    )


async def _check_site_access(site_id: str, user: dict):
    """Concepteur owner ou admin only."""
    site = await db.sites.find_one({"id": site_id}, {"_id": 0, "operator_id": 1})
    if not site:
        raise HTTPException(404, "Site introuvable")
    if user.get("role") != "admin" and site.get("operator_id") != user.get("id"):
        raise HTTPException(403, "Accès refusé")


@router.get("/sites/{site_id}/mollie/oauth/start")
async def oauth_start(site_id: str, user: dict = Depends(get_current_user)):
    """Génère l'URL d'autorisation Mollie Connect avec state CSRF token."""
    await _check_site_access(site_id, user)
    cid, _ = _client_creds()
    redirect_uri = _redirect_uri()

    # Génère un state CSRF qui contient le site_id (signé en clair pour MVP — Mollie le retourne tel quel)
    csrf_token = secrets.token_urlsafe(24)
    state = f"{site_id}:{csrf_token}"
    # Persiste le csrf token pour validation au callback
    await db.mollie_oauth_states.insert_one({
        "state": state,
        "site_id": site_id,
        "user_id": user.get("id"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat(),
    })

    scopes = os.environ.get("MOLLIE_OAUTH_SCOPES", DEFAULT_SCOPES)
    params = {
        "client_id": cid,
        "redirect_uri": redirect_uri,
        "state": state,
        "scope": scopes,
        "response_type": "code",
        "approval_prompt": "auto",
    }
    auth_url = f"{MOLLIE_AUTHORIZE_URL}?{urllib.parse.urlencode(params)}"
    return {"authorize_url": auth_url}


@router.get("/sites/mollie/oauth/callback")
async def oauth_callback(request: Request, code: Optional[str] = None,
                         state: Optional[str] = None,
                         error: Optional[str] = None):
    """Mollie redirects here after consent. Exchange code → tokens, persist, redirect cockpit."""
    if error:
        logger.warning(f"[mollie] OAuth callback error: {error}")
        return RedirectResponse(f"{FRONTEND_URL}/dashboard?mollie_error={error}")
    if not code or not state:
        raise HTTPException(400, "Paramètres OAuth manquants (code, state)")

    # 1. Validate state (CSRF + retrieve site_id)
    state_doc = await db.mollie_oauth_states.find_one({"state": state})
    if not state_doc:
        raise HTTPException(400, "State invalide ou expiré (CSRF check failed)")
    # Cleanup
    await db.mollie_oauth_states.delete_one({"state": state})
    expires_at = datetime.fromisoformat(state_doc["expires_at"].replace("Z", "+00:00"))
    if datetime.now(timezone.utc) > expires_at:
        raise HTTPException(400, "State OAuth expiré (>10 min)")
    site_id = state_doc["site_id"]

    # 2. Exchange code → tokens
    cid, cs = _client_creds()
    redirect_uri = _redirect_uri()
    try:
        async with httpx.AsyncClient(timeout=30) as cli:
            r = await cli.post(
                MOLLIE_TOKEN_URL,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "client_id": cid,
                    "client_secret": cs,
                },
                headers={"Accept": "application/json"},
            )
        if r.status_code != 200:
            logger.error(f"[mollie] token exchange failed HTTP {r.status_code}: {r.text[:300]}")
            return RedirectResponse(
                f"{FRONTEND_URL}/sites/{site_id}/integrations?mollie_error=token_exchange_failed",
            )
        tok = r.json()
    except Exception as e:
        logger.exception(f"[mollie] token exchange exception: {e}")
        return RedirectResponse(
            f"{FRONTEND_URL}/sites/{site_id}/integrations?mollie_error=exception",
        )

    access_token = tok.get("access_token")
    refresh_token = tok.get("refresh_token")
    expires_in = int(tok.get("expires_in", 3600))
    expires_at_iso = (
        datetime.now(timezone.utc) + timedelta(seconds=expires_in - 60)
    ).isoformat()

    # 3. (Optional) Récupère l'organization id pour affichage cockpit
    org_id = None
    org_name = None
    try:
        async with httpx.AsyncClient(timeout=20) as cli:
            r = await cli.get(
                "https://api.mollie.com/v2/organizations/me",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/json",
                },
            )
            if r.status_code == 200:
                org = r.json()
                org_id = org.get("id")
                org_name = org.get("name")
    except Exception:
        pass

    # 4. Persist on the site
    await db.sites.update_one(
        {"id": site_id},
        {"$set": {
            "payments.mollie_oauth": {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "expires_at": expires_at_iso,
                "scope": tok.get("scope"),
                "token_type": tok.get("token_type", "bearer"),
                "organization_id": org_id,
                "organization_name": org_name,
                "connected_at": datetime.now(timezone.utc).isoformat(),
                "connected_by": state_doc.get("user_id"),
                "mode": "live",  # Mollie Connect = live by default
            },
        }},
    )
    logger.info(f"[mollie] site {site_id[:8]} connected to Mollie org {org_name or org_id}")

    return RedirectResponse(
        f"{FRONTEND_URL}/sites/{site_id}/integrations?mollie=connected",
    )


@router.post("/sites/{site_id}/mollie/oauth/disconnect")
async def oauth_disconnect(site_id: str, user: dict = Depends(get_current_user)):
    """Best-effort revoke the token at Mollie + clean DB."""
    await _check_site_access(site_id, user)
    site = await db.sites.find_one({"id": site_id}, {"_id": 0, "payments.mollie_oauth": 1})
    oauth = ((site or {}).get("payments") or {}).get("mollie_oauth") or {}
    access_token = oauth.get("access_token")
    if access_token:
        cid, cs = _client_creds()
        try:
            # Mollie revoke endpoint : DELETE https://api.mollie.com/oauth2/tokens
            async with httpx.AsyncClient(timeout=15) as cli:
                await cli.request(
                    "DELETE",
                    MOLLIE_REVOKE_URL,
                    json={"token": access_token, "token_type_hint": "access_token"},
                    auth=(cid, cs),
                    headers={"Accept": "application/json"},
                )
        except Exception as e:
            logger.warning(f"[mollie] revoke failed: {e}")
    await db.sites.update_one(
        {"id": site_id},
        {"$unset": {"payments.mollie_oauth": ""}},
    )
    return {"ok": True, "disconnected": True}


@router.get("/sites/{site_id}/mollie/status")
async def oauth_status(site_id: str, user: dict = Depends(get_current_user)):
    """Returns Mollie Connect status for the site (used by integrations UI card)."""
    await _check_site_access(site_id, user)
    site = await db.sites.find_one({"id": site_id}, {"_id": 0, "payments.mollie_oauth": 1})
    oauth = ((site or {}).get("payments") or {}).get("mollie_oauth")
    if not oauth or not oauth.get("access_token"):
        return {"connected": False}
    return {
        "connected": True,
        "organization_id": oauth.get("organization_id"),
        "organization_name": oauth.get("organization_name"),
        "connected_at": oauth.get("connected_at"),
        "expires_at": oauth.get("expires_at"),
        "mode": oauth.get("mode"),
    }
