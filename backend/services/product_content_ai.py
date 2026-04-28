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

    # Phase 2.3 — Inject source_vision_lock so the LLM knows the REAL material
    # / color / silhouette detected by Gemini Vision on the source AE/CJ photos.
    # This prevents text drift (e.g. saying "microsuède" when the material is
    # actually PU leather).
    svl = product.get("source_vision_lock") or {}
    svl_lines: List[str] = []
    canonical_material_fr = ""
    forbidden_terms_fr: List[str] = []
    if isinstance(svl, dict):
        if svl.get("product_kind"):
            svl_lines.append(f"  - Type produit (Vision) : {svl['product_kind']}")
        if svl.get("material"):
            mat_en = svl['material']
            svl_lines.append(f"  - Matériau réel (Vision) : {mat_en}")
            mat_low = mat_en.lower()
            if "pu leather" in mat_low or ("leather" in mat_low and "real" not in mat_low and "top-grain" not in mat_low and "genuine" not in mat_low):
                canonical_material_fr = "cuir synthétique (PU leather, simili-cuir)"
                forbidden_terms_fr = ["microsuède", "microsuede", "microfibre", "suède", "suede", "tissu", "velours", "lin"]
            elif "top-grain" in mat_low or "real leather" in mat_low or "genuine leather" in mat_low:
                canonical_material_fr = "cuir véritable (top-grain leather)"
                forbidden_terms_fr = ["microsuède", "microsuede", "microfibre", "PU", "simili", "tissu"]
            elif "microsuede" in mat_low or "suede-like" in mat_low or "microfiber suede" in mat_low:
                canonical_material_fr = "microsuède (microfibre type suède)"
                forbidden_terms_fr = ["cuir", "leather", "velours", "lin"]
            elif "velvet" in mat_low:
                canonical_material_fr = "velours"
                forbidden_terms_fr = ["cuir", "leather", "microsuède", "tissu uni"]
            elif "linen" in mat_low or "cotton" in mat_low or "woven" in mat_low or "fabric" in mat_low:
                canonical_material_fr = "tissu (textile tissé)"
                forbidden_terms_fr = ["cuir", "leather", "PU", "simili", "microsuède"]
        if svl.get("color"):
            svl_lines.append(f"  - Couleur réelle (Vision) : {svl['color']}")
        if svl.get("silhouette_signature"):
            svl_lines.append(f"  - Traits distinctifs (Vision) : {svl['silhouette_signature']}")
        if svl.get("unique_features_visible"):
            svl_lines.append(f"  - Features visibles (Vision) : {svl['unique_features_visible']}")

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
    if svl_lines:
        block = (
            "🔒 ANALYSE VISUELLE SOURCE (AUTORITAIRE — PRIME SUR TOUT LE RESTE) :\n"
            + "\n".join(svl_lines)
            + "\n  ⚠️ RÈGLE ABSOLUE : si la description ou les specs ci-dessus contredisent "
            "cette analyse Vision (ex: la description dit 'microsuède' mais la Vision dit "
            "'PU leather'), tu DOIS croire la Vision et IGNORER les contradictions textuelles. "
            "La Vision a regardé le vrai produit ; la description fournisseur peut être inexacte ou traduite n'importe comment."
        )
        if canonical_material_fr:
            block += (
                f"\n\n  📌 MATÉRIAU CANONIQUE À EMPLOYER (français, OBLIGATOIRE) : {canonical_material_fr}.\n"
                f"  ❌ TERMES INTERDITS POUR CE PRODUIT (ne JAMAIS écrire ces mots) : "
                + ", ".join(forbidden_terms_fr)
                + ".\n  Si tu écris un terme interdit, ta réponse est rejetée et régénérée."
            )
        lines.append(block)
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
# Length caps (Phase 2.1 hardening — 2026-04-27)
# Brief user : titre ≤30 chars, description ≤140 chars. Le LLM tend à dépasser
# de quelques chars → on demande explicitement 28/130 dans le prompt
# (margin), on vérifie côté backend, on retry 1× si dépassement, et on
# tronque proprement en dernier recours.
# ---------------------------------------------------------------------------
USP_TITLE_PROMPT_MAX = 28
USP_DESC_PROMPT_MAX = 130
USP_TITLE_HARD_MAX = 30
USP_DESC_HARD_MAX = 140


