"""Phase 3.2 — Reset du snapshot budget LLM Altiaro.

Utilisé par l'admin quand il a rechargé ses crédits Emergent : un seul appel
efface `platform_health.llm_budget` (snapshot figé à 100 %) et reset
`platform_health.llm` de `budget_exhausted` → `ok`, pour qu'un launch
subséquent ne soit pas bloqué par un ancien état.

NOTE : Altiaro N'A PAS de cap artificiel sur le budget LLM global d'un launch.
Le cap observé ("Budget has been exceeded! Current cost: X") vient du PROXY
Emergent LLM Key, pas du code Altiaro. Seul cap code-side : 5 $/site pour les
images variantes couleur Nano Banana (`DEFAULT_BUDGET_CAP_USD` dans
`services/product_variant_pipeline.py`), volontaire et raisonnable.
"""
from __future__ import annotations

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException

from deps import db, get_current_user

router = APIRouter(tags=["admin-llm-health"])


def _require_admin(user: dict):
    if user.get("role") != "admin":
        raise HTTPException(403, "Admin only")


@router.post("/admin/llm-budget/reset")
async def reset_llm_budget_snapshot(user: dict = Depends(get_current_user)):
    """Efface les 2 docs `platform_health.{llm, llm_budget}` pour repartir clean.

    À appeler après avoir rechargé le compte Emergent LLM Key. Idempotent.
    """
    _require_admin(user)
    now = datetime.now(timezone.utc).isoformat()
    res_health = await db.platform_health.delete_one({"key": "llm_budget"})
    res_flag = await db.platform_health.update_one(
        {"key": "llm"},
        {"$set": {
            "key": "llm",
            "status": "ok",
            "last_success_at": now,
            "reset_at": now,
            "reset_by": user.get("email") or user.get("id"),
        }},
        upsert=True,
    )
    # Also wipe in-memory snapshot if the module is loaded
    try:
        from services import llm_resilience as _lr
        _lr._LAST_BUDGET_SNAPSHOT.update({
            "used_usd": None, "max_usd": None, "captured_at": None,
        })
    except Exception:
        pass
    return {
        "ok": True,
        "cleared_snapshot": bool(res_health.deleted_count),
        "llm_flag_reset": bool(res_flag.matched_count or res_flag.upserted_id),
        "reset_at": now,
    }
