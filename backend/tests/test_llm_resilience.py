"""Tests Phase 0 — LLM Resilience layer.

Validates :
- AC #1 : safe_llm_call retries 502 errors and eventually succeeds within max_attempts
- AC #2 : circuit breaker OPENs after 5 consecutive failures and short-circuits
- AC #3 : LLMUnavailableError carries provider/attempts/last_error metadata
- AC #5 : get_llm_health() shape

Run with :
    cd /app/backend && pytest tests/test_llm_resilience.py -v
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

# Path injection so tests run from /app/backend
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.llm_resilience import (  # noqa: E402
    CIRCUIT_FAILURE_THRESHOLD,
    LLMUnavailableError,
    get_llm_health,
    reset_breakers_for_tests,
    safe_llm_call,
)


@pytest.fixture(autouse=True)
def _reset_breakers():
    reset_breakers_for_tests()
    yield
    reset_breakers_for_tests()


def _make_flaky(fail_n_times: int, error_class=Exception, error_msg="Error code: 502 Bad Gateway"):
    """Returns a 0-arg coroutine factory that fails N times then succeeds."""
    counter = {"n": 0}

    async def _fn():
        if counter["n"] < fail_n_times:
            counter["n"] += 1
            raise error_class(error_msg)
        return "OK"

    return _fn, counter


@pytest.mark.asyncio
async def test_ac1_retries_then_succeeds_on_502():
    """AC#1 : 3× erreur 502 → succès au 4ème (limite max_attempts=4)."""
    fn, counter = _make_flaky(fail_n_times=3, error_msg="BadGatewayError: Error code: 502")
    # Speed up by mocking sleeps to ~0
    import services.llm_resilience as mod
    orig_delays = mod.RETRY_DELAYS_S
    mod.RETRY_DELAYS_S = (0.01, 0.02, 0.04)
    try:
        result = await safe_llm_call(fn, provider="claude")
        assert result == "OK"
        assert counter["n"] == 3, f"Expected 3 retries before success, got {counter['n']}"
        h = get_llm_health()
        assert h["breakers"]["claude"]["state"] == "CLOSED"
    finally:
        mod.RETRY_DELAYS_S = orig_delays


@pytest.mark.asyncio
async def test_ac1_max_attempts_exhausted_raises_llm_unavailable():
    """AC#1 : 4× erreur 502 (1 initial + 3 retries) → LLMUnavailableError."""
    fn, counter = _make_flaky(fail_n_times=99, error_msg="Error code: 502")
    import services.llm_resilience as mod
    mod.RETRY_DELAYS_S = (0.01, 0.02, 0.04)
    with pytest.raises(LLMUnavailableError) as exc:
        await safe_llm_call(fn, provider="claude", max_attempts=4)
    assert exc.value.provider == "claude"
    assert exc.value.attempts == 4
    assert "502" in (exc.value.last_error or "")
    assert counter["n"] == 4


@pytest.mark.asyncio
async def test_ac2_circuit_breaker_opens_after_5_failures():
    """AC#2 : 5 échecs consécutifs → state=OPEN, le 6e appel court-circuite
    sans toucher au réseau."""
    import services.llm_resilience as mod
    mod.RETRY_DELAYS_S = (0.001, 0.001, 0.001)
    fn_always_fail, _ = _make_flaky(fail_n_times=99, error_msg="Error code: 502")

    # Each safe_llm_call exhausts retries and bumps consecutive_failures by 1
    # (record_failure called once per safe_llm_call when retries exhaust).
    for i in range(CIRCUIT_FAILURE_THRESHOLD):
        with pytest.raises(LLMUnavailableError):
            await safe_llm_call(fn_always_fail, provider="claude", max_attempts=2)

    h = get_llm_health()
    assert h["breakers"]["claude"]["state"] == "OPEN", f"Expected OPEN after {CIRCUIT_FAILURE_THRESHOLD} fails, got {h['breakers']['claude']['state']}"

    # Le call suivant doit court-circuiter : LLMUnavailableError SANS toucher fn
    counter_after = {"n": 0}

    async def _fn_should_not_be_called():
        counter_after["n"] += 1
        return "should-not-reach"

    with pytest.raises(LLMUnavailableError) as exc:
        await safe_llm_call(_fn_should_not_be_called, provider="claude", max_attempts=4)
    assert "Circuit breaker OPEN" in str(exc.value)
    assert counter_after["n"] == 0, "Network was hit despite breaker OPEN"


@pytest.mark.asyncio
async def test_ac1_no_retry_on_4xx_application_error():
    """AC#1 bis : 401/422/etc. ne déclenchent PAS de retry (bug applicatif)."""
    import services.llm_resilience as mod
    mod.RETRY_DELAYS_S = (0.001, 0.001, 0.001)
    fn, counter = _make_flaky(fail_n_times=99, error_msg="Error code: 401 Unauthorized")
    with pytest.raises(Exception) as exc:
        await safe_llm_call(fn, provider="claude")
    # Should NOT be wrapped in LLMUnavailableError, and counter should be 1
    assert not isinstance(exc.value, LLMUnavailableError)
    assert counter["n"] == 1, f"Expected NO retry on 4xx, got {counter['n']} attempts"


@pytest.mark.asyncio
async def test_ac5_health_endpoint_shape():
    """AC#5 : get_llm_health() retourne bien la structure attendue."""
    h = get_llm_health()
    assert "overall" in h
    assert h["overall"] in ("healthy", "degraded", "down")
    assert "breakers" in h
    for name in ("claude", "nano_banana"):
        assert name in h["breakers"]
        b = h["breakers"][name]
        assert "state" in b
        assert b["state"] in ("CLOSED", "OPEN", "HALF_OPEN")
        assert "consecutive_failures" in b
        assert "recent_failures_60s" in b
        assert "last_error" in b
    assert "config" in h
    assert h["config"]["max_attempts"] == 4
    assert h["config"]["circuit_threshold"] == 5
    assert "ts" in h


@pytest.mark.asyncio
async def test_breakers_independent_claude_vs_nano_banana():
    """Bonus : si Claude tombe, Nano Banana n'est pas affecté (et vice-versa)."""
    import services.llm_resilience as mod
    mod.RETRY_DELAYS_S = (0.001, 0.001, 0.001)
    fn_fail, _ = _make_flaky(fail_n_times=99, error_msg="Error code: 502")

    for _ in range(CIRCUIT_FAILURE_THRESHOLD):
        with pytest.raises(LLMUnavailableError):
            await safe_llm_call(fn_fail, provider="claude", max_attempts=2)

    h = get_llm_health()
    assert h["breakers"]["claude"]["state"] == "OPEN"
    assert h["breakers"]["nano_banana"]["state"] == "CLOSED"


if __name__ == "__main__":
    # Allow running standalone : python tests/test_llm_resilience.py
    asyncio.run(test_ac1_retries_then_succeeds_on_502())
    asyncio.run(test_ac1_max_attempts_exhausted_raises_llm_unavailable())
    asyncio.run(test_ac2_circuit_breaker_opens_after_5_failures())
    asyncio.run(test_ac1_no_retry_on_4xx_application_error())
    asyncio.run(test_ac5_health_endpoint_shape())
    print("\n✅ All Phase 0 resilience tests passed (manual run).")
