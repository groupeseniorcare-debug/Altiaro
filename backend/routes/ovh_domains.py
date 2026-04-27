"""OVH domain integration (Sprint 24).

Flow Concepteur :
1. Vérifier la disponibilité d'un nom de domaine + voir le prix (affiché avec markup plateforme)
2. Acheter en 1 clic via Mollie (prix plateforme = prix OVH + markup fixe)
3. Backend utilise l'API OVH pour acheter sur ton compte OVH + configure DNS
4. Domaine automatiquement lié au site du Concepteur (CNAME/A → notre infra)

Flow Admin :
- Voir la liste de tous les domaines achetés + renouveler + transférer

Prix (markup plateforme, configurable via PLATFORM_DOMAIN_MARKUP_EUR env) :
- Prix final = prix OVH TTC + markup (par défaut 10€/an)
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Optional

import ovh
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from deps import db, get_current_user, _check_site_access, FRONTEND_URL

logger = logging.getLogger("conceptfactory.domains")
router = APIRouter()

OVH_ENDPOINT = os.environ.get("OVH_ENDPOINT", "ovh-eu")
OVH_APP_KEY = os.environ.get("OVH_APP_KEY", "")
OVH_APP_SECRET = os.environ.get("OVH_APP_SECRET", "")
OVH_CONSUMER_KEY = os.environ.get("OVH_CONSUMER_KEY", "")
MARKUP_EUR = float(os.environ.get("PLATFORM_DOMAIN_MARKUP_EUR", "10"))
PLATFORM_IP = os.environ.get("PLATFORM_SITE_IP", "")

# Supported TLDs we expose to Concepteurs (we hide risky / expensive ones)
ALLOWED_TLDS = {".fr", ".com", ".net", ".shop", ".store", ".eu", ".be", ".de",
                ".it", ".es", ".nl", ".co", ".io", ".boutique"}


def _require_config():
    if not (OVH_APP_KEY and OVH_APP_SECRET and OVH_CONSUMER_KEY):
        raise HTTPException(503, "OVH non configuré côté serveur.")


def _client() -> ovh.Client:
    _require_config()
    return ovh.Client(
        endpoint=OVH_ENDPOINT,
        application_key=OVH_APP_KEY,
        application_secret=OVH_APP_SECRET,
        consumer_key=OVH_CONSUMER_KEY,
    )


def _normalise_domain(name: str) -> str:
    return (name or "").strip().lower().replace("https://", "").replace("http://", "").rstrip("/")


def _tld_of(domain: str) -> str:
    parts = domain.split(".")
    if len(parts) < 2:
        return ""
    return "." + parts[-1]


# ============== AVAILABILITY + PRICE ============== #
class CheckInput(BaseModel):
    domain: str


@router.post("/domains/check")
async def check_domain(data: CheckInput, user: dict = Depends(get_current_user)):
    """Vérifie si un domaine est disponible + retourne le prix plateforme."""
    domain = _normalise_domain(data.domain)
    if "." not in domain:
        raise HTTPException(400, "Renseigne un domaine complet (ex: maboutique.fr)")
    tld = _tld_of(domain)
    if tld not in ALLOWED_TLDS:
        raise HTTPException(400, f"Extension non supportée. Valides : {sorted(ALLOWED_TLDS)}")

    client = _client()
    import asyncio as _aio
    try:
        # Step 1: create a cart (mandatory to get a quote)
        cart = await _aio.to_thread(
            client.post, "/order/cart",
            ovhSubsidiary="FR", description="cf-check-domain",
        )
        cart_id = cart["cartId"]
        # Step 2: add the domain to see if it's available + at what price
        items = await _aio.to_thread(
            client.post, f"/order/cart/{cart_id}/domain",
            domain=domain,
        )
        item = items if isinstance(items, dict) else (items[0] if items else {})
        # prices
        ovh_price_ttc = 0.0
        for p in item.get("prices", []):
            if p.get("label") == "TOTAL":
                ovh_price_ttc = float(p.get("price", {}).get("value") or 0)
                break
        platform_price = round(ovh_price_ttc + MARKUP_EUR, 2) if ovh_price_ttc else None
        # Cleanup the cart (we'll recreate at purchase)
        try:
            await _aio.to_thread(client.delete, f"/order/cart/{cart_id}")
        except Exception:
            pass
        return {
            "domain": domain,
            "tld": tld,
            "available": bool(ovh_price_ttc > 0),
            "ovh_price_ttc_eur": ovh_price_ttc,
            "platform_price_eur": platform_price,
            "markup_eur": MARKUP_EUR,
            "currency": "EUR",
        }
    except ovh.exceptions.APIError as e:
        logger.warning(f"OVH check domain failed: {e}")
        raise HTTPException(502, f"OVH API : {str(e)[:200]}")
    except Exception as e:
        logger.exception("check_domain failed")
        raise HTTPException(500, str(e)[:200])


# ============== PURCHASE (via Mollie) ============== #
class PurchaseInput(BaseModel):
    domain: str
    site_id: str


def _ovh_client_required():
    """Raises if OVH is not configured. Used before creating Mollie payment."""
    _require_config()


async def _execute_ovh_purchase(domain_record: dict) -> dict:
    """Actually buy the domain on OVH (called from Mollie webhook after payment).

    Returns the updated record dict. Idempotent: if already purchased, returns as-is.
    """
    domain = domain_record["domain"]
    site_id = domain_record["site_id"]

    # Idempotency guard — avoid double-buying on webhook retries
    fresh = await db.domains.find_one({"id": domain_record["id"]}, {"_id": 0})
    if fresh and fresh.get("status") in ("purchased", "dns_configured", "active"):
        return fresh

    client = _client()
    try:
        cart = await asyncio.to_thread(
            client.post, "/order/cart",
            ovhSubsidiary="FR",
            description=f"cf-site-{site_id[:8]}-{domain}",
        )
        cart_id = cart["cartId"]
        await asyncio.to_thread(client.post, f"/order/cart/{cart_id}/assign")
        items = await asyncio.to_thread(
            client.post, f"/order/cart/{cart_id}/domain", domain=domain,
        )
        item = items if isinstance(items, dict) else (items[0] if items else {})
        item_id = item.get("itemId")
        if not item_id:
            raise RuntimeError("OVH n'a pas retourné d'itemId.")
        checkout = await asyncio.to_thread(
            client.post, f"/order/cart/{cart_id}/checkout",
            autoPayWithPreferredPaymentMethod=True,
            waiveRetractationPeriod=True,
        )
        order_id = checkout.get("orderId")
        now_iso = datetime.now(timezone.utc).isoformat()
        await db.domains.update_one(
            {"id": domain_record["id"]},
            {"$set": {
                "status": "purchased",
                "ovh_cart_id": cart_id,
                "ovh_order_id": order_id,
                "ovh_item_id": item_id,
                "ovh_purchased_at": now_iso,
            }},
        )
        await db.sites.update_one(
            {"id": site_id},
            {"$set": {"domain": domain, "domain_status": "purchased",
                      "updated_at": now_iso}},
        )
        updated = await db.domains.find_one({"id": domain_record["id"]}, {"_id": 0})
        # Fire-and-forget success email to Concepteur
        try:
            from routes.emails import send_domain_purchased
            site = await db.sites.find_one({"id": site_id}, {"_id": 0})
            user = await db.users.find_one(
                {"id": domain_record.get("purchased_by")}, {"_id": 0}
            )
            if site and user:
                await send_domain_purchased(updated, site, user)
        except Exception:
            logger.exception("send_domain_purchased failed")
        return updated
    except Exception as e:
        logger.exception(f"OVH execute purchase failed for {domain}")
        err_msg = str(e)[:500]
        await db.domains.update_one(
            {"id": domain_record["id"]},
            {"$set": {
                "status": "ovh_purchase_failed",
                "ovh_error": err_msg,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }},
        )
        # Fire-and-forget failure email to Concepteur
        try:
            from routes.emails import send_domain_purchase_failed
            site = await db.sites.find_one({"id": site_id}, {"_id": 0})
            user = await db.users.find_one(
                {"id": domain_record.get("purchased_by")}, {"_id": 0}
            )
            if site and user:
                await send_domain_purchase_failed(domain_record, site, user, err_msg)
        except Exception:
            logger.exception("send_domain_purchase_failed failed")
        raise


async def complete_domain_purchase(payment_id: str, paid: bool) -> None:
    """Called by the Mollie webhook when a domain-purchase payment event arrives.

    If paid → trigger the real OVH purchase.
    If failed/expired/cancelled → mark the domain record as cancelled.
    """
    record = await db.domains.find_one({"mollie_payment_id": payment_id}, {"_id": 0})
    if not record:
        logger.warning(f"Domain payment webhook: no record for {payment_id}")
        return
    if record.get("status") in ("purchased", "dns_configured", "active"):
        return  # already done
    now_iso = datetime.now(timezone.utc).isoformat()
    if not paid:
        await db.domains.update_one(
            {"id": record["id"]},
            {"$set": {"status": "payment_failed", "updated_at": now_iso}},
        )
        return
    # paid → mark and trigger OVH
    await db.domains.update_one(
        {"id": record["id"]},
        {"$set": {"status": "paid_pending_ovh", "paid_at": now_iso,
                  "updated_at": now_iso}},
    )
    fresh = await db.domains.find_one({"id": record["id"]}, {"_id": 0})
    try:
        await _execute_ovh_purchase(fresh)
    except Exception:
        pass  # already logged + status persisted


@router.post("/domains/purchase")
async def initiate_domain_purchase(data: PurchaseInput,
                                   request: Request,
                                   user: dict = Depends(get_current_user)):
    """Démarre l'achat d'un domaine : crée un record + un paiement Mollie.

    Le Concepteur est redirigé vers Mollie pour payer le prix plateforme (coût
    OVH TTC + markup 10€). Dès que le paiement est confirmé par le webhook,
    l'achat OVH est déclenché automatiquement.
    """
    await _check_site_access(data.site_id, user)
    domain = _normalise_domain(data.domain)
    tld = _tld_of(domain)
    if tld not in ALLOWED_TLDS:
        raise HTTPException(400, f"Extension non supportée : {tld}")

    _ovh_client_required()  # fail-fast before creating Mollie payment

    existing = await db.domains.find_one({"domain": domain}, {"_id": 0})
    if existing and existing.get("status") in ("purchased", "dns_configured", "active"):
        raise HTTPException(400, "Ce domaine est déjà acheté.")
    # Allow retry if previous attempt failed
    if existing and existing.get("status") == "pending_payment":
        raise HTTPException(400, "Un paiement est déjà en cours pour ce domaine. Finalise-le depuis Mollie.")

    # Re-check availability + price via OVH to avoid a stale front price
    client = _client()
    try:
        cart = await asyncio.to_thread(
            client.post, "/order/cart",
            ovhSubsidiary="FR", description="cf-quote",
        )
        cart_id = cart["cartId"]
        items = await asyncio.to_thread(
            client.post, f"/order/cart/{cart_id}/domain", domain=domain,
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
    except ovh.exceptions.APIError as e:
        raise HTTPException(502, f"OVH : {str(e)[:200]}")
    if ovh_price_ttc <= 0:
        raise HTTPException(400, "Domaine indisponible ou non cotable.")
    platform_price = round(ovh_price_ttc + MARKUP_EUR, 2)

    # Create the Mollie payment
    import uuid
    record_id = f"dom-{domain.replace('.', '-')}-{uuid.uuid4().hex[:8]}"
    now_iso = datetime.now(timezone.utc).isoformat()
    await db.domains.insert_one({
        "id": record_id,
        "domain": domain,
        "tld": tld,
        "site_id": data.site_id,
        "purchased_by": user.get("id"),
        "purchased_at": now_iso,
        "ovh_price_ttc_eur": ovh_price_ttc,
        "markup_eur": MARKUP_EUR,
        "platform_price_eur": platform_price,
        "status": "pending_payment",
        "created_at": now_iso,
        "updated_at": now_iso,
    })

    from routes.payments import _get_client as _mollie_client
    mollie, mode = _mollie_client()
    redirect_url = f"{FRONTEND_URL}/sites/{data.site_id}/domains?domain_payment=1&domain={domain}"
    try:
        webhook_url = str(request.url_for("mollie_webhook"))
    except Exception:
        webhook_url = f"{os.environ.get('BACKEND_URL', '')}/api/webhooks/mollie"

    try:
        payment = mollie.payments.create({
            "amount": {"currency": "EUR", "value": f"{platform_price:.2f}"},
            "description": f"Domaine {domain}",
            "redirectUrl": redirect_url,
            "webhookUrl": webhook_url,
            "metadata": {
                "type": "domain_purchase",
                "domain": domain,
                "domain_record_id": record_id,
                "site_id": data.site_id,
                "user_id": user.get("id"),
            },
            "locale": "fr_FR",
        })
    except Exception as e:
        await db.domains.delete_one({"id": record_id})
        logger.exception("Mollie create payment for domain failed")
        raise HTTPException(502, f"Mollie : {str(e)[:200]}")

    await db.domains.update_one(
        {"id": record_id},
        {"$set": {
            "mollie_payment_id": payment.id,
            "mollie_checkout_url": payment.checkout_url,
            "mollie_mode": mode,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }},
    )
    return {
        "ok": True,
        "domain": domain,
        "platform_price_eur": platform_price,
        "checkout_url": payment.checkout_url,
        "payment_id": payment.id,
        "domain_record_id": record_id,
    }


@router.get("/domains/{domain}/purchase-status")
async def get_purchase_status(domain: str, user: dict = Depends(get_current_user)):
    """Polled by the frontend after Mollie redirect to know if OVH purchase is done."""
    domain = _normalise_domain(domain)
    record = await db.domains.find_one({"domain": domain}, {"_id": 0})
    if not record:
        raise HTTPException(404, "Domaine inconnu.")
    if user.get("role") != "admin" and record.get("site_id"):
        await _check_site_access(record["site_id"], user)
    return {
        "domain": domain,
        "status": record.get("status"),
        "ovh_error": record.get("ovh_error"),
        "site_id": record.get("site_id"),
        "platform_price_eur": record.get("platform_price_eur"),
        "paid_at": record.get("paid_at"),
    }


# ============== DNS CONFIG ============== #
@router.post("/domains/{domain}/configure-dns")
async def configure_dns(domain: str, user: dict = Depends(get_current_user)):
    """Configure la zone DNS pour pointer le domaine vers notre plateforme.

    Ajoute :
    - A record @ → PLATFORM_SITE_IP
    - CNAME www → @

    Requiert que le domaine soit dans l'état "purchased" (la zone OVH met
    en général 5-15 min à être créée après achat).
    """
    domain = _normalise_domain(domain)
    record = await db.domains.find_one({"domain": domain}, {"_id": 0})
    if not record:
        raise HTTPException(404, "Domaine inconnu.")
    if user.get("role") != "admin":
        if record.get("site_id"):
            await _check_site_access(record["site_id"], user)
    if not PLATFORM_IP:
        raise HTTPException(503, "PLATFORM_SITE_IP non configurée côté serveur.")

    client = _client()
    import asyncio as _aio
    try:
        # A record @ → PLATFORM_IP
        await _aio.to_thread(
            client.post, f"/domain/zone/{domain}/record",
            fieldType="A", subDomain="", target=PLATFORM_IP, ttl=300,
        )
        # CNAME www → @
        try:
            await _aio.to_thread(
                client.post, f"/domain/zone/{domain}/record",
                fieldType="CNAME", subDomain="www", target=f"{domain}.", ttl=300,
            )
        except Exception as e:
            logger.warning(f"CNAME www failed (might already exist): {e}")
        # Refresh
        await _aio.to_thread(client.post, f"/domain/zone/{domain}/refresh")
        await db.domains.update_one(
            {"domain": domain},
            {"$set": {"status": "dns_configured",
                      "dns_configured_at": datetime.now(timezone.utc).isoformat()}},
        )
        await db.sites.update_one(
            {"domain": domain},
            {"$set": {"domain_status": "active",
                      "updated_at": datetime.now(timezone.utc).isoformat()}},
        )
        return {"ok": True, "domain": domain, "platform_ip": PLATFORM_IP}
    except ovh.exceptions.ResourceNotFoundError:
        raise HTTPException(409, "La zone DNS n'est pas encore créée. Réessaye dans 10 min.")
    except ovh.exceptions.APIError as e:
        logger.exception("DNS config failed")
        raise HTTPException(502, f"OVH API : {str(e)[:300]}")


# ============== LIST / MANAGE ============== #
@router.get("/domains")
async def list_my_domains(user: dict = Depends(get_current_user)):
    q = {} if user.get("role") == "admin" else {"purchased_by": user.get("id")}
    cursor = db.domains.find(q, {"_id": 0}).sort("purchased_at", -1).limit(200)
    return {"domains": await cursor.to_list(200)}


@router.get("/domains/{domain}/dns")
async def get_dns_zone(domain: str, user: dict = Depends(get_current_user)):
    domain = _normalise_domain(domain)
    record = await db.domains.find_one({"domain": domain}, {"_id": 0})
    if not record:
        raise HTTPException(404, "Domaine inconnu.")
    if user.get("role") != "admin" and record.get("site_id"):
        await _check_site_access(record["site_id"], user)
    client = _client()
    import asyncio as _aio
    try:
        ids = await _aio.to_thread(client.get, f"/domain/zone/{domain}/record")
        records = []
        for rid in ids[:50]:
            try:
                r = await _aio.to_thread(client.get, f"/domain/zone/{domain}/record/{rid}")
                records.append(r)
            except Exception:
                pass
        return {"domain": domain, "records": records}
    except ovh.exceptions.APIError as e:
        raise HTTPException(502, f"OVH API : {str(e)[:200]}")


@router.get("/domains/config-status")
async def config_status(user: dict = Depends(get_current_user)):
    """Indique si l'intégration OVH est fonctionnelle."""
    status = {
        "config_ready": bool(OVH_APP_KEY and OVH_APP_SECRET and OVH_CONSUMER_KEY),
        "endpoint": OVH_ENDPOINT,
        "markup_eur": MARKUP_EUR,
        "platform_ip_configured": bool(PLATFORM_IP and PLATFORM_IP != "0.0.0.0"),
    }
    # Probe auth
    if status["config_ready"]:
        try:
            client = _client()
            import asyncio as _aio
            me = await _aio.to_thread(client.get, "/me")
            status["ovh_account"] = me.get("nichandle")
            status["auth_ok"] = True
        except Exception as e:
            status["auth_ok"] = False
            status["auth_error"] = str(e)[:200]
    return status


