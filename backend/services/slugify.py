"""
Slugify helper — déterministe et indépendant des LLM.

Compatible avec le `slugify` JS côté frontend (`/app/frontend/src/lib/slugify.js`)
et avec `slugify_color` côté Python (services/color_variant_images.py).

Cas d'usage :
  - URL produit (PDP storefront)
  - URL article blog
  - Identifiant variante couleur

Règles :
  - lowercase ASCII
  - voyelles accentuées → équivalent ASCII (é→e, ç→c, etc.)
  - tout caractère non `[a-z0-9]` → tiret unique
  - trims des tirets en bordure
  - max 80 caractères, coupé sur le dernier tiret pour ne pas couper un mot
  - fallback "produit-<6 chars hex>" si la chaîne est vide après nettoyage
"""
from __future__ import annotations

import re
import unicodedata
import uuid

_RX_NON_ALNUM = re.compile(r"[^a-z0-9]+")
_RX_MULTIDASH = re.compile(r"-{2,}")


def slugify(text: str, *, max_len: int = 80, fallback_prefix: str = "produit") -> str:
    """Slugify ASCII-safe pour URL.

    >>> slugify("Fauteuil Releveur Électrique avec Massage & Relaxation")
    'fauteuil-releveur-electrique-avec-massage-relaxation'
    >>> slugify("")
    'produit-...' (8 hex chars)
    """
    if not text or not str(text).strip():
        return f"{fallback_prefix}-{uuid.uuid4().hex[:8]}"

    s = str(text).strip().lower()
    # Normalise les accents (NFD décompose, on droppe les diacritiques)
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    # Remplace tout non-alnum par un tiret
    s = _RX_NON_ALNUM.sub("-", s)
    s = _RX_MULTIDASH.sub("-", s).strip("-")

    if not s:
        return f"{fallback_prefix}-{uuid.uuid4().hex[:8]}"

    if len(s) > max_len:
        # Coupe au dernier tiret avant max_len pour ne pas tronquer un mot
        cut = s[:max_len]
        last_dash = cut.rfind("-")
        s = cut[:last_dash] if last_dash > max_len // 2 else cut
        s = s.strip("-")

    return s or f"{fallback_prefix}-{uuid.uuid4().hex[:8]}"


def _pick_text(name) -> str:
    """Tolère un nom multilingue (`{"fr": "...", "en": "..."}`) ou string."""
    if isinstance(name, dict):
        return name.get("fr") or name.get("en") or next(iter(name.values()), "")
    return str(name or "")
