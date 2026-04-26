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


STYLE_PRESETS = {
    "lifestyle": (
        "Premium lifestyle photography, soft natural morning light, warm tones, "
        "shallow depth of field, senior-friendly scene, tasteful interior, "
        "editorial composition. The product is the hero, prominently featured."
    ),
    "studio": (
        "Studio product photography on cream paper sweep, diffused softbox, "
        "subtle shadow, editorial catalog look, 8k, ultra-sharp focus. No hands, no text."
    ),
    "closeup": (
        "Ultra-detailed macro close-up, texture and materials visible, "
        "warm rim light, editorial magazine aesthetic, shallow DoF, cinematic. "
        "Focus on craftsmanship and premium materials."
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


async def _generate_one(prompt: str, site_id: str, product_id: str) -> Optional[str]:
    """Call Nano Banana and write the PNG to disk. Returns public URL or None.

    Phase 0 — utilise `safe_nano_banana_bytes` (retry expo + circuit breaker
    sur 'nano_banana'). Si le breaker est OPEN ou les retries échouent, on
    raise LLMUnavailableError → traduit en 503 pour l'UI.
    """
    if not EMERGENT_LLM_KEY:
        raise HTTPException(400, "EMERGENT_LLM_KEY absente")
    from services.llm_resilience import safe_nano_banana_bytes, LLMUnavailableError
    try:
        data = await safe_nano_banana_bytes(
            prompt,
            system="You generate premium product photography for a Silver Economy D2C brand.",
            session_id=f"pimg-{product_id}-{uuid.uuid4().hex[:6]}",
            timeout=120,
            request_id=f"pimg-{product_id[:8]}",
        )
        if not data:
            return None
        filename = f"p_{product_id}_{uuid.uuid4().hex[:8]}.png"
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


class GenProductImgInput(BaseModel):
    style: str = Field(default="lifestyle",
                       description="lifestyle | studio | closeup | in_use")
    tweak: Optional[str] = ""
    replace_main: bool = False  # if True, prepend to product.images[0]


@router.post("/products/{product_id}/generate-image")
async def generate_product_image(
    product_id: str,
    data: GenProductImgInput,
    user: dict = Depends(get_current_user),
):
    """Generate one premium AI image for a product using the brand palette."""
    product = await db.products.find_one({"id": product_id}, {"_id": 0})
    if not product:
        raise HTTPException(404, "Produit introuvable")
    site_id = product.get("site_id")
    await _check_site_access(site_id, user)
    site = await db.sites.find_one({"id": site_id}, {"_id": 0, "design.brand": 1})
    brand = ((site or {}).get("design") or {}).get("brand") or {}

    prompt = _build_prompt(product, brand, data.style, data.tweak or "")
    url = await _generate_one(prompt, site_id, product_id)
    if not url:
        raise HTTPException(502, "L'IA n'a pas renvoyé d'image.")

    update = {"$push": {"generated_images": {
        "url": url,
        "style": data.style,
        "tweak": data.tweak or "",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }}}
    if data.replace_main:
        # Prepend to images[]
        images = list(product.get("images") or [])
        images.insert(0, url)
        update["$set"] = {"images": images[:10],
                          "updated_at": datetime.now(timezone.utc).isoformat()}
    await db.products.update_one({"id": product_id}, update)
    return {"ok": True, "url": url, "style": data.style, "prompt": prompt[:300]}


class BulkGenInput(BaseModel):
    style: str = "lifestyle"
    limit: int = 20
    only_missing: bool = True  # only for products with no generated_images yet


@router.post("/sites/{site_id}/products/bulk-generate-images")
async def bulk_generate_images(
    site_id: str,
    data: BulkGenInput,
    user: dict = Depends(get_current_user),
):
    """Background-ish bulk generator (runs synchronously up to `limit` items).
    For large catalogs prefer calling per-product, as Nano Banana is ~60-90 s/img."""
    await _check_site_access(site_id, user)
    query = {"site_id": site_id, "status": "active"}
    if data.only_missing:
        query["generated_images"] = {"$exists": False}
    products = await db.products.find(query, {"_id": 0, "id": 1, "name": 1}).limit(data.limit).to_list(data.limit)
    if not products:
        return {"ok": True, "generated": 0, "skipped": 0, "message": "Rien à générer."}
    site = await db.sites.find_one({"id": site_id}, {"_id": 0, "design.brand": 1})
    brand = ((site or {}).get("design") or {}).get("brand") or {}
    ok_count, fail = 0, 0
    for p in products:
        try:
            prompt = _build_prompt(p, brand, data.style, "")
            url = await _generate_one(prompt, site_id, p["id"])
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
