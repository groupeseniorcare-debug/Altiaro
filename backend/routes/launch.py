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
import os
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from deps import db, get_current_user, _check_site_access
from routes.design import _sanitize_brand_text
from services.llm_resilience import (
    safe_claude_json,
    LLMUnavailableError,
)

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
        "current_step":  step_key,
        "current_label": label,
        "progress_pct":  progress_pct,
    })
    # Append to checkpoints (idempotent — $addToSet sur un dict ne marche pas,
    # on push avec test d'unicité côté key)
    await db.launch_jobs.update_one(
        {"id": job_id, "checkpoints.step": {"$ne": step_key}},
        {"$push": {"checkpoints": {
            "step":         step_key,
            "label":        label,
            "progress_pct": progress_pct,
            "ts":           datetime.now(timezone.utc).isoformat(),
        }}},
    )


async def _mark_degraded(job_id: str, step_key: str, reason: str):
    """Marque une sous-étape comme dégradée (LLM down, budget, parse, etc.)
    pour qu'elle soit affichée en orange dans le LaunchProgress et puisse être
    relancée à part."""
    await db.launch_jobs.update_one(
        {"id": job_id, "degraded_steps.step": {"$ne": step_key}},
        {"$push": {"degraded_steps": {
            "step":   step_key,
            "reason": (reason or "")[:200],
            "ts":     datetime.now(timezone.utc).isoformat(),
        }}},
    )
    logger.warning(f"[launch:{job_id}] step={step_key} → DEGRADED ({reason})")


async def _mark_failed_resumable(job_id: str, step_key: str, reason: str):
    """Marque le job en `failed` mais avec `resumable=true` + `failed_step` →
    permet la reprise via POST /launch-jobs/{id}/resume sans regénérer ce qui
    a déjà été fait."""
    await _update_job(job_id, {
        "status":      "failed",
        "resumable":   True,
        "failed_step": step_key,
        "error":       (reason or "")[:300],
        "failed_at":   datetime.now(timezone.utc).isoformat(),
    })
    logger.error(f"[launch:{job_id}] FAILED (resumable) at {step_key}: {reason}")


# ------------------------------------------------------------------
# Phase C helpers — premium testimonials (Claude + Nano Banana portraits)
# and CMS pages (About / Contact) generated from the narrative_angle.
# ------------------------------------------------------------------
async def _generate_premium_testimonials(site_id: str, wizard: dict, budget_exhausted: bool, *, job_id: Optional[str] = None):
    """Génère 3 témoignages fictifs réalistes + 3 portraits Nano Banana cohérents
    avec la niche et la voix de marque. Stocke dans `site.design.testimonials_premium`.

    Idempotent : si déjà 3 témoignages persistés ET pas overwrite, on ne refait rien.
    """
    site = await db.sites.find_one({"id": site_id}, {"_id": 0, "design": 1, "name": 1, "niche": 1})
    if not site:
        return
    design = site.get("design") or {}
    overwrite = bool(wizard.get("overwrite_all"))
    existing = (design.get("testimonials_premium") or [])
    if not overwrite and len(existing) >= 3:
        logger.info("[launch] testimonials already present — skip")
        return

    brand = design.get("brand") or {}
    brand_name = brand.get("name") or wizard.get("brand_name") or site.get("name") or "la marque"
    voice = brand.get("voice") or wizard.get("voice") or "premium"
    niche = site.get("niche") or wizard.get("niche") or "silver economy"
    narrative_angle = wizard.get("narrative_angle") or design.get("narrative_angle") or ""

    # 1) Texte des 3 témoignages via Claude (résilience auto via safe_claude_json)
    system_msg = (
        "Tu es copywriter senior pour des marques de luxe. Tu réponds UNIQUEMENT en JSON "
        "valide, sans markdown fence, sans texte autour."
    )
    user_prompt = f"""Génère 3 témoignages clients ULTRA-PREMIUM pour cette marque :

Marque    : {brand_name}
Niche     : {niche}
Voix      : {voice}
Angle narratif : {narrative_angle[:200]}

Format JSON STRICT (array de 3 objets) :
[
  {{"name":"Prénom L.","city":"Ville, Pays","age":68,"text":"Témoignage 30-50 mots, ton sincère, jamais commercial, premier degré, détail spécifique et émotionnel"}},
  ...
]

Règles :
- Prénoms réalistes français/européens variés (pas 'John Doe')
- Villes EU : Paris, Lyon, Bruxelles, Genève, Munich, Amsterdam, Milano…
- Si niche silver economy : âges 65-78
- Pas d'emojis, pas de superlatifs creux ('incroyable', 'magique'),
  mais une émotion concrète, un avant/après spécifique
- Réponds UNIQUEMENT le tableau JSON."""

    try:
        items = await safe_claude_json(system_msg, user_prompt, timeout=60)
    except LLMUnavailableError as e:
        logger.warning(f"[launch] testimonials degraded — LLM unavailable: {e.last_error}")
        if job_id:
            await _mark_degraded(job_id, "testimonials_premium", f"LLM down: {e.last_error}")
        return
    except ValueError as e:
        logger.warning(f"[launch] testimonials JSON parse failed: {e}")
        if job_id:
            await _mark_degraded(job_id, "testimonials_premium", f"JSON parse: {e}")
        return
    if isinstance(items, dict):
        items = items.get("testimonials") or items.get("items") or []
    if not isinstance(items, list) or len(items) < 3:
        logger.warning(f"[launch] testimonials malformed ({type(items)}) — skip")
        return

    # 2) Portraits Nano Banana pour chaque témoignage (1 par 1, throttle naturel)
    from routes import product_images as pimg_routes  # noqa: PLC0415
    out: list[dict] = []
    for i, t in enumerate(items[:3]):
        if budget_exhausted:
            break
        name = (t.get("name") or "").strip() or f"Client {i+1}"
        age = int(t.get("age") or 70)
        portrait_prompt = (
            f"Editorial portrait photography, 50mm, soft golden hour window light, "
            f"shallow depth of field, neutral textured background. "
            f"A {age}-year-old elegant European person, dignified expression, "
            f"natural calm smile, wearing tasteful classic clothing (cashmere, linen). "
            f"Loro Piana / The Row catalogue aesthetic. Photo realistic, not commercial. "
            f"Warm cinematic palette, no text, no logo. Subject centered, three-quarter angle."
        )
        try:
            url = await asyncio.wait_for(
                pimg_routes._generate_one(portrait_prompt, site_id=site_id, product_id=f"testim-{i}"),
                timeout=90,
            )
        except (asyncio.TimeoutError, LLMUnavailableError):
            url = None
        except Exception as e:
            msg = str(e)
            logger.warning(f"[launch] testim portrait {i}: {msg[:120]}")
            if "402" in msg or "budget" in msg.lower():
                budget_exhausted = True
            url = None

        out.append({
            "id":       str(uuid.uuid4()),
            "name":     name,
            "city":     t.get("city") or "",
            "age":      age,
            "text":     t.get("text") or "",
            "image":    url,
            "rating":   5,
            "verified": True,
        })

    if out:
        await db.sites.update_one(
            {"id": site_id},
            {"$set": {
                "design.testimonials_premium": out,
                "design.testimonials_generated_at": datetime.now(timezone.utc).isoformat(),
            }},
        )
        logger.info(f"[launch] {len(out)} premium testimonials persisted (with portraits)")


