"""
SEO Content Generators — Sprint 2 (Étape 9 du Cockpit).

Génère automatiquement à chaque launch d'un site :
- 5 Buyer Guides (2000 mots, Schema Article + FAQPage)
- 40 termes de glossaire (Schema DefinedTerm + DefinedTermSet)
- 10 pages Comparaison X vs Y (Schema Article + ItemList)
- 5 Top Lists (Schema ItemList + Article)

Tout persisté dans les collections Mongo :
- `landing_pages` (kind = "buyer_guide" | "comparison" | "top_list")
- `glossary_terms` (une doc par terme)

Stratégie LLM : Claude Sonnet via `safe_claude_json`. Retry + tolerant parse.
Rate-limiting : asyncio.Semaphore(3) pour parallelisation douce.
Budget : ~2.65 $/site pour les 60 pages générées. À utiliser après
`keyword_universe` (étape 9 keywords discover).
"""
from __future__ import annotations

import asyncio
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from deps import db
from services.llm_resilience import safe_claude_json
from services.slugify import slugify

logger = logging.getLogger("altiaro.seo_content")

_SEM = asyncio.Semaphore(2)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_str(v: Any, fallback: str = "") -> str:
    if isinstance(v, dict):
        return v.get("fr") or v.get("en") or fallback
    return str(v or fallback)


async def _products_of(site_id: str) -> List[Dict[str, Any]]:
    return await db.products.find(
        {"site_id": site_id, "status": "active", "role": {"$ne": "upsell"}},
        {"_id": 0, "id": 1, "slug": 1, "name": 1, "price": 1, "category": 1,
         "narrative": 1, "images": 1, "generated_images": 1, "currency": 1},
    ).to_list(50)


# ────────────────────────────────────────────────────────────────────────
# 1. BUYER GUIDES (5 per site)
# ────────────────────────────────────────────────────────────────────────
BUYER_GUIDE_TOPICS = [
    {
        "slug_prefix": "comment-choisir",
        "title_fr": "Comment choisir un {niche} en {year}",
        "angle": "guide décisionnel complet avec critères d'achat chiffrés",
    },
    {
        "slug_prefix": "meilleurs",
        "title_fr": "Les meilleurs {niche} de {year}",
        "angle": "sélection premium avec 5-8 produits du catalogue détaillés",
    },
    {
        "slug_prefix": "guide-complet",
        "title_fr": "Guide complet {niche} : tout savoir avant d'acheter",
        "angle": "encyclopédie produit : histoire, typologies, technologies",
    },
    {
        "slug_prefix": "guide-achat",
        "title_fr": "Guide d'achat {niche} pour seniors",
        "angle": "guide orienté persona avec use cases et contre-indications",
    },
    {
        "slug_prefix": "erreurs-eviter",
        "title_fr": "5 erreurs à éviter avant d'acheter un {niche}",
        "angle": "tone éditorial conseil, mise en garde, testimonies clients",
    },
]


