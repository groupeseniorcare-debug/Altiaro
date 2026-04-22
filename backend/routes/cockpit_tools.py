"""
Cockpit tools — pricing analysis, financial forecast, upsell recommendations.
All endpoints are site-scoped and Concepteur/Admin-accessible.
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

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from deps import db, get_current_user, _check_site_access

logger = logging.getLogger("conceptfactory.cockpit_tools")
router = APIRouter()

EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")


def _strip_json_fence(text: str) -> str:
    return re.sub(r"^```(json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()


async def _claude_json(system: str, user: str, timeout: int = 60) -> Optional[dict]:
    if not EMERGENT_LLM_KEY:
        return None
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        chat = (
            LlmChat(
                api_key=EMERGENT_LLM_KEY,
                session_id=f"cockpit-{uuid.uuid4().hex[:8]}",
                system_message=system,
            )
            .with_model("anthropic", "claude-sonnet-4-5-20250929")
        )
        raw = await asyncio.wait_for(chat.send_message(UserMessage(text=user)), timeout=timeout)
        return json.loads(_strip_json_fence(raw if isinstance(raw, str) else str(raw)))
    except Exception:
        logger.exception("Claude cockpit tool failed")
        return None


# =====================================================================
# 1. Competitive pricing analysis
# =====================================================================
class PricingInput(BaseModel):
    site_id: str


@router.post("/sites/{site_id}/pricing-analysis")
async def pricing_analysis(site_id: str, _body: PricingInput, user=Depends(get_current_user)):
    await _check_site_access(site_id, user)
    site = await db.sites.find_one({"id": site_id}, {"_id": 0})
    if not site:
        raise HTTPException(404, "Site introuvable")

    niche = site.get("niche") or site.get("name", "")
    countries = site.get("selected_countries") or ["FR"]

    system = """Tu es un expert e-commerce Silver Economy spécialiste du pricing.
À partir d'une niche et de marchés cibles, produit une analyse concurrentielle et des fourchettes de prix recommandées.
Réponds en JSON strict (pas de prose, pas de markdown) :
{
  "market_overview": "2-3 phrases synthétiques",
  "competitors": [
    {"name": "...", "price_range": "X-Y€", "positioning": "entrée/milieu/premium", "strengths": "..."}
  ],
  "recommended_ranges": [
    {"product_type": "...", "entry_eur": 299, "sweet_spot_eur": 599, "premium_eur": 1200,
     "rationale": "pourquoi ce positionnement convertit le mieux"}
  ],
  "margin_advice": "recommandation marge brute % sur le sweet_spot",
  "strategic_notes": ["3 conseils tactiques pour maximiser la conversion"]
}"""

    user = f"""Niche : {niche}
Marchés cibles : {', '.join(countries)}
Contexte : dropshipping Silver Economy (60+), Altiaro SaaS, budget Ads 30€/j par marché.
Fournis l'analyse complète en JSON."""

    data = await _claude_json(system, user, timeout=90)
    if not data:
        raise HTTPException(502, "Analyse IA indisponible (Claude). Réessaie dans 1 minute.")

    snapshot = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "niche": niche,
        "countries": countries,
        **data,
    }
    await db.sites.update_one(
        {"id": site_id},
        {"$set": {"design.pricing_analysis": snapshot}},
    )
    return snapshot


@router.get("/sites/{site_id}/pricing-analysis")
async def pricing_analysis_get(site_id: str, user=Depends(get_current_user)):
    await _check_site_access(site_id, user)
    site = await db.sites.find_one({"id": site_id}, {"_id": 0, "design.pricing_analysis": 1})
    return ((site or {}).get("design") or {}).get("pricing_analysis") or {}


# =====================================================================
# 2. Financial forecast — 30 days projection
# =====================================================================
class ForecastInput(BaseModel):
    site_id: str
    daily_budget_total_eur: float = 30.0     # per market
    concepteur_share_eur: float = 15.0        # per market


