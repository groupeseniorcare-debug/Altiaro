"""
Chantier 7 — Dashboard Analytics interne post-validation.

Trois responsabilités :
  1. `POST /api/public/sites/{id}/track`       → ingestion des events storefront (public, no auth)
  2. `GET  /api/sites/{id}/analytics/overview` → KPIs + funnel + revenue + daily (concepteur/admin)
  3. `GET  /api/sites/{id}/analytics/funnel`   → funnel détaillé avec drop-off
  4. `GET  /api/sites/{id}/analytics/live`     → sessions actives (5 min)

Collection : `db.storefront_events` (cf. docstring POST /track).
RGPD : on ne stocke JAMAIS l'IP brute — seulement un `ip_hash` sha256(ip + sel journalier).
"""
from __future__ import annotations
import hashlib
import logging
import os
import time
import json
import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status as http_status
from pydantic import BaseModel, Field

from deps import db, get_current_user, _check_site_access

logger = logging.getLogger(__name__)
router = APIRouter()

# ─── Config ──────────────────────────────────────────────────────────────────
ALLOWED_EVENTS = {
    "page_view",
    "product_view",
    "add_to_cart",
    "begin_checkout",
    "purchase",
}
RATE_LIMIT_WINDOW_SEC = 60
RATE_LIMIT_MAX = 60
IP_SALT_BASE = os.environ.get("IP_HASH_SALT", "altiaro-2026")  # non-secret OK, rotating

# In-memory sliding-window per IP. Stateless supervisord restart resets, suffisant
# pour un MVP (si besoin de distributed, passer sur Redis plus tard).
_rl_bucket: dict[str, list[float]] = defaultdict(list)


def _client_ip(request: Request) -> str:
    """Best-effort client IP (behind K8s ingress / cloudflare)."""
    fwd = request.headers.get("x-forwarded-for") or ""
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "0.0.0.0"


def _rate_limited(ip: str) -> bool:
    now = time.time()
    cutoff = now - RATE_LIMIT_WINDOW_SEC
    bucket = _rl_bucket[ip]
    # drop stale timestamps
    while bucket and bucket[0] < cutoff:
        bucket.pop(0)
    if len(bucket) >= RATE_LIMIT_MAX:
        return True
    bucket.append(now)
    return False


def _ip_hash(ip: str) -> str:
    """sha256(ip + salt-du-jour). Rotation journalière → re-identification
    impossible entre deux jours."""
    daily = datetime.now(timezone.utc).strftime("%Y%m%d")
    salt = f"{IP_SALT_BASE}:{daily}"
    return hashlib.sha256(f"{ip}|{salt}".encode("utf-8")).hexdigest()[:32]


# ─── Ingestion publique ──────────────────────────────────────────────────────

class TrackInput(BaseModel):
    event: str = Field(..., description="page_view | product_view | add_to_cart | begin_checkout | purchase")
    session_id: str = Field(..., min_length=6, max_length=80)
    product_id: Optional[str] = None
    value: Optional[float] = None
    currency: Optional[str] = None
    path: Optional[str] = None
    referrer: Optional[str] = None
    country: Optional[str] = None
    lang: Optional[str] = None
    meta: Optional[dict] = None


