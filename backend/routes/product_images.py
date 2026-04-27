"""
Product hero images — AI-generated premium lifestyle shots via Nano Banana (Gemini image).

Endpoints:
- POST /api/products/{id}/generate-image — generate 1 hero image from prompt + brand palette
- POST /api/sites/{site_id}/products/bulk-generate-images — bg job for all products without AI image

Stores public URL under product.generated_images[] (list) and optionally prepends to images[].
"""
from __future__ import annotations

import asyncio
import base64
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from deps import db, get_current_user, _check_site_access, EMERGENT_LLM_KEY, UPLOAD_DIR

logger = logging.getLogger("conceptfactory.product_images")
router = APIRouter()

NANO_BANANA_MODEL = "gemini-3.1-flash-image-preview"

PRODUCT_IMG_DIR = UPLOAD_DIR / "products_ai"
PRODUCT_IMG_DIR.mkdir(parents=True, exist_ok=True)


STYLE_PRESETS_V1_DEPRECATED = None  # placeholder — see STYLE_PRESETS below (Lot C)

# Lot C — STYLE_PRESETS renforcés avec préservation d'identité produit
# (image-to-image par défaut quand une image AE source existe).
#
# ⚠️ Le préfixe IDENTITY_HEADER est injecté automatiquement dans le prompt
#    par _build_prompt() quand le caller passe `reference_image_b64` à
#    _generate_one(). Pour les générations text-only (rare, ex: brand logo,
#    testimonial portraits), le préfixe n'est PAS appliqué.

IDENTITY_HEADER = (
    "PRESERVE EXACT IDENTITY OF THE PRODUCT IN THE REFERENCE IMAGE. "
    "The product MUST be visually identical to the source: same model, same color, same fabric, "
    "same dimensions, same accessories, same control panel, same footrest mechanism, "
    "same side pockets, same headrest, same stitching, same proportions. "
    "Do NOT redesign, modify, improve, restyle, or update the product. "
    "ONLY the surrounding scene, lighting, and camera angle should differ. "
)

STYLE_PRESETS = {
    "lifestyle": (
        "Generate a professional lifestyle product photography in an elegant Haussmann-style "
        "Parisian apartment living room. Setting: herringbone parquet flooring (point de Hongrie), "
        "white marble fireplace with classical moldings, large window with soft golden-hour daylight, "
        "ivory linen curtains, brass design lamp, leather-bound classical books. "
        "Camera: 35mm at f/4, slight low angle, rule-of-thirds. NO PERSON in the frame. "
        "Style: editorial luxury minimal, Architectural Digest aesthetic, photorealistic, 4K. "
        "No text, no watermark, no brand names."
    ),
    "studio": (
        "Generate a high-end studio product photography. Background: seamless gradient from warm "
        "ivory (#F5F2EB top) to soft anthracite (#1F1F1F bottom), no texture, no clutter. "
        "Camera: 50mm at f/8, three-quarter view (slightly from the right), eye-level. "
        "Lighting: large softbox at 45° upper-left + subtle rim light upper-right, soft shadow under product. "
        "Style: Apple-product-page minimalist aesthetic, ultra-clean, ultra-sharp focus, photorealistic, 4K. "
        "No logo, no text, no background distraction."
    ),
    "closeup": (
        "Generate a closeup detail product photography. Tight macro on the most visible textural "
        "element of the product (stitching, fabric, mechanism, control panel — pick the most prominent in source). "
        "Lighting: warm grazing light from upper-left at 30°, revealing fabric weave and seams. "
        "Camera: 100mm macro at f/2.8, very shallow depth of field. "
        "Style: editorial macro photography, focus stacked on the texture, premium magazine ad aesthetic, 4K."
    ),
    "in_use": (
        "Candid lifestyle photo of a 70-year-old person using the product in a "
        "beautifully lit home, natural smile, dignity, warm cinematic palette, "
        "editorial documentary style, no staged feel."
    ),
    "detail": (
        "Premium catalogue detail shot focusing on a single functional element "
        "of the product (mechanism, finishing, stitching, articulation). "
        "Soft directional studio light, dark moody background, ultra-sharp macro. "
        "Loro Piana lookbook aesthetic. Materials and craftsmanship as the hero."
    ),
}


