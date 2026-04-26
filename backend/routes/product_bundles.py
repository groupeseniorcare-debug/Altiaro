"""
Bundle intelligence — AI analyses the full catalogue of a site and suggests
cross-sell product bundles (3-5 complementary products per anchor).

Stored on product.bundles_with = [product_id, ...] (max 4).

Triggered:
- Bulk : `POST /api/sites/{site_id}/bundles/auto-generate`
- Per product : inferred from shared category + AI refinement
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends

from deps import db, get_current_user

logger = logging.getLogger("conceptfactory.product_bundles")
EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")

router = APIRouter()

_JSON_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```\s*$", re.MULTILINE)


def _strip_json_fence(text: str) -> str:
    return _JSON_FENCE_RE.sub("", (text or "").strip()).strip()


def _pick_text(val, lang: str = "fr") -> str:
    if isinstance(val, dict):
        return val.get(lang) or val.get("fr") or next(iter(val.values()), "") or ""
    return str(val or "")


async def _call_claude_json(system: str, user: str, timeout: int = 90) -> Optional[dict]:
    """Phase 0 — délègue à `safe_claude_json` (retry expo + circuit breaker)."""
    if not EMERGENT_LLM_KEY:
        return None
    from services.llm_resilience import safe_claude_json, LLMUnavailableError
    try:
        return await safe_claude_json(
            system, user,
            session_id=f"bundles-{uuid.uuid4().hex[:8]}",
            timeout=timeout,
        )
    except (LLMUnavailableError, ValueError) as e:
        logger.warning(f"[bundles] LLM call returned None: {e}")
        return None
    except Exception:
        logger.exception("Bundles Claude call failed")
        return None


@router.post("/sites/{site_id}/bundles/auto-generate")
async def auto_generate_bundles(site_id: str, user=Depends(get_current_user)):
    """
    Analyse tout le catalogue du site et propose 2-4 produits cross-sell
    pertinents pour chaque produit. Écrit le résultat dans product.bundles_with.
    """
    site = await db.sites.find_one({"id": site_id}, {"_id": 0, "name": 1, "niche": 1})
    if not site:
        raise HTTPException(404, "Site introuvable")

    products = await db.products.find(
        {"site_id": site_id, "status": "active"},
        {"_id": 0, "id": 1, "name": 1, "category": 1, "tags": 1, "price": 1, "price_eur": 1, "short_description": 1},
    ).to_list(1000)
    if len(products) < 2:
        return {"status": "not_enough_products", "count": len(products)}

    # Build compact catalogue description for the LLM
    items = []
    for p in products:
        name = _pick_text(p.get("name"))
        desc = _pick_text(p.get("short_description"))
        price = p.get("price") or p.get("price_eur") or 0
        items.append({
            "id": p["id"],
            "name": name[:100],
            "category": p.get("category") or "",
            "tags": (p.get("tags") or [])[:6],
            "price": price,
            "desc": desc[:160],
        })

    system = (
        "Tu es un expert merchandising e-commerce spécialisé dans le cross-sell. "
        "Tu renvoies UNIQUEMENT du JSON valide, sans commentaire."
    )
    user = f"""Voici le catalogue complet de la boutique {site.get('name')} (niche : {site.get('niche')}).

{json.dumps(items, ensure_ascii=False, indent=2)}

Pour CHAQUE produit, identifie 2 à 4 autres produits du catalogue qui complètent logiquement l'achat (cross-sell réel, pas au hasard).

Règles :
- Ne propose QUE des IDs présents dans le catalogue ci-dessus.
- Privilégie les accessoires, consommables, produits complémentaires d'usage.
- Si 2 produits sont très similaires (substituts), ne les mets pas en bundle.
- Évite les bundles symétriques inutiles (A→B, B→A systématiquement) : réfléchis à ce qui se vend réellement ensemble.
- Un produit peut ne pas avoir de bundle si rien ne le complète (retourne un tableau vide).

Retourne EXACTEMENT ce JSON :
{{
  "bundles": {{
    "<product_id_1>": ["<id_complement_1>", "<id_complement_2>", ...],
    "<product_id_2>": ["<id_complement_1>", ...]
  }}
}}

Tous les produits doivent apparaître comme clés (avec liste vide si aucun bundle).
Maximum 4 IDs par produit."""

    data = await _call_claude_json(system, user, timeout=120)
    if not data or not isinstance(data, dict):
        return {"status": "llm_failed"}

    bundles = data.get("bundles") or {}
    if not isinstance(bundles, dict):
        return {"status": "llm_failed"}

    valid_ids = {p["id"] for p in items}
    updates = 0
    total_links = 0
    for pid, linked in bundles.items():
        if pid not in valid_ids:
            continue
        cleaned = [x for x in (linked or []) if x in valid_ids and x != pid][:4]
        await db.products.update_one(
            {"id": pid},
            {"$set": {"bundles_with": cleaned, "bundles_generated_at": datetime.now(timezone.utc).isoformat()}},
        )
        updates += 1
        total_links += len(cleaned)

    logger.info(f"[bundles] site {site_id} : {updates} products updated, {total_links} links")
    return {"status": "ok", "products_updated": updates, "total_links": total_links}
