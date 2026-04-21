"""
Deep Analyzer v2 — Altiora
- Open to ANY e-commerce product (no Silver Economy restriction)
- 5-step deep analysis (2-5 min total)
- Background task with real-time progress tracking
- Native-language keyword expansion per country
"""
from __future__ import annotations
import asyncio
import json
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Optional
from unicodedata import normalize

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from deps import db, get_current_user, EMERGENT_LLM_KEY

router = APIRouter(prefix="/niches")   # route kept for URL-compat with frontend
logger = logging.getLogger("conceptfactory.analyzer")

COUNTRY_LANG = {
    "FR": ("France", "français"),
    "DE": ("Deutschland", "Deutsch"),
    "CH": ("Schweiz/Suisse", "Deutsch + français"),
    "BE": ("Belgique/België", "français + Nederlands"),
    "UK": ("United Kingdom", "English"),
    "NL": ("Nederland", "Nederlands"),
    "IT": ("Italia", "italiano"),
    "ES": ("España", "español"),
}
DEFAULT_COUNTRIES = ["FR", "DE", "CH", "BE", "UK", "NL"]
JSON_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


class AnalyzeInput(BaseModel):
    product: str = Field(..., min_length=2, max_length=200)
    persona: Optional[str] = Field("tout_public",
        description="senior | millennial | famille | pro | tout_public")
    countries: Optional[list[str]] = None
    notes: Optional[str] = ""


def _strip(t: str) -> str:
    return JSON_FENCE.sub("", t).strip()


def _slug(s: str) -> str:
    n = normalize("NFKD", s or "").encode("ascii", "ignore").decode("ascii")
    n = re.sub(r"[^a-zA-Z0-9]+", "-", n).strip("-").lower()
    return n[:80] or f"niche-{uuid.uuid4().hex[:6]}"


async def _claude_json(system: str, user: str, session_id: str, timeout: int = 120) -> dict:
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=session_id, system_message=system)\
        .with_model("anthropic", "claude-sonnet-4-5-20250929")
    try:
        raw = await asyncio.wait_for(chat.send_message(UserMessage(text=user)), timeout=timeout)
    except asyncio.TimeoutError:
        raise RuntimeError(f"LLM timeout after {timeout}s")
    raw = _strip(raw if isinstance(raw, str) else str(raw))
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Last-chance extract: find first { and last }
        i, j = raw.find("{"), raw.rfind("}")
        if i != -1 and j != -1:
            try:
                return json.loads(raw[i:j + 1])
            except Exception:
                pass
        raise RuntimeError(f"Invalid JSON from LLM: {raw[:300]}")


# ================== PROMPTS ================== #

SYSTEM = """Tu es un consultant expert en études de marché e-commerce international.
Tu analyses des produits pour des lancements multi-pays EU.
Tu bases tes estimations sur : Google Keyword Planner, Ahrefs, SEMrush, SimilarWeb, Amazon Bestsellers.
Tu réponds UNIQUEMENT en JSON valide strict, sans markdown."""

STEP1_PROMPT = """# Étape 1/5 — EXPANSION KEYWORDS MULTI-LANGUES

Produit : {product}
Persona cible : {persona}
Pays : {countries}

Pour CHAQUE pays ci-dessus, génère 20-30 mots-clés en **langue native** :
- 8-10 mots-clés transactionnels (intent achat immédiat)
- 8-10 mots-clés informatifs (comparatifs, guides)
- 4-5 mots-clés longue traîne (4+ mots, faible concurrence)
- Prends en compte : traduction CORRECTE (pas littérale), argot local, synonymes usuels

Également identifie :
- Le **produit générique** (nom commun en FR) et sa catégorie e-commerce précise
- 3 variantes de produit probables (ex: taille, matériau, usage)

Schéma JSON strict :
{{
  "product_canonical": "nom standardisé du produit",
  "category": "catégorie e-commerce précise (ex: Mobilier > Salon > Canapés convertibles)",
  "variants": ["variante 1", "variante 2", "variante 3"],
  "keywords_by_country": {{
    "FR": {{
      "transactional": ["mot1", "mot2", ...],
      "informational": ["mot1", ...],
      "long_tail": ["phrase longue", ...]
    }},
    "DE": {{...}}, ...
  }}
}}"""


