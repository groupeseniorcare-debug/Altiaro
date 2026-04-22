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
TOKEN_URL = "https://api-sg.aliexpress.com/rest/auth/token/create"
REFRESH_URL = "https://api-sg.aliexpress.com/rest/auth/token/refresh"
SYNC_API_URL = "https://api-sg.aliexpress.com/sync"


# =====================================================================
# OAuth — authorize + callback
# =====================================================================
def _sign_state(site_id: str) -> str:
    """HMAC-sign the state to prevent CSRF and restore site_id safely on callback."""
    raw = f"{site_id}.{int(time.time())}"
    mac = hmac.new(APP_SECRET.encode(), raw.encode(), hashlib.sha256).hexdigest()[:16]
    return f"{raw}.{mac}"


def _verify_state(state: str) -> Optional[str]:
    try:
        parts = state.split(".")
        if len(parts) != 3:
            return None
        site_id, ts, mac = parts
        expected = hmac.new(APP_SECRET.encode(), f"{site_id}.{ts}".encode(), hashlib.sha256).hexdigest()[:16]
        if not hmac.compare_digest(mac, expected):
            return None
        # 15 min validity window
        if int(time.time()) - int(ts) > 900:
            return None
        return site_id
    except Exception:
        return None


@router.get("/aliexpress/authorize-url")
async def get_authorize_url(site_id: str, user=Depends(get_current_user)):
    """Return the URL the Concepteur should be redirected to. Keeps all secrets server-side."""
    await _check_site_access(site_id, user)
    if not APP_KEY:
        raise HTTPException(503, "Intégration AliExpress non configurée côté serveur.")
    state = _sign_state(site_id)
    params = {
        "response_type": "code",
        "client_id": APP_KEY,
        "redirect_uri": CALLBACK_URL,
        "state": state,
        "sp": "ae",
    }
    return {"authorize_url": f"{AUTHORIZE_URL}?{urlencode(params)}", "state": state}


@router.get("/aliexpress/oauth/callback", response_class=HTMLResponse)
async def aliexpress_oauth_callback(
    request: Request,
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    error_description: Optional[str] = None,
):
    """Registered in the AliExpress App Console. Always returns 200 for health checks."""
    now = datetime.now(timezone.utc)
    try:
        await db.aliexpress_oauth_callbacks.insert_one({
            "received_at": now, "code": code, "state": state,
            "error": error, "error_description": error_description,
            "ip": (request.headers.get("x-forwarded-for") or (request.client.host if request.client else "")),
            "user_agent": request.headers.get("user-agent", ""),
        })
    except Exception:
        logger.exception("[aliexpress] persist callback failed")

    if error:
        logger.warning(f"[aliexpress] OAuth error : {error} — {error_description}")
        return HTMLResponse(_page(title="Autorisation refusée", body=f"<code>{error}</code> — {error_description or ''}", ok=False))

    if not code:
        return HTMLResponse(_page(title="Endpoint OAuth Altiaro × AliExpress", body="Ce point d'entrée est réservé au flow OAuth initié depuis votre cockpit."))

    site_id = _verify_state(state or "")
    if not site_id:
        return HTMLResponse(_page(title="Lien invalide ou expiré", body="Relancez la connexion depuis votre cockpit Altiaro.", ok=False))

    try:
        token_payload = await _exchange_code_for_token(code)
    except Exception as e:
        logger.exception("[aliexpress] token exchange failed")
        return HTMLResponse(_page(title="Échec de la connexion", body=f"Erreur lors de l'échange du code : {str(e)[:200]}", ok=False))

    expires_in = int(token_payload.get("expires_in") or 172800)  # ~48h default
    refresh_in = int(token_payload.get("refresh_token_valid_time") or token_payload.get("refresh_expires_in") or 365 * 86400)
    expires_at = now + timedelta(seconds=expires_in)
    refresh_at = now + timedelta(seconds=refresh_in)

    await db.sites.update_one(
        {"id": site_id},
        {"$set": {
            "design.aliexpress": {
                "connected": True,
                "access_token": token_payload.get("access_token"),
                "refresh_token": token_payload.get("refresh_token"),
                "expires_at": expires_at.isoformat(),
                "refresh_expires_at": refresh_at.isoformat(),
                "user_id": token_payload.get("user_id") or token_payload.get("account_id") or "",
                "user_nick": token_payload.get("user_nick") or token_payload.get("seller_id") or "",
                "connected_at": now.isoformat(),
                "last_refreshed_at": None,
            }
        }}
    )
    logger.info(f"[aliexpress] site {site_id} connected (user_id={token_payload.get('user_id')})")

    return HTMLResponse(_page(
        title="Connexion AliExpress confirmée",
        body="Votre boutique Altiaro est maintenant liée à votre compte AliExpress Dropshipping. Vous pouvez fermer cette fenêtre et retourner dans votre cockpit.",
        ok=True,
    ))


