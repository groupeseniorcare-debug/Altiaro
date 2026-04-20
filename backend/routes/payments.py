"""
Mollie payments for Concept Factory storefront.
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
            logger.warning(f"Webhook pour paiement inconnu : {payment_id}")
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
