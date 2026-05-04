"""Smart robots.txt + sitemap-prerender.xml — SSR fallback pour bots LLM.

Servir un robots.txt qui :
- Donne aux bots LLM/SEO un Sitemap pointé vers `sitemap-prerender.xml`
  qui liste les URLs prerenderées directement consommables en HTML brut.
- Pour les autres bots : comportement classique.

Montre les bots cibles : Googlebot, Bingbot, GPTBot, ClaudeBot,
PerplexityBot, CCBot, Google-Extended, Applebot, FacebookExternalHit, etc.
"""
from __future__ import annotations

from xml.sax.saxutils import escape as xml_escape
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import PlainTextResponse, Response

from deps import db

router = APIRouter(tags=["prerender-seo"])

LLM_BOTS = (
    "GPTBot", "ChatGPT-User", "ClaudeBot", "Claude-Web",
    "PerplexityBot", "CCBot", "Google-Extended", "Applebot",
    "YouBot", "AmazonBot",
)
SEO_BOTS = (
    "Googlebot", "Bingbot", "DuckDuckBot", "Yandex", "Slurp",
    "FacebookExternalHit", "Twitterbot", "LinkedInBot",
)


@router.get("/public/sites/{site_id}/robots.smart.txt", response_class=PlainTextResponse)
async def robots_smart(site_id: str, request: Request):
    """Robots.txt enrichi avec sitemap-prerender pour bots LLM/SEO."""
    site = await db.sites.find_one(
        {"id": site_id},
        {"_id": 0, "id": 1, "custom_domain": 1, "name": 1},
    )
    if not site:
        raise HTTPException(404, "Site introuvable")
    domain = site.get("custom_domain") or request.headers.get("host") or ""
    base = f"https://{domain}" if domain else ""
    api_base = str(request.base_url).rstrip("/")
    pre_sitemap = f"{api_base}/api/public/sites/{site_id}/sitemap-prerender.xml"
    main_sitemap = f"{base}/sitemap.xml" if base else f"{api_base}/api/public/sites/{site_id}/sitemap.xml"

    lines: list[str] = []
    # Default rules
    lines += [
        "User-agent: *",
        "Allow: /",
        "Disallow: /cart",
        "Disallow: /checkout",
        "Disallow: /account/",
        "Disallow: /api/",
        "",
    ]
    # LLM crawlers — explicit allow + prerender sitemap
    for ua in LLM_BOTS:
        lines += [
            f"User-agent: {ua}",
            "Allow: /",
            "Allow: /api/seo/prerender/",
            f"Sitemap: {pre_sitemap}",
            "",
        ]
    # SEO bots — main sitemap + prerender fallback
    for ua in SEO_BOTS:
        lines += [
            f"User-agent: {ua}",
            "Allow: /",
            "Allow: /api/seo/prerender/",
            "",
        ]
    lines += [
        f"Sitemap: {main_sitemap}",
        f"Sitemap: {pre_sitemap}",
        "",
    ]
    return "\n".join(lines)


@router.get("/public/sites/{site_id}/sitemap-prerender.xml")
async def sitemap_prerender(site_id: str, request: Request):
    site = await db.sites.find_one({"id": site_id}, {"_id": 0, "id": 1, "custom_domain": 1})
    if not site:
        raise HTTPException(404, "Site introuvable")

    api_base = str(request.base_url).rstrip("/")
    base_pre = f"{api_base}/api/seo/prerender/{site_id}?path="
    urls: list[str] = []

    def push(loc: str, priority: str = "0.7"):
        urls.append(
            f"<url><loc>{xml_escape(loc)}</loc>"
            f"<changefreq>weekly</changefreq>"
            f"<priority>{priority}</priority></url>"
        )

    # Home + about
    push(f"{base_pre}/", "1.0")
    push(f"{base_pre}/about", "0.8")

    # Products
    async for p in db.products.find(
        {"site_id": site_id, "status": "active"},
        {"_id": 0, "slug": 1, "id": 1},
    ):
        slug = p.get("slug") or p.get("id")
        push(f"{base_pre}/products/{slug}", "0.9")

    # Buyer guides + comparisons + top lists (landing_pages)
    kind_path = {"buyer_guide": "buyer-guides", "comparison": "compare", "top_list": "top"}
    async for lp in db.landing_pages.find(
        {"site_id": site_id, "published": True,
         "kind": {"$in": list(kind_path.keys())}},
        {"_id": 0, "slug": 1, "kind": 1},
    ):
        prefix = kind_path.get(lp.get("kind"))
        if prefix and lp.get("slug"):
            push(f"{base_pre}/{prefix}/{lp['slug']}", "0.8")

    # Glossary
    async for t in db.glossary_terms.find(
        {"site_id": site_id, "published": True},
        {"_id": 0, "slug": 1},
    ):
        if t.get("slug"):
            push(f"{base_pre}/glossary/{t['slug']}", "0.6")

    body = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(urls)
        + "\n</urlset>\n"
    )
    return Response(content=body, media_type="application/xml")
