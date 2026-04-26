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
    """Phase 0 — délègue à `safe_claude_json` (retry expo + circuit breaker).

    Préserve l'API existante : retourne `None` si l'IA est indisponible ou
    que le JSON est mal formé (les appelants peuvent déjà gérer le cas None).
    """
    if not EMERGENT_LLM_KEY:
        return None
    from services.llm_resilience import safe_claude_json, LLMUnavailableError
    try:
        return await safe_claude_json(
            system, user,
            session_id=f"cockpit-{uuid.uuid4().hex[:8]}",
            timeout=timeout,
        )
    except (LLMUnavailableError, ValueError) as e:
        logger.warning(f"[cockpit] LLM call returned None: {e}")
        return None
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
# =====================================================================
# 2. Financial forecast — 30 days projection, 3 scenarios, per-market detail
# =====================================================================
class ForecastInput(BaseModel):
    site_id: str
    daily_budget_total_eur: float = 30.0     # per market
    concepteur_share_eur: float = 15.0        # per market


# VAT rates by country — used to convert TTC revenue to HT
VAT_BY_COUNTRY = {
    "FR": 0.20, "DE": 0.19, "CH": 0.081, "BE": 0.21, "LU": 0.17,
    "UK": 0.20, "NL": 0.21, "IT": 0.22, "ES": 0.21, "AT": 0.20, "IE": 0.23,
}

# Scenario multipliers — conversion rate & upsell attach rate benchmarks
# for Silver Economy e-commerce (2024 industry data).
SCENARIOS = {
    "pessimistic": {
        "label": "Pessimiste",
        "conv_rate_pct": 0.8,
        "upsell_attach_rate_pct": 15,
        "cpc_multiplier": 1.15,       # assume 15% CPC inflation (competition spike)
        "description": "CR 0,8%, attach 15%, CPC +15%. Si tes Ads sous-performent.",
    },
    "realistic": {
        "label": "Réaliste",
        "conv_rate_pct": 1.5,
        "upsell_attach_rate_pct": 25,
        "cpc_multiplier": 1.0,
        "description": "CR 1,5%, attach 25%, CPC Google estimé. Benchmark Silver Eco 2024.",
    },
    "optimistic": {
        "label": "Optimiste",
        "conv_rate_pct": 2.5,
        "upsell_attach_rate_pct": 40,
        "cpc_multiplier": 0.9,         # assume CPC optimization
        "description": "CR 2,5%, attach 40%, CPC -10%. Ads optimisées, UX performante.",
    },
}

# Default fallbacks when Google data is missing (per-market typical CPC for FR senior niches)
DEFAULT_CPC_BY_COUNTRY = {
    "FR": 1.20, "DE": 1.50, "CH": 2.20, "BE": 1.10, "UK": 1.80,
    "NL": 1.30, "IT": 0.95, "ES": 0.90, "LU": 1.00, "AT": 1.30,
}


def _product_name_text(p):
    n = p.get("name")
    if isinstance(n, dict):
        return n.get("fr") or n.get("en") or next(iter(n.values()), "") or "(sans nom)"
    return str(n or "") or "(sans nom)"


