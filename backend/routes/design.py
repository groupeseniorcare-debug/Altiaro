"""Site Designer : le Concepteur clique « Générer mon site » et Claude Sonnet 4.5
produit la config complète du storefront (brand, hero, sections, pages, SEO).
Optionnellement un logo graphique est généré par Gemini Nano Banana.

Structure stockée dans `sites.{site_id}.design`.

Endpoints :
- GET  /api/sites/{id}/design                       → design courant (ou null)
- POST /api/sites/{id}/design/generate              → génère tout (Claude + logo)
- POST /api/sites/{id}/design/regenerate/{section}  → régénère hero|brand|benefits|faq|testimonials|about|legal|logo
- POST /api/sites/{id}/design/publish               → toggle published=true/false
- GET  /api/public/sites/{id}/design                → read-only pour le storefront
- POST /api/public/sites/{id}/contact               → formulaire contact → collection leads
"""
from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import re
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, EmailStr, Field

from deps import db, get_current_user, _check_site_access, EMERGENT_LLM_KEY, UPLOAD_DIR
from legal_templates import (
    CGV, MENTIONS_LEGALES, CONFIDENTIALITE,
    COOKIES, LIVRAISON, RETOURS, MEDIATION,
    render_legal,
)

logger = logging.getLogger("conceptfactory.design")
router = APIRouter()

JSON_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


# ---------------------------------------------------------------------
# Brand text sanitizer — Claude sometimes ignores "reply with only the final text"
# and returns preambles, markdown, or full explanations. This strips that noise.
# ---------------------------------------------------------------------
_BRAND_PREAMBLES = re.compile(
    r"^\s*(?:voici|proposition(?:s)?\s+de\s+\w+|suggestion(?:s)?(?:\s+de)?|mon\s+choix|je\s+propose|nom\s+(?:de\s+)?(?:marque|choisi)\s*:?|baseline\s*:?|tagline\s*:?|ton\s+de\s+voix\s*:?|histoire\s*:?|le\s+nom\s+(?:est|serait)?\s*:?)\s*[:\-–—]?\s*",
    re.IGNORECASE,
)


def _sanitize_brand_text(raw: str, max_len: int = 80) -> str:
    """Strip markdown, preambles, quotes and pick the first meaningful line.

    Brand fields should be plain text (no headings, no bullet lists, no prose).
    If Claude responds with a full explanation like "# Proposition de nom\n\n**Soléa**\n\n...",
    this extracts "Soléa".
    """
    if not raw:
        return ""
    text = str(raw).strip()
    # 1) If there's a bold token (** ... **) early on, prefer it — Claude loves bolding the answer.
    bold = re.search(r"\*\*([^*\n]{1,80})\*\*", text)
    if bold:
        text = bold.group(1).strip()
    else:
        # 2) Demote markdown headings / blockquotes to their content (keep the text, drop the markers)
        text = re.sub(r"^\s*#{1,6}\s+", "", text, flags=re.MULTILINE)
        text = re.sub(r"^\s*>\s*", "", text, flags=re.MULTILINE)
        text = re.sub(r"```[^`]*```", "", text, flags=re.DOTALL)
        # 3) Take first non-empty line
        for line in text.splitlines():
            line = line.strip()
            if line:
                text = line
                break
    # 4) Remove markdown formatting chars
    text = re.sub(r"[*_`#>]+", "", text)
    # 5) Strip surrounding quotes (straight + curly + FR guillemets)
    text = text.strip().strip('"').strip("'").strip("«»").strip("“”‘’").strip()
    # 6) Strip common French preambles
    text = _BRAND_PREAMBLES.sub("", text).strip()
    # 7) Drop trailing colon/period noise
    text = text.rstrip(".:, ").strip()
    # 8) Enforce max length
    if len(text) > max_len:
        text = text[:max_len].rsplit(" ", 1)[0].rstrip(".:, ")
    return text
NANO_BANANA_MODEL = "gemini-3.1-flash-image-preview"


# ================== Claude prompt ================== #
SYSTEM = """Tu es expert UI/UX Designer + Copywriter senior, spécialisé e-commerce Silver Economy EU.
Tu conçois des sites pour clients 60+ : ton rassurant, couleurs chaudes lisibles, texte clair.
Tu réponds UNIQUEMENT avec du JSON valide (pas de markdown, pas de commentaire)."""

USER_TMPL = """Contexte :
- Nom du site : {name}
- Niche : {niche}
- Pays cibles : {countries}
- Produit phare : {flagship}
- Bénéfices clés des produits : {benefits_hint}
- Voix de marque existante (si présente) : {brand_voice}
- Positionnement prix issu de l'analyse marché (étape 1) : {pricing_hint}
- Directive spécifique du Concepteur : {tweak}

Objectif : produire la configuration COMPLÈTE du storefront en 1 shot.

Contraintes :
1. Tous les textes doivent être traduits en FR (obligatoire), EN, DE, NL
2. Couleurs au format HEX. primary_color = couleur principale (boutons, accents). accent_color = nuance douce secondaire. background = blanc cassé. text = foncé pour lisibilité seniors.
3. Polices : choisir parmi ["Fraunces","Inter","Playfair Display","Manrope","Crimson Pro","Source Serif","DM Sans","Lora"]
4. 4 bénéfices (icônes Phosphor : ShieldCheck, Truck, Phone, ArrowsClockwise, Heart, Medal, Clock, Lightning, HandHeart, ThumbsUp — choisir les + pertinents)
5. 3 témoignages fictifs mais crédibles (prénom, âge 60-85, ville, citation courte 20-40 mots, note 4-5)
6. 10 questions FAQ pertinentes pour la niche, avec réponses de 2-3 phrases
7. Page À propos : 4 paragraphes (mission, équipe, engagement qualité, relation client)
8. Hero : titre percutant 5-8 mots, sous-titre 1 phrase rassurante, CTA 2-3 mots, trust_line 1 phrase (ex: « Livraison gratuite dès 50€ · Support 7j/7 »)
9. SEO : title 50-60 caractères, description 140-160 caractères

Schéma JSON strict à produire :
{{
  "brand": {{
    "logo_text": "{name}",
    "logo_style_prompt": "Description courte du style logo à générer (ex: 'minimalist line icon representing confort and trust')",
    "primary_color": "#HEX",
    "accent_color": "#HEX",
    "background_color": "#FDFBF7",
    "text_color": "#1C1917",
    "font_heading": "Fraunces",
    "font_body": "Inter",
    "tagline": {{"fr":"","en":"","de":"","nl":""}}
  }},
  "hero": {{
    "title": {{"fr":"","en":"","de":"","nl":""}},
    "subtitle": {{"fr":"","en":"","de":"","nl":""}},
    "cta_label": {{"fr":"","en":"","de":"","nl":""}},
    "trust_line": {{"fr":"","en":"","de":"","nl":""}}
  }},
  "benefits": [
    {{"icon":"ShieldCheck","title":{{"fr":"","en":"","de":"","nl":""}},"desc":{{"fr":"","en":"","de":"","nl":""}}}}
  ],
  "testimonials": [
    {{"name":"Marie D.","age":72,"city":"Lyon","rating":5,"quote":{{"fr":"","en":"","de":"","nl":""}}}}
  ],
  "faq": [
    {{"q":{{"fr":"","en":"","de":"","nl":""}},"a":{{"fr":"","en":"","de":"","nl":""}}}}
  ],
  "about": {{
    "headline": {{"fr":"","en":"","de":"","nl":""}},
    "paragraphs": [
      {{"fr":"","en":"","de":"","nl":""}}
    ]
  }},
  "contact": {{
    "headline": {{"fr":"","en":"","de":"","nl":""}},
    "intro": {{"fr":"","en":"","de":"","nl":""}},
    "support_email": "contact@{slug}.fr",
    "support_phone": "+33 1 80 50 60 70",
    "support_hours": {{"fr":"Lun-Ven 9h-19h","en":"Mon-Fri 9am-7pm","de":"Mo-Fr 9-19 Uhr","nl":"Ma-Vr 9u-19u"}}
  }},
  "seo": {{
    "title": {{"fr":"","en":"","de":"","nl":""}},
    "description": {{"fr":"","en":"","de":"","nl":""}}
  }},
  "footer": {{
    "tagline": {{"fr":"","en":"","de":"","nl":""}},
    "columns": [
      {{"title":{{"fr":"Aide","en":"Help","de":"Hilfe","nl":"Hulp"}},"links":[{{"label":{{"fr":"Contact","en":"","de":"","nl":""}},"href":"/contact"}}]}}
    ]
  }}
}}

Produis EXACTEMENT 4 benefits, 3 testimonials, 10 FAQ, 4 paragraphs About."""


def _strip(text: str) -> str:
    return JSON_FENCE.sub("", text).strip()


async def _claude_json(
    system: str, user: str, session_id: str,
    timeout: int = 180, quality_tier: str = "standard",
) -> dict:
    """Phase 0 — délègue à `safe_claude_json` (retry expo + circuit breaker).

    Conserve la signature historique (utilisée à 9+ endroits dans design.py).
    Préserve le flag platform_health pour budget_exhausted (utilisé par la
    bannière du cockpit).

    Bloc 1 sous-chantier 1a — `quality_tier` propagé. Default "standard"
    (Haiku 4.5, ~3× moins cher). Use `quality_tier="premium"` (Sonnet 4.5)
    pour brand identity (nom/tagline/voice) et SEO core uniquement.
    """
    from services.llm_resilience import safe_claude_json, LLMUnavailableError
    try:
        data = await safe_claude_json(
            system, user,
            quality_tier=quality_tier,
            session_id=session_id, timeout=timeout,
        )
        # Success → auto-clear any stale budget_exhausted flag
        try:
            await db.platform_health.update_one(
                {"key": "llm"},
                {"$set": {"key": "llm", "status": "ok",
                          "last_success_at": datetime.now(timezone.utc).isoformat()}},
                upsert=True,
            )
        except Exception:
            pass
        return data
    except ValueError as e:
        # JSON parse error — non-retryable
        logger.error(f"Design Claude returned invalid JSON: {e}")
        raise HTTPException(status_code=502, detail=f"L'IA a retourné un JSON invalide : {str(e)[:160]}")
    except LLMUnavailableError as e:
        logger.warning(f"[design] LLM unavailable after retries: {e.last_error}")
        raise HTTPException(
            status_code=503,
            detail=f"IA temporairement indisponible (proxy upstream KO, breaker={e.provider}). "
                   "Réessayez dans 1-3 min — le système retentera automatiquement.",
        )
    except HTTPException:
        raise
    except Exception as e:
        msg = str(e)
        if "Budget has been exceeded" in msg or ("budget" in msg.lower() and "exceeded" in msg.lower()):
            try:
                await db.platform_health.update_one(
                    {"key": "llm"},
                    {"$set": {"key": "llm", "status": "budget_exhausted",
                              "last_error_at": datetime.now(timezone.utc).isoformat()}},
                    upsert=True,
                )
            except Exception:
                pass
            raise HTTPException(
                status_code=402,
                detail="Budget Emergent LLM Key épuisé. Recharge la clé depuis Profile → Universal Key → Add Balance.",
            )
        logger.warning(f"[design] Claude unexpected error: {msg[:200]}")
        raise HTTPException(status_code=502, detail=f"IA indisponible : {msg[:180]}")


