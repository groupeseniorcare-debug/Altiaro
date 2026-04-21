"""Sourcing integrations (Sprint 16) — CJ Dropshipping + AliExpress Affiliate.

Both providers are optional — they require user-provided API keys in .env.
If keys are missing, endpoints return a friendly 503 with setup instructions.

Endpoints:
- GET  /api/sourcing/providers              → list available providers with status
- POST /api/sourcing/search                 → unified search across enabled providers
- POST /api/sites/{id}/sourcing/import      → import a product into site catalog
"""
from __future__ import annotations
import hmac
import hashlib
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from deps import db, get_current_user, _check_site_access

router = APIRouter()

CJ_API_KEY = os.environ.get("CJ_API_KEY", "")
CJ_BASE = "https://developers.cjdropshipping.com/api2.0/v1"

AE_APP_KEY = os.environ.get("ALIEXPRESS_APP_KEY", "")
AE_APP_SECRET = os.environ.get("ALIEXPRESS_APP_SECRET", "")
AE_TRACKING_ID = os.environ.get("ALIEXPRESS_TRACKING_ID", "")
AE_BASE = "https://api-sg.aliexpress.com/sync"


# ============= CJ DROPSHIPPING ============= #
_cj_token = {"value": None, "expires_at": None}


async def _cj_auth() -> str:
    if not CJ_API_KEY:
        raise HTTPException(503, "CJ Dropshipping non configuré. Ajoute CJ_API_KEY dans backend/.env "
                                 "(portail gratuit : https://developers.cjdropshipping.com — My CJ → Authorization → API → Generate)")
    if _cj_token["value"] and _cj_token["expires_at"] and _cj_token["expires_at"] > datetime.now(timezone.utc):
        return _cj_token["value"]
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.post(f"{CJ_BASE}/authentication/getAccessToken",
                         json={"apiKey": CJ_API_KEY})
        if r.status_code != 200:
            raise HTTPException(502, f"CJ auth failed: {r.text[:150]}")
        data = r.json().get("data") or {}
        _cj_token["value"] = data.get("accessToken")
        try:
            _cj_token["expires_at"] = datetime.fromisoformat(
                (data.get("accessTokenExpiryDate") or "").replace("+08:00", "+08:00"))
        except Exception:
            _cj_token["expires_at"] = None
        return _cj_token["value"]


async def _cj_search(keyword: str, page: int = 1, size: int = 20) -> list:
    token = await _cj_auth()
    async with httpx.AsyncClient(timeout=25) as c:
        r = await c.get(f"{CJ_BASE}/product/list",
                        params={"pageNum": page, "pageSize": size, "productNameEn": keyword},
                        headers={"CJ-Access-Token": token})
        if r.status_code != 200:
            return []
        items = (r.json().get("data") or {}).get("list") or []

    def _to_float(v) -> float:
        """CJ renvoie parfois des prix 'range' ex '0.48 -- 0.67'. On prend le low."""
        if v is None:
            return 0.0
        s = str(v).strip()
        if not s:
            return 0.0
        # Split sur -- / - / ~ / , / ' to ' → low price
        for sep in ("--", "~", " to ", ","):
            if sep in s:
                s = s.split(sep, 1)[0].strip()
                break
        # enlève devise
        s = s.replace("$", "").replace("€", "").replace("US", "").strip()
        try:
            return float(s)
        except (ValueError, TypeError):
            return 0.0

    out = []
    for it in items:
        sell = _to_float(it.get("sellPrice"))
        ship = _to_float(it.get("cheapestShippingPrice"))
        out.append({
            "provider": "cj",
            "product_id": str(it.get("pid") or it.get("productId") or ""),
            "title": it.get("productNameEn") or it.get("productName") or "",
            "image": it.get("productImage") or (it.get("productImageSet") or [None])[0],
            "price_usd": sell,
            "cost_usd": sell or ship,  # sellPrice est le coût fournisseur CJ
            "supplier_url": f"https://cjdropshipping.com/product/{it.get('pid','')}",
            "sku": it.get("productSku") or "",
            "category": it.get("categoryName") or "",
        })
    return out


# ============= ALIEXPRESS AFFILIATE ============= #
def _ae_sign(secret: str, params: dict) -> str:
    s = "".join(f"{k}{params[k]}" for k in sorted(params))
    return hmac.new(secret.encode(), s.encode(), hashlib.sha256).hexdigest().upper()


async def _ae_call(method: str, biz_params: dict) -> dict:
    if not (AE_APP_KEY and AE_APP_SECRET):
        raise HTTPException(503,
            "AliExpress Affiliate non configuré. Ajoute ALIEXPRESS_APP_KEY, ALIEXPRESS_APP_SECRET et "
            "ALIEXPRESS_TRACKING_ID dans backend/.env "
            "(inscription gratuite : https://portals.aliexpress.com → Tools → API → Apply → Affiliates Individual → "
            "App Console → Create → copie App Key + App Secret)")
    params = {
        "app_key": AE_APP_KEY,
        "method": method,
        "timestamp": int(time.time() * 1000),
        "format": "json",
        "v": "2.0",
        "sign_method": "hmac-sha256",
        **biz_params,
    }
    params["sign"] = _ae_sign(AE_APP_SECRET, params)
    async with httpx.AsyncClient(timeout=25) as c:
        r = await c.post(AE_BASE, data=params)
        if r.status_code != 200:
            return {}
        return r.json()


