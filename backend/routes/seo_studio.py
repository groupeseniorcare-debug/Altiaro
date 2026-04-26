"""
SEO/AEO Studio — advanced optimization endpoints.

- GET /api/public/sites/{id}/products/{pid}/jsonld
    → Product JSON-LD (+ FAQ + BreadcrumbList + AggregateRating if reviews)
      for AI engines (ChatGPT, Perplexity) and rich Google snippets.

- GET /api/sites/{id}/seo/aeo-readiness
    → Per-page AEO readiness checklist.

- POST /api/sites/{id}/seo/bulk-optimize
    → Claude generates SEO metadata for all products missing it
      (title ≤ 60 chars, meta description ≤ 155 chars, 5 keywords,
      alt-text for each image, long-tail queries) in one pass per product.

- GET /api/sites/{id}/seo/keyword-strategy
    → Mines google data + active products to return transactional vs
      informational keyword map per market.
"""
from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel

from deps import db, get_current_user

logger = logging.getLogger("conceptfactory.seo_studio")
router = APIRouter()


def _origin() -> str:
    return os.environ.get("PUBLIC_FRONTEND_URL") or os.environ.get("REACT_APP_BACKEND_URL") or "https://www.example.com"


def _name_fr(p: dict) -> str:
    n = p.get("name") or {}
    if isinstance(n, dict):
        return n.get("fr") or n.get("en") or next(iter(n.values()), "") or "(sans nom)"
    return str(n or "(sans nom)")


def _desc_fr(p: dict) -> str:
    d = p.get("description") or {}
    if isinstance(d, dict):
        return d.get("fr") or d.get("en") or ""
    return str(d or "")


# =====================================================================
# 1. Public JSON-LD per product — rich schema for AI engines + Google
# =====================================================================
@router.get("/public/sites/{site_id}/products/{product_id}/jsonld")
async def product_jsonld(site_id: str, product_id: str):
    """Returns a JSON-LD array combining Product, Offer, BreadcrumbList
    and (if present) FAQPage & AggregateRating.
    Storefront product page should inject this as <script type="application/ld+json">.
    """
    product = await db.products.find_one(
        {"id": product_id, "site_id": site_id, "status": "active"},
        {"_id": 0},
    )
    if not product:
        raise HTTPException(status_code=404, detail="Produit introuvable")
    site = await db.sites.find_one({"id": site_id}, {"_id": 0, "design.brand": 1, "name": 1})
    brand = ((site or {}).get("design") or {}).get("brand") or {}
    brand_name = brand.get("name") or (site or {}).get("name") or "Boutique"
    origin = _origin()
    product_url = f"{origin}/shop/{site_id}/product/{product_id}"

    name = _name_fr(product)
    description = _desc_fr(product) or (product.get("narrative") or {}).get("seo", {}).get("meta_description") or ""
    images = product.get("images") or []

    offer = {
        "@type": "Offer",
        "url": product_url,
        "priceCurrency": product.get("currency") or "EUR",
        "price": round(float(product.get("price") or 0), 2),
        "availability": "https://schema.org/InStock" if (product.get("stock") is None or product.get("stock", 1) > 0) else "https://schema.org/OutOfStock",
        "itemCondition": "https://schema.org/NewCondition",
        "seller": {"@type": "Organization", "name": brand_name},
    }
    product_schema: dict = {
        "@context": "https://schema.org/",
        "@type": "Product",
        "@id": f"{product_url}#product",
        "name": name,
        "description": description[:300],
        "image": images[:8],
        "sku": product.get("sku") or product_id,
        "brand": {"@type": "Brand", "name": brand_name},
        "offers": offer,
        "url": product_url,
    }
    reviews = product.get("reviews") or []
    if reviews:
        rating_sum = sum(float(r.get("rating") or 5) for r in reviews)
        avg = round(rating_sum / len(reviews), 1)
        product_schema["aggregateRating"] = {
            "@type": "AggregateRating",
            "ratingValue": avg,
            "reviewCount": len(reviews),
            "bestRating": 5,
            "worstRating": 1,
        }

    breadcrumb = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Accueil", "item": f"{origin}/shop/{site_id}"},
            {"@type": "ListItem", "position": 2, "name": "Produits", "item": f"{origin}/shop/{site_id}"},
            {"@type": "ListItem", "position": 3, "name": name, "item": product_url},
        ],
    }

    out = [product_schema, breadcrumb]

    # FAQ schema — use narrative.faq if Claude produced one, else fallback
    narrative = product.get("narrative") or {}
    faq_items = narrative.get("faq") or []
    if faq_items:
        out.append({
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": [
                {
                    "@type": "Question",
                    "name": (q.get("question") or q.get("q") or "")[:200],
                    "acceptedAnswer": {"@type": "Answer", "text": (q.get("answer") or q.get("a") or "")[:800]},
                }
                for q in faq_items[:10]
                if (q.get("question") or q.get("q")) and (q.get("answer") or q.get("a"))
            ],
        })
    return out


