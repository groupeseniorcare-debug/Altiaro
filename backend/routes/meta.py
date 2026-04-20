"""Meta endpoints : phases catalog, health."""
from fastapi import APIRouter, Depends

from deps import get_current_user
from seed_prompts import PHASES

router = APIRouter()


@router.get("/meta/phases")
async def meta_phases(user: dict = Depends(get_current_user)):
    return [{"code": k, "name": v} for k, v in PHASES.items()]


@router.get("/health")
async def health():
    return {"status": "ok", "service": "conceptfactory"}
