"""AliExpress Weekly Deals Watcher — scanne les produits AliExpress des
niches actives de chaque site et détecte ceux dont le prix a chuté de
≥ 20 % cette semaine. Crée une notification dans le cockpit pour que
le Concepteur puisse l'importer en 1 clic.

Stratégie pragmatique :
- On utilise les keywords de la niche du site + sa category dominante
  pour construire ~3 requêtes de scan.
- Pour chaque produit retourné, on compare au prix de la semaine dernière
  (stocké dans `ae_deals_history` par `item_id`).
- Un produit « deal » = drop ≥ 20 % avec ≥ 500 commandes historiques.
- Ces deals sont rangés dans `db.ae_deals[{site_id, item_id, ...}]` avec
  un flag `dismissed` / `imported` pour l'UX cockpit.

Entrypoints :
- POST /api/sites/{id}/deals/scan                     → trigger manuel
- GET  /api/sites/{id}/deals                          → liste deals actifs
- POST /api/sites/{id}/deals/{item_id}/dismiss        → mark seen
"""
from __future__ import annotations
import logging
import re
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from deps import db, get_current_user
from routes.aliexpress import _signed_post, SYNC_API_URL, _get_platform_settings

router = APIRouter()
logger = logging.getLogger("conceptfactory.ae_deals")

MIN_DROP_PCT = 20.0
MIN_ORDERS = 500


def _parse_orders(orders_raw: str) -> int:
    """AliExpress renvoie `"10,000+"`, `"4,000+"`, `"500"` — on parse."""
    if not orders_raw:
        return 0
    s = str(orders_raw).replace(",", "").replace("+", "").strip()
    try:
        return int(s)
    except ValueError:
        return 0


def _parse_price_eur(p: dict) -> Optional[float]:
    """Produit AE : `targetSalePrice` en EUR (priorisé) ou `salePriceFormat`."""
    tsp = p.get("targetSalePrice")
    if tsp:
        try:
            return float(tsp)
        except (TypeError, ValueError):
            pass
    sf = p.get("salePriceFormat") or ""
    # "4,69€" → 4.69
    m = re.search(r"([\d.,]+)", str(sf).replace(" ", ""))
    if m:
        try:
            return float(m.group(1).replace(",", "."))
        except ValueError:
            return None
    return None


def _build_queries(site: dict) -> list[str]:
    """Keywords to scan — derived from site niche / category / design."""
    queries: list[str] = []
    niche = site.get("niche") or ""
    if niche:
        queries.append(niche)
    # category dominant from products
    # (caller will fetch products if needed)
    return queries or ["silver economy", "senior comfort"]


async def _search_ae(keyword: str, page_size: int = 20) -> list[dict]:
    """Stateless wrapper — uses platform token. Returns product list or []."""
    biz = {
        "method": "aliexpress.ds.text.search",
        "keyWord": keyword,
        "pageIndex": "1",
        "pageSize": str(min(page_size, 40)),
        "local": "en",
        "countryCode": "FR",
        "currency": "EUR",
        "sortBy": "orders,desc",
    }
    try:
        resp = await _signed_post(SYNC_API_URL, biz, site_id=None)
    except Exception:
        logger.exception("[ae_deals] search failed")
        return []
    try:
        data = resp.get("aliexpress_ds_text_search_response") or {}
        pdata = (data.get("data") or {}).get("products") or {}
        items = pdata.get("selection_search_product") or []
        return items if isinstance(items, list) else []
    except Exception:
        logger.exception("[ae_deals] parse failed")
        return []


