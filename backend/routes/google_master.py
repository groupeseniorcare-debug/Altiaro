"""Master Google OAuth pour Altiaro (compte plateforme).

Ce flow OAuth est exécuté **une seule fois** par un administrateur Altiaro.
Il génère un `refresh_token` long-lived stocké dans
`db.platform_settings.google_master` et utilisé ensuite par toutes les
fonctions de provisioning (`services/google_provisioning.py`) pour appeler
les API Google au nom du compte maître :

- Search Console (sites.add, sitemaps.submit, urlInspection)
- Site Verification (insert/verify)
- Content for Shopping (Merchant Center : accounts.insert, products.insert)
- Google Ads (customers.createCustomerClient, conversions)
- Analytics Admin (properties.create, dataStreams.create)

Scopes demandés (cf. Google_OAuth playbook 2026) :
- `https://www.googleapis.com/auth/webmasters`
- `https://www.googleapis.com/auth/webmasters.readonly`
- `https://www.googleapis.com/auth/content`
- `https://www.googleapis.com/auth/adwords`
- `https://www.googleapis.com/auth/analytics.edit`
- `https://www.googleapis.com/auth/analytics.readonly`
- `https://www.googleapis.com/auth/siteverification`
- `openid`, `email`, `profile`
"""
from __future__ import annotations
import logging
import os
import secrets
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse

from deps import db, get_current_user

router = APIRouter(tags=["google-master"])
logger = logging.getLogger("altiaro.google_master")

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"

MASTER_SCOPES = [
    "openid", "email", "profile",
    "https://www.googleapis.com/auth/webmasters",
    "https://www.googleapis.com/auth/webmasters.readonly",
    "https://www.googleapis.com/auth/content",
    "https://www.googleapis.com/auth/adwords",
    "https://www.googleapis.com/auth/analytics.edit",
    "https://www.googleapis.com/auth/analytics.readonly",
    "https://www.googleapis.com/auth/siteverification",
]


def _client_id() -> str:
    return os.environ.get("GOOGLE_CLIENT_ID") or ""


def _client_secret() -> str:
    return os.environ.get("GOOGLE_CLIENT_SECRET") or ""


def _redirect_uri() -> str:
    # Redirect dédié à ce flow (différent de GSC site-par-site)
    return os.environ.get("GOOGLE_MASTER_REDIRECT_URI") or ""


def _require_admin(user: dict):
    if user.get("role") != "admin":
        raise HTTPException(403, "Réservé aux administrateurs")


# ============================================================
#  Endpoints
# ============================================================
@router.get("/admin/google/master/start")
async def master_start(user: dict = Depends(get_current_user)):
    _require_admin(user)
    if not _client_id() or not _client_secret() or not _redirect_uri():
        raise HTTPException(500,
            "Variables manquantes : GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET / GOOGLE_MASTER_REDIRECT_URI")
    state = secrets.token_urlsafe(24)
    await db.google_master_oauth_states.update_one(
        {"state": state},
        {"$set": {
            "state": state,
            "user_id": user.get("id"),
            "user_email": user.get("email"),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }},
        upsert=True,
    )
    params = {
        "client_id": _client_id(),
        "redirect_uri": _redirect_uri(),
        "response_type": "code",
        "scope": " ".join(MASTER_SCOPES),
        "access_type": "offline",
        "prompt": "consent",       # force le retour d'un refresh_token
        "include_granted_scopes": "true",
        "state": state,
    }
    url = f"{GOOGLE_AUTH_URL}?{urlencode(params)}"
    return {"authorization_url": url, "state": state}


