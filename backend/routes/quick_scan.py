"""Quick Scan — Go/No-Go Express pour valider une niche avant lancement.

Contrairement au Deep Market Analyzer (qui est exhaustif et sert à construire un site),
cet outil répond à UNE seule question en <30s : *est-ce que je lance un site sur ce
produit, oui ou non ?*

Méthodologie :
1. Claude (Sonnet 4.5) génère 5 variantes de mots-clés stratégiques + estime
   le prix de vente concurrent moyen (min/median/max) dans le pays ciblé.
2. Google Keyword Planner donne les vrais volumes / CPC / concurrence pour
   le produit principal + les 5 variantes.
3. On calcule 4 critères go/no-go :
   - Prix moyen ≥ 50€
   - Volume cumulé (top 4 mots-clés) ≥ 5 000/mois
   - Concurrence pondérée ≤ 66/100
   - Coût d'acquisition estimé (CPC×50) ≤ 40% du prix
4. Verdict : GO / GO_WITH_RESERVE / NO_GO + score /100 + recommandation texte.
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
from pydantic import BaseModel, Field

from deps import db, get_current_user

logger = logging.getLogger("conceptfactory.quick_scan")
router = APIRouter()

EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")

# Seuils Go/No-Go (tunables via .env pour ajuster sans déployer)
MIN_PRICE_EUR = float(os.environ.get("QS_MIN_PRICE_EUR", "50"))
MIN_VOLUME_TOTAL = int(os.environ.get("QS_MIN_VOLUME_TOTAL", "5000"))
MAX_COMPETITION_INDEX = int(os.environ.get("QS_MAX_COMPETITION", "75"))
MAX_ACQ_COST_PCT = float(os.environ.get("QS_MAX_ACQ_COST_PCT", "40"))
ASSUMED_CONV_RATE = float(os.environ.get("QS_ASSUMED_CONV_RATE", "0.02"))  # 2% e-com senior

# 5 marchés cibles Silver Economy (Benelux agrégé)
DEFAULT_MULTI_MARKETS = os.environ.get(
    "QS_MULTI_MARKETS", "FR,DE,BNL,CH,UK"
).split(",")

# Agrégations : un code virtuel qui combine plusieurs vrais marchés.
# Le scan exécute chaque sous-marché séparément puis merge les métriques.
MARKET_AGGREGATES = {
    "BNL": {
        "name": "Benelux",
        "members": ["BE", "NL", "LU"],
    },
}


# ============== CLAUDE : variantes + prix concurrents ============== #
_SYSTEM_PROMPT = """Tu es un expert senior en e-commerce européen pour la Silver Economy \
(60+ ans). Ta mission : aider un Concepteur à décider s'il doit lancer un site \
e-commerce spécialisé sur un produit. Sois factuel, français, pragmatique. JSON strict uniquement."""

_USER_TEMPLATE = """Produit / niche à évaluer : **{product}**
Pays cible : **{country_name}**

Renvoie EXACTEMENT ce JSON (pas de markdown, pas de commentaire) :

{{
  "keyword_variants": ["kw1", "kw2", "kw3", "kw4", "kw5"],
  "avg_price_eur": {{"min": <int>, "median": <int>, "max": <int>}},
  "market_trend": "growing" | "stable" | "declining",
  "is_saturated": true | false,
  "red_flags": ["<string>", ...],
  "top_competitors": ["<domain.tld>", ...],
  "regulatory_notes": "<1 phrase si réglementation spéciale, sinon ''>",
  "estimated_keyword_metrics": [
    {{"keyword": "<kw>", "volume_monthly": <int>, "cpc_eur": <float>, "competition_index": <int 0-100>}},
    ... 6 items (produit principal + 5 variantes)
  ]
}}

Règles :
- keyword_variants : 5 requêtes de recherche français (ou langue du pays) que \
cible un client final qui veut ACHETER ce produit. Vraies formulations \
d'acheteurs 60+, pas du keyword stuffing. Pas de modificateurs ("pas cher", \
"promo"). Exemples : pour "fauteuil releveur électrique" → ["fauteuil releveur", \
"fauteuil électrique senior", "fauteuil médicalisé", "fauteuil relaxation \
personne âgée", "fauteuil massant senior"].
- avg_price_eur : prix public TTC pratiqué chez les concurrents principaux \
dans le pays. Fourchette réaliste. Pour "fauteuil releveur" en France : \
min 600, median 1200, max 2500.
- market_trend : tendance 12 mois du marché.
- is_saturated : true si + de 10 gros acteurs établis dominent la SERP.
- red_flags : max 3 alertes critiques. Exemples : "dispositif médical, remboursement Sécu complexe", "marque \
Amazon domine à >50% PDM", "tendance baissière -30% sur 3 ans".
- top_competitors : 3-5 domaines que le Concepteur va devoir affronter.
- regulatory_notes : "" si rien, sinon la mention clé (ex: "dispositif médical \
classe I, marquage CE requis").
- estimated_keyword_metrics : estime les volumes mensuels Google et CPC de chaque \
mot-clé (produit + 5 variantes). Utilise ta connaissance du marché FR/EU pour la \
Silver Economy. competition_index 0-100 (0=facile, 100=saturé). Valeurs de \
fallback si l'API Google n'est pas disponible."""


