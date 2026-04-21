"""
Google Ads Copy Generator pour Altiora.
Le Concepteur sélectionne un pays + une langue, on génère :
- 15 headlines (≤30 chars) prêts pour une Responsive Search Ad
- 4 descriptions (≤90 chars)
- 20-30 mots-clés (broad/phrase)
- 10-15 mots-clés négatifs
- 4-6 sitelinks
- 4-6 callouts
via Claude Sonnet 4.5. Les résultats sont persistés dans `ads_copy` pour réutilisation
et exportables en CSV compatible Google Ads Editor.
"""
from __future__ import annotations

import asyncio
import csv
import io
import json
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from deps import db, get_current_user, _check_site_access, EMERGENT_LLM_KEY

logger = logging.getLogger("conceptfactory.ads_copy")

router = APIRouter(prefix="/sites/{site_id}/ads-copy")


# Google Ads RSA (Responsive Search Ad) hard limits
HEADLINE_MAX = 30
DESCRIPTION_MAX = 90
SITELINK_MAX = 25
CALLOUT_MAX = 25


COUNTRY_LOCALES = {
    "FR": {"name": "France", "default_lang": "fr", "currency": "EUR"},
    "DE": {"name": "Allemagne", "default_lang": "de", "currency": "EUR"},
    "CH": {"name": "Suisse", "default_lang": "fr", "currency": "CHF"},
    "BE": {"name": "Belgique", "default_lang": "fr", "currency": "EUR"},
    "UK": {"name": "Royaume-Uni", "default_lang": "en", "currency": "GBP"},
    "NL": {"name": "Pays-Bas", "default_lang": "nl", "currency": "EUR"},
}

LANG_NAMES = {"fr": "français", "en": "anglais", "de": "allemand", "nl": "néerlandais"}


class GenerateAdsInput(BaseModel):
    country: str = Field(..., description="Code ISO 2 lettres (FR/DE/CH/BE/UK/NL)")
    language: Optional[str] = None  # fr/en/de/nl — default from country
    product_focus: Optional[str] = ""  # optional product/angle to emphasize
    tone: Optional[str] = "rassurant"  # "rassurant" | "premium" | "direct"


ADS_SYSTEM_PROMPT = """Tu es un expert Google Ads spécialisé Silver Economy (60+ ans) en Europe.
Tu écris des Responsive Search Ads (RSA) optimisées Quality Score ≥7.

Règles IMPÉRATIVES :
- Headlines : EXACTEMENT 15, chacun ≤30 caractères (ESPACES COMPRIS). Tu comptes STRICTEMENT.
- Descriptions : EXACTEMENT 4, chacune ≤90 caractères.
- Sitelinks : 4 sitelinks, titre ≤25 chars + 2 descriptions ≤35 chars chacune.
- Callouts : 6 callouts, chacun ≤25 chars.
- Keywords : 25 mots-clés pertinents, mix short-tail + long-tail + branded.
- Negative keywords : 12 mots-clés à exclure (ex: "gratuit", "occasion", "forum", "avis forum"...).

Techniques à exploiter :
- Inclure le mot-clé principal dans ≥3 headlines
- CTA forts : "Commandez", "Découvrez", "Livraison 48h", "Garantie 2 ans"
- Bénéfices concrets : "Sans douleur", "Autonomie retrouvée", "Confort retrouvé"
- Social proof : "+10 000 clients", "4.8/5", "Recommandé seniors"
- Urgency modérée : "Stock limité", "Offre du mois"
- Tu adaptes au pays : culture, devises, réassurances spécifiques (TVA incluse FR, MwSt DE, BTW NL)
- Tu écris dans la langue demandée, ton senior-friendly, évite le jargon jeune

Tu réponds UNIQUEMENT avec du JSON valide (sans markdown, sans commentaire) :
{
  "headlines": ["Headline 1", ...15 items],
  "descriptions": ["Description 1", ...4 items],
  "keywords": ["mot clé 1", ...25 items],
  "negative_keywords": ["gratuit", ...12 items],
  "sitelinks": [
    {"title": "Titre ≤25", "desc1": "Desc1 ≤35", "desc2": "Desc2 ≤35", "url_suffix": "/produits"}, ...4 items
  ],
  "callouts": ["Callout ≤25", ...6 items],
  "final_url_suggestion": "/",
  "notes": "1-2 phrases sur angle choisi"
}"""

JSON_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def _strip_json_fence(text: str) -> str:
    return JSON_FENCE_RE.sub("", text).strip()


