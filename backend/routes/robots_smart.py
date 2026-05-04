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
    """Sitemap dédié au pipeline Dynamic Rendering — couvre TOUTES les pages
    indexables servies par `routes/prerender.py`.

    Phase 1 — 2026-05-04 : ajout des types blog, collections, longtail,
    alignement des paths sur la convention canonique `/comparisons/` et
    `/top-lists/` (avec aliases legacy `/compare/` et `/top/` toujours
    supportés côté prerender pour back-compat).

    Hiérarchie priorités :
      home 1.0 · about 0.8 · products 0.9 · buyer-guides 0.8
      comparisons / top-lists 0.7 · glossary / blog 0.6
      longtail / collections 0.5
    """
    site = await db.sites.find_one(
        {"id": site_id},
        {"_id": 0, "id": 1, "custom_domain": 1, "default_locale": 1},
    )
    if not site:
        raise HTTPException(404, "Site introuvable")

    api_base = str(request.base_url).rstrip("/")
    base_pre = f"{api_base}/api/seo/prerender/{site_id}?path="
    urls: list[str] = []

    def push(loc: str, priority: str = "0.7", lastmod: str | None = None,
             changefreq: str = "weekly"):
        url_xml = f"<url><loc>{xml_escape(loc)}</loc>"
        if lastmod:
            # Supporte ISO datetime et `YYYY-MM-DD`. On garde la date seule.
            url_xml += f"<lastmod>{xml_escape(str(lastmod)[:10])}</lastmod>"
        url_xml += (
            f"<changefreq>{xml_escape(changefreq)}</changefreq>"
            f"<priority>{xml_escape(priority)}</priority></url>"
        )
        urls.append(url_xml)

    # Home + about (changefreq weekly)
    push(f"{base_pre}/", priority="1.0", changefreq="weekly")
    push(f"{base_pre}/about", priority="0.8", changefreq="monthly")

    # Products
    async for p in db.products.find(
        {"site_id": site_id, "status": "active"},
        {"_id": 0, "slug": 1, "id": 1, "updated_at": 1},
    ):
        slug = p.get("slug") or p.get("id")
        push(f"{base_pre}/products/{slug}", priority="0.9",
             lastmod=p.get("updated_at"), changefreq="weekly")

    # Landing pages : buyer_guide / comparison / top_list / longtail
    # Convention canonique 2026-05-04 : /comparisons/ et /top-lists/ (avec
    # alias rétrocompat /compare/ et /top/ supportés en prerender mais NON
    # listés dans le sitemap pour éviter la duplication d'index).
    landing_paths = {
        "buyer_guide": ("buyer-guides",  "0.8"),
        "comparison":  ("comparisons",   "0.7"),
        "top_list":    ("top-lists",     "0.7"),
        "longtail":    ("longtail",      "0.5"),
    }
    async for lp in db.landing_pages.find(
        {"site_id": site_id, "published": True,
         "kind": {"$in": list(landing_paths.keys())}},
        {"_id": 0, "slug": 1, "kind": 1, "updated_at": 1},
    ):
        prefix_priority = landing_paths.get(lp.get("kind"))
        if prefix_priority and lp.get("slug"):
            prefix, prio = prefix_priority
            push(f"{base_pre}/{prefix}/{lp['slug']}",
                 priority=prio, lastmod=lp.get("updated_at"),
                 changefreq="monthly")

    # Glossary
    async for t in db.glossary_terms.find(
        {"site_id": site_id, "published": True},
        {"_id": 0, "slug": 1, "updated_at": 1},
    ):
        if t.get("slug"):
            push(f"{base_pre}/glossary/{t['slug']}", priority="0.6",
                 lastmod=t.get("updated_at"), changefreq="monthly")

    # Blog
    async for bp in db.blog_posts.find(
        {"site_id": site_id, "status": {"$in": ["published", None]}},
        {"_id": 0, "slug": 1, "updated_at": 1, "created_at": 1},
    ):
        if bp.get("slug"):
            push(f"{base_pre}/blog/{bp['slug']}", priority="0.6",
                 lastmod=bp.get("updated_at") or bp.get("created_at"),
                 changefreq="weekly")

    # Collections
    async for col in db.collections.find(
        {"site_id": site_id},
        {"_id": 0, "slug": 1, "updated_at": 1},
    ):
        if col.get("slug"):
            push(f"{base_pre}/collections/{col['slug']}", priority="0.5",
                 lastmod=col.get("updated_at"), changefreq="weekly")

    body = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(urls)
        + "\n</urlset>\n"
    )
    return Response(content=body, media_type="application/xml")
