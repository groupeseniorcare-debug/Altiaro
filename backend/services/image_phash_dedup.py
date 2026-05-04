"""Sprint 2.2 — Déduplication d'images par pHash (perceptual hash).

Usage :
    from services.image_phash_dedup import register_image, find_duplicate

    # Après avoir généré une image PIL / des bytes PNG :
    dup_hash = await find_duplicate(site_id, png_bytes, threshold=5)
    if dup_hash:
        # regénérer avec un seed différent
        ...
    else:
        await register_image(site_id, png_bytes, context={"kind":"hero","product_id":...})

Collection MongoDB : `site_images`
    { id, site_id, phash, kind, ref_id, url, created_at }

On utilise `imagehash.phash` (Hamming distance) :
    - 0-2 = identique (doublon pur)
    - 3-5 = quasi-identique (variation compression)
    - 6-10 = très similaire (à réinitialiser)
    - >10 = différente

Sprint 2.2 également : `style_seed` par marque — chaque site a
`design.brand.style_seed` (entier stable) qui nourrit Nano Banana pour
homogénéiser le rendu inter-fiches.
"""
from __future__ import annotations

import io
import logging
import random
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from deps import db

logger = logging.getLogger("altiaro.image_phash")

try:
    import imagehash
    from PIL import Image
    _AVAILABLE = True
except Exception as e:  # pragma: no cover
    logger.warning(f"imagehash/PIL unavailable: {e}")
    _AVAILABLE = False


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def compute_phash(image_bytes: bytes) -> Optional[str]:
    """Return the perceptual hash (64-bit hex) of an image. Returns None on failure."""
    if not _AVAILABLE or not image_bytes:
        return None
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        return str(imagehash.phash(img))
    except Exception as e:
        logger.warning(f"compute_phash failed: {e}")
        return None


def hamming_distance(a: str, b: str) -> int:
    """Hamming distance between two 64-bit hex phashes."""
    if not a or not b or len(a) != len(b):
        return 64
    try:
        return bin(int(a, 16) ^ int(b, 16)).count("1")
    except Exception:
        return 64


async def find_duplicate(site_id: str, image_bytes: bytes, *,
                         threshold: int = 5) -> Optional[Dict[str, Any]]:
    """Check if an image with phash distance <= threshold already exists for
    this site. Returns the matching doc or None."""
    if not _AVAILABLE:
        return None
    phash = compute_phash(image_bytes)
    if not phash:
        return None
    # Lightweight scan of last 500 images for this site (enough at industrial scale
    # for 14 posts × 2 images = 28 entries; 10 sites = 280; keep fast)
    cursor = db.site_images.find({"site_id": site_id}, {"_id": 0, "phash": 1,
                                                         "id": 1, "kind": 1,
                                                         "ref_id": 1, "url": 1})
    async for doc in cursor:
        d = hamming_distance(phash, doc.get("phash") or "")
        if d <= threshold:
            doc["distance"] = d
            return doc
    return None


async def register_image(site_id: str, image_bytes: bytes, *,
                         kind: str, ref_id: Optional[str] = None,
                         url: Optional[str] = None,
                         extra: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """Persist the image's phash in `site_images`. Returns the phash or None."""
    phash = compute_phash(image_bytes)
    if not phash:
        return None
    doc = {
        "id": str(uuid.uuid4()),
        "site_id": site_id,
        "phash": phash,
        "kind": kind,            # 'hero' | 'inline' | 'product_studio' | ...
        "ref_id": ref_id,         # e.g. blog_post.id or product.id
        "url": url,
        "created_at": _now_iso(),
    }
    if extra:
        doc.update(extra)
    try:
        await db.site_images.insert_one(doc)
    except Exception as e:
        logger.warning(f"register_image insert failed: {e}")
        return None
    return phash


async def get_or_create_style_seed(site_id: str) -> int:
    """Ensures each site has a stable `design.brand.style_seed` used to keep
    image generation consistent. Returns the seed."""
    site = await db.sites.find_one({"id": site_id},
                                    {"_id": 0, "design": 1}) or {}
    seed = ((site.get("design") or {}).get("brand") or {}).get("style_seed")
    if isinstance(seed, int) and seed > 0:
        return seed
    new_seed = random.randint(100000, 9999999)
    await db.sites.update_one(
        {"id": site_id},
        {"$set": {"design.brand.style_seed": new_seed}},
    )
    return new_seed


async def style_seed_suffix(site_id: str) -> str:
    """Returns a prompt suffix string to append to Nano Banana prompts that
    softly constrains the style (camera, lighting, palette) based on a
    deterministic per-site seed — gives visual coherence across images.
    """
    seed = await get_or_create_style_seed(site_id)
    # Pick deterministic presets from the seed
    cameras = ["35mm prime lens, f/2.8", "50mm prime, f/4", "24mm wide, f/5.6"]
    lights = ["soft morning window light", "diffused overcast daylight",
              "warm late afternoon golden light"]
    moods = ["serene and editorial", "minimal and premium",
             "warm and intimate"]
    cam = cameras[seed % len(cameras)]
    lit = lights[(seed // 7) % len(lights)]
    mood = moods[(seed // 13) % len(moods)]
    return (f" Style directive (seed {seed}): {cam}; {lit}; {mood}; "
            "muted neutral color palette; no text overlays; no watermarks.")