@router.post("/public/sites/{site_id}/track", status_code=http_status.HTTP_202_ACCEPTED)
async def track_event(site_id: str, request: Request):
    """Endpoint public (pas d'auth). Ingère un event storefront.

    Rate-limit : `RATE_LIMIT_MAX` req/IP sur `RATE_LIMIT_WINDOW_SEC` secondes → 429.
    Site inconnu → 404. Event inconnu → 400.
    Aucune IP brute stockée (hash journalier → RGPD friendly).

    2026-05-03 : accepte aussi les bodies envoyés avec Content-Type
    `text/plain` (et autres) pour permettre aux storefronts en custom domain
    d'éviter le pré-flight CORS — l'infra Cloudflare/Emergent en front du pod
    intercepte les pré-flights et renvoie `ACAO=*` qui casse `credentials`.
    Avec `text/plain` (CORS-safelisted), aucun pré-flight n'est émis.
    """
    ip = _client_ip(request)
    if _rate_limited(ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    # Parse body tolerantly (accept JSON via any Content-Type).
    try:
        raw = await request.body()
        if not raw:
            raise HTTPException(status_code=400, detail="Empty body")
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError) as e:
            raise HTTPException(status_code=400, detail=f"Invalid JSON body: {e}")
        body = TrackInput(**payload)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid payload: {e}")

    if body.event not in ALLOWED_EVENTS:
        raise HTTPException(status_code=400, detail=f"Unknown event '{body.event}'")

    # Validate site_id exists
    site = await db.sites.find_one({"id": site_id}, {"_id": 0, "id": 1, "status": 1})
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    doc = {
        "_id": str(uuid.uuid4()),
        "site_id": site_id,
        "event": body.event,
        "session_id": body.session_id,
        "product_id": body.product_id,
        "value": float(body.value) if body.value is not None else None,
        "currency": (body.currency or "EUR").upper()[:3] if body.currency else None,
        "path": (body.path or "")[:500] or None,
        "referrer": (body.referrer or "")[:500] or None,
        "country": (body.country or "")[:3].upper() or None,
        "lang": (body.lang or "")[:5].lower() or None,
        "user_agent": (request.headers.get("user-agent") or "")[:300],
        "ip_hash": _ip_hash(ip),
        "created_at": datetime.now(timezone.utc),
        "meta": body.meta or {},
    }
    try:
        await db.storefront_events.insert_one(doc)
    except Exception:
        logger.exception("track_event insert failed")
        # On ne remonte PAS d'erreur au client pour ne pas casser l'expérience
        # visiteur. Le tracking est best-effort.
    return {"ok": True}


# ─── Helpers lecture (aggregate pipelines) ──────────────────────────────────

def _range_to_delta(r: str) -> timedelta:
    return {
        "7d": timedelta(days=7),
        "30d": timedelta(days=30),
        "90d": timedelta(days=90),
    }.get(r, timedelta(days=30))


