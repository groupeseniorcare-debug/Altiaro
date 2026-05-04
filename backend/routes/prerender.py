"""Dynamic Rendering — SSR HTML pour bots et LLM crawlers.

Endpoints exposés :
    GET /api/seo/prerender/{site_id}?path=/products/...
        → 200 text/html (HTML brut, sans JS, prêt à indexer)

Architecture (Phase 1 — 2026-05-04) :
    Le module expose deux APIs :
      - le router HTTP (utilisé par robots.smart.txt + sitemap-prerender)
      - une API programmatique `prerender_html(site, path) -> Optional[str]`
        consommée par le middleware UA-routing edge-level
        (`prerender_routing_middleware`) sans re-router HTTP.

Paths supportés :
    /                       → home (lit cms_pages.about + design.brand)
    /about                  → page "à propos" (cascade cms_pages.about → design.about → fallback)
    /products/{slug}        → fiche produit
    /buyer-guides/{slug}    → guide d'achat
    /glossary/{slug}        → terme glossaire
    /comparisons/{slug}     → comparatif (alias rétrocompat : /compare/{slug})
    /top-lists/{slug}       → top liste (alias rétrocompat : /top/{slug})
    /longtail/{slug}        → landing long-tail
    /blog/{slug}            → article blog
    /collections/{slug}     → collection (catégorie)

Règles HTML :
    - <html lang="..."> dynamique selon site.default_locale (fallback "fr")
    - <head> enrichi : title, meta description, canonical, OG, JSON-LD adapté
    - Charte sobre : font-family serif, max-width 760px, margins propres
    - Pas de troncature aggressive : contenu réel laissé passer
"""
from __future__ import annotations

import html
import json
import logging
import re
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse

from deps import db

router = APIRouter(tags=["prerender"])
logger = logging.getLogger("altiaro.prerender")

# ---------------------------------------------------------------------------
# Helpers communs
# ---------------------------------------------------------------------------

def _h(s: Any) -> str:
    """HTML-escape (avec quotes pour usage attribut)."""
    return html.escape(str(s or ""), quote=True)


def _pick_lang(v: Any, lang: str = "fr") -> str:
    """Extrait la langue préférée d'un champ multilingue (dict ou str)."""
    if isinstance(v, dict):
        return v.get(lang) or v.get("fr") or v.get("en") or next(iter(v.values()), "")
    return str(v or "")


def _site_lang(site: dict) -> str:
    """Langue par défaut du site (fallback 'fr')."""
    return (site.get("default_locale") or site.get("default_language") or "fr").split("-")[0]


def _site_brand_name(site: dict) -> str:
    return ((site.get("design") or {}).get("brand") or {}).get("name") or site.get("name") or ""


# Markdown → HTML très simple (pas de dépendance lourde, suffit pour bots).
# Supporte : h1/h2/h3, paragraphes, **bold**, *italic*, [link](url), listes -.
_MD_BOLD = re.compile(r"\*\*([^*]+)\*\*")
_MD_ITAL = re.compile(r"(?<!\*)\*([^*]+)\*(?!\*)")
_MD_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def _md_to_html(md: str) -> str:
    """Conversion markdown → HTML minimaliste safe-for-bots (escape d'abord)."""
    if not md:
        return ""
    txt = html.escape(md, quote=False)
    out: list[str] = []
    in_list = False
    for line in txt.split("\n"):
        ln = line.rstrip()
        if not ln.strip():
            if in_list:
                out.append("</ul>")
                in_list = False
            out.append("")
            continue
        # Listes -
        if ln.lstrip().startswith("- "):
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append(f"<li>{ln.lstrip()[2:]}</li>")
            continue
        if in_list:
            out.append("</ul>")
            in_list = False
        # Headings
        if ln.startswith("### "):
            out.append(f"<h3>{ln[4:]}</h3>")
        elif ln.startswith("## "):
            out.append(f"<h2>{ln[3:]}</h2>")
        elif ln.startswith("# "):
            out.append(f"<h1>{ln[2:]}</h1>")
        else:
            out.append(f"<p>{ln}</p>")
    if in_list:
        out.append("</ul>")
    rendered = "\n".join(out)
    # Inline replacements (post-block pour ne pas casser le markdown structurel)
    rendered = _MD_BOLD.sub(r"<strong>\1</strong>", rendered)
    rendered = _MD_ITAL.sub(r"<em>\1</em>", rendered)
    rendered = _MD_LINK.sub(r'<a href="\2">\1</a>', rendered)
    return rendered


