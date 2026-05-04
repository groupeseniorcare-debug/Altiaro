"""Google Ads API integration (Sprint 19) — Admin only.

Fonctionnalités :
- OAuth2 Web Flow (connect account via popup/redirect)
- List accessible customer accounts (MCC → sub-accounts)
- Keyword Planner : GenerateKeywordIdeas pour enrichir l'analyseur de niches avec
  les vrais volumes Google par pays
- List campaigns + basic metrics (read-only)

Les refresh tokens sont stockés par admin_user_id dans db.google_ads_credentials.
Seuls les utilisateurs avec role="admin" peuvent utiliser ces endpoints.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from deps import db, get_current_user

logger = logging.getLogger("conceptfactory.google_ads")
router = APIRouter()

DEV_TOKEN = os.environ.get("GOOGLE_ADS_DEVELOPER_TOKEN", "")
CLIENT_ID = os.environ.get("GOOGLE_ADS_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("GOOGLE_ADS_CLIENT_SECRET", "")
REDIRECT_URI = os.environ.get("GOOGLE_ADS_REDIRECT_URI", "")
SCOPES = ["https://www.googleapis.com/auth/adwords"]

# Mapping pays → geo_target_constant + language
# Voir : https://developers.google.com/google-ads/api/data/codes-formats
MARKETS = {
    "FR": {"geo": 2250, "lang": 1002, "name": "France"},
    "DE": {"geo": 2276, "lang": 1001, "name": "Allemagne"},
    "BE": {"geo": 2056, "lang": 1002, "name": "Belgique"},
    "NL": {"geo": 2528, "lang": 1010, "name": "Pays-Bas"},
    "LU": {"geo": 2442, "lang": 1002, "name": "Luxembourg"},
    "UK": {"geo": 2826, "lang": 1000, "name": "Royaume-Uni"},
    "CH": {"geo": 2756, "lang": 1002, "name": "Suisse"},
    "ES": {"geo": 2724, "lang": 1003, "name": "Espagne"},
    "IT": {"geo": 2380, "lang": 1004, "name": "Italie"},
}


# ====================== HELPERS ====================== #
def _require_admin(user: dict):
    if user.get("role") != "admin":
        raise HTTPException(403, "Google Ads Center est réservé aux Admins.")


def _require_config():
    if not (DEV_TOKEN and CLIENT_ID and CLIENT_SECRET and REDIRECT_URI):
        raise HTTPException(503,
            "Google Ads non configuré côté serveur. Il manque un des : "
            "GOOGLE_ADS_DEVELOPER_TOKEN, GOOGLE_ADS_CLIENT_ID, "
            "GOOGLE_ADS_CLIENT_SECRET, GOOGLE_ADS_REDIRECT_URI.")


def _build_flow(state: Optional[str] = None):
    from google_auth_oauthlib.flow import Flow
    client_config = {
        "web": {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [REDIRECT_URI],
        }
    }
    flow = Flow.from_client_config(client_config, scopes=SCOPES, state=state)
    flow.redirect_uri = REDIRECT_URI
    return flow


async def _get_client_for_user(user_id: str):
    """Retourne un GoogleAdsClient initialisé avec le refresh_token stocké."""
    creds = await db.google_ads_credentials.find_one(
        {"admin_user_id": user_id}, {"_id": 0}
    )
    if not creds or not creds.get("refresh_token"):
        raise HTTPException(401, "Compte Google Ads non connecté. Clique sur 'Connecter'.")
    from google.ads.googleads.client import GoogleAdsClient
    cfg = {
        "developer_token": DEV_TOKEN,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": creds["refresh_token"],
        "use_proto_plus": True,
    }
    login_cid = creds.get("login_customer_id")
    if login_cid:
        cfg["login_customer_id"] = login_cid.replace("-", "")
    return GoogleAdsClient.load_from_dict(cfg, version="v21")


def _norm_cid(cid: str) -> str:
    return (cid or "").replace("-", "").strip()


# ====================== OAUTH FLOW ====================== #
@router.get("/google-ads/oauth/start")
async def oauth_start(user: dict = Depends(get_current_user)):
    """Retourne l'URL Google pour démarrer la connexion OAuth.

    Fix 2026-05-04 : le `state` n'utilise plus `admin_user_id` (qui causait
    des écrasements si l'admin cliquait 2× avant de finaliser le flow). On
    génère maintenant un UUID aléatoire par call, stocké avec admin_user_id
    et code_verifier pour le callback.
    """
    import uuid as _uuid
    _require_admin(user)
    _require_config()
    random_state = _uuid.uuid4().hex
    flow = _build_flow(state=random_state)
    auth_url, state = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        include_granted_scopes="true",
    )
    # Persist state → admin_user_id + code_verifier (PKCE)
    # upsert sur `state` (unique par flow) pour éviter toute collision
    await db.google_ads_oauth_state.update_one(
        {"state": state},
        {"$set": {
            "state": state,
            "admin_user_id": user.get("id"),
            "code_verifier": getattr(flow, "code_verifier", None),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }},
        upsert=True,
    )
    return {"authorization_url": auth_url, "state": state}


@router.get("/google-ads/oauth/callback")
async def oauth_callback(request: Request, code: Optional[str] = None, state: Optional[str] = None,
                         error: Optional[str] = None):
    """Callback Google → échange code→refresh_token, persiste, redirige vers l'app."""
    # Prefer PUBLIC_ORIGIN; otherwise derive from the request Origin/Referer.
    frontend_base = os.environ.get("PUBLIC_ORIGIN")
    if not frontend_base:
        ref = request.headers.get("referer") or request.headers.get("origin") or ""
        if ref:
            from urllib.parse import urlparse
            p = urlparse(ref)
            if p.scheme and p.netloc:
                frontend_base = f"{p.scheme}://{p.netloc}"
    if not frontend_base:
        # Last resort: build from request URL (avoids hardcoded preview URL)
        frontend_base = f"{request.url.scheme}://{request.url.hostname}"
    if error or not code or not state:
        return RedirectResponse(
            f"{frontend_base}/admin/integrations?google_ads=error&reason={error or 'missing_code'}",
            status_code=302,
        )
    _require_config()
    try:
        # Retrieve code_verifier + admin_user_id (PKCE) stored at oauth/start
        # Fix 2026-05-04 : state est un UUID aléatoire (plus admin_user_id).
        # On récupère donc admin_user_id depuis le state_doc.
        state_doc = await db.google_ads_oauth_state.find_one(
            {"state": state}, {"_id": 0}
        )
        if not state_doc or not state_doc.get("admin_user_id"):
            return RedirectResponse(
                f"{frontend_base}/admin/integrations?google_ads=error&reason=state_expired_or_invalid",
                status_code=302,
            )
        admin_user_id = state_doc["admin_user_id"]
        flow = _build_flow(state=state)
        if state_doc.get("code_verifier"):
            flow.code_verifier = state_doc["code_verifier"]
        flow.fetch_token(code=code)
        creds_obj = flow.credentials
        await db.google_ads_credentials.update_one(
            {"admin_user_id": admin_user_id},
            {"$set": {
                "admin_user_id": admin_user_id,
                "refresh_token": creds_obj.refresh_token,
                "access_token": creds_obj.token,
                "token_expiry": creds_obj.expiry.isoformat() if creds_obj.expiry else None,
                "scopes": list(creds_obj.scopes or []),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "is_active": True,
            }},
            upsert=True,
        )
        # Cleanup OAuth state
        await db.google_ads_oauth_state.delete_one({"state": state})
        return RedirectResponse(
            f"{frontend_base}/admin/integrations?google_ads=connected",
            status_code=302,
        )
    except Exception as e:
        logger.exception("Google Ads OAuth callback failed")
        return RedirectResponse(
            f"{frontend_base}/admin/integrations?google_ads=error&reason={str(e)[:100]}",
            status_code=302,
        )


