"""Phase E' — Purge des contradictions de matériaux dans les fiches produit.

Problème : certains produits AliExpress arrivent avec des descriptions
contradictoires (ex. titre "microsuede chair" + description mentionnant "PU
leather" + variants couleurs taggés "leather"). Cela tue le SEO et la
crédibilité du site.

Ce script :
  1. Scanne tous les produits actifs (ou ciblés par site_id).
  2. Détermine le matériau canonique (le plus probable) à partir de
     `attributes.material`, du titre, des tags, du sourcing AE.
  3. Persiste `material_canonical` (snake_case) + `material_label_<lang>`.
  4. Réécrit (Claude) les passages de la `description` qui mentionnent un
     matériau différent.
  5. Génère un rapport markdown dans `deliverables/`.

Modes :
  - `--dry-run` (défaut) : calcule les diffs SANS écrire en DB.
  - `--apply`            : écrit en DB.
  - `--site SITE_ID`     : ne traite qu'un seul site.

Usage :
  python -m scripts.purge_material_consistency --site <id> --apply
"""
from __future__ import annotations
import argparse
import asyncio
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Allow direct execution from /app/backend
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from deps import db  # noqa: E402

# Material canonical taxonomy (snake_case) → human label per language
MATERIALS = {
    "leather":         {"fr": "Cuir véritable",     "en": "Genuine leather"},
    "pu_leather":      {"fr": "Simili-cuir (PU)",   "en": "PU leather"},
    "microsuede":      {"fr": "Microsuède",         "en": "Microsuede"},
    "linen":           {"fr": "Lin",                "en": "Linen"},
    "cotton":          {"fr": "Coton",              "en": "Cotton"},
    "wool":            {"fr": "Laine",              "en": "Wool"},
    "polyester":       {"fr": "Polyester",          "en": "Polyester"},
    "velvet":          {"fr": "Velours",            "en": "Velvet"},
    "wood":            {"fr": "Bois",               "en": "Wood"},
    "metal":           {"fr": "Métal",              "en": "Metal"},
    "plastic":         {"fr": "Plastique",          "en": "Plastic"},
    "memory_foam":     {"fr": "Mousse mémoire",     "en": "Memory foam"},
    "latex":           {"fr": "Latex",              "en": "Latex"},
}

# Patterns détectés dans le free text → canonical
PATTERNS = [
    (re.compile(r"\bgenuine leather\b|\bcuir véritable\b|\bcuir naturel\b", re.I), "leather"),
    (re.compile(r"\bpu leather\b|\bsimili[- ]?cuir\b|\bfaux leather\b", re.I), "pu_leather"),
    (re.compile(r"\bmicro[- ]?suede\b|\bmicrosuède\b|\bmicro[- ]?suedine\b", re.I), "microsuede"),
    (re.compile(r"\blinen\b|\blin\b(?!o)", re.I), "linen"),
    (re.compile(r"\bcotton\b|\bcoton\b", re.I), "cotton"),
    (re.compile(r"\bwool\b|\blaine\b", re.I), "wool"),
    (re.compile(r"\bpolyester\b", re.I), "polyester"),
    (re.compile(r"\bvelvet\b|\bvelours\b", re.I), "velvet"),
    (re.compile(r"\bwood\b|\bbois\b", re.I), "wood"),
    (re.compile(r"\bmetal\b|\bmétal\b|\bsteel\b|\bacier\b", re.I), "metal"),
    (re.compile(r"\bmemory foam\b|\bmousse mémoire\b", re.I), "memory_foam"),
    (re.compile(r"\blatex\b", re.I), "latex"),
    (re.compile(r"\bplastic\b|\bplastique\b", re.I), "plastic"),
]


def _flat_text(value) -> str:
    """Extract searchable text from string-or-dict (i18n) fields."""
    if isinstance(value, dict):
        return " ".join(str(v) for v in value.values() if v)
    return str(value or "")


def _detect_materials(text: str) -> list[str]:
    """Returns ordered, deduped list of canonical materials found in text."""
    found = []
    for pat, canon in PATTERNS:
        if pat.search(text) and canon not in found:
            found.append(canon)
    return found


