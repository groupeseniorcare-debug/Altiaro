"""SEO utilities — sitemap.xml + hreflang + robots + llms.txt.

Chantier 5 : le SEO organique est dissocié de la config Ads.
`seo_countries` par défaut = TOUS les pays supportés (`ALL_SUPPORTED_COUNTRIES`).
`selected_countries` (ads) est ignoré ici — le SEO ne se restreint pas au budget.
"""
from __future__ import annotations
import os
from typing import Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from datetime import datetime, timezone
from deps import db
from seo_constants import (
    LANG_BY_COUNTRY, CURRENCY_BY_COUNTRY, ALL_SUPPORTED_LANGS,
    get_seo_countries, get_seo_langs,
)

router = APIRouter()


@router.get("/public/sites/{site_id}/i18n-config")
async def i18n_config(site_id: str):
    """Chantier 3 (Phase 3) — Expose la config i18n publique d'un storefront.

    Le frontend appelle ce endpoint au mount du layout storefront pour savoir
    quelles langues proposer dans le sélecteur et quelle langue par défaut
    afficher. Public (pas d'auth) — utilisé par les visiteurs finaux.
    """
    site = await db.sites.find_one(
        {"id": site_id},
        {"_id": 0, "id": 1, "seo_countries": 1, "selected_countries": 1, "primary_country": 1},
    )
    if not site:
        raise HTTPException(404, "Site not found")
    seo_cc = get_seo_countries(site)
    seo_langs = get_seo_langs(site)
    # Primary country : explicite sur site.primary_country, sinon 1er ads_country,
    # sinon 1er seo_country (fallback raisonnable).
    primary_country = (
        (site.get("primary_country") or "").upper()
        or (site.get("selected_countries") or [None])[0]
        or (seo_cc[0] if seo_cc else "FR")
    )
    primary_lang = LANG_BY_COUNTRY.get(primary_country, "fr")
    if primary_lang not in seo_langs:
        primary_lang = seo_langs[0] if seo_langs else "fr"
    return {
        "site_id": site_id,
        "primary_lang": primary_lang,
        "primary_country": primary_country,
        "available_langs": seo_langs,
        "all_supported_langs": ALL_SUPPORTED_LANGS,
    }


def _origin() -> str:
    return os.environ.get("PUBLIC_ORIGIN") or "https://senior-france.preview.emergentagent.com"