@router.get("/google-ads/status")
async def status(user: dict = Depends(get_current_user)):
    """Indique si l'admin a déjà connecté son compte Google Ads."""
    _require_admin(user)
    creds = await db.google_ads_credentials.find_one(
        {"admin_user_id": user["id"]}, {"_id": 0}
    )
    return {
        "config_ready": bool(DEV_TOKEN and CLIENT_ID and CLIENT_SECRET and REDIRECT_URI),
        "connected": bool(creds and creds.get("refresh_token") and creds.get("is_active")),
        "updated_at": creds.get("updated_at") if creds else None,
        "login_customer_id": creds.get("login_customer_id") if creds else None,
        "preferred_customer_id": creds.get("preferred_customer_id") if creds else None,
    }


@router.post("/google-ads/disconnect")
async def disconnect(user: dict = Depends(get_current_user)):
    _require_admin(user)
    await db.google_ads_credentials.update_one(
        {"admin_user_id": user["id"]},
        {"$set": {"is_active": False, "refresh_token": None,
                  "updated_at": datetime.now(timezone.utc).isoformat()}},
    )
    return {"ok": True}


class SetLoginCidInput(BaseModel):
    login_customer_id: str


@router.post("/google-ads/login-customer-id")
async def set_login_cid(data: SetLoginCidInput, user: dict = Depends(get_current_user)):
    """Définit le Login Customer ID (MCC) à utiliser pour les requêtes."""
    _require_admin(user)
    cid = _norm_cid(data.login_customer_id)
    if not cid.isdigit() or len(cid) != 10:
        raise HTTPException(400, "Login Customer ID invalide (doit être 10 chiffres).")
    await db.google_ads_credentials.update_one(
        {"admin_user_id": user["id"]},
        {"$set": {"login_customer_id": cid,
                  "updated_at": datetime.now(timezone.utc).isoformat()}},
    )
    return {"ok": True, "login_customer_id": cid}


