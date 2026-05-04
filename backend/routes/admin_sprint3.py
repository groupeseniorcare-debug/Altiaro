"""Sprint 3 — endpoints admin pour les nouveautés industrialisation.

Expose :
  - POST /api/sites/{id}/launch/health-check           → run_health_check (11 points)
  - POST /api/sites/{id}/launch/bing-provision         → Bing Webmaster AddSite + SubmitSitemap
  - POST /api/admin/cron/aliexpress-refresh            → run ad hoc du cron AE refresh
  - POST /api/admin/cron/directory-followup            → run ad hoc du follow-up annuaires
  - GET  /api/admin/integrations/bing-status           → vérifie si BING_WEBMASTER_API_KEY est posé
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from deps import db, get_current_user, _check_site_access

router = APIRouter()


def _require_admin(user: dict):
    if not user or user.get("role") != "admin":
        raise HTTPException(403, "Admin required")


@router.post("/sites/{site_id}/launch/health-check", tags=["sprint3"])
async def trigger_health_check(site_id: str, user: dict = Depends(get_current_user)):
    """Run the 11-point real HTTP health-check for a site."""
    await _check_site_access(site_id, user)
    from services.launch_health_check import run_health_check
    return await run_health_check(site_id)


@router.post("/sites/{site_id}/launch/bing-provision", tags=["sprint3"])
async def trigger_bing_provision(site_id: str, user: dict = Depends(get_current_user)):
    """Bing Webmaster Tools : AddSite + SubmitSitemap (idempotent)."""
    await _check_site_access(site_id, user)
    site = await db.sites.find_one({"id": site_id}) or {}
    if not site:
        raise HTTPException(404, "Site not found")
    from services.bing_webmaster import provision_bing_for_site
    res = await provision_bing_for_site(site)
    # Persist on site doc
    await db.sites.update_one(
        {"id": site_id},
        {"$set": {"integrations.bing_webmaster": res}},
    )
    return res


@router.post("/admin/cron/aliexpress-refresh", tags=["sprint3"])
async def manual_aliexpress_refresh(user: dict = Depends(get_current_user)):
    """Manual trigger of AE products refresh (for QA)."""
    _require_admin(user)
    from services.cron_jobs import refresh_aliexpress_products_job
    return await refresh_aliexpress_products_job()


@router.post("/admin/cron/directory-followup", tags=["sprint3"])
async def manual_directory_followup(user: dict = Depends(get_current_user)):
    """Manual trigger of directory submission follow-up."""
    _require_admin(user)
    from services.directory_fsm import follow_up_pending_reviews
    return await follow_up_pending_reviews()


@router.get("/admin/integrations/bing-status", tags=["sprint3"])
async def bing_status(user: dict = Depends(get_current_user)):
    """Quick check : is BING_WEBMASTER_API_KEY configured?"""
    _require_admin(user)
    import os
    key = os.environ.get("BING_WEBMASTER_API_KEY", "")
    return {
        "configured": bool(key),
        "hint": ("Set BING_WEBMASTER_API_KEY in .env — obtain at "
                 "https://www.bing.com/webmasters/home/mysites → Settings → API Access")
                if not key else "OK",
    }


@router.post("/sites/{site_id}/legal/adapt-niche", tags=["sprint3"])
async def legal_adapt_niche(site_id: str, user: dict = Depends(get_current_user)):
    """Sprint 2.3 — rewrite legal texts to fit the site's niche via Claude Haiku."""
    await _check_site_access(site_id, user)
    site = await db.sites.find_one({"id": site_id}) or {}
    if not site:
        raise HTTPException(404, "Site not found")
    niche = site.get("niche") or "e-commerce premium"
    # Build base texts. Priority order:
    #   1. site.legal.{key}.body_md (already adapted previously)
    #   2. site.design.legal_pages.{key}.body_md (injected during launch-auto)
    #   3. altiaro_legal platform defaults
    legal_src = site.get("legal") or {}
    design_legal = (site.get("design") or {}).get("legal_pages") or {}
    base = {}
    # Aliases : design.legal_pages uses 'mentions_legales' while site.legal uses 'mentions'
    aliases = {"mentions": ["mentions", "mentions_legales"]}
    for key in ("cgv", "mentions", "confidentialite", "livraison", "retours"):
        candidates = aliases.get(key, [key])
        body = ""
        for cand in candidates:
            v1 = legal_src.get(cand) or {}
            v2 = design_legal.get(cand) or {}
            if isinstance(v1, dict) and (v1.get("body_md") or v1.get("body")):
                body = v1.get("body_md") or v1.get("body") or ""
                break
            if isinstance(v2, dict) and (v2.get("body_md") or v2.get("body")):
                body = v2.get("body_md") or v2.get("body") or ""
                break
            if isinstance(v1, str) and v1:
                body = v1; break
            if isinstance(v2, str) and v2:
                body = v2; break
        if body:
            base[key] = body
    if not base:
        try:
            from altiaro_legal import PLATFORM_LEGAL_TEMPLATES  # type: ignore
            for k in ("cgv", "mentions", "confidentialite", "livraison", "retours"):
                base[k] = (PLATFORM_LEGAL_TEMPLATES.get(k) or "") if PLATFORM_LEGAL_TEMPLATES else ""
        except Exception:
            pass
    base = {k: v for k, v in base.items() if v}
    if not base:
        return {"ok": False, "reason": "no_base_legal_text",
                "hint": "Run launch-auto first to inject default legal templates."}
    from services.legal_niche_adapter import adapt_legal_for_niche
    adapted = await adapt_legal_for_niche(site_id, niche, base)
    update = {}
    for k, text in adapted.items():
        update[f"legal.{k}.body_md"] = text
        update[f"legal.{k}.updated_at"] = __import__("datetime").datetime.utcnow().isoformat() + "Z"
        update[f"legal.{k}.niche_adapted"] = True
        update[f"legal.{k}.niche"] = niche
    if update:
        await db.sites.update_one({"id": site_id}, {"$set": update})
    return {"ok": True, "sections_adapted": list(adapted.keys()), "niche": niche,
            "base_sections": list(base.keys())}
