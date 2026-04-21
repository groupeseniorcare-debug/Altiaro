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


# Country → language mapping for translation targets
LANG_BY_COUNTRY = {
    "FR": "fr", "BE": "fr", "LU": "fr", "CH": "fr",
    "DE": "de", "AT": "de",
    "UK": "en", "IE": "en",
    "NL": "nl", "IT": "it", "ES": "es",
}


async def _cj_product_detail(product_id: str) -> dict:
    """Fetch detailed product info (description, images, variants) from CJ."""
    if not CJ_API_KEY or not product_id:
        return {}
    try:
        token = await _cj_auth()
        async with httpx.AsyncClient(timeout=20) as c:
            r = await c.get(f"{CJ_BASE}/product/query",
                            params={"pid": product_id},
                            headers={"CJ-Access-Token": token})
            if r.status_code != 200:
                return {}
            return (r.json().get("data") or {}) or {}
    except Exception:
        return {}


async def _translate_product(title_en: str, desc_en: str, target_langs: list) -> dict:
    """Use Claude (via Emergent LLM key) to translate a product title + description
    into the target languages. Returns {fr: {...}, de: {...}, ...}.
    Never raises — returns original text as fallback on error.
    """
    from routes.design import _claude_json  # reuse existing plumbing
    from deps import EMERGENT_LLM_KEY
    if not EMERGENT_LLM_KEY or not target_langs:
        return {}
    # Only the languages we haven't already
    langs = [lg for lg in target_langs if lg in ("fr", "de", "nl", "it", "es", "en")]
    if not langs:
        return {}
    system = ("You are a senior e-commerce copywriter translating dropshipping product "
              "listings for a premium French e-shop. Write fluent, benefit-driven copy "
              "(never literal translation). Respect the target language's tone and "
              "shopping conventions. Never invent specs that aren't in the source. "
              "Output STRICT JSON only.")
    langs_desc = ", ".join([{
        "fr": "French (senior-friendly, rassurant, jamais de jargon US)",
        "de": "German (clear, precise, professional)",
        "nl": "Dutch (direct, friendly)",
        "it": "Italian (warm, persuasive)",
        "es": "Spanish (Spain, cordial, clear)",
        "en": "English (UK, clean, benefit-focused)",
    }[lg] for lg in langs])
    user_prompt = f"""Translate and adapt the following product into these languages: {langs_desc}.

SOURCE (English, from CJ Dropshipping, may be poor/literal):
Title: {title_en[:300]}
Description: {desc_en[:2500] if desc_en else '(none — infer from title)'}

Rules:
- Keep title < 70 chars, persuasive but honest
- Description : 2-3 short paragraphs, bullet-points welcome, focus on benefits for the end-user (seniors / home / autonomy)
- Remove CJ jargon, shipping mentions, Chinese brand hints
- Use the target language's punctuation conventions

Return STRICT JSON with one key per target language, each containing {{title, description}}. Example structure:
{{"fr": {{"title": "...", "description": "..."}}, "de": {{"title": "...", "description": "..."}}}}

Languages to produce: {", ".join(langs)}
"""
    try:
        res = await _claude_json(system, user_prompt, f"translate-{uuid.uuid4().hex[:8]}", timeout=90)
        # Validate structure
        out = {}
        for lg in langs:
            block = res.get(lg) or {}
            if isinstance(block, dict) and block.get("title"):
                out[lg] = {
                    "title": str(block.get("title") or "")[:250],
                    "description": str(block.get("description") or "")[:3000],
                }
        return out
    except Exception:
        return {}


@router.post("/sites/{site_id}/sourcing/import")
async def import_product(site_id: str, data: ImportInput, user: dict = Depends(get_current_user)):
    await _check_site_access(site_id, user)
    # Load site to determine target translation languages
    site = await db.sites.find_one({"id": site_id}, {"_id": 0, "selected_countries": 1})
    countries = (site or {}).get("selected_countries") or ["FR"]
    target_langs = list(set(LANG_BY_COUNTRY.get((c or "").upper(), "fr") for c in countries))
    if "fr" not in target_langs:
        target_langs.append("fr")

    # Fetch CJ detail for richer description + better images
    detail = {}
    raw_desc = ""
    extra_images = []
    if data.provider == "cj" and data.product_id:
        detail = await _cj_product_detail(data.product_id)
        raw_desc = detail.get("description") or detail.get("productDescription") or ""
        # Extra images from CJ detail
        imgs = detail.get("productImageSet") or detail.get("productImages") or []
        if isinstance(imgs, list):
            extra_images = [i for i in imgs if isinstance(i, str)][:5]

    # Strip HTML from CJ description
    import re as _re
    if raw_desc:
        raw_desc = _re.sub(r"<[^>]+>", " ", raw_desc)
        raw_desc = _re.sub(r"\s+", " ", raw_desc).strip()[:3000]

    # Translate via Claude (non-blocking error)
    translations = await _translate_product(data.title, raw_desc, target_langs)

    # Build i18n dicts — fallback to original if a lang wasn't translated
    name_dict = {}
    desc_dict = {}
    for lg in ["fr", "de", "nl", "it", "es", "en"]:
        if lg in translations:
            name_dict[lg] = translations[lg]["title"]
            desc_dict[lg] = translations[lg]["description"]
        else:
            name_dict[lg] = data.title
            desc_dict[lg] = raw_desc if lg == "en" else ""

    pid = str(uuid.uuid4())
    images = [data.image] if data.image else []
    for i in extra_images:
        if i and i not in images:
            images.append(i)

    doc = {
        "id": pid,
        "site_id": site_id,
        "name": name_dict,
        "description": desc_dict,
        "price": round(data.price_eur, 2),
        "cost_price_ht": round(data.cost_eur, 2),
        "compare_at_price": None,
        "currency": "EUR",
        "images": images[:6],
        "stock": None,
        "supplier_url": data.supplier_url or "",
        "sku": data.sku or f"{data.provider.upper()}-{data.product_id[:12]}",
        "status": "draft",
        "featured": False,
        "source": {"provider": data.provider, "product_id": data.product_id},
        "translation_status": "translated" if translations else "fallback_original",
        "translated_langs": list(translations.keys()),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.products.insert_one(dict(doc))
    doc.pop("_id", None)
    return {"ok": True, "product": doc}