async def _aggregate_overview(site_id: str, since: datetime, until: datetime) -> dict:
    """Agrégation principale : un seul pipeline pour sessions + funnel + revenue."""
    match = {"site_id": site_id, "created_at": {"$gte": since, "$lt": until}}

    # 1) Totaux par event + valeur purchase
    by_event_cursor = db.storefront_events.aggregate([
        {"$match": match},
        {"$group": {
            "_id": "$event",
            "count": {"$sum": 1},
            "sum_value": {"$sum": {"$ifNull": ["$value", 0]}},
            "unique_sessions": {"$addToSet": "$session_id"},
        }},
    ])
    by_event: dict[str, dict] = {}
    all_sessions: set = set()
    async for row in by_event_cursor:
        ev = row["_id"]
        sess = set(row.get("unique_sessions") or [])
        all_sessions |= sess
        by_event[ev] = {
            "count": int(row.get("count") or 0),
            "sum_value": float(row.get("sum_value") or 0.0),
            "unique_sessions": len(sess),
        }

    page_views = by_event.get("page_view", {}).get("count", 0)
    product_views = by_event.get("product_view", {}).get("count", 0)
    atc = by_event.get("add_to_cart", {}).get("count", 0)
    checkout = by_event.get("begin_checkout", {}).get("count", 0)
    purchases = by_event.get("purchase", {}).get("count", 0)
    purchase_revenue = by_event.get("purchase", {}).get("sum_value", 0.0)

    conversion_rate_pct = (purchases / len(all_sessions) * 100.0) if all_sessions else 0.0

    # 2) Séries daily (sessions + revenue + purchases par jour UTC)
    daily_cursor = db.storefront_events.aggregate([
        {"$match": match},
        {"$group": {
            "_id": {
                "d": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
                "event": "$event",
            },
            "count": {"$sum": 1},
            "sum_value": {"$sum": {"$ifNull": ["$value", 0]}},
            "sessions": {"$addToSet": "$session_id"},
        }},
    ])
    daily_map: dict[str, dict] = {}
    async for row in daily_cursor:
        d = row["_id"]["d"]
        ev = row["_id"]["event"]
        rec = daily_map.setdefault(d, {"date": d, "sessions_set": set(), "purchases": 0, "revenue": 0.0})
        rec["sessions_set"] |= set(row.get("sessions") or [])
        if ev == "purchase":
            rec["purchases"] += int(row.get("count") or 0)
            rec["revenue"] += float(row.get("sum_value") or 0.0)
    daily = sorted(
        [{
            "date": r["date"],
            "sessions": len(r["sessions_set"]),
            "purchases": r["purchases"],
            "revenue": round(r["revenue"], 2),
        } for r in daily_map.values()],
        key=lambda x: x["date"],
    )

    # 3) Top products (par vues + achats)
    top_cursor = db.storefront_events.aggregate([
        {"$match": {**match, "event": {"$in": ["product_view", "purchase"]},
                    "product_id": {"$ne": None}}},
        {"$group": {
            "_id": {"product_id": "$product_id", "event": "$event"},
            "count": {"$sum": 1},
        }},
    ])
    prod_counts: dict[str, dict] = {}
    async for row in top_cursor:
        pid = row["_id"]["product_id"]
        ev = row["_id"]["event"]
        rec = prod_counts.setdefault(pid, {"product_id": pid, "views": 0, "purchases": 0})
        if ev == "product_view":
            rec["views"] += int(row.get("count") or 0)
        elif ev == "purchase":
            rec["purchases"] += int(row.get("count") or 0)
    top_products = sorted(prod_counts.values(), key=lambda x: (-x["views"], -x["purchases"]))[:5]
    # Enrichir avec le nom + image
    if top_products:
        pids = [p["product_id"] for p in top_products]
        prods = await db.products.find(
            {"id": {"$in": pids}},
            {"_id": 0, "id": 1, "name": 1, "image": 1, "price": 1},
        ).to_list(length=len(pids))
        prod_map = {p["id"]: p for p in prods}
        for p in top_products:
            src = prod_map.get(p["product_id"]) or {}
            nm = src.get("name")
            if isinstance(nm, dict):
                nm = nm.get("fr") or next(iter(nm.values()), "")
            p["name"] = nm or "—"
            p["image"] = src.get("image") or None
            p["price"] = src.get("price")

    # 4) Top countries (par sessions uniques)
    country_cursor = db.storefront_events.aggregate([
        {"$match": {**match, "country": {"$ne": None}}},
        {"$group": {"_id": "$country", "sessions": {"$addToSet": "$session_id"}}},
        {"$project": {"country": "$_id", "sessions": {"$size": "$sessions"}, "_id": 0}},
        {"$sort": {"sessions": -1}},
        {"$limit": 10},
    ])
    top_countries = [row async for row in country_cursor]

    # 5) AOV + orders_count (croisé avec db.orders pour chiffre "fiscal")
    orders_pipe = db.orders.aggregate([
        {"$match": {"site_id": site_id, "status": {"$in": ["paid", "fulfilled", "shipped", "delivered"]},
                    "created_at": {"$gte": since, "$lt": until}}},
        {"$group": {
            "_id": None,
            "count": {"$sum": 1},
            "total": {"$sum": {"$ifNull": ["$total", 0]}},
        }},
    ])
    orders_row = None
    async for r in orders_pipe:
        orders_row = r
        break
    real_orders = int((orders_row or {}).get("count") or 0)
    real_revenue = float((orders_row or {}).get("total") or 0.0)

    # On préfère le revenu "orders" (validé) si dispo, sinon on retombe sur les
    # events "purchase" (remontés par le storefront, pré-validation paiement).
    final_revenue = real_revenue if real_orders > 0 else purchase_revenue
    final_orders = real_orders if real_orders > 0 else purchases
    aov = (final_revenue / final_orders) if final_orders else 0.0

    return {
        "visitors": {
            "unique_sessions": len(all_sessions),
            "page_views": page_views,
        },
        "funnel": {
            "product_view": product_views,
            "add_to_cart": atc,
            "begin_checkout": checkout,
            "purchase": purchases,
            "conversion_rate_pct": round(conversion_rate_pct, 2),
        },
        "revenue": {
            "total": round(final_revenue, 2),
            "currency": "EUR",
            "orders_count": final_orders,
            "aov": round(aov, 2),
            "source": "orders" if real_orders > 0 else "events",
        },
        "top_products": top_products,
        "top_countries": top_countries,
        "daily": daily,
    }