def _base_style() -> str:
    """Charte sobre commune à toutes les pages prerender (les bots se moquent
    du visuel mais on garde une présentation propre pour audit humain)."""
    return (
        "body{font-family:Georgia,serif;max-width:760px;margin:2rem auto;"
        "padding:0 1rem;color:#1c1917;line-height:1.65;}"
        "h1{font-size:2rem;margin-bottom:.5rem;}"
        "h2{font-size:1.4rem;margin-top:2rem;}"
        "h3{font-size:1.15rem;margin-top:1.5rem;}"
        "p{margin:1em 0;}"
        "img{max-width:100%;height:auto;border-radius:6px;}"
        "header,footer{color:#78716c;font-size:.9rem;}"
        "table{border-collapse:collapse;width:100%;margin:1em 0;}"
        "td,th{border:1px solid #e7e5e4;padding:.5rem;text-align:left;vertical-align:top;}"
        "details{margin:.5em 0;border:1px solid #e7e5e4;padding:.6em;border-radius:6px;}"
        "summary{cursor:pointer;font-weight:600;}"
    )


def _render_head(
    *, lang: str, title: str, description: str, canonical: str,
    og_type: str = "website", og_image: str = "",
    jsonld: Optional[dict] = None,
) -> str:
    """Génère le bloc <head> standard."""
    desc_safe = _h(description[:200])
    parts = [
        f"<!doctype html><html lang='{_h(lang)}'><head>",
        "<meta charset='utf-8'/>",
        "<meta name='viewport' content='width=device-width,initial-scale=1'/>",
        f"<title>{_h(title)}</title>",
        f"<meta name='description' content='{desc_safe}'/>",
        f"<link rel='canonical' href='{_h(canonical)}'/>",
        f"<meta property='og:title' content='{_h(title)}'/>",
        f"<meta property='og:description' content='{desc_safe}'/>",
        f"<meta property='og:type' content='{_h(og_type)}'/>",
        f"<meta property='og:url' content='{_h(canonical)}'/>",
    ]
    if og_image:
        parts.append(f"<meta property='og:image' content='{_h(og_image)}'/>")
    if jsonld:
        parts.append(
            f"<script type='application/ld+json'>"
            f"{html.escape(json.dumps(jsonld, ensure_ascii=False), quote=False)}"
            f"</script>"
        )
    parts.append(f"<style>{_base_style()}</style>")
    parts.append("</head>")
    return "".join(parts)


# ---------------------------------------------------------------------------
# Renderers par type de page
# ---------------------------------------------------------------------------

async def _render_home(site: dict) -> str:
    """Home — extraction propre depuis cms_pages.about (premium) ou design.about (legacy)."""
    lang = _site_lang(site)
    domain = site.get("custom_domain") or ""
    canonical = f"https://{domain}/" if domain else ""
    brand = _site_brand_name(site)
    design = site.get("design") or {}

    # Cascade : cms_pages.about (premium) → design.about (legacy) → fallback
    cms_about = (design.get("cms_pages") or {}).get("about") or {}
    legacy_about = design.get("about") or {}
    hero = design.get("hero") or {}

    title = brand
    tagline = (
        cms_about.get("subtitle")
        or _pick_lang((legacy_about.get("headline") or {}), lang)
        or _pick_lang(hero.get("subheadline"), lang)
        or ""
    )
    if tagline:
        title = f"{brand} — {tagline}"
    description = (
        tagline
        or _pick_lang(hero.get("headline"), lang)
        or f"Bienvenue sur {brand}"
    )
    intro_md = (
        cms_about.get("body_md")
        or "\n\n".join(_pick_lang(p, lang) for p in (legacy_about.get("paragraphs") or []))
    )
    intro_html = _md_to_html(intro_md[:2400]) if intro_md else f"<p>{_h(description)}</p>"

    jsonld = {
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": brand,
        "url": canonical or None,
        "description": description[:300],
    }
    head = _render_head(
        lang=lang, title=title, description=description,
        canonical=canonical, og_type="website",
        og_image=(hero.get("image_url") or ""),
        jsonld=jsonld,
    )
    body = (
        "<body>"
        f"<header><a href='/'>{_h(brand)}</a></header>"
        f"<main><h1>{_h(brand)}</h1>"
        f"<p><strong>{_h(tagline)}</strong></p>"
        f"{intro_html}</main>"
        f"<footer>© {_h(brand)}</footer>"
        "</body></html>"
    )
    return head + body


