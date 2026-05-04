"""Wordmark typographique — génération instantanée sans LLM.

Pillow + Fraunces serif → PNG 1200×400 avec le brand_name centré.
Usage :

    from services.wordmark_generator import generate_wordmark
    png_bytes = generate_wordmark("Altea", {"primary_color": "#D4C5B0", "accent_color": "#8B7E6A"})

Le service upstream (`persist_wordmark_for_site`) se charge d'écrire le fichier
dans `/uploads/logos/wordmark_{site_id}_{hash}.png` et d'updater le doc site.
"""
from __future__ import annotations

import hashlib
import io
import logging
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger("altiaro.wordmark")

FONTS_DIR = Path(__file__).parent.parent / "assets" / "fonts"
FRAUNCES_SEMIBOLD = FONTS_DIR / "Fraunces-SemiBold.ttf"
FRAUNCES_REGULAR = FONTS_DIR / "Fraunces-Regular.ttf"
# Fallback OS-level fonts (preinstalled on the debian slim container)
FALLBACK_SERIF = "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf"

DEFAULT_BG = "#F5F2EB"       # ivoire Luxury Minimal
DEFAULT_INK = "#1C1917"      # noir chaud
CANVAS_W, CANVAS_H = 1200, 400


def _hex_to_rgb(hex_color: str) -> tuple:
    h = (hex_color or "").lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) != 6:
        return (245, 242, 235)
    try:
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return (245, 242, 235)


def _relative_luminance(rgb: tuple) -> float:
    def _c(x):
        x = x / 255.0
        return x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4
    r, g, b = rgb
    return 0.2126 * _c(r) + 0.7152 * _c(g) + 0.0722 * _c(b)


def _best_ink(bg_rgb: tuple, accent_hex: Optional[str]) -> tuple:
    """Pick ink color : the accent if it has enough contrast, else black/white."""
    bg_lum = _relative_luminance(bg_rgb)
    if accent_hex:
        a = _hex_to_rgb(accent_hex)
        a_lum = _relative_luminance(a)
        contrast = (max(bg_lum, a_lum) + 0.05) / (min(bg_lum, a_lum) + 0.05)
        if contrast >= 4.5:
            return a
    # fallback — use black on light bg, white on dark bg
    return (28, 25, 23) if bg_lum > 0.5 else (250, 247, 242)


def _pick_font(size: int) -> ImageFont.FreeTypeFont:
    for p in (FRAUNCES_SEMIBOLD, FRAUNCES_REGULAR):
        if p.exists():
            try:
                return ImageFont.truetype(str(p), size)
            except (OSError, IOError):
                continue
    return ImageFont.truetype(FALLBACK_SERIF, size)


def _fit_font_size(text: str, max_width: int, max_height: int,
                   start_size: int = 220, min_size: int = 60) -> ImageFont.FreeTypeFont:
    """Dichotomie rapide : plus grande taille qui rentre dans la boîte."""
    size = start_size
    while size > min_size:
        f = _pick_font(size)
        bbox = f.getbbox(text)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        if w <= max_width and h <= max_height:
            return f
        size -= 10
    return _pick_font(min_size)


def generate_wordmark(brand_name: str, palette: Optional[Dict[str, str]] = None,
                      *, with_rule: bool = True) -> bytes:
    """Produit le PNG bytes d'un wordmark typographique.

    Args:
        brand_name  : texte affiché (max ~18 chars pour un rendu propre).
        palette     : dict {primary_color, accent_color, background_color}.
        with_rule   : ajoute 2 fins traits décoratifs au-dessus et en-dessous.
    """
    palette = palette or {}
    bg_hex = palette.get("background_color") or DEFAULT_BG
    accent_hex = palette.get("accent_color") or palette.get("primary_color") or DEFAULT_INK

    bg_rgb = _hex_to_rgb(bg_hex)
    ink_rgb = _best_ink(bg_rgb, accent_hex)

    # Clean brand name
    name = re.sub(r"\s+", " ", (brand_name or "Maison").strip())[:24] or "Maison"

    img = Image.new("RGB", (CANVAS_W, CANVAS_H), bg_rgb)
    draw = ImageDraw.Draw(img)

    # Fit font inside 88 % of the canvas width
    max_w, max_h = int(CANVAS_W * 0.80), int(CANVAS_H * 0.55)
    font = _fit_font_size(name, max_w, max_h)

    bbox = font.getbbox(name)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    # Pillow's bbox starts at the font ascent; offset x by -bbox[0], y by -bbox[1]
    x = (CANVAS_W - text_w) // 2 - bbox[0]
    y = (CANVAS_H - text_h) // 2 - bbox[1]

    draw.text((x, y), name, fill=ink_rgb, font=font)

    if with_rule:
        rule_w = int(CANVAS_W * 0.16)
        mid_x = CANVAS_W // 2
        # thin rule above & below the wordmark, centered
        y_top = (CANVAS_H - text_h) // 2 - 46
        y_bot = y_top + text_h + 92
        draw.line([(mid_x - rule_w // 2, y_top), (mid_x + rule_w // 2, y_top)],
                   fill=ink_rgb, width=2)
        draw.line([(mid_x - rule_w // 2, y_bot), (mid_x + rule_w // 2, y_bot)],
                   fill=ink_rgb, width=2)

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


async def persist_wordmark_for_site(site_id: str, brand_name: str,
                                     palette: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """Generate + save + update DB. Returns dict with `wordmark_url`."""
    from deps import db, UPLOAD_DIR
    png = generate_wordmark(brand_name, palette)
    digest = hashlib.sha256(png).hexdigest()[:10]
    # Write under UPLOAD_DIR / logos
    logos_dir = Path(UPLOAD_DIR) / "logos"
    logos_dir.mkdir(parents=True, exist_ok=True)
    filename = f"wordmark_{site_id}_{digest}.png"
    (logos_dir / filename).write_bytes(png)
    url = f"/api/uploads/logos/{filename}"
    now = datetime.now(timezone.utc).isoformat()
    await db.sites.update_one(
        {"id": site_id},
        {"$set": {
            "design.brand.logo_wordmark_url": url,
            "design.brand.logo_wordmark_generated_at": now,
            "updated_at": now,
        }},
    )
    logger.info(f"[wordmark] persisted {url} for site {site_id[:8]}")
    return {"wordmark_url": url, "size_bytes": len(png), "digest": digest,
            "brand_name": brand_name}
