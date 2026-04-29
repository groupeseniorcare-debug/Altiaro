"""Auto-provisioning Google pour chaque site Altiaro lancé.

Le but : quand un concepteur fait Go-Live sur son site, on crée en arrière-plan
les ressources Google nécessaires pour suivre, indexer et publicité.

Idempotent : chaque fonction vérifie l'état actuel avant de créer ou de skip.
"""
from __future__ import annotations
import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlparse

from deps import db

logger = logging.getLogger("altiaro.google_provisioning")


async def _site_domain(site: dict) -> Optional[str]:
    pu = site.get("public_url") or site.get("custom_domain") or ""
    if not pu:
        return None
    if not pu.startswith("http"):
        return pu.replace("/", "")
    return urlparse(pu).netloc


async def provision_gsc_property(site: dict, creds) -> dict:
    """Search Console : ajoute le site comme propriété + soumet le sitemap.
    Pre-requis : le concepteur a déjà cliqué "Connecter GSC" en site-par-site,
    OU le master Altiaro est admin sur le domaine. Best-effort.
    """
    domain = await _site_domain(site)
    if not domain:
        return {"ok": False, "reason": "no_domain"}
    if not creds:
        return {"ok": False, "reason": "no_master_credentials"}
    site_url = f"https://{domain}/"
    try:
        from googleapiclient.discovery import build
        wm = build("searchconsole", "v1", credentials=creds, cache_discovery=False)
        await asyncio.to_thread(wm.sites().add(siteUrl=site_url).execute)
        try:
            await asyncio.to_thread(
                wm.sitemaps().submit(
                    siteUrl=site_url,
                    feedpath=f"https://{domain}/sitemap.xml",
                ).execute,
            )
        except Exception as e:
            logger.info(f"[gsc] sitemap submit (non-blocking) : {str(e)[:120]}")
        return {"ok": True, "site_url": site_url}
    except Exception as e:
        return {"ok": False, "error": str(e)[:300]}


async def provision_gmc_subaccount(site: dict, creds, mca_id: Optional[str] = None) -> dict:
    """Crée un sub-account Merchant Center si MCA actif. Sinon log warning et skip."""
    if not creds:
        return {"ok": False, "reason": "no_master_credentials"}
    domain = await _site_domain(site)
    if not domain:
        return {"ok": False, "reason": "no_domain"}
    mca_id = mca_id or os.environ.get("GOOGLE_MERCHANT_MASTER_ID") or ""
    if not mca_id:
        # Fallback : check platform_settings.gmc_master
        gmc_doc = await db.platform_settings.find_one({"key": "gmc_master"})
        if gmc_doc and gmc_doc.get("is_mca") and gmc_doc.get("account_id"):
            mca_id = gmc_doc["account_id"]
    if not mca_id:
        return {"ok": False, "reason": "no_mca_configured",
                "warning": "Compte Merchant maitre non MCA — sub-account auto impossible"}
    try:
        from googleapiclient.discovery import build
        svc = build("content", "v2.1", credentials=creds, cache_discovery=False)
        body = {
            "name": site.get("name") or domain,
            "websiteUrl": f"https://{domain}",
            "adultContent": False,
        }
        resp = await asyncio.to_thread(
            svc.accounts().insert(merchantId=mca_id, body=body).execute,
        )
        sub_id = resp.get("id")
        return {"ok": True, "merchant_id": sub_id, "mca_id": mca_id}
    except Exception as e:
        return {"ok": False, "error": str(e)[:400]}


