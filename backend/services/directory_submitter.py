"""Annuaires Silver Economy — auto-submit via email-fallback.

20 cibles hard-codees. Chaque submission envoie un email automatisé
via Resend depuis `submissions@altiaro.com` avec un template Claude
personnalisé par annuaire (ton + cible).

Persistance : `db.directory_submissions` (1 doc par site × annuaire).

Usage :
    POST /api/sites/{id}/marketing/directories/auto-submit
    GET  /api/sites/{id}/marketing/directories/status
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

from deps import db

logger = logging.getLogger("altiaro.directories")


# Liste hard-codée — emails de soumission/contact des annuaires Silver Economy FR.
# A enrichir au fil de l'eau. Email = best-effort (souvent contact@ ou
# referencement@).
DIRECTORIES: List[Dict[str, str]] = [
    {"slug": "senior-actu", "name": "Senior Actu", "email": "contact@senioractu.com", "url": "https://www.senioractu.com", "niche_match": "senior"},
    {"slug": "happyvisio", "name": "Happyvisio", "email": "contact@happyvisio.com", "url": "https://www.happyvisio.com", "niche_match": "senior"},
    {"slug": "mnh-partenaires", "name": "MNH Partenaires", "email": "partenariats@mnh.fr", "url": "https://www.mnh.fr", "niche_match": "senior"},
    {"slug": "senior-service", "name": "Sénior Service", "email": "contact@seniorservice.fr", "url": "https://www.seniorservice.fr", "niche_match": "senior"},
    {"slug": "annuaire-silver", "name": "Annuaire Pro Silver", "email": "contact@silvereco.fr", "url": "https://www.silvereco.fr", "niche_match": "senior"},
    {"slug": "agevillage", "name": "Agevillage", "email": "contact@agevillage.com", "url": "https://www.agevillage.com", "niche_match": "senior"},
    {"slug": "capretraite", "name": "Cap Retraite", "email": "contact@capretraite.fr", "url": "https://www.capretraite.fr", "niche_match": "senior"},
    {"slug": "dependance-info", "name": "Dépendance Info", "email": "contact@dependance.info", "url": "https://www.dependance.info", "niche_match": "senior"},
    {"slug": "essentiel-autonomie", "name": "Essentiel Autonomie (AG2R)", "email": "contact@essentielautonomie.com", "url": "https://www.essentielautonomie.com", "niche_match": "senior"},
    {"slug": "silvermaisonretraite", "name": "Silver Maison Retraite", "email": "contact@silvermaisonretraite.fr", "url": "https://www.silvermaisonretraite.fr", "niche_match": "senior"},
    {"slug": "yelp-fr", "name": "Yelp France", "email": "", "url": "https://biz.yelp.fr", "niche_match": "all", "submit_form": "https://biz.yelp.fr/signup_business"},
    {"slug": "pagesjaunes", "name": "PagesJaunes", "email": "", "url": "https://professionnels.pagesjaunes.fr", "niche_match": "all", "submit_form": "https://professionnels.pagesjaunes.fr/inscription"},
    {"slug": "bing-places", "name": "Bing Places", "email": "", "url": "https://www.bingplaces.com", "niche_match": "all", "submit_form": "https://www.bingplaces.com/Account/Signin"},
    {"slug": "silvereco-pro", "name": "Silver Éco Pro", "email": "redaction@silvereco.fr", "url": "https://www.silvereco.fr", "niche_match": "senior"},
    {"slug": "info-aidant", "name": "Info-Aidant", "email": "contact@info-aidant.fr", "url": "https://www.info-aidant.fr", "niche_match": "senior"},
    {"slug": "tousergo", "name": "Tous Ergo", "email": "contact@tousergo.com", "url": "https://www.tousergo.com", "niche_match": "senior"},
    {"slug": "viva-magazine", "name": "Viva Magazine", "email": "redaction@viva.presse.fr", "url": "https://www.viva.presse.fr", "niche_match": "senior"},
    {"slug": "notre-temps", "name": "Notre Temps", "email": "redaction@notretemps.com", "url": "https://www.notretemps.com", "niche_match": "senior"},
    {"slug": "pleine-vie", "name": "Pleine Vie", "email": "redaction@pleinevie.fr", "url": "https://www.pleinevie.fr", "niche_match": "senior"},
    {"slug": "familles-rurales", "name": "Familles Rurales", "email": "contact@famillesrurales.org", "url": "https://www.famillesrurales.org", "niche_match": "senior"},
]


async def _build_template(site: dict, directory: dict) -> Dict[str, str]:
    """Génère email subject + body via Claude pour ce duo (site, annuaire)."""
    brand = (site.get("design") or {}).get("brand") or {}
    business = brand.get("name") or site.get("name") or ""
    domain = site.get("custom_domain") or ""
    niche = site.get("niche") or ""
    about = (site.get("about_rich") or {}).get("tagline") or ""
    try:
        from services.llm_resilience import safe_claude_json
        data = await safe_claude_json(
            "Tu rédiges des emails de prospection courts, pros et chaleureux pour des annuaires spécialisés.",
            (
                f"Annuaire cible : {directory['name']} ({directory['url']})\n"
                f"Mon e-shop : {business} — {domain}\n"
                f"Niche : {niche}\n"
                f"Tagline : {about}\n\n"
                "Rédige un email de demande de référencement de 100-130 mots, ton respectueux, "
                "qui explique notre activité, ce qu'on apporte aux lecteurs de cet annuaire, "
                "et qui propose la réciprocité (lien retour). "
                "Termine par une signature pro « L'équipe Altiaro ».\n\n"
                "Format JSON : {\"subject\": \"60 chars max\", \"body_html\": \"<p>...</p>\"}"
            ),
            quality_tier="standard",
            session_id=f"dir-{directory['slug']}-{site.get('id','')[:8]}",
            timeout=60,
            request_id=f"dir-{directory['slug']}",
        )
        return {
            "subject": data.get("subject", f"Demande de référencement — {business}"),
            "body_html": data.get("body_html", ""),
        }
    except Exception as e:
        return {
            "subject": f"Demande de référencement — {business}",
            "body_html": (
                f"<p>Bonjour,</p><p>Notre boutique <strong>{business}</strong> "
                f"({domain}) est spécialisée en <em>{niche}</em>. "
                f"Nous serions honorés d'être référencés sur {directory['name']}.</p>"
                f"<p>{about}</p><p>Nous proposons un lien retour depuis nos pages.</p>"
                f"<p>Cordialement,<br/>L'équipe Altiaro</p>"
            ),
            "_llm_error": str(e)[:120],
        }


async def submit_to_directory(site: dict, directory: dict) -> Dict[str, Any]:
    """Tente la soumission d'un site à 1 annuaire (email-only MVP)."""
    sid = site["id"]
    submission_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    record = {
        "id": submission_id,
        "site_id": sid,
        "directory_slug": directory["slug"],
        "directory_name": directory["name"],
        "directory_url": directory["url"],
        "channel": "email" if directory.get("email") else "manual_form",
        "status": "pending",
        "submitted_at": now,
    }
    if not directory.get("email"):
        record["status"] = "manual_form_required"
        record["submit_form"] = directory.get("submit_form")
        await db.directory_submissions.update_one(
            {"site_id": sid, "directory_slug": directory["slug"]},
            {"$set": record},
            upsert=True,
        )
        return {"ok": True, **record}

    template = await _build_template(site, directory)
    try:
        from routes.emails import send_email_via_resend
        await send_email_via_resend(
            to=directory["email"],
            subject=template["subject"],
            html=template["body_html"],
            tags=["directory_submission", directory["slug"]],
        )
        record["status"] = "submitted"
        record["sent_to"] = directory["email"]
        record["subject"] = template["subject"]
    except Exception as e:
        record["status"] = "send_failed"
        record["error"] = str(e)[:300]
    await db.directory_submissions.update_one(
        {"site_id": sid, "directory_slug": directory["slug"]},
        {"$set": record},
        upsert=True,
    )
    return {"ok": record["status"] in ("submitted", "manual_form_required"), **record}


async def auto_submit_all(site_id: str) -> Dict[str, Any]:
    site = await db.sites.find_one({"id": site_id}, {"_id": 0})
    if not site:
        return {"ok": False, "reason": "site_not_found"}
    sem = asyncio.Semaphore(3)
    async def _one(d):
        async with sem:
            return await submit_to_directory(site, d)
    results = await asyncio.gather(*[_one(d) for d in DIRECTORIES], return_exceptions=True)
    submitted = sum(1 for r in results if isinstance(r, dict) and r.get("ok"))
    return {
        "ok": True,
        "site_id": site_id,
        "total": len(DIRECTORIES),
        "submitted": submitted,
        "results": [r for r in results if isinstance(r, dict)],
    }


async def get_status(site_id: str) -> Dict[str, Any]:
    docs = await db.directory_submissions.find(
        {"site_id": site_id}, {"_id": 0},
    ).to_list(100)
    by_status: Dict[str, int] = {}
    for d in docs:
        by_status[d.get("status", "?")] = by_status.get(d.get("status", "?"), 0) + 1
    return {"site_id": site_id, "items": docs, "summary": by_status, "total_directories": len(DIRECTORIES)}
