"""Testimonials AI — génère des avis authentiques et leurs portraits
niche-adaptés via Claude (textes) + Nano Banana (photos).

Pragmatique : une seule route `POST /api/sites/{id}/testimonials/ai-generate`
qui :
1. Lit la niche du site + top 3 produits actifs.
2. Demande à Claude 6 témoignages crédibles (nom FR, rôle/âge, citation 2
   phrases) adaptés à cette niche — persona hétérogène (clients seniors +
   aidants familiaux quand pertinent).
3. Pour chaque, appelle Nano Banana pour générer un portrait vertical 3:4
   d'un senior français utilisant le type de produit décrit dans la niche,
   lumière naturelle, documentaire éditorial.
4. Persiste dans `design.testimonials.items` (tableau d'items `{name, role,
   rating, text, image}`).

Endpoints :
- POST /api/sites/{id}/testimonials/ai-generate   (force: bool = false)
- GET  /api/sites/{id}/testimonials              (lecture, pour debug)
"""
from __future__ import annotations
import asyncio
import base64
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from deps import db, get_current_user, EMERGENT_LLM_KEY, UPLOAD_DIR
from routes.product_narrative import _call_claude_json

logger = logging.getLogger("conceptfactory.testimonials_ai")
router = APIRouter()

NANO_BANANA_MODEL = "gemini-3.1-flash-image-preview"
TESTI_IMG_DIR = UPLOAD_DIR / "testimonials_ai"
TESTI_IMG_DIR.mkdir(parents=True, exist_ok=True)


def _pick_text(val) -> str:
    if isinstance(val, dict):
        for k in ("fr", "fr-FR", "en"):
            if val.get(k):
                return str(val[k])
        return str(next(iter(val.values()), ""))
    return str(val or "")


async def _nano_banana_portrait(prompt: str, site_id: str) -> str | None:
    if not EMERGENT_LLM_KEY:
        return None
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"testi-{site_id}-{uuid.uuid4().hex[:6]}",
            system_message="You generate candid, documentary-style photography for a Silver Economy D2C brand.",
        )
        chat.with_model("gemini", NANO_BANANA_MODEL).with_params(modalities=["image", "text"])
        _, images = await asyncio.wait_for(
            chat.send_message_multimodal_response(UserMessage(text=prompt)),
            timeout=90,
        )
        if not images:
            return None
        img = images[0]
        data = base64.b64decode(img["data"])
        filename = f"t_{site_id}_{uuid.uuid4().hex[:8]}.png"
        path = TESTI_IMG_DIR / filename
        path.write_bytes(data)
        return f"/api/uploads/testimonials_ai/{filename}"
    except Exception:
        logger.exception("[testimonials_ai] nano banana failed")
        return None


async def _generate_testimonial_texts(site: dict, products: list, count: int = 6) -> list[dict] | None:
    niche = site.get("niche") or ""
    brand_name = _pick_text((site.get("design") or {}).get("brand", {}).get("name") or site.get("name") or "")
    product_names = [_pick_text(p.get("name") or "") for p in products[:5] if p.get("name")]
    categories = list({_pick_text(p.get("category") or "") for p in products[:8] if p.get("category")})

    system = (
        "Tu es un copywriter expert en storytelling client. Ton style : sobre, "
        "authentique, jamais promotionnel. Tu écris des témoignages qui sonnent "
        "vrais, avec des noms et prénoms français plausibles, des lieux réels, "
        "des détails concrets (pas de superlatifs creux)."
    )
    user = (
        f"Marque : {brand_name or 'la marque'}\n"
        f"Niche : {niche or 'e-commerce'}\n"
        f"Produits proposés : {', '.join(product_names) if product_names else niche}\n"
        f"Catégories : {', '.join(categories) if categories else 'produits seniors'}\n\n"
        f"Génère {count} témoignages clients DIFFÉRENTS et crédibles. Mix : 4 seniors 65-80 "
        "ans (clients directs) + 1 aidant familial 40-55 ans + 1 couple. Chaque "
        "témoignage doit mentionner un détail concret du produit ou du service "
        "(livraison, conseil, qualité, simplicité) — jamais de superlatifs vides.\n\n"
        "Format JSON strict :\n"
        "{\n"
        "  \"testimonials\": [\n"
        "    {\"name\": \"Françoise D.\", \"role\": \"Cliente · 72 ans\", \"location\": \"Lyon\","
        "     \"rating\": 5, \"text\": \"citation 2 phrases, ton naturel\","
        "     \"image_prompt\": \"prompt anglais pour Nano Banana — portrait 3:4 vertical format,"
        "     décrit la personne (âge, genre, cheveux, expression naturelle), le contexte"
        "     (intérieur avec le type de produit de la niche) et la lumière naturelle douce\"},"
        " …6 items]\n"
        "}\n\n"
        "Les prompts image doivent être ULTRA SPÉCIFIQUES à la niche. Exemple pour "
        "\"fauteuils releveurs\" : \"Candid portrait of a 72-year-old French woman "
        "sitting comfortably in a gray electric stand-up armchair in her bright "
        "living room, soft morning light from a window, warm natural smile, "
        "editorial documentary style, vertical 3:4.\""
    )

    data, err = await _call_claude_json(system, user, timeout=60)
    if err:
        logger.warning(f"[testimonials_ai] claude error: {err}")
        return None
    items = data.get("testimonials") or []
    if not isinstance(items, list) or not items:
        return None
    return items[:count]


