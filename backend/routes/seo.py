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

    design = site.get("design") or {}
    collections = design.get("collections") or []
    if not collections:
        collections = [{"slug": "mobilite"}, {"slug": "sommeil"}, {"slug": "quotidien"}]
    blog_posts = design.get("blog_posts") or []

    def urlset(path: str, prio: str = "0.8", changefreq: str = "weekly") -> str:
        alts = "".join(
            f'<xhtml:link rel="alternate" hreflang="{lg}" href="{base}{path}?lang={lg}"/>'
            for lg in langs
        )
        return (f"<url><loc>{base}{path}</loc><lastmod>{now}</lastmod>"
                f"<changefreq>{changefreq}</changefreq><priority>{prio}</priority>{alts}</url>")

    urls = [
        urlset("", "1.0", "daily"),
        urlset("/collections", "0.9"),
        urlset("/about", "0.7"),
        urlset("/faq", "0.6"),
        urlset("/contact", "0.6"),
        urlset("/livraison", "0.6"),
        urlset("/retours", "0.6"),
        urlset("/blog", "0.7"),
        urlset("/cgv", "0.3", "yearly"),
        urlset("/mentions", "0.3", "yearly"),
        urlset("/confidentialite", "0.3", "yearly"),
    ]
    for c in collections:
        slug = c.get("slug") if isinstance(c, dict) else str(c)
        if slug:
            urls.append(urlset(f"/collection/{slug}", "0.85"))
    for p in products:
        urls.append(urlset(f"/product/{p['id']}", "0.8"))
    for b in blog_posts:
        slug = b.get("slug") if isinstance(b, dict) else None
        if slug:
            urls.append(urlset(f"/blog/{slug}", "0.7", "monthly"))

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
    sitemap_url = f"{_origin()}/api/public/sites/{site_id}/sitemap.xml"
    # Explicit allow-list for modern AI crawlers (AEO — Answer Engine Optimization)
    lines = [
        "User-agent: *",
        f"Allow: /shop/{site_id}/",
        "Disallow: /shop/*/account/",
        "Disallow: /shop/*/cart",
        "Disallow: /shop/*/checkout",
        "",
        "# AI / LLM crawlers — explicitly allowed (AEO)",
        "User-agent: GPTBot",
        "Allow: /",
        "User-agent: OAI-SearchBot",
        "Allow: /",
        "User-agent: ChatGPT-User",
        "Allow: /",
        "User-agent: ClaudeBot",
        "Allow: /",
        "User-agent: anthropic-ai",
        "Allow: /",
        "User-agent: PerplexityBot",
        "Allow: /",
        "User-agent: Google-Extended",
        "Allow: /",
        "User-agent: Applebot-Extended",
        "Allow: /",
        "User-agent: CCBot",
        "Allow: /",
        "",
        f"Sitemap: {sitemap_url}",
        f"Sitemap: {_origin()}/api/public/sites/{site_id}/llms.txt",
        "",
    ]
    return Response(content="\n".join(lines), media_type="text/plain")


