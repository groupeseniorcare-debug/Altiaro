"""
Dépendances partagées : DB, auth helpers, utils.
Importé par tous les routeurs FastAPI de /app/backend/routes/.
"""

import os
import logging
import bcrypt
import jwt
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional
from bson import ObjectId

from fastapi import HTTPException, Depends, Request, Response
from motor.motor_asyncio import AsyncIOMotorClient

ROOT_DIR = Path(__file__).parent

logger = logging.getLogger("conceptfactory")

# Config
MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]
JWT_SECRET = os.environ["JWT_SECRET"]
JWT_ALGORITHM = "HS256"
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@conceptfactory.fr")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "Factory2026!")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")
EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")

UPLOAD_DIR = ROOT_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]


# ------------------------------------------------------------------ #
# Password + JWT helpers
# ------------------------------------------------------------------ #
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(user_id: str, email: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=60 * 8),
        "type": "access",
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(days=7),
        "type": "refresh",
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def set_auth_cookies(response: Response, access: str, refresh: str):
    response.set_cookie("access_token", access, httponly=True, secure=True, samesite="none", max_age=28800, path="/")
    response.set_cookie("refresh_token", refresh, httponly=True, secure=True, samesite="none", max_age=604800, path="/")


def clear_auth_cookies(response: Response):
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")


def serialize_user(doc: dict) -> dict:
    return {
        "id": str(doc["_id"]),
        "email": doc["email"],
        "name": doc.get("name", ""),
        "role": doc.get("role", "operator"),
        "created_at": doc.get("created_at"),
    }


async def get_current_user(request: Request) -> dict:
    token = request.cookies.get("access_token")
    if not token:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user = await db.users.find_one({"_id": ObjectId(payload["sub"])})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return serialize_user(user)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def require_admin(user: dict = Depends(get_current_user)) -> dict:
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


# ------------------------------------------------------------------ #
# Site helpers
# ------------------------------------------------------------------ #
async def _site_with_progress(site: dict) -> dict:
    total = await db.steps.count_documents({"site_id": site["id"]})
    validated = await db.steps.count_documents({"site_id": site["id"], "status": "validated"})
    pending = await db.steps.count_documents({"site_id": site["id"], "status": "awaiting_validation"})
    current = await db.steps.find_one({"site_id": site["id"], "status": "in_progress"})
    site["progress_total"] = total
    site["progress_validated"] = validated
    site["progress_pending"] = pending
    site["progress_pct"] = round((validated / total) * 100) if total else 0
    site["current_step_number"] = current["number"] if current else None
    site["current_step_title"] = current["title"] if current else None
    return site


async def _check_site_access(site_id: str, user: dict):
    site = await db.sites.find_one({"id": site_id}, {"_id": 0})
    if not site:
        raise HTTPException(status_code=404, detail="Site introuvable")
    if user["role"] != "admin" and site.get("operator_id") != user["id"]:
        raise HTTPException(status_code=403, detail="Accès refusé")
    return site