@router.post("/sites/{site_id}/financial-forecast")
async def financial_forecast(site_id: str, body: ForecastInput, user=Depends(get_current_user)):
    await _check_site_access(site_id, user)
    site = await db.sites.find_one({"id": site_id}, {"_id": 0})
    if not site:
        raise HTTPException(404, "Site introuvable")

    countries = site.get("selected_countries") or ["FR"]
    days = 30

    products = await db.products.find(
        {"site_id": site_id, "status": "active"},
        {"_id": 0, "id": 1, "price": 1, "source_id": 1, "variants": 1, "cost": 1, "aliexpress_raw": 1},
    ).to_list(200)

    if not products:
        raise HTTPException(400, "Aucun produit actif. Importe au moins 1 produit avant d'estimer le prévisionnel.")

    # Average retail price (across active products)
    prices = [float(p.get("price") or 0) for p in products if (p.get("price") or 0) > 0]
    avg_price = round(sum(prices) / len(prices), 2) if prices else 0

    # Average supplier cost — use variant.price if available, else 40% of retail
    def _est_cost(p):
        variants = p.get("variants") or []
        if variants:
            vcosts = [float(v.get("price") or 0) for v in variants if (v.get("price") or 0) > 0]
            if vcosts:
                return min(vcosts)
        return round(float(p.get("price") or 0) * 0.40, 2)

    costs = [_est_cost(p) for p in products]
    avg_cost = round(sum(costs) / len(costs), 2) if costs else 0

    # Pull estimated CPA from the latest niche analysis (per market average)
    niche_an = site.get("design", {}).get("niche_analysis") or {}
    results = niche_an.get("results") or []
    # Filter results to the selected countries
    sel = [r for r in results if r.get("country") in countries]
    cpas = [float((r.get("metrics") or {}).get("estimated_cpa_eur") or 0) for r in sel]
    avg_cpa = round(sum(cpas) / len(cpas), 2) if cpas else max(avg_price * 0.30, 30)

    # Compute
    n_markets = len(countries)
    daily_budget_total = body.daily_budget_total_eur * n_markets
    monthly_budget_total = daily_budget_total * days
    concepteur_monthly = body.concepteur_share_eur * n_markets * days
    platform_monthly = monthly_budget_total - concepteur_monthly

    conversions_monthly = round(monthly_budget_total / avg_cpa) if avg_cpa > 0 else 0
    revenue_monthly = round(conversions_monthly * avg_price, 2)
    cogs_monthly = round(conversions_monthly * avg_cost, 2)
    shipping_monthly = round(conversions_monthly * 8, 2)  # avg shipping allowance
    gross_margin = round(revenue_monthly - cogs_monthly - shipping_monthly, 2)
    net_margin = round(gross_margin - concepteur_monthly, 2)  # concepteur's POV (he funded his 50%)
    roas = round(revenue_monthly / monthly_budget_total, 2) if monthly_budget_total > 0 else 0
    break_even_cpa = round(avg_price - avg_cost - 8, 2)

    forecast = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "markets": countries,
        "days": days,
        "assumptions": {
            "avg_retail_price_eur": avg_price,
            "avg_supplier_cost_eur": avg_cost,
            "avg_shipping_cost_eur": 8.0,
            "estimated_cpa_eur": avg_cpa,
            "break_even_cpa_eur": break_even_cpa,
            "active_products": len(products),
        },
        "budget": {
            "daily_per_market_eur": body.daily_budget_total_eur,
            "concepteur_daily_per_market_eur": body.concepteur_share_eur,
            "platform_daily_per_market_eur": body.daily_budget_total_eur - body.concepteur_share_eur,
            "total_daily_eur": daily_budget_total,
            "total_monthly_eur": monthly_budget_total,
            "concepteur_monthly_eur": concepteur_monthly,
            "platform_monthly_eur": platform_monthly,
        },
        "projection": {
            "estimated_conversions": conversions_monthly,
            "estimated_revenue_eur": revenue_monthly,
            "estimated_cogs_eur": cogs_monthly,
            "estimated_shipping_eur": shipping_monthly,
            "gross_margin_eur": gross_margin,
            "net_margin_concepteur_eur": net_margin,
            "roas": roas,
        },
        "verdict": (
            "healthy" if roas >= 2.5 and gross_margin > concepteur_monthly
            else "acceptable" if roas >= 1.8
            else "risky"
        ),
    }

    await db.sites.update_one(
        {"id": site_id},
        {"$set": {"design.financial_forecast": forecast}},
    )
    return forecast


@router.get("/sites/{site_id}/financial-forecast")
async def financial_forecast_get(site_id: str, user=Depends(get_current_user)):
    await _check_site_access(site_id, user)
    site = await db.sites.find_one({"id": site_id}, {"_id": 0, "design.financial_forecast": 1})
    return ((site or {}).get("design") or {}).get("financial_forecast") or {}


# =====================================================================
# 3. Upsell recommendations — Claude suggests AliExpress search keywords
# =====================================================================
class UpsellInput(BaseModel):
    site_id: str


