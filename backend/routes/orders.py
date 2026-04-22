"""Orders (site-level listing + admin ops center)."""
import csv
import io
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from deps import db, get_current_user, require_admin, _check_site_access

router = APIRouter()

ALLOWED_ORDER_STATUSES = [
    "pending_payment", "paid", "shipped", "delivered", "cancelled", "refunded"
]

STATUS_TRANSITIONS = {
    "pending_payment": ["paid", "cancelled"],
    "paid": ["shipped", "refunded", "cancelled"],
    "shipped": ["delivered", "refunded"],
    "delivered": ["refunded"],
    "cancelled": [],
    "refunded": [],
}


class OrderStatusUpdate(BaseModel):
    status: str
    note: Optional[str] = ""
    tracking_number: Optional[str] = ""
    carrier: Optional[str] = ""


@router.get("/sites/{site_id}/orders")
async def list_orders(site_id: str, user: dict = Depends(get_current_user)):
    await _check_site_access(site_id, user)
    items = await db.orders.find({"site_id": site_id}, {"_id": 0, "_meta_ip": 0}).sort("created_at", -1).to_list(500)
    return items


@router.get("/sites/{site_id}/fulfillment")
async def fulfillment_summary(site_id: str, user: dict = Depends(get_current_user)):
    """Per-order supplier/tracking summary. Each line = one customer order
    joined with its CJ/AE mapping to show fulfillment status at a glance."""
    await _check_site_access(site_id, user)
    orders = await db.orders.find(
        {"site_id": site_id, "status": {"$in": ["paid", "shipped", "delivered"]}},
        {"_id": 0, "id": 1, "order_number": 1, "status": 1, "total": 1, "currency": 1,
         "created_at": 1, "tracking_number": 1, "carrier": 1, "customer": 1,
         "supplier_order_id": 1, "supplier_provider": 1},
    ).sort("created_at", -1).limit(200).to_list(200)

    # Fetch mappings in bulk
    order_ids = [o["id"] for o in orders]
    mappings_raw = await db.order_mappings.find(
        {"customer_order_id": {"$in": order_ids}}, {"_id": 0}
    ).to_list(400)
    mapping_by_order = {}
    for m in mappings_raw:
        mapping_by_order.setdefault(m["customer_order_id"], []).append(m)

    result = []
    counters = {"pending_supplier": 0, "placed": 0, "shipped": 0, "delivered": 0, "error": 0}
    for o in orders:
        maps = mapping_by_order.get(o["id"]) or []
        has_error = any(m.get("status") == "supplier_error" for m in maps)
        if not maps and o.get("status") == "paid":
            state = "pending_supplier"
        elif has_error:
            state = "error"
        elif any(m.get("status") == "delivered" for m in maps):
            state = "delivered"
        elif any(m.get("status") == "shipped" for m in maps):
            state = "shipped"
        elif any(m.get("status") == "placed" for m in maps):
            state = "placed"
        else:
            state = "pending_supplier"
        counters[state] = counters.get(state, 0) + 1
        result.append({
            **o,
            "fulfillment_state": state,
            "supplier_mappings": [
                {"provider": m.get("provider"),
                 "supplier_order_id": m.get("cj_order_id") or m.get("aliexpress_order_id"),
                 "status": m.get("status"),
                 "tracking_number": m.get("tracking_number"),
                 "carrier": m.get("carrier"),
                 "last_sync_at": m.get("last_sync_at")}
                for m in maps
            ],
        })
    return {"counters": counters, "total": len(result), "orders": result}


@router.post("/sites/{site_id}/orders/{order_id}/supplier-retry")
async def retry_supplier_order(site_id: str, order_id: str, user: dict = Depends(get_current_user)):
    """Manual retry of supplier auto-fulfillment (CJ or AE). Used when the auto-placement
    failed at webhook time — Concepteur can re-attempt from the fulfillment dashboard."""
    await _check_site_access(site_id, user)
    order = await db.orders.find_one({"id": order_id, "site_id": site_id}, {"_id": 0})
    if not order:
        raise HTTPException(404, "Order not found")
    if order.get("status") not in ("paid", "shipped"):
        raise HTTPException(400, "Order must be paid first")

    # Detect providers present in this order's items
    providers = set()
    for item in order.get("items") or []:
        p = await db.products.find_one({"id": item.get("product_id")}, {"_id": 0, "source": 1})
        if p and (p.get("source") or {}).get("provider"):
            providers.add((p["source"] or {})["provider"])

    results = {}
    if "cj" in providers:
        from routes.sourcing import auto_place_cj_order
        results["cj"] = await auto_place_cj_order(order_id)
    if "aliexpress" in providers:
        from routes.aliexpress import auto_place_aliexpress_order
        results["aliexpress"] = await auto_place_aliexpress_order(order)
    if not results:
        raise HTTPException(400, "No CJ or AliExpress items in this order.")
    return {"ok": True, "retried": results}



