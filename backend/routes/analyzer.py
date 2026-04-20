"""
AI-powered niche analyzer for Concept Factory.
The Concepteur types any product idea → we get structured market analysis
across 6 EU countries (FR, DE, CH, BE, UK, NL) via Claude Sonnet 4.5.

When a DataForSEO key becomes available, we'll merge in real Google Ads
volumes/CPC via the `enrich_with_dataforseo()` hook.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Optional, List
from unicodedata import normalize

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from deps import db, get_current_user, EMERGENT_LLM_KEY

logger = logging.getLogger("conceptfactory.analyzer")

router = APIRouter(prefix="/niches")


class AnalyzeInput(BaseModel):
    product: str = Field(..., min_length=2, max_length=200,
                         description="Produit ou niche (ex: 'fauteuil releveur électrique')")
    budget_per_country_eur: int = 30  # fixed by business rule
    notes: Optional[str] = ""


# ----------------------------------------------------------------- #
# System prompt — forces structured JSON output
# ----------------------------------------------------------------- #
ANALYZER_SYSTEM_PROMPT = """Tu es un expert en analyse de marché e-commerce Silver Economy (60+ ans) en Europe.
Tu analyses un produit/niche sur 6 marchés : France (FR), Allemagne (DE), Suisse (CH), Belgique+Luxembourg (BE), Royaume-Uni (UK), Pays-Bas (NL).

Tu réponds UNIQUEMENT avec du JSON valide (sans markdown, sans commentaire).
Tu fournis des estimations QUALIFIÉES basées sur ta connaissance des données Google Ads Keyword Planner, Ahrefs, SEMrush.

Schéma JSON obligatoire :
{
  "name": "Nom du produit/niche (ex: Fauteuil releveur électrique)",
  "slug": "kebab-case-slug",
  "emoji": "un emoji",
  "category": "Catégorie marché (ex: Confort premium, Mobilité, Salle de bain...)",
  "tagline": "Accroche marketing en FR, ton senior-friendly bienveillant, 8-15 mots",
  "description": "2-3 phrases expliquant le produit et son usage cible",
  "keywords": ["3 à 6 mots-clés principaux"],
  "buy_price_eur": [prix_achat_min, prix_achat_max],
  "sell_price_eur": [prix_vente_min, prix_vente_max],
  "aov_eur": [panier_moyen_min, panier_moyen_max],
  "margin_pct": 65,
  "ecf_score": 0-100,
  "hero": true/false (true si produit HERO gros AOV >500€),
  "suppliers": ["CJ Dropshipping", "BigBuy", "AliExpress EU"],
  "country_metrics": {
    "FR": {"volume": 2900, "cpc": 0.85, "kd": 34, "cpa_target": 22, "seasonality": "Stable", "verdict": "GO", "reasoning": "Raison brève"},
    "DE": {...}, "CH": {...}, "BE": {...}, "UK": {...}, "NL": {...}
  },
  "best_country": "FR",
  "overall_verdict": "GO|MAYBE|NOGO",
  "verdict_reasoning": "1-2 phrases justifiant le verdict global",
  "risks": ["2-3 risques identifiés"],
  "opportunities": ["2-3 opportunités de différenciation"],
  "synthesis_per_country": {
    "FR": "Synthèse 2-3 phrases : volumes, concurrence, saisonnalité, go/pass",
    "DE": "...", "CH": "...", "BE": "...", "UK": "...", "NL": "..."
  }
}

Règles de verdict par marché :
- GO : volume ≥ 3000/mois ET CPC raisonnable par rapport au panier
- MAYBE : volume 1500-3000 OU concurrence forte
- NOGO : volume < 1500 OU CPA cible > 30% du panier

Règles verdict global :
- GO : total volume 6 pays ≥ 20000 ET margin_pct > 60 ET au moins 2 marchés GO
- MAYBE : total 10000-20000 OU margin_pct 50-60
- NOGO : < 10000 total OU margin_pct < 50

Tu DOIS retourner un JSON parfaitement valide, rien d'autre."""


JSON_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def _strip_json_fence(text: str) -> str:
    """Remove markdown fences if the model returned them despite instructions."""
    return JSON_FENCE_RE.sub("", text).strip()


def _make_slug(name: str) -> str:
    n = normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    n = re.sub(r"[^a-zA-Z0-9]+", "-", n).strip("-").lower()
    return n[:80] or f"niche-{uuid.uuid4().hex[:6]}"