# =====================================================================
# 2. AEO Readiness — checklist of AI-engine-friendly signals
# =====================================================================
@router.get("/sites/{site_id}/seo/aeo-readiness")
async def aeo_readiness(site_id: str, user=Depends(get_current_user)):
    site = await db.sites.find_one(
        {"id": site_id},
        {"_id": 0, "design": 1, "selected_countries": 1, "selected_languages": 1, "name": 1},
    )
    if not site:
        raise HTTPException(404, "Site introuvable")
    design = site.get("design") or {}

    products = await db.products.find(
        {"site_id": site_id, "status": "active"},
        {"_id": 0, "id": 1, "name": 1, "narrative": 1, "images": 1, "description": 1}
    ).to_list(2000)
    total = len(products)
    with_faq = sum(1 for p in products if (p.get("narrative") or {}).get("faq"))
    with_seo_meta = sum(1 for p in products if (p.get("narrative") or {}).get("seo"))
    with_alt = sum(1 for p in products if all(isinstance(img, dict) and img.get("alt") for img in (p.get("images") or []) if isinstance(img, dict)))

    checks = [
        {"key": "has_brand", "label": "Identité de marque complète", "ok": bool((design.get("brand") or {}).get("name")), "weight": 10,
         "how_to_fix": "Remplis nom + tagline + palette dans l'Étape 5 → Identité."},
        {"key": "llms_txt", "label": "Fichier /llms.txt généré (AI crawlers)", "ok": True, "weight": 15,
         "how_to_fix": "Automatique — vérifier /api/public/sites/{id}/llms.txt"},
        {"key": "sitemap", "label": "sitemap.xml + hreflang multi-marchés", "ok": len(site.get("selected_countries") or []) >= 1, "weight": 10,
         "how_to_fix": "Automatique pour tous les pays sélectionnés."},
        {"key": "product_faq", "label": f"FAQ produit (≥70%)  —  {with_faq}/{total}", "ok": total > 0 and with_faq / total >= 0.7, "weight": 15,
         "how_to_fix": "Lance SEO → Bulk optimize IA pour générer les FAQ manquantes."},
        {"key": "product_seo_meta", "label": f"Meta titles/descriptions IA (≥80%) — {with_seo_meta}/{total}", "ok": total > 0 and with_seo_meta / total >= 0.8, "weight": 15,
         "how_to_fix": "Lance SEO → Bulk optimize IA."},
        {"key": "alt_texts", "label": f"Alt-texts images (≥50%) — {with_alt}/{total}", "ok": total > 0 and with_alt / total >= 0.5, "weight": 10,
         "how_to_fix": "Les alt-texts sont générés avec le bulk optimize IA."},
        {"key": "blog_content", "label": "Blog ≥ 5 articles (contenu informationnel)", "ok": len(design.get("blog_posts") or []) >= 5, "weight": 10,
         "how_to_fix": "Publie 5 articles infos (« Comment choisir un fauteuil releveur ? » etc.)."},
        {"key": "structured_contact", "label": "Contact & adresse renseignés (Local SEO)", "ok": bool((design.get("contact") or {}).get("email")), "weight": 5,
         "how_to_fix": "Remplis email + téléphone + adresse dans Étape 5 → Pages."},
        {"key": "legal_pages", "label": "CGV + Mentions + Confidentialité", "ok": all((design.get("legal_pages") or {}).get(k, {}).get("body_md") for k in ["cgv", "mentions_legales", "confidentialite"]), "weight": 5,
         "how_to_fix": "Automatique depuis infos société (Compte → Société)."},
        {"key": "published", "label": "Site publié (indexable)", "ok": bool(design.get("published")), "weight": 5,
         "how_to_fix": "Clique sur Publier dans le Studio de marque."},
    ]
    total_weight = sum(c["weight"] for c in checks)
    earned = sum(c["weight"] for c in checks if c["ok"])
    score = round((earned / total_weight) * 100) if total_weight else 0
    verdict = "excellent" if score >= 85 else "bon" if score >= 65 else "moyen" if score >= 40 else "faible"
    return {
        "score": score,
        "verdict": verdict,
        "checks": checks,
        "coverage": {
            "products_total": total,
            "products_with_faq": with_faq,
            "products_with_seo_meta": with_seo_meta,
            "products_with_alt": with_alt,
        },
    }