async def _scan_site(site: dict) -> dict:
    """Scan one site's keywords, compute price drops, store deals."""
    now = datetime.now(timezone.utc)
    site_id = site["id"]
    niche = site.get("niche") or ""

    # 1. Build queries : niche + top product categories
    queries = set(_build_queries(site))
    products = await db.products.find(
        {"site_id": site_id, "status": "active"},
        {"_id": 0, "name": 1, "category": 1},
    ).limit(20).to_list(20)
    for p in products:
        cat = p.get("category")
        if cat:
            queries.add(str(cat))
    queries = list(queries)[:3]  # cap 3 queries

    scanned = 0
    deals_found = 0
    for q in queries:
        items = await _search_ae(q, page_size=20)
        scanned += len(items)
        for it in items:
            item_id = str(it.get("itemId") or "")
            if not item_id:
                continue
            price = _parse_price_eur(it)
            orders = _parse_orders(it.get("orders"))
            if price is None or orders < MIN_ORDERS:
                continue

            # Load last snapshot
            prev = await db.ae_deals_history.find_one(
                {"site_id": site_id, "item_id": item_id},
                {"_id": 0, "last_price_eur": 1, "min_price_eur": 1},
            )
            prev_price = (prev or {}).get("last_price_eur")
            min_price = (prev or {}).get("min_price_eur") or price

            await db.ae_deals_history.update_one(
                {"site_id": site_id, "item_id": item_id},
                {
                    "$set": {
                        "site_id": site_id,
                        "item_id": item_id,
                        "last_price_eur": price,
                        "last_seen_at": now.isoformat(),
                        "min_price_eur": min(min_price, price),
                    },
                },
                upsert=True,
            )

            if prev_price and prev_price > 0:
                drop_pct = round(((prev_price - price) / prev_price) * 100, 1)
                if drop_pct >= MIN_DROP_PCT:
                    deal = {
                        "site_id": site_id,
                        "item_id": item_id,
                        "title": it.get("title") or "",
                        "price_eur": price,
                        "previous_price_eur": prev_price,
                        "drop_pct": drop_pct,
                        "image": it.get("itemMainPic") or "",
                        "score": it.get("score") or "",
                        "orders": orders,
                        "keyword": q,
                        "item_url": "https:" + (it.get("itemUrl") or "") if it.get("itemUrl") else "",
                        "detected_at": now.isoformat(),
                        "status": "new",  # new | imported | dismissed
                        "niche": niche,
                    }
                    await db.ae_deals.update_one(
                        {"site_id": site_id, "item_id": item_id},
                        {"$set": deal},
                        upsert=True,
                    )
                    deals_found += 1

    # Store last scan meta on site
    await db.sites.update_one(
        {"id": site_id},
        {"$set": {
            "design.ae_deals.last_scan_at": now.isoformat(),
            "design.ae_deals.last_scan_queries": queries,
            "design.ae_deals.last_scan_scanned": scanned,
            "design.ae_deals.last_scan_deals": deals_found,
        }},
    )
    return {"site_id": site_id, "queries": queries, "scanned": scanned, "deals_found": deals_found}


async def scan_all_sites() -> dict:
    """Entry-point pour APScheduler — scanne tous les sites actifs."""
    pl = await _get_platform_settings()
    if not pl.get("connected") or not pl.get("access_token"):
        logger.warning("[ae_deals] platform not connected — skipping scan")
        return {"status": "not_connected", "ran": 0}
    cursor = db.sites.find(
        {"design.ae_deals.auto_enabled": {"$ne": False}},
        {"_id": 0, "id": 1, "name": 1, "niche": 1},
    )
    sites = await cursor.to_list(500)
    results = []
    for s in sites:
        try:
            r = await _scan_site(s)
            results.append(r)
        except Exception:
            logger.exception(f"[ae_deals] site {s['id']} scan crashed")
    return {"status": "done", "ran": len(results), "results": results[:20]}


# =====================================================================
# API Endpoints
# =====================================================================
@router.post("/sites/{site_id}/deals/scan")
async def scan_site_deals(site_id: str, user=Depends(get_current_user)):
    """Trigger manuel d'un scan (Concepteur)."""
    site = await db.sites.find_one({"id": site_id}, {"_id": 0})
    if not site:
        raise HTTPException(404, "Site introuvable")
    pl = await _get_platform_settings()
    if not pl.get("connected"):
        raise HTTPException(503, "AliExpress non connecté. Lance l'OAuth d'abord.")
    result = await _scan_site(site)
    return result


@router.get("/sites/{site_id}/deals")
async def list_site_deals(site_id: str, status: str = "new", user=Depends(get_current_user)):
    """Liste les deals détectés pour ce site. status: new|imported|dismissed|all."""
    site = await db.sites.find_one({"id": site_id}, {"_id": 0})
    if not site:
        raise HTTPException(404, "Site introuvable")
    q = {"site_id": site_id}
    if status != "all":
        q["status"] = status
    deals = await db.ae_deals.find(q, {"_id": 0}).sort("drop_pct", -1).limit(30).to_list(30)
    last_scan = (site.get("design") or {}).get("ae_deals") or {}
    return {"deals": deals, "last_scan": last_scan}


class DealUpdateInput(BaseModel):
    status: str  # imported | dismissed


@router.post("/sites/{site_id}/deals/{item_id}/status")
async def update_deal_status(site_id: str, item_id: str, body: DealUpdateInput, user=Depends(get_current_user)):
    if body.status not in {"imported", "dismissed", "new"}:
        raise HTTPException(400, "status invalide")
    res = await db.ae_deals.update_one(
        {"site_id": site_id, "item_id": item_id},
        {"$set": {"status": body.status, "updated_at": datetime.now(timezone.utc).isoformat()}},
    )
    if res.matched_count == 0:
        raise HTTPException(404, "Deal introuvable")
    return {"ok": True, "status": body.status}
