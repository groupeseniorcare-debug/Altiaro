"""Users CRUD (admin only)."""
from datetime import datetime, timezone
from typing import Optional
from bson import ObjectId

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr

from deps import db, require_admin, hash_password, serialize_user

router = APIRouter(prefix="/users")


class UserCreateInput(BaseModel):
    email: EmailStr
    password: str
    name: str
    role: str = "operator"


@router.get("")
async def list_users(admin: dict = Depends(require_admin)):
    users = await db.users.find({}).sort("created_at", -1).to_list(1000)
    return [serialize_user(u) for u in users]


@router.post("")
async def create_user(data: UserCreateInput, admin: dict = Depends(require_admin)):
    email = data.email.lower().strip()
    existing = await db.users.find_one({"email": email})
    if existing:
        raise HTTPException(status_code=400, detail="Un utilisateur avec cet email existe déjà")
    if data.role not in ("admin", "operator"):
        raise HTTPException(status_code=400, detail="Rôle invalide")
    doc = {
        "email": email,
        "password_hash": hash_password(data.password),
        "name": data.name,
        "role": data.role,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    result = await db.users.insert_one(doc)
    doc["_id"] = result.inserted_id
    return serialize_user(doc)


@router.delete("/{user_id}")
async def delete_user(user_id: str, admin: dict = Depends(require_admin)):
    if user_id == admin["id"]:
        raise HTTPException(status_code=400, detail="Vous ne pouvez pas supprimer votre propre compte")
    try:
        result = await db.users.delete_one({"_id": ObjectId(user_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="ID invalide")
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    return {"ok": True}
