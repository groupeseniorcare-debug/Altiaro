"""
Site duplication : clone un site existant avec ses produits et ses étapes.
- Les 50 étapes sont recrées à zéro (locked, sauf #1 in_progress).
- Les produits sont dupliqués (nouveaux IDs, même contenu) en statut `draft` par défaut.
- Les commandes et les campagnes Ads NE SONT PAS dupliquées (données runtime).
- Admin peut dupliquer vers n'importe quel operator.
  Concepteur peut dupliquer SES sites, le nouveau est auto-assigné à lui.
"""
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from deps import db, get_current_user, _site_with_progress, _check_site_access
from seed_prompts import get_seed_steps_for_site


router = APIRouter()


class DuplicateInput(BaseModel):
    name: Optional[str] = None
    operator_id: Optional[str] = None  # admin-only override
    selected_countries: Optional[List[str]] = None
    copy_products: bool = True


@router.post("/sites/{site_id}/duplicate")
async def duplicate_site(
    site_id: str,
    data: DuplicateInput,
    user: dict = Depends(get_current_user),
):
    original = await _check_site_access(site_id, user)

    new_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    selected = data.selected_countries or original.get("selected_countries") or []
    budget = len(selected) * 30 if selected else original.get("daily_budget_eur", 0)

    # Admin can reassign, operator always owns the copy
    if user["role"] == "admin" and data.operator_id:
        new_operator = data.operator_id
    elif user["role"] == "admin":
        new_operator = original.get("operator_id")
    else:
        new_operator = user["id"]

    new_site = {
        "id": new_id,
        "name": data.name or f"{original['name']} (copie)",
        "niche": original.get("niche", ""),
        "niche_slug": original.get("niche_slug"),
        "analysis_id": original.get("analysis_id"),
        "selected_countries": selected,
        "daily_budget_eur": budget,
        "domain": "",  # custom domain is per-site, must be re-set
        "shopify_url": "",
        "operator_id": new_operator,
        "notes": original.get("notes", ""),
        "status": "active",
        "created_at": now,
        "created_by": user["id"],
        "duplicated_from": site_id,
    }
    await db.sites.insert_one(new_site)

    # Fresh steps (locked from #2)
    steps = get_seed_steps_for_site(new_id)
    if steps:
        await db.steps.insert_many(steps)

    products_cloned = 0
    if data.copy_products:
        source_products = await db.products.find(
            {"site_id": site_id}, {"_id": 0}
        ).to_list(500)
        if source_products:
            bulk = []
            for p in source_products:
                clone = dict(p)
                clone.pop("_id", None)
                clone["id"] = str(uuid.uuid4())
                clone["site_id"] = new_id
                clone["status"] = "draft"  # force review before going live on the new site
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
    return await _site_with_progress(new_site)
