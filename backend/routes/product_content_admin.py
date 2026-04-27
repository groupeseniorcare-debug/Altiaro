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

import asyncio
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from deps import db, require_admin
from services.product_content_ai import (
    generate_product_tagline,
    generate_product_usps,
    generate_product_how_to,
    generate_product_faq,
)
from services.product_variant_pipeline import (
    DEFAULT_BUDGET_CAP_USD,
    BudgetCap,
    generate_all_variant_sets_for_site,
    generate_full_variant_set,
    slugify_color,
)

logger = logging.getLogger("conceptfactory.product_content_admin")
router = APIRouter()


# Note (2026-04-27 Phase 2.1 hardening) : ces routes sont **strictement
# admin-only**. Le site owner n'a PLUS le droit d'appeler ces endpoints
# (resserrage de sécurité après audit e1_tester). Pour une régénération
# côté concepteur, exposer plus tard un endpoint dédié sous
# `/sites/{site_id}/products/{id}/regenerate-*` avec `_check_site_access`.


@router.post(
    "/admin/products/{product_id}/regenerate-tagline",
    tags=["product-content-admin"],
    summary="Regénère la tagline IA d'un produit (Haiku 4.5) — admin only",
)
async def regenerate_product_tagline(
    product_id: str,
    user: dict = Depends(require_admin),
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
    summary="Regénère les 4 USPs IA d'un produit (Haiku 4.5) — admin only",
)
async def regenerate_product_usps(
    product_id: str,
    user: dict = Depends(require_admin),
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


# ============================================================================
# Phase 2.3 (Lot I I11) — Product HowTo steps
# ============================================================================
@router.post(
    "/admin/products/{product_id}/regenerate-how-to",
    tags=["product-content-admin"],
    summary="Regénère les 3-4 étapes HowTo IA d'un produit (Haiku 4.5) — admin only",
)
async def regenerate_product_how_to_endpoint(
    product_id: str,
    n_steps: int = Query(4, ge=3, le=5),
    user: dict = Depends(require_admin),
):
    product = await db.products.find_one({"id": product_id}, {"_id": 0})
    if not product:
        raise HTTPException(404, "Produit introuvable")
    site = await db.sites.find_one({"id": product["site_id"]}, {"_id": 0, "design.brand": 1})
    brand = ((site or {}).get("design") or {}).get("brand") or {}
    try:
        steps = await generate_product_how_to(
            product, brand, n_steps=n_steps,
            request_id=f"backfill-howto-{product_id[:8]}",
        )
    except Exception as e:
        logger.exception(f"[regenerate-how-to] {product_id} failed")
        raise HTTPException(502, f"Génération IA échouée : {str(e)[:200]}")

    now_iso = datetime.now(timezone.utc).isoformat()
    await db.products.update_one(
        {"id": product_id},
        {"$set": {
            "how_to_steps": steps,
            "how_to_steps_generated_at": now_iso,
            "updated_at": now_iso,
        }},
    )
    logger.info(f"[regenerate-how-to] {product_id} → {len(steps)} steps")
    return {
        "ok": True, "product_id": product_id, "how_to_steps": steps,
        "model": "claude-haiku-4-5", "cost_estimate_usd": 0.004,
    }


# ============================================================================
# Phase 2.3 (Lot I I12) — Product-specific FAQ (single source of truth)
# ============================================================================
@router.post(
    "/admin/products/{product_id}/regenerate-faq",
    tags=["product-content-admin"],
    summary="Regénère la FAQ produit (4-6 Q/R) IA — admin only",
)
async def regenerate_product_faq_endpoint(
    product_id: str,
    n_questions: int = Query(5, ge=4, le=6),
    user: dict = Depends(require_admin),
):
    product = await db.products.find_one({"id": product_id}, {"_id": 0})
    if not product:
        raise HTTPException(404, "Produit introuvable")
    site = await db.sites.find_one({"id": product["site_id"]}, {"_id": 0, "design.brand": 1})
    brand = ((site or {}).get("design") or {}).get("brand") or {}
    try:
        faq = await generate_product_faq(
            product, brand, n_questions=n_questions,
            request_id=f"backfill-faq-{product_id[:8]}",
        )
    except Exception as e:
        logger.exception(f"[regenerate-faq] {product_id} failed")
        raise HTTPException(502, f"Génération IA échouée : {str(e)[:200]}")

    now_iso = datetime.now(timezone.utc).isoformat()
    await db.products.update_one(
        {"id": product_id},
        {"$set": {
            "faq_product": faq,
            "faq_product_generated_at": now_iso,
            "updated_at": now_iso,
        }},
    )
    logger.info(f"[regenerate-faq] {product_id} → {len(faq)} Q/A")
    return {
        "ok": True, "product_id": product_id, "faq_product": faq,
        "model": "claude-haiku-4-5", "cost_estimate_usd": 0.005,
    }


# ============================================================================
# Lot I (Phase 2.2) — Variant images pipeline (8 styles per color variant)
# ============================================================================
@router.post(
    "/admin/products/{product_id}/regenerate-variant-images",
    tags=["product-variant-images"],
    summary="Regénère les 8 styles d'images (Nano Banana img-to-img) pour 1 variante couleur — admin only",
)
async def regenerate_product_variant_images(
    product_id: str,
    variant_id: str = Query(..., description="Slug couleur (ex: 'black') OU ID de variant. Slug recommandé."),
    overwrite: bool = Query(False, description="Si True, regénère TOUS les 8 styles même s'ils existent déjà."),
    budget_cap_usd: float = Query(DEFAULT_BUDGET_CAP_USD, description="Cap budget USD pour cet appel (max 5$)."),
    user: dict = Depends(require_admin),
):
    """Génère les 8 styles fixes (`studio_main`, `studio_card`, `lifestyle`,
    `wide_lifestyle`, `closeup`, `detail`, `in_use`, `side_profile`) pour une
    variante couleur d'un produit, via Nano Banana img-to-img.

    L'image source img-to-img est :
    1. Première image existante de `generated_images_by_variant[variant_id]` si dispo
    2. Sinon `generated_images[0]` du produit

    Idempotent : si un style existe déjà → skip (sauf si `overwrite=True`).
    Budget-aware : stoppe si le cap est atteint, retourne le partiel.

    Coût indicatif : 8 × 0.05$ = ~0.40 $ par variante (full set).
    """
    if budget_cap_usd > 5.0:
        budget_cap_usd = 5.0  # hard ceiling

    product = await db.products.find_one({"id": product_id}, {"_id": 0})
    if not product:
        raise HTTPException(404, "Produit introuvable")

    # Resolve variant_id → color_slug
    color_slug = (variant_id or "").strip().lower()
    if not color_slug:
        raise HTTPException(400, "variant_id requis (slug couleur ou ID variant)")
    # If variant_id looks like a UUID (variant ID), resolve to slug
    if "-" in color_slug and len(color_slug) >= 30:
        for v in product.get("variants") or []:
            if v.get("id") == variant_id:
                props = v.get("properties") or []
                if props and props[0]:
                    color_slug = slugify_color(str(props[0]).strip())
                    break

    budget = BudgetCap(cap_usd=budget_cap_usd)
    try:
        result = await generate_full_variant_set(
            db, product_id, color_slug,
            overwrite=overwrite,
            budget=budget,
            request_id=f"admin-regen-{product_id[:8]}-{color_slug}",
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        msg = str(e)
        if "402" in msg or "budget" in msg.lower():
            raise HTTPException(429, "Budget Nano Banana épuisé.")
        logger.exception(f"[regenerate-variant-images] {product_id}/{color_slug}")
        raise HTTPException(502, f"Generation failed : {msg[:200]}")

    return result


# In-memory task tracker for the async batch endpoint.
# Acceptable for MVP : single-worker uvicorn. For multi-worker, persist to Mongo.
_BATCH_TASKS: dict = {}


@router.post(
    "/admin/sites/{site_id}/regenerate-all-variant-images",
    tags=["product-variant-images"],
    summary="Lance en arrière-plan la regénération 8-styles pour TOUTES les variantes d'un site — admin only",
)
async def regenerate_all_variant_images_for_site(
    site_id: str,
    overwrite: bool = Query(False),
    budget_cap_usd: float = Query(DEFAULT_BUDGET_CAP_USD),
    user: dict = Depends(require_admin),
):
    """Lance un batch async de regénération sur tous les couples
    (produit, couleur) d'un site. Retourne immédiatement un `task_id` ;
    suivre le statut via `GET /api/admin/tasks/{task_id}`.

    Hard cap : 5 USD par site (modifiable jusqu'à 5$ max).
    """
    site = await db.sites.find_one({"id": site_id}, {"_id": 0, "id": 1, "name": 1})
    if not site:
        raise HTTPException(404, "Site introuvable")
    if budget_cap_usd > 5.0:
        budget_cap_usd = 5.0

    task_id = f"vimg-{uuid.uuid4().hex[:12]}"
    started_at = datetime.now(timezone.utc).isoformat()
    _BATCH_TASKS[task_id] = {
        "task_id": task_id,
        "kind": "regenerate-all-variant-images",
        "site_id": site_id,
        "site_name": site.get("name"),
        "overwrite": overwrite,
        "budget_cap_usd": budget_cap_usd,
        "status": "running",
        "started_at": started_at,
        "started_by": user.get("email"),
        "result": None,
    }

    async def _run():
        try:
            result = await generate_all_variant_sets_for_site(
                db, site_id,
                overwrite=overwrite,
                budget_cap_usd=budget_cap_usd,
            )
            _BATCH_TASKS[task_id]["status"] = "done"
            _BATCH_TASKS[task_id]["result"] = result
            _BATCH_TASKS[task_id]["finished_at"] = datetime.now(timezone.utc).isoformat()
            logger.info(
                f"[batch-variant-pipeline] task {task_id} done — "
                f"spent ${result['budget']['spent_usd']:.2f}"
            )
        except Exception as e:
            _BATCH_TASKS[task_id]["status"] = "failed"
            _BATCH_TASKS[task_id]["error"] = str(e)[:300]
            _BATCH_TASKS[task_id]["finished_at"] = datetime.now(timezone.utc).isoformat()
            logger.exception(f"[batch-variant-pipeline] task {task_id} failed")

    asyncio.create_task(_run())

    return {
        "ok": True,
        "task_id": task_id,
        "status": "running",
        "started_at": started_at,
        "poll_url": f"/api/admin/tasks/{task_id}",
        "site_id": site_id,
        "overwrite": overwrite,
        "budget_cap_usd": budget_cap_usd,
    }


@router.get(
    "/admin/tasks/{task_id}",
    tags=["product-variant-images"],
    summary="Statut d'une tâche async (variant images batch)",
)
async def admin_get_task_status(task_id: str, user: dict = Depends(require_admin)):
    task = _BATCH_TASKS.get(task_id)
    if not task:
        raise HTTPException(404, "Tâche inconnue ou expirée")
    return task
