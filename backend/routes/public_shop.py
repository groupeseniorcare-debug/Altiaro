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


@router.get("/sites/by-slug/{slug}")
async def public_site_by_slug(slug: str):
    """Résout un site par son `slug` humain-lisible (ex: `demo-altiaro`).

    Utilisé par le storefront React quand l'URL contient un slug au lieu d'un UUID.
    Retourne le même format que `GET /public/sites/{site_id}` — en particulier
    le champ `id` (UUID canonique) que le frontend utilise ensuite pour les
    endpoints dérivés (`/products`, `/design`, etc.).

    NB : cette route doit être déclarée AVANT `/sites/{site_id}` pour que FastAPI
    ne capture pas `by-slug` comme valeur de `site_id`.
    """
    site = await db.sites.find_one({"slug": slug}, {"_id": 0})
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
        "slug": site.get("slug"),
        "name": site["name"],
        "niche": site.get("niche", ""),
        "domain": site.get("domain", ""),
        "niche_data": niche,
    }


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
        "slug": site.get("slug"),
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

    q: dict = {"site_id": site_id, "status": "active", "role": {"$ne": "upsell"}}
    if collection:
        # Lot A2 — match flexible sur `category` (string) OU `categories` (array)
        # pour supporter à la fois l'ancien schéma et les produits classifiés
        # en multi-collection (ex: fauteuil dans `fauteuils-releveurs` + `fauteuils-massage`).
        q["$or"] = [{"category": collection}, {"categories": collection}]
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
        # Lot A2 — préserve un éventuel $or précédent (ex: collection match)
        # via $and pour éviter qu'il soit écrasé ici.
        stock_or = [{"stock": None}, {"stock": {"$gt": 0}}]
        if "$or" in q:
            q["$and"] = [{"$or": q.pop("$or")}, {"$or": stock_or}]
        else:
            q["$or"] = stock_or
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


@router.get("/sites/{site_id}/navigation")
async def public_navigation(site_id: str):
    """Header + footer navigation for the storefront."""
    site = await db.sites.find_one({"id": site_id}, {"_id": 0, "design.navigation": 1})
    nav = ((site or {}).get("design") or {}).get("navigation") or {}
    return {
        "header": nav.get("header") or [
            {"label": "Accueil", "href": "/", "external": False},
            {"label": "Collections", "href": "/collections", "external": False},
            {"label": "À propos", "href": "/a-propos", "external": False},
            {"label": "Contact", "href": "/contact", "external": False},
        ],
        "footer": nav.get("footer") or [
            {"label": "CGV", "href": "/cgv", "external": False},
            {"label": "Mentions légales", "href": "/mentions", "external": False},
            {"label": "Confidentialité", "href": "/confidentialite", "external": False},
        ],
    }


@router.get("/sites/{site_id}/collections")
async def public_collections(site_id: str):
    """Combine user-created collections (db.collections) + legacy design.collections."""
    site = await db.sites.find_one({"id": site_id}, {"_id": 0, "design.collections": 1})
    if not site:
        raise HTTPException(status_code=404, detail="Site introuvable")
    # 1. Real user-created collections
    user_cols = await db.collections.find(
        {"site_id": site_id},
        {"_id": 0, "id": 1, "name": 1, "slug": 1, "description": 1, "cover_image": 1,
         "product_ids": 1, "featured": 1},
    ).sort("featured", -1).to_list(100)
    out = []
    for c in user_cols:
        out.append({
            "slug": c["slug"],
            "title": c["name"],
            "description": c.get("description") or "",
            "image": c.get("cover_image"),
            "products_count": len(c.get("product_ids") or []),
            "featured": bool(c.get("featured")),
            "source": "user",
        })
    # 2. Fallback legacy collections (auto-generated by design IA)
    legacy = (site.get("design") or {}).get("collections") or []
    existing_slugs = {c["slug"] for c in out}
    for c in legacy:
        slug = c.get("slug") or ""
        if not slug or slug in existing_slugs:
            continue
        # Bloc 4 — match flexible : la classification produit peut écrire `category`
        # (string) ou `categories` (array). On compte les deux pour ne rien rater.
        count = await db.products.count_documents({
            "site_id": site_id, "status": "active",
            "$or": [{"category": slug}, {"categories": slug}],
        })
        out.append({**{k: v for k, v in c.items() if k != "_id"},
                    "products_count": count, "source": "legacy"})
    # Lot A2 — Plus de fallback "Silver Economy" hardcoded avec stocks Unsplash
    # hors-niche. Si aucune collection n'est définie, on retourne [] et le
    # frontend affichera un état vide propre (« Toutes nos références »).
    return out


@router.get("/sites/{site_id}/collections/{slug}")
async def public_collection_detail(site_id: str, slug: str):
    """Collection detail — prefer user-created collection first."""
    site = await db.sites.find_one({"id": site_id}, {"_id": 0, "design.collections": 1})
    if not site:
        raise HTTPException(status_code=404, detail="Site introuvable")
    # 1. Try user-created collection
    user_col = await db.collections.find_one(
        {"site_id": site_id, "slug": slug},
        {"_id": 0, "id": 1, "name": 1, "slug": 1, "description": 1,
         "cover_image": 1, "product_ids": 1, "featured": 1},
    )
    if user_col:
        return {
            "slug": user_col["slug"],
            "title": user_col["name"],
            "description": user_col.get("description") or "",
            "image": user_col.get("cover_image"),
            "products_count": len(user_col.get("product_ids") or []),
            "product_ids": user_col.get("product_ids") or [],
            "source": "user",
        }
    # 2. Legacy fallback
    legacy = (site.get("design") or {}).get("collections") or []
    found = next((c for c in legacy if c.get("slug") == slug), None)
    if not found:
        # Lot A2 — Plus de fallback générique "Silver Economy" hardcoded.
        # Si la collection demandée n'existe pas en DB ni dans le legacy
        # design.collections, on renvoie 404 propre.
        raise HTTPException(status_code=404, detail="Collection introuvable")
    # Bloc 4 — match flexible : `category` (string) OU `categories` (array)
    count = await db.products.count_documents({
        "site_id": site_id, "status": "active",
        "$or": [{"category": slug}, {"categories": slug}],
    })
    return {**{k: v for k, v in found.items() if k != "_id"}, "products_count": count, "source": "legacy"}


