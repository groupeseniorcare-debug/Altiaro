"""Backfill `variants[]` pour les produits AliExpress qui ont été importés
avant le fix du pipeline (sourcing.py — branche AE absente).

Re-fetch les SKUs via l'API AE Dropshipping (`_ae_ds_product_detail`) puis
mappe vers la structure standard `variants[]` (réutilise `_map_ae_skus_to_variants`).

Usage :
  cd /app/backend
  python -m scripts.backfill_ae_variants <site_id>     # un seul site
  python -m scripts.backfill_ae_variants --all         # tous les sites
  python -m scripts.backfill_ae_variants --dry-run     # aucune écriture
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))
load_dotenv(BACKEND_DIR / ".env")

from motor.motor_asyncio import AsyncIOMotorClient  # noqa: E402

# Late import : sourcing requires environment to be loaded first
from routes.sourcing import _ae_ds_product_detail, _map_ae_skus_to_variants  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("backfill_ae_variants")


async def backfill(site_id: str | None, dry_run: bool):
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]

    query = {
        "source.provider": "aliexpress",
        "$or": [{"variants": {"$exists": False}}, {"variants": {"$size": 0}}],
    }
    if site_id and site_id != "--all":
        query["site_id"] = site_id

    total = await db.products.count_documents(query)
    log.info(f"=== {total} produit(s) AE à backfiller "
             f"(site_id={site_id or 'TOUS'}, dry_run={dry_run}) ===")

    cursor = db.products.find(query, {"_id": 0, "id": 1, "site_id": 1, "name": 1, "source": 1})
    summary = {"processed": 0, "with_variants": 0, "no_variants": 0, "errors": 0}
    async for p in cursor:
        pid = p["id"]
        sid = p["site_id"]
        ae_pid = (p.get("source") or {}).get("product_id")
        nm = p.get("name") or {}
        if isinstance(nm, dict):
            nm = nm.get("fr") or nm.get("en") or next(iter(nm.values()), "")
        nm = (nm or "")[:50]

        if not ae_pid:
            log.warning(f"[skip] {pid} ({nm}) — pas de source.product_id")
            summary["errors"] += 1
            continue

        try:
            ae_detail = await _ae_ds_product_detail(ae_pid, site_id=sid)
        except Exception as e:
            log.exception(f"[fail] {pid} ({nm}) — _ae_ds_product_detail: {e}")
            summary["errors"] += 1
            continue
        if not ae_detail:
            log.warning(f"[skip] {pid} ({nm}) — produit AE indisponible (404 / désindexé)")
            summary["no_variants"] += 1
            continue

        # Calcul du taux USD→EUR depuis le doc actuel (price/cost_price_ht)
        usd_to_eur = 0.92
        try:
            cost_usd = float(ae_detail.get("cost_usd") or 0)
            doc_for_rate = await db.products.find_one({"id": pid}, {"_id": 0, "cost_price_ht": 1})
            cost_eur = float((doc_for_rate or {}).get("cost_price_ht") or 0)
            if cost_usd > 0 and cost_eur > 0:
                usd_to_eur = cost_eur / cost_usd
        except Exception:
            pass

        variants = _map_ae_skus_to_variants(
            ae_detail.get("skus_raw") or [], usd_to_eur=usd_to_eur, max_variants=30
        )
        summary["processed"] += 1

        if not variants:
            log.info(f"[backfill] OK product {pid} ({nm}) → 0 variantes (mono-SKU)")
            summary["no_variants"] += 1
            if not dry_run:
                # On laisse [] explicite pour signaler que le pipeline a tourné
                await db.products.update_one(
                    {"id": pid},
                    {"$set": {"variants": [], "variants_backfilled_at":
                              datetime.now(timezone.utc).isoformat()}},
                )
            continue

        log.info(f"[backfill] OK product {pid} ({nm}) → {len(variants)} variantes")
        summary["with_variants"] += 1
        if dry_run:
            continue
        await db.products.update_one(
            {"id": pid},
            {"$set": {
                "variants": variants,
                "variants_backfilled_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }},
        )

    log.info(f"=== TERMINÉ : {summary} ===")
    client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("site_id", nargs="?", default=None,
                        help="site_id à backfiller (défaut : tous les sites)")
    parser.add_argument("--all", action="store_true", help="Tous les sites")
    parser.add_argument("--dry-run", action="store_true", help="Aucune écriture")
    args = parser.parse_args()
    sid = None if args.all else args.site_id
    asyncio.run(backfill(sid, args.dry_run))
