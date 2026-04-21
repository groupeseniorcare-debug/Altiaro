"""
Product narrative enrichment — AI hook that auto-generates premium
storytelling, tech specs and FAQ for each product.

Triggered :
- Automatically after product import (hook #16)
- Manually via `POST /api/products/{id}/enrich-narrative`
- Bulk via `POST /api/sites/{site_id}/products/enrich-narratives`

Stored on product.narrative = { headline, subheadline, sections[], tech_specs[], faq[] }
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
from pydantic import BaseModel

from deps import db, get_current_user

logger = logging.getLogger("conceptfactory.product_narrative")
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
    if not EMERGENT_LLM_KEY:
        logger.warning("No EMERGENT_LLM_KEY — narrative enrichment skipped")
        return None
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        chat = (
            LlmChat(
                api_key=EMERGENT_LLM_KEY,
                session_id=f"narrative-{uuid.uuid4().hex[:8]}",
                system_message=system,
            )
            .with_model("anthropic", "claude-sonnet-4-5-20250929")
        )
        raw = await asyncio.wait_for(chat.send_message(UserMessage(text=user)), timeout=timeout)
        text = raw if isinstance(raw, str) else str(raw)
        return json.loads(_strip_json_fence(text))
    except (asyncio.TimeoutError, json.JSONDecodeError) as e:
        logger.error(f"Narrative Claude call failed: {e}")
        return None
    except Exception:
        logger.exception("Narrative Claude unexpected error")
        return None


async def enrich_product_narrative(product_id: str, force: bool = False) -> dict:
    """
    Generate narrative, tech_specs and FAQ for a product.
    Returns { status, product_id, narrative? }.
    """
    product = await db.products.find_one({"id": product_id}, {"_id": 0})
    if not product:
        return {"status": "not_found", "product_id": product_id}
    if product.get("narrative") and not force:
        return {"status": "skipped_already_enriched", "product_id": product_id}

    site = await db.sites.find_one({"id": product.get("site_id")}, {"_id": 0, "name": 1, "niche": 1, "design": 1})
    niche = (site or {}).get("niche") or ""
    brand_name = (site or {}).get("name") or ""
    brand_tagline = _pick_text(((site or {}).get("design") or {}).get("brand", {}).get("tagline"))

    name = _pick_text(product.get("name"))
    desc = _pick_text(product.get("description") or product.get("short_description"))
    price = product.get("price_eur") or product.get("price") or 0
    category = product.get("category") or ""
    tags = product.get("tags") or []

    system = (
        "Tu es un rédacteur expert en copywriting e-commerce pour le marché senior français. "
        "Tu produis un narratif PREMIUM, empathique, jamais infantilisant, qui rassure autant qu'il séduit. "
        "Tu renvoies UNIQUEMENT du JSON valide, strict, sans commentaire ni markdown."
    )

    user = f"""Tu vas enrichir la fiche produit avec un narratif premium.

=== MARQUE ===
- Nom : {brand_name}
- Niche : {niche}
- Tagline : {brand_tagline}

=== PRODUIT ===
- Nom : {name}
- Catégorie : {category}
- Tags : {", ".join(tags) if tags else "—"}
- Prix TTC : {price} €
- Description brute : {desc[:1500]}

=== CONSIGNES ===
Génère un narratif qui convertit. Public : seniors (60-90 ans) et leurs aidants.
Ton : élégant, rassurant, concret. Pas de superlatifs vides. Jamais de "nos chers seniors".
Bénéfices ancrés dans le quotidien réel (se lever, dormir, marcher, recevoir).

Retourne EXACTEMENT ce JSON :
{{
  "headline": "Titre commercial court et puissant (max 70 caractères) — peut reformuler le nom produit",
  "subheadline": "Sous-titre descriptif qui pose le bénéfice principal (max 140 caractères)",
  "sections": [
    {{
      "title": "Titre accrocheur de la section (max 55 caractères)",
      "body": "Paragraphe narratif 2-4 phrases, 60-100 mots, qui raconte un usage concret.",
      "bullet_points": [
        "Preuve tangible 1 (bénéfice concret, chiffré si possible, max 85 caractères)",
        "Preuve tangible 2 (max 85 caractères)",
        "Preuve tangible 3 (max 85 caractères)"
      ]
    }},
    {{
      "title": "2e section — angle différent (matière, fabrication, service, accompagnement)",
      "body": "Paragraphe narratif 2-4 phrases, 60-100 mots.",
      "bullet_points": [
        "Preuve 1",
        "Preuve 2",
        "Preuve 3"
      ]
    }},
    {{
      "title": "3e section — pourquoi nous, comparaison, service",
      "body": "Paragraphe narratif 2-4 phrases.",
      "bullet_points": [
        "Preuve 1",
        "Preuve 2",
        "Preuve 3"
      ]
    }}
  ],
  "tech_specs": [
    {{"label": "Dimensions", "value": "xx × xx × xx cm"}},
    {{"label": "Poids", "value": "x kg"}},
    {{"label": "Matériau principal", "value": "..."}},
    {{"label": "Charge maximale supportée", "value": "... kg"}},
    {{"label": "Alimentation / utilisation", "value": "..."}},
    {{"label": "Entretien", "value": "..."}},
    {{"label": "Garantie", "value": "2 ans pièces et main d'œuvre"}},
    {{"label": "Normes", "value": "CE, conforme UE"}}
  ],
  "faq": [
    {{
      "question": "Question très fréquente avant l'achat (livraison, installation, compatibilité…)",
      "answer": "Réponse franche 2-4 phrases qui lève l'objection."
    }},
    {{"question": "2e question (usage au quotidien, ergonomie, confort)",
      "answer": "Réponse 2-4 phrases."}},
    {{"question": "3e question (remboursement mutuelle / Sécu / LPPR si pertinent)",
      "answer": "Réponse 2-4 phrases."}},
    {{"question": "4e question (garantie, SAV, durée de vie)",
      "answer": "Réponse 2-4 phrases."}},
    {{"question": "5e question (retour, remboursement si insatisfaction)",
      "answer": "Réponse 2-4 phrases."}}
  ]
}}