@router.post("/sites/{site_id}/financial-forecast")
async def financial_forecast(site_id: str, body: ForecastInput, user=Depends(get_current_user)):
    """30-day projection with 3 scenarios (pessimistic / realistic / optimistic),
    per-market breakdown + global consolidation, integrating main products,
    upsells attach rate, Google CPC data, and actionable insights."""
    await _check_site_access(site_id, user)
    site = await db.sites.find_one({"id": site_id}, {"_id": 0})
    if not site:
        raise HTTPException(404, "Site introuvable")

    countries = site.get("selected_countries") or ["FR"]
    days = 30

    # --- 1. Catalog snapshot (main + upsells) ---------------------------
    products = await db.products.find(
        {"site_id": site_id, "status": "active"},
        {"_id": 0, "id": 1, "name": 1, "price": 1, "cost_price_ht": 1,
         "role": 1, "linked_product_ids": 1, "supplier_url": 1},
    ).to_list(500)

    main_products = [p for p in products if p.get("role") != "upsell"]
    upsells = [p for p in products if p.get("role") == "upsell"]

    if not main_products:
        raise HTTPException(400, "Aucun produit principal actif. Importe au moins 1 produit à l'étape 2.")

    def _avg(lst):
        lst = [x for x in lst if x > 0]
        return round(sum(lst) / len(lst), 2) if lst else 0

    main_prices = [float(p.get("price") or 0) for p in main_products]
    main_costs = [float(p.get("cost_price_ht") or 0) for p in main_products]
    avg_main_price = _avg(main_prices) or 1.0
    avg_main_cost = _avg(main_costs) or (avg_main_price * 0.40)  # fallback 40%
    avg_main_margin_pct = round(((avg_main_price - avg_main_cost) / avg_main_price) * 100, 1) if avg_main_price else 0

    # Upsell economics (with -20% impulse discount assumption)
    IMPULSE_DISCOUNT = 0.20
    upsell_prices_discounted = [float(p.get("price") or 0) * (1 - IMPULSE_DISCOUNT) for p in upsells]
    upsell_costs = [float(p.get("cost_price_ht") or 0) for p in upsells]
    avg_upsell_price = _avg(upsell_prices_discounted)
    avg_upsell_cost = _avg(upsell_costs)
    avg_upsell_margin_pct = (
        round(((avg_upsell_price - avg_upsell_cost) / avg_upsell_price) * 100, 1)
        if avg_upsell_price > 0 else 0
    )

    # % of main products that have at least 1 linked upsell (or any upsell exists site-wide)
    if upsells:
        any_upsell_unlinked = any(not (u.get("linked_product_ids") or []) for u in upsells)
        if any_upsell_unlinked:
            upsell_coverage_pct = 100.0  # global fallback → every main gets recommendation
        else:
            main_ids = {p["id"] for p in main_products}
            covered = set()
            for u in upsells:
                covered.update(m for m in (u.get("linked_product_ids") or []) if m in main_ids)
            upsell_coverage_pct = round((len(covered) / max(1, len(main_ids))) * 100, 1)
    else:
        upsell_coverage_pct = 0.0

    # --- 2. Google CPC data per market (from niche_analysis) ------------
    niche_an = site.get("design", {}).get("niche_analysis") or {}
    results = niche_an.get("results") or []
    cpc_by_market = {}
    volume_by_market = {}
    competition_by_market = {}
    for r in results:
        cc = r.get("country")
        if cc in countries:
            m = r.get("metrics") or {}
            cpc_by_market[cc] = float(m.get("cpc_weighted_eur") or 0) or DEFAULT_CPC_BY_COUNTRY.get(cc, 1.2)
            volume_by_market[cc] = int(m.get("volume_total") or 0)
            competition_by_market[cc] = int(m.get("competition_weighted") or 0)
    # Fallback for markets missing from niche_analysis
    for cc in countries:
        cpc_by_market.setdefault(cc, DEFAULT_CPC_BY_COUNTRY.get(cc, 1.2))
        volume_by_market.setdefault(cc, 0)
        competition_by_market.setdefault(cc, 0)

    # --- 3. Compute each scenario × each market -------------------------
    daily_budget_per_market = float(body.daily_budget_total_eur or 30)
    concepteur_share_per_market = float(body.concepteur_share_eur or 15)
    SHIPPING_COST_PER_ORDER = 6.0  # avg supplier fulfillment + carrier fee

    def _compute_scenario(scen_key, scen):
        conv_rate = scen["conv_rate_pct"] / 100.0
        attach = scen["upsell_attach_rate_pct"] / 100.0 if upsells else 0.0
        cpc_mult = scen["cpc_multiplier"]

        # Per-order economics (same across markets, differs by scenario via attach rate)
        aov = avg_main_price + (attach * avg_upsell_price)
        per_order_cogs = avg_main_cost + (attach * avg_upsell_cost)
        per_order_gross = aov - per_order_cogs - SHIPPING_COST_PER_ORDER

        per_market = {}
        total = {
            "clicks": 0, "conversions": 0,
            "revenue_ttc_eur": 0.0, "revenue_ht_eur": 0.0,
            "cogs_eur": 0.0, "shipping_eur": 0.0,
            "ad_spend_eur": 0.0, "gross_margin_eur": 0.0,
            "net_margin_concepteur_eur": 0.0,
        }
        for cc in countries:
            cpc = round(cpc_by_market.get(cc, 1.2) * cpc_mult, 2)
            vat = VAT_BY_COUNTRY.get(cc, 0.20)
            daily_clicks = daily_budget_per_market / cpc if cpc > 0 else 0
            daily_conv = daily_clicks * conv_rate
            monthly_conv = daily_conv * days
            monthly_revenue_ttc = monthly_conv * aov
            monthly_revenue_ht = monthly_revenue_ttc / (1 + vat)
            monthly_vat_collected = monthly_revenue_ttc - monthly_revenue_ht
            monthly_cogs = monthly_conv * per_order_cogs
            monthly_shipping = monthly_conv * SHIPPING_COST_PER_ORDER
            monthly_ad_spend = daily_budget_per_market * days
            monthly_gross = monthly_revenue_ht - monthly_cogs - monthly_shipping - monthly_ad_spend
            monthly_net_concepteur = monthly_gross * 0.50  # 50/50 split with platform
            monthly_commission_altiaro = monthly_gross * 0.50
            roas = monthly_revenue_ttc / monthly_ad_spend if monthly_ad_spend > 0 else 0
            cpa_real = monthly_ad_spend / monthly_conv if monthly_conv > 0 else 0
            aov_ht = aov / (1 + vat)
            break_even_conv = (
                monthly_ad_spend / max(aov_ht - per_order_cogs - SHIPPING_COST_PER_ORDER, 0.01)
                if (aov_ht - per_order_cogs - SHIPPING_COST_PER_ORDER) > 0
                else None
            )
            gross_margin_pct = (monthly_gross / monthly_revenue_ht * 100) if monthly_revenue_ht > 0 else 0
            per_market[cc] = {
                "cpc_eur": cpc,
                "vat_pct": round(vat * 100, 1),
                "daily_clicks": round(daily_clicks, 1),
                "daily_conversions": round(daily_conv, 2),
                "monthly_conversions": round(monthly_conv),
                "aov_ttc_eur": round(aov, 2),
                "aov_ht_eur": round(aov_ht, 2),
                "revenue_ttc_eur": round(monthly_revenue_ttc, 2),
                "revenue_ht_eur": round(monthly_revenue_ht, 2),
                "vat_collected_eur": round(monthly_vat_collected, 2),
                "cogs_eur": round(monthly_cogs, 2),
                "shipping_eur": round(monthly_shipping, 2),
                "ad_spend_eur": round(monthly_ad_spend, 2),
                "gross_margin_eur": round(monthly_gross, 2),
                "gross_margin_pct": round(gross_margin_pct, 1),
                "commission_altiaro_eur": round(monthly_commission_altiaro, 2),
                "net_margin_concepteur_eur": round(monthly_net_concepteur, 2),
                "roas": round(roas, 2),
                "cpa_real_eur": round(cpa_real, 2),
                "break_even_monthly_conv": round(break_even_conv, 1) if break_even_conv is not None else None,
                "search_volume_monthly": volume_by_market.get(cc, 0),
                "competition_index": competition_by_market.get(cc, 0),
            }
            total["clicks"] += daily_clicks * days
            total["conversions"] += monthly_conv
            total["revenue_ttc_eur"] += monthly_revenue_ttc
            total["revenue_ht_eur"] += monthly_revenue_ht
            total.setdefault("vat_collected_eur", 0.0)
            total["vat_collected_eur"] += monthly_vat_collected
            total["cogs_eur"] += monthly_cogs
            total["shipping_eur"] += monthly_shipping
            total["ad_spend_eur"] += monthly_ad_spend
            total["gross_margin_eur"] += monthly_gross
            total["net_margin_concepteur_eur"] += monthly_net_concepteur
            total.setdefault("commission_altiaro_eur", 0.0)
            total["commission_altiaro_eur"] += monthly_commission_altiaro

        roas_global = total["revenue_ttc_eur"] / total["ad_spend_eur"] if total["ad_spend_eur"] > 0 else 0
        cpa_real_global = total["ad_spend_eur"] / total["conversions"] if total["conversions"] > 0 else 0
        gross_margin_pct_global = (total["gross_margin_eur"] / total["revenue_ht_eur"] * 100) if total["revenue_ht_eur"] > 0 else 0
        return {
            "key": scen_key,
            "label": scen["label"],
            "description": scen["description"],
            "params": {
                "conv_rate_pct": scen["conv_rate_pct"],
                "upsell_attach_rate_pct": scen["upsell_attach_rate_pct"] if upsells else 0,
                "cpc_multiplier": cpc_mult,
                "avg_order_value_ttc_eur": round(aov, 2),
                "gross_per_order_eur": round(per_order_gross, 2),
                "cogs_per_order_eur": round(per_order_cogs, 2),
                "shipping_cost_per_order_eur": SHIPPING_COST_PER_ORDER,
            },
            "per_market": per_market,
            "global": {
                "clicks": round(total["clicks"]),
                "conversions": round(total["conversions"]),
                "revenue_ttc_eur": round(total["revenue_ttc_eur"], 2),
                "revenue_ht_eur": round(total["revenue_ht_eur"], 2),
                "vat_collected_eur": round(total["vat_collected_eur"], 2),
                "cogs_eur": round(total["cogs_eur"], 2),
                "shipping_eur": round(total["shipping_eur"], 2),
                "ad_spend_eur": round(total["ad_spend_eur"], 2),
                "gross_margin_eur": round(total["gross_margin_eur"], 2),
                "gross_margin_pct": round(gross_margin_pct_global, 1),
                "commission_altiaro_eur": round(total["commission_altiaro_eur"], 2),
                "net_margin_concepteur_eur": round(total["net_margin_concepteur_eur"], 2),
                "roas": round(roas_global, 2),
                "cpa_real_eur": round(cpa_real_global, 2),
            },
        }

    scenarios_out = {k: _compute_scenario(k, v) for k, v in SCENARIOS.items()}

    # --- 4. Verdict based on realistic scenario -------------------------
    realistic_g = scenarios_out["realistic"]["global"]
    realistic_roas = realistic_g["roas"]
    realistic_net = realistic_g["net_margin_concepteur_eur"]
    verdict = (
        "healthy" if realistic_roas >= 2.5 and realistic_net > 0
        else "acceptable" if realistic_roas >= 1.8 and realistic_net > -100
        else "risky"
    )

    # --- 4.b Launch gate — THE critical safety check --------------------
    # Per-order gross margin HT must cover the CPA (ads cost per acquisition)
    # with a safety buffer. This prevents launching products where the ad
    # cost eats the whole margin (e.g. fauteuils releveurs: 100€ margin vs 90€ CPA).
    MIN_SAFETY_RATIO = 1.5  # margin/CPA < 1.5 = blocked
    OK_SAFETY_RATIO = 2.0   # margin/CPA ≥ 2.0 = safe launch
    real_conv = max(realistic_g["conversions"], 1)
    per_order_margin_ht = (
        realistic_g["revenue_ht_eur"] - realistic_g["cogs_eur"] - realistic_g["shipping_eur"]
    ) / real_conv
    per_order_cpa = realistic_g["cpa_real_eur"]
    safety_ratio = per_order_margin_ht / per_order_cpa if per_order_cpa > 0 else 999

    if safety_ratio >= OK_SAFETY_RATIO and per_order_margin_ht - per_order_cpa >= 30:
        gate_status = "ok"
        gate_message = (
            f"Feu vert : ta marge par commande ({per_order_margin_ht:.0f} € HT) couvre "
            f"{safety_ratio:.1f}× ton coût d'acquisition ({per_order_cpa:.0f} €). "
            f"Tu gagnes ~{per_order_margin_ht - per_order_cpa:.0f} € net par vente."
        )
        gate_blocker = None
    elif safety_ratio >= MIN_SAFETY_RATIO:
        gate_status = "warning"
        gate_message = (
            f"Marge fine : {per_order_margin_ht:.0f} € HT de marge vs {per_order_cpa:.0f} € de CPA "
            f"({safety_ratio:.1f}×). Ça passe mais le moindre CPC qui monte te fait basculer. "
            f"Augmente tes prix, ajoute des upsells ou monte le budget pour baisser le CPA."
        )
        gate_blocker = None
    else:
        gate_status = "blocked"
        gate_message = (
            f"Stop : tu ne peux pas lancer ce projet. Ta marge brute par commande "
            f"({per_order_margin_ht:.0f} € HT) est trop faible face à ton coût d'acquisition "
            f"({per_order_cpa:.0f} €). Le moindre clic te fait perdre de l'argent."
        )
        actions = []
        if low_margin_count := len([
            p for p in main_products
            if p.get("price") and p.get("cost_price_ht") and p["price"] > 0
            and ((p["price"] - p["cost_price_ht"]) / p["price"]) < 0.50
        ]):
            actions.append(f"Remplace les {low_margin_count} produit(s) à marge <50%")
        if not upsells or upsell_coverage_pct < 80:
            actions.append("Ajoute des upsells (+25% panier moyen)")
        if per_order_margin_ht < per_order_cpa:
            actions.append(f"Monte tes prix d'au moins +{per_order_cpa - per_order_margin_ht:.0f} €/commande")
        gate_blocker = {
            "reason": "margin_below_cpa",
            "actions": actions or ["Pivote sur une niche moins concurrentielle (CPC plus bas)"],
        }

    launch_gate = {
        "status": gate_status,                                  # ok | warning | blocked
        "per_order_margin_ht_eur": round(per_order_margin_ht, 2),
        "per_order_cpa_eur": round(per_order_cpa, 2),
        "per_order_net_profit_eur": round(per_order_margin_ht - per_order_cpa, 2),
        "safety_ratio": round(safety_ratio, 2),
        "min_safety_ratio_required": MIN_SAFETY_RATIO,
        "ok_safety_ratio": OK_SAFETY_RATIO,
        "message": gate_message,
        "blocker": gate_blocker,
    }

    # --- 5. Actionable insights -----------------------------------------
    insights = []
    low_margin_products = [
        p for p in main_products
        if p.get("price") and p.get("cost_price_ht")
        and p["price"] > 0
        and ((p["price"] - p["cost_price_ht"]) / p["price"]) < 0.40
    ]
    if low_margin_products:
        insights.append({
            "severity": "warning",
            "title": f"{len(low_margin_products)} produit(s) à marge faible (<40%)",
            "body": "Les CAC Ads mangent ta marge. Cherche des alternatives à marge ≥ 50% sur CJ/AliExpress.",
            "products": [
                {"id": p["id"], "name": _product_name_text(p)[:60],
                 "margin_pct": round(((p["price"] - p["cost_price_ht"]) / p["price"]) * 100, 1)}
                for p in low_margin_products[:5]
            ],
            "action": "reimport_products",
        })

    if not upsells:
        potential_extra_rev = realistic_g["revenue_ttc_eur"] * 0.12  # attach 25% × upsell price ≈ +12% CA typique
        insights.append({
            "severity": "info",
            "title": "Aucun upsell importé",
            "body": f"En ajoutant 3-5 upsells à l'étape 3 (avec -20% impulse au drawer panier), tu pourrais gagner ~{round(potential_extra_rev)}€ de revenue/mois en scénario réaliste.",
            "action": "add_upsells",
        })
    elif upsell_coverage_pct < 80:
        insights.append({
            "severity": "info",
            "title": f"Couverture upsell incomplète ({upsell_coverage_pct:.0f}%)",
            "body": "Certains produits principaux n'ont pas d'upsell associé — ils ratent des cross-sells storefront.",
            "action": "link_upsells",
        })

    # Per-market red flags
    for cc in countries:
        pm = scenarios_out["realistic"]["per_market"][cc]
        if pm["gross_margin_eur"] < 0:
            insights.append({
                "severity": "warning",
                "title": f"Marché {cc} : marge brute négative",
                "body": (
                    f"CPC {pm['cpc_eur']}€ × {days}j / CR 1,5% ne génère pas assez de CA pour couvrir "
                    f"le budget Ads ({pm['ad_spend_eur']}€). Ton panier moyen doit être plus élevé OU "
                    f"supprime ce marché."
                ),
                "market": cc,
                "action": "remove_market_or_raise_aov",
            })
        if pm["competition_index"] > 70:
            insights.append({
                "severity": "warning",
                "title": f"Marché {cc} : concurrence saturée ({pm['competition_index']}/100)",
                "body": "CPC risque de grimper. Privilégie des mots-clés long-tail ou pivote sur un autre marché.",
                "market": cc,
                "action": "pivot_keywords",
            })

    # ROAS insight
    if realistic_roas < 2.0:
        insights.append({
            "severity": "warning",
            "title": f"ROAS réaliste faible ({realistic_roas}x)",
            "body": "En dessous de 2x, ton business est fragile. Augmente tes prix, améliore tes upsells, ou change de niche.",
            "action": "raise_prices_or_pivot",
        })
    elif realistic_roas >= 3.0:
        insights.append({
            "severity": "success",
            "title": f"ROAS réaliste solide ({realistic_roas}x)",
            "body": "Tu peux scale avec confiance. Duplique ton site sur d'autres marchés depuis la Scale station.",
            "action": "scale",
        })

    # --- 6. Sensitivity analysis (what-if) ------------------------------
    real_global = scenarios_out["realistic"]["global"]
    # Impact if attach rate +10pts
    if upsells:
        extra_rev_per_attach_pt = real_global["revenue_ttc_eur"] * (avg_upsell_price / max(
            scenarios_out["realistic"]["params"]["avg_order_value_ttc_eur"], 1
        )) / 100
        sens_upsell_10 = round(extra_rev_per_attach_pt * 10, 2)
    else:
        sens_upsell_10 = 0
    # Impact if avg main price +10€
    extra_rev_price = real_global["conversions"] * 10
    sens_price_plus_10 = round(extra_rev_price, 2)
    # Impact if daily budget x2
    sens_double_budget = round(real_global["revenue_ttc_eur"], 2)  # linear assumption

    forecast = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "markets": countries,
        "days": days,
        "verdict": verdict,
        "budget": {
            "daily_per_market_eur": daily_budget_per_market,
            "concepteur_daily_per_market_eur": concepteur_share_per_market,
            "platform_daily_per_market_eur": daily_budget_per_market - concepteur_share_per_market,
            "total_daily_eur": daily_budget_per_market * len(countries),
            "total_monthly_eur": daily_budget_per_market * len(countries) * days,
            "concepteur_monthly_eur": concepteur_share_per_market * len(countries) * days,
            "platform_monthly_eur": (daily_budget_per_market - concepteur_share_per_market) * len(countries) * days,
        },
        "catalog": {
            "main_products_count": len(main_products),
            "upsells_count": len(upsells),
            "avg_main_price_eur": avg_main_price,
            "avg_main_cost_eur": avg_main_cost,
            "avg_main_margin_pct": avg_main_margin_pct,
            "avg_upsell_price_eur": round(avg_upsell_price, 2),
            "avg_upsell_cost_eur": avg_upsell_cost,
            "avg_upsell_margin_pct": avg_upsell_margin_pct,
            "upsell_coverage_pct": upsell_coverage_pct,
            "impulse_discount_pct": round(IMPULSE_DISCOUNT * 100),
        },
        "google_data": {
            "per_market": {
                cc: {
                    "cpc_eur": cpc_by_market[cc],
                    "volume_monthly": volume_by_market[cc],
                    "competition_index": competition_by_market[cc],
                    "has_real_data": cc in {r.get("country") for r in results},
                }
                for cc in countries
            },
        },
        "scenarios": scenarios_out,
        "sensitivity": {
            "revenue_gain_if_upsell_attach_plus_10pts_eur": sens_upsell_10,
            "revenue_gain_if_avg_price_plus_10eur": sens_price_plus_10,
            "revenue_gain_if_daily_budget_doubled_eur": sens_double_budget,
        },
        "launch_gate": launch_gate,
        "insights": insights,
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


