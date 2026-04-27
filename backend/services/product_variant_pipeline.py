"""Lot I (Phase 2.2) — Pipeline 8 styles d'images premium par variante.

Étend `color_variant_images.py` (Lot H) avec une liste FIXE de 8 styles
définis par le brief utilisateur 2026-04-27. Chaque style a son propre
prompt et son aspect ratio cible.

Styles (8 fixes) :
  1. studio_main      4:5   Fond studio clair (ivoire/lin), produit centré
  2. studio_card      1:1   Même fond studio, cadrage serré (vignette grille)
  3. lifestyle        4:5   Intérieur premium haussmannien/scandinave
  4. wide_lifestyle  16:9   Panoramique de la même scène, produit décentré
  5. closeup          1:1   Gros plan matières / textures
  6. detail           1:1   Détail technique (mécanisme, télécommande, finition)
  7. in_use           4:5   Produit en utilisation, silhouette anonyme
  8. side_profile     4:5   Vue de profil/3-4 fond studio neutre

Conformément au brief : img-to-img Nano Banana, fidélité au modèle source
AliExpress/CJ (préservation forme + textures). Seuls la couleur, la mise
en scène et l'angle changent selon le style.

Budget hard cap : 5$/site (~50 images Nano Banana à 0.05$/image, soit
~6 produits × 1 couleur × 8 styles, ou répartir comme ça arrive).

Schema (sur `products[]`) :
  generated_images_by_variant: {
    "black": [
      {style: "studio_main", aspect: "4:5", url: "...", ...},
      {style: "studio_card", aspect: "1:1", url: "...", ...},
      ... (8 entries)
    ],
    "white": [...]
  }
"""
from __future__ import annotations

import asyncio
import base64
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from deps import UPLOAD_DIR
from services.color_variant_images import (
    _fetch_image_b64,
    color_label_to_english,
    detect_product_kind,
    slugify_color,
)
from services.image_qa import (
    GEMINI_VISION_USD_PER_CALL,
    analyze_source_product_multi,
    qa_check_generated_image,
)
from services.llm_resilience import LLMUnavailableError, safe_nano_banana_bytes

logger = logging.getLogger("altiaro.product_variant_pipeline")


# Per-image budget assumption (Nano Banana via Emergent universal key)
NANO_BANANA_USD_PER_IMAGE = 0.05
DEFAULT_BUDGET_CAP_USD = 5.0  # per-site cap (brief 2026-04-27)


# -------------------------------------------------------------------------
# 8 fixed styles — slug, aspect ratio, per-style scene brief.
# Phase 2.2 hardening (2026-04-27 user feedback) :
#   - Identity Lock + Material Lock + Color Lock injected per call
#   - Per-style brief is ULTRA-PRECISE (no ambiguity) — esp. `in_use`
#   - Negative prompt block hardens against common Nano Banana failures
# Templates use {product_kind}, {material}, {color}, {color_label_en}.
# -------------------------------------------------------------------------
IDENTITY_BLOCK = (
    "REFERENCE IMAGE LOCK (HIGHEST PRIORITY) — The provided reference image "
    "shows the EXACT product to render. You MUST preserve PIXEL-IDENTICAL: "
    "the {product_kind} silhouette, dimensions, armrest shape, headrest shape, "
    "footrest mechanism, base/legs structure, button or control placement, "
    "stitching pattern, capitonnage (tufting) lines, every visible technical "
    "feature. The ONLY things you may change between images are: camera angle, "
    "framing, lighting, and the surrounding decor. The {product_kind} itself "
    "MUST be the SAME exact model, SAME exact finish, SAME exact proportions. "
    "Never substitute one material for another, never alter the silhouette, "
    "never add or remove buttons, seams, or technical features.\n\n"
    "SILHOUETTE SIGNATURE LOCK — The product is uniquely identified by these "
    "formal traits, ALL of which MUST be visible in the rendered image (where "
    "the framing allows): {silhouette_signature}. If a trait is invisible due "
    "to framing (e.g. base hidden by closeup), it is fine — but no trait may "
    "be ALTERED, REPLACED or REMOVED. Number of armrests, number of cushions, "
    "type of base/legs, headrest shape — all FIXED.\n\n"
    "VISIBLE FEATURES — Where the framing shows them, these technical elements "
    "must remain visible and IDENTICAL: {unique_features_visible}.\n\n"
    "MATERIAL LOCK — The upholstery / surface material is: {material}. "
    "This material is FIXED across all 8 images. NEVER substitute one material "
    "for another (leather <-> fabric <-> microsuede <-> velvet are all DIFFERENT). "
    "The texture, grain, weave and finish must look IDENTICAL to the reference.\n\n"
    "COLOR LOCK — The exact color of the {product_kind} upholstery is: "
    "{color} (target color label: {color_label_en}). Identical undertone, "
    "identical finish (matte/satin/glossy as in reference) across all images.\n\n"
    "QUALITY — Photorealistic 4K editorial product photography. "
    "No text, no watermark, no brand mark, no logo overlay."
)