async def _render_about(site: dict) -> str:
    """About — cascade cms_pages.about → design.about → fallback générique."""
    lang = _site_lang(site)
    domain = site.get("custom_domain") or ""
    canonical = f"https://{domain}/about" if domain else ""
    brand = _site_brand_name(site)
    design = site.get("design") or {}

    cms_about = (design.get("cms_pages") or {}).get("about") or {}
    legacy_about = design.get("about") or {}

    if cms_about:
        title = f"{cms_about.get('title') or 'À propos'} — {brand}"
        subtitle = cms_about.get("subtitle") or ""
        body_md = cms_about.get("body_md") or ""
        highlights = cms_about.get("highlights") or []
        body_html = _md_to_html(body_md)
        hl_html = ""
        if highlights:
            hl_items = "".join(
                f"<section><h3>{_h(h.get('title',''))}</h3>"
                f"<p>{_h(h.get('body',''))}</p></section>"
                for h in highlights if isinstance(h, dict)
            )
            hl_html = f"<section><h2>Nos engagements</h2>{hl_items}</section>"
        description = subtitle or body_md[:200]
        main = (
            f"<h1>{_h(cms_about.get('title') or 'À propos')}</h1>"
            f"<p><em>{_h(subtitle)}</em></p>"
            f"{body_html}{hl_html}"
        )
    elif legacy_about:
        headline = _pick_lang(legacy_about.get("headline"), lang) or "À propos"
        title = f"{headline} — {brand}"
        paragraphs = legacy_about.get("paragraphs") or []
        body_html = "".join(
            f"<p>{_h(_pick_lang(p, lang))}</p>" for p in paragraphs
        )
        description = (paragraphs[0] if paragraphs else "")
        if isinstance(description, dict):
            description = _pick_lang(description, lang)
        main = f"<h1>{_h(headline)}</h1>{body_html}"
    else:
        description = f"Découvrez {brand}"
        title = f"À propos — {brand}"
        main = (
            f"<h1>À propos de {_h(brand)}</h1>"
            f"<p>{_h(description)}</p>"
        )

    jsonld = {
        "@context": "https://schema.org",
        "@type": "AboutPage",
        "name": title,
        "description": description[:300] if isinstance(description, str) else "",
        "url": canonical or None,
    }
    head = _render_head(
        lang=lang, title=title,
        description=description if isinstance(description, str) else "",
        canonical=canonical, og_type="website", jsonld=jsonld,
    )
    return (
        head
        + f"<body><header><a href='/'>{_h(brand)}</a></header>"
        + f"<main>{main}</main>"
        + f"<footer>© {_h(brand)}</footer></body></html>"
    )