@router.get("/admin/orders")
async def admin_list_orders(
    status: Optional[str] = None,
    site_id: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    admin: dict = Depends(require_admin),
):
    query = {}
    if status:
        query["status"] = status
    if site_id:
        query["site_id"] = site_id
    if q:
        q_clean = q.strip()
        query["$or"] = [
            {"order_number": {"$regex": q_clean, "$options": "i"}},
            {"customer.email": {"$regex": q_clean, "$options": "i"}},
            {"customer.name": {"$regex": q_clean, "$options": "i"}},
        ]
    total = await db.orders.count_documents(query)
    items = (
        await db.orders.find(query, {"_id": 0, "_meta_ip": 0})
        .sort("created_at", -1)
        .skip(max(0, offset))
        .limit(min(max(1, limit), 500))
        .to_list(500)
    )
    by_site = {}
    for order in items:
        sid = order["site_id"]
        if sid not in by_site:
            prods = await db.products.find(
                {"site_id": sid},
                {"_id": 0, "id": 1, "supplier_url": 1}
            ).to_list(500)
            by_site[sid] = {p["id"]: p.get("supplier_url") or "" for p in prods}
        for it in order.get("items", []):
            it["supplier_url"] = by_site[sid].get(it["product_id"], "")
    return {"total": total, "items": items}


@router.get("/admin/orders/stats")
async def admin_orders_stats(admin: dict = Depends(require_admin)):
    pipeline = [
        {"$group": {
            "_id": "$status",
            "count": {"$sum": 1},
            "revenue": {"$sum": "$total"},
        }},
    ]
    by_status = {s: {"count": 0, "revenue": 0.0} for s in ALLOWED_ORDER_STATUSES}
    async for row in db.orders.aggregate(pipeline):
        by_status[row["_id"]] = {"count": row["count"], "revenue": round(row["revenue"], 2)}
    total_count = sum(v["count"] for v in by_status.values())
    total_revenue = sum(v["revenue"] for v in by_status.values())
    return {
        "by_status": by_status,
        "total_count": total_count,
        "total_revenue": round(total_revenue, 2),
    }


@router.patch("/admin/orders/{order_id}")
async def admin_update_order_status(
    order_id: str,
    data: OrderStatusUpdate,
    admin: dict = Depends(require_admin),
):
    order = await db.orders.find_one({"id": order_id}, {"_id": 0, "_meta_ip": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Commande introuvable")
    new_status = data.status
    if new_status not in ALLOWED_ORDER_STATUSES:
        raise HTTPException(status_code=400, detail="Statut invalide")
    current = order["status"]
    if new_status != current and new_status not in STATUS_TRANSITIONS.get(current, []):
        raise HTTPException(
            status_code=400,
            detail=f"Transition interdite : {current} → {new_status}"
        )
    now = datetime.now(timezone.utc).isoformat()
    history_entry = {
        "from": current,
        "to": new_status,
        "at": now,
        "by": admin["id"],
        "note": data.note or "",
    }
    set_fields = {"status": new_status, "updated_at": now}
    if data.tracking_number:
        set_fields["tracking_number"] = data.tracking_number
    if data.carrier:
        set_fields["carrier"] = data.carrier
    await db.orders.update_one(
        {"id": order_id},
        {
            "$set": set_fields,
            "$push": {"status_history": history_entry},
        },
    )
    # Send shipping update email on transition → shipped if we have a tracking number
    if new_status == "shipped" and data.tracking_number:
        try:
            from routes.emails import send_shipping_update
            refreshed = await db.orders.find_one({"id": order_id}, {"_id": 0})
            if refreshed and refreshed.get("site_id"):
                site = await db.sites.find_one({"id": refreshed["site_id"]}, {"_id": 0})
                if site:
                    await send_shipping_update(refreshed, site,
                                               data.tracking_number, data.carrier or "")
        except Exception:
            import logging
            logging.getLogger("conceptfactory").exception("Failed to send shipping email")
    return await db.orders.find_one({"id": order_id}, {"_id": 0, "_meta_ip": 0})


@router.get("/admin/orders/export.csv")
async def admin_orders_csv(
    status: Optional[str] = None,
    site_id: Optional[str] = None,
    admin: dict = Depends(require_admin),
):
    """Streaming CSV export — O(1) memory regardless of volume."""
    query = {}
    if status:
        query["status"] = status
    if site_id:
        query["site_id"] = site_id

    COLUMNS = [
        "order_number", "created_at", "status", "site_name",
        "customer_name", "customer_email", "customer_phone",
        "country", "postal_code", "city", "address",
        "items_count", "subtotal", "shipping", "total", "currency", "language",
    ]

    async def row_generator():
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(COLUMNS)
        yield buf.getvalue()
        buf.seek(0)
        buf.truncate(0)

        cursor = db.orders.find(query, {"_id": 0, "_meta_ip": 0}).sort("created_at", -1)
        async for o in cursor:
            items_count = sum(it.get("quantity", 0) for it in o.get("items", []))
            addr = o.get("shipping_address", {})
            cust = o.get("customer", {})
            writer.writerow([
                o.get("order_number", ""), o.get("created_at", ""), o.get("status", ""),
                o.get("site_name", ""),
                cust.get("name", ""), cust.get("email", ""), cust.get("phone", ""),
                addr.get("country_code", ""), addr.get("postal_code", ""),
                addr.get("city", ""), addr.get("line1", ""),
                items_count, o.get("subtotal", 0), o.get("shipping_fee", 0),
                o.get("total", 0), o.get("currency", "EUR"), o.get("language", ""),
            ])
            yield buf.getvalue()
            buf.seek(0)
            buf.truncate(0)

    return StreamingResponse(
        row_generator(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="orders.csv"'},
    )
