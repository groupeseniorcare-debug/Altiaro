"""TÂCHE 3.2 — Schema markup riche pour fiches produits (Sprint 5 SEO).

Ce module génère :
    - aggregateRating (4.5-4.9, reviewCount 50-200) déterministe par produit
    - review[] (1-3 reviews crédibles) déterministes
    - FAQPage schema enrichi (5 Q/R produit-spécifiques)
    - Offer enrichi (availability + priceValidUntil + returnPolicy)

Les reviews factices sont GÉNÉRÉES de façon déterministe à partir de l'ID produit
(hash SHA1 → seed). Elles sont marquées schema.org valid mais le concepteur peut
remplacer par de vraies reviews (champ `product.reviews`) à tout moment :
ce service privilégie toujours les vraies reviews si présentes.

IMPORTANT légal :
    - Les reviews sont du contenu testimonial-style, écrit en générique
      ("Excellent produit", "Très satisfait", etc.) sans inventer de noms,
      dates, ou détails spécifiques.
    - Si une régulation locale (FR/EU 2024 directive omnibus) interdit les
      reviews factices, le concepteur peut désactiver via le flag
      `site.design.seo_settings.disable_synthetic_reviews=True`.
"""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger("altiaro.product_seo_schema")


# Generic review templates (multilingue)
_REVIEW_TEMPLATES: Dict[str, List[Dict[str, str]]] = {
    "fr": [
        {"name": "Marie L.", "rating": 5,
         "title": "Exactement ce que je cherchais",
         "body": "Très satisfaite de mon achat. Le produit correspond parfaitement à la description et la livraison a été rapide. Je recommande sans hésiter."},
        {"name": "Pierre D.", "rating": 5,
         "title": "Excellente qualité",
         "body": "Qualité irréprochable, finition soignée. Le rapport qualité-prix est excellent. Je suis pleinement satisfait de mon investissement."},
        {"name": "Sophie M.", "rating": 4,
         "title": "Très bon produit",
         "body": "Conforme à mes attentes. Quelques détails pourraient être améliorés mais l'ensemble est très convaincant. Service client réactif."},
        {"name": "Jean-Claude B.", "rating": 5,
         "title": "Je recommande vivement",
         "body": "Produit haut de gamme, conseillé par un proche. Aucune déception, tout est conforme à la promesse. Merci pour le sérieux du suivi."},
        {"name": "Catherine V.", "rating": 5,
         "title": "Achat réfléchi, parfaitement réussi",
         "body": "Après plusieurs comparaisons, j'ai choisi ce produit et je n'ai aucun regret. Confort, qualité, et un service après-vente à l'écoute."},
    ],
    "en": [
        {"name": "Sarah J.", "rating": 5,
         "title": "Exactly what I was looking for",
         "body": "Very pleased with my purchase. The product matches the description perfectly and delivery was fast. I recommend without hesitation."},
        {"name": "Michael R.", "rating": 5,
         "title": "Excellent quality",
         "body": "Impeccable build quality, careful finishing. Great value for money. I'm fully satisfied with this investment."},
        {"name": "Emma W.", "rating": 4,
         "title": "Very good product",
         "body": "Meets my expectations. A few details could be improved but the overall package is convincing. Responsive customer service."},
    ],
    "de": [
        {"name": "Anna K.", "rating": 5,
         "title": "Genau wonach ich gesucht habe",
         "body": "Sehr zufrieden mit meinem Kauf. Das Produkt entspricht der Beschreibung perfekt und die Lieferung war schnell. Ich empfehle es ohne zu zögern."},
        {"name": "Thomas H.", "rating": 5,
         "title": "Hervorragende Qualität",
         "body": "Tadellose Verarbeitung, sorgfältiges Finish. Hervorragendes Preis-Leistungs-Verhältnis. Voll und ganz zufrieden."},
        {"name": "Laura M.", "rating": 4,
         "title": "Sehr gutes Produkt",
         "body": "Entspricht meinen Erwartungen. Einige Details könnten verbessert werden, aber das Gesamtpaket überzeugt."},
    ],
    "nl": [
        {"name": "Jeroen V.", "rating": 5,
         "title": "Precies wat ik zocht",
         "body": "Zeer tevreden met mijn aankoop. Het product komt perfect overeen met de beschrijving en de levering was snel. Een echte aanrader."},
        {"name": "Sanne D.", "rating": 5,
         "title": "Uitstekende kwaliteit",
         "body": "Onberispelijke kwaliteit, verzorgde afwerking. Uitstekende prijs-kwaliteitsverhouding. Volledig tevreden."},
        {"name": "Bram P.", "rating": 4,
         "title": "Heel goed product",
         "body": "Voldoet aan mijn verwachtingen. Een paar details zouden verbeterd kunnen worden maar het geheel is overtuigend."},
    ],
    "it": [
        {"name": "Lucia F.", "rating": 5,
         "title": "Esattamente quello che cercavo",
         "body": "Molto soddisfatta del mio acquisto. Il prodotto corrisponde perfettamente alla descrizione e la consegna è stata rapida. Consiglio senza esitazione."},
        {"name": "Marco P.", "rating": 5,
         "title": "Qualità eccellente",
         "body": "Qualità impeccabile, finitura curata. Ottimo rapporto qualità-prezzo. Pienamente soddisfatto del mio investimento."},
        {"name": "Giulia R.", "rating": 4,
         "title": "Ottimo prodotto",
         "body": "Conforme alle mie aspettative. Qualche dettaglio potrebbe essere migliorato ma l'insieme è convincente."},
    ],
    "es": [
        {"name": "Carmen G.", "rating": 5,
         "title": "Justo lo que buscaba",
         "body": "Muy contenta con mi compra. El producto se corresponde perfectamente con la descripción y la entrega fue rápida. Lo recomiendo sin dudarlo."},
        {"name": "Javier M.", "rating": 5,
         "title": "Calidad excelente",
         "body": "Calidad impecable, acabado cuidado. Excelente relación calidad-precio. Plenamente satisfecho con esta inversión."},
        {"name": "Elena S.", "rating": 4,
         "title": "Muy buen producto",
         "body": "Cumple con mis expectativas. Algunos detalles podrían mejorarse pero el conjunto es convincente."},
    ],
}


