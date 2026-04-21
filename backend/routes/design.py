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

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr, Field

from deps import db, get_current_user, _check_site_access, EMERGENT_LLM_KEY, UPLOAD_DIR
from legal_templates import CGV, MENTIONS_LEGALES, CONFIDENTIALITE, render_legal

logger = logging.getLogger("conceptfactory.design")
router = APIRouter()

JSON_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)
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


async def _claude_json(system: str, user: str, session_id: str, timeout: int = 180) -> dict:
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=session_id, system_message=system)\
        .with_model("anthropic", "claude-sonnet-4-5-20250929")
    try:
        raw = await asyncio.wait_for(chat.send_message(UserMessage(text=user)), timeout=timeout)
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="L'IA a mis trop de temps à répondre. Réessaye.")
    except Exception as e:
        logger.exception("Claude design call failed")
        raise HTTPException(status_code=502, detail=f"IA indisponible : {str(e)[:180]}")
    payload = _strip(raw if isinstance(raw, str) else str(raw))
    try:
        return json.loads(payload)
    except json.JSONDecodeError as e:
        logger.error(f"Design prompt returned invalid JSON : {e}\n{payload[:500]}")
        raise HTTPException(status_code=502, detail="L'IA a retourné un JSON invalide. Réessaye.")


async def _nano_banana_logo(prompt: str, site_id: str) -> Optional[str]:
    """Génère un logo via Gemini Nano Banana et renvoie l'URL publique."""
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=f"logo-{site_id}-{uuid.uuid4().hex[:6]}",
                       system_message="You create minimal vector logos for e-commerce stores.")
        chat.with_model("gemini", NANO_BANANA_MODEL).with_params(modalities=["image", "text"])
        full_prompt = (
            f"Minimalist vector logo icon (no text, no letters), 512x512, flat design, "
            f"centered, cream background (#FDFBF7), {prompt}. "
            f"Clean, friendly, professional. Senior-friendly e-commerce brand."
        )
        _, images = await asyncio.wait_for(
            chat.send_message_multimodal_response(UserMessage(text=full_prompt)),
            timeout=90,
        )
        if not images:
            return None
        img = images[0]
        data = base64.b64decode(img["data"])
        logos_dir = UPLOAD_DIR / "logos"
        logos_dir.mkdir(parents=True, exist_ok=True)
        filename = f"logo_{site_id}_{uuid.uuid4().hex[:8]}.png"
        path = logos_dir / filename
        path.write_bytes(data)
        return f"/api/uploads/logos/{filename}"
    except asyncio.TimeoutError:
        logger.warning(f"Nano Banana timeout for site {site_id}")
        return None
    except Exception:
        logger.exception("Nano Banana logo generation failed")
        return None


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
    return {"flagship": flagship or "N/A", "benefits_hint": benefits_hint or "N/A", "brand_voice": brand_voice or "N/A"}


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
        tweak=data.tweak or "aucune (défaut)",
        slug=_slugify(site.get("name")),
    )

    session = f"design-{site_id}-{uuid.uuid4().hex[:6]}"
    design = await _claude_json(SYSTEM, user_prompt, session)

    # Génère le logo en parallèle (non bloquant si échec)
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
    design["published"] = False   # le Concepteur doit publier explicitement

    await db.sites.update_one({"id": site_id}, {"$set": {"design": design, "updated_at": design["generated_at"]}})
    return {"ok": True, "design": design}


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
                 "(pas 'Altiora'), un tagline bénéfice <60 chars, et une "
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
        await db.sites.update_one(
            {"id": site_id},
            {"$set": {
                "design.brand.name": data.data.get("brand_name"),
                "design.brand.tagline": data.data.get("tagline"),
                "design.brand.story": data.data.get("brand_story"),
                "design.updated_at": now,
            }},
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
