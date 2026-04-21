"""Site settings : taxes, shipping zones, payment methods, transactional emails."""
from datetime import datetime, timezone
from typing import Optional, Dict, List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from deps import db, get_current_user, _check_site_access

router = APIRouter()


DEFAULT_SETTINGS = {
    "taxes": {
        "regime": "tva_standard",  # franchise | tva_standard | oss
        "rates_by_country": {
            "FR": 20.0, "BE": 21.0, "LU": 17.0, "DE": 19.0,
            "NL": 21.0, "CH": 0.0, "UK": 20.0,
        },
        "ioss_enabled": False,
    },
    "shipping": {
        "zones": [
            {"id": "fr", "name": "France métropolitaine", "countries": ["FR"],
             "carrier": "Colissimo", "delivery_days": "2-3",
             "tiers": [{"max_kg": 1, "price": 4.90}, {"max_kg": 5, "price": 8.90}, {"max_kg": 30, "price": 14.90}],
             "free_above": 79.0},
            {"id": "bl", "name": "Belgique & Luxembourg", "countries": ["BE", "LU"],
             "carrier": "Colissimo Europe", "delivery_days": "3-5",
             "tiers": [{"max_kg": 2, "price": 9.90}, {"max_kg": 30, "price": 18.90}],
             "free_above": 120.0},
        ],
    },
    "payment_methods": {
        "creditcard": True,
        "bancontact": True,
        "ideal": True,
        "applepay": True,
        "googlepay": True,
        "paypal": True,
        "banktransfer_b2b_min": 500.0,
    },
    "emails": {
        "from_name": "",
        "reply_to": "",
        "support_email": "",
        "support_phone": "",
        "signature": "L'équipe {brand}",
    },
    "updated_at": None,
}


class SettingsInput(BaseModel):
    taxes: Optional[Dict] = None
    shipping: Optional[Dict] = None
    payment_methods: Optional[Dict] = None
    emails: Optional[Dict] = None


@router.get("/sites/{site_id}/settings")
async def get_settings(site_id: str, user: dict = Depends(get_current_user)):
    await _check_site_access(site_id, user)
    site = await db.sites.find_one({"id": site_id}, {"_id": 0, "settings": 1})
    settings = (site or {}).get("settings") or {}
    # Merge with defaults so new fields don't break UI
    out = {**DEFAULT_SETTINGS, **settings}
    for key in ("taxes", "shipping", "payment_methods", "emails"):
        out[key] = {**DEFAULT_SETTINGS[key], **(settings.get(key) or {})}
    return out


@router.put("/sites/{site_id}/settings")
async def update_settings(site_id: str, data: SettingsInput, user: dict = Depends(get_current_user)):
    await _check_site_access(site_id, user)
    site = await db.sites.find_one({"id": site_id}, {"_id": 0, "settings": 1})
    current = (site or {}).get("settings") or {}
    updates = {}
    for field in ("taxes", "shipping", "payment_methods", "emails"):
        val = getattr(data, field)
        if val is None:
            continue
        merged = {**(current.get(field) or {}), **val}
        # Deep-merge taxes.rates_by_country (don't replace whole dict)
        if field == "taxes" and "rates_by_country" in val:
            merged["rates_by_country"] = {
                **(current.get("taxes") or {}).get("rates_by_country", DEFAULT_SETTINGS["taxes"]["rates_by_country"]),
                **val["rates_by_country"],
            }
        updates[field] = merged
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.sites.update_one({"id": site_id}, {"$set": {f"settings.{k}": v for k, v in updates.items()}})
    return await get_settings(site_id, user)


@router.get("/public/sites/{site_id}/settings")
async def public_settings(site_id: str):
    """Minimal subset exposed to storefront (shipping zones, payment methods visible)."""
    site = await db.sites.find_one({"id": site_id}, {"_id": 0, "settings": 1})
    if not site:
        raise HTTPException(status_code=404, detail="Site introuvable")
    settings = site.get("settings") or {}
    return {
        "shipping_zones": (settings.get("shipping") or {}).get("zones") or DEFAULT_SETTINGS["shipping"]["zones"],
        "payment_methods": settings.get("payment_methods") or DEFAULT_SETTINGS["payment_methods"],
        "support_email": (settings.get("emails") or {}).get("support_email") or "",
        "support_phone": (settings.get("emails") or {}).get("support_phone") or "",
    }
