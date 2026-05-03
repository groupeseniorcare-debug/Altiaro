"""
Multi-domain routing pour Altiaro — Approximated edition (2026-05-01).

Architecture custom domain :

```
Concepteur saisit `mon-shop.fr` (étape 6)
      ↓
POST /api/sites/{id}/domain/verify   (hook étape 6)
      ↓
1. Approximated.create_vhost(mon-shop.fr → commerce-builder-21.preview.emergentagent.com:443)
2. ovh_dns.replace_with_a_records(mon-shop.fr, [213.188.213.253])  (apex + www)
3. ovh_dns.refresh_zone(mon-shop.fr)
4. Background poller (60s × 15 min) → quand apx_hit && is_resolving && has_ssl :
       sites.custom_domain_verified = true
       steps.domain.status = "completed"
      ↓
Visiteur ouvre https://mon-shop.fr → Approximated proxy (SSL géré)
                                  → pod Emergent (Host header conservé via X-Forwarded-Host)
                                  → custom_domain_middleware route /shop/{site_id}/
```

Migration :
- `/admin/sites/{id}/domain/approximated-provision` (relance manuelle)
- `/admin/sites/{id}/domain/approximated-status`    (debug)

Les endpoints legacy `cf-*` (Cloudflare for SaaS) et `proxy-*` (Caddy) ont été
retirés en 2026-05-01. Voir CHANGELOG.

Phase 1 (workaround Mollie one-shot) — voir POST /sites/{id}/domain/manual-purchase-link.
"""
from __future__ import annotations

import asyncio
import logging
import os
import re
import socket
import uuid
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

try:
    import dns.exception  # type: ignore
    import dns.resolver  # type: ignore

    HAS_DNS = True
except ImportError:
    HAS_DNS = False

from deps import FRONTEND_URL, _check_site_access, db, get_current_user
from services import approximated_provisioning as apx
from services import ovh_dns

logger = logging.getLogger("conceptfactory.domain")

router = APIRouter()


# Legacy CNAME target advertised via /sites/:id/domain (rétrocompat UI). The
# real provisioning now goes through A records + Approximated cluster IPs.
_parsed = urlparse(FRONTEND_URL)
CNAME_TARGET = os.environ.get("PUBLIC_CNAME_TARGET") or (
    _parsed.hostname or "senior-france.preview.emergentagent.com"
)

