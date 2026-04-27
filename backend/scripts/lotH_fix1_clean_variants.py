"""Lot H Fix 1 — Audit + clean variants des produits existants.

Itère sur tous les produits d'un site (par défaut Altea) et applique
`filter_useless_axes()` aux variantes existantes.
- Supprime les axes parasites (Ships From, Plug Type) de `properties[]`
- Dédoublonne les variantes
- Log dans `admin_notifications` chaque suppression

Idempotent : si déjà nettoyé, ne change rien (pas de removed_axes).

Usage :
    cd /app/backend && python -m scripts.lotH_fix1_clean_variants
    cd /app/backend && python -m scripts.lotH_fix1_clean_variants --site-id <uuid>
    cd /app/backend && python -m scripts.lotH_fix1_clean_variants --all  # tous les sites
    cd /app/backend && python -m scripts.lotH_fix1_clean_variants --dry-run  # preview only
"""
import argparse
import asyncio
import os
import sys

sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")

from motor.motor_asyncio import AsyncIOMotorClient  # noqa: E402

from services.variant_filter import (  # noqa: E402
    filter_useless_axes,
    log_filtered_axes_to_admin,
)

ALTEA_DEFAULT = "6867223e-7ea5-45a7-815a-300cd89b7656"


async def audit_site(db, site_id: str, dry_run: bool = False) -> dict:
    """Returns stats {total_products, cleaned_products, total_variants_before, total_variants_after}."""
    stats = {
        "site_id": site_id,
        "total_products": 0,
        "cleaned_products": 0,
        "total_variants_before": 0,
        "total_variants_after": 0,
        "axes_removed": [],
    }

    async for p in db.products.find({"site_id": site_id}, {"_id": 0, "id": 1, "name": 1, "variants": 1}):
        stats["total_products"] += 1
        variants = p.get("variants") or []
        if not variants:
            continue

        n_before = len(variants)
        stats["total_variants_before"] += n_before

        cleaned, removed = filter_useless_axes(variants)
        n_after = len(cleaned)
        stats["total_variants_after"] += n_after

        if not removed:
            # Already clean
            continue

        stats["cleaned_products"] += 1
        nm = p.get("name", {})
        if isinstance(nm, dict):
            nm = nm.get("fr") or list(nm.values())[0] if nm else "?"
        print(f"\n→ Product {p['id'][:8]} ({nm[:60]})")
        print(f"  Axes removed: {[(r['kind'], r['sample_values'][:3]) for r in removed]}")
        print(f"  Variants: {n_before} → {n_after}")
        for v in cleaned:
            props = v.get("properties", [])
            print(f"    · vid={v.get('vid','?')[:18]:<18} props={props} stock={v.get('stock')}")

        for r in removed:
            stats["axes_removed"].append({
                "product_id": p["id"],
                "axis_kind": r["kind"],
                "axis_values_sample": r["sample_values"],
                "n_values": r["n_values"],
            })

        if not dry_run:
            await db.products.update_one(
                {"id": p["id"]},
                {"$set": {"variants": cleaned}},
            )
            await log_filtered_axes_to_admin(db, site_id, p["id"], removed)

    return stats


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--site-id", default=ALTEA_DEFAULT)
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="Preview only, no DB writes")
    args = parser.parse_args()

    c = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = c[os.environ.get("DB_NAME", "altiaro_dev")]

    site_ids: list[str] = []
    if args.all:
        async for s in db.sites.find({}, {"_id": 0, "id": 1}):
            site_ids.append(s["id"])
    else:
        site_ids = [args.site_id]

    print("=== Lot H Fix 1 — variant audit ===")
    print(f"Mode: {'DRY-RUN (no writes)' if args.dry_run else 'LIVE (DB updates)'}")
    print(f"Sites: {len(site_ids)}")

    for sid in site_ids:
        print(f"\n## Site {sid[:8]}")
        stats = await audit_site(db, sid, dry_run=args.dry_run)
        print(f"\n  Summary: {stats['cleaned_products']}/{stats['total_products']} products cleaned, "
              f"{stats['total_variants_before']} → {stats['total_variants_after']} variants total, "
              f"{len(stats['axes_removed'])} axes removed")


if __name__ == "__main__":
    asyncio.run(main())