async def _generate_one(
    prompt: str,
    site_id: str,
    product_id: str,
    *,
    reference_image_b64: Optional[str] = None,
    style: Optional[str] = None,
) -> Optional[str]:
    """Call Nano Banana and write the PNG to disk. Returns public URL or None.

    Phase 0 — utilise `safe_nano_banana_bytes` (retry expo + circuit breaker
    sur 'nano_banana'). Si le breaker est OPEN ou les retries échouent, on
    raise LLMUnavailableError → traduit en 503 pour l'UI.

    Lot C — `reference_image_b64` (optionnel) : si fourni, active le mode
    image-to-image (le modèle voit l'image source comme contexte multimodal)
    ce qui produit une variation cohérente avec le produit réel. Le préfixe
    IDENTITY_HEADER est ajouté automatiquement au prompt dans ce mode pour
    forcer la préservation du modèle/couleur/tissu/proportions.

    `style` (optionnel) : utilisé uniquement pour le nom de fichier
    (`p_{pid}_{style}_{rand}.png`) — facilite le tri par style côté disque.
    """
    if not EMERGENT_LLM_KEY:
        raise HTTPException(400, "EMERGENT_LLM_KEY absente")
    from services.llm_resilience import safe_nano_banana_bytes, LLMUnavailableError

    # Lot C — injecte le header identity-preservation devant le prompt
    # quand on est en mode image-to-image (sinon le modèle invente un produit générique)
    final_prompt = f"{IDENTITY_HEADER}\n\n{prompt}" if reference_image_b64 else prompt
    try:
        data = await safe_nano_banana_bytes(
            final_prompt,
            system="You generate premium product photography for a Silver Economy D2C brand.",
            session_id=f"pimg-{product_id}-{uuid.uuid4().hex[:6]}",
            timeout=120,
            request_id=f"pimg-{product_id[:8]}",
            reference_image_b64=reference_image_b64,
        )
        if not data:
            return None
        style_part = f"_{style}" if style else ""
        filename = f"p_{product_id}{style_part}_{uuid.uuid4().hex[:8]}.png"
        path = PRODUCT_IMG_DIR / filename
        path.write_bytes(data)
        # Flag the LLM as healthy on any success
        try:
            await db.platform_health.update_one(
                {"key": "llm"},
                {"$set": {"key": "llm", "status": "ok",
                          "last_success_at": datetime.now(timezone.utc).isoformat()}},
                upsert=True,
            )
        except Exception:
            pass
        return f"/api/uploads/products_ai/{filename}"
    except LLMUnavailableError as e:
        logger.warning(f"[nano-product] LLM down for {product_id}: {e.last_error}")
        raise HTTPException(503, "Génération image indisponible (proxy upstream KO). Réessayez dans quelques minutes.")
    except HTTPException:
        raise
    except Exception as e:
        msg = str(e)
        if "Budget has been exceeded" in msg or ("budget" in msg.lower() and "exceeded" in msg.lower()):
            try:
                await db.platform_health.update_one(
                    {"key": "llm"},
                    {"$set": {"key": "llm", "status": "budget_exhausted",
                              "last_error_at": datetime.now(timezone.utc).isoformat()}},
                    upsert=True,
                )
            except Exception:
                pass
            raise HTTPException(402, "Budget Emergent LLM Key épuisé. Recharge la clé.")
        logger.exception("Nano Banana product image failed")
        raise HTTPException(502, f"Génération image échouée : {msg[:180]}")


def _build_prompt(product: dict, brand: dict, style: str, user_tweak: str) -> str:
    name_fr = ""
    name = product.get("name") or {}
    if isinstance(name, dict):
        name_fr = name.get("fr") or name.get("en") or ""
    else:
        name_fr = str(name)
    palette = brand.get("palette") or {}
    primary = brand.get("primary_color") or palette.get("primary") or "#B84B31"
    accent = brand.get("accent_color") or palette.get("accent") or "#E9C46A"
    background = brand.get("background_color") or palette.get("background") or "#FDFBF7"
    text_col = brand.get("text_color") or palette.get("text") or "#1C1917"
    brand_voice = brand.get("voice") or "chaleureux, rassurant, premium"
    base_style = STYLE_PRESETS.get(style, STYLE_PRESETS["lifestyle"])
    tweak_line = f"\nExtra art direction: {user_tweak}\n" if user_tweak else ""
    return (
        f"Premium editorial photograph of the product: {name_fr}. "
        f"{base_style}\n\n"
        f"Brand palette (must harmonize): primary {primary}, accent {accent}, "
        f"background {background}, key text tone {text_col}. "
        f"Brand voice: {brand_voice}. Target audience: 60-90 year-olds.\n"
        f"Constraints: no text, no watermark, no logos, no brand names visible, "
        f"no hands holding the product unless essential, single hero subject, "
        f"magazine-quality composition, rule of thirds, photorealistic, 8k.\n"
        f"{tweak_line}"
    )