@router.get("/public/sites/{site_id}/llms.txt")
async def llms_txt(site_id: str):
    """llms.txt — AEO summary for Answer Engines (ChatGPT, Claude, Perplexity, Gemini).
    Standard : https://llmstxt.org/
    Provides a curated content index with stable URLs + key Q/A for AI citation."""
    site = await db.sites.find_one({"id": site_id}, {"_id": 0})
    if not site:
        raise HTTPException(404, "Site introuvable")

    origin = _origin()
    base = f"{origin}/shop/{site_id}"
    name = site.get("name") or "Boutique"
    niche = site.get("niche") or "produits senior"
    design = site.get("design") or {}
    tagline_raw = (design.get("brand") or {}).get("tagline")
    tagline = tagline_raw if isinstance(tagline_raw, str) else (
        tagline_raw.get("fr") if isinstance(tagline_raw, dict) else ""
    )
    about = design.get("about") or {}
    about_headline = about.get("headline") or f"Histoire de {name}"
    if isinstance(about_headline, dict):
        about_headline = about_headline.get("fr") or next(iter(about_headline.values()), "")

    # Products
    products = await db.products.find(
        {"site_id": site_id, "status": "active"},
        {"_id": 0, "id": 1, "name": 1, "short_description": 1, "description": 1, "price": 1, "price_eur": 1, "category": 1}
    ).limit(50).to_list(50)

    # Collections
    collections = design.get("collections") or [
        {"slug": "mobilite", "title": "Mobilité & confort"},
        {"slug": "sommeil", "title": "Sommeil & récupération"},
        {"slug": "quotidien", "title": "Quotidien serein"},
    ]

    lines = [
        f"# {name}",
        "",
        f"> {tagline or f'{name} — une sélection pensée pour les seniors et leurs aidants, avec un service humain et des produits testés.'}",
        "",
        "## Résumé",
        "",
        f"{name} est une boutique spécialisée {niche}. Nous sélectionnons chaque produit comme si c'était pour un proche : partenaires audités, validation par des ergothérapeutes, garantie 2 ans, service client humain joignable du lundi au vendredi.",
        "",
        "## Points clés",
        "- Livraison offerte dès 50 € d'achat, partout en France métropolitaine",
        "- Garantie 2 ans pièces et main d'œuvre sur tous les produits",
        "- Retour gratuit sous 14 jours, remboursement intégral en 5 jours ouvrés",
        "- Conseillers humains joignables par téléphone du lundi au vendredi de 9h à 18h",
        "- Certains équipements éligibles au remboursement LPPR / mutuelle",
        "",
        "## Pages principales",
        f"- [Accueil]({base}) — vitrine de la boutique",
        f"- [Collections]({base}/collections) — univers thématiques",
    ]
    for c in collections[:6]:
        if isinstance(c, dict) and c.get("slug"):
            title = c.get("title")
            if isinstance(title, dict):
                title = title.get("fr") or next(iter(title.values()), c["slug"])
            lines.append(f"- [{title or c['slug']}]({base}/collection/{c['slug']}) — collection thématique")
    lines.extend([
        f"- [À propos]({base}/about) — histoire, valeurs, équipe",
        f"- [FAQ]({base}/faq) — questions fréquentes",
        f"- [Livraison]({base}/livraison) — délais, coûts, zones couvertes",
        f"- [Retours]({base}/retours) — politique de retour sous 14 jours",
        f"- [Contact]({base}/contact) — coordonnées et formulaire",
        "",
        "## Produits",
    ])
    for p in products[:20]:
        pname = p.get("name")
        if isinstance(pname, dict):
            pname = pname.get("fr") or next(iter(pname.values()), "")
        desc = p.get("short_description") or p.get("description") or ""
        if isinstance(desc, dict):
            desc = desc.get("fr") or next(iter(desc.values()), "")
        desc = (str(desc) or "")[:200].replace("\n", " ").strip()
        price = p.get("price") or p.get("price_eur") or 0
        lines.append(f"- [{pname}]({base}/product/{p['id']}) — {desc} — {price} €")

    lines.extend([
        "",
        "## Questions fréquentes",
        "",
        "**Quel est le délai de livraison ?**",
        "Expédition sous 24h ouvrées, réception en 48 à 72h en France métropolitaine. Livraison offerte dès 50 € d'achat.",
        "",
        "**Puis-je retourner un produit qui ne me convient pas ?**",
        "Oui, vous avez 14 jours à réception pour changer d'avis. Retour gratuit (étiquette prépayée fournie) et remboursement sous 5 jours ouvrés.",
        "",
        "**Comment contacter un conseiller ?**",
        "Par téléphone du lundi au vendredi de 9h à 18h, ou par email (réponse sous 2h ouvrées en moyenne). Jamais de chatbot : une vraie équipe humaine.",
        "",
        "**Les produits sont-ils remboursés par la Sécurité sociale ?**",
        "Certains équipements (fauteuils releveurs médicalisés, matelas anti-escarres) sont pris en charge partiellement au titre de la LPPR. Nous vous aidons à monter le dossier avec votre mutuelle.",
        "",
        f"Sitemap XML : {origin}/api/public/sites/{site_id}/sitemap.xml",
    ])
    return Response(content="\n".join(lines), media_type="text/plain; charset=utf-8")


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