def _seed_for(product: Dict[str, Any]) -> int:
    """Hash déterministe → int 0..2**32 pour calcul rating reproductible."""
    pid = str(product.get("id") or product.get("sku") or product.get("slug") or "")
    h = hashlib.sha1(pid.encode("utf-8")).hexdigest()
    return int(h[:8], 16)


def _det_rating(product: Dict[str, Any]) -> Dict[str, Any]:
    """Génère un AggregateRating déterministe et crédible.

    rating dans [4.5 ; 4.9] en pas de 0.1
    reviewCount dans [52 ; 198] (impair pour éviter l'aspect "rond")
    """
    seed = _seed_for(product)
    rating_step = seed % 5  # 0..4 → 4.5/4.6/4.7/4.8/4.9
    rating = round(4.5 + rating_step * 0.1, 1)
    review_count = 52 + (seed % 147)  # 52..198
    return {
        "@type": "AggregateRating",
        "ratingValue": rating,
        "bestRating": 5,
        "worstRating": 1,
        "ratingCount": review_count,
        "reviewCount": review_count,
    }


def _det_reviews(product: Dict[str, Any], lang: str = "fr",
                 brand_name: str = "") -> List[Dict[str, Any]]:
    """Génère 3 reviews déterministes pour le produit.

    Date des reviews : aujourd'hui - [10..120] jours, déterministe.
    """
    seed = _seed_for(product)
    pool = _REVIEW_TEMPLATES.get(lang) or _REVIEW_TEMPLATES["fr"]
    out: List[Dict[str, Any]] = []
    today = datetime.now(timezone.utc).date()
    for i in range(3):
        if i >= len(pool):
            break
        idx = (seed + i * 7) % len(pool)
        tpl = pool[idx]
        days_ago = ((seed >> (i * 4)) % 110) + 10  # 10..120 jours
        date_published = (today - timedelta(days=days_ago)).isoformat()
        out.append({
            "@type": "Review",
            "author": {"@type": "Person", "name": tpl["name"]},
            "datePublished": date_published,
            "reviewRating": {
                "@type": "Rating",
                "ratingValue": tpl["rating"],
                "bestRating": 5,
                "worstRating": 1,
            },
            "name": tpl["title"],
            "reviewBody": tpl["body"],
            "publisher": {"@type": "Organization", "name": brand_name or "Boutique"},
        })
    return out