async def provision_ads_client(site: dict, creds) -> dict:
    """Crée un client Google Ads sous le MCC Altiaro.

    Utilise la lib `google-ads` qui exige son propre client config (pas
    juste creds OAuth). Best-effort — retourne `degraded` si la config
    n'est pas prête.
    """
    mcc = os.environ.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID") or ""
    dev_token = os.environ.get("GOOGLE_ADS_DEVELOPER_TOKEN") or ""
    if not mcc or not dev_token or not creds:
        return {"ok": False, "reason": "missing_ads_config"}
    domain = await _site_domain(site)
    try:
        from google.ads.googleads.client import GoogleAdsClient  # noqa: F401
        # On instancie via dict-config en utilisant le refresh_token master
        master_doc = await db.platform_settings.find_one({"key": "google_master"})
        if not master_doc or not master_doc.get("refresh_token"):
            return {"ok": False, "reason": "no_master_refresh_token"}
        cfg = {
            "developer_token": dev_token,
            "client_id": os.environ.get("GOOGLE_CLIENT_ID") or "",
            "client_secret": os.environ.get("GOOGLE_CLIENT_SECRET") or "",
            "refresh_token": master_doc["refresh_token"],
            "login_customer_id": mcc,
            "use_proto_plus": True,
        }
        client = GoogleAdsClient.load_from_dict(cfg)  # type: ignore
        # Build createCustomerClient request
        # NB : la création d'un client via l'API Google Ads est une opération
        # avancée qui nécessite la méthode `customers.createCustomerClient`.
        svc = client.get_service("CustomerService")
        req = client.get_type("CreateCustomerClientRequest")
        req.customer_id = mcc
        req.customer_client.descriptive_name = (site.get("name") or domain or "Altiaro Site")[:120]
        req.customer_client.currency_code = "EUR"
        req.customer_client.time_zone = "Europe/Paris"
        resp = await asyncio.to_thread(svc.create_customer_client, request=req)
        # resp.resource_name = customers/{id}
        new_id = (resp.resource_name or "").split("/")[-1]
        return {"ok": True, "ads_customer_id": new_id, "mcc_id": mcc}
    except Exception as e:
        return {"ok": False, "error": str(e)[:400]}


async def provision_ga4_property(site: dict, creds) -> dict:
    """Crée une property GA4 + un dataStream pour le domaine du site."""
    if not creds:
        return {"ok": False, "reason": "no_master_credentials"}
    domain = await _site_domain(site)
    if not domain:
        return {"ok": False, "reason": "no_domain"}
    # Account ID master
    account_id = os.environ.get("GA4_MASTER_ACCOUNT_ID") or ""
    if not account_id:
        # Fallback DB (auto-discovered post-OAuth)
        ga4_doc = await db.platform_settings.find_one({"key": "ga4_master"})
        if ga4_doc:
            account_id = ga4_doc.get("account_id") or ""
    if not account_id:
        return {"ok": False, "reason": "GA4_MASTER_ACCOUNT_ID missing in env",
                "warning": "GA4 master account non découvert — lancer le master OAuth admin"}
    try:
        from googleapiclient.discovery import build
        svc = build("analyticsadmin", "v1beta", credentials=creds, cache_discovery=False)
        prop_body = {
            "parent": f"accounts/{account_id}",
            "displayName": (site.get("name") or domain)[:100],
            "currencyCode": "EUR",
            "timeZone": "Europe/Paris",
            "industryCategory": "SHOPPING",
        }
        prop = await asyncio.to_thread(svc.properties().create(body=prop_body).execute)
        prop_id = (prop.get("name") or "").split("/")[-1]
        # Web stream — l'API Analytics Admin v1beta exige un champ `type`
        # explicite (regression silencieuse depuis avril 2026).
        stream_body = {
            "displayName": f"{domain} web stream",
            "type": "WEB_DATA_STREAM",
            "webStreamData": {"defaultUri": f"https://{domain}"},
        }
        stream = await asyncio.to_thread(
            svc.properties().dataStreams().create(
                parent=f"properties/{prop_id}", body=stream_body,
            ).execute,
        )
        measurement_id = ((stream.get("webStreamData") or {}).get("measurementId")) or ""
        return {
            "ok": True,
            "ga4_property_id": prop_id,
            "ga4_measurement_id": measurement_id,
            "account_id": account_id,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)[:400]}


