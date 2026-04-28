"""Phase 2.5 (Tâche B) — AI-Tweak endpoint.

Le concepteur peut taper un prompt en langage naturel à l'étape 5 du Cockpit
(ex : "palette ivoire et terracotta", "ton plus chaleureux sur les produits")
→ on envoie ça à Claude Sonnet 4.5 qui retourne un JSON patch ciblé sur un
WHITELIST de champs sûrs, et on l'applique en DB sur le site.

Safety :
  - Whitelist stricte : design.palette.*, design.font_pair.*, design.brand.*,
    design.tone_voice, design.navigation.*, cms_pages.*, seo.*
  - Blacklist explicite : products.*, orders.*, users.*, billing.*, mollie_*
  - Snapshot automatique du `design` avant modification (undo possible 24 h)

Cost : ~0,02 $ par tweak (Sonnet 4.5 input + output courts).
"""
from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from deps import db, get_current_user, _check_site_access

logger = logging.getLogger("altiaro.ai_tweak")
router = APIRouter()


# -------------------------------------------------------------------------
# Whitelist of modifiable dot-paths (only these fields can be patched)
# -------------------------------------------------------------------------
WHITELISTED_PATHS = [
    "design.palette.primary",
    "design.palette.secondary",
    "design.palette.accent",
    "design.palette.background",
    "design.palette.surface",
    "design.palette.text",
    "design.font_pair.heading",
    "design.font_pair.body",
    "design.brand.voice",
    "design.brand.tone_voice",
    "design.brand.tagline.fr",
    "design.brand.tagline.en",
    "design.brand.manifesto.fr",
    "design.brand.manifesto.en",
    "design.tone_voice",
    "design.navigation.primary",
    "design.navigation.footer",
    "design.homepage_sections",
]
BLACKLIST_ROOTS = ["products", "orders", "users", "billing", "mollie",
                   "payments", "domains", "ledger", "oauth", "stripe"]


class AiTweakRequest(BaseModel):
    prompt: str = Field(..., min_length=3, max_length=1200)


def _strip_fence(t: str) -> str:
    return re.sub(r"^```(?:json)?\s*|\s*```$", "", (t or "").strip(), flags=re.MULTILINE).strip()


def _get_path(obj: Dict[str, Any], path: str) -> Any:
    cur: Any = obj
    for seg in path.split("."):
        if not isinstance(cur, dict) or seg not in cur:
            return None
        cur = cur[seg]
    return cur


def _is_path_allowed(path: str) -> bool:
    root = path.split(".", 1)[0]
    if root in BLACKLIST_ROOTS:
        return False
    return any(path == w or path.startswith(w + ".") for w in WHITELISTED_PATHS)


@router.post("/sites/{site_id}/design/ai-tweak",
             tags=["design"],
             summary="AI tweak — natural language design modification via Sonnet 4.5")
