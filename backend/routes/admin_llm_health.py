"""
Admin endpoint /api/admin/llm-health — Phase 0 LLM Resilience.
Admin endpoint /api/admin/llm-budget  — Bloc 1 sous-chantier 2.

Returns the live state of the LLM circuit breakers (Claude + Nano Banana)
plus the resilience config so an external monitor (or the LaunchProgress UI)
can decide whether to retry now or wait for the breaker to half-open.
"""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from deps import db, require_admin
from services.llm_resilience import get_llm_health, get_llm_budget_estimate

logger = logging.getLogger("altiaro.admin_llm_health")
router = APIRouter(prefix="/admin", tags=["admin-llm-health"])


@router.get("/llm-health")
async def llm_health(_user=Depends(require_admin)):
    """
    Returns:
      {
        "overall": "healthy" | "degraded" | "down",
        "breakers": {
          "claude":      { state, consecutive_failures, recent_failures_60s,
                           opened_at, last_success_at, last_failure_at,
                           last_error, transitions[…] },
          "nano_banana": { … }
        },
        "config": { max_attempts, retry_delays_s, jitter_pct, circuit_threshold,
                    circuit_open_duration, sliding_window_s },
        "ts": ISO datetime
      }
    """
    return get_llm_health()


@router.get("/llm-budget")
async def llm_budget(_user=Depends(require_admin)):
    """Bloc 1 sous-chantier 2 — returns the last-known LLM budget snapshot.

    The Emergent LLM Key has a monthly USD budget enforced server-side by
    LiteLLM. We can't poll Emergent's billing API directly, so we sniff the
    "Budget has been exceeded! Current cost: X, Max budget: Y" exception
    messages and persist them into `platform_health.llm_budget`.

    Output:
      { used_usd, max_usd, pct, captured_at, alert_level, days_remaining_in_month }

    `alert_level` :
      - "ok"       → pct < 80
      - "warning"  → 80 ≤ pct < 95
      - "critical" → pct ≥ 95
      - "unknown"  → no error captured yet (budget still healthy)

    Side effect : if alert_level is warning or critical AND no notification
    has been emitted today, insert a row into `admin_notifications` (dedup
    per day so admin gets at most 1 ping per day per level).
    """
    snap = await get_llm_budget_estimate()
    level = snap.get("alert_level")
    if level in ("warning", "critical"):
        await _maybe_notify_admin(level, snap)
    return snap


async def _maybe_notify_admin(level: str, snap: dict) -> None:
    """Idempotent : emits a notification at most once per day per (level)."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    dedup_key = f"llm-budget-{level}-{today}"
    try:
        existing = await db.admin_notifications.find_one({"dedup_key": dedup_key})
        if existing:
            return
        msg = (
            f"⚠️ Budget LLM Emergent à {snap.get('pct')}% "
            f"({snap.get('used_usd')}$ / {snap.get('max_usd')}$ utilisés). "
            f"{'Recharge urgente' if level == 'critical' else 'Recharge à prévoir'}."
        )
        await db.admin_notifications.insert_one({
            "id":         f"notif-{dedup_key}",
            "dedup_key":  dedup_key,
            "type":       "llm_budget",
            "level":      level,
            "title":      "Budget IA — alerte" if level == "warning" else "Budget IA — critique",
            "body":       msg,
            "snapshot":   snap,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "read":       False,
        })
        logger.warning(f"[llm-budget] {level} notification emitted (dedup={dedup_key})")
    except Exception:
        logger.exception("[llm-budget] notification failed (non-blocking)")


# Public read-only mini-version (no admin required) — used by the LaunchProgress
# UI pill so non-admin Concepteurs see the upstream health too.
public_router = APIRouter(prefix="/platform", tags=["platform"])


@public_router.get("/llm-health")
async def llm_health_public():
    h = get_llm_health()
    # Strip noisy details for non-admin
    return {
        "overall": h["overall"],
        "breakers": {
            name: {"state": b["state"], "recent_failures_60s": b["recent_failures_60s"]}
            for name, b in h["breakers"].items()
        },
        "ts": h["ts"],
    }
