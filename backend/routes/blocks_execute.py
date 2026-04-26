"""
Mega-Block Execute : au lieu d'exécuter les 50 étapes une par une, le Concepteur
peut générer TOUT le livrable d'un bloc (Template, Produits, SEO, Marketing) en 1 clic
via Claude Sonnet 4.5.

4 mega-prompts, un par bloc. Chaque bloc renvoie un livrable structuré JSON adapté :
- template : legal docs, Shopify config, React copy, checkout flow
- products  : top-10 produits recommandés avec sourcing + angles marketing
- seo       : positionnement, voix de marque, 20 titres articles SEO + meta
- marketing : plan Google Ads + Facebook + analytics + KPI cibles

Les outputs sont persistés dans la collection `block_outputs` et exposés à l'UI.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from deps import db, get_current_user, _check_site_access, EMERGENT_LLM_KEY
from seed_prompts import BLOCKS

logger = logging.getLogger("conceptfactory.blocks_execute")
router = APIRouter()


JSON_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def _strip_json_fence(text: str) -> str:
    return JSON_FENCE_RE.sub("", text).strip()


# ============================================================== #
# Mega-prompts : un par bloc, produit un livrable JSON structuré
# ============================================================== #
MEGA_PROMPTS = {
    "template": {
        "system": """Tu es un expert e-commerce senior spécialisé Silver Economy EU (60+ ans).
Tu livres un KIT COMPLET de templates pour lancer une boutique : juridique, Shopify, front React, checkout.
Tu réponds UNIQUEMENT avec du JSON valide (pas de markdown, pas de commentaire).""",
        "user_template": """Niche : {niche}
Pays cibles : {countries}
Nom de la marque : {name}
{extra_context}

Génère le KIT COMPLET "Template & Boutique" selon le schéma JSON suivant :
{{
  "legal_docs": {{
    "cgv": "Texte complet CGV B2C adapté aux pays ciblés (25 articles minimum, ton senior-friendly)",
    "mentions_legales": "Template mentions légales avec placeholders [RAISON_SOCIALE], [SIREN]...",
    "politique_rgpd": "Politique RGPD conforme CNIL/BFDI (2 pages)",
    "cgu_cookies": "Politique cookies + CGU",
    "retractation": "Formulaire de rétractation 14 jours conforme EU"
  }},
  "shopify_config": {{
    "taxes": "Config taxes par pays (FR 20%, DE 19%, BE 21%, NL 21%, UK 20%, CH export)",
    "shipping_zones": ["FR_domestic", "EU_extended", "UK_post_brexit", "CH_import"],
    "payment_methods_per_country": {{"FR": ["CB","Apple Pay","PayPal"], "DE": ["SEPA","Klarna","PayPal"], "NL": ["iDEAL","Klarna"]}},
    "apps_essentielles": ["DSers","Judge.me","Klaviyo","Shopify Flow","ReConvert"],
    "checkout_settings": "Config checkout detailed step by step"
  }},
  "react_storefront": {{
    "home_hero": "Headline + sous-headline + CTA home page, ton rassurant senior",
    "about_page": "Page À propos 400 mots, ton humain, focus confiance",
    "faq_10": [{{"q":"Livraison","a":"Réponse détaillée"}}],
    "footer_links": ["Qui sommes-nous","CGV","RGPD","Contact","Livraison","Retours"]
  }},
  "sav_setup": {{
    "email_templates": {{
      "confirmation_commande": "Template email confirmation FR",
      "expedition": "Template email expédition",
      "remboursement": "Template email remboursement",
      "insatisfaction": "Template de réponse SAV empathique"
    }},
    "policies": "Politique retours 30j, remboursement sous 14j, guarantie 2 ans",
    "sla": "SLA réponse SAV : 24h ouvrables, cible 4h"
  }},
  "logistics": {{
    "carriers_per_country": {{"FR": "Colissimo","DE": "DHL","UK": "Royal Mail"}},
    "fulfillment_flow": "Workflow dropshipping : commande → fournisseur → tracking auto → client",
    "returns_process": "Process retours simplifié"
  }},
  "checklist_lancement": ["20 items précis à valider avant d'ouvrir la boutique"]
}}

Sois concret, chiffré, adapté Silver Economy EU. Aucun placeholder non rempli."""
    },

    "products": {
        "system": """Tu es expert product research e-commerce Silver Economy. Tu sélectionnes les produits GAGNANTS