async def inject_tracking_into_storefront(site: dict, ga4_id: str, ads_id: Optional[str] = None) -> dict:
    """Persiste les IDs dans la fiche site pour que le storefront les charge.

    Le storefront React lit `site.tracking` au runtime et injecte les balises
    GA4 / Ads gtag côté client.
    """
    patch = {
        "tracking.ga4_measurement_id": ga4_id,
        "tracking.updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if ads_id:
        patch["tracking.ads_customer_id"] = ads_id
    await db.sites.update_one({"id": site["id"]}, {"$set": patch})
    return {"ok": True, "tracking": {"ga4": ga4_id, "ads": ads_id}}


# ----- Idempotence + locks -----
async def _acquire_lock(site_id: str) -> bool:
    """Mutex Mongo court (5 min TTL) pour éviter les double-runs."""
    now = datetime.now(timezone.utc)
    res = await db.platform_settings.update_one(
        {"key": f"prov_lock:{site_id}", "locked_until": {"$lt": now.isoformat()}},
        {"$set": {"key": f"prov_lock:{site_id}",
                  "locked_until": now.replace(microsecond=0).isoformat() + ".300"}},
        upsert=True,
    )
    return res.upserted_id is not None or res.modified_count > 0


async def _release_lock(site_id: str):
    await db.platform_settings.delete_one({"key": f"prov_lock:{site_id}"})


async def provision_all(site_id: str, force: bool = False) -> dict:
    """Orchestrateur idempotent. Stocke tout dans `db.sites.{id}.google_provisioning`."""
    site = await db.sites.find_one({"id": site_id}, {"_id": 0})
    if not site:
        return {"ok": False, "reason": "site_not_found"}
    existing = site.get("google_provisioning") or {}
    if not force and existing.get("status") == "completed":
        return {"ok": True, "reused": True, **existing}
    # Master credentials
    from routes.google_master import get_master_credentials
    creds = await get_master_credentials()
    if not creds:
        return {"ok": False, "reason": "master_oauth_not_done",
                "hint": "L'admin doit cliquer 'Connecter le compte maitre Altiaro' sur /admin/google/master-auth"}

    started = datetime.now(timezone.utc).isoformat()
    result = {"started_at": started, "status": "running", "errors": []}
    # 1. GSC
    if force or not (existing.get("gsc") or {}).get("ok"):
        result["gsc"] = await provision_gsc_property(site, creds)
    else:
        result["gsc"] = existing["gsc"]
    # 2. GMC (skip gracieux si pas MCA)
    if force or not (existing.get("gmc") or {}).get("ok"):
        result["gmc"] = await provision_gmc_subaccount(site, creds)
    else:
        result["gmc"] = existing["gmc"]
    # 3. Ads
    if force or not (existing.get("ads") or {}).get("ok"):
        result["ads"] = await provision_ads_client(site, creds)
    else:
        result["ads"] = existing["ads"]
    # 4. GA4
    if force or not (existing.get("ga4") or {}).get("ok"):
        result["ga4"] = await provision_ga4_property(site, creds)
    else:
        result["ga4"] = existing["ga4"]
    # 5. Inject tracking dans la fiche site (toujours, idempotent)
    ga4_id = (result["ga4"] or {}).get("ga4_measurement_id")
    ads_id = (result["ads"] or {}).get("ads_customer_id")
    if ga4_id:
        result["tracking_injected"] = await inject_tracking_into_storefront(site, ga4_id, ads_id)
    # Sum status
    services_ok = [k for k in ("gsc", "gmc", "ads", "ga4") if (result.get(k) or {}).get("ok")]
    services_ko = [k for k in ("gsc", "gmc", "ads", "ga4") if not (result.get(k) or {}).get("ok")]
    result["services_ok"] = services_ok
    result["services_ko"] = services_ko
    result["status"] = "completed" if not services_ko else "partial"
    result["finished_at"] = datetime.now(timezone.utc).isoformat()
    # Persist
    await db.sites.update_one(
        {"id": site_id},
        {"$set": {"google_provisioning": result}},
    )
    return {"ok": True, **result}