async def _generate_premium_cms_pages(site_id: str, wizard: dict, *, job_id: Optional[str] = None):
    """Génère pages 'À propos' (400-500 mots) et 'Contact' éditoriales,
    avec narrative_angle. Stocke dans `site.design.cms_pages = {about, contact}`.

    Idempotent : skip si déjà présent et pas overwrite.
    """
    site = await db.sites.find_one({"id": site_id}, {"_id": 0, "design": 1, "name": 1})
    if not site:
        return
    design = site.get("design") or {}
    overwrite = bool(wizard.get("overwrite_all"))
    cms = design.get("cms_pages") or {}
    if not overwrite and cms.get("about") and cms.get("contact"):
        return

    brand = design.get("brand") or {}
    brand_name = brand.get("name") or wizard.get("brand_name") or site.get("name") or "la marque"
    mission = brand.get("mission") or wizard.get("mission") or ""
    voice = brand.get("voice") or wizard.get("voice") or "premium"
    narrative_angle = wizard.get("narrative_angle") or design.get("narrative_angle") or ""

    system_msg = (
        "Tu es directeur éditorial d'une agence de luxe. Tu réponds UNIQUEMENT en JSON "
        "valide, sans markdown fence, sans texte autour."
    )
    user_prompt = f"""Rédige les pages "À propos" et "Contact" pour la marque suivante :

Marque         : {brand_name}
Mission        : {mission}
Voix           : {voice}
Angle narratif : {narrative_angle[:300]}

Format JSON STRICT :
{{
  "about": {{
    "title": "Titre éditorial 4-7 mots, jamais 'À propos' générique",
    "subtitle": "Phrase de bandeau 10-15 mots",
    "body_md": "Texte de 400-500 mots en markdown, structure : ouverture forte, histoire/origine fictive plausible, valeurs concrètes (3-4), engagement client. Ton {voice}, jamais corporate.",
    "highlights": [
      {{"title":"Engagement court 3-4 mots","body":"15-25 mots"}},
      {{"title":"Engagement court 3-4 mots","body":"15-25 mots"}},
      {{"title":"Engagement court 3-4 mots","body":"15-25 mots"}}
    ]
  }},
  "contact": {{
    "title": "Titre éditorial 4-7 mots",
    "subtitle": "Bandeau 10-15 mots invitant au dialogue",
    "intro_md": "Intro markdown 60-100 mots, ton humain, donne envie d'écrire, jamais robotique",
    "phone_label": "Au téléphone",
    "phone_hours": "Du lundi au vendredi, 9h-18h",
    "email_label": "Par e-mail",
    "promise": "Promesse délai réponse, 1 phrase ('réponse sous 24h ouvrées')"
  }}
}}

Règles :
- Pas de phrases creuses ("Notre équipe est passionnée…")
- Pas de "best in class", "leader du marché", emoji
- Privilégier l'humain, le détail concret, le ton de voix demandé
- Réponds UNIQUEMENT le JSON."""

    try:
        parsed = await safe_claude_json(system_msg, user_prompt, timeout=90)
    except LLMUnavailableError as e:
        logger.warning(f"[launch] cms_pages degraded — LLM unavailable: {e.last_error}")
        if job_id:
            await _mark_degraded(job_id, "cms_pages", f"LLM down: {e.last_error}")
        return
    except ValueError as e:
        logger.warning(f"[launch] cms_pages JSON parse failed: {e}")
        if job_id:
            await _mark_degraded(job_id, "cms_pages", f"JSON parse: {e}")
        return

    if not isinstance(parsed, dict) or not parsed.get("about"):
        logger.warning("[launch] cms_pages malformed — skip")
        return

    # ────────────────────────────────────────────────────────────────────
    # Bloc 3 — Brand-prefix sur les H1 (about + contact) pour le SEO.
    # Le H1 d'une page corporate doit idéalement contenir le nom de marque
    # (signal SEO fort + cohérence éditoriale). Claude génère parfois un
    # titre "pur éditorial" qui n'inclut pas le brand → on préfixe ici.
    # Idempotent : si Claude a déjà mis le brand dans le titre, on ne
    # préfixe pas (évite "Altea — Altea, l'art …").
    # ────────────────────────────────────────────────────────────────────
    for slug in ("about", "contact"):
        page = parsed.get(slug)
        if isinstance(page, dict):
            original_title = (page.get("title") or "").strip()
            if original_title and brand_name and brand_name.lower() not in original_title.lower():
                page["title"] = f"{brand_name} — {original_title}"

    await db.sites.update_one(
        {"id": site_id},
        {"$set": {
            "design.cms_pages": parsed,
            "design.cms_pages_generated_at": datetime.now(timezone.utc).isoformat(),
        }},
    )
    logger.info("[launch] cms_pages (about+contact) persisted")


