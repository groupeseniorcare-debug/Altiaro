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