@router.get("/admin/google/master/callback")
async def master_callback(
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
):
    """Google redirige ici après consent. On échange le code contre un
    refresh_token et on stocke dans `platform_settings.google_master`."""
    frontend = os.environ.get("PUBLIC_FRONTEND_URL") or os.environ.get("FRONTEND_URL") or ""
    success_url = f"{frontend}/admin/integrations?google_master=connected"
    error_url = lambda r: f"{frontend}/admin/integrations?google_master=error&reason={r}"  # noqa: E731

    if error:
        return RedirectResponse(error_url(error), status_code=302)
    if not code or not state:
        return RedirectResponse(error_url("missing_code_or_state"), status_code=302)

    state_doc = await db.google_master_oauth_states.find_one({"state": state})
    if not state_doc:
        return RedirectResponse(error_url("invalid_state"), status_code=302)
    await db.google_master_oauth_states.delete_one({"state": state})

    # Exchange code → tokens
    try:
        async with httpx.AsyncClient(timeout=15.0) as cli:
            r = await cli.post(GOOGLE_TOKEN_URL, data={
                "code": code,
                "client_id": _client_id(),
                "client_secret": _client_secret(),
                "redirect_uri": _redirect_uri(),
                "grant_type": "authorization_code",
            })
        if r.status_code != 200:
            logger.warning(f"[google_master] token exchange failed : {r.status_code} {r.text[:200]}")
            return RedirectResponse(error_url("token_exchange_failed"), status_code=302)
        tok = r.json()
    except Exception as e:
        logger.exception(f"[google_master] token exchange exception : {e}")
        return RedirectResponse(error_url("exception"), status_code=302)

    refresh_token = tok.get("refresh_token")
    access_token = tok.get("access_token")
    scope_str = tok.get("scope") or ""
    if not refresh_token:
        # Si l'utilisateur a déjà consenti une fois sans révoquer, Google peut
        # ne pas renvoyer de refresh_token. On force `prompt=consent` mais au
        # cas où, on renvoie un message clair.
        return RedirectResponse(error_url("no_refresh_token"), status_code=302)

    # Récupère l'email du compte connecté (userinfo endpoint)
    google_email = None
    try:
        async with httpx.AsyncClient(timeout=10.0) as cli:
            ui = await cli.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
        if ui.status_code == 200:
            google_email = ui.json().get("email")
    except Exception:
        pass

    await db.platform_settings.update_one(
        {"key": "google_master"},
        {"$set": {
            "key": "google_master",
            "refresh_token": refresh_token,
            "scopes": scope_str.split(),
            "google_email": google_email,
            "granted_at": datetime.now(timezone.utc).isoformat(),
            "granted_by_user_id": state_doc.get("user_id"),
            "granted_by_user_email": state_doc.get("user_email"),
        }},
        upsert=True,
    )
    logger.info(f"[google_master] refresh_token stored — google_email={google_email}, scopes={len(scope_str.split())}")

    # Auto-discovery + verification DNS altiaro.com en background
    # (non-bloquant : on redirige immédiatement ; les jobs tournent ensuite)
    import asyncio as _aio
    _aio.create_task(_post_oauth_discovery())
    return RedirectResponse(success_url, status_code=302)


async def _post_oauth_discovery():
    """Background : appelle discover_all() + verify_altiaro_master_domain()
    juste après le callback OAuth, et persiste les résultats dans
    `platform_settings.{ga4_master, gmc_master, ads_master, dns_master_verification}`.
    """
    try:
        creds = await get_master_credentials()
        if not creds:
            logger.warning("[post_oauth] credentials introuvables")
            return
        from services.google_master_discovery import (
            discover_all, verify_altiaro_master_domain,
        )
        disc = await discover_all(creds)
        if (disc.get("ga4") or {}).get("ok"):
            await db.platform_settings.update_one(
                {"key": "ga4_master"},
                {"$set": {"key": "ga4_master", **disc["ga4"],
                          "discovered_at": datetime.now(timezone.utc).isoformat()}},
                upsert=True,
            )
        if (disc.get("gmc") or {}).get("ok"):
            await db.platform_settings.update_one(
                {"key": "gmc_master"},
                {"$set": {"key": "gmc_master", **disc["gmc"],
                          "discovered_at": datetime.now(timezone.utc).isoformat()}},
                upsert=True,
            )
        if (disc.get("ads") or {}).get("ok"):
            await db.platform_settings.update_one(
                {"key": "ads_master"},
                {"$set": {"key": "ads_master", **disc["ads"],
                          "discovered_at": datetime.now(timezone.utc).isoformat()}},
                upsert=True,
            )
        # Verification altiaro.com (Site Verification + GSC sites.add)
        verif = await verify_altiaro_master_domain(creds, domain="altiaro.com")
        await db.platform_settings.update_one(
            {"key": "altiaro_master_verification"},
            {"$set": {"key": "altiaro_master_verification", **verif,
                      "verified_at": datetime.now(timezone.utc).isoformat()}},
            upsert=True,
        )
        logger.info(f"[post_oauth] discovery+verify finished : {disc}")
    except Exception:
        logger.exception("[post_oauth] failed")


