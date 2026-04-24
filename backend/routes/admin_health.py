"""
Admin Health — Phase 3.

Endpoint unique `/api/admin/integrations/health` qui ping en parallèle les
10 intégrations externes utilisées par Altiaro et retourne un JSON normalisé
pour la page `/admin/integrations` du frontend.

Principes :
- Chaque ping a un timeout strict de 2 s (`httpx.Timeout`).
- Cache en mémoire, TTL 60 s par défaut — bypass via `?force=true`.
- `asyncio.gather(..., return_exceptions=True)` → un ping lent ne bloque pas les autres.
- Aucune clé / secret n'est renvoyée dans la réponse (uniquement des flags booléens).
- Protégé `require_admin`.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request

from deps import db, require_admin

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin/integrations", tags=["admin-health"])

# ------------------------------------------------------------------ #
# Cache                                                                #
# ------------------------------------------------------------------ #
_CACHE_TTL = 60  # seconds
_CACHE: dict[str, tuple[float, dict]] = {}


def _cached(key: str) -> dict | None:
    item = _CACHE.get(key)
    if not item:
        return None
    ts, res = item
    if (time.time() - ts) > _CACHE_TTL:
        return None
    return res


def _set_cache(key: str, result: dict) -> None:
    _CACHE[key] = (time.time(), result)


# ------------------------------------------------------------------ #
# Helpers                                                              #
# ------------------------------------------------------------------ #
PING_TIMEOUT_S = 2.0


def _result(
    key: str,
    name: str,
    *,
    status: str,
    message: str,
    connected: bool = False,
    requires_oauth: bool = False,
    configured_env: bool = False,
    details: dict | None = None,
    docs_url: str | None = None,
    actions: list[str] | None = None,
    duration_ms: int = 0,
) -> dict:
    return {
        "key": key,
        "name": name,
        "status": status,  # ok | warning | error | not_configured
        "message": message,
        "connected": bool(connected),
        "requires_oauth": bool(requires_oauth),
        "configured_env": bool(configured_env),
        "details": details or {},
        "docs_url": docs_url,
        "actions": actions or [],
        "last_checked": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "duration_ms": duration_ms,
    }


async def _run(coro):
    """Timebox un ping à 2 s, retourne (result_dict_or_None, exception_or_None)."""
    try:
        return await asyncio.wait_for(coro, timeout=PING_TIMEOUT_S), None
    except asyncio.TimeoutError:
        return None, "timeout"
    except Exception as e:
        logger.warning(f"[health] unexpected error in ping: {type(e).__name__}: {e}")
        return None, str(e)


# ==================================================================== #
# 10 pings                                                              #
# ==================================================================== #

async def _ping_emergent_llm() -> dict:
    t0 = time.perf_counter()
    key_env = os.environ.get("EMERGENT_LLM_KEY", "").strip()
    if not key_env:
        return _result(
            "emergent_llm", "Emergent LLM (Claude + Nano Banana)",
            status="not_configured",
            message="EMERGENT_LLM_KEY manquante dans .env",
            docs_url="https://emergent.sh (Profile → Universal Key)",
            actions=["configure"],
            duration_ms=int((time.perf_counter() - t0) * 1000),
        )
    # Lit le flag budget_exhausted depuis platform_settings (DB locale)
    doc = await db.platform_settings.find_one({"key": "llm_status"})
    last_error_at = (doc or {}).get("last_error_at")
    exhausted = bool((doc or {}).get("exhausted"))
    dur = int((time.perf_counter() - t0) * 1000)
    if exhausted:
        return _result(
            "emergent_llm", "Emergent LLM (Claude + Nano Banana)",
            status="error",
            message="Budget LLM épuisé — actualisez votre clé Emergent",
            connected=False,
            configured_env=True,
            details={"last_error_at": last_error_at, "exhausted": True},
            actions=["test", "reset"],
            duration_ms=dur,
        )
    return _result(
        "emergent_llm", "Emergent LLM (Claude + Nano Banana)",
        status="ok",
        message="LLM opérationnel · Claude 4.5 + Nano Banana prêts",
        connected=True,
        configured_env=True,
        details={"last_error_at": last_error_at},
        actions=["test"],
        duration_ms=dur,
    )


async def _ping_aliexpress() -> dict:
    t0 = time.perf_counter()
    app_key = os.environ.get("ALIEXPRESS_APP_KEY", "").strip()
    app_secret = os.environ.get("ALIEXPRESS_APP_SECRET", "").strip()
    if not (app_key and app_secret):
        return _result(
            "aliexpress", "AliExpress Dropshipping",
            status="not_configured",
            message="ALIEXPRESS_APP_KEY/SECRET manquants dans .env",
            requires_oauth=True,
            docs_url="https://portals.aliexpress.com (Open Platform)",
            actions=["configure"],
            duration_ms=int((time.perf_counter() - t0) * 1000),
        )
    doc = await db.platform_settings.find_one({"key": "aliexpress"}) or {}
    connected = bool(doc.get("refresh_token") or doc.get("access_token"))
    dur = int((time.perf_counter() - t0) * 1000)
    if not connected:
        return _result(
            "aliexpress", "AliExpress Dropshipping",
            status="warning",
            message="Configuré mais OAuth à finaliser · cliquez sur Connecter",
            connected=False,
            requires_oauth=True,
            configured_env=True,
            actions=["connect"],
            duration_ms=dur,
        )
    return _result(
        "aliexpress", "AliExpress Dropshipping",
        status="ok",
        message=f"Connecté · compte {doc.get('user_nick', 'AE')}",
        connected=True,
        requires_oauth=True,
        configured_env=True,
        details={
            "user_nick": doc.get("user_nick"),
            "expires_at": doc.get("expires_at"),
            "connected_at": doc.get("connected_at"),
        },
        actions=["test", "disconnect"],
        duration_ms=dur,
    )


async def _ping_cj() -> dict:
    t0 = time.perf_counter()
    api_key = os.environ.get("CJ_API_KEY", "").strip()
    if not api_key:
        return _result(
            "cj", "CJ Dropshipping",
            status="not_configured",
            message="CJ_API_KEY manquante dans .env",
            docs_url="https://developers.cjdropshipping.com (API Management)",
            actions=["configure"],
            duration_ms=int((time.perf_counter() - t0) * 1000),
        )
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(PING_TIMEOUT_S)) as client:
            # CJ uses 2-step auth : getAccessToken first, then CJ-Access-Token header.
            auth_resp = await client.post(
                "https://developers.cjdropshipping.com/api2.0/v1/authentication/getAccessToken",
                json={"apiKey": api_key},
            )
            if auth_resp.status_code != 200:
                return _result(
                    "cj", "CJ Dropshipping",
                    status="error",
                    message=f"CJ auth HTTP {auth_resp.status_code}",
                    configured_env=True,
                    actions=["retest", "configure"],
                    duration_ms=int((time.perf_counter() - t0) * 1000),
                )
            auth_data = auth_resp.json()
            if auth_data.get("result") is not True:
                return _result(
                    "cj", "CJ Dropshipping",
                    status="error",
                    message=f"Clé rejetée : {(auth_data.get('message') or 'erreur inconnue')[:60]}",
                    configured_env=True,
                    actions=["retest", "configure"],
                    duration_ms=int((time.perf_counter() - t0) * 1000),
                )
            token = (auth_data.get("data") or {}).get("accessToken")
            resp = await client.get(
                "https://developers.cjdropshipping.com/api2.0/v1/product/list",
                params={"pageSize": 1, "pageNum": 1},
                headers={"CJ-Access-Token": token},
            )
        dur = int((time.perf_counter() - t0) * 1000)
        if resp.status_code == 200:
            payload = resp.json()
            if payload.get("code") == 200 or payload.get("result") is True:
                total = (payload.get("data") or {}).get("total", 0)
                return _result(
                    "cj", "CJ Dropshipping",
                    status="ok",
                    message=f"Connecté · catalogue accessible ({total:,} produits)".replace(",", " "),
                    connected=True,
                    configured_env=True,
                    actions=["test"],
                    duration_ms=dur,
                )
            return _result(
                "cj", "CJ Dropshipping",
                status="error",
                message=f"Requête refusée : {(payload.get('message') or 'erreur inconnue')[:60]}",
                connected=False,
                configured_env=True,
                actions=["retest", "configure"],
                duration_ms=dur,
            )
        return _result(
            "cj", "CJ Dropshipping",
            status="error",
            message=f"CJ product/list HTTP {resp.status_code}",
            connected=False,
            configured_env=True,
            actions=["retest"],
            duration_ms=dur,
        )
    except httpx.TimeoutException:
        return _result(
            "cj", "CJ Dropshipping",
            status="error",
            message="Timeout après 2s",
            configured_env=True,
            actions=["retest"],
            duration_ms=int(PING_TIMEOUT_S * 1000),
        )


async def _ping_google_ads() -> dict:
    t0 = time.perf_counter()
    dev_token = os.environ.get("GOOGLE_ADS_DEVELOPER_TOKEN", "").strip()
    client_id = os.environ.get("GOOGLE_ADS_CLIENT_ID", "").strip()
    client_secret = os.environ.get("GOOGLE_ADS_CLIENT_SECRET", "").strip()
    configured = bool(dev_token)
    full_oauth = bool(dev_token and client_id and client_secret)
    if not configured:
        return _result(
            "google_ads", "Google Ads (Keyword Planner + Campaigns)",
            status="not_configured",
            message="GOOGLE_ADS_DEVELOPER_TOKEN manquant dans .env",
            requires_oauth=True,
            docs_url="https://ads.google.com → Tools → API Center",
            actions=["configure"],
            duration_ms=int((time.perf_counter() - t0) * 1000),
        )
    if not full_oauth:
        return _result(
            "google_ads", "Google Ads (Keyword Planner + Campaigns)",
            status="not_configured",
            message="Developer Token OK · manque GOOGLE_ADS_CLIENT_ID + SECRET (OAuth)",
            configured_env=False,
            requires_oauth=True,
            docs_url="https://console.cloud.google.com/apis/credentials",
            actions=["configure"],
            duration_ms=int((time.perf_counter() - t0) * 1000),
        )
    # Le callback Google Ads persiste les tokens dans `google_ads_credentials`
    # (pas dans `platform_settings.google_ads`). On lit donc la bonne source :
    # doc actif le plus récent avec refresh_token.
    doc = await db.google_ads_credentials.find_one(
        {"is_active": True, "refresh_token": {"$exists": True, "$nin": [None, ""]}},
        sort=[("updated_at", -1)],
    ) or {}
    connected = bool(doc.get("refresh_token"))
    dur = int((time.perf_counter() - t0) * 1000)
    if not connected:
        return _result(
            "google_ads", "Google Ads (Keyword Planner + Campaigns)",
            status="warning",
            message="Configuré mais OAuth à finaliser · cliquez sur Connecter",
            connected=False,
            requires_oauth=True,
            configured_env=True,
            actions=["connect"],
            duration_ms=dur,
        )
    # Schéma de google_ads_credentials : admin_user_id, refresh_token, scopes,
    # updated_at. Pas de preferred_customer_id ici → on fallback sur l'env.
    customer_id = (
        doc.get("preferred_customer_id")
        or doc.get("login_customer_id")
        or os.environ.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID", "").strip()
        or None
    )
    return _result(
        "google_ads", "Google Ads (Keyword Planner + Campaigns)",
        status="ok",
        message=f"Connecté · customer_id {customer_id or 'à sélectionner'}",
        connected=True,
        requires_oauth=True,
        configured_env=True,
        details={
            "customer_id": customer_id,
            "connected_at": doc.get("connected_at") or doc.get("updated_at"),
            "scopes": doc.get("scopes"),
        },
        actions=["test", "disconnect"],
        duration_ms=dur,
    )


async def _ping_gsc() -> dict:
    t0 = time.perf_counter()
    client_id = os.environ.get("GOOGLE_CLIENT_ID", "").strip()
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET", "").strip()
    if not (client_id and client_secret):
        return _result(
            "google_search_console", "Google Search Console",
            status="not_configured",
            message="GOOGLE_CLIENT_ID/SECRET manquants dans .env",
            requires_oauth=True,
            docs_url="/docs/GSC_SETUP.md",
            actions=["configure"],
            duration_ms=int((time.perf_counter() - t0) * 1000),
        )
    # GSC est scope site. On compte les sites qui ont un token GSC valide.
    connected_count = await db.sites.count_documents({
        "gsc_connected": True,
    })
    total_sites = await db.sites.count_documents({})
    dur = int((time.perf_counter() - t0) * 1000)
    if connected_count == 0:
        msg = "Configuré · aucun site n'a encore connecté GSC"
        if total_sites == 0:
            msg = "Configuré · attend qu'un site soit créé puis connecté"
        return _result(
            "google_search_console", "Google Search Console",
            status="warning",
            message=msg,
            connected=False,
            requires_oauth=True,
            configured_env=True,
            details={"sites_connected": 0, "sites_total": total_sites},
            docs_url="/docs/GSC_SETUP.md",
            actions=["docs"],
            duration_ms=dur,
        )
    return _result(
        "google_search_console", "Google Search Console",
        status="ok",
        message=f"Connecté sur {connected_count}/{total_sites} site(s)",
        connected=True,
        requires_oauth=True,
        configured_env=True,
        details={"sites_connected": connected_count, "sites_total": total_sites},
        actions=["test"],
        duration_ms=dur,
    )


async def _ping_google_merchant() -> dict:
    """Statut dynamique du Merchant Center, lu depuis platform_settings.merchant.

    Étapes résolues par ordre de priorité :
    - GOOGLE_CLIENT_ID/SECRET absents → not_configured
    - OAuth pas finalisé (pas de refresh_token) → warning
    - merchant_id manquant (ni en DB ni en env) → warning
    - last_sync_status == "error" → error
    - last_sync_status == "partial" → warning
    - Tout est OK → ok
    """
    t0 = time.perf_counter()
    cid = os.environ.get("GOOGLE_CLIENT_ID", "").strip()
    secret = os.environ.get("GOOGLE_CLIENT_SECRET", "").strip()
    configured_env = bool(cid and secret)

    if not configured_env:
        return _result(
            "google_merchant_center", "Google Merchant Center",
            status="not_configured",
            message="GOOGLE_CLIENT_ID/SECRET manquants dans .env",
            requires_oauth=True,
            configured_env=False,
            docs_url="https://merchants.google.com",
            actions=["configure"],
            duration_ms=int((time.perf_counter() - t0) * 1000),
        )

    try:
        settings = await db.platform_settings.find_one({"key": "merchant"}) or {}
    except Exception as e:
        return _result(
            "google_merchant_center", "Google Merchant Center",
            status="error",
            message=f"Erreur DB : {str(e)[:50]}",
            requires_oauth=True,
            configured_env=True,
            docs_url="https://merchants.google.com",
            actions=["test"],
            duration_ms=int((time.perf_counter() - t0) * 1000),
        )

    refresh_token = settings.get("refresh_token")
    merchant_id = settings.get("merchant_id") or os.environ.get("MERCHANT_ID", "").strip()
    last_sync_at = settings.get("last_sync_at")
    last_sync_status = settings.get("last_sync_status")
    connected_at = settings.get("connected_at")

    details = {
        "connected_at": connected_at,
        "last_sync_at": last_sync_at,
        "last_sync_status": last_sync_status,
        "merchant_id": merchant_id or None,
    }

    if not refresh_token:
        return _result(
            "google_merchant_center", "Google Merchant Center",
            status="warning",
            message="OAuth à finaliser · cliquez sur Connecter",
            requires_oauth=True,
            configured_env=True,
            details=details,
            docs_url="https://merchants.google.com",
            actions=["connect"],
            duration_ms=int((time.perf_counter() - t0) * 1000),
        )

    if not merchant_id:
        return _result(
            "google_merchant_center", "Google Merchant Center",
            status="warning",
            message="Connecté · renseignez le Merchant ID",
            connected=True,
            requires_oauth=True,
            configured_env=True,
            details=details,
            docs_url="https://merchants.google.com",
            actions=["configure"],
            duration_ms=int((time.perf_counter() - t0) * 1000),
        )

    if last_sync_status == "error":
        return _result(
            "google_merchant_center", "Google Merchant Center",
            status="error",
            message=f"Dernière sync en échec · Merchant ID {merchant_id}",
            connected=True,
            requires_oauth=True,
            configured_env=True,
            details=details,
            docs_url="https://merchants.google.com",
            actions=["test"],
            duration_ms=int((time.perf_counter() - t0) * 1000),
        )

    if last_sync_status == "partial":
        return _result(
            "google_merchant_center", "Google Merchant Center",
            status="warning",
            message="Sync partielle · voir détails par site",
            connected=True,
            requires_oauth=True,
            configured_env=True,
            details=details,
            docs_url="https://merchants.google.com",
            actions=["test"],
            duration_ms=int((time.perf_counter() - t0) * 1000),
        )

    if last_sync_at:
        msg = f"Connecté · Merchant ID {merchant_id} · sync OK"
    else:
        msg = f"Connecté · Merchant ID {merchant_id} · prêt à synchroniser"
    return _result(
        "google_merchant_center", "Google Merchant Center",
        status="ok",
        message=msg,
        connected=True,
        requires_oauth=True,
        configured_env=True,
        details=details,
        actions=["test"],
        duration_ms=int((time.perf_counter() - t0) * 1000),
    )


async def _ping_mollie() -> dict:
    t0 = time.perf_counter()
    mode = os.environ.get("MOLLIE_MODE", "test").strip().lower()
    key = os.environ.get(
        "MOLLIE_TEST_KEY" if mode == "test" else "MOLLIE_LIVE_KEY", ""
    ).strip()
    if not key:
        return _result(
            "mollie", "Mollie (paiements)",
            status="not_configured",
            message=f"MOLLIE_{mode.upper()}_KEY manquante dans .env",
            docs_url="https://my.mollie.com/dashboard/developers/api-keys",
            actions=["configure"],
            duration_ms=int((time.perf_counter() - t0) * 1000),
        )
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(PING_TIMEOUT_S)) as client:
            resp = await client.get(
                "https://api.mollie.com/v2/methods",
                params={"amount[value]": "100.00", "amount[currency]": "EUR"},
                headers={"Authorization": f"Bearer {key}"},
            )
        dur = int((time.perf_counter() - t0) * 1000)
        if resp.status_code == 200:
            data = resp.json()
            methods = [m["id"] for m in (data.get("_embedded") or {}).get("methods", [])]
            label = "test" if mode == "test" else "LIVE"
            return _result(
                "mollie", "Mollie (paiements)",
                status="ok",
                message=f"Mode {label} · {len(methods)} méthode(s) actives : " + ", ".join(methods[:3]),
                connected=True,
                configured_env=True,
                details={"mode": mode, "methods": methods},
                actions=["test"],
                duration_ms=dur,
            )
        return _result(
            "mollie", "Mollie (paiements)",
            status="error",
            message=f"Clé rejetée · HTTP {resp.status_code}",
            configured_env=True,
            actions=["retest", "configure"],
            duration_ms=dur,
        )
    except httpx.TimeoutException:
        return _result(
            "mollie", "Mollie (paiements)",
            status="error",
            message="Timeout après 2s",
            configured_env=True,
            actions=["retest"],
            duration_ms=int(PING_TIMEOUT_S * 1000),
        )


async def _ping_resend() -> dict:
    t0 = time.perf_counter()
    key = os.environ.get("RESEND_API_KEY", "").strip()
    if not key:
        return _result(
            "resend", "Resend (emails transactionnels)",
            status="not_configured",
            message="RESEND_API_KEY manquante dans .env",
            docs_url="https://resend.com/api-keys",
            actions=["configure"],
            duration_ms=int((time.perf_counter() - t0) * 1000),
        )
    from_addr = os.environ.get("RESEND_DEFAULT_FROM", "").strip()
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(PING_TIMEOUT_S)) as client:
            resp = await client.get(
                "https://api.resend.com/api-keys",
                headers={"Authorization": f"Bearer {key}"},
            )
        dur = int((time.perf_counter() - t0) * 1000)
        # 200 = clé full-access · 401 "restricted_api_key" = clé restricted-send = auth OK
        is_restricted = resp.status_code == 401 and "restricted" in resp.text.lower()
        auth_ok = resp.status_code == 200 or is_restricted
        if not auth_ok:
            return _result(
                "resend", "Resend (emails transactionnels)",
                status="error",
                message=f"Clé rejetée · HTTP {resp.status_code}",
                configured_env=True,
                actions=["retest", "configure"],
                duration_ms=dur,
            )
        # Si from = onboarding@resend.dev → sandbox
        sandbox = from_addr.endswith("@resend.dev")
        if sandbox:
            return _result(
                "resend", "Resend (emails transactionnels)",
                status="warning",
                message="Sandbox actif · vérifiez un domaine pour envoyer aux clients",
                connected=True,
                configured_env=True,
                details={"from": from_addr, "sandbox": True, "key_restricted": is_restricted},
                docs_url="https://resend.com/domains",
                actions=["test", "docs"],
                duration_ms=dur,
            )
        return _result(
            "resend", "Resend (emails transactionnels)",
            status="ok",
            message=f"Connecté · expéditeur {from_addr or '(non défini)'}",
            connected=True,
            configured_env=True,
            details={"from": from_addr, "key_restricted": is_restricted},
            actions=["test"],
            duration_ms=dur,
        )
    except httpx.TimeoutException:
        return _result(
            "resend", "Resend (emails transactionnels)",
            status="error",
            message="Timeout après 2s",
            configured_env=True,
            actions=["retest"],
            duration_ms=int(PING_TIMEOUT_S * 1000),
        )


async def _ping_ovh() -> dict:
    t0 = time.perf_counter()
    app_key = os.environ.get("OVH_APP_KEY", "").strip()
    app_secret = os.environ.get("OVH_APP_SECRET", "").strip()
    consumer = os.environ.get("OVH_CONSUMER_KEY", "").strip()
    if not (app_key and app_secret and consumer):
        return _result(
            "ovh", "OVH (domaines custom)",
            status="not_configured",
            message="OVH_APP_KEY / SECRET / CONSUMER_KEY manquants dans .env",
            docs_url="https://eu.api.ovh.com/createToken/",
            actions=["configure"],
            duration_ms=int((time.perf_counter() - t0) * 1000),
        )
    try:
        # GET /me via le client python ovh (sync) dans un thread
        def _probe() -> dict:
            import ovh
            cli = ovh.Client(
                endpoint=os.environ.get("OVH_ENDPOINT", "ovh-eu"),
                application_key=app_key,
                application_secret=app_secret,
                consumer_key=consumer,
            )
            me = cli.get("/me") or {}
            domains = cli.get("/domain") or []
            return {"nichandle": me.get("nichandle"), "state": me.get("state"), "domains_count": len(domains)}

        res = await asyncio.to_thread(_probe)
        dur = int((time.perf_counter() - t0) * 1000)
        platform_ip_ok = bool(os.environ.get("PLATFORM_SITE_IP", "").strip())
        msg = f"Connecté · compte {res['nichandle']} · {res['domains_count']} domaine(s)"
        if not platform_ip_ok:
            msg += " · PLATFORM_SITE_IP manquante pour DNS auto"
        status = "ok" if platform_ip_ok else "warning"
        return _result(
            "ovh", "OVH (domaines custom)",
            status=status,
            message=msg,
            connected=True,
            configured_env=True,
            details={**res, "platform_ip_configured": platform_ip_ok},
            actions=["test"],
            duration_ms=dur,
        )
    except Exception as e:
        return _result(
            "ovh", "OVH (domaines custom)",
            status="error",
            message=f"Erreur OVH : {str(e)[:60]}",
            configured_env=True,
            actions=["retest"],
            duration_ms=int((time.perf_counter() - t0) * 1000),
        )


async def _ping_indexnow() -> dict:
    t0 = time.perf_counter()
    key = os.environ.get("INDEXNOW_KEY", "").strip()
    if not key or len(key) < 8:
        return _result(
            "indexnow", "IndexNow (Bing / Yandex / Naver / Seznam)",
            status="not_configured",
            message="INDEXNOW_KEY manquante ou trop courte — générer avec `openssl rand -hex 16`",
            docs_url="https://www.bing.com/indexnow",
            actions=["configure"],
            duration_ms=int((time.perf_counter() - t0) * 1000),
        )
    dur = int((time.perf_counter() - t0) * 1000)
    return _result(
        "indexnow", "IndexNow (Bing / Yandex / Naver / Seznam)",
        status="ok",
        message=f"Clé servie sur /api/public/indexnow-{key[:6]}…{key[-4:]}.txt",
        connected=True,
        configured_env=True,
        details={"key_length": len(key)},
        actions=["test"],
        duration_ms=dur,
    )


# ==================================================================== #
# Registry                                                              #
# ==================================================================== #
_PING_REGISTRY = {
    "emergent_llm": _ping_emergent_llm,
    "aliexpress": _ping_aliexpress,
    "cj": _ping_cj,
    "google_ads": _ping_google_ads,
    "google_search_console": _ping_gsc,
    "google_merchant_center": _ping_google_merchant,
    "mollie": _ping_mollie,
    "resend": _ping_resend,
    "ovh": _ping_ovh,
    "indexnow": _ping_indexnow,
}


async def _run_one_cached(key: str, force: bool = False) -> dict:
    if not force:
        cached = _cached(key)
        if cached is not None:
            return {**cached, "cached": True}
    fn = _PING_REGISTRY[key]
    result, err = await _run(fn())
    if result is None:
        result = _result(
            key, key.replace("_", " ").title(),
            status="error",
            message=f"Ping failed : {err or 'timeout'}",
            duration_ms=int(PING_TIMEOUT_S * 1000),
        )
    logger.info(f"[health] {key}: {result['status']} in {result.get('duration_ms', 0)}ms")
    _set_cache(key, result)
    return {**result, "cached": False}


# ==================================================================== #
# Routes                                                                #
# ==================================================================== #

@router.get("/health")
async def get_health(force: bool = False, _admin: dict = Depends(require_admin)) -> dict:
    """Ping les 10 intégrations en parallèle et renvoie un snapshot normalisé."""
    t0 = time.perf_counter()
    keys = list(_PING_REGISTRY.keys())
    results = await asyncio.gather(
        *(_run_one_cached(k, force=force) for k in keys),
        return_exceptions=True,
    )
    integrations: list[dict] = []
    for k, r in zip(keys, results):
        if isinstance(r, Exception):
            integrations.append(_result(
                k, k,
                status="error",
                message=f"Exception {type(r).__name__} : {str(r)[:60]}",
                duration_ms=int(PING_TIMEOUT_S * 1000),
            ))
        else:
            integrations.append(r)
    total_dur = int((time.perf_counter() - t0) * 1000)
    return {
        "checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "duration_ms": total_dur,
        "integrations": integrations,
    }


@router.get("/{key}/ping")
async def ping_one(key: str, force: bool = True, _admin: dict = Depends(require_admin)) -> dict:
    if key not in _PING_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Unknown integration key: {key}")
    return await _run_one_cached(key, force=force)


@router.post("/{key}/connect")
async def connect_one(key: str, request: Request, _admin: dict = Depends(require_admin)) -> dict:
    """
    Dispatcher du flow 'Connecter'. Retourne soit :
    - `{"authorize_url": "..."}` pour les intégrations OAuth (popup côté frontend)
    - `{"docs_url": "..."}` pour les intégrations à configurer dans .env
    """
    if key not in _PING_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Unknown integration key: {key}")

    # Dispatch par key
    if key == "aliexpress":
        # Réutilise l'endpoint existant (lit env + génère URL OAuth signée)
        from routes.aliexpress import get_authorize_url_admin
        return await get_authorize_url_admin(request, _admin)
    if key == "google_ads":
        # Délégation à l'endpoint dédié (PKCE + state persisté en DB).
        # Reconstruire l'URL à la main ici cassait le callback (pas de state,
        # pas de code_verifier → fetch_token échouait).
        from routes.google_ads import oauth_start as ads_oauth_start
        resp = await ads_oauth_start(_admin)  # {"authorization_url": ..., "state": ...}
        url = resp.get("authorization_url") or resp.get("authorize_url")
        if not url:
            raise HTTPException(status_code=500, detail="Google Ads OAuth start n'a pas renvoyé d'URL")
        return {"authorize_url": url, "state": resp.get("state")}
    if key == "google_search_console":
        return {
            "docs_url": "/docs/GSC_SETUP.md",
            "message": "GSC se connecte site par site depuis le cockpit /sites/{id}/seo (panel GSC). Voir /docs/GSC_SETUP.md.",
        }
    if key == "google_merchant_center":
        # Délégation à l'endpoint merchant qui gère le state CSRF
        # + persiste correctement les tokens à l'étape callback.
        from routes.merchant import oauth_start as merchant_oauth_start
        resp = await merchant_oauth_start(_admin)
        # merchant renvoie déjà {"authorize_url": ..., "state": ...}
        return resp

    # Tout le reste : configurer dans .env, pas d'OAuth plateforme
    docs_map = {
        "emergent_llm": "https://emergent.sh (Profile → Universal Key)",
        "cj": "https://developers.cjdropshipping.com",
        "mollie": "https://my.mollie.com/dashboard/developers/api-keys",
        "resend": "https://resend.com/api-keys",
        "ovh": "https://eu.api.ovh.com/createToken/",
        "indexnow": "https://www.bing.com/indexnow",
    }
    return {
        "docs_url": docs_map.get(key, "/README.md"),
        "message": "Configurez la clé dans /app/backend/.env puis redémarrez le backend.",
    }
