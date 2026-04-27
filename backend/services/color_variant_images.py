"""Lot H — Color variant image generation via Nano Banana img-to-img.

Génère un set d'images IA cohérentes pour CHAQUE couleur d'un produit
à partir des images de la couleur "default" (référence visuelle stable).

Le prompt strict force Nano Banana à :
  - Conserver EXACTEMENT la même mise en scène
  - Conserver EXACTEMENT le même angle, lumière, fond, accessoires
  - Changer UNIQUEMENT la couleur du produit (de X vers Y)

Idempotent : les images existantes pour une couleur sont préservées si
`overwrite=False`. Compatible avec budget hard cap (par appel d'orchestration).

Storage layout :
  /uploads/products_ai/{product_id}/variants/{color_slug}/{style}.png

DB schema (sur `products[]`) :
  generated_images_by_variant: {
    "black": [{style, url, color, color_label, generated_at, source_style, tweak}, ...],
    "white": [...],
    "brown": [...]
  }
  generated_images_legacy_textonly: [...] (backup d'origine, déjà existant)

Coût indicatif (Nano Banana ≈ 0.05$/image) :
  6 produits × 3 couleurs × 3 styles = 54 appels = ~$2.50-$2.70
"""
from __future__ import annotations

import asyncio
import base64
import logging
import re
import unicodedata
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import aiohttp

from deps import UPLOAD_DIR

logger = logging.getLogger("altiaro.color_variant_images")


# Le prompt strict — préserve TOUT sauf la couleur. Plus défensif que IDENTITY_HEADER
# du module product_images (ici on REMPLACE la couleur, pas qu'on la conserve).
COLOR_VARIATION_PROMPT_TEMPLATE = (
    "EXACTLY the same product photo as the reference image. "
    "SAME composition, SAME lighting setup, SAME camera angle, SAME background, "
    "SAME furniture and decoration, SAME camera lens, SAME focal length, SAME depth of field. "
    "The ONLY thing that changes is the {product_kind} upholstery color: "
    "change it from {original_color} to {target_color}. "
    "Keep all other elements absolutely identical including textures, materials, "
    "accessories, control panel, side pockets, footrest mechanism, headrest, stitching, "
    "seams, buttons, switches, and proportions of the {product_kind}. "
    "Do not redesign, restyle, or modify the product shape or features. "
    "Photorealistic 4K editorial product photography, no text, no watermark, no brand."
)


def slugify_color(name: str) -> str:
    """Convert a color name to a filesystem-safe slug.

    Examples :
      "Black"        → "black"
      "Bleu Marine"  → "bleu-marine"
      "Beige Crème"  → "beige-creme"
    """
    if not name:
        return "unknown"
    s = str(name).strip().lower()
    # Strip accents
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    # Replace anything non-alphanumeric with -
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"^-+|-+$", "", s)
    return s or "unknown"


async def _fetch_image_b64(url: str) -> Optional[str]:
    """Fetch an image (local /api/uploads/... or remote URL) and return base64 raw.

    Local URLs like `/api/uploads/products_ai/xxx.png` are read from disk.
    Remote HTTPS URLs are downloaded.
    """
    if not url:
        return None
    try:
        if url.startswith("/api/uploads/"):
            rel = url.split("/api/uploads/", 1)[1]
            path = UPLOAD_DIR / rel
            if not path.exists():
                logger.warning(f"[color-variant] local file not found: {path}")
                return None
            return base64.b64encode(path.read_bytes()).decode("ascii")
        elif url.startswith("http://") or url.startswith("https://"):
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=20)) as r:
                    if r.status != 200:
                        logger.warning(f"[color-variant] remote fetch {url} → HTTP {r.status}")
                        return None
                    return base64.b64encode(await r.read()).decode("ascii")
        else:
            logger.warning(f"[color-variant] unknown URL scheme: {url}")
            return None
    except Exception as e:
        logger.warning(f"[color-variant] fetch {url} failed: {e}")
        return None


