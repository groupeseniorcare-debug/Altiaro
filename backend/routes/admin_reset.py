"""
Admin Reset — endpoints pour remettre un site à un état antérieur,
utile pour tester le pipeline de génération de bout en bout sans
re-sourcer les produits.

Endpoints :
  POST /api/admin/sites/{site_id}/reset-to-step-5
    Body : {confirm: true}
    → Supprime branding/design/images IA/blog/landings/pages CMS/traductions
    → Garde produits, upsells, forecast, domaine, google_provisioning, niche.

  PATCH /api/sites/{site_id}/launch-instructions
    Body : {instructions: str}
    → Persist `site.launch_instructions` (≤ 2000 car), pris en compte par
      l'auto-launch (Claude brand, Nano Banana images).

Accès : admin uniquement (reset), opérateur du site OK (instructions).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from deps import db, get_current_user, _check_site_access

logger = logging.getLogger("altiaro.admin_reset")
router = APIRouter(tags=["admin"])


# ─────────────────────── Models ─────────────────────── #

class ResetConfirm(BaseModel):
    confirm: bool = Field(..., description="Doit être `true` pour procéder au reset")


class LaunchInstructions(BaseModel):
    instructions: str = Field("", max_length=2000)


# ─────────────────────── Endpoints ─────────────────────── #

@router.post("/admin/sites/{site_id}/reset-to-step-5")
async def reset_site_to_step_5(
    site_id: str,
    body: ResetConfirm,
    user: dict = Depends(get_current_user),
):
    """Remet un site à l'état "fin étape 4" :
      - Garde : produits (avec source_image_url AliExpress), upsells,
        forecast, niche, target_countries, langue primaire, domaine,
        google_provisioning.
      - Wipe : branding, design, images IA produits, traductions,
        blog, landings, pages CMS, AEO, keyword universe, launch_jobs,
        manual_step_overrides, went_live_at, status → "staging".

    Utile pour revalider toute l'usine de bout en bout sur un site
    existant sans rejouer l'import des produits.
    """
    if (user or {}).get("role") != "admin":
        raise HTTPException(403, "Admin uniquement")
    if not body.confirm:
        raise HTTPException(400, "`confirm: true` requis pour exécuter le reset")

    site = await db.sites.find_one({"id": site_id}, {"_id": 0, "id": 1, "name": 1})
    if not site:
        raise HTTPException(404, "Site introuvable")

    summary: dict[str, int] = {}

    # 1) Reset du document site (branding/design/status/overrides/went_live)
    site_update_result = await db.sites.update_one(
        {"id": site_id},
        {
            "$set": {
                "status": "staging",
                "brand": None,
                "design": None,
                "logo_url": None,
                "hero_image_url": None,
                "manual_step_overrides": {},
                "reset_to_step5_at": datetime.now(timezone.utc).isoformat(),
                "reset_to_step5_by": user.get("id"),
            },
            "$unset": {
                "went_live_at": "",
                "live_at": "",
                "brand_autogen": "",
            },
        },
    )
    summary["site_document_reset"] = int(site_update_result.modified_count)

    # 2) Produits : wipe images IA + traductions, garde source_image_url
    products_update = await db.products.update_many(
        {"site_id": site_id},
        {
            "$set": {
                "images_by_variant": None,
                "translations": None,
                "narrative": None,
                "translations_status": None,
            },
            "$unset": {
                "ai_images_ready_at": "",
                "narrative_generated_at": "",
            },
        },
    )
    summary["products_reset"] = int(products_update.modified_count)

    # 3) Delete collections de génération (blog, landings, AEO, keywords, pages)
    for coll, filt in [
        ("blog_posts",       {"site_id": site_id}),
        ("blog_jobs",        {"site_id": site_id}),
        ("landing_pages",    {"site_id": site_id}),
        ("pages_jobs",       {"site_id": site_id}),
        ("aeo_jobs",         {"site_id": site_id}),
        ("keyword_universe", {"site_id": site_id}),
        ("keyword_clusters", {"site_id": site_id}),
        ("emerging_keywords",{"site_id": site_id}),
        ("content_gaps",     {"site_id": site_id}),
        ("launch_jobs",      {"site_id": site_id}),
        ("design_jobs",      {"site_id": site_id}),
        ("narrative_jobs",   {"site_id": site_id}),
        ("analysis_jobs",    {"site_id": site_id}),
        ("seo_audits",       {"site_id": site_id}),
        ("seo_automation_log",{"site_id": site_id}),
        ("citation_history", {"site_id": site_id}),
        ("citation_runs",    {"site_id": site_id}),
        ("site_snapshots",   {"site_id": site_id}),
    ]:
        try:
            r = await db[coll].delete_many(filt)
            if r.deleted_count:
                summary[coll] = int(r.deleted_count)
        except Exception as e:
            logger.warning(f"[reset] delete {coll} failed: {e}")

    # 4) Steps : reset des étapes 5 → 10 vers pending
    #    (les étapes 1-4 restent validées : pricing, import, upsells, forecast)
    steps_to_reset = ["branding", "domain", "content", "translate", "seo", "qa"]
    try:
        r = await db.steps.update_many(
            {"site_id": site_id, "key": {"$in": steps_to_reset}},
            {"$set": {"status": "pending", "completed": False},
             "$unset": {"completed_at": "", "validated_at": ""}},
        )
        summary["steps_reset"] = int(r.modified_count)
    except Exception as e:
        logger.warning(f"[reset] steps reset failed: {e}")

    return {
        "ok": True,
        "site_id": site_id,
        "site_name": site.get("name"),
        "summary": summary,
        "preserved": [
            "products (with source_image_url)",
            "upsells, forecast, pricing",
            "niche, target_countries, primary language",
            "domain (altea-home.com etc.)",
            "google_provisioning (merchant_id, ads, ga4)",
        ],
        "reset_at": datetime.now(timezone.utc).isoformat(),
    }


@router.patch("/sites/{site_id}/launch-instructions")
async def save_launch_instructions(
    site_id: str,
    body: LaunchInstructions,
    user: dict = Depends(get_current_user),
):
    """Persist les consignes en langage naturel du concepteur avant le
    lancement. Ces consignes sont injectées dans les prompts Claude/Nano
    Banana pendant l'auto-launch (étape 5)."""
    await _check_site_access(site_id, user)
    instr = (body.instructions or "").strip()
    result = await db.sites.update_one(
        {"id": site_id},
        {"$set": {
            "launch_instructions": instr,
            "launch_instructions_updated_at": datetime.now(timezone.utc).isoformat(),
        }},
    )
    if result.matched_count == 0:
        raise HTTPException(404, "Site introuvable")
    return {"ok": True, "site_id": site_id, "length": len(instr)}


@router.get("/sites/{site_id}/launch-instructions")
async def get_launch_instructions(
    site_id: str,
    user: dict = Depends(get_current_user),
):
    await _check_site_access(site_id, user)
    site = await db.sites.find_one(
        {"id": site_id},
        {"_id": 0, "launch_instructions": 1, "launch_instructions_updated_at": 1},
    )
    if not site:
        raise HTTPException(404, "Site introuvable")
    return {
        "site_id": site_id,
        "instructions": site.get("launch_instructions") or "",
        "updated_at": site.get("launch_instructions_updated_at"),
    }
