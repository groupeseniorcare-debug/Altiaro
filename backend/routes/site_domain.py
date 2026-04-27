"""
Multi-domain routing pour Altiaro.
Chaque site peut être branché sur un domaine custom (ex: luméaconfort.fr).

Flow :
1. Le Concepteur renseigne le domaine dans l'UI.
2. Il configure un CNAME chez son registrar : custom.domain → {CNAME_TARGET}
3. Il clique "Vérifier" → on résout le DNS et confirme que le CNAME pointe bien.
4. Une fois vérifié, le storefront public est accessible via https://luméaconfort.fr
   (résolution via GET /api/public/domains/resolve?host=... pour le front storefront).

Phase 1 (2026-04-27) — Workaround "manual purchase link" :
Quand le mandate Mollie standard d'un concepteur est cassé (recurring KO), on
expose un lien Mollie **one-shot** (sequenceType=oneoff) au prix OVH **sans
markup plateforme**. Le webhook Mollie existant (`mollie_webhook`) détecte le
metadata `type=domain_purchase` et déclenche automatiquement l'achat OVH +
le cron auto-DNS prend le relais.
"""
import logging
import os
import re
import socket
import uuid
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException, Depends, Request
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
# Phase 1 — Manual purchase link (Mollie one-shot, OVH price, no markup)
# -------------------------------------------------------------------- #
class ManualPurchaseInput(BaseModel):
    domain: Optional[str] = None  # if absent, takes the site's pending_payment domain