async def _nano_banana_logo(prompt: str, site_id: str) -> Optional[str]:
    """Génère un logo via Gemini Nano Banana et renvoie l'URL publique.

    Phase 0 — délègue à `safe_nano_banana_bytes` (retry expo + circuit breaker).
    """
    from services.llm_resilience import safe_nano_banana_bytes, LLMUnavailableError
    full_prompt = (
        f"Minimalist vector logo icon (no text, no letters), 512x512, flat design, "
        f"centered, cream background (#FDFBF7), {prompt}. "
        f"Clean, friendly, professional. Senior-friendly e-commerce brand."
    )
    try:
        data = await safe_nano_banana_bytes(
            full_prompt,
            system="You create minimal vector logos for e-commerce stores.",
            session_id=f"logo-{site_id}-{uuid.uuid4().hex[:6]}",
            timeout=90,
            request_id=f"logo-{site_id[:8]}",
        )
        if not data:
            return None
        logos_dir = UPLOAD_DIR / "logos"
        logos_dir.mkdir(parents=True, exist_ok=True)
        filename = f"logo_{site_id}_{uuid.uuid4().hex[:8]}.png"
        path = logos_dir / filename
        path.write_bytes(data)
        return f"/api/uploads/logos/{filename}"
    except LLMUnavailableError as e:
        logger.warning(f"[design] Nano Banana logo unavailable: {e.last_error}")
        return None
    except Exception:
        logger.exception("Nano Banana logo generation failed")
        return None


async def _nano_banana_hero_image(prompt: str, site_id: str) -> Optional[str]:
    """Génère une image hero lifestyle 3:2 via Nano Banana.

    Phase 0 — délègue à `safe_nano_banana_bytes` (retry expo + circuit breaker).
    """
    from services.llm_resilience import safe_nano_banana_bytes, LLMUnavailableError
    full_prompt = (
        f"Editorial lifestyle photography, 3:2 landscape format, premium magazine quality, "
        f"warm morning natural light, soft shadows, shallow depth of field. "
        f"{prompt}. "
        f"Tasteful French interior, editorial composition, dignity, documentary style. "
        f"No text, no logo, no watermark."
    )
    try:
        data = await safe_nano_banana_bytes(
            full_prompt,
            system="You create premium lifestyle photography for Silver Economy D2C e-commerce brands.",
            session_id=f"hero-{site_id}-{uuid.uuid4().hex[:6]}",
            timeout=120,
            request_id=f"hero-{site_id[:8]}",
        )
        if not data:
            return None
        heroes_dir = UPLOAD_DIR / "heroes"
        heroes_dir.mkdir(parents=True, exist_ok=True)
        filename = f"hero_{site_id}_{uuid.uuid4().hex[:8]}.png"
        path = heroes_dir / filename
        path.write_bytes(data)
        return f"/api/uploads/heroes/{filename}"
    except LLMUnavailableError as e:
        logger.warning(f"[design] Nano Banana hero unavailable: {e.last_error}")
        return None
    except Exception:
        logger.exception("Nano Banana hero generation failed")
        return None


