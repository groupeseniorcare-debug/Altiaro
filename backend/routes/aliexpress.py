"""
AliExpress Dropshipping OAuth + API stubs.

This file currently exposes only the OAuth callback endpoint registered with
AliExpress when creating the App (category: Drop Shipping). It receives the
authorization `code` that AliExpress redirects to after a seller authorizes
our application.

Full flow will be :
  1. merchant clicks "Connect AliExpress" in the cockpit
  2. we redirect them to https://api-sg.aliexpress.com/oauth/authorize?...
  3. AliExpress redirects back to /api/aliexpress/oauth/callback?code=XXX&state=YYY
  4. we exchange the code for an access_token and persist it on the site
  5. we use the access_token to call product-import / order-place / tracking APIs

For now: we capture the code + state and render a friendly success page so
AliExpress's validation ping (and any seller authorizing) receives HTTP 200.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from deps import db

logger = logging.getLogger("conceptfactory.aliexpress")
router = APIRouter()


@router.get("/aliexpress/oauth/callback", response_class=HTMLResponse)
async def aliexpress_oauth_callback(
    request: Request,
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    error_description: Optional[str] = None,
):
    """
    Endpoint registered as Callback URL in the AliExpress App Console.
    Always responds 200 OK so AliExpress health checks pass.
    """
    now = datetime.now(timezone.utc)

    # Persist the raw callback for audit / later exchange
    try:
        await db.aliexpress_oauth_callbacks.insert_one({
            "received_at": now,
            "code": code,
            "state": state,
            "error": error,
            "error_description": error_description,
            "ip": request.headers.get("x-forwarded-for") or request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent", ""),
        })
    except Exception:
        logger.exception("[aliexpress] could not persist OAuth callback")

    if error:
        logger.warning(f"[aliexpress] OAuth error received : {error} — {error_description}")
        return HTMLResponse(_render_error_page(error, error_description), status_code=200)

    if not code:
        # Probably a validation ping from AliExpress or a browser visiting directly.
        return HTMLResponse(_render_waiting_page(), status_code=200)

    logger.info(f"[aliexpress] OAuth code received (state={state}) — length={len(code)}")
    return HTMLResponse(_render_success_page(), status_code=200)


def _render_success_page() -> str:
    return """<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><title>Altiaro × AliExpress — Connexion réussie</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
  body{margin:0;font-family:Georgia,'Times New Roman',serif;background:#FDFBF7;color:#1C1917;
       min-height:100vh;display:flex;align-items:center;justify-content:center;padding:24px}
  .card{background:#fff;max-width:440px;border-radius:20px;padding:48px 40px;text-align:center;
        box-shadow:0 10px 40px rgba(28,25,23,.08);border:1px solid #F5F2EB}
  .badge{width:64px;height:64px;border-radius:50%;background:#10b98120;
         display:inline-flex;align-items:center;justify-content:center;margin-bottom:24px;font-size:32px}
  h1{font-size:26px;margin:0 0 12px}
  p{color:#57534E;font-family:system-ui,sans-serif;font-size:15px;line-height:1.65;margin:0 0 18px}
  .note{font-size:12px;color:#A8A29E;margin-top:24px;border-top:1px solid #F5F2EB;padding-top:16px}
</style></head>
<body><div class="card">
  <div class="badge">✓</div>
  <h1>Connexion AliExpress confirmée</h1>
  <p>Votre boutique Altiaro est maintenant liée à votre compte AliExpress Dropshipping.
  Vous pouvez fermer cette fenêtre et retourner dans votre cockpit.</p>
  <div class="note">Altiaro · altiaro.com</div>
</div></body></html>"""


def _render_waiting_page() -> str:
    return """<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><title>Altiaro × AliExpress OAuth</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
  body{margin:0;font-family:Georgia,serif;background:#FDFBF7;color:#1C1917;
       min-height:100vh;display:flex;align-items:center;justify-content:center;padding:24px}
  .card{background:#fff;max-width:440px;border-radius:20px;padding:40px;text-align:center;
        box-shadow:0 10px 40px rgba(28,25,23,.08);border:1px solid #F5F2EB}
  h1{font-size:22px;margin:0 0 10px}
  p{color:#57534E;font-family:system-ui,sans-serif;font-size:14px;line-height:1.6;margin:0}
</style></head>
<body><div class="card">
  <h1>Endpoint OAuth Altiaro × AliExpress</h1>
  <p>Ce point d'entrée est réservé à la redirection OAuth initiée depuis votre cockpit Altiaro.</p>
</div></body></html>"""


def _render_error_page(err: str, desc: Optional[str]) -> str:
    safe_desc = (desc or "").replace("<", "&lt;").replace(">", "&gt;")
    safe_err = (err or "").replace("<", "&lt;").replace(">", "&gt;")
    return f"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><title>Altiaro × AliExpress — Erreur</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
  body{{margin:0;font-family:Georgia,serif;background:#FDFBF7;color:#1C1917;
       min-height:100vh;display:flex;align-items:center;justify-content:center;padding:24px}}
  .card{{background:#fff;max-width:480px;border-radius:20px;padding:40px;text-align:center;
        box-shadow:0 10px 40px rgba(28,25,23,.08);border:1px solid #FFE4E6}}
  h1{{font-size:22px;margin:0 0 10px;color:#BE123C}}
  p{{color:#57534E;font-family:system-ui,sans-serif;font-size:14px;line-height:1.6;margin:0 0 10px}}
  code{{background:#FFE4E6;padding:2px 6px;border-radius:4px;font-size:12px}}
</style></head>
<body><div class="card">
  <h1>Autorisation refusée</h1>
  <p>L'autorisation AliExpress n'a pas pu être finalisée.</p>
  <p><code>{safe_err}</code> — {safe_desc}</p>
</div></body></html>"""
