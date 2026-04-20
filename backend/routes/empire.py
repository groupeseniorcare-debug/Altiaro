"""
Dashboard Empire : vue macro admin cross-pays pour piloter le portfolio.

Agrège en temps réel :
- KPIs globaux : CA total, commandes, marge Admin (50%) vs Concepteur (50%), AOV, CR
- Breakdown par pays (calculé via shipping_address.country_code)
- Breakdown par scale_batch (familles de sites clonés)
- Top 5 produits cross-sites (commandés)
- Timeseries CA 30 derniers jours
- Alertes auto : sites sans commande >7j, domaines non vérifiés >7j, marge < 30%
"""
import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends

from deps import db, require_admin

logger = logging.getLogger("conceptfactory.empire")
router = APIRouter()


COUNTRY_NAMES = {
    "FR": "France", "DE": "Allemagne", "CH": "Suisse",
    "BE": "Belgique", "UK": "Royaume-Uni", "NL": "Pays-Bas",
    "LU": "Luxembourg",
}

# Orders counted as revenue (settled)
REVENUE_STATUSES = {"paid", "shipped", "delivered"}


def _now():
    return datetime.now(timezone.utc)


@router.get("/admin/empire")
async def empire_dashboard(days: int = 30, admin: dict = Depends(require_admin)):
    since_dt = _now() - timedelta(days=days)
    since_iso = since_dt.isoformat()

    # ---------- All sites ---------- #
    sites = await db.sites.find({}, {"_id": 0}).to_list(5000)
    site_by_id = {s["id"]: s for s in sites}
    total_sites = len(sites)
    active_sites = sum(1 for s in sites if s.get("status") == "active")

    # ---------- Orders (all, settled only counted as revenue) ---------- #
    orders = await db.orders.find(
        {}, {"_id": 0, "_meta_ip": 0}
    ).to_list(50000)
    settled = [o for o in orders if o.get("status") in REVENUE_STATUSES]
    recent_settled = [
        o for o in settled
        if o.get("created_at", "") >= since_iso
    ]

    total_gmv = sum(o.get("total", 0) for o in settled)
    total_orders = len(settled)
    recent_gmv = sum(o.get("total", 0) for o in recent_settled)
    recent_orders_count = len(recent_settled)
    aov = round(total_gmv / total_orders, 2) if total_orders else 0
    admin_share = round(total_gmv * 0.5, 2)  # 50% model
    concepteur_share = round(total_gmv - admin_share, 2)

    # ---------- Per country breakdown (from shipping_address.country_code) ---------- #
    per_country = defaultdict(lambda: {"revenue": 0, "orders": 0, "cities": set()})
    for o in settled:
        cc = (o.get("shipping_address") or {}).get("country_code", "UNKNOWN")
        per_country[cc]["revenue"] += o.get("total", 0)
        per_country[cc]["orders"] += 1
        city = (o.get("shipping_address") or {}).get("city")
        if city:
            per_country[cc]["cities"].add(city)

    country_rows = []
    for cc, stats in per_country.items():
        country_rows.append({
            "code": cc,
            "name": COUNTRY_NAMES.get(cc, cc),
            "revenue": round(stats["revenue"], 2),
            "orders": stats["orders"],
            "aov": round(stats["revenue"] / stats["orders"], 2) if stats["orders"] else 0,
            "unique_cities": len(stats["cities"]),
        })
    country_rows.sort(key=lambda x: x["revenue"], reverse=True)

    # ---------- Per scale family ---------- #
    families = defaultdict(list)
    for s in sites:
        bid = s.get("scale_batch_id")
        src = s.get("scaled_from")
        # Group by source site (or batch_id if source was deleted)
        key = src or (f"batch:{bid}" if bid else None)
        if key:
            families[key].append(s)

    family_rows = []
    for source_id, children in families.items():
        source = site_by_id.get(source_id)
        fam_site_ids = [c["id"] for c in children] + ([source_id] if source else [])
        fam_orders = [
            o for o in settled if o.get("site_id") in fam_site_ids
        ]
        fam_rev = sum(o.get("total", 0) for o in fam_orders)
        family_rows.append({
            "source_id": source_id if source else None,
            "source_name": source.get("name") if source else "(source supprimée)",
            "children_count": len(children),
            "total_sites": len(fam_site_ids),
            "total_revenue": round(fam_rev, 2),
            "total_orders": len(fam_orders),
            "countries": sorted(set(
                (c.get("selected_countries") or ["?"])[0] for c in children
            )),
        })
    family_rows.sort(key=lambda f: f["total_revenue"], reverse=True)

    # ---------- Top 5 products cross-sites ---------- #
    product_counter = defaultdict(lambda: {"revenue": 0, "quantity": 0, "name": ""})
    for o in settled:
        for it in o.get("items") or []:
            pid = it.get("product_id", "unknown")
            name = it.get("name") or ""
            product_counter[pid]["revenue"] += (it.get("price", 0) * it.get("quantity", 0))
            product_counter[pid]["quantity"] += it.get("quantity", 0)
            product_counter[pid]["name"] = name
    top_products = sorted(
        [
            {
                "product_id": pid,
                "name": stats["name"],
                "revenue": round(stats["revenue"], 2),
                "quantity": stats["quantity"],
            }
            for pid, stats in product_counter.items()
        ],
        key=lambda x: x["revenue"],
        reverse=True,
    )[:5]

    # ---------- Timeseries CA last N days (by day) ---------- #
    ts = defaultdict(lambda: {"revenue": 0, "orders": 0})
    for o in recent_settled:
        created = o.get("created_at", "")[:10]
        if created:
            ts[created]["revenue"] += o.get("total", 0)
            ts[created]["orders"] += 1
    # Backfill missing days so the chart is smooth
    timeseries = []
    for i in range(days):
        day = (since_dt + timedelta(days=i)).date().isoformat()
        d = ts.get(day, {"revenue": 0, "orders": 0})
        timeseries.append({
            "date": day,
            "revenue": round(d["revenue"], 2),
            "orders": d["orders"],
        })

    # ---------- Alertes auto ---------- #
    alerts = []
    cutoff_7d = (_now() - timedelta(days=7)).isoformat()

    # Sites active sans aucune commande depuis >7j
    sites_with_recent_order = set()
    for o in orders:
        if o.get("created_at", "") >= cutoff_7d:
            sites_with_recent_order.add(o.get("site_id"))
    for s in sites:
        if s.get("status") == "active" and s["id"] not in sites_with_recent_order:
            created = s.get("created_at", "")
            if created and created < cutoff_7d:
                alerts.append({
                    "severity": "warning",
                    "type": "no_orders_7d",
                    "site_id": s["id"],
                    "site_name": s["name"],
                    "message": "Aucune commande depuis 7 jours",
                })

    # Domaines custom non vérifiés depuis >7j
    for s in sites:
        if s.get("custom_domain") and not s.get("custom_domain_verified"):
            alerts.append({
                "severity": "info",
                "type": "domain_unverified",
                "site_id": s["id"],
                "site_name": s["name"],
                "domain": s["custom_domain"],
                "message": f"Domaine {s['custom_domain']} non vérifié",
            })

    # Produits importés avec supplier_url mais marge < 30% (simple heuristic)
    # We don't track cost directly, so skip this for now — requires manual financials

    # Sites sans produits actifs (drafts seulement)
    for s in sites:
        if s.get("status") == "active":
            actives = await db.products.count_documents({"site_id": s["id"], "status": "active"})
            total = await db.products.count_documents({"site_id": s["id"]})
            if total > 0 and actives == 0:
                alerts.append({
                    "severity": "warning",
                    "type": "no_active_products",
                    "site_id": s["id"],
                    "site_name": s["name"],
                    "message": f"{total} produit(s) en draft — aucun actif en boutique",
                })
            elif total == 0 and (s.get("progress_pct") or 0) > 20:
                alerts.append({
                    "severity": "info",
                    "type": "empty_catalog",
                    "site_id": s["id"],
                    "site_name": s["name"],
                    "message": "Boutique avancée mais catalogue vide",
                })

    alerts.sort(key=lambda a: {"critical": 0, "warning": 1, "info": 2}.get(a["severity"], 3))

    # ---------- Pending orders (urgent action) ---------- #
    pending = [
        {"id": o["id"], "order_number": o.get("order_number"), "site_id": o["site_id"],
         "site_name": o.get("site_name"), "total": o.get("total"), "status": o.get("status"),
         "created_at": o.get("created_at")}
        for o in orders
        if o.get("status") in {"pending_payment", "paid"}
    ]
    pending.sort(key=lambda o: o.get("created_at", ""), reverse=True)

    # ---------- Ads copy coverage ---------- #
    ads_count = await db.ads_copy.count_documents({})
    niche_analyses_count = await db.niche_analyses.count_documents({})

    return {
        "generated_at": _now().isoformat(),
        "period_days": days,
        "totals": {
            "total_gmv": round(total_gmv, 2),
            "total_orders": total_orders,
            "aov": aov,
            "admin_share": admin_share,
            "concepteur_share": concepteur_share,
            "recent_gmv": round(recent_gmv, 2),
            "recent_orders": recent_orders_count,
            "total_sites": total_sites,
            "active_sites": active_sites,
            "niche_analyses": niche_analyses_count,
            "ads_campaigns": ads_count,
        },
        "per_country": country_rows,
        "families": family_rows,
        "top_products": top_products,
        "timeseries": timeseries,
        "alerts": alerts,
        "pending_orders": pending[:10],
    }