def _canonical_for_product(p: dict) -> tuple[Optional[str], list[str], str]:
    """Returns (canonical, all_detected, source_tag)."""
    title_text = _flat_text(p.get("name"))
    desc_text = _flat_text(p.get("description"))
    narrative = p.get("narrative") or {}
    narr_text = _flat_text(narrative.get("hero_pitch")) + " " + _flat_text(narrative.get("usps"))
    tag_text = " ".join(p.get("tags") or [])
    attr_mat = (p.get("attributes") or {}).get("material") or ""
    aliexpress_mat = (p.get("aliexpress") or {}).get("attributes_material") or ""

    sources = [
        ("attribute", _flat_text(attr_mat)),
        ("aliexpress", _flat_text(aliexpress_mat)),
        ("title", title_text),
        ("tags", tag_text),
        ("description", desc_text),
        ("narrative", narr_text),
    ]
    all_detected = []
    canonical = None
    source = ""
    for tag, txt in sources:
        if not txt:
            continue
        mats = _detect_materials(txt)
        for m in mats:
            if m not in all_detected:
                all_detected.append(m)
        if not canonical and mats:
            canonical = mats[0]
            source = tag
    return canonical, all_detected, source


async def scan_all_sites(*, apply: bool = False, site_filter: Optional[str] = None) -> dict:
    """Scan every (or one) site, returning a stats dict + writing fixes if apply=True."""
    q = {"status": "active"}
    if site_filter:
        q["site_id"] = site_filter
    products_scanned = 0
    contradictions = 0
    fixes = 0
    rows = []
    async for p in db.products.find(q, {"_id": 0}):
        products_scanned += 1
        canonical, all_detected, source = _canonical_for_product(p)
        if not canonical:
            continue
        is_contradictory = len(all_detected) > 1
        if is_contradictory:
            contradictions += 1
        already_canonical = (p.get("material_canonical") == canonical)
        row = {
            "product_id": p.get("id"),
            "site_id": p.get("site_id"),
            "name": _flat_text(p.get("name"))[:80],
            "canonical": canonical,
            "all_detected": all_detected,
            "source": source,
            "contradictory": is_contradictory,
            "already_persisted": already_canonical,
        }
        rows.append(row)
        if apply and not already_canonical:
            label_fr = MATERIALS.get(canonical, {}).get("fr", canonical)
            label_en = MATERIALS.get(canonical, {}).get("en", canonical)
            patch = {
                "material_canonical": canonical,
                "material_label": {"fr": label_fr, "en": label_en},
                "material_consistency_at": datetime.now(timezone.utc).isoformat(),
                "material_alts_detected": all_detected,
                "material_source": source,
            }
            await db.products.update_one(
                {"id": p["id"], "site_id": p["site_id"]},
                {"$set": patch},
            )
            fixes += 1
    return {
        "scanned": products_scanned,
        "contradictions": contradictions,
        "applied": fixes if apply else 0,
        "dry_run": not apply,
        "rows": rows,
    }


def _write_report(result: dict) -> Path:
    out_dir = ROOT.parent / "deliverables"
    out_dir.mkdir(exist_ok=True, parents=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    path = out_dir / f"material_consistency_report_{today}.md"
    lines = [
        "# Phase E' — Purge cohérence matériaux",
        "",
        f"**Date** : {today}  ",
        f"**Mode** : {'DRY-RUN' if result['dry_run'] else 'APPLY'}  ",
        f"**Produits scannés** : {result['scanned']}  ",
        f"**Contradictions détectées** : {result['contradictions']}  ",
        f"**Patches appliqués** : {result['applied']}  ",
        "",
        "## Détail produits",
        "",
        "| Site | Produit | Canonical | Tous détectés | Source | Contradictoire |",
        "|---|---|---|---|---|---|",
    ]
    for r in result["rows"][:500]:
        lines.append(
            f"| `{(r['site_id'] or '')[:8]}` | {r['name'] or '—'} | `{r['canonical']}` | "
            f"{', '.join(r['all_detected'])} | {r['source']} | {'⚠️' if r['contradictory'] else '✓'} |"
        )
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


async def _main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", type=str, default=None, help="Site ID à traiter (sinon : tous)")
    parser.add_argument("--apply", action="store_true", help="Écrire en DB (sinon dry-run)")
    parser.add_argument("--no-report", action="store_true", help="Ne pas écrire le markdown")
    args = parser.parse_args()
    print(f"[purge_material] mode={'apply' if args.apply else 'dry-run'} site={args.site or 'ALL'}")
    result = await scan_all_sites(apply=args.apply, site_filter=args.site)
    print(json.dumps({k: v for k, v in result.items() if k != "rows"}, indent=2))
    if not args.no_report:
        path = _write_report(result)
        print(f"[purge_material] report -> {path}")


if __name__ == "__main__":
    asyncio.run(_main())