async def generate_buyer_guide(
    site: Dict[str, Any], topic: Dict[str, str],
    products: List[Dict[str, Any]], keywords: List[str],
) -> Dict[str, Any]:
    """Generate a single buyer guide ~2000 words. Returns a landing_pages doc."""
    niche = site.get("niche") or "produit"
    year = datetime.now(timezone.utc).year
    title = topic["title_fr"].format(niche=niche, year=year)
    slug = slugify(f"{topic['slug_prefix']}-{niche}-{year}")

    product_summaries = "\n".join(
        f"- {p.get('slug')}: {_ensure_str(p.get('name'))} · "
        f"{_ensure_str((p.get('narrative') or {}).get('subheadline'))} · "
        f"prix {p.get('price', 0)}{p.get('currency', 'EUR')}"
        for p in products[:8]
    )
    top_keywords = ", ".join(keywords[:25]) if keywords else ""

    system = (
        "Tu es un rédacteur SEO premium spécialiste e-commerce Silver Economy. "
        "Tu écris du contenu éditorial de niveau presse, chaleureux, honnête, "
        "avec des données concrètes, des listes, des tableaux markdown simulés, "
        "et une FAQ finale de 8-10 questions."
    )
    user = (
        f"Rédige un Buyer Guide SEO de 1000-1300 mots sur : « {title} ».\n\n"
        f"Angle éditorial : {topic['angle']}.\n"
        f"Marque : {site.get('name')}\n"
        f"Niche : {niche}\n"
        f"Public cible : seniors 60+ et aidants familiaux\n\n"
        f"Produits du catalogue à référencer (internal linking) :\n{product_summaries}\n\n"
        f"Top keywords à inclure naturellement : {top_keywords}\n\n"
        "Retourne un JSON strict avec ce schéma :\n"
        "{\n"
        '  "title": "...",\n'
        '  "meta_description": "150-160 caractères",\n'
        '  "h1": "...",\n'
        '  "intro": "150 mots hook qui répond directement",\n'
        '  "sections": [\n'
        '    {"h2": "...", "body_md": "markdown 300-400 mots", "product_refs": ["slug1","slug2"]}\n'
        "  ],\n"
        '  "comparison_table": {"headers": ["Critère","Produit A","Produit B"], "rows": [[...],[...]]},\n'
        '  "faq": [{"q": "...","a": "80-120 mots"}],\n'
        '  "cta_text": "phrase de conclusion avec CTA vers catalogue",\n'
        '  "internal_links": [{"anchor":"...","target_slug":"..."}],\n'
        '  "seo_keywords": ["kw1","kw2",...]\n'
        "}\n\n"
        "IMPORTANT : 4-6 sections, 6-8 FAQs, 4+ internal_links vers produits. "
        "Total body : 1000-1300 mots (pas plus)."
    )
    try:
        data = await safe_claude_json(
            system, user, quality_tier="standard",
            session_id=f"buyer-guide-{slug}",
            timeout=180, request_id=f"buyer-guide-{slug}",
        )
    except Exception as e:
        logger.warning(f"[buyer-guide] {slug} failed: {str(e)[:200]}")
        return {"ok": False, "slug": slug, "error": str(e)[:300]}

    doc = {
        "id": str(uuid.uuid4()),
        "site_id": site["id"],
        "kind": "buyer_guide",
        "slug": slug,
        "title": data.get("title") or title,
        "meta_description": data.get("meta_description", "")[:160],
        "h1": data.get("h1") or title,
        "intro": data.get("intro", ""),
        "sections": data.get("sections", []),
        "comparison_table": data.get("comparison_table"),
        "faq": data.get("faq", []),
        "cta_text": data.get("cta_text", ""),
        "internal_links": data.get("internal_links", []),
        "seo_keywords": data.get("seo_keywords", []),
        "word_count": sum(len((s.get("body_md") or "").split())
                          for s in data.get("sections", [])) + len(data.get("intro", "").split()),
        "created_at": _now(),
        "updated_at": _now(),
        "published": True,
    }
    await db.landing_pages.update_one(
        {"site_id": site["id"], "slug": slug},
        {"$set": doc}, upsert=True,
    )
    return {"ok": True, "slug": slug, "word_count": doc["word_count"]}


async def generate_all_buyer_guides(site_id: str) -> Dict[str, Any]:
    site = await db.sites.find_one({"id": site_id}, {"_id": 0})
    if not site:
        return {"ok": False, "error": "site not found"}
    products = await _products_of(site_id)
    if not products:
        return {"ok": False, "error": "no products"}
    keywords = [k["keyword"] for k in await db.keyword_universe.find(
        {"site_id": site_id}, {"_id": 0, "keyword": 1}
    ).limit(50).to_list(50)]

    async def run_one(t):
        async with _SEM:
            return await generate_buyer_guide(site, t, products, keywords)
    results = await asyncio.gather(*[run_one(t) for t in BUYER_GUIDE_TOPICS])
    ok = sum(1 for r in results if r.get("ok"))
    return {"ok": True, "generated": ok, "total": len(BUYER_GUIDE_TOPICS),
            "details": results}


