"""Lot A1 — Favicon multi-tailles par site.

Lit le logo PNG du site (`design.brand.logo_url`) et génère 5 tailles
standards dans `/uploads/favicons/{site_id}/` :

   16×16   .png  →  classic browser tab
   32×32   .png  →  retina browser tab + bookmark bar
   180×180 .png  →  apple-touch-icon (iOS home screen)
   192×192 .png  →  Android home screen / PWA
   512×512 .png  →  PWA splash + Web App Manifest

Stratégie :
- Resize avec antialiasing (Pillow LANCZOS).
- Si le logo est carré, redimensionne directement.
- Si rectangulaire, paste sur fond transparent carré centré (préserve
  les marges visuelles du design).
- Lot G Fix 2 — si le logo source n'a pas d'alpha (Nano Banana ne respecte
  pas toujours `transparent background` malgré le prompt), `remove_white_background()`
  détecte les pixels quasi-blancs et les passe en alpha=0 avant resize.
- Aucun appel LLM. Coût : 0 €.

Persiste l'URL principale (32×32) dans `site.design.favicon_url` et
le set complet dans `site.design.favicons` (objet par taille).
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Optional

from PIL import Image

from deps import db, UPLOAD_DIR

logger = logging.getLogger("altiaro.favicon_generator")

FAVICON_SIZES: Dict[str, int] = {
    "favicon-16": 16,
    "favicon-32": 32,
    "apple-touch-icon": 180,
    "android-192": 192,
    "android-512": 512,
}

# Lot G Fix 2 — Seuil de luminance au-dessus duquel un pixel est considéré
# "quasi-blanc" et donc éligible au remove background. 245 = très permissif
# (efface tout ce qui est blanc cassé), conserve les zones grises et noires
# du wordmark intact. R+G+B > 735 ≈ chaque canal > 245.
WHITE_BG_THRESHOLD_SUM = 735


def remove_white_background(img: Image.Image, threshold_sum: int = WHITE_BG_THRESHOLD_SUM) -> Image.Image:
    """Convertit les pixels quasi-blancs d'un PNG en pixels transparents.

    Utile en fallback quand Nano Banana / autre générateur d'image ne respecte
    pas la consigne `transparent background` malgré le prompt. Conserve l'anti-
    aliasing en faisant un fade alpha proportionnel à la luminosité (les bords
    flous des lettres ne pixelisent pas en escaliers).

    Args:
        img: PIL Image (RGB ou RGBA acceptés)
        threshold_sum: somme R+G+B au-dessus de laquelle alpha=0 (default 735)

    Returns:
        PIL Image en mode RGBA avec fond transparent.
    """
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    pixels = img.load()
    w, h = img.size
    # Boucle pixel-par-pixel : pour 2k×512px ≈ 1M pixels = ~150 ms, acceptable.
    for y in range(h):
        for x in range(w):
            r, g, b, a = pixels[x, y]
            s = r + g + b
            if s >= threshold_sum:
                # Pixel blanc → totalement transparent
                pixels[x, y] = (r, g, b, 0)
            elif s >= threshold_sum - 90:
                # Bord anti-aliasé entre 645 et 735 → fade alpha proportionnel
                # pour un edge propre (évite les escaliers visibles)
                fade = int(((threshold_sum - s) / 90) * 255)
                pixels[x, y] = (r, g, b, min(a, fade))
    return img


def ensure_alpha_channel(src_path: Path) -> Image.Image:
    """Charge une image et garantit qu'elle a un canal alpha utilisable.

    Si l'image source est RGB (sans transparence), applique automatiquement
    `remove_white_background()` pour obtenir un alpha cohérent. Si déjà RGBA
    avec alpha non-nul partout (= image opaque encadrée), applique aussi le
    remove pour que les coins blancs deviennent transparents.

    Args:
        src_path: chemin du PNG source.

    Returns:
        PIL Image en mode RGBA prête à être resize / pastée.
    """
    img = Image.open(src_path)
    img.load()
    needs_remove = False
    if img.mode != "RGBA":
        needs_remove = True
    else:
        # Détection : si tous les pixels coins sont opaques + blancs, l'image
        # a un fond blanc opaque malgré le mode RGBA → on force le remove.
        w, h = img.size
        corners = [img.getpixel((0, 0)), img.getpixel((w - 1, 0)),
                   img.getpixel((0, h - 1)), img.getpixel((w - 1, h - 1))]
        whites = sum(1 for c in corners if c[3] >= 250 and (c[0] + c[1] + c[2]) >= WHITE_BG_THRESHOLD_SUM)
        if whites >= 3:
            needs_remove = True

    if needs_remove:
        logger.info(f"[favicon] {src_path.name} : applying remove_white_background fallback")
        img = remove_white_background(img)
    return img


def _load_logo_bytes_from_url(logo_url: str) -> Optional[Path]:
    """Convertit une URL `/api/uploads/...` en Path absolue sur disque.
    Retourne None si introuvable ou hors du dossier uploads (sécurité)."""
    if not logo_url:
        return None
    # Strip prefix /api/uploads/
    rel = logo_url.split("/api/uploads/", 1)
    if len(rel) != 2:
        return None
    candidate = (UPLOAD_DIR / rel[1]).resolve()
    # Sécurité : empêcher path traversal
    if not str(candidate).startswith(str(UPLOAD_DIR.resolve())):
        return None
    return candidate if candidate.exists() else None


def _square_with_padding(img: Image.Image) -> Image.Image:
    """Si l'image n'est pas carrée, la centre dans un canevas carré transparent."""
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    w, h = img.size
    if w == h:
        return img
    side = max(w, h)
    canvas = Image.new("RGBA", (side, side), (255, 255, 255, 0))
    offset = ((side - w) // 2, (side - h) // 2)
    canvas.paste(img, offset, img)
    return canvas


def generate_favicons_from_logo(site_id: str, logo_url: str) -> Dict[str, str]:
    """Génère les 5 favicons et les écrit sur disque.

    Args:
        site_id: UUID du site.
        logo_url: URL relative du logo (ex: `/api/uploads/logos/logo_xxx.png`).

    Returns:
        Dict mapping taille → URL relative servable, ou {} si échec.
    """
    src_path = _load_logo_bytes_from_url(logo_url)
    if not src_path:
        logger.warning(f"[favicon] logo introuvable pour site {site_id[:8]} : {logo_url}")
        return {}

    out_dir = UPLOAD_DIR / "favicons" / site_id
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Lot G Fix 2 — garantit alpha channel propre (remove_white_background
        # si le logo source est RGB ou a un fond blanc opaque)
        cleaned = ensure_alpha_channel(src_path)
        squared = _square_with_padding(cleaned)
        urls: Dict[str, str] = {}
        for slug, size in FAVICON_SIZES.items():
            resized = squared.resize((size, size), Image.LANCZOS)
            # PWA icons gagnent à être en RGBA, le manifeste gère bien
            fname = f"{slug}.png"
            fpath = out_dir / fname
            resized.save(fpath, format="PNG", optimize=True)
            urls[slug] = f"/api/uploads/favicons/{site_id}/{fname}"
            logger.debug(f"[favicon] {site_id[:8]} {fname} ({size}x{size}, {fpath.stat().st_size}B)")
        logger.info(f"[favicon] generated {len(urls)} sizes for site {site_id[:8]}")
        return urls
    except Exception as e:
        logger.exception(f"[favicon] generation failed for site {site_id[:8]}: {e}")
        return {}


async def regenerate_and_persist_favicons(site_id: str) -> Dict[str, str]:
    """Lit le logo en DB, regénère tous les favicons, et persiste les URLs.

    Idempotent : peut être appelé plusieurs fois sans effet de bord (écrase
    les fichiers existants). Utilisé par :
    - le pipeline `launch.py` après génération du logo (auto)
    - une route admin de regen on-demand (manuelle)
    """
    site = await db.sites.find_one(
        {"id": site_id},
        {"_id": 0, "design.brand.logo_url": 1, "design.brand.name": 1},
    )
    if not site:
        return {}
    brand = ((site.get("design") or {}).get("brand") or {})
    logo_url = brand.get("logo_url")
    if not logo_url:
        logger.warning(f"[favicon] site {site_id[:8]} sans logo_url, skip")
        return {}

    urls = generate_favicons_from_logo(site_id, logo_url)
    if not urls:
        return {}

    primary_url = urls.get("favicon-32") or next(iter(urls.values()))
    apple_url = urls.get("apple-touch-icon")
    await db.sites.update_one(
        {"id": site_id},
        {"$set": {
            "design.favicon_url": primary_url,
            "design.favicon_apple_url": apple_url,
            "design.favicons": urls,
        }},
    )
    logger.info(f"[favicon] site {site_id[:8]} : favicon_url = {primary_url}")
    return urls
