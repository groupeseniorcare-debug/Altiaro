"""TÂCHE 3.1 — Programmatic SEO landing pages (Sprint 5 SEO).

Génère automatiquement des landing pages combinatoires
`/longtail/{produit}-{intent}-{segment}` pour capter le long-tail SEO.

Architecture :
    1. Pour chaque produit du site, génère ~30-50 combinaisons (intent × segment)
    2. Pour chaque combinaison, génère via Claude Haiku :
        - meta_title (60 chars)
        - meta_description (150 chars)
        - h1
        - intro (~80 mots, optimisé featured snippet)
        - 2-3 sections H2 (chacune 150-200 mots)
    3. Persiste dans `landing_pages` collection (kind=longtail)
    4. Le sitemap-prerender les inclut auto

Budget cible (Altea, 9 produits × 30 = 270 landings) ≈ 0,5-1 € en Claude Haiku.
"""
from __future__ import annotations

import asyncio
import logging
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from deps import db
from services.slugify import slugify

logger = logging.getLogger("altiaro.programmatic_seo")

# ─────────────────────────────────────────────────────────────────────
# Intent / Segment taxonomy par niche
# ─────────────────────────────────────────────────────────────────────

# Format : niche_keyword → {intents: [...], segments: [...]}
NICHE_TAXONOMY: Dict[str, Dict[str, List[str]]] = {
    "fauteuil releveur": {
        "intents": [
            "prix-tarif",
            "remboursement-cpam",
            "remboursement-mutuelle",
            "comparatif-2026",
            "avis-test",
            "garantie",
            "electrique-vs-manuel",
            "comment-choisir",
            "installation-domicile",
            "entretien",
        ],
        "segments": [
            "pour-personne-agee-80-ans",
            "pour-personne-agee-90-ans",
            "pour-arthrose",
            "pour-mobilite-reduite",
            "pour-petit-budget",
            "pour-grande-taille",
            "pour-petite-taille",
            "pour-ehpad",
            "pour-domicile",
            "pour-aidants",
        ],
    },
    "default": {
        "intents": [
            "prix-tarif",
            "comment-choisir",
            "comparatif-2026",
            "avis-test",
            "garantie",
            "guide-achat",
        ],
        "segments": [
            "pour-debutant",
            "pour-expert",
            "pour-petit-budget",
            "pour-cadeau",
            "pour-domicile",
            "pour-professionnel",
        ],
    },
}


def _pick_taxonomy(niche: str) -> Dict[str, List[str]]:
    n = (niche or "").lower()
    for key, tax in NICHE_TAXONOMY.items():
        if key != "default" and key in n:
            return tax
    return NICHE_TAXONOMY["default"]


def _humanize(slug: str) -> str:
    """'pour-personne-agee-90-ans' → 'pour personne âgée 90 ans'"""
    return slug.replace("-", " ").replace("agee", "âgée").replace("eme", "ème")


# ─────────────────────────────────────────────────────────────────────
# LLM generation (Claude Haiku via Emergent)
# ─────────────────────────────────────────────────────────────────────

_LLM_PROMPT_FR = """Tu es un rédacteur SEO expert. Génère une landing page courte mais riche pour la requête longue-traîne suivante :

Produit : {product_name}
Intent : {intent_human}
Segment client : {segment_human}
Niche : {niche}
Marque : {brand}

Format de sortie EN JSON STRICT (pas de markdown, pas d'explication) :
{{
  "meta_title": "string max 65 chars, accrocheur, contient l'intent",
  "meta_description": "string max 155 chars, donne envie de cliquer, mentionne le segment",
  "h1": "string max 70 chars, naturel, optimisé featured snippet",
  "intro_snippet": "réponse directe de 40-60 mots, structure pour featured snippet, commence par une affirmation forte",
  "sections": [
    {{ "h2": "string", "body_md": "string 150-200 mots en markdown léger" }},
    {{ "h2": "string", "body_md": "string 150-200 mots en markdown léger" }},
    {{ "h2": "string", "body_md": "string 150-200 mots en markdown léger" }}
  ],
  "faq": [
    {{ "q": "question", "a": "réponse 30-50 mots" }},
    {{ "q": "question", "a": "réponse 30-50 mots" }}
  ]
}}

Règles :
- Ton professionnel, factuel, rassurant.
- Mentionne le produit dès l'intro et dans au moins 1 H2.
- Inclus 2-3 mots-clés sémantiquement liés à l'intent.
- Ne mens pas sur les caractéristiques (reste générique si pas d'info).
- Ne mentionne aucune marque concurrente.
- Évite les phrases creuses ("Notre produit est génial").
- Markdown : juste **gras** et listes - pour ne pas polluer.
"""


