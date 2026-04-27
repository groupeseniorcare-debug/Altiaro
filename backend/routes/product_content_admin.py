"""
Lot I (Phase 2.1) — Admin endpoints for product content AI back-fill.

Two admin-only endpoints to regenerate Lot I content (tagline, USPs) for an
existing product, useful when the launch.py pipeline didn't produce them
or when the user wants to regenerate manually.

Routes:
- POST /api/admin/products/{product_id}/regenerate-tagline
- POST /api/admin/products/{product_id}/regenerate-usps

Both endpoints:
- Require admin role (or site owner if `concepteur` access is later allowed)
- Use Claude Haiku 4.5 via `services.product_content_ai`
- Persist result in `products.tagline` (string) or `products.usps` (list)
- Return the freshly generated content + cost estimate (~$0.001-0.005 per call)
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from deps import db, get_current_user
from services.product_content_ai import (
    generate_product_tagline,
    generate_product_usps,
)

logger = logging.getLogger("conceptfactory.product_content_admin")
router = APIRouter()


async def _require_admin_or_site_owner(user: dict, site_id: str) -> None:
    """Allow admins or site owners (concepteur with site_id access)."""
    if user.get("role") == "admin":
        return
    site = await db.sites.find_one({"id": site_id}, {"_id": 0, "owner_id": 1})
    if site and site.get("owner_id") == user.get("id"):
        return
    raise HTTPException(403, "Admin or site owner required")


@router.post(
    "/admin/products/{product_id}/regenerate-tagline",
    tags=["product-content-admin"],
    summary="Regénère la tagline IA d'un produit (Haiku 4.5)",
)
async def regenerate_product_tagline(
    product_id: str,
    user: dict = Depends(get_current_user),
):
    """Regenerate the product tagline (40-80 chars, French) via Claude Haiku 4.5.

    Persists in `products.tagline`. Returns:
    ```json
    {
      "ok": true,
      "product_id": "...",
      "tagline": "Le sommeil retrouvé, sans compromis",
      "tagline_length": 38,
      "model": "claude-haiku-4-5",
      "cost_estimate_usd": 0.002
    }
    ```
    """
    product = await db.products.find_one({"id": product_id}, {"_id": 0})
    if not product:
        raise HTTPException(404, "Produit introuvable")
    await _require_admin_or_site_owner(user, product.get("site_id"))

    site = await db.sites.find_one(
        {"id": product["site_id"]}, {"_id": 0, "design.brand": 1}
    )
    brand = ((site or {}).get("design") or {}).get("brand") or {}

    try:
        tagline = await generate_product_tagline(product, brand, request_id=f"backfill-tagline-{product_id[:8]}")
    except Exception as e:
        logger.exception(f"[regenerate-tagline] {product_id} failed")
        raise HTTPException(502, f"Génération IA échouée : {str(e)[:200]}")

    if not tagline:
        raise HTTPException(502, "Tagline vide retournée par l'IA")

    now_iso = datetime.now(timezone.utc).isoformat()
    await db.products.update_one(
        {"id": product_id},
        {"$set": {
            "tagline": tagline,
            "tagline_generated_at": now_iso,
            "updated_at": now_iso,
        }},
    )
    logger.info(f"[regenerate-tagline] {product_id} → '{tagline[:60]}…' ({len(tagline)} chars)")

    return {
        "ok": True,
        "product_id": product_id,
        "tagline": tagline,
        "tagline_length": len(tagline),
        "model": "claude-haiku-4-5",
        "cost_estimate_usd": 0.002,
    }


@router.post(
    "/admin/products/{product_id}/regenerate-usps",
    tags=["product-content-admin"],
    summary="Regénère les 4 USPs IA d'un produit (Haiku 4.5)",
)
async def regenerate_product_usps(
    product_id: str,
    user: dict = Depends(get_current_user),
):
    """Regenerate 4 product-specific USPs via Claude Haiku 4.5.

    Each USP has shape: `{icon: <LucideName>, title: ≤30c, description: ≤140c}`.

    Persists in `products.usps`. Returns:
    ```json
    {
      "ok": true,
      "product_id": "...",
      "usps": [
        {"icon": "Wind", "title": "Mécanisme à 2 moteurs silencieux", "description": "Moins de 30 dB ..."},
        ...
      ],
      "model": "claude-haiku-4-5",
      "cost_estimate_usd": 0.005
    }
    ```
    """
    product = await db.products.find_one({"id": product_id}, {"_id": 0})
    if not product:
        raise HTTPException(404, "Produit introuvable")
    await _require_admin_or_site_owner(user, product.get("site_id"))

    site = await db.sites.find_one(
        {"id": product["site_id"]}, {"_id": 0, "design.brand": 1}
    )
    brand = ((site or {}).get("design") or {}).get("brand") or {}

    try:
        usps = await generate_product_usps(product, brand, request_id=f"backfill-usps-{product_id[:8]}")
    except Exception as e:
        logger.exception(f"[regenerate-usps] {product_id} failed")
        raise HTTPException(502, f"Génération IA échouée : {str(e)[:200]}")

    if not usps or len(usps) < 4:
        raise HTTPException(
            502,
            f"L'IA n'a retourné que {len(usps) if usps else 0} USPs valides "
            f"(attendu 4). Réessaye, ou vérifie la description du produit.",
        )

    now_iso = datetime.now(timezone.utc).isoformat()
    await db.products.update_one(
        {"id": product_id},
        {"$set": {
            "usps": usps,
            "usps_generated_at": now_iso,
            "updated_at": now_iso,
        }},
    )
    logger.info(f"[regenerate-usps] {product_id} → {len(usps)} USPs (icons: {[u['icon'] for u in usps]})")

    return {
        "ok": True,
        "product_id": product_id,
        "usps": usps,
        "model": "claude-haiku-4-5",
        "cost_estimate_usd": 0.005,
    }