async def _fetch_ae_reference_b64(product: dict) -> Optional[str]:
    """Lot C — Helper : télécharge l'image source AliExpress (product.images[0])
    et retourne son base64 brut (sans préfixe data-uri).

    Utilisé automatiquement par `generate_product_image` et le pipeline
    launch-auto pour activer le mode image-to-image (cohérence visuelle
    avec le produit réel). Retourne None si pas de source ou téléchargement
    échoué : le caller fallback sur text-only dans ce cas.
    """
    images = product.get("images") or []
    if not images:
        return None
    src = images[0]
    src_url = src if isinstance(src, str) else (src.get("url") if isinstance(src, dict) else None)
    if not src_url:
        return None
    try:
        import httpx
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as cli:
            r = await cli.get(src_url, headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code == 200 and r.content:
                return base64.b64encode(r.content).decode("ascii")
    except Exception as e:
        logger.warning(f"[pimg] AE reference download failed for {src_url[:80]}: {e}")
    return None


class GenProductImgInput(BaseModel):
    style: str = Field(default="studio",
                       description="studio | lifestyle | closeup | in_use | detail")
    tweak: Optional[str] = ""
    replace_main: bool = False  # if True, prepend to product.images[0]
    use_reference: bool = True   # Lot C — img-to-img by default (preserve product identity)


@router.post("/products/{product_id}/generate-image")
async def generate_product_image(
    product_id: str,
    data: GenProductImgInput,
    user: dict = Depends(get_current_user),
):
    """Generate one premium AI image for a product using the brand palette.

    Lot C — par défaut `use_reference=True` : l'image source AliExpress
    est passée comme contexte multimodal à Nano Banana → variation cohérente
    avec le produit réel (même modèle, même couleur, même tissu). Pour
    désactiver ce mode (cas rare : produit sans image source), passer
    `use_reference=False`.
    """
    product = await db.products.find_one({"id": product_id}, {"_id": 0})
    if not product:
        raise HTTPException(404, "Produit introuvable")
    site_id = product.get("site_id")
    await _check_site_access(site_id, user)
    site = await db.sites.find_one({"id": site_id}, {"_id": 0, "design.brand": 1})
    brand = ((site or {}).get("design") or {}).get("brand") or {}

    prompt = _build_prompt(product, brand, data.style, data.tweak or "")
    ref_b64 = await _fetch_ae_reference_b64(product) if data.use_reference else None
    url = await _generate_one(prompt, site_id, product_id,
                              reference_image_b64=ref_b64, style=data.style)
    if not url:
        raise HTTPException(502, "L'IA n'a pas renvoyé d'image.")

    update = {"$push": {"generated_images": {
        "url": url,
        "style": data.style,
        "tweak": data.tweak or "",
        "method": "img-to-img" if ref_b64 else "text-only",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }}}
    if data.replace_main:
        # Prepend to images[]
        images = list(product.get("images") or [])
        images.insert(0, url)
        update["$set"] = {"images": images[:10],
                          "updated_at": datetime.now(timezone.utc).isoformat()}
    await db.products.update_one({"id": product_id}, update)
    return {"ok": True, "url": url, "style": data.style,
            "method": "img-to-img" if ref_b64 else "text-only",
            "prompt": prompt[:300]}


class BulkGenInput(BaseModel):
    style: str = "studio"  # Lot C — studio par défaut (image principale)
    limit: int = 20
    only_missing: bool = True  # only for products with no generated_images yet
    use_reference: bool = True  # Lot C — img-to-img by default


@router.post("/sites/{site_id}/products/bulk-generate-images")
async def bulk_generate_images(
    site_id: str,
    data: BulkGenInput,
    user: dict = Depends(get_current_user),
):
    """Background-ish bulk generator (runs synchronously up to `limit` items).
    For large catalogs prefer calling per-product, as Nano Banana is ~60-90 s/img.

    Lot C — par défaut img-to-img (cohérence visuelle avec source AE).
    """
    await _check_site_access(site_id, user)
    query = {"site_id": site_id, "status": "active"}
    if data.only_missing:
        query["generated_images"] = {"$exists": False}
    products = await db.products.find(
        query, {"_id": 0, "id": 1, "name": 1, "images": 1}
    ).limit(data.limit).to_list(data.limit)
    if not products:
        return {"ok": True, "generated": 0, "skipped": 0, "message": "Rien à générer."}
    site = await db.sites.find_one({"id": site_id}, {"_id": 0, "design.brand": 1})
    brand = ((site or {}).get("design") or {}).get("brand") or {}
    ok_count, fail = 0, 0
    for p in products:
        try:
            prompt = _build_prompt(p, brand, data.style, "")
            ref_b64 = await _fetch_ae_reference_b64(p) if data.use_reference else None
            url = await _generate_one(prompt, site_id, p["id"],
                                      reference_image_b64=ref_b64, style=data.style)
            if url:
                await db.products.update_one(
                    {"id": p["id"]},
                    {"$push": {"generated_images": {
                        "url": url, "style": data.style,
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    }}},
                )
                ok_count += 1
        except HTTPException as he:
            fail += 1
            if he.status_code == 402:  # budget exhausted — stop here
                return {"ok": False, "generated": ok_count, "failed": fail,
                        "message": "Budget IA épuisé, génération interrompue."}
        except Exception:
            fail += 1
    return {"ok": True, "generated": ok_count, "failed": fail, "style": data.style}


@router.get("/products/{product_id}/generated-images")
async def list_generated_images(product_id: str, user: dict = Depends(get_current_user)):
    product = await db.products.find_one({"id": product_id}, {"_id": 0, "site_id": 1, "generated_images": 1})
    if not product:
        raise HTTPException(404, "Produit introuvable")
    await _check_site_access(product["site_id"], user)
    return {"images": product.get("generated_images") or []}


class GenSectionImgInput(BaseModel):
    section_index: int
    style: str = "lifestyle"
    tweak: Optional[str] = ""


@router.post("/products/{product_id}/generate-section-image")
async def generate_narrative_section_image(
    product_id: str,
    data: GenSectionImgInput,
    user: dict = Depends(get_current_user),
):
    """Generate a Nano Banana image for a specific narrative section and
    store the URL directly on narrative.sections[i].image."""
    product = await db.products.find_one({"id": product_id}, {"_id": 0})
    if not product:
        raise HTTPException(404, "Produit introuvable")
    site_id = product.get("site_id")
    await _check_site_access(site_id, user)
    sections = ((product.get("narrative") or {}).get("sections")) or []
    if data.section_index < 0 or data.section_index >= len(sections):
        raise HTTPException(400, f"Section invalide (0-{len(sections)-1})")
    section = sections[data.section_index]
    site = await db.sites.find_one({"id": site_id}, {"_id": 0, "design.brand": 1})
    brand = ((site or {}).get("design") or {}).get("brand") or {}

    # Use section title + body as art-direction context
    context_prompt = _build_prompt(product, brand, data.style, data.tweak or "")
    extra = (
        f"\nContexte narratif de la section : « {section.get('title', '')} » — "
        f"{section.get('body', '')[:400]}.\n"
        "L'image doit illustrer cette section de manière sensorielle et concrète "
        "(matières, gestes, lumière), sans texte ni logo visible."
    )
    url = await _generate_one(context_prompt + extra, site_id, f"{product_id}-sec{data.section_index}")
    if not url:
        raise HTTPException(502, "L'IA n'a pas renvoyé d'image.")

    # Update section[i].image in place
    await db.products.update_one(
        {"id": product_id},
        {"$set": {
            f"narrative.sections.{data.section_index}.image": url,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }},
    )
    return {"ok": True, "url": url, "section_index": data.section_index}


@router.delete("/products/{product_id}/generated-images")
async def clear_generated_images(product_id: str, user: dict = Depends(get_current_user)):
    product = await db.products.find_one({"id": product_id}, {"_id": 0, "site_id": 1})
    if not product:
        raise HTTPException(404, "Produit introuvable")
    await _check_site_access(product["site_id"], user)
    await db.products.update_one({"id": product_id}, {"$set": {"generated_images": []}})
    return {"ok": True}
