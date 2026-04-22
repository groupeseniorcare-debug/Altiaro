"""Public storefront (no auth). Rate-limited on order creation."""
import secrets
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Request, Query

from deps import db
from models_shop import OrderCreateInput
from seed_niches import COUNTRIES
from tax_utils import site_vat_rate, compute_order_ht

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
async def public_products(
    site_id: str,
    collection: Optional[str] = Query(None, description="Slug de collection"),
    tag: Optional[List[str]] = Query(None, description="Tag(s) à filtrer"),
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    in_stock: Optional[bool] = None,
    on_sale: Optional[bool] = None,
    sort: str = "featured",
):
    site = await db.sites.find_one({"id": site_id}, {"_id": 0, "id": 1})
    if not site:
        raise HTTPException(status_code=404, detail="Site introuvable")

    q: dict = {"site_id": site_id, "status": "active"}
    if collection:
        q["category"] = collection
    if tag:
        q["tags"] = {"$in": tag}
    price_q: dict = {}
    if min_price is not None:
        price_q["$gte"] = min_price
    if max_price is not None:
        price_q["$lte"] = max_price
    if price_q:
        q["price"] = price_q
    if in_stock:
        q["$or"] = [{"stock": None}, {"stock": {"$gt": 0}}]
    if on_sale:
        q["compare_at_price"] = {"$gt": 0, "$exists": True}

    sort_map = {
        "featured": [("featured", -1), ("created_at", -1)],
        "newest": [("created_at", -1)],
        "price_asc": [("price", 1)],
        "price_desc": [("price", -1)],
        "bestsellers": [("sales_count", -1), ("featured", -1), ("created_at", -1)],
    }
    sort_spec = sort_map.get(sort, sort_map["featured"])

    items = await db.products.find(q, {"_id": 0}).sort(sort_spec).to_list(500)
    return items


@router.get("/sites/{site_id}/collections")
async def public_collections(site_id: str):
    """Liste des collections du site + compte produits par collection."""
    site = await db.sites.find_one({"id": site_id}, {"_id": 0, "design": 1})
    if not site:
        raise HTTPException(status_code=404, detail="Site introuvable")
    collections = (site.get("design") or {}).get("collections") or []

    # Fallback générique pour que la page soit toujours démontrable
    if not collections:
        collections = [
            {"slug": "mobilite", "title": "Mobilité & confort", "description": "Fauteuils releveurs, déambulateurs, aides à la marche.",
             "image": "https://images.unsplash.com/photo-1586773860418-d37222d8fce3?w=900&auto=format&fit=crop"},
            {"slug": "sommeil", "title": "Sommeil & récupération", "description": "Matelas médicaux, lits électriques, linge adapté.",
             "image": "https://images.unsplash.com/photo-1505693416388-ac5ce068fe85?w=900&auto=format&fit=crop"},
            {"slug": "quotidien", "title": "Quotidien serein", "description": "Alarmes, éclairages, ustensiles ergonomiques.",
             "image": "https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?w=900&auto=format&fit=crop"},
        ]

    # enrichir avec le nombre de produits réels (category == slug)
    out = []
    for c in collections:
        slug = c.get("slug") or ""
        count = 0
        if slug:
            count = await db.products.count_documents({"site_id": site_id, "status": "active", "category": slug})
        out.append({**{k: v for k, v in c.items() if k != "_id"}, "products_count": count})
    return out


@router.get("/sites/{site_id}/collections/{slug}")
async def public_collection_detail(site_id: str, slug: str):
    site = await db.sites.find_one({"id": site_id}, {"_id": 0, "design": 1})
    if not site:
        raise HTTPException(status_code=404, detail="Site introuvable")
    collections = (site.get("design") or {}).get("collections") or []
    found = next((c for c in collections if c.get("slug") == slug), None)

    if not found:
        # Fallback: on renvoie une collection "virtuelle" basée sur le slug
        fallback = {
            "mobilite": {"title": "Mobilité & confort", "description": "Fauteuils releveurs, déambulateurs, aides à la marche, cannes et rollators."},
            "sommeil": {"title": "Sommeil & récupération", "description": "Matelas médicaux, lits électriques, linge de lit adapté, oreillers ergonomiques."},
            "quotidien": {"title": "Quotidien serein", "description": "Alarmes, éclairages automatiques, ustensiles ergonomiques, téléphones simplifiés."},
        }
        if slug in fallback:
            found = {"slug": slug, **fallback[slug]}
        else:
            raise HTTPException(status_code=404, detail="Collection introuvable")

    count = await db.products.count_documents({"site_id": site_id, "status": "active", "category": slug})
    return {**{k: v for k, v in found.items() if k != "_id"}, "products_count": count}


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
    ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip() or (
        request.client.host if request.client else "unknown"
    )
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

    site = await db.sites.find_one({"id": site_id}, {"_id": 0})
    if not site:
        raise HTTPException(status_code=404, detail="Site introuvable")
    if not data.items:
        raise HTTPException(status_code=400, detail="Panier vide")

    vat_rate = site_vat_rate(site)

    canonical_items = []
    for item in data.items:
        prod = await db.products.find_one(
            {"id": item.product_id, "site_id": site_id, "status": "active"},
            {"_id": 0, "price": 1, "currency": 1, "name": 1, "images": 1,
             "cost_price_ht": 1, "vat_rate": 1, "sku": 1}
        )
        if not prod:
            raise HTTPException(
                status_code=400,
                detail=f"Produit {item.product_id} introuvable ou inactif"
            )
        canonical_items.append({
            "product_id": item.product_id,
            "name": item.name,
            "sku": prod.get("sku") or "",
            "price": prod["price"],                         # TTC
            "cost_price_ht": float(prod.get("cost_price_ht") or 0),   # snapshot achat HT
            "item_vat_rate": prod.get("vat_rate"),          # override line-level si défini
            "quantity": item.quantity,
            "currency": prod.get("currency", "EUR"),
            "image": (prod.get("images") or [None])[0],
        })

    ht_breakdown = compute_order_ht(canonical_items, vat_rate)
    subtotal = ht_breakdown["subtotal_ttc"]
    shipping_fee = 0 if subtotal >= 50 else 4.90
    tax = round(subtotal - ht_breakdown["subtotal_ht"], 2)   # TVA collectée
    total = round(subtotal + shipping_fee, 2)

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
        "vat_rate": vat_rate,
        "subtotal": subtotal,
        "subtotal_ht": ht_breakdown["subtotal_ht"],
        "cost_ht": ht_breakdown["cost_ht"],
        "gross_margin_ht": ht_breakdown["gross_margin_ht"],
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