@router.get("/public/sites/{site_id}/sitemap.xml")
async def sitemap(site_id: str):
    site = await db.sites.find_one({"id": site_id}, {"_id": 0})
    if not site:
        raise HTTPException(404, "Site introuvable")
    origin = _origin()
    # Use the verified custom domain as sitemap base so URLs match the
    # canonical <link> tags served by the SPA (SEO consistency).
    custom = site.get("custom_domain") if site.get("custom_domain_verified") else None
    if custom:
        base = f"https://{custom}"
        shop_root = ""  # No /shop/{id} prefix on custom domains
    else:
        base = f"{origin}"
        shop_root = f"/shop/{site_id}"
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Chantier 5 — langues dérivées de seo_countries (pas selected_countries)
    langs = sorted(get_seo_langs(site)) or ["fr"]

    products = await db.products.find(
        {"site_id": site_id, "status": "active"},
        {"_id": 0, "id": 1, "slug": 1, "name": 1, "images": 1,
         "generated_images": 1, "updated_at": 1},
    ).to_list(5000)

    design = site.get("design") or {}
    collections = design.get("collections") or []
    if not collections:
        collections = [{"slug": "mobilite"}, {"slug": "sommeil"}, {"slug": "quotidien"}]
    blog_posts = design.get("blog_posts") or []

    def _full(path: str) -> str:
        return f"{base}{shop_root}{path}"

    def urlset(path: str, prio: str = "0.8", changefreq: str = "weekly") -> str:
        full = _full(path)
        alts = "".join(
            f'<xhtml:link rel="alternate" hreflang="{lg}" href="{full}?lang={lg}"/>'
            for lg in langs
        )
        alts += f'<xhtml:link rel="alternate" hreflang="x-default" href="{full}?lang={langs[0]}"/>'
        return (f"<url><loc>{full}</loc><lastmod>{now}</lastmod>"
                f"<changefreq>{changefreq}</changefreq><priority>{prio}</priority>{alts}</url>")

    def product_urlset(p: dict) -> str:
        """Product URL enriched with <image:image> for Google Image Search + AEO."""
        # Canonical = /products/{slug} on custom domain, /shop/{id}/product/{slug}
        # on the platform. Slug is always preferred over UUID for SEO.
        slug = p.get("slug") or p.get("id")
        if custom:
            path = f"/products/{slug}"
        else:
            path = f"/product/{slug}"
        full = _full(path)
        alts = "".join(
            f'<xhtml:link rel="alternate" hreflang="{lg}" href="{full}?lang={lg}"/>'
            for lg in langs
        )
        alts += f'<xhtml:link rel="alternate" hreflang="x-default" href="{full}?lang={langs[0]}"/>'
        pname_raw = p.get("name")
        pname = pname_raw if isinstance(pname_raw, str) else (
            (pname_raw or {}).get("fr") or next(iter((pname_raw or {}).values()), "")
        )
        ai_urls = [g.get("url") for g in (p.get("generated_images") or []) if isinstance(g, dict) and g.get("url")]
        supplier_urls = [u for u in (p.get("images") or []) if isinstance(u, str)]
        images = (ai_urls + supplier_urls)[:8]
        image_tags = "".join(
            f"<image:image><image:loc>{_xml_escape(img if img.startswith('http') else origin + img)}</image:loc>"
            f"<image:title>{_xml_escape(pname)}</image:title></image:image>"
            for img in images
        )
        lastmod = p.get("updated_at")
        lastmod = (str(lastmod)[:10] if lastmod else now)
        return (
            f"<url><loc>{full}</loc><lastmod>{lastmod}</lastmod>"
            f"<changefreq>weekly</changefreq><priority>0.85</priority>{alts}{image_tags}</url>"
        )

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
        urls.append(product_urlset(p))
    for b in blog_posts:
        slug = b.get("slug") if isinstance(b, dict) else None
        if slug:
            urls.append(urlset(f"/blog/{slug}", "0.7", "monthly"))

    # Phase B3 — articles de blog réels (db.blog_posts)
    try:
        db_posts = await db.blog_posts.find(
            {"site_id": site_id, "status": "published"},
            {"_id": 0, "slug": 1, "updated_at": 1, "created_at": 1},
        ).to_list(2000)
        for b in db_posts:
            slug = b.get("slug")
            if slug:
                urls.append(urlset(f"/blog/{slug}", "0.7", "monthly"))
    except Exception:
        pass

    # Phase B6 — landing pages SEO factory
    try:
        landings = await db.landing_pages.find(
            {"site_id": site_id, "status": "published"},
            {"_id": 0, "slug": 1, "locale": 1},
        ).to_list(2000)
        for ld in landings:
            slug = ld.get("slug")
            if slug:
                urls.append(urlset(f"/landing/{slug}", "0.75", "monthly"))
    except Exception:
        pass

    # Sprint 2/3 — SEO content (buyer guides, comparisons, top lists, glossary, team)
    try:
        kind_to_path = {
            "buyer_guide": "/buyer-guides",
            "comparison": "/compare",
            "top_list": "/top",
        }
        seo_pages = await db.landing_pages.find(
            {"site_id": site_id, "published": True,
             "kind": {"$in": list(kind_to_path.keys())}},
            {"_id": 0, "slug": 1, "kind": 1, "updated_at": 1},
        ).to_list(2000)
        if seo_pages:
            urls.append(urlset("/buyer-guides", "0.75"))
            urls.append(urlset("/glossary", "0.65"))
            urls.append(urlset("/top", "0.7"))
        for sp in seo_pages:
            prefix = kind_to_path.get(sp.get("kind"))
            if prefix and sp.get("slug"):
                urls.append(urlset(f"{prefix}/{sp['slug']}", "0.8", "monthly"))
        glossary = await db.glossary_terms.find(
            {"site_id": site_id, "published": True},
            {"_id": 0, "slug": 1},
        ).to_list(2000)
        for t in glossary:
            if t.get("slug"):
                urls.append(urlset(f"/glossary/{t['slug']}", "0.55", "monthly"))
        # Team / authors (Sprint 3)
        s_team = await db.sites.find_one(
            {"id": site_id}, {"_id": 0, "authors": 1},
        )
        if s_team and (s_team.get("authors") or []):
            urls.append(urlset("/team", "0.6"))
            for a in s_team["authors"]:
                if a.get("slug"):
                    urls.append(urlset(f"/team/{a['slug']}", "0.5", "yearly"))
    except Exception:
        pass

    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
           'xmlns:xhtml="http://www.w3.org/1999/xhtml" '
           'xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">\n'
           + "\n".join(urls) + "\n</urlset>")
    return Response(content=xml, media_type="application/xml")


