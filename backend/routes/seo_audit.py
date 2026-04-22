"""
SEO Dashboard — per-site audit of SEO health and content completeness.

Reports :
- Overall SEO score (0-100) based on 6 dimensions
- Per-product enrichment status (narrative, SEO, reviews)
- Coverage indicators (blog posts count, collections, schemas)
- Recommendations with concrete actions

Read-only endpoint : `GET /api/sites/{id}/seo-audit`
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends

from deps import db, get_current_user

logger = logging.getLogger("conceptfactory.seo_audit")
router = APIRouter()


def _pct(num: int, total: int) -> int:
    if total <= 0:
        return 0
    return round((num / total) * 100)


@router.get("/sites/{site_id}/seo-audit")
async def seo_audit(site_id: str, user=Depends(get_current_user)):
    """Comprehensive SEO audit for a site — ~6 dimensions scored 0-100."""
    site = await db.sites.find_one({"id": site_id}, {"_id": 0})
    if not site:
        raise HTTPException(404, "Site introuvable")

    design = site.get("design") or {}
    brand = design.get("brand") or {}
    published = bool(design.get("published"))

    # Products
    products = await db.products.find(
        {"site_id": site_id, "status": "active"},
        {"_id": 0, "id": 1, "name": 1, "narrative": 1, "reviews": 1, "rating": 1, "category": 1, "tags": 1, "bundles_with": 1, "images": 1, "updated_at": 1}
    ).to_list(5000)
    total_products = len(products)
    enriched_products = sum(1 for p in products if (p.get("narrative") or {}).get("seo"))
    products_with_reviews = sum(1 for p in products if (p.get("reviews") or []))
    products_with_bundles = sum(1 for p in products if (p.get("bundles_with") or []))
    products_with_images = sum(1 for p in products if (p.get("images") or []))

    # Blog
    blog_posts = design.get("blog_posts") or []
    blog_count = len(blog_posts)

    # Collections
    collections = design.get("collections") or []
    collection_count = len(collections) if isinstance(collections, list) else 0

    # Brand
    has_brand = bool(brand.get("primary_color") and brand.get("font_heading"))
    has_logo = bool(brand.get("logo_url"))
    has_tagline = bool(brand.get("tagline"))

    # Legal + about
    legal_pages = design.get("legal_pages") or {}
    legal_complete = all(legal_pages.get(k, {}).get("body_md") for k in ["cgv", "mentions_legales", "confidentialite"])

    about_done = bool((design.get("about") or {}).get("paragraphs"))
    contact_done = bool((design.get("contact") or {}).get("email"))
    values_done = bool(design.get("values"))
    founder_done = bool(design.get("founder_story"))

    # Dimension scores (0-100)
    d_catalog = 0
    if total_products > 0:
        d_catalog = round(
            25 * min(1, total_products / 10)  # enough products (10)
            + 25 * min(1, products_with_images / max(1, total_products))  # all products have images
            + 30 * (enriched_products / total_products)  # AI narrative coverage
            + 20 * (products_with_bundles / max(1, total_products))  # cross-sell coverage
        )

    d_content = round(
        50 * min(1, blog_count / 10)  # blog coverage
        + 20 * (1 if about_done else 0)
        + 15 * (1 if values_done else 0)
        + 15 * (1 if founder_done else 0)
    )

    d_structure = round(
        30 * (1 if has_brand else 0)
        + 20 * (1 if has_logo else 0)
        + 20 * (1 if has_tagline else 0)
        + 15 * (1 if collection_count >= 3 else 0)
        + 15 * (1 if published else 0)
    )

    d_trust = 0
    if total_products > 0:
        d_trust = round(
            50 * (products_with_reviews / max(1, total_products))
            + 30 * (1 if legal_complete else 0)
            + 20 * (1 if contact_done else 0)
        )
    else:
        d_trust = round(30 * (1 if legal_complete else 0) + 20 * (1 if contact_done else 0))

    # AEO / technical
    d_aeo = round(
        25 * (1 if published else 0)
        + 25 * (1 if enriched_products >= max(1, total_products * 0.5) else 0)
        + 20 * (1 if blog_count >= 3 else 0)
        + 15 * (1 if has_brand else 0)
        + 15 * (1 if collection_count >= 3 else 0)
    )

    # Freshness — recent updates
    now = datetime.now(timezone.utc)
    thirty_days_ago = now - timedelta(days=30)
    fresh_products = 0
    for p in products:
        up = p.get("updated_at")
        if isinstance(up, str):
            try:
                if datetime.fromisoformat(up.replace("Z", "+00:00")) > thirty_days_ago:
                    fresh_products += 1
            except Exception:
                pass
        elif isinstance(up, datetime):
            if up > thirty_days_ago:
                fresh_products += 1
    d_freshness = _pct(fresh_products + min(blog_count, 3) * 10, max(1, total_products) + 30)
    d_freshness = min(100, d_freshness)

    overall = round((d_catalog + d_content + d_structure + d_trust + d_aeo + d_freshness) / 6)

    # Recommendations
    recos = []
    if not published:
        recos.append({"severity": "critical", "text": "Votre boutique n'est pas publiée — aucune page n'est indexée par Google.", "action": "Valider le prompt #17 pour publier"})
    if total_products < 10:
        recos.append({"severity": "high", "text": f"Seulement {total_products} produit(s) actif(s). Les sites avec <10 produits rankent difficilement.", "action": "Ajouter plus de produits (catalogue #16)"})
    if total_products > 0 and enriched_products < total_products:
        missing = total_products - enriched_products
        recos.append({"severity": "high", "text": f"{missing} produit(s) sans narratif IA (SEO + AEO incomplet).", "action": f"Déclencher 'Auto-bundles IA' et 'Régénérer IA' sur ces produits"})
    if blog_count < 10:
        recos.append({"severity": "high", "text": f"{blog_count} article(s) blog — 10+ articles sont recommandés pour un ranking organique sérieux.", "action": "Valider le prompt #27 (génération auto 10 articles) ou utiliser 'Rédiger avec l'IA'"})
    if total_products > 0 and products_with_bundles == 0:
        recos.append({"severity": "medium", "text": "Aucun cross-sell configuré entre vos produits (panier moyen sous-optimal).", "action": "Bouton 'Auto-bundles IA' dans la page Produits"})
    if total_products > 0 and products_with_reviews == 0:
        recos.append({"severity": "medium", "text": "Aucun avis client publié — les snippets 'étoiles' Google sont désactivés.", "action": "Marquer des commandes comme livrées → invitations envoyées à J+14"})
    if not has_logo:
        recos.append({"severity": "low", "text": "Pas de logo défini — moins premium en SERP et Knowledge Graph.", "action": "Valider le prompt #6 (brand book) avec upload logo"})
    if not legal_complete:
        recos.append({"severity": "medium", "text": "Pages légales incomplètes (impact confiance + conformité RGPD).", "action": "Valider le prompt #9 (legal docs)"})
    if not about_done:
        recos.append({"severity": "medium", "text": "Page 'À propos' vide — signal E-E-A-T manquant pour Google.", "action": "Renseigner `design.about.paragraphs`"})

    return {
        "site_id": site_id,
        "site_name": site.get("name"),
        "published": published,
        "audited_at": now.isoformat(),
        "overall_score": overall,
        "dimensions": {
            "catalog": {"score": d_catalog, "label": "Catalogue produit"},
            "content": {"score": d_content, "label": "Contenu éditorial"},
            "structure": {"score": d_structure, "label": "Structure & branding"},
            "trust": {"score": d_trust, "label": "Confiance (avis + légal)"},
            "aeo": {"score": d_aeo, "label": "AEO (réponses IA)"},
            "freshness": {"score": d_freshness, "label": "Fraîcheur du contenu"},
        },
        "coverage": {
            "products_total": total_products,
            "products_enriched": enriched_products,
            "products_with_reviews": products_with_reviews,
            "products_with_bundles": products_with_bundles,
            "products_with_images": products_with_images,
            "blog_posts": blog_count,
            "collections": collection_count,
        },
        "checks": {
            "published": published,
            "has_brand": has_brand,
            "has_logo": has_logo,
            "has_tagline": has_tagline,
            "legal_complete": legal_complete,
            "about_done": about_done,
            "contact_done": contact_done,
            "values_done": values_done,
            "founder_done": founder_done,
        },
        "recommendations": recos,
    }
