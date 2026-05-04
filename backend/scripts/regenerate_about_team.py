"""
regenerate_about_team.py — Squelette de régénération About + Team pour Altiaro.

CONTEXTE (2026-05-04) :
    L'audit Phase 0 a révélé deux gaps de contenu sur les sites Altiaro :

    1. `site.design.team_members` est vide ou absent sur la majorité des sites
       (count=0 sur Altea malgré le CHANGELOG affirmant "About/Team générés").

    2. `site.design.about_rich` est absent. Le SSR prerender (`backend/routes/
       prerender.py:174-175`) lit pourtant `site.about_rich` pour servir
       `/about` aux bots LLM ; sur les sites actuels, le contenu existe sous
       `site.design.about` (legacy) ou `site.design.cms_pages.about` (premium
       2026-04+) mais PAS sous `about_rich` au top-level du document site.

    Ce script industrialise la rectification :
       - Synthétise un payload `about_rich` à partir de `cms_pages.about` +
         `design.brand` + identité légale Altiaro.
       - Regénère 3 portraits team_members IA (nom + rôle + portrait Nano
         Banana + bio courte) en s'appuyant sur la voix de marque.
       - Persiste : site.about_rich (top), site.design.team_members (array).

ÉTAT D'EXÉCUTION : DRY-RUN UNIQUEMENT (script squelette).
    Le budget Emergent LLM est à 100,04 % au 2026-05-04. Toute génération
    réelle échouerait en `Budget exceeded` côté proxy LiteLLM.

ACTIVATION (Phase 2 ultérieure, post-rechargement budget) :
    1. L'utilisateur recharge le crédit Emergent.
    2. Lancer en dry-run d'abord :
         python3 backend/scripts/regenerate_about_team.py --site-id <id> --dry-run
    3. Vérifier le payload simulé (logged en stdout).
    4. Lancer en production :
         python3 backend/scripts/regenerate_about_team.py --site-id <id> --execute
    5. Vérifier en DB que `site.about_rich` et `site.design.team_members`
       sont peuplés. Re-tester `/api/seo/prerender/{site_id}?path=/about`.

CIBLE BUDGET (estimation) :
    - About rich : 1 appel Sonnet 4.5 (synthèse premium) ≈ $0.05
    - Team members : 3 × (1 appel Haiku bio + 1 appel Nano Banana portrait) ≈ $0.30
    - Total : ~$0.35 par site régénéré.
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Bootstrap env for standalone CLI usage
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("regenerate_about_team")


# ---------------------------------------------------------------------------
# Building blocks (DRY-RUN safe — no LLM calls)
# ---------------------------------------------------------------------------

def _synth_about_rich_dryrun(site: Dict[str, Any]) -> Dict[str, Any]:
    """Construit un payload `about_rich` en dry-run sans appeler aucun LLM.

    Réutilise ce qui existe déjà sur le site (`design.cms_pages.about` ou
    `design.about` legacy) plutôt que de simuler du contenu inventé.
    """
    design = site.get("design") or {}
    cms_about = (design.get("cms_pages") or {}).get("about") or {}
    legacy_about = design.get("about") or {}
    brand = design.get("brand") or {}

    # Fallback en cascade : cms_pages.about (premium) > design.about (legacy)
    title = cms_about.get("title") or brand.get("name") or site.get("name", "")
    tagline = (
        cms_about.get("subtitle")
        or (legacy_about.get("headline") or {}).get("fr")
        or ""
    )
    body_md = cms_about.get("body_md") or ""
    if not body_md and legacy_about.get("paragraphs"):
        # Concat paragraphes FR legacy
        paras = legacy_about["paragraphs"]
        body_md = "\n\n".join(
            (p.get("fr") if isinstance(p, dict) else str(p))
            for p in paras
        )
    highlights = cms_about.get("highlights") or []

    return {
        "title": title,
        "tagline": tagline,
        "mission": tagline[:200] if tagline else "",
        "story": body_md,
        "highlights": highlights,
        "synthesized_at": datetime.now(timezone.utc).isoformat(),
        "synthesis_method": "dryrun_from_existing_cms",
        "synthesis_source": "cms_pages.about" if cms_about else "design.about_legacy",
    }


def _team_members_skeleton() -> List[Dict[str, Any]]:
    """Renvoie 3 entrées team_members vides — squelette de structure attendue.

    Le vrai pipeline (Phase 2) appellera Claude Haiku pour le bio + Nano Banana
    pour le portrait. Ici on retourne uniquement le shape attendu.
    """
    return [
        {
            "id": f"team_dryrun_{i}",
            "name": "TBD",                # à générer via Claude
            "role": "TBD",                # à générer via Claude
            "bio_md": "",                 # à générer via Claude
            "portrait_url": "",           # à générer via Nano Banana
            "languages": ["fr"],
            "generated_at": None,
            "method": "skeleton_dryrun",
        }
        for i in range(1, 4)
    ]


# ---------------------------------------------------------------------------
# CLI driver
# ---------------------------------------------------------------------------

async def _run(site_id: str, dry_run: bool, execute: bool) -> int:
    if not (dry_run ^ execute):
        logger.error("Choisis --dry-run OU --execute (exclusif).")
        return 2
    if execute:
        logger.error(
            "Mode --execute désactivé en Phase 0 (budget LLM Emergent à 100%%). "
            "Recharger d'abord le crédit Emergent puis remettre cette branche en commentaire."
        )
        return 3

    # Lecture seule depuis MongoDB — aucun appel LLM
    from pymongo import MongoClient
    mongo_url = os.environ["MONGO_URL"]
    db_name = os.environ.get("DB_NAME") or "altiaro_dev"
    cli = MongoClient(mongo_url)
    db = cli[db_name]
    site = db.sites.find_one({"id": site_id}, {"_id": 0})
    if not site:
        logger.error(f"Site introuvable : {site_id}")
        return 4

    logger.info(f"[DRY-RUN] Site : {site.get('name','?')} ({site_id})")
    logger.info(f"[DRY-RUN] custom_domain : {site.get('custom_domain') or '—'}")

    # 1) About rich (synthèse depuis l'existant — pas de LLM)
    about_rich = _synth_about_rich_dryrun(site)
    logger.info("[DRY-RUN] about_rich payload :")
    for k, v in about_rich.items():
        if isinstance(v, str):
            preview = v[:160] + "..." if len(v) > 160 else v
            logger.info(f"  {k} : {preview!r}")
        else:
            logger.info(f"  {k} : {v}")

    # 2) Team members (squelette — pas de LLM)
    team = _team_members_skeleton()
    logger.info(f"[DRY-RUN] team_members count : {len(team)} (skeleton)")
    for m in team:
        logger.info(f"  - {m['id']} : name={m['name']!r}, role={m['role']!r}")

    logger.info("[DRY-RUN] Aucune écriture DB. Aucun appel LLM. Aucun appel Google.")
    logger.info("[DRY-RUN] Pour activer : recharger le crédit Emergent puis retirer "
                "le garde-fou dans _run() (mode --execute).")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[1].strip())
    parser.add_argument("--site-id", required=True, help="UUID du site à régénérer")
    parser.add_argument("--dry-run", action="store_true", help="Mode simulation (par défaut)")
    parser.add_argument("--execute", action="store_true", help="DÉSACTIVÉ en Phase 0")
    args = parser.parse_args()

    if not (args.dry_run or args.execute):
        args.dry_run = True

    code = asyncio.run(_run(args.site_id, args.dry_run, args.execute))
    sys.exit(code)


if __name__ == "__main__":
    main()
