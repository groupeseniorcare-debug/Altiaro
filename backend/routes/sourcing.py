"""Sourcing integrations (Sprint 16) — CJ Dropshipping + AliExpress Affiliate.

Both providers are optional — they require user-provided API keys in .env.
If keys are missing, endpoints return a friendly 503 with setup instructions.

Endpoints:
- GET  /api/sourcing/providers              → list available providers with status
- POST /api/sourcing/search                 → unified search across enabled providers
- POST /api/sites/{id}/sourcing/import      → import a product into site catalog
"""
from __future__ import annotations
import asyncio
import json
import hmac
import hashlib
import os
import re as _re
import time
import uuid
from datetime import datetime, timezone
from typing import Optional, List

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from deps import db, get_current_user, _check_site_access

import logging
logger = logging.getLogger(__name__)

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
    """Search CJ catalog. The public API does AND-substring match on productNameEn
    and NOT fuzzy matching (the CJ website uses a different Elasticsearch endpoint
    not exposed publicly). Strategy: try full phrase, then last 2 words, then last
    word — fall through until we get results. Respect 1 QPS rate limit."""
    token = await _cj_auth()

    def _to_float(v) -> float:
        if v is None:
            return 0.0
        s = str(v).strip()
        if not s:
            return 0.0
        for sep in ("--", "~", " to ", ","):
            if sep in s:
                s = s.split(sep, 1)[0].strip()
                break
        s = s.replace("$", "").replace("€", "").replace("US", "").strip()
        try:
            return float(s)
        except (ValueError, TypeError):
            return 0.0

    # Build progressively simpler query variants. The most specific product-type
    # word is usually the last word ("electric lift chair" → "chair" is too generic,
    # but "lift chair" captures the intent).
    words = keyword.strip().split()
    variants = []
    if len(words) >= 3:
        variants.append(keyword)
        variants.append(" ".join(words[-2:]))   # e.g., "lift chair"
    elif len(words) == 2:
        variants.append(keyword)
    else:
        variants.append(keyword)
    # Dedupe keeping order
    seen = set()
    variants = [v for v in variants if not (v.lower() in seen or seen.add(v.lower()))]

    async with httpx.AsyncClient(timeout=25) as c:
        for i, q in enumerate(variants):
            if i > 0:
                await asyncio.sleep(1.1)  # Respect CJ's 1 QPS throttle
            r = await c.get(
                f"{CJ_BASE}/product/list",
                params={"pageNum": page, "pageSize": size, "productNameEn": q},
                headers={"CJ-Access-Token": token},
            )
            if r.status_code == 429:
                await asyncio.sleep(1.2)
                r = await c.get(
                    f"{CJ_BASE}/product/list",
                    params={"pageNum": page, "pageSize": size, "productNameEn": q},
                    headers={"CJ-Access-Token": token},
                )
            if r.status_code != 200:
                continue
            items = (r.json().get("data") or {}).get("list") or []
            if items:
                # Found results → return them
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
                        "cost_usd": sell,
                        "shipping_usd": ship,
                        "supplier_url": f"https://cjdropshipping.com/product/{it.get('pid','')}",
                        "sku": it.get("productSku") or "",
                        "category": it.get("categoryName") or "",
                        "_matched_query": q,
                    })
                return out
    return []


async def _translate_keyword_fr_to_en(keyword: str) -> Optional[str]:
    """Translate a French search keyword to English for CJ/AliExpress catalogs.
    Returns None if already ASCII-only English or if Claude fails.
    Uses a small cache and a fast prompt."""
    # ASCII-only heuristic: looks like it's already English, skip
    if all(ord(c) < 128 for c in keyword) and not any(w in keyword.lower() for w in [
        "fauteuil", "releveur", "pilulier", "loupe", "canne", "déambulateur", "marche",
        "senior", "aide", "audition", "confort", "dos", "coussin", "orthopédique",
        "domicile", "salle", "bain", "siège"
    ]):
        return None
    from deps import EMERGENT_LLM_KEY
    if not EMERGENT_LLM_KEY:
        return None
    try:
        from services.llm_resilience import safe_claude_text, LLMUnavailableError
        try:
            raw = await safe_claude_text(
                (
                    "You translate French e-commerce search keywords to English for "
                    "dropshipping catalog search (CJ / AliExpress). "
                    "Output ONLY the English product type in 1-2 words (no adjectives, no filler). "
                    "Examples: "
                    "'fauteuil releveur' → 'lift chair' | "
                    "'pilulier électronique' → 'pill dispenser' | "
                    "'déambulateur' → 'walker' | "
                    "'loupe grossissante' → 'magnifier' | "
                    "'canne de marche' → 'walking cane'. "
                    "No punctuation, no quotes, lowercase."
                ),
                f"Translate: {keyword}",
                session_id=f"kw-trans-{uuid.uuid4().hex[:6]}",
                timeout=10,
            )
        except LLMUnavailableError:
            return None
        en = (raw or "").strip().strip('"').strip("'").lower()
        # Basic sanity check
        if 0 < len(en) < 100 and not en.startswith("i "):
            return en
    except Exception:
        pass
    return None


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


