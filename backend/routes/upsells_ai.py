"""Upsells AI suggestions — analyse le catalogue actuel via Claude
et propose 8-10 upsells/accessoires pertinents pour augmenter le panier moyen.

Endpoints :
  POST   /api/sites/{site_id}/upsells/suggest          → génère N suggestions
  GET    /api/sites/{site_id}/upsells/suggestions      → liste, filtre status
  PATCH  /api/sites/{site_id}/upsells/suggestions/{id} → adopt/ignore

Collection : `upsell_suggestions`
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from deps import _check_site_access, db, get_current_user

logger = logging.getLogger("altiaro.upsells_ai")
EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")

router = APIRouter()

_JSON_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```\s*$", re.MULTILINE)
# Limite de générations en parallèle pour ne pas saturer le proxy LiteLLM
_LLM_SEM = asyncio.Semaphore(2)


def _strip_json_fence(text: str) -> str:
    return _JSON_FENCE_RE.sub("", (text or "").strip()).strip()


def _pick_text(value):
    """Renvoie le 1er string disponible quel que soit le format (str | dict i18n)."""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        for k in ("fr", "en", "de", "es", "it", "nl"):
            v = value.get(k)
            if isinstance(v, str) and v.strip():
                return v
        for v in value.values():
            if isinstance(v, str) and v.strip():
                return v
    return ""


# ─── Models ──────────────────────────────────────────────────────────────

class StatusUpdate(BaseModel):
    status: str = Field(..., description="suggested | adopted | ignored")


# ─── Helpers ─────────────────────────────────────────────────────────────

async def _call_claude_json(system: str, user: str, timeout: int = 120):
    if not EMERGENT_LLM_KEY:
        return None, "missing_llm_key"
    last_err = None
    for attempt in range(2):
        try:
            from emergentintegrations.llm.chat import LlmChat, UserMessage
            async with _LLM_SEM:
                chat = (
                    LlmChat(
                        api_key=EMERGENT_LLM_KEY,
                        session_id=f"upsells-{uuid.uuid4().hex[:8]}",
                        system_message=system,
                    )
                    .with_model("anthropic", "claude-sonnet-4-5-20250929")
                )
                raw = await asyncio.wait_for(
                    chat.send_message(UserMessage(text=user)), timeout=timeout
                )
            text = raw if isinstance(raw, str) else str(raw)
            return json.loads(_strip_json_fence(text)), None
        except Exception as e:
            last_err = e
            msg = str(e)
            if "Budget has been exceeded" in msg:
                break
            if attempt == 0 and ("502" in msg or "503" in msg or "Bad Gateway" in msg):
                logger.warning(f"[upsells-claude] transient {msg[:120]} — retry in 3s")
                await asyncio.sleep(3)
                continue
            break
    logger.exception(f"[upsells-claude] failed after retries: {last_err}")
    return None, str(last_err) if last_err else "unknown"


def _normalize_suggestion(raw: dict) -> Optional[dict]:
    """Coerce une entrée Claude en doc DB. Retourne None si trop incomplet."""
    if not isinstance(raw, dict):
        return None
    name = (raw.get("name") or raw.get("title") or "").strip()
    if not name:
        return None
    cat = str(raw.get("category", "accessoire")).lower().strip()
    if cat not in ("accessoire", "garantie", "service", "bundle"):
        cat = "accessoire"
    try:
        price = float(raw.get("estimated_price_eur") or raw.get("price") or 0)
    except Exception:
        price = 0.0
    kw_ae = raw.get("search_keywords_aliexpress") or []
    kw_cj = raw.get("search_keywords_cj") or []
    if isinstance(kw_ae, str):
        kw_ae = [k.strip() for k in kw_ae.split(",") if k.strip()]
    if isinstance(kw_cj, str):
        kw_cj = [k.strip() for k in kw_cj.split(",") if k.strip()]
    return {
        "name": name[:160],
        "description": str(raw.get("description") or "").strip()[:500],
        "category": cat,
        "estimated_price_eur": round(price, 2),
        "rationale": str(raw.get("rationale") or raw.get("why") or "").strip()[:500],
        "search_keywords_aliexpress": [str(k)[:80] for k in kw_ae][:5],
        "search_keywords_cj": [str(k)[:80] for k in kw_cj][:5],
    }


# ─── Routes ──────────────────────────────────────────────────────────────

@router.post("/sites/{site_id}/upsells/suggest")
async def suggest_upsells(site_id: str, user=Depends(get_current_user)):
    """Analyse le catalogue actif du site et génère 8-10 suggestions d'upsells."""
    await _check_site_access(site_id, user)

    site = await db.sites.find_one({"id": site_id})
    if not site:
        raise HTTPException(404, "Site introuvable")

    products = await db.products.find(
        {"site_id": site_id, "status": "active", "role": {"$ne": "upsell"}}
    ).to_list(50)
    if not products:
        raise HTTPException(
            422,
            "Aucun produit principal dans le catalogue — importe d'abord des produits à l'étape 2.",
        )

    # Construction du contexte produits (max 12 items, descriptions courtes)
    lines = []
    for p in products[:12]:
        nm = _pick_text(p.get("name") or p.get("title"))
        desc = _pick_text(p.get("short_description") or p.get("description") or "")
        try:
            price = float(p.get("price") or p.get("price_eur") or 0)
        except Exception:
            price = 0.0
        lines.append(f"- « {nm[:120]} » | {price:.2f}€ | {desc[:160]}")
    products_block = "\n".join(lines)

    niche_hint = ""
    n = site.get("niche") or site.get("niche_label") or site.get("name")
    if isinstance(n, str) and n:
        niche_hint = f"Niche du site : {n}\n\n"

    system = (
        "Tu es un expert e-commerce silver economy / dropshipping premium spécialisé "
        "dans l'optimisation du panier moyen via les upsells et accessoires. "
        "Tu réponds UNIQUEMENT en JSON array valide, sans texte avant ou après, "
        "sans markdown fence."
    )
    user_prompt = f"""{niche_hint}Voici les produits actuellement dans le catalogue :

{products_block}

Suggère 8 à 10 upsells/accessoires pertinents pour augmenter le panier moyen.

Pour chaque suggestion, retourne un objet JSON strict avec ces clés :
{{
  "name": "Nom court et commercial du produit",
  "description": "1 à 2 phrases descriptives orientées bénéfice",
  "category": "accessoire" | "garantie" | "service" | "bundle",
  "estimated_price_eur": 19.90,
  "rationale": "Pourquoi cet upsell est pertinent pour ce catalogue",
  "search_keywords_aliexpress": ["mot-clé 1", "mot-clé 2"],
  "search_keywords_cj": ["mot-clé 1", "mot-clé 2"]
}}

Privilégie : housse de protection, kit de nettoyage, coussin orthopédique complémentaire,
télécommande de rechange, extension de garantie, accessoires d'installation,
kit de fixation, plateau repas adapté, repose-pieds compatible, etc.

Évite : autres produits du même type que ceux déjà en catalogue (cannibalisation),
produits non liés à la thématique.

Réponds UNIQUEMENT avec un tableau JSON `[...]`, sans aucun texte autour."""

    data, err = await _call_claude_json(system, user_prompt, timeout=120)
    if data is None:
        raise HTTPException(502, f"Génération IA indisponible : {err or 'unknown'}")

    if isinstance(data, dict):
        # Au cas où Claude enveloppe : {"suggestions": [...]}
        for k in ("suggestions", "upsells", "items", "results"):
            if isinstance(data.get(k), list):
                data = data[k]
                break

    if not isinstance(data, list):
        raise HTTPException(502, "Réponse IA mal formée (pas un array)")

    now = datetime.now(timezone.utc).isoformat()
    docs = []
    for raw in data:
        norm = _normalize_suggestion(raw)
        if not norm:
            continue
        sid = str(uuid.uuid4())
        doc = {
            "_id": sid,
            "id": sid,
            "site_id": site_id,
            **norm,
            "status": "suggested",
            "created_at": now,
            "updated_at": now,
            "created_by": str(user.get("id") or ""),
        }
        docs.append(doc)

    if docs:
        await db.upsell_suggestions.insert_many(docs)

    # Strip _id (non JSON-serializable contexte)
    for d in docs:
        d.pop("_id", None)

    return {"ok": True, "count": len(docs), "suggestions": docs}