NEGATIVE_BLOCK = (
    "AVOID — blurry product, distorted proportions, warped or asymmetric "
    "shape where the {product_kind} should be symmetrical, missing armrests, "
    "extra limbs, extra chair parts, ghost elements, deformed hands, "
    "watermarks, text, logos, photoshop seams, glossy plastic when source "
    "is fabric, leather grain when source is fabric (or vice versa), "
    "different chair/object model than reference, different color, "
    "different material, person standing instead of seated for in_use."
)

VARIANT_STYLES: List[Dict[str, str]] = [
    {
        "slug": "studio_main",
        "aspect": "4:5",
        "label_en": "main studio shot",
        "scene": (
            "Pure ivory studio background (#F5F2EB warm off-white seamless paper). "
            "Three-quarter front view of the {product_kind}, shot at eye level, "
            "soft diffused lighting from the upper left, no harsh shadows on the background. "
            "The full {product_kind} is visible from headrest down to footrest base. "
            "Subtle ground shadow under the product. "
            "Vertical 4:5 framing with generous negative space above and below. "
            "Editorial catalog hero quality."
        ),
    },
    {
        "slug": "studio_card",
        "aspect": "1:1",
        "label_en": "square card shot",
        "scene": (
            "Same ivory #F5F2EB seamless studio background as the main shot. "
            "Tighter framing — the {product_kind} occupies 70% of a square 1:1 frame, "
            "perfectly centered. Same lighting and angle as studio_main. "
            "Suitable as a product grid card thumbnail."
        ),
    },
    {
        "slug": "lifestyle",
        "aspect": "4:5",
        "label_en": "lifestyle scene",
        "scene": (
            "Premium Parisian Haussmannian apartment interior: oak parquet floor with "
            "herringbone pattern, tall window with sheer linen curtains diffusing soft "
            "afternoon daylight, white wall mouldings in the background. "
            "The {product_kind} sits naturally in the room, slight side angle, "
            "integrated as a real piece of furniture. NO PEOPLE in this shot. "
            "Subtle props nearby: a stack of art books, a reading lamp, a cashmere throw. "
            "Vertical 4:5 framing, depth of field bringing the {product_kind} forward. "
            "High-end interior magazine editorial quality."
        ),
    },
    {
        "slug": "wide_lifestyle",
        "aspect": "16:9",
        "label_en": "wide cinematic lifestyle",
        "scene": (
            "PANORAMIC 16:9 horizontal cinematic view of the same Haussmannian living room: "
            "wide-angle perspective showing the full corner of the room, oak parquet, "
            "tall window with linen curtains, white mouldings, soft natural daylight. "
            "The {product_kind} is positioned on the LEFT THIRD of the frame, the room "
            "extending to the right with elegant decor (art books, a plant, a vintage rug). "
            "NO PEOPLE in this shot. Cinematic editorial composition, 35mm equivalent focal "
            "length, golden hour soft light, calm and timeless atmosphere."
        ),
    },
    {
        "slug": "closeup",
        "aspect": "1:1",
        "label_en": "macro material closeup",
        "scene": (
            "Extreme macro close-up on the EXACT upholstery surface of THIS {product_kind} "
            "(same chair as the reference, not a different one). "
            "Show the texture of the {material} in {color}: weave, stitching, grain, "
            "every fiber detail visible. "
            "Shallow depth of field, beautiful natural light from a soft side window, warm tone. "
            "1:1 square framing — only the rich textured surface fills the frame, "
            "with at most a hint of the seam or armrest curve to anchor context. "
            "Editorial textile photography style. NO PEOPLE."
        ),
    },
    {
        "slug": "detail",
        "aspect": "1:1",
        "label_en": "technical detail",
        "scene": (
            "Macro detail shot of ONE specific technical feature of THIS {product_kind} "
            "(same chair as reference): the recline mechanism articulation, the remote "
            "control or recline lever, the motor housing, or the armrest joint. "
            "Plain neutral light grey #E7E5E4 background, soft directional studio lighting "
            "from the right. 1:1 square framing, the technical detail is the hero of the shot. "
            "Conveys precision and quality engineering. NO PEOPLE, no text, no labels visible."
        ),
    },
    {
        "slug": "in_use",
        "aspect": "4:5",
        "label_en": "in-use lifestyle (person seated)",
        "scene": (
            "Realistic in-use scene with a PERSON FULLY SEATED IN the {product_kind}. "
            "CRITICAL: the person's back must be against the backrest, their bottom on the "
            "seat, legs naturally placed (or footrest extended if applicable). The person "
            "is INSIDE/ON the chair, NOT standing next to it, NOT in front of it, NOT far away. "
            "The person is anonymous — face is partially out of frame, in soft shadow, "
            "or only the back of the head / a hand on the armrest is shown (no recognisable "
            "facial features). Casual elegant attire, 50-70 years old, relaxed posture. "
            "Warm cozy interior in soft golden afternoon light, an open book or a cup of tea "
            "as a subtle prop. Vertical 4:5 framing, natural authentic moment. "
            "Editorial lifestyle photography."
        ),
    },
    {
        "slug": "side_profile",
        "aspect": "4:5",
        "label_en": "side profile shot",
        "scene": (
            "Pure 90-degree side profile of the {product_kind}, shot at exactly 90° from the "
            "side. Plain neutral light grey #E7E5E4 studio background, single soft side light "
            "revealing every silhouette line. Vertical 4:5 framing — the {product_kind} fills "
            "80% of the frame. All profile lines visible: the curve of the back, the angle of "
            "the armrest, the shape of the legs or base. Architectural product photography "
            "emphasizing form, proportions, and engineering. NO PEOPLE."
        ),
    },
]