@router.get("/sites/{site_id}/products/{product_id_or_slug}")
async def public_product_detail(site_id: str, product_id_or_slug: str):
    """Resolve a product by id OR by slug (SEO-friendly URLs).

    Also returns the canonical slug so the frontend can 301-redirect UUID URLs.
    """
    # Try UUID first (fast-path, uses an index)
    p = await db.products.find_one(
        {"id": product_id_or_slug, "site_id": site_id, "status": "active"},
        {"_id": 0},
    )
    if not p:
        # Fallback: lookup by slug
        p = await db.products.find_one(
            {"slug": product_id_or_slug, "site_id": site_id, "status": "active"},
            {"_id": 0},
        )
    if not p:
        raise HTTPException(status_code=404, detail="Produit introuvable")
    return p


@router.get("/sites/{site_id}/products/{product_id_or_slug}/upsells")
async def public_product_upsells(site_id: str, product_id_or_slug: str, limit: int = 4):
    """Return upsells linked to this main product.

    Accepts either the product id or the slug (SEO-friendly URLs).
    Fallback: if no specific upsell is linked, return any active upsell of the site."""
    # Resolve to canonical id
    p = await db.products.find_one(
        {"$or": [{"id": product_id_or_slug}, {"slug": product_id_or_slug}],
         "site_id": site_id, "status": "active"},
        {"_id": 0, "id": 1},
    )
    product_id = (p or {}).get("id") or product_id_or_slug
    # Linked first
    linked = await db.products.find(
        {"site_id": site_id, "status": "active", "role": "upsell",
         "linked_product_ids": product_id},
        {"_id": 0},
    ).sort("created_at", -1).limit(max(1, min(limit, 12))).to_list(12)
    if linked:
        return linked
    # Fallback to any upsell for this site (so new shops always see something)
    return await db.products.find(
        {"site_id": site_id, "status": "active", "role": "upsell"},
        {"_id": 0},
    ).sort("created_at", -1).limit(max(1, min(limit, 12))).to_list(12)


@router.post("/sites/{site_id}/upsells-for-products")
async def public_upsells_for_products(site_id: str, body: dict, limit: int = 6):
    """Post-purchase: given a list of purchased product_ids, return aggregated upsells.
    Body: { "product_ids": ["...", "..."] }
    """
    pids = body.get("product_ids") or []
    if not isinstance(pids, list) or not pids:
        return []
    linked = await db.products.find(
        {"site_id": site_id, "status": "active", "role": "upsell",
         "linked_product_ids": {"$in": pids}},
        {"_id": 0},
    ).sort("created_at", -1).limit(max(1, min(limit, 12))).to_list(12)
    if linked:
        # De-dup by id
        seen = set()
        uniq = []
        for x in linked:
            if x["id"] not in seen:
                uniq.append(x)
                seen.add(x["id"])
        return uniq[: max(1, min(limit, 12))]
    # Fallback
    return await db.products.find(
        {"site_id": site_id, "status": "active", "role": "upsell"},
        {"_id": 0},
    ).sort("created_at", -1).limit(max(1, min(limit, 12))).to_list(12)


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
             "cost_price_ht": 1, "vat_rate": 1, "sku": 1, "role": 1}
        )
        if not prod:
            raise HTTPException(
                status_code=400,
                detail=f"Produit {item.product_id} introuvable ou inactif"
            )
        # Impulse-cart upsell discount — only applies to products with role=upsell,
        # capped to 50% to prevent abuse.
        discount_pct = float(item.upsell_discount_pct or 0)
        discount_pct = max(0.0, min(discount_pct, 50.0))
        original_price = float(prod["price"])
        applied_price = original_price
        if discount_pct > 0 and prod.get("role") == "upsell":
            applied_price = round(original_price * (1 - discount_pct / 100.0), 2)
        canonical_items.append({
            "product_id": item.product_id,
            "name": item.name,
            "sku": prod.get("sku") or "",
            "price": applied_price,                         # TTC (discounted if upsell impulse)
            "original_price": original_price,
            "upsell_discount_pct": discount_pct if applied_price != original_price else 0,
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

    # Phase D' — Devise selon pays détecté (Mollie GBP au checkout UK, parité 1:1).
    # Priorité : 1) CF-IPCountry header (Cloudflare) 2) shipping_address.country
    geo_country = (request.headers.get("CF-IPCountry") or "").upper().strip()
    if not geo_country or geo_country == "XX":
        try:
            geo_country = (data.shipping_address.country or "").upper().strip()
        except Exception:
            geo_country = ""
    base_currency = canonical_items[0]["currency"] if canonical_items else "EUR"
    final_currency = "GBP" if geo_country == "GB" else base_currency

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
        "currency": final_currency,
        "geo_country": geo_country or None,
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
