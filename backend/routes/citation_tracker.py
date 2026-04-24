"""AI Citation Tracker — mesure hebdomadaire la visibilité de la marque
dans les réponses des moteurs IA (ChatGPT/Claude/Perplexity/Gemini).

Approche pragmatique sans API Perplexity/OpenAI externe :
- On utilise Claude (via Emergent LLM Key) comme **panel de référence** en lui
  posant les 5-10 questions conversationnelles les plus importantes du site
  (`aeo.conversational_keywords` déjà générés par le module AEO).
- On parse la réponse et on détecte si le **nom de marque** apparaît, soit en
  mention directe, soit via le domaine du site.
- On stocke un snapshot hebdo `citation_rate` sur le site, alimente un
  tracker UI (sparkline + détail par question).

NB : c'est une mesure **directionnelle** (Claude n'est pas le seul moteur IA,
mais c'est un bon proxy). L'intérêt est de suivre l'évolution dans le temps
au fur et à mesure que le contenu AEO s'enrichit.

Entrypoints :
- POST /api/sites/{id}/citation-tracker/run          → déclenche un run
- GET  /api/sites/{id}/citation-tracker              → dernier run + historique
"""
from __future__ import annotations
import logging
import re
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from deps import db, get_current_user
from routes.product_narrative import _call_claude_json

router = APIRouter()
logger = logging.getLogger("conceptfactory.citation_tracker")


def _pick_text(val) -> str:
    if isinstance(val, dict):
        for k in ("fr", "fr-FR", "en"):
            if val.get(k):
                return str(val[k])
        return str(next(iter(val.values()), ""))
    return str(val or "")


def _pick_questions(site: dict, products: list, max_questions: int = 6) -> list[str]:
    """Sélectionne les meilleures questions conversationnelles pour tester.
    Priorité :
    1. `aeo.conversational_keywords` déclarés au site
    2. FAQ de chaque produit (premier item)
    3. Construction synthetique depuis le nom du produit
    """
    questions: list[str] = []

    # 1. Site-level AEO test queries (if we ever store them)
    for q in ((site.get("design") or {}).get("aeo_test_queries") or []):
        if q and isinstance(q, str):
            questions.append(q)

    # 2. Product FAQ heads
    for p in products[:8]:
        narrative = p.get("narrative") or {}
        for f in (narrative.get("faq") or [])[:2]:
            q = (f.get("question") or f.get("q") or "").strip()
            if q and len(q) > 15 and len(q) < 200 and q not in questions:
                questions.append(q)
        if len(questions) >= max_questions:
            break

    # 3. Fallback synthetic questions from product names
    if len(questions) < max_questions:
        for p in products[:max_questions]:
            name = _pick_text(p.get("name") or "")
            if not name:
                continue
            synth = f"Quelle est la meilleure marque pour un {name.lower()} en France en 2026 ?"
            if synth not in questions:
                questions.append(synth)
            if len(questions) >= max_questions:
                break

    return questions[:max_questions]


def _mentions_brand(answer: str, brand_name: str, domain: Optional[str]) -> bool:
    """Détection case-insensitive de la marque ou du domaine dans la réponse IA."""
    if not answer:
        return False
    low = answer.lower()
    if brand_name:
        # Exact match sur le nom (avec word boundary unicode-safe)
        pattern = re.compile(
            r"(?<!\w)" + re.escape(brand_name.lower()) + r"(?!\w)",
        )
        if pattern.search(low):
            return True
    if domain:
        # Strip protocol & www
        d = domain.lower().replace("https://", "").replace("http://", "").replace("www.", "").strip("/")
        if d and d in low:
            return True
    return False


