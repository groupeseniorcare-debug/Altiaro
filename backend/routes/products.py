"""Products CRUD per site."""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Depends

from deps import db, get_current_user, _check_site_access
from models_shop import ProductCreateInput, ProductUpdateInput

router = APIRouter(prefix="/sites/{site_id}/products")


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
    return await db.products.find_one({"id": product_id, "site_id": site_id}, {"_id": 0})


@router.delete("/{product_id}")
async def delete_product(site_id: str, product_id: str, user: dict = Depends(get_current_user)):
    await _check_site_access(site_id, user)
    await db.products.delete_one({"id": product_id, "site_id": site_id})
    return {"ok": True}
