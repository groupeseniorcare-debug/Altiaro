"""
Multi-domain routing pour Altiaro.
Chaque site peut être branché sur un domaine custom (ex: luméaconfort.fr).

Flow :
1. Le Concepteur renseigne le domaine dans l'UI.
2. Il configure un CNAME chez son registrar : custom.domain → {CNAME_TARGET}
3. Il clique "Vérifier" → on résout le DNS et confirme que le CNAME pointe bien.
4. Une fois vérifié, le storefront public est accessible via https://luméaconfort.fr
   (résolution via GET /api/public/domains/resolve?host=... pour le front storefront).
"""
import logging
import os
import re
import socket
from typing import Optional
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

try:
    import dns.resolver  # type: ignore
    import dns.exception  # type: ignore
    HAS_DNS = True
except ImportError:
    HAS_DNS = False

from deps import db, get_current_user, _check_site_access, FRONTEND_URL

logger = logging.getLogger("conceptfactory.domain")

router = APIRouter()


# The CNAME target advertised to end users
_parsed = urlparse(FRONTEND_URL)
CNAME_TARGET = os.environ.get("PUBLIC_CNAME_TARGET") or (_parsed.hostname or "senior-france.preview.emergentagent.com")

# RFC 1035 hostname validation (labels 1-63 chars, total ≤253)
_HOSTNAME_RE = re.compile(
    r"^(?=.{1,253}$)(?!-)(?!.*--)[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?"
    r"(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+$"
)


class SetDomainInput(BaseModel):
    custom_domain: str


def _normalize_domain(d: str) -> str:
    d = (d or "").strip().lower()
    # Strip protocol / path if user pasted a URL
    if "://" in d:
        d = urlparse(d).hostname or ""
    d = d.rstrip("/")
    # Strip leading www. — we always verify the apex + keep www as separate alias
    return d


def _is_valid_hostname(d: str) -> bool:
    return bool(d) and bool(_HOSTNAME_RE.match(d))


def _resolve_cname(host: str) -> Optional[str]:
    """Try CNAME first, fallback on A record comparison."""
    if not HAS_DNS:
        return None
    try:
        answers = dns.resolver.resolve(host, "CNAME", lifetime=5)
        for r in answers:
            return str(r.target).rstrip(".").lower()
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.exception.DNSException):
        return None
    except Exception as e:
        logger.debug(f"CNAME lookup failed for {host}: {e}")
        return None
    return None


def _resolve_a(host: str) -> list:
    if not HAS_DNS:
        try:
            return [socket.gethostbyname(host)]
        except OSError:
            return []
    try:
        answers = dns.resolver.resolve(host, "A", lifetime=5)
        return [str(r.address) for r in answers]
    except Exception:
        return []


@router.get("/sites/{site_id}/domain")
async def get_domain_status(site_id: str, user: dict = Depends(get_current_user)):
    site = await _check_site_access(site_id, user)
    return {
        "custom_domain": site.get("custom_domain", "") or site.get("domain", ""),
        "custom_domain_verified": bool(site.get("custom_domain_verified")),
        "custom_domain_verified_at": site.get("custom_domain_verified_at"),
        "cname_target": CNAME_TARGET,
        "instructions": {
            "type": "CNAME",
            "name": "@ (ou www selon registrar)",
            "value": CNAME_TARGET,
            "ttl": 3600,
        },
    }


@router.post("/sites/{site_id}/domain")
async def set_domain(
    site_id: str,
    data: SetDomainInput,
    user: dict = Depends(get_current_user),
):
    await _check_site_access(site_id, user)
    domain = _normalize_domain(data.custom_domain)
    if not _is_valid_hostname(domain):
        raise HTTPException(
            status_code=400,
            detail="Nom de domaine invalide. Ex : maboutique.fr"
        )

    # Enforce uniqueness across all sites
    existing = await db.sites.find_one(
        {"custom_domain": domain, "id": {"$ne": site_id}},
        {"_id": 0, "id": 1}
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail="Ce domaine est déjà utilisé par un autre site."
        )

    await db.sites.update_one(
        {"id": site_id},
        {"$set": {
            "custom_domain": domain,
            "custom_domain_verified": False,
            "custom_domain_verified_at": None,
        }}
    )
    return await get_domain_status(site_id, user)


@router.delete("/sites/{site_id}/domain")
async def clear_domain(site_id: str, user: dict = Depends(get_current_user)):
    await _check_site_access(site_id, user)
    await db.sites.update_one(
        {"id": site_id},
        {"$unset": {
            "custom_domain": "",
            "custom_domain_verified": "",
            "custom_domain_verified_at": "",
        }}
    )
    return {"ok": True}


@router.post("/sites/{site_id}/domain/verify")
async def verify_domain(site_id: str, user: dict = Depends(get_current_user)):
    site = await _check_site_access(site_id, user)
    domain = site.get("custom_domain") or site.get("domain")
    if not domain:
        raise HTTPException(status_code=400, detail="Aucun domaine à vérifier.")
    domain = _normalize_domain(domain)
    if not _is_valid_hostname(domain):
        raise HTTPException(status_code=400, detail=f"Domaine invalide : {domain}")

    cname = _resolve_cname(domain)
    target_norm = CNAME_TARGET.rstrip(".").lower()

    verified = False
    reason = ""
    if cname:
        if cname == target_norm or cname.endswith("." + target_norm) or target_norm.endswith("." + cname):
            verified = True
            reason = f"CNAME pointe vers {cname}"
        else:
            reason = f"CNAME trouvé ({cname}) mais ne correspond pas à la cible attendue ({target_norm})."
    else:
        # Fallback : compare A records — if both resolve to the same IPs, treat as OK
        user_ips = set(_resolve_a(domain))
        target_ips = set(_resolve_a(target_norm))
        if user_ips and target_ips and user_ips & target_ips:
            verified = True
            reason = f"A records convergent ({', '.join(user_ips & target_ips)})"
        else:
            reason = "Aucun CNAME vers la cible Altiaro n'a été détecté."

    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    await db.sites.update_one(
        {"id": site_id},
        {"$set": {
            "custom_domain_verified": verified,
            "custom_domain_verified_at": now if verified else None,
            "custom_domain_last_check_at": now,
            "custom_domain_last_check_reason": reason,
        }}
    )
    return {
        "domain": domain,
        "verified": verified,
        "reason": reason,
        "cname_found": cname,
        "cname_target": target_norm,
        "checked_at": now,
    }


# -------------------------------------------------------------------- #
# Public resolver : frontend storefront calls this to know which site_id
# to load when the user visits https://custom.domain/
# -------------------------------------------------------------------- #
@router.get("/public/domains/resolve")
async def public_resolve_domain(host: str):
    host = _normalize_domain(host)
    if not host:
        raise HTTPException(status_code=400, detail="Host manquant.")
    site = await db.sites.find_one(
        {"custom_domain": host, "custom_domain_verified": True},
        {"_id": 0, "id": 1, "name": 1}
    )
    if not site:
        raise HTTPException(status_code=404, detail="Aucun site vérifié pour ce domaine.")
    return {"site_id": site["id"], "site_name": site["name"], "host": host}