Règles dures :
- Caractéristiques techniques PLAUSIBLES pour ce type de produit (pas d'hallucination grossière).
- Si un champ tech_spec ne s'applique pas au produit, remplace-le par un champ pertinent (Capacité, Angle d'ouverture, Autonomie batterie, etc).
- Toutes les FAQ doivent être orientées "objection client", pas du remplissage.
- Français naturel, pas de jargon médical lourd."""

    data = await _call_claude_json(system, user)
    if not data or not isinstance(data, dict):
        return {"status": "llm_failed", "product_id": product_id}

    narrative = {
        "headline": str(data.get("headline") or "")[:120],
        "subheadline": str(data.get("subheadline") or "")[:200],
        "sections": [
            {
                "title": str(s.get("title") or "")[:80],
                "body": str(s.get("body") or "")[:800],
                "bullet_points": [str(b)[:120] for b in (s.get("bullet_points") or []) if b][:5],
            }
            for s in (data.get("sections") or []) if isinstance(s, dict)
        ][:3],
        "tech_specs": [
            {"label": str(t.get("label") or "")[:50], "value": str(t.get("value") or "")[:120]}
            for t in (data.get("tech_specs") or []) if isinstance(t, dict) and t.get("label")
        ][:10],
        "faq": [
            {"question": str(f.get("question") or "")[:180], "answer": str(f.get("answer") or "")[:600]}
            for f in (data.get("faq") or []) if isinstance(f, dict) and f.get("question")
        ][:6],
        "enriched_at": datetime.now(timezone.utc).isoformat(),
        "enriched_model": "claude-sonnet-4-5-20250929",
    }

    await db.products.update_one(
        {"id": product_id},
        {"$set": {"narrative": narrative, "updated_at": datetime.now(timezone.utc).isoformat()}},
    )
    logger.info(f"[narrative] enriched product {product_id} ({len(narrative['sections'])} sections, {len(narrative['faq'])} FAQ)")

    # Fire-and-forget IndexNow to re-index the enriched product URL
    try:
        from routes.indexnow import fire_and_forget_indexnow
        origin = os.environ.get("PUBLIC_ORIGIN") or "https://senior-france.preview.emergentagent.com"
        url = f"{origin}/shop/{product.get('site_id')}/product/{product_id}"
        fire_and_forget_indexnow([url])
    except Exception:
        logger.exception("[narrative→indexnow] dispatch failed")

    return {"status": "ok", "product_id": product_id, "narrative": narrative}


# =====================================================================
# ROUTES
# =====================================================================
class EnrichBulkInput(BaseModel):
    force: bool = False
    limit: int = 50


@router.post("/products/{product_id}/enrich-narrative")
async def enrich_one(product_id: str, force: bool = False, user=Depends(get_current_user)):
    result = await enrich_product_narrative(product_id, force=force)
    if result.get("status") == "not_found":
        raise HTTPException(404, "Produit introuvable")
    if result.get("status") == "llm_failed":
        raise HTTPException(502, "Échec de l'enrichissement IA (budget ou timeout). Réessayez.")
    return result


@router.post("/sites/{site_id}/products/enrich-narratives")
async def enrich_bulk(site_id: str, body: EnrichBulkInput, user=Depends(get_current_user)):
    """Bulk enrichment : parcourt tous les produits du site sans narrative et les enrichit."""
    q = {"site_id": site_id}
    if not body.force:
        q["narrative"] = {"$exists": False}
    products = await db.products.find(q, {"_id": 0, "id": 1}).limit(body.limit).to_list(body.limit)
    # Sequential to respect API limits
    results = []
    for p in products:
        r = await enrich_product_narrative(p["id"], force=body.force)
        results.append(r)
    ok = sum(1 for r in results if r.get("status") == "ok")
    return {"total": len(results), "enriched": ok, "results": results}