@router.get("/admin/google/master/status")
async def master_status(user: dict = Depends(get_current_user)):
    _require_admin(user)
    doc = await db.platform_settings.find_one({"key": "google_master"}, {"_id": 0, "refresh_token": 0})
    return {
        "configured": bool(_client_id() and _client_secret() and _redirect_uri()),
        "connected": bool(doc),
        "google_email": (doc or {}).get("google_email"),
        "scopes": (doc or {}).get("scopes") or [],
        "granted_at": (doc or {}).get("granted_at"),
        "granted_by_user_email": (doc or {}).get("granted_by_user_email"),
        "required_scopes": MASTER_SCOPES,
    }


@router.post("/admin/google/master/disconnect")
async def master_disconnect(user: dict = Depends(get_current_user)):
    _require_admin(user)
    res = await db.platform_settings.delete_one({"key": "google_master"})
    return {"ok": True, "deleted": res.deleted_count}


# ============================================================
#  Helper utilisé par le service de provisioning
# ============================================================
async def get_master_credentials():
    """Retourne un objet `google.oauth2.credentials.Credentials` frais
    (access_token rafraîchi automatiquement) ou `None` si pas encore connecté.
    Utilisé par `services/google_provisioning.py`."""
    doc = await db.platform_settings.find_one({"key": "google_master"})
    if not doc or not doc.get("refresh_token"):
        return None
    try:
        from google.oauth2.credentials import Credentials
    except Exception:
        logger.warning("[google_master] google-auth not installed — install google-api-python-client")
        return None
    creds = Credentials(
        token=None,
        refresh_token=doc["refresh_token"],
        client_id=_client_id(),
        client_secret=_client_secret(),
        token_uri=GOOGLE_TOKEN_URL,
        scopes=doc.get("scopes") or MASTER_SCOPES,
    )
    # Refresh access_token in-process (1h TTL)
    try:
        from google.auth.transport.requests import Request as _G
        creds.refresh(_G())
    except Exception as e:
        logger.exception(f"[google_master] credentials refresh failed : {e}")
        return None
    return creds


# ============================================================
#  Endpoints publics : dashboard admin, DNS, retry discovery,
#  provisioning par site
# ============================================================
class DnsVerificationInput:
    pass  # placeholder pour les linters


@router.post("/admin/google/dns-verification")
async def admin_dns_verification(payload: dict, user: dict = Depends(get_current_user)):
    """Pose un TXT DNS de vérification Google sur un domaine via OVH.

    Body : `{domain, token}`. Réutilisable pour tout futur domaine plateforme.
    """
    _require_admin(user)
    domain = (payload or {}).get("domain") or "altiaro.com"
    token = (payload or {}).get("token") or os.environ.get("GOOGLE_SITE_VERIFICATION_ALTIARO") or ""
    if not token:
        raise HTTPException(400, "Token de vérification manquant")
    from scripts.setup_altiaro_master_dns import run as _dns_run
    try:
        out = await _dns_run(domain=domain, token=token)
        return {"ok": True, **out}
    except Exception as e:
        logger.exception("[admin_dns_verification] failed")
        raise HTTPException(502, f"OVH DNS error : {str(e)[:300]}")


