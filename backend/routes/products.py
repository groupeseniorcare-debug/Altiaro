"""Products CRUD per site + import from URL."""
import asyncio
import os
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, HttpUrl

from deps import db, get_current_user, _check_site_access
from models_shop import ProductCreateInput, ProductUpdateInput
from scraper import import_from_url
from routes.indexnow import fire_and_forget_indexnow

router = APIRouter(prefix="/sites/{site_id}/products")


def _product_urls(site_id: str, product_id: str) -> list[str]:
    """Build canonical URLs (home + product + sitemap) for IndexNow fire."""
    origin = os.environ.get("PUBLIC_ORIGIN") or "https://senior-france.preview.emergentagent.com"
    return [
        f"{origin}/shop/{site_id}",
        f"{origin}/shop/{site_id}/product/{product_id}",
        f"{origin}/api/public/sites/{site_id}/sitemap.xml",
    ]


class ImportInput(BaseModel):
    url: HttpUrl


@router.get("")
async def list_products(site_id: str, user: dict = Depends(get_current_user)):
    await _check_site_access(site_id, user)
    items = await db.products.find({"site_id": site_id}, {"_id": 0}).sort("created_at", -1).to_list(500)
    return items


@router.post("")
async def create_product(site_id: str, data: ProductCreateInput, user: dict = Depends(get_current_user)):
    await _check_site_access(site_id, user)
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "id": str(uuid.uuid4()),
        "site_id": site_id,
        **data.model_dump(),
        "created_at": now,
        "updated_at": now,
        "created_by": user["id"],
    }
    await db.products.insert_one(dict(doc))
    doc.pop("_id", None)
    # Auto-submit to IndexNow (Bing, Yandex, Naver, Seznam) — no-op if disabled
    try:
        fire_and_forget_indexnow(_product_urls(site_id, doc["id"]))
    except Exception:
        pass
    # Merchant Center push (fire-and-forget, silent no-op si pas connecté)
    try:
        from routes.merchant import sync_product_if_connected
        asyncio.create_task(sync_product_if_connected(site_id, doc["id"]))
    except Exception:
        pass
    # Phase 6 — sitemap dirty
    try:
        from routes.seo_automation import mark_sitemap_dirty
        asyncio.create_task(mark_sitemap_dirty(site_id))
    except Exception:
        pass
    return doc


@router.get("/{product_id}")
async def get_product(site_id: str, product_id: str, user: dict = Depends(get_current_user)):
    await _check_site_access(site_id, user)
    p = await db.products.find_one({"id": product_id, "site_id": site_id}, {"_id": 0})
    if not p:
        raise HTTPException(status_code=404, detail="Produit introuvable")
    return p


@router.patch("/{product_id}")
async def update_product(site_id: str, product_id: str, data: ProductUpdateInput, user: dict = Depends(get_current_user)):
    await _check_site_access(site_id, user)
    update = {k: v for k, v in data.model_dump().items() if v is not None}
    if not update:
        raise HTTPException(status_code=400, detail="Aucun champ à mettre à jour")
    update["updated_at"] = datetime.now(timezone.utc).isoformat()
    result = await db.products.update_one({"id": product_id, "site_id": site_id}, {"$set": update})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Produit introuvable")
    try:
        fire_and_forget_indexnow(_product_urls(site_id, product_id))
    except Exception:
        pass
    # Merchant Center push (fire-and-forget, silent no-op si pas connecté)
    try:
        from routes.merchant import sync_product_if_connected
        asyncio.create_task(sync_product_if_connected(site_id, product_id))
    except Exception:
        pass
    # Phase 6 — sitemap dirty
    try:
        from routes.seo_automation import mark_sitemap_dirty
        asyncio.create_task(mark_sitemap_dirty(site_id))
    except Exception:
        pass
    return await db.products.find_one({"id": product_id, "site_id": site_id}, {"_id": 0})


@router.delete("/{product_id}")
async def delete_product(site_id: str, product_id: str, user: dict = Depends(get_current_user)):
    await _check_site_access(site_id, user)
    # Notify search engines BEFORE delete (URL still resolves for the submission payload).
    # Phase 4 fix : suppression = signal fort de désindexation à envoyer à Bing/Yandex/etc.
    try:
        fire_and_forget_indexnow(_product_urls(site_id, product_id))
    except Exception:
        pass
    # Capture SKU BEFORE delete — needed by Merchant Center delete hook (offerId = sku)
    existing = await db.products.find_one(
        {"id": product_id, "site_id": site_id}, {"_id": 0, "sku": 1, "id": 1}
    )
    sku = str((existing or {}).get("sku") or product_id) if existing else product_id
    await db.products.delete_one({"id": product_id, "site_id": site_id})
    # Merchant Center delete (fire-and-forget, silent no-op si pas connecté)
    try:
        from routes.merchant import delete_product_if_connected
        asyncio.create_task(delete_product_if_connected(site_id, product_id, sku))
    except Exception:
        pass
    return {"ok": True}