class SetPreferredCidInput(BaseModel):
    preferred_customer_id: str


@router.post("/google-ads/preferred-customer-id")
async def set_preferred_cid(data: SetPreferredCidInput, user: dict = Depends(get_current_user)):
    """Définit le compte Google Ads à utiliser comme cible (celui qui a les campagnes actives)."""
    _require_admin(user)
    cid = _norm_cid(data.preferred_customer_id)
    if not cid.isdigit() or len(cid) != 10:
        raise HTTPException(400, "Customer ID invalide (doit être 10 chiffres).")
    await db.google_ads_credentials.update_one(
        {"admin_user_id": user["id"]},
        {"$set": {"preferred_customer_id": cid,
                  "updated_at": datetime.now(timezone.utc).isoformat()}},
    )
    return {"ok": True, "preferred_customer_id": cid}


# ====================== LIST CUSTOMERS ====================== #
@router.get("/google-ads/customers")
async def list_customers(user: dict = Depends(get_current_user)):
    """Liste les comptes Google Ads accessibles."""
    _require_admin(user)
    client = await _get_client_for_user(user["id"])
    try:
        cs = client.get_service("CustomerService")
        accessible = cs.list_accessible_customers()
        out = []
        for rn in accessible.resource_names:
            cid = rn.split("/")[-1]
            out.append({"resource_name": rn, "customer_id": cid,
                        "customer_id_pretty": f"{cid[:3]}-{cid[3:6]}-{cid[6:]}"})
        return {"customers": out}
    except Exception as e:
        logger.exception("list_accessible_customers failed")
        raise HTTPException(502, f"Google Ads API error: {str(e)[:300]}")


# ====================== KEYWORD PLANNER ====================== #
class KeywordIdeasInput(BaseModel):
    customer_id: str
    seed_keywords: list[str]
    country: str = "FR"
    page_url: Optional[str] = None
    limit: int = 50


