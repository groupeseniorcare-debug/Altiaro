"""Storefront-level search : products + FAQ across a site."""
import re
from fastapi import APIRouter, HTTPException, Query
from deps import db

router = APIRouter()


@router.get("/public/sites/{site_id}/storefront-search")
async def search_storefront(site_id: str, q: str = Query("", max_length=200)):
    q = q.strip()
    if not q or len(q) < 2:
        return {"query": q, "products": [], "total": 0}
    if not await db.sites.find_one({"id": site_id}, {"_id": 0, "id": 1}):
        raise HTTPException(status_code=404, detail="Site introuvable")

    # Simple case-insensitive regex across name/description/short_description/tags
    safe = re.escape(q)
    regex = re.compile(safe, re.IGNORECASE)
    cursor = db.products.find(
        {
            "site_id": site_id,
            "status": {"$ne": "archived"},
            "$or": [
                {"name": regex},
                {"short_description": regex},
                {"description": regex},
                {"tags": regex},
                {"category": regex},
            ],
        },
        {
            "_id": 0,
            "id": 1,
            "name": 1,
            "short_description": 1,
            "price_eur": 1,
            "price": 1,
            "images": 1,
            "stock": 1,
            "sku": 1,
            "category": 1,
        }
    ).limit(30)
    products = await cursor.to_list(30)
    return {"query": q, "products": products, "total": len(products)}
