"""Lot H — Color name detection (Python mirror of frontend `lib/colorMapping.js`).

Used by the pipeline `launch.py::_generate_color_variant_images_for_product`
to detect whether a variant axis is a "color" axis (vs. size, model, ...)
and therefore eligible for img-to-img color regeneration.

Keeps in sync with the frontend dictionary so a new site has consistent
behavior on both sides.
"""
from __future__ import annotations

import unicodedata

# Mirror frontend dictionary (FR + EN). Values are not used here, only keys
# for membership tests. Keep alphabetized.
KNOWN_COLOR_NAMES: set[str] = {
    # Black/White/Grey
    "noir", "black", "jet",
    "blanc", "white", "ivoire", "ivory", "creme", "cream", "ecru",
    "gris", "grey", "gray", "gris clair", "gris fonce",
    "light grey", "light gray", "dark grey", "dark gray",
    "charcoal", "anthracite",
    # Beige/Sand
    "beige", "sable", "sand", "taupe", "camel",
    # Brown/Chocolate
    "marron", "brown", "chocolat", "chocolate",
    "cafe", "coffee", "cognac", "caramel",
    "noisette", "hazelnut",
    # Blue
    "bleu", "blue", "bleu marine", "marine", "navy",
    "bleu nuit", "bleu ciel", "sky blue", "bleu canard",
    "teal", "turquoise", "cyan",
    # Red/Burgundy
    "rouge", "red", "bordeaux", "burgundy",
    "cerise", "carmin",
    # Green
    "vert", "green", "kaki", "khaki",
    "olive", "emeraude", "emerald",
    "menthe", "mint", "forest", "vert sapin",
    # Pink
    "rose", "pink", "rose pale", "rose poudre", "fuchsia",
    # Purple
    "violet", "purple", "mauve", "lilas", "lilac",
    "prune", "plum",
    # Yellow/Gold
    "jaune", "yellow", "or", "gold",
    "moutarde", "mustard",
    # Orange
    "orange", "terracotta", "terre cuite", "rouille", "rust",
    "abricot", "apricot", "saumon", "salmon",
    # Metals
    "argent", "silver", "bronze", "cuivre", "copper",
    "platine", "platinum",
    # Multi
    "multicolore", "multicolor", "multi", "rainbow",
    "imprime", "imprimé", "pattern", "motif",
}


def _normalize_color_name(name: str) -> str:
    """Lowercase + strip accents + trim. Keeps inner spaces intact."""
    if not name:
        return ""
    s = str(name).strip().lower()
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    return s


def is_color_value(name: str) -> bool:
    """True if `name` is recognized as a color in the dictionary."""
    return _normalize_color_name(name) in KNOWN_COLOR_NAMES


def is_color_axis(values: list[str]) -> bool:
    """True if ≥50 % of the distinct values look like color names.

    Mirroir of the JS `isColorAxis()` heuristic.
    """
    if not values:
        return False
    distinct = list({_normalize_color_name(v) for v in values if v})
    if not distinct:
        return False
    matched = sum(1 for v in distinct if v in KNOWN_COLOR_NAMES)
    return (matched / len(distinct)) >= 0.5


__all__ = ["is_color_value", "is_color_axis", "KNOWN_COLOR_NAMES"]