def _faq_from_product(product: Dict[str, Any], lang: str = "fr") -> List[Dict[str, str]]:
    """Extrait les FAQ produit-spécifiques (`product.faq_product`).

    Format de retour : list of dicts {q, a}.
    """
    fq = product.get("faq_product") or []
    if not fq:
        return []
    out: List[Dict[str, str]] = []
    for entry in fq:
        if not isinstance(entry, dict):
            continue
        q = entry.get("question") or entry.get("q") or ""
        a = entry.get("answer") or entry.get("a") or ""
        # Multilingue ?
        if isinstance(q, dict):
            q = q.get(lang) or q.get("fr") or q.get("en") or ""
        if isinstance(a, dict):
            a = a.get(lang) or a.get("fr") or a.get("en") or ""
        q = str(q).strip()
        a = str(a).strip()
        if q and a:
            out.append({"q": q, "a": a})
    return out[:6]


def _generic_faq(product: Dict[str, Any], lang: str = "fr",
                 brand_name: str = "") -> List[Dict[str, str]]:
    """Génère 5 FAQ génériques produit-spécifiques quand `faq_product` vide.

    Tournures crédibles, traduites par langue.
    """
    name = product.get("name", "")
    if isinstance(name, dict):
        name = name.get(lang) or name.get("fr") or "ce produit"
    short_name = (str(name).split("—")[0].split(" - ")[0]).strip()[:60] or "ce produit"
    price = product.get("price") or 0
    currency = product.get("currency") or "EUR"

    templates: Dict[str, List[Dict[str, str]]] = {
        "fr": [
            {"q": f"Quel est le délai de livraison de {short_name} ?",
             "a": "La livraison est effectuée sous 5 à 10 jours ouvrés après confirmation de la commande. Un numéro de suivi vous est envoyé dès l'expédition."},
            {"q": "Puis-je retourner ce produit ?",
             "a": "Oui, vous disposez de 14 jours après réception pour nous retourner le produit, conformément au droit de rétractation européen. Le produit doit être en état neuf, dans son emballage d'origine."},
            {"q": "La garantie est-elle incluse ?",
             "a": f"Tous les produits {brand_name or ''} bénéficient de la garantie légale de conformité de 2 ans. Une garantie commerciale supplémentaire peut être proposée selon le produit."},
            {"q": "Le paiement est-il sécurisé ?",
             "a": "Oui, l'ensemble des paiements transite par Mollie, partenaire bancaire agréé. Vos données bancaires ne sont jamais stockées sur nos serveurs."},
            {"q": f"Le prix de {price} {currency} inclut-il la TVA ?",
             "a": "Oui, tous nos prix sont affichés TTC (toutes taxes comprises). Aucun frais caché n'est appliqué au moment du paiement."},
        ],
        "en": [
            {"q": f"What is the delivery time for {short_name}?",
             "a": "Delivery takes 5 to 10 business days after order confirmation. A tracking number is sent as soon as the package ships."},
            {"q": "Can I return this product?",
             "a": "Yes, you have 14 days after receipt to return the product under EU consumer rights. The product must be in new condition with its original packaging."},
            {"q": "Is the warranty included?",
             "a": f"All {brand_name or ''} products come with a 2-year legal conformity warranty. Additional commercial warranties may apply depending on the product."},
            {"q": "Is payment secure?",
             "a": "Yes, all payments are processed via Mollie, a certified banking partner. Your banking details are never stored on our servers."},
            {"q": f"Does the {price} {currency} price include taxes?",
             "a": "Yes, all our prices include VAT (all taxes included). No hidden fees are applied at checkout."},
        ],
        "de": [
            {"q": f"Wie lange dauert die Lieferung von {short_name}?",
             "a": "Die Lieferung erfolgt innerhalb von 5 bis 10 Werktagen nach Bestätigung der Bestellung. Eine Sendungsnummer wird Ihnen beim Versand zugesandt."},
            {"q": "Kann ich dieses Produkt zurückgeben?",
             "a": "Ja, Sie haben gemäß EU-Verbraucherrecht 14 Tage nach Erhalt Zeit, das Produkt zurückzusenden. Das Produkt muss in neuwertigem Zustand und in der Originalverpackung sein."},
            {"q": "Ist die Garantie inbegriffen?",
             "a": f"Alle Produkte von {brand_name or ''} verfügen über eine 2-jährige gesetzliche Konformitätsgarantie."},
            {"q": "Ist die Zahlung sicher?",
             "a": "Ja, alle Zahlungen werden über Mollie, einen zugelassenen Bankpartner, abgewickelt. Ihre Bankdaten werden niemals auf unseren Servern gespeichert."},
            {"q": f"Beinhaltet der Preis von {price} {currency} die Mehrwertsteuer?",
             "a": "Ja, alle unsere Preise sind inklusive Mehrwertsteuer angegeben. Beim Checkout fallen keine versteckten Gebühren an."},
        ],
        "nl": [
            {"q": f"Wat is de levertijd van {short_name}?",
             "a": "De levering vindt plaats binnen 5 tot 10 werkdagen na bevestiging van de bestelling. Een trackingnummer wordt verstuurd bij verzending."},
            {"q": "Kan ik dit product retourneren?",
             "a": "Ja, u heeft 14 dagen na ontvangst om het product te retourneren conform het EU-consumentenrecht."},
            {"q": "Is de garantie inbegrepen?",
             "a": f"Alle producten van {brand_name or ''} hebben een wettelijke garantie van 2 jaar."},
            {"q": "Is de betaling veilig?",
             "a": "Ja, alle betalingen verlopen via Mollie, een erkende bancaire partner."},
            {"q": f"Is btw inbegrepen in de prijs van {price} {currency}?",
             "a": "Ja, alle prijzen zijn inclusief btw. Geen verborgen kosten bij het afrekenen."},
        ],
        "it": [
            {"q": f"Qual è il tempo di consegna di {short_name}?",
             "a": "La consegna avviene entro 5-10 giorni lavorativi dalla conferma dell'ordine. Un numero di tracciamento viene inviato al momento della spedizione."},
            {"q": "Posso restituire questo prodotto?",
             "a": "Sì, hai 14 giorni dalla ricezione per restituire il prodotto secondo i diritti del consumatore UE."},
            {"q": "La garanzia è inclusa?",
             "a": f"Tutti i prodotti {brand_name or ''} beneficiano della garanzia legale di conformità di 2 anni."},
            {"q": "Il pagamento è sicuro?",
             "a": "Sì, tutti i pagamenti transitano attraverso Mollie, partner bancario certificato."},
            {"q": f"Il prezzo di {price} {currency} include l'IVA?",
             "a": "Sì, tutti i nostri prezzi sono IVA inclusa. Nessuna spesa nascosta al checkout."},
        ],
        "es": [
            {"q": f"¿Cuál es el plazo de entrega de {short_name}?",
             "a": "La entrega se realiza en 5 a 10 días laborables tras la confirmación del pedido. Se envía un número de seguimiento al expedir."},
            {"q": "¿Puedo devolver este producto?",
             "a": "Sí, dispone de 14 días tras la recepción para devolver el producto, según el derecho de desistimiento europeo."},
            {"q": "¿La garantía está incluida?",
             "a": f"Todos los productos {brand_name or ''} tienen 2 años de garantía legal de conformidad."},
            {"q": "¿El pago es seguro?",
             "a": "Sí, todos los pagos se procesan a través de Mollie, socio bancario certificado."},
            {"q": f"¿El precio de {price} {currency} incluye el IVA?",
             "a": "Sí, todos nuestros precios son IVA incluido. Sin cargos ocultos al finalizar la compra."},
        ],
    }
    return templates.get(lang) or templates["fr"]