@router.post("/sites/{site_id}/upsell-recommendations")
async def upsell_recommendations(site_id: str, _body: UpsellInput, user=Depends(get_current_user)):
    await _check_site_access(site_id, user)
    # Load products + the pricing_analysis from step 1 (used as IA context)
    site = await db.sites.find_one(
        {"id": site_id},
        {"_id": 0, "niche": 1, "selected_countries": 1, "design.pricing_analysis": 1},
    )
    pricing_context = ""
    pa = ((site or {}).get("design") or {}).get("pricing_analysis") or {}
    if pa.get("ranges"):
        pricing_context = "\n\nPOSITIONNEMENT PRIX CIBLE (étape 1 d'analyse de marché) :\n"
        for r in pa.get("ranges", [])[:4]:
            pricing_context += f"- {r.get('segment','')}: {r.get('entry','?')}–{r.get('premium','?')}€ (sweet-spot {r.get('sweet_spot','?')}€)\n"

    products = await db.products.find(
        {"site_id": site_id,
         "status": {"$in": ["active", "draft"]},
         "role": {"$ne": "upsell"}},
        {"_id": 0, "name": 1, "price": 1}
    ).to_list(50)

    if not products:
        raise HTTPException(400, "Aucun produit pour recommander des upsells.")

    def _name(p):
        n = p.get("name")
        if isinstance(n, dict):
            return n.get("fr") or n.get("en") or next(iter(n.values()), "")
        return str(n or "")

    catalog_text = "\n".join([f"- {_name(p)} ({p.get('price')}€)" for p in products[:20]])

    system = """Tu es un expert e-commerce Silver Economy spécialiste des upsells/cross-sells.
À partir d'un catalogue principal ET du positionnement prix cible du site, recommande 6 à 10 upsells/accessoires complémentaires, parfaits pour augmenter le panier moyen ou la marge.
Respecte la cohérence de gamme : si le site est positionné premium, ne recommande pas d'accessoires low-cost.
Réponds en JSON strict :
{
  "upsells": [
    {"keyword_ali": "coussin ergonomique mousse mémoire", "label_fr": "Coussin mémoire de forme",
     "pairs_with": "fauteuil releveur", "target_price_eur": 49, "margin_impact": "high",
     "rationale": "15 mots"}
  ]
}"""

    user = f"""Niche : {(site or {}).get('niche','')}
Marchés : {', '.join((site or {}).get('selected_countries') or ['FR'])}
Catalogue principal actuel :
{catalog_text}
{pricing_context}

Liste 6 à 10 upsells (accessoires, garanties, consommables) que je peux rechercher sur AliExpress/CJ via mots-clés.
Priorise ceux avec une vraie utilité (pas juste un gadget), cohérents avec le positionnement prix, et à forte marge."""

    data = await _claude_json(system, user, timeout=60)
    if not data or not data.get("upsells"):
        raise HTTPException(502, "Recommandations IA indisponibles. Réessaie dans 1 minute.")

    snapshot = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "used_pricing_context": bool(pricing_context),
        **data,
    }
    await db.sites.update_one(
        {"id": site_id},
        {"$set": {"design.upsell_recommendations": snapshot}},
    )
    return snapshot


# =====================================================================
# 4. Manual step validation — Concepteur can mark a journey step as "done"
#    regardless of auto-completion heuristics.
# =====================================================================
VALID_STEP_KEYS = {
    "pricing", "import", "upsells", "forecast",
    "branding", "pages", "content", "seo", "qa",
}


class StepValidateInput(BaseModel):
    step: str
    validated: bool = True


@router.post("/sites/{site_id}/journey/validate-step")
async def validate_journey_step(
    site_id: str, body: StepValidateInput, user=Depends(get_current_user),
):
    """Mark a cockpit journey step as validated (or un-validate it).
    The Concepteur drives his own progress — there are no product-count gates."""
    await _check_site_access(site_id, user)
    if body.step not in VALID_STEP_KEYS:
        raise HTTPException(400, f"Étape inconnue : {body.step}")

    site = await db.sites.find_one({"id": site_id}, {"_id": 0, "journey_validated": 1})
    validated = set((site or {}).get("journey_validated") or [])
    if body.validated:
        validated.add(body.step)
    else:
        validated.discard(body.step)
    await db.sites.update_one(
        {"id": site_id},
        {"$set": {
            "journey_validated": sorted(validated),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }},
    )
    return {"ok": True, "validated_steps": sorted(validated)}


@router.get("/sites/{site_id}/upsell-recommendations")
async def upsell_recommendations_get(site_id: str, user=Depends(get_current_user)):
    await _check_site_access(site_id, user)
    site = await db.sites.find_one({"id": site_id}, {"_id": 0, "design.upsell_recommendations": 1})
    return ((site or {}).get("design") or {}).get("upsell_recommendations") or {}
