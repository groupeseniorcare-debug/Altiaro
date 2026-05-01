"""
Per-launch LLM cost tracker — Phase 4 (instrumentation real cost).

Objectif : capturer dans `launch_jobs.cost_summary` le coût réel approximé
de chaque launch, ventilé par catégorie (brand, content, images, translate)
+ snapshot du compteur global Emergent (avant/après) pour avoir aussi la
valeur de référence facturée côté serveur.

Comme `emergentintegrations.llm.chat.LlmChat` n'expose pas le `response_cost`
de litellm, on estime via tokens approximés (~4 caractères / token) et le
prix unitaire Anthropic + un coût fixe par image Nano Banana.

Un `CostTracker` est associé à un `job_id`. Chaque appel `safe_claude_*` ou
`safe_nano_banana*` qui sait à quel job il appartient s'enregistre via
`record_text(...)` ou `record_image(...)`. À la fin du run, on persiste.

⚠️ Estimation, pas mesure exacte. Les chiffres réels facturés par Emergent
(côté proxy LiteLLM serveur) restent la source de vérité ; on en propose
un snapshot delta via `platform_health.llm_budget` quand disponible.
"""
from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Dict, Optional

logger = logging.getLogger("altiaro.cost_tracker")

# ─── Pricing (USD) — Anthropic public list 2026-04 ─────────────────────── #
# Source : https://www.anthropic.com/pricing#anthropic-api
# Conversion EUR ≈ USD * 0.92 (approx, simplifié)
USD_TO_EUR = 0.92

# Per 1M tokens
ANTHROPIC_PRICE_USD = {
    # Sonnet 4.5
    "claude-sonnet-4-5-20250929":   {"input": 3.00, "output": 15.00},
    # Haiku 4.5
    "claude-haiku-4-5-20251001":    {"input": 1.00, "output": 5.00},
    # Fallbacks raisonnables (modèles plus anciens, mêmes ordres)
    "default_premium":              {"input": 3.00, "output": 15.00},
    "default_standard":             {"input": 1.00, "output": 5.00},
}

# Nano Banana (gemini-2.5-flash-image) image gen — facturé par Emergent
# environ $0.04 / image générée (estimation publique).
NANO_BANANA_PRICE_PER_IMAGE_USD = 0.04