# =====================================================================
# 3. Bulk optimize SEO metadata for all products — uses Claude
# =====================================================================
class BulkOptimizeInput(BaseModel):
    force: bool = False  # re-generate even if seo_meta already exists
    only_missing: bool = True


async def _bulk_optimize_job(site_id: str, force: bool):
    """Runs in background — calls Claude per product to fill narrative.seo
    + generate alt-texts for images.  Skips products that already have SEO.

    Phase 0 — utilise `safe_claude_text` (retry expo + circuit breaker). Mode
    dégradé : un produit qui échoue n'arrête pas le batch.
    """
    from services.llm_resilience import safe_claude_text, LLMUnavailableError
    key = os.environ.get("EMERGENT_LLM_KEY")
    if not key:
        logger.error("[seo-bulk] EMERGENT_LLM_KEY missing")
        return

    site = await db.sites.find_one({"id": site_id}, {"_id": 0, "design.brand": 1, "selected_languages": 1})
    brand = ((site or {}).get("design") or {}).get("brand") or {}
    brand_name = brand.get("name") or "notre boutique"
    voice = brand.get("voice") or "chaleureux, expert, rassurant"

    q = {"site_id": site_id, "status": "active"}
    if not force:
        q["$or"] = [{"narrative": None}, {"narrative.seo": {"$exists": False}}]
    cursor = db.products.find(q, {"_id": 0})

    system_msg = (
        "Tu es un expert SEO/AEO pour e-commerce. Pour chaque produit, tu produis "
        "un JSON strict sans commentaire avec : seo_title (≤60 car), meta_description "
        "(≤155 car, inclut un CTA), keywords (5 long-tail FR, mix transactionnel + "
        "informationnel), alt_texts (array, 1 par image, ≤125 car, décrit la scène et "
        "inclut un keyword secondaire), faq (3 questions/réponses courtes pour AEO). "
        f"Ton de marque : {voice}. Marque : {brand_name}."
    )

    async for p in cursor:
        try:
            name = _name_fr(p)
            desc = _desc_fr(p) or ""
            nb_images = len(p.get("images") or [])
            alt_placeholders = ",".join(['"..."'] * max(nb_images, 1))
            prompt = (
                f"Produit : {name}\nDescription : {desc[:400]}\n"
                f"Prix : {p.get('price')} €\nNombre d'images : {nb_images}\n\n"
                "Réponds UNIQUEMENT avec un JSON :\n"
                '{"seo_title":"...","meta_description":"...","keywords":["...","...","...","...","..."],'
                f'"alt_texts":[{alt_placeholders}],'
                '"faq":[{"question":"...","answer":"..."},{"question":"...","answer":"..."},{"question":"...","answer":"..."}]}'
            )
            try:
                txt = await safe_claude_text(
                    system_msg, prompt,
                    session_id=f"seo-bulk-{site_id}-{p['id']}",
                    timeout=120,
                )
            except LLMUnavailableError as e:
                logger.warning(f"[seo-bulk] LLM down for {p['id']}: {e.last_error} — skip product")
                continue
            txt = (txt or "").strip()
            if txt.startswith("```"):
                txt = re.sub(r"^```(?:json)?\n?", "", txt).rstrip("` \n")
            try:
                data = json.loads(txt)
            except json.JSONDecodeError:
                logger.warning(f"[seo-bulk] invalid JSON for {p['id']} — skip")
                continue

            # Persist into narrative.seo + update image alt-texts
            narrative = p.get("narrative") or {}
            narrative["seo"] = {
                "title": (data.get("seo_title") or "")[:65],
                "meta_description": (data.get("meta_description") or "")[:160],
                "keywords": data.get("keywords") or [],
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }
            narrative["faq"] = data.get("faq") or narrative.get("faq") or []

            images = p.get("images") or []
            alt_texts = data.get("alt_texts") or []
            new_images = []
            for i, img in enumerate(images):
                alt = (alt_texts[i] if i < len(alt_texts) else "").strip() or name
                if isinstance(img, str):
                    new_images.append({"url": img, "alt": alt[:130]})
                elif isinstance(img, dict):
                    new_images.append({**img, "alt": alt[:130]})
            await db.products.update_one(
                {"id": p["id"], "site_id": site_id},
                {"$set": {
                    "narrative": narrative,
                    "images": new_images or images,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }},
            )
            logger.info("[seo-bulk] optimized %s", p["id"])
        except Exception as e:
            logger.exception("[seo-bulk] failed for %s: %s", p.get("id"), e)

    await db.sites.update_one(
        {"id": site_id},
        {"$set": {"design.seo_bulk_last_run": datetime.now(timezone.utc).isoformat()}},
    )


