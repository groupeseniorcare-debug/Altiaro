"""Sprint 4 — Génération d'alt text SEO pour toutes les images IA produit.

Pour chaque produit (et chaque image), appelle Claude pour générer un alt
text optimisé SEO (60-120 chars, format : "Produit — contexte — feature"),
puis persiste dans `product.images[i].alt_text`.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

from deps import db
from services.llm_resilience import safe_claude_json

logger = logging.getLogger("altiaro.alt_text")

_SEM = asyncio.Semaphore(4)


def _name(v: Any) -> str:
    if isinstance(v, dict):
        return v.get("fr") or v.get("en") or next(iter(v.values()), "")
    return str(v or "")


async def generate_alt_texts_for_product(product: Dict[str, Any], brand: str) -> Dict[str, Any]:
    images = product.get("generated_images") or []
    if not images:
        images = [{"url": u} for u in (product.get("images") or []) if isinstance(u, str)][:4]
    if not images:
        return {"ok": True, "updated": 0, "reason": "no images"}

    name = _name(product.get("name"))
    feature = _name((product.get("narrative") or {}).get("subheadline")) or \
              _name(product.get("description"))[:120]
    category = _name(product.get("category"))

    system = (
        "Tu es un rédacteur SEO expert en alt text e-commerce. "
        "Tu produis des alt textes courts, descriptifs et optimisés."
    )
    user = (
        f"Génère {len(images)} alt textes SEO distincts pour ces images produit :\n"
        f"- Produit : {name}\n- Marque : {brand}\n- Catégorie : {category}\n"
        f"- Feature clé : {feature}\n\n"
        "Chaque alt text : 60–120 chars, structure « Produit — contexte — feature »,"
        " optimisé image search Google. Ton premium, factuel. Pas de stop words inétiles.\n\n"
        "Retourne un JSON strict : {\"alts\": [\"alt1\", \"alt2\", ...]}."
    )
    try:
        data = await safe_claude_json(
            system, user, model="claude-sonnet-4-5",
            session_id=f"alt-{product.get('id', '')[:8]}",
            timeout=60, request_id=f"alt-{product.get('id', '')[:8]}",
        )
    except Exception as e:
        logger.warning(f"[alt-text] {product.get('id', '')[:8]} failed: {str(e)[:120]}")
        return {"ok": False, "error": str(e)[:200]}

    alts: List[str] = [str(a)[:150] for a in (data.get("alts") or []) if a]
    if not alts:
        return {"ok": False, "error": "no alts in response"}

    updated = 0
    new_images = []
    for i, img in enumerate(images):
        if not isinstance(img, dict):
            img = {"url": img}
        if i < len(alts):
            img = {**img, "alt_text": alts[i]}
            updated += 1
        new_images.append(img)

    await db.products.update_one(
        {"id": product["id"]},
        {"$set": {
            "generated_images": new_images,
            "alt_texts_generated_at": datetime.now(timezone.utc).isoformat(),
        }},
    )
    return {"ok": True, "updated": updated, "total_images": len(images)}


async def generate_alt_texts_for_site(site_id: str) -> Dict[str, Any]:
    site = await db.sites.find_one({"id": site_id}, {"_id": 0, "name": 1, "design": 1})
    if not site:
        return {"ok": False, "error": "site not found"}
    brand = (site.get("design") or {}).get("brand", {}).get("name") or site.get("name") or ""

    products = await db.products.find(
        {"site_id": site_id, "status": "active"},
        {"_id": 0, "id": 1, "name": 1, "description": 1, "narrative": 1,
         "category": 1, "images": 1, "generated_images": 1},
    ).to_list(100)

    async def _one(p):
        async with _SEM:
            return await generate_alt_texts_for_product(p, brand)

    results = await asyncio.gather(*[_one(p) for p in products], return_exceptions=True)
    ok = sum(1 for r in results if isinstance(r, dict) and r.get("ok"))
    return {"ok": True, "products_enriched": ok, "products_total": len(products)}
