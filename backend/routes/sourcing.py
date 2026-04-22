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
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"kw-trans-{uuid.uuid4().hex[:6]}",
            system_message=(
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
        ).with_model("anthropic", "claude-sonnet-4-5-20250929")
        raw = await asyncio.wait_for(
            chat.send_message(UserMessage(text=f"Translate: {keyword}")),
            timeout=10,
        )
        en = (raw if isinstance(raw, str) else str(raw)).strip().strip('"').strip("'").lower()
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
    # Load site to determine target translation languages + shipping destinations
    site = await db.sites.find_one({"id": site_id}, {"_id": 0, "selected_countries": 1})
    countries = (site or {}).get("selected_countries") or ["FR"]
    target_langs = list(set(LANG_BY_COUNTRY.get((c or "").upper(), "fr") for c in countries))
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
        # Check shipping availability to each target country
        first_vid = variants[0]["vid"] if variants else ""
        if first_vid:
            for cc in countries[:6]:  # Cap at 6 to respect rate-limit
                await asyncio.sleep(1.1)  # Respect CJ 1 QPS
                options = await _cj_freight_to_country(data.product_id, first_vid, (cc or "FR").upper())
                if options:
                    # Pick cheapest
                    cheapest = min(
                        options,
                        key=lambda o: float(o.get("logisticPrice") or 9999) if o.get("logisticPrice") is not None else 9999,
                    )
                    shipping_by_country[cc.upper()] = {
                        "available": True,
                        "carrier": cheapest.get("logisticName") or cheapest.get("logisticAliasName") or "CJ",
                        "price_usd": float(cheapest.get("logisticPrice") or 0),
                        "delivery_days": cheapest.get("logisticAging") or "",
                        "options_count": len(options),
                    }
                else:
                    shipping_by_country[cc.upper()] = {"available": False}

    # Strip HTML from CJ description
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
        "images": images[:8],
        "stock": None,
        "supplier_url": data.supplier_url or "",
        "sku": data.sku or f"{data.provider.upper()}-{data.product_id[:12]}",
        "status": "draft",
        "featured": False,
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


@router.post("/sites/{site_id}/sourcing/import-by-url")
async def import_by_url(site_id: str, data: ImportUrlInput, user: dict = Depends(get_current_user)):
    """Import a product directly from its provider URL (no search needed)."""
    await _check_site_access(site_id, user)
    provider, product_id = _parse_provider_url(data.url)

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
            raise HTTPException(503, "AliExpress Affiliate non configuré.")
        try:
            resp = await _ae_call(
                "aliexpress.affiliate.productdetail.get",
                {"product_ids": product_id, "target_currency": "USD", "target_language": "EN",
                 "tracking_id": AE_TRACKING_ID or "default"},
            )
            items = (((resp or {}).get("aliexpress_affiliate_productdetail_get_response") or {})
                     .get("resp_result") or {}).get("result") or {}
            prods = (items.get("products") or {}).get("product") or []
            if prods:
                p = prods[0]
                title = p.get("product_title") or ""
                image = p.get("product_main_image_url") or ""
                try:
                    cost_usd = float(p.get("target_sale_price") or p.get("sale_price") or 0)
                except (ValueError, TypeError):
                    cost_usd = 0.0
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(502, f"AliExpress indisponible : {str(e)[:180]}")

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
    )
    # Respect CJ 1 QPS: sleep before the import (which will call detail again for specs)
    if provider == "cj":
        await asyncio.sleep(1.2)
    # Delegate to the existing importer (handles translation + specs + shipping + save)
    return await import_product(site_id, import_payload, user)