# RFC 1035 hostname validation (labels 1-63 chars, total ≤253)
_HOSTNAME_RE = re.compile(
    r"^(?=.{1,253}$)(?!-)(?!.*--)[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?"
    r"(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+$"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
class SetDomainInput(BaseModel):
    custom_domain: str


def _normalize_domain(d: str) -> str:
    d = (d or "").strip().lower()
    if "://" in d:
        d = urlparse(d).hostname or ""
    d = d.rstrip("/")
    return d


def _is_valid_hostname(d: str) -> bool:
    return bool(d) and bool(_HOSTNAME_RE.match(d))


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


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# CRUD custom domain (étape 6 du Cockpit)
# ---------------------------------------------------------------------------
@router.get("/sites/{site_id}/domain")
async def get_domain_status(site_id: str, user: dict = Depends(get_current_user)):
    site = await _check_site_access(site_id, user)
    return {
        "custom_domain": site.get("custom_domain", "") or site.get("domain", ""),
        "custom_domain_verified": bool(site.get("custom_domain_verified")),
        "custom_domain_verified_at": site.get("custom_domain_verified_at"),
        "approximated": site.get("custom_domain_approximated"),
        "cname_target": CNAME_TARGET,
        "instructions": {
            "type": "A",
            "name": "@ (puis www)",
            "value": (apx._CACHED_CLUSTER_IPS or ["213.188.213.253"])[0],
            "ttl": 300,
            "note": (
                "Pointer le record A apex (et www) du domaine vers l'IP du "
                "cluster Approximated. C'est fait automatiquement si le "
                "domaine a été acheté via Altiaro (OVH)."
            ),
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
        raise HTTPException(400, "Nom de domaine invalide. Ex : maboutique.fr")
    existing = await db.sites.find_one(
        {"custom_domain": domain, "id": {"$ne": site_id}}, {"_id": 0, "id": 1}
    )
    if existing:
        raise HTTPException(409, "Ce domaine est déjà utilisé par un autre site.")
    await db.sites.update_one(
        {"id": site_id},
        {
            "$set": {
                "custom_domain": domain,
                "custom_domain_verified": False,
                "custom_domain_verified_at": None,
            }
        },
    )
    return await get_domain_status(site_id, user)


@router.delete("/sites/{site_id}/domain")
async def clear_domain(site_id: str, user: dict = Depends(get_current_user)):
    await _check_site_access(site_id, user)
    await db.sites.update_one(
        {"id": site_id},
        {
            "$unset": {
                "custom_domain": "",
                "custom_domain_verified": "",
                "custom_domain_verified_at": "",
                "custom_domain_approximated": "",
            }
        },
    )
    # Best-effort : on retire le vhost côté Approximated
    try:
        site = await db.sites.find_one({"id": site_id}, {"_id": 0, "domain": 1, "custom_domain": 1})
        domain = (site or {}).get("custom_domain") or (site or {}).get("domain")
        if domain and apx.is_configured():
            await apx.delete_vhost(_normalize_domain(domain))
    except Exception:
        logger.exception("delete_vhost on clear failed")
    return {"ok": True}


# ---------------------------------------------------------------------------
# SKIP / UNSKIP — Permet au concepteur d'avancer sur les étapes 7-10 sans
# avoir configuré son domaine. Le check QA étape 10 enforcera quand même
# que `custom_domain` soit set + verified avant la mise en ligne.
# ---------------------------------------------------------------------------

@router.post("/sites/{site_id}/domain/skip")
async def skip_domain(site_id: str, user: dict = Depends(get_current_user)):
    """Marque l'étape Domaine comme skippée (le concepteur veut tester
    le flow et ajoutera son domaine plus tard). Débloque les étapes 7-10
    via journey_gating._check_domain qui lit `site.domain_skipped`.

    Idempotent. À l'étape 10 QA, un check séparé `domain_configured` re-
    forcera l'obligation d'avoir un vrai domaine avant le go-live.
    """
    await _check_site_access(site_id, user)
    from datetime import datetime, timezone
    await db.sites.update_one(
        {"id": site_id},
        {"$set": {
            "domain_skipped": True,
            "domain_skipped_at": datetime.now(timezone.utc).isoformat(),
            "domain_skipped_by": user.get("id"),
        }},
    )
    logger.info(f"[domain-skip] site={site_id[:8]} skipped by {user.get('email')}")
    return {"ok": True, "domain_skipped": True}


@router.post("/sites/{site_id}/domain/unskip")
async def unskip_domain(site_id: str, user: dict = Depends(get_current_user)):
    """Annule le skip (le concepteur revient configurer son domaine)."""
    await _check_site_access(site_id, user)
    await db.sites.update_one(
        {"id": site_id},
        {"$unset": {
            "domain_skipped": "",
            "domain_skipped_at": "",
            "domain_skipped_by": "",
        }},
    )
    return {"ok": True, "domain_skipped": False}




# ---------------------------------------------------------------------------
# Approximated provisioning core
# ---------------------------------------------------------------------------
async def _provision_approximated(site_id: str, domain: str) -> dict:
    """Idempotent end-to-end provisioning.

    1. Ensure vhost exists on Approximated (target = TARGET_HOST)
    2. Push A records to OVH (apex + www) → cluster IPs
    3. Refresh zone
    4. Launch a background poller to flip `custom_domain_verified` once SSL is up
    """
    domain = _normalize_domain(domain)
    if not _is_valid_hostname(domain):
        raise ValueError(f"Invalid domain: {domain}")
    report: dict = {"domain": domain, "started_at": _now_iso()}

    # Step 1 — Approximated vhost
    if not apx.is_configured():
        report["approximated"] = {"skipped": "APPROXIMATED_API_KEY missing"}
    else:
        vh = await apx.create_vhost(domain)
        report["approximated"] = vh

    # Step 2 — Get cluster IPs
    targets = await apx.get_dns_targets(probe_domain=domain)
    report["dns_targets"] = targets
    cluster_ips = list(targets.get("ips") or [])

    # Step 3 — OVH DNS push (only if domain is in our OVH account)
    if cluster_ips and ovh_dns.is_configured():
        try:
            ovh_report = await ovh_dns.replace_with_a_records(
                domain, cluster_ips, include_www=True, ttl=300
            )
            report["ovh_dns"] = ovh_report
        except Exception as e:
            logger.exception("OVH DNS push failed")
            report["ovh_dns"] = {"ok": False, "error": str(e)[:300]}
    elif not cluster_ips:
        report["ovh_dns"] = {"skipped": "no cluster IPs known"}
    else:
        report["ovh_dns"] = {"skipped": "OVH not configured"}

    # Step 4 — kick off async poller (best-effort, fire-and-forget)
    try:
        asyncio.create_task(_poll_until_ready(site_id, domain, max_seconds=15 * 60))
        report["poller_started"] = True
    except Exception:
        report["poller_started"] = False

    # Persist on site
    await db.sites.update_one(
        {"id": site_id},
        {
            "$set": {
                "custom_domain_approximated": report,
                "custom_domain_provisioned_at": _now_iso(),
            }
        },
    )
    return report


async def _poll_until_ready(site_id: str, domain: str, max_seconds: int = 900) -> None:
    """Background poll of the vhost status. Marks the site as verified as soon
    as `apx_hit && is_resolving && has_ssl`.
    """
    if not apx.is_configured():
        return
    deadline = asyncio.get_event_loop().time() + max_seconds
    interval = 60
    last_status: dict = {}
    while asyncio.get_event_loop().time() < deadline:
        try:
            st = await apx.get_vhost_status(domain, force_check=False)
            last_status = st
            if st.get("ready"):
                await db.sites.update_one(
                    {"id": site_id},
                    {
                        "$set": {
                            "custom_domain_verified": True,
                            "custom_domain_verified_at": _now_iso(),
                            "custom_domain_last_check_reason": "Approximated SSL ready",
                            "custom_domain_last_check_at": _now_iso(),
                            "custom_domain_approximated_status": st,
                        }
                    },
                )
                # Mark step 6 (domain) complete in the cockpit if possible
                try:
                    await db.steps.update_one(
                        {"site_id": site_id, "id": "domain"},
                        {
                            "$set": {
                                "status": "completed",
                                "completed_at": _now_iso(),
                                "auto_completed_by": "approximated_poller",
                            }
                        },
                    )
                except Exception:
                    pass
                logger.info(f"[apx-poller] {domain} READY ({st.get('status')})")
                return
            await db.sites.update_one(
                {"id": site_id},
                {"$set": {"custom_domain_approximated_status": st}},
            )
            logger.info(
                f"[apx-poller] {domain} status={st.get('status')} "
                f"apx_hit={st.get('apx_hit')} resolving={st.get('is_resolving')} "
                f"ssl={st.get('has_ssl')}"
            )
        except Exception as e:
            logger.warning(f"[apx-poller] {domain} check failed: {e}")
        await asyncio.sleep(interval)
    logger.warning(
        f"[apx-poller] {domain} TIMEOUT after {max_seconds}s last={last_status.get('status')}"
    )


# ---------------------------------------------------------------------------
# Verify hook (étape 6)
# ---------------------------------------------------------------------------
@router.post("/sites/{site_id}/domain/verify")
async def verify_domain(site_id: str, user: dict = Depends(get_current_user)):
    site = await _check_site_access(site_id, user)
    domain = site.get("custom_domain") or site.get("domain")
    if not domain:
        raise HTTPException(400, "Aucun domaine à vérifier.")
    domain = _normalize_domain(domain)
    if not _is_valid_hostname(domain):
        raise HTTPException(400, f"Domaine invalide : {domain}")

    # Trigger Approximated + OVH provisioning. Idempotent.
    try:
        report = await _provision_approximated(site_id, domain)
    except Exception as e:
        logger.exception("approximated provisioning failed")
        raise HTTPException(502, f"Provisioning Approximated : {str(e)[:300]}")

    # Quick status check (best-effort, no force-check)
    status = None
    if apx.is_configured():
        try:
            status = await apx.get_vhost_status(domain)
        except Exception:
            status = None

    verified = bool(status and status.get("ready"))
    if verified:
        await db.sites.update_one(
            {"id": site_id},
            {
                "$set": {
                    "custom_domain_verified": True,
                    "custom_domain_verified_at": _now_iso(),
                    "custom_domain_last_check_reason": "Approximated SSL ready",
                }
            },
        )

    return {
        "domain": domain,
        "verified": verified,
        "status": status,
        "provisioning": report,
        "checked_at": _now_iso(),
    }


# ---------------------------------------------------------------------------
# Phase 1 — Manual purchase link (Mollie one-shot, OVH price, no markup)
# ---------------------------------------------------------------------------
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
    await _check_site_access(site_id, user)
    from routes.ovh_domains import (
        ALLOWED_TLDS,
        _client as _ovh_client,
        _normalise_domain as _ovh_normalise,
        _tld_of,
    )
    from routes.payments import _get_client as _mollie_client

    domain_input = (data.domain or "").strip() if data and data.domain else ""
    if not domain_input:
        existing = await db.domains.find_one(
            {"site_id": site_id, "status": "pending_payment"}, {"_id": 0}
        )
        if not existing:
            raise HTTPException(
                404,
                "Aucun domaine en attente de paiement pour ce site. Renseigne `domain` dans le body.",
            )
        domain = existing["domain"]
    else:
        domain = _ovh_normalise(domain_input)
        if "." not in domain:
            raise HTTPException(400, "Domaine invalide. Ex : altea.com")

    tld = _tld_of(domain)
    if tld not in ALLOWED_TLDS:
        raise HTTPException(400, f"Extension non supportée : {tld}")

    client = _ovh_client()
    try:
        cart = await asyncio.to_thread(
            client.post,
            "/order/cart",
            ovhSubsidiary="FR",
            description=f"cf-manual-{site_id[:8]}",
        )
        cart_id = cart["cartId"]
        items = await asyncio.to_thread(
            client.post, f"/order/cart/{cart_id}/domain", domain=domain
        )
        item = items if isinstance(items, dict) else (items[0] if items else {})
        ovh_price_ttc = 0.0
        for p in item.get("prices", []):
            if p.get("label") == "TOTAL":
                ovh_price_ttc = float(p.get("price", {}).get("value") or 0)
                break
        try:
            await asyncio.to_thread(client.delete, f"/order/cart/{cart_id}")
        except Exception:
            pass
    except Exception as e:
        logger.exception("OVH manual price check failed")
        raise HTTPException(502, f"OVH : {str(e)[:200]}")

    if ovh_price_ttc <= 0:
        raise HTTPException(400, "Domaine indisponible ou non cotable par OVH.")

    manual_price = round(ovh_price_ttc, 2)

    record = await db.domains.find_one(
        {"domain": domain, "site_id": site_id}, {"_id": 0}
    )
    if record:
        record_id = record["id"]
        if record.get("status") in ("purchased", "dns_configured", "active"):
            raise HTTPException(400, "Ce domaine est déjà acheté.")
    else:
        record_id = f"dom-{domain.replace('.', '-')}-{uuid.uuid4().hex[:8]}"
        await db.domains.insert_one(
            {
                "id": record_id,
                "domain": domain,
                "tld": tld,
                "site_id": site_id,
                "purchased_by": user.get("id"),
                "purchased_at": _now_iso(),
                "ovh_price_ttc_eur": ovh_price_ttc,
                "markup_eur": 0,
                "platform_price_eur": manual_price,
                "status": "pending_payment",
                "manual_purchase": True,
                "created_at": _now_iso(),
                "updated_at": _now_iso(),
            }
        )

    mollie, mode = _mollie_client()
    redirect_url = f"{FRONTEND_URL}/sites/{site_id}/domains?domain_payment=1&domain={domain}"
    webhook_url = f"{FRONTEND_URL}/api/webhooks/mollie"

    try:
        payment = mollie.payments.create(
            {
                "amount": {"currency": "EUR", "value": f"{manual_price:.2f}"},
                "description": f"Domaine {domain} (achat manuel)",
                "redirectUrl": redirect_url,
                "webhookUrl": webhook_url,
                "sequenceType": "oneoff",
                "metadata": {
                    "type": "domain_purchase",
                    "manual": True,
                    "domain": domain,
                    "domain_record_id": record_id,
                    "site_id": site_id,
                    "user_id": user.get("id"),
                },
                "locale": "fr_FR",
            }
        )
    except Exception as e:
        logger.exception("Mollie create manual one-shot payment failed")
        raise HTTPException(502, f"Mollie : {str(e)[:200]}")

    await db.domains.update_one(
        {"id": record_id},
        {
            "$set": {
                "mollie_payment_id": payment.id,
                "mollie_checkout_url": payment.checkout_url,
                "mollie_mode": mode,
                "ovh_price_ttc_eur": ovh_price_ttc,
                "platform_price_eur": manual_price,
                "markup_eur": 0,
                "manual_purchase": True,
                "updated_at": _now_iso(),
            }
        },
    )

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


# ---------------------------------------------------------------------------
# Public resolver (storefront frontend)
# ---------------------------------------------------------------------------
@router.get("/public/domains/resolve")
async def public_resolve_domain(host: str):
    host = _normalize_domain(host)
    if not host:
        raise HTTPException(400, "Host manquant.")
    site = await db.sites.find_one(
        {"custom_domain": host, "custom_domain_verified": True},
        {"_id": 0, "id": 1, "name": 1},
    )
    if not site:
        raise HTTPException(404, "Aucun site vérifié pour ce domaine.")
    return {"site_id": site["id"], "site_name": site["name"], "host": host}


# ---------------------------------------------------------------------------
# Admin endpoints (Approximated)
# ---------------------------------------------------------------------------
@router.post(
    "/admin/sites/{site_id}/domain/approximated-provision",
    tags=["admin"],
    summary="Re-déclenche le provisioning Approximated + OVH DNS pour un site",
)
async def admin_approximated_provision(
    site_id: str, user: dict = Depends(get_current_user)
):
    if user.get("role") != "admin":
        raise HTTPException(403, "Admin only")
    site = await db.sites.find_one({"id": site_id}, {"_id": 0})
    if not site:
        raise HTTPException(404, "Site introuvable")
    domain = site.get("custom_domain") or site.get("domain")
    if not domain:
        raise HTTPException(400, "Site sans domaine custom")
    return await _provision_approximated(site_id, _normalize_domain(domain))


@router.get(
    "/admin/sites/{site_id}/domain/approximated-status",
    tags=["admin"],
    summary="Statut détaillé Approximated (apx_hit, dns, ssl) pour un site",
)
async def admin_approximated_status(
    site_id: str,
    force: bool = False,
    user: dict = Depends(get_current_user),
):
    if user.get("role") != "admin":
        raise HTTPException(403, "Admin only")
    site = await db.sites.find_one({"id": site_id}, {"_id": 0})
    if not site:
        raise HTTPException(404, "Site introuvable")
    domain = site.get("custom_domain") or site.get("domain")
    if not domain:
        raise HTTPException(400, "Site sans domaine custom")
    if not apx.is_configured():
        raise HTTPException(503, "APPROXIMATED_API_KEY manquant")
    return await apx.get_vhost_status(_normalize_domain(domain), force_check=force)