(marge >65%, volume Google >2000/mois, CPC <1€, panier >40€, conforme import EU, non MDR).
Tu réponds UNIQUEMENT avec du JSON valide.""",
        "user_template": """Niche : {niche}
Pays cibles : {countries}
Marque : {name}
{extra_context}

Génère la SHORTLIST "Produits & Sourcing" selon ce schéma JSON :
{{
  "top_10_produits": [
    {{
      "rank": 1,
      "nom_commercial_fr": "Nom rassurant senior-first",
      "nom_en": "English name",
      "kw_principal": "mot-clé Google principal",
      "volume_recherche_mensuel": 3200,
      "cpc_eur": 0.75,
      "kd_100": 34,
      "prix_achat_eur": [25, 45],
      "prix_vente_recommande_eur": 129,
      "marge_brute_pct": 68,
      "aov_estime_eur": 140,
      "angle_marketing": "Accroche forte senior-friendly",
      "objection_principale": "Frein d'achat identifié + levier pour le lever",
      "fournisseurs_suggeres": ["CJ Dropshipping","BigBuy","Alibaba FOB"],
      "sample_supplier_urls": ["URL plausible à vérifier"],
      "hero_product": true,
      "score_go_10": 9,
      "saisonnalite": "Stable / Pic hiver / Fête des mères"
    }}
  ],
  "produit_hero": "Le produit #1 retenu comme flagship (avec justif)",
  "complementary_upsells": ["3 produits cross-sell possibles pour augmenter AOV"],
  "risques_compliance": ["2-3 risques (ex: marquage CE, MDR, UL)"],
  "plan_import_eu": "Stratégie IOSS / OSS TVA / douane CH / Brexit UK",
  "moq_strategies": "Stratégies MOQ fournisseur Chine"
}}

Base-toi sur des ordres de grandeur réalistes (Google Keyword Planner, Ahrefs). Sois spécifique."""
    },

    "seo": {
        "system": """Tu es expert SEO + brand strategist + copywriter Silver Economy. Tu construis une marque
qui inspire confiance aux 60+ et dominera les SERP FR/EU. Tu réponds UNIQUEMENT en JSON valide.""",
        "user_template": """Niche : {niche}
Pays cibles : {countries}
Marque : {name}
{extra_context}

Génère le KIT COMPLET "SEO & Marque" en JSON :
{{
  "positionnement": {{
    "mission": "Phrase de mission 20 mots",
    "vision": "Vision 3-5 ans",
    "promesse_unique": "USP en 12 mots max",
    "valeurs_3": ["valeur 1","valeur 2","valeur 3"],
    "cible_persona": "Description persona type 60+ ou aidant"
  }},
  "brand_voice": {{
    "tonalite": "Rassurante, pédagogique, chaleureuse...",
    "mots_a_privilegier": ["15 mots"],
    "mots_a_bannir": ["10 mots jeune/startup inadaptés seniors"],
    "exemple_phrase_do": "Phrase exemple conforme",
    "exemple_phrase_dont": "Phrase exemple à éviter"
  }},
  "arborescence_seo": [
    {{"page": "Home","h1": "...","meta_title": "...","meta_desc": "..."}},
    "15 pages minimum : collections, produits hero, guides"
  ],
  "20_articles_blog": [
    {{"title": "Titre article","meta": "Meta 155 chars","kw": "mot-clé principal","intention": "commercial/informationnel","outline_h2": ["H2 1","H2 2","H2 3"]}}
  ],
  "aeo_geo_snippets": [
    {{"question_ia": "Question posée à ChatGPT/Perplexity","reponse_cible": "Notre réponse à rankbaiter","sources_a_citer": ["sources fiables"]}}
  ],
  "link_building_plan": "Stratégie netlinking 6 mois : PR, partenariats forums seniors, guest posts",
  "schema_org_a_implementer": ["Organization","Product","Review","FAQPage","BreadcrumbList"],
  "audit_tech_checklist": ["10 items SEO technique à vérifier"]
}}

Sois concret, francophone, calibré Silver Economy."""
    },

    "marketing": {
        "system": """Tu es expert acquisition payante + analytics + scaling e-commerce. Tu pilotes des campagnes
Google Ads / Meta / TikTok avec budgets 30€/j par pays. Tu réponds UNIQUEMENT en JSON valide.""",
        "user_template": """Niche : {niche}
Pays cibles : {countries}
Marque : {name}
Budget : 30€/jour/pays
{extra_context}

