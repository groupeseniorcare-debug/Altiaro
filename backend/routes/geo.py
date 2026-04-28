"""Phase D' — Détection géo (langue + devise)."""
from __future__ import annotations
from fastapi import APIRouter, Request
from geo_mapping import detect

router = APIRouter(tags=["geo"])


@router.get("/geo/detect")
async def geo_detect(request: Request):
    cf = request.headers.get("CF-IPCountry")
    if cf and cf != "XX":
        return detect(cf)
    fwd = request.headers.get("X-Geo-Country")
    if fwd:
        return detect(fwd)
    return detect(None)