STEP2_PROMPT = """# Étape 2/5 — SIZING MARCHÉ PAR PAYS

Produit : {product}
Catégorie : {category}
Persona : {persona}

Pour CHAQUE pays ({countries}), estime en te basant sur Google Keyword Planner, Ahrefs, SimilarWeb :

1. **Volume mensuel** (somme des volumes mensuels des 10 mots-clés transactionnels les plus forts)
2. **CPC moyen** (€) pour Google Ads sur ce produit
3. **Keyword Difficulty** SEO (0-100)
4. **Panier moyen estimé** (€) par pays (le pouvoir d'achat varie énormément)
5. **Saisonnalité** : "Stable" | "Pic hiver" | "Pic été" | "Pic rentrée" | "Pic fêtes"
6. **Taille du marché** total (€/an) pour cette catégorie dans ce pays
7. **Croissance** estimée sur 3 ans ("+X%/an")
8. **Taux de pénétration** e-commerce (% des achats catégorie qui se font en ligne)

Mots-clés de référence à utiliser :
{keywords}

Schéma JSON strict :
{{
  "country_sizing": {{
    "FR": {{
      "monthly_search_volume": 12500,
      "cpc_avg_eur": 0.85,
      "kd": 34,
      "aov_eur": 280,
      "seasonality": "Pic hiver",
      "market_size_annual_eur": 48000000,
      "growth_3y_pct": 12,
      "ecommerce_penetration_pct": 45,
      "commentary": "2-3 phrases d'analyse"
    }},
    "DE": {{...}}, ...
  }}
}}"""


STEP3_PROMPT = """# Étape 3/5 — ANALYSE CONCURRENTIELLE PAR PAYS

Produit : {product}
Catégorie : {category}

Pour CHAQUE pays ({countries}), liste 5-8 concurrents que tu identifies **réellement présents dans le top 10 Google pour ce produit** (basés sur ta connaissance réelle du marché).

Pour chaque concurrent :
- **Nom** (marque/site)
- **URL estimée**
- **Type** : "marketplace" | "DNVB" | "marque historique" | "dropshipper"
- **Fourchette de prix** sur ce produit en €
- **Force principale**
- **Faiblesse exploitable**
- **Part de marché estimée** (%) sur ce segment

Déduis une **matrice de positionnement** : les 2 axes sur lesquels se différencier (ex: prix/premium, fonctionnalités/simplicité).

Schéma JSON strict :
{{
  "competitors_by_country": {{
    "FR": [
      {{"name":"...", "url":"...", "type":"marketplace", "price_range":"120-180€", "strength":"...", "weakness":"...", "market_share_pct": 12}}
    ],
    "DE": [...], ...
  }},
  "positioning_matrix": {{
    "axis_x": "Prix (entrée <> premium)",
    "axis_y": "Usage (généraliste <> spécialisé)",
    "white_space": "Description du positionnement qui n'est PAS occupé par la concurrence"
  }}
}}"""


STEP4_PROMPT = """# Étape 4/5 — CADRE LÉGAL & OPÉRATIONNEL PAR PAYS

Produit : {product}
Catégorie : {category}

Pour CHAQUE pays ({countries}), liste les contraintes réelles :

1. **Certifications obligatoires** (CE, NF, DIN, BSI, ISO…) — en précisant lesquelles
2. **Mentions légales obligatoires** sur fiche produit (recyclage, origine, etc.)
3. **TVA standard** (%)
4. **Droits de douane** si import hors UE
5. **Transporteurs locaux à privilégier** (ex: DPD FR, DHL DE, Royal Mail UK)
6. **Délai de livraison attendu** (en jours)
7. **Langue du SAV** obligatoire
8. **Réglementation particulière** (ex: DEEE, garantie légale, cooling-off)
9. **Modes de paiement préférés** (CB majoritaire en FR, SOFORT en DE, iDEAL en NL, etc.)

Schéma JSON strict :
{{
  "legal_ops_by_country": {{
    "FR": {{
      "mandatory_certifications": ["CE", "NF EN 13234"],
      "mandatory_mentions": ["DEEE", "mention recyclage"],
      "vat_pct": 20,
      "customs_duty_pct_outside_eu": 5.5,
      "preferred_carriers": ["Colissimo", "DPD", "Chronopost"],
      "expected_delivery_days": 3,
      "support_language": "français",
      "specific_regulations": ["Garantie légale 2 ans", "Rétractation 14j"],
      "preferred_payment_methods": ["CB", "PayPal", "Virement"]
    }}
  }}
}}"""