# ─── Endpoints privés (concepteur / admin) ───────────────────────────────────

VALID_RANGES = {"7d", "30d", "90d"}


@router.get("/sites/{site_id}/analytics/overview")
async def analytics_overview(
    site_id: str,
    range: str = "30d",
    user: dict = Depends(get_current_user),
) -> dict:
    await _check_site_access(site_id, user)
    if range not in VALID_RANGES:
        raise HTTPException(400, f"range must be one of {sorted(VALID_RANGES)}")
    delta = _range_to_delta(range)
    now = datetime.now(timezone.utc)
    since = now - delta
    previous_since = since - delta

    # Current period
    current = await _aggregate_overview(site_id, since, now)

    # Previous period (comparaison %)
    previous = await _aggregate_overview(site_id, previous_since, since)

    def _pct_change(a: float, b: float) -> Optional[float]:
        if b == 0:
            return None if a == 0 else 100.0
        return round(((a - b) / b) * 100, 1)

    variations = {
        "visitors_pct":    _pct_change(current["visitors"]["unique_sessions"], previous["visitors"]["unique_sessions"]),
        "conversion_pct":  _pct_change(current["funnel"]["conversion_rate_pct"], previous["funnel"]["conversion_rate_pct"]),
        "revenue_pct":     _pct_change(current["revenue"]["total"], previous["revenue"]["total"]),
        "orders_pct":      _pct_change(current["revenue"]["orders_count"], previous["revenue"]["orders_count"]),
    }

    return {
        "site_id": site_id,
        "range": range,
        "since": since.isoformat(),
        "until": now.isoformat(),
        **current,
        "vs_previous": variations,
    }


@router.get("/sites/{site_id}/analytics/funnel")
async def analytics_funnel(
    site_id: str,
    range: str = "30d",
    user: dict = Depends(get_current_user),
) -> dict:
    await _check_site_access(site_id, user)
    if range not in VALID_RANGES:
        raise HTTPException(400, f"range must be one of {sorted(VALID_RANGES)}")
    delta = _range_to_delta(range)
    now = datetime.now(timezone.utc)
    since = now - delta

    match = {"site_id": site_id, "created_at": {"$gte": since, "$lt": now}}
    cursor = db.storefront_events.aggregate([
        {"$match": match},
        {"$group": {"_id": "$event", "count": {"$sum": 1},
                    "sessions": {"$addToSet": "$session_id"}}},
    ])
    totals = {"product_view": 0, "add_to_cart": 0, "begin_checkout": 0, "purchase": 0}
    sess: dict[str, int] = {}
    async for row in cursor:
        ev = row["_id"]
        if ev in totals:
            totals[ev] = int(row["count"])
            sess[ev] = len(row.get("sessions") or [])

    # Drop-off ordonné : product_view → add_to_cart → begin_checkout → purchase
    order = ["product_view", "add_to_cart", "begin_checkout", "purchase"]
    steps = []
    prev_count = None
    for ev in order:
        count = totals.get(ev, 0)
        drop_off_pct = None
        if prev_count and prev_count > 0:
            drop_off_pct = round((1 - count / prev_count) * 100, 1)
        steps.append({
            "event": ev,
            "count": count,
            "sessions": sess.get(ev, 0),
            "drop_off_pct": drop_off_pct,
        })
        prev_count = count
    return {
        "site_id": site_id,
        "range": range,
        "since": since.isoformat(),
        "until": now.isoformat(),
        "steps": steps,
    }