class GenerateInput(BaseModel):
    count: int = 6
    force: bool = False
    skip_images: bool = False  # if true, only generate texts (faster, cheaper)


@router.post("/sites/{site_id}/testimonials/ai-generate")
async def generate_testimonials(site_id: str, body: GenerateInput, user=Depends(get_current_user)):
    site = await db.sites.find_one({"id": site_id}, {"_id": 0})
    if not site:
        raise HTTPException(404, "Site introuvable")

    existing = (site.get("design") or {}).get("testimonials") or {}
    has_items = isinstance(existing.get("items"), list) and len(existing.get("items") or []) >= 3
    if has_items and not body.force:
        return {
            "status": "already_exists",
            "message": "Des témoignages existent déjà. Utilisez `force: true` pour régénérer.",
            "count": len(existing.get("items") or []),
        }

    products = await db.products.find(
        {"site_id": site_id, "status": "active"},
        {"_id": 0, "name": 1, "category": 1},
    ).limit(10).to_list(10)

    testimonials = await _generate_testimonial_texts(site, products, count=body.count)
    if not testimonials:
        raise HTTPException(502, "Impossible de générer les textes (budget LLM ?). Réessaye dans quelques minutes.")

    # Génère les images en parallèle (limit concurrent Nano calls to 2)
    sem = asyncio.Semaphore(2)

    async def _gen_img(prompt: str) -> str | None:
        async with sem:
            return await _nano_banana_portrait(prompt, site_id)

    image_tasks = []
    if not body.skip_images:
        for t in testimonials:
            p = t.get("image_prompt") or ""
            if not p:
                image_tasks.append(None)
            else:
                image_tasks.append(asyncio.create_task(_gen_img(p)))

        # Wait for all
        image_urls = []
        for task in image_tasks:
            if task is None:
                image_urls.append(None)
            else:
                try:
                    image_urls.append(await task)
                except Exception:
                    image_urls.append(None)
    else:
        image_urls = [None] * len(testimonials)

    # Build final items
    final = []
    for t, img_url in zip(testimonials, image_urls):
        final.append({
            "name": t.get("name") or "",
            "role": t.get("role") or "",
            "location": t.get("location") or "",
            "rating": int(t.get("rating") or 5),
            "text": t.get("text") or "",
            "image": img_url,
            "ai_generated": True,
        })

    # Persist
    await db.sites.update_one(
        {"id": site_id},
        {"$set": {
            "design.testimonials.items": final,
            "design.testimonials.ai_generated_at": datetime.now(timezone.utc).isoformat(),
        }},
    )

    return {
        "status": "done",
        "count": len(final),
        "with_images": sum(1 for i in image_urls if i),
        "items": final,
    }


@router.get("/sites/{site_id}/testimonials")
async def get_testimonials(site_id: str, user=Depends(get_current_user)):
    site = await db.sites.find_one({"id": site_id}, {"_id": 0, "design.testimonials": 1})
    if not site:
        raise HTTPException(404, "Site introuvable")
    return (site.get("design") or {}).get("testimonials") or {"items": [], "ai_generated_at": None}