STEP5_PROMPT = """# Étape 5/5 — SYNTHÈSE STRATÉGIQUE & VERDICT

Produit : {product}
Persona : {persona}

Tu as maintenant toutes les données suivantes sur les pays {countries} :
- Sizing : {sizing}
- Concurrence : {competitors_summary}
- Cadre légal : {legal_summary}

Produis la synthèse finale :

1. **Verdict par pays** basé sur des règles strictes :
   - GO : volume ≥ 5000 ET aov_eur ≥ 80 ET CPC raisonnable (<10% AOV) ET concurrence pas saturée
   - MAYBE : volume 2000-5000 OU concurrence forte mais white space clair
   - NOGO : volume < 2000 OU réglementation bloquante OU CPC > 15% AOV
2. **Verdict global** : GO si ≥ 2 pays GO, MAYBE si 1 pays GO, NOGO sinon
3. **Stratégie de lancement recommandée** : ordre de priorité des pays avec justification
4. **Prix de vente recommandé** par pays (en € TTC)
5. **Prix d'achat cible** (pour garder ≥ 55% de marge HT)
6. **Fournisseurs suggérés** (CJ Dropshipping, BigBuy, AliExpress, Alibaba, locaux)
7. **Score ECF global** (0-100) basé sur somme pondérée volume/marge/concurrence
8. **Tagline marketing** en FR (8-15 mots, ton adapté persona)
9. **Risques principaux** (3-4)
10. **Opportunités de différenciation** (3-4)

Schéma JSON strict :
{{
  "name": "Nom produit standardisé",
  "slug": "kebab-case",
  "emoji": "un emoji",
  "category": "catégorie",
  "tagline": "...",
  "description": "2-3 phrases produit",
  "persona": "{persona}",

  "country_verdicts": {{
    "FR": {{"verdict": "GO", "reasoning": "Volume 12500/mois, AOV 280€, CPC 0.85€ = 0.3% AOV, concurrence fragmentée"}},
    "DE": {{...}}, ...
  }},

  "overall_verdict": "GO",
  "verdict_reasoning": "1-2 phrases",

  "launch_strategy": {{
    "priority_order": ["FR","DE","UK"],
    "reasoning": "..."
  }},

  "pricing_by_country": {{
    "FR": {{"sell_ttc_eur": 249, "cost_ht_target_eur": 75, "margin_pct": 63}},
    "DE": {{...}}
  }},

  "suppliers": [
    {{"name":"CJ Dropshipping","relevance":"high","reasoning":"..."}},
    {{"name":"BigBuy","relevance":"medium","reasoning":"..."}},
    {{"name":"AliExpress","relevance":"high","reasoning":"..."}}
  ],

  "ecf_score": 78,
  "hero": true,

  "risks": ["..."],
  "opportunities": ["..."]
}}"""


# ================== Background task orchestrator ================== #