@router.post("/sites/{site_id}/journey/validate-step", deprecated=True)
async def validate_journey_step(
    site_id: str, body: StepValidateInput, user=Depends(get_current_user),
):
    """DEPRECATED (Chantier 1) — La validation manuelle est supprimée.

    Les 9 étapes sont maintenant complétées automatiquement selon les données
    en DB (5 produits importés = étape 2 OK, design publié = étape 5 OK, etc.).

    Utilisez GET /api/sites/{site_id}/steps/status pour obtenir l'état auto.
    Cet endpoint est conservé en 410 Gone pour forcer les clients frontend
    obsolètes à basculer.
    """
    raise HTTPException(
        status_code=410,
        detail=(
            "La validation manuelle des étapes est supprimée. "
            "Les étapes sont désormais complétées automatiquement par les données. "
            "Consultez GET /api/sites/{site_id}/steps/status pour voir l'état."
        ),
    )


@router.get("/sites/{site_id}/upsell-recommendations")
async def upsell_recommendations_get(site_id: str, user=Depends(get_current_user)):
    await _check_site_access(site_id, user)
    site = await db.sites.find_one({"id": site_id}, {"_id": 0, "design.upsell_recommendations": 1})
    return ((site or {}).get("design") or {}).get("upsell_recommendations") or {}