ALL_STYLE_SLUGS = [s["slug"] for s in VARIANT_STYLES]


# -------------------------------------------------------------------------
# Cost tracking helpers
# -------------------------------------------------------------------------
class BudgetCap:
    """Mutable cumulative cost tracker (USD) shared across many parallel
    image generations. Caller checks `.exhausted()` before each new call.
    Phase 2.2 v2 — also tracks Gemini Vision QA calls (~0.008 USD each).
    """

    def __init__(self, cap_usd: float = DEFAULT_BUDGET_CAP_USD):
        self.cap_usd = float(cap_usd)
        self.spent_usd = 0.0
        self.images_generated = 0
        self.images_failed = 0
        self.qa_calls = 0
        self.source_analyses = 0

    def add_image(self, success: bool = True) -> None:
        self.spent_usd += NANO_BANANA_USD_PER_IMAGE
        if success:
            self.images_generated += 1
        else:
            self.images_failed += 1

    def add_qa_call(self) -> None:
        self.spent_usd += GEMINI_VISION_USD_PER_CALL
        self.qa_calls += 1

    def add_source_analysis(self) -> None:
        self.spent_usd += GEMINI_VISION_USD_PER_CALL
        self.source_analyses += 1

    def exhausted(self) -> bool:
        return self.spent_usd + NANO_BANANA_USD_PER_IMAGE > self.cap_usd

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cap_usd": round(self.cap_usd, 4),
            "spent_usd": round(self.spent_usd, 4),
            "remaining_usd": round(max(0.0, self.cap_usd - self.spent_usd), 4),
            "images_generated": self.images_generated,
            "images_failed": self.images_failed,
            "qa_calls": self.qa_calls,
            "source_analyses": self.source_analyses,
        }