async def _set_progress(job_id: str, step: int, label: str, status: str = "running", error: Optional[str] = None, result: Optional[dict] = None):
    update = {
        "step": step,
        "step_label": label,
        "status": status,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if error:
        update["error"] = error
    if result is not None:
        update["result"] = result
    await db.analysis_jobs.update_one({"id": job_id}, {"$set": update})


async def _run_deep_analysis(job_id: str, user_id: str, product: str, persona: str, countries: list, notes: str):
    try:
        session = f"job-{job_id}"
        ctx = {
            "product": product,
            "persona": persona,
            "countries": ", ".join(f"{c} ({COUNTRY_LANG.get(c, (c, c))[0]})" for c in countries),
        }

        # STEP 1
        await _set_progress(job_id, 1, "Extension keywords multi-langues (30s)")
        step1 = await _claude_json(SYSTEM, STEP1_PROMPT.format(**ctx), f"{session}-s1", timeout=90)
        ctx["category"] = step1.get("category", "")

        # STEP 1.5 — Google Ads Keyword Planner enrichment (optionnel, non bloquant)
        google_enriched = {"available": False, "by_country": {}, "reason": "not_attempted"}
        try:
            from routes.google_ads import fetch_keyword_volumes
            kw_input = {}
            for c in countries:
                block = (step1.get("keywords_by_country", {}).get(c, {}) or {})
                merged = (block.get("transactional", []) or [])[:10] + (block.get("informational", []) or [])[:5]
                if merged:
                    kw_input[c] = merged
            if kw_input:
                await _set_progress(job_id, 1, "Volumes réels Google Keyword Planner (15s)")
                google_enriched = await fetch_keyword_volumes(kw_input)
        except Exception as e:
            logger.warning(f"[analyzer] google enrichment skipped: {e}")
            google_enriched = {"available": False, "by_country": {}, "reason": str(e)[:120]}

        # STEP 2
        kws_short = json.dumps({c: (step1.get("keywords_by_country", {}).get(c, {}) or {}).get("transactional", [])[:6] for c in countries}, ensure_ascii=False)[:1500]
        await _set_progress(job_id, 2, "Sizing marché par pays (60s)")
        step2 = await _claude_json(SYSTEM, STEP2_PROMPT.format(**ctx, keywords=kws_short), f"{session}-s2", timeout=120)

        # Override Claude estimations with Google real data where available
        if google_enriched.get("available"):
            country_sizing = step2.get("country_sizing", {}) or {}
            for c, g in google_enriched["by_country"].items():
                if g.get("total_volume_monthly", 0) > 0:
                    csz = country_sizing.get(c) or {}
                    csz["monthly_search_volume"] = g["total_volume_monthly"]
                    if g.get("avg_cpc_eur", 0) > 0:
                        csz["cpc_avg_eur"] = g["avg_cpc_eur"]
                    csz["google_verified"] = True
                    country_sizing[c] = csz
            step2["country_sizing"] = country_sizing

        # STEP 3
        await _set_progress(job_id, 3, "Analyse concurrentielle par pays (60s)")
        step3 = await _claude_json(SYSTEM, STEP3_PROMPT.format(**ctx), f"{session}-s3", timeout=120)

        # STEP 4
        await _set_progress(job_id, 4, "Cadre légal & opérationnel (30s)")
        step4 = await _claude_json(SYSTEM, STEP4_PROMPT.format(**ctx), f"{session}-s4", timeout=90)

        # STEP 5
        sizing_sum = json.dumps(step2.get("country_sizing", {}), ensure_ascii=False)[:2000]
        comp_sum = json.dumps({c: [{"name": x.get("name"), "type": x.get("type"), "price": x.get("price_range")} for x in (step3.get("competitors_by_country", {}).get(c, []) or [])[:4]] for c in countries}, ensure_ascii=False)[:1500]
        legal_sum = json.dumps({c: {"vat": v.get("vat_pct"), "certs": v.get("mandatory_certifications")} for c, v in (step4.get("legal_ops_by_country", {}) or {}).items()}, ensure_ascii=False)[:1000]

        await _set_progress(job_id, 5, "Synthèse stratégique & verdict final (30s)")
        step5 = await _claude_json(
            SYSTEM,
            STEP5_PROMPT.format(**ctx, sizing=sizing_sum, competitors_summary=comp_sum, legal_summary=legal_sum),
            f"{session}-s5", timeout=120,
        )

        # COMPILE
        analysis = {
            **step5,
            "product_canonical": step1.get("product_canonical") or step5.get("name"),
            "variants": step1.get("variants", []),
            "keywords_by_country": step1.get("keywords_by_country", {}),
            "country_sizing": step2.get("country_sizing", {}),
            "competitors_by_country": step3.get("competitors_by_country", {}),
            "positioning_matrix": step3.get("positioning_matrix", {}),
            "legal_ops_by_country": step4.get("legal_ops_by_country", {}),
            "countries": countries,
            "google_keyword_planner": google_enriched,
            "google_verified": bool(google_enriched.get("available")),
        }
        # Aggregates
        sizing = analysis.get("country_sizing", {})
        volumes = [int(s.get("monthly_search_volume", 0) or 0) for s in sizing.values()]
        cpcs = [float(s.get("cpc_avg_eur", 0) or 0) for s in sizing.values()]
        analysis["total_volume_monthly"] = sum(volumes)
        analysis["avg_cpc_eur"] = round(sum(cpcs) / max(len(cpcs), 1), 2)
        analysis["go_countries"] = [c for c, v in (analysis.get("country_verdicts") or {}).items() if v.get("verdict") == "GO"]
        if not analysis.get("slug"):
            analysis["slug"] = _slug(analysis.get("name") or product)

        # Persist full analysis
        analysis_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        await db.niche_analyses.insert_one({
            "id": analysis_id,
            "user_id": user_id,
            "product_input": product,
            "persona": persona,
            "countries_requested": countries,
            "notes": notes,
            "analysis": analysis,
            "source": ("ai_claude_sonnet_4.5_multistep_v2_google_verified"
                       if google_enriched.get("available")
                       else "ai_claude_sonnet_4.5_multistep_v2"),
            "enriched_with_google_ads": bool(google_enriched.get("available")),
            "created_at": now,
            "job_id": job_id,
        })
        await _set_progress(job_id, 5, "Analyse complète ✓", status="completed",
                            result={"analysis_id": analysis_id})
        logger.info(f"[analyzer] Job {job_id} completed — analysis_id {analysis_id}")
    except Exception as e:
        logger.exception(f"[analyzer] Job {job_id} failed")
        await _set_progress(job_id, 0, "Erreur", status="failed", error=str(e)[:500])


# ================== Endpoints ================== #

STEP_LABELS = [
    "Extension keywords multi-langues",
    "Sizing marché par pays",
    "Analyse concurrentielle",
    "Cadre légal & opérationnel",
    "Synthèse stratégique",
]


@router.post("/analyze")
async def analyze_niche(data: AnalyzeInput, bg: BackgroundTasks, user: dict = Depends(get_current_user)):
    """Start a deep analysis job. Returns job_id immediately (poll /analysis-jobs/{id})."""
    countries = [c.upper() for c in (data.countries or DEFAULT_COUNTRIES) if c.upper() in COUNTRY_LANG]
    if not countries:
        countries = DEFAULT_COUNTRIES[:]

    job_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    await db.analysis_jobs.insert_one({
        "id": job_id,
        "user_id": user["id"],
        "product": data.product.strip(),
        "persona": data.persona or "tout_public",
        "countries": countries,
        "notes": data.notes or "",
        "step": 0,
        "step_label": "En attente de démarrage…",
        "steps_total": 5,
        "status": "pending",
        "created_at": now,
        "updated_at": now,
    })
    bg.add_task(_run_deep_analysis, job_id, user["id"], data.product.strip(),
                data.persona or "tout_public", countries, data.notes or "")
    return {"job_id": job_id, "status": "pending", "steps_total": 5, "step_labels": STEP_LABELS}


@router.get("/analysis-jobs/{job_id}")
async def get_job(job_id: str, user: dict = Depends(get_current_user)):
    job = await db.analysis_jobs.find_one({"id": job_id, "user_id": user["id"]}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Job introuvable")
    return job


@router.get("/analyses")
async def list_my_analyses(user: dict = Depends(get_current_user), limit: int = 20):
    items = await db.niche_analyses.find({"user_id": user["id"]}, {"_id": 0})\
        .sort("created_at", -1).limit(limit).to_list(limit)
    for a in items:
        a.pop("notes", None)
        if a.get("analysis"):
            a["analysis_summary"] = {
                "name": a["analysis"].get("name"),
                "emoji": a["analysis"].get("emoji"),
                "category": a["analysis"].get("category"),
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
    a = await db.niche_analyses.find_one({"id": analysis_id, "user_id": user["id"]}, {"_id": 0})
    if not a:
        raise HTTPException(status_code=404, detail="Analyse introuvable")
    return a
