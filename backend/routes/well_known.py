"""Routes "well-known" / verification publiques.

Endpoints publics utilisés par Google (Search Console, Site Verification API)
pour vérifier la propriété du domaine `altiaro.com`. Idempotent, ne nécessite
aucune authentification.
"""
from __future__ import annotations
import os
from fastapi import APIRouter
from fastapi.responses import HTMLResponse, PlainTextResponse

router = APIRouter(tags=["well-known"])


def _altiaro_token() -> str:
    return os.environ.get("GOOGLE_SITE_VERIFICATION_ALTIARO") or ""


@router.get("/public/google-site-verification.html", include_in_schema=False)
async def google_site_verification_html():
    """Backup de vérification : page minimale qui contient le meta tag.

    Google permet plusieurs méthodes de verification (DNS TXT, meta, fichier).
    Si le concepteur a un blocage DNS / cache CDN, cette URL servie par notre
    backend offre une alternative immédiate.

    Le concepteur peut soit :
    - Pointer Google vers `https://altiaro.com/google-site-verification.html`
    - Ou copier ce fichier à la racine de son hébergeur
    """
    token = _altiaro_token()
    html = (
        "<!doctype html>\n<html lang=\"fr\"><head>\n"
        f"<meta name=\"google-site-verification\" content=\"{token}\" />\n"
        "<title>Site verification Altiaro</title></head>\n"
        f"<body><p>google-site-verification: {token}</p></body></html>"
    )
    return HTMLResponse(content=html, media_type="text/html; charset=utf-8")


@router.get("/public/google-site-verification.txt", include_in_schema=False)
async def google_site_verification_txt():
    """Variante texte plain (utile pour curl debugging)."""
    token = _altiaro_token()
    return PlainTextResponse(content=f"google-site-verification: {token}\n")


# Variante root-level pour matcher la convention Google :
# `https://altiaro.com/google{TOKEN}.html`. Google sert ce path quand on
# choisit la méthode "fichier HTML" depuis la Search Console.
@router.get("/public/google{token}.html", include_in_schema=False)
async def google_token_html(token: str):
    expected = _altiaro_token()
    if not expected:
        return PlainTextResponse(content="not configured", status_code=503)
    if token != expected:
        return PlainTextResponse(content="not found", status_code=404)
    return HTMLResponse(content=f"google-site-verification: google{expected}.html\n")
