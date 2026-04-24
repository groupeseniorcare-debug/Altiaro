"""Sites CRUD."""
import uuid
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from deps import db, get_current_user, require_admin, _site_with_progress, _check_site_access
from seed_prompts import get_seed_steps_for_site
from seo_constants import (
    ALL_SUPPORTED_COUNTRIES, ALL_SUPPORTED_LANGS, LANG_BY_COUNTRY,
    filter_supported, get_seo_countries, get_seo_langs,
)

router = APIRouter(prefix="/sites")

class SiteCreateInput(BaseModel):
    name: str
    niche: str
    niche_slug: Optional[str] = None
    analysis_id: Optional[str] = None
    selected_countries: Optional[List[str]] = None
    seo_countries: Optional[List[str]] = None   # Chantier 5 — défaut = tous
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
    seo_countries: Optional[List[str]] = None   # Chantier 5
    daily_budget_eur: Optional[int] = None
    domain: Optional[str] = None
    shopify_url: Optional[str] = None
    operator_id: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class SeoSettingsInput(BaseModel):
    """Chantier 5 — Settings SEO/AEO dissociés des settings Ads."""
    seo_countries: Optional[List[str]] = None


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
    # Chantier 5 — seo_countries dissocié. Default = tous les pays supportés.
    seo_countries_in = filter_supported(data.seo_countries) if data.seo_countries is not None else list(ALL_SUPPORTED_COUNTRIES)
    if not seo_countries_in:
        seo_countries_in = list(ALL_SUPPORTED_COUNTRIES)
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
        "seo_countries": seo_countries_in,    # Chantier 5
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
    # Chantier 5 — valider seo_countries s'il est fourni (filtre pays supportés)
    if "seo_countries" in update:
        filtered = filter_supported(update["seo_countries"])
        update["seo_countries"] = filtered or list(ALL_SUPPORTED_COUNTRIES)
    result = await db.sites.update_one({"id": site_id}, {"$set": update})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Site introuvable")
    site = await db.sites.find_one({"id": site_id}, {"_id": 0})
    return await _site_with_progress(site)


# ---------------------------------------------------------------
# Chantier 5 — SEO settings dissociés
# ---------------------------------------------------------------

@router.get("/{site_id}/seo-settings")
async def get_seo_settings(site_id: str, user: dict = Depends(get_current_user)):
    """Expose la config SEO/AEO d'un site (langues/pays activés pour le SEO
    organique), distincte de la config Ads. Accessible concepteur ET admin.

    Si `seo_countries` n'est pas défini en DB (anciens sites), renvoie le
    fallback ALL_SUPPORTED_COUNTRIES (couverture maximale par défaut).
    """
    await _check_site_access(site_id, user)
    site = await db.sites.find_one({"id": site_id}, {"_id": 0})
    if not site:
        raise HTTPException(404, "Site introuvable")
    seo_cc = get_seo_countries(site)
    seo_langs = get_seo_langs(site)
    return {
        "site_id": site_id,
        "seo_countries": seo_cc,
        "seo_langs": seo_langs,
        "ads_countries": site.get("selected_countries") or [],
        "all_supported_countries": ALL_SUPPORTED_COUNTRIES,
        "all_supported_langs": ALL_SUPPORTED_LANGS,
        "country_to_lang": LANG_BY_COUNTRY,
        "explicit": isinstance(site.get("seo_countries"), list) and bool(site.get("seo_countries")),
    }


@router.patch("/{site_id}/seo-settings")
async def patch_seo_settings(
    site_id: str,
    data: SeoSettingsInput,
    user: dict = Depends(get_current_user),
):
    """Modifie la liste des pays SEO d'un site. Vide/None → reset au défaut
    (tous les pays supportés). Concepteur OK sur son propre site."""
    await _check_site_access(site_id, user)
    site = await db.sites.find_one({"id": site_id}, {"_id": 0, "id": 1})
    if not site:
        raise HTTPException(404, "Site introuvable")
    if data.seo_countries is None:
        # Reset au défaut
        new_cc = list(ALL_SUPPORTED_COUNTRIES)
    else:
        filtered = filter_supported(data.seo_countries)
        new_cc = filtered or list(ALL_SUPPORTED_COUNTRIES)
    await db.sites.update_one(
        {"id": site_id},
        {"$set": {"seo_countries": new_cc}},
    )
    updated = await db.sites.find_one({"id": site_id}, {"_id": 0})
    return {
        "ok": True,
        "seo_countries": new_cc,
        "seo_langs": get_seo_langs(updated or {}),
    }


@router.delete("/{site_id}")
async def delete_site(site_id: str, admin: dict = Depends(require_admin)):
    await db.sites.delete_one({"id": site_id})
    await db.steps.delete_many({"site_id": site_id})
    await db.financials.delete_many({"site_id": site_id})
    await db.products.delete_many({"site_id": site_id})
    await db.orders.delete_many({"site_id": site_id})
    return {"ok": True}
