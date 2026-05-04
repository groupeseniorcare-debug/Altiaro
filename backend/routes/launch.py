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

from fastapi import APIRouter, HTTPException, Depends, Query
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
    now_iso = datetime.now(timezone.utc).isoformat()
    patch["updated_at"] = now_iso
    # Heartbeat universel : tout update du job rafraîchit `last_heartbeat_at`.
    # Le frontend peut donc détecter `is_stale` même quand on n'est pas dans
    # une boucle items (phases d'initialisation, brand, content, etc.).
    patch.setdefault("last_heartbeat_at", now_iso)
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


async def _mark_degraded(job_id: str, step_key: str, reason: str, message: str = ""):
    """Marque une sous-étape comme dégradée (LLM down, budget, parse, etc.)
    pour qu'elle soit affichée en orange dans le LaunchProgress et puisse être
    relancée à part.

    Args:
        reason: code machine ("llm_budget_cap", "api_error", "timeout", ...).
        message: libellé FR premium pour l'utilisateur. Si vide, dérivé de `reason`.
    """
    pretty_reasons = {
        "llm_budget_cap": "Plafond IA atteint pour aujourd'hui",
        "api_error":      "Service IA temporairement indisponible",
        "timeout":        "Délai dépassé sur cette étape",
        "parse_error":    "Réponse IA non exploitable, sera relancée",
    }
    msg = message or pretty_reasons.get((reason or "").lower(), reason or "non disponible")
    await db.launch_jobs.update_one(
        {"id": job_id, "degraded_steps.step": {"$ne": step_key}},
        {"$push": {"degraded_steps": {
            "step":       step_key,
            "reason":     (reason or "")[:80],
            "message":    msg[:240],
            "skipped_at": datetime.now(timezone.utc).isoformat(),
            "ts":         datetime.now(timezone.utc).isoformat(),
        }}},
    )
    logger.warning(f"[launch:{job_id}] step={step_key} → DEGRADED ({reason}: {msg[:80]})")


async def _set_items_progress(
    job_id: str,
    items_done: int,
    items_total: int,
    current_item_label: str = "",
    *,
    reset: bool = False,
):
    """Écrit la micro-progression d'une boucle (images, narrative, pages…) +
    refresh `last_heartbeat_at` pour neutraliser la détection `is_stale`.

    Usage :
        await _set_items_progress(job_id, 0, 9, "", reset=True)   # init boucle
        for i, p in enumerate(products):
            await _set_items_progress(job_id, i, 9, f"Produit {p.name}…")
            # ... travail …
            await _set_items_progress(job_id, i + 1, 9, f"Produit {p.name} terminé")
    """
    label = (current_item_label or "")[:160]
    now_iso = datetime.now(timezone.utc).isoformat()
    patch = {
        "step_progress.items_done":          int(items_done),
        "step_progress.items_total":         int(items_total),
        "step_progress.current_item_label":  label,
        "step_progress.updated_at":          now_iso,
        "last_heartbeat_at":                 now_iso,
        "updated_at":                        now_iso,
    }
    if reset:
        # Permet au frontend de remettre le compteur à 0 quand on change de phase
        patch["step_progress.phase_started_at"] = now_iso
    await db.launch_jobs.update_one({"id": job_id}, {"$set": patch})


async def _heartbeat(job_id: str):
    """Mini-helper : ne touche que le heartbeat. À appeler dans les longues
    sous-tâches (Nano Banana 60-120 s) pour rassurer le frontend."""
    now_iso = datetime.now(timezone.utc).isoformat()
    await db.launch_jobs.update_one(
        {"id": job_id},
        {"$set": {"last_heartbeat_at": now_iso, "updated_at": now_iso}},
    )


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
    # Phase 4 — instrumentation cost tracker
    from services import cost_tracker as _ct
    _ct.start_job(job_id)
    # Capture snapshot Emergent budget AVANT (delta après = coût réel facturé)
    try:
        snap = await db.platform_health.find_one({"key": "llm_budget"}, {"_id": 0})
        if snap and snap.get("used_usd") is not None:
            _ct.attach_emergent_before(job_id, float(snap["used_usd"]))
    except Exception:
        pass

    with _ct.job_context(job_id):
        await _run_launch_inner(job_id, site_id, user_id, wizard)

    # Persiste le coût final dans launch_jobs.cost_summary
    summary = _ct.end_job(job_id)
    if summary:
        try:
            snap = await db.platform_health.find_one({"key": "llm_budget"}, {"_id": 0})
            if snap and snap.get("used_usd") is not None:
                summary.emergent_used_usd_after = float(snap["used_usd"])
        except Exception:
            pass
        try:
            await db.launch_jobs.update_one(
                {"id": job_id},
                {"$set": {"cost_summary": summary.to_dict()}},
            )
            logger.info(
                f"[launch:{job_id[:8]}] cost_summary persisted: "
                f"total=${summary.total_usd:.4f} ({summary.claude_calls} Claude / "
                f"{summary.image_calls} images)"
            )
        except Exception as e:
            logger.warning(f"[launch:{job_id[:8]}] cost_summary persist failed: {e}")