def _enrich(analysis: dict) -> dict:
    """Compute aggregates from country_metrics."""
    cm = analysis.get("country_metrics", {}) or {}
    volumes = [m.get("volume", 0) for m in cm.values() if isinstance(m, dict)]
    cpcs = [m.get("cpc", 0) for m in cm.values() if isinstance(m, dict)]
    kds = [m.get("kd", 0) for m in cm.values() if isinstance(m, dict)]
    analysis["total_volume_monthly"] = sum(volumes)
    analysis["avg_cpc_eur"] = round(sum(cpcs) / max(len(cpcs), 1), 2)
    analysis["avg_kd"] = round(sum(kds) / max(len(kds), 1), 1)
    analysis["go_countries"] = [
        c for c, m in cm.items()
        if isinstance(m, dict) and m.get("verdict") == "GO"
    ]
    if not analysis.get("slug"):
        analysis["slug"] = _make_slug(analysis.get("name", ""))
    return analysis


async def _ask_claude(prompt: str, session_id: str) -> dict:
    """Call Claude Sonnet 4.5 and parse JSON response."""
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        chat = (
            LlmChat(
                api_key=EMERGENT_LLM_KEY,
                session_id=session_id,
                system_message=ANALYZER_SYSTEM_PROMPT,
            )
            .with_model("anthropic", "claude-sonnet-4-5-20250929")
        )
        response = await asyncio.wait_for(
            chat.send_message(UserMessage(text=prompt)),
            timeout=90
        )
        raw = response if isinstance(response, str) else str(response)
        raw = _strip_json_fence(raw)
        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            logger.error(f"LLM returned invalid JSON: {e}\n{raw[:500]}")
            raise HTTPException(
                status_code=502,
                detail="L'IA a retourné un format invalide. Réessayez."
            )
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="L'analyse prend trop de temps (>90s). Réessayez.")
    except HTTPException:
        raise
    except Exception as e:
        err = str(e)
        if "Budget has been exceeded" in err or "budget" in err.lower():
            raise HTTPException(
                status_code=402,
                detail="Budget LLM épuisé. Profile → Universal Key → Add Balance."
            )
        logger.exception("Analyzer LLM call failed")
        raise HTTPException(status_code=500, detail=f"Erreur IA : {err[:200]}")


# ----------------------------------------------------------------- #
# Endpoints
# ----------------------------------------------------------------- #
@router.post("/analyze")
async def analyze_niche(data: AnalyzeInput, user: dict = Depends(get_current_user)):
    """Launch full multi-country niche analysis.
    Returns a rich report + persists it in `niche_analyses` for history."""
    product = data.product.strip()

    prompt = f"""Analyse ce produit pour un e-commerce multi-pays Silver Economy :

PRODUIT : {product}
{f"NOTES : {data.notes}" if data.notes else ""}

Budget publicitaire par marché choisi : {data.budget_per_country_eur}€/jour
Cible : seniors 60+ et leurs aidants, en Europe continentale.

Fournis une analyse complète selon le schéma JSON demandé. Sois réaliste sur les
volumes (ordres de grandeur Google Ads Keyword Planner) et les CPC (benchmarks
Silver Economy). Pour chaque pays, donne une synthèse exploitable dans synthesis_per_country."""

    session_id = f"analyze-{user['id']}-{uuid.uuid4().hex[:8]}"
    analysis = await _ask_claude(prompt, session_id)
    analysis = _enrich(analysis)

    # Persist
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "id": str(uuid.uuid4()),
        "user_id": user["id"],
        "product_input": product,
        "notes": data.notes or "",
        "budget_per_country_eur": data.budget_per_country_eur,
        "analysis": analysis,
        "source": "ai_claude_sonnet_4.5",
        "enriched_with_dataforseo": False,  # toggled when real key lands
        "created_at": now,
    }
    await db.niche_analyses.insert_one(dict(doc))
    doc.pop("_id", None)
    return doc


@router.get("/analyses")
async def list_my_analyses(user: dict = Depends(get_current_user), limit: int = 20):
    """History of recent analyses for the current user."""
    items = (
        await db.niche_analyses.find(
            {"user_id": user["id"]},
            {"_id": 0}
        )
        .sort("created_at", -1)
        .limit(limit)
        .to_list(limit)
    )
    # Trim heavy fields for list view
    for a in items:
        a.pop("notes", None)
        if a.get("analysis"):
            a["analysis_summary"] = {
                "name": a["analysis"].get("name"),
                "emoji": a["analysis"].get("emoji"),
                "overall_verdict": a["analysis"].get("overall_verdict"),
                "total_volume_monthly": a["analysis"].get("total_volume_monthly"),
                "ecf_score": a["analysis"].get("ecf_score"),
                "go_countries": a["analysis"].get("go_countries", []),
                "slug": a["analysis"].get("slug"),
            }
            del a["analysis"]
    return items


@router.get("/analyses/{analysis_id}")
async def get_analysis(analysis_id: str, user: dict = Depends(get_current_user)):
    a = await db.niche_analyses.find_one(
        {"id": analysis_id, "user_id": user["id"]},
        {"_id": 0}
    )
    if not a:
        raise HTTPException(status_code=404, detail="Analyse introuvable")
    return a
