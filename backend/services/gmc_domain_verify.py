"""GMC Domain Verification — Automatique : TXT OVH + Google Site Verification.

Flow :
  1. Demande à Google le `verification_token` pour `https://{custom_domain}`.
  2. Pose le record TXT `google-site-verification=<token>` sur la zone OVH
     du domaine via `services/ovh_dns.upsert_record`.
  3. Wait DNS propagation (poll 60s × 10min).
  4. Trigger Google verification.insert.
  5. Persiste `site.gmc_domain_verified=true` + dates.
Échec gracieux — chaque étape best-effort, retourne le statut détaillé.
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from deps import db

logger = logging.getLogger("altiaro.gmc_domain_verify")


async def _get_verification_token(creds, domain: str) -> Optional[str]:
    """Demande à Google le TXT verification token pour ce domaine."""
    try:
        from googleapiclient.discovery import build
        svc = build("siteVerification", "v1", credentials=creds, cache_discovery=False)
        body = {
            "site": {"identifier": f"https://{domain}/", "type": "SITE"},
            "verificationMethod": "DNS_TXT",
        }
        resp = await asyncio.to_thread(
            svc.webResource().getToken(body=body).execute,
        )
        return resp.get("token")
    except Exception as e:
        logger.warning(f"[gmc-verify] getToken failed for {domain}: {str(e)[:200]}")
        return None


async def _put_txt_record(domain: str, value: str) -> Dict[str, Any]:
    """Pose un TXT record sur la zone OVH du domaine."""
    try:
        from services import ovh_dns
        # Upsert TXT @ <zone> avec value = google-site-verification=<token>
        return await ovh_dns.upsert_txt_record(
            zone=domain,
            subdomain="",  # apex
            target=f"google-site-verification={value}",
        )
    except AttributeError:
        # Fallback : appel direct si la fonction spécifique n'existe pas
        try:
            from services.ovh_dns import _ovh_post  # type: ignore
            return {"ok": False, "reason": "upsert_txt_record_not_implemented_in_ovh_service"}
        except Exception as e:
            return {"ok": False, "error": str(e)[:200]}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}


async def _trigger_verification(creds, domain: str) -> Dict[str, Any]:
    try:
        from googleapiclient.discovery import build
        svc = build("siteVerification", "v1", credentials=creds, cache_discovery=False)
        body = {
            "site": {"identifier": f"https://{domain}/", "type": "SITE"},
        }
        resp = await asyncio.to_thread(
            svc.webResource().insert(verificationMethod="DNS_TXT", body=body).execute,
        )
        return {"ok": True, "id": resp.get("id")}
    except Exception as e:
        return {"ok": False, "error": str(e)[:300]}


async def verify_domain_for_site(site_id: str) -> Dict[str, Any]:
    """Pipeline complet end-to-end pour un site."""
    out: Dict[str, Any] = {"site_id": site_id, "started_at": datetime.now(timezone.utc).isoformat()}
    site = await db.sites.find_one({"id": site_id}, {"_id": 0, "id": 1, "custom_domain": 1, "custom_domain_verified": 1})
    if not site:
        return {**out, "ok": False, "reason": "site_not_found"}
    domain = site.get("custom_domain")
    if not domain or not site.get("custom_domain_verified"):
        return {**out, "ok": False, "reason": "domain_not_yet_provisioned"}

    from services.gmc_onboarding import _resolve_master_credentials
    creds = await _resolve_master_credentials()
    if not creds:
        return {**out, "ok": False, "reason": "no_master_credentials"}

    # 1) Get token
    token = await _get_verification_token(creds, domain)
    if not token:
        return {**out, "ok": False, "reason": "google_token_failed"}
    out["verification_token"] = token[:30] + "…"

    # 2) Put TXT on OVH
    txt_result = await _put_txt_record(domain, token)
    out["ovh_txt"] = txt_result
    if not txt_result.get("ok"):
        return {**out, "ok": False, "reason": "ovh_txt_failed"}

    # 3) Wait propagation (poll 30s × 10 = 5min max for MVP)
    out["propagation_wait"] = "60s×5 = 5min max"
    await asyncio.sleep(60)

    # 4) Trigger verification
    for attempt in range(5):
        res = await _trigger_verification(creds, domain)
        if res.get("ok"):
            out["verification"] = {"ok": True, "attempts": attempt + 1}
            await db.sites.update_one(
                {"id": site_id},
                {"$set": {
                    "gmc_domain_verified": True,
                    "gmc_domain_verified_at": datetime.now(timezone.utc).isoformat(),
                }},
            )
            return {**out, "ok": True}
        out[f"verification_attempt_{attempt+1}"] = res
        if attempt < 4:
            await asyncio.sleep(60)

    return {**out, "ok": False, "reason": "verification_failed_after_5_attempts"}
