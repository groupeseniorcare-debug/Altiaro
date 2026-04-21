"""Customer accounts on the storefront (register, login, /me, /orders).

Storefront customers are distinct from platform users (admin/operator).
They live in collection `customers`, scoped by site_id.
Auth = JWT in Authorization header (not cookies) — one account per (site_id, email).
"""
import os
import uuid
import hashlib
import bcrypt
import jwt
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field

from deps import db

router = APIRouter()

JWT_SECRET = os.environ.get("JWT_SECRET", "change-me")
JWT_ALGO = "HS256"
JWT_TTL_DAYS = 30


def _hash_pwd(p: str) -> str:
    return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()


def _check_pwd(p: str, h: str) -> bool:
    try:
        return bcrypt.checkpw(p.encode(), h.encode())
    except Exception:
        return False


def _token(customer_id: str, site_id: str) -> str:
    payload = {
        "cid": customer_id,
        "sid": site_id,
        "exp": datetime.now(timezone.utc) + timedelta(days=JWT_TTL_DAYS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)


async def _auth_customer(request: Request, site_id: str) -> dict:
    """Extract customer from Authorization: Bearer <token>."""
    header = request.headers.get("authorization", "")
    if not header.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Authentification requise")
    token = header.split(" ", 1)[1].strip()
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Session expirée")
    if payload.get("sid") != site_id:
        raise HTTPException(status_code=403, detail="Token invalide pour ce site")
    customer = await db.customers.find_one({"id": payload["cid"]}, {"_id": 0, "password_hash": 0})
    if not customer:
        raise HTTPException(status_code=401, detail="Compte introuvable")
    return customer


# ------------------- Schemas ------------------- #
class RegisterInput(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=200)
    first_name: str = Field(min_length=1, max_length=80)
    last_name: str = Field(min_length=1, max_length=80)
    phone: Optional[str] = ""


class LoginInput(BaseModel):
    email: EmailStr
    password: str


class ProfileUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    postal_code: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None


# ------------------- Endpoints ------------------- #
@router.post("/public/sites/{site_id}/customers/register")
async def register(site_id: str, data: RegisterInput):
    if not await db.sites.find_one({"id": site_id}, {"_id": 0, "id": 1}):
        raise HTTPException(status_code=404, detail="Site introuvable")
    email_lower = data.email.lower().strip()
    existing = await db.customers.find_one({"site_id": site_id, "email": email_lower}, {"_id": 0, "id": 1})
    if existing:
        raise HTTPException(status_code=409, detail="Un compte existe déjà avec cet email")
    cid = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    await db.customers.insert_one({
        "id": cid,
        "site_id": site_id,
        "email": email_lower,
        "password_hash": _hash_pwd(data.password),
        "first_name": data.first_name.strip(),
        "last_name": data.last_name.strip(),
        "phone": (data.phone or "").strip(),
        "created_at": now,
    })
    return {"token": _token(cid, site_id), "customer": {
        "id": cid, "email": email_lower, "first_name": data.first_name, "last_name": data.last_name,
    }}


@router.post("/public/sites/{site_id}/customers/login")
async def login(site_id: str, data: LoginInput):
    email_lower = data.email.lower().strip()
    customer = await db.customers.find_one({"site_id": site_id, "email": email_lower})
    if not customer or not _check_pwd(data.password, customer["password_hash"]):
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect")
    return {"token": _token(customer["id"], site_id), "customer": {
        "id": customer["id"],
        "email": customer["email"],
        "first_name": customer["first_name"],
        "last_name": customer["last_name"],
    }}


@router.get("/public/sites/{site_id}/customers/me")
async def me(site_id: str, request: Request):
    customer = await _auth_customer(request, site_id)
    return customer


@router.patch("/public/sites/{site_id}/customers/me")
async def update_me(site_id: str, data: ProfileUpdate, request: Request):
    customer = await _auth_customer(request, site_id)
    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    if updates:
        updates["updated_at"] = datetime.now(timezone.utc).isoformat()
        await db.customers.update_one({"id": customer["id"]}, {"$set": updates})
    return await db.customers.find_one({"id": customer["id"]}, {"_id": 0, "password_hash": 0})


@router.get("/public/sites/{site_id}/customers/orders")
async def my_orders(site_id: str, request: Request):
    customer = await _auth_customer(request, site_id)
    # Match by email (customer email in the order document)
    orders = await db.orders.find(
        {"site_id": site_id, "customer.email": customer["email"]},
        {"_id": 0, "_meta_ip": 0}
    ).sort("created_at", -1).to_list(100)
    return orders


@router.get("/public/sites/{site_id}/orders/{order_number}")
async def public_order_detail(site_id: str, order_number: str, email: str = ""):
    """Public order tracking : requires email for non-authenticated lookup."""
    order = await db.orders.find_one(
        {"site_id": site_id, "order_number": order_number},
        {"_id": 0, "_meta_ip": 0}
    )
    if not order:
        raise HTTPException(status_code=404, detail="Commande introuvable")
    # Simple ownership check : email must match
    if email and order.get("customer", {}).get("email", "").lower() != email.lower().strip():
        raise HTTPException(status_code=403, detail="Email ne correspond pas à cette commande")
    if not email:
        raise HTTPException(status_code=400, detail="Email requis pour consulter une commande")
    return order