async def _run_launch_inner(job_id: str, site_id: str, user_id: str, wizard: dict):
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
        from services import cost_tracker as _ct
        _ct._current_bucket.set("brand")
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
                    # Phase 3.3 Fix 1.2 — Auto-generate the typographic wordmark
                    # (Pillow pure, no LLM, ~50 ms, transparent PNG) so the
                    # storefront header displays a proper brand wordmark
                    # instead of the abstract Nano Banana pictogram.
                    try:
                        from services.wordmark_generator import persist_wordmark_for_site
                        fresh = await db.sites.find_one(
                            {"id": site_id},
                            {"_id": 0, "design.brand.name": 1, "design.brand.primary_color": 1,
                             "design.brand.accent_color": 1, "name": 1},
                        )
                        fresh_brand = ((fresh or {}).get("design") or {}).get("brand") or {}
                        wm_name = (fresh_brand.get("name") or (fresh or {}).get("name")
                                   or _logo_name or "Maison")
                        wm_palette = {
                            "primary_color": fresh_brand.get("primary_color"),
                            "accent_color": fresh_brand.get("accent_color"),
                        }
                        await persist_wordmark_for_site(site_id, wm_name, wm_palette)
                    except Exception as we:
                        logger.warning(f"[launch] wordmark generation failed: {we}")
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
        # Phase 3 bis — Parallélisation Nano Banana
        # Les générations d'images IA (hero + sections) sont lancées en
        # parallèle via asyncio.gather, mais bornées par un Semaphore global
        # à `LAUNCH_IMAGE_CONCURRENCY` (default 4) pour ne pas saturer
        # l'API et préserver le worker uvicorn (chaque image bloque ~60-90 s).
        try:
            _img_concurrency = int(os.environ.get("LAUNCH_IMAGE_CONCURRENCY", "4"))
        except (TypeError, ValueError):
            _img_concurrency = 4
        _img_concurrency = max(1, min(_img_concurrency, 8))
        _IMG_SEM = asyncio.Semaphore(_img_concurrency)
        # Dict mutable partagé entre coroutines parallèles pour propager
        # l'épuisement budget (asyncio.gather n'autorise pas `nonlocal` simple
        # sur un bool depuis une closure définie dans la boucle).
        nonlocal_budget = {"exhausted": False}

        async def _check_budget_health() -> bool:
            """Re-read platform_health; if _claude_json just flagged budget_exhausted, stop."""
            h = await db.platform_health.find_one({"key": "llm"}, {"_id": 0})
            return bool(h and h.get("status") == "budget_exhausted")

        for section_key, label, pct in content_steps:
            await _advance(job_id, f"content-{section_key}", label, pct)
            # Switch bucket to "content" pour cette phase (idempotent).
            _ct._current_bucket.set("content")
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
        # Sprint 2.3 — adapt legal templates to the niche via Claude Haiku.
        # Idempotent : skip if already done. Best-effort : si l'IA échoue, on
        # garde les templates standards déjà injectés ci-dessus.
        try:
            existing_legal = (site2.get("legal") or {})
            niche_already_done = any(
                isinstance(v, dict) and v.get("niche_adapted") for v in existing_legal.values()
            )
            if not niche_already_done and not budget_exhausted:
                from services.legal_niche_adapter import adapt_legal_for_niche
                niche = site2.get("niche") or "e-commerce premium"
                # base_texts : on prend le markdown injecté à l'étape précédente
                legal_pages = design2.get("legal_pages") or {}
                base = {}
                for k in ("cgv", "mentions", "confidentialite", "livraison", "retours"):
                    v = legal_pages.get(k) or {}
                    if isinstance(v, dict):
                        base[k] = v.get("body_md") or v.get("body") or ""
                    elif isinstance(v, str):
                        base[k] = v
                base = {k: v for k, v in base.items() if v}
                if base:
                    adapted = await adapt_legal_for_niche(site_id, niche, base)
                    update_payload = {}
                    now_iso = datetime.now(timezone.utc).isoformat()
                    for k, text in adapted.items():
                        update_payload[f"legal.{k}.body_md"] = text
                        update_payload[f"legal.{k}.niche_adapted"] = True
                        update_payload[f"legal.{k}.niche"] = niche
                        update_payload[f"legal.{k}.updated_at"] = now_iso
                    if update_payload:
                        await db.sites.update_one({"id": site_id}, {"$set": update_payload})
                        logger.info(f"[launch] legal pages adapted to niche '{niche}' "
                                    f"({len(adapted)} sections)")
        except Exception as e:
            logger.warning(f"[launch] legal niche adaptation skipped: {str(e)[:160]}")

        # Sprint 4 Fix 6 — Bandeaux réassurance fiche produit, niche-aware.
        # Idempotent : skip si design.reassurance_badges déjà rempli.
        # Best-effort : fallback statique 4 badges génériques si l'IA échoue.
        try:
            current_badges = (design2.get("reassurance_badges") or [])
            if not current_badges and not budget_exhausted:
                niche_for_badges = site2.get("niche") or "e-commerce premium"
                primary_lang = site2.get("primary_lang") or "fr"
                from services.llm_resilience import safe_claude_json
                badges_system = (
                    "Tu es expert UX copywriter e-commerce premium. Tu rédiges "
                    "des bandeaux de réassurance courts (max 4 mots chacun) "
                    f"pour une fiche produit dans la niche « {niche_for_badges} ». "
                    "Les bandeaux doivent être CONCRETS et spécifiques à la "
                    "niche (pas génériques). Réponds UNIQUEMENT en JSON valide."
                )
                badges_user = (
                    f"Produis 5 bandeaux réassurance pour la niche « {niche_for_badges} »."
                    f" Langue principale : {primary_lang}.\n"
                    "Schéma JSON strict :\n"
                    "{\n"
                    "  \"badges\": [\n"
                    "    {\"icon\": \"ShieldCheck|Truck|Phone|ArrowsClockwise|Heart|Medal|Clock|Lightning|HandHeart|ThumbsUp|CheckCircle|Certificate\", "
                    "\"title\": {\"fr\":\"...\",\"en\":\"...\",\"de\":\"...\",\"nl\":\"...\"}, "
                    "\"subtitle\": {\"fr\":\"...\",\"en\":\"...\",\"de\":\"...\",\"nl\":\"...\"}}\n"
                    "  ]\n"
                    "}\n"
                    "Exemples attendus pour fauteuil releveur médical : "
                    "« Remboursement LPP possible · Sur prescription médicale », "
                    "« Livraison + installation · Par technicien agréé », "
                    "« Garantie 3 ans · Pièces incluses », "
                    "« SAV 7j/7 · Support téléphonique », "
                    "« Dispositif médical CE · Classe I certifié ».\n"
                    "Tu DOIS adapter aux spécificités de la niche."
                )
                badges_json = await safe_claude_json(
                    system=badges_system, user=badges_user,
                    quality_tier="speed",
                    request_id=f"reassurance-{site_id[:8]}",
                    timeout=60,
                )
                badges_list = (badges_json or {}).get("badges") or []
                # Validation + sanitize
                clean_badges = []
                VALID_ICONS = {
                    "ShieldCheck", "Truck", "Phone", "ArrowsClockwise", "Heart",
                    "Medal", "Clock", "Lightning", "HandHeart", "ThumbsUp",
                    "CheckCircle", "Certificate",
                }
                for b in badges_list[:6]:
                    if not isinstance(b, dict):
                        continue
                    icon = b.get("icon") or "ShieldCheck"
                    if icon not in VALID_ICONS:
                        icon = "ShieldCheck"
                    title = b.get("title") or {}
                    subtitle = b.get("subtitle") or {}
                    if not isinstance(title, dict):
                        title = {"fr": str(title)}
                    if not isinstance(subtitle, dict):
                        subtitle = {"fr": str(subtitle)}
                    if title.get(primary_lang):
                        clean_badges.append({
                            "icon": icon,
                            "title": title,
                            "subtitle": subtitle,
                        })
                if len(clean_badges) >= 3:
                    now_iso = datetime.now(timezone.utc).isoformat()
                    await db.sites.update_one(
                        {"id": site_id},
                        {"$set": {
                            "design.reassurance_badges": clean_badges,
                            "design.reassurance_badges_niche": niche_for_badges,
                            "design.reassurance_badges_generated_at": now_iso,
                        }},
                    )
                    logger.info(f"[launch] reassurance_badges generated ({len(clean_badges)}) "
                                f"for niche '{niche_for_badges}'")
        except Exception as e:
            logger.warning(f"[launch] reassurance_badges generation skipped: {str(e)[:160]}")

        # 8) Products — narrative + images (biggest step) ------------------
        # Phase 4 — bucket : on tagge "content" pour copywriting et "images"
        # pour les générations Nano Banana (basculé inline ci-dessous).
        _ct._current_bucket.set("content")
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
            # Init micro-progression : 0/N, label vide
            await _set_items_progress(
                job_id, 0, total_products,
                "Préparation des fiches produits…", reset=True,
            )
            for idx, p in enumerate(products):
                if budget_exhausted:
                    logger.info("[launch] skip remaining products (budget)")
                    await _mark_degraded(
                        job_id, f"products-remaining-{idx}",
                        "llm_budget_cap",
                        f"{total_products - idx} produits restants à enrichir lorsque le budget IA sera renouvelé",
                    )
                    break
                name = p.get("name", {})
                if isinstance(name, dict):
                    label_name = name.get("fr") or name.get("en") or "(produit)"
                else:
                    label_name = str(name)

                # Phase 4 — Fix resume idempotent : early-skip si déjà enrichi.
                # On lit `generated_images` (champ persisté sur le doc produit) et
                # `narrative` pour décider. MIN_IMAGES_THRESHOLD=3 + narrative
                # complète = produit considéré "OK", on ne reboucle plus dessus.
                MIN_IMAGES_THRESHOLD = 3
                existing_imgs_count = len(p.get("generated_images") or [])
                _narr = p.get("narrative") or {}
                has_narrative = bool(
                    (_narr.get("sections") if isinstance(_narr, dict) else None)
                    or (_narr.get("long_text") if isinstance(_narr, dict) else None)
                )
                if (
                    not overwrite
                    and existing_imgs_count >= MIN_IMAGES_THRESHOLD
                    and has_narrative
                ):
                    logger.info(
                        f"[launch] skip product {p['id'][:8]} "
                        f"(already enriched: {existing_imgs_count} imgs + narrative)"
                    )
                    await _set_items_progress(
                        job_id, idx + 1, total_products,
                        f"Fiche {idx+1}/{total_products} — déjà enrichie, skip",
                    )
                    continue
                    break
                pct_now = 65 + per_step * idx
                name = p.get("name", {})
                if isinstance(name, dict):
                    label_name = name.get("fr") or name.get("en") or "(produit)"
                else:
                    label_name = str(name)
                # Avance globale (% pipeline) + micro-progression (items_done/total)
                await _advance(
                    job_id,
                    f"product-{idx}",
                    f"Fiche produit {idx+1}/{total_products} — {label_name[:32]}",
                    min(95, pct_now),
                )
                await _set_items_progress(
                    job_id, idx, total_products,
                    f"Fiche {idx+1}/{total_products} — {label_name[:60]}",
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
                _ct._current_bucket.set("content")
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
                    # Phase 2.6 Tâche C — retour passé en dict {section_title,
                    # product_kind, steps}. On stocke aussi `how_to_steps_meta`
                    # pour piloter le H2 frontend selon le type de produit.
                    if (overwrite or not fresh_p.get("how_to_steps")) and not budget_exhausted:
                        try:
                            from services.product_content_ai import generate_product_how_to
                            howto = await asyncio.wait_for(
                                generate_product_how_to(
                                    fresh_p, brand_dict,
                                    n_steps=4,
                                    request_id=f"launch-howto-{p['id'][:8]}",
                                ),
                                timeout=45,
                            )
                            steps = (howto or {}).get("steps") or []
                            if steps and len(steps) >= 3:
                                meta = {
                                    "section_title": (howto or {}).get("section_title") or {},
                                    "product_kind":  (howto or {}).get("product_kind") or "generic",
                                }
                                await db.products.update_one(
                                    {"id": p["id"]},
                                    {"$set": {
                                        "how_to_steps": steps,
                                        "how_to_steps_meta": meta,
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

                    # 8a-cinq (Phase 2.5 / Tâche A) — Editorial cards (1 hero + 3 cards)
                    if (overwrite or not fresh_p.get("editorial_cards")) and not budget_exhausted:
                        try:
                            from services.product_content_ai import generate_product_editorial_cards
                            cards = await asyncio.wait_for(
                                generate_product_editorial_cards(
                                    fresh_p, brand_dict, n_cards=3,
                                    request_id=f"launch-editorial-{p['id'][:8]}",
                                ),
                                timeout=50,
                            )
                            if cards and cards.get("hero") and cards.get("cards"):
                                await db.products.update_one(
                                    {"id": p["id"]},
                                    {"$set": {
                                        "editorial_cards": cards,
                                        "editorial_cards_generated_at": datetime.now(timezone.utc).isoformat(),
                                    }},
                                )
                        except asyncio.TimeoutError:
                            logger.warning(f"[launch] editorial {p['id']} timed out")
                        except Exception as e:
                            msg = str(e)
                            logger.warning(f"[launch] editorial {p['id']}: {msg[:120]}")
                            if "402" in msg or "budget" in msg.lower():
                                budget_exhausted = True

                # 8b) Product images — parallélisées via sémaphore global Nano Banana.
                # Bucket switch → "images"
                _ct._current_bucket.set("images")
                # Avant : 3 styles × 60-90 s = 180-270 s en série.
                # Après : ≤ N concurrents → temps ~max(image) = 60-90 s.
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

                async def _gen_one_hero(style):
                    if budget_exhausted:
                        return
                    async with _IMG_SEM:
                        if budget_exhausted:
                            return
                        try:
                            await asyncio.wait_for(
                                pimg_routes.generate_product_image(
                                    product_id=p["id"],
                                    data=pimg_routes.GenProductImgInput(style=style, tweak="", replace_main=False),
                                    user={"id": user_id, "role": "admin"},
                                ),
                                timeout=120,
                            )
                            await _heartbeat(job_id)
                        except asyncio.TimeoutError:
                            logger.warning(f"[launch] img {style} {p['id']} timed out")
                        except Exception as e:
                            msg = str(e)
                            logger.warning(f"[launch] img {style} {p['id']}: {msg[:120]}")
                            if "402" in msg or "budget" in msg.lower():
                                nonlocal_budget["exhausted"] = True
                if styles_to_gen and not budget_exhausted:
                    await asyncio.gather(*[_gen_one_hero(s) for s in styles_to_gen], return_exceptions=True)
                if nonlocal_budget["exhausted"]:
                    budget_exhausted = True

                # 8c) 2 narrative-section images (parallèles)
                try:
                    fresh = await db.products.find_one({"id": p["id"]}, {"_id": 0, "narrative.sections": 1})
                    narr_sections = ((fresh or {}).get("narrative") or {}).get("sections") or []
                    sec_targets = []
                    for sec_idx in range(min(2, len(narr_sections))):
                        sec = narr_sections[sec_idx]
                        if not overwrite and sec.get("image"):
                            continue
                        sec_targets.append(sec_idx)

                    async def _gen_one_section(sec_idx):
                        if budget_exhausted:
                            return
                        async with _IMG_SEM:
                            if budget_exhausted:
                                return
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
                                await _heartbeat(job_id)
                            except asyncio.TimeoutError:
                                logger.warning(f"[launch] section-img p={p['id']} i={sec_idx} timed out")
                            except Exception as e:
                                msg = str(e)
                                logger.warning(f"[launch] section-img p={p['id']} i={sec_idx}: {msg[:120]}")
                                if "402" in msg or "budget" in msg.lower():
                                    nonlocal_budget["exhausted"] = True

                    if sec_targets and not budget_exhausted:
                        await asyncio.gather(*[_gen_one_section(s) for s in sec_targets], return_exceptions=True)
                    if nonlocal_budget["exhausted"]:
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

                # Fin d'itération produit : on incrémente le compteur global
                # de la phase Produits (et on rafraîchit le heartbeat).
                await _set_items_progress(
                    job_id, idx + 1, total_products,
                    f"{idx+1}/{total_products} produits enrichis",
                )

        # ── Phase C — Cohérence storefront enrichie ─────────────────────
        # Témoignages premium fictifs + portraits Nano Banana + pages CMS
        # (À propos / Contact) générées avec le narrative_angle.
        # Bloc 1 sous-chantier 1c — skip si déjà présents (sauf overwrite).
        await _set_items_progress(
            job_id, 0, 4,
            "Assemblage du storefront (témoignages, pages éditoriales)",
            reset=True,
        )
        fresh_design = ((await db.sites.find_one({"id": site_id}, {"_id": 0, "design.testimonials_premium": 1, "design.cms_pages": 1})) or {}).get("design") or {}
        existing_tp = fresh_design.get("testimonials_premium") or []
        existing_cms = fresh_design.get("cms_pages") or {}
        try:
            await _advance(job_id, "testimonials", "Témoignages clients (3 portraits IA)…", 95)
            await _set_items_progress(job_id, 1, 4, "Témoignages clients (3 portraits IA)…")
            if not overwrite and isinstance(existing_tp, list) and len(existing_tp) >= 3:
                logger.info(f"[launch] testimonials_premium already populated ({len(existing_tp)} items), skipped")
            else:
                await _generate_premium_testimonials(site_id, wizard, budget_exhausted, job_id=job_id)
        except Exception as e:
            logger.exception("[launch] premium_testimonials failed (non-blocking)")
            await _mark_degraded(
                job_id, "testimonials_premium",
                "llm_budget_cap" if "402" in str(e) or "budget" in str(e).lower() else "api_error",
                f"Témoignages premium reportés ({str(e)[:120]})",
            )

        try:
            await _advance(job_id, "cms-pages", "Pages À propos / Contact éditoriales…", 97)
            await _set_items_progress(job_id, 2, 4, "Pages éditoriales (À propos, Contact)…")
            if not overwrite and existing_cms.get("about") and existing_cms.get("contact"):
                logger.info("[launch] cms_pages already populated (about+contact), skipped")
            else:
                await _generate_premium_cms_pages(site_id, wizard, job_id=job_id)
        except Exception as e:
            logger.exception("[launch] cms_pages failed (non-blocking)")
            await _mark_degraded(
                job_id, "cms_pages",
                "llm_budget_cap" if "402" in str(e) or "budget" in str(e).lower() else "api_error",
                f"Pages éditoriales reportées ({str(e)[:120]})",
            )

        # ── Phase 2.6 Tâche D — BrandStory (texte + visuel atelier) ─────
        # Remplace l'ancienne section <FounderStory> "Camille Lefèvre"
        # fictive par une section "Notre maison" qui parle de la marque
        # comme entité (atelier, savoir-faire, ancrage France).
        # Skip si déjà populé (sauf overwrite). Skip image si budget LLM
        # cap atteint, mais le texte (Haiku) tente quand même.
        try:
            await _advance(job_id, "brand-story", "Notre maison (atelier + texte)…", 98)
            await _set_items_progress(job_id, 3, 4, "Notre maison (atelier + texte)…")
            fresh_brand = ((await db.sites.find_one(
                {"id": site_id},
                {"_id": 0, "design.brand": 1, "niche": 1, "design.cms_pages": 1},
            )) or {})
            brand_dict_bs = (fresh_brand.get("design") or {}).get("brand") or {}
            niche_bs = fresh_brand.get("niche") or wizard.get("niche") or ""
            existing_ws = bool(brand_dict_bs.get("workshop_story")) and bool(brand_dict_bs.get("workshop_image"))
            if not overwrite and existing_ws:
                logger.info("[launch] brand_story already populated, skipped")
            else:
                from services.brand_story import (
                    generate_brand_story_text,
                    generate_brand_workshop_image_bytes,
                )
                # 1) Texte (Haiku) — peut passer même budget tendu
                story_set: dict = {}
                if not budget_exhausted:
                    try:
                        bs_text = await asyncio.wait_for(
                            generate_brand_story_text(brand_dict_bs, niche=niche_bs,
                                                       request_id=f"launch-brandstory-{site_id[:8]}"),
                            timeout=40,
                        )
                        if bs_text and isinstance(bs_text, dict):
                            story_set["design.brand.workshop_story"] = bs_text
                    except asyncio.TimeoutError:
                        await _mark_degraded(job_id, "brand_story_text", "timeout 40s")
                    except Exception as e:
                        msg = str(e)
                        await _mark_degraded(job_id, "brand_story_text", msg[:200])
                        if "402" in msg or "budget" in msg.lower():
                            budget_exhausted = True

                # 2) Image atelier (Nano Banana) — skip dur si budget cap
                if not budget_exhausted:
                    try:
                        img_bytes = await asyncio.wait_for(
                            generate_brand_workshop_image_bytes(
                                brand_dict_bs, niche=niche_bs,
                                request_id=f"launch-workshop-img-{site_id[:8]}",
                            ),
                            timeout=130,
                        )
                        if img_bytes:
                            # Persist sous /uploads/sites/{site_id}/brand/workshop_*.jpg
                            from deps import UPLOAD_DIR
                            out_dir = UPLOAD_DIR / "sites" / site_id / "brand"
                            out_dir.mkdir(parents=True, exist_ok=True)
                            fname = f"workshop_{uuid.uuid4().hex[:8]}.jpg"
                            (out_dir / fname).write_bytes(img_bytes)
                            url = f"/api/uploads/sites/{site_id}/brand/{fname}"
                            story_set["design.brand.workshop_image"] = url
                    except asyncio.TimeoutError:
                        await _mark_degraded(job_id, "brand_story_image", "timeout 130s")
                    except Exception as e:
                        msg = str(e)
                        await _mark_degraded(job_id, "brand_story_image", msg[:200])
                        if "402" in msg or "budget" in msg.lower():
                            budget_exhausted = True
                else:
                    await _mark_degraded(job_id, "brand_story_image",
                                         "skipped: LLM budget cap reached")

                if story_set:
                    story_set["design.brand.workshop_generated_at"] = datetime.now(timezone.utc).isoformat()
                    await db.sites.update_one({"id": site_id}, {"$set": story_set})
                    logger.info(f"[launch] brand_story persisted: {list(story_set.keys())}")
        except Exception as e:
            logger.exception("[launch] brand_story failed (non-blocking)")
            await _mark_degraded(job_id, "brand_story", str(e)[:200])

        # ── Phase 2.6 Tâche E — Photos client lifestyle (pilote uniquement) ─
        # Génère 4 photos lifestyle "client" Nano Banana pour le produit
        # pilote (le 1er ou le `featured`). Cap budget : skip + degraded.
        try:
            await _advance(job_id, "review-photos", "Photos client (4 scènes lifestyle)…", 99)
            # Pick pilot product : featured or first
            pilot = await db.products.find_one(
                {"site_id": site_id, "featured": True},
                {"_id": 0, "id": 1, "name": 1, "source_vision_lock": 1, "review_photos": 1},
            )
            if not pilot:
                pilot = await db.products.find_one(
                    {"site_id": site_id, "role": "main"},
                    {"_id": 0, "id": 1, "name": 1, "source_vision_lock": 1, "review_photos": 1},
                    sort=[("created_at", 1)],
                )
            if not pilot:
                logger.info("[launch] no pilot product, skip review_photos")
            elif not overwrite and (pilot.get("review_photos") or []):
                logger.info(f"[launch] review_photos already populated for {pilot['id']}, skipped")
            elif budget_exhausted:
                await _mark_degraded(job_id, "review_photos",
                                     "skipped: LLM budget cap reached")
            else:
                from services.review_photos import generate_client_lifestyle_photo
                from deps import UPLOAD_DIR
                fresh_brand2 = ((await db.sites.find_one(
                    {"id": site_id}, {"_id": 0, "design.brand": 1},
                )) or {}).get("design") or {}
                brand_dict_rp = fresh_brand2.get("brand") or {}
                urls: list = []
                out_dir = UPLOAD_DIR / "products_ai" / pilot["id"] / "reviews"
                out_dir.mkdir(parents=True, exist_ok=True)
                for i in range(4):
                    if budget_exhausted:
                        break
                    try:
                        bytes_ = await asyncio.wait_for(
                            generate_client_lifestyle_photo(
                                pilot, brand_dict_rp,
                                scene_idx=i,
                                request_id=f"launch-rp-{pilot['id'][:8]}-{i}",
                            ),
                            timeout=130,
                        )
                        if bytes_:
                            fname = f"client_{i}_{uuid.uuid4().hex[:8]}.jpg"
                            (out_dir / fname).write_bytes(bytes_)
                            urls.append(f"/api/uploads/products_ai/{pilot['id']}/reviews/{fname}")
                    except asyncio.TimeoutError:
                        await _mark_degraded(job_id, f"review_photo_{i}", "timeout 130s")
                    except Exception as e:
                        msg = str(e)
                        if "402" in msg or "budget" in msg.lower():
                            budget_exhausted = True
                            await _mark_degraded(job_id, "review_photos",
                                                 "halted: budget cap mid-loop")
                            break
                        await _mark_degraded(job_id, f"review_photo_{i}", msg[:200])
                if urls:
                    await db.products.update_one(
                        {"id": pilot["id"]},
                        {"$set": {
                            "review_photos": urls,
                            "review_photos_generated_at": datetime.now(timezone.utc).isoformat(),
                        }},
                    )
                    logger.info(f"[launch] review_photos persisted: {len(urls)} photos for {pilot['id']}")
        except Exception as e:
            logger.exception("[launch] review_photos failed (non-blocking)")
            await _mark_degraded(job_id, "review_photos", str(e)[:200])

        # 9) Mark Étape 5 validated + unlock Étape 6 ---------------------
        await _advance(job_id, "finalize", "Finalisation & déblocage SEO", 96)
        try:
            await db.sites.update_one(
                {"id": site_id},
                {"$addToSet": {"validated_steps": 5},
                 "$set": {"launch_generated_at": datetime.now(timezone.utc).isoformat(),
                          # Refonte UX — automatisation activée par défaut
                          "automation.content_enabled": True,
                          "automation.seo_enabled": True,
                          "automation.translation_enabled": True}},
            )
        except Exception:
            pass

        # 9.5) Phase A2 — Enqueue automatique de 3 articles piliers
        # (guide d'achat, comparatif/critères, tendances/pourquoi maintenant).
        # Le worker `blog_worker_tick` les générera de manière asynchrone.
        try:
            site_doc = await db.sites.find_one(
                {"id": site_id},
                {"_id": 0, "id": 1, "name": 1, "niche": 1, "available_langs": 1, "primary_lang": 1},
            )
            if site_doc:
                primary_lang = site_doc.get("primary_lang") or (site_doc.get("available_langs") or ["fr"])[0]
                niche = site_doc.get("niche", "produits premium")
                pillar_briefs = [
                    {
                        "pillar": "buying_guide",
                        "topic": f"Guide d'achat complet : comment bien choisir un produit en {niche}",
                    },
                    {
                        "pillar": "comparison",
                        "topic": f"Critères et comparatif : quels matériaux et quelles caractéristiques privilégier en {niche}",
                    },
                    {
                        "pillar": "trends",
                        "topic": f"Tendances {datetime.now(timezone.utc).year} en {niche} : pourquoi investir maintenant",
                    },
                ]
                from uuid import uuid4 as _u4
                for brief in pillar_briefs:
                    await db.blog_jobs.insert_one({
                        "id": str(_u4()),
                        "site_id": site_id,
                        "status": "queued",
                        "progress": 0,
                        "articles_planned": 1,
                        "articles_done": 0,
                        "topics": [brief["topic"]],
                        "language": primary_lang,
                        "pillar": brief["pillar"],
                        "retries": 0,
                        "max_retries": 3,
                        "requested_by": "launch_auto",
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "started_at": None,
                        "completed_at": None,
                        "error": None,
                    })
                logger.info(f"[launch] enqueued 3 pillar blog jobs for site {site_id[:8]}")
        except Exception:
            logger.exception("[launch] pillar blog enqueue failed (non-blocking)")

        # 9.6) Sprint 1+2+3+4 — SEO Content Industrialization (non-blocking)
        #   Sprint 1 — AEO snippets 40-60 mots pour chaque produit
        #   Sprint 2 — Buyer guides (5) + Glossary (40) + Comparisons (10) + Top lists (5)
        #   Sprint 3 — About rich + 3 auteurs fictifs E-E-A-T
        #   Sprint 4 — Alt text IA pour toutes les images produit
        # Chaque bloc est try/except silencieux → n'interrompt pas le launch en
        # cas d'échec (budget LLM, réponse malformée, timeout, etc.).
        try:
            await _advance(job_id, "seo-content-sprints", "Contenu SEO/AEO (Sprints 1-4)…", 97)

            if not budget_exhausted:
                # Sprint 3 — About + team (rapide, ~1 prompt + 3 portraits)
                try:
                    from services import brand_premium as _bp
                    r3 = await _bp.generate_about_and_team(site_id)
                    logger.info(f"[launch-seo] brand_premium: {r3}")
                except Exception as e:
                    msg = str(e)
                    if "402" in msg or "budget" in msg.lower():
                        budget_exhausted = True
                    await _mark_degraded(job_id, "brand_premium", str(e)[:200])

            if not budget_exhausted:
                # Sprint 1 — AEO snippets 40-60 mots par produit
                try:
                    from routes.aeo import _run_bulk_snippets_job as _run_snip
                    snippet_job_id = str(uuid.uuid4())
                    await db.aeo_jobs.insert_one({
                        "id": snippet_job_id, "site_id": site_id, "type": "aeo_snippet",
                        "status": "queued", "progress": 0,
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "triggered_by": "launch",
                    })
                    await _run_snip(site_id, snippet_job_id, force=False, max_products=50)
                except Exception as e:
                    msg = str(e)
                    if "402" in msg or "budget" in msg.lower():
                        budget_exhausted = True
                    await _mark_degraded(job_id, "aeo_snippets", str(e)[:200])

            if not budget_exhausted:
                # Sprint 4 — Alt text IA pour toutes les images produit
                try:
                    from services import image_alt_text as _alt
                    r4 = await _alt.generate_alt_texts_for_site(site_id)
                    logger.info(f"[launch-seo] alt_texts: {r4}")
                except Exception as e:
                    msg = str(e)
                    if "402" in msg or "budget" in msg.lower():
                        budget_exhausted = True
                    await _mark_degraded(job_id, "alt_texts", str(e)[:200])

            if not budget_exhausted:
                # Sprint 2 — Buyer guides + Glossary + Comparisons + Top lists
                # C'est le plus coûteux (~60 pages × ~40 cts = ~2.5$ / site).
                try:
                    from services import seo_content_generators as _scg
                    r2 = await _scg.generate_all_seo_content(site_id)
                    logger.info(f"[launch-seo] seo_content: buyer_guides={r2.get('buyer_guides', {}).get('generated')} "
                                f"glossary={r2.get('glossary', {}).get('generated')} "
                                f"comparisons={r2.get('comparisons', {}).get('generated')} "
                                f"top_lists={r2.get('top_lists', {}).get('generated')}")
                except Exception as e:
                    msg = str(e)
                    if "402" in msg or "budget" in msg.lower():
                        budget_exhausted = True
                    await _mark_degraded(job_id, "seo_content_generators", str(e)[:200])
        except Exception:
            logger.exception("[launch] seo-content-sprints block crashed (non-blocking)")

        await _advance(job_id, "finalize-seo", "Contenu SEO/AEO prêt", 99)

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
    """Return the current progress of a launch job (latest if no job_id given).

    Enrichi avec :
      - phase_label (FR premium, sans jargon)
      - phase_range ({"min": int, "max": int})
      - elapsed_seconds
      - last_heartbeat_age_seconds (None si aucun heartbeat)
      - is_stale (True si heartbeat > 180 s)
      - items_done / items_total / current_item_label (depuis step_progress)
    """
    await _check_site_access(site_id, user)
    query = {"site_id": site_id}
    if job_id:
        query["id"] = job_id
    doc = await db.launch_jobs.find_one(
        query, {"_id": 0}, sort=[("created_at", -1)],
    )
    if not doc:
        return {"status": "idle"}

    # Phases premium — mapping aux bornes de progress du pipeline actuel
    # NB: la vraie valeur vit dans `progress_pct` côté DB (écrit par _run_launch).
    # L'ancien champ `progress` reste toléré pour compat mais n'est plus peuplé.
    progress = int(doc.get("progress_pct") or doc.get("progress") or 0)
    phases = [
        (0,  10, "Analyse de votre niche et positionnement"),
        (10, 25, "Génération de l'identité de marque (nom, baseline, palette, logo)"),
        (25, 55, "Création des images IA produits — 8 styles par produit"),
        (55, 75, "Rédaction des descriptions produits premium"),
        (75, 90, "Assemblage du storefront (home, collections, pages)"),
        (90, 100, "Contrôle qualité final et mise en ligne"),
    ]
    phase_label = phases[-1][2]
    phase_range = {"min": 90, "max": 100}
    for lo, hi, label in phases:
        if lo <= progress < hi:
            phase_label = label
            phase_range = {"min": lo, "max": hi}
            break

    # Durée écoulée + fraîcheur heartbeat
    from datetime import datetime as _dt, timezone as _tz
    now = _dt.now(_tz.utc)

    def _parse_iso(s):
        if not s:
            return None
        try:
            if isinstance(s, _dt):
                return s if s.tzinfo else s.replace(tzinfo=_tz.utc)
            return _dt.fromisoformat(str(s).replace("Z", "+00:00"))
        except Exception:
            return None

    started = _parse_iso(doc.get("started_at") or doc.get("created_at"))
    elapsed_s = int((now - started).total_seconds()) if started else None

    hb = _parse_iso(doc.get("last_heartbeat") or doc.get("last_heartbeat_at"))
    hb_age = int((now - hb).total_seconds()) if hb else None
    is_stale = (
        doc.get("status") == "running"
        and hb_age is not None
        and hb_age > 180
    )

    # Micro-étapes courantes (lues dans step_progress si présent)
    step_progress = doc.get("step_progress") or {}
    items_done = step_progress.get("items_done")
    items_total = step_progress.get("items_total")
    current_item_label = step_progress.get("current_item_label") or step_progress.get("current_label")

    # Alias heartbeat pour le frontend (toujours exposé)
    doc["progress"] = progress  # normalisé (= progress_pct)
    doc["progress_pct"] = progress
    doc["phase_label"] = phase_label
    doc["phase_range"] = phase_range
    doc["elapsed_seconds"] = elapsed_s
    doc["last_heartbeat_age_seconds"] = hb_age
    doc["is_stale"] = bool(is_stale)
    doc["items_done"] = items_done
    doc["items_total"] = items_total
    doc["current_item_label"] = current_item_label
    # Phase 4 — Live cost summary (si le tracker tourne encore en mémoire)
    try:
        from services.cost_tracker import get_job as _ct_get
        live = _ct_get(doc.get("id"))
        if live is not None and not doc.get("cost_summary"):
            doc["cost_summary"] = live.to_dict()
            doc["cost_summary"]["live"] = True
    except Exception:
        pass
    return doc


@router.post("/sites/{site_id}/design/launch-restart", status_code=202)
async def launch_restart(
    site_id: str,
    user: dict = Depends(get_current_user),
):
    """Marque le dernier job en running/queued comme `failed` (si stale),
    puis relance un auto-launch propre.

    Utile quand un job est zombie (heartbeat > 3 min) ou quand l'utilisateur
    veut forcer une reprise après un crash/restart backend.
    """
    await _check_site_access(site_id, user)
    from datetime import datetime as _dt, timezone as _tz
    now_iso = _dt.now(_tz.utc).isoformat()

    # 1) Clore proprement les jobs running/queued existants
    r = await db.launch_jobs.update_many(
        {"site_id": site_id, "status": {"$in": ["running", "queued"]}},
        {
            "$set": {
                "status": "failed",
                "error": "Relancé manuellement par l'utilisateur (job précédent interrompu)",
                "finished_at": now_iso,
            }
        },
    )
    closed = int(r.modified_count)

    # 2) Relancer via le endpoint auto-launch (réutilise toute la logique)
    try:
        resp = await launch_site_auto(site_id, user=user)  # type: ignore[name-defined]
        return {"ok": True, "closed_previous_jobs": closed, "new_launch": resp}
    except Exception as e:
        logger.exception("launch_restart: relance échouée")
        raise HTTPException(500, f"Relance impossible : {e}")


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


async def _claude_brand_autoprefill(
    site_name: str,
    niche: str,
    products_titles: list[str],
    user_instructions: str = "",
) -> dict:
    """Demande à Claude de générer une identité de marque ultra-premium complète.

    Retourne un dict avec brand_name, tagline, mission, voice, mood, palette,
    font_pair, hero_concept, narrative_angle. Lève HTTPException(502) si Claude
    indispo ou JSON invalide.

    Si `user_instructions` est non vide, elles sont injectées EN PRIORITÉ dans
    le prompt : l'IA doit les respecter (nom de marque imposé, style dicté,
    audience cible, etc.).
    """
    products_block = "\n".join(f"- « {t} »" for t in products_titles[:5] if t) or "(catalogue vide)"
    instr = (user_instructions or "").strip()
    system_msg = (
        "Tu es directeur artistique senior d'agence de luxe (Apple, Hermès, Aesop, Dyson, "
        "Loro Piana). Tu réponds UNIQUEMENT en JSON valide, sans texte avant/après, sans "
        "markdown fence."
    )
    priority_block = ""
    if instr:
        priority_block = (
            "\n⚠️ CONSIGNES UTILISATEUR PRIORITAIRES (À RESPECTER ABSOLUMENT, "
            "prévaut sur les règles ci-dessous en cas de conflit) :\n"
            f"« {instr[:1500]} »\n"
        )
    user_prompt = f"""Crée l'identité de marque ULTRA-PREMIUM pour cette boutique e-commerce.
{priority_block}
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
    auto_translate: bool = Query(
        False,
        description="Phase 3 — Si True, lance la traduction multi-langue automatique vers les "
                    "pays cibles (`site.target_countries`) après l'étape 5. Cap 3 $/site.",
    ),
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
    user_instructions = (site.get("launch_instructions") or "").strip()

    # Phase 4.a — réponse HTTP immédiate (<1s). L'appel Claude
    # `_claude_brand_autoprefill` (~10s) est déplacé dans la task background.
    job_id = str(uuid.uuid4())
    await db.launch_jobs.insert_one({
        "id":              job_id,
        "site_id":         site_id,
        "user_id":         user["id"],
        "status":          "running",
        "progress_pct":    1,
        "current_step":    "auto_prefill",
        "current_label":   "Conception de l'identité de marque (Claude Sonnet)…",
        "wizard":          {},  # rempli après autoprefill
        "auto_mode":       True,
        "premium_mode":    True,
        "auto_brand":      None,
        "created_at":      datetime.now(timezone.utc).isoformat(),
    })

    async def _autoprefill_and_run():
        from services import cost_tracker as _ct
        # Init du tracker tôt pour capturer le coût de l'autoprefill aussi.
        _ct.start_job(job_id)
        try:
            with _ct.job_context(job_id), _ct.bucket_context("brand"):
                parsed = await _claude_brand_autoprefill(
                    site_name, niche, products_titles, user_instructions,
                )
        except Exception as e:
            logger.warning(f"[launch-auto] autoprefill failed for {site_id}: {e}")
            await _update_job(job_id, {
                "status": "failed",
                "error": f"Autoprefill brand failed: {str(e)[:200]}",
                "completed_at": datetime.now(timezone.utc).isoformat(),
            })
            return

        wizard_payload = {
            "brand_name":      _sanitize_brand_text(parsed["brand_name"]),
            "tagline":         parsed["tagline"],
            "mission":         parsed["mission"],
            "voice":           parsed["voice"],
            "mood":            "Éditorial",
            "palette_choice":  parsed["palette"],
            "font_pair":       parsed["font_pair"],
            "homepage_preset": "default_template",
            "overwrite_all":   True,
            "logo_style":      "horizontal_premium",
            "hero_concept":    parsed.get("hero_concept", ""),
            "narrative_angle": parsed.get("narrative_angle", ""),
            "user_instructions": user_instructions,
            "premium_mode":    True,
        }
        mood_map = {
            "luxury_minimal": "Minimaliste",
            "warm_premium":   "Chaleureux",
            "editorial":      "Éditorial",
            "scandinavian":   "Moderne",
        }
        wizard_payload["mood"] = mood_map.get(parsed["mood"], "Éditorial")

        await db.launch_jobs.update_one(
            {"id": job_id},
            {"$set": {
                "wizard":      wizard_payload,
                "auto_brand":  parsed,
                "current_label": "Démarrage de la génération…",
                "updated_at":  datetime.now(timezone.utc).isoformat(),
            }},
        )

        await _run_launch(job_id, site_id, user["id"], wizard_payload)

    asyncio.create_task(_autoprefill_and_run())

    # Phase 3 — auto-traduction post-launch : si demandé, on enchaîne la
    # traduction du site vers les langues correspondant aux pays cibles.
    # Map ISO country → lang : DE→de, AT→de, BE→fr/nl, NL→nl, IT→it, ES→es,
    # GB→en, IE→en, CH→fr/de, FR→fr, LU→fr (déjà traduit en source). Le hook
    # tourne en background une fois `_run_launch` terminé (poll status).
    if auto_translate:
        target_countries = site.get("target_countries") or [site.get("country") or "FR"]
        country_lang_map = {
            "FR":"fr","BE":"fr","CH":"fr","LU":"fr",
            "DE":"de","AT":"de",
            "NL":"nl",
            "IT":"it",
            "ES":"es",
            "GB":"en","IE":"en","UK":"en","US":"en",
        }
        primary = site.get("primary_lang") or "fr"
        target_langs = sorted({
            country_lang_map.get(c.upper())
            for c in target_countries
            if country_lang_map.get(c.upper()) and country_lang_map.get(c.upper()) != primary
        })
        if target_langs:
            async def _wait_and_translate():
                # Wait for launch to finish (poll status)
                from routes.translate import _translate_site_async, TRANSLATE_TASKS
                for _ in range(120):  # max ~30 min
                    await asyncio.sleep(15)
                    j = await db.launch_jobs.find_one({"id": job_id}, {"_id": 0, "status": 1})
                    if not j or (j.get("status") or "").startswith("completed") or j.get("status") == "failed":
                        break
                # Now translate
                t_id = uuid.uuid4().hex[:12]
                TRANSLATE_TASKS[t_id] = {
                    "task_id": t_id, "site_id": site_id,
                    "source_lang": primary, "target_langs": target_langs,
                    "overwrite": False, "status": "queued",
                    "progress": {t: "queued" for t in target_langs},
                    "spent_usd": 0.0, "totals": {},
                    "started_at": datetime.now(timezone.utc).isoformat(),
                    "triggered_by": f"launch-auto:{job_id}",
                }
                logger.info(f"[launch] auto-translate kicking {target_langs} for site {site_id[:8]}")
                await _translate_site_async(site_id, target_langs, False, t_id)
            asyncio.create_task(_wait_and_translate())

    return {
        "ok":         True,
        "job_id":     job_id,
        "status":     "running",
        "auto_brand": None,  # Phase 4.a — autoprefill is done in background, poll launch-status
        "auto_translate_queued": bool(auto_translate),
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


@router.post("/sites/{site_id}/design/launch-resume-degraded", tags=["launch-resilience"])
async def resume_last_degraded(
    site_id: str,
    user: dict = Depends(get_current_user),
):
    """Alias pratique : relance les étapes dégradées du DERNIER job
    `completed_with_degraded` ou `failed` sans avoir à connaître le job_id.

    Utilisé par l'encart "Relancer les étapes reportées" du LaunchProgress.
    """
    await _check_site_access(site_id, user)
    job = await db.launch_jobs.find_one(
        {"site_id": site_id, "status": {"$in": ["completed_with_degraded", "failed"]}},
        {"_id": 0},
        sort=[("created_at", -1)],
    )
    if not job:
        raise HTTPException(404, "Aucun job avec étapes dégradées à relancer.")
    if not (job.get("degraded_steps") or []):
        raise HTTPException(400, "Aucune étape reportée à relancer pour ce site.")
    return await resume_launch_job(site_id, job["id"], user)


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