@router.post(
    "/sites/{site_id}/domain/manual-purchase-link",
    tags=["domain-manual-purchase"],
    summary="Génère un lien Mollie one-shot (sans markup) pour débloquer l'achat d'un domaine",
)
async def create_manual_domain_purchase_link(
    site_id: str,
    data: ManualPurchaseInput,
    request: Request,
    user: dict = Depends(get_current_user),
):
    """Workaround manuel pour acheter un domaine quand le mandate Mollie
    standard est KO sur le concepteur.

    - Crée un paiement Mollie **one-shot** (`sequenceType=oneoff`, pas de mandate)
      au **prix OVH brut** (markup plateforme = 0, exceptionnel).
    - Réutilise le webhook `mollie_webhook` existant (metadata
      `type=domain_purchase`) qui déclenche automatiquement l'achat OVH +
      cron DNS auto /5min.
    - Si un record `domains` `pending_payment` existe déjà pour ce couple
      (site_id, domain), on lui rattache le nouveau paiement.

    Body :
    - `domain` (optionnel) : si absent, prend le domaine `pending_payment` du
      site. Format `altea.com`, sans schéma ni path.

    Retour :
    ```json
    {
      "ok": true,
      "domain": "altea.com",
      "amount": "7.99",
      "currency": "EUR",
      "checkout_url": "https://www.mollie.com/checkout/...",
      "mollie_payment_id": "tr_xxx",
      "expires_at": "...",
      "domain_record_id": "dom-altea-com-xxxxxxxx",
      "manual": true
    }
    ```
    """
    await _check_site_access(site_id, user)

    # Local imports to avoid circular deps at module load
    from routes.ovh_domains import (
        _normalise_domain as _ovh_normalise,
        _client as _ovh_client,
        _tld_of,
        ALLOWED_TLDS,
    )
    from routes.payments import _get_client as _mollie_client

    # 1. Resolve target domain
    domain_input = (data.domain or "").strip() if data and data.domain else ""
    if not domain_input:
        existing = await db.domains.find_one(
            {"site_id": site_id, "status": "pending_payment"}, {"_id": 0}
        )
        if not existing:
            raise HTTPException(
                status_code=404,
                detail="Aucun domaine en attente de paiement pour ce site. "
                       "Renseigne `domain` dans le body.",
            )
        domain = existing["domain"]
    else:
        domain = _ovh_normalise(domain_input)
        if "." not in domain:
            raise HTTPException(400, "Domaine invalide. Ex : altea.com")

    tld = _tld_of(domain)
    if tld not in ALLOWED_TLDS:
        raise HTTPException(400, f"Extension non supportée : {tld}")

    # 2. Re-fetch OVH price live
    client = _ovh_client()
    import asyncio as _aio

    try:
        cart = await _aio.to_thread(
            client.post, "/order/cart",
            ovhSubsidiary="FR", description=f"cf-manual-{site_id[:8]}",
        )
        cart_id = cart["cartId"]
        items = await _aio.to_thread(
            client.post, f"/order/cart/{cart_id}/domain", domain=domain,
        )
        item = items if isinstance(items, dict) else (items[0] if items else {})
        ovh_price_ttc = 0.0
        for p in item.get("prices", []):
            if p.get("label") == "TOTAL":
                ovh_price_ttc = float(p.get("price", {}).get("value") or 0)
                break
        try:
            await _aio.to_thread(client.delete, f"/order/cart/{cart_id}")
        except Exception:
            pass
    except Exception as e:
        logger.exception("OVH manual price check failed")
        raise HTTPException(502, f"OVH : {str(e)[:200]}")

    if ovh_price_ttc <= 0:
        raise HTTPException(400, "Domaine indisponible ou non cotable par OVH.")

    manual_price = round(ovh_price_ttc, 2)  # NO markup (exceptional, manual flow)

    # 3. Get or create domain record
    now_iso = datetime.now(timezone.utc).isoformat()
    record = await db.domains.find_one(
        {"domain": domain, "site_id": site_id}, {"_id": 0}
    )
    if record:
        record_id = record["id"]
        if record.get("status") in ("purchased", "dns_configured", "active"):
            raise HTTPException(400, "Ce domaine est déjà acheté.")
    else:
        record_id = f"dom-{domain.replace('.', '-')}-{uuid.uuid4().hex[:8]}"
        await db.domains.insert_one({
            "id": record_id,
            "domain": domain,
            "tld": tld,
            "site_id": site_id,
            "purchased_by": user.get("id"),
            "purchased_at": now_iso,
            "ovh_price_ttc_eur": ovh_price_ttc,
            "markup_eur": 0,
            "platform_price_eur": manual_price,
            "status": "pending_payment",
            "manual_purchase": True,
            "created_at": now_iso,
            "updated_at": now_iso,
        })

    # 4. Create Mollie one-shot payment
    mollie, mode = _mollie_client()

    redirect_url = f"{FRONTEND_URL}/sites/{site_id}/domains?domain_payment=1&domain={domain}"
    webhook_url = f"{FRONTEND_URL}/api/webhooks/mollie"

    try:
        payment = mollie.payments.create({
            "amount": {"currency": "EUR", "value": f"{manual_price:.2f}"},
            "description": f"Domaine {domain} (achat manuel)",
            "redirectUrl": redirect_url,
            "webhookUrl": webhook_url,
            "sequenceType": "oneoff",  # explicit : NO mandate, NO subscription
            "metadata": {
                "type": "domain_purchase",  # routes to complete_domain_purchase()
                "manual": True,
                "domain": domain,
                "domain_record_id": record_id,
                "site_id": site_id,
                "user_id": user.get("id"),
            },
            "locale": "fr_FR",
        })
    except Exception as e:
        logger.exception("Mollie create manual one-shot payment failed")
        raise HTTPException(502, f"Mollie : {str(e)[:200]}")

    await db.domains.update_one(
        {"id": record_id},
        {"$set": {
            "mollie_payment_id": payment.id,
            "mollie_checkout_url": payment.checkout_url,
            "mollie_mode": mode,
            "ovh_price_ttc_eur": ovh_price_ttc,
            "platform_price_eur": manual_price,
            "markup_eur": 0,
            "manual_purchase": True,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }},
    )

    # Best-effort expires_at extraction (mollie SDK exposes attrs lazily)
    expires_at = (
        getattr(payment, "expires_at", None)
        or getattr(payment, "expiresAt", None)
        or None
    )

    logger.info(
        f"[manual-purchase] site={site_id[:8]} domain={domain} "
        f"price={manual_price}€ payment={payment.id} mode={mode}"
    )

    return {
        "ok": True,
        "domain": domain,
        "amount": f"{manual_price:.2f}",
        "currency": "EUR",
        "checkout_url": payment.checkout_url,
        "mollie_payment_id": payment.id,
        "expires_at": expires_at,
        "domain_record_id": record_id,
        "manual": True,
        "mode": mode,
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