def _estimate_tokens(text: str) -> int:
    """Approximation grossière : ~4 caractères = 1 token (Anthropic GPT-style)."""
    if not text:
        return 0
    return max(1, len(text) // 4)


def _claude_cost_usd(model: str, input_chars: int, output_chars: int) -> float:
    in_tok = _estimate_tokens("x" * input_chars)
    out_tok = _estimate_tokens("x" * output_chars)
    px = ANTHROPIC_PRICE_USD.get(model)
    if not px:
        # Fallback — devine d'après le nom
        px = ANTHROPIC_PRICE_USD["default_premium"] if "sonnet" in (model or "") else ANTHROPIC_PRICE_USD["default_standard"]
    return (in_tok * px["input"] + out_tok * px["output"]) / 1_000_000.0


# ─── Per-job tracker ──────────────────────────────────────────────────── #


@dataclass
class JobCostSummary:
    job_id: str
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    # Compteurs d'appels
    claude_calls: int = 0
    image_calls: int = 0
    # Tokens cumulés (approx)
    claude_in_tokens: int = 0
    claude_out_tokens: int = 0
    # Coûts estimés ventilés (USD)
    cost_brand_usd: float = 0.0
    cost_content_usd: float = 0.0
    cost_images_usd: float = 0.0
    cost_translate_usd: float = 0.0
    cost_other_usd: float = 0.0
    # Snapshot Emergent serveur (avant / après) — facultatif
    emergent_used_usd_before: Optional[float] = None
    emergent_used_usd_after: Optional[float] = None

    @property
    def total_usd(self) -> float:
        return round(
            self.cost_brand_usd
            + self.cost_content_usd
            + self.cost_images_usd
            + self.cost_translate_usd
            + self.cost_other_usd,
            6,
        )

    @property
    def total_eur(self) -> float:
        return round(self.total_usd * USD_TO_EUR, 4)

    def emergent_delta_usd(self) -> Optional[float]:
        if self.emergent_used_usd_before is None or self.emergent_used_usd_after is None:
            return None
        return round(self.emergent_used_usd_after - self.emergent_used_usd_before, 4)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["total_usd"] = self.total_usd
        d["total_eur"] = round(self.total_usd * USD_TO_EUR, 4)
        d["cost_brand_eur"] = round(self.cost_brand_usd * USD_TO_EUR, 4)
        d["cost_content_eur"] = round(self.cost_content_usd * USD_TO_EUR, 4)
        d["cost_images_eur"] = round(self.cost_images_usd * USD_TO_EUR, 4)
        d["cost_translate_eur"] = round(self.cost_translate_usd * USD_TO_EUR, 4)
        d["cost_other_eur"] = round(self.cost_other_usd * USD_TO_EUR, 4)
        d["emergent_delta_usd"] = self.emergent_delta_usd()
        d["closed_at"] = datetime.now(timezone.utc).isoformat()
        return d


# Registre global thread-safe
_TRACKERS: Dict[str, JobCostSummary] = {}
_LOCK = threading.RLock()


def start_job(job_id: str) -> JobCostSummary:
    """Initialise (idempotent) un tracker pour un job."""
    with _LOCK:
        t = _TRACKERS.get(job_id)
        if not t:
            t = JobCostSummary(job_id=job_id)
            _TRACKERS[job_id] = t
        return t


def get_job(job_id: Optional[str]) -> Optional[JobCostSummary]:
    if not job_id:
        return None
    with _LOCK:
        return _TRACKERS.get(job_id)


def end_job(job_id: str) -> Optional[JobCostSummary]:
    """Pop le tracker (à appeler quand le job est terminé et persisté)."""
    with _LOCK:
        return _TRACKERS.pop(job_id, None)


# ─── Helpers d'enregistrement ────────────────────────────────────────── #


def record_text(
    job_id: Optional[str],
    *,
    model: str,
    input_text: str,
    output_text: str,
    bucket: str = "other",
) -> None:
    """Enregistre un appel Claude texte. `bucket` ∈ {brand, content, translate, other}."""
    if not job_id:
        return
    t = start_job(job_id)
    in_chars = len(input_text or "")
    out_chars = len(output_text or "")
    cost = _claude_cost_usd(model, in_chars, out_chars)
    in_tok = _estimate_tokens(input_text)
    out_tok = _estimate_tokens(output_text)
    with _LOCK:
        t.claude_calls += 1
        t.claude_in_tokens += in_tok
        t.claude_out_tokens += out_tok
        bk = f"cost_{bucket}_usd"
        if hasattr(t, bk):
            setattr(t, bk, getattr(t, bk) + cost)
        else:
            t.cost_other_usd += cost


def record_image(
    job_id: Optional[str],
    *,
    bucket: str = "images",
    n: int = 1,
    unit_price_usd: float = NANO_BANANA_PRICE_PER_IMAGE_USD,
) -> None:
    """Enregistre N images Nano Banana générées."""
    if not job_id:
        return
    t = start_job(job_id)
    cost = unit_price_usd * max(1, int(n))
    with _LOCK:
        t.image_calls += int(n)
        bk = f"cost_{bucket}_usd"
        if hasattr(t, bk):
            setattr(t, bk, getattr(t, bk) + cost)
        else:
            t.cost_images_usd += cost


def attach_emergent_before(job_id: str, used_usd: Optional[float]) -> None:
    if not job_id or used_usd is None:
        return
    t = start_job(job_id)
    with _LOCK:
        if t.emergent_used_usd_before is None:
            t.emergent_used_usd_before = float(used_usd)


def attach_emergent_after(job_id: str, used_usd: Optional[float]) -> None:
    if not job_id or used_usd is None:
        return
    t = start_job(job_id)
    with _LOCK:
        t.emergent_used_usd_after = float(used_usd)


# ─── Context-var pour propager le job_id sans plomberie partout ──────── #
# Beaucoup d'appels LLM (safe_claude_text, safe_nano_banana) sont déjà
# disséminés ; pour ne pas devoir faire passer `job_id` dans tous les
# constructeurs, on utilise un contextvars.ContextVar qui suit la coroutine
# courante (`_run_launch`). Si la valeur est non-None, on enregistre
# automatiquement dans le tracker.
import contextvars

_current_job_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "altiaro_current_launch_job_id", default=None
)
_current_bucket: contextvars.ContextVar[str] = contextvars.ContextVar(
    "altiaro_current_cost_bucket", default="other"
)


def get_current_job_id() -> Optional[str]:
    return _current_job_id.get()


def get_current_bucket() -> str:
    return _current_bucket.get()


class job_context:
    """Context manager pour scoper un job_id à un bloc async."""
    def __init__(self, job_id: Optional[str]):
        self.job_id = job_id
        self._token = None

    def __enter__(self):
        self._token = _current_job_id.set(self.job_id)
        return self

    def __exit__(self, *exc):
        if self._token is not None:
            _current_job_id.reset(self._token)


class bucket_context:
    """Context manager pour scoper un bucket de coût."""
    def __init__(self, bucket: str):
        self.bucket = bucket
        self._token = None

    def __enter__(self):
        self._token = _current_bucket.set(self.bucket)
        return self

    def __exit__(self, *exc):
        if self._token is not None:
            _current_bucket.reset(self._token)
