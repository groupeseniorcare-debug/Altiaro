"""
Product URL import helpers.
Fetches the target page and extracts title/description/images/price from
Open Graph, JSON-LD, and Schema.org product markup.
Works best for Shopify, WooCommerce and well-structured storefronts.
Falls back gracefully (returns partial data) for AliExpress/CJ when JS renders the page.
"""
from __future__ import annotations

import json
import re
import logging
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger("conceptfactory.scraper")

DEFAULT_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
DEFAULT_HEADERS = {
    "User-Agent": DEFAULT_UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,*/*;q=0.8",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
}

PRICE_RE = re.compile(r"([\d]{1,6}(?:[.,]\d{1,2})?)")


def _clean_price(value) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip()
    m = PRICE_RE.search(s)
    if not m:
        return None
    raw = m.group(1).replace(",", ".")
    try:
        price = float(raw)
        # Sanity filter
        if 0.5 <= price <= 50000:
            return round(price, 2)
    except ValueError:
        return None
    return None


def _get_meta(soup: BeautifulSoup, *names: str) -> Optional[str]:
    for n in names:
        tag = soup.find("meta", attrs={"property": n}) or soup.find("meta", attrs={"name": n})
        if tag and tag.get("content"):
            return tag["content"].strip()
    return None


def _extract_from_jsonld(soup: BeautifulSoup) -> Dict[str, Any]:
    """Extract product data from JSON-LD <script> blocks."""
    out: Dict[str, Any] = {}
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            raw = script.string or script.get_text() or ""
            if not raw.strip():
                continue
            data = json.loads(raw)
        except Exception:
            continue
        items = data if isinstance(data, list) else [data]
        for item in items:
            if not isinstance(item, dict):
                continue
            if "@graph" in item and isinstance(item["@graph"], list):
                items.extend(item["@graph"])
                continue
            t = item.get("@type")
            types = t if isinstance(t, list) else [t]
            if not any((x or "").lower() == "product" for x in types):
                continue
            if not out.get("name") and item.get("name"):
                out["name"] = str(item["name"]).strip()
            if not out.get("description") and item.get("description"):
                out["description"] = str(item["description"]).strip()
            # image
            img = item.get("image")
            if img:
                if isinstance(img, list):
                    imgs = [str(i) for i in img if isinstance(i, (str,))]
                elif isinstance(img, dict) and img.get("url"):
                    imgs = [str(img["url"])]
                else:
                    imgs = [str(img)]
                out.setdefault("images", []).extend(imgs)
            # offers
            offers = item.get("offers")
            if offers:
                offer = offers[0] if isinstance(offers, list) else offers
                if isinstance(offer, dict):
                    price = _clean_price(offer.get("price") or offer.get("lowPrice"))
                    if price and not out.get("price"):
                        out["price"] = price
                    cur = offer.get("priceCurrency")
                    if cur and not out.get("currency"):
                        out["currency"] = str(cur).upper()
            if item.get("sku") and not out.get("sku"):
                out["sku"] = str(item["sku"])
    return out


def _parse_html(html: str, url: str) -> Dict[str, Any]:
    soup = BeautifulSoup(html, "lxml")
    data: Dict[str, Any] = {}

    # 1. Try JSON-LD first (most reliable)
    jsonld = _extract_from_jsonld(soup)
    data.update({k: v for k, v in jsonld.items() if v})

    # 2. Open Graph meta fallbacks
    if not data.get("name"):
        name = _get_meta(soup, "og:title", "twitter:title") or (soup.title.string.strip() if soup.title and soup.title.string else None)
        if name:
            data["name"] = name
    if not data.get("description"):
        desc = _get_meta(soup, "og:description", "twitter:description", "description")
        if desc:
            data["description"] = desc
    if not data.get("images"):
        og_image = _get_meta(soup, "og:image", "og:image:secure_url", "twitter:image")
        if og_image:
            data["images"] = [og_image]
    if not data.get("price"):
        for prop in ("product:price:amount", "og:price:amount", "price"):
            p = _get_meta(soup, prop)
            price = _clean_price(p)
            if price:
                data["price"] = price
                break
    if not data.get("currency"):
        cur = _get_meta(soup, "product:price:currency", "og:price:currency")
        if cur:
            data["currency"] = str(cur).upper()

    # 3. Shopify-specific : look for window.ShopifyAnalytics
    if not data.get("price"):
        for script in soup.find_all("script"):
            txt = script.get_text() or ""
            if "ShopifyAnalytics" in txt:
                m = re.search(r'"price":\s*(\d+)', txt)
                if m:
                    # Shopify stores prices in cents
                    cents = int(m.group(1))
                    if cents > 0:
                        data["price"] = round(cents / 100, 2)
                        break

    # 4. De-duplicate & sanitize images, keep max 6
    if data.get("images"):
        seen: List[str] = []
        for img in data["images"]:
            if not img or not isinstance(img, str):
                continue
            if img.startswith("//"):
                img = "https:" + img
            elif img.startswith("/"):
                parsed = urlparse(url)
                img = f"{parsed.scheme}://{parsed.netloc}{img}"
            if img not in seen:
                seen.append(img)
        data["images"] = seen[:6]

    # Defaults
    data.setdefault("currency", "EUR")
    data.setdefault("images", [])

    return data


async def import_from_url(url: str, timeout: float = 10.0) -> Dict[str, Any]:
    """Fetch a product page and extract a draft product dict.
    Returns at minimum name/description/images/price/currency/source_url."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("URL invalide (doit commencer par http:// ou https://)")

    try:
        async with httpx.AsyncClient(
            headers=DEFAULT_HEADERS,
            timeout=timeout,
            follow_redirects=True,
        ) as c:
            resp = await c.get(url)
            resp.raise_for_status()
            html = resp.text
    except httpx.TimeoutException:
        raise TimeoutError("Le site met trop de temps à répondre.")
    except httpx.HTTPStatusError as e:
        raise RuntimeError(f"Le site a retourné une erreur HTTP {e.response.status_code}.")
    except httpx.RequestError as e:
        raise RuntimeError(f"Impossible de joindre le site : {e}")

    data = _parse_html(html, url)
    data["source_url"] = url
    data["source_host"] = parsed.netloc
    return data
