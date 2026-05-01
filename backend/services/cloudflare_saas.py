"""
Cloudflare for SaaS — Custom Hostnames provisioning.

Architecture :

    Concepteur tape mon-shop.fr
        ↓ DNS CNAME (auto-configuré par Altiaro via OVH API à l'étape 6)
    mon-shop.fr  →  altiaro.com  (zone Cloudflare gérée par Altiaro)
        ↓
    Cloudflare termine TLS (cert émis automatiquement via Custom Hostnames)
        ↓ origin_request avec header `Host: mon-shop.fr` préservé
    Pod Emergent (notre app)
        ↓ custom_domain_middleware lit Host (ou X-Forwarded-Host)
        ↓ réécrit /  → /shop/{site_id}/
    Storefront du concepteur

Avantages :
  - 100 % automatique : 1 appel API et tout marche
  - Free tier : 100 hostnames gratuits, parfait pour démarrer
  - SSL Let's Encrypt / Cloudflare auto, illimité
  - Anti-DDoS, CDN, observability inclus

Limitation honnête identifiée :
  - Si l'origin Altiaro (le pod Emergent) est elle-même derrière Cloudflare
    (ce qui semble être le cas via le DNS d'Emergent), on a une chaîne
    Cloudflare→Cloudflare. C'est SUPPORTÉ par CF for SaaS via un "custom
    origin server" ou simplement en ajoutant un Page Rule. La doc Cloudflare
    couvre ce cas (Saas → Saas).
  - Dans le pire cas, on ajoute un domaine racine dédié `altiaro.shop` chez
    OVH, géré directement par Cloudflare (sans Emergent au milieu), et on
    forward de cette zone vers le pod via un Worker ou un CNAME tunnel.

Variables d'environnement :
    CLOUDFLARE_API_TOKEN          Token avec permissions :
                                    - Zone:SSL and Certificates:Edit
                                    - Zone:Zone:Read
                                    - Zone:Custom Hostnames:Edit
    CLOUDFLARE_ZONE_ID            ID de la zone Cloudflare où sont les hostnames
                                  custom (ex: la zone d'altiaro.com ou altiaro.shop)
    CLOUDFLARE_FALLBACK_ORIGIN    Hostname de l'origin (pod Emergent) où CF
                                  forwardera les requêtes (default: altiaro.com)

Référence : https://developers.cloudflare.com/cloudflare-for-platforms/cloudflare-for-saas/api/
"""
from __future__ import annotations

import logging
import os
from typing import Optional

import httpx

logger = logging.getLogger("altiaro.cloudflare_saas")

CF_API_BASE = "https://api.cloudflare.com/client/v4"


def _cfg() -> dict:
    return {
        "token": os.environ.get("CLOUDFLARE_API_TOKEN", "").strip(),
        "zone_id": os.environ.get("CLOUDFLARE_ZONE_ID", "").strip(),
        "fallback_origin": os.environ.get(
            "CLOUDFLARE_FALLBACK_ORIGIN", "altiaro.com"
        ).strip(),
    }


def is_configured() -> bool:
    c = _cfg()
    return bool(c["token"] and c["zone_id"])


def _headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


