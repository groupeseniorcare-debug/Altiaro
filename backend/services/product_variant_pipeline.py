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
from services.llm_resilience import LLMUnavailableError, safe_nano_banana_bytes

logger = logging.getLogger("altiaro.product_variant_pipeline")


# Per-image budget assumption (Nano Banana via Emergent universal key)
NANO_BANANA_USD_PER_IMAGE = 0.05
DEFAULT_BUDGET_CAP_USD = 5.0  # per-site cap (brief 2026-04-27)


# -------------------------------------------------------------------------
# 8 fixed styles — slug, aspect ratio, prompt template
# Each prompt MUST keep the product identity stable (img-to-img Nano Banana).
# Templates use {product_kind} and {target_color} placeholders.
# -------------------------------------------------------------------------
IDENTITY_BLOCK = (
    "EXACTLY the same {product_kind} as the reference image: "
    "SAME silhouette, SAME mechanism, SAME proportions, SAME materials, "
    "SAME stitching pattern, SAME features and accessories. "
    "Do not redesign, restyle, or alter the product shape. "
    "The {product_kind} upholstery / dominant color is {target_color}. "
    "Photorealistic 4K editorial product photography. "
    "No text, no watermark, no brand mark, no logo overlay."
)

VARIANT_STYLES: List[Dict[str, str]] = [
    {
        "slug": "studio_main",
        "aspect": "4:5",
        "label_en": "main studio shot",
        "scene": (
            "Clean professional studio setup with soft warm directional lighting from the upper left. "
            "Background is plain ivory #F5F2EB seamless paper, gradient fading slightly darker at the edges. "
            "The {product_kind} is centered, shot frontally, three-quarter pose, full product visible. "
            "Subtle ground shadow under the product anchoring it. "
            "Editorial catalog hero — vertical 4:5 framing, generous negative space above and below."
        ),
    },
    {
        "slug": "studio_card",
        "aspect": "1:1",
        "label_en": "square card shot",
        "scene": (
            "Same ivory #F5F2EB seamless studio background as the main shot, soft natural lighting. "
            "The {product_kind} is centered, slightly closer-cropped framing for a square 1:1 grid card. "
            "Tight composition, the product fills 75% of the frame, balanced negative space. "
            "Suitable for a product grid thumbnail."
        ),
    },
    {
        "slug": "lifestyle",
        "aspect": "4:5",
        "label_en": "lifestyle scene",
        "scene": (
            "Upscale Parisian Haussmannian living room interior: oak parquet floor with herringbone pattern, "
            "tall window with sheer linen curtains diffusing soft afternoon daylight, "
            "white wall mouldings in the background, a vintage gold-framed mirror partially visible. "
            "The {product_kind} sits naturally in the room, slightly off-center, integrated as a real piece of furniture. "
            "Subtle props: a stack of art books, a reading lamp, a cashmere throw nearby. "
            "Vertical 4:5 framing, depth of field bringing the {product_kind} forward."
        ),
    },
    {
        "slug": "wide_lifestyle",
        "aspect": "16:9",
        "label_en": "wide cinematic lifestyle",
        "scene": (
            "PANORAMIC 16:9 horizontal cinematic view of the same Haussmannian living room: "
            "wide-angle perspective showing the full corner of the room, oak parquet, tall window with linen curtains, "
            "white mouldings, soft natural daylight from the side. "
            "The {product_kind} is positioned in the right third of the frame, the room extending to the left "
            "with elegant decor (art books, plants, a vintage rug, a soft wool throw). "
            "Cinematic editorial composition, shot at 35mm equivalent focal length, "
            "shallow gradient of light from window, calm and timeless atmosphere."
        ),
    },
    {
        "slug": "closeup",
        "aspect": "1:1",
        "label_en": "macro material closeup",
        "scene": (
            "Macro extreme close-up on the {product_kind} upholstery and seam textures. "
            "Show the weave of the fabric, the stitching detail, the grain of the material in {target_color}. "
            "Shallow depth of field, beautiful natural light from a soft side window, warm tone. "
            "1:1 square framing, no full product visible — only the rich textured surface filling the frame. "
            "Editorial textile photography style."
        ),
    },
    {
        "slug": "detail",
        "aspect": "1:1",
        "label_en": "technical detail",
        "scene": (
            "Detail shot of a key technical feature of the {product_kind}: the mechanism articulation, "
            "the remote control or recline lever, the motor housing, or a precision-engineered hinge. "
            "Clean light grey neutral background, soft directional studio lighting from the right. "
            "1:1 square framing, the technical detail is the hero of the shot, "
            "beautifully lit to convey precision and quality. "
            "No human present, no text or labels visible."
        ),
    },
    {
        "slug": "in_use",
        "aspect": "4:5",
        "label_en": "in-use lifestyle",
        "scene": (
            "Realistic in-use scene: a person (anonymous, no face visible — only partial silhouette, "
            "back of the head, hand on armrest, or feet on footrest) is using the {product_kind} comfortably. "
            "Warm cozy interior in soft golden afternoon light, like reading a book or relaxing. "
            "Vertical 4:5 framing, natural authentic moment, no posing, the product is the setting. "
            "Editorial lifestyle photography, hint of motion blur if appropriate."
        ),
    },
    {
        "slug": "side_profile",
        "aspect": "4:5",
        "label_en": "side profile shot",
        "scene": (
            "Pure side-view profile of the {product_kind}, shot at 90 degrees from the side or three-quarter back angle. "
            "Plain neutral light grey #E7E5E4 studio background, single soft side light revealing the silhouette. "
            "Vertical 4:5 framing, the product fills 80% of the frame, all profile lines visible: "
            "the curve of the back, the angle of the armrest, the shape of the legs or base. "
            "Architectural product photography emphasizing form and proportions."
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
    """

    def __init__(self, cap_usd: float = DEFAULT_BUDGET_CAP_USD):
        self.cap_usd = float(cap_usd)
        self.spent_usd = 0.0
        self.images_generated = 0
        self.images_failed = 0

    def add_image(self, success: bool = True) -> None:
        self.spent_usd += NANO_BANANA_USD_PER_IMAGE
        if success:
            self.images_generated += 1
        else:
            self.images_failed += 1

    def exhausted(self) -> bool:
        return self.spent_usd + NANO_BANANA_USD_PER_IMAGE > self.cap_usd

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cap_usd": round(self.cap_usd, 4),
            "spent_usd": round(self.spent_usd, 4),
            "remaining_usd": round(max(0.0, self.cap_usd - self.spent_usd), 4),
            "images_generated": self.images_generated,
            "images_failed": self.images_failed,
        }


# -------------------------------------------------------------------------
# Build a single style prompt
# -------------------------------------------------------------------------
def build_style_prompt(style: Dict[str, str], product_kind: str, target_color: str) -> str:
    identity = IDENTITY_BLOCK.format(product_kind=product_kind, target_color=target_color)
    scene = style["scene"].format(product_kind=product_kind, target_color=target_color)
    aspect = style["aspect"]
    return (
        f"{identity}\n\n"
        f"SCENE: {scene}\n\n"
        f"ASPECT RATIO: render at exactly {aspect} aspect ratio."
    )


# -------------------------------------------------------------------------
# Generate a single style image and persist it on disk
# -------------------------------------------------------------------------
async def _generate_one_style(
    *,
    product_id: str,
    color_slug: str,
    color_label: str,
    style: Dict[str, str],
    product_kind: str,
    target_color_en: str,
    reference_image_b64: str,
    request_id_prefix: str,
) -> Optional[Dict[str, Any]]:
    """Generate one style image. Returns the dict ready to insert in
    `generated_images_by_variant[color_slug]` or None on failure."""
    prompt = build_style_prompt(style, product_kind, target_color_en)
    try:
        data = await safe_nano_banana_bytes(
            prompt,
            system=(
                "You generate premium product photography for a Silver Economy "
                "D2C brand. You preserve product identity strictly: same shape, "
                "same materials, same features. Only the scene, the lighting and "
                "the camera framing change. Photorealistic editorial style."
            ),
            session_id=f"{request_id_prefix}-{style['slug']}",
            timeout=120,
            request_id=f"{request_id_prefix}-{style['slug']}",
            reference_image_b64=reference_image_b64,
        )
    except LLMUnavailableError as e:
        logger.warning(
            f"[variant-pipeline] LLM down for {product_id[:8]}/{color_slug}/{style['slug']}: {e.last_error}"
        )
        return None
    except Exception as e:
        msg = str(e)
        if "402" in msg or "Budget has been exceeded" in msg or "budget" in msg.lower():
            logger.error("[variant-pipeline] BUDGET EXHAUSTED — abort propagated")
            raise
        logger.exception(f"[variant-pipeline] {product_id[:8]}/{color_slug}/{style['slug']} failed")
        return None
    if not data:
        return None

    # Persist to /uploads/products_ai/{product_id}/variants/{color_slug}/{style}_<rand>.png
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
        "tweak": "8styles-pipeline-v1",
        "label_en": style["label_en"],
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
    new_images: List[Dict[str, Any]] = []
    skipped: List[str] = []

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

        img = await _generate_one_style(
            product_id=product_id,
            color_slug=color_slug,
            color_label=color_label,
            style=style,
            product_kind=product_kind,
            target_color_en=target_color_en,
            reference_image_b64=ref_b64,
            request_id_prefix=request_id,
        )
        budget.add_image(success=bool(img))
        if img:
            new_images.append(img)
            # Replace any existing entry of the same style if overwrite, else append
            if overwrite:
                final_for_color = [x for x in final_for_color if x.get("style") != style["slug"]]
            final_for_color.append(img)
            logger.info(
                f"[variant-pipeline] {request_id}: {style['slug']} OK ({img['aspect']})"
            )

    by_variant[color_slug] = final_for_color
    await db.products.update_one(
        {"id": product_id},
        {"$set": {
            "generated_images_by_variant": by_variant,
            "generated_images_by_variant_updated_at": datetime.now(timezone.utc).isoformat(),
        }},
    )

    return {
        "ok": True,
        "product_id": product_id,
        "color_slug": color_slug,
        "color_label": color_label,
        "images": final_for_color,
        "new_images_count": len(new_images),
        "skipped_styles": skipped,
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