# ============== ADMIN MONITORING ============== #
@router.get(
    "/admin/domains/{domain_id}/status",
    tags=["domain-manual-purchase"],
    summary="Admin : statut complet d'un record domain (DB + Mollie + OVH)",
)
async def admin_domain_status(
    domain_id: str,
    user: dict = Depends(get_current_user),
):
    """Retourne l'état détaillé d'un record `domains` :
    - `db` : le record Mongo brut
    - `mollie` : le paiement Mollie (status, is_paid, amount, checkout_url)
    - `ovh` : la commande OVH (si déjà déclenchée)

    Réservé aux admins. Utile pour diagnostiquer un blocage de paiement
    manuel (Phase 1 — workaround domaine).
    """
    if user.get("role") != "admin":
        raise HTTPException(403, "Admin only")

    record = await db.domains.find_one({"id": domain_id}, {"_id": 0})
    if not record:
        raise HTTPException(404, "Domaine inconnu")

    out = {"db": record, "mollie": None, "ovh": None}

    # Mollie payment status
    payment_id = record.get("mollie_payment_id")
    if payment_id:
        try:
            from routes.payments import _get_client as _mollie_client
            client, mode = _mollie_client()
            payment = client.payments.get(payment_id)
            out["mollie"] = {
                "id": payment.id,
                "mode": mode,
                "status": getattr(payment, "status", None),
                "is_paid": bool(payment.is_paid()) if hasattr(payment, "is_paid") else None,
                "is_expired": bool(payment.is_expired()) if hasattr(payment, "is_expired") else None,
                "is_failed": bool(payment.is_failed()) if hasattr(payment, "is_failed") else None,
                "is_canceled": bool(payment.is_canceled()) if hasattr(payment, "is_canceled") else None,
                "amount": dict(payment.amount) if hasattr(payment, "amount") else None,
                "checkout_url": getattr(payment, "checkout_url", None),
                "method": getattr(payment, "method", None),
                "metadata": getattr(payment, "metadata", None),
                "sequence_type": getattr(payment, "sequence_type", None) or getattr(payment, "sequenceType", None),
                "expires_at": getattr(payment, "expires_at", None) or getattr(payment, "expiresAt", None),
                "paid_at": getattr(payment, "paid_at", None) or getattr(payment, "paidAt", None),
            }
        except Exception as e:
            out["mollie"] = {"error": str(e)[:200]}

    # OVH order status
    ovh_order_id = record.get("ovh_order_id")
    if ovh_order_id:
        try:
            client = _client()
            import asyncio as _aio
            order = await _aio.to_thread(client.get, f"/me/order/{ovh_order_id}")
            try:
                status_info = await _aio.to_thread(client.get, f"/me/order/{ovh_order_id}/status")
                order["status"] = status_info
            except Exception:
                pass
            out["ovh"] = order
        except Exception as e:
            out["ovh"] = {"error": str(e)[:200]}

    return out


