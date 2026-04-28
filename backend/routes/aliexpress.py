"""
AliExpress Dropshipping OAuth + API client.

Flow :
  1. Concepteur clicks "Connecter AliExpress" in cockpit
  2. Backend returns an authorize URL with state=site_id (HMAC-signed)
  3. Merchant authorizes, AliExpress redirects to /api/aliexpress/oauth/callback
  4. Backend exchanges the code for access_token + refresh_token
  5. Tokens stored in `db.sites.design.aliexpress = {access_token, refresh_token, expires_at}`

Product search / import / order placement / tracking live in this file but
are gated behind the token helper. The exact API method names are pre-wired
from the AliExpress Dropshipping playbook but MUST be confirmed against the
sandbox the first time the app talks to AliExpress.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import os
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel

from deps import db, get_current_user, _check_site_access

logger = logging.getLogger("conceptfactory.aliexpress")
router = APIRouter()

APP_KEY = os.environ.get("ALIEXPRESS_APP_KEY", "")
APP_SECRET = os.environ.get("ALIEXPRESS_APP_SECRET", "")
CALLBACK_URL = os.environ.get(
    "ALIEXPRESS_CALLBACK_URL",
    "https://altiaro.com/api/aliexpress/oauth/callback",
)

AUTHORIZE_URL = "https://api-sg.aliexpress.com/oauth/authorize"
# Standard OAuth2 token endpoint — separate domain from the API
OAUTH_TOKEN_URL = "https://oauth.aliexpress.com/token"
# Fallback : signed REST endpoint (rarely needed since OAuth2 is canonical)
TOKEN_URL = "https://api-sg.aliexpress.com/rest/auth/token/create"
REFRESH_URL = "https://api-sg.aliexpress.com/rest/auth/token/refresh"
SYNC_API_URL = "https://api-sg.aliexpress.com/sync"


async def _get_platform_settings() -> dict:
    """Platform-level AliExpress connection (single Altiaro account, all sites inherit)."""
    doc = await db.platform_settings.find_one({"key": "aliexpress"}, {"_id": 0})
    return doc or {}


async def _set_platform_settings(patch: dict) -> None:
    await db.platform_settings.update_one(
        {"key": "aliexpress"}, {"$set": patch}, upsert=True
    )


# =====================================================================
# OAuth — authorize + callback
# =====================================================================
# State = base64url(site_id | origin | ts) + "." + hmac_short
# origin = URL of the Altiaro environment that initiated the flow
# (altiaro.com in production, *.preview.emergentagent.com in dev).
# This lets the single AliExpress callback URL relay the code back to the
# right environment transparently — NO need to register multiple callbacks.
import base64 as _b64


def _sign_state(site_id: str, origin: str) -> str:
    raw = f"{site_id}|{origin}|{int(time.time())}"
    payload = _b64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")
    mac = hmac.new(APP_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()[:16]
    return f"{payload}.{mac}"


def _verify_state(state: str) -> Optional[tuple]:
    """Returns (site_id, origin) or None."""
    try:
        payload, mac = state.split(".", 1)
        expected = hmac.new(APP_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()[:16]
        if not hmac.compare_digest(mac, expected):
            return None
        # Add back padding for b64 decode
        pad = "=" * (-len(payload) % 4)
        raw = _b64.urlsafe_b64decode(payload + pad).decode()
        site_id, origin, ts = raw.split("|", 2)
        if int(time.time()) - int(ts) > 900:  # 15 min window
            return None
        return (site_id, origin)
    except Exception:
        return None


def _current_origin(request: Request) -> str:
    """Infer the public origin of THIS server (preview vs prod)."""
    # Trust x-forwarded-proto/host when behind an ingress
    proto = request.headers.get("x-forwarded-proto") or request.url.scheme
    host = request.headers.get("x-forwarded-host") or request.headers.get("host") or request.url.hostname
    return f"{proto}://{host}".rstrip("/")


@router.get("/aliexpress/oauth/callback")
async def aliexpress_oauth_callback(
    request: Request,
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    error_description: Optional[str] = None,
):
    """
    Registered in the AliExpress App Console.
    Smart relay : if the state says this OAuth was initiated from another Altiaro
    environment (e.g. preview), we redirect the code+state there so that
    environment can do the token exchange against its own DB.
    Otherwise we process locally.
    """
    now = datetime.now(timezone.utc)
    try:
        await db.aliexpress_oauth_callbacks.insert_one({
            "received_at": now, "code": code, "state": state,
            "error": error, "error_description": error_description,
            "ip": (request.headers.get("x-forwarded-for") or (request.client.host if request.client else "")),
            "user_agent": request.headers.get("user-agent", ""),
            "handled_by": _current_origin(request),
        })
    except Exception:
        logger.exception("[aliexpress] persist callback failed")

    if error:
        logger.warning(f"[aliexpress] OAuth error : {error} — {error_description}")
        return HTMLResponse(_page(title="Autorisation refusée", body=f"<code>{error}</code> — {error_description or ''}", ok=False))

    if not code:
        return HTMLResponse(_page(title="Endpoint OAuth Altiaro × AliExpress", body="Ce point d'entrée est réservé au flow OAuth initié depuis votre cockpit."))

    parsed = _verify_state(state or "")
    if not parsed:
        return HTMLResponse(_page(title="Lien invalide ou expiré", body="Relancez la connexion depuis votre cockpit Altiaro.", ok=False))
    site_id, origin = parsed
    here = _current_origin(request)

    # If the OAuth was initiated from a different Altiaro environment, relay there.
    if origin and origin != here:
        logger.info(f"[aliexpress] relaying OAuth from {here} → {origin}")
        params = urlencode({"code": code, "state": state})
        return RedirectResponse(
            url=f"{origin}/api/aliexpress/oauth/relay?{params}",
            status_code=302,
        )

    return await _finalize_oauth(site_id, code)


@router.get("/aliexpress/oauth/relay")
async def aliexpress_oauth_relay(
    request: Request,
    code: str,
    state: str,
):
    """
    Endpoint that receives a relayed OAuth code from the 'master' callback on
    altiaro.com. Only accepts requests whose state verifies to THIS origin.
    """
    parsed = _verify_state(state)
    if not parsed:
        return HTMLResponse(_page(title="Lien invalide ou expiré", body="Relancez la connexion depuis votre cockpit Altiaro.", ok=False))
    site_id, origin = parsed
    here = _current_origin(request)
    if origin != here:
        logger.warning(f"[aliexpress] relay rejected : state origin {origin} != here {here}")
        return HTMLResponse(_page(title="Environnement incorrect", body="Ce lien d'autorisation n'appartient pas à cet environnement.", ok=False))
    return await _finalize_oauth(site_id, code)


async def _finalize_oauth(site_id: str, code: str) -> HTMLResponse:
    """
    Platform-level OAuth finalization.
    We ignore `site_id` in the sense that tokens are stored globally (on
    `db.platform_settings.key=aliexpress`) — every Altiaro store inherits them.
    The site_id is only used to attribute who initiated the connection.
    """
    try:
        token_payload = await _exchange_code_for_token(code)
    except Exception as e:
        logger.exception("[aliexpress] token exchange failed")
        return HTMLResponse(_page(title="Échec de la connexion", body=f"Erreur lors de l'échange du code : {str(e)[:200]}", ok=False))

    # AliExpress may wrap the response under varying keys — unwrap defensively
    for wrapper in ("aliexpress_system_oauth2_token", "auth_token_create_response", "result", "data"):
        if wrapper in token_payload and isinstance(token_payload[wrapper], dict):
            inner = token_payload[wrapper]
            # Merge: outer keys stay, inner overrides
            merged = {**token_payload, **inner}
            token_payload = merged
            break

    access_token = token_payload.get("access_token")
    if not access_token:
        logger.error(f"[aliexpress] token response missing access_token — raw keys: {list(token_payload.keys())}")
        try:
            await db.aliexpress_oauth_callbacks.insert_one({
                "received_at": datetime.now(timezone.utc),
                "stage": "token_exchange_missing_access_token",
                "raw_response_keys": list(token_payload.keys()),
                "raw_response_preview": {k: str(v)[:200] for k, v in token_payload.items()},
            })
        except Exception:
            pass
        return HTMLResponse(_page(
            title="Réponse AliExpress incomplète",
            body=f"La réponse AliExpress ne contient pas d'access_token. Clés reçues : <code>{', '.join(token_payload.keys())}</code>. Cette info a été loggée — je peux corriger en 2 min.",
            ok=False,
        ))

    now = datetime.now(timezone.utc)
    expires_in = int(token_payload.get("expires_in") or 172800)
    expires_at = now + timedelta(seconds=expires_in)

    # refresh_token_valid_time (AliExpress) = absolute Unix timestamp in **milliseconds**.
    # refresh_expires_in = duration in seconds. Handle both safely.
    refresh_at = None
    rtvt = token_payload.get("refresh_token_valid_time")
    rei = token_payload.get("refresh_expires_in")
    try:
        if rtvt:
            ms = int(rtvt)
            # If the value is >10^12 it's ms ; if 10^9-10^11 it's seconds.
            ts_s = ms / 1000 if ms > 1e12 else ms
            refresh_at = datetime.fromtimestamp(ts_s, tz=timezone.utc)
        elif rei:
            refresh_at = now + timedelta(seconds=int(rei))
        else:
            refresh_at = now + timedelta(days=365)
    except (ValueError, OverflowError, OSError):
        refresh_at = now + timedelta(days=365)

    await _set_platform_settings({
        "key": "aliexpress",
        "connected": True,
        "access_token": access_token,
        "refresh_token": token_payload.get("refresh_token"),
        "expires_at": expires_at.isoformat(),
        "refresh_expires_at": refresh_at.isoformat(),
        "user_id": token_payload.get("user_id") or token_payload.get("account_id") or "",
        "user_nick": token_payload.get("user_nick") or token_payload.get("seller_id") or token_payload.get("account") or "",
        "connected_at": now.isoformat(),
        "connected_by_site_id": site_id,
        "last_refreshed_at": None,
    })
    logger.info(f"[aliexpress] PLATFORM connected (user_id={token_payload.get('user_id')} by site={site_id})")

    return HTMLResponse(_page(
        title="Connexion AliExpress confirmée",
        body="La plateforme Altiaro est maintenant liée à votre compte AliExpress Dropshipping. Tous les sites en bénéficient. Vous pouvez fermer cette fenêtre.",
        ok=True,
    ))


# =====================================================================
# Admin-only status + disconnect (platform-level)
# =====================================================================
def _require_admin(user):
    if user.get("role") != "admin":
        raise HTTPException(403, "Admin uniquement.")


@router.get("/admin/aliexpress/status")
async def aliexpress_status_admin(user=Depends(get_current_user)):
    _require_admin(user)
    pl = await _get_platform_settings()
    return {
        "connected": bool(pl.get("connected") and pl.get("access_token")),
        "user_nick": pl.get("user_nick") or "",
        "connected_at": pl.get("connected_at"),
        "expires_at": pl.get("expires_at"),
        "last_refreshed_at": pl.get("last_refreshed_at"),
        "configured_server_side": bool(APP_KEY and APP_SECRET),
    }


@router.post("/admin/aliexpress/disconnect")
async def aliexpress_disconnect_admin(user=Depends(get_current_user)):
    _require_admin(user)
    await _set_platform_settings({
        "connected": False,
        "access_token": None,
        "refresh_token": None,
        "disconnected_at": datetime.now(timezone.utc).isoformat(),
    })
    return {"status": "ok"}


@router.get("/admin/aliexpress/debug")
async def aliexpress_debug(user=Depends(get_current_user)):
    """Last OAuth callbacks + current platform settings (tokens REDACTED)."""
    _require_admin(user)
    pl = await _get_platform_settings()
    safe_pl = {k: v for k, v in (pl or {}).items() if k not in {"access_token", "refresh_token"}}
    safe_pl["has_access_token"] = bool((pl or {}).get("access_token"))
    safe_pl["has_refresh_token"] = bool((pl or {}).get("refresh_token"))
    cbs = await db.aliexpress_oauth_callbacks.find({}, {"_id": 0, "code": 0}).sort("received_at", -1).to_list(10)
    for cb in cbs:
        if isinstance(cb.get("received_at"), datetime):
            cb["received_at"] = cb["received_at"].isoformat()
    return {"platform_settings": safe_pl, "callbacks": cbs}


@router.get("/admin/aliexpress/authorize-url")
async def get_authorize_url_admin(request: Request, user=Depends(get_current_user)):
    """Admin-triggered OAuth — initiated from /admin/integrations page."""
    _require_admin(user)
    if not APP_KEY:
        raise HTTPException(503, "Intégration AliExpress non configurée côté serveur.")
    origin = _current_origin(request)
    # Encode a neutral site_id since this is platform-level
    state = _sign_state("_admin_", origin)
    params = {
        "response_type": "code",
        "client_id": APP_KEY,
        "redirect_uri": CALLBACK_URL,
        "state": state,
        "sp": "ae",
    }
    return {"authorize_url": f"{AUTHORIZE_URL}?{urlencode(params)}", "state": state, "origin": origin}


# =====================================================================
# Token helpers (platform-level)
# =====================================================================
async def _exchange_code_for_token(code: str) -> dict:
    """
    Exchange OAuth code → access_token via the AliExpress signed REST endpoint.
    Minimal params — AliExpress is strict about extra fields.
    """
    params = {"code": code}
    try:
        data = await _signed_post(TOKEN_URL, params, need_access_token=False)
    except HTTPException as he:
        # _signed_post raises HTTPException with detail being the error dict — surface it
        try:
            await db.aliexpress_oauth_callbacks.insert_one({
                "received_at": datetime.now(timezone.utc),
                "stage": "token_exchange_http_exception",
                "detail": str(he.detail)[:500],
            })
        except Exception:
            pass
        raise
    # Persist raw for debug
    try:
        await db.aliexpress_oauth_callbacks.insert_one({
            "received_at": datetime.now(timezone.utc),
            "stage": "rest_token_response",
            "raw_keys": list(data.keys()) if isinstance(data, dict) else [],
            "raw_preview": {k: str(v)[:300] for k, v in data.items()} if isinstance(data, dict) else str(data)[:500],
        })
    except Exception:
        pass
    return data


async def _mark_disconnected(reason: str) -> None:
    """Phase 2.7.4 — when AE rejects access OR refresh tokens, flip the
    `connected` flag to False so the frontend can display a clear
    "Reconnecter AliExpress" CTA instead of opaque 502 errors."""
    await _set_platform_settings({
        "connected": False,
        "last_error": reason,
        "disconnected_at": datetime.now(timezone.utc).isoformat(),
    })


async def _refresh_access_token() -> dict:
    pl = await _get_platform_settings()
    refresh_token = pl.get("refresh_token")
    if not refresh_token:
        raise HTTPException(401, "AE_RECONNECT_REQUIRED: AliExpress non connecté. Reconnectez via Admin → Intégrations.")
    try:
        resp = await _signed_post(REFRESH_URL, {"refresh_token": refresh_token}, need_access_token=False)
    except HTTPException as e:
        # AliExpress 502 with IllegalRefreshToken → mark disconnected and surface a clean 401
        msg = (e.detail or "") if isinstance(e.detail, str) else str(e.detail or "")
        if "IllegalRefreshToken" in msg or "InvalidRefreshToken" in msg or "expired" in msg.lower():
            await _mark_disconnected("refresh_token_expired")
            raise HTTPException(401, "AE_RECONNECT_REQUIRED: refresh_token expiré. Reconnectez AliExpress via Admin → Intégrations.")
        raise
    if not resp.get("access_token"):
        await _mark_disconnected("refresh_no_access_token")
        raise HTTPException(401, f"AE_RECONNECT_REQUIRED: refresh AliExpress sans access_token ({resp}).")
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(seconds=int(resp.get("expires_in") or 86400))
    refresh_expires_at = now + timedelta(seconds=int(resp.get("refresh_expires_in") or 172800))
    await _set_platform_settings({
        "access_token": resp.get("access_token"),
        "refresh_token": resp.get("refresh_token") or refresh_token,
        "expires_at": expires_at.isoformat(),
        "refresh_expires_at": refresh_expires_at.isoformat(),
        "last_refreshed_at": now.isoformat(),
        "connected": True,
        "last_error": None,
    })
    return resp


async def _get_valid_access_token(site_id: Optional[str] = None) -> str:
    """
    Returns a valid platform-level AliExpress access token. `site_id` is kept
    as a parameter for backward compat but the token is global.

    Phase 2.7.4 — if the token is expired AND the refresh fails, surface a
    401 AE_RECONNECT_REQUIRED so the frontend can show the reconnect banner.
    """
    pl = await _get_platform_settings()
    token = pl.get("access_token")
    if not token or pl.get("connected") is False:
        raise HTTPException(401, "AE_RECONNECT_REQUIRED: AliExpress non connecté. Reconnectez via Admin → Intégrations.")
    expires_at = pl.get("expires_at")
    if expires_at:
        try:
            dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            if dt < (datetime.now(timezone.utc) + timedelta(minutes=5)):
                resp = await _refresh_access_token()
                return resp.get("access_token")
        except HTTPException:
            raise
        except Exception:
            pass
    return token


# =====================================================================
# AliExpress signature (SHA256) + signed POST helper
# =====================================================================
def _sign_params(params: dict, secret: str, path: str = "") -> str:
    """
    AliExpress signature (system/REST APIs) :
      concat = "".join(sorted(k+v))
      base   = path + concat   (path is included for /rest/* endpoints)
      sign   = HMAC-SHA256(secret, base) hex upper
    """
    concat = "".join(f"{k}{v}" for k, v in sorted(params.items()) if v is not None)
    base = (path or "") + concat
    return hmac.new(secret.encode(), base.encode(), hashlib.sha256).hexdigest().upper()


def _extract_path_for_signing(url: str) -> str:
    """
    For REST endpoints (/rest/...), AliExpress requires the path to be
    prepended to the signature base string. For the /sync endpoint, the path
    is NOT included.
    """
    from urllib.parse import urlparse
    path = urlparse(url).path or ""
    if path.startswith("/rest"):
        return path[len("/rest"):]  # e.g. "/auth/token/create"
    return ""  # /sync → no path


async def _signed_post(url: str, biz_params: dict, need_access_token: bool = True, site_id: Optional[str] = None, _retried: bool = False) -> dict:
    """Common signed request helper for AliExpress REST/SYNC APIs.

    Phase 2.7.4 — if AE returns IllegalAccessToken (token revoked or invalidated
    server-side BEFORE our local `expires_at`), we proactively refresh once
    and retry. If the refresh itself fails, _refresh_access_token() will
    flip `connected:false` and raise 401 AE_RECONNECT_REQUIRED.
    """
    if not APP_KEY or not APP_SECRET:
        raise HTTPException(503, "Intégration AliExpress non configurée côté serveur.")
    params = dict(biz_params)
    params["app_key"] = APP_KEY
    params["sign_method"] = "sha256"
    params["timestamp"] = str(int(time.time() * 1000))
    if need_access_token:
        params["session"] = await _get_valid_access_token(site_id)
    path = _extract_path_for_signing(url)
    params["sign"] = _sign_params(params, APP_SECRET, path=path)
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(url, data=params)
        r.raise_for_status()
        data = r.json()
    if isinstance(data, dict) and (data.get("error_response") or data.get("code") in {"401", "15"}):
        # Detect server-side token invalidation and retry once after refresh.
        err = data.get("error_response") or data
        err_code = (err.get("code") or "")
        err_msg  = (err.get("msg") or err.get("message") or "")
        if (
            need_access_token
            and not _retried
            and ("IllegalAccessToken" in err_code or "InvalidAccessToken" in err_msg or "expired" in err_msg.lower())
        ):
            try:
                await _refresh_access_token()
            except HTTPException:
                # _refresh_access_token already mapped this to a clean 401.
                raise
            return await _signed_post(url, biz_params, need_access_token=True, site_id=site_id, _retried=True)
        raise HTTPException(502, f"AliExpress : {data}")
    return data


# =====================================================================
# NEXT STEP — Product search / import / order / tracking
# (endpoints & method names pre-wired from playbook; confirm in sandbox)
# =====================================================================
class ProductSearchInput(BaseModel):
    site_id: str
    keyword: str
    page: int = 1
    page_size: int = 20


@router.post("/aliexpress/products/search")
async def aliexpress_product_search(data: ProductSearchInput, user=Depends(get_current_user)):
    await _check_site_access(data.site_id, user)
    biz = {
        "method": "aliexpress.ds.text.search",
        "keyWord": data.keyword,
        "pageIndex": str(data.page),
        "pageSize": str(min(data.page_size, 50)),
        "local": "en",
        "countryCode": "FR",
        "currency": "EUR",
        "sortBy": "orders,desc",
    }
    return await _signed_post(SYNC_API_URL, biz, site_id=data.site_id)


class ProductImportInput(BaseModel):
    site_id: str
    product_id: str


@router.post("/aliexpress/products/import")
async def aliexpress_product_import(data: ProductImportInput, user=Depends(get_current_user)):
    await _check_site_access(data.site_id, user)
    biz = {
        "method": "aliexpress.ds.product.get",
        "product_id": data.product_id,
        "ship_to_country": "FR",
        "target_currency": "EUR",
        "target_language": "FR",
    }
    raw = await _signed_post(SYNC_API_URL, biz, site_id=data.site_id)

    # Normalise the AliExpress response into our internal product shape.
    # AliExpress wraps the data under either `aliexpress_ds_product_get_response` or
    # `result`, depending on response variant — we defend against both.
    payload = raw.get("aliexpress_ds_product_get_response") or raw
    result = payload.get("result") or payload
    base = result.get("ae_item_base_info_dto") or {}
    multimedia = result.get("ae_multimedia_info_dto") or {}
    skus = (result.get("ae_item_sku_info_dtos") or {}).get("ae_item_sku_info_d_t_o") or []
    store = result.get("ae_store_info") or {}
    price_info = (result.get("ae_item_properties") or {})

    # Extract price (min across SKUs, fallback to base price)
    min_price = None
    if isinstance(skus, list) and skus:
        prices = [float(s.get("offer_sale_price") or s.get("sku_price") or 0) for s in skus if (s.get("offer_sale_price") or s.get("sku_price"))]
        if prices:
            min_price = min(prices)
    if not min_price:
        try:
            min_price = float(base.get("sale_price") or base.get("price") or 0)
        except Exception:
            min_price = 0.0

    # Images
    image_urls = []
    raw_imgs = multimedia.get("image_urls") or base.get("product_image_url") or ""
    if isinstance(raw_imgs, str):
        image_urls = [u.strip() for u in raw_imgs.split(";") if u.strip()]
    elif isinstance(raw_imgs, list):
        image_urls = [str(u) for u in raw_imgs if u]
    if not image_urls and base.get("main_image_url"):
        image_urls = [base["main_image_url"]]

    title = base.get("subject") or base.get("product_title") or f"Produit AliExpress {data.product_id}"
    category = base.get("category_id") or ""
    currency = base.get("currency_code") or "EUR"

    # Our internal product schema mirrors what SiteProducts.jsx expects.
    product_id_internal = f"ae-{data.product_id}"
    now_iso = datetime.now(timezone.utc).isoformat()
    product_doc = {
        "id": product_id_internal,
        "site_id": data.site_id,
        "status": "active",
        "source": "aliexpress",
        "source_id": str(data.product_id),
        "supplier": "AliExpress",
        "supplier_url": f"https://www.aliexpress.com/item/{data.product_id}.html",
        "name": {"fr": title, "en": title},
        "description": {"fr": "", "en": ""},
        "price": round(min_price or 0.0, 2),
        "currency": currency,
        "category": str(category),
        "images": image_urls[:10],
        "tags": [],
        "variants": [
            {
                "sku_id": str(s.get("sku_id") or ""),
                "sku_code": str(s.get("sku_code") or ""),
                "sku_attr": str(s.get("sku_attr") or ""),
                "price": float(s.get("offer_sale_price") or s.get("sku_price") or 0),
                "stock": int(s.get("sku_available_stock") or 0),
                "properties": s.get("ae_sku_property_dtos") or s.get("properties") or [],
            }
            for s in (skus if isinstance(skus, list) else [])
        ],
        "store": {"name": store.get("store_name") or "", "id": str(store.get("store_id") or "")},
        "aliexpress_raw": {
            "category_id": category,
            "properties": price_info,
        },
        "created_at": now_iso,
        "updated_at": now_iso,
        "imported_at": now_iso,
    }

    # Upsert on (site_id, source_id) so re-importing updates in place.
    await db.products.update_one(
        {"site_id": data.site_id, "source": "aliexpress", "source_id": str(data.product_id)},
        {"$set": {k: v for k, v in product_doc.items() if k != "created_at"},
         "$setOnInsert": {"created_at": now_iso}},
        upsert=True,
    )

    # Fire AI narrative enrichment in background (reuses existing hook)
    try:
        from routes.product_narrative import enrich_product_narrative
        import asyncio as _aio
        _aio.create_task(enrich_product_narrative(product_id_internal))
    except Exception:
        logger.exception("[aliexpress] narrative hook dispatch failed")

    return {
        "ok": True,
        "product_id": product_id_internal,
        "name": title,
        "price": product_doc["price"],
        "image": image_urls[0] if image_urls else "",
        "variants_count": len(product_doc["variants"]),
    }


class OrderPlaceInput(BaseModel):
    site_id: str
    customer_order_id: str
    product_id: str
    sku_attr: str  # e.g. "14:175;5:100014064"
    quantity: int
    shipping: dict  # {name, address, city, zip, country, phone}


@router.post("/aliexpress/orders/place")
async def aliexpress_order_place(data: OrderPlaceInput, user=Depends(get_current_user)):
    await _check_site_access(data.site_id, user)
    biz = {
        "method": "aliexpress.ds.order.create",
        "param_place_order_request4_open_api_d_t_o": str({
            "product_items": [{
                "product_id": data.product_id,
                "sku_attr": data.sku_attr,
                "product_count": data.quantity,
            }],
            "logistics_address": {
                "address": data.shipping.get("address", ""),
                "city": data.shipping.get("city", ""),
                "contact_person": data.shipping.get("name", ""),
                "country": data.shipping.get("country", "FR"),
                "full_name": data.shipping.get("name", ""),
                "mobile_no": data.shipping.get("phone", ""),
                "phone_country": "33",
                "zip": data.shipping.get("zip", ""),
            },
        }),
    }
    resp = await _signed_post(SYNC_API_URL, biz, site_id=data.site_id)
    ae_order_id = (resp.get("aliexpress_ds_order_create_response") or {}).get("result", {}).get("order_list", [None])[0]
    if ae_order_id:
        await db.order_mappings.insert_one({
            "site_id": data.site_id,
            "customer_order_id": data.customer_order_id,
            "aliexpress_order_id": ae_order_id,
            "status": "placed",
            "placed_at": datetime.now(timezone.utc).isoformat(),
        })
    return resp


@router.get("/aliexpress/orders/{ae_order_id}/tracking")
async def aliexpress_order_tracking(ae_order_id: str, site_id: str, user=Depends(get_current_user)):
    await _check_site_access(site_id, user)
    biz = {
        "method": "aliexpress.logistics.ds.trackinginfo.get",
        "ae_order_id": ae_order_id,
        "language": "en_US",
    }
    return await _signed_post(SYNC_API_URL, biz, site_id=site_id)


# =====================================================================
# Auto-order hook (called from Mollie webhook on paid transition)
# =====================================================================
async def auto_place_aliexpress_order(order: dict) -> dict:
    """
    When a customer order is paid, walk through each AliExpress-sourced item
    and place the corresponding order on AliExpress. Persists a mapping per
    line item so tracking can later reconcile. Non-blocking, logs failures.
    """
    site_id = order.get("site_id")
    if not site_id:
        return {"skipped": "no_site"}

    pl = await _get_platform_settings()
    if not (pl.get("connected") and pl.get("access_token")):
        logger.info("[ae-auto-order] plateforme non connectée AliExpress — skip")
        return {"skipped": "platform_not_connected"}

    items = order.get("items") or []
    addr = order.get("shipping_address") or {}
    customer = order.get("customer") or {}
    placed = []
    errors = []

    for it in items:
        pid = it.get("product_id")
        if not pid:
            continue
        product = await db.products.find_one(
            {"id": pid, "site_id": site_id, "source": "aliexpress"},
            {"_id": 0, "source_id": 1, "variants": 1, "name": 1},
        )
        if not product:
            continue  # not an AliExpress product — handled by local fulfilment

        source_id = product.get("source_id")
        # Pick the variant the customer selected (if any) else fall back to the 1st
        variants = product.get("variants") or []
        selected = None
        if it.get("sku_id"):
            selected = next((v for v in variants if str(v.get("sku_id")) == str(it["sku_id"])), None)
        if not selected and variants:
            selected = variants[0]
        sku_attr = (selected or {}).get("sku_attr") or ""
        if not sku_attr:
            errors.append({"product_id": pid, "reason": "no_sku_attr"})
            continue

        biz = {
            "method": "aliexpress.ds.order.create",
            "ds_extend_request": "",
            "param_place_order_request4_open_api_d_t_o": _json_str({
                "product_items": [{
                    "product_id": source_id,
                    "sku_attr": sku_attr,
                    "product_count": int(it.get("quantity", 1)),
                }],
                "logistics_address": {
                    "address":        addr.get("line1") or addr.get("address_line1") or "",
                    "address2":       addr.get("line2") or addr.get("address_line2") or "",
                    "city":           addr.get("city") or "",
                    "contact_person": addr.get("full_name") or customer.get("name") or "",
                    "country":        (addr.get("country_code") or addr.get("country") or "FR")[:2].upper(),
                    "full_name":      addr.get("full_name") or customer.get("name") or "",
                    "mobile_no":      addr.get("phone") or customer.get("phone") or "",
                    "phone_country":  "33",
                    "zip":            addr.get("postal_code") or "",
                    "province":       addr.get("state") or addr.get("region") or "",
                },
            }),
        }

        try:
            resp = await _signed_post(SYNC_API_URL, biz, site_id=site_id)
            ae_order_id = _extract_order_id(resp)
            await db.order_mappings.insert_one({
                "id": uuid.uuid4().hex,
                "site_id": site_id,
                "customer_order_id": order.get("id"),
                "customer_order_number": order.get("order_number"),
                "product_id_internal": pid,
                "product_id_aliexpress": source_id,
                "sku_attr": sku_attr,
                "quantity": int(it.get("quantity", 1)),
                "aliexpress_order_id": ae_order_id,
                "status": "placed" if ae_order_id else "failed",
                "raw_response": resp if not ae_order_id else None,
                "placed_at": datetime.now(timezone.utc).isoformat(),
            })
            if ae_order_id:
                placed.append(ae_order_id)
            else:
                errors.append({"product_id": pid, "response": resp})
        except Exception as e:
            logger.exception(f"[ae-auto-order] failed for product {pid}")
            errors.append({"product_id": pid, "error": str(e)[:200]})

    logger.info(f"[ae-auto-order] order {order.get('order_number')} — placed={len(placed)} errors={len(errors)}")
    return {"placed": placed, "errors": errors}


def _json_str(obj: dict) -> str:
    import json as _json
    return _json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def _extract_order_id(resp: dict):
    """Probe common response shapes for the AliExpress order id."""
    probes = [
        resp.get("aliexpress_ds_order_create_response", {}).get("result", {}).get("order_list", {}).get("number", [None])[0],
        resp.get("aliexpress_ds_order_create_response", {}).get("result", {}).get("order_list", [None])[0] if isinstance(resp.get("aliexpress_ds_order_create_response", {}).get("result", {}).get("order_list"), list) else None,
        (resp.get("result") or {}).get("order_id"),
        resp.get("order_id"),
    ]
    for p in probes:
        if p:
            return str(p)
    return None


# =====================================================================
# Daily cron — refresh tracking for all open order mappings
# =====================================================================
_AE_STATUS_MAP = {
    "WAIT_SELLER_SEND_GOODS": "paid",
    "SELLER_PART_SEND_GOODS": "shipped",
    "WAIT_BUYER_ACCEPT_GOODS": "shipped",
    "IN_TRANSIT": "shipped",
    "FINISH": "delivered",
    "FUND_PROCESSING": "refunded",
    "WAIT_GROUP_SUCCESS": "paid",
}


async def sync_all_aliexpress_tracking() -> dict:
    """Iterate all open AliExpress order mappings and refresh their tracking info.
    Also pushes the tracking_number + carrier onto the parent customer order so the
    client storefront timeline picks it up.
    """
    cursor = db.order_mappings.find(
        {"aliexpress_order_id": {"$ne": None},
         "status": {"$in": ["placed", "paid", "shipped"]}},
        {"_id": 0}
    )
    mappings = await cursor.to_list(500)
    ok, err = 0, 0
    for m in mappings:
        try:
            biz = {
                "method": "aliexpress.logistics.ds.trackinginfo.get",
                "ae_order_id": m["aliexpress_order_id"],
                "language": "en_US",
            }
            resp = await _signed_post(SYNC_API_URL, biz, site_id=m["site_id"])
            payload = (resp.get("aliexpress_logistics_ds_trackinginfo_get_response") or resp).get("result") or {}
            tracking_number = payload.get("official_tracking_no") or payload.get("tracking_number") or ""
            carrier = payload.get("official_carrier_name") or payload.get("carrier_name") or ""
            ae_status = payload.get("status") or payload.get("logistics_status") or ""
            internal = _AE_STATUS_MAP.get(ae_status.upper(), m.get("status"))

            updates = {
                "tracking_number": tracking_number,
                "carrier": carrier,
                "ae_status": ae_status,
                "status": internal,
                "last_sync_at": datetime.now(timezone.utc).isoformat(),
            }
            await db.order_mappings.update_one({"id": m["id"]}, {"$set": updates})

            # Push onto parent customer order (non-destructive)
            if tracking_number:
                parent_updates = {"tracking_number": tracking_number, "carrier": carrier}
                if internal == "shipped":
                    parent_updates["status"] = "shipped"
                await db.orders.update_one(
                    {"id": m["customer_order_id"]},
                    {"$set": parent_updates,
                     "$push": {"status_history": {
                         "status": internal,
                         "at": datetime.now(timezone.utc).isoformat(),
                         "source": "aliexpress_tracking",
                         "ae_status": ae_status,
                     }}},
                )
                # Send "expédié" email once
                if internal == "shipped" and not m.get("shipping_email_sent"):
                    try:
                        from routes.emails import send_shipping_update
                        parent_order = await db.orders.find_one({"id": m["customer_order_id"]}, {"_id": 0})
                        site = await db.sites.find_one({"id": m["site_id"]}, {"_id": 0})
                        if parent_order and site:
                            await send_shipping_update(parent_order, site, tracking_number, carrier)
                            await db.order_mappings.update_one(
                                {"id": m["id"]}, {"$set": {"shipping_email_sent": True}},
                            )
                    except Exception:
                        logger.exception("[ae-tracking] shipping email failed")
            ok += 1
        except Exception:
            logger.exception(f"[ae-tracking-sync] failed for mapping {m.get('id')}")
            err += 1
    return {"total": len(mappings), "ok": ok, "errors": err}


# =====================================================================
# HTML helper for OAuth callback pages
# =====================================================================
def _page(title: str, body: str, ok: Optional[bool] = None) -> str:
    color = "#10b981" if ok else ("#BE123C" if ok is False else "#1C1917")
    badge = "✓" if ok else ("!" if ok is False else "●")
    return f"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><title>Altiaro × AliExpress</title>
<meta name="viewport" content="width=device-width,initial-scale=1"><style>
body{{margin:0;font-family:Georgia,serif;background:#FDFBF7;color:#1C1917;
     min-height:100vh;display:flex;align-items:center;justify-content:center;padding:24px}}
.card{{background:#fff;max-width:460px;border-radius:20px;padding:44px 36px;text-align:center;
      box-shadow:0 10px 40px rgba(28,25,23,.08);border:1px solid #F5F2EB}}
.badge{{width:60px;height:60px;border-radius:50%;background:{color}22;color:{color};
       display:inline-flex;align-items:center;justify-content:center;margin-bottom:22px;
       font-size:30px;font-weight:700}}
h1{{font-size:24px;margin:0 0 12px}}
p{{color:#57534E;font-family:system-ui,sans-serif;font-size:15px;line-height:1.65;margin:0}}
.note{{font-size:12px;color:#A8A29E;margin-top:26px;border-top:1px solid #F5F2EB;padding-top:16px}}
code{{background:#F5F2EB;padding:2px 6px;border-radius:4px;font-size:12px}}
</style></head>
<body><div class="card">
  <div class="badge">{badge}</div>
  <h1>{title}</h1>
  <p>{body}</p>
  <div class="note">Altiaro · altiaro.com</div>
</div></body></html>"""
