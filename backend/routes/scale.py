"""
Scale 6 pays : en 1 clic, duplique un site source vers jusqu'à 5 clones pays.
Chaque clone :
- hérite du nom + " — {Country}"
- a selected_countries = [country], daily_budget_eur = 30
- a primary_language dérivée du pays (FR→fr, DE→de, CH→fr, BE→fr, UK→en, NL→nl)
- peut recevoir un domaine custom (non vérifié — l'user fera le CNAME ensuite)
- optionnellement : Ads Copy générée en background (ne bloque pas la réponse)
- optionnellement : clone du catalogue produits (en draft pour revue)
"""
import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field

from deps import db, get_current_user, _site_with_progress, _check_site_access
from seed_prompts import get_seed_steps_for_site
from routes.domain import _normalize_domain, _is_valid_hostname
from routes.ads_copy import _generate_and_persist, COUNTRY_LOCALES


logger = logging.getLogger("conceptfactory.scale")
router = APIRouter()


# Storefront primary language per country (for Silver Economy targeting)
COUNTRY_TO_LANG = {
    "FR": "fr",
    "DE": "de",
    "CH": "fr",  # Romandie (Geneva, Lausanne — highest AOV in CH)
    "BE": "fr",  # Wallonia + Brussels — BE-LU primary target
    "UK": "en",
    "NL": "nl",
}


class ScaleInput(BaseModel):
    target_countries: List[str] = Field(..., min_length=1, max_length=5)
    custom_domains: Optional[Dict[str, str]] = None  # { "DE": "shop.de", ... }
    copy_products: bool = True
    generate_ads_copy: bool = True
    tone: str = "rassurant"


async def _generate_ads_background(new_site: dict, country: str, lang: str, tone: str, user_id: str):
    """Fire-and-forget Ads Copy generation for a freshly scaled site.
    Errors are swallowed + logged — the clone is already created, Ads is a bonus."""
    try:
        await _generate_and_persist(
            site=new_site,
            country=country,
            language=lang,
            tone=tone,
            product_focus="",
            user_id=user_id,
        )
        logger.info(f"[scale] Ads Copy generated for {new_site['name']} ({country}/{lang})")
    except Exception as e:
        logger.exception(f"[scale] Ads Copy generation failed for {new_site['id']} ({country}): {e}")