@router.get("/sites/{site_id}/upsells/suggestions")
async def list_upsell_suggestions(
    site_id: str,
    status: Optional[str] = None,
    user=Depends(get_current_user),
):
    await _check_site_access(site_id, user)
    q = {"site_id": site_id}
    if status:
        if status not in ("suggested", "adopted", "ignored"):
            raise HTTPException(400, "status invalide")
        q["status"] = status
    cursor = db.upsell_suggestions.find(q, {"_id": 0}).sort("created_at", -1).limit(200)
    items = await cursor.to_list(200)
    counts = {
        "suggested": await db.upsell_suggestions.count_documents({"site_id": site_id, "status": "suggested"}),
        "adopted":   await db.upsell_suggestions.count_documents({"site_id": site_id, "status": "adopted"}),
        "ignored":   await db.upsell_suggestions.count_documents({"site_id": site_id, "status": "ignored"}),
    }
    return {"ok": True, "items": items, "counts": counts}


@router.patch("/sites/{site_id}/upsells/suggestions/{suggestion_id}")
async def update_upsell_suggestion(
    site_id: str,
    suggestion_id: str,
    body: StatusUpdate,
    user=Depends(get_current_user),
):
    await _check_site_access(site_id, user)
    if body.status not in ("suggested", "adopted", "ignored"):
        raise HTTPException(400, "status invalide")
    res = await db.upsell_suggestions.update_one(
        {"site_id": site_id, "id": suggestion_id},
        {"$set": {"status": body.status, "updated_at": datetime.now(timezone.utc).isoformat()}},
    )
    if res.matched_count == 0:
        raise HTTPException(404, "Suggestion introuvable")
    doc = await db.upsell_suggestions.find_one({"id": suggestion_id}, {"_id": 0})
    return {"ok": True, "suggestion": doc}


# ─── Index Mongo (boot) ──────────────────────────────────────────────────

async def ensure_indexes():
    try:
        await db.upsell_suggestions.create_index([("site_id", 1), ("status", 1), ("created_at", -1)])
    except Exception:
        logger.exception("[upsells_ai] ensure_indexes failed (non-blocking)")