async def _ae_ds_product_detail(product_id: str, site_id: Optional[str] = None) -> dict | None:
    """
    Fetch a product detail using the **Dropshipping API** (`aliexpress.ds.product.get`).
    This is the correct API for apps that completed OAuth (buyerApp / DS).
    The previously used `aliexpress.affiliate.productdetail.get` requires an
    Affiliate-type app and returns `InsufficientPermission` otherwise.

    Returns a normalised dict {title, images, main_image, cost_usd, sku, currency}
    or None if the product truly can't be found.
    Raises HTTPException on upstream 502 / missing OAuth.
    """
    # Import tardif pour éviter les cycles d'import.
    from routes.aliexpress import _signed_post, SYNC_API_URL
    biz = {
        "method": "aliexpress.ds.product.get",
        "product_id": str(product_id),
        "ship_to_country": "FR",
        "target_currency": "USD",
        "target_language": "EN",
    }
    raw = await _signed_post(SYNC_API_URL, biz, site_id=site_id)
    payload = raw.get("aliexpress_ds_product_get_response") or raw
    result = payload.get("result") or payload
    base = result.get("ae_item_base_info_dto") or {}
    multimedia = result.get("ae_multimedia_info_dto") or {}
    skus_wrap = result.get("ae_item_sku_info_dtos") or {}
    skus = skus_wrap.get("ae_item_sku_info_d_t_o") or []
    if not base and not skus:
        return None

    # Title
    title = base.get("subject") or base.get("product_title") or ""

    # Images (image_urls est une chaîne ; séparateur officiel = ";")
    images: list[str] = []
    raw_imgs = multimedia.get("image_urls") or base.get("product_image_url") or ""
    if isinstance(raw_imgs, str):
        images = [u.strip() for u in raw_imgs.split(";") if u.strip()]
    elif isinstance(raw_imgs, list):
        images = [str(u) for u in raw_imgs if u]
    main_image = base.get("main_image_url") or (images[0] if images else "")
    if main_image and main_image not in images:
        images.insert(0, main_image)
    images = images[:8]

    # Prix : min offer_sale_price sur les SKUs, sinon base.sale_price
    cost_usd = 0.0
    if isinstance(skus, list) and skus:
        prices = []
        for s in skus:
            v = s.get("offer_sale_price") or s.get("sku_price")
            if v:
                try:
                    prices.append(float(v))
                except (ValueError, TypeError):
                    pass
        if prices:
            cost_usd = min(prices)
    if not cost_usd:
        try:
            cost_usd = float(base.get("sale_price") or base.get("price") or 0)
        except (ValueError, TypeError):
            cost_usd = 0.0

    # SKU : prend le 1er sku si dispo, sinon product_id comme fallback
    sku = ""
    if isinstance(skus, list) and skus:
        sku = str(skus[0].get("sku_id") or skus[0].get("id") or "")
    if not sku:
        sku = str(base.get("product_id") or product_id)

    currency = base.get("currency_code") or "USD"
    return {
        "title": title,
        "main_image": main_image,
        "images": images,
        "cost_usd": cost_usd,
        "sku": sku,
        "currency": currency,
        # Brut SKU list — chaque entrée = 1 variante AE (color/size/etc.)
        # Conservée intégralement pour permettre au pipeline d'import de mapper
        # correctement les variantes vers le doc Mongo (sourcing.py _import_by_url_inner).
        "skus_raw": skus if isinstance(skus, list) else [],
    }


