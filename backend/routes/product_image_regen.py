"""
Phase 2.7.3 — Régénération ciblée d'une image produit (1 style × 1 variante)
depuis le cockpit étape 5.

Le concepteur (ou l'admin) peut, via cette route, demander à l'IA de
régénérer une image qui ne lui plaît pas, optionnellement en lui fournissant
un addon de prompt en langage naturel ("la personne doit être plus âgée",
"plus de lumière", etc.).

Réutilise le pipeline existant `services/product_variant_pipeline.py` en
mode `only_styles=[…]` + `extra_brief="…"`.
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from deps import db, get_current_user
from services.product_variant_pipeline import (
    ALL_STYLE_SLUGS,
    BudgetCap,
    generate_full_variant_set,
)

router = APIRouter(tags=["product-image-regenerate"])
logger = logging.getLogger("conceptfactory.product_image_regen")


class RegenInput(BaseModel):
    variant_color: str = Field(
        ...,
        description="Slug couleur (ex: 'black', 'white', 'brown'). Doit exister dans `generated_images_by_variant`.",
    )
    style: str = Field(
        ...,
        description="Slug du style à régénérer (ex: 'in_use', 'studio_main', 'lifestyle').",
    )
    custom_prompt_addon: Optional[str] = Field(
        None,
        max_length=400,
        description="Précision libre du concepteur — ajoutée au brief par défaut. Ex: 'la personne doit être plus âgée avec des cheveux gris'.",
    )


async def _check_product_access(site_id: str, product_id: str, user: dict):
    site = await db.sites.find_one(
        {"id": site_id},
        {"_id": 0, "id": 1, "operator_id": 1},
    )
    if not site:
        raise HTTPException(404, "Site introuvable")
    role = (user or {}).get("role")
    uid = (user or {}).get("id")
    if role != "admin" and site.get("operator_id") != uid:
        raise HTTPException(403, "Accès interdit")
    p = await db.products.find_one(
        {"id": product_id, "site_id": site_id},
        {"_id": 0, "id": 1},
    )
    if not p:
        raise HTTPException(404, "Produit introuvable sur ce site")
    return site, p


@router.post("/sites/{site_id}/products/{product_id}/regenerate-image")
async def regenerate_one_image(
    site_id: str,
    product_id: str,
    data: RegenInput,
    user: dict = Depends(get_current_user),
):
    """Régénère 1 image (1 style × 1 variante) avec un addon de prompt optionnel.

    Coût ~0,06$ par appel (Nano Banana ~0,05$ + Vision QA ~0,008$).
    Persiste la nouvelle image, dédoublonne automatiquement (Phase 2.7.1)
    et retourne l'URL de la nouvelle image.
    """
    await _check_product_access(site_id, product_id, user)

    style_slug = (data.style or "").strip().lower()
    if style_slug not in ALL_STYLE_SLUGS:
        raise HTTPException(
            400,
            f"Style inconnu '{style_slug}'. Valides: {ALL_STYLE_SLUGS}",
        )

    color_slug = (data.variant_color or "").strip().lower()
    if not color_slug:
        raise HTTPException(400, "variant_color requis")

    # Per-call cap = 0.30$ (3 attempts max @ 0.058$ + QA ≈ 0.18$).
    budget = BudgetCap(cap_usd=0.30)
    try:
        result = await generate_full_variant_set(
            db,
            product_id,
            color_slug,
            overwrite=True,
            budget=budget,
            request_id=f"regen-{site_id[:8]}-{product_id[:8]}-{color_slug}-{style_slug}",
            only_styles=[style_slug],
            extra_brief=data.custom_prompt_addon or None,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.exception(f"[regen] failed {product_id[:8]}/{color_slug}/{style_slug}")
        msg = str(e)
        if "402" in msg or "budget" in msg.lower():
            raise HTTPException(402, "Budget LLM épuisé — réessayez plus tard")
        raise HTTPException(502, f"Régénération échouée : {msg[:160]}")

    # Find the freshly generated image entry for this style
    new_img = next(
        (img for img in (result.get("images") or []) if img.get("style") == style_slug),
        None,
    )
    if not new_img:
        # The pipeline ran but QA rejected all 3 attempts → degraded.
        return {
            "ok": False,
            "regenerated": False,
            "reason": "qa_rejected_all_attempts",
            "style": style_slug,
            "variant_color": color_slug,
            "budget": result.get("budget"),
            "failed_qa_styles": result.get("failed_qa_styles") or [],
        }

    return {
        "ok": True,
        "regenerated": True,
        "style": style_slug,
        "variant_color": color_slug,
        "image": new_img,
        "url": new_img.get("url"),
        "qa_passed": new_img.get("qa_passed"),
        "qa_attempt": new_img.get("qa_attempt"),
        "budget": result.get("budget"),
    }