# -------------------------------------------------------------------------
# Build a single style prompt
# -------------------------------------------------------------------------
def build_style_prompt(
    style: Dict[str, str],
    product_kind: str,
    material: str,
    color: str,
    color_label_en: str,
    silhouette_signature: str = "",
    unique_features_visible: str = "",
) -> str:
    fmt = dict(
        product_kind=product_kind, material=material,
        color=color, color_label_en=color_label_en,
        silhouette_signature=silhouette_signature or "wide armrests, defined backrest, structured base",
        unique_features_visible=unique_features_visible or "the product as shown in the reference",
    )
    identity = IDENTITY_BLOCK.format(**fmt)
    scene = style["scene"].format(**fmt)
    negative = NEGATIVE_BLOCK.format(**fmt)
    aspect = style["aspect"]
    return (
        f"{identity}\n\n"
        f"SCENE BRIEF: {scene}\n\n"
        f"{negative}\n\n"
        f"ASPECT RATIO: render at exactly {aspect} aspect ratio."
    )


# -------------------------------------------------------------------------
# Generate ONE style image with QA + retry. Returns the persisted image dict
# or None on failure.
# -------------------------------------------------------------------------
async def _generate_one_style(
    *,
    product_id: str,
    color_slug: str,
    color_label: str,
    color_label_en: str,
    style: Dict[str, str],
    product_kind: str,
    material: str,
    color_descriptor: str,
    silhouette_signature: str,
    unique_features_visible: str,
    reference_image_b64: str,
    request_id_prefix: str,
    qa_enabled: bool = True,
    max_retries: int = 2,
) -> Optional[Dict[str, Any]]:
    """Generate one style image. Runs Gemini Vision QA (6 strict booleans)
    against the reference + style brief + silhouette signature. Retries up
    to `max_retries` (default 2) on QA failure. Returns None on definitive
    failure (caller does not persist; storefront falls back to source AE)."""
    prompt = build_style_prompt(
        style, product_kind, material, color_descriptor, color_label_en,
        silhouette_signature=silhouette_signature,
        unique_features_visible=unique_features_visible,
    )
    last_qa: Optional[Dict[str, Any]] = None

    for attempt in range(max_retries + 1):
        try:
            data = await safe_nano_banana_bytes(
                prompt,
                system=(
                    "You generate premium product photography for a Silver Economy "
                    "D2C brand. You preserve product identity strictly: same shape, "
                    "same materials, same color, same features. Only the scene, "
                    "the lighting and the camera framing change. Photorealistic "
                    "editorial style."
                ),
                session_id=f"{request_id_prefix}-{style['slug']}-a{attempt}",
                timeout=120,
                request_id=f"{request_id_prefix}-{style['slug']}-a{attempt}",
                reference_image_b64=reference_image_b64,
            )
        except LLMUnavailableError as e:
            logger.warning(
                f"[variant-pipeline] LLM down for {product_id[:8]}/{color_slug}/{style['slug']} "
                f"a{attempt}: {e.last_error}"
            )
            return None
        except Exception as e:
            msg = str(e)
            if "402" in msg or "Budget has been exceeded" in msg or "budget" in msg.lower():
                logger.error("[variant-pipeline] BUDGET EXHAUSTED — abort propagated")
                raise
            logger.exception(
                f"[variant-pipeline] {product_id[:8]}/{color_slug}/{style['slug']} a{attempt}"
            )
            continue

        if not data:
            continue

        # QA Vision check against reference + style brief
        if qa_enabled:
            try:
                gen_b64 = base64.b64encode(data).decode()
                qa = await qa_check_generated_image(
                    generated_b64=gen_b64,
                    reference_b64=reference_image_b64,
                    style_slug=style["slug"],
                    style_brief=style["scene"].format(
                        product_kind=product_kind, material=material,
                        color=color_descriptor, color_label_en=color_label_en,
                        silhouette_signature=silhouette_signature or "",
                        unique_features_visible=unique_features_visible or "",
                    ),
                    expected_material=material,
                    expected_color=color_descriptor,
                    silhouette_signature=silhouette_signature,
                    unique_features_visible=unique_features_visible,
                    request_id=f"qa-{request_id_prefix}-{style['slug']}-a{attempt}",
                )
                last_qa = qa
                if qa.get("all_pass"):
                    return _persist_image(
                        data, product_id, color_slug, color_label,
                        style, attempt, qa,
                    )
                else:
                    failed = [k for k, v in (qa.get("checks") or {}).items() if not v]
                    logger.warning(
                        f"[variant-pipeline] QA FAILED {style['slug']} a{attempt}: "
                        f"failed={failed} issues={qa.get('issues', [])[:3]}"
                    )
                    # On retry, the prompt stays the same — but Nano Banana is stochastic
                    # so a fresh attempt may pass. (Optionally we could mutate prompt.)
                    continue
            except Exception as e:
                logger.warning(
                    f"[variant-pipeline] QA exception {style['slug']} a{attempt}: {str(e)[:200]} "
                    "— accepting image (fail-open)"
                )
                return _persist_image(
                    data, product_id, color_slug, color_label,
                    style, attempt,
                    {"vision_qa_skipped": True, "issues": [str(e)[:120]]},
                )
        else:
            return _persist_image(data, product_id, color_slug, color_label, style, attempt, None)

    # All retries exhausted with QA failures — return None to signal failure.
    # Caller will not persist the slot, only log.
    logger.error(
        f"[variant-pipeline] {style['slug']} FAILED ALL {max_retries + 1} "
        f"attempts for {product_id[:8]}/{color_slug}. Last QA: {last_qa}"
    )
    return None