@router.post("/sites/{site_id}/seo/bulk-optimize")
async def bulk_optimize(
    site_id: str,
    body: BulkOptimizeInput,
    background_tasks: BackgroundTasks,
    user=Depends(get_current_user),
):
    """Kicks off a background job that generates SEO metadata for all products."""
    site = await db.sites.find_one({"id": site_id}, {"_id": 0, "id": 1})
    if not site:
        raise HTTPException(404, "Site introuvable")
    total = await db.products.count_documents({"site_id": site_id, "status": "active"})
    background_tasks.add_task(_bulk_optimize_job, site_id, body.force)
    return {
        "ok": True,
        "queued_products": total,
        "message": f"Optimisation IA lancée en arrière-plan sur {total} produit(s). Recharge dans 1-3 minutes.",
    }


# =====================================================================
# 4. Keyword strategy per market (transactional vs informational)
# =====================================================================
@router.get("/sites/{site_id}/seo/keyword-strategy")
async def keyword_strategy(site_id: str, user=Depends(get_current_user)):
    site = await db.sites.find_one(
        {"id": site_id},
        {"_id": 0, "selected_countries": 1, "design.niche_analysis": 1, "design.ai_search_terms": 1},
    )
    if not site:
        raise HTTPException(404, "Site introuvable")
    countries = site.get("selected_countries") or ["FR"]
    niche_an = (site.get("design") or {}).get("niche_analysis") or {}
    results = niche_an.get("results") or []

    def _classify(kw: str) -> str:
        """Transactional if 'acheter|prix|commander|pas cher|meilleur', else informational."""
        kw_l = (kw or "").lower()
        if re.search(r"\b(acheter|achat|prix|commander|meilleur|pas cher|promo|avis)\b", kw_l):
            return "transactional"
        if re.search(r"\b(comment|pourquoi|guide|choisir|quand|quoi|est-ce)\b", kw_l):
            return "informational"
        return "neutral"

    per_market = {}
    for cc in countries:
        market_res = next((r for r in results if r.get("country") == cc), None)
        kws = (market_res or {}).get("keywords") or []
        classified = {"transactional": [], "informational": [], "neutral": []}
        for k in kws:
            kw = k.get("keyword") if isinstance(k, dict) else str(k)
            bucket = _classify(kw)
            classified[bucket].append({
                "keyword": kw,
                "volume": (k.get("volume_monthly") if isinstance(k, dict) else None) or 0,
                "cpc": (k.get("cpc_eur") if isinstance(k, dict) else None) or 0,
                "competition": (k.get("competition") if isinstance(k, dict) else None) or 0,
            })
        per_market[cc] = {
            **{k: sorted(v, key=lambda x: -x["volume"])[:15] for k, v in classified.items()},
            "total": len(kws),
            "has_data": bool(market_res),
        }
    # Blog topic suggestions (informational gap)
    blog_suggestions = []
    for cc, data in per_market.items():
        for info_kw in data["informational"][:3]:
            blog_suggestions.append({
                "country": cc,
                "keyword": info_kw["keyword"],
                "suggested_title": f"{info_kw['keyword'].capitalize()} : guide complet 2026",
                "volume": info_kw["volume"],
            })
    return {
        "per_market": per_market,
        "blog_suggestions": blog_suggestions[:10],
    }
