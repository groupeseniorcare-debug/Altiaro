"""
Helper OVH DNS pour custom domains Altiaro.

Diffère de `routes/ovh_domains.py` qui se concentre sur l'achat OVH +
post-achat. Ici on a juste besoin de :

- Lister les records DNS d'une zone OVH existante
- Supprimer les records A/AAAA/CNAME conflictuels pour un sous-domaine donné
- Créer un record A
- Forcer le refresh de la zone

C'est utilisé par le flow Approximated : on doit pointer le domaine vers
les IPs du cluster Approximated, en remplaçant proprement les anciens
records (Cloudflare ou direct).
"""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Dict, List, Optional

import ovh  # type: ignore

logger = logging.getLogger("conceptfactory.ovh_dns")

OVH_APP_KEY = os.environ.get("OVH_APP_KEY", "").strip()
OVH_APP_SECRET = os.environ.get("OVH_APP_SECRET", "").strip()
OVH_CONSUMER_KEY = os.environ.get("OVH_CONSUMER_KEY", "").strip()
OVH_ENDPOINT = os.environ.get("OVH_ENDPOINT", "ovh-eu").strip() or "ovh-eu"


def is_configured() -> bool:
    return bool(OVH_APP_KEY and OVH_APP_SECRET and OVH_CONSUMER_KEY)


def _client() -> ovh.Client:
    if not is_configured():
        raise RuntimeError("OVH credentials missing in env")
    return ovh.Client(
        endpoint=OVH_ENDPOINT,
        application_key=OVH_APP_KEY,
        application_secret=OVH_APP_SECRET,
        consumer_key=OVH_CONSUMER_KEY,
    )


async def list_records(domain: str) -> List[Dict[str, Any]]:
    """Return all records for a zone with their full payload."""
    client = _client()
    ids = await asyncio.to_thread(client.get, f"/domain/zone/{domain}/record")
    out: List[Dict[str, Any]] = []
    for rid in ids:
        try:
            r = await asyncio.to_thread(
                client.get, f"/domain/zone/{domain}/record/{rid}"
            )
            out.append(r)
        except Exception as e:  # pragma: no cover
            logger.warning(f"OVH fetch record {rid} failed: {e}")
    return out


async def delete_records_for_subdomain(
    domain: str,
    sub_domain: str,
    field_types: Optional[List[str]] = None,
) -> List[int]:
    """Delete every record (matching field_types) for a given subdomain."""
    client = _client()
    field_types = field_types or ["A", "AAAA", "CNAME"]
    deleted: List[int] = []
    records = await list_records(domain)
    for r in records:
        if (r.get("subDomain") or "") != (sub_domain or ""):
            continue
        if r.get("fieldType") not in field_types:
            continue
        try:
            await asyncio.to_thread(
                client.delete, f"/domain/zone/{domain}/record/{r['id']}"
            )
            deleted.append(int(r["id"]))
        except Exception as e:  # pragma: no cover
            logger.warning(f"OVH delete record {r.get('id')} failed: {e}")
    return deleted


async def create_a_record(
    domain: str, sub_domain: str, target_ip: str, ttl: int = 300
) -> Dict[str, Any]:
    """Create a single A record."""
    client = _client()
    return await asyncio.to_thread(
        client.post,
        f"/domain/zone/{domain}/record",
        fieldType="A",
        subDomain=sub_domain,
        target=target_ip,
        ttl=ttl,
    )


async def refresh_zone(domain: str) -> None:
    client = _client()
    await asyncio.to_thread(client.post, f"/domain/zone/{domain}/refresh")


async def replace_with_a_records(
    domain: str,
    target_ips: List[str],
    *,
    include_www: bool = True,
    ttl: int = 300,
) -> Dict[str, Any]:
    """High-level helper used by the Approximated provisioning flow.

    1. Delete any existing A / AAAA / CNAME records for `@` and `www`
    2. Create an A record per target IP for `@` (and `www` if include_www)
    3. Refresh the zone

    Returns a structured report.
    """
    if not target_ips:
        raise ValueError("target_ips empty")
    deleted_apex = await delete_records_for_subdomain(domain, "")
    deleted_www: List[int] = []
    if include_www:
        deleted_www = await delete_records_for_subdomain(domain, "www")
    created_apex: List[Dict[str, Any]] = []
    created_www: List[Dict[str, Any]] = []
    errors: List[str] = []
    for ip in target_ips:
        try:
            created_apex.append(await create_a_record(domain, "", ip, ttl=ttl))
        except Exception as e:
            errors.append(f"apex {ip}: {e}")
        if include_www:
            try:
                created_www.append(await create_a_record(domain, "www", ip, ttl=ttl))
            except Exception as e:
                errors.append(f"www {ip}: {e}")
    try:
        await refresh_zone(domain)
        refreshed = True
    except Exception as e:
        refreshed = False
        errors.append(f"refresh: {e}")
    return {
        "ok": not errors,
        "domain": domain,
        "target_ips": list(target_ips),
        "deleted_records_apex": deleted_apex,
        "deleted_records_www": deleted_www,
        "created_records_apex": [r.get("id") for r in created_apex],
        "created_records_www": [r.get("id") for r in created_www],
        "refreshed": refreshed,
        "errors": errors,
    }
