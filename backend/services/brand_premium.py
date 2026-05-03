"""
About + Team personas generator — Sprint 3 E-E-A-T (Étape 9 du Cockpit).

Génère pour chaque site :
- Page About enrichie : histoire de marque, mission, valeurs, certifications,
  NAP, 1200-1500 mots avec Schema Organization + AboutPage.
- 3 auteurs fictifs premium pour le blog (bio 120-180 mots + spécialité +
  photo générée via Nano Banana portrait style LinkedIn pro) → E-E-A-T fort.

Persisté dans :
- `site.about_rich` (dict)
- `site.authors[]` (array of persona dicts)
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict

from deps import db
from services.llm_resilience import safe_claude_json
from services.slugify import slugify

logger = logging.getLogger("altiaro.brand_premium")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def generate_about_and_team(site_id: str) -> Dict[str, Any]:
    site = await db.sites.find_one({"id": site_id}, {"_id": 0})
    if not site:
        return {"ok": False, "error": "site not found"}
    niche = site.get("niche") or "produit"
    brand_name = site.get("name") or "La marque"

    system = (
        "Tu es un rédacteur éditorial premium spécialiste branding Silver Economy. "
        "Tu produis un contenu About de niveau magazine + 3 personas équipe "
        "crédibles E-E-A-T avec bios détaillées."
    )
    user = (
        f"Génère un About premium + équipe pour la marque e-commerce « {brand_name} » "
        f"dans la niche « {niche} ».\n\n"
        "Retourne un JSON strict avec :\n"
        "{\n"
        '  "about": {\n'
        '    "tagline": "8-12 mots",\n'
        '    "mission": "60-80 mots",\n'
        '    "story": "600-800 mots en 3-4 paragraphes (genèse marque, valeurs, promesse)",\n'
        '    "values": [{"name":"","desc":"50 mots"}],\n'
        '    "certifications": [{"name":"","year":"","desc":"20 mots"}],\n'
        '    "nap": {"name":"","address":"rue fictive + CP + ville FR","phone":"+33...","email":"contact@..."},\n'
        '    "founded_year": 20xx\n'
        "  },\n"
        '  "authors": [\n'
        '    {"name":"Prénom Nom","role":"Rédactrice en chef / Expert produit","bio":"120-180 mots",\n'
        '     "specialty":"ergothérapie | design | gériatrie",\n'
        '     "sameAs":["https://linkedin.com/in/fictif"],'
        '     "photo_prompt":"prompt Nano Banana 80 mots: portrait style LinkedIn pro, tenue soignée, sourire doux, arrière-plan studio flouté"}\n'
        "  ]\n"
        "}\n\n"
        "Contraintes : 3 auteurs diversifiés (genre, âge, spécialité). "
        "Cohérence NAP avec ville française. Certifications : 2-3, crédibles (ex: "
        "EcoVadis, Qualitel, Afnor). Valeurs : 4-5."
    )

    try:
        data = await safe_claude_json(
            system, user, quality_tier="standard",
            session_id=f"about-{site_id[:8]}",
            timeout=150, request_id=f"about-{site_id[:8]}",
        )
    except Exception as e:
        logger.warning(f"[brand-premium] failed: {str(e)[:200]}")
        return {"ok": False, "error": str(e)[:300]}

    about = data.get("about") or {}
    authors_data = data.get("authors") or []

    # Generate photos for each author (best-effort, don't block on failure)
    authors_out = []
    try:
        from services.llm_resilience import safe_nano_banana_bytes
    except Exception:
        safe_nano_banana_bytes = None

    async def _gen_photo(prompt: str) -> str:
        if not safe_nano_banana_bytes:
            return ""
        try:
            data_bytes = await safe_nano_banana_bytes(
                prompt, system="Premium portrait photography, editorial, professional.",
                session_id=f"author-photo-{uuid.uuid4().hex[:8]}",
                timeout=60, request_id=f"author-photo-{uuid.uuid4().hex[:8]}",
            )
            if data_bytes:
                import base64, os
                uploads_dir = "/app/backend/uploads/authors"
                os.makedirs(uploads_dir, exist_ok=True)
                fname = f"{uuid.uuid4().hex[:12]}.png"
                path = os.path.join(uploads_dir, fname)
                with open(path, "wb") as f:
                    f.write(data_bytes)
                return f"/uploads/authors/{fname}"
        except Exception as e:
            logger.warning(f"[author-photo] failed: {str(e)[:120]}")
        return ""

    for i, a in enumerate(authors_data[:3]):
        photo_prompt = a.get("photo_prompt") or f"professional portrait of {a.get('name', 'person')}"
        photo_url = await _gen_photo(photo_prompt)
        authors_out.append({
            "id": str(uuid.uuid4()),
            "slug": slugify(a.get("name") or f"author-{i}"),
            "name": a.get("name", ""),
            "role": a.get("role", ""),
            "bio": a.get("bio", ""),
            "specialty": a.get("specialty", ""),
            "sameAs": a.get("sameAs") or [],
            "photo_url": photo_url,
            "created_at": _now(),
        })

    await db.sites.update_one(
        {"id": site_id},
        {"$set": {"about_rich": about, "authors": authors_out, "brand_enriched_at": _now()}},
    )
    return {"ok": True, "about_words": len((about.get("story") or "").split()),
            "authors_generated": len(authors_out),
            "photos_generated": sum(1 for a in authors_out if a.get("photo_url"))}
