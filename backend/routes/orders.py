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


@router.get("/sites/{site_id}/orders")
async def list_orders(site_id: str, user: dict = Depends(get_current_user)):
    await _check_site_access(site_id, user)
    items = await db.orders.find({"site_id": site_id}, {"_id": 0, "_meta_ip": 0}).sort("created_at", -1).to_list(500)
    return items


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
    await db.orders.update_one(
        {"id": order_id},
        {
            "$set": {"status": new_status, "updated_at": now},
            "$push": {"status_history": history_entry},
        },
    )
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
