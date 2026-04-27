"""
Lot I (Phase 2.1) — AI generation for premium product content.

Provides 2 atomic generators using Claude Haiku 4.5 (cheap, fast):
- `generate_product_tagline(product, brand)` → string 40-80 chars
- `generate_product_usps(product, brand)` → list of 4 dicts {icon, title, description}

Both generators are designed to be called either by:
- The `launch.py` pipeline (auto-generated for every new product on a "from-scratch" site)
- The admin back-fill endpoints `POST /api/admin/products/{id}/regenerate-{tagline|usps}`

Output schemas (stored on `products` collection):
    products.tagline = "Le sommeil retrouvé, sans compromis"   # str (FR primary, multi-lang dict supported)
    products.usps    = [
        {"icon": "Wind",      "title": "2 moteurs silencieux",     "description": "Mécanisme à <30dB pour..."},
        ...
    ]

Lucide icon names whitelist — only these are validated against (frontend ICON_MAP).
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

from services.llm_resilience import safe_claude_text, LLMUnavailableError

logger = logging.getLogger("conceptfactory.product_content_ai")

# ---------------------------------------------------------------------------
# Lucide icon whitelist (must match frontend ICON_MAP exactly).
# Names follow lucide-react PascalCase convention.
# ---------------------------------------------------------------------------
ALLOWED_USP_ICONS = [
    "Wind",          # silent / airflow / motors
    "Heart",         # comfort / care / bien-être
    "Shield",        # safety / robustness
    "Cpu",           # smart / electronics / control
    "Zap",           # power / energy / fast
    "Battery",       # autonomy
    "Feather",       # softness / lightweight
    "Sparkles",      # premium finish / detail
    "Leaf",          # eco / natural materials
    "Award",         # quality / certification
    "Layers",        # multi-zone / layered comfort
    "Gauge",         # adjustable / precision
    "Settings2",     # customization
    "Ruler",         # dimensions / extensible
    "Move",          # mobility / motion
    "Compass",       # ergonomic positioning
    "ThermometerSun",  # temperature regulation / heating
    "Volume2",       # acoustic / silent
    "Lightbulb",     # illuminated / smart features
    "Hand",          # hand-crafted / manual
    "Anchor",        # stability / anchoring
    "MousePointer2", # remote / control
    "Headphones",    # support / audio
    "Stethoscope",   # medical-grade / health
    "Target",        # precision / focused benefit
    "Star",          # premium quality / rating
    "Crown",         # luxury / premium positioning
    "Gem",           # high-end material / finish
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
_JSON_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def _strip_json_fence(text: str) -> str:
    return _JSON_FENCE_RE.sub("", (text or "").strip()).strip()


def _pick_primary_lang_text(value, primary_lang: str = "fr") -> str:
    """Extract a clean string from a value that may be a dict {fr,en,...} or a string."""
    if not value:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return str(value.get(primary_lang) or value.get("fr") or value.get("en") or
                   next(iter(value.values()), ""))
    return str(value)


def _product_context(product: Dict[str, Any], brand: Dict[str, Any]) -> str:
    """Builds a rich context string for the LLM, in French."""
    name = _pick_primary_lang_text(product.get("name"))
    desc = _pick_primary_lang_text(product.get("description"))[:600]
    cat = product.get("category") or product.get("collection") or ""
    price = product.get("price") or 0
    currency = product.get("currency") or "EUR"

    # narrative.tech_specs / narrative.headline if available — gives more substance
    narrative = product.get("narrative") or {}
    headline = _pick_primary_lang_text(narrative.get("headline"))
    subheadline = _pick_primary_lang_text(narrative.get("subheadline"))
    tech_specs = narrative.get("tech_specs") or []
    specs_str = ""
    if isinstance(tech_specs, list) and tech_specs:
        bullets = []
        for s in tech_specs[:8]:
            if isinstance(s, dict):
                k = _pick_primary_lang_text(s.get("label") or s.get("key") or "")
                v = _pick_primary_lang_text(s.get("value") or "")
                if k and v:
                    bullets.append(f"  - {k}: {v}")
        specs_str = "\n".join(bullets)

    brand_voice = brand.get("voice") or "premium"
    brand_name = _pick_primary_lang_text(brand.get("name") or brand.get("logo_text"))

    lines = [
        f"MARQUE : {brand_name} (ton de voix : {brand_voice})",
        f"PRODUIT : {name}",
    ]
    if cat:
        lines.append(f"CATÉGORIE : {cat}")
    if price:
        lines.append(f"PRIX : {price} {currency}")
    if headline:
        lines.append(f"ACCROCHE NARRATIVE : {headline}")
    if subheadline:
        lines.append(f"SOUS-TITRE : {subheadline}")
    if desc:
        lines.append(f"DESCRIPTION : {desc}")
    if specs_str:
        lines.append("CARACTÉRISTIQUES TECHNIQUES :\n" + specs_str)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 1) Tagline (40-80 chars, French primary)
# ---------------------------------------------------------------------------
async def generate_product_tagline(
    product: Dict[str, Any],
    brand: Dict[str, Any],
    *,
    request_id: Optional[str] = None,
) -> str:
    """Generate a product-level tagline, 40-80 chars, premium tone (Aesop-style).

    Returns a clean French string ready to display. Caller stores it as
    `products.tagline` (string) — multi-lang support can be layered later by
    pickLang side.
    """
    brand_voice = brand.get("voice") or "premium"
    context = _product_context(product, brand)

    system = (
        "Tu es directeur de création pour une marque e-commerce premium "
        "(références : Aesop, Hermès, Le Labo). Tu écris en français, "
        "avec un ton sobre, sensuel, jamais agressif. Pas de superlatifs, "
        "pas d'exclamation, pas de marketing-speak."
    )
    user = (
        f"{context}\n\n"
        f"TÂCHE : écris UNE SEULE tagline pour ce produit, en français, "
        f"entre 40 et 80 caractères (espaces inclus).\n\n"
        f"CONTRAINTES :\n"
        f"- Évite : « Le meilleur », « N°1 », « Incroyable », « Profitez de »\n"
        f"- Privilégie : émotion, rituel, présence, qualité tangible\n"
        f"- Ton : aligné avec la voix de marque '{brand_voice}'\n"
        f"- Format : juste la tagline, AUCUN guillemet, AUCUN préambule, AUCUN markdown\n"
        f"- Ne mentionne PAS le nom du produit (la tagline s'affiche sous le titre)\n"
    )

    try:
        raw = await safe_claude_text(
            system=system,
            user=user,
            quality_tier="standard",  # Haiku 4.5
            timeout=30.0,
            request_id=request_id,
        )
    except LLMUnavailableError:
        raise

    # Sanitize : strip markdown, quotes, preambles, take first line only
    text = (raw or "").strip()
    # Try to extract bold first
    bold = re.search(r"\*\*([^*\n]{20,140})\*\*", text)
    if bold:
        text = bold.group(1).strip()
    else:
        # First non-empty line
        for line in text.split("\n"):
            line = line.strip()
            if line and not line.startswith(("#", ">", "```", "//", "Tagline", "tagline")):
                text = line
                break
    text = re.sub(r'^["\'«»“”‘’]+|["\'«»“”‘’]+$', "", text).strip()
    text = re.sub(r"^\s*(tagline|baseline)\s*:\s*", "", text, flags=re.IGNORECASE).strip()
    text = re.sub(r"[*_`]+", "", text).strip()
    # Hard cap at 90 chars (we asked 40-80 ; defensive)
    if len(text) > 90:
        text = text[:90].rsplit(" ", 1)[0].rstrip(",.;:")
    return text


# ---------------------------------------------------------------------------
# 2) USPs — 4 product-specific items with Lucide icon name
# ---------------------------------------------------------------------------
async def generate_product_usps(
    product: Dict[str, Any],
    brand: Dict[str, Any],
    *,
    request_id: Optional[str] = None,
) -> List[Dict[str, str]]:
    """Generate 4 product-specific USPs as a list of dicts.

    Each dict has shape:
        {"icon": "<LucideIconName>", "title": "<title ≤30 chars>",
         "description": "<description ≤140 chars>"}

    Returns exactly 4 items (raises on failure). Icons are validated against
    `ALLOWED_USP_ICONS`; unknown names default to "Sparkles" to never break
    the frontend.
    """
    context = _product_context(product, brand)
    icon_list = ", ".join(ALLOWED_USP_ICONS)

    system = (
        "Tu es directeur de création pour une marque e-commerce premium. "
        "Tu écris en français. Tu produis des bénéfices CONCRETS, "
        "tangibles, spécifiques au produit (pas génériques). "
        "Tu réponds STRICTEMENT en JSON valide, sans markdown."
    )
    user = (
        f"{context}\n\n"
        f"TÂCHE : produis 4 USPs (Unique Selling Points) PRODUIT-SPÉCIFIQUES.\n\n"
        f"INTERDITS (génériques inutiles, ne jamais inclure) :\n"
        f"- Livraison rapide / livraison offerte\n"
        f"- Garantie 2 ans / SAV\n"
        f"- Retour gratuit\n"
        f"- Service client / support 7j/7\n"
        f"- Paiement sécurisé\n\n"
        f"CHAQUE USP DOIT :\n"
        f"- décrire un BÉNÉFICE TANGIBLE lié à la mécanique, au matériau, à la techno, à l'ergonomie\n"
        f"- Exemple BON : « Mécanisme à 2 moteurs silencieux » | « Mémoire de forme haute densité » | "
        f"« Repose-pieds extensible 12 cm » | « Télécommande rétroéclairée »\n"
        f"- Exemple MAUVAIS : « Confort optimal » | « Très qualitatif »\n\n"
        f"FORMAT JSON (réponds UNIQUEMENT ceci, pas de markdown, pas de texte autour) :\n"
        f'{{\n'
        f'  "usps": [\n'
        f'    {{"icon": "<icon_name>", "title": "<≤30 chars>", "description": "<≤140 chars, bénéfice concret>"}},\n'
        f'    ... (exactement 4 items)\n'
        f'  ]\n'
        f'}}\n\n'
        f"icon_name DOIT être l'un de : {icon_list}\n"
        f"Choisis l'icône la plus pertinente pour chaque USP."
    )

    raw = await safe_claude_text(
        system=system,
        user=user,
        quality_tier="standard",
        timeout=45.0,
        request_id=request_id,
    )

    cleaned = _strip_json_fence(raw or "")
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        # Try to find the first {...} block
        m = re.search(r"\{[\s\S]+\}", cleaned)
        if not m:
            logger.warning(f"[usps] JSON parse failed, raw={raw[:200]!r}")
            raise ValueError("Réponse Claude USPs non parsable en JSON")
        data = json.loads(m.group(0))

    items = data.get("usps") or data.get("items") or []
    if not isinstance(items, list) or len(items) < 1:
        raise ValueError("Réponse Claude USPs invalide (liste vide)")

    cleaned_items: List[Dict[str, str]] = []
    for it in items[:4]:
        if not isinstance(it, dict):
            continue
        icon = str(it.get("icon") or "").strip()
        title = str(it.get("title") or "").strip()
        desc = str(it.get("description") or it.get("desc") or "").strip()
        if not title:
            continue
        # Validate icon
        if icon not in ALLOWED_USP_ICONS:
            # Try case-insensitive match
            ci = next((i for i in ALLOWED_USP_ICONS if i.lower() == icon.lower()), None)
            icon = ci or "Sparkles"
        # Hard caps
        if len(title) > 36:
            title = title[:33] + "…"
        if len(desc) > 160:
            desc = desc[:157] + "…"
        cleaned_items.append({"icon": icon, "title": title, "description": desc})

    if len(cleaned_items) < 4:
        # Pad with generic-but-not-empty items keyed off product name to never break UI
        # Caller can detect the partial result via len() < 4
        logger.warning(
            f"[usps] only {len(cleaned_items)} valid items returned by Claude — caller should retry"
        )

    return cleaned_items