async def _generate_landing_content(
    *, product_name: str, intent_human: str, segment_human: str,
    niche: str, brand: str,
    timeout_s: float = 50.0,
) -> Optional[Dict[str, Any]]:
    """Appelle Claude Haiku via emergentintegrations pour générer le contenu."""
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
    except Exception as e:
        logger.warning(f"emergentintegrations not available: {e}")
        return None

    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        logger.warning("EMERGENT_LLM_KEY missing — skip LLM gen")
        return None

    prompt = _LLM_PROMPT_FR.format(
        product_name=product_name,
        intent_human=intent_human,
        segment_human=segment_human,
        niche=niche,
        brand=brand,
    )

    try:
        chat = LlmChat(
            api_key=api_key,
            session_id=f"prog_seo_{slugify(product_name)}_{slugify(intent_human)[:20]}",
            system_message="Tu es un rédacteur SEO senior. Réponds UNIQUEMENT en JSON valide, sans markdown wrapping.",
        ).with_model("anthropic", "claude-haiku-4-5-20251001")

        msg = UserMessage(text=prompt)
        resp = await asyncio.wait_for(chat.send_message(msg), timeout=timeout_s)
        if not resp:
            return None
        # Extract JSON from response
        text = resp.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```\s*$", "", text)
        import json as _json
        data = _json.loads(text)
        # Sanity validate keys
        if not data.get("h1") or not data.get("intro_snippet"):
            return None
        return data
    except asyncio.TimeoutError:
        logger.warning(f"LLM timeout for {product_name} / {intent_human}")
        return None
    except Exception as e:
        logger.warning(f"LLM error for {product_name} / {intent_human}: {str(e)[:160]}")
        return None


# ─────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────


def _build_combinations(
    products: List[Dict[str, Any]],
    taxonomy: Dict[str, List[str]],
    *,
    max_per_product: int = 30,
) -> List[Tuple[Dict[str, Any], str, str]]:
    """Génère la liste (product, intent, segment) à processer.

    On limite à `max_per_product` pour cap budget. On prend des combinaisons
    distribuées (round-robin segments × intents).
    """
    out: List[Tuple[Dict[str, Any], str, str]] = []
    intents = taxonomy["intents"]
    segments = taxonomy["segments"]
    for p in products:
        local: List[Tuple[Dict[str, Any], str, str]] = []
        for i_idx, intent in enumerate(intents):
            for s_idx, segment in enumerate(segments):
                local.append((p, intent, segment))
        # Cap to max_per_product (deterministic stride to keep diversity)
        if len(local) > max_per_product:
            stride = max(1, len(local) // max_per_product)
            local = local[::stride][:max_per_product]
        out.extend(local)
    return out


async def generate_programmatic_landings_for_site(
    site_id: str,
    *,
    max_per_product: int = 30,
    concurrency: int = 4,
    skip_if_exists: bool = True,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Génère et persiste des landing pages programmatic pour un site.

    Parameters
    ----------
    site_id : str
    max_per_product : int
        Cap nombre de landings par produit (default 30).
    concurrency : int
        Nombre d'appels LLM en parallèle (default 4).
    skip_if_exists : bool
        Si True, skip la génération pour les slugs déjà présents.
    dry_run : bool
        Si True, calcule les combinaisons sans appeler le LLM.
    """
    site = await db.sites.find_one({"id": site_id}, {"_id": 0})
    if not site:
        return {"ok": False, "reason": "site_not_found"}

    niche = site.get("niche") or ""
    brand = ((site.get("design") or {}).get("brand") or {}).get("name") or site.get("name", "")
    lang = (site.get("default_locale") or site.get("default_language") or "fr").split("-")[0]

    products = await db.products.find(
        {"site_id": site_id, "status": "active"},
        {"_id": 0, "id": 1, "slug": 1, "name": 1, "price": 1},
    ).to_list(2000)

    taxonomy = _pick_taxonomy(niche)
    combos = _build_combinations(products, taxonomy, max_per_product=max_per_product)
    logger.info(f"[prog_seo] site={site_id[:8]} combinations={len(combos)}")

    if dry_run:
        return {
            "ok": True, "dry_run": True, "combinations": len(combos),
            "products": len(products), "intents": len(taxonomy["intents"]),
            "segments": len(taxonomy["segments"]),
        }

    sem = asyncio.Semaphore(concurrency)
    created = 0
    skipped = 0
    failed = 0

    async def _process(p, intent, segment):
        nonlocal created, skipped, failed
        async with sem:
            product_name_str = p.get("name") or ""
            if isinstance(product_name_str, dict):
                product_name_str = (product_name_str.get(lang)
                                     or product_name_str.get("fr")
                                     or product_name_str.get("en") or "")
            base_slug = slugify(f"{product_name_str}-{intent}-{segment}")[:120]
            if not base_slug:
                failed += 1
                return

            if skip_if_exists:
                existing = await db.landing_pages.find_one(
                    {"site_id": site_id, "slug": base_slug, "kind": "longtail"},
                    {"_id": 0, "id": 1},
                )
                if existing:
                    skipped += 1
                    return

            content = await _generate_landing_content(
                product_name=product_name_str,
                intent_human=_humanize(intent),
                segment_human=_humanize(segment),
                niche=niche,
                brand=brand,
            )
            if not content:
                failed += 1
                return

            now = datetime.now(timezone.utc).isoformat()
            doc = {
                "id": f"lt_{base_slug[:80]}",
                "site_id": site_id,
                "kind": "longtail",
                "slug": base_slug,
                "lang": lang,
                "product_id": p.get("id"),
                "product_slug": p.get("slug"),
                "intent": intent,
                "segment": segment,
                "title": content.get("meta_title") or content.get("h1"),
                "meta_title": content.get("meta_title"),
                "meta_description": content.get("meta_description"),
                "h1": content.get("h1"),
                "intro": content.get("intro_snippet"),
                "intro_snippet": content.get("intro_snippet"),
                "sections": content.get("sections") or [],
                "faq": content.get("faq") or [],
                "tags": [intent, segment, niche],
                "source": "programmatic_seo_v1",
                "published": True,
                "status": "published",
                "created_at": now,
                "updated_at": now,
            }
            await db.landing_pages.update_one(
                {"site_id": site_id, "slug": base_slug, "kind": "longtail"},
                {"$set": doc},
                upsert=True,
            )
            created += 1

    tasks = [_process(p, intent, seg) for p, intent, seg in combos]
    await asyncio.gather(*tasks, return_exceptions=True)

    return {
        "ok": True,
        "site_id": site_id,
        "products": len(products),
        "combinations_total": len(combos),
        "created": created,
        "skipped_existing": skipped,
        "failed": failed,
        "intents_used": taxonomy["intents"],
        "segments_used": taxonomy["segments"],
    }
