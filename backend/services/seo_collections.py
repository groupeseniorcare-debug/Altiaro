"""TÂCHE 3.4 — Enrichissement SEO des pages catégorie / collection.

Pour chaque collection existante, génère via Claude Haiku :
    - intro (200-300 mots, optimisée featured snippet)
    - 3-4 sections H2 (200 mots chacune)
    - FAQ (5 Q/R catégorie-spécifiques)
    - meta_title / meta_description SEO

Persisté dans `collections.seo_content = {intro, sections, faq, meta_title, meta_description, ...}`.

Bonus : crée des collections **dérivées segmentées** (ex: fauteuils-releveurs-pour-personnes-agees-90-ans)
en sélectionnant un sous-ensemble pertinent de produits.
"""
from __future__ import annotations

import asyncio
import logging
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from deps import db
from services.slugify import slugify

logger = logging.getLogger("altiaro.seo_collections")

_LLM_PROMPT = """Tu rédiges du contenu SEO pour une page catégorie e-commerce premium.

Catégorie : {category_name}
Niche : {niche}
Marque : {brand}
Audience cible : {audience}
Nb produits dans cette catégorie : {n_products}

Format de sortie EN JSON STRICT (pas de markdown wrapper) :
{{
  "meta_title": "max 65 chars, contient le mot-clé principal",
  "meta_description": "max 155 chars, donne envie de cliquer",
  "h1": "titre H1 max 70 chars, naturel",
  "intro": "200-300 mots en markdown léger. Premier paragraphe = 40-60 mots optimisé featured snippet (réponse directe à la question 'que cherche l'utilisateur ?'). Suite = présentation des avantages, critères de choix.",
  "sections": [
    {{ "h2": "Comment choisir le bon ...", "body_md": "200 mots markdown, 1er para = featured snippet 40-60 mots" }},
    {{ "h2": "Pour qui sont conçus les ...", "body_md": "200 mots markdown" }},
    {{ "h2": "Que regarder avant d'acheter ?", "body_md": "200 mots markdown avec liste critères" }}
  ],
  "faq": [
    {{ "q": "...", "a": "30-50 mots" }},
    {{ "q": "...", "a": "30-50 mots" }},
    {{ "q": "...", "a": "30-50 mots" }},
    {{ "q": "...", "a": "30-50 mots" }},
    {{ "q": "...", "a": "30-50 mots" }}
  ]
}}

Règles :
- Ton expert et factuel, ni techno-jargon ni marketing-bullshit.
- Aucune marque concurrente.
- Pas de prix précis (les prix bougent).
- Markdown : juste **gras** et listes - .
- Pas de répétition entre intro et sections.
"""