async def _render_pdp(site: dict, slug: str) -> Optional[str]:
    p = await db.products.find_one(
        {"site_id": site["id"], "$or": [{"slug": slug}, {"id": slug}], "status": "active"},
        {"_id": 0},
    )
    if not p:
        return None
    lang = _site_lang(site)
    name = _pick_lang(p.get("name"), lang) or p.get("title") or ""
    desc_raw = (p.get("aeo_snippet") or _pick_lang((p.get("narrative") or {}).get("subheadline"), lang)
                or _pick_lang(p.get("description"), lang) or "")
    desc = (desc_raw or "")[:300]
    domain = site.get("custom_domain") or ""
    canonical = f"https://{domain}/products/{p.get('slug') or slug}" if domain else ""
    images = [im.get("url") for im in (p.get("generated_images") or [])
              if isinstance(im, dict) and im.get("url")][:6]
    if not images:
        images = [u for u in (p.get("images") or []) if isinstance(u, str)][:6]
    price = p.get("price") or p.get("selling_price") or 0
    currency = p.get("currency") or "EUR"
    brand = _site_brand_name(site)
    jsonld = {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": name,
        "description": desc,
        "image": images,
        "sku": p.get("sku") or p.get("id"),
        "brand": {"@type": "Brand", "name": brand},
        "offers": {"@type": "Offer", "price": price, "priceCurrency": currency,
                   "url": canonical, "availability": "https://schema.org/InStock"},
    }
    usps_html = ""
    usps = p.get("usps") or []
    if usps:
        usps_html = "<ul>" + "".join(
            f"<li>{_h(_pick_lang(u, lang) if isinstance(u, dict) else u)}</li>"
            for u in usps[:6]
        ) + "</ul>"
    head = _render_head(
        lang=lang, title=f"{name} — {brand}", description=desc,
        canonical=canonical, og_type="product",
        og_image=(images[0] if images else ""), jsonld=jsonld,
    )
    return (
        head
        + f"<body><header><a href='/'>{_h(brand)}</a></header><main>"
        + f"<h1>{_h(name)}</h1><p>{_h(desc)}</p>"
        + f"<p><strong>Prix : {_h(price)} {_h(currency)}</strong></p>"
        + usps_html
        + "".join(f"<img src='{_h(u)}' alt='{_h(name)}' loading='lazy'/>" for u in images[:3])
        + f"</main><footer><a href='{_h(canonical)}'>Voir la fiche complète</a></footer>"
        "</body></html>"
    )


async def _render_buyer_guide(site: dict, slug: str) -> Optional[str]:
    g = await db.landing_pages.find_one(
        {"site_id": site["id"], "slug": slug, "kind": "buyer_guide"}, {"_id": 0},
    )
    if not g:
        return None
    lang = _site_lang(site)
    domain = site.get("custom_domain") or ""
    canonical = f"https://{domain}/buyer-guides/{slug}" if domain else ""
    brand = _site_brand_name(site)
    sections_html = "".join(
        f"<section><h2>{_h(s.get('h2',''))}</h2><div>{_md_to_html(s.get('body_md',''))}</div></section>"
        for s in (g.get("sections") or [])
    )
    faq_items = g.get("faq") or []
    faq_html = "".join(
        f"<details><summary>{_h(f.get('q',''))}</summary><p>{_h(f.get('a',''))}</p></details>"
        for f in faq_items
    )
    jsonld_main = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": g.get("h1") or g.get("title"),
        "description": g.get("meta_description"),
        "datePublished": g.get("created_at"),
        "dateModified": g.get("updated_at"),
        "author": {"@type": "Organization", "name": brand},
    }
    if faq_items:
        # Dual JSON-LD : Article + FAQPage
        jsonld_main = [
            jsonld_main,
            {
                "@context": "https://schema.org",
                "@type": "FAQPage",
                "mainEntity": [
                    {"@type": "Question", "name": f.get("q",""),
                     "acceptedAnswer": {"@type": "Answer", "text": f.get("a","")}}
                    for f in faq_items
                ],
            },
        ]
    head = _render_head(
        lang=lang, title=g.get("title") or g.get("h1") or "Guide",
        description=g.get("meta_description") or "",
        canonical=canonical, og_type="article", jsonld=jsonld_main,
    )
    return (
        head
        + f"<body><header><a href='/'>{_h(brand)}</a></header><main>"
        + f"<h1>{_h(g.get('h1') or g.get('title'))}</h1>"
        + f"<p>{_h(g.get('intro',''))}</p>{sections_html}"
        + (f"<section><h2>FAQ</h2>{faq_html}</section>" if faq_html else "")
        + "</main></body></html>"
    )


async def _render_glossary_term(site: dict, slug: str) -> Optional[str]:
    t = await db.glossary_terms.find_one({"site_id": site["id"], "slug": slug}, {"_id": 0})
    if not t:
        return None
    lang = _site_lang(site)
    domain = site.get("custom_domain") or ""
    canonical = f"https://{domain}/glossary/{slug}" if domain else ""
    brand = _site_brand_name(site)
    definition = t.get("definition") or ""
    jsonld = {
        "@context": "https://schema.org", "@type": "DefinedTerm",
        "name": t.get("term"), "description": definition,
    }
    head = _render_head(
        lang=lang, title=f"{t.get('term')} — {brand}",
        description=definition[:160], canonical=canonical, jsonld=jsonld,
    )
    return (
        head
        + f"<body><header><a href='/'>{_h(brand)}</a></header>"
        + f"<main><h1>{_h(t.get('term'))}</h1><p>{_h(definition)}</p></main>"
        + "</body></html>"
    )