async def ai_tweak_site(
    site_id: str,
    body: AiTweakRequest,
    user: dict = Depends(get_current_user),
):
    site = await _check_site_access(site_id, user)
    if not site:
        raise HTTPException(404, "Site introuvable")

    # Build a COMPACT snapshot of the current tweakable fields for Claude
    current_state = {p: _get_path(site, p) for p in WHITELISTED_PATHS}
    current_state = {k: v for k, v in current_state.items() if v is not None}

    system = (
        "Tu es assistant de design pour une plateforme e-commerce multi-tenant. "
        "Le concepteur te décrit en langage naturel les modifications à apporter "
        "à SON site. Tu retournes UNIQUEMENT un JSON valide avec la liste des "
        "changements à effectuer sur les champs autorisés.\n\n"
        "RÈGLES :\n"
        "- Tu ne modifies QUE les champs listés dans `allowed_paths`.\n"
        "- Pour chaque changement, tu fournis : `path` (dot-notation), `old`, "
        "`new`, `rationale` (1 phrase).\n"
        "- Les couleurs sont des hex codes (#RRGGBB). Pour une palette, propose "
        "6 valeurs cohérentes (primary/secondary/accent/background/surface/text).\n"
        "- Le ton de voix : chaîne courte parmi "
        "{premium, chaleureux, institutionnel, minimal, artisanal, joyeux, sobre}.\n"
        "- Si la demande est hors scope (ex: changer un prix), tu retournes "
        '{"changes": [], "refused": "raison"} sans rien modifier.'
    )
    user_msg = (
        f"ÉTAT ACTUEL (extrait, champs autorisés uniquement) :\n"
        f"{json.dumps(current_state, ensure_ascii=False, indent=2)}\n\n"
        f"ALLOWED_PATHS : {WHITELISTED_PATHS}\n\n"
        f"DEMANDE DU CONCEPTEUR : {body.prompt}\n\n"
        f"Réponds SEULEMENT ce JSON :\n"
        f'{{"changes": [{{"path": "...", "old": <val>, "new": <val>, "rationale": "..."}}], "summary": "<1 phrase>"}}'
    )

    try:
        from services.llm_resilience import safe_claude_text
        raw = await safe_claude_text(
            system=system, user=user_msg,
            quality_tier="premium", timeout=40.0,
            request_id=f"ai-tweak-{site_id[:8]}",
        )
    except Exception as e:
        logger.exception(f"[ai-tweak] {site_id} claude failed")
        raise HTTPException(502, f"LLM indisponible : {str(e)[:200]}")

    cleaned = _strip_fence(raw or "")
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]+\}", cleaned)
        if not m:
            raise HTTPException(502, "Réponse LLM non parsable")
        data = json.loads(m.group(0))

    refused = data.get("refused")
    changes = data.get("changes") or []
    if refused or not changes:
        return {
            "ok": False, "refused": refused or "Aucun changement proposé",
            "summary": data.get("summary") or "",
            "changes_applied": 0, "changes_rejected": [], "snapshot_id": None,
        }

    # Validate & apply
    snapshot_id = str(uuid.uuid4())
    await db.site_snapshots.insert_one({
        "id": snapshot_id,
        "site_id": site_id,
        "created_at": datetime.now(timezone.utc),
        "expires_at": datetime.now(timezone.utc) + timedelta(hours=48),
        "reason": "ai-tweak",
        "prompt": body.prompt[:600],
        "snapshot_fields": current_state,
    })

    applied: List[Dict[str, Any]] = []
    rejected: List[Dict[str, Any]] = []
    dot_set: Dict[str, Any] = {}
    for c in changes[:20]:
        if not isinstance(c, dict):
            continue
        path = str(c.get("path") or "").strip()
        if not path or not _is_path_allowed(path):
            rejected.append({"path": path, "reason": "path_not_allowed"})
            continue
        new_val = c.get("new")
        old_val = c.get("old")
        # Clamp hex colors
        if "palette" in path and isinstance(new_val, str):
            if not re.match(r"^#[0-9a-fA-F]{6}$", new_val.strip()):
                rejected.append({"path": path, "reason": "bad_hex"})
                continue
            new_val = new_val.strip().upper()
        dot_set[path] = new_val
        applied.append({
            "path": path,
            "old": old_val,
            "new": new_val,
            "rationale": (c.get("rationale") or "")[:200],
        })

    if dot_set:
        await db.sites.update_one(
            {"id": site_id},
            {"$set": {**dot_set, "design.ai_tweaked_at": datetime.now(timezone.utc).isoformat()}},
        )
        logger.info(f"[ai-tweak] {site_id} applied {len(applied)} changes "
                    f"(snapshot={snapshot_id}, rejected={len(rejected)})")

    return {
        "ok": True,
        "summary": data.get("summary") or f"{len(applied)} changement(s) appliqué(s)",
        "changes_applied": len(applied),
        "changes": applied,
        "changes_rejected": rejected,
        "snapshot_id": snapshot_id,
    }


@router.post("/sites/{site_id}/design/ai-tweak/undo",
             tags=["design"],
             summary="Revert last AI-tweak using snapshot_id")
async def ai_tweak_undo(
    site_id: str,
    snapshot_id: str,
    user: dict = Depends(get_current_user),
):
    site = await _check_site_access(site_id, user)
    if not site:
        raise HTTPException(404, "Site introuvable")
    snap = await db.site_snapshots.find_one({"id": snapshot_id, "site_id": site_id})
    if not snap:
        raise HTTPException(404, "Snapshot introuvable ou expiré")
    # MongoDB retourne les datetimes en naive (tzinfo None). On normalise
    # en UTC-aware avant comparaison pour éviter le TypeError
    # `can't compare offset-naive and offset-aware datetimes`.
    exp = snap.get("expires_at")
    if exp is not None:
        if getattr(exp, "tzinfo", None) is None:
            try:
                exp = exp.replace(tzinfo=timezone.utc)
            except Exception:
                exp = None
        if exp is not None and exp < datetime.now(timezone.utc):
            raise HTTPException(410, "Snapshot expiré")
    fields = snap.get("snapshot_fields") or {}
    if not fields:
        return {"ok": False, "reverted": 0}
    await db.sites.update_one({"id": site_id}, {"$set": fields})
    return {"ok": True, "reverted": len(fields)}
