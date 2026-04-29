"""Phase Refonte UX — toggles d'automatisation par site.

L'idée : le concepteur ne doit RIEN avoir à comprendre ; tout tourne en
arrière-plan. Cette route expose un toggle on/off par catégorie
(content, seo, translation) + un endpoint `status` qui agrège ce qui se
passe pour la pédagogie du concepteur.

Schéma DB (`db.sites.{id}.automation`) :
    {
      "content_enabled":    bool,    # blog auto + landings + FAQ + maillage
      "seo_enabled":        bool,    # crons SEO transverses (sitemap, indexnow)
      "translation_enabled":bool,    # cron de re-traduction
      "updated_at":         ISO,
    }
"""
from __future__ import annotations
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from deps import db, get_current_user

router = APIRouter(tags=["automation"])
logger = logging.getLogger("altiaro.automation")


def _default_automation() -> dict:
    return {
        "content_enabled": True,
        "seo_enabled": True,
        "translation_enabled": True,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


async def get_automation(site_id: str) -> dict:
    site = await db.sites.find_one({"id": site_id}, {"_id": 0, "automation": 1})
    if not site:
        return _default_automation()
    return site.get("automation") or _default_automation()


async def is_content_automation_on(site_id: str) -> bool:
    auto = await get_automation(site_id)
    return bool(auto.get("content_enabled", True))


class CategoryToggleInput(BaseModel):
    enabled: bool


@router.get("/sites/{site_id}/automation")
async def get_automation_state(site_id: str, user=Depends(get_current_user)):
    """Retourne l'état des toggles pour ce site."""
    site = await db.sites.find_one({"id": site_id}, {"_id": 0, "id": 1, "operator_id": 1, "automation": 1})
    if not site:
        raise HTTPException(404, "Site introuvable")
    if user.get("role") != "admin" and site.get("operator_id") != user.get("id"):
        raise HTTPException(403, "Accès refusé")
    return site.get("automation") or _default_automation()


@router.post("/sites/{site_id}/automation/{category}")
async def toggle_automation(
    site_id: str,
    category: str,
    body: CategoryToggleInput,
    user=Depends(get_current_user),
):
    """Active/désactive une catégorie d'automatisation.
    `category` ∈ {`content`, `seo`, `translation`}.
    """
    if category not in {"content", "seo", "translation"}:
        raise HTTPException(400, f"Catégorie inconnue : {category}")
    site = await db.sites.find_one({"id": site_id}, {"_id": 0, "id": 1, "operator_id": 1})
    if not site:
        raise HTTPException(404, "Site introuvable")
    if user.get("role") != "admin" and site.get("operator_id") != user.get("id"):
        raise HTTPException(403, "Accès refusé")
    field = f"automation.{category}_enabled"
    await db.sites.update_one(
        {"id": site_id},
        {"$set": {field: body.enabled,
                  "automation.updated_at": datetime.now(timezone.utc).isoformat()}},
    )
    logger.info(f"[automation] site={site_id[:8]} {category}={'ON' if body.enabled else 'OFF'} by {user.get('email','?')}")
    return await get_automation(site_id)


@router.get("/sites/{site_id}/automation/status")
async def automation_status(site_id: str, user=Depends(get_current_user)):
    """Vue agrégée pour le Cockpit : toggles + dernière activité par catégorie.

    Tout est best-effort, pas d'erreur si une collection est vide.
    """
    site = await db.sites.find_one(
        {"id": site_id},
        {"_id": 0, "id": 1, "operator_id": 1, "automation": 1,
         "available_langs": 1, "primary_lang": 1, "qa_audit": 1},
    )
    if not site:
        raise HTTPException(404, "Site introuvable")
    if user.get("role") != "admin" and site.get("operator_id") != user.get("id"):
        raise HTTPException(403, "Accès refusé")
    auto = site.get("automation") or _default_automation()

    # Content stats
    from datetime import timedelta
    now = datetime.now(timezone.utc)
    since_30d = (now - timedelta(days=30)).isoformat()
    blog_total = await db.blog_posts.count_documents({"site_id": site_id, "status": "published"})
    blog_30d = await db.blog_posts.count_documents({
        "site_id": site_id, "status": "published",
        "$or": [{"created_at": {"$gte": since_30d}}, {"published_at": {"$gte": since_30d}}],
    })
    last_post = await db.blog_posts.find_one(
        {"site_id": site_id, "status": "published"},
        {"_id": 0, "title": 1, "created_at": 1, "published_at": 1},
        sort=[("created_at", -1)],
    )
    landings_total = 0
    try:
        landings_total = await db.landing_pages.count_documents(
            {"site_id": site_id, "status": "published"},
        )
    except Exception:
        pass

    # SEO score : on prend l'audit le plus récent (qa_audit / seo_audit)
    seo_score = None
    try:
        latest_audit = await db.seo_audits.find_one(
            {"site_id": site_id}, {"_id": 0, "score": 1, "audit_date": 1},
            sort=[("audit_date", -1)],
        )
        if latest_audit:
            seo_score = int(latest_audit.get("score") or 0)
    except Exception:
        pass

    # GSC connecté ?
    gsc_connected = False
    try:
        gsc_doc = await db.gsc_oauth_states.find_one(
            {"site_id": site_id, "status": "active"}, {"_id": 0, "site_url": 1},
        )
        gsc_connected = bool(gsc_doc)
    except Exception:
        pass

    return {
        "automation": auto,
        "content": {
            "enabled": auto.get("content_enabled", True),
            "blog_total": blog_total,
            "blog_published_30d": blog_30d,
            "landings_total": landings_total,
            "last_post_at": (last_post or {}).get("created_at") if last_post else None,
            "next_run": "Lun/Mer/Ven 06h00 UTC" if auto.get("content_enabled", True) else None,
        },
        "seo": {
            "enabled": auto.get("seo_enabled", True),
            "score": seo_score,
            "gsc_connected": gsc_connected,
        },
        "translation": {
            "enabled": auto.get("translation_enabled", True),
            "languages_active": site.get("available_langs") or [],
            "primary": site.get("primary_lang") or "fr",
        },
    }
