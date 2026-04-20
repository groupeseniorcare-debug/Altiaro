"""Meta endpoints : phases catalog, blocks catalog, health."""
from fastapi import APIRouter, Depends

from deps import get_current_user
from seed_prompts import PHASES, BLOCKS, PHASE_TO_BLOCK

router = APIRouter()


@router.get("/meta/phases")
async def meta_phases(user: dict = Depends(get_current_user)):
    return [
        {
            "code": k,
            "name": v,
            "block": PHASE_TO_BLOCK.get(k),
        }
        for k, v in PHASES.items()
    ]


@router.get("/meta/blocks")
async def meta_blocks(user: dict = Depends(get_current_user)):
    """Expose the 4 high-level blocks (Template / Products / SEO / Marketing)."""
    return [
        {"id": bid, **meta, "phases": [p for p, b in PHASE_TO_BLOCK.items() if b == bid]}
        for bid, meta in sorted(BLOCKS.items(), key=lambda x: x[1]["order"])
    ]


@router.get("/health")
async def health():
    return {"status": "ok", "service": "conceptfactory"}