async def _render_comparison(site: dict, slug: str) -> Optional[str]:
    """Rend une page /comparisons/{slug} (kind=comparison)."""
    c = await db.landing_pages.find_one(
        {"site_id": site["id"], "slug": slug, "kind": "comparison"}, {"_id": 0},
    )
    if not c:
        return None
    lang = _site_lang(site)
    domain = site.get("custom_domain") or ""
    canonical = f"https://{domain}/comparisons/{slug}" if domain else ""
    brand = _site_brand_name(site)
    table = c.get("comparison_table") or {}
    headers = table.get("headers") or []
    rows = table.get("rows") or []
    table_html = ""
    if headers and rows:
        thead = "<tr>" + "".join(f"<th>{_h(h_)}</th>" for h_ in headers) + "</tr>"
        tbody = "".join(
            "<tr>" + "".join(f"<td>{_h(c2)}</td>" for c2 in r) + "</tr>"
            for r in rows
        )
        table_html = f"<table>{thead}{tbody}</table>"
    strengths_a = c.get("section_a_strengths") or []
    strengths_b = c.get("section_b_strengths") or []
    strengths_html = ""
    if strengths_a or strengths_b:
        strengths_html = (
            "<section><h2>Points forts comparés</h2>"
            f"<h3>{_h(c.get('product_a_slug',''))}</h3>"
            "<ul>" + "".join(f"<li>{_h(s)}</li>" for s in strengths_a) + "</ul>"
            f"<h3>{_h(c.get('product_b_slug',''))}</h3>"
            "<ul>" + "".join(f"<li>{_h(s)}</li>" for s in strengths_b) + "</ul>"
            "</section>"
        )
    verdict = c.get("verdict") or ""
    verdict_html = f"<section><h2>Notre verdict</h2><p>{_h(verdict)}</p></section>" if verdict else ""
    faq_items = c.get("faq") or []
    faq_html = "".join(
        f"<details><summary>{_h(f.get('q',''))}</summary><p>{_h(f.get('a',''))}</p></details>"
        for f in faq_items
    )
    cta_links = ""
    for slug_field in ("product_a_slug", "product_b_slug"):
        ps = c.get(slug_field)
        if ps and domain:
            cta_links += f"<a href='https://{_h(domain)}/products/{_h(ps)}'>{_h(ps)}</a> "

    jsonld_main = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": c.get("h1") or c.get("title"),
        "description": c.get("meta_description"),
        "datePublished": c.get("created_at"),
        "dateModified": c.get("updated_at"),
        "author": {"@type": "Organization", "name": brand},
    }
    jsonld = jsonld_main
    if faq_items:
        jsonld = [
            jsonld_main,
            {
                "@context": "https://schema.org", "@type": "FAQPage",
                "mainEntity": [
                    {"@type": "Question", "name": f.get("q",""),
                     "acceptedAnswer": {"@type": "Answer", "text": f.get("a","")}}
                    for f in faq_items
                ],
            },
        ]
    head = _render_head(
        lang=lang, title=c.get("title") or c.get("h1") or "Comparatif",
        description=c.get("meta_description") or "",
        canonical=canonical, og_type="article", jsonld=jsonld,
    )
    return (
        head
        + f"<body><header><a href='/'>{_h(brand)}</a></header><main>"
        + f"<h1>{_h(c.get('h1') or c.get('title'))}</h1>"
        + f"<p>{_h(c.get('intro',''))}</p>"
        + table_html + strengths_html + verdict_html
        + (f"<section><h2>FAQ</h2>{faq_html}</section>" if faq_html else "")
        + (f"<footer>{cta_links}</footer>" if cta_links else "")
        + "</main></body></html>"
    )


