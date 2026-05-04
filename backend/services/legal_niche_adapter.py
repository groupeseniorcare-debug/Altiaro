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


async def adapt_legal_for_niche(site_id: str, niche: str,
                                base_texts: Dict[str, str]) -> Dict[str, str]:
    """Rewrite each legal section to reflect the specifics of the niche.

    Returns a dict {section: adapted_text}. Sections that failed LLM are
    returned unchanged (fallback to base_texts).
    """
    adapted: Dict[str, str] = {}
    for section in LEGAL_SECTIONS:
        base = base_texts.get(section) or ""
        if not base:
            continue
        try:
            out = await _adapt_one(site_id, niche, section, base)
            adapted[section] = out or base
        except Exception as e:
            logger.warning(f"[legal_niche] {section} adapt failed: {e}")
            adapted[section] = base
    return adapted


async def _adapt_one(site_id: str, niche: str, section: str, base: str) -> Optional[str]:
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
        f"SECTION : {section_label}\n\n"
        f"TEXTE GÉNÉRIQUE :\n{base}\n\n"
        f"Ta mission : réécris ce texte en y injectant les spécificités concrètes "
        f"de la niche « {niche} ». Exemples d'adaptation attendus :\n"
        f"- Conditions de retour : produits volumineux/fragiles → précise l'emballage requis\n"
        f"- Livraison : poids/volume/distance spécifiques à la niche\n"
        f"- Garanties : sectorielles (ex. 2 ans légal + 5 ans commerciale pour outillage premium)\n"
        f"- SAV : process adapté à la niche (pièces détachées, intervention, etc.)\n"
        f"- RGPD : préciser les traitements spécifiques (ex. données santé pour Silver Economy)\n\n"
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