async def _ae_search(keyword: str, page: int = 1, size: int = 20, country: str = "FR") -> list:
    biz = {
        "keywords": keyword,
        "page_no": page,
        "page_size": size,
        "tracking_id": AE_TRACKING_ID or "default",
        "target_currency": "EUR",
        "target_language": "FR",
        "ship_to_country": country,
        "sort": "SALE_PRICE_ASC",
    }
    data = await _ae_call("aliexpress.affiliate.product.query", biz)
    try:
        items = data["aliexpress_affiliate_product_query_response"]["resp_result"]["result"]["products"]["product"]
    except (KeyError, TypeError):
        return []
    out = []
    for it in items:
        price_str = str(it.get("target_sale_price") or it.get("sale_price") or "0").replace("€", "").strip()
        try:
            price = float(price_str)
        except Exception:
            price = 0
        out.append({
            "provider": "aliexpress",
            "product_id": str(it.get("product_id", "")),
            "title": it.get("product_title") or "",
            "image": it.get("product_main_image_url") or "",
            "price_usd": price,
            "cost_usd": price * 0.7,   # estimation (70% of retail as cost)
            "supplier_url": it.get("product_detail_url") or "",
            "sku": str(it.get("product_id", "")),
            "category": it.get("second_level_category_name") or "",
            "rating": float(it.get("evaluate_rate", "0").replace("%", "") or 0),
            "orders": int(it.get("lastest_volume", 0)),
        })
    return out


# ============= ROUTES ============= #

@router.get("/sourcing/providers")
async def list_providers(user: dict = Depends(get_current_user)):
    return {
        "providers": [
            {"id": "cj", "name": "CJ Dropshipping", "enabled": bool(CJ_API_KEY),
             "setup_url": "https://developers.cjdropshipping.com",
             "setup_steps": "My CJ → Authorization → API → Generate (clé gratuite)"},
            {"id": "aliexpress", "name": "AliExpress Affiliate", "enabled": bool(AE_APP_KEY and AE_APP_SECRET),
             "setup_url": "https://portals.aliexpress.com",
             "setup_steps": "Register (Affiliate) → Tools → API → Affiliates Individual → App Console → Create"},
        ]
    }


class SearchInput(BaseModel):
    keyword: str
    providers: Optional[list[str]] = None
    page: int = 1
    size: int = 20
    country: str = "FR"


@router.post("/sourcing/search")
async def search(data: SearchInput, user: dict = Depends(get_current_user)):
    kw = data.keyword.strip()
    if not kw:
        raise HTTPException(400, "Mot-clé requis")
    want = set(data.providers or ["cj", "aliexpress"])
    results = []
    errors = []
    if "cj" in want and CJ_API_KEY:
        try:
            results.extend(await _cj_search(kw, data.page, data.size))
        except HTTPException as e:
            errors.append({"provider": "cj", "detail": e.detail})
        except Exception as e:
            errors.append({"provider": "cj", "detail": str(e)[:200]})
    if "aliexpress" in want and AE_APP_KEY and AE_APP_SECRET:
        try:
            results.extend(await _ae_search(kw, data.page, data.size, data.country))
        except HTTPException as e:
            errors.append({"provider": "aliexpress", "detail": e.detail})
        except Exception as e:
            errors.append({"provider": "aliexpress", "detail": str(e)[:200]})
    return {"count": len(results), "results": results, "errors": errors,
            "providers_available": {"cj": bool(CJ_API_KEY),
                                    "aliexpress": bool(AE_APP_KEY and AE_APP_SECRET)}}


class ImportInput(BaseModel):
    provider: str
    product_id: str
    title: str
    image: Optional[str] = ""
    price_eur: float
    cost_eur: float
    supplier_url: Optional[str] = ""
    sku: Optional[str] = ""


@router.post("/sites/{site_id}/sourcing/import")
async def import_product(site_id: str, data: ImportInput, user: dict = Depends(get_current_user)):
    await _check_site_access(site_id, user)
    pid = str(uuid.uuid4())
    doc = {
        "id": pid,
        "site_id": site_id,
        "name": {"fr": data.title, "en": data.title, "de": data.title, "nl": data.title},
        "description": {"fr": "", "en": "", "de": "", "nl": ""},
        "price": round(data.price_eur, 2),
        "cost_price_ht": round(data.cost_eur, 2),
        "compare_at_price": None,
        "currency": "EUR",
        "images": [data.image] if data.image else [],
        "stock": None,
        "supplier_url": data.supplier_url or "",
        "sku": data.sku or f"{data.provider.upper()}-{data.product_id[:12]}",
        "status": "draft",
        "featured": False,
        "source": {"provider": data.provider, "product_id": data.product_id},
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.products.insert_one(dict(doc))
    doc.pop("_id", None)
    return {"ok": True, "product": doc}
