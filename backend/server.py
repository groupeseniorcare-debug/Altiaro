"""
Launch OS — E-commerce brand factory back-office.
FastAPI backend: auth (JWT httpOnly cookies), sites, 50-step workflow,
validation gating, LLM integration (Emergent), financials, dashboard.
"""

from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

import os
import logging
import uuid
import secrets
import bcrypt
import jwt
from datetime import datetime, timezone, timedelta
from typing import Optional, List
from bson import ObjectId

from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request, Response, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, EmailStr, Field

from seed_prompts import get_seed_steps_for_site, PROMPTS, PHASES
from seed_niches import seed_niches, COUNTRIES
from models_shop import (
    ProductCreateInput, ProductUpdateInput, OrderCreateInput,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("launchos")

# ------------------------------------------------------------------ #
# Config & DB
# ------------------------------------------------------------------ #
MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]
JWT_SECRET = os.environ["JWT_SECRET"]
JWT_ALGORITHM = "HS256"
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@conceptfactory.fr")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "Factory2026!")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")
EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

UPLOAD_DIR = ROOT_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

app = FastAPI(title="Concept Factory API")
api = APIRouter(prefix="/api")


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
        "exp": datetime.now(timezone.utc) + timedelta(minutes=60 * 8),  # 8h for ops UX
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
# Pydantic models
# ------------------------------------------------------------------ #
class LoginInput(BaseModel):
    email: EmailStr
    password: str


class UserCreateInput(BaseModel):
    email: EmailStr
    password: str
    name: str
    role: str = "operator"  # operator | admin


class SiteCreateInput(BaseModel):
    name: str
    niche: str
    niche_slug: Optional[str] = None
    domain: Optional[str] = ""
    shopify_url: Optional[str] = ""
    operator_id: Optional[str] = None
    notes: Optional[str] = ""


class SiteUpdateInput(BaseModel):
    name: Optional[str] = None
    niche: Optional[str] = None
    domain: Optional[str] = None
    shopify_url: Optional[str] = None
    operator_id: Optional[str] = None
    status: Optional[str] = None  # active | paused | archived | live
    notes: Optional[str] = None


class StepUpdateInput(BaseModel):
    deliverable_url: Optional[str] = None
    deliverable_notes: Optional[str] = None
    ai_response: Optional[str] = None


class StepValidateInput(BaseModel):
    comment: Optional[str] = ""


class StepRejectInput(BaseModel):
    reason: str


class StepExecuteInput(BaseModel):
    model_provider: str = "anthropic"  # anthropic | openai | gemini
    model_name: str = "claude-sonnet-4-5-20250929"
    user_variables: Optional[dict] = None  # e.g., { "NICHE": "seniors", "NOM_MARQUE": "Luméa" }


class FinancialInput(BaseModel):
    month: str  # "YYYY-MM"
    revenue: float = 0
    ad_spend: float = 0
    cogs: float = 0
    other_costs: float = 0
    orders_count: int = 0
    notes: Optional[str] = ""


# ------------------------------------------------------------------ #
# Startup
# ------------------------------------------------------------------ #
@app.on_event("startup")
async def startup():
    # indexes
    await db.users.create_index("email", unique=True)
    await db.sites.create_index("created_at")
    await db.steps.create_index([("site_id", 1), ("number", 1)])
    await db.financials.create_index([("site_id", 1), ("month", 1)], unique=True)
    await db.login_attempts.create_index("identifier")
    await db.niches.create_index("slug", unique=True)
    await db.niches.create_index("rank")
    await db.countries.create_index("code", unique=True)
    await db.products.create_index([("site_id", 1), ("status", 1)])
    await db.products.create_index("created_at")
    await db.orders.create_index([("site_id", 1), ("created_at", -1)])
    await db.orders.create_index("order_number", unique=True)

    # seed niche engine catalog (idempotent)
    try:
        seeded = await seed_niches(db)
        logger.info(f"Seeded {seeded} niches in catalog")
    except Exception:
        logger.exception("Failed to seed niches catalog")

    # seed admin
    existing = await db.users.find_one({"email": ADMIN_EMAIL})
    if existing is None:
        await db.users.insert_one({
            "email": ADMIN_EMAIL,
            "password_hash": hash_password(ADMIN_PASSWORD),
            "name": "Admin",
            "role": "admin",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        logger.info(f"Seeded admin user {ADMIN_EMAIL}")
    elif not verify_password(ADMIN_PASSWORD, existing["password_hash"]):
        await db.users.update_one(
            {"email": ADMIN_EMAIL},
            {"$set": {"password_hash": hash_password(ADMIN_PASSWORD)}},
        )
        logger.info(f"Updated admin password for {ADMIN_EMAIL}")


@app.on_event("shutdown")
async def shutdown():
    client.close()


# ------------------------------------------------------------------ #
# AUTH ROUTES
# ------------------------------------------------------------------ #
@api.post("/auth/login")
async def login(data: LoginInput, response: Response, request: Request):
    email = data.email.lower().strip()
    ip = request.client.host if request.client else "unknown"
    identifier = f"{ip}:{email}"

    # brute force check
    attempt = await db.login_attempts.find_one({"identifier": identifier})
    if attempt and attempt.get("count", 0) >= 5:
        last = datetime.fromisoformat(attempt["last"])
        if datetime.now(timezone.utc) - last < timedelta(minutes=15):
            raise HTTPException(status_code=429, detail="Trop de tentatives. Réessayez dans 15 minutes.")

    user = await db.users.find_one({"email": email})
    if not user or not verify_password(data.password, user["password_hash"]):
        await db.login_attempts.update_one(
            {"identifier": identifier},
            {"$inc": {"count": 1}, "$set": {"last": datetime.now(timezone.utc).isoformat()}},
            upsert=True,
        )
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect")

    await db.login_attempts.delete_one({"identifier": identifier})
    access = create_access_token(str(user["_id"]), user["email"])
    refresh = create_refresh_token(str(user["_id"]))
    set_auth_cookies(response, access, refresh)
    return serialize_user(user)


@api.post("/auth/logout")
async def logout(response: Response, user: dict = Depends(get_current_user)):
    clear_auth_cookies(response)
    return {"ok": True}


@api.get("/auth/me")
async def me(user: dict = Depends(get_current_user)):
    return user


@api.post("/auth/refresh")
async def refresh(request: Request, response: Response):
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=401, detail="No refresh token")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid refresh type")
        user = await db.users.find_one({"_id": ObjectId(payload["sub"])})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        new_access = create_access_token(str(user["_id"]), user["email"])
        response.set_cookie("access_token", new_access, httponly=True, secure=True, samesite="none", max_age=28800, path="/")
        return {"ok": True}
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")


# ------------------------------------------------------------------ #
# USERS (admin)
# ------------------------------------------------------------------ #
@api.get("/users")
async def list_users(admin: dict = Depends(require_admin)):
    users = await db.users.find({}).sort("created_at", -1).to_list(1000)
    return [serialize_user(u) for u in users]


@api.post("/users")
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


@api.delete("/users/{user_id}")
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


# ------------------------------------------------------------------ #
# SITES
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


@api.get("/sites")
async def list_sites(user: dict = Depends(get_current_user)):
    query = {} if user["role"] == "admin" else {"operator_id": user["id"]}
    sites = await db.sites.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
    for s in sites:
        await _site_with_progress(s)
    return sites


@api.post("/sites")
async def create_site(data: SiteCreateInput, admin: dict = Depends(require_admin)):
    site_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "id": site_id,
        "name": data.name,
        "niche": data.niche,
        "niche_slug": data.niche_slug or None,
        "domain": data.domain or "",
        "shopify_url": data.shopify_url or "",
        "operator_id": data.operator_id,
        "notes": data.notes or "",
        "status": "active",
        "created_at": now,
        "created_by": admin["id"],
    }
    await db.sites.insert_one(doc)
    # seed 50 steps
    steps = get_seed_steps_for_site(site_id)
    await db.steps.insert_many(steps)
    doc.pop("_id", None)
    return await _site_with_progress(doc)


@api.get("/sites/{site_id}")
async def get_site(site_id: str, user: dict = Depends(get_current_user)):
    site = await db.sites.find_one({"id": site_id}, {"_id": 0})
    if not site:
        raise HTTPException(status_code=404, detail="Site introuvable")
    if user["role"] != "admin" and site.get("operator_id") != user["id"]:
        raise HTTPException(status_code=403, detail="Accès refusé")
    return await _site_with_progress(site)


@api.patch("/sites/{site_id}")
async def update_site(site_id: str, data: SiteUpdateInput, admin: dict = Depends(require_admin)):
    update = {k: v for k, v in data.model_dump().items() if v is not None}
    if not update:
        raise HTTPException(status_code=400, detail="Aucun champ à mettre à jour")
    result = await db.sites.update_one({"id": site_id}, {"$set": update})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Site introuvable")
    site = await db.sites.find_one({"id": site_id}, {"_id": 0})
    return await _site_with_progress(site)


@api.delete("/sites/{site_id}")
async def delete_site(site_id: str, admin: dict = Depends(require_admin)):
    await db.sites.delete_one({"id": site_id})
    await db.steps.delete_many({"site_id": site_id})
    await db.financials.delete_many({"site_id": site_id})
    await db.products.delete_many({"site_id": site_id})
    await db.orders.delete_many({"site_id": site_id})
    return {"ok": True}


# ------------------------------------------------------------------ #
# STEPS
# ------------------------------------------------------------------ #
async def _check_site_access(site_id: str, user: dict):
    site = await db.sites.find_one({"id": site_id}, {"_id": 0})
    if not site:
        raise HTTPException(status_code=404, detail="Site introuvable")
    if user["role"] != "admin" and site.get("operator_id") != user["id"]:
        raise HTTPException(status_code=403, detail="Accès refusé")
    return site


@api.get("/sites/{site_id}/steps")
async def list_steps(site_id: str, user: dict = Depends(get_current_user)):
    await _check_site_access(site_id, user)
    steps = await db.steps.find({"site_id": site_id}, {"_id": 0}).sort("number", 1).to_list(200)
    return steps


@api.get("/steps/{step_id}")
async def get_step(step_id: str, user: dict = Depends(get_current_user)):
    step = await db.steps.find_one({"id": step_id}, {"_id": 0})
    if not step:
        raise HTTPException(status_code=404, detail="Étape introuvable")
    await _check_site_access(step["site_id"], user)
    return step


@api.patch("/steps/{step_id}")
async def update_step(step_id: str, data: StepUpdateInput, user: dict = Depends(get_current_user)):
    step = await db.steps.find_one({"id": step_id}, {"_id": 0})
    if not step:
        raise HTTPException(status_code=404, detail="Étape introuvable")
    await _check_site_access(step["site_id"], user)
    if step["status"] == "locked":
        raise HTTPException(status_code=400, detail="Cette étape est verrouillée")
    if step["status"] == "validated":
        raise HTTPException(status_code=400, detail="Cette étape est déjà validée")

    update = {k: v for k, v in data.model_dump().items() if v is not None}
    update["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.steps.update_one({"id": step_id}, {"$set": update})
    return await db.steps.find_one({"id": step_id}, {"_id": 0})


@api.post("/steps/{step_id}/submit")
async def submit_step(step_id: str, user: dict = Depends(get_current_user)):
    """Le concepteur marque une étape comme terminée — auto-validation + unlock next.
    Plus de gating admin sauf pour l'étape finale 'Notifier lancement Ads prêt'."""
    step = await db.steps.find_one({"id": step_id}, {"_id": 0})
    if not step:
        raise HTTPException(status_code=404, detail="Étape introuvable")
    await _check_site_access(step["site_id"], user)
    if step["status"] == "locked":
        raise HTTPException(status_code=400, detail="Étape verrouillée")
    if step["status"] == "validated":
        raise HTTPException(status_code=400, detail="Étape déjà validée")
    if not (step.get("deliverable_url") or step.get("deliverable_notes") or step.get("deliverable_files") or step.get("ai_response")):
        raise HTTPException(status_code=400, detail="Ajoutez au moins un livrable (URL, notes, fichier ou réponse IA) avant de valider")

    now = datetime.now(timezone.utc).isoformat()
    await db.steps.update_one(
        {"id": step_id},
        {"$set": {
            "status": "validated",
            "submitted_at": now,
            "validated_at": now,
            "validated_by": user["id"],
            "updated_at": now,
        }},
    )
    # unlock next step automatically
    next_step = await db.steps.find_one({"site_id": step["site_id"], "number": step["number"] + 1})
    if next_step and next_step["status"] == "locked":
        await db.steps.update_one(
            {"id": next_step["id"]},
            {"$set": {"status": "in_progress", "updated_at": now}},
        )
    return await db.steps.find_one({"id": step_id}, {"_id": 0})


@api.post("/steps/{step_id}/validate")
async def validate_step(step_id: str, data: StepValidateInput, admin: dict = Depends(require_admin)):
    step = await db.steps.find_one({"id": step_id}, {"_id": 0})
    if not step:
        raise HTTPException(status_code=404, detail="Étape introuvable")
    now = datetime.now(timezone.utc).isoformat()
    await db.steps.update_one(
        {"id": step_id},
        {"$set": {
            "status": "validated",
            "validated_at": now,
            "validated_by": admin["id"],
            "validation_comment": data.comment or "",
            "updated_at": now,
        }},
    )
    # unlock next step
    next_step = await db.steps.find_one({"site_id": step["site_id"], "number": step["number"] + 1})
    if next_step and next_step["status"] == "locked":
        await db.steps.update_one(
            {"id": next_step["id"]},
            {"$set": {"status": "in_progress", "updated_at": now}},
        )
    return await db.steps.find_one({"id": step_id}, {"_id": 0})


@api.post("/steps/{step_id}/reject")
async def reject_step(step_id: str, data: StepRejectInput, admin: dict = Depends(require_admin)):
    step = await db.steps.find_one({"id": step_id}, {"_id": 0})
    if not step:
        raise HTTPException(status_code=404, detail="Étape introuvable")
    now = datetime.now(timezone.utc).isoformat()
    await db.steps.update_one(
        {"id": step_id},
        {"$set": {
            "status": "rejected",
            "rejection_reason": data.reason,
            "validated_by": admin["id"],
            "updated_at": now,
        }},
    )
    return await db.steps.find_one({"id": step_id}, {"_id": 0})


@api.post("/steps/{step_id}/execute")
async def execute_step_with_ai(step_id: str, data: StepExecuteInput, user: dict = Depends(get_current_user)):
    step = await db.steps.find_one({"id": step_id}, {"_id": 0})
    if not step:
        raise HTTPException(status_code=404, detail="Étape introuvable")
    site = await _check_site_access(step["site_id"], user)
    if step["status"] == "locked":
        raise HTTPException(status_code=400, detail="Étape verrouillée")

    # Build substitution context
    variables = data.user_variables or {}
    prompt_text = step["prompt"]
    # Auto-substitute common placeholders from site info
    defaults = {
        "[NICHE]": site.get("niche", ""),
        "[NOM_MARQUE]": site.get("name", ""),
        "[NOM]": site.get("name", ""),
        "[NOM_CHOISI]": site.get("name", ""),
        "[DOMAINE]": site.get("domain", ""),
        "[URL_ADMIN]": site.get("shopify_url", ""),
        "[MON_SHOPIFY]": site.get("shopify_url", ""),
    }
    for k, v in defaults.items():
        if v:
            prompt_text = prompt_text.replace(k, str(v))
    for k, v in variables.items():
        prompt_text = prompt_text.replace(f"[{k}]", str(v)).replace(f"{{{k}}}", str(v))

    # Call LLM
    try:
        import asyncio as _asyncio
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        system_msg = (
            "Tu es un expert e-commerce, SEO, copywriting et ops. Tu réponds en français. "
            "Tu fournis des livrables concrets, structurés, prêts à l'emploi. "
            "Tu utilises des tableaux markdown, des listes, et des exemples chiffrés quand pertinent."
        )
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"step-{step_id}",
            system_message=system_msg,
        ).with_model(data.model_provider, data.model_name)
        message = UserMessage(text=prompt_text)
        response = await _asyncio.wait_for(chat.send_message(message), timeout=50)
        ai_text = response if isinstance(response, str) else str(response)
    except _asyncio.TimeoutError:
        raise HTTPException(
            status_code=504,
            detail="Le modèle met trop de temps à répondre (>50s). Réessayez ou changez de modèle."
        )
    except Exception as e:
        logger.exception("LLM execution failed")
        err_str = str(e)
        if "Budget has been exceeded" in err_str or "budget" in err_str.lower():
            raise HTTPException(
                status_code=402,
                detail="Budget Emergent LLM Key épuisé. Allez dans Profile → Universal Key → Add Balance pour recharger, puis réessayez."
            )
        if "invalid_api_key" in err_str.lower() or "unauthorized" in err_str.lower():
            raise HTTPException(
                status_code=401,
                detail="Clé LLM invalide ou expirée. Contactez l'administrateur."
            )
        raise HTTPException(status_code=500, detail=f"Erreur LLM : {err_str[:300]}")

    now = datetime.now(timezone.utc).isoformat()
    await db.steps.update_one(
        {"id": step_id},
        {"$set": {
            "ai_response": ai_text,
            "ai_model_used": f"{data.model_provider}/{data.model_name}",
            "ai_executed_at": now,
            "updated_at": now,
        }},
    )
    return {"ai_response": ai_text, "model": f"{data.model_provider}/{data.model_name}"}


@api.post("/steps/{step_id}/upload")
async def upload_step_file(step_id: str, file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    step = await db.steps.find_one({"id": step_id}, {"_id": 0})
    if not step:
        raise HTTPException(status_code=404, detail="Étape introuvable")
    await _check_site_access(step["site_id"], user)

    ext = Path(file.filename).suffix
    safe_name = f"{uuid.uuid4().hex}{ext}"
    target = UPLOAD_DIR / safe_name
    content = await file.read()
    if len(content) > 15 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Fichier trop volumineux (max 15 Mo)")
    target.write_bytes(content)

    file_record = {
        "original_name": file.filename,
        "stored_name": safe_name,
        "url": f"/api/uploads/{safe_name}",
        "size": len(content),
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
        "uploaded_by": user["id"],
    }
    await db.steps.update_one(
        {"id": step_id},
        {"$push": {"deliverable_files": file_record},
         "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}},
    )
    return file_record


# ------------------------------------------------------------------ #
# VALIDATIONS (admin queue)
# ------------------------------------------------------------------ #
@api.get("/validations")
async def validation_queue(admin: dict = Depends(require_admin)):
    """Monitoring admin des étapes complétées récemment (lecture seule, pas de gating).
    Utile pour auditer la qualité du travail des concepteurs."""
    steps = await db.steps.find({"status": "validated"}, {"_id": 0}).sort("validated_at", -1).limit(100).to_list(100)
    site_ids = list({s["site_id"] for s in steps})
    sites = await db.sites.find({"id": {"$in": site_ids}}, {"_id": 0, "id": 1, "name": 1, "niche": 1}).to_list(200)
    sites_by_id = {s["id"]: s for s in sites}
    for s in steps:
        s["site"] = sites_by_id.get(s["site_id"])
    return steps


# ------------------------------------------------------------------ #
# FINANCIALS
# ------------------------------------------------------------------ #
@api.get("/sites/{site_id}/financials")
async def list_financials(site_id: str, user: dict = Depends(get_current_user)):
    await _check_site_access(site_id, user)
    items = await db.financials.find({"site_id": site_id}, {"_id": 0}).sort("month", -1).to_list(60)
    return items


@api.post("/sites/{site_id}/financials")
async def upsert_financial(site_id: str, data: FinancialInput, user: dict = Depends(get_current_user)):
    await _check_site_access(site_id, user)
    margin = data.revenue - data.cogs - data.other_costs - data.ad_spend
    roas = round(data.revenue / data.ad_spend, 2) if data.ad_spend > 0 else 0
    doc = {
        "site_id": site_id,
        "month": data.month,
        "revenue": data.revenue,
        "ad_spend": data.ad_spend,
        "cogs": data.cogs,
        "other_costs": data.other_costs,
        "orders_count": data.orders_count,
        "margin": margin,
        "roas": roas,
        "notes": data.notes or "",
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "updated_by": user["id"],
    }
    await db.financials.update_one(
        {"site_id": site_id, "month": data.month},
        {"$set": doc, "$setOnInsert": {"created_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True,
    )
    result = await db.financials.find_one({"site_id": site_id, "month": data.month}, {"_id": 0})
    return result


# ------------------------------------------------------------------ #
# DASHBOARD
# ------------------------------------------------------------------ #
@api.get("/dashboard/kpis")
async def dashboard_kpis(user: dict = Depends(get_current_user)):
    site_query = {} if user["role"] == "admin" else {"operator_id": user["id"]}
    sites = await db.sites.find(site_query, {"_id": 0}).to_list(1000)
    site_ids = [s["id"] for s in sites]

    # Aggregate financials across all accessible sites
    pipeline = [
        {"$match": {"site_id": {"$in": site_ids}}},
        {"$group": {
            "_id": None,
            "total_revenue": {"$sum": "$revenue"},
            "total_ad_spend": {"$sum": "$ad_spend"},
            "total_cogs": {"$sum": "$cogs"},
            "total_other_costs": {"$sum": "$other_costs"},
            "total_orders": {"$sum": "$orders_count"},
            "total_margin": {"$sum": "$margin"},
        }}
    ]
    agg = await db.financials.aggregate(pipeline).to_list(1)
    totals = agg[0] if agg else {
        "total_revenue": 0, "total_ad_spend": 0, "total_cogs": 0,
        "total_other_costs": 0, "total_orders": 0, "total_margin": 0,
    }
    totals.pop("_id", None)

    # Per-site summary
    per_site = []
    for s in sites:
        fin = await db.financials.aggregate([
            {"$match": {"site_id": s["id"]}},
            {"$group": {
                "_id": None,
                "revenue": {"$sum": "$revenue"},
                "ad_spend": {"$sum": "$ad_spend"},
                "margin": {"$sum": "$margin"},
                "orders": {"$sum": "$orders_count"},
            }}
        ]).to_list(1)
        f = fin[0] if fin else {"revenue": 0, "ad_spend": 0, "margin": 0, "orders": 0}
        f.pop("_id", None)
        await _site_with_progress(s)
        per_site.append({**s, **f})

    # Monthly trend (last 12 months aggregate across all sites)
    trend = await db.financials.aggregate([
        {"$match": {"site_id": {"$in": site_ids}}},
        {"$group": {
            "_id": "$month",
            "revenue": {"$sum": "$revenue"},
            "ad_spend": {"$sum": "$ad_spend"},
            "margin": {"$sum": "$margin"},
        }},
        {"$sort": {"_id": 1}},
        {"$project": {"_id": 0, "month": "$_id", "revenue": 1, "ad_spend": 1, "margin": 1}},
    ]).to_list(24)

    # Step progress aggregate
    total_steps = await db.steps.count_documents({"site_id": {"$in": site_ids}})
    validated_steps = await db.steps.count_documents({"site_id": {"$in": site_ids}, "status": "validated"})
    pending_steps = await db.steps.count_documents({"site_id": {"$in": site_ids}, "status": "awaiting_validation"})

    # ROAS global
    roas_global = round(totals["total_revenue"] / totals["total_ad_spend"], 2) if totals["total_ad_spend"] > 0 else 0

    return {
        "totals": {
            **totals,
            "sites_count": len(sites),
            "active_sites": sum(1 for s in sites if s.get("status") == "active"),
            "roas_global": roas_global,
            "total_steps": total_steps,
            "validated_steps": validated_steps,
            "pending_validations": pending_steps,
            "global_progress_pct": round((validated_steps / total_steps) * 100) if total_steps else 0,
        },
        "per_site": per_site,
        "monthly_trend": trend,
    }


# ------------------------------------------------------------------ #
# PRODUCTS (admin/operator — catalogue d'un site)
# ------------------------------------------------------------------ #
def _serialize_product(doc: dict) -> dict:
    doc.pop("_id", None)
    return doc


@api.get("/sites/{site_id}/products")
async def list_products(site_id: str, user: dict = Depends(get_current_user)):
    await _check_site_access(site_id, user)
    items = await db.products.find({"site_id": site_id}, {"_id": 0}).sort("created_at", -1).to_list(500)
    return items


@api.post("/sites/{site_id}/products")
async def create_product(site_id: str, data: ProductCreateInput, user: dict = Depends(get_current_user)):
    await _check_site_access(site_id, user)
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "id": str(uuid.uuid4()),
        "site_id": site_id,
        **data.model_dump(),
        "created_at": now,
        "updated_at": now,
        "created_by": user["id"],
    }
    await db.products.insert_one(dict(doc))
    return _serialize_product(doc)


@api.get("/sites/{site_id}/products/{product_id}")
async def get_product(site_id: str, product_id: str, user: dict = Depends(get_current_user)):
    await _check_site_access(site_id, user)
    p = await db.products.find_one({"id": product_id, "site_id": site_id}, {"_id": 0})
    if not p:
        raise HTTPException(status_code=404, detail="Produit introuvable")
    return p


@api.patch("/sites/{site_id}/products/{product_id}")
async def update_product(site_id: str, product_id: str, data: ProductUpdateInput, user: dict = Depends(get_current_user)):
    await _check_site_access(site_id, user)
    update = {k: v for k, v in data.model_dump().items() if v is not None}
    if not update:
        raise HTTPException(status_code=400, detail="Aucun champ à mettre à jour")
    update["updated_at"] = datetime.now(timezone.utc).isoformat()
    result = await db.products.update_one({"id": product_id, "site_id": site_id}, {"$set": update})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Produit introuvable")
    p = await db.products.find_one({"id": product_id, "site_id": site_id}, {"_id": 0})
    return p


@api.delete("/sites/{site_id}/products/{product_id}")
async def delete_product(site_id: str, product_id: str, user: dict = Depends(get_current_user)):
    await _check_site_access(site_id, user)
    await db.products.delete_one({"id": product_id, "site_id": site_id})
    return {"ok": True}


# ------------------------------------------------------------------ #
# ORDERS (admin/operator)
# ------------------------------------------------------------------ #
@api.get("/sites/{site_id}/orders")
async def list_orders(site_id: str, user: dict = Depends(get_current_user)):
    await _check_site_access(site_id, user)
    items = await db.orders.find({"site_id": site_id}, {"_id": 0}).sort("created_at", -1).to_list(500)
    return items


# ------------------------------------------------------------------ #
# PUBLIC STOREFRONT (no auth) — /api/public/*
# ------------------------------------------------------------------ #
@api.get("/public/sites/{site_id}")
async def public_site(site_id: str):
    """Infos publiques d'un site (pour rendre la storefront sans auth)."""
    site = await db.sites.find_one({"id": site_id}, {"_id": 0})
    if not site:
        raise HTTPException(status_code=404, detail="Site introuvable")
    # Retourner uniquement champs publics
    niche = None
    if site.get("niche_slug"):
        niche = await db.niches.find_one(
            {"slug": site["niche_slug"]},
            {"_id": 0, "name": 1, "emoji": 1, "tagline": 1, "category": 1}
        )
    return {
        "id": site["id"],
        "name": site["name"],
        "niche": site.get("niche", ""),
        "domain": site.get("domain", ""),
        "niche_data": niche,
    }


@api.get("/public/sites/{site_id}/products")
async def public_products(site_id: str):
    """Liste publique des produits actifs d'un site (storefront)."""
    site = await db.sites.find_one({"id": site_id}, {"_id": 0, "id": 1})
    if not site:
        raise HTTPException(status_code=404, detail="Site introuvable")
    items = await db.products.find(
        {"site_id": site_id, "status": "active"},
        {"_id": 0}
    ).sort([("featured", -1), ("created_at", -1)]).to_list(500)
    return items


@api.get("/public/sites/{site_id}/products/{product_id}")
async def public_product_detail(site_id: str, product_id: str):
    p = await db.products.find_one(
        {"id": product_id, "site_id": site_id, "status": "active"},
        {"_id": 0}
    )
    if not p:
        raise HTTPException(status_code=404, detail="Produit introuvable")
    return p


@api.post("/public/sites/{site_id}/orders")
async def public_create_order(site_id: str, data: OrderCreateInput):
    """Endpoint public checkout — crée une commande en statut pending_payment.
    Mollie sera branché en Phase 5.
    SÉCURITÉ: on ignore les prix envoyés par le client et on utilise ceux en base."""
    site = await db.sites.find_one({"id": site_id}, {"_id": 0, "id": 1, "name": 1})
    if not site:
        raise HTTPException(status_code=404, detail="Site introuvable")
    if not data.items:
        raise HTTPException(status_code=400, detail="Panier vide")

    # Validate each item against DB and use canonical server-side price
    canonical_items = []
    for item in data.items:
        prod = await db.products.find_one(
            {"id": item.product_id, "site_id": site_id, "status": "active"},
            {"_id": 0, "price": 1, "currency": 1, "name": 1, "images": 1}
        )
        if not prod:
            raise HTTPException(
                status_code=400,
                detail=f"Produit {item.product_id} introuvable ou inactif"
            )
        canonical_items.append({
            "product_id": item.product_id,
            "name": item.name,
            "price": prod["price"],  # ⚠ server-side canonical price
            "quantity": item.quantity,
            "currency": prod.get("currency", "EUR"),
            "image": (prod.get("images") or [None])[0],
        })

    subtotal = sum(it["price"] * it["quantity"] for it in canonical_items)
    shipping_fee = 0 if subtotal >= 50 else 4.90
    tax = 0  # TVA en Phase 5 par pays
    total = round(subtotal + shipping_fee + tax, 2)

    now = datetime.now(timezone.utc)
    order_number = f"CF-{int(now.timestamp())}-{secrets.token_hex(2).upper()}"

    doc = {
        "id": str(uuid.uuid4()),
        "site_id": site_id,
        "site_name": site["name"],
        "order_number": order_number,
        "items": canonical_items,
        "customer": data.customer.model_dump(),
        "shipping_address": data.shipping_address.model_dump(),
        "language": data.language,
        "notes": data.notes or "",
        "subtotal": round(subtotal, 2),
        "shipping_fee": shipping_fee,
        "tax": tax,
        "total": total,
        "currency": canonical_items[0]["currency"] if canonical_items else "EUR",
        "status": "pending_payment",
        "payment_method": None,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }
    await db.orders.insert_one(dict(doc))
    doc.pop("_id", None)
    return doc


@api.get("/public/sites/{site_id}/orders/{order_number}")
async def public_order_lookup(site_id: str, order_number: str):
    """Permet au client de consulter le détail de sa commande après checkout."""
    o = await db.orders.find_one(
        {"site_id": site_id, "order_number": order_number},
        {"_id": 0}
    )
    if not o:
        raise HTTPException(status_code=404, detail="Commande introuvable")
    return o


# ------------------------------------------------------------------ #
# NICHE ENGINE (catalogue 20 niches × 6 pays)
# ------------------------------------------------------------------ #
@api.get("/niches")
async def list_niches(user: dict = Depends(get_current_user)):
    """Liste complète du catalogue de niches (triée par rank croissant)."""
    niches = await db.niches.find({}, {"_id": 0}).sort("rank", 1).to_list(200)
    return niches


@api.get("/niches/{slug}")
async def get_niche(slug: str, user: dict = Depends(get_current_user)):
    niche = await db.niches.find_one({"slug": slug}, {"_id": 0})
    if not niche:
        raise HTTPException(status_code=404, detail="Niche introuvable")
    return niche


@api.get("/countries")
async def list_countries(user: dict = Depends(get_current_user)):
    """Liste des 6 pays supportés (référentiel)."""
    countries = await db.countries.find({}, {"_id": 0}).sort("code", 1).to_list(20)
    if not countries:
        # Fallback si jamais la collection est vide
        return COUNTRIES
    return countries


# ------------------------------------------------------------------ #
# META (phases & prompts catalog read-only)
# ------------------------------------------------------------------ #
@api.get("/meta/phases")
async def meta_phases(user: dict = Depends(get_current_user)):
    return [{"code": k, "name": v} for k, v in PHASES.items()]


@api.get("/health")
async def health():
    return {"status": "ok", "service": "launchos"}


# ------------------------------------------------------------------ #
# Mount router & static
# ------------------------------------------------------------------ #
app.include_router(api)
app.mount("/api/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

# CORS — explicit origins (credentials requires non-wildcard)
cors_origins_env = os.environ.get("CORS_ORIGINS", "")
cors_origins = [o.strip() for o in cors_origins_env.split(",") if o.strip()]
if not cors_origins:
    cors_origins = [FRONTEND_URL]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