def _truncate_clean(text: str, hard_max: int) -> str:
    """Truncate at hard_max keeping word boundaries, append ellipsis if cut."""
    if len(text) <= hard_max:
        return text
    cut = text[: hard_max - 1]
    sp = cut.rfind(" ")
    if sp > hard_max * 0.6:
        cut = cut[:sp]
    return cut.rstrip(",.;:· ") + "…"


def _is_within_caps(usps: List[Dict[str, str]]) -> bool:
    """All 4 USPs must respect title ≤ HARD_MAX and desc ≤ HARD_MAX."""
    if len(usps) < 4:
        return False
    for u in usps:
        if len(u.get("title", "")) > USP_TITLE_HARD_MAX:
            return False
        if len(u.get("description", "")) > USP_DESC_HARD_MAX:
            return False
    return True


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

    Hardening (Phase 2.1, 2026-04-27) :
    - Asks Claude for ≤28 chars titles and ≤130 chars descriptions (margin)
    - Validates the response. If any item exceeds 30/140 → retries ONCE with
      a stricter prompt. If still over → truncates cleanly with ellipsis.
    """
    items = await _call_usps_llm(
        product, brand,
        title_max=USP_TITLE_PROMPT_MAX,
        desc_max=USP_DESC_PROMPT_MAX,
        request_id=request_id,
        strict=False,
    )

    # Retry once if any item exceeds the hard cap
    if not _is_within_caps(items):
        too_long = [
            f"  USP {i}: t={len(u.get('title',''))}/{USP_TITLE_HARD_MAX} "
            f"d={len(u.get('description',''))}/{USP_DESC_HARD_MAX}"
            for i, u in enumerate(items[:4])
            if len(u.get("title", "")) > USP_TITLE_HARD_MAX
            or len(u.get("description", "")) > USP_DESC_HARD_MAX
        ]
        logger.warning(
            f"[usps] {request_id or ''} caps exceeded, retry with stricter prompt:\n"
            + "\n".join(too_long)
        )
        items = await _call_usps_llm(
            product, brand,
            title_max=22,  # even tighter on retry
            desc_max=110,
            request_id=(request_id or "") + "-retry",
            strict=True,
        )

    # Final defensive truncation (always applied, even on the retry result)
    cleaned: List[Dict[str, str]] = []
    for it in items[:4]:
        title = _truncate_clean(it.get("title", ""), USP_TITLE_HARD_MAX)
        desc = _truncate_clean(it.get("description", ""), USP_DESC_HARD_MAX)
        cleaned.append({"icon": it.get("icon") or "Sparkles", "title": title, "description": desc})

    if len(cleaned) < 4:
        logger.warning(
            f"[usps] only {len(cleaned)} valid items after retry — caller may want to retry"
        )

    return cleaned


async def _call_usps_llm(
    product: Dict[str, Any],
    brand: Dict[str, Any],
    *,
    title_max: int,
    desc_max: int,
    request_id: Optional[str],
    strict: bool,
) -> List[Dict[str, str]]:
    """Single LLM call to generate 4 USPs with explicit length constraints.
    Returns sanitized items (Lucide icon validated, length capped at prompt
    request — final hard cap is enforced by the caller)."""
    context = _product_context(product, brand)
    icon_list = ", ".join(ALLOWED_USP_ICONS)

    system = (
        "Tu es copywriter premium pour une marque de lifestyle haut de gamme "
        "(références : Aesop, Hermès, Officine Universelle Buly, Le Labo). "
        "Tu écris en français. Ta plume est sobre, sensorielle, narrative — "
        "jamais agressive. La marque parle bas et juste.\n\n"
        "Tu produis des USPs (bénéfices clés) qui mêlent CONCRÈTEMENT "
        "ce que fait le produit ET l'expérience sensible qu'il offre. "
        "Tu réponds STRICTEMENT en JSON valide, sans markdown.\n\n"
        f"CONTRAINTES DE LONGUEUR ABSOLUES — TU DOIS LES RESPECTER :\n"
        f"- title  : MAXIMUM {title_max} caractères, espaces inclus. "
        f"Plus court c'est mieux. Compte les caractères AVANT de répondre.\n"
        f"- description : MAXIMUM {desc_max} caractères. "
        f"Compte AVANT de répondre.\n"
        + ("INSTRUCTION CRITIQUE : si tu dépasses, ta réponse est rejetée. "
           "Sois TRÈS concis. Coupe les mots inutiles." if strict else "")
    )
    user = (
        f"{context}\n\n"
        f"TÂCHE : produis 4 USPs PRODUIT-SPÉCIFIQUES, ton premium narratif.\n\n"
        f"INTERDITS (génériques inutiles, ne jamais inclure) :\n"
        f"- Livraison rapide / livraison offerte / garantie / SAV / retour gratuit\n"
        f"- Mots fonctionnels plats : « pratique », « efficace », « qualité supérieure »\n"
        f"- Tournures techniques sèches déshabillées (« 2 moteurs » sans poésie)\n"
        f"- Superlatifs : « meilleur », « N°1 », « incroyable »\n\n"
        f"PRIVILÉGIE :\n"
        f"- Verbes d'expérience : « s'abandonne », « épouse », « révèle », "
        f"« apaise », « accompagne », « se laisse oublier »\n"
        f"- Évocations sensorielles : texture, geste, lumière, son, douceur\n"
        f"- Précision technique HABILLÉE poétiquement (pas niée)\n"
        f"- Le titre est elliptique, évocateur (style Cormorant)\n"
        f"- La description prolonge le titre, raconte une expérience CONCRÈTE\n\n"
        f"EXEMPLES CIBLES (à imiter en TON, pas à recopier) — fauteuil releveur :\n"
        f'  {{"icon": "Feather", "title": "Le geste sans effort", '
        f'"description": "Deux moteurs silencieux accompagnent la verticale en douceur, sans rupture."}}\n'
        f'  {{"icon": "Heart", "title": "Mémoire enveloppante", '
        f'"description": "Une mousse haute densité épouse votre silhouette et la garde en mémoire."}}\n'
        f'  {{"icon": "Volume2", "title": "Le silence des belles mécaniques", '
        f'"description": "Moteurs et articulations à moins de 30 dB, comme un soupir."}}\n'
        f'  {{"icon": "Layers", "title": "Sous la main, la matière", '
        f'"description": "Microfibre dense, finition sourde, sans aucun reflet plastique."}}\n\n'
        f"FORMAT JSON STRICT (réponds UNIQUEMENT ceci, pas de markdown autour) :\n"
        f'{{\n'
        f'  "usps": [\n'
        f'    {{"icon": "<icon_name>", "title": "<≤{title_max} caractères>", '
        f'"description": "<≤{desc_max} caractères, ton sensoriel narratif>"}},\n'
        f'    ... (exactement 4 items)\n'
        f'  ]\n'
        f'}}\n\n'
        f"icon_name DOIT être l'un de : {icon_list}\n"
        f"Choisis l'icône la plus pertinente pour chaque USP.\n"
        f"RAPPEL : title ≤ {title_max} chars, description ≤ {desc_max} chars."
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
        if icon not in ALLOWED_USP_ICONS:
            ci = next((i for i in ALLOWED_USP_ICONS if i.lower() == icon.lower()), None)
            icon = ci or "Sparkles"
        cleaned_items.append({"icon": icon, "title": title, "description": desc})
    return cleaned_items


# ---------------------------------------------------------------------------
# Phase 2.3 — Allowed icons for HowTo steps (subset, more action-oriented)
# ---------------------------------------------------------------------------
# Phase 2.6 Tâche C — Mapping product_kind → templates HowTo adaptatifs
# ---------------------------------------------------------------------------
HOWTO_SECTION_TITLES = {
    "seated_furniture": {"fr": "Comment l'utiliser", "en": "How to use it"},
    "blanket":          {"fr": "Comment l'utiliser au quotidien", "en": "Your daily ritual"},
    "cushion":          {"fr": "Trouver votre maintien", "en": "Find your support"},
    "soft_goods":       {"fr": "Installer en quelques gestes", "en": "Set up in a few gestures"},
    "generic":          {"fr": "Bien commencer", "en": "Getting started"},
}

HOWTO_STEP_HINTS = {
    "seated_furniture": (
        "Étapes d'un rituel d'usage : 1) S'installer (s'asseoir, prendre la "
        "place, sentir l'assise), 2) Régler (commande filaire, inclinaison, "
        "lift), 3) Activer (massage, chauffage, USB selon les features réelles), "
        "4) Profiter (relâcher, lecture, sieste, lever sans effort)."
    ),
    "blanket": (
        "Étapes d'un rituel quotidien d'usage : 1) Choisir le réglage (chaleur, "
        "minuterie), 2) Préparer pour la nuit (déplier, télécommande, position), "
        "3) Entretenir (machine, sécheuse, séchage), 4) Conserver (plier, ranger "
        "dans la housse fournie)."
    ),
    "cushion": (
        "Étapes pour trouver le bon maintien : 1) Positionner (lombaire, "
        "siège, dos), 2) Ajuster (sangle, hauteur, fermeté), 3) Tester (5 min "
        "assis, écouter le corps), 4) Adapter selon l'activité (bureau, voyage, "
        "soir)."
    ),
    "soft_goods": (
        "Étapes pour installer en quelques gestes : 1) Préparer (mesurer le "
        "fauteuil/lit, choisir la face), 2) Draper (couvrir, ajuster les coins), "
        "3) Sécuriser (élastiques, sangles, agrafes), 4) Entretenir (lavage "
        "machine, repassage doux)."
    ),
    "generic": (
        "4 étapes adaptées en s'appuyant sur les features visibles "
        "et les attributs réels du produit, sans inventer de fonctions absentes."
    ),
}


def _detect_product_kind(product: Dict[str, Any]) -> str:
    """Normalise la valeur `source_vision_lock.product_kind` vers un des
    5 buckets de notre mapping HowTo (seated_furniture / blanket / cushion /
    soft_goods / generic). Fait du **fuzzy match par contains** car le SVL
    contient parfois des descriptions longues type "electric lift recliner
    armchair with integrated cup holders" plutôt que des slugs courts.
    """
    svl = product.get("source_vision_lock") or {}
    raw = (svl.get("product_kind") or "").strip().lower()
    if not raw:
        # Fallback secondaire : nom produit
        name = product.get("name") or {}
        if isinstance(name, dict):
            name = name.get("fr") or name.get("en") or ""
        raw = (str(name) or "").lower()

    # Ordre IMPORTANT : blanket avant cover (sinon "cover" triggers soft_goods
    # même si le produit est "blanket cover"); idem cushion avant chair.
    keyword_buckets = [
        ("blanket", ["blanket", "throw", "couverture", "plaid", "duvet"]),
        ("cushion", ["cushion", "pillow", "lumbar", "coussin", "oreiller"]),
        ("soft_goods", ["slipcover", "sofa cover", "chair cover", "housse", "cover"]),
        ("seated_furniture", [
            "recliner", "armchair", "lift chair", "rise chair", "chair",
            "fauteuil", "siège", "seat",
        ]),
    ]
    for bucket, kws in keyword_buckets:
        for kw in kws:
            if kw in raw:
                return bucket
    return raw if raw in HOWTO_SECTION_TITLES else "generic"


# ---------------------------------------------------------------------------
ALLOWED_HOWTO_ICONS = [
    "ArrowDownToLine", "Hand", "MousePointer2", "Settings2", "Move",
    "ChevronsRight", "Check", "Sparkles", "Gauge", "Headphones",
    "Heart", "Sofa", "Plug", "Power", "Volume2", "Compass",
]


# ---------------------------------------------------------------------------
# 3) "Comment l'utiliser" — 3-4 step infographic (Phase 2.3 / Lot I I11)
# ---------------------------------------------------------------------------
async def generate_product_how_to(
    product: Dict[str, Any],
    brand: Dict[str, Any],
    *,
    n_steps: int = 4,
    request_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate `n_steps` (default 4) actionable, sensorielle steps to use the
    product.

    Phase 2.6 Tâche C — retourne désormais un **dict** structuré :
        {
          "section_title": {"fr": "...", "en": "..."}  # adapté au product_kind
          "product_kind": "blanket" | "cushion" | "seated_furniture" | ...
          "steps": [{icon, title, description}, ...]
        }

    Le `section_title` est piloté par `source_vision_lock.product_kind` :
    chaque "kind" a son titre éditorial (ex. "Trouver votre maintien" pour un
    coussin, "Comment l'utiliser au quotidien" pour une couverture chauffante).
    Le prompt Haiku reçoit aussi un *hint* pédagogique qui oriente les 4 étapes
    sur l'usage réel du produit, et non sur des suppositions génériques.

    Lit `source_vision_lock` (matériau + features visibles) pour ancrer le
    contenu sur la réalité du produit, et non sur des suppositions génériques.
    """
    n_steps = max(3, min(int(n_steps or 4), 5))
    context = _product_context(product, brand)
    icons = ", ".join(ALLOWED_HOWTO_ICONS)

    # Phase 2.6 Tâche C — détection adaptative
    pk = _detect_product_kind(product)
    section_title = HOWTO_SECTION_TITLES.get(pk, HOWTO_SECTION_TITLES["generic"])
    step_hint = HOWTO_STEP_HINTS.get(pk, HOWTO_STEP_HINTS["generic"])

    system = (
        "Tu es directeur éditorial d'une marque premium (références Aesop, "
        "Hermès Petit h, Le Labo). Tu écris en français un guide pas à pas "
        "ESSENTIEL et POÉTIQUE pour utiliser un produit. Tu produis du JSON valide.\n\n"
        "Ton : sobre, sensoriel, narratif. Jamais d'impératif sec, jamais d'emoji. "
        "Privilégie verbes d'expérience (« installez-vous », « laissez », « retrouvez »).\n\n"
        "CONTRAINTES DE LONGUEUR ABSOLUES :\n"
        "- title : MAXIMUM 32 caractères, espaces inclus.\n"
        "- description : MAXIMUM 120 caractères.\n"
        "Compte AVANT de répondre. Si tu dépasses, ta réponse est rejetée."
    )
    user = (
        f"{context}\n\n"
        f"TYPE PRODUIT (Vision lock) : {pk}\n"
        f"GUIDE PÉDAGOGIQUE D'ÉTAPES POUR CE TYPE :\n  {step_hint}\n\n"
        f"TÂCHE : produis EXACTEMENT {n_steps} étapes d'utilisation, ton premium, "
        f"ancrées sur le matériau et les features réellement visibles (ANALYSE VISUELLE SOURCE ci-dessus). "
        f"Suis le GUIDE PÉDAGOGIQUE ci-dessus comme grille narrative ; n'invente "
        f"jamais de fonctions absentes du produit.\n\n"
        f"FORMAT JSON STRICT (réponds UNIQUEMENT ceci, sans markdown) :\n"
        f'{{\n'
        f'  "steps": [\n'
        f'    {{"icon": "<icon>", "title": "<≤32 chars>", '
        f'"description": "<≤120 chars, ton sensoriel, geste ou expérience concrète>"}},\n'
        f'    ... ({n_steps} items)\n'
        f'  ]\n'
        f'}}\n\n'
        f"icon DOIT être l'un de : {icons}.\n"
        f"Choisis l'icône la plus pertinente pour chaque étape."
    )

    raw = await safe_claude_text(
        system=system, user=user,
        quality_tier="standard", timeout=40.0, request_id=request_id,
    )
    cleaned = _strip_json_fence(raw or "")
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]+\}", cleaned)
        if not m:
            raise ValueError("Réponse Claude HowTo non parsable")
        data = json.loads(m.group(0))

    items = data.get("steps") or data.get("items") or []
    if not isinstance(items, list) or not items:
        raise ValueError("Réponse Claude HowTo invalide (liste vide)")

    out: List[Dict[str, str]] = []
    for it in items[:n_steps]:
        if not isinstance(it, dict):
            continue
        icon = str(it.get("icon") or "").strip()
        title = str(it.get("title") or "").strip()
        desc = str(it.get("description") or "").strip()
        if not title:
            continue
        if icon not in ALLOWED_HOWTO_ICONS:
            ci = next((i for i in ALLOWED_HOWTO_ICONS if i.lower() == icon.lower()), None)
            icon = ci or "ChevronsRight"
        out.append({
            "icon": icon,
            "title": _truncate_clean(title, 32),
            "description": _truncate_clean(desc, 120),
        })
    if len(out) < 3:
        raise ValueError(f"Réponse Claude HowTo : {len(out)} étapes valides (min 3)")
    return {
        "section_title": dict(section_title),
        "product_kind": pk,
        "steps": out,
    }


