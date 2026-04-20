"""Public storefront (no auth). Rate-limited on order creation."""
import secrets
import uuid
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, HTTPException, Request

from deps import db
from models_shop import OrderCreateInput
from seed_niches import COUNTRIES

router = APIRouter(prefix="/public")


@router.get("/sites/{site_id}")
async def public_site(site_id: str):
    site = await db.sites.find_one({"id": site_id}, {"_id": 0})
    if not site:
        raise HTTPException(status_code=404, detail="Site introuvable")
    niche = None
    if site.get("niche_slug"):
        niche = await db.niches.find_one(
            {"slug": site["niche_slug"]},
            {"_id": 0, "name": 1, "emoji": 1, "tagline": 1, "category": 1}
        )
    return {
        "id": site["id"],
        "name": site["name"],
        "niche": site.get("niche", ""),
        "domain": site.get("domain", ""),
        "niche_data": niche,
    }


@router.get("/sites/{site_id}/products")
async def public_products(site_id: str):
    site = await db.sites.find_one({"id": site_id}, {"_id": 0, "id": 1})
    if not site:
        raise HTTPException(status_code=404, detail="Site introuvable")
    items = await db.products.find(
        {"site_id": site_id, "status": "active"},
        {"_id": 0}
    ).sort([("featured", -1), ("created_at", -1)]).to_list(500)
    return items


@router.get("/sites/{site_id}/products/{product_id}")
async def public_product_detail(site_id: str, product_id: str):
    p = await db.products.find_one(
        {"id": product_id, "site_id": site_id, "status": "active"},
        {"_id": 0}
    )
    if not p:
        raise HTTPException(status_code=404, detail="Produit introuvable")
    return p


@router.post("/sites/{site_id}/orders")
async def public_create_order(site_id: str, data: OrderCreateInput, request: Request):
    """Checkout public.
    - Rate limit: 10 commandes / IP / 10 min
    - Sécurité: prix canoniques serveur (ignore le prix client)
    """
    ip = request.client.host if request.client else "unknown"
    window_start = datetime.now(timezone.utc) - timedelta(minutes=10)
    recent_count = await db.orders.count_documents({
        "_meta_ip": ip,
        "created_at": {"$gte": window_start.isoformat()},
    })
    if recent_count >= 10:
        raise HTTPException(
            status_code=429,
            detail="Trop de commandes depuis cette adresse. Réessayez dans 10 minutes."
        )

    site = await db.sites.find_one({"id": site_id}, {"_id": 0, "id": 1, "name": 1})
    if not site:
        raise HTTPException(status_code=404, detail="Site introuvable")
    if not data.items:
        raise HTTPException(status_code=400, detail="Panier vide")

    canonical_items = []
    for item in data.items:
        prod = await db.products.find_one(
            {"id": item.product_id, "site_id": site_id, "status": "active"},
            {"_id": 0, "price": 1, "currency": 1, "name": 1, "images": 1}
        )
        if not prod:
            raise HTTPException(
                status_code=400,
                detail=f"Produit {item.product_id} introuvable ou inactif"
            )
        canonical_items.append({
            "product_id": item.product_id,
            "name": item.name,
            "price": prod["price"],
            "quantity": item.quantity,
            "currency": prod.get("currency", "EUR"),
            "image": (prod.get("images") or [None])[0],
        })

    subtotal = sum(it["price"] * it["quantity"] for it in canonical_items)
    shipping_fee = 0 if subtotal >= 50 else 4.90
    tax = 0
    total = round(subtotal + shipping_fee + tax, 2)

    now = datetime.now(timezone.utc)
    order_number = f"CF-{int(now.timestamp())}-{secrets.token_hex(2).upper()}"

    doc = {
        "id": str(uuid.uuid4()),
        "site_id": site_id,
        "site_name": site["name"],
        "order_number": order_number,
        "items": canonical_items,
        "customer": data.customer.model_dump(),
        "shipping_address": data.shipping_address.model_dump(),
        "language": data.language,
        "notes": data.notes or "",
        "subtotal": round(subtotal, 2),
        "shipping_fee": shipping_fee,
        "tax": tax,
        "total": total,
        "currency": canonical_items[0]["currency"] if canonical_items else "EUR",
        "status": "pending_payment",
        "payment_method": None,
        "status_history": [],
        "_meta_ip": ip,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }
    await db.orders.insert_one(dict(doc))
    doc.pop("_id", None)
    doc.pop("_meta_ip", None)
    return doc


@router.get("/sites/{site_id}/orders/{order_number}")
async def public_order_lookup(site_id: str, order_number: str):
    o = await db.orders.find_one(
        {"site_id": site_id, "order_number": order_number},
        {"_id": 0, "_meta_ip": 0, "status_history": 0}
    )
    if not o:
        raise HTTPException(status_code=404, detail="Commande introuvable")
    return o
