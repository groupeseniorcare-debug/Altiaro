"""URGENT 2/3 — Découverte automatique des comptes Google maitres + vérification de domaine.

Toutes les fonctions utilisent les credentials master obtenues via
`routes.google_master.get_master_credentials()` (refresh_token long-lived).
Elles sont best-effort : retournent un dict avec `ok` + payload, sans crash.
"""
from __future__ import annotations
import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger("altiaro.google_master_discovery")


def _build(service: str, version: str, creds):
    from googleapiclient.discovery import build
    return build(service, version, credentials=creds, cache_discovery=False)


async def discover_ga4_master_account(creds) -> dict:
    """Analytics Admin API — accountSummaries.list :
    retourne le compte master GA4 (1 si unique, sinon le 1er match "Altiaro").
    """
    if not creds:
        return {"ok": False, "reason": "no_master_credentials"}
    try:
        svc = _build("analyticsadmin", "v1beta", creds)
        resp = await asyncio.to_thread(svc.accountSummaries().list().execute)
        accounts = resp.get("accountSummaries") or []
        if not accounts:
            return {"ok": False, "reason": "no_accounts_visible"}
        # Prefer name containing 'altiaro', else first
        chosen = next(
            (a for a in accounts if "altiaro" in (a.get("displayName") or "").lower()),
            accounts[0],
        )
        account_id = (chosen.get("account") or "").split("/")[-1]  # "accounts/12345678" → 12345678
        return {
            "ok": True,
            "account_id": account_id,
            "display_name": chosen.get("displayName"),
            "property_summaries": [
                {
                    "property_id": (p.get("property") or "").split("/")[-1],
                    "display_name": p.get("displayName"),
                }
                for p in (chosen.get("propertySummaries") or [])
            ],
            "all_accounts_count": len(accounts),
        }
    except Exception as e:
        logger.exception("[ga4_discovery] failed")
        return {"ok": False, "reason": "exception", "error": str(e)[:300]}


async def discover_merchant_mca(creds) -> dict:
    """Content for Shopping API — accounts.authinfo + accounts.list pour identifier le MCA.

    Retourne `{ok, is_mca, account_id, total_subaccounts}` ou `{ok:False, reason}`.
    """
    if not creds:
        return {"ok": False, "reason": "no_master_credentials"}
    try:
        svc = _build("content", "v2.1", creds)
        info = await asyncio.to_thread(svc.accounts().authinfo().execute)
        ids = info.get("accountIdentifiers") or []
        if not ids:
            return {"ok": False, "reason": "no_merchant_accounts"}
        # MCA = aggregator avec children. authinfo renvoie merchantId pour aggregator,
        # ou aggregatorId quand accountId est lui-même un sub-account.
        mca_id = None
        simple_id = None
        for it in ids:
            if it.get("merchantId") and it.get("aggregatorId") is None:
                # Probablement un MCA standalone OU un compte simple
                mca_id = it["merchantId"]
            elif it.get("aggregatorId"):
                mca_id = it["aggregatorId"]
            if it.get("merchantId"):
                simple_id = it["merchantId"]
        target = mca_id or simple_id
        # Try listing sub-accounts to confirm MCA status
        is_mca = False
        sub_count = 0
        try:
            sub = await asyncio.to_thread(
                svc.accounts().list(merchantId=target, maxResults=50).execute,
            )
            sub_count = len(sub.get("resources") or [])
            is_mca = sub_count >= 1
        except Exception as e:
            logger.info(f"[gmc_discovery] accounts.list returned {str(e)[:120]} (probably simple account)")
            is_mca = False
        warning = None
        if not is_mca:
            warning = (
                "Compte Merchant simple (non-MCA) détecté. La création "
                "automatique de sub-accounts est impossible tant que le "
                "compte n'est pas converti en MCA via Google Support."
            )
        return {
            "ok": True,
            "account_id": target,
            "is_mca": is_mca,
            "total_subaccounts": sub_count,
            "warning": warning,
            "identifiers_count": len(ids),
        }
    except Exception as e:
        logger.exception("[gmc_discovery] failed")
        return {"ok": False, "reason": "exception", "error": str(e)[:300]}


async def discover_ads_mcc(creds) -> dict:
    """Confirmation simple : le MCC ID est en .env ; on retourne juste ce qu'on a.

    Pour un check live, on pourrait appeler `customers.listAccessibleCustomers`
    via la lib google-ads, mais ça nécessite le developer_token. On suppose
    que l'utilisateur a confirmé manuellement (Standard Access).
    """
    mcc = os.environ.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID") or ""
    if not mcc:
        return {"ok": False, "reason": "GOOGLE_ADS_LOGIN_CUSTOMER_ID missing in env"}
    return {"ok": True, "mcc_id": mcc, "mcc_id_human": f"{mcc[:3]}-{mcc[3:6]}-{mcc[6:]}"}


async def verify_altiaro_master_domain(creds, domain: str = "altiaro.com") -> dict:
    """Site Verification API + Search Console API.

    1. webResource.insert(verificationMethod=DNS_TXT)
    2. webmasters.sites.add(siteUrl='sc-domain:altiaro.com') (best-effort si Site Verification a réussi)
    """
    if not creds:
        return {"ok": False, "reason": "no_master_credentials"}
    out = {"site_verification": None, "gsc_added": None}
    # 1. Site Verification
    try:
        sv = _build("siteVerification", "v1", creds)
        body = {"site": {"identifier": domain, "type": "INET_DOMAIN"}}
        resp = await asyncio.to_thread(
            sv.webResource().insert(verificationMethod="DNS_TXT", body=body).execute,
        )
        out["site_verification"] = {"ok": True, "id": resp.get("id"), "owners": resp.get("owners")}
    except Exception as e:
        msg = str(e)[:400]
        out["site_verification"] = {"ok": False, "error": msg}
        logger.warning(f"[verify] siteVerification failed : {msg}")
    # 2. GSC sites.add (sc-domain) — ne fonctionne que si la verification est réussie
    try:
        wm = _build("searchconsole", "v1", creds)
        await asyncio.to_thread(wm.sites().add(siteUrl=f"sc-domain:{domain}").execute)
        out["gsc_added"] = {"ok": True, "site_url": f"sc-domain:{domain}"}
    except Exception as e:
        out["gsc_added"] = {"ok": False, "error": str(e)[:400]}
    return out


async def discover_all(creds) -> dict:
    """Helper : exécute les 3 découvertes en parallèle et renvoie un dict consolidé."""
    ga4, gmc, ads = await asyncio.gather(
        discover_ga4_master_account(creds),
        discover_merchant_mca(creds),
        discover_ads_mcc(creds),
    )
    return {"ga4": ga4, "gmc": gmc, "ads": ads,
            "discovered_at": datetime.now(timezone.utc).isoformat()}