@router.get("/public/sites/{site_id}/robots.txt")
async def robots(site_id: str):
    site = await db.sites.find_one({"id": site_id}, {"_id": 0})
    if not site:
        raise HTTPException(404, "Site introuvable")
    origin = _origin()
    sitemap_url = f"{origin}/api/public/sites/{site_id}/sitemap.xml"
    # Chantier 5 — multi-lang llms.txt : 1 URL par langue SEO
    langs = get_seo_langs(site)
    llms_lines: list[str] = []
    llms_lines.append(f"Sitemap: {origin}/api/public/sites/{site_id}/llms.txt")
    llms_lines.append(f"Sitemap: {origin}/api/public/sites/{site_id}/llms-full.txt")
    for lg in langs:
        if lg == "fr":
            continue  # default sans ?lang=
        llms_lines.append(f"Sitemap: {origin}/api/public/sites/{site_id}/llms.txt?lang={lg}")
        llms_lines.append(f"Sitemap: {origin}/api/public/sites/{site_id}/llms-full.txt?lang={lg}")

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
        *llms_lines,
        "",
    ]
    return Response(content="\n".join(lines), media_type="text/plain")


def _pick_lang(value, lang: str, fallback: str = "fr") -> str:
    """Extrait une valeur textuelle dans la langue demandée.

    - str → renvoyé tel quel (contenu pas encore traduit)
    - dict {fr, de, ...} → tente lang, puis fallback, puis 1re valeur non-vide
    - autre → str()
    """
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        v = value.get(lang)
        if v:
            return v if isinstance(v, str) else str(v)
        v = value.get(fallback)
        if v:
            return v if isinstance(v, str) else str(v)
        for _, vv in value.items():
            if vv:
                return vv if isinstance(vv, str) else str(vv)
        return ""
    return str(value)


def _canonical_lang(raw: Optional[str]) -> str:
    lg = (raw or "fr").lower().strip()
    if lg not in ALL_SUPPORTED_LANGS:
        lg = "fr"
    return lg