def _persist_image(
    data: bytes,
    product_id: str,
    color_slug: str,
    color_label: str,
    style: Dict[str, str],
    attempt: int,
    qa_result: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Persist the image bytes to disk and return the descriptor dict."""
    out_dir = UPLOAD_DIR / "products_ai" / product_id / "variants" / color_slug
    out_dir.mkdir(parents=True, exist_ok=True)
    fname = f"{style['slug']}_{uuid.uuid4().hex[:8]}.png"
    (out_dir / fname).write_bytes(data)
    url = f"/api/uploads/products_ai/{product_id}/variants/{color_slug}/{fname}"
    return {
        "style": style["slug"],
        "aspect": style["aspect"],
        "url": url,
        "color": color_label,
        "color_label": color_label,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_style": "img-to-img",
        "tweak": "8styles-pipeline-v2-qa",
        "label_en": style["label_en"],
        "qa_attempt": attempt,
        "qa_passed": bool(qa_result and qa_result.get("all_pass") if qa_result else None),
        "qa_issues": (qa_result or {}).get("issues") or [],
    }


# -------------------------------------------------------------------------
# Main orchestrator — generate the 8 styles for one (product, color) pair
# -------------------------------------------------------------------------
async def generate_full_variant_set(
    db,
    product_id: str,
    color_slug: str,
    *,
    overwrite: bool = False,
    budget: Optional[BudgetCap] = None,
    request_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate the 8 fixed styles for one (product, color_slug) pair.

    - Idempotent : if a style already exists in `generated_images_by_variant[color_slug]`
      and `overwrite=False`, it is skipped.
    - Budget-aware : if `budget.exhausted()` returns True, we stop early and
      return the partial result (imagse already generated are persisted).
    - Returns a dict with `images` (list of 8 dicts), `budget` (state), and `skipped`.

    The reference image used for img-to-img is the FIRST image of the
    existing `generated_images_by_variant[color_slug]` (if any) or
    `generated_images[0]` of the product.
    """
    p = await db.products.find_one(
        {"id": product_id},
        {
            "_id": 0, "id": 1, "name": 1, "variants": 1,
            "generated_images": 1, "generated_images_by_variant": 1,
            "images": 1, "original_images": 1, "original_image": 1,
            "source_vision_lock": 1,
        },
    )
    if not p:
        raise ValueError(f"Product {product_id} not found")

    by_variant = dict(p.get("generated_images_by_variant") or {})
    existing_for_color = by_variant.get(color_slug) or []
    existing_styles = {img.get("style") for img in existing_for_color if img.get("style")}

    # Find the color label (original casing) — match by slug
    color_label = color_slug
    for v in p.get("variants") or []:
        props = v.get("properties") or []
        if props and props[0]:
            if slugify_color(str(props[0]).strip()) == color_slug:
                color_label = str(props[0]).strip()
                break

    # Pick the reference image (img-to-img source)
    ref_url = None
    if existing_for_color:
        ref_url = existing_for_color[0].get("url")
    if not ref_url:
        gi = p.get("generated_images") or []
        if gi:
            ref_url = gi[0].get("url")
    if not ref_url:
        raise ValueError(
            f"No reference image available for {product_id[:8]}/{color_slug}. "
            f"Run the base generation first (Lot H or original studio shot)."
        )
    ref_b64 = await _fetch_image_b64(ref_url)
    if not ref_b64:
        raise ValueError(f"Reference image not loadable: {ref_url}")

    product_kind = detect_product_kind(p.get("name") or "")
    target_color_en = color_label_to_english(color_label)

    if budget is None:
        budget = BudgetCap()

    request_id = request_id or f"vpipe-{product_id[:8]}-{color_slug}"

    # ---------------------------------------------------------------
    # Phase 2.2 v3 — Multi-image source analysis : run Gemini Vision
    # ONCE on ALL the source AE/CJ photos (up to 6) to build a
    # `source_vision_lock` dict with 5 sub-fields injected into every
    # per-style prompt :
    #   product_kind, material, color, silhouette_signature, unique_features_visible
    # The lock is cached at product-level (invariant across variants),
    # only the per-variant `color_descriptor` overrides the base color.
    # ---------------------------------------------------------------
    cached_lock = (p.get("source_vision_lock") or {}) if isinstance(p.get("source_vision_lock"), dict) else {}
    source_lock: Dict[str, Any] = dict(cached_lock)
    silhouette_signature = ""
    unique_features_visible = ""

    if not cached_lock or "silhouette_signature" not in cached_lock:
        # Build the multi-image source set from `original_images` (best),
        # else `images`, else fall back to the reference `ref_b64`.
        source_urls: List[str] = []
        for u in (p.get("original_images") or []):
            if isinstance(u, str) and u and u not in source_urls:
                source_urls.append(u)
        if not source_urls:
            for u in (p.get("images") or []):
                if isinstance(u, str) and u and u not in source_urls:
                    source_urls.append(u)
        if not source_urls and p.get("original_image"):
            source_urls.append(p["original_image"])
        # Cap to 6
        source_urls = source_urls[:6]

        source_b64_list: List[str] = []
        for u in source_urls:
            try:
                b = await _fetch_image_b64(u)
                if b:
                    source_b64_list.append(b)
            except Exception as _e:
                logger.warning(f"[variant-pipeline] {request_id}: source img fetch failed {u[:80]}: {str(_e)[:120]}")
        if not source_b64_list:
            source_b64_list = [ref_b64]

        try:
            source_lock_new = await analyze_source_product_multi(
                source_b64_list,
                color_hint=color_label,
                request_id=f"{request_id}-source-multi",
            )
            budget.add_source_analysis()
            source_lock = source_lock_new
            # Persist at product-level for future runs (cache)
            await db.products.update_one(
                {"id": product_id},
                {"$set": {
                    "source_vision_lock": source_lock,
                    "source_vision_lock_updated_at": datetime.now(timezone.utc).isoformat(),
                    "source_vision_lock_n_images": len(source_b64_list),
                }},
            )
        except Exception as e:
            logger.warning(
                f"[variant-pipeline] {request_id} multi-source analysis failed: {str(e)[:200]} "
                "— falling back to generic descriptors"
            )
            source_lock = {
                "product_kind":            product_kind,
                "material":                "fabric upholstery, woven texture",
                "color":                   f"{target_color_en}, matte finish",
                "silhouette_signature":    "",
                "unique_features_visible": "",
            }

    material = source_lock.get("material") or "fabric upholstery"
    color_descriptor = source_lock.get("color") or f"{target_color_en}, matte finish"
    if source_lock.get("product_kind") and len(source_lock["product_kind"]) > len(product_kind):
        product_kind = source_lock["product_kind"]
    silhouette_signature = source_lock.get("silhouette_signature") or ""
    unique_features_visible = source_lock.get("unique_features_visible") or ""

    new_images: List[Dict[str, Any]] = []
    skipped: List[str] = []
    failed_qa: List[str] = []

    # Build the final image set : start with existing kept ones, then add new
    final_for_color: List[Dict[str, Any]] = []
    if not overwrite:
        # Keep existing entries that match one of our 8 slugs (preserve work)
        for img in existing_for_color:
            if img.get("style") in ALL_STYLE_SLUGS:
                final_for_color.append(img)

    for style in VARIANT_STYLES:
        if not overwrite and style["slug"] in existing_styles:
            skipped.append(style["slug"])
            continue
        if budget.exhausted():
            logger.warning(
                f"[variant-pipeline] {request_id}: budget cap reached "
                f"({budget.spent_usd:.2f}/{budget.cap_usd:.2f}$), skipping {style['slug']}"
            )
            skipped.append(style["slug"] + "(budget)")
            continue

        # Account for the ~3 image attempts and ~3 QA calls in the worst case
        # against the budget when we choose to start a style (don't start if
        # we can't afford even 1 try).
        img = await _generate_one_style(
            product_id=product_id,
            color_slug=color_slug,
            color_label=color_label,
            color_label_en=target_color_en,
            style=style,
            product_kind=product_kind,
            material=material,
            color_descriptor=color_descriptor,
            silhouette_signature=silhouette_signature,
            unique_features_visible=unique_features_visible,
            reference_image_b64=ref_b64,
            request_id_prefix=request_id,
            qa_enabled=True,
            max_retries=2,
        )
        # Crude budget accounting : we don't know exactly how many attempts
        # _generate_one_style made; we assume successful = 1 image + 1 QA,
        # failed = 3 images + 3 QA (worst case). Caller can refine if needed.
        if img:
            attempts = int(img.get("qa_attempt") or 0) + 1
            for _ in range(attempts):
                budget.add_image(success=True)
                budget.add_qa_call()
            new_images.append(img)
            if overwrite:
                final_for_color = [x for x in final_for_color if x.get("style") != style["slug"]]
            final_for_color.append(img)
            logger.info(
                f"[variant-pipeline] {request_id}: {style['slug']} OK "
                f"({img['aspect']}, {attempts} attempt(s), qa_passed={img.get('qa_passed')})"
            )
        else:
            for _ in range(3):
                budget.add_image(success=False)
                budget.add_qa_call()
            failed_qa.append(style["slug"])
            logger.error(
                f"[variant-pipeline] {request_id}: {style['slug']} FAILED — "
                "not persisted (all 3 attempts rejected by Vision QA)"
            )

    by_variant[color_slug] = final_for_color
    await db.products.update_one(
        {"id": product_id},
        {"$set": {
            "generated_images_by_variant": by_variant,
            "generated_images_by_variant_updated_at": datetime.now(timezone.utc).isoformat(),
            "generated_images_locked_material": material,
            "generated_images_locked_color": color_descriptor,
            "generated_images_locked_product_kind": product_kind,
            "generated_images_locked_silhouette": silhouette_signature,
            "generated_images_locked_features": unique_features_visible,
        }},
    )

    return {
        "ok": True,
        "product_id": product_id,
        "color_slug": color_slug,
        "color_label": color_label,
        "locked": {
            "product_kind":            product_kind,
            "material":                material,
            "color":                   color_descriptor,
            "silhouette_signature":    silhouette_signature,
            "unique_features_visible": unique_features_visible,
        },
        "source_vision_lock": source_lock,
        "images": final_for_color,
        "new_images_count": len(new_images),
        "skipped_styles": skipped,
        "failed_qa_styles": failed_qa,
        "budget": budget.to_dict(),
    }


# -------------------------------------------------------------------------
# Site-level batch — orchestrates across all (product, variant) pairs.
# Used by the admin batch endpoint and by launch.py post-Lot-H step.
# -------------------------------------------------------------------------
async def generate_all_variant_sets_for_site(
    db,
    site_id: str,
    *,
    overwrite: bool = False,
    budget_cap_usd: float = DEFAULT_BUDGET_CAP_USD,
    progress_cb=None,
) -> Dict[str, Any]:
    """For each active product on the site that has a `generated_images_by_variant`
    populated (at least one color with a reference image), complete each color
    to the full 8-styles set.

    Respects a hard budget cap per site (default 5 USD). Idempotent.
    """
    products = await db.products.find(
        {"site_id": site_id, "status": "active"},
        {"_id": 0, "id": 1, "name": 1, "generated_images_by_variant": 1, "generated_images": 1},
    ).to_list(500)

    budget = BudgetCap(cap_usd=budget_cap_usd)
    results: List[Dict[str, Any]] = []

    for p in products:
        pid = p["id"]
        by_variant = p.get("generated_images_by_variant") or {}
        gi = p.get("generated_images") or []
        if not by_variant and not gi:
            continue
        # If by_variant is empty but generated_images exists, treat the product
        # as single-variant (slug = "default")
        if not by_variant and gi:
            by_variant = {"default": gi}
        for color_slug in list(by_variant.keys()):
            if budget.exhausted():
                logger.warning(
                    f"[batch-variant-pipeline] site {site_id[:8]}: budget cap reached, halting"
                )
                break
            try:
                r = await generate_full_variant_set(
                    db, pid, color_slug,
                    overwrite=overwrite,
                    budget=budget,
                    request_id=f"batch-{site_id[:8]}-{pid[:8]}-{color_slug}",
                )
                results.append({"product_id": pid, "color_slug": color_slug,
                                "new_images_count": r["new_images_count"],
                                "skipped": r["skipped_styles"]})
                if progress_cb:
                    try:
                        await progress_cb(p, color_slug, r)
                    except Exception:
                        pass
            except Exception as e:
                logger.warning(
                    f"[batch-variant-pipeline] {pid[:8]}/{color_slug}: {str(e)[:120]}"
                )
                results.append({"product_id": pid, "color_slug": color_slug,
                                "error": str(e)[:200]})
        if budget.exhausted():
            break

    return {
        "site_id": site_id,
        "products_processed": len(results),
        "results": results,
        "budget": budget.to_dict(),
    }


__all__ = [
    "VARIANT_STYLES",
    "ALL_STYLE_SLUGS",
    "BudgetCap",
    "build_style_prompt",
    "generate_full_variant_set",
    "generate_all_variant_sets_for_site",
    "slugify_color",
    "DEFAULT_BUDGET_CAP_USD",
    "NANO_BANANA_USD_PER_IMAGE",
]