def _strip_json(raw: str) -> str:
    """Tolère ```json ... ``` wrapping."""
    s = (raw or "").strip()
    s = re.sub(r"^```(?:json)?\s*", "", s)
    s = re.sub(r"\s*```\s*$", "", s)
    return s.strip()


async def _claude_analysis(product: str, country_name: str) -> dict:
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    user_prompt = _USER_TEMPLATE.format(product=product, country_name=country_name)
    chat = (
        LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"quickscan-{uuid.uuid4().hex[:8]}",
            system_message=_SYSTEM_PROMPT,
        )
        .with_model("anthropic", "claude-sonnet-4-5-20250929")
    )
    try:
        raw = await asyncio.wait_for(
            chat.send_message(UserMessage(text=user_prompt)),
            timeout=45,
        )
    except asyncio.TimeoutError:
        raise HTTPException(504, "L'IA a mis trop de temps. Réessaye.")
    except Exception as e:
        logger.exception("Claude quickscan call failed")
        raise HTTPException(502, f"IA indisponible : {str(e)[:180]}")
    raw_text = raw if isinstance(raw, str) else str(raw)
    try:
        return json.loads(_strip_json(raw_text))
    except json.JSONDecodeError:
        logger.error(f"QuickScan bad JSON: {raw_text[:400]}")
        raise HTTPException(502, "IA a retourné un format invalide, réessaye.")


# ============== GOOGLE ADS : volumes réels ============== #
async def _fetch_google_volumes(seed_keywords: list[str], country: str) -> list[dict]:
    """Appelle shared_keyword_ideas en interne (réutilise le router Google Ads).
    Retourne la liste des ideas avec volumes/cpc/competition.
    """
    from routes.google_ads import (
        _get_platform_client, MARKETS,
    )
    market = MARKETS.get(country.upper())
    if not market:
        raise HTTPException(400, f"Pays non supporté : {country}")
    seeds = [s for s in seed_keywords if s and s.strip()][:10]
    if not seeds:
        return []

    client, customer_id = await _get_platform_client()
    if not client or not customer_id:
        logger.warning("Google Ads non connecté — quickscan sans volumes réels")
        return []

    def _call():
        svc = client.get_service("KeywordPlanIdeaService")
        req = client.get_type("GenerateKeywordIdeasRequest")
        req.customer_id = customer_id
        req.language = f"languageConstants/{market['lang']}"
        req.geo_target_constants.append(f"geoTargetConstants/{market['geo']}")
        req.include_adult_keywords = False
        req.keyword_plan_network = client.enums.KeywordPlanNetworkEnum.GOOGLE_SEARCH
        seed_obj = client.get_type("KeywordSeed")
        seed_obj.keywords.extend(seeds)
        req.keyword_seed = seed_obj
        response = svc.generate_keyword_ideas(request=req)
        out = []
        for idea in response:
            m = idea.keyword_idea_metrics
            out.append({
                "keyword": idea.text,
                "volume": int(m.avg_monthly_searches or 0),
                "cpc_low_eur": round((m.low_top_of_page_bid_micros or 0) / 1_000_000, 2),
                "cpc_high_eur": round((m.high_top_of_page_bid_micros or 0) / 1_000_000, 2),
                "competition_index": int(m.competition_index or 0),
            })
            if len(out) >= 100:
                break
        out.sort(key=lambda x: x["volume"], reverse=True)
        return out

    try:
        return await asyncio.to_thread(_call)
    except Exception as e:
        logger.exception(f"Google Ads quickscan failed: {e}")
        return []