# =====================================================================
# Status + disconnect
# =====================================================================
@router.get("/sites/{site_id}/aliexpress/status")
async def aliexpress_status(site_id: str, user=Depends(get_current_user)):
    await _check_site_access(site_id, user)
    site = await db.sites.find_one({"id": site_id}, {"_id": 0, "design.aliexpress": 1})
    ali = ((site or {}).get("design") or {}).get("aliexpress") or {}
    return {
        "connected": bool(ali.get("connected") and ali.get("access_token")),
        "user_nick": ali.get("user_nick") or "",
        "connected_at": ali.get("connected_at"),
        "expires_at": ali.get("expires_at"),
        "last_refreshed_at": ali.get("last_refreshed_at"),
        "configured_server_side": bool(APP_KEY and APP_SECRET),
    }


@router.post("/sites/{site_id}/aliexpress/disconnect")
async def aliexpress_disconnect(site_id: str, user=Depends(get_current_user)):
    await _check_site_access(site_id, user)
    await db.sites.update_one(
        {"id": site_id},
        {"$set": {"design.aliexpress": {"connected": False, "disconnected_at": datetime.now(timezone.utc).isoformat()}}},
    )
    return {"status": "ok"}


# =====================================================================
# Token helpers (private)
# =====================================================================
async def _exchange_code_for_token(code: str) -> dict:
    """Exchange OAuth code → access_token. AliExpress uses a /rest/auth/token/create endpoint with signed request."""
    params = {
        "code": code,
        "uuid": uuid.uuid4().hex,
    }
    return await _signed_post(TOKEN_URL, params, need_access_token=False)


async def _refresh_access_token(site_id: str) -> dict:
    site = await db.sites.find_one({"id": site_id}, {"_id": 0, "design.aliexpress": 1})
    ali = ((site or {}).get("design") or {}).get("aliexpress") or {}
    refresh_token = ali.get("refresh_token")
    if not refresh_token:
        raise HTTPException(401, "Site non connecté à AliExpress.")
    params = {"refresh_token": refresh_token}
    resp = await _signed_post(REFRESH_URL, params, need_access_token=False)
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(seconds=int(resp.get("expires_in") or 172800))
    await db.sites.update_one(
        {"id": site_id},
        {"$set": {
            "design.aliexpress.access_token": resp.get("access_token"),
            "design.aliexpress.refresh_token": resp.get("refresh_token") or refresh_token,
            "design.aliexpress.expires_at": expires_at.isoformat(),
            "design.aliexpress.last_refreshed_at": now.isoformat(),
        }},
    )
    return resp


async def _get_valid_access_token(site_id: str) -> str:
    site = await db.sites.find_one({"id": site_id}, {"_id": 0, "design.aliexpress": 1})
    ali = ((site or {}).get("design") or {}).get("aliexpress") or {}
    token = ali.get("access_token")
    if not token:
        raise HTTPException(401, "Site non connecté à AliExpress. Cliquez sur 'Connecter AliExpress' depuis le cockpit.")
    # Proactive refresh if expiring within 5 min
    expires_at = ali.get("expires_at")
    if expires_at:
        try:
            dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            if dt < (datetime.now(timezone.utc) + timedelta(minutes=5)):
                resp = await _refresh_access_token(site_id)
                return resp.get("access_token")
        except Exception:
            pass
    return token


# =====================================================================
# AliExpress signature (SHA256) + signed POST helper
# =====================================================================
def _sign_params(params: dict, secret: str) -> str:
    """AliExpress signature algorithm : concat sorted k+v then HMAC-SHA256 hex upper."""
    concat = "".join(f"{k}{v}" for k, v in sorted(params.items()) if v is not None)
    return hmac.new(secret.encode(), concat.encode(), hashlib.sha256).hexdigest().upper()


async def _signed_post(url: str, biz_params: dict, need_access_token: bool = True, site_id: Optional[str] = None) -> dict:
    """Common signed request helper for AliExpress REST/SYNC APIs."""
    if not APP_KEY or not APP_SECRET:
        raise HTTPException(503, "Intégration AliExpress non configurée côté serveur.")
    params = dict(biz_params)
    params["app_key"] = APP_KEY
    params["sign_method"] = "sha256"
    params["timestamp"] = str(int(time.time() * 1000))
    if need_access_token:
        if not site_id:
            raise HTTPException(500, "site_id manquant pour appel authentifié")
        params["session"] = await _get_valid_access_token(site_id)
    params["sign"] = _sign_params(params, APP_SECRET)
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(url, data=params)
        r.raise_for_status()
        data = r.json()
    if isinstance(data, dict) and (data.get("error_response") or data.get("code") in {"401", "15"}):
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
    # TODO (next step) : normalise raw → upsert in db.products with site_id
    return {"raw": raw, "note": "Normalisation vers db.products à finaliser en sandbox"}


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
