"""Sprint 4 — Endpoint pour rejouer le maillage interne Jaccard sur des
blog_posts existants (sans régénérer le contenu).

Utile pour les sites créés avant Sprint 1.3 dont les `internal_links` sont
vides. Coût LLM : 0.

Usage :
    POST /api/sites/{site_id}/magic/content/relink
        { "lang": "fr" }   # optionnel, default=primary lang
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from deps import db, get_current_user, _check_site_access

router = APIRouter()
logger = logging.getLogger("altiaro.relink")


class RelinkInput(BaseModel):
    lang: Optional[str] = None


@router.post("/sites/{site_id}/magic/content/relink", tags=["sprint4"])
async def magic_content_relink(site_id: str,
                                payload: RelinkInput = RelinkInput(),
                                user: dict = Depends(get_current_user)):
    """Rejoue _apply_internal_linking sur les blog_posts existants."""
    await _check_site_access(site_id, user)
    site = await db.sites.find_one({"id": site_id}, {"_id": 0})
    if not site:
        raise HTTPException(404, "Site introuvable")

    target_lang = (payload.lang or
                   (site.get("primary_locale") or "fr-FR").split("-")[0]
                   ).lower()

    posts = await db.blog_posts.find(
        {"site_id": site_id, "lang": target_lang},
        {"_id": 0},
    ).to_list(500)
    if not posts:
        return {"ok": False, "reason": "no_posts_for_lang", "lang": target_lang}

    pillar = next((p for p in posts if p.get("role") == "pillar"), None)
    if not pillar:
        return {"ok": False, "reason": "no_pillar_post", "posts_total": len(posts)}

    # Reuse pipeline functions for consistency
    from services.magic_content_pipeline import _apply_internal_linking
    await _apply_internal_linking(posts, pillar)

    # Count what was actually written
    updated = await db.blog_posts.count_documents(
        {"site_id": site_id, "lang": target_lang,
         "role": {"$ne": "pillar"},
         "internal_links": {"$exists": True, "$ne": []}},
    )
    return {
        "ok": True,
        "lang": target_lang,
        "posts_total": len(posts),
        "pillar_slug": pillar.get("slug"),
        "non_pillars_with_links": updated,
    }
