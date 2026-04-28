"""
Phase 2.6 Tâche E — services.review_photos
==========================================

Génère un pool de 4-6 photos lifestyle "client" pour un produit. Chaque
photo simule une scène domestique réaliste avec le produit visible
naturellement dans le décor (style smartphone snap, pas pro studio).

Usage :
    from services.review_photos import generate_client_lifestyle_photo
    bytes_ = await generate_client_lifestyle_photo(product, brand, scene_idx=0)
    # → écrire dans UPLOAD_DIR / sites/{site_id}/reviews/...

Cap budget LLM : si Nano Banana retourne 402 / "budget exceeded",
chaque appel renvoie None et log WARN — l'appelant fait skip + degraded.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from services.llm_resilience import safe_nano_banana_bytes, LLMUnavailableError

logger = logging.getLogger(__name__)


# 6 scènes domestiques différentes, ton smartphone snap (pas pro studio)
LIFESTYLE_SCENES: List[str] = [
    # Salon le matin
    "Authentic smartphone snapshot of a French living room in the morning. "
    "{product_kind} placed naturally near a window with morning light. "
    "Light wear marks suggesting daily use. Coffee mug on a nearby side table. "
    "Slight phone-cam imperfection, slight motion blur. NO people in the frame. "
    "Vertical 4:3 ratio, natural daylight, IKEA-meets-bourgeois interior.",
    # Salon en soirée
    "Authentic smartphone snapshot of a cozy French living room at dusk. "
    "{product_kind} as the focal point, warm lamp light, a folded throw on the side. "
    "Evening atmosphere, soft warm light, a book half-opened nearby. "
    "Slight phone-cam grain. NO people. Horizontal 4:3 ratio.",
    # Chambre senior
    "Authentic smartphone photograph of a French senior bedroom interior. "
    "{product_kind} positioned for everyday use. Floral curtains in soft "
    "pastel tones, framed family photos blurred in the background, hardwood "
    "floor with a small woven rug. NO people in the frame. 4:3 ratio.",
    # Détail proche du produit
    "Close-up smartphone photograph of {product_kind} in a French residential "
    "interior. Texture and material clearly visible. Soft daylight, hint of "
    "everyday clutter at the edge of the frame. Authentic, not staged. NO people. "
    "4:3 ratio.",
    # Salon avec plante
    "Smartphone snapshot of {product_kind} in a Parisian apartment living room "
    "with a tall green plant nearby and parquet floor. Light dust catching the "
    "afternoon sunbeam. Authentic everyday scene, NO people. 4:3 ratio.",
    # Vue large avec produit en contexte
    "Wide smartphone photograph of a French residential living room, "
    "{product_kind} part of the everyday scene with a coffee table, a magazine, "
    "and a knitted throw. Natural daylight. NO people. 16:9 horizontal ratio.",
]


def _detect_product_label(product: Dict[str, Any]) -> str:
    """Heuristique courte pour insérer le bon nom dans le prompt."""
    svl = product.get("source_vision_lock") or {}
    pk = (svl.get("product_kind") or "").strip().lower()
    mapping = {
        "seated_furniture": "an electric rise & recline armchair",
        "chair": "an electric rise & recline armchair",
        "armchair": "an electric rise & recline armchair",
        "recliner": "a recliner armchair",
        "fauteuil": "an electric rise & recline armchair",
        "blanket": "a folded warm blanket",
        "throw": "a folded throw blanket",
        "heated_blanket": "a folded heated blanket",
        "couverture": "a folded warm blanket",
        "cushion": "a lumbar support cushion",
        "pillow": "a lumbar support cushion",
        "lumbar_cushion": "a lumbar support cushion",
        "soft_goods": "a fitted slipcover on a sofa",
        "sofa_cover": "a fitted slipcover on a sofa",
        "slipcover": "a fitted slipcover on a chair",
        "housse": "a fitted slipcover on a chair",
    }
    if pk in mapping:
        return mapping[pk]
    # Fallback : nom produit en EN si dispo
    name = product.get("name") or {}
    if isinstance(name, dict):
        name = name.get("en") or name.get("fr") or ""
    return (str(name) or "the product").lower()[:80]


async def generate_client_lifestyle_photo(
    product: Dict[str, Any],
    brand: Dict[str, Any],
    *,
    scene_idx: int = 0,
    timeout: float = 120.0,
    request_id: Optional[str] = None,
) -> Optional[bytes]:
    """Génère une photo lifestyle "client" — scène domestique avec
    le produit visible naturellement.

    Returns bytes (PNG/JPEG) or None if Nano Banana failed (e.g. budget cap).
    """
    scene_idx = scene_idx % len(LIFESTYLE_SCENES)
    product_kind = _detect_product_label(product)
    palette = (brand or {}).get("palette") or {}
    primary = palette.get("primary") or "#4A5D52"

    prompt = LIFESTYLE_SCENES[scene_idx].format(product_kind=product_kind) + (
        f"\nColor accents that should match the product palette: {primary}. "
        "Photorealistic, slight smartphone-camera grain, NOT a studio shot. "
        "NO text overlay, NO logos, NO watermarks, NO faces."
    )
    try:
        return await safe_nano_banana_bytes(
            prompt=prompt,
            system="You are a French resident snapping an authentic photograph "
                   "of their home with their phone, not a professional photographer.",
            timeout=timeout,
            request_id=request_id or f"review-photo-{scene_idx}",
        )
    except LLMUnavailableError as e:
        logger.warning(f"[review_photos] Nano Banana unavailable: {e}")
        return None


async def generate_review_photos_for_product(
    product: Dict[str, Any],
    brand: Dict[str, Any],
    *,
    n: int = 4,
    request_id_prefix: str = "review-photos",
) -> List[bytes]:
    """Helper qui génère N photos en série. Renvoie la liste des bytes
    (peut être plus courte que N si certaines générations ont échoué).
    """
    n = max(2, min(int(n or 4), 6))
    out: List[bytes] = []
    for i in range(n):
        b = await generate_client_lifestyle_photo(
            product, brand,
            scene_idx=i,
            request_id=f"{request_id_prefix}-{i}",
        )
        if b:
            out.append(b)
    return out


__all__ = [
    "generate_client_lifestyle_photo",
    "generate_review_photos_for_product",
    "LIFESTYLE_SCENES",
]