@router.post("/google-ads/keyword-ideas")
async def keyword_ideas(data: KeywordIdeasInput, user: dict = Depends(get_current_user)):
    """GenerateKeywordIdeas avec volumes réels mensuels + competition index."""
    _require_admin(user)
    market = MARKETS.get(data.country.upper())
    if not market:
        raise HTTPException(400, f"Pays non supporté : {data.country}. Valides : {list(MARKETS.keys())}")
    client = await _get_client_for_user(user["id"])
    try:
        svc = client.get_service("KeywordPlanIdeaService")
        req = client.get_type("GenerateKeywordIdeasRequest")
        req.customer_id = _norm_cid(data.customer_id)
        req.language = f"languageConstants/{market['lang']}"
        req.geo_target_constants.append(f"geoTargetConstants/{market['geo']}")
        req.include_adult_keywords = False
        req.keyword_plan_network = client.enums.KeywordPlanNetworkEnum.GOOGLE_SEARCH

        seed = client.get_type("KeywordAndUrlSeed") if data.page_url and data.seed_keywords \
            else client.get_type("KeywordSeed") if data.seed_keywords \
            else client.get_type("UrlSeed")
        if data.seed_keywords and data.page_url:
            seed.keywords.extend(data.seed_keywords)
            seed.url = data.page_url
            req.keyword_and_url_seed = seed
        elif data.seed_keywords:
            seed.keywords.extend(data.seed_keywords)
            req.keyword_seed = seed
        elif data.page_url:
            seed.url = data.page_url
            req.url_seed = seed
        else:
            raise HTTPException(400, "seed_keywords ou page_url requis")

        response = svc.generate_keyword_ideas(request=req)
        out = []
        for idea in response:
            m = idea.keyword_idea_metrics
            out.append({
                "keyword": idea.text,
                "avg_monthly_searches": int(m.avg_monthly_searches or 0),
                "competition": str(m.competition).split(".")[-1] if m.competition else "UNKNOWN",
                "competition_index": int(m.competition_index or 0),
                "low_top_of_page_bid_eur": (m.low_top_of_page_bid_micros or 0) / 1_000_000,
                "high_top_of_page_bid_eur": (m.high_top_of_page_bid_micros or 0) / 1_000_000,
            })
            if len(out) >= data.limit:
                break
        out.sort(key=lambda x: x["avg_monthly_searches"], reverse=True)
        return {"country": data.country, "market": market["name"],
                "count": len(out), "ideas": out}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("keyword_ideas failed")
        raise HTTPException(502, f"Keyword Planner error: {str(e)[:300]}")


# ====================== CAMPAIGNS (read-only) ====================== #
class CampaignsInput(BaseModel):
    customer_id: str
    days: int = 30


@router.post("/google-ads/campaigns")
async def campaigns(data: CampaignsInput, user: dict = Depends(get_current_user)):
    """Liste les campagnes + metrics agrégés sur N derniers jours."""
    _require_admin(user)
    client = await _get_client_for_user(user["id"])
    try:
        ga = client.get_service("GoogleAdsService")
        during = "LAST_30_DAYS" if data.days == 30 else "LAST_7_DAYS" if data.days == 7 else "LAST_14_DAYS"
        query = f"""
            SELECT
                campaign.id, campaign.name, campaign.status,
                campaign.advertising_channel_type,
                metrics.impressions, metrics.clicks, metrics.cost_micros,
                metrics.conversions, metrics.ctr, metrics.average_cpc
            FROM campaign
            WHERE segments.date DURING {during}
            ORDER BY metrics.cost_micros DESC
            LIMIT 100
        """
        req = client.get_type("SearchGoogleAdsStreamRequest")
        req.customer_id = _norm_cid(data.customer_id)
        req.query = query
        out = []
        for batch in ga.search_stream(req):
            for row in batch.results:
                out.append({
                    "campaign_id": str(row.campaign.id),
                    "name": row.campaign.name,
                    "status": str(row.campaign.status).split(".")[-1],
                    "channel": str(row.campaign.advertising_channel_type).split(".")[-1],
                    "impressions": int(row.metrics.impressions or 0),
                    "clicks": int(row.metrics.clicks or 0),
                    "cost_eur": (row.metrics.cost_micros or 0) / 1_000_000,
                    "conversions": float(row.metrics.conversions or 0),
                    "ctr": float(row.metrics.ctr or 0) * 100,
                    "avg_cpc_eur": (row.metrics.average_cpc or 0) / 1_000_000,
                })
        return {"customer_id": data.customer_id, "days": data.days,
                "count": len(out), "campaigns": out}
    except Exception as e:
        logger.exception("campaigns failed")
        raise HTTPException(502, f"Google Ads API error: {str(e)[:300]}")


@router.get("/google-ads/markets")
async def list_markets(user: dict = Depends(get_current_user)):
    _require_admin(user)
    return {"markets": [{"code": k, **v} for k, v in MARKETS.items()]}


