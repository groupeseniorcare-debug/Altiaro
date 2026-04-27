"""Lot H Fix 1 — Filtre des axes de variantes parasites (Ships From, Plug Type).

Quand on importe un produit AliExpress / CJ, les variantes peuvent contenir
plusieurs axes :
  - axes UTILES : couleur, taille, modèle (à exposer au client)
  - axes PARASITES : "Ships From" (entrepôt logistique), "Plug Type"
    (type de prise électrique régionale), etc. (NE PAS exposer au client)

Le schéma actuel `variants[].properties[]` est positionnel (pas de label),
donc on classifie chaque axe par ses VALEURS via heuristique :
  - Si toutes les valeurs sont des codes pays / ports / warehouses → ships_from
  - Si toutes les valeurs contiennent "PLUG" / sont des types de prise → plug
  - Sinon → useful (à conserver)

Le filtrage produit un nouveau `variants[]` :
  - Les axes parasites sont retirés de `properties[]` (on raccourcit)
  - Les variantes dédupliquées sur les axes utiles restants
  - Le `name` est reconstruit ("Black / L" au lieu de "Black / GERMANY / L")

Logger admin : appelle `log_filtered_axis()` qui inscrit dans
`db.admin_notifications` chaque suppression pour audit / extension
de la whitelist.

Idempotent : si on relance sur des variantes déjà nettoyées, ne fait rien.
"""
from __future__ import annotations

import logging
import unicodedata
from datetime import datetime, timezone
from typing import Iterable

logger = logging.getLogger("altiaro.variant_filter")


# Pays / régions / warehouses — quand toutes les valeurs d'un axe correspondent,
# c'est un axe "Ships From" qu'il faut SUPPRIMER (pas un choix client).
SHIPS_FROM_VALUES = {
    # Country names UPPERCASE (AE format default)
    "GERMANY", "FRANCE", "CHINA", "ITALY", "SPAIN", "USA", "UNITED KINGDOM",
    "POLAND", "CZECH", "CZECH REPUBLIC", "AUSTRALIA", "JAPAN",
    "NETHERLANDS", "BELGIUM", "RUSSIA", "BRAZIL", "TURKEY",
    "UAE", "UNITED ARAB EMIRATES", "SAUDI ARABIA", "MEXICO",
    "CANADA", "INDIA", "KOREA", "SOUTH KOREA", "PORTUGAL",
    "AUSTRIA", "DENMARK", "FINLAND", "NORWAY", "SWEDEN",
    "SWITZERLAND", "IRELAND", "GREECE",
    # Country names normal-case (we lowercase before lookup)
    "allemagne", "france", "chine", "italie", "espagne",
    "etats-unis", "etats unis", "royaume-uni", "royaume uni",
    "pologne", "tchequie", "australie", "japon", "pays-bas", "pays bas",
    "belgique", "russie", "bresil", "turquie", "emirats", "mexique",
    "canada", "inde", "coree", "portugal", "autriche", "danemark",
    "finlande", "norvege", "suede", "suisse", "irlande", "grece",
    # ISO 2-letter codes
    "FR", "DE", "CN", "US", "IT", "ES", "NL", "BE", "GB", "UK",
    "PL", "CZ", "AU", "JP", "RU", "BR", "TR", "AE", "MX", "CA",
    "IN", "KR", "PT", "AT", "DK", "FI", "NO", "SE", "CH", "IE", "GR",
    # Generic warehouse markers
    "GLOBAL", "WORLDWIDE", "OVERSEAS", "OVERSEAS WAREHOUSE",
    "EU WAREHOUSE", "CN WAREHOUSE", "US WAREHOUSE", "RU WAREHOUSE",
    "AU WAREHOUSE", "JP WAREHOUSE", "DOMESTIC",
    "SHIPS FROM", "ENTREPOT", "ENTREPÔT",
}

# Types de prises électriques — "EU Plug", "US Plug", etc. (jamais utile au client)
PLUG_TYPE_VALUES = {
    "EU PLUG", "US PLUG", "UK PLUG", "AU PLUG", "JP PLUG", "CN PLUG",
    "EUROPE PLUG", "AMERICAN PLUG", "BRITISH PLUG", "ASIAN PLUG",
    "TYPE A", "TYPE B", "TYPE C", "TYPE D", "TYPE E", "TYPE F",
    "TYPE G", "TYPE H", "TYPE I", "TYPE J", "TYPE K", "TYPE L",
    "EU STANDARD", "US STANDARD", "UK STANDARD", "AU STANDARD",
    "PRISE EU", "PRISE US", "PRISE UK", "PRISE FR",
}

# Auxiliary heuristics
WAREHOUSE_KEYWORDS = ("WAREHOUSE", "ENTREPOT", "ENTREPÔT", "DEPOT", "STOCK")


def _normalize(s: str) -> str:
    """Strip + uppercase + remove accents for robust matching."""
    if s is None:
        return ""
    s = str(s).strip()
    # Strip accents
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    return s.upper()


def _is_ships_from_value(v: str) -> bool:
    """Classifie une valeur unique. Plus tolérant que match exact :
    si la valeur contient un keyword de warehouse → ships_from."""
    norm = _normalize(v)
    if not norm:
        return False
    if norm in SHIPS_FROM_VALUES:
        return True
    # Contains "WAREHOUSE", "DEPOT", etc.
    if any(kw in norm for kw in WAREHOUSE_KEYWORDS):
        return True
    return False