# ------------------------------------------------------------------
# Lot H Fix 6 — Color variant images (img-to-img) helper
# ------------------------------------------------------------------
async def _generate_color_variant_images_for_product(
    db,
    product_id: str,
    site_id: str,
    *,
    max_colors: int = 5,
    on_budget_exhausted=None,
):
    """Génère les images IA cohérentes pour les couleurs additionnelles d'un produit.

    Stratégie (cohérente avec scripts/lotH_h2h3_regen_color_variants.py) :
      - Lit `product.variants[].properties[0]` pour identifier les couleurs.
      - La 1ère couleur = "default" → COPIE les `generated_images` existants
        dans `generated_images_by_variant[default_slug]` (0 cost).
      - Pour les autres couleurs (jusqu'à `max_colors`) → génère
        studio + lifestyle + closeup via Nano Banana img-to-img avec
        prompt strict (préservation identité produit).

    Idempotent : skip les couleurs déjà présentes dans
    `generated_images_by_variant`. Tolérant aux 402 (budget) :
    propage l'exception au caller.

    Pour TOUS les futurs sites créés via launch-auto, cela garantit que la
    galerie variant-aware (Lot H Fix 4) fonctionne automatiquement.
    """
    from services.color_variant_images import (  # noqa: PLC0415
        slugify_color,
        generate_color_variant_image,
        detect_product_kind,
        color_label_to_english,
        _fetch_image_b64,
    )
    from services.colormapping_py import is_color_axis  # noqa: PLC0415 # below

    p = await db.products.find_one(
        {"id": product_id},
        {"_id": 0, "id": 1, "name": 1, "variants": 1, "generated_images": 1, "generated_images_by_variant": 1},
    )
    if not p:
        return
    variants = p.get("variants") or []
    if len(variants) <= 1:
        return  # mono-variant → pas de couleurs à générer

    # Extract the color axis (must be position 0 after H1 audit + must look like colors)
    raw_colors_pos0 = []
    for v in variants:
        props = v.get("properties") or []
        if props and props[0]:
            raw_colors_pos0.append(str(props[0]).strip())
    distinct_colors = list({c.lower(): c for c in raw_colors_pos0}.values())  # preserve original-cased
    if len(distinct_colors) <= 1:
        return  # 1 single color → no variant set needed
    if not is_color_axis(distinct_colors):
        # Not a color axis (e.g., size only) → nothing to do
        return

    # Reorder by appearance order
    seen = set()
    ordered = []
    for c in raw_colors_pos0:
        if c.lower() in seen:
            continue
        seen.add(c.lower())
        ordered.append(c)
    colors = ordered[: max_colors + 1]  # +1 because [0] = default
    default_color = colors[0]
    default_slug = slugify_color(default_color)
    other_colors = colors[1:]

    gi = p.get("generated_images") or []
    if not gi:
        logger.info(f"[launch] color-variants {product_id[:8]}: no generated_images yet — skip")
        return

    by_variant = dict(p.get("generated_images_by_variant") or {})

    # 1) Default color = copy from generated_images (0 LLM cost)
    if default_slug not in by_variant:
        by_variant[default_slug] = [
            {
                "style": img.get("style"),
                "url": img.get("url"),
                "color": default_color,
                "color_label": default_color,
                "generated_at": img.get("created_at") or datetime.now(timezone.utc).isoformat(),
                "source_style": img.get("style"),
                "tweak": "default-copy-from-generated_images",
            }
            for img in gi
        ]
        logger.info(f"[launch] color-variants {product_id[:8]}: default {default_slug} copied ({len(gi)} imgs)")

    # 2) Other colors = regen via img-to-img
    ref = next((img for img in gi if img.get("style") == "studio"), gi[0])
    ref_b64 = await _fetch_image_b64(ref.get("url"))
    if not ref_b64:
        logger.warning(f"[launch] color-variants {product_id[:8]}: ref not loadable — skip")
        return
    product_kind = detect_product_kind(p.get("name") or "")
    default_color_en = color_label_to_english(default_color)

    for color in other_colors:
        slug = slugify_color(color)
        if slug in by_variant and isinstance(by_variant[slug], list) and len(by_variant[slug]) >= len(gi):
            continue  # already done — idempotent skip
        target_color_en = color_label_to_english(color)
        color_imgs = []
        for img in gi:
            style = img.get("style", "studio")
            try:
                url = await generate_color_variant_image(
                    product_id=product_id,
                    color_slug=slug,
                    color_label=color,
                    target_color_label=target_color_en,
                    original_color_label=default_color_en,
                    style=style,
                    reference_image_b64=ref_b64,
                    product_kind=product_kind,
                )
            except Exception as e:
                msg = str(e)
                logger.warning(f"[launch] color-variant {product_id[:8]} {slug}/{style}: {msg[:120]}")
                if "402" in msg or "budget" in msg.lower():
                    raise
                continue
            if url:
                color_imgs.append({
                    "style": style,
                    "url": url,
                    "color": color,
                    "color_label": color,
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "source_style": style,
                    "tweak": "img-to-img-color",
                })
        if color_imgs:
            by_variant[slug] = color_imgs
            logger.info(f"[launch] color-variants {product_id[:8]}: {slug} = {len(color_imgs)} imgs")

    await db.products.update_one(
        {"id": product_id},
        {"$set": {
            "generated_images_by_variant": by_variant,
            "generated_images_by_variant_updated_at": datetime.now(timezone.utc).isoformat(),
        }},
    )


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

        # Pre-flight: if the LLM key is known to be out of budget, abort IMMEDIATELY
        # instead of wasting 10+ minutes on each content step timing out.
        health = await db.platform_health.find_one({"key": "llm"}, {"_id": 0})
        if health and health.get("status") == "budget_exhausted":
            await _update_job(job_id, {
                "status": "failed",
                "error": "Budget Emergent LLM Key épuisé. Recharge la clé (Profile → Universal Key → Add Balance) puis relance le wizard.",
                "completed_at": datetime.now(timezone.utc).isoformat(),
            })
            return

        site = await db.sites.find_one({"id": site_id}, {"_id": 0})
        if not site:
            raise Exception("Site introuvable")

        design = site.get("design") or {}
        overwrite = bool(wizard.get("overwrite_all"))

        # 1) Brand identity & palette -------------------------------------
        await _advance(job_id, "brand", "Identité de marque & palette", 5)
        # Sanitize brand name coming from the wizard (user may have typed "Test409" or
        # pasted markdown by mistake).
        _raw_name = (wizard.get("brand_name") or "").strip()
        _clean_name = _sanitize_brand_text(_raw_name, max_len=40) if _raw_name else ""
        _clean_tagline = _sanitize_brand_text((wizard.get("tagline") or "").strip(), max_len=80) if wizard.get("tagline") else ""
        _clean_mission = _sanitize_brand_text((wizard.get("mission") or "").strip(), max_len=400) if wizard.get("mission") else ""

        brand_patch = {
            "primary_color": (wizard.get("palette_choice") or {}).get("primary") or design.get("brand", {}).get("primary_color") or "#B84B31",
            "accent_color":  (wizard.get("palette_choice") or {}).get("accent")  or design.get("brand", {}).get("accent_color")  or "#E9C46A",
            "background_color": (wizard.get("palette_choice") or {}).get("background") or design.get("brand", {}).get("background_color") or "#FAF7F2",
            "text_color":    (wizard.get("palette_choice") or {}).get("text")    or design.get("brand", {}).get("text_color")    or "#1C1917",
            "font_heading":  (wizard.get("font_pair") or {}).get("heading") or design.get("brand", {}).get("font_heading") or "Fraunces",
            "font_body":     (wizard.get("font_pair") or {}).get("body")    or design.get("brand", {}).get("font_body")    or "Inter",
            "voice": wizard.get("voice") or design.get("brand", {}).get("voice") or "chaleureux et rassurant, premium",
        }
        # Brand name is the single source of truth — write it to BOTH `name` and `logo_text`
        # so the header image logo, header text fallback, footer text and © copyright all stay in sync.
        if _clean_name:
            brand_patch["name"] = _clean_name
            brand_patch["logo_text"] = _clean_name
        if _clean_tagline:
            brand_patch["tagline"] = _clean_tagline
        if _clean_mission:
            brand_patch["mission"] = _clean_mission
            brand_patch["story"] = _clean_mission

        # When the wizard runs in "overwrite" mode, ditch stale logo images and legacy logo_text
        # from previous generations — they would otherwise keep showing an older brand identity.
        if overwrite:
            brand_patch["logo_url"] = None

        await db.sites.update_one(
            {"id": site_id},
            {"$set": {
                "design.brand": {**design.get("brand", {}), **brand_patch},
                "design.updated_at": datetime.now(timezone.utc).isoformat(),
            }},
        )

        # 2) Logo premium horizontal (Nano Banana) ------------------------
        # Bloc 1 — sous-chantier 1c+1d :
        #   1c) skip si logo déjà présent (sauf overwrite=true)
        #   1d) routage propre vers /uploads/logos/ via design._nano_banana_logo
        await _advance(job_id, "logo", "Logo premium horizontal (Nano Banana)", 12)
        existing_logo = ((await db.sites.find_one({"id": site_id}, {"_id":0, "design.brand.logo_url":1})) or {}).get("design", {}).get("brand", {}).get("logo_url")
        if existing_logo and not overwrite:
            logger.info(f"[launch] logo already exists ({existing_logo[:60]}…), skipped")
        else:
            try:
                _logo_name = _clean_name or brand_patch.get("logo_text") or site.get("name") or "Maison"
                logo_prompt = (
                    f"Ultra-premium horizontal wordmark logo for a luxury French brand named "
                    f"« {_logo_name} ». "
                    "Editorial typography only (elegant light serif with subtle ligatures), "
                    "DEEP BLACK text (#0A0A0A) on a PURE WHITE background (#FFFFFF), no cream, no ivory, no off-white. "
                    "The background must be 100% white so it blends invisibly into a white website header. "
                    "Extremely refined kerning, tagline optional below in small caps. Aspect ratio 16:5 (horizontal, "
                    "wider than tall), with generous white margins on all sides. Absolutely NO icon, NO symbol, "
                    "NO flourish, NO framed box, NO colored background — pure typography only. "
                    "Museum-quality, think Hermès / Aesop / Loro Piana. High resolution, extremely sharp, "
                    "antialiased edges."
                )
                # Bloc 1 fix bug #1d : utiliser le helper dédié design._nano_banana_logo
                # qui écrit dans /uploads/logos/. Avant on utilisait product_images._generate_one
                # avec product_id="logo-{site_id[:8]}" → écrivait des fichiers parasites
                # `p_logo-XXX_*.png` dans /uploads/products_ai/.
                url = await asyncio.wait_for(
                    design_routes._nano_banana_logo(logo_prompt, site_id),
                    timeout=150,
                )
                if url:
                    # Lot G Fix 2 — Nano Banana ne respecte PAS toujours la consigne
                    # `transparent background`. On garde le prompt "fond blanc"
                    # (mieux respecté) puis on applique systématiquement le fallback
                    # Pillow `ensure_alpha_channel()` pour transformer le fond blanc
                    # opaque en transparence parfaite (anti-aliasing préservé).
                    try:
                        from services.favicon_generator import ensure_alpha_channel
                        from pathlib import Path as _Path
                        # url est de la forme /api/uploads/logos/xxx.png
                        rel = url.split("/api/uploads/", 1)
                        if len(rel) == 2:
                            disk_path = _Path("/app/backend/uploads") / rel[1]
                            if disk_path.exists():
                                cleaned = ensure_alpha_channel(disk_path)
                                cleaned.save(disk_path, format="PNG", optimize=True)
                                logger.info(f"[launch] logo cleaned to RGBA: {disk_path.name}")
                    except Exception as ce:
                        logger.warning(f"[launch] logo alpha cleanup failed: {ce}")

                    await db.sites.update_one(
                        {"id": site_id},
                        {"$set": {"design.brand.logo_url": url,
                                  "design.brand.logo_method": "nano-banana+pillow-cleaned",
                                  "design.updated_at": datetime.now(timezone.utc).isoformat()}},
                    )
                    # Lot A1 — Auto-generate favicons (5 sizes) from the logo PNG.
                    # 0 LLM, 0 cost. Idempotent : peut être ré-appelé.
                    try:
                        from services.favicon_generator import regenerate_and_persist_favicons
                        await regenerate_and_persist_favicons(site_id)
                    except Exception as fe:
                        logger.warning(f"[launch] favicon generation failed: {fe}")
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
        # Phase 0.5 fix — Le launch s'exécute en mode "service" (background) et doit
        # pouvoir orchestrer les routes internes même quand l'admin lance un site dont
        # il n'est pas operator_id. On utilise le rôle 'admin' pour by-pass l'ACL des
        # sous-routes (le check d'ACL initial sur /launch-auto a déjà été passé par
        # l'opérateur ou l'admin légitime au moment du POST).
        fake_user = {"id": user_id, "role": "admin"}
        budget_exhausted = False

        async def _check_budget_health() -> bool:
            """Re-read platform_health; if _claude_json just flagged budget_exhausted, stop."""
            h = await db.platform_health.find_one({"key": "llm"}, {"_id": 0})
            return bool(h and h.get("status") == "budget_exhausted")

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
                # After a timeout, re-check health — _claude_json may have hit
                # budget_exhausted inside the cancelled call and persisted the flag.
                if await _check_budget_health():
                    budget_exhausted = True
                    await _update_job(job_id, {"warning": "Budget Emergent LLM Key épuisé — génération interrompue."})
            except Exception as e:
                msg = str(e)
                status_code = getattr(e, "status_code", None)
                logger.warning(f"[launch] {section_key} failed: {msg[:120]}")
                if status_code == 402 or "402" in msg or ("budget" in msg.lower() and "exceed" in msg.lower()) or await _check_budget_health():
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

        # 5bis) Hero image IA (Nano Banana lifestyle 3:2) ------------------
        await _advance(job_id, "hero-image", "Image hero IA (lifestyle)", 54)
        # Bloc 1 sous-chantier 1c — skip si déjà présent
        existing_hero = ((await db.sites.find_one({"id": site_id}, {"_id": 0, "design.hero_image": 1})) or {}).get("design", {}).get("hero_image")
        if existing_hero and not overwrite:
            logger.info(f"[launch] hero-image already exists ({str(existing_hero)[:60]}…), skipped")
        elif not budget_exhausted:
            try:
                await asyncio.wait_for(
                    design_routes.generate_hero_image(
                        site_id=site_id,
                        data=design_routes.RegenInput(tweak=""),
                        user=fake_user,
                    ),
                    timeout=120,
                )
            except asyncio.TimeoutError:
                logger.warning("[launch] hero-image timed out")
            except Exception as e:
                logger.warning(f"[launch] hero-image failed: {str(e)[:120]}")

        # 5ter) Témoignages IA niche-adaptés (6 avis + portraits) ----------
        await _advance(job_id, "testimonials-ai", "6 avis + portraits IA (Nano Banana)", 56)
        if not budget_exhausted:
            try:
                from routes.testimonials_ai import _run_generation_bg, GenerateInput as TGenInput
                # Fire in background — storefront will display them once ready.
                # Don't block the launch job.
                fresh_site = await db.sites.find_one({"id": site_id}, {"_id": 0})
                if fresh_site:
                    asyncio.create_task(_run_generation_bg(
                        site_id,
                        fresh_site,
                        TGenInput(count=6, force=True, skip_images=False),
                    ))
            except Exception as e:
                logger.warning(f"[launch] testimonials-ai trigger failed: {str(e)[:120]}")

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

                # Backup l'image fournisseur d'origine AVANT toute régénération
                # (idempotent : on n'écrase jamais le backup s'il existe déjà).
                # Permet rollback si le user n'aime pas le rendu IA.
                try:
                    if not p.get("original_image"):
                        original_imgs = p.get("images") or []
                        if original_imgs:
                            await db.products.update_one(
                                {"id": p["id"]},
                                {"$set": {
                                    "original_image":  original_imgs[0],
                                    "original_images": list(original_imgs),
                                }},
                            )
                except Exception:
                    logger.warning(f"[launch] backup original_image p={p['id']} failed (non-blocking)")

                # 8a) narrative (if missing or overwrite)
                await _advance(
                    job_id,
                    f"product-{idx}-copy",
                    f"Fauteuil {idx+1}/{total_products} : copywriting éditorial…",
                    min(95, pct_now),
                )
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

                # 8a-bis) Lot I — Tagline (40-80 chars) + 4 USPs product-specific
                # Cheap (Haiku 4.5, ~$0.007/produit) and propagated to every new
                # site via the "from-scratch" rule (HANDOFF §13.11).
                # Skipped if budget exhausted or already present (idempotent).
                fresh_p = await db.products.find_one(
                    {"id": p["id"]},
                    {"_id": 0, "id": 1, "name": 1, "description": 1, "category": 1,
                     "price": 1, "currency": 1, "tagline": 1, "usps": 1, "narrative": 1},
                )
                if fresh_p and not budget_exhausted:
                    site_brand = (await db.sites.find_one(
                        {"id": site_id}, {"_id": 0, "design.brand": 1}
                    )) or {}
                    brand_dict = ((site_brand.get("design") or {}).get("brand") or {})

                    if overwrite or not fresh_p.get("tagline"):
                        try:
                            from services.product_content_ai import generate_product_tagline
                            tag = await asyncio.wait_for(
                                generate_product_tagline(fresh_p, brand_dict, request_id=f"launch-tag-{p['id'][:8]}"),
                                timeout=30,
                            )
                            if tag:
                                await db.products.update_one(
                                    {"id": p["id"]},
                                    {"$set": {
                                        "tagline": tag,
                                        "tagline_generated_at": datetime.now(timezone.utc).isoformat(),
                                    }},
                                )
                        except asyncio.TimeoutError:
                            logger.warning(f"[launch] tagline {p['id']} timed out")
                        except Exception as e:
                            msg = str(e)
                            logger.warning(f"[launch] tagline {p['id']}: {msg[:120]}")
                            if "402" in msg or "budget" in msg.lower():
                                budget_exhausted = True

                    if (overwrite or not fresh_p.get("usps")) and not budget_exhausted:
                        try:
                            from services.product_content_ai import generate_product_usps
                            usps = await asyncio.wait_for(
                                generate_product_usps(fresh_p, brand_dict, request_id=f"launch-usps-{p['id'][:8]}"),
                                timeout=45,
                            )
                            if usps and len(usps) >= 4:
                                await db.products.update_one(
                                    {"id": p["id"]},
                                    {"$set": {
                                        "usps": usps,
                                        "usps_generated_at": datetime.now(timezone.utc).isoformat(),
                                    }},
                                )
                        except asyncio.TimeoutError:
                            logger.warning(f"[launch] usps {p['id']} timed out")
                        except Exception as e:
                            msg = str(e)
                            logger.warning(f"[launch] usps {p['id']}: {msg[:120]}")
                            if "402" in msg or "budget" in msg.lower():
                                budget_exhausted = True

                    # 8a-ter (Phase 2.3 / Lot I I11) — HowTo steps (3-4 étapes, ton premium)
                    if (overwrite or not fresh_p.get("how_to_steps")) and not budget_exhausted:
                        try:
                            from services.product_content_ai import generate_product_how_to
                            steps = await asyncio.wait_for(
                                generate_product_how_to(
                                    fresh_p, brand_dict,
                                    n_steps=4,
                                    request_id=f"launch-howto-{p['id'][:8]}",
                                ),
                                timeout=45,
                            )
                            if steps and len(steps) >= 3:
                                await db.products.update_one(
                                    {"id": p["id"]},
                                    {"$set": {
                                        "how_to_steps": steps,
                                        "how_to_steps_generated_at": datetime.now(timezone.utc).isoformat(),
                                    }},
                                )
                        except asyncio.TimeoutError:
                            logger.warning(f"[launch] how-to {p['id']} timed out")
                        except Exception as e:
                            msg = str(e)
                            logger.warning(f"[launch] how-to {p['id']}: {msg[:120]}")
                            if "402" in msg or "budget" in msg.lower():
                                budget_exhausted = True

                    # 8a-quater (Phase 2.3 / Lot I I12) — FAQ produit (4-6 Q/R spécifiques)
                    if (overwrite or not fresh_p.get("faq_product")) and not budget_exhausted:
                        try:
                            from services.product_content_ai import generate_product_faq
                            faq = await asyncio.wait_for(
                                generate_product_faq(
                                    fresh_p, brand_dict,
                                    n_questions=5,
                                    request_id=f"launch-faq-{p['id'][:8]}",
                                ),
                                timeout=50,
                            )
                            if faq and len(faq) >= 3:
                                await db.products.update_one(
                                    {"id": p["id"]},
                                    {"$set": {
                                        "faq_product": faq,
                                        "faq_product_generated_at": datetime.now(timezone.utc).isoformat(),
                                    }},
                                )
                        except asyncio.TimeoutError:
                            logger.warning(f"[launch] faq {p['id']} timed out")
                        except Exception as e:
                            msg = str(e)
                            logger.warning(f"[launch] faq {p['id']}: {msg[:120]}")
                            if "402" in msg or "budget" in msg.lower():
                                budget_exhausted = True

                # 8b) 5 product hero images (use existing imported supplier images as base; add AI)
                await _advance(
                    job_id,
                    f"product-{idx}-images",
                    f"Fauteuil {idx+1}/{total_products} : images studio premium (5)…",
                    min(95, pct_now),
                )
                generated = p.get("generated_images") or []
                existing_ai_count = len(generated)
                # Bloc 1 sous-chantier 1b — 3 images IA premium par produit par défaut
                # (lifestyle, studio, closeup). Avant : 5 (incluait detail + in_use).
                # Économie : -40% coût Nano Banana par produit.
                # Le mode "Tout boost premium" (`boost_premium=true` dans wizard) bascule à 5.
                boost_premium = bool(wizard.get("boost_premium") or wizard.get("premium_5_images"))
                target_ai_count = 5 if boost_premium else 3
                # Lot C — studio en premier (image principale lue par getPrimaryImage)
                full_preset_order = ["studio", "lifestyle", "closeup", "detail", "in_use"]
                styles_to_gen = []
                # Bloc 1 sous-chantier 1c — skip si déjà target atteint (sauf overwrite)
                if not overwrite and existing_ai_count >= target_ai_count:
                    logger.info(f"[launch] product {p['id'][:8]} already has {existing_ai_count}≥{target_ai_count} AI images, skipped")
                elif overwrite or existing_ai_count < target_ai_count:
                    needed = target_ai_count if overwrite else max(0, target_ai_count - existing_ai_count)
                    styles_to_gen = full_preset_order[:needed]
                for style in styles_to_gen:
                    if budget_exhausted:
                        break
                    try:
                        await asyncio.wait_for(
                            pimg_routes.generate_product_image(
                                product_id=p["id"],
                                data=pimg_routes.GenProductImgInput(style=style, tweak="", replace_main=False),
                                user={"id": user_id, "role": "admin"},
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
                                    user={"id": user_id, "role": "admin"},
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

                # 8d) Lot H Fix 6 — Color variant images (img-to-img)
                # Si le produit a un axe couleur, génère le set d'images IA
                # POUR CHAQUE couleur additionnelle (max MAX_COLOR_VARIANTS_AI),
                # en partant de l'image studio comme référence visuelle stable.
                # Ainsi tout futur site créé via launch-auto a automatiquement
                # une galerie variant-aware (cohérente avec Lot H Fix 4 frontend).
                # Coût ~$0.05/image × ~3 styles × ~3-4 couleurs = ~$0.6/produit max.
                try:
                    if budget_exhausted:
                        pass
                    else:
                        await _generate_color_variant_images_for_product(
                            db, p["id"], site_id, max_colors=int(os.environ.get("MAX_COLOR_VARIANTS_AI", "5")),
                            on_budget_exhausted=lambda: None,  # signaled via raise below
                        )
                except Exception as e:
                    msg = str(e)
                    logger.warning(f"[launch] color-variants {p['id']}: {msg[:120]}")
                    if "402" in msg or "budget" in msg.lower():
                        budget_exhausted = True

                # 8e) Lot I Fix I7 — 8-styles pipeline (Phase 2.2)
                # Complète chaque variante couleur à 8 styles fixes premium :
                # studio_main, studio_card, lifestyle, wide_lifestyle (16:9),
                # closeup, detail, in_use, side_profile.
                # Hard cap 5$ par site (cumulatif sur tous les produits).
                # Idempotent : skip les styles déjà présents.
                # Conformément à la décision user 2026-04-27 (Q4) : déclenché
                # à l'étape 5 du Cockpit (= cette boucle de génération produit
                # dans launch.py).
                try:
                    if budget_exhausted:
                        pass
                    else:
                        from services.product_variant_pipeline import (  # noqa: PLC0415
                            BudgetCap, generate_full_variant_set,
                        )
                        # Per-product budget = remaining of site cap divided by remaining products
                        # MVP : simple per-product cap = 0.6$ to avoid one product eating it all.
                        per_product_cap = float(os.environ.get("MAX_VARIANT_PIPELINE_USD_PER_PRODUCT", "0.8"))
                        budget = BudgetCap(cap_usd=per_product_cap)
                        # Re-fetch product to get fresh by_variant
                        fresh_p = await db.products.find_one(
                            {"id": p["id"]},
                            {"_id": 0, "id": 1, "generated_images_by_variant": 1, "generated_images": 1},
                        )
                        by_variant = fresh_p.get("generated_images_by_variant") or {}
                        if not by_variant and fresh_p.get("generated_images"):
                            # Mono-variant product → still complete to 8 styles under "default" slug
                            by_variant = {"default": fresh_p["generated_images"]}
                        for color_slug in list(by_variant.keys()):
                            if budget.exhausted():
                                break
                            try:
                                await generate_full_variant_set(
                                    db, p["id"], color_slug,
                                    overwrite=False,
                                    budget=budget,
                                    request_id=f"launch-{site_id[:8]}-{p['id'][:8]}-{color_slug}",
                                )
                            except ValueError as e:
                                logger.info(f"[launch] 8-styles {p['id'][:8]}/{color_slug}: {str(e)[:80]}")
                            except Exception as e:
                                msg = str(e)
                                if "402" in msg or "budget" in msg.lower():
                                    budget_exhausted = True
                                    break
                                logger.warning(f"[launch] 8-styles {p['id'][:8]}/{color_slug}: {msg[:120]}")
                except Exception as e:
                    msg = str(e)
                    logger.warning(f"[launch] 8-styles outer {p['id']}: {msg[:120]}")
                    if "402" in msg or "budget" in msg.lower():
                        budget_exhausted = True

        # ── Phase C — Cohérence storefront enrichie ─────────────────────
        # Témoignages premium fictifs + portraits Nano Banana + pages CMS
        # (À propos / Contact) générées avec le narrative_angle.
        # Bloc 1 sous-chantier 1c — skip si déjà présents (sauf overwrite).
        fresh_design = ((await db.sites.find_one({"id": site_id}, {"_id": 0, "design.testimonials_premium": 1, "design.cms_pages": 1})) or {}).get("design") or {}
        existing_tp = fresh_design.get("testimonials_premium") or []
        existing_cms = fresh_design.get("cms_pages") or {}
        try:
            await _advance(job_id, "testimonials", "Témoignages clients (3 portraits IA)…", 95)
            if not overwrite and isinstance(existing_tp, list) and len(existing_tp) >= 3:
                logger.info(f"[launch] testimonials_premium already populated ({len(existing_tp)} items), skipped")
            else:
                await _generate_premium_testimonials(site_id, wizard, budget_exhausted, job_id=job_id)
        except Exception as e:
            logger.exception("[launch] premium_testimonials failed (non-blocking)")
            await _mark_degraded(job_id, "testimonials_premium", str(e)[:200])

        try:
            await _advance(job_id, "cms-pages", "Pages À propos / Contact éditoriales…", 97)
            if not overwrite and existing_cms.get("about") and existing_cms.get("contact"):
                logger.info("[launch] cms_pages already populated (about+contact), skipped")
            else:
                await _generate_premium_cms_pages(site_id, wizard, job_id=job_id)
        except Exception as e:
            logger.exception("[launch] cms_pages failed (non-blocking)")
            await _mark_degraded(job_id, "cms_pages", str(e)[:200])

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

        # Si des étapes sont en mode dégradé → status final
        # `completed_with_degraded` (le frontend pourra afficher un récap +
        # bouton "Relancer uniquement les étapes dégradées").
        final_doc = await db.launch_jobs.find_one({"id": job_id}, {"_id": 0, "degraded_steps": 1})
        degraded = (final_doc or {}).get("degraded_steps") or []
        final_status = "completed_with_degraded" if degraded else "completed"

        await _update_job(job_id, {
            "status":        final_status,
            "progress_pct":  100,
            "current_label": "Site généré !" + (f" ({len(degraded)} étape(s) en mode standard)" if degraded else ""),
            "completed_at":  datetime.now(timezone.utc).isoformat(),
        })

    except LLMUnavailableError as e:
        # LLM down → marquer le job comme `failed` MAIS resumable depuis la
        # dernière sous-étape connue (le checkpoint le plus récent).
        logger.warning(f"[launch] job {job_id} interrupted by LLM outage: {e.last_error}")
        last_cp = await db.launch_jobs.find_one(
            {"id": job_id}, {"_id": 0, "current_step": 1}
        )
        await _mark_failed_resumable(
            job_id,
            (last_cp or {}).get("current_step") or "unknown",
            f"LLM upstream down ({e.provider}): {e.last_error}",
        )
    except Exception as e:
        logger.exception(f"[launch] job {job_id} failed")
        await _update_job(job_id, {
            "status":       "failed",
            "error":        str(e)[:300],
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


# ------------------------------------------------------------------
# Auto-pilot endpoint : 1 click, full premium identity via Claude
# ------------------------------------------------------------------
import json as _json  # local alias to keep imports tight
import os as _os
import re as _re

_JSON_FENCE = _re.compile(r"^```(?:json)?\s*|\s*```\s*$", _re.MULTILINE)


def _pick_text_simple(value):
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        for k in ("fr", "en", "de", "es", "it", "nl"):
            if isinstance(value.get(k), str) and value[k].strip():
                return value[k]
        for v in value.values():
            if isinstance(v, str) and v.strip():
                return v
    return ""


async def _claude_brand_autoprefill(site_name: str, niche: str, products_titles: list[str]) -> dict:
    """Demande à Claude de générer une identité de marque ultra-premium complète.

    Retourne un dict avec brand_name, tagline, mission, voice, mood, palette,
    font_pair, hero_concept, narrative_angle. Lève HTTPException(502) si Claude
    indispo ou JSON invalide.
    """
    products_block = "\n".join(f"- « {t} »" for t in products_titles[:5] if t) or "(catalogue vide)"
    system_msg = (
        "Tu es directeur artistique senior d'agence de luxe (Apple, Hermès, Aesop, Dyson, "
        "Loro Piana). Tu réponds UNIQUEMENT en JSON valide, sans texte avant/après, sans "
        "markdown fence."
    )
    user_prompt = f"""Crée l'identité de marque ULTRA-PREMIUM pour cette boutique e-commerce.

Contexte :
- Nom du site : {site_name or "(non défini)"}
- Niche : {niche}
- Produits du catalogue :
{products_block}

Génère un JSON STRICT avec exactement ces clés :
{{
  "brand_name": "Nom de marque court et mémorable, 1-3 mots, élégant, jamais 'Pro'/'Plus'/'Shop'/'Store'",
  "tagline": "Phrase d'accroche premium, 6-10 mots, jamais 'Le meilleur choix'",
  "mission": "Mission de marque inspirante, 25-40 mots, orientée valeur humaine",
  "voice": "premium",
  "mood": "luxury_minimal",
  "palette": {{
    "primary": "#hexcode (couleur signature, raffinée, jamais cliché)",
    "accent": "#hexcode (accent subtil pour CTAs)",
    "background": "#hexcode (off-white ou ivoire chaud, jamais #ffffff pur)",
    "text": "#hexcode (anthracite ou sépia profond, jamais #000000 pur)",
    "rationale": "1 phrase justifiant les choix"
  }},
  "font_pair": {{
    "heading": "Cormorant Garamond",
    "body": "Inter",
    "rationale": "1 phrase justifiant l'association"
  }},
  "hero_concept": "Description du hero en 25-40 mots — photo lifestyle éditoriale, jamais stock photo générique",
  "narrative_angle": "Angle éditorial unique de la marque en 2 phrases"
}}

Règles strictes :
- voice ∈ {{"premium","warm","expert","minimal"}} (uniquement)
- mood ∈ {{"luxury_minimal","warm_premium","editorial","scandinavian"}} (uniquement)
- heading ∈ {{"Cormorant Garamond","Playfair Display","DM Serif Display","Fraunces"}}
- body    ∈ {{"Inter","Manrope","DM Sans","Nunito Sans"}}
- Pas de néon, pas de couleurs criardes
- Pour silver economy : tons profonds, terreux, ivoires, anthracites
- Tagline jamais générique
- Mission orientée valeur humaine, pas commerciale

Réponds UNIQUEMENT avec le JSON, sans rien autour."""

    try:
        # Bloc 1 — brand identity → quality_tier="premium" (Sonnet 4.5).
        # Coût ↑ mais c'est le DNA propagé dans tout le site, qualité non
        # négociable. Le reste du pipeline (témoignages, blog, narrative)
        # peut tomber sur Haiku par défaut.
        parsed = await safe_claude_json(system_msg, user_prompt, timeout=90, quality_tier="premium")
    except LLMUnavailableError as e:
        # 502 to UI : the upstream is OPEN — user should retry later
        raise HTTPException(
            502,
            f"IA indisponible (proxy upstream KO). Le breaker est {e.provider}={e.last_error or 'OPEN'}. "
            f"Réessaie dans quelques minutes ou lance la version manuelle."
        )
    except ValueError as e:
        raise HTTPException(502, f"Réponse IA mal formée : {e}")

    # Validation minimale
    required = ["brand_name", "tagline", "mission", "voice", "mood", "palette", "font_pair"]
    missing = [k for k in required if k not in parsed]
    if missing:
        raise HTTPException(502, f"Champs IA manquants : {missing}")

    # Coercion soft sur les valeurs autorisées
    if parsed["voice"] not in ("premium", "warm", "expert", "minimal"):
        parsed["voice"] = "premium"
    if parsed["mood"] not in ("luxury_minimal", "warm_premium", "editorial", "scandinavian"):
        parsed["mood"] = "luxury_minimal"
    if not isinstance(parsed["palette"], dict):
        parsed["palette"] = {"primary": "#1A1A1A", "accent": "#A87B5C",
                             "background": "#FAF7F2", "text": "#2A2A2A"}
    if not isinstance(parsed["font_pair"], dict):
        parsed["font_pair"] = {"heading": "Cormorant Garamond", "body": "Inter"}

    return parsed


@router.post("/sites/{site_id}/design/launch-auto", status_code=201)
async def launch_site_auto(
    site_id: str,
    user: dict = Depends(get_current_user),
):
    """One-click full auto generation — Claude pré-remplit toute l'identité de
    marque en mode ultra-premium puis lance le job de design existant.

    Le user n'a aucun champ à remplir : on charge le contexte (niche + produits),
    on demande à Claude une identité complète, on la passe au pipeline `_run_launch`
    classique (réutilisé tel quel — flag `premium_mode=True` propagé via le doc job).
    """
    await _check_site_access(site_id, user)

    site = await db.sites.find_one({"id": site_id}, {"_id": 0})
    if not site:
        raise HTTPException(404, "Site introuvable")

    # Anti-concurrence — mais auto-libère les jobs zombie (running + non-updated
    # depuis > 3 min). Cas typique : restart backend pendant un job, l'écran
    # LaunchProgress du user reste stuck à X%, le user re-clique → on ne le
    # bloque pas en 409 froid, on libère silencieusement et on relance.
    three_min_ago = (datetime.now(timezone.utc) - timedelta(minutes=3)).isoformat()
    await db.launch_jobs.update_many(
        {
            "site_id": site_id,
            "status": "running",
            "updated_at": {"$lt": three_min_ago},
        },
        {"$set": {
            "status": "failed",
            "error": "stale > 3min — auto-killed (relance)",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }},
    )
    running = await db.launch_jobs.find_one(
        {"site_id": site_id, "status": "running"}, {"_id": 0, "id": 1, "progress_pct": 1}
    )
    if running:
        raise HTTPException(
            409,
            f"Une génération est déjà en cours pour ce site "
            f"(job {running['id'][:8]}…, progression {running.get('progress_pct', 0)}%). "
            f"Patiente quelques secondes ou rafraîchis la page.",
        )

    # Charge le contexte (niche + 5 produits actifs)
    products_sample = await db.products.find(
        {"site_id": site_id, "status": "active"}, {"_id": 0, "name": 1, "title": 1},
    ).limit(5).to_list(5)
    products_titles = []
    for p in products_sample:
        t = _pick_text_simple(p.get("title")) or _pick_text_simple(p.get("name"))
        if t:
            products_titles.append(t[:120])

    niche = (
        site.get("niche") or site.get("niche_label") or site.get("category")
        or "premium e-commerce"
    )
    site_name = site.get("name") or ""

    # 1) Demande à Claude l'identité complète
    parsed = await _claude_brand_autoprefill(site_name, niche, products_titles)

    # 2) Construit le payload Wizard equivalent (réutilise WizardInput pour
    #    rester compatible avec _run_launch sans modifier ce dernier).
    wizard_payload = {
        "brand_name":      _sanitize_brand_text(parsed["brand_name"]),
        "tagline":         parsed["tagline"],
        "mission":         parsed["mission"],
        "voice":           parsed["voice"],
        "mood":            "Éditorial",  # mapping vers les 4 valeurs internes connues
        "palette_choice":  parsed["palette"],
        "font_pair":       parsed["font_pair"],
        "homepage_preset": "default_template",
        "overwrite_all":   True,
        "logo_style":      "horizontal_premium",
        # Hints supplémentaires pour _run_launch (ignorés s'il ne les lit pas
        # — pas de breaking change)
        "hero_concept":    parsed.get("hero_concept", ""),
        "narrative_angle": parsed.get("narrative_angle", ""),
        "premium_mode":    True,
    }

    # Mapping mood Claude → mood interne
    mood_map = {
        "luxury_minimal": "Minimaliste",
        "warm_premium":   "Chaleureux",
        "editorial":      "Éditorial",
        "scandinavian":   "Moderne",
    }
    wizard_payload["mood"] = mood_map.get(parsed["mood"], "Éditorial")

    # 3) Spawn le job (même infra que /design/launch)
    job_id = str(uuid.uuid4())
    await db.launch_jobs.insert_one({
        "id":              job_id,
        "site_id":         site_id,
        "user_id":         user["id"],
        "status":          "running",
        "progress_pct":    0,
        "current_step":    "start",
        "current_label":   "Conception de l'identité de marque…",
        "wizard":          wizard_payload,
        "auto_mode":       True,
        "premium_mode":    True,
        "auto_brand":      parsed,  # exposé au frontend pour affichage live
        "created_at":      datetime.now(timezone.utc).isoformat(),
    })

    asyncio.create_task(_run_launch(job_id, site_id, user["id"], wizard_payload))

    return {
        "ok":         True,
        "job_id":     job_id,
        "status":     "running",
        "auto_brand": parsed,  # le user voit ce que Claude a choisi
    }


@router.post("/sites/{site_id}/design/launch-jobs/{job_id}/abort")
async def abort_launch_job(
    site_id: str,
    job_id: str,
    user: dict = Depends(get_current_user),
):
    """Marque manuellement un job 'running' comme 'failed' pour libérer le
    verrou anti-concurrence. Utilisé par le bouton "Annuler et relancer" du
    LaunchProgress quand le job est figé > 90s.
    """
    await _check_site_access(site_id, user)
    res = await db.launch_jobs.update_one(
        {"id": job_id, "site_id": site_id, "status": "running"},
        {"$set": {
            "status":     "failed",
            "error":      "Annulé par l'utilisateur via LaunchProgress",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }},
    )
    return {"ok": True, "matched": res.matched_count, "modified": res.modified_count}


@router.post("/sites/{site_id}/design/launch-jobs/{job_id}/resume", tags=["launch-resilience"])
async def resume_launch_job(
    site_id: str,
    job_id: str,
    user: dict = Depends(get_current_user),
):
    """Reprend un job tombé en `failed` (ou `completed_with_degraded`) à partir
    de son dernier checkpoint, sans regénérer ce qui est déjà fait.

    - Refuse si le circuit breaker est OPEN (l'utilisateur doit attendre)
    - Refuse si le job n'est pas resumable (job pas connu, status=running, etc.)
    - Sinon : remet le job en `running`, conserve `checkpoints` et `degraded_steps`,
      et relance `_run_launch` qui sait skipper les étapes déjà réalisées
      grâce à ses tests d'idempotence (`if not p.get("narrative")`, etc.).
    """
    from services.llm_resilience import get_llm_health
    await _check_site_access(site_id, user)

    health = get_llm_health()
    claude_state = health["breakers"].get("claude", {}).get("state", "?")
    if claude_state == "OPEN":
        raise HTTPException(
            503,
            "Le proxy Claude est en panne (circuit breaker OPEN). "
            "Réessaie dans quelques minutes — le système retentera automatiquement."
        )

    job = await db.launch_jobs.find_one({"id": job_id, "site_id": site_id}, {"_id": 0})
    if not job:
        raise HTTPException(404, "Job introuvable")
    if job.get("status") == "running":
        raise HTTPException(409, "Le job est déjà en cours")
    if not job.get("resumable") and not job.get("degraded_steps"):
        raise HTTPException(
            400,
            "Ce job n'est pas reprenable (terminé sans erreur ou erreur applicative non récupérable). "
            "Lance une nouvelle génération."
        )

    # Reset state for resume
    await db.launch_jobs.update_one(
        {"id": job_id},
        {"$set": {
            "status":         "running",
            "resumed_at":     datetime.now(timezone.utc).isoformat(),
            "resume_count":   (job.get("resume_count") or 0) + 1,
            "error":          None,
            "current_label":  "Reprise du job…",
        }},
    )

    wizard = job.get("wizard") or {}
    asyncio.create_task(_run_launch(job_id, site_id, user["id"], wizard))
    return {
        "ok":             True,
        "job_id":         job_id,
        "resumed":        True,
        "resume_count":   (job.get("resume_count") or 0) + 1,
        "previous_step":  job.get("failed_step") or job.get("current_step"),
        "degraded_steps": job.get("degraded_steps") or [],
    }


async def auto_resume_failed_jobs():
    """Cron 5 min — repère les jobs `failed + resumable=true + auto_resume!=false`
    qui ont échoué dans les 30 dernières minutes ET dont le breaker Claude est
    revenu CLOSED/HALF_OPEN. Tente une reprise auto **une seule fois** par job.
    """
    from services.llm_resilience import get_llm_health
    health = get_llm_health()
    claude_state = health["breakers"].get("claude", {}).get("state", "?")
    if claude_state == "OPEN":
        logger.info("[auto-resume] Claude breaker OPEN — skip cycle")
        return

    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat()
    cursor = db.launch_jobs.find({
        "status":           "failed",
        "resumable":        True,
        "failed_at":        {"$gte": cutoff},
        "auto_resume":      {"$ne": False},
        "auto_resumed_at":  {"$exists": False},   # 1× max
    }, {"_id": 0, "id": 1, "site_id": 1, "user_id": 1, "wizard": 1})
    async for job in cursor:
        try:
            await db.launch_jobs.update_one(
                {"id": job["id"]},
                {"$set": {
                    "status":          "running",
                    "auto_resumed_at": datetime.now(timezone.utc).isoformat(),
                    "current_label":   "Reprise automatique…",
                    "error":           None,
                }},
            )
            asyncio.create_task(_run_launch(
                job["id"], job["site_id"], job.get("user_id") or "auto",
                job.get("wizard") or {},
            ))
            logger.info(f"[auto-resume] kicked job={job['id'][:8]} site={job['site_id'][:8]}")
        except Exception:
            logger.exception(f"[auto-resume] failed for job={job.get('id')}")