def _truncate(s: str, maxlen: int) -> str:
    """Safety net: truncate over-long strings so nothing exceeds Google limits."""
    s = (s or "").strip()
    return s if len(s) <= maxlen else s[: maxlen - 1].rstrip() + "…"


def _validate_and_sanitize(data: dict) -> dict:
    """Enforce Google limits even if the LLM slipped."""
    headlines = [_truncate(h, HEADLINE_MAX) for h in (data.get("headlines") or [])][:15]
    descriptions = [_truncate(d, DESCRIPTION_MAX) for d in (data.get("descriptions") or [])][:4]

    sitelinks = []
    for sl in (data.get("sitelinks") or [])[:6]:
        if not isinstance(sl, dict):
            continue
        sitelinks.append({
            "title": _truncate(sl.get("title", ""), SITELINK_MAX),
            "desc1": _truncate(sl.get("desc1", ""), 35),
            "desc2": _truncate(sl.get("desc2", ""), 35),
            "url_suffix": (sl.get("url_suffix") or "/").strip()[:100],
        })

    callouts = [_truncate(c, CALLOUT_MAX) for c in (data.get("callouts") or [])][:8]

    return {
        "headlines": headlines,
        "descriptions": descriptions,
        "keywords": [k.strip() for k in (data.get("keywords") or []) if isinstance(k, str)][:40],
        "negative_keywords": [k.strip() for k in (data.get("negative_keywords") or []) if isinstance(k, str)][:30],
        "sitelinks": sitelinks,
        "callouts": callouts,
        "final_url_suggestion": (data.get("final_url_suggestion") or "/").strip()[:200],
        "notes": (data.get("notes") or "").strip()[:500],
    }


async def _ask_claude(prompt: str, session_id: str) -> dict:
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        chat = (
            LlmChat(
                api_key=EMERGENT_LLM_KEY,
                session_id=session_id,
                system_message=ADS_SYSTEM_PROMPT,
            )
            .with_model("anthropic", "claude-sonnet-4-5-20250929")
        )
        response = await asyncio.wait_for(
            chat.send_message(UserMessage(text=prompt)),
            timeout=90
        )
        raw = response if isinstance(response, str) else str(response)
        raw = _strip_json_fence(raw)
        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            logger.error(f"Ads LLM returned invalid JSON: {e}\n{raw[:500]}")
            raise HTTPException(status_code=502, detail="L'IA a retourné un format invalide. Réessayez.")
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="La génération prend trop de temps (>90s). Réessayez.")
    except HTTPException:
        raise
    except Exception as e:
        err = str(e)
        if "Budget has been exceeded" in err or "budget" in err.lower():
            raise HTTPException(
                status_code=402,
                detail="Budget LLM épuisé. Profile → Universal Key → Add Balance."
            )
        logger.exception("Ads LLM call failed")
        raise HTTPException(status_code=500, detail=f"Erreur IA : {err[:200]}")


async def _build_context(site: dict) -> str:
    """Gather niche + analysis + products to feed the LLM richer context."""
    parts = [f"SITE : {site.get('name', '')}", f"NICHE : {site.get('niche', '')}"]

    if site.get("analysis_id"):
        analysis = await db.niche_analyses.find_one({"id": site["analysis_id"]}, {"_id": 0})
        if analysis and analysis.get("analysis"):
            a = analysis["analysis"]
            parts.append(f"DESCRIPTION NICHE : {a.get('description', '')}")
            if a.get("keywords"):
                parts.append(f"MOTS-CLÉS NICHE : {', '.join(a['keywords'])}")
            if a.get("opportunities"):
                parts.append(f"OPPORTUNITÉS : {' · '.join(a['opportunities'])}")
            if a.get("tagline"):
                parts.append(f"TAGLINE : {a['tagline']}")

    # Products sample (top 3 actifs)
    products = await db.products.find(
        {"site_id": site["id"], "status": "active"}, {"_id": 0, "name": 1, "price": 1}
    ).limit(3).to_list(3)
    if products:
        lines = [
            f"- {p.get('name', {}).get('fr') or p.get('name', {}).get('en') or 'produit'} ({p.get('price', 0)}€)"
            for p in products
        ]
        parts.append("PRODUITS PHARES :\n" + "\n".join(lines))

    return "\n".join(parts)


@router.post("/generate")
async def generate_ads_copy(site_id: str, data: GenerateAdsInput, user: dict = Depends(get_current_user)):
    site = await _check_site_access(site_id, user)
    return await _generate_and_persist(
        site=site,
        country=data.country,
        language=data.language,
        tone=data.tone or "rassurant",
        product_focus=data.product_focus or "",
        user_id=user["id"],
    )