@router.post("/sites/{site_id}/scale")
async def scale_site(
    site_id: str,
    data: ScaleInput,
    background: BackgroundTasks,
    user: dict = Depends(get_current_user),
):
    source = await _check_site_access(site_id, user)

    # Normalize + validate inputs
    targets = []
    seen = set()
    for c in data.target_countries:
        cc = (c or "").upper().strip()
        if cc not in COUNTRY_LOCALES:
            raise HTTPException(status_code=400, detail=f"Pays non supporté : {cc}")
        if cc in seen:
            continue
        seen.add(cc)
        targets.append(cc)

    # Validate custom domains (hostname shape + no dups across targets)
    domains_map: Dict[str, str] = {}
    used_domains = set()
    for cc in targets:
        raw = (data.custom_domains or {}).get(cc, "").strip() if data.custom_domains else ""
        if not raw:
            continue
        norm = _normalize_domain(raw)
        if not _is_valid_hostname(norm):
            raise HTTPException(status_code=400, detail=f"Domaine invalide pour {cc} : {raw}")
        if norm in used_domains:
            raise HTTPException(status_code=400, detail=f"Domaine dupliqué : {norm}")
        used_domains.add(norm)
        # Check DB-wide uniqueness (excluding the source site itself)
        clash = await db.sites.find_one(
            {"custom_domain": norm, "id": {"$ne": site_id}},
            {"_id": 0, "id": 1, "name": 1},
        )
        if clash:
            raise HTTPException(
                status_code=409,
                detail=f"Domaine {norm} déjà utilisé par « {clash.get('name', '—')} »",
            )
        domains_map[cc] = norm

    # Source products (single fetch, reused for each clone)
    source_products = []
    if data.copy_products:
        source_products = await db.products.find(
            {"site_id": site_id}, {"_id": 0}
        ).to_list(500)

    now = datetime.now(timezone.utc).isoformat()
    created_sites = []

    # Admin can scale on behalf of the source operator; operator scales to himself
    new_operator = (
        source.get("operator_id") if user["role"] == "admin"
        else user["id"]
    )

    for cc in targets:
        new_id = str(uuid.uuid4())
        new_site = {
            "id": new_id,
            "name": f"{source['name']} — {COUNTRY_LOCALES[cc]['name']}",
            "niche": source.get("niche", ""),
            "niche_slug": source.get("niche_slug"),
            "analysis_id": source.get("analysis_id"),
            "selected_countries": [cc],
            "primary_language": COUNTRY_TO_LANG.get(cc, "en"),
            "daily_budget_eur": 30,
            "domain": "",
            "shopify_url": "",
            "operator_id": new_operator,
            "notes": source.get("notes", ""),
            "status": "active",
            "created_at": now,
            "created_by": user["id"],
            "scaled_from": site_id,
            "scale_batch_id": None,  # set below once we know all siblings
        }
        if cc in domains_map:
            new_site["custom_domain"] = domains_map[cc]
            new_site["custom_domain_verified"] = False
        await db.sites.insert_one(new_site)

        # Fresh 50 steps
        steps = get_seed_steps_for_site(new_id)
        if steps:
            await db.steps.insert_many(steps)

        products_cloned = 0
        if source_products:
            bulk = []
            for p in source_products:
                clone = dict(p)
                clone.pop("_id", None)
                clone["id"] = str(uuid.uuid4())
                clone["site_id"] = new_id
                clone["status"] = "draft"  # review before going live in the new market
                clone["featured"] = False
                clone["created_at"] = now
                clone["updated_at"] = now
                clone["created_by"] = user["id"]
                clone["cloned_from"] = p.get("id")
                bulk.append(clone)
            if bulk:
                await db.products.insert_many(bulk)
                products_cloned = len(bulk)

        new_site.pop("_id", None)
        new_site["products_cloned"] = products_cloned
        await _site_with_progress(new_site)
        created_sites.append(new_site)

    # Tag all siblings with a shared batch_id so the UI can group them
    batch_id = str(uuid.uuid4())
    await db.sites.update_many(
        {"id": {"$in": [s["id"] for s in created_sites]}},
        {"$set": {"scale_batch_id": batch_id}},
    )
    for s in created_sites:
        s["scale_batch_id"] = batch_id

    # Fire background Ads Copy generation (1 per clone — ~30s each, parallel)
    ads_scheduled = 0
    if data.generate_ads_copy:
        for new_site in created_sites:
            cc = new_site["selected_countries"][0]
            lang = new_site.get("primary_language") or COUNTRY_TO_LANG.get(cc, "en")
            background.add_task(
                _generate_ads_background,
                new_site,
                cc,
                lang,
                data.tone or "rassurant",
                user["id"],
            )
            ads_scheduled += 1

    return {
        "source_site_id": site_id,
        "scale_batch_id": batch_id,
        "created": created_sites,
        "ads_copy_scheduled": ads_scheduled,
        "total_daily_budget_eur": 30 * len(created_sites),
    }


@router.get("/sites/{site_id}/scale-siblings")
async def list_scale_siblings(site_id: str, user: dict = Depends(get_current_user)):
    """Returns all sites in the same scale batch (including the source), useful
    to display a 'family' card on the UI."""
    site = await _check_site_access(site_id, user)
    batch_id = site.get("scale_batch_id")
    if not batch_id:
        # Maybe THIS site is the source — look for its children
        source_id = site["id"]
        children = await db.sites.find(
            {"scaled_from": source_id}, {"_id": 0}
        ).to_list(20)
        if not children:
            return {"siblings": [site], "source_id": source_id, "batch_id": None}
        for c in children:
            await _site_with_progress(c)
        return {"siblings": [site] + children, "source_id": source_id, "batch_id": children[0].get("scale_batch_id")}

    siblings = await db.sites.find(
        {"$or": [{"scale_batch_id": batch_id}, {"id": site.get("scaled_from")}]},
        {"_id": 0},
    ).to_list(20)
    for s in siblings:
        await _site_with_progress(s)
    return {"siblings": siblings, "source_id": site.get("scaled_from"), "batch_id": batch_id}
