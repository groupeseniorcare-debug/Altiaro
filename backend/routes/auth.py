"""Auth routes : login, logout, me, refresh."""
from datetime import datetime, timezone, timedelta
from bson import ObjectId

import jwt
from fastapi import APIRouter, HTTPException, Depends, Request, Response
from pydantic import BaseModel, EmailStr

from deps import (
    db, JWT_SECRET, JWT_ALGORITHM,
    verify_password, create_access_token, create_refresh_token,
    set_auth_cookies, clear_auth_cookies, serialize_user, get_current_user,
)

router = APIRouter(prefix="/auth")


class LoginInput(BaseModel):
    email: EmailStr
    password: str


@router.post("/login")
async def login(data: LoginInput, response: Response, request: Request):
    email = data.email.lower().strip()
    ip = request.client.host if request.client else "unknown"
    identifier = f"{ip}:{email}"

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

    if user.get("status") == "pending_email_verification":
        raise HTTPException(
            status_code=403,
            detail={
                "code": "pending_email_verification",
                "message": "Votre compte attend la vérification par email.",
                "email": email,
            },
        )

    await db.login_attempts.delete_one({"identifier": identifier})
    access = create_access_token(str(user["_id"]), user["email"])
    refresh = create_refresh_token(str(user["_id"]))
    set_auth_cookies(response, access, refresh)
    return serialize_user(user)


@router.post("/logout")
async def logout(response: Response, user: dict = Depends(get_current_user)):
    clear_auth_cookies(response)
    return {"ok": True}


@router.get("/me")
async def me(user: dict = Depends(get_current_user)):
    return user


@router.get("/session")
async def session(request: Request):
    """Silent probe — returns {user: null} instead of 401 when not logged in.
    Used by the SPA to avoid noisy console errors on initial load."""
    try:
        user = await get_current_user(request)
        return {"user": user}
    except HTTPException:
        return {"user": None}


@router.post("/refresh")
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