# ====================== PUBLIC HELPER (for analyzer) ====================== #
async def _get_platform_client():
    """Trouve n'importe quel Admin ayant connecté Google Ads et renvoie son client.
    Préfère : le `preferred_customer_id` stocké (configuré manuellement), sinon
    premier compte accessible non-manager, sinon premier accessible.
    Retourne (client, customer_id) ou (None, None) si aucune connexion.
    """
    if not (DEV_TOKEN and CLIENT_ID and CLIENT_SECRET):
        return None, None
    creds = await db.google_ads_credentials.find_one(
        {"is_active": True, "refresh_token": {"$ne": None}},
        {"_id": 0},
    )
    if not creds or not creds.get("refresh_token"):
        return None, None
    from google.ads.googleads.client import GoogleAdsClient
    cfg = {
        "developer_token": DEV_TOKEN,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": creds["refresh_token"],
        "use_proto_plus": True,
    }
    login_cid = (creds.get("login_customer_id") or "").replace("-", "")
    if login_cid:
        cfg["login_customer_id"] = login_cid
    try:
        client = GoogleAdsClient.load_from_dict(cfg, version="v21")
    except Exception as e:
        logger.warning(f"Google Ads client init failed: {e}")
        return None, None

    # 1) preferred_customer_id (manually picked by admin) wins
    preferred = (creds.get("preferred_customer_id") or "").replace("-", "")
    if preferred:
        return client, preferred

    # 2) login_customer_id is typically the MCC → we must find a child non-manager
    try:
        cs = client.get_service("CustomerService")
        accessible = cs.list_accessible_customers()
        rns = list(accessible.resource_names)
        if not rns:
            return None, None
        # Try to find a non-manager via GoogleAdsService.search on each
        ga = client.get_service("GoogleAdsService")
        for rn in rns:
            cid = rn.split("/")[-1]
            try:
                req = client.get_type("SearchGoogleAdsRequest")
                req.customer_id = cid
                req.query = "SELECT customer.id, customer.manager, customer.status FROM customer LIMIT 1"
                resp = ga.search(request=req)
                for row in resp:
                    if not row.customer.manager:
                        return client, cid
            except Exception:
                continue
        # Fallback: first one anyway
        return client, rns[0].split("/")[-1]
    except Exception as e:
        logger.warning(f"list_accessible_customers failed: {e}")
    return None, None


async def fetch_keyword_volumes(keywords_by_country: dict) -> dict:
    """Pour chaque pays, résout les volumes mensuels Google réels pour la liste
    de mots-clés fournie. Limites : 20 mots-clés par pays max (quota friendly).

    Input : {"FR": ["kw1", "kw2", ...], "DE": [...]}
    Output : {
      "available": bool,
      "by_country": {
        "FR": {"keywords": [{"keyword": "kw1", "volume": 2400, "competition": "MEDIUM",
                             "competition_index": 55, "cpc_low_eur": 0.8, "cpc_high_eur": 2.1}],
               "total_volume_monthly": 18500, "avg_cpc_eur": 1.35}
      }}
    Jamais d'exception remontée : si erreur, available=false."""
    out = {"available": False, "by_country": {}, "reason": None}
    client, default_cid = await _get_platform_client()
    if not client:
        out["reason"] = "no_admin_connected"
        return out

    for country, kws in (keywords_by_country or {}).items():
        country = (country or "").upper()
        market = MARKETS.get(country)
        if not market or not kws:
            continue
        kws_clean = [k for k in (kws or []) if k and isinstance(k, str)][:20]
        if not kws_clean:
            continue
        try:
            svc = client.get_service("KeywordPlanIdeaService")
            req = client.get_type("GenerateKeywordHistoricalMetricsRequest")
            req.customer_id = default_cid
            req.keywords.extend(kws_clean)
            req.language = f"languageConstants/{market['lang']}"
            req.geo_target_constants.append(f"geoTargetConstants/{market['geo']}")
            req.keyword_plan_network = client.enums.KeywordPlanNetworkEnum.GOOGLE_SEARCH
            hist_opts = client.get_type("HistoricalMetricsOptions")
            hist_opts.include_average_cpc = True
            req.historical_metrics_options = hist_opts

            resp = svc.generate_keyword_historical_metrics(request=req)
            rows = []
            vol_sum = 0
            cpc_values = []
            for r in resp.results:
                kw = r.text or ""
                m = r.keyword_metrics
                v = int(m.avg_monthly_searches or 0) if m else 0
                low = (m.low_top_of_page_bid_micros or 0) / 1_000_000 if m else 0
                high = (m.high_top_of_page_bid_micros or 0) / 1_000_000 if m else 0
                rows.append({
                    "keyword": kw,
                    "volume": v,
                    "competition": str(m.competition).split(".")[-1] if m and m.competition else "UNKNOWN",
                    "competition_index": int(m.competition_index or 0) if m else 0,
                    "cpc_low_eur": round(low, 2),
                    "cpc_high_eur": round(high, 2),
                })
                vol_sum += v
                if high > 0:
                    cpc_values.append((low + high) / 2)
            avg_cpc = round(sum(cpc_values) / len(cpc_values), 2) if cpc_values else 0
            rows.sort(key=lambda x: x["volume"], reverse=True)
            out["by_country"][country] = {
                "keywords": rows,
                "total_volume_monthly": vol_sum,
                "avg_cpc_eur": avg_cpc,
            }
        except Exception as e:
            logger.warning(f"[google-ads enrich] {country} failed: {str(e)[:180]}")
            out["by_country"][country] = {"keywords": [], "total_volume_monthly": 0,
                                          "avg_cpc_eur": 0, "error": str(e)[:180]}
    out["available"] = any(v.get("total_volume_monthly", 0) > 0 for v in out["by_country"].values())
    if not out["available"]:
        out["reason"] = "no_volumes_returned"
    return out



