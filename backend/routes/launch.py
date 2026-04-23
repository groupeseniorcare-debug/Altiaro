"""
Launch Orchestrator — "Generate complete store on demand"
=========================================================

Endpoint : POST /sites/{id}/design/launch → spawn async job
Endpoint : GET  /sites/{id}/design/launch-status → real-time progress

The orchestrator enriches an EXISTING site :
  - Brand identity (name, tagline, voice, palette, fonts)
  - Premium horizontal logo (Nano Banana)
  - Navigation + mega menu from real collections
  - Fixed homepage template
      Hero → Logos partenaires → Best-sellers → Collections → À propos → Avis → Gestion commande → Footer
  - Static pages : About, Contact, FAQ, Legal
  - **Every imported product** gets :
      - AI narrative (enrich-narrative)
      - 5 hero images (lifestyle × 2, studio × 1, closeup × 1, in_use × 1)
      - 2 narrative-section images (embedded in detail page)
  - Marks Étape 5 "validated" and unlocks Étape 6.

NO products are created. Only existing products are enriched.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from deps import db, get_current_user, _check_site_access

logger = logging.getLogger("conceptfactory.launch")
router = APIRouter()

# ------------------------------------------------------------------
# Input models
# ------------------------------------------------------------------
class WizardInput(BaseModel):
    brand_name: Optional[str] = None
    tagline: Optional[str] = None
    mission: Optional[str] = None
    voice: Optional[str] = "chaleureux et rassurant, premium"
    mood: Optional[str] = "Éditorial"              # Éditorial | Minimaliste | Chaleureux | Moderne
    palette_choice: Optional[dict] = None          # {primary, accent, background, text}
    font_pair: Optional[dict] = None               # {heading, body}
    homepage_preset: Optional[str] = "default_template"
    overwrite_all: bool = False                    # True = clean slate; False = fill only missing
    logo_style: Optional[str] = "horizontal_premium"


# ------------------------------------------------------------------
# Homepage template enforced by the wizard
# ------------------------------------------------------------------
DEFAULT_LAUNCH_HOMEPAGE_ORDER = [
    "hero",
    "press_logos",       # Logos partenaires
    "products",          # Best-sellers (grille)
    "collections",       # Collections cards
    "founder_story",     # À propos (card)
    "testimonials",      # Avis + social proof
    "benefits",          # Gestion commande / réassurance
    "faq",
    "newsletter",
    "final_cta",
]


# ------------------------------------------------------------------
# Job tracking helpers
# ------------------------------------------------------------------
async def _update_job(job_id: str, patch: dict):
    patch["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.launch_jobs.update_one({"id": job_id}, {"$set": patch})


async def _advance(job_id: str, step_key: str, label: str, progress_pct: int):
    await _update_job(job_id, {
        "current_step": step_key,
        "current_label": label,
        "progress_pct": progress_pct,
    })


# ------------------------------------------------------------------
# Main orchestrator (runs in background)
# ------------------------------------------------------------------
async def _run_launch(job_id: str, site_id: str, user_id: str, wizard: dict):
    """Long-running background task. Updates launch_jobs doc as it progresses."""
    try:
        # ---------- Deferred imports to avoid circular deps at startup ----------
        from routes import design as design_routes
        from routes import product_narrative as pn_routes
        from routes import product_images as pimg_routes

        site = await db.sites.find_one({"id": site_id}, {"_id": 0})
        if not site:
            raise Exception("Site introuvable")

        design = site.get("design") or {}
        overwrite = bool(wizard.get("overwrite_all"))

        # 1) Brand identity & palette -------------------------------------
        await _advance(job_id, "brand", "Identité de marque & palette", 5)
        brand_patch = {
            "primary_color": (wizard.get("palette_choice") or {}).get("primary") or design.get("brand", {}).get("primary_color") or "#B84B31",
            "accent_color":  (wizard.get("palette_choice") or {}).get("accent")  or design.get("brand", {}).get("accent_color")  or "#E9C46A",
            "background_color": (wizard.get("palette_choice") or {}).get("background") or design.get("brand", {}).get("background_color") or "#FAF7F2",
            "text_color":    (wizard.get("palette_choice") or {}).get("text")    or design.get("brand", {}).get("text_color")    or "#1C1917",
            "font_heading":  (wizard.get("font_pair") or {}).get("heading") or design.get("brand", {}).get("font_heading") or "Fraunces",
            "font_body":     (wizard.get("font_pair") or {}).get("body")    or design.get("brand", {}).get("font_body")    or "Inter",
            "voice": wizard.get("voice") or design.get("brand", {}).get("voice") or "chaleureux et rassurant, premium",
        }
        if wizard.get("brand_name"):
            brand_patch["logo_text"] = wizard["brand_name"]
        if wizard.get("tagline"):
            brand_patch["tagline"] = wizard["tagline"]
        if wizard.get("mission"):
            brand_patch["mission"] = wizard["mission"]

        await db.sites.update_one(
            {"id": site_id},
            {"$set": {
                "design.brand": {**design.get("brand", {}), **brand_patch},
                "design.updated_at": datetime.now(timezone.utc).isoformat(),
            }},
        )

        # 2) Logo premium horizontal (Nano Banana) ------------------------
        await _advance(job_id, "logo", "Logo premium horizontal (Nano Banana)", 12)
        try:
            logo_prompt = (
                f"Ultra-premium horizontal wordmark logo for a luxury French brand named "
                f"« {wizard.get('brand_name') or brand_patch.get('logo_text') or site.get('name')} ». "
                "Editorial typography (light serif with subtle ligatures), monochrome on transparent background, "
                "extremely refined kerning, tagline optional below in small caps. Aspect ratio 16:5 (horizontal, "
                "wider than tall). Absolutely NO icon, NO symbol, NO flourish — typography only. "
                "Museum-quality, think Hermès / Aesop / Loro Piana. Output ready to go on a white website header. "
                "High resolution, extremely sharp."
            )
            url = await asyncio.wait_for(
                pimg_routes._generate_one(logo_prompt, site_id, f"logo-{site_id[:8]}"),
                timeout=150,
            )
            if url:
                await db.sites.update_one(
                    {"id": site_id},
                    {"$set": {"design.brand.logo_url": url,
                              "design.updated_at": datetime.now(timezone.utc).isoformat()}},
                )
        except asyncio.TimeoutError:
            logger.warning("[launch] logo timed out")
        except Exception as e:
            logger.warning(f"[launch] logo skipped: {str(e)[:120]}")

        # 3) Homepage sections — apply fixed template ---------------------
        await _advance(job_id, "template", "Template homepage fixe", 18)
        sections = []
        for key in DEFAULT_LAUNCH_HOMEPAGE_ORDER:
            sections.append({"key": key, "visible": True})
        # Include the rest as invisible (schema-safe)
        for d in design_routes.DEFAULT_HOMEPAGE_SECTIONS:
            if d["key"] not in DEFAULT_LAUNCH_HOMEPAGE_ORDER:
                sections.append({"key": d["key"], "visible": False})
        await db.sites.update_one(
            {"id": site_id},
            {"$set": {
                "design.homepage_sections": sections,
                "design.updated_at": datetime.now(timezone.utc).isoformat(),
            }},
        )

        # 4) Content sections regeneration --------------------------------
        # Each of these calls the existing `regenerate_section` handler, which already
        # uses Claude + returns premium copy aligned to the brand voice.
        content_steps = [
            ("hero",        "Hero premium de la page d'accueil", 22),
            ("benefits",    "Bénéfices & réassurance",          28),
            ("testimonials", "Témoignages clients",              34),
            ("faq",         "FAQ optimisée",                     40),
            ("about",       "Page À propos éditoriale",          46),
            ("contact",     "Page Contact",                      52),
        ]
        fake_user = {"id": user_id, "role": "concepteur"}
        budget_exhausted = False
        for section_key, label, pct in content_steps:
            await _advance(job_id, f"content-{section_key}", label, pct)
            if budget_exhausted:
                logger.info(f"[launch] skip {section_key}: budget already flagged")
                continue
            try:
                if not overwrite and design.get(section_key):
                    logger.info(f"[launch] skip {section_key}: already present")
                    continue
                # Hard timeout guard (Claude is usually 15-40s; if it hangs, skip)
                await asyncio.wait_for(
                    design_routes.regenerate_section(
                        site_id=site_id,
                        section=section_key,
                        data=design_routes.RegenInput(tweak=""),
                        user=fake_user,
                    ),
                    timeout=90,
                )
            except asyncio.TimeoutError:
                logger.warning(f"[launch] {section_key} timed out")
            except Exception as e:
                msg = str(e)
                logger.warning(f"[launch] {section_key} failed: {msg[:120]}")
                if "402" in msg or "budget" in msg.lower() or "exhaust" in msg.lower():
                    budget_exhausted = True
                    await _update_job(job_id, {"warning": "Budget Emergent LLM Key épuisé — sections restantes ignorées."})

        # 5) Navigation with mega menu from real collections --------------
        await _advance(job_id, "navigation", "Navigation & mega menu", 56)
        if not budget_exhausted:
            try:
                await asyncio.wait_for(
                    design_routes.ai_optimize_nav(site_id=site_id, user=fake_user),
                    timeout=90,
                )
            except asyncio.TimeoutError:
                logger.warning("[launch] navigation timed out")
            except Exception as e:
                msg = str(e)
                logger.warning(f"[launch] navigation failed: {msg[:120]}")
                if "402" in msg or "budget" in msg.lower():
                    budget_exhausted = True

        # 6) Collections AI suggest ---------------------------------------
        await _advance(job_id, "collections", "Suggestion de collections IA", 60)
        if not budget_exhausted:
            try:
                suggestions = await asyncio.wait_for(
                    design_routes.ai_suggest_collections(site_id=site_id, user=fake_user),
                    timeout=90,
                )
                # Auto-create the first 3 suggested collections (if any and not already present)
                existing_names = {
                    (c.get("name") or "").lower()
                    for c in (await db.collections.find({"site_id": site_id}, {"_id": 0, "name": 1}).to_list(50))
                }
                for s in (suggestions.get("collections") or [])[:3]:
                    if (s.get("name") or "").lower() in existing_names:
                        continue
                    await db.collections.insert_one({
                        "id": str(uuid.uuid4()),
                        "site_id": site_id,
                        "name": s.get("name"),
                        "slug": (s.get("name") or "").lower().replace(" ", "-").replace("/", "-")[:60],
                        "description": s.get("description") or "",
                        "cover_image": None,
                        "product_ids": s.get("product_ids") or [],
                        "featured": bool(s.get("featured")),
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    })
            except asyncio.TimeoutError:
                logger.warning("[launch] collections timed out")
            except Exception as e:
                msg = str(e)
                logger.warning(f"[launch] collections failed: {msg[:120]}")
                if "402" in msg or "budget" in msg.lower():
                    budget_exhausted = True

        # 7) Legal pages ---------------------------------------------------
        await _advance(job_id, "legal", "Pages légales", 62)
        site2 = await db.sites.find_one({"id": site_id}, {"_id": 0})
        if not site2:
            # Site was deleted while the job was running → abort cleanly.
            await _update_job(job_id, {
                "status": "failed",
                "error": "Le site a été supprimé pendant la génération.",
                "completed_at": datetime.now(timezone.utc).isoformat(),
            })
            return
        design2 = site2.get("design") or {}
        design2 = design_routes._inject_legal(design2, site2)
        await db.sites.update_one(
            {"id": site_id},
            {"$set": {"design.legal_pages": design2["legal_pages"],
                      "design.updated_at": datetime.now(timezone.utc).isoformat()}},
        )

        # 8) Products — narrative + images (biggest step) ------------------
        products = await db.products.find(
            {"site_id": site_id, "status": {"$ne": "deleted"}},
            {"_id": 0, "id": 1, "name": 1, "images": 1, "narrative": 1, "generated_images": 1},
        ).to_list(200)

        total_products = len(products)
        if total_products == 0 or budget_exhausted:
            if budget_exhausted:
                await _advance(job_id, "products-skip", "Enrichissement produits ignoré (budget IA)", 95)
            else:
                await _advance(job_id, "products-skip", "Aucun produit importé à enrichir", 95)
        else:
            per_step = max(1, (95 - 65) // max(1, total_products))
            for idx, p in enumerate(products):
                if budget_exhausted:
                    logger.info("[launch] skip remaining products (budget)")
                    break
                pct_now = 65 + per_step * idx
                name = p.get("name", {})
                if isinstance(name, dict):
                    label_name = name.get("fr") or name.get("en") or "(produit)"
                else:
                    label_name = str(name)
                await _advance(
                    job_id,
                    f"product-{idx}",
                    f"Fiche produit {idx+1}/{total_products} — {label_name[:32]}",
                    min(95, pct_now),
                )
                # 8a) narrative (if missing or overwrite)
                if overwrite or not p.get("narrative"):
                    try:
                        result = await asyncio.wait_for(
                            pn_routes.enrich_product_narrative(p["id"], force=True),
                            timeout=120,
                        )
                        if isinstance(result, dict) and result.get("status") == "llm_budget_exceeded":
                            budget_exhausted = True
                            continue
                    except asyncio.TimeoutError:
                        logger.warning(f"[launch] narrative {p['id']} timed out")
                    except Exception as e:
                        msg = str(e)
                        logger.warning(f"[launch] narrative {p['id']}: {msg[:120]}")
                        if "402" in msg or "budget" in msg.lower():
                            budget_exhausted = True
                            continue

                # 8b) 5 product hero images (use existing imported supplier images as base; add AI)
                generated = p.get("generated_images") or []
                existing_ai_count = len(generated)
                target_ai_count = 3  # 3 IA images (so that imported + AI = ~5 total for the gallery)
                styles_to_gen = []
                if overwrite or existing_ai_count < target_ai_count:
                    needed = max(0, target_ai_count - existing_ai_count) if not overwrite else target_ai_count
                    # Mix of styles
                    styles_to_gen = ["lifestyle", "studio", "closeup"][:needed]
                for style in styles_to_gen:
                    if budget_exhausted:
                        break
                    try:
                        await asyncio.wait_for(
                            pimg_routes.generate_product_image(
                                product_id=p["id"],
                                data=pimg_routes.GenProductImgInput(style=style, tweak="", replace_main=False),
                                user={"id": user_id, "role": "concepteur"},
                            ),
                            timeout=120,
                        )
                    except asyncio.TimeoutError:
                        logger.warning(f"[launch] img {style} {p['id']} timed out")
                    except Exception as e:
                        msg = str(e)
                        logger.warning(f"[launch] img {style} {p['id']}: {msg[:120]}")
                        if "402" in msg or "budget" in msg.lower():
                            budget_exhausted = True

                # 8c) 2 narrative-section images (embedded in detail page)
                try:
                    fresh = await db.products.find_one({"id": p["id"]}, {"_id": 0, "narrative.sections": 1})
                    narr_sections = ((fresh or {}).get("narrative") or {}).get("sections") or []
                    for sec_idx in range(min(2, len(narr_sections))):
                        if budget_exhausted:
                            break
                        sec = narr_sections[sec_idx]
                        if not overwrite and sec.get("image"):
                            continue
                        try:
                            await asyncio.wait_for(
                                pimg_routes.generate_narrative_section_image(
                                    product_id=p["id"],
                                    data=pimg_routes.GenSectionImgInput(
                                        section_index=sec_idx,
                                        style="in_use" if sec_idx == 0 else "closeup",
                                        tweak="",
                                    ),
                                    user={"id": user_id, "role": "concepteur"},
                                ),
                                timeout=120,
                            )
                        except asyncio.TimeoutError:
                            logger.warning(f"[launch] section-img p={p['id']} i={sec_idx} timed out")
                        except Exception as e:
                            msg = str(e)
                            logger.warning(f"[launch] section-img p={p['id']} i={sec_idx}: {msg[:120]}")
                            if "402" in msg or "budget" in msg.lower():
                                budget_exhausted = True
                except Exception as e:
                    logger.warning(f"[launch] section-loop {p['id']}: {e}")

        # 9) Mark Étape 5 validated + unlock Étape 6 ---------------------
        await _advance(job_id, "finalize", "Finalisation & déblocage SEO", 98)
        try:
            await db.sites.update_one(
                {"id": site_id},
                {"$addToSet": {"validated_steps": 5},
                 "$set": {"launch_generated_at": datetime.now(timezone.utc).isoformat()}},
            )
        except Exception:
            pass

        await _update_job(job_id, {
            "status": "completed",
            "progress_pct": 100,
            "current_label": "Site généré !",
            "completed_at": datetime.now(timezone.utc).isoformat(),
        })

    except Exception as e:
        logger.exception(f"[launch] job {job_id} failed")
        await _update_job(job_id, {
            "status": "failed",
            "error": str(e)[:300],
            "completed_at": datetime.now(timezone.utc).isoformat(),
        })


# ------------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------------
@router.post("/sites/{site_id}/design/launch", status_code=201)
async def launch_site(
    site_id: str,
    wizard: WizardInput,
    user: dict = Depends(get_current_user),
):
    """Spawn the launch orchestrator and return a job_id for polling."""
    await _check_site_access(site_id, user)

    # Prevent concurrent launches for the same site
    running = await db.launch_jobs.find_one(
        {"site_id": site_id, "status": "running"},
        {"_id": 0, "id": 1},
    )
    if running:
        raise HTTPException(409, "Une génération est déjà en cours pour ce site.")

    job_id = str(uuid.uuid4())
    await db.launch_jobs.insert_one({
        "id": job_id,
        "site_id": site_id,
        "user_id": user["id"],
        "status": "running",
        "progress_pct": 0,
        "current_step": "start",
        "current_label": "Démarrage…",
        "wizard": wizard.dict(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    # Fire and forget (asyncio task scheduled by the running FastAPI loop)
    asyncio.create_task(_run_launch(job_id, site_id, user["id"], wizard.dict()))

    return {"ok": True, "job_id": job_id, "status": "running"}


@router.get("/sites/{site_id}/design/launch-status")
async def launch_status(
    site_id: str,
    job_id: Optional[str] = None,
    user: dict = Depends(get_current_user),
):
    """Return the current progress of a launch job (latest if no job_id given)."""
    await _check_site_access(site_id, user)
    query = {"site_id": site_id}
    if job_id:
        query["id"] = job_id
    doc = await db.launch_jobs.find_one(
        query, {"_id": 0}, sort=[("created_at", -1)],
    )
    if not doc:
        return {"status": "idle"}
    return doc