async def _render_top_list(site: dict, slug: str) -> Optional[str]:
    """Rend une page /top-lists/{slug} (kind=top_list)."""
    t = await db.landing_pages.find_one(
        {"site_id": site["id"], "slug": slug, "kind": "top_list"}, {"_id": 0},
    )
    if not t:
        return None
    lang = _site_lang(site)
    domain = site.get("custom_domain") or ""
    canonical = f"https://{domain}/top-lists/{slug}" if domain else ""
    brand = _site_brand_name(site)
    items = t.get("items") or []
    items_html = ""
    list_elements = []
    for i, it in enumerate(items, start=1):
        if not isinstance(it, dict):
            continue
        title = it.get("title") or it.get("name") or f"Position {i}"
        body = it.get("body") or it.get("body_md") or it.get("description") or ""
        product_slug = it.get("product_slug") or it.get("slug")
        product_link = ""
        if product_slug and domain:
            product_link = (
                f"<p><a href='https://{_h(domain)}/products/{_h(product_slug)}'>"
                f"Voir le produit</a></p>"
            )
        items_html += (
            f"<section><h2>{i}. {_h(title)}</h2>"
            f"<div>{_md_to_html(body) if body else ''}</div>"
            f"{product_link}</section>"
        )
        list_elements.append({
            "@type": "ListItem",
            "position": i,
            "name": title,
            "url": (f"https://{domain}/products/{product_slug}"
                    if product_slug and domain else None),
        })
    conclusion = t.get("conclusion") or ""
    conclusion_html = (
        f"<section><h2>Conclusion</h2>{_md_to_html(conclusion)}</section>"
        if conclusion else ""
    )
    faq_items = t.get("faq") or []
    faq_html = "".join(
        f"<details><summary>{_h(f.get('q',''))}</summary><p>{_h(f.get('a',''))}</p></details>"
        for f in faq_items
    )
    jsonld_main = {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "name": t.get("h1") or t.get("title"),
        "description": t.get("meta_description"),
        "itemListElement": list_elements,
    }
    jsonld = jsonld_main
    if faq_items:
        jsonld = [
            jsonld_main,
            {"@context": "https://schema.org", "@type": "FAQPage",
             "mainEntity": [
                 {"@type": "Question", "name": f.get("q",""),
                  "acceptedAnswer": {"@type": "Answer", "text": f.get("a","")}}
                 for f in faq_items
             ]},
        ]
    head = _render_head(
        lang=lang, title=t.get("title") or t.get("h1") or "Top",
        description=t.get("meta_description") or "",
        canonical=canonical, og_type="article", jsonld=jsonld,
    )
    return (
        head
        + f"<body><header><a href='/'>{_h(brand)}</a></header><main>"
        + f"<h1>{_h(t.get('h1') or t.get('title'))}</h1>"
        + f"<p>{_h(t.get('intro',''))}</p>"
        + items_html + conclusion_html
        + (f"<section><h2>FAQ</h2>{faq_html}</section>" if faq_html else "")
        + "</main></body></html>"
    )


async def _render_longtail(site: dict, slug: str) -> Optional[str]:
    """Rend une page /longtail/{slug} (kind=longtail)."""
    lp = await db.landing_pages.find_one(
        {"site_id": site["id"], "slug": slug, "kind": "longtail"}, {"_id": 0},
    )
    if not lp:
        return None
    lang = _site_lang(site)
    domain = site.get("custom_domain") or ""
    canonical = f"https://{domain}/longtail/{slug}" if domain else ""
    brand = _site_brand_name(site)
    body_md = lp.get("body_md") or lp.get("intro") or ""
    sections = lp.get("sections") or []
    sections_html = "".join(
        f"<section><h2>{_h(s.get('h2',''))}</h2><div>{_md_to_html(s.get('body_md',''))}</div></section>"
        for s in sections if isinstance(s, dict)
    )
    jsonld = {
        "@context": "https://schema.org", "@type": "Article",
        "headline": lp.get("h1") or lp.get("title"),
        "description": lp.get("meta_description"),
        "datePublished": lp.get("created_at"),
        "dateModified": lp.get("updated_at"),
        "author": {"@type": "Organization", "name": brand},
    }
    head = _render_head(
        lang=lang, title=lp.get("title") or lp.get("h1") or "Page",
        description=lp.get("meta_description") or "",
        canonical=canonical, og_type="article", jsonld=jsonld,
    )
    return (
        head
        + f"<body><header><a href='/'>{_h(brand)}</a></header><main>"
        + f"<h1>{_h(lp.get('h1') or lp.get('title'))}</h1>"
        + (sections_html or _md_to_html(body_md))
        + "</main></body></html>"
    )


