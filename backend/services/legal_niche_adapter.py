"""Sprint 2.3 — Templates légaux adaptés par IA à la niche.

Le `altiaro_legal.py` fournit des templates CGV/Mentions/Confidentialité/
Livraison/Retours génériques. Cette couche ajoute une passe IA (Haiku) qui
injecte les spécificités de la niche : seuils de retour, zones de livraison
réalistes, garanties sectorielles, gestion du SAV, etc.

Utilisation :
    from services.legal_niche_adapter import adapt_legal_for_niche

    adapted = await adapt_legal_for_niche(
        site_id="...",
        niche="outils de jardinage premium",
        base_texts={
            "cgv": "...",
            "retours": "...",
            ...
        },
    )
    # adapted["cgv"], adapted["retours"], ... sont les versions niche-aware.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from services.llm_resilience import safe_claude_json

logger = logging.getLogger("altiaro.legal_niche")

LEGAL_SECTIONS = ("cgv", "mentions", "confidentialite", "livraison", "retours")


# ────────────────────────────────────────────────────────────────────────
# NICHE_LEGAL_REQUIREMENTS — Mentions obligatoires injectées dans le prompt
# selon la famille de niche détectée. Chaque entrée contient :
#   - keywords : mots-clés de détection (lowercased substring match)
#   - required_terms : listes de clauses/termes DEVANT apparaître dans les
#     sections légales adaptées.
# Utilisé par `adapt_legal_for_niche` pour forcer l'IA à réintégrer les
# mentions sectorielles obligatoires (LPP, CPAM, CE, NF EN, garantie 2 ans,
# droit santé, etc.).
# ────────────────────────────────────────────────────────────────────────
NICHE_LEGAL_REQUIREMENTS: Dict[str, Dict[str, Any]] = {
    "silver_economy_medical": {
        "keywords": [
            "fauteuil releveur", "fauteuil roulant", "matelas médicalisé",
            "lit médicalisé", "monte-escalier", "aide à la mobilité",
            "silver economy", "senior", "séniore", "handicap",
            "dispositif médical", "orthopédie", "incontinence",
            "téléassistance", "déambulateur",
        ],
        "required_terms": [
            "dispositif médical classe I",
            "marquage CE médical",
            "LPP (Liste des Produits et Prestations remboursables)",
            "remboursement partiel CPAM sur prescription médicale",
            "garantie légale de conformité 2 ans (art. L.217-3 Code de la consommation)",
            "droit de rétractation 14 jours (art. L.221-18) — exclusion produits d'hygiène descellés",
            "SAV : pièces détachées disponibles 7 ans minimum",
            "livraison sur rendez-vous étage + installation (produits volumineux > 30kg)",
            "reprise ancien matériel sur demande (éco-participation DEEE)",
            "traitement de données de santé : base légale art. 9 RGPD (consentement explicite)",
        ],
        "hint_for_ai": (
            "Niche SILVER ECONOMY MEDICAL. Les produits sont assimilables à "
            "des dispositifs médicaux ou aides techniques. Le client-type "
            "est une personne âgée ou à mobilité réduite, parfois éligible "
            "à un remboursement CPAM/LPP sur prescription."
        ),
    },
    "premium_tools_garden": {
        "keywords": [
            "outil de jardinage", "outils de jardinage", "jardin premium",
            "sécateur", "motoculture", "tondeuse", "tronçonneuse",
            "outillage professionnel", "bricolage premium", "visseuse",
            "perceuse",
        ],
        "required_terms": [
            "conformité NF EN ISO 11806 (motoculture) ou normes CE Machines (Directive 2006/42/CE)",
            "marquage CE outillage obligatoire",
            "garantie commerciale étendue 5 ans (pièces métalliques) en complément des 2 ans légaux",
            "pièces détachées disponibles 10 ans via réseau partenaire",
            "livraison colis volumineux (>20kg) par transporteur dédié, créneau à confirmer",
            "droit de rétractation 14 jours — produits non utilisés, dans leur emballage",
            "retours à la charge du client pour raison de convenance, prise en charge Altiaro si défaut",
            "éco-participation DEEE affichée sur chaque produit motorisé",
            "consignes de sécurité obligatoires inscrites dans la notice (EPI, distances)",
        ],
        "hint_for_ai": (
            "Niche OUTILLAGE / JARDIN PREMIUM. Les produits sont soumis à "
            "la directive Machines 2006/42/CE, marquage CE obligatoire. "
            "Garanties longues (5 ans pièces) attendues sur ce segment."
        ),
    },
    "mattress_bedding": {
        "keywords": [
            "matelas", "literie", "oreiller", "surmatelas", "sommier",
            "couette",
        ],
        "required_terms": [
            "certification OEKO-TEX Standard 100 (exempt de substances nocives)",
            "conformité Règlement (UE) 305/2011 produits de construction (mousses ignifuges)",
            "garantie commerciale 10 ans (affaissement) + 2 ans légaux",
            "droit de rétractation 14 jours — matelas non déballé de sa housse hygiénique scellée (art. L.221-28 3°)",
            "livraison à domicile, reprise ancienne literie sur demande (éco-participation Eco-Mobilier)",
            "conseils d'entretien obligatoires (rotation, hygrométrie, housse)",
            "traitement anti-acariens certifié si revendiqué",
        ],
        "hint_for_ai": (
            "Niche LITERIE / MATELAS. Le droit de rétractation ne s'applique "
            "pas si le matelas a été déballé (exclusion art. L.221-28 3°). "
            "OEKO-TEX et garanties longues attendues sur ce segment."
        ),
    },
    "fashion_apparel": {
        "keywords": [
            "mode", "vêtement", "prêt-à-porter", "accessoires mode",
            "maroquinerie", "chaussures",
        ],
        "required_terms": [
            "droit de rétractation 14 jours — article non porté, étiquettes intactes",
            "garantie légale de conformité 2 ans",
            "échanges taille/couleur offerts en France métropolitaine",
            "traitement RGPD des mensurations et préférences clients (base légale : exécution contrat)",
            "traçabilité origine matières (règlement UE 2018/848 pour bio/éthique si revendiqué)",
        ],
        "hint_for_ai": (
            "Niche MODE / PRÊT-À-PORTER. Échanges/retours simples attendus, "
            "information sur l'origine des matières si revendication éthique."
        ),
    },
    "beauty_cosmetics": {
        "keywords": [
            "cosmétique", "beauté", "soin visage", "parfum", "maquillage",
            "hygiène", "santé naturelle",
        ],
        "required_terms": [
            "conformité Règlement (CE) n°1223/2009 produits cosmétiques",
            "DPP (Dossier Produit Présent) consultable",
            "liste INCI complète sur chaque fiche produit",
            "droit de rétractation 14 jours — produit non descellé (exclusion art. L.221-28 5° pour raisons d'hygiène)",
            "tests dermatologiques certifiés (si revendiqués)",
            "traitement RGPD des données de peau/santé : base légale consentement explicite (art. 9)",
        ],
        "hint_for_ai": (
            "Niche BEAUTÉ / COSMÉTIQUE. Règlement européen cosmétique strict, "
            "l'exclusion de rétractation 'produit descellé' est capitale."
        ),
    },
    "generic_premium": {
        "keywords": [],  # fallback
        "required_terms": [
            "garantie légale de conformité 2 ans (art. L.217-3 Code de la consommation)",
            "garantie légale des vices cachés (art. 1641 Code civil)",
            "droit de rétractation 14 jours (art. L.221-18)",
            "médiation de la consommation CM2C ou équivalent",
            "protection des données RGPD — base légale détaillée par finalité",
        ],
        "hint_for_ai": "Niche e-commerce premium générique. Mentions légales françaises B2C standard.",
    },
}


def _detect_niche_family(niche: str) -> str:
    """Retourne la clé NICHE_LEGAL_REQUIREMENTS correspondant à la niche.

    Matching par keywords (substring lowercase). Fallback `generic_premium`.
    """
    n = (niche or "").lower().strip()
    if not n:
        return "generic_premium"
    for family, spec in NICHE_LEGAL_REQUIREMENTS.items():
        if family == "generic_premium":
            continue
        for kw in spec["keywords"]:
            if kw in n:
                return family
    return "generic_premium"


async def adapt_legal_for_niche(site_id: str, niche: str,
                                base_texts: Dict[str, str]) -> Dict[str, str]:
    """Rewrite each legal section to reflect the specifics of the niche.

    Returns a dict {section: adapted_text}. Sections that failed LLM are
    returned unchanged (fallback to base_texts).
    """
    family = _detect_niche_family(niche)
    spec = NICHE_LEGAL_REQUIREMENTS[family]
    logger.info(f"[legal_niche] site={site_id[:8]} niche={niche!r} family={family} "
                f"required_terms={len(spec['required_terms'])}")
    adapted: Dict[str, str] = {}
    for section in LEGAL_SECTIONS:
        base = base_texts.get(section) or ""
        if not base:
            continue
        try:
            out = await _adapt_one(site_id, niche, section, base, family=family, spec=spec)
            adapted[section] = out or base
        except Exception as e:
            logger.warning(f"[legal_niche] {section} adapt failed: {e}")
            adapted[section] = base
    return adapted


async def _adapt_one(site_id: str, niche: str, section: str, base: str,
                      family: str = "generic_premium",
                      spec: Optional[Dict[str, Any]] = None) -> Optional[str]:
    spec = spec or NICHE_LEGAL_REQUIREMENTS["generic_premium"]
    section_label = {
        "cgv": "Conditions Générales de Vente",
        "mentions": "Mentions légales",
        "confidentialite": "Politique de confidentialité",
        "livraison": "Politique de livraison",
        "retours": "Politique de retours et remboursement",
    }.get(section, section)

    system = (
        "Tu es juriste e-commerce spécialisé droit français B2C. Tu adaptes "
        "des textes juridiques génériques aux spécificités d'une niche. Tu "
        "ne renvoies QUE le texte adapté au format markdown (sans JSON, sans "
        "balises, sans explication extérieure). Tu conserves la structure H2/H3 "
        "et toutes les clauses légales obligatoires (LCEN, RGPD, Code de la "
        "consommation, droit de rétractation 14j). Tu NE changes PAS l'identité "
        "légale (Groupeseniorcare SAS, KBIS, SIRET) présente dans le texte."
    )
    user = (
        f"NICHE : {niche}\n"
        f"FAMILLE DÉTECTÉE : {family}\n"
        f"CONTEXTE SECTORIEL : {spec.get('hint_for_ai', '')}\n"
        f"SECTION : {section_label}\n\n"
        f"TEXTE GÉNÉRIQUE :\n{base}\n\n"
        f"MENTIONS OBLIGATOIRES À INTÉGRER (au moins celles pertinentes pour cette section) :\n"
        + "\n".join(f"  • {t}" for t in spec["required_terms"])
        + "\n\n"
        f"Ta mission : réécris ce texte en y injectant les spécificités concrètes "
        f"de la niche « {niche} ». Tu dois OBLIGATOIREMENT intégrer les mentions "
        f"sectorielles listées ci-dessus qui concernent cette section (pas forcément "
        f"toutes, choisis celles pertinentes au contexte de la section).\n\n"
        f"Exemples d'adaptation attendus :\n"
        f"- Conditions de retour : produits volumineux/fragiles → précise l'emballage requis\n"
        f"- Livraison : poids/volume/distance spécifiques à la niche\n"
        f"- Garanties : sectorielles (ex. 2 ans légal + 5 ans commerciale pour outillage premium)\n"
        f"- SAV : process adapté à la niche (pièces détachées, intervention, etc.)\n"
        f"- RGPD : préciser les traitements spécifiques (ex. données de santé pour Silver Economy)\n\n"
        f"Conserve EXACTEMENT :\n"
        f"- Les références à l'entité légale vendeuse\n"
        f"- Les mentions obligatoires Code de la consommation / RGPD / LCEN\n"
        f"- Les placeholders {{{{double_braces}}}} s'il y en a\n"
        f"- La structure H2/H3 globale\n\n"
        f"Ne renvoie QUE le texte markdown adapté, rien d'autre."
    )
    try:
        # On utilise safe_claude_json avec un format dict marker pour contrainte douce
        # Mais ici on veut du markdown pur. On appelle donc directement le proxy
        # via safe_claude_json en mode 'raw' si dispo, sinon on fait un fallback.
        from services.llm_resilience import safe_claude_text
        out = await safe_claude_text(
            system=system, user=user, quality_tier="speed",
            request_id=f"legal-{section}-{site_id[:8]}", timeout=120,
        )
        if out and len(out) > 200:
            return out.strip()
    except ImportError:
        # safe_claude_text absent → fallback via safe_claude_json en faux dict
        fake_sys = system + " Renvoie UN JSON STRICT: {\"text\": \"...markdown complet...\"}"
        try:
            j = await safe_claude_json(system=fake_sys, user=user, quality_tier="speed",
                                        request_id=f"legal-{section}-{site_id[:8]}", timeout=120)
            if isinstance(j, dict) and j.get("text"):
                return j["text"].strip()
        except Exception as e:
            logger.warning(f"[legal_niche] fallback JSON failed {section}: {e}")
    except Exception as e:
        logger.warning(f"[legal_niche] raw text call failed {section}: {e}")
    return None
