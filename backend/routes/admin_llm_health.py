"""
Admin endpoint /api/admin/llm-health — Phase 0 LLM Resilience.

Returns the live state of the LLM circuit breakers (Claude + Nano Banana)
plus the resilience config so an external monitor (or the LaunchProgress UI)
can decide whether to retry now or wait for the breaker to half-open.
"""
from fastapi import APIRouter, Depends

from deps import require_admin
from services.llm_resilience import get_llm_health

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
