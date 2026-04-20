"""Generic uploads (images pour produits, logos, etc.)"""
import uuid
from pathlib import Path
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File

from deps import UPLOAD_DIR, get_current_user

router = APIRouter(prefix="/uploads")

ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif"}
MAX_SIZE = 8 * 1024 * 1024  # 8 Mo par image


@router.post("/image")
async def upload_image(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(status_code=400, detail=f"Extension non supportée. Utilisez : {', '.join(sorted(ALLOWED_EXT))}")
    content = await file.read()
    if len(content) > MAX_SIZE:
        raise HTTPException(status_code=413, detail="Image trop volumineuse (max 8 Mo)")
    safe_name = f"img_{uuid.uuid4().hex}{ext}"
    (UPLOAD_DIR / safe_name).write_bytes(content)
    return {
        "url": f"/api/uploads/{safe_name}",
        "size": len(content),
        "original_name": file.filename,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
    }