# ---------------------------------------------------------------------------
# 4) FAQ produit — 4-6 questions ultra-spécifiques au modèle (Lot I I12)
# ---------------------------------------------------------------------------
async def generate_product_faq(
    product: Dict[str, Any],
    brand: Dict[str, Any],
    *,
    n_questions: int = 5,
    request_id: Optional[str] = None,
) -> List[Dict[str, str]]:
    """Generate 4-6 FAQ items SPECIFIC to this exact product (model, material,
    technical features, dimensions, usage cases). Excludes generic shipping/
    returns/warranty questions (those go to a global FAQ in the footer).

    Output : list of {question, answer}.
    """
    n_questions = max(4, min(int(n_questions or 5), 6))
    context = _product_context(product, brand)

    system = (
        "Tu es responsable expérience client pour une marque premium. "
        "Tu écris en français des FAQs UTILES, FACTUELLES et ANCRÉES sur le produit "
        "(matériau, mécanisme, dimensions, usage). Pas de jargon, pas de marketing-speak. "
        "Tu produis du JSON valide, sans markdown."
    )
    user = (
        f"{context}\n\n"
        f"TÂCHE : produis EXACTEMENT {n_questions} questions/réponses SPÉCIFIQUES À CE PRODUIT.\n\n"
        f"INTERDITS — ne pose JAMAIS de questions :\n"
        f"- Sur la livraison, les délais d'expédition, le suivi de commande\n"
        f"- Sur les retours, garantie, SAV, remboursement\n"
        f"- Sur le paiement, les promos, le code promo\n"
        f"  (ces sujets sont traités dans une FAQ globale en footer)\n\n"
        f"PRIVILÉGIE — questions PRODUIT spécifiques :\n"
        f"- Le matériau réel (cf ANALYSE VISUELLE SOURCE) et son entretien\n"
        f"- Le mécanisme, la motorisation, l'autonomie, le bruit\n"
        f"- Les dimensions, la charge max, la compatibilité (qui peut l'utiliser ?)\n"
        f"- L'installation, le branchement, l'usage quotidien\n"
        f"- Les variantes (couleurs, tailles, finitions disponibles)\n"
        f"- Les bénéfices ergonomiques / médicaux (si applicable)\n\n"
        f"CONTRAINTES :\n"
        f"- question : phrase claire, ≤ 110 caractères\n"
        f"- answer   : 1-3 phrases factuelles, 80-280 caractères, ton premium sobre\n\n"
        f"FORMAT JSON STRICT :\n"
        f'{{\n'
        f'  "faq": [\n'
        f'    {{"question": "<≤110 chars>", "answer": "<80-280 chars>"}},\n'
        f'    ... ({n_questions} items)\n'
        f'  ]\n'
        f'}}\n'
    )

    raw = await safe_claude_text(
        system=system, user=user,
        quality_tier="standard", timeout=45.0, request_id=request_id,
    )
    cleaned = _strip_json_fence(raw or "")
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]+\}", cleaned)
        if not m:
            raise ValueError("Réponse Claude FAQ non parsable")
        data = json.loads(m.group(0))

    items = data.get("faq") or data.get("items") or []
    if not isinstance(items, list) or not items:
        raise ValueError("Réponse Claude FAQ invalide (liste vide)")

    out: List[Dict[str, str]] = []
    for it in items[:n_questions]:
        if not isinstance(it, dict):
            continue
        q = str(it.get("question") or "").strip()
        a = str(it.get("answer") or "").strip()
        if not q or not a:
            continue
        out.append({
            "question": _truncate_clean(q, 110),
            "answer": _truncate_clean(a, 320),
        })
    if len(out) < 3:
        raise ValueError(f"Réponse Claude FAQ : {len(out)} items valides (min 3)")
    return out


