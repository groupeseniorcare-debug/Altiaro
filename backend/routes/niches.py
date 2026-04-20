"""Niche Engine catalog."""
from fastapi import APIRouter, HTTPException, Depends

from deps import db, get_current_user
from seed_niches import COUNTRIES

router = APIRouter()


@router.get("/niches")
async def list_niches(user: dict = Depends(get_current_user)):
    niches = await db.niches.find({}, {"_id": 0}).sort("rank", 1).to_list(200)
    return niches


@router.get("/niches/{slug}")
async def get_niche(slug: str, user: dict = Depends(get_current_user)):
    niche = await db.niches.find_one({"slug": slug}, {"_id": 0})
    if not niche:
        raise HTTPException(status_code=404, detail="Niche introuvable")
    return niche


@router.get("/countries")
async def list_countries(user: dict = Depends(get_current_user)):
    countries = await db.countries.find({}, {"_id": 0}).sort("code", 1).to_list(20)
    if not countries:
        return COUNTRIES
    return countries
