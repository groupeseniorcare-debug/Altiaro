"""
LLM Resilience layer — Phase 0 Altiaro
========================================

Centralised wrapper around Claude (text) and Nano Banana (image) calls with :
- Exponential backoff + jitter retry (3 tries, 2s/8s/32s)
- Per-provider circuit breaker (CLOSED → OPEN → HALF_OPEN)
- Structured logging (request_id + attempt + error_class)
- Differentiated retry policy : retry on 502/503/504/timeout/429,
  no retry on 4xx (except 408/429) or JSON parse errors

Public API
----------
- `LLMUnavailableError` : raised when circuit is OPEN or all retries exhausted
- `safe_claude_json(system, user, *, timeout=90, request_id=None)` : returns
  the parsed JSON dict (Claude is asked to reply in strict JSON ; we strip
  fences ourselves)
- `safe_claude_text(system, user, *, timeout=90, request_id=None)` : returns
  the raw text reply (no JSON parsing)
- `safe_nano_banana(prompt, *, site_id=None, product_id=None, timeout=60,
   request_id=None)` : returns the persisted upload URL or None on degraded
- `get_llm_health()` : returns dict for the /admin/llm-health endpoint

NOTE — every direct call to LlmChat in the codebase MUST be migrated to one
of these helpers. The Phase 0 audit grep is :
    grep -rn "LlmChat\|chat.send_message" backend/routes/ \\
        | grep -v "from services.llm_resilience"
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import random
import re
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Dict, Optional

logger = logging.getLogger("altiaro.llm_resilience")

# ─── Config ──────────────────────────────────────────────────────────────
RETRY_DELAYS_S = (2.0, 8.0, 32.0)        # 3 tentatives = 1 initiale + 3 retries (4 essais total max)
JITTER_PCT = 0.25                         # ±25% sur chaque délai

CIRCUIT_FAILURE_THRESHOLD = 5             # 5 échecs consécutifs ouvrent le breaker
CIRCUIT_OPEN_DURATION_S = 5 * 60          # 5 min en OPEN avant HALF_OPEN
SLIDING_WINDOW_S = 60                     # fenêtre glissante pour le compteur

# ─── Cost-tier model mapping (Phase 1) ───────────────────────────────────
# Bloc 1 sous-chantier 1a — pour réduire le coût d'un launch-auto premium
# de ~$19 à ~$5-8, on bascule par défaut sur Haiku (≈3× moins cher) pour
# tous les usages copywriting / éditorial / blog / témoignages texte.
# Les usages "premium" (brand identity, mission, voice, SEO core) gardent
# Sonnet 4.5.
ANTHROPIC_MODEL_PREMIUM = "claude-sonnet-4-5-20250929"
ANTHROPIC_MODEL_STANDARD = "claude-haiku-4-5-20251001"

def _resolve_anthropic_model(model: Optional[str], quality_tier: Optional[str]) -> str:
    """Pick the right Anthropic model id from `quality_tier` or explicit `model`.
    Explicit `model` wins. `quality_tier` only mapping if model is None."""
    if model:
        return model
    if quality_tier == "premium":
        return ANTHROPIC_MODEL_PREMIUM
    # Default = standard (Haiku) — applies when caller passes nothing
    return ANTHROPIC_MODEL_STANDARD

# Exceptions HTTP-like qui DOIVENT être retryées
RETRYABLE_KEYWORDS = (
    "BadGatewayError",
    "ServiceUnavailableError",
    "GatewayTimeoutError",
    "Error code: 502",
    "Error code: 503",
    "Error code: 504",
    "Error code: 408",
    "Error code: 429",
    "Read timed out",
    "ReadTimeout",
    "Connection error",
    "RemoteProtocolError",
)

JSON_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```\s*$", re.MULTILINE)

EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")


# ─── Errors ──────────────────────────────────────────────────────────────
class LLMUnavailableError(Exception):
    """Raised when the LLM cannot be reached (circuit OPEN or retries exhausted).

    Carries `provider`, `request_id`, `last_error`, `attempts` for log/UI."""
    def __init__(self, message: str, provider: str = "?", request_id: str = "?",
                 last_error: Optional[str] = None, attempts: int = 0) -> None:
        super().__init__(message)
        self.provider = provider
        self.request_id = request_id
        self.last_error = last_error
        self.attempts = attempts


# ─── Circuit Breaker ─────────────────────────────────────────────────────
@dataclass
class CircuitBreaker:
    name: str
    state: str = "CLOSED"            # CLOSED | OPEN | HALF_OPEN
    consecutive_failures: int = 0
    opened_at: Optional[float] = None
    last_success_at: Optional[float] = None
    last_failure_at: Optional[float] = None
    last_error: Optional[str] = None
    recent_failures: list[float] = field(default_factory=list)  # timestamps in sliding window
    transitions: list[dict] = field(default_factory=list)        # audit trail (last 20)

    def _now(self) -> float:
        return time.time()

    def record_success(self) -> None:
        now = self._now()
        if self.state in ("OPEN", "HALF_OPEN"):
            self._transition("CLOSED", reason=f"success in {self.state}")
        self.state = "CLOSED"
        self.consecutive_failures = 0
        self.opened_at = None
        self.last_success_at = now
        # purge sliding window
        cutoff = now - SLIDING_WINDOW_S
        self.recent_failures = [t for t in self.recent_failures if t >= cutoff]

    def record_failure(self, err_msg: str) -> None:
        now = self._now()
        self.last_failure_at = now
        self.last_error = err_msg[:200]
        self.consecutive_failures += 1
        # sliding window
        cutoff = now - SLIDING_WINDOW_S
        self.recent_failures = [t for t in self.recent_failures if t >= cutoff]
        self.recent_failures.append(now)
        if self.consecutive_failures >= CIRCUIT_FAILURE_THRESHOLD and self.state != "OPEN":
            self.state = "OPEN"
            self.opened_at = now
            self._transition("OPEN", reason=f"{self.consecutive_failures} consecutive failures")

    def can_attempt(self) -> bool:
        if self.state == "CLOSED":
            return True
        if self.state == "OPEN":
            if self.opened_at and (self._now() - self.opened_at) >= CIRCUIT_OPEN_DURATION_S:
                self.state = "HALF_OPEN"
                self._transition("HALF_OPEN", reason="open duration elapsed")
                return True   # 1 probe attempt
            return False
        # HALF_OPEN — only 1 attempt at a time, but we don't enforce strict
        # serialisation (good enough for our throughput).
        return True

    def _transition(self, new_state: str, reason: str = "") -> None:
        ts = datetime.now(timezone.utc).isoformat()
        entry = {"ts": ts, "to": new_state, "reason": reason[:120]}
        self.transitions.append(entry)
        self.transitions = self.transitions[-20:]
        logger.warning(f"[circuit:{self.name}] → {new_state} ({reason})")

    def to_dict(self) -> dict:
        return {
            "name":                  self.name,
            "state":                 self.state,
            "consecutive_failures":  self.consecutive_failures,
            "recent_failures_60s":   len(self.recent_failures),
            "opened_at":             _iso(self.opened_at),
            "last_success_at":       _iso(self.last_success_at),
            "last_failure_at":       _iso(self.last_failure_at),
            "last_error":            self.last_error,
            "transitions":           self.transitions[-5:],
        }


def _iso(ts: Optional[float]) -> Optional[str]:
    if ts is None:
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


# Two independent breakers : Claude (text) and Nano Banana (image)
_BREAKERS: dict[str, CircuitBreaker] = {
    "claude":      CircuitBreaker(name="claude"),
    "nano_banana": CircuitBreaker(name="nano_banana"),
}


# ─── Retry logic ─────────────────────────────────────────────────────────
def _is_retryable(err: BaseException) -> bool:
    s = str(err)
    cls = err.__class__.__name__
    if isinstance(err, asyncio.TimeoutError):
        return True
    if cls in ("TimeoutError", "ReadTimeout", "ConnectError", "RemoteProtocolError"):
        return True
    for kw in RETRYABLE_KEYWORDS:
        if kw in s or kw in cls:
            return True
    return False


def _delay_for(attempt: int) -> float:
    # attempt is 0-indexed (0 = first retry after initial fail)
    if attempt >= len(RETRY_DELAYS_S):
        attempt = len(RETRY_DELAYS_S) - 1
    base = RETRY_DELAYS_S[attempt]
    jitter = base * JITTER_PCT * (2 * random.random() - 1)
    return max(0.5, base + jitter)


def _extract_retry_after(err: BaseException) -> Optional[float]:
    s = str(err)
    m = re.search(r"[Rr]etry[- ]?[Aa]fter[\":=\s]+(\d+)", s)
    if m:
        return float(m.group(1))
    return None


async def safe_llm_call(
    fn: Callable[[], Awaitable[Any]],
    *,
    provider: str,
    request_id: Optional[str] = None,
    timeout: float = 60.0,
    max_attempts: int = 4,   # 1 initial + 3 retries
) -> Any:
    """Generic resilience wrapper. `fn` is a 0-arg coroutine factory closure.

    Raises `LLMUnavailableError` on circuit OPEN or all retries exhausted.
    Re-raises non-retryable errors as-is (caller can catch them).
    """
    rid = request_id or uuid.uuid4().hex[:8]
    breaker = _BREAKERS.get(provider)
    if breaker is None:
        breaker = _BREAKERS.setdefault(provider, CircuitBreaker(name=provider))

    if not breaker.can_attempt():
        raise LLMUnavailableError(
            f"Circuit breaker OPEN for {provider} — short-circuit",
            provider=provider, request_id=rid,
            last_error=breaker.last_error, attempts=0,
        )

    last_err: Optional[BaseException] = None
    for attempt in range(max_attempts):
        try:
            result = await asyncio.wait_for(fn(), timeout=timeout)
            breaker.record_success()
            if attempt > 0:
                logger.info(f"[llm:{provider}] rid={rid} OK on retry #{attempt}")
            return result
        except LLMUnavailableError:
            raise   # don't retry inside another resilience call
        except (asyncio.TimeoutError, Exception) as e:  # noqa: BLE001
            last_err = e
            err_cls = e.__class__.__name__
            # Bloc 1 sous-chantier 2 — sniff budget snapshot from any exception
            # message so /admin/llm-budget always has fresh data.
            try:
                _maybe_record_budget_snapshot(str(e))
            except Exception:
                pass
            if not _is_retryable(e) or attempt >= max_attempts - 1:
                breaker.record_failure(f"{err_cls}: {str(e)[:120]}")
                logger.warning(
                    f"[llm:{provider}] rid={rid} attempt={attempt+1}/{max_attempts} "
                    f"FAIL non-retryable={not _is_retryable(e)} err={err_cls}: {str(e)[:120]}"
                )
                if not _is_retryable(e):
                    raise   # bubble up application error (4xx, parse, etc.)
                # Retries exhausted → wrap into LLMUnavailableError
                raise LLMUnavailableError(
                    f"{provider} unavailable after {attempt+1} attempts: {err_cls}",
                    provider=provider, request_id=rid,
                    last_error=str(e)[:200], attempts=attempt + 1,
                ) from e

            # Decide delay
            ra = _extract_retry_after(e)
            delay = ra if ra is not None else _delay_for(attempt)
            logger.warning(
                f"[llm:{provider}] rid={rid} attempt={attempt+1}/{max_attempts} "
                f"transient err={err_cls}: {str(e)[:100]} → retry in {delay:.1f}s"
            )
            await asyncio.sleep(delay)

    # Should not reach here, but in case
    raise LLMUnavailableError(
        f"{provider} unavailable",
        provider=provider, request_id=rid,
        last_error=str(last_err)[:200] if last_err else None, attempts=max_attempts,
    )


# ─── High-level helpers ──────────────────────────────────────────────────
def _strip_json_fence(text: str) -> str:
    return JSON_FENCE_RE.sub("", (text or "").strip()).strip()


async def safe_llm_text(
    provider: str,
    model: str,
    system: str,
    user: str,
    *,
    session_id: Optional[str] = None,
    timeout: float = 90.0,
    request_id: Optional[str] = None,
) -> str:
    """Generic single-shot LLM call (any provider supported by emergentintegrations).

    Like `safe_claude_text` but lets the caller pick the provider/model. Useful
    for `routes/steps.py` where the user can choose between Anthropic/OpenAI/Gemini.
    The breaker is keyed on the provider name (`claude` for `anthropic`, else
    the provider name itself).
    """
    if not EMERGENT_LLM_KEY:
        raise LLMUnavailableError("EMERGENT_LLM_KEY missing", provider=provider)
    sid = session_id or f"safe-{uuid.uuid4().hex[:8]}"

    async def _do() -> str:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        chat = (
            LlmChat(api_key=EMERGENT_LLM_KEY, session_id=sid, system_message=system)
            .with_model(provider, model)
        )
        raw = await chat.send_message(UserMessage(text=user))
        return raw if isinstance(raw, str) else str(raw)

    breaker_name = "claude" if provider == "anthropic" else provider
    return await safe_llm_call(_do, provider=breaker_name,
                               request_id=request_id, timeout=timeout)


async def safe_claude_text(
    system: str,
    user: str,
    *,
    model: Optional[str] = None,
    quality_tier: str = "standard",
    session_id: Optional[str] = None,
    timeout: float = 90.0,
    request_id: Optional[str] = None,
    initial_messages: Optional[list] = None,
) -> str:
    """Send a single-shot user message to Claude with full resilience.

    Returns the raw text reply (no parsing). Raises LLMUnavailableError on
    persistent upstream failure.

    `quality_tier` (default "standard") :
      - "standard" → claude-haiku-4-5-20251001 (≈3× moins cher, suffisant pour
        copywriting éditorial, blog drafts, témoignages texte, narrative)
      - "premium"  → claude-sonnet-4-5-20250929 (réservé brand identity,
        mission/voice, SEO core, keyword strategy critiques)
    Explicit `model` overrides `quality_tier`.

    `initial_messages` (optional) — list of {"role": "user"|"assistant",
    "content": "..."} for multi-turn conversations (used by the Copilot).
    """
    if not EMERGENT_LLM_KEY:
        raise LLMUnavailableError("EMERGENT_LLM_KEY missing", provider="claude")
    sid = session_id or f"safe-{uuid.uuid4().hex[:8]}"
    resolved_model = _resolve_anthropic_model(model, quality_tier)

    async def _do() -> str:
        # Local import = avoid hard dep on emergentintegrations at module load
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        kwargs = {"api_key": EMERGENT_LLM_KEY, "session_id": sid, "system_message": system}
        if initial_messages:
            kwargs["initial_messages"] = initial_messages
        chat = LlmChat(**kwargs).with_model("anthropic", resolved_model)
        raw = await chat.send_message(UserMessage(text=user))
        text = raw if isinstance(raw, str) else str(raw)
        # Cost tracking auto-record (no-op si aucun job_id n'est dans le contexte)
        try:
            from services.cost_tracker import (
                record_text, get_current_job_id, get_current_bucket,
            )
            record_text(
                get_current_job_id(),
                model=resolved_model,
                input_text=(system or "") + "\n" + (user or ""),
                output_text=text,
                bucket=get_current_bucket(),
            )
        except Exception:
            pass
        return text

    return await safe_llm_call(_do, provider="claude", request_id=request_id, timeout=timeout)


async def safe_claude_json(
    system: str,
    user: str,
    *,
    model: Optional[str] = None,
    quality_tier: str = "standard",
    session_id: Optional[str] = None,
    timeout: float = 90.0,
    request_id: Optional[str] = None,
) -> dict | list:
    """Same as safe_claude_text but parses the JSON reply.

    JSON parse errors are NOT retried (it's an application-level concern :
    Claude returned text, the prompt is wrong). They bubble up as ValueError.

    `quality_tier` defaults to "standard" (Haiku) — see safe_claude_text.
    Pass `quality_tier="premium"` to escalate to Sonnet for brand identity
    or critical SEO copy.
    """
    text = await safe_claude_text(
        system, user, model=model, quality_tier=quality_tier,
        session_id=session_id, timeout=timeout, request_id=request_id,
    )
    cleaned = _strip_json_fence(text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.warning(f"[claude-json] parse failed: {cleaned[:200]}")
        raise ValueError(f"Réponse Claude mal formée (JSON invalid): {e}") from e


async def safe_nano_banana_bytes(
    prompt: str,
    *,
    system: str = "",
    session_id: Optional[str] = None,
    timeout: float = 120.0,
    request_id: Optional[str] = None,
    reference_image_b64: Optional[str] = None,
) -> Optional[bytes]:
    """Generate an image with Nano Banana (gemini-3.1-flash-image-preview)
    and return the **raw decoded bytes** (typically PNG/JPEG). The caller
    is responsible for persisting the file (e.g. into uploads/).

    Returns None if the model returned no image data (degraded path —
    happens occasionally even on successful HTTP). Raises LLMUnavailableError
    on persistent upstream failure (502/503/504/timeout × 4 retries).

    Lot C — image-to-image support :
        Si `reference_image_b64` est fourni (base64 brut, sans préfixe data-uri),
        l'image est attachée comme contexte multimodal Gemini (`ImageContent`)
        ce qui permet de générer une variation cohérente avec la source
        (ex : « le même fauteuil que sur cette photo, scène lifestyle »).
        Sans `reference_image_b64`, comportement classique text→image.

    Used by routes/product_images.py and routes/testimonials_ai.py to keep
    `LlmChat(...)` import out of `routes/` (Phase 0 audit).
    """
    NANO_MODEL = "gemini-3.1-flash-image-preview"
    if not EMERGENT_LLM_KEY:
        raise LLMUnavailableError("EMERGENT_LLM_KEY missing", provider="nano_banana")
    sid = session_id or f"banana-{uuid.uuid4().hex[:8]}"

    async def _do() -> Optional[bytes]:
        import base64 as _b64
        from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent
        chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=sid,
                       system_message=system or "")
        chat.with_model("gemini", NANO_MODEL).with_params(modalities=["image", "text"])
        # Build the user message — attach reference image if provided (img-to-img mode)
        file_contents = []
        if reference_image_b64:
            file_contents.append(ImageContent(image_base64=reference_image_b64))
        msg = UserMessage(text=prompt, file_contents=file_contents)
        _, images = await chat.send_message_multimodal_response(msg)
        if not images:
            return None
        first = images[0]
        # The integrations layer returns either {data: <base64>} or {url: ...}
        if isinstance(first, dict) and first.get("data"):
            payload = _b64.b64decode(first["data"])
            try:
                from services.cost_tracker import record_image, get_current_job_id
                record_image(get_current_job_id(), n=1, bucket="images")
            except Exception:
                pass
            return payload
        return None

    return await safe_llm_call(_do, provider="nano_banana",
                               request_id=request_id, timeout=timeout)


async def safe_nano_banana(
    prompt: str,
    *,
    site_id: Optional[str] = None,
    product_id: Optional[str] = None,
    timeout: float = 90.0,
    request_id: Optional[str] = None,
    save_path_hint: Optional[str] = None,
) -> Optional[str]:
    """Generate a Nano Banana (gemini-3.1-flash-image-preview) image, persist
    to /app/backend/uploads/, return the public URL.

    Returns None if the call succeeds but the model returned no image data
    (degraded path). Raises LLMUnavailableError on persistent upstream failure.

    NB : if you call this 3× concurrently for the same product, you'll get
    3 different images — caller is responsible for batching.
    """
    NANO_MODEL = "gemini-3.1-flash-image-preview"
    if not EMERGENT_LLM_KEY:
        raise LLMUnavailableError("EMERGENT_LLM_KEY missing", provider="nano_banana")
    sid = f"banana-{uuid.uuid4().hex[:8]}"

    async def _do() -> Optional[str]:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=sid, system_message="")
        chat = chat.with_model("gemini", NANO_MODEL).with_params(modalities=["image", "text"])
        reply = await chat.send_message(UserMessage(text=prompt))
        # The integrations layer returns either a URL string, a dict with "image_url"/"url",
        # or a base64 data URI. We tolerate all 3 to remain forward-compatible.
        url = None
        if isinstance(reply, str):
            if reply.startswith(("http://", "https://", "/uploads/")):
                url = reply
        elif isinstance(reply, dict):
            url = reply.get("image_url") or reply.get("url") or reply.get("path")
        if url:
            try:
                from services.cost_tracker import record_image, get_current_job_id
                record_image(get_current_job_id(), n=1, bucket="images")
            except Exception:
                pass
        return url

    return await safe_llm_call(_do, provider="nano_banana",
                               request_id=request_id, timeout=timeout)


# ─── Health endpoint payload ─────────────────────────────────────────────
def get_llm_health() -> dict:
    """Return a snapshot for /api/admin/llm-health."""
    breakers = {name: br.to_dict() for name, br in _BREAKERS.items()}
    overall = "healthy"
    for br in _BREAKERS.values():
        if br.state == "OPEN":
            overall = "down"
            break
        if br.state == "HALF_OPEN" or len(br.recent_failures) >= 3:
            overall = "degraded"
    return {
        "overall":  overall,
        "breakers": breakers,
        "config": {
            "max_attempts":           4,
            "retry_delays_s":         list(RETRY_DELAYS_S),
            "jitter_pct":             JITTER_PCT,
            "circuit_threshold":      CIRCUIT_FAILURE_THRESHOLD,
            "circuit_open_duration":  CIRCUIT_OPEN_DURATION_S,
            "sliding_window_s":       SLIDING_WINDOW_S,
        },
        "ts": datetime.now(timezone.utc).isoformat(),
    }


def reset_breakers_for_tests() -> None:
    """Test helper — DO NOT call in production code paths."""
    for br in _BREAKERS.values():
        br.state = "CLOSED"
        br.consecutive_failures = 0
        br.opened_at = None
        br.last_success_at = None
        br.last_failure_at = None
        br.last_error = None
        br.recent_failures = []
        br.transitions = []



# ─── Budget tracking (Bloc 1 sous-chantier 2) ────────────────────────────
# Émettre un drapeau rouge AVANT que le budget Emergent LLM Key explose,
# pour que l'admin recharge à temps. On parse les messages d'erreur LiteLLM
# qui ressemblent à : "Budget has been exceeded! Current cost: 19.13, Max
# budget: 19.001" et on persiste un snapshot dans la collection
# `platform_health` (clé "llm_budget"). L'endpoint /admin/llm-budget lit ce
# document.
_BUDGET_REGEX = re.compile(
    r"Current cost:\s*([0-9]+\.?[0-9]*)\s*,\s*Max budget:\s*([0-9]+\.?[0-9]*)",
    re.IGNORECASE,
)
_LAST_BUDGET_SNAPSHOT: Dict[str, Any] = {
    "used_usd": None,
    "max_usd": None,
    "captured_at": None,
}


def _maybe_record_budget_snapshot(error_message: str) -> None:
    """Best-effort parse of LiteLLM budget error messages → in-memory cache.
    Persistance MongoDB séparée via `_persist_budget_snapshot()` (async, lazy)."""
    if not error_message:
        return
    m = _BUDGET_REGEX.search(error_message)
    if not m:
        return
    try:
        used = float(m.group(1))
        cap = float(m.group(2))
    except (ValueError, IndexError):
        return
    _LAST_BUDGET_SNAPSHOT.update({
        "used_usd": used,
        "max_usd": cap,
        "captured_at": datetime.now(timezone.utc).isoformat(),
    })
    # Fire-and-forget persistence (best effort, doesn't block the call path)
    try:
        loop = asyncio.get_event_loop()
        loop.create_task(_persist_budget_snapshot(used, cap))
    except RuntimeError:
        pass  # No running loop (test env) — in-memory snapshot is enough


async def _persist_budget_snapshot(used: float, cap: float) -> None:
    """Store the last budget snapshot in MongoDB (`platform_health.llm_budget`).
    Survives server restart."""
    try:
        from deps import db  # local import to avoid circular at module load
        await db.platform_health.update_one(
            {"key": "llm_budget"},
            {"$set": {
                "key": "llm_budget",
                "used_usd": used,
                "max_usd": cap,
                "pct": round((used / cap) * 100, 2) if cap > 0 else None,
                "captured_at": datetime.now(timezone.utc).isoformat(),
                "alert_level": "critical" if cap > 0 and used / cap >= 0.95
                              else "warning" if cap > 0 and used / cap >= 0.80
                              else "ok",
            }},
            upsert=True,
        )
    except Exception:
        logger.exception("[llm-budget] persistence failed (non-blocking)")


async def get_llm_budget_estimate() -> Dict[str, Any]:
    """Return a JSON-serializable budget snapshot for `/admin/llm-budget`.

    Reads first from MongoDB (`platform_health.llm_budget`), falls back to the
    in-memory snapshot, falls back to "unknown" if no error has been captured
    yet (i.e. budget is still healthy, never raised an exception).
    """
    snapshot: Dict[str, Any] = {
        "used_usd": None,
        "max_usd": None,
        "pct": None,
        "captured_at": None,
        "alert_level": "unknown",
        "days_remaining_in_month": None,
    }
    # Days remaining in the current month
    now = datetime.now(timezone.utc)
    if now.month == 12:
        next_month = now.replace(year=now.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        next_month = now.replace(month=now.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0)
    snapshot["days_remaining_in_month"] = max(0, (next_month - now).days)

    try:
        from deps import db
        doc = await db.platform_health.find_one({"key": "llm_budget"}, {"_id": 0})
        if doc and doc.get("max_usd"):
            snapshot.update({
                "used_usd":     doc.get("used_usd"),
                "max_usd":      doc.get("max_usd"),
                "pct":          doc.get("pct"),
                "captured_at":  doc.get("captured_at"),
                "alert_level":  doc.get("alert_level") or "unknown",
            })
            return snapshot
    except Exception:
        pass

    # Fallback : in-memory snapshot (server lifetime only)
    if _LAST_BUDGET_SNAPSHOT.get("max_usd"):
        used = _LAST_BUDGET_SNAPSHOT["used_usd"]
        cap = _LAST_BUDGET_SNAPSHOT["max_usd"]
        snapshot.update({
            "used_usd":   used,
            "max_usd":    cap,
            "pct":        round((used / cap) * 100, 2) if cap and cap > 0 else None,
            "captured_at": _LAST_BUDGET_SNAPSHOT.get("captured_at"),
            "alert_level": "critical" if cap and used / cap >= 0.95
                          else "warning" if cap and used / cap >= 0.80
                          else "ok",
        })
    return snapshot