class UpsellLinksInput(BaseModel):
    linked_product_ids: list[str]


@router.patch("/{product_id}/upsell-links")
async def update_upsell_links(
    site_id: str,
    product_id: str,
    data: UpsellLinksInput,
    user: dict = Depends(get_current_user),
):
    """Update the list of main products an upsell is linked to.
    Only valid on products with role='upsell'."""
    await _check_site_access(site_id, user)
    p = await db.products.find_one({"id": product_id, "site_id": site_id}, {"_id": 0, "role": 1})
    if not p:
        raise HTTPException(status_code=404, detail="Produit introuvable")
    if p.get("role") != "upsell":
        raise HTTPException(status_code=400, detail="Ce produit n'est pas un upsell")
    # Keep only ids that actually belong to this site and are main products
    valid = await db.products.find(
        {"id": {"$in": data.linked_product_ids}, "site_id": site_id, "role": {"$ne": "upsell"}},
        {"_id": 0, "id": 1},
    ).to_list(200)
    clean_ids = [v["id"] for v in valid]
    await db.products.update_one(
        {"id": product_id, "site_id": site_id},
        {"$set": {"linked_product_ids": clean_ids,
                  "updated_at": datetime.now(timezone.utc).isoformat()}},
    )
    return {"ok": True, "linked_product_ids": clean_ids}


@router.post("/import")
async def import_product_from_url(site_id: str, data: ImportInput, user: dict = Depends(get_current_user)):
    """Fetch a supplier URL and return a *draft* product (NOT persisted).
    The frontend pre-fills the editor, the user reviews, then POSTs normally.
    Supported best : Shopify, WooCommerce, sites exposant JSON-LD ou Open Graph.
    AliExpress/CJ peuvent retourner des données partielles (JS rendering)."""
    await _check_site_access(site_id, user)
    try:
        draft = await import_from_url(str(data.url))
    except (TimeoutError, ValueError, RuntimeError) as e:
        raise HTTPException(status_code=422, detail=str(e))

    # Shape it into ProductCreateInput format
    name_text = draft.get("name", "")[:200]
    desc_text = draft.get("description", "")[:4000]
    return {
        "draft": {
            "name": {"fr": name_text, "en": name_text, "de": "", "nl": ""},
            "description": {"fr": desc_text, "en": "", "de": "", "nl": ""},
            "price": draft.get("price") or 0,
            "currency": draft.get("currency") or "EUR",
            "images": draft.get("images") or [],
            "sku": draft.get("sku", ""),
            "supplier_url": draft.get("source_url", ""),
            "status": "draft",
            "featured": False,
            "stock": None,
            "compare_at_price": None,
        },
        "source": {
            "host": draft.get("source_host"),
            "url": draft.get("source_url"),
            "has_price": bool(draft.get("price")),
            "images_found": len(draft.get("images") or []),
        }
    }


@router.post("/{product_id}/resync")
async def resync_product_from_supplier(site_id: str, product_id: str, user: dict = Depends(get_current_user)):
    """Refetch the supplier URL and return *what changed* vs our DB.
    We DO NOT overwrite automatically — the Concepteur decides."""
    await _check_site_access(site_id, user)
    p = await db.products.find_one({"id": product_id, "site_id": site_id}, {"_id": 0})
    if not p:
        raise HTTPException(status_code=404, detail="Produit introuvable")
    if not p.get("supplier_url"):
        raise HTTPException(status_code=400, detail="Ce produit n'a pas d'URL fournisseur")

    try:
        fresh = await import_from_url(p["supplier_url"])
    except (TimeoutError, ValueError, RuntimeError) as e:
        raise HTTPException(status_code=422, detail=str(e))

    fresh_price = fresh.get("price")
    current_price = p.get("price")
    price_delta = None
    if fresh_price and current_price:
        price_delta = {
            "old": current_price,
            "new": fresh_price,
            "diff": round(fresh_price - current_price, 2),
            "diff_pct": round(((fresh_price - current_price) / current_price) * 100, 1) if current_price else 0,
        }

    fresh_images = fresh.get("images") or []
    current_images = p.get("images") or []

    return {
        "supplier_url": p["supplier_url"],
        "source_host": fresh.get("source_host"),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "price": price_delta,
        "has_new_images": len(fresh_images) > len(current_images),
        "fresh_name": fresh.get("name", "")[:200],
        "fresh_images_count": len(fresh_images),
        "current_images_count": len(current_images),
        "raw": fresh,  # full payload so the UI can propose "apply"
    }
