"""
Phase 2.6 Tâche D — services.brand_story
========================================

Génère le contenu de la section "Notre maison / L'atelier" (composant
frontend `<BrandStory>`) qui remplace l'ancienne `<FounderStory>` (qui
parlait d'une personne fictive type "Camille Lefèvre").

Deux fonctions :

1. `generate_brand_story_text(brand, niche)` :
       Haiku 4.5 → retourne un dict multilang FR + EN minimum :
           {
             "eyebrow":    {"fr": "...", "en": "..."},
             "headline":   {"fr": "...", "en": "..."},
             "paragraph":  {"fr": "...", "en": "..."},
             "cta_label":  {"fr": "...", "en": "..."},
             "cta_href":   "/about"
           }
       Ton Aesop / Hermès, pas d'emoji, pas de personne fictive.
       Ancré sur le nom de la marque + tagline + niche + géo France.

2. `generate_brand_workshop_image_bytes(brand)` :
       Nano Banana (gemini-3.1-flash-image-preview) → retourne `bytes`.
       Composition : entrepôt premium / atelier moderne, packaging soigné,
       équipe stylisée et anonyme en arrière-plan, lumière naturelle,
       ambiance scandinave épurée. Le logo de la marque (s'il est en URL
       absolue) est passé en `reference_image_b64` pour cohérence chromatique.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, Optional

from services.llm_resilience import (
    safe_claude_text,
    safe_nano_banana_bytes,
    LLMUnavailableError,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
_JSON_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def _strip_json_fence(s: str) -> str:
    return _JSON_FENCE.sub("", (s or "").strip())


def _safe_get(d: Optional[Dict[str, Any]], path: str, default=None):
    cur = d or {}
    for part in path.split("."):
        if not isinstance(cur, dict):
            return default
        cur = cur.get(part)
        if cur is None:
            return default
    return cur


# ---------------------------------------------------------------------------
# 1) Texte BrandStory — Haiku 4.5
# ---------------------------------------------------------------------------
async def generate_brand_story_text(
    brand: Dict[str, Any],
    *,
    niche: str = "",
    request_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Génère le contenu textuel de la section "Notre maison" (multilang)."""
    brand_name = (brand or {}).get("name") or "Notre maison"
    tagline = (brand or {}).get("tagline") or ""
    voice = (brand or {}).get("voice") or "premium"
    niche_label = (niche or _safe_get(brand, "niche") or "").strip()

    system = (
        "Tu es directeur éditorial d'une maison française premium "
        "(références Aesop, Hermès Petit h, Le Labo). Tu écris en français "
        "et en anglais. Tu produis du JSON valide.\n\n"
        "RÈGLES ABSOLUES :\n"
        "- JAMAIS de personne fictive (pas de prénom inventé, pas de portrait "
        "  signé). On parle de la MAISON / MARQUE comme entité.\n"
        "- Ton sobre, sensoriel, narratif. Pas d'emoji, pas d'impératif sec.\n"
        "- Mentionner la France : sélection rigoureuse, centre logistique en "
        "  France métropolitaine, expédition rapide, garantie 2 ans, retours 14 j.\n"
        "- Pas de superlatif vide ('le meilleur', 'révolutionnaire')."
    )
    user = (
        f"MARQUE : {brand_name}\n"
        f"TAGLINE : {tagline}\n"
        f"VOIX : {voice}\n"
        f"CATÉGORIE : {niche_label}\n\n"
        "TÂCHE : produis le contenu de la section 'Notre maison' du site "
        "(remplace une ancienne 'À propos du fondateur' avec personne fictive). "
        "Format JSON STRICT, FR + EN obligatoires :\n"
        "{\n"
        '  "eyebrow": {"fr": "Notre maison" | "L\\u2019atelier" | "Les coulisses", "en": "..."},\n'
        '  "headline": {"fr": "<1 phrase évocatrice ≤ 80 chars>", "en": "..."},\n'
        '  "paragraph": {"fr": "<2 à 3 phrases ton Aesop, ≤ 350 chars>", "en": "..."},\n'
        '  "cta_label": {"fr": "Découvrir notre maison" | "Découvrir notre histoire", "en": "..."},\n'
        '  "cta_href": "/about"\n'
        "}\n\n"
        "Réponds UNIQUEMENT le JSON, sans markdown."
    )

    raw = await safe_claude_text(
        system=system, user=user,
        quality_tier="standard", timeout=35.0,
        request_id=request_id or "brand-story",
    )
    cleaned = _strip_json_fence(raw or "")
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]+\}", cleaned)
        if not m:
            raise ValueError("BrandStory JSON non parsable")
        data = json.loads(m.group(0))

    # Sanity defaults
    data.setdefault("cta_href", "/about")
    for k in ("eyebrow", "headline", "paragraph", "cta_label"):
        v = data.get(k)
        if isinstance(v, str):
            data[k] = {"fr": v, "en": v}
        elif isinstance(v, dict):
            data[k] = {"fr": v.get("fr") or v.get("en") or "",
                       "en": v.get("en") or v.get("fr") or ""}
        else:
            data[k] = {"fr": "", "en": ""}
    return data


# ---------------------------------------------------------------------------
# 2) Image atelier — Nano Banana
# ---------------------------------------------------------------------------
async def generate_brand_workshop_image_bytes(
    brand: Dict[str, Any],
    *,
    niche: str = "",
    logo_b64: Optional[str] = None,
    request_id: Optional[str] = None,
) -> Optional[bytes]:
    """Génère le visuel "coulisses / atelier" de la marque.

    Nano Banana (gemini-3.1-flash-image-preview), format vertical 4:5
    (mieux pour la grille StorefrontHome). Pas de texte sur l'image —
    le copy vient à côté en HTML.

    Si `logo_b64` est fourni, il est passé en référence image-to-image
    pour cohérence chromatique (sans plaquer le logo).
    """
    brand_name = (brand or {}).get("name") or "Maison"  # noqa: F841 - kept for future log/template use
    palette = (brand or {}).get("palette") or {}
    primary = palette.get("primary") or "#4A5D52"
    accent = palette.get("accent") or "#E8E2D5"
    niche_label = (niche or _safe_get(brand, "niche") or "produits premium").strip()

    prompt = (
        "Editorial photograph of a premium French e-commerce warehouse / "
        "workshop. Wide cinematic view of carefully arranged rows of "
        f"unbranded {niche_label} packages, in soft cardboard and white kraft "
        "wrapping. Stylised, anonymous figures in earthy linen aprons in the "
        "soft-focus background; their faces are NEVER visible (back, profile "
        "or out-of-focus only). Natural daylight from large windows, dust "
        "particles in the air, Scandinavian minimalism. "
        f"Color palette aligned with the brand : primary {primary}, "
        f"accent {accent}, neutral ivory. "
        "NO text overlay. NO logos. NO watermarks. NO faces in focus. "
        "4:5 vertical aspect ratio, magazine-quality, soft analog grain, "
        "Aesop / Hermès editorial mood. Photorealistic, 35mm lens, f/2.8, "
        "shallow depth of field on foreground packages."
    )

    try:
        return await safe_nano_banana_bytes(
            prompt=prompt,
            system="You are a premium editorial photographer for a high-end "
                   "European lifestyle brand.",
            timeout=120.0,
            request_id=request_id or "brand-workshop-image",
            reference_image_b64=logo_b64,
        )
    except LLMUnavailableError as e:
        logger.warning(f"[brand_story] Nano Banana unavailable: {e}")
        return None


__all__ = [
    "generate_brand_story_text",
    "generate_brand_workshop_image_bytes",
]