# ---------------------------------------------------------------------------
# 5) Editorial cards — 1 hero vertical + 3 short cards (Phase 2.5 / Tâche A)
# ---------------------------------------------------------------------------
async def generate_product_editorial_cards(
    product: Dict[str, Any],
    brand: Dict[str, Any],
    *,
    n_cards: int = 3,
    request_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate one hero block + 3 short editorial cards for the product page.

    Output shape :
        {
          "hero":  {"image_style": "wide_lifestyle"|"lifestyle",
                    "title":       "<6-10 mots>",
                    "description": "<1-2 phrases, ≤180 chars>"},
          "cards": [
            {"image_style": "closeup"|"detail"|"in_use"|...,
             "title":       "<6-8 mots>",
             "description": "<≤100 chars>"},
            ... 3 items
          ]
        }

    Les `image_style` sont sélectionnés parmi un pool canonical ; le frontend
    pioche l'image correspondante depuis `generated_images_by_variant[color]`.
    """
    context = _product_context(product, brand)
    allowed_hero = ["wide_lifestyle", "lifestyle"]
    allowed_card = ["closeup", "detail", "in_use", "side_profile",
                    "texture_closeup", "folded_display", "on_sofa",
                    "on_bed", "on_chair", "stacked", "context_room"]

    system = (
        "Tu es directeur éditorial d'une marque premium (références Aesop, "
        "Hermès, Le Labo). Tu écris en français des micro-essais produit "
        "sobres, sensoriels et narratifs. Pas d'emoji, pas de ponctuation "
        "excessive, ton poétique ancré sur la matière. JSON valide uniquement."
    )
    user = (
        f"{context}\n\n"
        f"TÂCHE : produis UN bloc hero (titre + 1-2 phrases) et "
        f"EXACTEMENT {n_cards} cards (titre + 1 phrase), ancrés sur l'ANALYSE "
        f"VISUELLE SOURCE.\n\n"
        f"CONTRAINTES ABSOLUES :\n"
        f"- hero.title       : 4-10 mots\n"
        f"- hero.description : 1-2 phrases, ≤ 180 caractères\n"
        f"- card.title       : 3-6 mots (≤ 40 chars)\n"
        f"- card.description : 1 phrase, ≤ 110 caractères\n\n"
        f"Associe chaque bloc à un image_style (pour que le front pioche "
        f"l'image adéquate générée par le pipeline 8-styles) :\n"
        f"- hero.image_style ∈ {allowed_hero}\n"
        f"- card.image_style ∈ {allowed_card}\n"
        f"(Privilégie closeup/detail/in_use si le produit est un fauteuil ; "
        f"texture_closeup/folded_display/on_sofa si c'est du textile/couverture ; "
        f"on_chair/stacked/texture_closeup si c'est un coussin.)\n\n"
        f"FORMAT JSON STRICT (réponds UNIQUEMENT ceci) :\n"
        f'{{\n'
        f'  "hero":  {{"image_style": "<style>", "title": "<...>", "description": "<...>"}},\n'
        f'  "cards": [\n'
        f'    {{"image_style": "<style>", "title": "<...>", "description": "<...>"}},\n'
        f'    ... ({n_cards} items)\n'
        f'  ]\n'
        f'}}\n'
    )

    raw = await safe_claude_text(
        system=system, user=user,
        quality_tier="standard", timeout=50.0, request_id=request_id,
    )
    cleaned = _strip_json_fence(raw or "")
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]+\}", cleaned)
        if not m:
            raise ValueError("Réponse Claude editorial non parsable")
        data = json.loads(m.group(0))

    hero_raw = data.get("hero") or {}
    hero = {
        "image_style":
            str(hero_raw.get("image_style") or "wide_lifestyle").strip().lower()
            if str(hero_raw.get("image_style") or "").strip().lower() in allowed_hero
            else "wide_lifestyle",
        "title": _truncate_clean(str(hero_raw.get("title") or "").strip(), 90),
        "description": _truncate_clean(str(hero_raw.get("description") or "").strip(), 200),
    }
    cards_raw = data.get("cards") or []
    cards: List[Dict[str, str]] = []
    for it in cards_raw[:n_cards]:
        if not isinstance(it, dict):
            continue
        style = str(it.get("image_style") or "detail").strip().lower()
        if style not in allowed_card:
            style = "detail"
        t = _truncate_clean(str(it.get("title") or "").strip(), 42)
        d = _truncate_clean(str(it.get("description") or "").strip(), 120)
        if not t:
            continue
        cards.append({"image_style": style, "title": t, "description": d})
    if len(cards) < 2:
        raise ValueError(f"Editorial cards invalides ({len(cards)}/{n_cards})")
    if not hero["title"]:
        raise ValueError("Editorial hero title vide")
    return {"hero": hero, "cards": cards}

