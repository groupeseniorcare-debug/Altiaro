"""Dynamic Rendering — SSR HTML pour bots.

Endpoint backend qui retourne un HTML complet (avec title + meta + JSON-LD
+ contenu principal) pour les pages SEO critiques d'un site. Pour servir
ce HTML aux bots automatiquement, il faut un proxy en amont (Approximated
ou Cloudflare Worker) qui détecte le User-Agent et fait un sub-request à
cet endpoint au lieu du SPA. Pour l'instant, l'URL est exposée directement
et peut être pointée depuis robots.txt / sitemap pour les LLM crawlers.

GET /api/seo/prerender/{site_id}?path=/products/{slug}
  -> 200 text/html avec contenu pré-rendu serveur-side
"""
from __future__ import annotations

import html
import json
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, PlainTextResponse

from deps import db

router = APIRouter(tags=["prerender"])
logger = logging.getLogger("altiaro.prerender")

BOT_UA_NEEDLES = (
    "googlebot", "bingbot", "slurp", "duckduckbot", "baiduspider",
    "yandexbot", "facebookexternalhit", "twitterbot", "linkedinbot",
    "discordbot", "slackbot", "telegrambot", "whatsapp",
    "gptbot", "chatgpt-user", "claude-web", "claudebot", "anthropic",
    "perplexitybot", "ccbot", "google-extended", "applebot",
)


def _is_bot(ua: str) -> bool:
    ua = (ua or "").lower()
    return any(n in ua for n in BOT_UA_NEEDLES)


def _h(s: Any) -> str:
    return html.escape(str(s or ""), quote=True)


def _pick_lang(v: Any, lang: str = "fr") -> str:
    if isinstance(v, dict):
        return v.get(lang) or v.get("fr") or v.get("en") or next(iter(v.values()), "")
    return str(v or "")


async def _render_pdp(site: dict, slug: str) -> Optional[str]:
    p = await db.products.find_one(
        {"site_id": site["id"], "$or": [{"slug": slug}, {"id": slug}], "status": "active"},
        {"_id": 0},
    )
    if not p:
        return None
    name = _pick_lang(p.get("name"))
    desc = (p.get("aeo_snippet") or _pick_lang((p.get("narrative") or {}).get("subheadline"))
            or _pick_lang(p.get("description")))[:300]
    domain = site.get("custom_domain") or ""
    canonical = f"https://{domain}/products/{p.get('slug') or slug}" if domain else ""
    images = [im.get("url") for im in (p.get("generated_images") or []) if isinstance(im, dict) and im.get("url")][:6]
    if not images:
        images = [u for u in (p.get("images") or []) if isinstance(u, str)][:6]
    price = p.get("price") or p.get("selling_price") or 0
    currency = p.get("currency") or "EUR"
    jsonld = {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": name,
        "description": desc,
        "image": images,
        "sku": p.get("sku") or p.get("id"),
        "brand": {"@type": "Brand", "name": (site.get("design") or {}).get("brand", {}).get("name") or site.get("name")},
        "offers": {"@type": "Offer", "price": price, "priceCurrency": currency, "url": canonical, "availability": "https://schema.org/InStock"},
    }
    return f"""<!doctype html><html lang="fr"><head>
<meta charset="utf-8"/>
<title>{_h(name)} — {_h(site.get('name',''))}</title>
<meta name="description" content="{_h(desc)}"/>
<link rel="canonical" href="{_h(canonical)}"/>
<meta property="og:title" content="{_h(name)}"/>
<meta property="og:description" content="{_h(desc)}"/>
<meta property="og:type" content="product"/>
<meta property="og:url" content="{_h(canonical)}"/>
{("<meta property='og:image' content='" + _h(images[0]) + "'/>") if images else ""}
<script type="application/ld+json">{html.escape(json.dumps(jsonld, ensure_ascii=False))}</script>
</head><body>
<header><a href="/">{_h(site.get('name',''))}</a></header>
<main>
<h1>{_h(name)}</h1>
<p>{_h(desc)}</p>
<p><strong>Prix : {_h(price)} {_h(currency)}</strong></p>
{"".join("<img src='%s' alt='%s' loading='lazy'/>" % (_h(u), _h(name)) for u in images[:3])}
</main>
<footer><a href="{_h(canonical)}">Voir la fiche complète</a></footer>
</body></html>"""