def _is_plug_value(v: str) -> bool:
    norm = _normalize(v)
    if not norm:
        return False
    if norm in PLUG_TYPE_VALUES:
        return True
    if "PLUG" in norm and len(norm) <= 30:  # "EU PLUG" etc., not a sentence
        return True
    return False


def classify_axis(values: list[str]) -> str:
    """Classify an axis based on its values.

    Returns one of: 'ships_from' | 'plug' | 'useful'

    Heuristique : si ≥80% des valeurs distinctes correspondent à un type
    parasite, l'axe est classé comme tel. Sinon "useful" → on garde.
    """
    distinct = list({str(v).strip() for v in values if v is not None and str(v).strip()})
    if not distinct:
        return "useful"  # axe vide → on ne touche pas

    n = len(distinct)
    n_ships = sum(1 for v in distinct if _is_ships_from_value(v))
    n_plug = sum(1 for v in distinct if _is_plug_value(v))

    if n_ships >= max(1, int(0.8 * n)):
        return "ships_from"
    if n_plug >= max(1, int(0.8 * n)):
        return "plug"
    return "useful"


def filter_useless_axes(variants: list[dict]) -> tuple[list[dict], list[dict]]:
    """Strip axes parasites from variants[].

    Args:
        variants: liste de dicts avec champs `vid`, `sku`, `properties: [str, ...]`,
                  `name`, `sell_price_eur`, `stock`, `image`.

    Returns:
        (cleaned_variants, removed_axes_meta) :
          - cleaned_variants : nouveau tableau avec properties[] raccourci, dédupliqué.
          - removed_axes_meta : liste de {position, kind, sample_values, n_values}
            décrivant les axes supprimés (utile pour log admin).
    """
    if not variants:
        return variants, []

    # Combien d'axes (positions) ?
    n_axes = max((len(v.get("properties") or []) for v in variants), default=0)
    if n_axes <= 1:
        return variants, []  # 1 seul axe → forcément utile

    # Classifie chaque position
    axis_kinds: list[str] = []
    axis_values_per_pos: list[list[str]] = []
    for i in range(n_axes):
        vals = [
            (v.get("properties") or [None] * (i + 1))[i]
            for v in variants
            if len(v.get("properties") or []) > i
        ]
        vals = [str(x).strip() for x in vals if x is not None and str(x).strip()]
        kind = classify_axis(vals)
        axis_kinds.append(kind)
        axis_values_per_pos.append(sorted(set(vals)))

    keep = [i for i, k in enumerate(axis_kinds) if k == "useful"]
    removed = [
        {
            "position": i,
            "kind": axis_kinds[i],
            "sample_values": axis_values_per_pos[i][:6],
            "n_values": len(axis_values_per_pos[i]),
        }
        for i in range(n_axes)
        if axis_kinds[i] != "useful"
    ]

    if len(keep) == n_axes:
        return variants, []  # rien à filtrer

    # Cas dégénéré : tous les axes parasites → garder 1 seule variante (la 1ère)
    if not keep:
        logger.warning("[variant_filter] all axes parasites → keep first variant only")
        return [variants[0]], removed

    # Filtre les axes parasites + dédoublonne
    seen: set[tuple] = set()
    cleaned: list[dict] = []
    for v in variants:
        props = v.get("properties") or []
        new_props = [props[i] for i in keep if i < len(props)]
        key = tuple(new_props)
        if key in seen:
            continue
        seen.add(key)
        v_new = dict(v)  # shallow copy
        v_new["properties"] = new_props
        # Reconstruit le name proprement
        v_new["name"] = " / ".join(p for p in new_props if p) or v.get("name", "")
        cleaned.append(v_new)

    return cleaned, removed


async def log_filtered_axes_to_admin(
    db,
    site_id: str,
    product_id: str,
    removed_axes: list[dict],
) -> None:
    """Log each filtered axis to `db.admin_notifications` for audit."""
    if not removed_axes:
        return
    now = datetime.now(timezone.utc).isoformat()
    docs = [
        {
            "id": f"variant-axis-filtered-{product_id[:8]}-{ax['position']}-{int(datetime.now().timestamp())}",
            "type": "variant_axis_filtered",
            "site_id": site_id,
            "product_id": product_id,
            "axis_position": ax["position"],
            "axis_kind": ax["kind"],
            "axis_values_sample": ax["sample_values"],
            "axis_values_count": ax["n_values"],
            "created_at": now,
            "read": False,
        }
        for ax in removed_axes
    ]
    try:
        await db.admin_notifications.insert_many(docs)
    except Exception as e:
        logger.warning(f"[variant_filter] failed to insert admin_notifications: {e}")


def filter_useless_axes_with_log(
    variants: list[dict],
    site_id: str | None = None,
    product_id: str | None = None,
) -> tuple[list[dict], list[dict]]:
    """Wrapper qui combine filtrage + log informationnel (sans DB).

    Pour le log DB asynchrone, voir `log_filtered_axes_to_admin()`.
    """
    cleaned, removed = filter_useless_axes(variants)
    if removed:
        kinds = ", ".join(f"pos{r['position']}={r['kind']}" for r in removed)
        n_before = len(variants)
        n_after = len(cleaned)
        logger.info(
            f"[variant_filter] site={site_id[:8] if site_id else '?'} "
            f"product={product_id[:8] if product_id else '?'} "
            f"axes_removed={kinds} variants {n_before}→{n_after}"
        )
    return cleaned, removed


__all__ = [
    "classify_axis",
    "filter_useless_axes",
    "filter_useless_axes_with_log",
    "log_filtered_axes_to_admin",
]
