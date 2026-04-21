"""SEO utilities (Sprint 17) — sitemap.xml multi-pays + hreflang support."""
from __future__ import annotations
import os
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from datetime import datetime, timezone
from deps import db

router = APIRouter()

# Supported language codes mapped to country codes of the site
LANG_BY_COUNTRY = {
    "FR": "fr", "BE": "fr", "LU": "fr", "CH": "fr",
    "DE": "de", "AT": "de",
    "UK": "en", "IE": "en",
    "NL": "nl", "IT": "it", "ES": "es",
}


def _origin() -> str:
    return os.environ.get("PUBLIC_ORIGIN") or "https://senior-france.preview.emergentagent.com"


@router.get("/public/sites/{site_id}/sitemap.xml")
async def sitemap(site_id: str):
    site = await db.sites.find_one({"id": site_id}, {"_id": 0})
    if not site:
        raise HTTPException(404, "Site introuvable")
    origin = _origin()
    base = f"{origin}/shop/{site_id}"
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Build languages from selected countries
    langs = sorted({LANG_BY_COUNTRY.get((c or "").upper(), "en")
                   for c in (site.get("selected_countries") or ["FR"])})
    if not langs:
        langs = ["fr"]

    products = await db.products.find(
        {"site_id": site_id, "status": "active"}, {"_id": 0, "id": 1, "name": 1}
    ).to_list(5000)

    def urlset(path: str, prio: str = "0.8") -> str:
        alts = "".join(
            f'<xhtml:link rel="alternate" hreflang="{lg}" href="{base}{path}?lang={lg}"/>'
            for lg in langs
        )
        return (f"<url><loc>{base}{path}</loc><lastmod>{now}</lastmod>"
                f"<changefreq>weekly</changefreq><priority>{prio}</priority>{alts}</url>")

    urls = [urlset("", "1.0"), urlset("/about"), urlset("/faq"), urlset("/contact"),
            urlset("/cgv", "0.3"), urlset("/mentions", "0.3"), urlset("/confidentialite", "0.3")]
    for p in products:
        urls.append(urlset(f"/product/{p['id']}", "0.7"))

    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
           'xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
           + "\n".join(urls) + "\n</urlset>")
    return Response(content=xml, media_type="application/xml")


@router.get("/public/sites/{site_id}/robots.txt")
async def robots(site_id: str):
    site = await db.sites.find_one({"id": site_id}, {"_id": 0, "id": 1})
    if not site:
        raise HTTPException(404, "Site introuvable")
    content = (f"User-agent: *\nAllow: /shop/{site_id}/\n"
               f"Sitemap: {_origin()}/api/public/sites/{site_id}/sitemap.xml\n")
    return Response(content=content, media_type="text/plain")


def _xml_escape(s: str) -> str:
    if s is None:
        return ""
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
               .replace(">", "&gt;").replace('"', "&quot;").replace("'", "&apos;"))


@router.get("/public/sites/{site_id}/merchant-feed.xml")
async def merchant_feed(site_id: str, country: str = "FR"):
    """Google Merchant Center RSS 2.0 feed (conforme Google Shopping).
    Exposé par pays via ?country=FR|DE|BE|NL|UK|CH."""
    site = await db.sites.find_one({"id": site_id}, {"_id": 0})
    if not site:
        raise HTTPException(404, "Site introuvable")
    origin = _origin()
    base = f"{origin}/shop/{site_id}"
    country = (country or "FR").upper()
    lang = LANG_BY_COUNTRY.get(country, "fr")

    currency_by_country = {
        "FR": "EUR", "BE": "EUR", "LU": "EUR", "NL": "EUR",
        "DE": "EUR", "AT": "EUR", "IT": "EUR", "ES": "EUR", "IE": "EUR",
        "CH": "CHF", "UK": "GBP",
    }
    currency = currency_by_country.get(country, "EUR")

    products = await db.products.find(
        {"site_id": site_id, "status": "active"},
        {"_id": 0}
    ).to_list(5000)

    items = []
    for p in products:
        name_dict = p.get("name") or {}
        desc_dict = p.get("description") or {}
        title = (name_dict.get(lang) if isinstance(name_dict, dict) else str(name_dict or "")) or \
                (name_dict.get("fr") if isinstance(name_dict, dict) else "") or "Produit"
        desc = (desc_dict.get(lang) if isinstance(desc_dict, dict) else str(desc_dict or "")) or \
               (desc_dict.get("fr") if isinstance(desc_dict, dict) else "") or title
        price = float(p.get("price") or 0)
        img = (p.get("images") or [""])[0]
        pid = p.get("id")
        sku = p.get("sku") or pid
        stock = p.get("stock")
        availability = "in stock" if (stock is None or stock > 0) else "out of stock"

        items.append(
            f"<item>"
            f"<g:id>{_xml_escape(sku)}</g:id>"
            f"<g:title>{_xml_escape(title)[:150]}</g:title>"
            f"<g:description>{_xml_escape(desc)[:5000]}</g:description>"
            f"<g:link>{base}/product/{pid}?lang={lang}</g:link>"
            f"<g:image_link>{_xml_escape(img)}</g:image_link>"
            f"<g:availability>{availability}</g:availability>"
            f"<g:price>{price:.2f} {currency}</g:price>"
            f"<g:brand>{_xml_escape(site.get('name') or 'Brand')}</g:brand>"
            f"<g:condition>new</g:condition>"
            f"<g:identifier_exists>false</g:identifier_exists>"
            f"<g:shipping><g:country>{country}</g:country>"
            f"<g:service>Standard</g:service><g:price>0.00 {currency}</g:price></g:shipping>"
            f"</item>"
        )

    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0" xmlns:g="http://base.google.com/ns/1.0">\n'
        '<channel>\n'
        f'<title>{_xml_escape(site.get("name") or "Shop")} — {country}</title>\n'
        f'<link>{base}</link>\n'
        f'<description>Flux produits Google Merchant Center</description>\n'
        + "\n".join(items) +
        "\n</channel>\n</rss>"
    )
    return Response(content=xml, media_type="application/xml")