async def _render_blog(site: dict, slug: str) -> Optional[str]:
    """Rend un article blog /blog/{slug}."""
    bp = await db.blog_posts.find_one(
        {"site_id": site["id"], "slug": slug}, {"_id": 0},
    )
    if not bp:
        return None
    lang = bp.get("language") or _site_lang(site)
    domain = site.get("custom_domain") or ""
    canonical = f"https://{domain}/blog/{slug}" if domain else ""
    brand = _site_brand_name(site)
    # Champs multilingues : tous peuvent être dict {lang: str} ou str selon
    # l'âge du document. _pick_lang gère les deux cas.
    title_str = _pick_lang(bp.get("meta_title"), lang) or _pick_lang(bp.get("title"), lang) or ""
    h1_str = _pick_lang(bp.get("title"), lang) or title_str
    description = _pick_lang(bp.get("meta_description"), lang) or _pick_lang(bp.get("excerpt"), lang) or ""
    excerpt = _pick_lang(bp.get("excerpt"), lang) or ""
    body_md = _pick_lang(bp.get("body"), lang) or ""
    body_html = _md_to_html(body_md)
    tags = bp.get("tags") or []
    tags_html = ""
    if tags:
        tags_html = "<p><em>Mots-clés : " + ", ".join(_h(t) for t in tags) + "</em></p>"
    jsonld = {
        "@context": "https://schema.org",
        "@type": "BlogPosting",
        "headline": h1_str or title_str,
        "description": description,
        "datePublished": bp.get("created_at"),
        "dateModified": bp.get("updated_at"),
        "inLanguage": lang,
        "author": {"@type": "Organization", "name": brand},
        "publisher": {"@type": "Organization", "name": brand},
    }
    head = _render_head(
        lang=lang, title=title_str, description=description,
        canonical=canonical, og_type="article", jsonld=jsonld,
    )
    return (
        head
        + f"<body><header><a href='/'>{_h(brand)}</a></header><main>"
        + f"<h1>{_h(h1_str)}</h1>"
        + (f"<p><strong>{_h(excerpt)}</strong></p>" if excerpt else "")
        + body_html
        + tags_html
        + f"<footer><time datetime='{_h(bp.get('created_at',''))}'>"
        + f"{_h(str(bp.get('created_at',''))[:10])}</time></footer>"
        + "</main></body></html>"
    )


async def _render_collection(site: dict, slug: str) -> Optional[str]:
    """Rend une collection /collections/{slug}."""
    col = await db.collections.find_one(
        {"site_id": site["id"], "slug": slug}, {"_id": 0},
    )
    if not col:
        return None
    lang = _site_lang(site)
    domain = site.get("custom_domain") or ""
    canonical = f"https://{domain}/collections/{slug}" if domain else ""
    brand = _site_brand_name(site)
    name = _pick_lang(col.get("name"), lang) or col.get("title") or slug
    description = _pick_lang(col.get("description"), lang) or ""
    product_ids = col.get("product_ids") or []
    products = []
    if product_ids:
        async for p in db.products.find(
            {"id": {"$in": product_ids}, "status": "active"},
            {"_id": 0, "name": 1, "slug": 1, "price": 1, "currency": 1, "generated_images": 1, "images": 1},
        ):
            products.append(p)
    products_html = ""
    list_elements = []
    for i, p in enumerate(products, start=1):
        pname = _pick_lang(p.get("name"), lang) or p.get("slug","")
        ps = p.get("slug")
        url = f"https://{domain}/products/{ps}" if (ps and domain) else ""
        img_url = ""
        gimgs = p.get("generated_images") or []
        if gimgs and isinstance(gimgs[0], dict):
            img_url = gimgs[0].get("url") or ""
        if not img_url and p.get("images"):
            img_url = p["images"][0] if isinstance(p["images"][0], str) else ""
        products_html += (
            "<section>"
            + (f"<img src='{_h(img_url)}' alt='{_h(pname)}' loading='lazy'/>" if img_url else "")
            + f"<h3><a href='{_h(url)}'>{_h(pname)}</a></h3>"
            + f"<p><strong>{_h(p.get('price','—'))} {_h(p.get('currency','EUR'))}</strong></p>"
            + "</section>"
        )
        list_elements.append({
            "@type": "ListItem", "position": i, "name": pname, "url": url or None,
        })
    jsonld = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": name,
        "description": description,
        "url": canonical,
        "mainEntity": {
            "@type": "ItemList",
            "itemListElement": list_elements,
        },
    }
    head = _render_head(
        lang=lang, title=f"{name} — {brand}",
        description=description, canonical=canonical,
        og_type="website",
        og_image=col.get("cover_image") or "",
        jsonld=jsonld,
    )
    return (
        head
        + f"<body><header><a href='/'>{_h(brand)}</a></header><main>"
        + f"<h1>{_h(name)}</h1>"
        + (f"<p>{_h(description)}</p>" if description else "")
        + (products_html if products_html else f"<p>Cette collection est en cours de constitution ({_h(len(product_ids))} produits référencés).</p>")
        + "</main></body></html>"
    )


