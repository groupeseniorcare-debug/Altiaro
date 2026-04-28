"""Phase D' — Détection géo (langue + devise) avec fallback ip-api.com."""
from __future__ import annotations
import asyncio
import logging
from fastapi import APIRouter, Request
from geo_mapping import detect

router = APIRouter(tags=["geo"])
logger = logging.getLogger("altiaro.geo")

_CACHE: dict = {}  # ip → (country, expires_at_ts)
_CACHE_TTL = 24 * 3600


async def _resolve_country_from_ip(ip: str) -> str | None:
    """Best-effort : resolve country from IP via free ip-api.com (rate-limited
    to ~45 req/min unauth — fine for our scale). Returns ISO-2 country or None.
    """
    if not ip or ip.startswith(("127.", "10.", "192.168.", "172.")):
        return None
    import time
    cached = _CACHE.get(ip)
    if cached and cached[1] > time.time():
        return cached[0]
    try:
        import httpx
        async with httpx.AsyncClient(timeout=1.5) as cli:
            r = await cli.get(f"http://ip-api.com/json/{ip}?fields=status,countryCode")
            j = r.json()
            if j.get("status") == "success":
                cc = j.get("countryCode")
                _CACHE[ip] = (cc, time.time() + _CACHE_TTL)
                return cc
    except Exception:
        return None
    return None


@router.get("/geo/detect")
async def geo_detect(request: Request):
    """Detects user country/language/currency.

    Lookup priority :
    1. `CF-IPCountry` header (Cloudflare reverse-proxy)
    2. `X-Geo-Country` header (custom override / proxy)
    3. `X-Forwarded-For` → ip-api.com (rate-limited fallback)
    4. Default → FR / EUR
    """
    cf = request.headers.get("CF-IPCountry")
    if cf and cf != "XX":
        return detect(cf)
    fwd = request.headers.get("X-Geo-Country")
    if fwd:
        return detect(fwd)
    # Fallback : real client IP from X-Forwarded-For
    xff = (request.headers.get("X-Forwarded-For") or "").split(",")[0].strip()
    real_ip = xff or (request.client.host if request.client else "")
    cc = await _resolve_country_from_ip(real_ip)
    return detect(cc)