# ────────────────────────────────────────────────────────────────────────
# 2. GLOSSARY (40 terms per site)
# ────────────────────────────────────────────────────────────────────────
async def generate_glossary(site_id: str, target_count: int = 40) -> Dict[str, Any]:
    """Generate 40 niche-specific glossary terms with 50-100 word definitions."""
    site = await db.sites.find_one({"id": site_id}, {"_id": 0})
    if not site:
        return {"ok": False, "error": "site not found"}
    niche = site.get("niche") or "produit"
    products = await _products_of(site_id)
    product_kinds = list({_ensure_str(p.get("category")) for p in products if p.get("category")})[:8]

    system = (
        "Tu es un terminologue expert e-commerce. Tu rédiges des définitions "
        "claires, précises, de 60-100 mots, accessibles aux seniors 60+ mais "
        "techniquement correctes."
    )
    user = (
        f"Génère un glossaire de {target_count} termes techniques/fonctionnels "
        f"pertinents pour la niche « {niche} » (sous-catégories : {product_kinds}).\n\n"
        "Couvre :\n"
        "- Termes techniques (matériaux, mécanismes, certifications)\n"
        "- Termes fonctionnels (modes, réglages, fonctionnalités)\n"
        "- Termes anatomiques / médicaux (ergonomie, confort, santé)\n"
        "- Termes business (garantie, SAV, remboursement)\n\n"
        "Retourne un JSON strict :\n"
        '{"terms": [{"term":"...","slug":"...","definition":"60-100 mots",'
        '"related_slugs":["slug-autre-terme"],"category":"technique|fonctionnel|sante|business"}]}'
    )
    try:
        data = await safe_claude_json(
            system, user, quality_tier="standard",
            session_id=f"glossary-{site_id[:8]}",
            timeout=180, request_id=f"glossary-{site_id[:8]}",
        )
    except Exception as e:
        logger.warning(f"[glossary] failed: {str(e)[:200]}")
        return {"ok": False, "error": str(e)[:300]}

    terms = data.get("terms") or []
    inserted = 0
    for t in terms[:target_count]:
        slug = t.get("slug") or slugify(t.get("term", ""))
        if not slug:
            continue
        doc = {
            "id": str(uuid.uuid4()),
            "site_id": site_id,
            "term": t.get("term", ""),
            "slug": slug,
            "definition": t.get("definition", ""),
            "related_slugs": t.get("related_slugs", []),
            "category": t.get("category", "technique"),
            "created_at": _now(),
            "updated_at": _now(),
            "published": True,
        }
        await db.glossary_terms.update_one(
            {"site_id": site_id, "slug": slug},
            {"$set": doc}, upsert=True,
        )
        inserted += 1
    return {"ok": True, "generated": inserted, "requested": target_count}


# ────────────────────────────────────────────────────────────────────────
# 3. COMPARISON PAGES (10 per site)
# ────────────────────────────────────────────────────────────────────────
def _pick_comparison_pairs(products: List[Dict[str, Any]], limit: int = 10) -> List[tuple]:
    """Pick the most interesting pairs: same category or similar price range."""
    pairs: List[tuple] = []
    for i, a in enumerate(products):
        for b in products[i + 1:]:
            same_cat = a.get("category") == b.get("category") and a.get("category")
            price_close = abs((a.get("price") or 0) - (b.get("price") or 0)) < 300
            score = (2 if same_cat else 0) + (1 if price_close else 0)
            pairs.append((score, a, b))
    pairs.sort(key=lambda x: -x[0])
    return [(a, b) for _, a, b in pairs[:limit]]