async def _render_buyer_guide(site: dict, slug: str) -> Optional[str]:
    g = await db.landing_pages.find_one({"site_id": site["id"], "slug": slug, "kind": "buyer_guide"}, {"_id": 0})
    if not g:
        return None
    domain = site.get("custom_domain") or ""
    canonical = f"https://{domain}/buyer-guides/{slug}" if domain else ""
    sections_html = "".join(
        f"<section><h2>{_h(s.get('h2',''))}</h2><div>{_h(s.get('body_md',''))}</div></section>"
        for s in (g.get("sections") or [])
    )
    faq_html = "".join(
        f"<details><summary>{_h(f.get('q',''))}</summary><p>{_h(f.get('a',''))}</p></details>"
        for f in (g.get("faq") or [])
    )
    jsonld = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": g.get("h1") or g.get("title"),
        "description": g.get("meta_description"),
        "datePublished": g.get("created_at"),
        "dateModified": g.get("updated_at"),
        "author": {"@type": "Organization", "name": (site.get("design") or {}).get("brand", {}).get("name") or site.get("name")},
    }
    return f"""<!doctype html><html lang="fr"><head>
<meta charset="utf-8"/>
<title>{_h(g.get('title') or g.get('h1'))}</title>
<meta name="description" content="{_h(g.get('meta_description'))}"/>
<link rel="canonical" href="{_h(canonical)}"/>
<script type="application/ld+json">{html.escape(json.dumps(jsonld, ensure_ascii=False))}</script>
</head><body>
<h1>{_h(g.get('h1') or g.get('title'))}</h1>
<p>{_h(g.get('intro',''))}</p>
{sections_html}
<section><h2>FAQ</h2>{faq_html}</section>
</body></html>"""


async def _render_glossary_term(site: dict, slug: str) -> Optional[str]:
    t = await db.glossary_terms.find_one({"site_id": site["id"], "slug": slug}, {"_id": 0})
    if not t:
        return None
    domain = site.get("custom_domain") or ""
    canonical = f"https://{domain}/glossary/{slug}" if domain else ""
    jsonld = {"@context": "https://schema.org", "@type": "DefinedTerm",
              "name": t.get("term"), "description": t.get("definition")}
    return f"""<!doctype html><html lang="fr"><head>
<meta charset="utf-8"/>
<title>{_h(t.get('term'))} — {_h(site.get('name',''))}</title>
<meta name="description" content="{_h((t.get('definition') or '')[:160])}"/>
<link rel="canonical" href="{_h(canonical)}"/>
<script type="application/ld+json">{html.escape(json.dumps(jsonld, ensure_ascii=False))}</script>
</head><body>
<h1>{_h(t.get('term'))}</h1>
<p>{_h(t.get('definition'))}</p>
</body></html>"""


@router.get("/seo/prerender/{site_id}", response_class=HTMLResponse)
async def prerender(site_id: str, request: Request, path: str = Query(..., description="e.g. /products/fauteuil-...")):
    site = await db.sites.find_one({"id": site_id}, {"_id": 0})
    if not site:
        raise HTTPException(404, "Site introuvable")
    p = (path or "/").strip()
    body: Optional[str] = None
    if p.startswith("/products/"):
        body = await _render_pdp(site, p.split("/", 2)[2].split("?")[0])
    elif p.startswith("/buyer-guides/"):
        body = await _render_buyer_guide(site, p.split("/", 2)[2].split("?")[0])
    elif p.startswith("/glossary/"):
        body = await _render_glossary_term(site, p.split("/", 2)[2].split("?")[0])
    elif p in ("/", "/about"):
        # Minimal home/about prerender — enough for bots to grab the brand
        domain = site.get("custom_domain") or ""
        about = site.get("about_rich") or {}
        body = (
            f"<!doctype html><html lang='fr'><head><meta charset='utf-8'/>"
            f"<title>{_h(site.get('name',''))} — {_h(about.get('tagline',''))}</title>"
            f"<meta name='description' content='{_h(about.get('mission','')[:160])}'/>"
            f"<link rel='canonical' href='https://{_h(domain)}{_h(p)}'/></head>"
            f"<body><h1>{_h(site.get('name',''))}</h1>"
            f"<p>{_h(about.get('tagline',''))}</p>"
            f"<p>{_h(about.get('mission',''))}</p>"
            f"<p>{_h(about.get('story','')[:1500])}</p></body></html>"
        )
    if not body:
        raise HTTPException(404, f"Path {p} non pré-rendu (formats supportés : /, /about, /products/{{slug}}, /buyer-guides/{{slug}}, /glossary/{{slug}})")
    headers = {"Cache-Control": "public, max-age=300", "X-Prerender": "altiaro"}
    return HTMLResponse(content=body, headers=headers)
