"""Google Search Console OAuth 2.0 integration.

Multi-tenant : chaque site stocke son propre `refresh_token` GSC dans
`site.design.gsc.*`. Les endpoints exposés :

- GET  /api/sites/{id}/gsc/connect             → URL OAuth Google (à ouvrir par le user)
- GET  /api/gsc/oauth/callback                 → Google redirige ici avec `code`
- GET  /api/sites/{id}/gsc/status              → {connected, property_url, last_synced_at}
- POST /api/sites/{id}/gsc/disconnect
- GET  /api/sites/{id}/gsc/metrics?days=28     → {avg_position, clicks, impressions, ctr, queries}

Setup : voir docs/GSC_SETUP.md. Les variables d'environnement requises :
GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI.
"""
import os
import secrets
import logging
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode, quote

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import RedirectResponse

from deps import db, get_current_user

router = APIRouter(tags=["gsc"])
logger = logging.getLogger(__name__)

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.environ.get("GOOGLE_REDIRECT_URI", "")
PUBLIC_ORIGIN = os.environ.get("PUBLIC_ORIGIN") or "https://senior-france.preview.emergentagent.com"

SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]


def _gsc_configured() -> bool:
    return bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET and GOOGLE_REDIRECT_URI)


@router.get("/sites/{site_id}/gsc/connect")
async def gsc_connect(site_id: str, user=Depends(get_current_user)):
    """Retourne l'URL OAuth Google à ouvrir dans un nouvel onglet pour connecter
    la Search Console du Concepteur au site."""
    if not _gsc_configured():
        raise HTTPException(
            503,
            "Google Search Console n'est pas encore configuré sur cette plateforme. "
            "L'administrateur doit fournir GOOGLE_CLIENT_ID / SECRET / REDIRECT_URI.",
        )
    site = await db.sites.find_one({"id": site_id}, {"_id": 0})
    if not site:
        raise HTTPException(404, "Site introuvable")

    # CSRF state with site_id + random token, persisted 10 min
    token = secrets.token_urlsafe(24)
    state = f"{site_id}:{token}"
    await db.gsc_oauth_states.insert_one({
        "state": state,
        "site_id": site_id,
        "expires_at": datetime.now(timezone.utc) + timedelta(minutes=10),
    })
    params = {
        "response_type": "code",
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",  # Force re-consent to guarantee a refresh_token
        "state": state,
        "include_granted_scopes": "true",
    }
    url = "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params, quote_via=quote)
    return {"authorization_url": url}


@router.get("/gsc/oauth/callback")
async def gsc_callback(code: str = Query(...), state: str = Query(...)):
    """Google redirige ici après consent. On échange `code` contre `refresh_token`."""
    if not _gsc_configured():
        raise HTTPException(503, "GSC non configuré.")

    # Validate state
    st = await db.gsc_oauth_states.find_one({"state": state}, {"_id": 0})
    if not st:
        raise HTTPException(400, "État OAuth invalide ou expiré.")
    if datetime.fromisoformat(
        str(st["expires_at"]).replace("Z", "+00:00")
    ).replace(tzinfo=timezone.utc) if isinstance(st["expires_at"], str) else st["expires_at"].replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(400, "État OAuth expiré.")

    site_id = st["site_id"]

    # Exchange code for tokens
    import httpx
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )
    if resp.status_code != 200:
        logger.error("Google token exchange failed: %s", resp.text[:300])
        raise HTTPException(502, "Échec de l'échange de token Google.")
    data = resp.json()
    refresh_token = data.get("refresh_token")
    access_token = data.get("access_token")
    if not refresh_token:
        raise HTTPException(
            400,
            "Google n'a pas renvoyé de refresh_token. Déconnectez l'app dans "
            "https://myaccount.google.com/permissions et réessayez.",
        )

    # Fetch the first GSC property available for this account
    property_url = None
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            sites_resp = await client.get(
                "https://searchconsole.googleapis.com/webmasters/v3/sites",
                headers={"Authorization": f"Bearer {access_token}"},
            )
        if sites_resp.status_code == 200:
            sites_list = (sites_resp.json() or {}).get("siteEntry") or []
            if sites_list:
                # Prefer siteUrl with permissionLevel >= siteOwner or siteFullUser
                preferred = next(
                    (s for s in sites_list if s.get("permissionLevel") in ("siteOwner", "siteFullUser")),
                    sites_list[0],
                )
                property_url = preferred.get("siteUrl")
    except Exception:
        logger.exception("GSC sites.list failed (non-fatal)")

    # Persist on the site document (never return refresh_token to the client)
    await db.sites.update_one(
        {"id": site_id},
        {"$set": {
            "design.gsc.refresh_token": refresh_token,
            "design.gsc.property_url": property_url,
            "design.gsc.connected_at": datetime.now(timezone.utc).isoformat(),
            "design.gsc.last_synced_at": None,
        }},
    )
    await db.gsc_oauth_states.delete_one({"state": state})

    # Redirect back to the cockpit with ?gsc=connected
    return RedirectResponse(
        url=f"{PUBLIC_ORIGIN}/sites/{site_id}?gsc=connected",
        status_code=302,
    )


