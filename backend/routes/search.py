"""Global search across sites, products, orders, niches (admin only)."""
import re
from typing import Optional

from fastapi import APIRouter, Depends

from deps import db, require_admin

router = APIRouter(prefix="/admin")


def _safe_regex(q: str) -> dict:
    """Turn free text into a case-insensitive regex filter safely escaped."""
    return {"$regex": re.escape(q), "$options": "i"}


@router.get("/search")
async def global_search(
    q: str = "",
    limit: int = 5,
    admin: dict = Depends(require_admin),
):
    """Multi-collection search. Returns up to `limit` matches per entity type."""
    q = (q or "").strip()
    if not q or len(q) < 2:
        return {
            "sites": [],
            "products": [],
            "orders": [],
            "niches": [],
            "users": [],
        }

    regex = _safe_regex(q)

    sites_task = db.sites.find(
        {"$or": [{"name": regex}, {"niche": regex}, {"domain": regex}]},
        {"_id": 0, "id": 1, "name": 1, "niche": 1, "domain": 1, "status": 1},
    ).sort("created_at", -1).limit(limit).to_list(limit)

    products_task = db.products.find(
        {"$or": [
            {"name.fr": regex}, {"name.en": regex},
            {"name.de": regex}, {"name.nl": regex},
            {"sku": regex},
        ]},
        {"_id": 0, "id": 1, "site_id": 1, "name": 1, "price": 1, "currency": 1, "images": 1, "status": 1},
    ).limit(limit).to_list(limit)

    orders_task = db.orders.find(
        {"$or": [
            {"order_number": regex},
            {"customer.email": regex},
            {"customer.name": regex},
        ]},
        {"_id": 0, "_meta_ip": 0, "status_history": 0, "items": 0},
    ).sort("created_at", -1).limit(limit).to_list(limit)

    niches_task = db.niches.find(
        {"$or": [{"name": regex}, {"slug": regex}, {"category": regex}]},
        {"_id": 0, "slug": 1, "name": 1, "emoji": 1, "category": 1, "ecf_score": 1, "rank": 1},
    ).limit(limit).to_list(limit)

    users_task = db.users.find(
        {"$or": [{"email": regex}, {"name": regex}]},
    ).limit(limit).to_list(limit)

    sites, products, orders, niches, users = (
        await sites_task, await products_task,
        await orders_task, await niches_task, await users_task,
    )

    users = [
        {
            "id": str(u["_id"]),
            "email": u["email"],
            "name": u.get("name", ""),
            "role": u.get("role", "operator"),
        }
        for u in users
    ]

    return {
        "sites": sites,
        "products": products,
        "orders": orders,
        "niches": niches,
        "users": users,
        "total": len(sites) + len(products) + len(orders) + len(niches) + len(users),
    }