# ====================== SHARED KEYWORD IDEAS (accessible Concepteurs) ====================== #
class SharedKeywordIdeasInput(BaseModel):
    seed_keywords: list[str]
    country: str = "FR"
    page_url: Optional[str] = None
    limit: int = 80


@router.post("/keywords/ideas")
async def shared_keyword_ideas(data: SharedKeywordIdeasInput,
                               user: dict = Depends(get_current_user)):
    """Recherche de mots-clés similaires via Google Keyword Planner.
    Utilise le compte Google Ads connecté au niveau plateforme (Admin).
    Accessible à tous les utilisateurs authentifiés (Admin + Concepteurs).

    Exemple d'usage : Concepteur tape "fauteuil senior" → 80 idées avec
    volume/competition/CPC pour rédiger son SEO + Ads Copy.
    """
    market = MARKETS.get(data.country.upper())
    if not market:
        raise HTTPException(400, f"Pays non supporté : {data.country}. Valides : {list(MARKETS.keys())}")
    seeds = [k.strip() for k in (data.seed_keywords or []) if k and k.strip()]
    if not seeds and not data.page_url:
        raise HTTPException(400, "seed_keywords ou page_url requis")

    client, customer_id = await _get_platform_client()
    if not client or not customer_id:
        raise HTTPException(503,
            "Google Keyword Planner non disponible. Aucun Admin n'a connecté "
            "son compte Google Ads. Demande à ton administrateur de se connecter "
            "depuis /admin/google-ads.")

    try:
        svc = client.get_service("KeywordPlanIdeaService")
        req = client.get_type("GenerateKeywordIdeasRequest")
        req.customer_id = customer_id
        req.language = f"languageConstants/{market['lang']}"
        req.geo_target_constants.append(f"geoTargetConstants/{market['geo']}")
        req.include_adult_keywords = False
        req.keyword_plan_network = client.enums.KeywordPlanNetworkEnum.GOOGLE_SEARCH

        if seeds and data.page_url:
            seed_obj = client.get_type("KeywordAndUrlSeed")
            seed_obj.keywords.extend(seeds)
            seed_obj.url = data.page_url
            req.keyword_and_url_seed = seed_obj
        elif seeds:
            seed_obj = client.get_type("KeywordSeed")
            seed_obj.keywords.extend(seeds)
            req.keyword_seed = seed_obj
        else:
            seed_obj = client.get_type("UrlSeed")
            seed_obj.url = data.page_url
            req.url_seed = seed_obj

        response = svc.generate_keyword_ideas(request=req)
        out = []
        for idea in response:
            m = idea.keyword_idea_metrics
            out.append({
                "keyword": idea.text,
                "avg_monthly_searches": int(m.avg_monthly_searches or 0),
                "competition": str(m.competition).split(".")[-1] if m.competition else "UNKNOWN",
                "competition_index": int(m.competition_index or 0),
                "cpc_low_eur": round((m.low_top_of_page_bid_micros or 0) / 1_000_000, 2),
                "cpc_high_eur": round((m.high_top_of_page_bid_micros or 0) / 1_000_000, 2),
            })
            if len(out) >= data.limit:
                break
        out.sort(key=lambda x: x["avg_monthly_searches"], reverse=True)
        return {
            "country": data.country,
            "market": market["name"],
            "seeds": seeds,
            "count": len(out),
            "ideas": out,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("shared_keyword_ideas failed")
        raise HTTPException(502, f"Google Keyword Planner error: {str(e)[:300]}")