# Chantier 5 — Textes génériques llms.txt / llms-full.txt par langue.
# Sections "Points clés" + "FAQ boutique" + intros sont fixes mais traduites.
LLMS_LABELS: dict[str, dict] = {
    "fr": {
        "summary_header": "## Résumé",
        "summary_intro": "{name} est une boutique spécialisée {niche}. Nous sélectionnons chaque produit comme si c'était pour un proche : partenaires audités, validation par des ergothérapeutes, garantie 2 ans, service client humain joignable du lundi au vendredi.",
        "keys_header": "## Points clés",
        "keys": [
            "Livraison offerte dès 50 € d'achat, partout en France métropolitaine",
            "Garantie 2 ans pièces et main d'œuvre sur tous les produits",
            "Retour gratuit sous 14 jours, remboursement intégral en 5 jours ouvrés",
            "Conseillers humains joignables par téléphone du lundi au vendredi de 9h à 18h",
            "Certains équipements éligibles au remboursement LPPR / mutuelle",
        ],
        "pages_header": "## Pages principales",
        "products_header": "## Produits",
        "faq_header": "## Questions fréquentes",
        "faqs": [
            ("Quel est le délai de livraison ?", "Expédition sous 24h ouvrées, réception en 48 à 72h. Livraison offerte dès 50 € d'achat."),
            ("Puis-je retourner un produit qui ne me convient pas ?", "Oui, vous avez 14 jours à réception pour changer d'avis. Retour gratuit et remboursement sous 5 jours ouvrés."),
            ("Comment contacter un conseiller ?", "Par téléphone du lundi au vendredi de 9h à 18h, ou par email (réponse sous 2h ouvrées en moyenne). Jamais de chatbot : une vraie équipe humaine."),
        ],
        "home_label": "Accueil", "collections_label": "Collections", "about_label": "À propos",
        "faq_label": "FAQ", "shipping_label": "Livraison", "returns_label": "Retours",
        "contact_label": "Contact", "blog_label": "Blog", "catalog_header": "## Catalogue complet",
        "posts_header": "## Articles publiés", "price_prefix": "Prix",
    },
    "de": {
        "summary_header": "## Zusammenfassung",
        "summary_intro": "{name} ist ein auf {niche} spezialisierter Shop. Wir wählen jedes Produkt so aus, als wäre es für einen Angehörigen: geprüfte Partner, ergotherapeutische Validierung, 2 Jahre Garantie, echter Kundenservice von Montag bis Freitag.",
        "keys_header": "## Kernpunkte",
        "keys": [
            "Kostenloser Versand ab 50 € Einkaufswert",
            "2 Jahre Garantie auf alle Produkte",
            "Kostenlose Rücksendung innerhalb von 14 Tagen, Rückerstattung in 5 Werktagen",
            "Echte Beraterinnen und Berater per Telefon erreichbar, Mo-Fr 9-18 Uhr",
            "Bestimmte Geräte können über die Krankenkasse bezuschusst werden",
        ],
        "pages_header": "## Hauptseiten",
        "products_header": "## Produkte",
        "faq_header": "## Häufige Fragen",
        "faqs": [
            ("Wie lang ist die Lieferzeit?", "Versand binnen 24 Werkstunden, Lieferung in 48-72 Stunden. Versand ab 50 € Einkaufswert kostenlos."),
            ("Kann ich ein Produkt zurücksenden?", "Ja, Sie haben 14 Tage Widerrufsrecht. Kostenlose Rücksendung und Rückerstattung in 5 Werktagen."),
            ("Wie erreiche ich einen Berater?", "Telefonisch Mo-Fr 9-18 Uhr oder per E-Mail (Antwort meist binnen 2 Stunden). Kein Chatbot – ein echtes Team."),
        ],
        "home_label": "Startseite", "collections_label": "Kollektionen", "about_label": "Über uns",
        "faq_label": "FAQ", "shipping_label": "Versand", "returns_label": "Rücksendung",
        "contact_label": "Kontakt", "blog_label": "Blog", "catalog_header": "## Gesamtkatalog",
        "posts_header": "## Veröffentlichte Artikel", "price_prefix": "Preis",
    },
    "en": {
        "summary_header": "## Summary",
        "summary_intro": "{name} is a shop specialised in {niche}. We pick each product as if it were for a relative: audited partners, occupational-therapist validation, 2-year warranty, human customer service reachable Monday to Friday.",
        "keys_header": "## Key points",
        "keys": [
            "Free shipping from £50 order value",
            "2-year warranty on all products",
            "Free 14-day returns, full refund within 5 working days",
            "Human advisors reachable by phone Mon-Fri 9am-6pm",
            "Some medical equipment eligible for NHS or mutual reimbursement",
        ],
        "pages_header": "## Main pages",
        "products_header": "## Products",
        "faq_header": "## Frequently asked questions",
        "faqs": [
            ("What's the delivery time?", "Dispatched within 24 business hours, delivery in 48-72h. Free shipping from £50 order value."),
            ("Can I return a product?", "Yes, you have 14 days from delivery. Free return and refund within 5 working days."),
            ("How do I contact an advisor?", "By phone Mon-Fri 9am-6pm, or by email (reply within ~2h business hours). No chatbot — a real human team."),
        ],
        "home_label": "Home", "collections_label": "Collections", "about_label": "About us",
        "faq_label": "FAQ", "shipping_label": "Shipping", "returns_label": "Returns",
        "contact_label": "Contact", "blog_label": "Blog", "catalog_header": "## Full catalogue",
        "posts_header": "## Published articles", "price_prefix": "Price",
    },
    "nl": {
        "summary_header": "## Samenvatting",
        "summary_intro": "{name} is een winkel gespecialiseerd in {niche}. We kiezen elk product alsof het voor een naaste is: gecontroleerde partners, validatie door ergotherapeuten, 2 jaar garantie, echte klantendienst bereikbaar van maandag tot vrijdag.",
        "keys_header": "## Kernpunten",
        "keys": [
            "Gratis verzending vanaf € 50",
            "2 jaar garantie op alle producten",
            "Gratis retourneren binnen 14 dagen, volledige terugbetaling in 5 werkdagen",
            "Echte adviseurs telefonisch bereikbaar ma-vr 9-18 uur",
            "Sommige apparaten komen in aanmerking voor vergoeding door de zorgverzekeraar",
        ],
        "pages_header": "## Hoofdpagina's",
        "products_header": "## Producten",
        "faq_header": "## Veelgestelde vragen",
        "faqs": [
            ("Hoe lang duurt de levering?", "Verzonden binnen 24 werkuren, levering in 48-72 uur. Gratis verzending vanaf € 50."),
            ("Kan ik een product retourneren?", "Ja, u heeft 14 dagen na levering. Gratis retour en terugbetaling binnen 5 werkdagen."),
            ("Hoe bereik ik een adviseur?", "Telefonisch ma-vr 9-18 uur of per e-mail (antwoord doorgaans binnen 2 werkuren). Geen chatbot — een echt team."),
        ],
        "home_label": "Home", "collections_label": "Collecties", "about_label": "Over ons",
        "faq_label": "FAQ", "shipping_label": "Verzending", "returns_label": "Retourneren",
        "contact_label": "Contact", "blog_label": "Blog", "catalog_header": "## Volledige catalogus",
        "posts_header": "## Gepubliceerde artikelen", "price_prefix": "Prijs",
    },
    "it": {
        "summary_header": "## Sintesi",
        "summary_intro": "{name} è un negozio specializzato in {niche}. Selezioniamo ogni prodotto come se fosse per un caro: partner verificati, convalida da terapisti occupazionali, 2 anni di garanzia, servizio clienti umano dal lunedì al venerdì.",
        "keys_header": "## Punti chiave",
        "keys": [
            "Spedizione gratuita da 50 € di acquisto",
            "Garanzia di 2 anni su tutti i prodotti",
            "Reso gratuito entro 14 giorni, rimborso in 5 giorni lavorativi",
            "Consulenti umani al telefono lun-ven 9-18",
            "Alcuni dispositivi rimborsabili dalla mutua / SSN",
        ],
        "pages_header": "## Pagine principali",
        "products_header": "## Prodotti",
        "faq_header": "## Domande frequenti",
        "faqs": [
            ("Tempi di consegna?", "Spedito entro 24 ore lavorative, consegna in 48-72h. Spedizione gratuita da 50 €."),
            ("Posso restituire un prodotto?", "Sì, avete 14 giorni dalla ricezione. Reso gratuito e rimborso in 5 giorni lavorativi."),
            ("Come contattare un consulente?", "Al telefono lun-ven 9-18 o via email (risposta in circa 2 ore lavorative). Nessun chatbot — un vero team."),
        ],
        "home_label": "Home", "collections_label": "Collezioni", "about_label": "Chi siamo",
        "faq_label": "FAQ", "shipping_label": "Spedizione", "returns_label": "Resi",
        "contact_label": "Contatti", "blog_label": "Blog", "catalog_header": "## Catalogo completo",
        "posts_header": "## Articoli pubblicati", "price_prefix": "Prezzo",
    },
    "es": {
        "summary_header": "## Resumen",
        "summary_intro": "{name} es una tienda especializada en {niche}. Seleccionamos cada producto como si fuera para un familiar: socios auditados, validación por terapeutas ocupacionales, garantía de 2 años, atención humana de lunes a viernes.",
        "keys_header": "## Puntos clave",
        "keys": [
            "Envío gratuito desde 50 € de compra",
            "Garantía de 2 años en todos los productos",
            "Devolución gratuita en 14 días, reembolso en 5 días laborables",
            "Asesores humanos por teléfono de lun a vie 9-18 h",
            "Algunos equipos elegibles para reembolso por mutua / Seguridad Social",
        ],
        "pages_header": "## Páginas principales",
        "products_header": "## Productos",
        "faq_header": "## Preguntas frecuentes",
        "faqs": [
            ("¿Cuál es el plazo de entrega?", "Envío en 24 horas laborables, entrega en 48-72 h. Envío gratuito desde 50 € de compra."),
            ("¿Puedo devolver un producto?", "Sí, dispone de 14 días desde la recepción. Devolución gratuita y reembolso en 5 días laborables."),
            ("¿Cómo contactar a un asesor?", "Por teléfono lun-vie 9-18 h o por email (respuesta en unas 2 h laborables). Sin chatbot — un equipo humano real."),
        ],
        "home_label": "Inicio", "collections_label": "Colecciones", "about_label": "Sobre nosotros",
        "faq_label": "FAQ", "shipping_label": "Envío", "returns_label": "Devoluciones",
        "contact_label": "Contacto", "blog_label": "Blog", "catalog_header": "## Catálogo completo",
        "posts_header": "## Artículos publicados", "price_prefix": "Precio",
    },
}


