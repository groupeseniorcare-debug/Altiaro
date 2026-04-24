"""
Google Merchant Center integration (Phase 5).

Expose:
- OAuth 2.0 flow avec scope `content` (start / callback / status / disconnect)
- Content API v2.1 pour push/delete produits (fire-and-forget + batch)
- Cron `merchant_daily_sync` scheduled depuis server.py (04h UTC)
- Hooks CRUD produits (sync_product_if_connected / delete_product_if_connected)

Approche V1 :
- Single-account Merchant (1 OAuth plateforme pour tous les sites)
- Filtrage par `customLabel0 = site_id` → permet segmentation dans Ads PMax
- Persistance dans `db.platform_settings` (key=`merchant`), pattern cohérent
  avec `google_ads.py` et `aliexpress.py`
- Architecture pensée pour migration MCA future : helper
  `_get_merchant_id_for_site(site_id)` centralise la résolution

Tous les endpoints `/merchant/*` sont admin-only.
Tant que `GOOGLE_CLIENT_ID/SECRET` sont vides, toutes les routes répondent
proprement `config_missing` — aucun crash.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
import uuid
from typing import Any, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse

try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import Flow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    _GOOGLE_LIBS_OK = True
except Exception:  # pragma: no cover
    _GOOGLE_LIBS_OK = False

from deps import db, require_admin

logger = logging.getLogger(__name__)
router = APIRouter()

# ============================================================== #
# Config                                                          #
# ============================================================== #
SCOPES = ["https://www.googleapis.com/auth/content"]
MAX_CONCURRENT_PUSHES = 10
DEFAULT_COUNTRY = "FR"
DEFAULT_LANG = "fr"
DEFAULT_CURRENCY = "EUR"


def _oauth_config() -> Optional[dict]:
    """Retourne la config OAuth si CLIENT_ID + SECRET présents, sinon None."""
    cid = os.environ.get("GOOGLE_CLIENT_ID", "").strip()
    secret = os.environ.get("GOOGLE_CLIENT_SECRET", "").strip()
    if not (cid and secret):
        return None
    redirect = (
        os.environ.get("GOOGLE_MERCHANT_REDIRECT_URI", "").strip()
        or os.environ.get("GOOGLE_REDIRECT_URI", "").strip()
        or f"{os.environ.get('PUBLIC_ORIGIN', '').rstrip('/')}/api/merchant/oauth/callback"
    )
    return {"client_id": cid, "client_secret": secret, "redirect_uri": redirect}


def _build_flow() -> Optional[Any]:
    cfg = _oauth_config()
    if not cfg or not _GOOGLE_LIBS_OK:
        return None
    return Flow.from_client_config(
        {
            "web": {
                "client_id": cfg["client_id"],
                "client_secret": cfg["client_secret"],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [cfg["redirect_uri"]],
            }
        },
        scopes=SCOPES,
        redirect_uri=cfg["redirect_uri"],
    )


async def _get_merchant_settings() -> dict:
    return await db.platform_settings.find_one({"key": "merchant"}) or {}


async def _get_merchant_id_for_site(site_id: str = "") -> Optional[str]:
    """V1 single-account : renvoie toujours le merchant_id plateforme.
    Priorité : platform_settings.merchant.merchant_id > env MERCHANT_ID.
    Architecture pensée MCA V2 : signature `site_id` prête pour résolution
    par sub-account.
    """
    settings = await _get_merchant_settings()
    return (
        settings.get("merchant_id")
        or os.environ.get("MERCHANT_ID", "").strip()
        or None
    )


async def _get_creds() -> Optional[Any]:
    """Construit les Credentials Google depuis platform_settings.merchant."""
    if not _GOOGLE_LIBS_OK:
        return None
    settings = await _get_merchant_settings()
    refresh_token = settings.get("refresh_token")
    if not refresh_token:
        return None
    cfg = _oauth_config()
    if not cfg:
        return None
    creds = Credentials(
        token=settings.get("access_token"),
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=cfg["client_id"],
        client_secret=cfg["client_secret"],
        scopes=SCOPES,
    )
    # Laissons google-auth gérer le refresh automatique quand le service fera un appel.
    return creds


def _service_for(creds):
    return build("content", "v2.1", credentials=creds, cache_discovery=False)


# ============================================================== #
# Mapping MongoDB → Google Product Resource                       #
# ============================================================== #

def _price_bucket(price: float) -> str:
    if price < 30:
        return "0-30"
    if price < 60:
        return "30-60"
    if price < 100:
        return "60-100"
    return "100+"


def _margin_bucket(product: dict) -> str:
    price = float(product.get("price") or 0)
    cost = float(product.get("cost_price_ht") or 0)
    if price <= 0 or cost <= 0:
        return "unknown"
    margin_pct = (price - cost) / price
    if margin_pct < 0.4:
        return "low"
    if margin_pct < 0.65:
        return "medium"
    return "high"


def _pick_lang_value(dict_or_str: Any, lang: str = DEFAULT_LANG) -> str:
    if isinstance(dict_or_str, dict):
        return str(
            dict_or_str.get(lang)
            or dict_or_str.get(DEFAULT_LANG)
            or next(iter(dict_or_str.values()), "")
            or ""
        )
    return str(dict_or_str or "")


def _product_to_google_resource(
    site: dict, product: dict, niche: Optional[dict] = None
) -> dict:
    """Mapping canonique MongoDB product → Google Content API Product resource.
    Centralisé ici pour utilisation par push individuel ET batch.
    """
    origin = os.environ.get("PUBLIC_ORIGIN", "").rstrip("/") or "https://altiaro.com"
    site_id = site["id"]
    pid = product["id"]
    sku = str(product.get("sku") or pid)
    title = _pick_lang_value(product.get("name"))[:150] or "Produit"
    desc = _pick_lang_value(product.get("description"))[:5000] or title
    images = [img for img in (product.get("images") or []) if img]
    price = float(product.get("price") or 0)
    stock = product.get("stock")
    availability = "in stock" if (stock is None or stock > 0) else "out of stock"

    resource = {
        "offerId": sku,
        "title": title,
        "description": desc,
        "link": f"{origin}/shop/{site_id}/product/{pid}",
        "imageLink": images[0] if images else "",
        "contentLanguage": DEFAULT_LANG,
        "targetCountry": DEFAULT_COUNTRY,
        "channel": "online",
        "availability": availability,
        "condition": "new",
        "brand": site.get("name") or "Brand",
        "identifierExists": False,
        "price": {"value": f"{price:.2f}", "currency": DEFAULT_CURRENCY},
        "shipping": [{
            "country": DEFAULT_COUNTRY,
            "service": "Standard",
            "price": {"value": "0.00", "currency": DEFAULT_CURRENCY},
        }],
        # --- Custom labels pour segmentation Ads ---
        "customLabel0": site_id,
        "customLabel1": site.get("niche_slug") or "",
        "customLabel2": site.get("operator_id") or "",
        "customLabel3": _price_bucket(price),
        "customLabel4": _margin_bucket(product),
    }
    if len(images) > 1:
        resource["additionalImageLinks"] = images[1:10]  # max 10
    if niche and niche.get("google_product_category_id"):
        resource["googleProductCategory"] = str(niche["google_product_category_id"])
    return resource


# ============================================================== #
# Push / Delete helpers                                            #
# ============================================================== #

async def _push_single_raw(service, merchant_id: str, resource: dict) -> dict:
    """Push 1 produit via Content API synchrone-in-thread. Retourne dict standardisé."""
    loop = asyncio.get_event_loop()

    def _call():
        return service.products().insert(merchantId=merchant_id, body=resource).execute()

    try:
        result = await loop.run_in_executor(None, _call)
        return {"ok": True, "offerId": resource["offerId"], "id": result.get("id")}
    except HttpError as e:
        status = e.resp.status if hasattr(e, "resp") else 0
        return {
            "ok": False,
            "offerId": resource["offerId"],
            "google_code": f"http_{status}",
            "message": str(e)[:200],
        }
    except Exception as e:
        return {
            "ok": False,
            "offerId": resource["offerId"],
            "google_code": "unknown",
            "message": str(e)[:200],
        }


async def _delete_single_raw(service, merchant_id: str, sku: str) -> dict:
    """Supprime 1 produit du Merchant Center.
    Content API product ID = {channel}:{contentLanguage}:{targetCountry}:{offerId}
    """
    product_resource_id = f"online:{DEFAULT_LANG}:{DEFAULT_COUNTRY}:{sku}"
    loop = asyncio.get_event_loop()

    def _call():
        return service.products().delete(
            merchantId=merchant_id, productId=product_resource_id
        ).execute()

    try:
        await loop.run_in_executor(None, _call)
        return {"ok": True, "offerId": sku}
    except HttpError as e:
        status = e.resp.status if hasattr(e, "resp") else 0
        return {"ok": False, "offerId": sku, "google_code": f"http_{status}", "message": str(e)[:200]}
    except Exception as e:
        return {"ok": False, "offerId": sku, "google_code": "unknown", "message": str(e)[:200]}


# ============================================================== #
# Fire-and-forget hooks (appelés depuis products.py CRUD)          #
# ============================================================== #

async def sync_product_if_connected(site_id: str, product_id: str) -> None:
    """Push 1 produit vers Merchant Center — silent no-op si :
    - Pas de OAuth connecté
    - Pas de merchant_id
    - Site pas publié
    - Produit inactif
    """
    try:
        settings = await _get_merchant_settings()
        if not settings.get("refresh_token"):
            return
        merchant_id = await _get_merchant_id_for_site(site_id)
        if not merchant_id:
            return
        site = await db.sites.find_one({"id": site_id}, {"_id": 0})
        if not site:
            return
        if not (site.get("design") or {}).get("published"):
            return
        product = await db.products.find_one(
            {"id": product_id, "site_id": site_id}, {"_id": 0}
        )
        if not product or product.get("status") != "active":
            return
        niche = None
        if site.get("niche_slug"):
            niche = await db.niches.find_one({"slug": site["niche_slug"]}, {"_id": 0})
        creds = await _get_creds()
        if not creds:
            return
        service = _service_for(creds)
        resource = _product_to_google_resource(site, product, niche)
        result = await _push_single_raw(service, merchant_id, resource)
        logger.info(
            f"[merchant] CRUD-hook push site={site_id} product={product_id}: "
            f"ok={result['ok']}"
            + (f" err={result.get('google_code')}" if not result["ok"] else "")
        )
    except Exception as e:
        logger.warning(f"[merchant] CRUD-hook silent fail site={site_id} product={product_id}: {e}")


async def delete_product_if_connected(site_id: str, product_id: str, sku: str) -> None:
    """Supprime 1 produit du Merchant Center — silent no-op si pas connecté."""
    try:
        settings = await _get_merchant_settings()
        if not settings.get("refresh_token"):
            return
        merchant_id = await _get_merchant_id_for_site(site_id)
        if not merchant_id:
            return
        creds = await _get_creds()
        if not creds:
            return
        service = _service_for(creds)
        result = await _delete_single_raw(service, merchant_id, sku)
        logger.info(
            f"[merchant] CRUD-hook delete site={site_id} sku={sku}: ok={result['ok']}"
        )
    except Exception as e:
        logger.warning(f"[merchant] delete-hook silent fail site={site_id} sku={sku}: {e}")


def fire_and_forget_sync(site_id: str, product_id: str) -> None:
    """Wrapper safe pour appel depuis des endpoints sync (CRUD produits)."""
    try:
        asyncio.create_task(sync_product_if_connected(site_id, product_id))
    except Exception as e:
        logger.warning(f"[merchant] fire_and_forget_sync failed: {e}")


def fire_and_forget_delete(site_id: str, product_id: str, sku: str) -> None:
    try:
        asyncio.create_task(delete_product_if_connected(site_id, product_id, sku))
    except Exception as e:
        logger.warning(f"[merchant] fire_and_forget_delete failed: {e}")


# ============================================================== #
# Batch sync (site entier)                                        #
# ============================================================== #

async def sync_all_site_products(
    site_id: str, triggered_by: str = "admin"
) -> dict:
    """Push en parallèle (sémaphore 10) tous les produits actifs d'un site.
    Persiste un enregistrement dans db.merchant_syncs.
    """
    settings = await _get_merchant_settings()
    if not settings.get("refresh_token"):
        return {"ok": False, "error": "not_connected", "message": "Merchant Center non connecté"}
    merchant_id = await _get_merchant_id_for_site(site_id)
    if not merchant_id:
        return {"ok": False, "error": "no_merchant_id", "message": "Merchant ID non configuré"}
    site = await db.sites.find_one({"id": site_id}, {"_id": 0})
    if not site:
        return {"ok": False, "error": "site_not_found"}
    if not (site.get("design") or {}).get("published"):
        return {
            "ok": False,
            "error": "site_not_published",
            "message": "Publiez le site avant de le pousser sur Google Shopping",
        }
    creds = await _get_creds()
    if not creds:
        return {"ok": False, "error": "no_creds"}
    service = _service_for(creds)
    niche = None
    if site.get("niche_slug"):
        niche = await db.niches.find_one({"slug": site["niche_slug"]}, {"_id": 0})
    products = await db.products.find(
        {"site_id": site_id, "status": "active"}, {"_id": 0}
    ).to_list(5000)
    if not products:
        return {"ok": True, "sync_id": None, "pushed_ok": 0, "pushed_err": 0, "errors": [], "message": "Aucun produit actif"}

    sync_id = str(uuid.uuid4())
    start_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    sem = asyncio.Semaphore(MAX_CONCURRENT_PUSHES)

    async def _push_one(p):
        async with sem:
            resource = _product_to_google_resource(site, p, niche)
            return await _push_single_raw(service, merchant_id, resource)

    results = await asyncio.gather(
        *(_push_one(p) for p in products), return_exceptions=True
    )
    ok_count = 0
    err_count = 0
    errors: list[dict] = []
    for r in results:
        if isinstance(r, Exception):
            err_count += 1
            errors.append({"google_code": "exception", "message": str(r)[:200]})
        elif isinstance(r, dict) and r.get("ok"):
            ok_count += 1
        else:
            err_count += 1
            errors.append(r if isinstance(r, dict) else {"google_code": "unknown"})

    finish_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    # Persiste le sync (keep only first 50 errors for DB size)
    await db.merchant_syncs.insert_one({
        "id": sync_id,
        "site_id": site_id,
        "triggered_by": triggered_by,
        "started_at": start_iso,
        "finished_at": finish_iso,
        "products_pushed_ok": ok_count,
        "products_pushed_err": err_count,
        "errors": errors[:50],
    })
    await db.platform_settings.update_one(
        {"key": "merchant"},
        {"$set": {
            "last_sync_at": finish_iso,
            "last_sync_status": "ok" if err_count == 0 else ("partial" if ok_count > 0 else "error"),
        }},
    )
    logger.info(
        f"[merchant] synced site={site_id} ok={ok_count} err={err_count} "
        f"triggered_by={triggered_by}"
    )
    return {
        "ok": True,
        "sync_id": sync_id,
        "pushed_ok": ok_count,
        "pushed_err": err_count,
        "errors": errors[:10],  # only first 10 in response payload
    }


# ============================================================== #
# Cron (appelée depuis server.py APScheduler)                     #
# ============================================================== #

async def daily_merchant_sync() -> None:
    """Job APScheduler : 04h UTC quotidien.
    Re-sync tous les sites publiés. Skip silencieux si pas connecté.
    """
    settings = await _get_merchant_settings()
    if not settings.get("refresh_token"):
        logger.info("[merchant] daily_sync skipped: not connected")
        return
    merchant_id = await _get_merchant_id_for_site("")
    if not merchant_id:
        logger.info("[merchant] daily_sync skipped: no merchant_id")
        return
    sites = await db.sites.find(
        {"design.published": True}, {"id": 1, "_id": 0}
    ).to_list(1000)
    logger.info(f"[merchant] daily_sync starting for {len(sites)} published sites")
    for s in sites:
        try:
            await sync_all_site_products(s["id"], triggered_by="cron_daily")
        except Exception as e:
            logger.warning(f"[merchant] daily_sync site={s['id']} failed: {e}")
    logger.info("[merchant] daily_sync done")


# ============================================================== #
# HTTP routes                                                      #
# ============================================================== #

@router.get("/merchant/oauth/start")
async def oauth_start(_admin: dict = Depends(require_admin)) -> dict:
    flow = _build_flow()
    if not flow:
        raise HTTPException(
            status_code=400,
            detail="GOOGLE_CLIENT_ID/SECRET manquants dans .env — configurez d'abord l'OAuth Google.",
        )
    url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    # Persist code_verifier (PKCE) + state pour pouvoir le réinjecter dans le
    # callback. Sans ça, Google renvoie "invalid_grant : Missing code verifier".
    await db.platform_settings.update_one(
        {"key": "merchant_oauth_state"},
        {"$set": {
            "key": "merchant_oauth_state",
            "state": state,
            "code_verifier": getattr(flow, "code_verifier", None),
            "created_at": time.time(),
        }},
        upsert=True,
    )
    return {"authorize_url": url, "state": state}


@router.get("/merchant/oauth/callback")
async def oauth_callback(
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
):
    """Callback OAuth Google. Pas d'auth admin requise (Google sign le state).
    Redirige vers /admin/integrations?merchant=connected|error.
    """
    frontend = (
        os.environ.get("FRONTEND_URL", "").rstrip("/")
        or os.environ.get("PUBLIC_ORIGIN", "").rstrip("/")
        or ""
    )
    target_err = f"{frontend}/admin/integrations?merchant=error"
    target_ok = f"{frontend}/admin/integrations?merchant=connected"

    if error:
        logger.warning(f"[merchant] oauth_callback error: {error}")
        return RedirectResponse(url=f"{target_err}&reason={error}", status_code=302)
    if not code:
        return RedirectResponse(url=f"{target_err}&reason=missing_code", status_code=302)
    flow = _build_flow()
    if not flow:
        return RedirectResponse(url=f"{target_err}&reason=config_missing", status_code=302)
    # Retrieve PKCE code_verifier saved at oauth_start. Required by Google since
    # Flow.authorization_url() auto-generates a code_challenge.
    saved_verifier = None
    try:
        state_doc = await db.platform_settings.find_one(
            {"key": "merchant_oauth_state"}, {"_id": 0}
        ) or {}
        saved_verifier = state_doc.get("code_verifier")
        if saved_verifier:
            flow.code_verifier = saved_verifier
        logger.info(
            f"[merchant] callback: code={bool(code)} state={state} "
            f"state_doc_present={bool(state_doc)} "
            f"code_verifier_loaded={bool(saved_verifier)} "
            f"flow.redirect_uri={flow.redirect_uri}"
        )
    except Exception:
        logger.exception("[merchant] failed to load code_verifier from DB")
    try:
        flow.fetch_token(code=code)
    except Exception as e:
        logger.exception(f"[merchant] oauth token exchange failed: {e}")
        return RedirectResponse(url=f"{target_err}&reason=token_exchange", status_code=302)

    creds = flow.credentials
    expires_iso = ""
    if getattr(creds, "expiry", None):
        try:
            expires_iso = creds.expiry.strftime("%Y-%m-%dT%H:%M:%SZ")
        except Exception:
            pass
    await db.platform_settings.update_one(
        {"key": "merchant"},
        {"$set": {
            "key": "merchant",
            "refresh_token": creds.refresh_token,
            "access_token": creds.token,
            "access_token_expires_at": expires_iso,
            "connected_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "granted_scopes": list(creds.scopes or SCOPES),
        }},
        upsert=True,
    )
    # Cleanup OAuth state (anti-replay + idempotence)
    try:
        await db.platform_settings.delete_one({"key": "merchant_oauth_state"})
    except Exception:
        pass
    logger.info(
        f"[merchant] oauth_callback success — refresh_token persisted · "
        f"granted_scopes={list(creds.scopes or SCOPES)}"
    )
    return RedirectResponse(url=target_ok, status_code=302)


@router.get("/merchant/status")
async def get_status(_admin: dict = Depends(require_admin)) -> dict:
    cfg = _oauth_config()
    if not cfg:
        return {
            "configured_env": False,
            "connected": False,
            "merchant_id": None,
            "message": "GOOGLE_CLIENT_ID/SECRET manquants",
        }
    settings = await _get_merchant_settings()
    connected = bool(settings.get("refresh_token"))
    settings_mid = settings.get("merchant_id")
    env_mid = os.environ.get("MERCHANT_ID", "").strip()
    merchant_id = settings_mid or env_mid or None
    return {
        "configured_env": True,
        "connected": connected,
        "merchant_id": merchant_id,
        "merchant_id_source": "db" if settings_mid else ("env" if env_mid else None),
        "connected_at": settings.get("connected_at"),
        "last_sync_at": settings.get("last_sync_at"),
        "last_sync_status": settings.get("last_sync_status"),
        "redirect_uri": cfg["redirect_uri"],
    }


@router.post("/merchant/disconnect")
async def disconnect(_admin: dict = Depends(require_admin)) -> dict:
    await db.platform_settings.update_one(
        {"key": "merchant"},
        {"$unset": {
            "refresh_token": "",
            "access_token": "",
            "access_token_expires_at": "",
            "connected_at": "",
        }},
    )
    logger.info("[merchant] disconnected by admin")
    return {"ok": True}


@router.post("/merchant/merchant-id")
async def set_merchant_id(
    data: dict = Body(...),
    _admin: dict = Depends(require_admin),
) -> dict:
    mid = str(data.get("merchant_id", "")).strip()
    if not mid:
        raise HTTPException(status_code=400, detail="merchant_id manquant")
    if not mid.isdigit():
        raise HTTPException(status_code=400, detail="merchant_id doit être un nombre (ex: 123456789)")
    await db.platform_settings.update_one(
        {"key": "merchant"},
        {"$set": {"key": "merchant", "merchant_id": mid}},
        upsert=True,
    )
    logger.info(f"[merchant] merchant_id set to {mid}")
    return {"ok": True, "merchant_id": mid}


@router.post("/sites/{site_id}/merchant/sync")
async def sync_site_endpoint(
    site_id: str, _admin: dict = Depends(require_admin)
) -> dict:
    return await sync_all_site_products(
        site_id, triggered_by=_admin.get("id", "admin")
    )


@router.post("/sites/{site_id}/merchant/products/{product_id}/sync")
async def sync_one_endpoint(
    site_id: str, product_id: str, _admin: dict = Depends(require_admin)
) -> dict:
    # Exécution synchrone (pas fire-and-forget) car l'admin attend un retour.
    settings = await _get_merchant_settings()
    if not settings.get("refresh_token"):
        return {"ok": False, "error": "not_connected"}
    merchant_id = await _get_merchant_id_for_site(site_id)
    if not merchant_id:
        return {"ok": False, "error": "no_merchant_id"}
    site = await db.sites.find_one({"id": site_id}, {"_id": 0})
    if not site:
        raise HTTPException(404, "Site introuvable")
    product = await db.products.find_one(
        {"id": product_id, "site_id": site_id}, {"_id": 0}
    )
    if not product:
        raise HTTPException(404, "Produit introuvable")
    niche = None
    if site.get("niche_slug"):
        niche = await db.niches.find_one({"slug": site["niche_slug"]}, {"_id": 0})
    creds = await _get_creds()
    service = _service_for(creds)
    resource = _product_to_google_resource(site, product, niche)
    result = await _push_single_raw(service, merchant_id, resource)
    return result


@router.delete("/sites/{site_id}/merchant/products/{product_id}")
async def delete_one_endpoint(
    site_id: str, product_id: str, _admin: dict = Depends(require_admin)
) -> dict:
    product = await db.products.find_one(
        {"id": product_id, "site_id": site_id}, {"_id": 0, "sku": 1, "id": 1}
    )
    if not product:
        raise HTTPException(404, "Produit introuvable")
    sku = str(product.get("sku") or product_id)
    settings = await _get_merchant_settings()
    if not settings.get("refresh_token"):
        return {"ok": False, "error": "not_connected"}
    merchant_id = await _get_merchant_id_for_site(site_id)
    if not merchant_id:
        return {"ok": False, "error": "no_merchant_id"}
    creds = await _get_creds()
    service = _service_for(creds)
    result = await _delete_single_raw(service, merchant_id, sku)
    return result


@router.get("/sites/{site_id}/merchant/status")
async def site_status(
    site_id: str, _admin: dict = Depends(require_admin)
) -> dict:
    """Statut merchant pour 1 site — utilisé par le panel SiteDetail."""
    settings = await _get_merchant_settings()
    connected = bool(settings.get("refresh_token"))
    merchant_id = await _get_merchant_id_for_site(site_id)
    site = await db.sites.find_one({"id": site_id}, {"_id": 0, "id": 1, "design.published": 1})
    published = bool((site or {}).get("design", {}).get("published"))
    total_active = await db.products.count_documents(
        {"site_id": site_id, "status": "active"}
    )
    last_sync = await db.merchant_syncs.find_one(
        {"site_id": site_id}, {"_id": 0}, sort=[("started_at", -1)]
    )
    return {
        "site_id": site_id,
        "connected": connected,
        "merchant_id": merchant_id,
        "site_published": published,
        "products_active": total_active,
        "last_sync": last_sync,
    }