async def add_custom_hostname(
    hostname: str,
    *,
    site_id: Optional[str] = None,
    ssl_method: str = "http",
) -> dict:
    """Crée (ou met à jour) un Custom Hostname Cloudflare.

    Args:
        hostname: nom de domaine du concepteur (ex: "mon-shop.fr")
        site_id: stocké dans `custom_metadata` pour traçabilité.
        ssl_method: "http" (HTTP-01 challenge), "txt" (DNS-01) ou "email".

    Returns:
        {"ok": bool, "id": str, "status": str, "ssl_status": str, ...}
    """
    hostname = (hostname or "").strip().lower()
    if not hostname:
        return {"ok": False, "error": "empty_hostname"}
    cfg = _cfg()
    if not is_configured():
        return {
            "ok": False,
            "error": "cloudflare_not_configured",
            "missing": [k for k in ("CLOUDFLARE_API_TOKEN", "CLOUDFLARE_ZONE_ID")
                        if not os.environ.get(k)],
        }

    payload = {
        "hostname": hostname,
        "ssl": {
            "method": ssl_method,
            "type": "dv",
            "settings": {
                "min_tls_version": "1.2",
                "http2": "on",
            },
        },
    }
    if site_id:
        payload["custom_metadata"] = {"altiaro_site_id": site_id}

    url = f"{CF_API_BASE}/zones/{cfg['zone_id']}/custom_hostnames"
    async with httpx.AsyncClient(timeout=15) as cli:
        try:
            r = await cli.post(url, headers=_headers(cfg["token"]), json=payload)
            data = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
            if r.status_code in (200, 201) and data.get("success"):
                res = data.get("result", {})
                logger.info(
                    f"[cf-saas] {hostname} created id={res.get('id')} "
                    f"status={res.get('status')} ssl={res.get('ssl', {}).get('status')}"
                )
                return {
                    "ok": True,
                    "id": res.get("id"),
                    "status": res.get("status"),
                    "ssl_status": (res.get("ssl") or {}).get("status"),
                    "verification_errors": (res.get("ssl") or {}).get("validation_errors", []),
                    "verification_records": (res.get("ssl") or {}).get("validation_records", []),
                }
            # Détection erreur "déjà existe" → on récupère l'ID via list
            errors = data.get("errors") or []
            if any(e.get("code") == 1406 for e in errors):
                # Hostname already exists, fetch it
                existing = await _find_hostname_by_name(hostname)
                if existing:
                    return {
                        "ok": True,
                        "id": existing.get("id"),
                        "status": existing.get("status"),
                        "ssl_status": (existing.get("ssl") or {}).get("status"),
                        "already_existed": True,
                    }
            logger.warning(f"[cf-saas] {hostname} create failed: {r.status_code} {r.text[:300]}")
            return {
                "ok": False,
                "error": "cloudflare_api_error",
                "http": r.status_code,
                "errors": errors,
                "raw": r.text[:300],
            }
        except httpx.HTTPError as e:
            logger.error(f"[cf-saas] {hostname} HTTP error: {e}")
            return {"ok": False, "error": "http_error", "detail": str(e)[:200]}


async def _find_hostname_by_name(hostname: str) -> Optional[dict]:
    cfg = _cfg()
    url = f"{CF_API_BASE}/zones/{cfg['zone_id']}/custom_hostnames"
    async with httpx.AsyncClient(timeout=10) as cli:
        r = await cli.get(url, headers=_headers(cfg["token"]),
                          params={"hostname": hostname})
        if r.status_code == 200:
            data = r.json()
            for item in data.get("result") or []:
                if item.get("hostname", "").lower() == hostname.lower():
                    return item
    return None


async def get_hostname_status(hostname: str) -> dict:
    """Lit le statut d'un Custom Hostname (active, pending_validation, etc.)."""
    if not is_configured():
        return {"ok": False, "error": "cloudflare_not_configured"}
    item = await _find_hostname_by_name(hostname)
    if not item:
        return {"ok": False, "error": "not_found", "hostname": hostname}
    return {
        "ok": True,
        "id": item.get("id"),
        "status": item.get("status"),
        "ssl_status": (item.get("ssl") or {}).get("status"),
        "ssl_active": (item.get("ssl") or {}).get("status") == "active",
        "verification_errors": (item.get("ssl") or {}).get("validation_errors", []),
    }


async def remove_custom_hostname(hostname: str) -> dict:
    if not is_configured():
        return {"ok": False, "error": "cloudflare_not_configured"}
    item = await _find_hostname_by_name(hostname)
    if not item:
        return {"ok": True, "already_absent": True}
    cfg = _cfg()
    url = f"{CF_API_BASE}/zones/{cfg['zone_id']}/custom_hostnames/{item['id']}"
    async with httpx.AsyncClient(timeout=10) as cli:
        r = await cli.delete(url, headers=_headers(cfg["token"]))
        return {"ok": r.status_code in (200, 204), "http": r.status_code}


async def verify_ssl_ready(hostname: str) -> bool:
    """Helper : True si le SSL est `active` côté Cloudflare."""
    s = await get_hostname_status(hostname)
    return bool(s.get("ssl_active"))