async def _ask_claude_panel(question: str, timeout: int = 45) -> tuple[Optional[str], Optional[str]]:
    """Pose la question à Claude en mode `panel IA`. Retourne (answer, error)."""
    system = (
        "Tu es un moteur IA qui répond à des questions d'acheteurs français. "
        "Réponds comme le ferait ChatGPT, Perplexity ou Gemini : cite des "
        "marques réelles que tu connais, donne des conseils concrets. "
        "Tu DOIS nommer 3 à 5 marques ou sites web réels quand la question "
        "porte sur un produit à acheter."
    )
    user = (
        f"Question utilisateur : {question}\n\n"
        "Réponds en 120-180 mots. Cite précisément les marques ou sites web "
        "recommandés. Format JSON strict : {\"answer\": \"...\", \"brands_cited\": [\"marque1\", ...]}"
    )
    data, err = await _call_claude_json(system, user, timeout=timeout)
    if err:
        return None, err
    answer = str(data.get("answer") or "").strip()
    brands = data.get("brands_cited") or []
    # Concatène answer + list brands pour augmenter la surface de détection
    full = answer + " | " + " | ".join(str(b) for b in brands)
    return full, None


class RunInput(BaseModel):
    max_questions: int = 6


@router.post("/sites/{site_id}/citation-tracker/run")
async def run_citation_tracker(site_id: str, body: RunInput, user=Depends(get_current_user)):
    """Déclenche un run de mesure : 5-6 questions simulées, rate de citation."""
    site = await db.sites.find_one({"id": site_id}, {"_id": 0})
    if not site:
        raise HTTPException(404, "Site introuvable")

    brand_name = _pick_text((site.get("design") or {}).get("brand", {}).get("name") or site.get("name") or "")
    domain = site.get("custom_domain") or ""

    if not brand_name:
        raise HTTPException(400, "La marque n'a pas de nom — rédige d'abord le brand book (Étape 5).")

    products = await db.products.find(
        {"site_id": site_id, "status": "active"},
        {"_id": 0, "name": 1, "narrative": 1},
    ).to_list(100)

    questions = _pick_questions(site, products, max_questions=body.max_questions)
    if not questions:
        return {
            "status": "noop",
            "message": "Pas assez de questions AEO pour tester. Enrichis d'abord les produits via le panneau AEO.",
        }

    results: list[dict] = []
    hit = 0
    for q in questions:
        answer, err = await _ask_claude_panel(q)
        if err == "budget_exceeded":
            # Stop immediately and return partial
            return {
                "status": "failed",
                "error": "Budget LLM épuisé — rechargez la clé Emergent.",
                "partial_results": results,
            }
        if err or not answer:
            results.append({"question": q, "answer": None, "cited": False, "error": err})
            continue
        cited = _mentions_brand(answer, brand_name, domain)
        if cited:
            hit += 1
        results.append({
            "question": q,
            "answer": answer[:400],  # cap pour stockage
            "cited": cited,
        })

    total = len(results)
    rate = round((hit / total) * 100) if total else 0

    snapshot = {
        "at": datetime.now(timezone.utc).isoformat(),
        "rate": rate,
        "hit": hit,
        "total": total,
        "brand_name": brand_name,
        "results": results,
    }

    # Persist snapshot + append to history (max 26 entries = 6 mois)
    await db.sites.update_one(
        {"id": site_id},
        {
            "$set": {"design.seo_coach.last_citation_run": snapshot},
            "$push": {
                "design.seo_coach.citation_history": {
                    "$each": [{"at": snapshot["at"], "rate": rate, "hit": hit, "total": total}],
                    "$slice": -26,
                },
            },
        },
    )

    return snapshot


@router.get("/sites/{site_id}/citation-tracker")
async def get_citation_tracker(site_id: str, user=Depends(get_current_user)):
    """Retourne le dernier snapshot + l'historique."""
    site = await db.sites.find_one(
        {"id": site_id},
        {"_id": 0, "design.seo_coach.last_citation_run": 1, "design.seo_coach.citation_history": 1},
    )
    if not site:
        raise HTTPException(404, "Site introuvable")

    coach = (site.get("design") or {}).get("seo_coach") or {}
    return {
        "last_run": coach.get("last_citation_run"),
        "history": coach.get("citation_history") or [],
    }
