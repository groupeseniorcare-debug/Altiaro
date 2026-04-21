"""Sites CRUD."""
import uuid
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from deps import db, get_current_user, require_admin, _site_with_progress
from seed_prompts import get_seed_steps_for_site

router = APIRouter(prefix="/sites")

class SiteCreateInput(BaseModel):
    name: str
    niche: str
    niche_slug: Optional[str] = None
    analysis_id: Optional[str] = None
    selected_countries: Optional[List[str]] = None
    daily_budget_eur: Optional[int] = None
    domain: Optional[str] = ""
    shopify_url: Optional[str] = ""
    operator_id: Optional[str] = None
    notes: Optional[str] = ""
    vat_rate: Optional[float] = None


class SiteUpdateInput(BaseModel):
    name: Optional[str] = None
    niche: Optional[str] = None
    selected_countries: Optional[List[str]] = None
    daily_budget_eur: Optional[int] = None
    domain: Optional[str] = None
    shopify_url: Optional[str] = None
    operator_id: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None


@router.get("")
async def list_sites(user: dict = Depends(get_current_user)):
    query = {} if user["role"] == "admin" else {"operator_id": user["id"]}
    sites = await db.sites.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
    for s in sites:
        await _site_with_progress(s)
    return sites


@router.post("")
async def create_site(data: SiteCreateInput, user: dict = Depends(get_current_user)):
    """Admins can create sites for anyone. Operators (Concepteurs) can create sites
    for themselves — typically after running a niche analysis."""
    site_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    selected_countries = data.selected_countries or []
    budget_eur = data.daily_budget_eur if data.daily_budget_eur is not None else len(selected_countries) * 30

    # Operators can only assign to themselves
    if user["role"] == "admin":
        operator_id = data.operator_id
    else:
        operator_id = user["id"]

    doc = {
        "id": site_id,
        "name": data.name,
        "niche": data.niche,
        "niche_slug": data.niche_slug or None,
        "analysis_id": data.analysis_id or None,
        "selected_countries": selected_countries,
        "daily_budget_eur": budget_eur,
        "domain": data.domain or "",
        "shopify_url": data.shopify_url or "",
        "operator_id": operator_id,
        "notes": data.notes or "",
        "vat_rate": data.vat_rate,   # null → dérivé au moment du calcul
        "status": "active",
        "created_at": now,
        "created_by": user["id"],
    }
    await db.sites.insert_one(doc)
    steps = get_seed_steps_for_site(site_id)
    await db.steps.insert_many(steps)
    doc.pop("_id", None)
    return await _site_with_progress(doc)


@router.get("/{site_id}")
async def get_site(site_id: str, user: dict = Depends(get_current_user)):
    site = await db.sites.find_one({"id": site_id}, {"_id": 0})
    if not site:
        raise HTTPException(status_code=404, detail="Site introuvable")
    if user["role"] != "admin" and site.get("operator_id") != user["id"]:
        raise HTTPException(status_code=403, detail="Accès refusé")
    return await _site_with_progress(site)


@router.patch("/{site_id}")
async def update_site(site_id: str, data: SiteUpdateInput, admin: dict = Depends(require_admin)):
    update = {k: v for k, v in data.model_dump().items() if v is not None}
    if not update:
        raise HTTPException(status_code=400, detail="Aucun champ à mettre à jour")
    result = await db.sites.update_one({"id": site_id}, {"$set": update})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Site introuvable")
    site = await db.sites.find_one({"id": site_id}, {"_id": 0})
    return await _site_with_progress(site)


@router.delete("/{site_id}")
async def delete_site(site_id: str, admin: dict = Depends(require_admin)):
    await db.sites.delete_one({"id": site_id})
    await db.steps.delete_many({"site_id": site_id})
    await db.financials.delete_many({"site_id": site_id})
    await db.products.delete_many({"site_id": site_id})
    await db.orders.delete_many({"site_id": site_id})
    return {"ok": True}