@router.post(
    "/admin/domains/{domain_id}/force-complete",
    tags=["domain-manual-purchase"],
    summary="Admin : force la finalisation OVH d'un domaine (parade webhook preview down)",
)
async def admin_domain_force_complete(
    domain_id: str,
    user: dict = Depends(get_current_user),
):
    """Force le déclenchement de `complete_domain_purchase()` pour un record
    `domains` donné, en parade au cas où Mollie n'a pas pu joindre le webhook
    (preview Emergent down, etc.).

    Sécurité :
    - Réservé aux admins.
    - Vérifie côté Mollie API que le paiement est bien `paid` avant de
      déclencher l'achat OVH (pas de finalisation gratuite).
    - Idempotent : si l'achat OVH est déjà fait, retourne le record tel quel.

    Workflow attendu :
    1. L'utilisateur paie via le checkout_url Mollie
    2. Si le webhook ne déclenche pas (preview down) → admin appelle cet endpoint
    3. On vérifie via API Mollie que le paiement est `paid`
    4. On déclenche `complete_domain_purchase(payment_id, paid=True)` qui
       appelle `_execute_ovh_purchase()` → cron auto-DNS finalise.
    """
    if user.get("role") != "admin":
        raise HTTPException(403, "Admin only")

    record = await db.domains.find_one({"id": domain_id}, {"_id": 0})
    if not record:
        raise HTTPException(404, "Domaine inconnu")

    # Idempotence
    if record.get("status") in ("purchased", "dns_configured", "active"):
        return {
            "ok": True,
            "already_done": True,
            "status": record.get("status"),
            "ovh_order_id": record.get("ovh_order_id"),
        }

    payment_id = record.get("mollie_payment_id")
    if not payment_id:
        raise HTTPException(400, "Aucun mollie_payment_id sur ce record.")

    # Verify payment is actually paid via Mollie API (anti-fraud)
    from routes.payments import _get_client as _mollie_client
    try:
        client, mode = _mollie_client()
        payment = client.payments.get(payment_id)
    except Exception as e:
        raise HTTPException(502, f"Mollie API : {str(e)[:200]}")

    is_paid = bool(payment.is_paid()) if hasattr(payment, "is_paid") else False
    if not is_paid:
        raise HTTPException(
            status_code=400,
            detail=f"Paiement Mollie non confirmé (status={getattr(payment, 'status', '?')}). "
                   f"Refuse de finaliser l'achat OVH tant que le paiement n'est pas `paid`.",
        )

    # Trigger the same handler the webhook would have triggered
    from routes.ovh_domains import complete_domain_purchase
    try:
        await complete_domain_purchase(payment_id, True)
    except Exception as e:
        logger.exception("force-complete: complete_domain_purchase failed")
        raise HTTPException(502, f"OVH purchase failed : {str(e)[:200]}")

    refreshed = await db.domains.find_one({"id": domain_id}, {"_id": 0})
    logger.info(
        f"[force-complete] admin {user.get('email')} forced completion "
        f"for {refreshed.get('domain')} (record {domain_id}) → "
        f"status={refreshed.get('status')} ovh_order={refreshed.get('ovh_order_id')}"
    )
    return {
        "ok": True,
        "forced": True,
        "by": user.get("email"),
        "mollie_payment_id": payment_id,
        "mollie_status": getattr(payment, "status", None),
        "domain": refreshed.get("domain"),
        "status": refreshed.get("status"),
        "ovh_order_id": refreshed.get("ovh_order_id"),
        "ovh_error": refreshed.get("ovh_error"),
    }
