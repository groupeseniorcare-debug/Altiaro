"""OAuth Google Master — health check + alerte token expiré.

Lancé au boot + via cron toutes les 6h. Écrit dans `db.admin_notifications`
une alerte high-priority si :
  - Pas de refresh_token en DB
  - Refresh test échoue avec `invalid_grant`

L'admin reçoit aussi un email Resend si `RESEND_ADMIN_EMAIL` est set.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any

from deps import db

logger = logging.getLogger("altiaro.google_oauth_health")


async def _try_refresh_master() -> Dict[str, Any]:
    """Tente un refresh sur le token master. Renvoie ok/expired/missing."""
    doc = await db.platform_settings.find_one({"key": "google_master"}) or {}
    refresh_token = doc.get("refresh_token")
    if not refresh_token:
        return {"ok": False, "reason": "no_refresh_token"}
    try:
        import os
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        creds = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=os.environ.get("GOOGLE_CLIENT_ID"),
            client_secret=os.environ.get("GOOGLE_CLIENT_SECRET"),
        )
        await asyncio.to_thread(creds.refresh, Request())
        return {"ok": True, "expires_in": getattr(creds, "expiry", None) and creds.expiry.isoformat()}
    except Exception as e:
        msg = str(e)
        if "invalid_grant" in msg or "expired" in msg.lower() or "revoked" in msg.lower():
            return {"ok": False, "reason": "invalid_grant", "error": msg[:200]}
        return {"ok": False, "reason": "refresh_failed", "error": msg[:200]}


async def google_master_health_tick() -> Dict[str, Any]:
    """Cron entry. Met à jour `platform_health` et logue notification si KO."""
    res = await _try_refresh_master()
    now = datetime.now(timezone.utc).isoformat()
    await db.platform_health.update_one(
        {"key": "google_master_oauth"},
        {"$set": {"last_check_at": now, **res}},
        upsert=True,
    )
    if not res.get("ok"):
        # Persist a high-priority admin notification (idempotent : 1/jour max)
        existing = await db.admin_notifications.find_one(
            {
                "key": "google_master_oauth_expired",
                "resolved": {"$ne": True},
            },
        )
        if not existing:
            await db.admin_notifications.insert_one({
                "key": "google_master_oauth_expired",
                "severity": "high",
                "title": "Google Master OAuth expiré",
                "message": (
                    f"Le refresh token Google Master ne fonctionne plus "
                    f"({res.get('reason')}). Toutes les opérations GMC, GSC, "
                    f"Ads, GA4 sont en panne. Reconnecte sur /admin/google-master."
                ),
                "action_url": "/admin/google-master",
                "created_at": now,
                "resolved": False,
            })
            logger.error(f"[oauth-health] notification créée — {res}")
            try:
                from routes.emails import send_email_via_resend
                import os
                admin_email = os.environ.get("RESEND_ADMIN_EMAIL") or ""
                if admin_email:
                    await send_email_via_resend(
                        to=admin_email,
                        subject="🚨 Google Master OAuth expiré — reconnect requis",
                        html=(
                            f"<p>Le refresh token Google Master ne fonctionne plus.</p>"
                            f"<p>Cause : <code>{res.get('reason')}</code></p>"
                            f"<p><a href='/admin/google-master'>Reconnecte ici</a>.</p>"
                        ),
                        tags=["oauth_alert"],
                    )
            except Exception:
                logger.exception("[oauth-health] email alert failed")
    return res
