"""
Mollie payments for Altiora storefront.
Flow :
  1. Frontend calls POST /api/public/payments/create with order_id → on crée un paiement Mollie et on renvoie checkout_url.
  2. Client paie sur Mollie → redirigé sur /shop/{site_id}/checkout/success?order={order_number}
  3. Mollie appelle POST /api/webhooks/mollie → on fetch le statut via API (vérification) + on met à jour l'order.
  4. Frontend poll GET /api/public/payments/{payment_id}/status en attendant la confirmation.

Clés : MOLLIE_TEST_KEY / MOLLIE_LIVE_KEY + MOLLIE_MODE=test|live dans .env
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from deps import db, FRONTEND_URL

logger = logging.getLogger("conceptfactory.mollie")
router = APIRouter()


def _get_client():
    from mollie.api.client import Client
    mode = (os.environ.get("MOLLIE_MODE") or "test").lower()
    key = os.environ.get("MOLLIE_LIVE_KEY" if mode == "live" else "MOLLIE_TEST_KEY") or ""
    if not key:
        raise HTTPException(status_code=500, detail="Clé Mollie non configurée (MOLLIE_TEST_KEY manquant).")
    c = Client()
    c.set_api_key(key)
    return c, mode


class CreatePaymentInput(BaseModel):
    order_number: str
    site_id: str


@router.post("/public/payments/create")
async def create_payment(data: CreatePaymentInput, request: Request):
    """Crée un paiement Mollie pour une commande pending_payment."""
    order = await db.orders.find_one(
        {"site_id": data.site_id, "order_number": data.order_number},
        {"_id": 0, "_meta_ip": 0},
    )
    if not order:
        raise HTTPException(status_code=404, detail="Commande introuvable")
    if order.get("status") != "pending_payment":
        raise HTTPException(status_code=400, detail=f"Commande déjà {order.get('status')}")

    client, mode = _get_client()

    total = round(float(order.get("total") or 0), 2)
    currency = (order.get("currency") or "EUR").upper()

    # Redirect customer back to the storefront success page
    redirect_url = f"{FRONTEND_URL}/shop/{data.site_id}/checkout/success?order={data.order_number}"
    # Webhook URL must be publicly reachable — use the backend URL
    webhook_url = str(request.url_for("mollie_webhook"))

    payment_data = {
        "amount": {"currency": currency, "value": f"{total:.2f}"},
        "description": f"Commande {order.get('order_number')}",
        "redirectUrl": redirect_url,
        "webhookUrl": webhook_url,
        "metadata": {
            "order_id": order.get("id"),
            "order_number": order.get("order_number"),
            "site_id": data.site_id,
        },
        "locale": _locale_for_language(order.get("language")),
    }

    try:
        payment = client.payments.create(payment_data)
    except Exception as e:
        logger.exception("Mollie payment creation failed")
        raise HTTPException(status_code=502, detail=f"Mollie : {str(e)[:200]}")

    await db.orders.update_one(
        {"id": order["id"]},
        {"$set": {
            "mollie_payment_id": payment.id,
            "mollie_checkout_url": payment.checkout_url,
            "mollie_mode": mode,
            "payment_method": "mollie",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }}
    )

    return {
        "payment_id": payment.id,
        "checkout_url": payment.checkout_url,
        "mode": mode,
    }


@router.get("/public/payments/{payment_id}/status")
async def get_payment_status(payment_id: str, site_id: str, order_number: str):
    """Le frontend poll cet endpoint pour savoir si le paiement est validé."""
    order = await db.orders.find_one(
        {"site_id": site_id, "order_number": order_number, "mollie_payment_id": payment_id},
        {"_id": 0, "_meta_ip": 0, "status_history": 0},
    )
    if not order:
        raise HTTPException(status_code=404, detail="Commande introuvable")
    return {
        "order_number": order.get("order_number"),
        "status": order.get("status"),
        "total": order.get("total"),
        "currency": order.get("currency"),
        "paid_at": order.get("paid_at"),
    }


@router.post("/webhooks/mollie", name="mollie_webhook")
async def mollie_webhook(request: Request):
    """Mollie POST {id: 'tr_xxx'} ici. On fetch via API puis update l'order.
    IMPORTANT : toujours retourner 200 OK (sinon Mollie retry en boucle)."""
    try:
        form = await request.form()
        payment_id = form.get("id") if form else None
        if not payment_id:
            try:
                body = await request.json()
                payment_id = body.get("id")
            except Exception:
                pass
        if not payment_id:
            logger.warning("Mollie webhook sans id")
            return {"ok": True}

        client, _ = _get_client()
        try:
            payment = client.payments.get(payment_id)
        except Exception as e:
            logger.exception(f"Mollie fetch payment {payment_id} failed: {e}")
            return {"ok": True}

        order = await db.orders.find_one(
            {"mollie_payment_id": payment_id}, {"_id": 0}
        )
        if not order:
            # Maybe it's a domain purchase payment?
            meta = getattr(payment, "metadata", None) or {}
            if isinstance(meta, dict) and meta.get("type") == "domain_purchase":
                from routes.domains import complete_domain_purchase
                await complete_domain_purchase(payment_id, bool(payment.is_paid()))
                return {"ok": True}
            # Maybe it's a card mandate setup ?
            await _handle_card_setup_webhook(payment, payment_id)
            return {"ok": True}

        current = order.get("status")
        now_iso = datetime.now(timezone.utc).isoformat()
        updates = {"updated_at": now_iso, "mollie_status": payment.status}

        # Idempotence
        if current not in ("pending_payment",):
            logger.info(f"Order {order.get('order_number')} déjà en {current}, webhook skip update status")
            await db.orders.update_one({"id": order["id"]}, {"$set": updates})
            return {"ok": True}

        new_status = current
        if payment.is_paid():
            new_status = "paid"
            updates["paid_at"] = now_iso
            updates["payment_method_used"] = getattr(payment, "method", None)
        elif payment.is_expired():
            new_status = "expired"
        elif payment.is_failed():
            new_status = "failed"
        elif payment.is_canceled():
            new_status = "cancelled"

        if new_status != current:
            updates["status"] = new_status
            # Status history entry
            await db.orders.update_one(
                {"id": order["id"]},
                {
                    "$set": updates,
                    "$push": {
                        "status_history": {
                            "status": new_status,
                            "at": now_iso,
                            "source": "mollie_webhook",
                            "payment_id": payment_id,
                        }
                    },
                },
            )
            logger.info(f"Order {order.get('order_number')} : {current} → {new_status}")
            # Log 50% share into Concepteur ledger on first 'paid' transition
            if new_status == "paid":
                try:
                    from routes.billing import log_order_share_on_paid
                    refreshed = await db.orders.find_one({"id": order["id"]}, {"_id": 0})
                    if refreshed:
                        await log_order_share_on_paid(refreshed)
                except Exception:
                    logger.exception("Failed to log order_share to ledger")
                # Send confirmation emails (client + admin) — non-blocking
                try:
                    from routes.emails import send_order_confirmation, send_admin_new_order
                    refreshed = await db.orders.find_one({"id": order["id"]}, {"_id": 0})
                    if refreshed and refreshed.get("site_id"):
                        site = await db.sites.find_one(
                            {"id": refreshed["site_id"]}, {"_id": 0}
                        )
                        if site:
                            await send_order_confirmation(refreshed, site)
                            await send_admin_new_order(refreshed, site)
                except Exception:
                    logger.exception("Failed to send confirmation emails")
        else:
            await db.orders.update_one({"id": order["id"]}, {"$set": updates})

        return {"ok": True}
    except Exception as e:
        logger.exception(f"Webhook Mollie exception : {e}")
        return {"ok": True}


def _locale_for_language(lang: str | None) -> str:
    return {
        "fr": "fr_FR", "en": "en_GB", "de": "de_DE", "nl": "nl_NL",
    }.get((lang or "fr").lower(), "fr_FR")


async def _handle_card_setup_webhook(payment, payment_id: str):
    """When a card mandate first payment (0.01€) succeeds, capture the mandate_id and card details."""
    meta = getattr(payment, "metadata", None) or {}
    if isinstance(meta, dict) and meta.get("purpose") != "card_mandate_setup":
        return
    user_id = meta.get("user_id") if isinstance(meta, dict) else None
    if not user_id:
        # try to find by pending setup payment id
        prof = await db.billing_profiles.find_one({"pending_setup_payment_id": payment_id}, {"_id": 0})
        if prof:
            user_id = prof.get("user_id")
    if not user_id:
        logger.warning(f"Card setup webhook without user_id : {payment_id}")
        return

    now_iso = datetime.now(timezone.utc).isoformat()
    if not payment.is_paid():
        await db.orders.find_one  # no-op
        await db.billing_profiles.update_one(
            {"user_id": user_id},
            {"$set": {
                "mandate_status": payment.status,
                "updated_at": now_iso,
            }},
        )
        return

    mandate_id = getattr(payment, "mandate_id", None) or ""
    details = getattr(payment, "details", None) or {}
    card_last4 = details.get("cardNumber") if isinstance(details, dict) else None
    card_brand = details.get("cardLabel") if isinstance(details, dict) else None

    await db.billing_profiles.update_one(
        {"user_id": user_id},
        {"$set": {
            "mandate_id": mandate_id,
            "mandate_status": "valid",
            "card_last4": card_last4,
            "card_brand": card_brand,
            "mandate_created_at": now_iso,
            "updated_at": now_iso,
        },
         "$unset": {"pending_setup_payment_id": ""}},
    )
    logger.info(f"Card mandate stored for user {user_id}: {mandate_id}")