async def generate_color_variant_image(
    product_id: str,
    color_slug: str,
    color_label: str,
    target_color_label: str,  # English label for the prompt (e.g., "white", "brown")
    original_color_label: str,
    style: str,
    reference_image_b64: str,
    product_kind: str = "chair",  # "chair", "blanket", "pillow", "device", ...
) -> Optional[str]:
    """Calls Nano Banana with the strict color-variation prompt + reference image.

    Returns the public URL (`/api/uploads/products_ai/{pid}/variants/{slug}/{style}.png`)
    or None on failure.

    Saves the generated PNG to disk under the variant folder.
    """
    from services.llm_resilience import safe_nano_banana_bytes, LLMUnavailableError
    prompt = COLOR_VARIATION_PROMPT_TEMPLATE.format(
        product_kind=product_kind,
        original_color=original_color_label,
        target_color=target_color_label,
    )
    try:
        data = await safe_nano_banana_bytes(
            prompt,
            system="You generate premium product photography for a Silver Economy D2C brand. You preserve product identity strictly.",
            session_id=f"colvar-{product_id}-{uuid.uuid4().hex[:6]}",
            timeout=120,
            request_id=f"colvar-{product_id[:8]}-{color_slug}-{style}",
            reference_image_b64=reference_image_b64,
        )
        if not data:
            return None

        # Storage : /uploads/products_ai/{product_id}/variants/{slug}/{style}.png
        out_dir = UPLOAD_DIR / "products_ai" / product_id / "variants" / color_slug
        out_dir.mkdir(parents=True, exist_ok=True)
        # Suffix random to avoid CDN cache when regenerating
        filename = f"{style}_{uuid.uuid4().hex[:8]}.png"
        out_path = out_dir / filename
        out_path.write_bytes(data)
        return f"/api/uploads/products_ai/{product_id}/variants/{color_slug}/{filename}"
    except LLMUnavailableError as e:
        logger.warning(f"[color-variant] LLM down for {product_id}/{color_slug}/{style}: {e.last_error}")
        return None
    except Exception as e:
        msg = str(e)
        if "Budget has been exceeded" in msg or "budget" in msg.lower():
            logger.error("[color-variant] BUDGET EXHAUSTED — abort")
            raise  # propagate to halt the loop
        logger.exception(f"[color-variant] failed for {product_id}/{color_slug}/{style}")
        return None


def detect_product_kind(name_dict_or_str) -> str:
    """Very simple heuristic to insert the correct noun in the prompt
    (chair / blanket / pillow / cushion / device / ...).

    Reads the product name (FR or EN) and returns the most likely kind.
    Defaults to "product" if nothing matches.
    """
    if isinstance(name_dict_or_str, dict):
        text = " ".join(str(v) for v in name_dict_or_str.values())
    else:
        text = str(name_dict_or_str or "")
    text = text.lower()
    mapping = [
        (("fauteuil", "chair", "recliner", "armchair"), "chair"),
        (("canapé", "sofa", "couch"), "sofa"),
        (("coussin", "cushion", "pillow"), "cushion"),
        (("plaid", "blanket", "throw", "couverture"), "blanket"),
        (("housse", "cover"), "cover"),
        (("matelas", "mattress"), "mattress"),
        (("oreiller",), "pillow"),
        (("table",), "table"),
        (("lampe", "lamp"), "lamp"),
        (("tapis", "rug"), "rug"),
    ]
    for keywords, kind in mapping:
        if any(k in text for k in keywords):
            return kind
    return "product"


def color_label_to_english(label: str) -> str:
    """Translate a French color label to English for the prompt.

    The prompt is in English (Nano Banana is more reliable in English).
    Most AE source labels are already in English ("Black", "White") — keep as-is.
    """
    if not label:
        return "neutral"
    fr_to_en = {
        "noir": "black", "blanc": "white", "gris": "grey", "gris clair": "light grey",
        "gris fonce": "dark grey", "gris foncé": "dark grey",
        "marron": "brown", "beige": "beige", "bleu": "blue", "bleu marine": "navy blue",
        "rouge": "red", "vert": "green", "rose": "pink", "violet": "purple",
        "jaune": "yellow", "or": "gold", "argent": "silver", "orange": "orange",
        "ivoire": "ivory", "creme": "cream", "crème": "cream", "taupe": "taupe",
        "chocolat": "chocolate", "cafe": "coffee", "café": "coffee",
        "kaki": "khaki", "olive": "olive", "bordeaux": "burgundy",
    }
    norm = unicodedata.normalize("NFD", label.strip().lower())
    norm = "".join(c for c in norm if unicodedata.category(c) != "Mn")
    return fr_to_en.get(norm, label.strip().lower())


__all__ = [
    "COLOR_VARIATION_PROMPT_TEMPLATE",
    "slugify_color",
    "generate_color_variant_image",
    "detect_product_kind",
    "color_label_to_english",
]