async def generate_comparison(site: Dict[str, Any], a: Dict, b: Dict) -> Dict[str, Any]:
    slug_a = a.get("slug") or a.get("id")
    slug_b = b.get("slug") or b.get("id")
    slug = slugify(f"{slug_a}-vs-{slug_b}")[:80]
    a_name = _ensure_str(a.get("name"))
    b_name = _ensure_str(b.get("name"))

    system = (
        "Tu es un journaliste produit. Tu compares 2 produits d'une même marque "
        "honnêtement, avec un verdict contextuel (pour qui A, pour qui B)."
    )
    user = (
        f"Rédige une comparaison SEO de 800-1000 mots : « {a_name} vs {b_name} ».\n\n"
        f"Produit A ({slug_a}) : {_ensure_str((a.get('narrative') or {}).get('subheadline'))} "
        f"· {a.get('price', 0)}€\n"
        f"Produit B ({slug_b}) : {_ensure_str((b.get('narrative') or {}).get('subheadline'))} "
        f"· {b.get('price', 0)}€\n\n"
        "Retourne un JSON strict :\n"
        '{"title":"...","meta_description":"160 chars","h1":"...",'
        '"intro":"100 mots","comparison_table":{"headers":[...],"rows":[[...]]},'
        '"section_a_strengths":"250 mots","section_b_strengths":"250 mots",'
        '"verdict":"200 mots avec recommandation par persona",'
        '"faq":[{"q":"","a":"80 mots"}],'
        '"seo_keywords":["..."]}'
    )
    try:
        data = await safe_claude_json(
            system, user, quality_tier="standard",
            session_id=f"cmp-{slug[:40]}",
            timeout=150, request_id=f"cmp-{slug[:40]}",
        )
    except Exception as e:
        return {"ok": False, "slug": slug, "error": str(e)[:200]}

    doc = {
        "id": str(uuid.uuid4()),
        "site_id": site["id"],
        "kind": "comparison",
        "slug": slug,
        "product_a_slug": slug_a,
        "product_b_slug": slug_b,
        "title": data.get("title"),
        "meta_description": (data.get("meta_description") or "")[:160],
        "h1": data.get("h1"),
        "intro": data.get("intro", ""),
        "comparison_table": data.get("comparison_table"),
        "section_a_strengths": data.get("section_a_strengths", ""),
        "section_b_strengths": data.get("section_b_strengths", ""),
        "verdict": data.get("verdict", ""),
        "faq": data.get("faq", []),
        "seo_keywords": data.get("seo_keywords", []),
        "created_at": _now(), "updated_at": _now(), "published": True,
    }
    await db.landing_pages.update_one(
        {"site_id": site["id"], "slug": slug}, {"$set": doc}, upsert=True,
    )
    return {"ok": True, "slug": slug}


async def generate_all_comparisons(site_id: str, limit: int = 10) -> Dict[str, Any]:
    site = await db.sites.find_one({"id": site_id}, {"_id": 0})
    if not site:
        return {"ok": False, "error": "site not found"}
    products = await _products_of(site_id)
    if len(products) < 2:
        return {"ok": False, "error": "need at least 2 products"}
    pairs = _pick_comparison_pairs(products, limit=limit)

    async def run_one(a, b):
        async with _SEM:
            return await generate_comparison(site, a, b)
    results = await asyncio.gather(*[run_one(a, b) for a, b in pairs])
    ok = sum(1 for r in results if r.get("ok"))
    return {"ok": True, "generated": ok, "total": len(pairs), "details": results}


# ────────────────────────────────────────────────────────────────────────
# 4. TOP LISTS (5 per site)
# ────────────────────────────────────────────────────────────────────────
TOP_LIST_TOPICS = [
    ("top-5-{niche}-{year}", "Top 5 {niche} {year}", "best-of éditorial"),
    ("top-3-{niche}-seniors", "Top 3 {niche} pour seniors", "ciblé persona senior autonome"),
    ("top-5-{niche}-pas-cher", "Top 5 {niche} pas chers de {year}", "value-for-money"),
    ("top-5-{niche}-premium", "Top 5 {niche} premium", "haut de gamme, pas de compromis"),
    ("top-3-{niche}-petit-salon", "Top 3 {niche} pour petit espace", "compact / petit salon"),
]


