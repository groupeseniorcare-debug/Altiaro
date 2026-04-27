"""Phase 2.3 — STYLE_PROFILES adaptatifs par catégorie produit.

La pipeline 8-styles d'origine (Lot I) ciblait des fauteuils (`seated_furniture`).
Le pilote V3 a démontré que pour des produits "soft goods" (housse, couverture,
coussin), certains styles comme `in_use` (personne assise) ou `side_profile`
(profil 90°) n'ont pas de sens.

Ce module définit des profils alternatifs par famille de produit, sélectionnés
automatiquement à partir du `source_vision_lock.product_kind` détecté par Vision.

Chaque profil produit toujours **8 styles** (cohérence galerie + budget). Les
profils partagent un sous-ensemble commun (studio_main, studio_card, detail)
et différent sur les mises en scène spécifiques.

Public API :
    classify_product_kind(product_kind: str) -> str    # "seated_furniture" | "blanket" | ...
    get_style_profile(profile_key: str) -> List[Dict]
    list_profile_keys() -> List[str]
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional

logger = logging.getLogger("altiaro.style_profiles")


# -------------------------------------------------------------------------
# Style definitions — building blocks shared across profiles.
# Each style has slug, aspect, label_en, scene (template with {product_kind}
# {material} {color} {color_label_en} {silhouette_signature} {unique_features_visible}).
# -------------------------------------------------------------------------
_S_STUDIO_MAIN = {
    "slug": "studio_main", "aspect": "4:5", "label_en": "main studio shot",
    "scene": (
        "Pure ivory studio background (#F5F2EB warm off-white seamless paper). "
        "Three-quarter front view of the {product_kind}, shot at eye level, "
        "soft diffused lighting from the upper left, no harsh shadows. "
        "The full {product_kind} is visible, centered, with subtle ground shadow. "
        "Vertical 4:5 framing with generous negative space above and below. "
        "Editorial catalog hero quality."
    ),
}
_S_STUDIO_CARD = {
    "slug": "studio_card", "aspect": "1:1", "label_en": "square card shot",
    "scene": (
        "Same ivory #F5F2EB seamless studio background as the main shot. "
        "Tighter framing — the {product_kind} occupies 70% of a square 1:1 frame, "
        "perfectly centered. Same lighting and angle. Suitable as a product grid card."
    ),
}
_S_DETAIL = {
    "slug": "detail", "aspect": "1:1", "label_en": "technical detail",
    "scene": (
        "Macro detail shot of ONE specific feature of THIS {product_kind} "
        "(visible in reference: {unique_features_visible}). "
        "Plain neutral light grey #E7E5E4 background, soft directional studio lighting. "
        "1:1 square framing, the detail is the hero of the shot. NO PEOPLE, no text, no labels."
    ),
}

# --- seated_furniture only ---
_S_LIFESTYLE_HAUSS = {
    "slug": "lifestyle", "aspect": "4:5", "label_en": "lifestyle scene",
    "scene": (
        "Premium Parisian Haussmannian apartment interior: oak parquet floor with "
        "herringbone pattern, tall window with sheer linen curtains diffusing soft "
        "afternoon daylight, white wall mouldings in the background. "
        "The {product_kind} sits naturally in the room, slight side angle. "
        "NO PEOPLE in this shot. Subtle props: art books, a reading lamp, a cashmere throw. "
        "Vertical 4:5 framing. High-end interior magazine editorial quality."
    ),
}
_S_WIDE_LIFESTYLE = {
    "slug": "wide_lifestyle", "aspect": "16:9", "label_en": "wide cinematic lifestyle",
    "scene": (
        "PANORAMIC 16:9 horizontal cinematic view of the same Haussmannian living room: "
        "wide-angle perspective, oak parquet, tall window with linen curtains, mouldings, "
        "soft natural daylight. The {product_kind} is positioned on the LEFT THIRD of "
        "the frame, the room extending to the right with elegant decor. NO PEOPLE. "
        "Cinematic 35mm equivalent focal length, golden hour light."
    ),
}
_S_CLOSEUP_MATERIAL = {
    "slug": "closeup", "aspect": "1:1", "label_en": "macro material closeup",
    "scene": (
        "Extreme macro close-up on the EXACT upholstery surface of THIS {product_kind}. "
        "Show the texture of the {material} in {color}: weave, stitching, grain, every "
        "fiber detail visible. Shallow depth of field, soft side window light, warm tone. "
        "1:1 framing — only the rich textured surface fills the frame. NO PEOPLE."
    ),
}
_S_IN_USE = {
    "slug": "in_use", "aspect": "4:5", "label_en": "in-use lifestyle (person seated)",
    "scene": (
        "Realistic in-use scene with a PERSON FULLY SEATED IN the {product_kind}. "
        "CRITICAL: back against backrest, bottom on seat, legs naturally placed. The person "
        "is INSIDE/ON the chair, NOT standing next to it. Anonymous: face partially out of "
        "frame or in soft shadow. 50-70 yo, casual elegant attire, relaxed posture. "
        "Warm cozy interior, soft golden light, an open book or cup of tea. Vertical 4:5 "
        "framing, natural authentic moment. Editorial lifestyle photography."
    ),
}
_S_SIDE_PROFILE = {
    "slug": "side_profile", "aspect": "4:5", "label_en": "side profile shot",
    "scene": (
        "Pure 90-degree side profile of the {product_kind}, shot at exactly 90° from the side. "
        "Plain neutral light grey #E7E5E4 studio background, single soft side light revealing "
        "every silhouette line. Vertical 4:5 framing — the {product_kind} fills 80% of the frame. "
        "All profile lines visible. Architectural product photography. NO PEOPLE."
    ),
}

# --- soft_goods / blanket / cushion ---
_S_FOLDED_DISPLAY = {
    "slug": "folded_display", "aspect": "4:5", "label_en": "folded display",
    "scene": (
        "The {product_kind} folded neatly and displayed on a pale ivory linen surface "
        "(#F5F2EB), single fold or rolled, showing the {material} texture and {color}. "
        "Soft natural daylight from above-right, gentle shadows. Vertical 4:5 framing. "
        "Premium textile editorial photography. NO PEOPLE."
    ),
}
_S_ON_SOFA = {
    "slug": "on_sofa", "aspect": "4:5", "label_en": "draped on sofa",
    "scene": (
        "The {product_kind} casually draped over the armrest of an off-white linen sofa "
        "in a calm Scandinavian living room. The {material} folds naturally, showing texture "
        "and {color}. Soft afternoon daylight from a tall window in the background, oak "
        "parquet floor visible. NO PEOPLE. Vertical 4:5, lifestyle interior magazine quality."
    ),
}
_S_ON_BED = {
    "slug": "on_bed", "aspect": "4:5", "label_en": "draped on bed",
    "scene": (
        "The {product_kind} folded at the foot of a beautifully made bed with crisp white "
        "linen sheets and a beige cashmere throw. The {material} in {color} contrasts gently "
        "with the white linen. Warm bedside lamp, soft morning light from a window. "
        "Vertical 4:5 framing. NO PEOPLE. Premium bedroom editorial photography."
    ),
}
_S_TEXTURE_CLOSEUP = {
    "slug": "texture_closeup", "aspect": "1:1", "label_en": "macro fabric texture",
    "scene": (
        "Extreme macro close-up of the {material} weave/pile of the {product_kind}, "
        "in {color}. Show every fiber, every stitch, every pile direction. Shallow depth "
        "of field, soft natural side light, warm tone. 1:1 framing — only the textured "
        "surface fills the frame. Editorial textile photography. NO PEOPLE."
    ),
}
_S_CONTEXT_ROOM = {
    "slug": "context_room", "aspect": "16:9", "label_en": "wide context room",
    "scene": (
        "Wide 16:9 cinematic view of a calm Scandinavian living-room or bedroom in soft "
        "morning light. The {product_kind} is integrated naturally (folded on a chair, "
        "draped on a sofa, or laid on a bed). NO PEOPLE. Oak floor, linen curtains, simple "
        "ceramic accents. The {product_kind} is a subtle but visible focal point. "
        "Editorial interior magazine quality."
    ),
}
_S_ON_CHAIR = {
    "slug": "on_chair", "aspect": "4:5", "label_en": "displayed on chair",
    "scene": (
        "The {product_kind} placed on a simple Scandinavian wooden chair (oak frame, beige "
        "linen seat) in a calm interior. The {material} in {color} is the focal point. "
        "Soft window light from the side, gentle ground shadow. Vertical 4:5 framing. "
        "NO PEOPLE. Premium textile editorial photography."
    ),
}
_S_STACKED = {
    "slug": "stacked", "aspect": "1:1", "label_en": "stacked composition",
    "scene": (
        "A stack of 2-3 {product_kind} pieces (or the same one folded in 2-3 layers), "
        "arranged with care on a pale ivory or oak surface. Show the {material} and {color} "
        "from multiple angles in one shot. Soft natural daylight. 1:1 framing. NO PEOPLE. "
        "Editorial product still life."
    ),
}
_S_ALT_ANGLE = {
    "slug": "alt_angle", "aspect": "4:5", "label_en": "alternate angle",
    "scene": (
        "Alternate camera angle on the {product_kind} : top-down or 3/4 back view, "
        "ivory studio background, same lighting as studio_main. Vertical 4:5 framing. "
        "NO PEOPLE. Reveals an angle not seen in studio_main."
    ),
}
_S_GENERIC_CONTEXT = {
    "slug": "context", "aspect": "4:5", "label_en": "lifestyle context",
    "scene": (
        "The {product_kind} placed naturally in a calm premium interior (Scandinavian or "
        "Haussmannian), soft daylight, no clutter. NO PEOPLE. Vertical 4:5 framing. "
        "Editorial lifestyle quality."
    ),
}


# -------------------------------------------------------------------------
# 5 profiles × 8 styles
# -------------------------------------------------------------------------
STYLE_PROFILES: Dict[str, List[Dict[str, str]]] = {
    "seated_furniture": [
        _S_STUDIO_MAIN, _S_STUDIO_CARD, _S_LIFESTYLE_HAUSS, _S_WIDE_LIFESTYLE,
        _S_CLOSEUP_MATERIAL, _S_DETAIL, _S_IN_USE, _S_SIDE_PROFILE,
    ],
    "soft_goods": [
        _S_STUDIO_MAIN, _S_STUDIO_CARD, _S_FOLDED_DISPLAY, _S_ON_SOFA,
        _S_ON_BED, _S_TEXTURE_CLOSEUP, _S_CONTEXT_ROOM, _S_DETAIL,
    ],
    "blanket": [
        _S_STUDIO_MAIN, _S_STUDIO_CARD, _S_FOLDED_DISPLAY, _S_ON_SOFA,
        _S_ON_BED, _S_TEXTURE_CLOSEUP, _S_CONTEXT_ROOM, _S_DETAIL,
    ],
    "cushion": [
        _S_STUDIO_MAIN, _S_STUDIO_CARD, _S_ON_CHAIR, _S_ON_SOFA,
        _S_LIFESTYLE_HAUSS, _S_TEXTURE_CLOSEUP, _S_DETAIL, _S_STACKED,
    ],
    "generic": [
        _S_STUDIO_MAIN, _S_STUDIO_CARD, _S_LIFESTYLE_HAUSS, _S_WIDE_LIFESTYLE,
        _S_CLOSEUP_MATERIAL, _S_DETAIL, _S_GENERIC_CONTEXT, _S_ALT_ANGLE,
    ],
}


# -------------------------------------------------------------------------
# Classifier — maps Vision-detected `product_kind` to a profile key
# -------------------------------------------------------------------------
_KEYWORDS_TO_PROFILE: List = [
    # (substring matches → profile_key) — first match wins, lowercased compare
    (("recliner", "armchair", "lift chair", "lounge chair", "fauteuil", "sofa chair"), "seated_furniture"),
    (("blanket", "throw", "couverture chauffante", "electric blanket", "couette"), "blanket"),
    (("cushion", "pillow", "lumbar", "coussin", "oreiller"), "cushion"),
    (("cover", "slipcover", "housse", "duvet cover", "drap"), "soft_goods"),
    # Sofas + bed-frames considered "seated_furniture" by default
    (("sofa", "couch", "canape", "canapé", "loveseat"), "seated_furniture"),
]


def classify_product_kind(product_kind: Optional[str]) -> str:
    """Maps a Vision-detected product_kind string to one of STYLE_PROFILES keys.
    Falls back to "generic" if no match."""
    if not product_kind:
        return "generic"
    pk = product_kind.lower()
    for keywords, profile in _KEYWORDS_TO_PROFILE:
        for kw in keywords:
            if kw in pk:
                logger.info(f"[style-profiles] '{product_kind}' → {profile} (kw='{kw}')")
                return profile
    logger.info(f"[style-profiles] '{product_kind}' → generic (no kw match)")
    return "generic"


def get_style_profile(profile_key: str) -> List[Dict[str, str]]:
    """Returns the list of 8 style dicts for a given profile."""
    return list(STYLE_PROFILES.get(profile_key) or STYLE_PROFILES["generic"])


def list_profile_keys() -> List[str]:
    return list(STYLE_PROFILES.keys())


__all__ = [
    "STYLE_PROFILES",
    "classify_product_kind",
    "get_style_profile",
    "list_profile_keys",
]