# ============== SCORING ============== #
def _compute_verdict(metrics: dict, insights: dict) -> dict:
    """Calcule le verdict GO / GO_WITH_RESERVE / NO_GO + score + checklist."""
    avg_price = float(metrics["avg_price_median"])
    volume = int(metrics["volume_total"])
    competition = int(metrics["competition_weighted"])
    cpc = float(metrics["cpc_weighted_eur"])
    estimated_cpa = cpc / ASSUMED_CONV_RATE if cpc > 0 else 0
    acq_pct = (estimated_cpa / avg_price * 100) if avg_price > 0 else 999
    metrics["estimated_cpa_eur"] = round(estimated_cpa, 2)
    metrics["acq_cost_pct"] = round(acq_pct, 1)

    checklist = [
        {
            "label": f"Prix moyen ≥ {MIN_PRICE_EUR:.0f}€",
            "value": f"{avg_price:.0f}€",
            "status": "pass" if avg_price >= MIN_PRICE_EUR else "fail",
            "required": True,
        },
        {
            "label": f"Volume total ≥ {MIN_VOLUME_TOTAL}/mois",
            "value": f"{volume:,}".replace(",", " "),
            "status": "pass" if volume >= MIN_VOLUME_TOTAL else "fail",
            "required": True,
        },
        {
            "label": f"Concurrence Google ≤ {MAX_COMPETITION_INDEX}/100",
            "value": f"{competition}/100",
            "status": "pass" if competition <= MAX_COMPETITION_INDEX else "warn",
            "required": False,  # soft constraint : warn only
        },
        {
            "label": f"Coût acquisition Ads ≤ {MAX_ACQ_COST_PCT:.0f}% du prix",
            "value": f"{acq_pct:.0f}% (CPA ~{estimated_cpa:.0f}€)",
            "status": "pass" if acq_pct <= MAX_ACQ_COST_PCT else "fail",
            "required": True,
        },
    ]
    # Red flags (bloquants complémentaires)
    red_flags = []
    if insights.get("market_trend") == "declining":
        red_flags.append("Marché en déclin sur 12 mois")
    if insights.get("is_saturated"):
        red_flags.append("Niche saturée (>10 gros acteurs)")
    for rf in (insights.get("red_flags") or [])[:3]:
        if rf:
            red_flags.append(rf)

    required_failures = [c for c in checklist if c["required"] and c["status"] == "fail"]
    hard_fail = (
        len(required_failures) > 0
        or insights.get("market_trend") == "declining"
        or insights.get("is_saturated")
    )
    competition_warn = competition > MAX_COMPETITION_INDEX

    # Score 0-100 (concurrence pèse moins car déjà soft)
    score = 0
    if avg_price >= 100:
        score += 25
    elif avg_price >= MIN_PRICE_EUR:
        score += 15
    if volume >= 20000:
        score += 30
    elif volume >= MIN_VOLUME_TOTAL:
        score += 20
    if competition <= 33:
        score += 20
    elif competition <= MAX_COMPETITION_INDEX:
        score += 15
    elif competition <= 85:
        score += 8
    if acq_pct <= 25:
        score += 25
    elif acq_pct <= MAX_ACQ_COST_PCT:
        score += 15

    # Verdict
    if hard_fail:
        verdict = "NO_GO"
    elif competition_warn:
        verdict = "GO_WITH_RESERVE"
        red_flags.insert(0, "Concurrence très élevée (>75/100) — coût Ads pénalisant")
    elif score >= 75:
        verdict = "GO"
    else:
        verdict = "GO_WITH_RESERVE"

    # Reason + recommendation
    if verdict == "GO":
        reason = f"Niche robuste : volume {volume:,}/mois, prix moyen {avg_price:.0f}€, concurrence {competition}/100, CPA estimé {estimated_cpa:.0f}€ ({acq_pct:.0f}% du prix).".replace(",", " ")
        recommendation = "Lance-toi. Configure un budget Ads à 30€/jour pour démarrer et vise un ROAS > 2 sur les 30 premiers jours."
    elif verdict == "GO_WITH_RESERVE" and competition_warn and not hard_fail:
        reason = f"Tous les fondamentaux sont au vert sauf la concurrence : **{competition}/100** (seuil {MAX_COMPETITION_INDEX})."
        recommendation = "GO possible mais **concurrence très élevée** : prévois un budget Ads 2× plus gros que sur un marché normal (60-80€/jour) et travaille le SEO/brand sur 6 mois minimum pour ne pas dépendre à 100% des enchères."
    elif verdict == "GO_WITH_RESERVE":
        weakest = min(checklist, key=lambda c: 0 if c["status"] != "pass" else 1)
        reason = f"Opportunité correcte mais un critère est tendu : **{weakest['label']}** à {weakest['value']}."
        recommendation = "Teste avec un budget réduit (15€/jour max) pendant 14 jours. Si CPA réel dépasse tes simulations, pivote."
    else:
        if required_failures:
            rf0 = required_failures[0]
            reason = f"Critère bloquant : **{rf0['label']}** à {rf0['value']}."
        elif insights.get("market_trend") == "declining":
            reason = "Marché en déclin : le volume et la marge vont s'éroder."
        elif insights.get("is_saturated"):
            reason = "Niche saturée : tu vas payer les Ads trop cher face aux acteurs établis."
        else:
            reason = "Plusieurs signaux négatifs s'accumulent."
        recommendation = "Cherche une autre niche. Affine ton idée (sous-catégorie, géographie, positionnement premium) et relance un scan."

    return {
        "verdict": verdict,
        "score": score,
        "reason": reason,
        "recommendation": recommendation,
        "checklist": checklist,
        "red_flags": red_flags,
        "competition_high": competition_warn,
    }