@router.get("/sites/{site_id}/gsc/status")
async def gsc_status(site_id: str, user=Depends(get_current_user)):
    site = await db.sites.find_one({"id": site_id}, {"_id": 0, "design.gsc": 1})
    if not site:
        raise HTTPException(404, "Site introuvable")
    gsc = (site.get("design") or {}).get("gsc") or {}
    return {
        "configured": _gsc_configured(),
        "connected": bool(gsc.get("refresh_token")),
        "property_url": gsc.get("property_url"),
        "connected_at": gsc.get("connected_at"),
        "last_synced_at": gsc.get("last_synced_at"),
    }


@router.post("/sites/{site_id}/gsc/disconnect")
async def gsc_disconnect(site_id: str, user=Depends(get_current_user)):
    site = await db.sites.find_one({"id": site_id}, {"_id": 0})
    if not site:
        raise HTTPException(404, "Site introuvable")
    await db.sites.update_one(
        {"id": site_id},
        {"$unset": {"design.gsc": ""}},
    )
    return {"ok": True}


async def _refresh_access_token(refresh_token: str) -> str | None:
    """Exchange a long-lived refresh_token for a short-lived access_token."""
    if not _gsc_configured():
        return None
    import httpx
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "refresh_token": refresh_token,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "grant_type": "refresh_token",
            },
        )
    if resp.status_code != 200:
        logger.warning("Google token refresh failed: %s", resp.text[:200])
        return None
    return (resp.json() or {}).get("access_token")


@router.get("/sites/{site_id}/gsc/metrics")
async def gsc_metrics(
    site_id: str,
    days: int = Query(28, ge=1, le=90),
    user=Depends(get_current_user),
):
    """Fetch Search Analytics : position moyenne, clicks, impressions, CTR, top queries."""
    site = await db.sites.find_one({"id": site_id}, {"_id": 0, "design.gsc": 1})
    if not site:
        raise HTTPException(404, "Site introuvable")
    gsc = (site.get("design") or {}).get("gsc") or {}
    if not gsc.get("refresh_token"):
        raise HTTPException(401, "Google Search Console non connecté pour ce site.")
    if not gsc.get("property_url"):
        raise HTTPException(400, "Aucune propriété GSC trouvée sur ce compte.")

    access_token = await _refresh_access_token(gsc["refresh_token"])
    if not access_token:
        raise HTTPException(401, "Impossible de rafraîchir le token Google.")

    end_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    start_date = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    property_enc = quote(gsc["property_url"], safe="")
    import httpx
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(
            f"https://searchconsole.googleapis.com/webmasters/v3/sites/{property_enc}/searchAnalytics/query",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "startDate": start_date,
                "endDate": end_date,
                "dimensions": ["query"],
                "rowLimit": 25,
            },
        )
    if resp.status_code != 200:
        logger.warning("GSC searchAnalytics failed: %s", resp.text[:300])
        raise HTTPException(502, f"Erreur Search Console : {resp.status_code}")

    data = resp.json() or {}
    rows = data.get("rows") or []
    total_clicks, total_impressions, total_position = 0, 0, 0.0
    queries = []
    for r in rows:
        clicks = r.get("clicks", 0) or 0
        impressions = r.get("impressions", 0) or 0
        position = r.get("position", 0) or 0
        kw = (r.get("keys") or ["(inconnu)"])[0]
        total_clicks += clicks
        total_impressions += impressions
        total_position += position
        queries.append({
            "query": kw,
            "clicks": clicks,
            "impressions": impressions,
            "position": round(position, 2),
            "ctr": round((clicks / impressions * 100) if impressions else 0, 2),
        })

    avg_position = round(total_position / len(rows), 2) if rows else None
    ctr = round((total_clicks / total_impressions * 100) if total_impressions else 0, 2)

    # Update last_synced_at
    await db.sites.update_one(
        {"id": site_id},
        {"$set": {"design.gsc.last_synced_at": datetime.now(timezone.utc).isoformat()}},
    )

    return {
        "period_days": days,
        "avg_position": avg_position,
        "clicks": total_clicks,
        "impressions": total_impressions,
        "ctr": ctr,
        "queries": queries,
    }
