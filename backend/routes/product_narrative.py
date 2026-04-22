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


async def _call_claude_json(system: str, user: str, timeout: int = 90) -> tuple[Optional[dict], Optional[str]]:
    """Returns (result, error_code).
    error_code values: 'no_key' | 'budget_exceeded' | 'timeout' | 'invalid_json' | 'upstream' | None (success)"""
    if not EMERGENT_LLM_KEY:
        logger.warning("No EMERGENT_LLM_KEY — narrative enrichment skipped")
        return None, "no_key"
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
        try:
            return json.loads(_strip_json_fence(text)), None
        except json.JSONDecodeError:
            logger.error(f"Narrative Claude returned invalid JSON: {text[:300]}")
            return None, "invalid_json"
    except asyncio.TimeoutError:
        return None, "timeout"
    except Exception as e:
        msg = str(e)
        if "Budget has been exceeded" in msg or ("budget" in msg.lower() and "exceeded" in msg.lower()):
            logger.warning("Narrative Claude: LLM budget exhausted")
            # Record a platform-level health flag for the UI banner
            try:
                await db.platform_health.update_one(
                    {"key": "llm"},
                    {"$set": {"key": "llm", "status": "budget_exhausted",
                              "last_error_at": datetime.now(timezone.utc).isoformat()}},
                    upsert=True,
                )
            except Exception:
                pass
            return None, "budget_exceeded"
        logger.exception("Narrative Claude unexpected error")
        return None, "upstream"


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
        "Tu es à la fois : (1) un rédacteur e-commerce premium pour le marché senior français, "
        "et (2) un consultant SEO/AEO de niveau expert (top 1% mondial) qui maîtrise "
        "les schémas structurés Google, les requêtes long-tail, People Also Ask, E-E-A-T, "
        "et l'optimisation pour les moteurs de réponse IA (ChatGPT/Perplexity/Claude). "
        "Tu produis un contenu qui ranke #1 en organique ET qui est cité par les IA. "
        "Tu renvoies UNIQUEMENT du JSON valide, strict, sans commentaire ni markdown."
    )

    user = f"""Tu enrichis une fiche produit avec un narratif + un package SEO/AEO ultra-pertinent.

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

=== MISSION ===
Le but est que CE produit soit trouvé organiquement sur Google ET cité par les IA de recherche.
Cela signifie : long-tail keywords réels, contenu factuel, structure schema.org parfaite,
réponses précises aux intents de recherche (comment, pourquoi, pour qui, prix, comparaison).

Public : seniors (60-90 ans) et aidants. Ton élégant, rassurant, jamais infantilisant.

Retourne EXACTEMENT ce JSON :
{{
  "headline": "Titre commercial court et puissant (max 70 caractères) — inclut le mot-clé principal",
  "subheadline": "Sous-titre descriptif qui pose le bénéfice principal (max 140 caractères)",
  "sections": [
    {{"title": "Titre section 1 (max 55 caractères, usage concret)",
     "body": "2-4 phrases, 60-100 mots, storytelling concret.",
     "bullet_points": ["Preuve 1 max 85 caractères", "Preuve 2", "Preuve 3"]}},
    {{"title": "Titre section 2 (matière/fabrication/service)",
     "body": "60-100 mots",
     "bullet_points": ["Preuve 1", "Preuve 2", "Preuve 3"]}},
    {{"title": "Titre section 3 (pourquoi nous / comparaison)",
     "body": "60-100 mots",
     "bullet_points": ["Preuve 1", "Preuve 2", "Preuve 3"]}}
  ],
  "tech_specs": [
    {{"label": "Dimensions", "value": "valeur plausible"}},
    {{"label": "Poids", "value": "..."}},
    {{"label": "Matériau principal", "value": "..."}},
    {{"label": "Charge maximale", "value": "..."}},
    {{"label": "Alimentation / utilisation", "value": "..."}},
    {{"label": "Entretien", "value": "..."}},
    {{"label": "Garantie", "value": "2 ans pièces et main d'œuvre"}},
    {{"label": "Normes", "value": "CE, conforme UE"}}
  ],
  "faq": [
    {{"question": "Q livraison/installation", "answer": "Réponse 2-4 phrases"}},
    {{"question": "Q usage quotidien", "answer": "Réponse 2-4 phrases"}},
    {{"question": "Q remboursement (LPPR/mutuelle/Sécu si pertinent)", "answer": "Réponse 2-4 phrases"}},
    {{"question": "Q garantie/SAV/durée de vie", "answer": "Réponse 2-4 phrases"}},
    {{"question": "Q rétractation/retour", "answer": "Réponse 2-4 phrases"}}
  ],
  "seo": {{
    "title": "Meta title 55-60 caractères, inclut le keyword principal + 1 bénéfice + marque. Ex: 'Fauteuil releveur 2 moteurs — Livré installé · Sereniva'",
    "description": "Meta description 140-158 caractères, inclut keyword + prix + USP + CTA implicite. Ex: 'Fauteuil releveur électrique 2 moteurs. Livré et installé en 72h, garantie 2 ans, essai 14 jours. À partir de 899€ TTC.'",
    "slug": "slug-url-kebab-case-avec-keyword-principal-SEO-friendly-max-60-chars",
    "keywords": ["keyword principal", "variation 1", "variation 2", "variation longue-traîne 1", "variation longue-traîne 2"],
    "people_also_ask": [
      {{"question": "Question que les utilisateurs tapent vraiment sur Google (long-tail, factuelle). Ex: 'Quel est le meilleur fauteuil releveur à 2 moteurs ?'",
        "answer": "Réponse factuelle 3-6 phrases, positionne ce produit comme meilleur choix SANS sur-vente. Cite des chiffres, des normes, des faits concrets."}},
      {{"question": "2e PAA (comparaison/prix/prise en charge)",
        "answer": "3-6 phrases factuelles"}},
      {{"question": "3e PAA (pour qui/quand/comment choisir)",
        "answer": "3-6 phrases factuelles"}},
      {{"question": "4e PAA (spécifique au produit)",
        "answer": "3-6 phrases factuelles"}}
    ],
    "best_for": [
      "Profil utilisateur type 1 (ex: 'Personnes de +70 ans avec arthrose des genoux')",
      "Profil 2",
      "Profil 3"
    ],
    "not_for": [
      "Profil 1 pour qui ce produit N'est PAS adapté (honnêteté = E-E-A-T)",
      "Profil 2"
    ],
    "usage_steps": [
      {{"name": "Étape 1 (installation/prise en main)", "text": "Description concrète 1-2 phrases"}},
      {{"name": "Étape 2", "text": "..."}},
      {{"name": "Étape 3", "text": "..."}},
      {{"name": "Étape 4 (entretien/sécurité)", "text": "..."}}
    ],
    "related_queries": [
      "Recherche connexe 1 (ex: 'fauteuil releveur remboursement sécurité sociale')",
      "Recherche connexe 2",
      "Recherche connexe 3",
      "Recherche connexe 4",
      "Recherche connexe 5",
      "Recherche connexe 6"
    ]
  }}
}}

RÈGLES DURES :
- Caractéristiques techniques plausibles (pas d'hallucination).
- PAA : vraies questions long-tail, pas du remplissage.
- best_for/not_for : honnêteté absolue (un produit qui admet ses limites vend 2× mieux).
- usage_steps : actions concrètes, pas du marketing.
- slug : kebab-case pur, ASCII uniquement, max 60 caractères, inclut le keyword principal.
- keywords : variations françaises réelles (regarde Google Suggest mentalement).
- related_queries : mélange info (comment, pourquoi) + commercial (prix, meilleur, comparatif).
- Jamais de "nos chers seniors" ni "personnes âgées" (dire "seniors").
- Français naturel, niveau Le Monde / Figaro."""

    data, err = await _call_claude_json(system, user)
    if err == "budget_exceeded":
        return {"status": "llm_budget_exceeded", "product_id": product_id}
    if not data or not isinstance(data, dict):
        return {"status": "llm_failed", "product_id": product_id, "error_code": err}

    seo_data = data.get("seo") or {}
    seo = {
        "title": str(seo_data.get("title") or "")[:200],
        "description": str(seo_data.get("description") or "")[:300],
        "slug": re.sub(r"[^a-z0-9-]", "", str(seo_data.get("slug") or "").lower().replace(" ", "-"))[:80],
        "keywords": [str(k)[:60] for k in (seo_data.get("keywords") or []) if k][:10],
        "people_also_ask": [
            {"question": str(p.get("question") or "")[:200], "answer": str(p.get("answer") or "")[:700]}
            for p in (seo_data.get("people_also_ask") or []) if isinstance(p, dict) and p.get("question")
        ][:6],
        "best_for": [str(b)[:150] for b in (seo_data.get("best_for") or []) if b][:5],
        "not_for": [str(b)[:150] for b in (seo_data.get("not_for") or []) if b][:5],
        "usage_steps": [
            {"name": str(s.get("name") or "")[:100], "text": str(s.get("text") or "")[:400]}
            for s in (seo_data.get("usage_steps") or []) if isinstance(s, dict) and s.get("name")
        ][:8],
        "related_queries": [str(q)[:120] for q in (seo_data.get("related_queries") or []) if q][:8],
    }

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
        "seo": seo,
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
    """Async job pattern — returns immediately with a job_id.
    Client polls GET /products/{id}/enrich-narrative/status.
    Bypasses the 60 s ingress timeout for Claude calls."""
    product = await db.products.find_one({"id": product_id}, {"_id": 0, "site_id": 1})
    if not product:
        raise HTTPException(404, "Produit introuvable")

    job_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    await db.narrative_jobs.insert_one({
        "id": job_id,
        "product_id": product_id,
        "site_id": product.get("site_id"),
        "user_id": user.get("id"),
        "status": "running",
        "created_at": now,
    })

    async def _run():
        try:
            result = await enrich_product_narrative(product_id, force=force)
            status = result.get("status")
            if status == "ok":
                await db.narrative_jobs.update_one(
                    {"id": job_id},
                    {"$set": {"status": "done", "finished_at": datetime.now(timezone.utc).isoformat()}},
                )
            elif status == "llm_budget_exceeded":
                await db.narrative_jobs.update_one(
                    {"id": job_id},
                    {"$set": {"status": "failed",
                              "error": "Budget Emergent LLM Key épuisé. Recharge la clé depuis Profile → Universal Key → Add Balance.",
                              "finished_at": datetime.now(timezone.utc).isoformat()}},
                )
            else:
                await db.narrative_jobs.update_one(
                    {"id": job_id},
                    {"$set": {"status": "failed",
                              "error": f"Échec IA ({status}). Réessayez dans 1 min.",
                              "finished_at": datetime.now(timezone.utc).isoformat()}},
                )
        except Exception as e:
            logger.exception("Narrative job failed")
            await db.narrative_jobs.update_one(
                {"id": job_id},
                {"$set": {"status": "failed", "error": str(e)[:300],
                          "finished_at": datetime.now(timezone.utc).isoformat()}},
            )

    asyncio.create_task(_run())
    return {"ok": True, "job_id": job_id, "status": "running"}


@router.get("/products/{product_id}/enrich-narrative/status")
async def enrich_status(product_id: str, user=Depends(get_current_user)):
    """Latest narrative job status for a product."""
    job = await db.narrative_jobs.find_one(
        {"product_id": product_id}, {"_id": 0}, sort=[("created_at", -1)]
    )
    return job or {"status": "idle"}


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