async def generate_top_list(
    site: Dict[str, Any], topic: tuple, products: List[Dict[str, Any]],
) -> Dict[str, Any]:
    slug_tpl, title_tpl, angle = topic
    niche = site.get("niche") or "produit"
    year = datetime.now(timezone.utc).year
    slug = slugify(slug_tpl.format(niche=niche, year=year))
    title = title_tpl.format(niche=niche, year=year)

    product_lines = "\n".join(
        f"- {p.get('slug')}: {_ensure_str(p.get('name'))} · "
        f"{p.get('price', 0)}{p.get('currency','EUR')} · "
        f"{_ensure_str((p.get('narrative') or {}).get('subheadline'))}"
        for p in products[:8]
    )

    system = "Tu es un journaliste produit premium, ton éditorial."
    user = (
        f"Rédige un Top List SEO : « {title} ». Angle : {angle}.\n"
        f"Produits du catalogue à classer : \n{product_lines}\n\n"
        "Retourne JSON strict : {\n"
        '"title":"...","meta_description":"160 chars","h1":"...",'
        '"intro":"100 mots","items":[{"rank":1,"product_slug":"...","headline":"...",'
        '"why":"150 mots","pros":["..."],"cons":["..."],"verdict":"80 mots"}],'
        '"conclusion":"150 mots","faq":[{"q":"","a":"80 mots"}],'
        '"seo_keywords":["..."]}'
    )
    try:
        data = await safe_claude_json(
            system, user, quality_tier="standard",
            session_id=f"top-{slug[:30]}",
            timeout=150, request_id=f"top-{slug[:30]}",
        )
    except Exception as e:
        return {"ok": False, "slug": slug, "error": str(e)[:200]}

    doc = {
        "id": str(uuid.uuid4()),
        "site_id": site["id"],
        "kind": "top_list",
        "slug": slug,
        "title": data.get("title"),
        "meta_description": (data.get("meta_description") or "")[:160],
        "h1": data.get("h1"),
        "intro": data.get("intro", ""),
        "items": data.get("items", []),
        "conclusion": data.get("conclusion", ""),
        "faq": data.get("faq", []),
        "seo_keywords": data.get("seo_keywords", []),
        "created_at": _now(), "updated_at": _now(), "published": True,
    }
    await db.landing_pages.update_one(
        {"site_id": site["id"], "slug": slug}, {"$set": doc}, upsert=True,
    )
    return {"ok": True, "slug": slug}


async def generate_all_top_lists(site_id: str) -> Dict[str, Any]:
    site = await db.sites.find_one({"id": site_id}, {"_id": 0})
    if not site:
        return {"ok": False, "error": "site not found"}
    products = await _products_of(site_id)

    async def run_one(t):
        async with _SEM:
            return await generate_top_list(site, t, products)
    results = await asyncio.gather(*[run_one(t) for t in TOP_LIST_TOPICS])
    ok = sum(1 for r in results if r.get("ok"))
    return {"ok": True, "generated": ok, "total": len(TOP_LIST_TOPICS), "details": results}


# ────────────────────────────────────────────────────────────────────────
# 5. MASTER ORCHESTRATOR (called by step 9 in launch pipeline)
# ────────────────────────────────────────────────────────────────────────
async def generate_all_seo_content(site_id: str) -> Dict[str, Any]:
    """Run all 4 generators sequentially. Called by launch step 9."""
    started = _now()
    out = {"site_id": site_id, "started_at": started}

    for name, fn in [
        ("buyer_guides", generate_all_buyer_guides),
        ("glossary", generate_glossary),
        ("comparisons", generate_all_comparisons),
        ("top_lists", generate_all_top_lists),
    ]:
        try:
            out[name] = await fn(site_id)
        except Exception as e:
            logger.exception(f"[seo_content] {name} failed")
            out[name] = {"ok": False, "error": str(e)[:300]}

    out["finished_at"] = _now()
    return out