# ---------------------------------------------------------------------------
# Dispatch + API publique
# ---------------------------------------------------------------------------

# Préfixes path → renderer. Alias rétrocompat (compare ↔ comparisons, top ↔ top-lists).
_PATH_RENDERERS = [
    ("/products/",       _render_pdp),
    ("/buyer-guides/",   _render_buyer_guide),
    ("/glossary/",       _render_glossary_term),
    ("/comparisons/",    _render_comparison),
    ("/compare/",        _render_comparison),    # alias storefront actuel
    ("/top-lists/",      _render_top_list),
    ("/top/",            _render_top_list),       # alias storefront actuel
    ("/longtail/",       _render_longtail),
    ("/blog/",           _render_blog),
    ("/collections/",    _render_collection),
]

# Paths exacts (sans suffixe slug) → renderer
_EXACT_RENDERERS = {
    "/":       _render_home,
    "/about":  _render_about,
}


def is_indexable_path(path: str) -> bool:
    """Vrai si le path tombe sur un type de page prerenderé.

    Utilisé par le middleware UA-routing pour décider s'il intercepte la
    requête bot ou la laisse passer (fallback SPA pour les pages non
    indexables : /cart, /checkout, /account, /admin, etc.)."""
    p = (path or "/").split("?")[0]
    if p in _EXACT_RENDERERS:
        return True
    for pref, _fn in _PATH_RENDERERS:
        if p.startswith(pref) and len(p) > len(pref):
            return True
    return False


async def prerender_html(site: dict, path: str) -> Optional[str]:
    """API programmatique : retourne le HTML prerenderé pour `site` à `path`,
    ou `None` si le path n'est pas supporté ou la ressource n'existe pas.

    Utilisée par :
      - le router HTTP `GET /api/seo/prerender/{site_id}` (handler `prerender`)
      - le middleware UA-routing edge-level (`prerender_routing_middleware`)
    """
    p = (path or "/").split("?")[0]
    if p in _EXACT_RENDERERS:
        return await _EXACT_RENDERERS[p](site)
    for pref, fn in _PATH_RENDERERS:
        if p.startswith(pref) and len(p) > len(pref):
            slug = p[len(pref):].split("/")[0].split("?")[0]
            if slug:
                return await fn(site, slug)
    return None


@router.get("/seo/prerender/{site_id}", response_class=HTMLResponse)
async def prerender(
    site_id: str,
    request: Request,
    path: str = Query(..., description="e.g. /products/fauteuil-..."),
):
    site = await db.sites.find_one({"id": site_id}, {"_id": 0})
    if not site:
        raise HTTPException(404, "Site introuvable")
    body = await prerender_html(site, path)
    if not body:
        raise HTTPException(
            404,
            f"Path {path} non pré-rendu (formats supportés : "
            "/, /about, /products/{slug}, /buyer-guides/{slug}, /glossary/{slug}, "
            "/comparisons/{slug} (alias /compare/), /top-lists/{slug} (alias /top/), "
            "/longtail/{slug}, /blog/{slug}, /collections/{slug})",
        )
    headers = {"Cache-Control": "public, max-age=300", "X-Prerender": "altiaro"}
    return HTMLResponse(content=body, headers=headers)