@router.get("/sites/{site_id}/analytics/live")
async def analytics_live(
    site_id: str,
    user: dict = Depends(get_current_user),
) -> dict:
    """Sessions actives sur les 5 dernières minutes. Polling 15s côté UI."""
    await _check_site_access(site_id, user)
    now = datetime.now(timezone.utc)
    since = now - timedelta(minutes=5)
    sessions = await db.storefront_events.distinct(
        "session_id",
        {"site_id": site_id, "created_at": {"$gte": since}},
    )
    return {
        "site_id": site_id,
        "active_sessions": len(sessions),
        "window_minutes": 5,
        "checked_at": now.isoformat(),
    }

@router.get("/sites/{site_id}/analytics/products")
async def analytics_products(
    site_id: str,
    range: str = "30d",
    user: dict = Depends(get_current_user),
) -> dict:
    """Phase 5 — Tableau Produits du dashboard post-validation.
    Retourne pour chaque produit du site : title (langue FR par défaut),
    image, vues, achats, CA sur la période.
    """
    await _check_site_access(site_id, user)
    if range not in VALID_RANGES:
        raise HTTPException(400, f"range must be one of {sorted(VALID_RANGES)}")
    delta = _range_to_delta(range)
    now = datetime.now(timezone.utc)
    since = now - delta

    # 1) Liste des produits du site (toujours renvoyée, même sans events)
    products: list[dict] = []
    async for p in db.products.find(
        {"site_id": site_id},
        {
            "_id": 0, "id": 1, "name": 1, "images": 1, "primary_image": 1,
            "price": 1, "stock": 1, "cost_price_ht": 1, "created_at": 1,
        },
    ):
        # Résout le titre FR (fallback EN puis première valeur)
        name = p.get("name")
        if isinstance(name, dict):
            title = name.get("fr") or name.get("en") or next(iter(name.values()), "")
        else:
            title = str(name or "")
        image = ""
        imgs = p.get("images") or []
        if isinstance(imgs, list) and imgs:
            image = imgs[0] if isinstance(imgs[0], str) else (imgs[0].get("url") or "")
        if not image:
            image = p.get("primary_image") or ""
        products.append({
            "product_id": p["id"],
            "title": title,
            "image": image,
            "price": float(p.get("price") or 0),
            "cost_ht": float(p.get("cost_price_ht") or 0),
            "stock": p.get("stock"),
            "views": 0,
            "purchases": 0,
            "revenue": 0.0,
        })

    # 2) Agrégation par product_id sur storefront_events de la période
    pipeline = [
        {"$match": {
            "site_id": site_id,
            "created_at": {"$gte": since, "$lt": now},
            "product_id": {"$ne": None},
            "event": {"$in": ["product_view", "purchase"]},
        }},
        {"$group": {
            "_id": {"pid": "$product_id", "event": "$event"},
            "count": {"$sum": 1},
            "revenue": {"$sum": {"$ifNull": ["$value", 0]}},
        }},
    ]
    stats_by_pid: dict[str, dict] = {}
    async for row in db.storefront_events.aggregate(pipeline):
        pid = row["_id"]["pid"]
        ev = row["_id"]["event"]
        stats = stats_by_pid.setdefault(pid, {"views": 0, "purchases": 0, "revenue": 0.0})
        if ev == "product_view":
            stats["views"] = int(row["count"])
        elif ev == "purchase":
            stats["purchases"] = int(row["count"])
            stats["revenue"] = round(float(row.get("revenue") or 0.0), 2)

    # 3) Merge & tri (CA desc, puis achats, puis vues)
    for p in products:
        s = stats_by_pid.get(p["product_id"])
        if s:
            p["views"] = s["views"]
            p["purchases"] = s["purchases"]
            p["revenue"] = s["revenue"]
    products.sort(key=lambda x: (-x["revenue"], -x["purchases"], -x["views"]))

    return {
        "site_id": site_id,
        "range": range,
        "since": since.isoformat(),
        "until": now.isoformat(),
        "products": products,
        "total_count": len(products),
    }