@router.get("/public/sites/{site_id}/llms.txt")
async def llms_txt(site_id: str, lang: Optional[str] = None):
    """llms.txt — AEO summary for Answer Engines (ChatGPT, Claude, Perplexity, Gemini).
    Chantier 5 — Multi-langue via ?lang=fr|de|en|nl|it|es (défaut: fr).
    Standard : https://llmstxt.org/"""
    site = await db.sites.find_one({"id": site_id}, {"_id": 0})
    if not site:
        raise HTTPException(404, "Site introuvable")

    lg = _canonical_lang(lang)
    L = LLMS_LABELS[lg]
    origin = _origin()
    base = f"{origin}/shop/{site_id}"
    name = site.get("name") or "Boutique"
    niche = site.get("niche") or "produits senior"
    design = site.get("design") or {}
    tagline = _pick_lang((design.get("brand") or {}).get("tagline"), lg)

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
        f"> {tagline or f'{name} — {niche}.'}",
        "",
        L["summary_header"],
        "",
        L["summary_intro"].format(name=name, niche=niche),
        "",
        L["keys_header"],
    ]
    lines.extend(f"- {k}" for k in L["keys"])
    lines.extend(["", L["pages_header"]])
    lines.append(f"- [{L['home_label']}]({base}?lang={lg})")
    lines.append(f"- [{L['collections_label']}]({base}/collections?lang={lg})")
    for c in collections[:6]:
        if isinstance(c, dict) and c.get("slug"):
            title = _pick_lang(c.get("title"), lg) or c["slug"]
            lines.append(f"- [{title}]({base}/collection/{c['slug']}?lang={lg})")
    lines.extend([
        f"- [{L['about_label']}]({base}/about?lang={lg})",
        f"- [{L['faq_label']}]({base}/faq?lang={lg})",
        f"- [{L['shipping_label']}]({base}/livraison?lang={lg})",
        f"- [{L['returns_label']}]({base}/retours?lang={lg})",
        f"- [{L['contact_label']}]({base}/contact?lang={lg})",
        "",
        L["products_header"],
    ])
    for p in products[:20]:
        pname = _pick_lang(p.get("name"), lg)
        desc = _pick_lang(p.get("short_description") or p.get("description"), lg)
        desc = (desc or "")[:200].replace("\n", " ").strip()
        price = p.get("price") or p.get("price_eur") or 0
        lines.append(f"- [{pname}]({base}/product/{p['id']}?lang={lg}) — {desc} — {price} €")

    lines.extend(["", L["faq_header"], ""])
    for q, a in L["faqs"]:
        lines.extend([f"**{q}**", a, ""])

    lines.append(f"Sitemap XML : {origin}/api/public/sites/{site_id}/sitemap.xml")
    return Response(content="\n".join(lines), media_type="text/plain; charset=utf-8")