@router.post("/sites/{site_id}/design/generate-hero-image")
async def generate_hero_image(site_id: str, data: RegenInput, user: dict = Depends(get_current_user)):
    """Génère une image hero (lifestyle 3:2) via Nano Banana, adaptée à la
    niche. L'URL est sauvegardée dans `design.hero.image` + utilisée
    automatiquement comme bg du footer."""
    await _check_site_access(site_id, user)
    site = await db.sites.find_one({"id": site_id}, {"_id": 0})
    if not site:
        raise HTTPException(status_code=404, detail="Site introuvable")
    niche = site.get("niche") or "produits Silver Economy"
    design = site.get("design") or {}
    brand_name = ((design.get("brand") or {}).get("name")) or site.get("name") or "la marque"
    prompt = data.tweak or (
        f"A bright, airy French living room with a senior person comfortably using "
        f"a {niche} product. Warm natural morning light coming from a large window, "
        f"wooden floor, simple elegant decor, serene atmosphere. Brand : {brand_name}."
    )
    url = await _nano_banana_hero_image(prompt, site_id)
    if not url:
        raise HTTPException(status_code=502, detail="Génération hero image échouée, réessaye.")
    design_hero = design.get("hero") or {}
    design_hero["image"] = url
    design["hero"] = design_hero
    design["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.sites.update_one({"id": site_id}, {"$set": {"design": design}})
    return {"ok": True, "hero_image": url}


def _slugify(s: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s or "").strip("-").lower()
    return s or "boutique"


async def _gather_context(site: dict) -> dict:
    """Agrège contexte : produits, outputs mega-blocks existants."""
    products = await db.products.find(
        {"site_id": site["id"], "status": "active"}, {"_id": 0, "name": 1, "description": 1, "price": 1, "featured": 1}
    ).limit(10).to_list(10)
    flagship = ""
    benefits_hint = ""
    for p in products:
        if p.get("featured"):
            flagship = (p.get("name") or {}).get("fr") or flagship
            break
    if not flagship and products:
        flagship = (products[0].get("name") or {}).get("fr", "")
    if products:
        benefits_hint = " · ".join([(p.get("name") or {}).get("fr", "")[:40] for p in products[:3]])

    # Existing brand voice from mega-block SEO output (if any)
    brand_voice = ""
    latest_seo = await db.block_outputs.find_one(
        {"site_id": site["id"], "block_id": "seo"}, {"_id": 0}, sort=[("created_at", -1)]
    )
    if latest_seo:
        payload = latest_seo.get("payload") or {}
        bv = payload.get("brand_voice") or {}
        if bv:
            brand_voice = json.dumps(bv, ensure_ascii=False)[:500]
    # Pricing analysis from step 1 (market positioning context)
    pricing_hint = ""
    pa = (site.get("design") or {}).get("pricing_analysis") or {}
    if pa.get("ranges"):
        sweet = [r.get("sweet_spot") for r in pa.get("ranges", []) if r.get("sweet_spot")]
        if sweet:
            pricing_hint = f"Positionnement prix sweet-spot : {min(sweet)}-{max(sweet)}€"
    return {"flagship": flagship or "N/A", "benefits_hint": benefits_hint or "N/A", "brand_voice": brand_voice or "N/A", "pricing_hint": pricing_hint or "N/A"}


def _inject_legal(design: dict, site: dict) -> dict:
    """Rend les 3 pages légales depuis les templates standards (sûrs)."""
    slug = _slugify(site.get("name"))
    vars_ = {
        "site_name": site.get("name") or "notre boutique",
        "niche_name": site.get("niche") or "produits spécialisés",
        "email_contact": f"contact@{slug}.fr",
    }
    design["legal_pages"] = {
        "cgv": {"title": "CGV", "body_md": render_legal(CGV, vars_)},
        "mentions_legales": {"title": "Mentions légales", "body_md": render_legal(MENTIONS_LEGALES, vars_)},
        "confidentialite": {"title": "Politique de confidentialité", "body_md": render_legal(CONFIDENTIALITE, vars_)},
        "cookies": {"title": "Politique de cookies", "body_md": render_legal(COOKIES, vars_)},
        "livraison": {"title": "Livraison & délais", "body_md": render_legal(LIVRAISON, vars_)},
        "retours": {"title": "Retours & rétractation", "body_md": render_legal(RETOURS, vars_)},
        "mediation": {"title": "Médiation de la consommation", "body_md": render_legal(MEDIATION, vars_)},
    }
    return design


# ================== Routes ================== #

class GenerateInput(BaseModel):
    tweak: Optional[str] = ""
    with_logo: bool = True


@router.get("/sites/{site_id}/design")
async def get_design(site_id: str, user: dict = Depends(get_current_user)):
    await _check_site_access(site_id, user)
    site = await db.sites.find_one({"id": site_id}, {"_id": 0, "design": 1, "name": 1, "id": 1})
    if not site:
        raise HTTPException(status_code=404, detail="Site introuvable")
    return {"design": site.get("design"), "site_id": site_id, "site_name": site.get("name")}


@router.post("/sites/{site_id}/design/generate")
async def generate_design(site_id: str, data: GenerateInput, user: dict = Depends(get_current_user)):
    """Kick off an async design generation job to bypass ingress 60 s timeouts.
    Returns immediately with a job_id. Frontend polls /design/generate/status."""
    await _check_site_access(site_id, user)
    site = await db.sites.find_one({"id": site_id}, {"_id": 0})
    if not site:
        raise HTTPException(status_code=404, detail="Site introuvable")

    ctx = await _gather_context(site)
    user_prompt = USER_TMPL.format(
        name=site.get("name") or "Boutique",
        niche=site.get("niche") or "produits Silver Economy",
        countries=", ".join(site.get("selected_countries") or ["FR"]),
        flagship=ctx["flagship"],
        benefits_hint=ctx["benefits_hint"],
        brand_voice=ctx["brand_voice"],
        pricing_hint=ctx["pricing_hint"],
        tweak=data.tweak or "aucune (défaut)",
        slug=_slugify(site.get("name")),
    )

    job_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    await db.design_jobs.insert_one({
        "id": job_id,
        "site_id": site_id,
        "user_id": user.get("id"),
        "status": "running",
        "with_logo": bool(data.with_logo),
        "tweak": data.tweak or "",
        "created_at": now,
    })

    async def _run():
        try:
            session = f"design-{site_id}-{uuid.uuid4().hex[:6]}"
            # Bloc 1 — endpoint legacy brand+sections. Premium pour qualité DNA.
            design = await _claude_json(SYSTEM, user_prompt, session, quality_tier="premium")
            if data.with_logo:
                logo_prompt = design.get("brand", {}).get("logo_style_prompt") or \
                    f"{site.get('niche')} brand, warm colors"
                logo_url = await _nano_banana_logo(logo_prompt, site_id)
                if logo_url:
                    design.setdefault("brand", {})["logo_url"] = logo_url
            design = _inject_legal(design, site)
            design["generated_at"] = datetime.now(timezone.utc).isoformat()
            design["generated_by"] = user.get("id")
            design["tweak"] = data.tweak or ""
            design["published"] = False
            await db.sites.update_one(
                {"id": site_id},
                {"$set": {"design": design, "updated_at": design["generated_at"]}},
            )
            await db.design_jobs.update_one(
                {"id": job_id},
                {"$set": {"status": "done", "finished_at": datetime.now(timezone.utc).isoformat()}},
            )
        except HTTPException as he:
            await db.design_jobs.update_one(
                {"id": job_id},
                {"$set": {"status": "failed", "error": he.detail, "finished_at": datetime.now(timezone.utc).isoformat()}},
            )
        except Exception as e:
            logger.exception("Design job failed")
            await db.design_jobs.update_one(
                {"id": job_id},
                {"$set": {"status": "failed", "error": str(e)[:300], "finished_at": datetime.now(timezone.utc).isoformat()}},
            )

    asyncio.create_task(_run())
    return {"ok": True, "job_id": job_id, "status": "running"}


@router.get("/sites/{site_id}/design/generate/status")
async def generate_design_status(site_id: str, user: dict = Depends(get_current_user)):
    """Returns the status of the latest design generation job for this site."""
    await _check_site_access(site_id, user)
    job = await db.design_jobs.find_one(
        {"site_id": site_id}, {"_id": 0}, sort=[("created_at", -1)]
    )
    return job or {"status": "idle"}


class RegenInput(BaseModel):
    tweak: Optional[str] = ""


REGEN_SECTIONS = {"hero", "brand", "benefits", "faq", "testimonials", "about", "contact", "footer", "seo", "logo"}


@router.post("/sites/{site_id}/design/regenerate/{section}")
async def regenerate_section(site_id: str, section: str, data: RegenInput, user: dict = Depends(get_current_user)):
    await _check_site_access(site_id, user)
    if section not in REGEN_SECTIONS:
        raise HTTPException(status_code=400, detail=f"Section invalide. Possible : {', '.join(sorted(REGEN_SECTIONS))}")
    site = await db.sites.find_one({"id": site_id}, {"_id": 0})
    if not site:
        raise HTTPException(status_code=404, detail="Site introuvable")
    current = site.get("design") or {}

    # Régénération logo seul
    if section == "logo":
        current_brand = current.get("brand") or {}
        prompt = data.tweak or current_brand.get("logo_style_prompt") or f"{site.get('niche','')} brand logo"
        url = await _nano_banana_logo(prompt, site_id)
        if not url:
            raise HTTPException(status_code=502, detail="Génération logo échouée, réessaye.")
        current_brand["logo_url"] = url
        current["brand"] = current_brand
        current["updated_at"] = datetime.now(timezone.utc).isoformat()
        await db.sites.update_one({"id": site_id}, {"$set": {"design": current}})
        return {"ok": True, "section": "logo", "logo_url": url}

    # Régénération d'une section JSON via Claude
    ctx = await _gather_context(site)
    tweak_txt = data.tweak or ""
    section_directive = (
        f'{tweak_txt} | REGENERE UNIQUEMENT la section "{section}" '
        f"(renvoie le JSON complet mais tu peux copier les autres sections du contexte si utiles)"
    )
    base_prompt = USER_TMPL.format(
        name=site.get("name") or "Boutique",
        niche=site.get("niche") or "produits Silver Economy",
        countries=", ".join(site.get("selected_countries") or ["FR"]),
        flagship=ctx["flagship"],
        benefits_hint=ctx["benefits_hint"],
        brand_voice=ctx["brand_voice"],
        pricing_hint=ctx["pricing_hint"],
        tweak=section_directive,
        slug=_slugify(site.get("name")),
    )
    current_json = json.dumps(current.get(section, {}), ensure_ascii=False, indent=2)[:1500]
    sub_prompt = (
        f"{base_prompt}\n\n"
        f"Contexte actuel de la section « {section} » :\n{current_json}\n"
    )
    session = f"design-regen-{section}-{site_id}-{uuid.uuid4().hex[:6]}"
    full = await _claude_json(SYSTEM, sub_prompt, session, timeout=120)
    new_section = full.get(section)
    if new_section is None:
        raise HTTPException(status_code=502, detail=f"L'IA n'a pas retourné la section {section}")
    current[section] = new_section
    current["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.sites.update_one({"id": site_id}, {"$set": {"design": current}})
    return {"ok": True, "section": section, section: new_section}


@router.post("/sites/{site_id}/design/publish")
async def publish_design(site_id: str, publish: bool = True, user: dict = Depends(get_current_user)):
    await _check_site_access(site_id, user)
    site = await db.sites.find_one({"id": site_id}, {"_id": 0, "design": 1})
    if not site or not site.get("design"):
        raise HTTPException(status_code=400, detail="Aucun design à publier. Génère d'abord ton site.")
    now = datetime.now(timezone.utc).isoformat()
    await db.sites.update_one(
        {"id": site_id},
        {"$set": {
            "design.published": bool(publish),
            "design.published_at": now if publish else None,
            "updated_at": now,
        }},
    )
    return {"ok": True, "published": bool(publish)}


class LogoUrlInput(BaseModel):
    logo_url: str = Field(..., min_length=3, max_length=2048)


class FooterBgInput(BaseModel):
    background_url: Optional[str] = Field(None, max_length=2048)


@router.post("/sites/{site_id}/design/brand/logo")
async def set_brand_logo(site_id: str, data: LogoUrlInput, user: dict = Depends(get_current_user)):
    """Permet au Concepteur d'uploader son propre logo (via /uploads/image) puis
    d'associer l'URL à design.brand.logo_url."""
    await _check_site_access(site_id, user)
    now = datetime.now(timezone.utc).isoformat()
    await db.sites.update_one(
        {"id": site_id},
        {"$set": {"design.brand.logo_url": data.logo_url, "updated_at": now}},
    )
    return {"ok": True, "logo_url": data.logo_url}


@router.post("/sites/{site_id}/design/footer/background")
async def set_footer_background(site_id: str, data: FooterBgInput, user: dict = Depends(get_current_user)):
    """Permet au Concepteur de définir (ou reset à None) l'image de fond du
    footer. Accepte une URL absolue (Unsplash, CDN) ou une URL relative de
    `/api/uploads/...`."""
    await _check_site_access(site_id, user)
    now = datetime.now(timezone.utc).isoformat()
    update = {"$set": {"design.updated_at": now}}
    if data.background_url:
        update["$set"]["design.footer.background_url"] = data.background_url
    else:
        update["$unset"] = {"design.footer.background_url": ""}
    await db.sites.update_one({"id": site_id}, update)
    return {"ok": True, "background_url": data.background_url or None}



# ================== PUBLIC ================== #

@router.get("/public/sites/{site_id}/design")
async def public_design(site_id: str):
    """Lu par le storefront. Retourne uniquement si published=true, sinon design par défaut."""
    site = await db.sites.find_one({"id": site_id}, {"_id": 0, "design": 1, "name": 1, "niche": 1})
    if not site:
        raise HTTPException(status_code=404, detail="Site introuvable")
    design = site.get("design") or {}
    if not design.get("published"):
        return {"published": False, "design": None}
    return {"published": True, "design": design}


class ContactInput(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    email: EmailStr
    phone: Optional[str] = ""
    subject: Optional[str] = ""
    message: str = Field(..., min_length=5, max_length=4000)


@router.post("/public/sites/{site_id}/contact")
async def public_contact(site_id: str, data: ContactInput):
    site = await db.sites.find_one({"id": site_id}, {"_id": 0, "id": 1, "name": 1, "operator_id": 1})
    if not site:
        raise HTTPException(status_code=404, detail="Site introuvable")
    doc = {
        "id": str(uuid.uuid4()),
        "site_id": site_id,
        "site_name": site.get("name"),
        "operator_id": site.get("operator_id"),
        "name": data.name,
        "email": data.email,
        "phone": data.phone or "",
        "subject": data.subject or "",
        "message": data.message,
        "status": "new",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.leads.insert_one(dict(doc))
    doc.pop("_id", None)
    return {"ok": True, "lead_id": doc["id"]}


# Bloc 1 sous-chantier 3 — RGPD audit log
class ConsentInput(BaseModel):
    essentiels: bool = True
    analytics: bool = False
    marketing: bool = False
    personnalisation: bool = False
    decided_at: Optional[str] = None
    version: int = 1


@router.post("/public/sites/{site_id}/consent")
async def public_consent(site_id: str, data: ConsentInput, request: Request):
    """RGPD audit log — every consent decision is persisted server-side so
    we can prove (in case of CNIL audit) that we honored the user's choice.
    No PII is collected (we don't even store IP — just a hashed visitor token
    via the existing analytics flow if the user ever buys something).
    """
    site = await db.sites.find_one({"id": site_id}, {"_id": 0, "id": 1})
    if not site:
        raise HTTPException(status_code=404, detail="Site introuvable")
    # Truncate user-agent for sanity
    ua = (request.headers.get("user-agent") or "")[:200]
    doc = {
        "id": str(uuid.uuid4()),
        "site_id": site_id,
        "essentiels": True,    # always true regardless of input (locked)
        "analytics": bool(data.analytics),
        "marketing": bool(data.marketing),
        "personnalisation": bool(data.personnalisation),
        "version": int(data.version or 1),
        "user_agent": ua,
        "decided_at": data.decided_at or datetime.now(timezone.utc).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.consent_logs.insert_one(dict(doc))
    return {"ok": True}


@router.get("/sites/{site_id}/leads")
async def list_leads(site_id: str, user: dict = Depends(get_current_user)):
    await _check_site_access(site_id, user)
    items = await db.leads.find({"site_id": site_id}, {"_id": 0}).sort("created_at", -1).limit(200).to_list(200)
    return items



# ====================== SPRINT 23 — PROMPT STUDIO ====================== #
STUDIO_SYSTEM = """You are a senior e-commerce brand strategist and UX writer for \
a premium direct-to-consumer boutique. You write copy in the language of the \
target customer (default fr). Your tone is Apple/Dyson: clean, confident, \
product-focused, benefit-driven, honest. No filler, no fluff, no clichés. \
Always output STRICT JSON only (no markdown, no backticks)."""


SECTION_SCHEMAS = {
    "positioning": {
        "json_schema": ("{\"brand_promise\": \"1 sentence\", "
                        "\"unique_selling_points\": [\"3-5 short USPs\"], "
                        "\"voice_attributes\": [\"3-4 adjectives\"], "
                        "\"target_customer\": \"short\", "
                        "\"elevator_pitch\": \"2 sentences max\"}"),
    },
    "identity": {
        "json_schema": ("{\"brand_name\": \"<20 chars\", "
                        "\"tagline\": \"<60 chars\", "
                        "\"brand_story\": \"2-3 sentences\"}"),
    },
    "hero": {
        "json_schema": ("{\"title\": \"<60 chars\", "
                        "\"subtitle\": \"<140 chars\", "
                        "\"cta_label\": \"2-3 words\", "
                        "\"trust_line\": \"<80 chars\"}"),
    },
    "benefits": {
        "json_schema": ("{\"items\": [{\"title\": \"3-5 words\", "
                        "\"description\": \"1-2 sentences\", "
                        "\"icon\": \"ShieldCheck|Truck|Clock|Heart|Star|Leaf|Package|Headset\"}]}"),
    },
    "faq": {
        "json_schema": ("{\"items\": [{\"question\": \"...\", \"answer\": \"1-3 sentences\"}]}"),
    },
    "seo": {
        "json_schema": ("{\"title\": \"<60 chars\", "
                        "\"description\": \"<155 chars\", "
                        "\"keywords\": [\"5-10 keywords\"]}"),
    },
    "testimonials": {
        "json_schema": ("{\"items\": [{\"name\": \"First L.\", "
                        "\"location\": \"city\", \"rating\": 5, "
                        "\"text\": \"1-2 sentences\"}]}"),
    },
    "product_narrative": {
        "json_schema": ("{\"headline\": \"<60 chars\", "
                        "\"subheadline\": \"<140 chars\", "
                        "\"sections\": [{\"title\": \"...\", "
                        "\"body\": \"1-2 paragraphs\", "
                        "\"bullet_points\": [\"3-4 concrete points\"]}], "
                        "\"tech_specs\": [{\"label\": \"...\", \"value\": \"...\"}], "
                        "\"faq\": [{\"question\": \"...\", \"answer\": \"...\"}]}"),
    },
}


async def _site_context_block(site_id: str) -> str:
    site = await db.sites.find_one({"id": site_id}, {"_id": 0})
    if not site:
        return ""
    ctx = {
        "site_name": site.get("name"),
        "niche": site.get("niche"),
        "countries": site.get("selected_countries") or ["FR"],
        "design": site.get("design") or {},
    }
    analysis_id = site.get("analysis_id")
    if analysis_id:
        a = await db.niche_analyses.find_one({"id": analysis_id}, {"_id": 0})
        if a:
            ax = a.get("analysis") or {}
            ctx["analysis"] = {
                "product": a.get("product_input"),
                "persona": a.get("persona"),
                "verdict": ax.get("verdict"),
                "verdict_reasoning": ax.get("verdict_reasoning"),
                "usp_angles": ax.get("usp_angles") or ax.get("positioning_angles"),
                "key_keywords": [kw for c in ctx["countries"]
                                 for kw in (ax.get("keywords_by_country", {}).get(c, {})
                                            .get("transactional", []) or [])[:6]],
                "competitors": ax.get("competitors_by_country") or {},
            }
    products = await db.products.find(
        {"site_id": site_id},
        {"_id": 0, "name": 1, "description": 1, "price": 1, "cost_price_ht": 1}
    ).limit(10).to_list(10)
    ctx["products"] = [{
        "name": (p.get("name") or {}).get("fr") or "",
        "description_excerpt": ((p.get("description") or {}).get("fr") or "")[:400],
        "price_eur": p.get("price"),
    } for p in products]
    return json.dumps(ctx, ensure_ascii=False, indent=2)[:6000]


DEFAULT_PROMPTS = {
    "positioning": ("En te basant sur le CONTEXT (niche, analyse, persona, produits), "
                    "rédige le positionnement de la marque. Focus bénéfice utilisateur "
                    "(jamais feature). Ton premium mais accessible. USPs spécifiques à "
                    "cette niche. Voix de marque : 3-4 adjectifs cohérents."),
    "identity": ("Propose un NOUVEAU nom de marque unique, prononçable, mémorable "
                 "(pas 'Altiaro'), un tagline bénéfice <60 chars, et une "
                 "brand story en 2-3 phrases."),
    "hero": ("Rédige le hero homepage, style Apple/Dyson : headline punchy bénéfice "
             "principal, subtitle explicative, CTA action courte, trust line."),
    "benefits": ("Génère 4 blocs bénéfices spécifiques à ce persona (pas 'livraison "
                 "rapide' générique). Choisis l'icône la plus pertinente."),
    "faq": ("Génère 7 questions RÉELLEMENT posées par ces clients : 3 produit, 2 "
            "livraison/paiement, 2 retour/SAV. Réponses courtes, rassurantes."),
    "seo": ("Rédige les meta SEO homepage : title <60 chars avec mot-clé principal, "
            "description <155 chars bénéfice+CTA, 5-10 keywords transactionnels."),
    "testimonials": ("Génère 5 témoignages réalistes : noms/villes cohérents pays "
                     "cible, 1-2 phrases spécifiques, 5 étoiles, ton naturel."),
    "product_narrative": ("Refonte COMPLÈTE et narrative du produit (Apple-style). "
                          "Ne copie jamais le texte CJ/AE source. Storytelling autour "
                          "des bénéfices, sections scrollables, tech_specs clean, FAQ."),
}


class PromptRunInput(BaseModel):
    section: str
    prompt: Optional[str] = None
    product_id: Optional[str] = None  # only for product_narrative


@router.post("/sites/{site_id}/design/prompt/run")
async def prompt_run(site_id: str, data: PromptRunInput,
                     user: dict = Depends(get_current_user)):
    await _check_site_access(site_id, user)
    section = (data.section or "").lower()
    if section not in SECTION_SCHEMAS:
        raise HTTPException(400, f"Section inconnue : {section}")
    context = await _site_context_block(site_id)
    # For product_narrative, add the specific product context
    if section == "product_narrative" and data.product_id:
        product = await db.products.find_one(
            {"id": data.product_id, "site_id": site_id}, {"_id": 0}
        )
        if product:
            product_ctx = {
                "name": (product.get("name") or {}).get("fr"),
                "description": (product.get("description") or {}).get("fr"),
                "price": product.get("price"),
                "cost": product.get("cost_price_ht"),
            }
            context += "\n\n=== TARGET PRODUCT ===\n" + json.dumps(
                product_ctx, ensure_ascii=False, indent=2
            )
    schema = SECTION_SCHEMAS[section]
    user_prompt = data.prompt or DEFAULT_PROMPTS.get(section, "Générer du contenu.")
    full_prompt = (f"=== CONTEXT ===\n{context}\n\n"
                   f"=== TASK ===\n{user_prompt}\n\n"
                   f"=== OUTPUT SCHEMA ===\n{schema['json_schema']}\n\n"
                   f"Return STRICT JSON only, no prose.")
    result = await _claude_json(
        STUDIO_SYSTEM, full_prompt,
        session_id=f"studio-{site_id}-{section}-{uuid.uuid4().hex[:6]}",
        timeout=120,
    )
    return {"section": section, "data": result, "prompt_used": user_prompt}


class PromptApplyInput(BaseModel):
    section: str
    data: dict
    product_id: Optional[str] = None


@router.post("/sites/{site_id}/design/prompt/apply")
async def prompt_apply(site_id: str, data: PromptApplyInput,
                       user: dict = Depends(get_current_user)):
    await _check_site_access(site_id, user)
    section = (data.section or "").lower()
    if section not in SECTION_SCHEMAS:
        raise HTTPException(400, "Section inconnue")
    # product_narrative → write into product, not site
    if section == "product_narrative" and data.product_id:
        await db.products.update_one(
            {"id": data.product_id, "site_id": site_id},
            {"$set": {"narrative": data.data,
                      "updated_at": datetime.now(timezone.utc).isoformat()}},
        )
        return {"ok": True, "section": section, "product_id": data.product_id}
    now = datetime.now(timezone.utc).isoformat()
    # identity → patch brand_name/tagline + create a brand_story
    if section == "identity":
        brand_name_clean = _sanitize_brand_text(data.data.get("brand_name") or "", max_len=40)
        tagline_clean = _sanitize_brand_text(data.data.get("tagline") or "", max_len=80)
        update = {
            "design.brand.name": brand_name_clean,
            "design.brand.tagline": tagline_clean,
            "design.brand.story": data.data.get("brand_story"),
            "design.updated_at": now,
        }
        if brand_name_clean:
            update["design.brand.logo_text"] = brand_name_clean
        await db.sites.update_one(
            {"id": site_id},
            {"$set": update},
        )
        return {"ok": True, "section": section}
    await db.sites.update_one(
        {"id": site_id},
        {"$set": {f"design.{section}": data.data, "design.updated_at": now}},
    )
    return {"ok": True, "section": section}


class PaletteSuggestInput(BaseModel):
    mood: Optional[str] = None


@router.post("/sites/{site_id}/design/palette/suggest")
async def palette_suggest(site_id: str, data: PaletteSuggestInput,
                          user: dict = Depends(get_current_user)):
    await _check_site_access(site_id, user)
    context = await _site_context_block(site_id)
    mood_hint = f" The user prefers a {data.mood} mood." if data.mood else ""
    user_prompt = (f"=== CONTEXT ===\n{context}\n\n"
                   f"=== TASK ===\nPropose 3 distinct colour palettes for this "
                   f"premium D2C boutique.{mood_hint} High contrast, senior-friendly, "
                   f"Apple/Dyson (lots of neutrals + 1 statement accent).\n\n"
                   f"=== OUTPUT SCHEMA ===\n"
                   f"{{\"palettes\": [{{"
                   f"\"name\": \"3-5 words\", "
                   f"\"description\": \"1 sentence mood\", "
                   f"\"primary_color\": \"#HEXCOLOR\", "
                   f"\"secondary_color\": \"#HEXCOLOR\", "
                   f"\"background_color\": \"#HEXCOLOR\", "
                   f"\"text_color\": \"#HEXCOLOR\", "
                   f"\"font_heading\": \"Fraunces|Playfair Display|Cormorant|Canela|DM Serif Display\", "
                   f"\"font_body\": \"Inter|Manrope|DM Sans|IBM Plex Sans\""
                   f"}}]}}\n\nReturn STRICT JSON only.")
    result = await _claude_json(
        STUDIO_SYSTEM, user_prompt,
        session_id=f"palette-{site_id}-{uuid.uuid4().hex[:6]}",
        timeout=90,
    )
    palettes = (result or {}).get("palettes") or []
    if not palettes:
        raise HTTPException(502, "L'IA n'a pas retourné de palettes. Réessaye.")
    return {"palettes": palettes[:3]}


class PaletteApplyInput(BaseModel):
    primary_color: str
    secondary_color: Optional[str] = None
    background_color: Optional[str] = None
    text_color: Optional[str] = None
    font_heading: Optional[str] = None
    font_body: Optional[str] = None


@router.post("/sites/{site_id}/design/palette/apply")
async def palette_apply(site_id: str, data: PaletteApplyInput,
                        user: dict = Depends(get_current_user)):
    await _check_site_access(site_id, user)
    patch = {}
    for k, v in data.dict(exclude_none=True).items():
        patch[f"design.brand.{k}"] = v
    patch["design.updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.sites.update_one({"id": site_id}, {"$set": patch})
    return {"ok": True}


# =====================================================================
# AI Field Generator — generate a single brand field with Claude
# =====================================================================
FIELD_PROMPTS = {
    "name": "Propose UN SEUL nom de marque court (1-3 mots, max 28 caractères), mémorable, qui sonne Silver Economy premium. Évite les clichés 'senior'. Réponds EXCLUSIVEMENT avec le nom final, sans guillemets, sans markdown, sans préambule, sans explication.",
    "tagline": "Propose UNE SEULE baseline ≤ 80 caractères qui capture l'essence de la marque. Emotion + bénéfice clé. Réponds EXCLUSIVEMENT avec la baseline finale, sans guillemets, sans markdown, sans préambule.",
    "voice": "Décris le ton de voix idéal (chaleureux/rassurant/expert/premium/etc.) en 1 phrase ≤ 150 car. Réponds EXCLUSIVEMENT avec la phrase finale, sans préambule.",
    "story": "Rédige une histoire de marque en 2-3 paragraphes (≤ 400 car.) qui inspire confiance et crée un lien émotionnel. Réponds directement, sans titre markdown ni préambule.",
    "font_pair": "Propose une paire de Google Fonts (heading + body) adaptée au ton. Format JSON : {\"heading\": \"...\", \"body\": \"...\", \"rationale\": \"pourquoi ce choix\"}",
    "palette": "Propose une palette 5 couleurs (primary, secondary, accent, background, text) en hex, cohérente avec la niche & l'audience senior. Format JSON : {\"primary\":\"#...\",\"secondary\":\"#...\",\"accent\":\"#...\",\"background\":\"#...\",\"text\":\"#...\",\"rationale\":\"...\"}",
}


class AiFieldInput(BaseModel):
    field: str  # "name" | "tagline" | "voice" | "story" | "font_pair" | "palette"
    tweak: Optional[str] = ""  # user hint e.g. "plus luxe minimal"


@router.post("/sites/{site_id}/design/ai-field")
async def ai_field(site_id: str, body: AiFieldInput, user: dict = Depends(get_current_user)):
    """Generate a single brand field (name, tagline, voice, story, palette, font_pair) via Claude."""
    await _check_site_access(site_id, user)
    if body.field not in FIELD_PROMPTS:
        raise HTTPException(400, f"Champ invalide. Possible : {', '.join(FIELD_PROMPTS)}")
    site = await db.sites.find_one({"id": site_id}, {"_id": 0})
    if not site:
        raise HTTPException(404, "Site introuvable")

    brand = (site.get("design") or {}).get("brand") or {}
    niche = site.get("niche") or "produits Silver Economy"
    current_name = brand.get("name") or site.get("name") or ""
    current_voice = brand.get("voice") or "chaleureux, rassurant, expert"

    directive = FIELD_PROMPTS[body.field]
    hint = body.tweak or ""
    want_json = body.field in {"palette", "font_pair"}

    system = (
        "Tu es un directeur artistique spécialisé Silver Economy (65+). Tu produis des éléments de marque "
        "premium, chaleureux et accessibles. Réponds TOUJOURS en français, sans préambule, sans guillemets superflus."
    )
    prompt = (
        f"Niche : {niche}\n"
        f"Marque actuelle : {current_name or '(aucun nom encore)'}\n"
        f"Ton de voix actuel : {current_voice}\n"
        f"Demande de l'utilisateur : {hint or '(aucune — propose ta meilleure idée)'}\n\n"
        f"Tâche : {directive}\n\n"
        + ("Réponds UNIQUEMENT avec le JSON demandé, sans commentaire." if want_json else "Réponds avec uniquement le texte final, rien d'autre.")
    )
    session = f"ai-field-{body.field}-{site_id}-{uuid.uuid4().hex[:6]}"
    # Bloc 1 — brand identity field regeneration (name/tagline/voice/story/
    # palette/font_pair) → quality_tier="premium" : ce sont des éléments de
    # DNA réutilisés partout, qualité non négociable.
    try:
        if want_json:
            data = await _claude_json(system, prompt, session, timeout=60, quality_tier="premium")
            # persist depending on field
            patch = {}
            if body.field == "palette":
                for k in ("primary", "secondary", "accent", "background", "text"):
                    v = data.get(k)
                    if isinstance(v, str) and v.startswith("#"):
                        patch[f"design.brand.{k}_color"] = v
                        patch[f"design.brand.palette.{k}"] = v
            elif body.field == "font_pair":
                if data.get("heading"):
                    patch["design.brand.font_heading"] = str(data["heading"])[:60]
                if data.get("body"):
                    patch["design.brand.font_body"] = str(data["body"])[:60]
            if patch:
                patch["design.updated_at"] = datetime.now(timezone.utc).isoformat()
                await db.sites.update_one({"id": site_id}, {"$set": patch})
            return {"ok": True, "field": body.field, "value": data, "rationale": data.get("rationale")}
        else:
            from services.llm_resilience import safe_claude_text, LLMUnavailableError  # type: ignore
            try:
                raw = await safe_claude_text(
                    system, prompt,
                    quality_tier="premium",  # Bloc 1 — brand DNA, qualité non négociable
                    session_id=session,
                    timeout=90,
                )
            except LLMUnavailableError as e:
                logger.warning(f"[ai-field] LLM unavailable: {e.last_error}")
                raise HTTPException(
                    status_code=503,
                    detail="IA temporairement indisponible (proxy upstream KO). Réessaye dans quelques minutes.",
                )
            txt = str(raw or "").strip().strip('"').strip("'").strip()
            # Sanitize plain-text brand fields (name/tagline/voice/story) — strip markdown,
            # preambles, quotes. Claude sometimes returns a full explanation with bold tokens
            # and markdown headings despite the "reply with only the final text" instruction.
            max_lens = {"name": 40, "tagline": 80, "voice": 150, "story": 500}
            txt = _sanitize_brand_text(txt, max_len=max_lens.get(body.field, 200))
            if not txt:
                raise HTTPException(status_code=502, detail="IA a renvoyé une réponse vide. Réessaye.")
            # Persist
            field_key = body.field
            db_field = {"name": "name", "tagline": "tagline", "voice": "voice", "story": "story"}[field_key]
            update = {
                f"design.brand.{db_field}": txt,
                "design.updated_at": datetime.now(timezone.utc).isoformat(),
            }
            # When the brand name is regenerated, mirror it to logo_text so the header/footer
            # text logo stays in sync (otherwise stale logo_text from older runs leaks into the UI).
            if field_key == "name":
                update["design.brand.logo_text"] = txt
            await db.sites.update_one(
                {"id": site_id},
                {"$set": update},
            )
            return {"ok": True, "field": body.field, "value": txt}
    except Exception as e:
        logger.exception("[ai-field] %s failed", body.field)
        raise HTTPException(status_code=502, detail=f"IA indisponible : {str(e)[:120]}")


# =====================================================================
# AI Navigation Optimizer — build a conversion-optimized nav
# =====================================================================
@router.post("/sites/{site_id}/design/wizard-suggestions")
async def wizard_suggestions(site_id: str, user: dict = Depends(get_current_user)):
    """One-shot AI brainstorm for the BrandWizard Step 1 pre-fill: 3 brand names,
    1 tagline, 1 mission, 1 voice — all sanitized, computed from the site's niche
    + imported products so suggestions actually fit the shop.
    Returns 402 if the Universal Key budget is exhausted so the UI can show a clear
    'recharge your key' banner instead of a generic error."""
    await _check_site_access(site_id, user)
    site = await db.sites.find_one({"id": site_id}, {"_id": 0})
    if not site:
        raise HTTPException(404, "Site introuvable")

    # Gather product context for contextually relevant names (fauteuils releveurs
    # → "Soléa / Alvenar" ; loupes → "Lueur / Éclaira"…).
    niche = site.get("niche") or site.get("niche_keyword") or "produits Silver Economy"
    products = await db.products.find(
        {"site_id": site_id, "status": "active"},
        {"_id": 0, "name": 1, "category": 1, "price": 1},
    ).limit(8).to_list(8)
    product_ctx = [
        {
            "name": (p.get("name") or {}).get("fr") if isinstance(p.get("name"), dict) else str(p.get("name") or ""),
            "category": p.get("category"),
            "price": p.get("price"),
        }
        for p in products if p.get("name")
    ]

    system = (
        "Tu es directeur artistique Silver Economy (60+ et aidants) pour des boutiques e-commerce premium. "
        "Tu proposes des identités de marque chaleureuses, dignes, sans clichés gériatriques. "
        "Réponds TOUJOURS en français, en JSON strict, sans markdown, sans préambule."
    )
    prompt = (
        f"Niche de la boutique : {niche}\n"
        f"Nom technique actuel du site (à ignorer si générique type 'Test XX') : {site.get('name')}\n"
        f"Produits importés ({len(product_ctx)}) : {json.dumps(product_ctx, ensure_ascii=False)[:800]}\n\n"
        "Propose TROIS noms de marque distincts + UNE tagline + UNE mission + UNE voix de marque, "
        "le tout cohérent avec la niche ci-dessus et adapté à un public 60+ aisé (Silver Economy).\n\n"
        "Contraintes strictes :\n"
        "- `names` : 3 noms distincts, 1-3 mots, max 24 caractères chacun. Noms imaginés, pas descriptifs "
        "(évite 'Confort Plus', 'Senior Shop', 'Fauteuils Premium'). Inspiration : maisons françaises "
        "(Hermès, Le Creuset, Diptyque), noms propres, lieux, mots latins doux.\n"
        "- `tagline` : ≤ 80 caractères, émotion + bénéfice clé.\n"
        "- `mission` : 1-2 phrases, ≤ 220 caractères. Pourquoi la marque existe.\n"
        "- `voice` : ≤ 140 caractères. Ex. 'Chaleureux, expert, tutoiement, jamais condescendant'.\n\n"
        'Renvoie UNIQUEMENT ce JSON :\n'
        '{"names":["...","...","..."],"tagline":"...","mission":"...","voice":"..."}'
    )
    session = f"wizard-suggest-{site_id}-{uuid.uuid4().hex[:6]}"
    try:
        data = await _claude_json(system, prompt, session, timeout=60)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("[wizard-suggestions] failed")
        raise HTTPException(status_code=502, detail=f"IA indisponible : {str(e)[:140]}")

    # Sanitize every field defensively (Claude sometimes still sneaks markdown into JSON strings).
    names = [_sanitize_brand_text(str(n), max_len=24) for n in (data.get("names") or [])[:3] if n]
    names = [n for n in names if n]
    return {
        "names": names or ["Aurélia", "Clarelle", "Soléa"],
        "tagline": _sanitize_brand_text(str(data.get("tagline") or ""), max_len=80),
        "mission": _sanitize_brand_text(str(data.get("mission") or ""), max_len=280),
        "voice": _sanitize_brand_text(str(data.get("voice") or ""), max_len=160) or "chaleureux et rassurant, premium",
    }


# =====================================================================
# AI Homepage Enrichment — generate press_mentions, founder_story, manifesto,
# editorial, values in ONE call. The Concepteur presses one button and the
# homepage goes from "pretty with defaults" to "fully personalized".
# =====================================================================
@router.post("/sites/{site_id}/design/ai-enrich-homepage")
async def ai_enrich_homepage(site_id: str, user: dict = Depends(get_current_user)):
    """One-shot AI enrichment of the storefront's contextual sections."""
    await _check_site_access(site_id, user)
    site = await db.sites.find_one({"id": site_id}, {"_id": 0})
    if not site:
        raise HTTPException(404, "Site introuvable")

    brand = (site.get("design") or {}).get("brand") or {}
    brand_name = _sanitize_brand_text(brand.get("logo_text") or brand.get("name") or "", max_len=40) or site.get("name", "")
    tagline = _sanitize_brand_text(brand.get("tagline") or "", max_len=120)
    voice = (brand.get("voice") or "chaleureux et rassurant, premium")[:200]
    niche = site.get("niche") or site.get("niche_keyword") or "produits Silver Economy"

    products = await db.products.find(
        {"site_id": site_id, "status": {"$ne": "deleted"}},
        {"_id": 0, "name": 1, "category": 1},
    ).limit(8).to_list(8)
    product_names = [
        (p.get("name") or {}).get("fr") if isinstance(p.get("name"), dict) else str(p.get("name") or "")
        for p in products if p.get("name")
    ][:5]

    system = (
        "Tu es directeur éditorial Silver Economy (60+ et aidants) pour une boutique premium française. "
        "Tu rédiges du contenu marketing élégant, digne, sans clichés gériatriques — ton chaleureux mais pas condescendant. "
        "Réponds EXCLUSIVEMENT en français, en JSON strict, sans markdown, sans préambule."
    )
    prompt = (
        f"Marque : « {brand_name} »\n"
        f"Tagline : « {tagline} »\n"
        f"Voix : {voice}\n"
        f"Niche : {niche}\n"
        f"Produits phares ({len(product_names)}) : {json.dumps(product_names, ensure_ascii=False)}\n\n"
        "Produis UN SEUL JSON avec ces 6 blocs :\n\n"
        "1) `press_mentions` : tableau de 6 médias français crédibles. Format : [{\"name\":\"...\"}].\n\n"
        "2) `founder_story` : portrait fictif cohérent. Format : "
        "{\"name\":\"Prénom Nom français élégant\", \"role\":\"Fondateur ou Fondatrice\", "
        "\"quote\":\"citation poignante 40-70 mots — mentionne un grand-parent ou un déclic\", "
        "\"signature\":\"Prénom L.\"}.\n\n"
        "3) `manifesto` : {\"eyebrow\":\"Manifeste\", "
        "\"headline\":\"statement 12-22 mots qui capture la conviction\", "
        "\"kicker\":\"paragraphe 50-90 mots humain, refus des clichés\"}.\n\n"
        "4) `editorial` : citation magazine. Format : "
        "{\"title\":\"4-8 mots\", \"body\":\"250-400 car. usage concret en contexte lifestyle\"}.\n\n"
        "5) `values` : 4 piliers. Format : "
        "[{\"title\":\"1-3 mots\", \"description\":\"1 phrase 15-25 mots\"}, ...].\n\n"
        "6) `brand_process` : 4 étapes du cycle de vie produit (sélection, fabrication, contrôle, logistique). "
        "Format : [{\"icon\":\"Leaf|HandsClapping|ShieldCheck|Tree\", \"kicker\":\"01 · Sélection\", "
        "\"title\":\"titre 4-8 mots\", \"body\":\"35-60 mots qui décrit l'engagement\"}].\n\n"
        "Renvoie UNIQUEMENT ce JSON valide."
    )
    session = f"enrich-{site_id}-{uuid.uuid4().hex[:6]}"
    try:
        data = await _claude_json(system, prompt, session, timeout=90)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("[ai-enrich-homepage] failed")
        raise HTTPException(status_code=502, detail=f"IA indisponible : {str(e)[:140]}")

    press = [{"name": _sanitize_brand_text(str(p.get("name") or ""), max_len=40)}
             for p in (data.get("press_mentions") or [])[:6] if p.get("name")]
    fs = data.get("founder_story") or {}
    fs_name = _sanitize_brand_text(str(fs.get("name") or ""), max_len=40) or "Camille Lefèvre"
    founder_story = {
        "name": fs_name,
        "role": _sanitize_brand_text(str(fs.get("role") or ""), max_len=40) or "Fondatrice",
        "quote": _sanitize_brand_text(str(fs.get("quote") or ""), max_len=500)
                 or "Cette maison est née d'une évidence familiale. Chaque produit est choisi avec la même attention qu'on réserverait à un proche.",
        "signature": _sanitize_brand_text(str(fs.get("signature") or ""), max_len=40)
                     or (fs_name.split(" ")[0] if fs_name else "Camille L."),
    }
    mf = data.get("manifesto") or {}
    manifesto = {
        "eyebrow": _sanitize_brand_text(str(mf.get("eyebrow") or ""), max_len=40) or "Manifeste",
        "headline": _sanitize_brand_text(str(mf.get("headline") or ""), max_len=240)
                    or "Bien vieillir chez soi n'est pas un luxe. C'est un droit.",
        "kicker": _sanitize_brand_text(str(mf.get("kicker") or ""), max_len=500)
                  or "Nous refusons la médiocrité. Nous refusons le paternalisme. Nous croyons qu'une belle vieillesse mérite de beaux objets.",
    }
    ed = data.get("editorial") or {}
    editorial = {
        "title": _sanitize_brand_text(str(ed.get("title") or ""), max_len=80),
        "body": _sanitize_brand_text(str(ed.get("body") or ""), max_len=500),
    }
    values = []
    for v in (data.get("values") or [])[:4]:
        title = _sanitize_brand_text(str(v.get("title") or ""), max_len=40)
        desc = _sanitize_brand_text(str(v.get("description") or ""), max_len=180)
        if title:
            values.append({"title": title, "description": desc})

    brand_process = []
    valid_icons = {"Leaf", "HandsClapping", "ShieldCheck", "Tree"}
    for i, s in enumerate((data.get("brand_process") or [])[:4]):
        title = _sanitize_brand_text(str(s.get("title") or ""), max_len=60)
        body = _sanitize_brand_text(str(s.get("body") or ""), max_len=240)
        kicker = _sanitize_brand_text(str(s.get("kicker") or ""), max_len=30) or f"{str(i+1).zfill(2)} · Étape"
        icon = s.get("icon") if s.get("icon") in valid_icons else ["Leaf", "HandsClapping", "ShieldCheck", "Tree"][i]
        if title:
            brand_process.append({"icon": icon, "kicker": kicker, "title": title, "body": body})

    now = datetime.now(timezone.utc).isoformat()
    await db.sites.update_one(
        {"id": site_id},
        {"$set": {
            "design.press_mentions": press,
            "design.founder_story": founder_story,
            "design.manifesto": manifesto,
            "design.editorial": editorial,
            "design.values": values,
            "design.brand_process": brand_process,
            "design.updated_at": now,
        }},
    )
    return {
        "ok": True,
        "enriched": {
            "press_mentions_count": len(press),
            "founder_story": True,
            "manifesto": True,
            "editorial": bool(editorial.get("title")),
            "values_count": len(values),
            "brand_process_count": len(brand_process),
        },
    }


# =====================================================================
# AI Navigation Optimizer — build a conversion-optimized nav
# =====================================================================
@router.post("/sites/{site_id}/navigation/ai-optimize")
async def ai_optimize_nav(site_id: str, user: dict = Depends(get_current_user)):
    """Uses Claude to build a sales-optimized navigation based on catalog."""
    await _check_site_access(site_id, user)
    products = await db.products.find(
        {"site_id": site_id, "status": "active"},
        {"_id": 0, "name": 1, "role": 1, "category": 1, "price": 1},
    ).to_list(300)
    collections = await db.collections.find(
        {"site_id": site_id},
        {"_id": 0, "name": 1, "slug": 1, "featured": 1},
    ).to_list(50)
    main_products = [p for p in products if p.get("role") != "upsell"]
    upsells = [p for p in products if p.get("role") == "upsell"]

    catalog_summary = {
        "main_count": len(main_products),
        "upsells_count": len(upsells),
        "collections": [{"name": c["name"], "slug": c["slug"], "featured": c.get("featured")} for c in collections],
        "sample_products": [
            {"name": (p.get("name", {}) or {}).get("fr", "") if isinstance(p.get("name"), dict) else str(p.get("name") or ""), "price": p.get("price")}
            for p in main_products[:10]
        ],
    }
    system = (
        "Tu es un expert CRO e-commerce Silver Economy. Tu construis une navigation HEADER "
        "et FOOTER optimisée pour la conversion : max 5 items header, hiérarchie claire, libellés "
        "courts et orientés valeur (ex: 'Fauteuils' > 'Nos produits'). Footer : liens utilitaires "
        "+ legal. Toujours pointer vers /collections/{slug} ou /shop si collection inexistante."
    )
    prompt = (
        "Catalogue :\n" + json.dumps(catalog_summary, ensure_ascii=False, indent=2) +
        "\n\nPropose UN JSON strict :\n"
        '{"header":[{"label":"...","href":"/...","external":false}, ...],'
        '"footer":[{"label":"...","href":"/...","external":false}, ...],'
        '"rationale":"explication courte"}'
    )
    session = f"ai-nav-{site_id}-{uuid.uuid4().hex[:6]}"
    try:
        data = await _claude_json(system, prompt, session, timeout=60)
        clean = {
            "header": [h for h in (data.get("header") or [])[:5] if h.get("label") and h.get("href")],
            "footer": [h for h in (data.get("footer") or [])[:8] if h.get("label") and h.get("href")],
        }
        # sanitize: ensure external is bool
        for bucket in ("header", "footer"):
            for it in clean[bucket]:
                it["external"] = bool(it.get("external"))
        await db.sites.update_one(
            {"id": site_id},
            {"$set": {"design.navigation": clean, "design.updated_at": datetime.now(timezone.utc).isoformat()}},
        )
        return {"ok": True, "navigation": clean, "rationale": data.get("rationale")}
    except Exception as e:
        logger.exception("[ai-nav] failed")
        raise HTTPException(502, f"IA indisponible : {str(e)[:120]}")


# =====================================================================
# AI Collections Suggester — propose collections based on catalog
# =====================================================================
@router.post("/sites/{site_id}/collections/ai-suggest")
async def ai_suggest_collections(site_id: str, user: dict = Depends(get_current_user)):
    """Proposes 3-5 collections from the active catalog. Does NOT create them —
    the user can pick and create via the existing POST endpoint."""
    await _check_site_access(site_id, user)
    products = await db.products.find(
        {"site_id": site_id, "status": "active", "role": {"$ne": "upsell"}},
        {"_id": 0, "id": 1, "name": 1, "category": 1, "price": 1},
    ).to_list(200)
    if not products:
        return {"suggestions": [], "message": "Importe au moins 2 produits principaux à l'étape 2."}

    catalog = [
        {
            "id": p["id"],
            "name": (p.get("name", {}) or {}).get("fr", "") if isinstance(p.get("name"), dict) else str(p.get("name") or ""),
            "price": p.get("price"),
        }
        for p in products[:50]
    ]
    system = (
        "Tu es un merchandiser Silver Economy. Tu regroupes les produits par usage/gamme en "
        "collections vendeuses : 3 à 5 collections max, nom court et évocateur (2-4 mots), "
        "description ≤ 120 car. Assigne chaque produit à UNE seule collection."
    )
    prompt = (
        "Catalogue :\n" + json.dumps(catalog, ensure_ascii=False, indent=2) +
        "\n\nPropose UN JSON strict :\n"
        '{"collections":[{"name":"...","description":"...","product_ids":["..."],"featured":true},...]}'
    )
    session = f"ai-col-{site_id}-{uuid.uuid4().hex[:6]}"
    try:
        data = await _claude_json(system, prompt, session, timeout=60)
        cleaned = []
        valid_ids = {p["id"] for p in products}
        for c in data.get("collections") or []:
            if not c.get("name"):
                continue
            cleaned.append({
                "name": str(c["name"])[:80],
                "description": str(c.get("description") or "")[:200],
                "product_ids": [pid for pid in (c.get("product_ids") or []) if pid in valid_ids],
                "featured": bool(c.get("featured")),
            })
        return {"suggestions": cleaned[:5]}
    except Exception as e:
        logger.exception("[ai-collections-suggest] failed")
        raise HTTPException(502, f"IA indisponible : {str(e)[:120]}")


# =====================================================================
# Backwards-compat: seed legal pages if empty
# =====================================================================
@router.post("/sites/{site_id}/design/seed-legal")
async def seed_legal_pages(site_id: str, user: dict = Depends(get_current_user)):
    """Force regeneration of legal pages (CGV, mentions, confidentialité) from templates."""
    await _check_site_access(site_id, user)
    site = await db.sites.find_one({"id": site_id}, {"_id": 0})
    if not site:
        raise HTTPException(404, "Site introuvable")
    design = site.get("design") or {}
    design = _inject_legal(design, site)
    design["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.sites.update_one({"id": site_id}, {"$set": {"design": design}})
    return {"ok": True, "pages": list(design["legal_pages"].keys())}


# =====================================================================
# Section editor — save manual edits to any content section
# =====================================================================
_EDITABLE_SECTIONS = {"hero", "about", "benefits", "faq", "testimonials", "contact", "footer", "seo"}


@router.patch("/sites/{site_id}/design/section/{section}")
async def patch_design_section(
    site_id: str,
    section: str,
    data: dict,
    user: dict = Depends(get_current_user),
):
    """Replace one content section (hero/about/benefits/faq/testimonials/contact/footer/seo).
    Used by the sub-tab editors in the Studio Content tab."""
    await _check_site_access(site_id, user)
    if section not in _EDITABLE_SECTIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Section invalide. Possibles : {', '.join(sorted(_EDITABLE_SECTIONS))}",
        )
    payload = data.get("data") if "data" in data and isinstance(data.get("data"), (dict, list)) else data
    await db.sites.update_one(
        {"id": site_id},
        {"$set": {
            f"design.{section}": payload,
            "design.updated_at": datetime.now(timezone.utc).isoformat(),
        }},
    )
    return {"ok": True, "section": section}


@router.get("/sites/{site_id}/design/studio-state")
async def studio_state(site_id: str, user: dict = Depends(get_current_user)):
    await _check_site_access(site_id, user)
    site = await db.sites.find_one({"id": site_id}, {"_id": 0, "design": 1, "selected_countries": 1, "name": 1})
    design = (site or {}).get("design") or {}
    sections_state = {}
    for s in SECTION_SCHEMAS:
        block = design.get(s)
        sections_state[s] = {
            "filled": bool(block),
            "preview": json.dumps(block, ensure_ascii=False)[:180] if block else "",
        }
    return {
        "site_name": site.get("name") if site else "",
        "brand": design.get("brand") or {},
        "sections": sections_state,
        "published": design.get("published", False),
        "updated_at": design.get("updated_at"),
        "default_prompts": DEFAULT_PROMPTS,
    }


# =====================================================================
# Brand patch — edit brand identity manually (name, tagline, voice, story, palette, fonts)
# =====================================================================
class BrandPatchInput(BaseModel):
    name: Optional[str] = None
    baseline: Optional[str] = None
    tagline: Optional[str] = None
    voice: Optional[str] = None
    story: Optional[str] = None
    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None
    background_color: Optional[str] = None
    text_color: Optional[str] = None
    accent_color: Optional[str] = None
    font_heading: Optional[str] = None
    font_body: Optional[str] = None


@router.patch("/sites/{site_id}/design/template-mode")
async def set_template_mode(site_id: str, payload: dict, user: dict = Depends(get_current_user)):
    """Set the storefront template mode: "monochrome" (default) or "brand".

    Monochrome forces black-on-white + gray cards regardless of the brand palette.
    Brand mode lets the site's palette bleed into surfaces, borders, etc.
    """
    await _check_site_access(site_id, user)
    mode = (payload or {}).get("mode", "monochrome")
    if mode not in {"monochrome", "brand"}:
        raise HTTPException(status_code=400, detail="mode must be 'monochrome' or 'brand'")
    await db.sites.update_one(
        {"id": site_id},
        {"$set": {
            "design.template_mode": mode,
            "design.updated_at": datetime.now(timezone.utc).isoformat(),
        }},
    )
    return {"ok": True, "template_mode": mode}


@router.patch("/sites/{site_id}/design/brand")
async def brand_patch(site_id: str, data: BrandPatchInput, user: dict = Depends(get_current_user)):
    """Edit individual fields of the brand identity without full regeneration."""
    await _check_site_access(site_id, user)
    patch = {}
    for k, v in data.dict(exclude_none=True).items():
        if k in {"primary_color", "secondary_color", "background_color", "text_color", "accent_color"}:
            # store both flat (for palette_apply compat) and in palette dict
            patch[f"design.brand.{k}"] = v
            patch[f"design.brand.palette.{k.replace('_color', '')}"] = v
        elif k == "name":
            # Sanitize brand name (strip markdown/preambles Claude sometimes leaks through)
            cleaned = _sanitize_brand_text(str(v), max_len=40)
            patch["design.brand.name"] = cleaned
            # Keep logo_text in sync so the header/footer text logo matches.
            patch["design.brand.logo_text"] = cleaned
        elif k == "tagline":
            patch["design.brand.tagline"] = _sanitize_brand_text(str(v), max_len=80)
        elif k == "voice":
            patch["design.brand.voice"] = _sanitize_brand_text(str(v), max_len=200)
        elif k == "story":
            patch["design.brand.story"] = _sanitize_brand_text(str(v), max_len=600)
        else:
            patch[f"design.brand.{k}"] = v
    if not patch:
        return {"ok": True, "changed": 0}
    patch["design.updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.sites.update_one({"id": site_id}, {"$set": patch})
    site = await db.sites.find_one({"id": site_id}, {"_id": 0, "design.brand": 1})
    return {"ok": True, "brand": (site or {}).get("design", {}).get("brand") or {}}


# =====================================================================
# Navigation — header + footer menu items
# =====================================================================
class NavChildItem(BaseModel):
    """Sub-item of a mega menu: a visual card with image + label + href."""
    label: str = ""
    href: str = ""
    image: Optional[str] = None
    external: bool = False


class NavItem(BaseModel):
    """Top-level navigation item. `type='mega'` turns it into a mega menu
    with visual children; any other value (or None) is a plain text link."""
    label: str
    href: str
    external: bool = False
    type: Optional[str] = None  # 'mega' | None (plain link)
    children: Optional[list[NavChildItem]] = None
    image: Optional[str] = None  # optional icon/thumb on the link itself
    target: Optional[str] = None  # '_blank' for external


class NavigationInput(BaseModel):
    header: list[NavItem] = []
    footer: list[NavItem] = []


@router.get("/sites/{site_id}/navigation")
async def get_navigation(site_id: str, user: dict = Depends(get_current_user)):
    await _check_site_access(site_id, user)
    site = await db.sites.find_one({"id": site_id}, {"_id": 0, "design.navigation": 1})
    nav = ((site or {}).get("design") or {}).get("navigation") or {}
    return {
        "header": nav.get("header") or [
            {"label": "Accueil", "href": "/", "external": False},
            {"label": "Collections", "href": "/collections", "external": False},
            {"label": "À propos", "href": "/a-propos", "external": False},
            {"label": "Contact", "href": "/contact", "external": False},
        ],
        "footer": nav.get("footer") or [
            {"label": "CGV", "href": "/cgv", "external": False},
            {"label": "Mentions légales", "href": "/mentions", "external": False},
            {"label": "Confidentialité", "href": "/confidentialite", "external": False},
        ],
    }


# Phase 2.7.2 — Auto-fix des hrefs storefront pour matcher les vraies routes
# React Router. Évite les "Mentions légales → vitrine Altiaro" au save.
NAVIGATION_HREF_ALIASES = {
    "/legal": "/mentions",
    "/legals": "/mentions",
    "/legal-notice": "/mentions",
    "/imprint": "/mentions",
    "/mentions-legales": "/mentions",
    "/mentions_legales": "/mentions",
    "/shipping": "/livraison",
    "/delivery": "/livraison",
    "/livraison-retours": "/livraison",
    "/returns": "/retours",
    "/return": "/retours",
    "/refunds": "/retours",
    "/terms": "/cgv",
    "/conditions-generales": "/cgv",
    "/conditions-generales-de-vente": "/cgv",
    "/privacy": "/confidentialite",
    "/policy": "/confidentialite",
    "/politique-de-confidentialite": "/confidentialite",
    "/a-propos": "/about",
    "/qui-sommes-nous": "/about",
    "/notre-histoire": "/about",
}


def _normalize_nav_item(it: dict) -> dict:
    href = (it.get("href") or "").strip()
    if href in NAVIGATION_HREF_ALIASES:
        it["href"] = NAVIGATION_HREF_ALIASES[href]
    return it


@router.put("/sites/{site_id}/navigation")
async def update_navigation(site_id: str, data: NavigationInput, user: dict = Depends(get_current_user)):
    await _check_site_access(site_id, user)
    clean = {
        "header": [_normalize_nav_item(i.dict(exclude_none=True)) for i in data.header][:12],
        "footer": [_normalize_nav_item(i.dict(exclude_none=True)) for i in data.footer][:12],
    }
    await db.sites.update_one(
        {"id": site_id},
        {"$set": {
            "design.navigation": clean,
            "design.updated_at": datetime.now(timezone.utc).isoformat(),
        }},
    )
    return {"ok": True, "navigation": clean}


# =====================================================================
# Collections — CRUD
# =====================================================================
class CollectionInput(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    slug: Optional[str] = None
    description: Optional[str] = ""
    cover_image: Optional[str] = None
    product_ids: list[str] = []
    featured: bool = False


def _slugify(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return re.sub(r"-+", "-", s).strip("-")


@router.get("/sites/{site_id}/collections")
async def list_collections(site_id: str, user: dict = Depends(get_current_user)):
    await _check_site_access(site_id, user)
    cols = await db.collections.find({"site_id": site_id}, {"_id": 0}).sort("created_at", 1).to_list(100)
    return cols


@router.post("/sites/{site_id}/collections")
async def create_collection(site_id: str, data: CollectionInput, user: dict = Depends(get_current_user)):
    await _check_site_access(site_id, user)
    slug = data.slug or _slugify(data.name)
    # Validate uniqueness of slug per site
    existing = await db.collections.find_one({"site_id": site_id, "slug": slug}, {"_id": 0, "id": 1})
    if existing:
        raise HTTPException(400, f"Une collection avec le slug '{slug}' existe déjà")
    # Validate product ids belong to site
    valid_ids = []
    if data.product_ids:
        found = await db.products.find(
            {"site_id": site_id, "id": {"$in": data.product_ids}},
            {"_id": 0, "id": 1}
        ).to_list(200)
        valid_ids = [p["id"] for p in found]
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "id": str(uuid.uuid4()),
        "site_id": site_id,
        "name": data.name,
        "slug": slug,
        "description": data.description or "",
        "cover_image": data.cover_image or None,
        "product_ids": valid_ids,
        "featured": bool(data.featured),
        "created_at": now,
        "updated_at": now,
    }
    await db.collections.insert_one(doc)
    return {k: v for k, v in doc.items() if k != "_id"}


@router.patch("/sites/{site_id}/collections/{collection_id}")
async def update_collection(site_id: str, collection_id: str, data: CollectionInput,
                            user: dict = Depends(get_current_user)):
    await _check_site_access(site_id, user)
    slug = data.slug or _slugify(data.name)
    conflict = await db.collections.find_one(
        {"site_id": site_id, "slug": slug, "id": {"$ne": collection_id}},
        {"_id": 0, "id": 1},
    )
    if conflict:
        raise HTTPException(400, f"Une autre collection utilise déjà le slug '{slug}'")
    valid_ids = []
    if data.product_ids:
        found = await db.products.find(
            {"site_id": site_id, "id": {"$in": data.product_ids}},
            {"_id": 0, "id": 1}
        ).to_list(200)
        valid_ids = [p["id"] for p in found]
    result = await db.collections.update_one(
        {"id": collection_id, "site_id": site_id},
        {"$set": {
            "name": data.name,
            "slug": slug,
            "description": data.description or "",
            "cover_image": data.cover_image or None,
            "product_ids": valid_ids,
            "featured": bool(data.featured),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }},
    )
    if result.matched_count == 0:
        raise HTTPException(404, "Collection introuvable")
    doc = await db.collections.find_one({"id": collection_id, "site_id": site_id}, {"_id": 0})
    return doc


@router.delete("/sites/{site_id}/collections/{collection_id}")
async def delete_collection(site_id: str, collection_id: str, user: dict = Depends(get_current_user)):
    await _check_site_access(site_id, user)
    await db.collections.delete_one({"id": collection_id, "site_id": site_id})
    return {"ok": True}


# =====================================================================
# Homepage Sections — Page Builder
# =====================================================================
DEFAULT_HOMEPAGE_SECTIONS = [
    {"key": "hero",              "label": "Hero",                  "visible": True},
    {"key": "press_logos",       "label": "Logos presse",          "visible": False},
    {"key": "benefits",          "label": "Bénéfices clés",        "visible": True},
    {"key": "collections",       "label": "Collections",           "visible": True},
    {"key": "products",          "label": "Grille produits",       "visible": True},
    {"key": "featured_product",  "label": "Produit vedette",       "visible": False},
    {"key": "lifestyle_editorial", "label": "Éditorial lifestyle", "visible": False},
    {"key": "values",            "label": "Nos valeurs",           "visible": False},
    {"key": "buying_guide",      "label": "Guide d'achat",         "visible": False},
    {"key": "testimonials",      "label": "Témoignages",           "visible": True},
    {"key": "founder_story",     "label": "Histoire du fondateur", "visible": False},
    {"key": "instagram",         "label": "Feed Instagram",        "visible": False},
    {"key": "blog_teaser",       "label": "Derniers articles",     "visible": False},
    {"key": "faq",               "label": "FAQ",                   "visible": True},
    {"key": "newsletter",        "label": "Newsletter CTA",        "visible": True},
    {"key": "final_cta",         "label": "CTA final",             "visible": True},
]

HOMEPAGE_PRESETS = {
    "minimal": ["hero", "benefits", "products", "faq", "final_cta"],
    "editorial": ["hero", "lifestyle_editorial", "founder_story", "benefits",
                  "collections", "products", "values", "testimonials", "faq", "newsletter", "final_cta"],
    "conversion": ["hero", "press_logos", "benefits", "products", "testimonials",
                   "featured_product", "buying_guide", "faq", "newsletter", "final_cta"],
    "full": [s["key"] for s in DEFAULT_HOMEPAGE_SECTIONS],
}


@router.get("/sites/{site_id}/design/homepage-sections")
async def get_homepage_sections(site_id: str, user: dict = Depends(get_current_user)):
    await _check_site_access(site_id, user)
    site = await db.sites.find_one({"id": site_id}, {"_id": 0, "design.homepage_sections": 1})
    stored = ((site or {}).get("design") or {}).get("homepage_sections")
    if not stored:
        return {"sections": DEFAULT_HOMEPAGE_SECTIONS, "presets": HOMEPAGE_PRESETS}
    # Merge with defaults — add any new key as invisible (lets us ship new sections without breaking existing sites)
    by_key = {s["key"]: s for s in stored}
    merged = []
    for default in DEFAULT_HOMEPAGE_SECTIONS:
        existing = by_key.get(default["key"])
        if existing:
            merged.append({"key": default["key"], "label": default["label"],
                           "visible": bool(existing.get("visible", default["visible"]))})
        else:
            merged.append({**default, "visible": False})
    # Preserve user ordering when available
    ordered_keys = [s["key"] for s in stored if s.get("key") in {d["key"] for d in DEFAULT_HOMEPAGE_SECTIONS}]
    if ordered_keys:
        by_key2 = {s["key"]: s for s in merged}
        merged = [by_key2[k] for k in ordered_keys if k in by_key2]
        # Append any default not yet in user's list (newly-shipped sections)
        for d in DEFAULT_HOMEPAGE_SECTIONS:
            if d["key"] not in ordered_keys:
                merged.append({**d, "visible": False})
    return {"sections": merged, "presets": HOMEPAGE_PRESETS}


class HomepageSectionItem(BaseModel):
    key: str
    visible: bool = True


class HomepageSectionsInput(BaseModel):
    sections: list[HomepageSectionItem]


@router.put("/sites/{site_id}/design/homepage-sections")
async def put_homepage_sections(
    site_id: str,
    data: HomepageSectionsInput,
    user: dict = Depends(get_current_user),
):
    await _check_site_access(site_id, user)
    valid_keys = {s["key"] for s in DEFAULT_HOMEPAGE_SECTIONS}
    clean = [
        {"key": s.key, "visible": bool(s.visible)}
        for s in data.sections
        if s.key in valid_keys
    ]
    await db.sites.update_one(
        {"id": site_id},
        {"$set": {
            "design.homepage_sections": clean,
            "design.updated_at": datetime.now(timezone.utc).isoformat(),
        }},
    )
    return {"ok": True, "count": len(clean)}


@router.post("/sites/{site_id}/design/homepage-sections/preset/{preset}")
async def apply_homepage_preset(
    site_id: str,
    preset: str,
    user: dict = Depends(get_current_user),
):
    await _check_site_access(site_id, user)
    if preset not in HOMEPAGE_PRESETS:
        raise HTTPException(400, f"Preset inconnu. Choix : {', '.join(HOMEPAGE_PRESETS.keys())}")
    enabled = set(HOMEPAGE_PRESETS[preset])
    sections = [
        {"key": d["key"], "visible": d["key"] in enabled}
        for d in DEFAULT_HOMEPAGE_SECTIONS
    ]
    await db.sites.update_one(
        {"id": site_id},
        {"$set": {
            "design.homepage_sections": sections,
            "design.updated_at": datetime.now(timezone.utc).isoformat(),
        }},
    )
    return {"ok": True, "preset": preset, "visible_count": len(enabled), "sections": sections}


# =====================================================================
# ÉTAPE 6 — Rédaction IA des pages statiques (About, FAQ, Contact, Livraison, Retours)
# =====================================================================
async def _run_pages_generation_job(site_id: str, job_id: str, site: dict):
    """Background worker : génère + persiste le copy des 5 pages statiques."""
    try:
        await db.pages_jobs.update_one({"id": job_id}, {"$set": {"status": "running"}})
        name = site.get("name") or "notre maison"
        niche = site.get("niche") or "produits seniors"
        brand = ((site.get("design") or {}).get("brand")) or {}
        voice = brand.get("voice") or "chaleureux, rassurant, premium, pédagogue"

        system = (
            "Tu es un rédacteur éditorial senior (top 1%) pour le marché français de la Silver Economy. "
            "Tu écris un copy ultra-premium (ton magazine, jamais corporate), E-E-A-T maximum, "
            "avec des phrases courtes et concrètes. Tu renvoies UNIQUEMENT du JSON valide."
        )
        user_prompt = f"""Rédige le contenu éditorial de 5 pages statiques pour la boutique {name} (niche : {niche}, voix de marque : {voice}).

Le JSON ci-dessous est STRICT — respecte la structure et les longueurs EXACTEMENT.

{{
  "about": {{
    "headline": "Phrase éditoriale 60-90 chars, pas de nom de marque, évocatrice",
    "paragraphs": [
      "Paragraphe 1 — l'origine, la conviction fondatrice (60-90 mots)",
      "Paragraphe 2 — notre méthode et nos exigences (60-90 mots)",
      "Paragraphe 3 — notre engagement humain (50-70 mots)"
    ],
    "values": [
      {{"title": "Valeur 1 (2-3 mots)", "description": "1 phrase concrète (15-20 mots)"}},
      {{"title": "Valeur 2 (2-3 mots)", "description": "1 phrase concrète (15-20 mots)"}},
      {{"title": "Valeur 3 (2-3 mots)", "description": "1 phrase concrète (15-20 mots)"}},
      {{"title": "Valeur 4 (2-3 mots)", "description": "1 phrase concrète (15-20 mots)"}}
    ]
  }},
  "contact": {{
    "headline": "Phrase d'invitation 50-70 chars",
    "intro": "1 paragraphe chaleureux 40-60 mots sur la relation humaine avec vos clients"
  }},
  "livraison": {{
    "headline": "Phrase rassurante 50-70 chars",
    "intro": "1 paragraphe 50-70 mots sur la philosophie de livraison (attention, soin, planning)",
    "notes": [
      "Note sur les produits volumineux (50-70 mots)",
      "Note sur l'emballage écologique et le zéro-plastique (40-60 mots)"
    ]
  }},
  "retours": {{
    "headline": "Phrase 50-70 chars sur la sérénité d'achat",
    "intro": "1 paragraphe 50-70 mots sur la politique de retour 14 jours, gratuite, sans justification",
    "steps": [
      {{"title": "Étape 1 titre court", "description": "1 phrase concrète 15-25 mots"}},
      {{"title": "Étape 2 titre court", "description": "1 phrase concrète 15-25 mots"}},
      {{"title": "Étape 3 titre court", "description": "1 phrase concrète 15-25 mots"}},
      {{"title": "Étape 4 titre court", "description": "1 phrase concrète 15-25 mots"}}
    ]
  }},
  "faq": {{
    "headline": "Phrase 50-70 chars d'intro FAQ",
    "items": [
      {{"question": "Question fréquente spécifique à la niche ({niche}) 1", "answer": "Réponse 40-60 mots précise et rassurante"}},
      {{"question": "Question 2 sur la livraison/délais", "answer": "Réponse 40-60 mots"}},
      {{"question": "Question 3 sur l'installation / mise en service", "answer": "Réponse 40-60 mots"}},
      {{"question": "Question 4 sur la garantie et le SAV", "answer": "Réponse 40-60 mots"}},
      {{"question": "Question 5 sur le remboursement mutuelle/Sécu (LPPR)", "answer": "Réponse 40-60 mots"}},
      {{"question": "Question 6 sur l'entretien du produit", "answer": "Réponse 40-60 mots"}},
      {{"question": "Question 7 sur les conseils personnalisés par téléphone", "answer": "Réponse 40-60 mots"}},
      {{"question": "Question 8 sur le paiement sécurisé / plusieurs fois", "answer": "Réponse 40-60 mots"}}
    ]
  }}
}}

CONTRAINTES :
- Aucune marque concurrente citée. Aucun disclaimer IA.
- Écris comme un rédacteur de Monocle/Kinfolk : phrases concrètes, images sensorielles, pas d'adjectifs creux.
- N'emploie jamais le mot "senior" comme étiquette froide — préfère "client", "parent", "proche"."""

        try:
            data = await _claude_json(system, user_prompt, session_id=f"pages-{site_id}", timeout=220)
        except HTTPException as e:
            await db.pages_jobs.update_one({"id": job_id}, {"$set": {
                "status": "failed", "error": f"{e.status_code}: {e.detail}"[:300],
                "finished_at": datetime.now(timezone.utc).isoformat(),
            }})
            return
        if not isinstance(data, dict):
            await db.pages_jobs.update_one({"id": job_id}, {"$set": {
                "status": "failed", "error": "IA n'a pas renvoyé un JSON valide.",
                "finished_at": datetime.now(timezone.utc).isoformat(),
            }})
            return

        pages = {}
        for key in ("about", "contact", "livraison", "retours", "faq"):
            block = data.get(key)
            if isinstance(block, dict):
                pages[key] = block

        if not pages:
            await db.pages_jobs.update_one({"id": job_id}, {"$set": {
                "status": "failed", "error": "Réponse IA incomplète.",
                "finished_at": datetime.now(timezone.utc).isoformat(),
            }})
            return

        now_iso = datetime.now(timezone.utc).isoformat()
        await db.sites.update_one(
            {"id": site_id},
            {"$set": {
                "design.pages": pages,
                "design.pages_generated_at": now_iso,
                "design.updated_at": now_iso,
            }},
        )
        await db.pages_jobs.update_one({"id": job_id}, {"$set": {
            "status": "done",
            "generated_pages": list(pages.keys()),
            "finished_at": now_iso,
        }})
    except Exception as e:
        logger.exception("pages generation job crashed")
        await db.pages_jobs.update_one({"id": job_id}, {"$set": {
            "status": "failed", "error": str(e)[:300],
            "finished_at": datetime.now(timezone.utc).isoformat(),
        }})


@router.post("/sites/{site_id}/design/generate-pages")
async def generate_static_pages(site_id: str, user: dict = Depends(get_current_user)):
    """Lance la génération IA des 5 pages statiques en background. Retourne
    un job_id, le client poll via GET .../generate-pages/{job_id}."""
    await _check_site_access(site_id, user)
    site = await db.sites.find_one({"id": site_id}, {"_id": 0})
    if not site:
        raise HTTPException(404, "Site introuvable")

    job_id = str(uuid.uuid4())
    await db.pages_jobs.insert_one({
        "id": job_id,
        "site_id": site_id,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    asyncio.create_task(_run_pages_generation_job(site_id, job_id, site))
    return {
        "status": "started",
        "job_id": job_id,
        "message": "Rédaction IA lancée. Recharge la page dans 60 à 120 secondes.",
    }


@router.get("/sites/{site_id}/design/generate-pages/{job_id}")
async def generate_static_pages_status(site_id: str, job_id: str, user: dict = Depends(get_current_user)):
    await _check_site_access(site_id, user)
    job = await db.pages_jobs.find_one({"id": job_id, "site_id": site_id}, {"_id": 0})
    if not job:
        raise HTTPException(404, "Job introuvable")
    return job


# =====================================================================
# Pulse SEO — widget de suivi éditorial et SEO
# =====================================================================
def _compute_eeat_score(post: dict) -> int:
    """Score E-E-A-T heuristique 0-100 basé sur des signaux concrets du contenu."""
    body = post.get("body") or ""
    word_count = len(body.split())
    score = 0
    if word_count >= 1500:
        score += 25
    elif word_count >= 900:
        score += 18
    elif word_count >= 500:
        score += 10
    if body.count("\n## ") >= 3:
        score += 15
    elif body.count("\n## ") >= 1:
        score += 8
    if "FAQ" in body or "?\n" in body or "### Question" in body:
        score += 15
    if body.count("\n- ") >= 5:
        score += 10
    if body.count("**") >= 6:
        score += 10
    if "/blog/" in body or ("[" in body and "](/" in body):
        score += 15
    if post.get("meta_title") and post.get("meta_description"):
        score += 10
    return min(score, 100)


@router.get("/sites/{site_id}/seo/pulse")
async def seo_pulse(site_id: str, user: dict = Depends(get_current_user)):
    """Widget dashboard : articles publiés, keywords couverts, E-E-A-T moyen."""
    await _check_site_access(site_id, user)
    site = await db.sites.find_one({"id": site_id}, {"_id": 0})
    if not site:
        raise HTTPException(404, "Site introuvable")

    design = site.get("design") or {}
    posts = design.get("blog_posts") or []

    now = datetime.now(timezone.utc)
    month_key = now.strftime("%Y-%m")
    posts_this_month = [p for p in posts if (p.get("published_at") or "").startswith(month_key)]

    covered_kws = set()
    for p in posts:
        for f in ("pillar_keyword", "satellite_keyword"):
            if p.get(f):
                covered_kws.add(str(p[f]).lower().strip())
        for v in p.get("satellite_keywords") or []:
            covered_kws.add(str(v).lower().strip())

    niche_an = design.get("niche_analysis") or {}
    total_informational = 0
    info_re = re.compile(r"\b(comment|pourquoi|guide|choisir|quand|quoi|est-ce|différence|types|bienfaits|avantages|inconvénients)\b", re.I)
    for result in niche_an.get("results") or []:
        for k in result.get("keywords") or []:
            kw = (k.get("keyword") if isinstance(k, dict) else str(k)) or ""
            if info_re.search(kw):
                total_informational += 1

    coverage_pct = 0
    if total_informational > 0:
        coverage_pct = round(min(100, (len(covered_kws) / total_informational) * 100))

    recent = sorted(posts, key=lambda p: p.get("published_at") or "", reverse=True)[:6]
    recent_scored = [{
        "slug": p.get("slug"),
        "title": p.get("title"),
        "type": p.get("type") or "article",
        "published_at": p.get("published_at"),
        "read_minutes": p.get("read_minutes"),
        "eeat_score": _compute_eeat_score(p),
        "word_count": len((p.get("body") or "").split()),
    } for p in recent]
    avg_eeat = round(sum(r["eeat_score"] for r in recent_scored) / len(recent_scored)) if recent_scored else 0

    bc = design.get("blog_cluster") or {}
    next_cluster = None
    if bc.get("auto_enabled"):
        if now.month == 12:
            nc = now.replace(year=now.year + 1, month=1, day=1, hour=6, minute=0, second=0, microsecond=0)
        else:
            nc = now.replace(month=now.month + 1, day=1, hour=6, minute=0, second=0, microsecond=0)
        next_cluster = nc.isoformat()

    return {
        "articles_this_month": len(posts_this_month),
        "articles_total": len(posts),
        "keywords_covered": len(covered_kws),
        "keywords_total_informational": total_informational,
        "coverage_pct": coverage_pct,
        "recent_articles": recent_scored,
        "avg_eeat_score": avg_eeat,
        "next_cluster_at": next_cluster,
        "avg_google_position": None,
        "google_source": "non_connecte",
    }

