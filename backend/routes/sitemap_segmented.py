"""TÂCHE 3.10 — Sitemap segmentation par type (Sprint 5 SEO).

Endpoints exposés (chacun un `<urlset>` valide) :
    GET /api/public/sites/{site_id}/sitemap-index.xml
    GET /api/public/sites/{site_id}/sitemap-products.xml
    GET /api/public/sites/{site_id}/sitemap-blog.xml
    GET /api/public/sites/{site_id}/sitemap-collections.xml
    GET /api/public/sites/{site_id}/sitemap-landings.xml
    GET /api/public/sites/{site_id}/sitemap-pages.xml

Le sitemap-index pointe vers les 5 sous-sitemaps. Chaque sous-sitemap utilise
les URLs canoniques (custom domain si vérifié, fallback platform).

Bonus : `POST /api/admin/sites/{site_id}/sitemap/ping-indexnow` qui notifie
IndexNow pour toutes les URLs (jusqu'à 10 000) après un batch (utile post
programmatic_seo).
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import List
from xml.sax.saxutils import escape as xml_escape

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from deps import db, get_current_user

logger = logging.getLogger("altiaro.sitemap_segmented")
router = APIRouter()


# ─────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────
def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


async def _resolve_site_base(site_id: str, request: Request) -> tuple:
    """Return (site, base_url) where base_url is the canonical public URL.

    Custom domain has priority if verified ; else platform fallback.
    """
    site = await db.sites.find_one(
        {"id": site_id},
        {"_id": 0, "id": 1, "custom_domain": 1, "custom_domain_verified": 1,
         "domain": 1},
    )
    if not site:
        raise HTTPException(404, "Site introuvable")

    domain = site.get("custom_domain") or ""
    verified = bool(site.get("custom_domain_verified"))
    if domain and verified:
        base = f"https://{domain}"
    else:
        # Fallback platform URL (preview/prod ingress)
        origin = (os.environ.get("PUBLIC_ORIGIN")
                   or os.environ.get("PUBLIC_FRONTEND_URL")
                   or os.environ.get("FRONTEND_URL")
                   or str(request.base_url).rstrip("/"))
        base = f"{origin}/shop/{site_id}"
    return site, base.rstrip("/")


def _wrap_urlset(urls: List[str]) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(urls) + "\n</urlset>\n"
    )


def _push_url(loc: str, *, priority: str = "0.7",
              lastmod: str | None = None,
              changefreq: str = "weekly") -> str:
    parts = [f"<url><loc>{xml_escape(loc)}</loc>"]
    if lastmod:
        parts.append(f"<lastmod>{xml_escape(str(lastmod)[:10])}</lastmod>")
    parts.append(f"<changefreq>{xml_escape(changefreq)}</changefreq>")
    parts.append(f"<priority>{xml_escape(priority)}</priority></url>")
    return "".join(parts)


# ─────────────────────────────────────────────────────────────────────
# Sitemap index (pointer to all sub-sitemaps)
# ─────────────────────────────────────────────────────────────────────
@router.get("/public/sites/{site_id}/sitemap-index.xml",
             tags=["sitemap-segmented"])
async def sitemap_index(site_id: str, request: Request):
    site, base = await _resolve_site_base(site_id, request)
    api_base = str(request.base_url).rstrip("/")
    sub_root = f"{api_base}/api/public/sites/{site_id}"
    today = _today()
    items = [
        "sitemap-products.xml",
        "sitemap-blog.xml",
        "sitemap-collections.xml",
        "sitemap-landings.xml",
        "sitemap-pages.xml",
    ]
    body = '<?xml version="1.0" encoding="UTF-8"?>\n<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for it in items:
        body += (
            f"<sitemap><loc>{xml_escape(sub_root + '/' + it)}</loc>"
            f"<lastmod>{xml_escape(today)}</lastmod></sitemap>\n"
        )
    body += "</sitemapindex>\n"
    return Response(content=body, media_type="application/xml")


# ─────────────────────────────────────────────────────────────────────
# Sub-sitemaps
# ─────────────────────────────────────────────────────────────────────
@router.get("/public/sites/{site_id}/sitemap-products.xml",
             tags=["sitemap-segmented"])
async def sitemap_products(site_id: str, request: Request):
    site, base = await _resolve_site_base(site_id, request)
    urls = []
    async for p in db.products.find(
        {"site_id": site_id, "status": "active"},
        {"_id": 0, "slug": 1, "id": 1, "updated_at": 1},
    ):
        slug = p.get("slug") or p.get("id")
        urls.append(_push_url(f"{base}/products/{slug}", priority="0.9",
                               lastmod=p.get("updated_at"),
                               changefreq="weekly"))
    return Response(content=_wrap_urlset(urls), media_type="application/xml")


@router.get("/public/sites/{site_id}/sitemap-blog.xml",
             tags=["sitemap-segmented"])
async def sitemap_blog(site_id: str, request: Request):
    site, base = await _resolve_site_base(site_id, request)
    urls = []
    async for bp in db.blog_posts.find(
        {"site_id": site_id, "status": {"$in": ["published", None]}},
        {"_id": 0, "slug": 1, "updated_at": 1, "created_at": 1},
    ):
        slug = bp.get("slug")
        if slug:
            urls.append(_push_url(
                f"{base}/blog/{slug}", priority="0.7",
                lastmod=bp.get("updated_at") or bp.get("created_at"),
                changefreq="monthly"))
    return Response(content=_wrap_urlset(urls), media_type="application/xml")


@router.get("/public/sites/{site_id}/sitemap-collections.xml",
             tags=["sitemap-segmented"])
async def sitemap_collections(site_id: str, request: Request):
    site, base = await _resolve_site_base(site_id, request)
    urls = []
    async for col in db.collections.find(
        {"site_id": site_id},
        {"_id": 0, "slug": 1, "updated_at": 1},
    ):
        slug = col.get("slug")
        if slug:
            urls.append(_push_url(
                f"{base}/collections/{slug}", priority="0.85",
                lastmod=col.get("updated_at"), changefreq="weekly"))
    return Response(content=_wrap_urlset(urls), media_type="application/xml")


@router.get("/public/sites/{site_id}/sitemap-landings.xml",
             tags=["sitemap-segmented"])
async def sitemap_landings(site_id: str, request: Request):
    """All landing_pages : buyer-guides, comparisons, top-lists, longtail
    (incl. programmatic_seo_v1) + glossary terms.
    """
    site, base = await _resolve_site_base(site_id, request)
    urls = []
    landing_paths = {
        "buyer_guide": ("buyer-guides", "0.8"),
        "comparison":  ("comparisons",  "0.7"),
        "top_list":    ("top-lists",    "0.7"),
        "longtail":    ("longtail",     "0.6"),
    }
    async for lp in db.landing_pages.find(
        {"site_id": site_id,
         "$or": [{"published": True}, {"status": "published"}],
         "kind": {"$in": list(landing_paths.keys())}},
        {"_id": 0, "slug": 1, "kind": 1, "updated_at": 1, "created_at": 1},
    ):
        prefix_priority = landing_paths.get(lp.get("kind"))
        if prefix_priority and lp.get("slug"):
            prefix, prio = prefix_priority
            urls.append(_push_url(
                f"{base}/{prefix}/{lp['slug']}", priority=prio,
                lastmod=lp.get("updated_at") or lp.get("created_at"),
                changefreq="monthly"))

    # Glossary terms
    async for t in db.glossary_terms.find(
        {"site_id": site_id,
         "$or": [{"published": True}, {"status": "published"}]},
        {"_id": 0, "slug": 1, "updated_at": 1},
    ):
        if t.get("slug"):
            urls.append(_push_url(
                f"{base}/glossary/{t['slug']}", priority="0.6",
                lastmod=t.get("updated_at"), changefreq="monthly"))

    return Response(content=_wrap_urlset(urls), media_type="application/xml")


@router.get("/public/sites/{site_id}/sitemap-pages.xml",
             tags=["sitemap-segmented"])
async def sitemap_pages(site_id: str, request: Request):
    """Static pages : home, about, faq, contact, legal, etc."""
    site, base = await _resolve_site_base(site_id, request)
    urls = [
        _push_url(f"{base}/", priority="1.0", changefreq="daily"),
        _push_url(f"{base}/about", priority="0.7", changefreq="monthly"),
        _push_url(f"{base}/faq", priority="0.6", changefreq="monthly"),
        _push_url(f"{base}/contact", priority="0.6", changefreq="monthly"),
        _push_url(f"{base}/blog", priority="0.7", changefreq="weekly"),
        _push_url(f"{base}/collections", priority="0.85", changefreq="weekly"),
        _push_url(f"{base}/products", priority="0.85", changefreq="weekly"),
        _push_url(f"{base}/livraison", priority="0.4", changefreq="yearly"),
        _push_url(f"{base}/retours", priority="0.4", changefreq="yearly"),
        _push_url(f"{base}/cgv", priority="0.3", changefreq="yearly"),
        _push_url(f"{base}/mentions", priority="0.3", changefreq="yearly"),
        _push_url(f"{base}/confidentialite", priority="0.3", changefreq="yearly"),
        _push_url(f"{base}/cookies", priority="0.3", changefreq="yearly"),
    ]
    return Response(content=_wrap_urlset(urls), media_type="application/xml")


# ─────────────────────────────────────────────────────────────────────
# IndexNow ping (post-batch notification)
# ─────────────────────────────────────────────────────────────────────
def _require_admin(user: dict):
    if not user or user.get("role") != "admin":
        raise HTTPException(403, "Admin required")


@router.post("/admin/sites/{site_id}/sitemap/ping-indexnow",
              tags=["sitemap-segmented"])
async def admin_ping_indexnow(site_id: str, request: Request,
                                limit: int = 1000,
                                user: dict = Depends(get_current_user)):
    """Notifie IndexNow pour toutes les URLs canoniques du site (jusqu'à `limit`).

    Utilise INDEXNOW_KEY de l'env. Bing/Yandex acceptent IndexNow.
    """
    _require_admin(user)
    site, base = await _resolve_site_base(site_id, request)
    indexnow_key = os.environ.get("INDEXNOW_KEY") or ""
    if not indexnow_key:
        raise HTTPException(400, "INDEXNOW_KEY not configured in .env")
    domain = base.replace("https://", "").replace("http://", "").split("/")[0]

    urls: List[str] = []
    # Products
    async for p in db.products.find(
        {"site_id": site_id, "status": "active"},
        {"_id": 0, "slug": 1, "id": 1},
    ):
        if len(urls) >= limit:
            break
        urls.append(f"{base}/products/{p.get('slug') or p.get('id')}")
    # Blogs
    async for bp in db.blog_posts.find(
        {"site_id": site_id, "status": {"$in": ["published", None]}},
        {"_id": 0, "slug": 1},
    ):
        if len(urls) >= limit:
            break
        if bp.get("slug"):
            urls.append(f"{base}/blog/{bp['slug']}")
    # Landings
    async for lp in db.landing_pages.find(
        {"site_id": site_id,
         "$or": [{"published": True}, {"status": "published"}]},
        {"_id": 0, "slug": 1, "kind": 1},
    ):
        if len(urls) >= limit:
            break
        kind = lp.get("kind") or "longtail"
        prefix = {"buyer_guide": "buyer-guides", "comparison": "comparisons",
                  "top_list": "top-lists"}.get(kind, kind)
        if lp.get("slug"):
            urls.append(f"{base}/{prefix}/{lp['slug']}")

    if not urls:
        return {"ok": False, "reason": "no_urls"}

    import httpx
    payload = {
        "host": domain,
        "key": indexnow_key,
        "keyLocation": f"{base}/{indexnow_key}.txt",
        "urlList": urls[:10000],  # IndexNow API max
    }
    try:
        async with httpx.AsyncClient(timeout=30) as cli:
            r = await cli.post("https://api.indexnow.org/indexnow", json=payload)
        ok = r.status_code in (200, 202)
        return {
            "ok": ok, "urls_pushed": len(urls), "status": r.status_code,
            "body": (r.text[:200] if r.text else None),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}