async def _generate_and_persist(
    site: dict,
    country: str,
    language: Optional[str],
    tone: str,
    product_focus: str,
    user_id: str,
) -> dict:
    """Reusable core : same logic used by /generate endpoint and by the
    Scale-6-pays background tasks."""
    country = (country or "").upper().strip()
    if country not in COUNTRY_LOCALES:
        raise HTTPException(status_code=400, detail=f"Pays non supporté : {country}")
    locale = COUNTRY_LOCALES[country]
    lang = (language or locale["default_lang"]).lower()
    if lang not in LANG_NAMES:
        raise HTTPException(status_code=400, detail=f"Langue non supportée : {lang}")

    context = await _build_context(site)

    prompt = f"""{context}

PAYS CIBLE : {locale['name']} ({country}) — devise : {locale['currency']}
LANGUE DE RÉDACTION : {LANG_NAMES[lang]} ({lang})
TON : {tone}
{f"FOCUS PRODUIT : {product_focus}" if product_focus else ""}

Génère une campagne Google Ads Responsive Search Ad complète selon le schéma JSON demandé.
Rappel strict : 15 headlines ≤30 chars, 4 descriptions ≤90 chars. COMPTE LES CARACTÈRES.
Adapte la réassurance au pays ({locale['name']}) : livraison, garantie légale, paiements locaux."""

    session_id = f"ads-{site['id']}-{country}-{uuid.uuid4().hex[:6]}"
    raw = await _ask_claude(prompt, session_id)
    clean = _validate_and_sanitize(raw)

    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "id": str(uuid.uuid4()),
        "site_id": site["id"],
        "country": country,
        "country_name": locale["name"],
        "language": lang,
        "tone": tone,
        "product_focus": product_focus,
        "data": clean,
        "created_at": now,
        "created_by": user_id,
    }
    await db.ads_copy.insert_one(dict(doc))
    doc.pop("_id", None)
    return doc


@router.get("")
async def list_ads_copy(site_id: str, user: dict = Depends(get_current_user)):
    await _check_site_access(site_id, user)
    items = (
        await db.ads_copy.find({"site_id": site_id}, {"_id": 0})
        .sort("created_at", -1)
        .to_list(100)
    )
    return items


@router.get("/{copy_id}")
async def get_ads_copy(site_id: str, copy_id: str, user: dict = Depends(get_current_user)):
    await _check_site_access(site_id, user)
    c = await db.ads_copy.find_one({"id": copy_id, "site_id": site_id}, {"_id": 0})
    if not c:
        raise HTTPException(status_code=404, detail="Campagne introuvable")
    return c


@router.delete("/{copy_id}")
async def delete_ads_copy(site_id: str, copy_id: str, user: dict = Depends(get_current_user)):
    await _check_site_access(site_id, user)
    await db.ads_copy.delete_one({"id": copy_id, "site_id": site_id})
    return {"ok": True}


@router.get("/{copy_id}/export.csv")
async def export_ads_copy_csv(site_id: str, copy_id: str, user: dict = Depends(get_current_user)):
    """CSV compatible Google Ads Editor : une ligne par headline/description/keyword."""
    await _check_site_access(site_id, user)
    c = await db.ads_copy.find_one({"id": copy_id, "site_id": site_id}, {"_id": 0})
    if not c:
        raise HTTPException(status_code=404, detail="Campagne introuvable")
    d = c.get("data", {})

    buf = io.StringIO()
    w = csv.writer(buf, quoting=csv.QUOTE_ALL)
    w.writerow(["Type", "Index", "Text", "Character count"])
    for i, h in enumerate(d.get("headlines", []), 1):
        w.writerow(["Headline", i, h, len(h)])
    for i, desc in enumerate(d.get("descriptions", []), 1):
        w.writerow(["Description", i, desc, len(desc)])
    for i, k in enumerate(d.get("keywords", []), 1):
        w.writerow(["Keyword", i, k, len(k)])
    for i, k in enumerate(d.get("negative_keywords", []), 1):
        w.writerow(["NegativeKeyword", i, k, len(k)])
    for i, sl in enumerate(d.get("sitelinks", []), 1):
        w.writerow(["Sitelink", i, f"{sl.get('title','')} | {sl.get('desc1','')} | {sl.get('desc2','')}", 0])
    for i, co in enumerate(d.get("callouts", []), 1):
        w.writerow(["Callout", i, co, len(co)])

    buf.seek(0)
    fname = f"ads-{c.get('country','')}-{c.get('language','')}-{copy_id[:8]}.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )
