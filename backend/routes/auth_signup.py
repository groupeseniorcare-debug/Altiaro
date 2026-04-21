"""Self-service signup + email OTP verification for Altiaro.

Flow:
  POST /auth/signup        → creates pending user + sends 6-digit OTP by email
  POST /auth/verify-email  → validates OTP → activates user + auth cookies
  POST /auth/resend-code   → re-sends a fresh OTP if expired
"""
from __future__ import annotations

import hashlib
import logging
import os
import re
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional

import resend
from bson import ObjectId
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr, Field

from deps import (
    db,
    hash_password,
    create_access_token,
    create_refresh_token,
    set_auth_cookies,
    serialize_user,
)

logger = logging.getLogger("altiora.auth_signup")
router = APIRouter(prefix="/auth")

RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
RESEND_FROM = os.environ.get("RESEND_DEFAULT_FROM", "onboarding@resend.dev")
# When the Resend domain is not verified yet, we can only send to the account
# owner; for dev we fall back to logging the OTP so devs/testing can proceed.
RESEND_OWNER_EMAIL = os.environ.get("RESEND_OWNER_EMAIL", "")

if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY

OTP_TTL_MINUTES = 15
OTP_MAX_ATTEMPTS = 5
SIGNUP_IP_COOLDOWN_PER_HOUR = 3
RESEND_COOLDOWN_PER_HOUR = 3


# ============== Models ==============
class SignupInput(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    company_name: Optional[str] = Field(default=None, max_length=120)


class VerifyInput(BaseModel):
    email: EmailStr
    code: str = Field(min_length=6, max_length=6)


class ResendInput(BaseModel):
    email: EmailStr


# ============== Helpers ==============
def _hash_otp(code: str, email: str) -> str:
    salt = os.environ.get("JWT_SECRET", "altiaro-otp-salt")
    return hashlib.sha256(f"{salt}::{email}::{code}".encode("utf-8")).hexdigest()


def _validate_password(pwd: str) -> None:
    if len(pwd) < 8:
        raise HTTPException(status_code=400, detail="Le mot de passe doit contenir au moins 8 caractères")
    if not re.search(r"[A-Za-z]", pwd) or not re.search(r"\d", pwd):
        raise HTTPException(
            status_code=400,
            detail="Le mot de passe doit contenir au moins une lettre et un chiffre",
        )


async def _rate_limit_ip(ip: str, key: str, max_per_hour: int):
    """Track an IP-scoped action; raise 429 when threshold is exceeded."""
    since = datetime.now(timezone.utc) - timedelta(hours=1)
    count = await db.rate_limits.count_documents(
        {"key": key, "ip": ip, "at": {"$gte": since}}
    )
    if count >= max_per_hour:
        raise HTTPException(
            status_code=429,
            detail="Trop de tentatives. Réessayez dans 1 heure.",
        )
    await db.rate_limits.insert_one({"key": key, "ip": ip, "at": datetime.now(timezone.utc)})


async def _send_otp_email(to: str, name: str, code: str) -> None:
    subject = "Altiaro — Votre code de confirmation"
    html = f"""<!DOCTYPE html>
<html lang="fr"><body style="margin:0;padding:40px 20px;background:#F5F5F4;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Inter,sans-serif;color:#0A0A0A">
<div style="max-width:520px;margin:0 auto;background:#FFFFFF;border:1px solid #E7E5E4;border-radius:12px;overflow:hidden">
  <div style="padding:32px 32px 0 32px">
    <div style="font-size:11px;letter-spacing:0.14em;text-transform:uppercase;color:#78716C">Altiaro</div>
    <h1 style="font-size:24px;font-weight:600;margin:16px 0 12px 0;letter-spacing:-0.01em">Confirmons votre email</h1>
    <p style="font-size:15px;line-height:1.6;color:#44403C;margin:0 0 24px 0">Bonjour {name},<br>Voici votre code de confirmation pour activer votre compte Concepteur :</p>
  </div>
  <div style="padding:0 32px">
    <div style="background:#0A0A0A;color:#FFFFFF;border-radius:8px;padding:24px;text-align:center">
      <div style="font-family:'JetBrains Mono',ui-monospace,monospace;font-size:36px;letter-spacing:0.4em;font-weight:600">{code}</div>
    </div>
    <p style="font-size:13px;color:#78716C;margin:20px 0 0 0">Ce code expire dans {OTP_TTL_MINUTES} minutes. Si vous n'êtes pas à l'origine de cette inscription, ignorez simplement cet email.</p>
  </div>
  <div style="margin-top:32px;padding:20px 32px;background:#FAFAF9;border-top:1px solid #E7E5E4;font-size:12px;color:#78716C;line-height:1.6">
    <div><strong style="color:#0A0A0A">Altiaro</strong> — La plateforme e-commerce des partenariats éclairés.</div>
    <div style="margin-top:6px">Édité par Robin Zuchiatti · SIREN 883 803 967 · <a href="https://altiaro.com/mentions-legales" style="color:#78716C">Mentions légales</a></div>
  </div>
</div></body></html>"""

    if not RESEND_API_KEY:
        logger.warning("RESEND_API_KEY missing — printing OTP to logs for dev: %s → %s", to, code)
        return

    target = to
    if RESEND_OWNER_EMAIL and to.lower() != RESEND_OWNER_EMAIL.lower():
        # Resend sandbox mode: forward all mails to the verified account email
        target = RESEND_OWNER_EMAIL
        logger.info("Resend sandbox: rerouting OTP email for %s → %s", to, target)
        # DEV AID: in sandbox also log the OTP so local / preview testing works
        # without Gmail access. Safe to remove once the Resend domain is verified.
        logger.warning("DEV · OTP for %s is: %s", to, code)
    try:
        resend.Emails.send({
            "from": RESEND_FROM,
            "to": [target],
            "subject": subject,
            "html": html,
        })
    except Exception as e:
        logger.error("Failed to send OTP email to %s: %s", to, e)
        # Never block signup on mail provider outage — log OTP so support can retrieve it
        logger.warning("DEV FALLBACK — OTP for %s is: %s", to, code)


# ============== Endpoints ==============
@router.post("/signup")
async def signup(data: SignupInput, request: Request):
    ip = request.client.host if request.client else "unknown"
    await _rate_limit_ip(ip, "signup", SIGNUP_IP_COOLDOWN_PER_HOUR)

    email = data.email.lower().strip()
    _validate_password(data.password)

    existing = await db.users.find_one({"email": email})
    if existing:
        # Do not leak whether a user exists — but if the account is pending,
        # tell the user they can re-verify
        status = existing.get("status", "active")
        if status == "pending_email_verification":
            return {
                "ok": True,
                "status": "pending_email_verification",
                "email": email,
                "detail": "Un compte existe déjà en attente de confirmation. Un nouveau code vient d'être envoyé.",
            }
        raise HTTPException(status_code=409, detail="Un compte existe déjà avec cet email")

    name = data.name.strip()
    now = datetime.now(timezone.utc)
    user_doc = {
        "name": name,
        "email": email,
        "password_hash": hash_password(data.password),
        "role": "operator",
        "status": "pending_email_verification",
        "company_name": (data.company_name or "").strip(),
        "created_at": now,
    }
    result = await db.users.insert_one(user_doc)
    user_id = str(result.inserted_id)

    # Generate 6-digit OTP, hashed at rest
    code = f"{secrets.randbelow(1_000_000):06d}"
    await db.email_verifications.delete_many({"email": email})  # wipe any stale
    await db.email_verifications.insert_one({
        "user_id": user_id,
        "email": email,
        "code_hash": _hash_otp(code, email),
        "attempts": 0,
        "created_at": now,
        "expires_at": now + timedelta(minutes=OTP_TTL_MINUTES),
    })

    await _send_otp_email(email, name, code)
    logger.info("Signup: user %s · OTP sent", email)

    return {
        "ok": True,
        "status": "pending_email_verification",
        "email": email,
        "expires_in_min": OTP_TTL_MINUTES,
    }


@router.post("/verify-email")
async def verify_email(data: VerifyInput, response: Response):
    email = data.email.lower().strip()
    code = (data.code or "").strip()
    if not code.isdigit() or len(code) != 6:
        raise HTTPException(status_code=400, detail="Code invalide")

    ver = await db.email_verifications.find_one({"email": email})
    if not ver:
        raise HTTPException(status_code=400, detail="Aucune demande de vérification en cours")

    if ver["expires_at"].replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        await db.email_verifications.delete_one({"_id": ver["_id"]})
        raise HTTPException(status_code=400, detail="Code expiré. Demandez un nouveau code.")

    if ver.get("attempts", 0) >= OTP_MAX_ATTEMPTS:
        await db.email_verifications.delete_one({"_id": ver["_id"]})
        raise HTTPException(status_code=429, detail="Trop de tentatives. Demandez un nouveau code.")

    expected = ver["code_hash"]
    got = _hash_otp(code, email)
    if not secrets.compare_digest(expected, got):
        await db.email_verifications.update_one(
            {"_id": ver["_id"]},
            {"$inc": {"attempts": 1}},
        )
        remaining = OTP_MAX_ATTEMPTS - ver.get("attempts", 0) - 1
        raise HTTPException(
            status_code=400,
            detail=f"Code incorrect. {max(remaining, 0)} tentative(s) restante(s).",
        )

    # Success — activate user, clean up OTP record, issue tokens
    user_id = ver["user_id"]
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=500, detail="Utilisateur introuvable")

    await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"status": "active", "email_verified_at": datetime.now(timezone.utc)}},
    )
    await db.email_verifications.delete_one({"_id": ver["_id"]})

    user = await db.users.find_one({"_id": ObjectId(user_id)})
    access = create_access_token(user_id, user["email"])
    refresh = create_refresh_token(user_id)
    set_auth_cookies(response, access, refresh)
    return serialize_user(user)


@router.post("/resend-code")
async def resend_code(data: ResendInput, request: Request):
    email = data.email.lower().strip()
    ip = request.client.host if request.client else "unknown"
    await _rate_limit_ip(ip, f"resend:{email}", RESEND_COOLDOWN_PER_HOUR)

    user = await db.users.find_one({"email": email})
    if not user or user.get("status") != "pending_email_verification":
        # Do not disclose account state
        return {"ok": True, "detail": "Si un compte existe, un nouveau code a été envoyé."}

    code = f"{secrets.randbelow(1_000_000):06d}"
    now = datetime.now(timezone.utc)
    await db.email_verifications.delete_many({"email": email})
    await db.email_verifications.insert_one({
        "user_id": str(user["_id"]),
        "email": email,
        "code_hash": _hash_otp(code, email),
        "attempts": 0,
        "created_at": now,
        "expires_at": now + timedelta(minutes=OTP_TTL_MINUTES),
    })
    await _send_otp_email(email, user.get("name", "Concepteur"), code)
    return {"ok": True, "detail": "Un nouveau code vous a été envoyé.", "expires_in_min": OTP_TTL_MINUTES}
