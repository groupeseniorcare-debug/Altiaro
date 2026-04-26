"""Public routes for Altiaro platform (landing, legal pages).
No auth required — crawlable by Google, Mollie reviewers, etc."""

import asyncio
import logging
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, HTTPException
from altiaro_legal import get_legal_page
from platform_policy import get_platform_policy

router = APIRouter(prefix="/platform", tags=["platform"])
logger = logging.getLogger("conceptfactory.platform")

# How long a `budget_exhausted` flag is trusted before we re-probe the LLM.
# Short value = the user gets unblocked fast as soon as they recharge.
LLM_STALE_AFTER = timedelta(minutes=10)
# Minimum interval between two auto-probes (avoids hammering Claude).
LLM_PROBE_COOLDOWN = timedelta(seconds=60)


async def _probe_llm_budget() -> bool:
    """Fast, cheap Claude call (1-2 tokens). Returns True if the LLM answers
    without a budget error — meaning the Universal Key has credits again.

    Phase 0 — délègue à `safe_claude_text` (retry + circuit breaker). Si le
    breaker est OPEN, on retourne False directement (pas de probe inutile).
    """
    try:
        import os
        key = os.environ.get("EMERGENT_LLM_KEY", "")
        if not key:
            return False
        from services.llm_resilience import safe_claude_text, LLMUnavailableError
        try:
            raw = await safe_claude_text(
                "Reply with the single word OK.",
                "ping",
                session_id=f"probe-{datetime.now(timezone.utc).timestamp()}",
                timeout=15,
            )
            return bool(raw)
        except LLMUnavailableError:
            # breaker OPEN or retries exhausted — flag stays bad
            return False
        except ValueError:
            # JSON parse error doesn't apply here (text), but defensive
            return False
    except Exception as e:
        msg = str(e)
        if "Budget has been exceeded" in msg or ("budget" in msg.lower() and "exceeded" in msg.lower()):
            return False
        # Transient errors → don't flip the flag, stay pessimistic.
        logger.warning(f"[llm-probe] transient error, keeping flag: {msg[:120]}")
        return False


@router.get("/legal/{slug}")
async def public_legal_page(slug: str):
    """Return the platform-level legal page content as JSON.
    Available slugs: mentions-legales, cgu, confidentialite, cookies."""
    page = get_legal_page(slug)
    if not page:
        raise HTTPException(status_code=404, detail="Page non trouvée")
    return page


@router.get("/info")
async def platform_info():
    """Public meta about the Altiaro platform — consumed by the landing page."""
    return {
        "name": "Altiaro",
        "legal_name": "Robin Zuchiatti (entrepreneur individuel)",
        "tagline": "La plateforme e-commerce des partenariats éclairés.",
        "value_prop": (
            "Altiaro accompagne les entrepreneurs qui lancent des marques "
            "e-commerce premium dans la Silver Economy — 50% de la marge brute "
            "partagée équitablement, sites générés par IA, scan de niches "
            "multi-marchés et cockpit de pilotage complet."
        ),
        "email": "contact@altiaro.com",
        "website": "https://altiaro.com",
        "founded": 2026,
        "markets": ["FR", "DE", "BL", "NL", "CH", "UK"],
    }


@router.get("/policy")
async def platform_policy_admin():
    """Politique plateforme Altiaro exposée aux Concepteurs (lecture seule)."""
    return get_platform_policy()


@router.get("/public/policy")
async def platform_policy_public():
    """Subset de la politique exposé sur tous les storefronts (FAQ, checkout, footer)."""
    p = get_platform_policy()
    return {
        "shipping": {
            "label": p["shipping"]["label"],
            "covered_countries": p["shipping"]["covered_countries"],
            "delivery_estimate": p["shipping"]["delivery_estimate"],
        },
        "payment": {
            "provider": p["payment"]["provider"],
            "methods_enabled": p["payment"]["methods_enabled"],
        },
        "returns": {"label": p["returns"]["label"]},
        "warranty": {"label": p["warranty"]["label"], "years": p["warranty"]["years"]},
        "customer_service": p["customer_service"],
    }



@router.get("/llm-status")
async def llm_status(force: int = 0):
    """Returns the current LLM (Emergent Key) health status.
    Auto-recovers:
      - If the flag is older than LLM_STALE_AFTER (10 min), silently clear it.
      - If the flag is fresh but hasn't been probed in the last minute,
        fire a 1-token test call. If Claude answers → clear the flag.
      - Pass `?force=1` to bypass the probe cooldown (used by the banner button).
    The Cockpit banner is therefore self-healing without user action.
    """
    from deps import db
    doc = await db.platform_health.find_one({"key": "llm"}, {"_id": 0}) or {}
    status = doc.get("status") or "ok"
    last_err = doc.get("last_error_at")
    last_probe = doc.get("last_probe_at")

    if status != "budget_exhausted":
        return {"status": status, "last_error_at": last_err}

    now = datetime.now(timezone.utc)

    def _parse(ts):
        try:
            return datetime.fromisoformat((ts or "").replace("Z", "+00:00"))
        except (ValueError, TypeError, AttributeError):
            return None

    err_ts = _parse(last_err)
    probe_ts = _parse(last_probe)
    probe_stale = (not probe_ts) or (now - probe_ts) > LLM_PROBE_COOLDOWN
    flag_stale = bool(err_ts) and (now - err_ts) > LLM_STALE_AFTER

    if force or flag_stale or probe_stale:
        ok = await _probe_llm_budget()
        await db.platform_health.update_one(
            {"key": "llm"},
            {"$set": {
                "key": "llm",
                "status": "ok" if ok else "budget_exhausted",
                "last_probe_at": now.isoformat(),
                **({"last_error_at": now.isoformat()} if not ok else {}),
            }},
            upsert=True,
        )
        return {"status": "ok" if ok else "budget_exhausted",
                "last_error_at": last_err, "auto_cleared": ok}

    return {"status": "budget_exhausted", "last_error_at": last_err}


@router.post("/llm-status/clear")
async def llm_status_clear():
    """Clear the LLM error flag — called when user confirms they've recharged the key."""
    from deps import db
    await db.platform_health.update_one(
        {"key": "llm"}, {"$set": {"key": "llm", "status": "ok", "last_error_at": None}},
        upsert=True,
    )
    return {"ok": True, "status": "ok"}