Génère le PLAN COMPLET "Marketing & Scale" en JSON :
{{
  "google_ads": {{
    "campagne_principale": {{
      "type": "Search + PMax",
      "budget_eur_jour": 30,
      "cpa_cible": 25,
      "roas_cible_min": 2.5,
      "keywords_exact": ["10 mots-clés exact match"],
      "keywords_phrase": ["15 phrase match"],
      "negatifs": ["20 négatifs : gratuit, occasion, forum..."]
    }},
    "remarketing_display": "Setup RLSA + Display avec audiences de conversion, budget séparé 10€/j"
  }},
  "meta_ads": {{
    "campagne_cold": "Campagne Advantage+ Shopping, audience large 45-75 FR, budget 20€/j",
    "campagne_warm": "Retargeting ATC + VV75%",
    "creative_brief": "5 angles créa : témoignage vidéo, avant/après, démo produit, aidant-offre cadeau, peur de tomber"
  }},
  "tiktok_ads": {{
    "pertinent": true,
    "approche": "Spark Ads via créateurs 50+ silver influence, budget 10€/j test 3 semaines",
    "creator_brief": "Brief détaillé"
  }},
  "conversion_optimisation": {{
    "social_proof_stack": ["Judge.me reviews","Trustpilot","Badges sécurité","Livraison tracée"],
    "trust_signals": ["Paiement CB local","Garantie 2 ans","Retour 30j gratuit","+10k clients"],
    "scarcity_ethique": "Techniques urgence acceptables pour seniors (stock limité, fin promo)",
    "upsell_postpurchase": "ReConvert + Bundles post-commande"
  }},
  "analytics_setup": {{
    "ga4_events": ["add_to_cart","begin_checkout","purchase","view_item","sign_up_newsletter"],
    "conversion_tracking": "Setup server-side via Shopify Custom Pixel + GA4 Enhanced Conversions",
    "kpis_dashboard": ["CAC","LTV","Marge/commande","ROAS","AOV","Tx conv","Retargeting CR"],
    "alertes_auto": ["CPC >+30% vs moyenne","CR <1%","ROAS <1.8 sur 7j"]
  }},
  "scaling_playbook": {{
    "trigger_scale": "Quand CAC < 40% AOV pendant 14j consécutifs",
    "plan_duplication_6_pays": "Process step-by-step pour dupliquer la marque gagnante sur DE/BE/UK/CH/NL",
    "milestones_ca": ["1k€/mois","5k€/mois","20k€/mois","100k€/mois"],
    "hiring_plan": "Quand embaucher : 1er SAV, 1er media buyer, 1er content manager"
  }},
  "checklist_prelaunch": ["15 items à valider avant de lancer les Ads"]
}}