@router.post("/admin/google/master/discover")
async def admin_master_discover(user: dict = Depends(get_current_user)):
    """Force la re-découverte GA4/GMC/Ads (utile si l'utilisateur a fini la
    config côté Google après le OAuth)."""
    _require_admin(user)
    creds = await get_master_credentials()
    if not creds:
        raise HTTPException(400, "Master OAuth pas encore effectué")
    from services.google_master_discovery import discover_all, verify_altiaro_master_domain
    disc = await discover_all(creds)
    # Persiste
    for k in ("ga4", "gmc", "ads"):
        if (disc.get(k) or {}).get("ok"):
            await db.platform_settings.update_one(
                {"key": f"{k}_master"},
                {"$set": {"key": f"{k}_master", **disc[k],
                          "discovered_at": datetime.now(timezone.utc).isoformat()}},
                upsert=True,
            )
    verif = await verify_altiaro_master_domain(creds, "altiaro.com")
    await db.platform_settings.update_one(
        {"key": "altiaro_master_verification"},
        {"$set": {"key": "altiaro_master_verification", **verif,
                  "verified_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True,
    )
    return {"ok": True, "discovery": disc, "verification": verif}


@router.get("/admin/google/master/dashboard")
async def admin_master_dashboard(user: dict = Depends(get_current_user)):
    """Vue agrégée pour la page `/admin/google/master-auth` (post-OAuth).

    Retourne tout ce qui a été découvert / vérifié côté Google.
    """
    _require_admin(user)
    keys = ["google_master", "ga4_master", "gmc_master", "ads_master",
            "altiaro_master_verification", "dns_master_verification"]
    out: dict = {}
    for k in keys:
        doc = await db.platform_settings.find_one({"key": k}, {"_id": 0, "refresh_token": 0})
        out[k] = doc
    return {
        "configured": bool(_client_id() and _client_secret() and _redirect_uri()),
        "connected": bool(out.get("google_master")),
        "google_email": (out.get("google_master") or {}).get("google_email"),
        "scopes": (out.get("google_master") or {}).get("scopes") or [],
        "ga4_master": out.get("ga4_master"),
        "gmc_master": out.get("gmc_master"),
        "ads_master": out.get("ads_master"),
        "altiaro_verification": out.get("altiaro_master_verification"),
        "dns_verification": out.get("dns_master_verification"),
        "ads_mcc_env": os.environ.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID") or "",
    }


@router.post("/sites/{site_id}/google-provisioning/run")
async def run_site_google_provisioning(
    site_id: str,
    payload: Optional[dict] = None,
    user: dict = Depends(get_current_user),
):
    """Déclenche `provision_all(site_id)` manuellement (bouton sur la page QA).
    Body optionnel : `{"force": true}` pour réessayer chaque sub-service."""
    site = await db.sites.find_one({"id": site_id}, {"_id": 0, "id": 1, "operator_id": 1})
    if not site:
        raise HTTPException(404, "Site introuvable")
    if user.get("role") != "admin" and site.get("operator_id") != user.get("id"):
        raise HTTPException(403, "Accès refusé")
    force = bool((payload or {}).get("force"))
    from services.google_provisioning import provision_all
    out = await provision_all(site_id, force=force)
    return out


@router.post("/sites/{site_id}/google-provisioning/retry")
async def retry_site_google_provisioning(
    site_id: str,
    payload: dict,
    user: dict = Depends(get_current_user),
):
    """Retry sélectif sur un sous-ensemble de services.
    Body : `{"services": ["gsc","gmc","ads","ga4"]}`.
    """
    site = await db.sites.find_one({"id": site_id}, {"_id": 0, "id": 1, "operator_id": 1, "google_provisioning": 1})
    if not site:
        raise HTTPException(404, "Site introuvable")
    if user.get("role") != "admin" and site.get("operator_id") != user.get("id"):
        raise HTTPException(403, "Accès refusé")
    services = (payload or {}).get("services") or ["gsc", "gmc", "ads", "ga4"]
    valid = {"gsc", "gmc", "ads", "ga4"}
    services = [s for s in services if s in valid]
    if not services:
        raise HTTPException(400, "Liste de services vide ou invalide")
    # On force la re-exécution UNIQUEMENT pour les services demandés en
    # supprimant leurs entrées précédentes, puis on rappelle provision_all()
    # qui reprend là où c'est manquant.
    unset = {f"google_provisioning.{s}": "" for s in services}
    await db.sites.update_one({"id": site_id}, {"$unset": unset})
    from services.google_provisioning import provision_all
    out = await provision_all(site_id, force=False)
    return out

