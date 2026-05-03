"""Sprint 2 + Sprint 3 — Câblage des services `seo_content_generators` et
`brand_premium` en endpoints FastAPI.

Admin endpoints (protected) :
- POST /api/sites/{id}/seo/buyer-guides/generate
- POST /api/sites/{id}/seo/glossary/generate
- POST /api/sites/{id}/seo/comparisons/generate
- POST /api/sites/{id}/seo/top-lists/generate
- POST /api/sites/{id}/seo/all-content/generate      (orchestrator)
- POST /api/sites/{id}/cms/about-team/generate       (Sprint 3)

Public endpoints (no auth, storefront consumption) :
- GET /api/public/sites/{id}/buyer-guides            (list)
- GET /api/public/sites/{id}/buyer-guides/{slug}
- GET /api/public/sites/{id}/glossary                (list)
- GET /api/public/sites/{id}/glossary/{slug}
- GET /api/public/sites/{id}/comparisons             (list)
- GET /api/public/sites/{id}/compare/{slug}
- GET /api/public/sites/{id}/top-lists               (list)
- GET /api/public/sites/{id}/top-lists/{slug}
- GET /api/public/sites/{id}/about-rich
- GET /api/public/sites/{id}/team                    (list)
- GET /api/public/sites/{id}/team/{slug}
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from deps import db, get_current_user
from services import seo_content_generators as scg
from services import brand_premium as bp

router = APIRouter(tags=["seo-content"])
logger = logging.getLogger("altiaro.seo_content_route")


async def _check_owner(site_id: str, user: dict) -> dict:
    s = await db.sites.find_one(
        {"id": site_id}, {"_id": 0, "id": 1, "operator_id": 1, "name": 1, "niche": 1},
    )
    if not s:
        raise HTTPException(404, "Site introuvable")
    if user.get("role") != "admin" and s.get("operator_id") != user.get("id"):
        raise HTTPException(403, "Accès interdit")
    return s


class _EmptyInput(BaseModel):
    pass


class _GlossaryInput(BaseModel):
    target_count: int = 40


class _ComparisonsInput(BaseModel):
    limit: int = 10


# ────────────────────────────────────────────────────────────────
# ADMIN endpoints
# ────────────────────────────────────────────────────────────────
@router.post("/sites/{site_id}/seo/buyer-guides/generate")
async def gen_buyer_guides(site_id: str, user: dict = Depends(get_current_user)):
    await _check_owner(site_id, user)
    return await scg.generate_all_buyer_guides(site_id)


@router.post("/sites/{site_id}/seo/glossary/generate")
async def gen_glossary(site_id: str, body: _GlossaryInput = _GlossaryInput(),
                       user: dict = Depends(get_current_user)):
    await _check_owner(site_id, user)
    return await scg.generate_glossary(site_id, target_count=body.target_count)


@router.post("/sites/{site_id}/seo/comparisons/generate")
async def gen_comparisons(site_id: str, body: _ComparisonsInput = _ComparisonsInput(),
                          user: dict = Depends(get_current_user)):
    await _check_owner(site_id, user)
    return await scg.generate_all_comparisons(site_id, limit=body.limit)


@router.post("/sites/{site_id}/seo/top-lists/generate")
async def gen_top_lists(site_id: str, user: dict = Depends(get_current_user)):
    await _check_owner(site_id, user)
    return await scg.generate_all_top_lists(site_id)


@router.post("/sites/{site_id}/seo/all-content/generate")
async def gen_all_seo_content(site_id: str, user: dict = Depends(get_current_user)):
    """Sprint 2 orchestrator — génère en séquence les 4 types."""
    await _check_owner(site_id, user)
    return await scg.generate_all_seo_content(site_id)


@router.post("/sites/{site_id}/cms/about-team/generate")
async def gen_about_team(site_id: str, user: dict = Depends(get_current_user)):
    """Sprint 3 — génère About enrichi + 3 auteurs fictifs E-E-A-T."""
    await _check_owner(site_id, user)
    return await bp.generate_about_and_team(site_id)


# ────────────────────────────────────────────────────────────────
# PUBLIC endpoints (storefront)
# ────────────────────────────────────────────────────────────────
async def _list_landings(site_id: str, kind: str, limit: int = 200) -> List[Dict[str, Any]]:
    docs = await db.landing_pages.find(
        {"site_id": site_id, "kind": kind, "published": True},
        {"_id": 0, "id": 1, "slug": 1, "title": 1, "h1": 1,
         "meta_description": 1, "intro": 1, "updated_at": 1},
    ).sort("created_at", -1).limit(limit).to_list(limit)
    return docs


@router.get("/public/sites/{site_id}/buyer-guides")
async def public_buyer_guides_list(site_id: str):
    items = await _list_landings(site_id, "buyer_guide")
    return {"count": len(items), "items": items}


@router.get("/public/sites/{site_id}/buyer-guides/{slug}")
async def public_buyer_guide_detail(site_id: str, slug: str):
    doc = await db.landing_pages.find_one(
        {"site_id": site_id, "slug": slug, "kind": "buyer_guide"},
        {"_id": 0},
    )
    if not doc:
        raise HTTPException(404, "Guide introuvable")
    return doc


@router.get("/public/sites/{site_id}/glossary")
async def public_glossary_list(site_id: str):
    terms = await db.glossary_terms.find(
        {"site_id": site_id, "published": True},
        {"_id": 0, "id": 1, "term": 1, "slug": 1, "category": 1, "definition": 1},
    ).sort("term", 1).to_list(500)
    return {"count": len(terms), "items": terms}


@router.get("/public/sites/{site_id}/glossary/{slug}")
async def public_glossary_term(site_id: str, slug: str):
    doc = await db.glossary_terms.find_one(
        {"site_id": site_id, "slug": slug}, {"_id": 0},
    )
    if not doc:
        raise HTTPException(404, "Terme introuvable")
    # Enrich related terms with readable labels
    related = []
    for s in (doc.get("related_slugs") or [])[:8]:
        r = await db.glossary_terms.find_one(
            {"site_id": site_id, "slug": s}, {"_id": 0, "term": 1, "slug": 1, "definition": 1},
        )
        if r:
            related.append(r)
    doc["related"] = related
    return doc


@router.get("/public/sites/{site_id}/comparisons")
async def public_comparisons_list(site_id: str):
    items = await _list_landings(site_id, "comparison")
    return {"count": len(items), "items": items}


@router.get("/public/sites/{site_id}/compare/{slug}")
async def public_comparison_detail(site_id: str, slug: str):
    doc = await db.landing_pages.find_one(
        {"site_id": site_id, "slug": slug, "kind": "comparison"},
        {"_id": 0},
    )
    if not doc:
        raise HTTPException(404, "Comparaison introuvable")
    return doc


@router.get("/public/sites/{site_id}/top-lists")
async def public_top_lists_list(site_id: str):
    items = await _list_landings(site_id, "top_list")
    return {"count": len(items), "items": items}


@router.get("/public/sites/{site_id}/top-lists/{slug}")
async def public_top_list_detail(site_id: str, slug: str):
    doc = await db.landing_pages.find_one(
        {"site_id": site_id, "slug": slug, "kind": "top_list"},
        {"_id": 0},
    )
    if not doc:
        raise HTTPException(404, "Top liste introuvable")
    return doc


@router.get("/public/sites/{site_id}/about-rich")
async def public_about_rich(site_id: str):
    s = await db.sites.find_one(
        {"id": site_id},
        {"_id": 0, "about_rich": 1, "authors": 1, "name": 1},
    )
    if not s:
        raise HTTPException(404, "Site introuvable")
    return {
        "name": s.get("name"),
        "about": s.get("about_rich") or {},
        "authors": s.get("authors") or [],
    }


@router.get("/public/sites/{site_id}/team")
async def public_team(site_id: str):
    s = await db.sites.find_one({"id": site_id}, {"_id": 0, "id": 1, "authors": 1})
    if not s:
        raise HTTPException(404, "Site introuvable")
    return {"items": s.get("authors") or []}


@router.get("/public/sites/{site_id}/team/{slug}")
async def public_team_member(site_id: str, slug: str):
    s = await db.sites.find_one({"id": site_id}, {"_id": 0, "id": 1, "authors": 1})
    if not s:
        raise HTTPException(404, "Site introuvable")
    for a in (s.get("authors") or []):
        if a.get("slug") == slug:
            return a
    raise HTTPException(404, "Auteur introuvable")