Base-toi sur benchmarks réels Silver Economy."""
    },
}


class ExecuteBlockInput(BaseModel):
    extra_context: Optional[str] = ""
    model_name: str = "claude-sonnet-4-5-20250929"


@router.get("/blocks/prompts")
async def list_block_prompts(user: dict = Depends(get_current_user)):
    """Expose the 4 mega-block prompts (without the full template) for the UI."""
    return [
        {
            "id": bid,
            "name": BLOCKS[bid]["name"],
            "emoji": BLOCKS[bid]["emoji"],
            "order": BLOCKS[bid]["order"],
            "description": BLOCKS[bid]["description"],
            "deliverable_outline": _describe_output(bid),
        }
        for bid in ["template", "products", "seo", "marketing"]
    ]


def _describe_output(block_id: str) -> list:
    """Human-readable overview of what the mega-prompt produces."""
    return {
        "template": [
            "5 documents juridiques clé-en-main (CGV, RGPD, mentions, cookies, rétractation)",
            "Config Shopify complète (taxes 6 pays, shipping, apps, paiements)",
            "Copy storefront React (hero, about, FAQ 10, footer)",
            "4 templates emails SAV + policies + SLA",
            "Workflow logistique dropshipping + checklist lancement 20 items",
        ],
        "products": [
            "Top 10 produits gagnants avec scoring GO /10",
            "Volume Google + CPC + KD + marge par produit",
            "Fournisseurs suggérés + sample URLs",
            "Produit hero + upsells + risques compliance",
            "Plan import EU (TVA OSS/IOSS, douane CH, Brexit UK)",
        ],
        "seo": [
            "Positionnement (mission, vision, USP, valeurs, persona)",
            "Brand voice (tonalité, mots à privilégier/bannir)",
            "Arborescence 15 pages + meta SEO",
            "20 articles blog avec H2 outlines",
            "AEO/GEO snippets pour ChatGPT + plan netlinking 6 mois",
        ],
        "marketing": [
            "Plan Google Ads (Search + PMax + Remarketing) avec CPA/ROAS cibles",
            "Plan Meta Ads (cold + warm + creative brief)",
            "TikTok strategy + conversion optimisation",
            "Setup GA4 + server-side + dashboard KPI",
            "Playbook scaling 6 pays + milestones CA + hiring plan",
        ],
    }.get(block_id, [])


async def _call_claude(system: str, user: str, session_id: str, model: str) -> dict:
    """Phase 0 — délègue à `safe_claude_json` (retry + circuit breaker).

    Préserve la signature historique : peut prendre n'importe quel modèle
    Anthropic via le wrapper.
    """
    from services.llm_resilience import safe_claude_json, LLMUnavailableError
    try:
        return await safe_claude_json(
            system, user, session_id=session_id, model=model, timeout=180,
        )
    except ValueError as e:
        logger.error(f"Block mega-prompt returned invalid JSON: {e}")
        raise HTTPException(status_code=502, detail="L'IA a retourné un format invalide. Réessayez.")
    except LLMUnavailableError as e:
        logger.warning(f"[blocks_execute] LLM unavailable: {e.last_error}")
        raise HTTPException(status_code=503, detail="IA temporairement indisponible (proxy upstream). Réessayez dans quelques minutes.")
    except HTTPException:
        raise
    except Exception as e:
        err = str(e)
        if "Budget has been exceeded" in err or "budget" in err.lower():
            raise HTTPException(status_code=402, detail="Budget LLM épuisé. Profile → Universal Key → Add Balance.")
        logger.exception("Block mega-prompt LLM call failed")
        raise HTTPException(status_code=500, detail=f"Erreur IA : {err[:200]}")


@router.post("/sites/{site_id}/blocks/{block_id}/execute")
async def execute_block(
    site_id: str,
    block_id: str,
    data: ExecuteBlockInput,
    user: dict = Depends(get_current_user),
):
    site = await _check_site_access(site_id, user)
    if block_id not in MEGA_PROMPTS:
        raise HTTPException(status_code=404, detail=f"Bloc inconnu : {block_id}")

    mp = MEGA_PROMPTS[block_id]
    countries_list = site.get("selected_countries") or []
    countries = ", ".join(countries_list) if countries_list else "FR (défaut)"

    prompt = mp["user_template"].format(
        niche=site.get("niche", ""),
        countries=countries,
        name=site.get("name", ""),
        extra_context=(f"Contexte additionnel : {data.extra_context}" if data.extra_context else ""),
    )

    session_id = f"block-{site_id}-{block_id}-{uuid.uuid4().hex[:6]}"
    output = await _call_claude(mp["system"], prompt, session_id, data.model_name)

    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "id": str(uuid.uuid4()),
        "site_id": site_id,
        "block_id": block_id,
        "block_name": BLOCKS[block_id]["name"],
        "block_emoji": BLOCKS[block_id]["emoji"],
        "model": data.model_name,
        "extra_context": data.extra_context or "",
        "output": output,
        "created_at": now,
        "created_by": user["id"],
    }
    await db.block_outputs.insert_one(dict(doc))
    doc.pop("_id", None)
    return doc


@router.get("/sites/{site_id}/blocks/{block_id}/outputs")
async def list_block_outputs(site_id: str, block_id: str, user: dict = Depends(get_current_user)):
    await _check_site_access(site_id, user)
    items = (
        await db.block_outputs.find(
            {"site_id": site_id, "block_id": block_id}, {"_id": 0}
        )
        .sort("created_at", -1)
        .to_list(20)
    )
    return items


@router.get("/sites/{site_id}/blocks/outputs-latest")
async def latest_block_outputs(site_id: str, user: dict = Depends(get_current_user)):
    """One latest output per block (for the UI panel overview)."""
    await _check_site_access(site_id, user)
    latest = {}
    for bid in MEGA_PROMPTS.keys():
        doc = await db.block_outputs.find_one(
            {"site_id": site_id, "block_id": bid}, {"_id": 0}, sort=[("created_at", -1)]
        )
        if doc:
            latest[bid] = doc
    return latest


@router.delete("/sites/{site_id}/blocks/outputs/{output_id}")
async def delete_block_output(
    site_id: str, output_id: str, user: dict = Depends(get_current_user)
):
    await _check_site_access(site_id, user)
    await db.block_outputs.delete_one({"id": output_id, "site_id": site_id})
    return {"ok": True}