async def _generate_collection_seo(
    *, category_name: str, niche: str, brand: str,
    audience: str = "consommateurs avertis", n_products: int = 0,
    timeout_s: float = 60.0,
) -> Optional[Dict[str, Any]]:
    """Appelle Claude Haiku pour générer le contenu SEO d'une catégorie."""
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
    except Exception:
        return None
    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        return None
    prompt = _LLM_PROMPT.format(
        category_name=category_name, niche=niche, brand=brand,
        audience=audience, n_products=n_products,
    )
    try:
        chat = LlmChat(
            api_key=api_key,
            session_id=f"col_seo_{slugify(category_name)[:30]}",
            system_message="Tu es rédacteur SEO catégorie e-commerce. Réponds UNIQUEMENT en JSON valide.",
        ).with_model("anthropic", "claude-haiku-4-5-20251001")
        resp = await asyncio.wait_for(
            chat.send_message(UserMessage(text=prompt)), timeout=timeout_s,
        )
        if not resp:
            return None
        text = resp.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```\s*$", "", text)
        import json as _json
        data = _json.loads(text)
        if not data.get("intro") or not data.get("h1"):
            return None
        return data
    except Exception as e:
        logger.warning(f"[seo_col] LLM failed for '{category_name}': {str(e)[:140]}")
        return None


# Segments dérivés par niche (pour générer des collections SEO segmentées)
DERIVED_SEGMENTS: Dict[str, List[Dict[str, str]]] = {
    "fauteuil releveur": [
        {"slug_suffix": "pour-personnes-agees-90-ans",
         "label": "pour personnes âgées de 90 ans et plus",
         "audience": "personnes âgées de 90 ans et plus, leur famille et aidants"},
        {"slug_suffix": "remboursable-cpam",
         "label": "remboursables CPAM",
         "audience": "patients ALD avec prescription médicale"},
        {"slug_suffix": "pour-arthrose-et-douleurs-articulaires",
         "label": "pour arthrose et douleurs articulaires",
         "audience": "personnes souffrant d'arthrose, polyarthrite ou douleurs lombaires"},
        {"slug_suffix": "pour-personnes-de-grande-taille",
         "label": "pour personnes de grande taille",
         "audience": "utilisateurs mesurant 1m80 et plus"},
        {"slug_suffix": "pour-petit-budget",
         "label": "pour petit budget",
         "audience": "acheteurs sensibles au prix recherchant le meilleur rapport qualité-prix"},
    ],
    "default": [
        {"slug_suffix": "pour-debutant",
         "label": "pour débutant",
         "audience": "personnes découvrant la catégorie"},
        {"slug_suffix": "pour-cadeau",
         "label": "à offrir en cadeau",
         "audience": "acheteurs cherchant un cadeau pour un proche"},
        {"slug_suffix": "pour-petit-budget",
         "label": "pour petit budget",
         "audience": "acheteurs sensibles au prix"},
    ],
}


def _pick_segments(niche: str) -> List[Dict[str, str]]:
    n = (niche or "").lower()
    for key, segs in DERIVED_SEGMENTS.items():
        if key != "default" and key in n:
            return segs
    return DERIVED_SEGMENTS["default"]


async def enrich_collections_seo(
    site_id: str,
    *, generate_derived: bool = True,
    concurrency: int = 2,
) -> Dict[str, Any]:
    """Enrichit les collections existantes + génère les collections dérivées.

    Returns
    -------
        Dict avec stats {enriched, derived_created, ...}
    """
    site = await db.sites.find_one({"id": site_id}, {"_id": 0})
    if not site:
        return {"ok": False, "reason": "site_not_found"}
    niche = site.get("niche") or ""
    brand = ((site.get("design") or {}).get("brand") or {}).get("name") or site.get("name", "")
    lang = (site.get("default_locale") or site.get("default_language") or "fr").split("-")[0]

    # 1) Enrichir les collections existantes
    existing_cols = await db.collections.find(
        {"site_id": site_id}, {"_id": 0},
    ).to_list(100)

    sem = asyncio.Semaphore(concurrency)
    enriched = 0
    derived_created = 0

    async def _enrich(col):
        nonlocal enriched
        async with sem:
            name = col.get("name")
            if isinstance(name, dict):
                name = name.get(lang) or name.get("fr") or next(iter(name.values()), "")
            name = str(name or col.get("slug") or "Catégorie")
            n_prods = len(col.get("product_ids") or [])
            if col.get("seo_content"):
                return  # already done
            content = await _generate_collection_seo(
                category_name=name, niche=niche, brand=brand,
                audience="grand public", n_products=n_prods,
            )
            if content:
                await db.collections.update_one(
                    {"id": col["id"]} if col.get("id") else {"site_id": site_id, "slug": col["slug"]},
                    {"$set": {"seo_content": content,
                              "seo_content_generated_at": datetime.now(timezone.utc).isoformat()}},
                )
                enriched += 1

    await asyncio.gather(*[_enrich(c) for c in existing_cols], return_exceptions=True)

    # 2) Créer les collections dérivées
    if generate_derived and existing_cols:
        segments = _pick_segments(niche)
        derived_tasks = []

        async def _create_derived(parent_col, seg):
            nonlocal derived_created
            async with sem:
                parent_slug = parent_col.get("slug") or ""
                if not parent_slug:
                    return
                derived_slug = f"{parent_slug}-{seg['slug_suffix']}"[:120]
                existing = await db.collections.find_one(
                    {"site_id": site_id, "slug": derived_slug}, {"_id": 0, "id": 1},
                )
                if existing:
                    return
                parent_name = parent_col.get("name")
                if isinstance(parent_name, dict):
                    parent_name = parent_name.get(lang) or parent_name.get("fr") or "Catégorie"
                derived_name = f"{parent_name} {seg['label']}"
                content = await _generate_collection_seo(
                    category_name=derived_name, niche=niche, brand=brand,
                    audience=seg["audience"],
                    n_products=len(parent_col.get("product_ids") or []),
                )
                if not content:
                    return
                doc = {
                    "id": f"col_{derived_slug[:80]}",
                    "site_id": site_id,
                    "slug": derived_slug,
                    "name": {lang: derived_name},
                    "title": derived_name,
                    "description": content.get("meta_description", ""),
                    "parent_collection_id": parent_col.get("id"),
                    "parent_collection_slug": parent_slug,
                    "segment": seg["slug_suffix"],
                    "product_ids": parent_col.get("product_ids") or [],
                    "seo_content": content,
                    "source": "seo_derived_v1",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
                await db.collections.update_one(
                    {"site_id": site_id, "slug": derived_slug},
                    {"$set": doc}, upsert=True,
                )
                derived_created += 1

        for parent in existing_cols:
            for seg in segments:
                derived_tasks.append(_create_derived(parent, seg))
        await asyncio.gather(*derived_tasks, return_exceptions=True)

    return {
        "ok": True,
        "site_id": site_id,
        "existing_collections": len(existing_cols),
        "enriched_with_seo": enriched,
        "derived_created": derived_created,
    }