def _map_ae_skus_to_variants(skus_raw: list, usd_to_eur: float | None = None, max_variants: int = 30) -> list[dict]:
    """Map les SKUs AliExpress (ae_item_sku_info_d_t_o) vers la structure
    `variants[]` standard utilisée dans `db.products`.

    Format AE source (par SKU) :
        {
          "sku_id": "1276...", "sku_code": "...", "sku_attr": "200000182:193;14:200000537",
          "offer_sale_price": "529.99", "sku_price": "549.99",
          "sku_available_stock": "12", "sku_image": "https://...",
          "ae_sku_property_dtos": {"ae_sku_property_d_t_o": [
              {"property_value_definition_name": "Gris foncé", "sku_property_value": "GRAY"},
              {"property_value_definition_name": "L",          "sku_property_value": "L"}
          ]}
        }

    Cible (1 entrée = 1 variante storefront) :
        {vid, sku, name, image, sell_price_usd, sell_price_eur, stock, properties}
    """
    out: list[dict] = []
    for sku in (skus_raw or [])[:max_variants]:
        if not isinstance(sku, dict):
            continue
        # Extraire les labels lisibles (ex: ["Gris foncé", "L"])
        prop_wrap = sku.get("ae_sku_property_dtos") or {}
        if isinstance(prop_wrap, dict):
            prop_list = prop_wrap.get("ae_sku_property_d_t_o") or []
        else:
            prop_list = prop_wrap if isinstance(prop_wrap, list) else []
        attr_labels: list[str] = []
        for attr in prop_list if isinstance(prop_list, list) else []:
            if not isinstance(attr, dict):
                continue
            value = (
                attr.get("property_value_definition_name")
                or attr.get("sku_property_value")
                or attr.get("property_value")
                or ""
            )
            if value:
                attr_labels.append(str(value).strip())

        try:
            sell_usd = float(sku.get("offer_sale_price") or sku.get("sku_price") or 0)
        except (TypeError, ValueError):
            sell_usd = 0.0
        sell_eur = round(sell_usd * usd_to_eur, 2) if (usd_to_eur and sell_usd) else None
        try:
            stock = int(sku.get("sku_available_stock") or 0)
        except (TypeError, ValueError):
            stock = 0

        vid = str(sku.get("sku_id") or sku.get("id") or "")
        if not vid:
            continue
        out.append({
            "vid": vid,
            "sku": str(sku.get("sku_code") or vid),
            "name": " / ".join(attr_labels) or "Variante",
            "image": (sku.get("sku_image") or "").strip() or None,
            "sell_price_usd": round(sell_usd, 2),
            "sell_price_eur": sell_eur,
            "stock": stock,
            "properties": attr_labels,  # ex: ["Gris foncé", "L"]
        })
    return out


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
    # Auto-translate FR → EN for CJ/AliExpress catalogs (both are English-indexed)
    en_kw = await _translate_keyword_fr_to_en(kw)
    effective_kw = en_kw or kw
    want = set(data.providers or ["cj", "aliexpress"])
    results = []
    errors = []
    if "cj" in want and CJ_API_KEY:
        try:
            results.extend(await _cj_search(effective_kw, data.page, data.size))
        except HTTPException as e:
            errors.append({"provider": "cj", "detail": e.detail})
        except Exception as e:
            errors.append({"provider": "cj", "detail": str(e)[:200]})
    if "aliexpress" in want and AE_APP_KEY and AE_APP_SECRET:
        try:
            results.extend(await _ae_search(effective_kw, data.page, data.size, data.country))
        except HTTPException as e:
            errors.append({"provider": "aliexpress", "detail": e.detail})
        except Exception as e:
            errors.append({"provider": "aliexpress", "detail": str(e)[:200]})
    return {"count": len(results), "results": results, "errors": errors,
            "translated_keyword": en_kw or None,
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
    role: Optional[str] = "main"  # "main" or "upsell"
    linked_product_ids: Optional[List[str]] = None  # main products this upsell is linked to


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
            if r.status_code == 429:
                # Respect QPS limit then retry once
                await asyncio.sleep(1.2)
                r = await c.get(f"{CJ_BASE}/product/query",
                                params={"pid": product_id},
                                headers={"CJ-Access-Token": token})
            if r.status_code != 200:
                return {}
            return (r.json().get("data") or {}) or {}
    except Exception:
        return {}


async def _cj_freight_to_country(pid: str, vid: str, country_code: str) -> list:
    """Call CJ freight API to check if product ships to `country_code`.
    Returns list of shipping options (may be empty = no shipping available).
    Each option = {logisticName, logisticAging, logisticPrice, ...}"""
    token = await _cj_auth()
    try:
        async with httpx.AsyncClient(timeout=25) as c:
            r = await c.post(
                f"{CJ_BASE}/logistic/freightCalculate",
                headers={"CJ-Access-Token": token},
                json={
                    "startCountryCode": "CN",
                    "endCountryCode": country_code,
                    "products": [{"quantity": 1, "vid": vid}],
                },
            )
            if r.status_code != 200:
                return []
            return r.json().get("data") or []
    except Exception:
        return []


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
    # Chantier 5 — Les traductions produit suivent seo_countries (couverture SEO
    # complète par défaut), pas selected_countries (ads). Les anciens sites sans
    # seo_countries bénéficient automatiquement du fallback "tous pays supportés".
    from seo_constants import get_seo_langs
    site = await db.sites.find_one({"id": site_id}, {"_id": 0, "selected_countries": 1, "seo_countries": 1})
    target_langs = get_seo_langs(site or {})
    if "fr" not in target_langs:
        target_langs.append("fr")

    # Fetch CJ detail for richer description + better images + specs
    detail = {}
    raw_desc = ""
    extra_images = []
    specs = {}
    variants = []
    shipping_by_country = {}
    suggested_sell_price_usd = None
    if data.provider == "cj" and data.product_id:
        detail = await _cj_product_detail(data.product_id)
        raw_desc = detail.get("description") or detail.get("productDescription") or ""
        # Extra images from CJ detail
        imgs = detail.get("productImageSet") or detail.get("productImages") or []
        if isinstance(imgs, list):
            extra_images = [i for i in imgs if isinstance(i, str)][:8]
        # Specs from CJ response
        weight_raw = detail.get("productWeight")
        try:
            weight_g = float(weight_raw) if weight_raw not in (None, "") else None
        except (ValueError, TypeError):
            weight_g = None
        material_en_set = detail.get("materialNameEnSet") or detail.get("materialNameEn") or []
        if isinstance(material_en_set, str):
            try:
                material_en_set = json.loads(material_en_set)
            except (json.JSONDecodeError, TypeError):
                material_en_set = [material_en_set]
        packing_en = detail.get("packingNameEnSet") or detail.get("packingNameEn") or []
        if isinstance(packing_en, str):
            try:
                packing_en = json.loads(packing_en)
            except (json.JSONDecodeError, TypeError):
                packing_en = [packing_en]
        specs = {
            "weight_g": weight_g,
            "weight_kg": round(weight_g / 1000.0, 2) if weight_g else None,
            "category": detail.get("categoryName") or "",
            "material": ", ".join(material_en_set) if isinstance(material_en_set, list) else "",
            "packing": ", ".join(packing_en) if isinstance(packing_en, list) else "",
            "product_type": detail.get("productType") or "",
            "supplier_sku": detail.get("productSku") or "",
        }
        # Suggested sell price by CJ (USD)
        try:
            if detail.get("suggestSellPrice"):
                suggested_sell_price_usd = float(detail.get("suggestSellPrice"))
        except (ValueError, TypeError):
            pass
        # Variants: keep minimal info
        raw_variants = detail.get("variants") or []
        if isinstance(raw_variants, list):
            for v in raw_variants[:20]:
                if not isinstance(v, dict):
                    continue
                variants.append({
                    "vid": str(v.get("vid") or ""),
                    "sku": v.get("variantSku") or "",
                    "name": v.get("variantNameEn") or v.get("variantName") or "",
                    "image": v.get("variantImage") or "",
                    "sell_price_usd": v.get("variantSellPrice"),
                    "weight_g": v.get("variantWeight"),
                })
        # Check shipping availability to each target country.
        # NOTE: the CJ freight endpoint requires full address (province+city) to return
        # real results — country-only calls return empty even for products that DO ship.
        # We mark everything as "unknown" for now; Concepteur verifies on CJ listing page.
        # FIX — la variable globale `countries` n'était pas définie (F821) : on lit les
        # pays depuis le site déjà chargé ligne 534. Fallback FR si rien n'est défini.
        cc_list = (site or {}).get("selected_countries") or (site or {}).get("seo_countries") or ["FR"]
        for cc in cc_list[:6]:
            shipping_by_country[cc.upper()] = {"available": None, "note": "À vérifier sur CJ"}

    elif data.provider == "aliexpress" and data.product_id:
        # Branche AE — récupère le détail SKU pour peupler `variants[]`.
        # On (re)appelle `_ae_ds_product_detail` ; l'API AE Dropshipping est
        # cheap (≤1.5s typique) et dédoublonner cet appel avec le preview
        # nécessiterait un cache transverse — pas la peine pour 5-10 imports/site.
        try:
            ae_detail = await _ae_ds_product_detail(data.product_id, site_id=site_id)
        except Exception:
            logger.exception("[sourcing-ae-import] _ae_ds_product_detail failed (non-blocking)")
            ae_detail = None

        if ae_detail:
            # Taux USD→EUR depuis le preview frontend (data.cost_eur / data.cost_usd
            # si présents dans le payload), sinon estimation 0.92 pour les variantes.
            usd_to_eur = None
            try:
                if getattr(data, "cost_eur", None) and ae_detail.get("cost_usd"):
                    cost_eur_v = float(data.cost_eur)
                    cost_usd_v = float(ae_detail.get("cost_usd") or 0)
                    if cost_usd_v > 0:
                        usd_to_eur = cost_eur_v / cost_usd_v
            except (TypeError, ValueError):
                pass
            if not usd_to_eur:
                usd_to_eur = 0.92  # fallback safe — réajusté ensuite par cron FX

            variants = _map_ae_skus_to_variants(
                ae_detail.get("skus_raw") or [],
                usd_to_eur=usd_to_eur,
                max_variants=30,
            )
            # Suggested sell price : moyenne des variantes (en USD)
            try:
                ae_prices = [v["sell_price_usd"] for v in variants if v.get("sell_price_usd")]
                if ae_prices:
                    suggested_sell_price_usd = round(sum(ae_prices) / len(ae_prices), 2)
            except Exception:
                pass

    # Strip HTML from CJ description
    if raw_desc:
        raw_desc = _re.sub(r"<[^>]+>", " ", raw_desc)
        raw_desc = _re.sub(r"\s+", " ", raw_desc).strip()[:3000]

    # Note: we DON'T block the import based on the freight check. The CJ freight
    # endpoint requires a full shipping address (province, city) to work reliably;
    # a country-only call often returns empty even for products that DO ship to FR.
    # We keep the shipping map in `shipping_by_country` for informational display
    # in the product editor, but the Concepteur must verify on the CJ listing page
    # before committing to an Ads budget.

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
        "images": images[:8],
        "stock": None,
        "supplier_url": data.supplier_url or "",
        "sku": data.sku or f"{data.provider.upper()}-{data.product_id[:12]}",
        "status": "active",
        "featured": False,
        "role": "upsell" if (data.role or "main") == "upsell" else "main",
        "linked_product_ids": list(data.linked_product_ids or []) if (data.role or "main") == "upsell" else [],
        "source": {"provider": data.provider, "product_id": data.product_id},
        "translation_status": "translated" if translations else "fallback_original",
        "translated_langs": list(translations.keys()),
        "specs": specs,
        "variants": variants,
        "shipping": shipping_by_country,
        "suggested_sell_price_usd": suggested_sell_price_usd,
        "raw_description_en": raw_desc,  # useful for later re-translation
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.products.insert_one(dict(doc))
    doc.pop("_id", None)
    return {"ok": True, "product": doc}



# =====================================================================
# IMPORT BY URL — paste a CJ or AliExpress product URL
# =====================================================================
class ImportUrlInput(BaseModel):
    url: str
    role: Optional[str] = "main"  # "main" or "upsell"
    linked_product_ids: Optional[List[str]] = None
    # Phase Chantier 2 — propagés du preview pour tagger le produit importé
    shipping_countries: Optional[List[str]] = None   # pays livrés par ce produit
    product_type: Optional[str] = None               # "main" | "upsell" | "accessory"


def _parse_provider_url(url: str) -> tuple[str, str]:
    """Extract (provider, product_id) from a CJ or AliExpress URL.
    Raises HTTPException if unrecognized."""
    u = url.strip()
    # CJ formats:
    #   - SEO slug + PID: /product/{slug}-p-{pid}.html  (current CJ format, 2024+)
    #   - Legacy PID only: /product/{pid}.html
    #   - UUID: /product/{uuid} (rare)
    m = _re.search(r"cjdropshipping\.com/product/(?:.*?-p-)?(\d{10,})(?:\.html|[?&#]|$)", u)
    if m:
        return "cj", m.group(1)
    # Fallback: UUID-style CJ product IDs (hex-dash format)
    m = _re.search(r"cjdropshipping\.com/product/([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})", u)
    if m:
        return "cj", m.group(1)
    # AliExpress: /item/{pid}.html or /i/{pid}.html
    m = _re.search(r"aliexpress\.[a-z.]+/(?:item|i)/(\d{6,})", u)
    if m:
        return "aliexpress", m.group(1)
    # AliExpress mobile / a.aliexpress.com/_{pid}
    m = _re.search(r"a\.aliexpress\.com/_[A-Za-z0-9]+", u)
    if m:
        raise HTTPException(400, "Lien AliExpress court non supporté. Ouvre le lien et copie l'URL complète (avec /item/…).")
    raise HTTPException(400, "URL non reconnue. Formats acceptés : https://cjdropshipping.com/product/… ou https://www.aliexpress.com/item/…")


@router.post("/sites/{site_id}/sourcing/preview-url")
async def preview_by_url(
    site_id: str,
    data: ImportUrlInput,
    user: dict = Depends(get_current_user),
):
    """Retourne un preview d'un produit (sans l'importer) pour affichage UI
    avec les checks livraison par pays. L'utilisateur voit :
      - Titre, image, prix d'achat, prix suggéré, marge
      - Livrable dans chaque pays cible du site (✅ / ❌)
      - Livraison gratuite (true/false) — warning si non
      - L'url source normalisée

    Gating : nécessite l'étape 'pricing' complétée.
    """
    from routes.journey_gating import require_step
    await _check_site_access(site_id, user)
    await require_step(site_id, "pricing")
    provider, product_id = _parse_provider_url(data.url)

    # Récupère les target_countries du site
    site = await db.sites.find_one({"id": site_id}, {"_id": 0, "selected_countries": 1, "country": 1, "countries": 1})
    target_countries: list[str] = []
    if site:
        target_countries = (
            site.get("selected_countries")
            or site.get("countries")
            or ([site["country"]] if site.get("country") else [])
        )
    target_countries = [c.upper() for c in target_countries if c]

    title = ""
    image = ""
    cost_usd = 0.0
    sku = ""
    shipping_by_country: dict = {}
    free_shipping: bool | None = None
    shipping_cost_eur: float = 0.0
    images: list = []

    if provider == "cj":
        detail = await _cj_product_detail(product_id)
        if not detail:
            raise HTTPException(404, "Produit CJ introuvable. Vérifie l'URL ou ton accès CJ.")
        title = detail.get("productNameEn") or detail.get("productName") or ""
        imgs_raw = detail.get("productImageSet") or detail.get("productImages") or []
        if isinstance(imgs_raw, list):
            images = [i for i in imgs_raw if isinstance(i, str)][:6]
        sku = detail.get("productSku") or ""
        sell = detail.get("sellPrice")
        if sell is not None:
            s = str(sell).split("--")[0].split("~")[0].replace("$", "").replace("US", "").strip()
            try:
                cost_usd = float(s)
            except (ValueError, TypeError):
                cost_usd = 0.0
        # CJ freight check for each target country
        # Use first variant vid if available, else empty string (fallback auto-pick)
        first_vid = ""
        variants_raw = detail.get("variants") or []
        if isinstance(variants_raw, list) and variants_raw:
            first_vid = str(variants_raw[0].get("vid") or variants_raw[0].get("id") or "")
        for cc in target_countries:
            try:
                freights = await _cj_freight_to_country(product_id, first_vid, cc)
                if freights:
                    f0 = freights[0]
                    shipping_by_country[cc] = {
                        "available": True,
                        "price_usd": float(f0.get("logisticPrice") or 0),
                        "days": f0.get("logisticAging") or f0.get("aging") or "—",
                        "method": f0.get("logisticName") or "CJ",
                    }
                else:
                    shipping_by_country[cc] = {"available": False, "reason": "aucune méthode CJ"}
            except Exception as e:
                shipping_by_country[cc] = {"available": False, "reason": str(e)[:100]}
        # Free shipping = premier coût USD == 0
        first_price = next((v.get("price_usd") for v in shipping_by_country.values() if v.get("available")), None)
        free_shipping = bool(first_price is not None and first_price <= 0.01)
        if first_price is not None:
            shipping_cost_eur = round(first_price * 0.92, 2)

    elif provider == "aliexpress":
        if not (AE_APP_KEY and AE_APP_SECRET):
            raise HTTPException(503, "AliExpress non configuré côté serveur.")
        try:
            detail = await _ae_ds_product_detail(product_id, site_id=site_id)
        except HTTPException:
            raise
        except Exception as e:
            logger.exception("[sourcing] AE preview failed")
            raise HTTPException(502, f"AliExpress indisponible : {str(e)[:180]}")
        if not detail:
            raise HTTPException(
                404,
                "Produit AliExpress introuvable. Vérifie l'URL (format /item/{id}.html) "
                "ou que le produit n'a pas été retiré par le vendeur.",
            )
        title = detail["title"]
        image = detail["main_image"]
        images = detail["images"]
        cost_usd = detail["cost_usd"]
        sku = detail["sku"]
        # AE : la livraison par pays dépend des SKUs. On marque "likely_available"
        # pour tous les pays cibles (check réel requiert appel shipping API qui
        # n'est pas toujours disponible sur le tier affiliate standard).
        for cc in target_countries:
            shipping_by_country[cc] = {
                "available": True,
                "confidence": "presumed",
                "reason": "AliExpress livre la plupart des pays EU — vérifiez lors du placement de la commande",
            }
        # Free shipping AE est souvent indiqué dans le flag "promotion_link" ou
        # "original_price"==0 mais ce n'est pas fiable. On suppose non-gratuit par défaut.
        free_shipping = False
        shipping_cost_eur = 0.0

    else:
        raise HTTPException(400, "Provider inconnu")

    if not title:
        raise HTTPException(404, "Produit vide (pas de titre). Vérifie l'URL.")

    rate = 0.92 if provider == "cj" else 1.0
    cost_eur = round(cost_usd * rate, 2)
    suggested_price_eur = round(cost_eur * 2.5 + shipping_cost_eur, 2) if cost_eur > 0 else 0.0
    margin_eur = round(suggested_price_eur - cost_eur - shipping_cost_eur, 2)
    margin_pct = round((margin_eur / suggested_price_eur) * 100, 1) if suggested_price_eur else 0

    # Warnings
    warnings: list[str] = []
    missing = [c for c, v in shipping_by_country.items() if not v.get("available")]
    if missing:
        warnings.append(
            f"⚠️ Non livrable dans : {', '.join(missing)}. "
            "Tes clients dans ces pays ne pourront pas commander ce produit."
        )
    if not free_shipping and provider == "cj":
        warnings.append(
            f"⚠️ Livraison payante (~{shipping_cost_eur}€) — "
            "privilégie les produits avec livraison gratuite pour préserver ta marge."
        )
    if cost_eur > 0 and margin_pct < 50:
        warnings.append(
            f"⚠️ Marge estimée faible ({margin_pct}%) — vérifie si tu peux "
            f"vendre au-dessus du prix suggéré ({suggested_price_eur}€)."
        )

    return {
        "provider": provider,
        "product_id": product_id,
        "title": title,
        "images": images,
        "primary_image": image or (images[0] if images else None),
        "sku": sku,
        "cost_usd": cost_usd,
        "cost_eur": cost_eur,
        "shipping_cost_eur": shipping_cost_eur,
        "suggested_price_eur": suggested_price_eur,
        "margin_eur": margin_eur,
        "margin_pct": margin_pct,
        "free_shipping": free_shipping,
        "target_countries": target_countries,
        "shipping_by_country": shipping_by_country,
        "missing_countries": missing,
        "can_import": True,  # on autorise l'import même en couverture partielle
        "warnings": warnings,
        "url": data.url,
    }


@router.post("/sites/{site_id}/sourcing/import-by-url")
async def import_by_url(site_id: str, data: ImportUrlInput, user: dict = Depends(get_current_user)):
    """Import a product directly from its provider URL (no search needed).

    Gating : nécessite l'étape 'pricing' complétée (409 sinon).
    """
    from routes.journey_gating import require_step
    await _check_site_access(site_id, user)
    await require_step(site_id, "pricing")
    provider, product_id = _parse_provider_url(data.url)

    # Wrapper défensif global : toute exception imprévue est loggée avec stack
    # complète + retournée au client avec un détail parlant (empêche les 500
    # nus "erreur serveur" côté UI).
    try:
        return await _import_by_url_inner(site_id, data, user, provider, product_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            "[sourcing] import_by_url failed — site=%s provider=%s pid=%s url=%s",
            site_id, provider, product_id, data.url,
        )
        raise HTTPException(
            500,
            f"Import {provider.upper()} en erreur : {type(e).__name__} — {str(e)[:180]}. "
            f"Réessaie dans quelques secondes ou contacte le support.",
        )


async def _import_by_url_inner(site_id: str, data: "ImportUrlInput", user: dict, provider: str, product_id: str):
    # Load product meta from the provider
    title = ""
    image = ""
    cost_usd = 0.0
    sku = ""

    if provider == "cj":
        detail = await _cj_product_detail(product_id)
        if not detail:
            raise HTTPException(404, "Produit CJ introuvable. Vérifie l'URL ou ton accès CJ.")
        title = detail.get("productNameEn") or detail.get("productName") or ""
        imgs = detail.get("productImageSet") or detail.get("productImages") or []
        if isinstance(imgs, list) and imgs:
            image = imgs[0] if isinstance(imgs[0], str) else ""
        sku = detail.get("productSku") or ""
        # Price: `sellPrice` at the top level
        sell = detail.get("sellPrice")
        if sell is not None:
            s = str(sell).split("--")[0].split("~")[0].replace("$", "").replace("US", "").strip()
            try:
                cost_usd = float(s)
            except (ValueError, TypeError):
                cost_usd = 0.0
    elif provider == "aliexpress":
        if not (AE_APP_KEY and AE_APP_SECRET):
            raise HTTPException(503, "AliExpress non configuré côté serveur.")
        try:
            detail = await _ae_ds_product_detail(product_id, site_id=site_id)
        except HTTPException:
            raise
        except Exception as e:
            logger.exception("[sourcing] AE import-by-url failed")
            raise HTTPException(502, f"AliExpress indisponible : {str(e)[:180]}")
        if not detail:
            raise HTTPException(
                404,
                "Produit AliExpress introuvable. Vérifie l'URL (format /item/{id}.html) "
                "ou que le produit n'a pas été retiré par le vendeur.",
            )
        title = detail["title"]
        image = detail["main_image"]
        cost_usd = detail["cost_usd"]
        sku = detail["sku"]

    if not title:
        raise HTTPException(404, "Impossible de lire le produit depuis cette URL.")

    # Default margin ×2.5 (concepteur ajustera ensuite son prix de vente)
    rate = 0.92 if provider == "cj" else 1.0
    cost_eur = round(cost_usd * rate, 2)
    price_eur = round(cost_eur * 2.5, 2) if cost_eur > 0 else 0.0

    import_payload = ImportInput(
        provider=provider,
        product_id=product_id,
        title=title,
        image=image,
        price_eur=price_eur,
        cost_eur=cost_eur,
        supplier_url=data.url,
        sku=sku,
        role=data.role or "main",
        linked_product_ids=data.linked_product_ids or [],
    )
    # Respect CJ 1 QPS: sleep before the import (which will call detail again for specs)
    if provider == "cj":
        await asyncio.sleep(1.2)
    # Delegate to the existing importer (handles translation + specs + shipping + save)
    result = await import_product(site_id, import_payload, user)

    # Phase Chantier 2 — enrich persisted doc with coverage & type
    # Si le frontend a passé shipping_countries (depuis le preview), on le persiste.
    # Sinon, on déduit depuis les pays cibles du site (hypothèse safe : le check
    # effectué au preview s'applique au moment de l'import).
    try:
        # `import_product` retourne {"ok": True, "product": {...}} — il faut
        # bien lire result["product"]["id"] et pas result["id"] (sinon le
        # patch n'est jamais appliqué et `shipping_countries` reste vide en
        # DB → le frontend affiche tous les pays en "non livrable").
        product_doc = (result or {}).get("product") or {}
        product_id_new = product_doc.get("id") or (result or {}).get("id") or (result or {}).get("product_id")
        if product_id_new:
            patch: dict = {}
            if data.shipping_countries is not None:
                patch["shipping_countries"] = [c.upper() for c in data.shipping_countries]
            else:
                # Fallback : si le frontend n'a pas passé shipping_countries
                # (preview AE indisponible, etc.), on prend les selected_countries
                # du site comme couverture par défaut. Plus optimiste mais évite
                # un faux négatif total côté UI.
                site = await db.sites.find_one({"id": site_id}, {"_id": 0, "selected_countries": 1})
                cc_list = (site or {}).get("selected_countries") or []
                if cc_list:
                    patch["shipping_countries"] = [str(c).upper() for c in cc_list]
            if data.product_type:
                patch["type"] = data.product_type
                if data.product_type in ("upsell", "accessory"):
                    patch["is_upsell"] = True
            if patch:
                patch["updated_at"] = datetime.now(timezone.utc).isoformat()
                await db.products.update_one(
                    {"id": product_id_new, "site_id": site_id},
                    {"$set": patch},
                )
                # Re-merge le patch dans le doc retourné pour que l'UI reflète
                # immédiatement la couverture sans avoir à refetch.
                if isinstance(result, dict) and isinstance(result.get("product"), dict):
                    result["product"].update(patch)
    except Exception:
        logger.exception("[sourcing] post-import enrich failed (non-blocking)")

    return result


# =====================================================================
# SPRINT C — CJ fulfillment automation
# Auto-place a supplier order at CJ when the customer order becomes "paid",
# and sync tracking back to the customer order periodically.
# =====================================================================


_CJ_STATUS_MAP = {
    # CJ logistic statuses → internal
    "CREATED": "placed",
    "IN_CART": "placed",
    "UNPAID": "placed",
    "UNSHIPPED": "paid",
    "PROCESSING": "paid",
    "DISPATCHED": "shipped",
    "SHIPPED": "shipped",
    "DELIVERING": "shipped",
    "IN_TRANSIT": "shipped",
    "DELIVERED": "delivered",
    "REFUNDED": "refunded",
    "CANCELLED": "cancelled",
}


async def auto_place_cj_order(customer_order_id: str) -> dict:
    """Triggered after Mollie confirms payment. For every CJ line item of the order,
    place a supplier order at CJ and store a mapping in `order_mappings`. Idempotent
    via the `(customer_order_id, cj_order_id)` unique index.

    Returns dict with per-line status for logging.
    """
    if not CJ_API_KEY:
        return {"ok": False, "reason": "no_api_key"}

    order = await db.orders.find_one({"id": customer_order_id}, {"_id": 0})
    if not order:
        return {"ok": False, "reason": "order_not_found"}

    # Build CJ product list — only lines whose product.source.provider == "cj"
    cj_products = []
    for item in (order.get("items") or []):
        p = await db.products.find_one({"id": item.get("product_id")}, {"_id": 0})
        if not p or (p.get("source") or {}).get("provider") != "cj":
            continue
        # CJ requires the VARIANT id (vid), NOT the product id. If no variants were
        # imported, we can't place the order — skip and record an error.
        variants = p.get("variants") or []
        if not variants:
            logger.warning(f"[cj-order] product {p.get('id')} has no variants — cannot order")
            continue
        vid = variants[0].get("vid")
        if not vid:
            continue
        cj_products.append({
            "vid": str(vid),
            "quantity": int(item.get("quantity") or 1),
            "customer_order_item_id": item.get("product_id"),
            "source_product_id": (p.get("source") or {}).get("product_id", ""),
        })

    if not cj_products:
        return {"ok": True, "placed": 0, "reason": "no_cj_items"}

    # Compose CJ payload (/shopping/order/createOrder)
    ship = order.get("shipping_address") or {}
    customer = order.get("customer") or {}
    first_name = (customer.get("name") or "").split(" ", 1)[0] or "Client"
    last_name = (customer.get("name") or "").split(" ", 1)[1] if " " in (customer.get("name") or "") else first_name
    cc = (ship.get("country_code") or "FR").upper()

    # CJ expects BOTH shippingCountry (full English name) AND shippingCountryCode (ISO2)
    country_names = {
        "FR": "France", "DE": "Germany", "BE": "Belgium", "NL": "Netherlands",
        "CH": "Switzerland", "UK": "United Kingdom", "GB": "United Kingdom",
        "ES": "Spain", "IT": "Italy", "PT": "Portugal", "LU": "Luxembourg",
        "AT": "Austria", "DK": "Denmark", "SE": "Sweden", "FI": "Finland",
        "IE": "Ireland", "US": "United States", "CA": "Canada",
    }
    country_full = country_names.get(cc, ship.get("country") or "France")

    # CJ requires a valid logisticName taken from their freightCalculate endpoint.
    # Call it first with the real variant + destination to get a shipping option.
    logistic_name = "CJPacket Ordinary"  # fallback
    first_vid = cj_products[0]["vid"] if cj_products else ""
    if first_vid:
        try:
            token_f = await _cj_auth()
            async with httpx.AsyncClient(timeout=25) as c_f:
                r_f = await c_f.post(
                    f"{CJ_BASE}/logistic/freightCalculate",
                    headers={"CJ-Access-Token": token_f},
                    json={
                        "startCountryCode": "CN",
                        "endCountryCode": cc,
                        "products": [{"quantity": p["quantity"], "vid": p["vid"]}
                                     for p in cj_products],
                    },
                )
                options = (r_f.json() or {}).get("data") or []
                if options:
                    cheapest = min(
                        options,
                        key=lambda o: float(o.get("logisticPrice") or 9999) if o.get("logisticPrice") is not None else 9999,
                    )
                    logistic_name = cheapest.get("logisticName") or logistic_name
        except Exception:
            logger.warning("[cj-order] freight calc failed, using fallback logistic name")

    cj_body = {
        "orderNumber": order.get("order_number") or customer_order_id,
        "shippingCountry": country_full,
        "shippingCountryCode": cc,
        "shippingProvince": ship.get("state") or ship.get("city") or "",
        "shippingCity": ship.get("city") or "",
        "shippingCounty": "",
        "shippingAddress": ship.get("line1", ""),
        "shippingAddress2": ship.get("line2", "") or "",
        "shippingCustomerName": customer.get("name") or f"{first_name} {last_name}",
        "shippingZip": ship.get("postal_code") or "",
        "shippingPhone": customer.get("phone") or "",
        "email": customer.get("email") or "",
        "remark": "Altiaro auto-fulfillment",
        "fromCountryCode": "CN",
        "logisticName": logistic_name,
        "products": [
            {"vid": p["vid"], "quantity": p["quantity"]}
            for p in cj_products
        ],
    }

    token = await _cj_auth()
    try:
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post(
                f"{CJ_BASE}/shopping/order/createOrder",
                headers={"CJ-Access-Token": token},
                json=cj_body,
            )
            body = r.json()
    except Exception as e:
        logger.exception("CJ order createOrder failed")
        await db.orders.update_one(
            {"id": customer_order_id},
            {"$push": {"status_history": {
                "status": "supplier_error",
                "at": datetime.now(timezone.utc).isoformat(),
                "source": "cj_order",
                "error": str(e)[:300],
            }}},
        )
        return {"ok": False, "reason": "cj_request_failed", "error": str(e)[:300]}

    if not body.get("result"):
        err_msg = body.get("message") or "CJ rejected order"
        logger.warning(f"[cj-order] failed for {customer_order_id}: {err_msg}")
        await db.orders.update_one(
            {"id": customer_order_id},
            {"$push": {"status_history": {
                "status": "supplier_error",
                "at": datetime.now(timezone.utc).isoformat(),
                "source": "cj_order",
                "error": err_msg[:300],
            }}},
        )
        return {"ok": False, "reason": "cj_rejected", "error": err_msg}

    # CJ sometimes returns data as {orderId:...}, sometimes as a plain string = orderId.
    raw_data = body.get("data")
    if isinstance(raw_data, dict):
        cj_order_id = raw_data.get("orderId") or raw_data.get("id") or ""
    else:
        cj_order_id = str(raw_data or "")

    # Persist mapping (one per order for simplicity — CJ groups all lines)
    mapping_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    await db.order_mappings.insert_one({
        "id": mapping_id,
        "customer_order_id": customer_order_id,
        "site_id": order.get("site_id"),
        "provider": "cj",
        "cj_order_id": cj_order_id,
        "status": "placed",
        "tracking_number": None,
        "carrier": None,
        "cj_products": cj_products,
        "created_at": now,
        "last_sync_at": now,
    })
    await db.orders.update_one(
        {"id": customer_order_id},
        {"$set": {"supplier_order_id": cj_order_id, "supplier_provider": "cj"},
         "$push": {"status_history": {
             "status": "supplier_placed",
             "at": now,
             "source": "cj_order",
             "cj_order_id": cj_order_id,
         }}},
    )
    logger.info(f"[cj-order] placed cj_order_id={cj_order_id} for {customer_order_id}")
    return {"ok": True, "cj_order_id": cj_order_id, "placed": len(cj_products)}


async def sync_all_cj_tracking() -> dict:
    """Cron: iterate all open CJ order mappings and refresh their tracking.
    Pushes tracking_number onto the parent customer order and triggers the
    shipping email once (using status_history to dedupe).
    """
    if not CJ_API_KEY:
        return {"ok": False, "reason": "no_api_key"}

    from routes.emails import send_shipping_update

    cursor = db.order_mappings.find(
        {"provider": "cj",
         "cj_order_id": {"$ne": None},
         "status": {"$in": ["placed", "paid", "shipped"]}},
        {"_id": 0},
    )
    mappings = await cursor.to_list(500)
    ok, err = 0, 0
    token = await _cj_auth()
    headers = {"CJ-Access-Token": token}

    async with httpx.AsyncClient(timeout=25) as c:
        for m in mappings:
            try:
                # 1. Query order status + tracking
                await asyncio.sleep(1.1)  # Respect CJ 1 QPS
                r = await c.get(
                    f"{CJ_BASE}/shopping/order/query",
                    params={"orderId": m["cj_order_id"]},
                    headers=headers,
                )
                if r.status_code != 200:
                    err += 1
                    continue
                data = (r.json().get("data") or {})
                cj_status = (data.get("orderStatus") or data.get("status") or "").upper()
                tracking_number = data.get("trackNumber") or data.get("trackingNumber") or ""
                carrier = data.get("logisticsName") or data.get("logisticName") or ""
                internal = _CJ_STATUS_MAP.get(cj_status, m.get("status"))

                updates = {
                    "tracking_number": tracking_number or m.get("tracking_number"),
                    "carrier": carrier or m.get("carrier"),
                    "cj_status": cj_status,
                    "status": internal,
                    "last_sync_at": datetime.now(timezone.utc).isoformat(),
                }
                await db.order_mappings.update_one({"id": m["id"]}, {"$set": updates})

                # 2. Propagate to parent customer order
                if tracking_number:
                    parent_updates = {"tracking_number": tracking_number, "carrier": carrier}
                    if internal == "shipped":
                        parent_updates["status"] = "shipped"
                    elif internal == "delivered":
                        parent_updates["status"] = "delivered"
                    await db.orders.update_one(
                        {"id": m["customer_order_id"]},
                        {"$set": parent_updates,
                         "$push": {"status_history": {
                             "status": internal,
                             "at": datetime.now(timezone.utc).isoformat(),
                             "source": "cj_tracking",
                             "cj_status": cj_status,
                             "tracking_number": tracking_number,
                         }}},
                    )

                    # 3. Send "shipped" email once (dedup via already_sent flag)
                    if internal == "shipped" and not m.get("shipping_email_sent"):
                        parent_order = await db.orders.find_one(
                            {"id": m["customer_order_id"]}, {"_id": 0}
                        )
                        site = await db.sites.find_one(
                            {"id": m["site_id"]}, {"_id": 0}
                        )
                        if parent_order and site:
                            try:
                                await send_shipping_update(parent_order, site, tracking_number, carrier)
                                await db.order_mappings.update_one(
                                    {"id": m["id"]},
                                    {"$set": {"shipping_email_sent": True}},
                                )
                            except Exception:
                                logger.exception("[cj-tracking] shipping email failed")
                ok += 1
            except Exception:
                logger.exception(f"[cj-tracking-sync] failed for mapping {m.get('id')}")
                err += 1
    return {"provider": "cj", "total": len(mappings), "ok": ok, "errors": err}


@router.post("/sourcing/cj/sync-tracking")
async def cj_sync_tracking_manual(user: dict = Depends(get_current_user)):
    """Admin-triggered manual sync of all CJ trackings (same logic as the cron)."""
    if user.get("role") != "admin":
        raise HTTPException(403, "Admin only")
    return await sync_all_cj_tracking()