@router.get("/public/sites/{site_id}/llms-full.txt")
async def llms_full_txt(site_id: str, lang: Optional[str] = None):
    """llms-full.txt — version exhaustive avec le contenu des articles de blog.
    Chantier 5 — Multi-langue via ?lang=fr|de|en|nl|it|es (défaut: fr).
    Les moteurs IA (Perplexity, ChatGPT, Gemini, Claude) citent directement à
    partir de ce fichier, c'est la pièce MAÎTRESSE de l'AEO.
    Standard : https://llmstxt.org/"""
    site = await db.sites.find_one({"id": site_id}, {"_id": 0})
    if not site:
        raise HTTPException(404, "Site introuvable")

    lg = _canonical_lang(lang)
    L = LLMS_LABELS[lg]
    origin = _origin()
    base = f"{origin}/shop/{site_id}"
    name = site.get("name") or "Boutique"
    niche = site.get("niche") or "produits senior"
    design = site.get("design") or {}
    brand = design.get("brand") or {}
    tagline = _pick_lang(brand.get("tagline"), lg)

    products = await db.products.find(
        {"site_id": site_id, "status": "active"},
        {"_id": 0},
    ).limit(100).to_list(100)
    blog_posts = list(design.get("blog_posts") or [])
    # Priorise pillars first, then satellites (max 40 total)
    blog_posts.sort(key=lambda p: (p.get("type") != "pillar", -len(p.get("body") or "")))
    blog_posts = blog_posts[:40]

    lines = [
        f"# {name} — llms-full.txt ({lg})",
        "",
        f"> {tagline or f'{name}, {niche}.'}",
        "",
        f"URL : {base}?lang={lg}",
        f"Niche : {niche}",
        f"Language : {lg}",
        f"Last updated : {datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
        "",
        "## About",
        "",
    ]
    about = design.get("pages", {}).get("about") or design.get("about") or {}
    headline = _pick_lang(about.get("headline"), lg)
    if headline:
        lines.extend([f"**{headline}**", ""])
    for par in (about.get("paragraphs") or [])[:3]:
        par_txt = _pick_lang(par, lg)
        if par_txt:
            lines.extend([str(par_txt), ""])

    # --- Produits : nom + description complète ---
    lines.extend(["", L["catalog_header"], ""])
    for p in products:
        pname = _pick_lang(p.get("name"), lg) or "Product"
        desc = _pick_lang(p.get("description") or p.get("short_description"), lg)
        price = p.get("price") or 0
        narrative = p.get("narrative") or {}
        sub = _pick_lang(narrative.get("subheadline"), lg)
        benefits = narrative.get("benefits") or []

        lines.extend([
            f"### {pname}",
            f"URL : {base}/product/{p['id']}?lang={lg}",
            f"{L['price_prefix']} : {price} €",
            "",
            str(sub) if sub else str(desc)[:600],
            "",
        ])
        if benefits:
            lines.append("Key benefits:")
            for b in benefits[:6]:
                btxt = _pick_lang(b, lg) if isinstance(b, (dict, str)) else str(b)
                if btxt:
                    lines.append(f"- {btxt}")
            lines.append("")

        # FAQ produit — clé pour AEO (les IA aspirent les Q/A directement)
        faq = narrative.get("faq") or []
        if faq:
            lines.append("FAQ:")
            for f in faq[:4]:
                q = _pick_lang(f.get("question") or f.get("q"), lg) if isinstance(f, dict) else None
                a = _pick_lang(f.get("answer") or f.get("a"), lg) if isinstance(f, dict) else None
                if q and a:
                    lines.append(f"- **Q:** {q}")
                    lines.append(f"  **A:** {a}")
            lines.append("")

    # --- Blog : articles (traductions si présentes, sinon fallback langue originale) ---
    lines.extend(["", L["posts_header"], ""])
    for post in blog_posts:
        translations = post.get("translations") or {}
        tr = translations.get(lg) if isinstance(translations, dict) else None
        if tr and isinstance(tr, dict) and (tr.get("title") or tr.get("body")):
            title = tr.get("title") or post.get("title") or ""
            body = (tr.get("body") or post.get("body") or "").strip()
        else:
            title = post.get("title") or ""
            body = (post.get("body") or "").strip()
        slug = post.get("slug") or ""
        # Cap body per article for safety (AI tokens / file size)
        if len(body) > 4000:
            body = body[:4000] + "\n\n[…]"
        lines.extend([
            f"### {title}",
            f"URL : {base}/blog/{slug}?lang={lg}",
            f"Type : {post.get('type') or 'article'}",
            "",
            body,
            "",
            "---",
            "",
        ])

    return Response(
        content="\n".join(lines),
        media_type="text/plain; charset=utf-8",
    )


