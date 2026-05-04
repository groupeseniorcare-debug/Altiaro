"""Sprint 3.3 — AliExpress auto-refresh cron job.

Récapitulatif du flow :
    - `products` contenant `ae_item_id` sont refreshés via l'API AliExpress
      (prix, stock, variants) toutes les 24 h.
    - Les drifts supérieurs à 5 % déclenchent une `admin_notifications`.
    - Les produits OOS (out-of-stock) sont automatiquement mis en `status=paused`.

Branchement : appelé depuis `server.py` dans la définition APScheduler.
Flag d'activation : `RUN_HEAVY=1` dans `.env`.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Any, Dict

from deps import db

logger = logging.getLogger("altiaro.cron.aliexpress")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def refresh_aliexpress_products_job() -> Dict[str, Any]:
    """Scheduled entry. Returns a summary dict."""
    if os.environ.get("RUN_HEAVY", "0") != "1":
        return {"ok": False, "reason": "RUN_HEAVY=0", "skipped": True}
    # Only refresh products older than 18h since last sync
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=18)).isoformat()
    products = await db.products.find(
        {"ae_item_id": {"$exists": True, "$ne": None},
         "status": "active",
         "$or": [{"ae_last_sync_at": {"$lt": cutoff}},
                 {"ae_last_sync_at": {"$exists": False}}]},
        {"_id": 0, "id": 1, "site_id": 1, "ae_item_id": 1,
         "price": 1, "stock": 1, "name": 1},
    ).to_list(100)
    if not products:
        return {"ok": True, "refreshed": 0, "reason": "no_stale_products"}

    refreshed = 0
    drifted = 0
    paused = 0
    try:
        from routes.aliexpress import refresh_one_product
    except Exception as e:
        logger.warning(f"[cron_aliexpress] cannot import refresh_one_product: {e}")
        return {"ok": False, "error": str(e)[:160]}

    for p in products:
        try:
            res = await refresh_one_product(p["id"])
            if res and res.get("ok"):
                refreshed += 1
                if res.get("price_drift_pct", 0) >= 5:
                    drifted += 1
                if res.get("paused_for_oos"):
                    paused += 1
        except Exception as e:
            logger.warning(f"[cron_aliexpress] product {p.get('id')} failed: {e}")

    if drifted or paused:
        await db.admin_notifications.insert_one({
            "id": f"cron-ali-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M')}",
            "type": "aliexpress_refresh",
            "severity": "warn" if (drifted or paused) else "info",
            "message": f"AliExpress auto-refresh : {refreshed}/{len(products)} mis à jour, "
                       f"{drifted} drift prix >=5%, {paused} pausés pour OOS.",
            "created_at": _now_iso(),
        })
    return {"ok": True, "refreshed": refreshed, "total": len(products),
            "drifted": drifted, "paused": paused}