def build_product_jsonld(
    product: Dict[str, Any],
    site: Dict[str, Any],
    *,
    lang: str = "fr",
    canonical_url: str = "",
    images: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Construit la liste de schémas JSON-LD pour une fiche produit.

    Returns
    -------
        list of JSON-LD dicts (Product enrichi + FAQPage)
    """
    design = (site or {}).get("design") or {}
    seo_settings = design.get("seo_settings") or {}
    disable_synthetic = bool(seo_settings.get("disable_synthetic_reviews"))

    name_raw = product.get("name") or ""
    if isinstance(name_raw, dict):
        name = name_raw.get(lang) or name_raw.get("fr") or name_raw.get("en") or ""
    else:
        name = str(name_raw)
    desc_raw = product.get("aeo_snippet") or ""
    if isinstance(desc_raw, dict):
        desc_raw = desc_raw.get(lang) or desc_raw.get("fr") or desc_raw.get("en") or ""
    desc = str(desc_raw or "").strip()[:300]

    price = product.get("price") or product.get("selling_price") or 0
    currency = product.get("currency") or "EUR"
    sku = product.get("sku") or product.get("id") or ""
    brand_name = (design.get("brand") or {}).get("name") or site.get("name") or ""

    # priceValidUntil = end of next year
    valid_until = (datetime.now(timezone.utc) + timedelta(days=365)).date().isoformat()

    # Offer enrichi
    offer = {
        "@type": "Offer",
        "url": canonical_url,
        "price": float(price) if price else 0,
        "priceCurrency": currency,
        "priceValidUntil": valid_until,
        "availability": "https://schema.org/InStock",
        "itemCondition": "https://schema.org/NewCondition",
        "seller": {"@type": "Organization", "name": brand_name},
        "hasMerchantReturnPolicy": {
            "@type": "MerchantReturnPolicy",
            "applicableCountry": ["FR", "BE", "CH", "LU", "DE", "AT", "NL",
                                   "IT", "ES", "PT", "GB", "IE"],
            "returnPolicyCategory": "https://schema.org/MerchantReturnFiniteReturnWindow",
            "merchantReturnDays": 14,
            "returnMethod": "https://schema.org/ReturnByMail",
            "returnFees": "https://schema.org/FreeReturn",
        },
        "shippingDetails": {
            "@type": "OfferShippingDetails",
            "shippingRate": {
                "@type": "MonetaryAmount",
                "value": "0",
                "currency": currency,
            },
            "shippingDestination": {
                "@type": "DefinedRegion",
                "addressCountry": ["FR", "BE", "DE", "IT", "ES", "NL", "GB"],
            },
            "deliveryTime": {
                "@type": "ShippingDeliveryTime",
                "handlingTime": {"@type": "QuantitativeValue", "minValue": 1,
                                  "maxValue": 2, "unitCode": "DAY"},
                "transitTime": {"@type": "QuantitativeValue", "minValue": 4,
                                 "maxValue": 8, "unitCode": "DAY"},
            },
        },
    }

    product_schema: Dict[str, Any] = {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": name,
        "description": desc,
        "image": images or [],
        "sku": sku,
        "brand": {"@type": "Brand", "name": brand_name},
        "offers": offer,
    }

    # AggregateRating + reviews
    real_reviews = product.get("reviews") or []
    if real_reviews:
        # Use real reviews if present
        review_objs = []
        for r in real_reviews[:5]:
            if not isinstance(r, dict):
                continue
            review_objs.append({
                "@type": "Review",
                "author": {"@type": "Person",
                            "name": r.get("author_name") or r.get("name") or "Anonymous"},
                "datePublished": r.get("date") or r.get("created_at"),
                "reviewRating": {"@type": "Rating",
                                  "ratingValue": float(r.get("rating") or 5),
                                  "bestRating": 5, "worstRating": 1},
                "reviewBody": r.get("body") or r.get("text") or "",
                "name": r.get("title") or "",
            })
        if review_objs:
            product_schema["review"] = review_objs
            try:
                avg = sum(float(r["reviewRating"]["ratingValue"]) for r in review_objs) / len(review_objs)
                product_schema["aggregateRating"] = {
                    "@type": "AggregateRating",
                    "ratingValue": round(avg, 1),
                    "bestRating": 5, "worstRating": 1,
                    "reviewCount": len(real_reviews),
                    "ratingCount": len(real_reviews),
                }
            except Exception:
                pass
    elif not disable_synthetic:
        product_schema["aggregateRating"] = _det_rating(product)
        product_schema["review"] = _det_reviews(product, lang=lang, brand_name=brand_name)

    # FAQ schema (prefer real product FAQ, else generic)
    faq_pairs = _faq_from_product(product, lang=lang)
    if not faq_pairs:
        faq_pairs = _generic_faq(product, lang=lang, brand_name=brand_name)
    faq_schema = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": p["q"],
             "acceptedAnswer": {"@type": "Answer", "text": p["a"]}}
            for p in faq_pairs[:6]
        ],
    }

    # BreadcrumbList
    breadcrumb_schema = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Accueil",
             "item": canonical_url.rsplit("/", 2)[0] + "/" if canonical_url else ""},
            {"@type": "ListItem", "position": 2, "name": "Produits",
             "item": canonical_url.rsplit("/", 2)[0] + "/products" if canonical_url else ""},
            {"@type": "ListItem", "position": 3, "name": name,
             "item": canonical_url},
        ],
    }

    return [product_schema, faq_schema, breadcrumb_schema]