def _xml_escape(s: str) -> str:
    if s is None:
        return ""
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
               .replace(">", "&gt;").replace('"', "&quot;").replace("'", "&apos;"))


@router.get("/public/sites/{site_id}/merchant-feed.xml")
async def merchant_feed(site_id: str, country: str = "FR"):
    """Google Merchant Center RSS 2.0 feed (conforme Google Shopping).
    Chantier 5 — ce flux reste basé sur les pays Ads (pas tous les SEO) car
    Google Merchant consomme de la bande passante + quotas côté Google.
    Exposé par pays via ?country=FR|DE|BE|NL|UK|CH..."""
    site = await db.sites.find_one({"id": site_id}, {"_id": 0})
    if not site:
        raise HTTPException(404, "Site introuvable")
    origin = _origin()
    base = f"{origin}/shop/{site_id}"
    country = (country or "FR").upper()
    lang = LANG_BY_COUNTRY.get(country, "fr")

    currency = CURRENCY_BY_COUNTRY.get(country, "EUR")

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



# ============================================================
#  Phase B1 — JSON-LD agrégé multilingue (Organization, WebSite,
#  Product, BreadcrumbList, FAQPage, HowTo, Article+Speakable,
#  LocalBusiness)
# ============================================================
@router.get("/public/sites/{site_id}/seo/jsonld")
async def public_jsonld(
    site_id: str,
    lang: str = "fr",
    product_id: Optional[str] = None,
    blog_slug: Optional[str] = None,
    landing_slug: Optional[str] = None,
    country: Optional[str] = None,
):
    """Retourne tous les blocs JSON-LD pertinents pour la page demandée.

    Utilisé par <SEOHead> côté storefront pour injecter
    <script type="application/ld+json">{...}</script>.
    """
    from services import seo_jsonld
    site = await db.sites.find_one({"id": site_id}, {"_id": 0})
    if not site:
        raise HTTPException(404, "Site introuvable")
    origin = _origin()
    public_url = site.get("public_url") or f"{origin}/shop/{site_id}"
    site = {**site, "public_url": public_url}
    out: list[dict] = []

    # 1) Organization + WebSite (toujours présents)
    out.append(seo_jsonld.organization(site))
    out.append(seo_jsonld.website(site))

    # 2) LocalBusiness si site a un pays principal (Phase B8 — GEO)
    countries = site.get("seo_countries") or []
    if countries:
        ar = countries[:11]
        lb = {
            "@context": "https://schema.org",
            "@type": "LocalBusiness",
            "name": (site.get("design") or {}).get("brand", {}).get("name") or site.get("name"),
            "url": public_url,
            "areaServed": [{"@type": "Country", "name": c} for c in ar],
        }
        out.append(lb)

    # 3) Product
    if product_id:
        p = await db.products.find_one({"id": product_id, "site_id": site_id}, {"_id": 0})
        if p:
            currency = "GBP" if (country or "").upper() == "GB" else "EUR"
            out.append(seo_jsonld.product(p, site, lang, currency=currency))
            # Breadcrumb produit
            name = p.get("name")
            pname = name.get(lang) if isinstance(name, dict) else (name or "Produit")
            out.append(seo_jsonld.breadcrumbs([
                {"name": "Accueil", "url": public_url},
                {"name": "Produits", "url": f"{public_url}/collections"},
                {"name": pname, "url": f"{public_url}/product/{product_id}"},
            ]))
            # FAQ produit (narrative.faq)
            faqs = (p.get("narrative") or {}).get("faq") or []
            if faqs:
                out.append(seo_jsonld.faq_page(faqs, lang))
            # HowTo (narrative.how_to)
            howto = (p.get("narrative") or {}).get("how_to") or []
            if howto:
                out.append(seo_jsonld.howto(howto, lang))

    # 4) Article (blog) + Speakable
    if blog_slug:
        post = await db.blog_posts.find_one(
            {"site_id": site_id, "slug": blog_slug}, {"_id": 0},
        )
        if post:
            out.append(seo_jsonld.article(post, lang))
            out.append(seo_jsonld.breadcrumbs([
                {"name": "Accueil", "url": public_url},
                {"name": "Blog", "url": f"{public_url}/blog"},
                {"name": (post.get("title", {}) or {}).get(lang) or "Article",
                 "url": f"{public_url}/blog/{blog_slug}"},
            ]))

    # 5) Landing page SEO Factory
    if landing_slug:
        lp = await db.landing_pages.find_one(
            {"site_id": site_id, "slug": landing_slug}, {"_id": 0},
        )
        if lp:
            out.append({
                "@context": "https://schema.org", "@type": "WebPage",
                "name": lp.get("h1") or lp.get("meta_title"),
                "description": lp.get("meta_description"),
                "url": f"{public_url}/landing/{landing_slug}",
                "speakable": {"@type": "SpeakableSpecification", "cssSelector": ["h1", ".lead"]},
            })

    # 6) hreflang (en bonus, exposé dans la réponse pour SEOHead)
    langs = sorted(get_seo_langs(site)) or ["fr"]
    path = ""
    if product_id:
        path = f"/product/{product_id}"
    elif blog_slug:
        path = f"/blog/{blog_slug}"
    elif landing_slug:
        path = f"/landing/{landing_slug}"
    alternates = seo_jsonld.hreflang_alternates(public_url, path, langs, default=langs[0])

    return {"jsonld": out, "hreflang": alternates}