# ============== ROUTES ============== #
class QuickScanInput(BaseModel):
    product_or_niche: str = Field(..., min_length=3, max_length=120)
    country: str = Field("FR", min_length=2, max_length=2)


class MultiScanInput(BaseModel):
    product_or_niche: str = Field(..., min_length=3, max_length=120)
    countries: Optional[list[str]] = None  # if None, uses DEFAULT_MULTI_MARKETS


async def _run_single_scan(product: str, country: str, user_id: Optional[str]) -> dict:
    """Core scan logic — used by both single and multi-market endpoints.

    Supports real market codes (FR, DE, BE, …) and aggregate codes
    (BNL = Benelux) which are fanned out in parallel and merged.
    """
    cc = country.upper()

    # ----- aggregate market? fan out to members and merge -----
    if cc in MARKET_AGGREGATES:
        agg = MARKET_AGGREGATES[cc]
        members = agg["members"]
        sub_results = await asyncio.gather(
            *(_run_single_scan(product, m, user_id) for m in members),
            return_exceptions=True,
        )
        # Filter exceptions (treat as missing data for that sub-market)
        ok = [r for r in sub_results if isinstance(r, dict)]
        if not ok:
            raise HTTPException(500, "Aucun sous-marché Benelux n'a répondu.")

        # Merge keyword metrics: sum volumes, weighted avg competition+cpc, take median price avg
        keywords_by_kw: dict[str, dict] = {}
        for r in ok:
            for k in r.get("keywords", []):
                kw = k.get("keyword", "").strip().lower()
                if not kw:
                    continue
                entry = keywords_by_kw.setdefault(kw, {
                    "keyword": k["keyword"],
                    "volume": 0,
                    "cpc_low_eur": 0.0,
                    "cpc_high_eur": 0.0,
                    "competition_index": 0,
                    "_vol_for_avg": 0,
                })
                v = int(k.get("volume") or 0)
                entry["volume"] += v
                entry["_vol_for_avg"] += v
                entry["cpc_low_eur"] += float(k.get("cpc_low_eur") or 0) * max(v, 1)
                entry["cpc_high_eur"] += float(k.get("cpc_high_eur") or 0) * max(v, 1)
                entry["competition_index"] += int(k.get("competition_index") or 0) * max(v, 1)

        merged_keywords = []
        for entry in keywords_by_kw.values():
            w = max(entry["_vol_for_avg"], 1)
            merged_keywords.append({
                "keyword": entry["keyword"],
                "volume": entry["volume"],
                "cpc_low_eur": round(entry["cpc_low_eur"] / w, 2),
                "cpc_high_eur": round(entry["cpc_high_eur"] / w, 2),
                "competition_index": round(entry["competition_index"] / w),
            })
        merged_keywords.sort(key=lambda k: k["volume"], reverse=True)

        # Aggregate top-level metrics
        vol_total = sum((r.get("metrics") or {}).get("volume_total", 0) for r in ok)
        if vol_total > 0:
            competition_weighted = round(
                sum((r.get("metrics") or {}).get("competition_weighted", 0) *
                    (r.get("metrics") or {}).get("volume_total", 0) for r in ok)
                / vol_total
            )
            cpc_weighted = round(
                sum((r.get("metrics") or {}).get("cpc_weighted_eur", 0) *
                    (r.get("metrics") or {}).get("volume_total", 0) for r in ok)
                / vol_total, 2,
            )
        else:
            competition_weighted = 0
            cpc_weighted = 0.0
        # Price stats → take median of medians (simple, fair enough at Benelux scope)
        price_medians = [(r.get("metrics") or {}).get("avg_price_median", 0) for r in ok]
        price_medians = [p for p in price_medians if p]
        price_median = sorted(price_medians)[len(price_medians) // 2] if price_medians else 0.0
        price_mins = [(r.get("metrics") or {}).get("avg_price_min", 0) for r in ok if (r.get("metrics") or {}).get("avg_price_min")]
        price_maxs = [(r.get("metrics") or {}).get("avg_price_max", 0) for r in ok if (r.get("metrics") or {}).get("avg_price_max")]

        metrics = {
            "avg_price_median": price_median,
            "avg_price_min": min(price_mins) if price_mins else 0.0,
            "avg_price_max": max(price_maxs) if price_maxs else 0.0,
            "volume_total": vol_total,
            "competition_weighted": competition_weighted,
            "cpc_weighted_eur": cpc_weighted,
        }

        # Use the first ok sub-scan's insights as a proxy (for red flags, checklist, etc.),
        # but recompute verdict on aggregated metrics. Red flags are de-duped across members.
        insights_proxy = {
            "red_flags": list({rf for r in ok for rf in (r.get("red_flags") or [])})[:3],
        }
        verdict_data = _compute_verdict(metrics, insights_proxy)
        # Sub-member verdicts summary (for the UI to show per-country)
        by_member = {r["country"]: {
            "name": r.get("country_name"),
            "verdict": r.get("verdict"),
            "score": r.get("score"),
            "volume_total": (r.get("metrics") or {}).get("volume_total", 0),
        } for r in ok}

        return {
            "id": f"qs-{uuid.uuid4().hex[:12]}",
            "product_or_niche": product,
            "country": cc,
            "country_name": agg["name"],
            "is_aggregate": True,
            "aggregate_members": by_member,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "created_by": user_id,
            "metrics": metrics,
            "verdict": verdict_data["verdict"],
            "score": verdict_data["score"],
            "reason": verdict_data["reason"],
            "recommendation": verdict_data["recommendation"],
            "checklist": verdict_data["checklist"],
            "red_flags": verdict_data["red_flags"],
            "competition_high": verdict_data.get("competition_high", False),
            "keywords": merged_keywords[:4],
        }

    # ----- real country code below -----
    from routes.google_ads import MARKETS
    market = MARKETS.get(cc)
    if not market:
        raise HTTPException(400, f"Pays non supporté : {country}")
    country_name = market["name"]

    # Étape 1 — Claude
    insights = await _claude_analysis(product, country_name)
    variants = insights.get("keyword_variants") or []
    avg_price = insights.get("avg_price_eur") or {}
    price_median = float(avg_price.get("median") or 0)

    # Étape 2 — Google Ads
    seeds = [product] + list(variants)
    ideas = await _fetch_google_volumes(seeds, country)
    data_source = "google_ads" if ideas else "claude_estimate"

    # Fallback Claude estimates
    if not ideas:
        est = insights.get("estimated_keyword_metrics") or []
        ideas = []
        for e in est:
            cpc = float(e.get("cpc_eur") or 0)
            ideas.append({
                "keyword": e.get("keyword", ""),
                "volume": int(e.get("volume_monthly") or 0),
                "cpc_low_eur": round(cpc * 0.7, 2),
                "cpc_high_eur": round(cpc * 1.3, 2),
                "competition_index": int(e.get("competition_index") or 0),
            })
        ideas.sort(key=lambda x: x["volume"], reverse=True)

    # Primary + top 3 variants
    primary = None
    for idea in ideas:
        if idea["keyword"].lower().strip() == product.lower().strip():
            primary = idea
            break
    if primary is None and ideas:
        primary = ideas[0]
    others = [i for i in ideas if i is not primary][:3]
    top4 = ([primary] if primary else []) + others

    if top4:
        volume_total = sum(i["volume"] for i in top4)
        total_vol_safe = max(volume_total, 1)
        competition_weighted = round(
            sum(i["competition_index"] * i["volume"] for i in top4) / total_vol_safe
        )
        cpc_weighted = round(
            sum(((i["cpc_low_eur"] + i["cpc_high_eur"]) / 2) * i["volume"] for i in top4) / total_vol_safe,
            2,
        )
    else:
        volume_total = 0
        competition_weighted = 0
        cpc_weighted = 0.0

    metrics = {
        "avg_price_median": price_median,
        "avg_price_min": float(avg_price.get("min") or 0),
        "avg_price_max": float(avg_price.get("max") or 0),
        "volume_total": volume_total,
        "competition_weighted": competition_weighted,
        "cpc_weighted_eur": cpc_weighted,
    }
    verdict_data = _compute_verdict(metrics, insights)

    return {
        "id": f"qs-{uuid.uuid4().hex[:12]}",
        "product_or_niche": product,
        "country": country.upper(),
        "country_name": country_name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": user_id,
        "metrics": metrics,
        "verdict": verdict_data["verdict"],
        "score": verdict_data["score"],
        "reason": verdict_data["reason"],
        "recommendation": verdict_data["recommendation"],
        "checklist": verdict_data["checklist"],
        "red_flags": verdict_data["red_flags"],
        "competition_high": verdict_data.get("competition_high", False),
        "keywords": [
            {
                "keyword": i["keyword"],
                "volume": i["volume"],
                "cpc_eur": round((i["cpc_low_eur"] + i["cpc_high_eur"]) / 2, 2),
                "competition_index": i["competition_index"],
            }
            for i in top4 + [i for i in ideas if i not in top4][:5]
        ][:10],
        "market": {
            "trend": insights.get("market_trend", "stable"),
            "is_saturated": bool(insights.get("is_saturated")),
            "top_competitors": insights.get("top_competitors", [])[:5],
            "regulatory_notes": insights.get("regulatory_notes", ""),
        },
        "google_ads_connected": data_source == "google_ads",
        "data_source": data_source,
        "thresholds": {
            "min_price_eur": MIN_PRICE_EUR,
            "min_volume_total": MIN_VOLUME_TOTAL,
            "max_competition_index": MAX_COMPETITION_INDEX,
            "max_acq_cost_pct": MAX_ACQ_COST_PCT,
            "assumed_conv_rate": ASSUMED_CONV_RATE,
        },
    }


@router.post("/quick-scan")
async def run_quick_scan(data: QuickScanInput, user: dict = Depends(get_current_user)):
    """Lance un scan Go/No-Go sur 1 marché."""
    result = await _run_single_scan(
        data.product_or_niche.strip(),
        data.country,
        user.get("id"),
    )
    await db.quick_scans.insert_one(dict(result))
    return result


@router.post("/quick-scan/multi")
async def run_multi_market_scan(
    data: MultiScanInput,
    user: dict = Depends(get_current_user),
):
    """Démarre un scan Go/No-Go en arrière-plan sur 5 marchés (FR/DE/BNL/CH/UK).

    Le code "BNL" est un agrégat Benelux (BE + NL + LU) exécuté en parallèle
    puis mergé dans un seul résultat.

    Retourne immédiatement `{group_id, status: "running"}` — le frontend doit
    ensuite poller `GET /quick-scan/multi/{group_id}` toutes les 2-3s pour voir
    les résultats apparaître au fur et à mesure (chaque marché ~10-15s).
    """
    product = data.product_or_niche.strip()
    countries = [c.upper().strip() for c in (data.countries or DEFAULT_MULTI_MARKETS) if c.strip()]
    countries = list(dict.fromkeys(countries))[:8]
    group_id = f"mg-{uuid.uuid4().hex[:12]}"
    now_iso = datetime.now(timezone.utc).isoformat()

    # Create the group record
    await db.quick_scan_groups.insert_one({
        "id": group_id,
        "product_or_niche": product,
        "countries": countries,
        "created_at": now_iso,
        "created_by": user.get("id"),
        "status": "running",
        "progress": {"done": 0, "total": len(countries)},
    })

    # Fire background tasks for each country (do not await)
    async def _worker(cc: str):
        try:
            r = await _run_single_scan(product, cc, user.get("id"))
            r["multi_group_id"] = group_id
            await db.quick_scans.insert_one(dict(r))
        except HTTPException as e:
            await db.quick_scans.insert_one({
                "id": f"qs-err-{uuid.uuid4().hex[:8]}",
                "country": cc,
                "product_or_niche": product,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "created_by": user.get("id"),
                "multi_group_id": group_id,
                "verdict": "ERROR",
                "error": e.detail,
            })
        except Exception as e:
            logger.exception(f"multi-scan worker failed for {cc}")
            await db.quick_scans.insert_one({
                "id": f"qs-err-{uuid.uuid4().hex[:8]}",
                "country": cc,
                "product_or_niche": product,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "created_by": user.get("id"),
                "multi_group_id": group_id,
                "verdict": "ERROR",
                "error": str(e)[:200],
            })
        finally:
            await db.quick_scan_groups.update_one(
                {"id": group_id},
                {"$inc": {"progress.done": 1}},
            )
            grp = await db.quick_scan_groups.find_one({"id": group_id}, {"_id": 0})
            if grp and grp["progress"]["done"] >= grp["progress"]["total"]:
                await db.quick_scan_groups.update_one(
                    {"id": group_id},
                    {"$set": {
                        "status": "done",
                        "completed_at": datetime.now(timezone.utc).isoformat(),
                    }},
                )

    for cc in countries:
        asyncio.create_task(_worker(cc))

    return {
        "group_id": group_id,
        "status": "running",
        "product_or_niche": product,
        "countries": countries,
        "created_at": now_iso,
    }


@router.get("/quick-scan/multi/{group_id}")
async def get_multi_scan_status(
    group_id: str,
    user: dict = Depends(get_current_user),
):
    """Retourne l'état + résultats partiels d'un scan multi-marché."""
    group = await db.quick_scan_groups.find_one({"id": group_id}, {"_id": 0})
    if not group:
        raise HTTPException(404, "Groupe introuvable.")
    if user.get("role") != "admin" and group.get("created_by") != user.get("id"):
        raise HTTPException(403, "Pas autorisé.")

    scans = await db.quick_scans.find(
        {"multi_group_id": group_id}, {"_id": 0}
    ).to_list(100)

    # Sort same way as before
    order = {"GO": 0, "GO_WITH_RESERVE": 1, "NO_GO": 2, "ERROR": 3}
    scans.sort(key=lambda r: (order.get(r.get("verdict"), 9), -(r.get("score") or 0)))

    return {
        "group_id": group_id,
        "product_or_niche": group.get("product_or_niche"),
        "countries": group.get("countries", []),
        "status": group.get("status", "running"),
        "progress": group.get("progress", {"done": len(scans), "total": len(group.get("countries", []))}),
        "created_at": group.get("created_at"),
        "completed_at": group.get("completed_at"),
        "results": scans,
        "summary": {
            "go": sum(1 for r in scans if r.get("verdict") == "GO"),
            "go_with_reserve": sum(1 for r in scans if r.get("verdict") == "GO_WITH_RESERVE"),
            "no_go": sum(1 for r in scans if r.get("verdict") == "NO_GO"),
            "error": sum(1 for r in scans if r.get("verdict") == "ERROR"),
        },
    }


@router.get("/quick-scan/history")
async def list_quick_scans(user: dict = Depends(get_current_user), limit: int = 50):
    """Liste les scans du user (ou tous si admin). Groupe les multi-scans."""
    q = {} if user.get("role") == "admin" else {"created_by": user.get("id")}
    cursor = db.quick_scans.find(q, {"_id": 0}).sort("created_at", -1).limit(limit)
    return {"scans": await cursor.to_list(limit)}
