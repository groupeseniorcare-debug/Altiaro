"""TVA & marges bruttes pour Altiora.

Règle unique : le prix de vente produit est TTC (ce que le client paye).
Le prix d'achat fournisseur est HT (déclaré par le Concepteur).
La marge brute HT = CA HT - Prix d'achat HT.
"""
from __future__ import annotations
from typing import Optional


# Taux de TVA standard par pays (les sites ciblent ce marché principal)
VAT_BY_COUNTRY = {
    "FR": 0.20,
    "DE": 0.19,
    "BE": 0.21,
    "NL": 0.21,
    "LU": 0.17,
    "UK": 0.20,
    "CH": 0.077,
    "ES": 0.21,
    "IT": 0.22,
    "PT": 0.23,
}
DEFAULT_VAT = 0.20


def site_vat_rate(site: Optional[dict]) -> float:
    """Renvoie le taux de TVA applicable à un site.

    Priorité : site.vat_rate > 1er pays ciblé > défaut 20%.
    """
    if not site:
        return DEFAULT_VAT
    if site.get("vat_rate") is not None:
        try:
            return float(site["vat_rate"])
        except (TypeError, ValueError):
            pass
    countries = site.get("selected_countries") or []
    for c in countries:
        code = (c or "").upper()
        if code in VAT_BY_COUNTRY:
            return VAT_BY_COUNTRY[code]
    return DEFAULT_VAT


def ttc_to_ht(amount_ttc: float, vat_rate: float) -> float:
    """Convertit un montant TTC en HT."""
    if vat_rate <= 0:
        return round(float(amount_ttc), 2)
    return round(float(amount_ttc) / (1.0 + float(vat_rate)), 2)


def compute_order_ht(items: list, vat_rate: float) -> dict:
    """À partir d'une liste d'items (avec snapshot), calcule les totaux HT & marge.

    Chaque item doit exposer : price (TTC), quantity, cost_price_ht (snapshot),
    item_vat_rate (optionnel pour overrider au niveau ligne).
    """
    subtotal_ttc = 0.0
    subtotal_ht = 0.0
    cost_ht = 0.0
    for it in items:
        qty = int(it.get("quantity") or 0)
        price_ttc = float(it.get("price") or 0)
        cost = float(it.get("cost_price_ht") or 0)
        line_vat = it.get("item_vat_rate")
        vat = float(line_vat) if line_vat is not None else float(vat_rate)
        line_ttc = price_ttc * qty
        line_ht = line_ttc / (1.0 + vat) if vat > 0 else line_ttc
        subtotal_ttc += line_ttc
        subtotal_ht += line_ht
        cost_ht += cost * qty
    gross_margin_ht = subtotal_ht - cost_ht
    return {
        "subtotal_ttc": round(subtotal_ttc, 2),
        "subtotal_ht": round(subtotal_ht, 2),
        "cost_ht": round(cost_ht, 2),
        "gross_margin_ht": round(gross_margin_ht, 2),
    }
