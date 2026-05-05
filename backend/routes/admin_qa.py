"""Admin QA endpoints — utilities for end-to-end testing without external deps.

Usage : QA / smoke tests internes uniquement.
Requires admin role.
"""
from __future__ import annotations

import logging
import uuid as _uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from deps import db, get_current_user

logger = logging.getLogger("altiaro.admin_qa")
router = APIRouter()


def _require_admin(user: dict):
    if not user or user.get("role") != "admin":
        raise HTTPException(403, "Admin required")


@router.post("/admin/qa/simulate-paid-webhook", tags=["admin-qa"])
async def simulate_paid_webhook(order_id: str, user: dict = Depends(get_current_user)):
    """Simule un webhook Mollie 'paid' sur un order existant.

    Idempotent. Bascule l'order pending_payment → paid, déclenche les emails
    (order_confirmation + admin_new_order), insère la admin_notifications,
    et log le 50 % share dans le ledger.

    But : tester le tunnel commande end-to-end sans avoir à passer par
    une vraie checkout Mollie.
    """
    _require_admin(user)
    order = await db.orders.find_one({"id": order_id}, {"_id": 0})
    if not order:
        raise HTTPException(404, "Order not found")

    site = await db.sites.find_one({"id": order["site_id"]}, {"_id": 0})
    if not site:
        raise HTTPException(404, "Site not found for this order")

    now_iso = datetime.now(timezone.utc).isoformat()
    current = order.get("status")

    fake_payment_id = order.get("mollie_payment_id") or f"tr_test_{_uuid.uuid4().hex[:16]}"

    if current == "paid":
        # Already paid — re-trigger downstream side-effects only if explicitly idempotent test
        logger.info(f"[qa] order {order.get('order_number')} already paid; re-running downstream")
    else:
        await db.orders.update_one(
            {"id": order_id},
            {
                "$set": {
                    "status": "paid",
                    "paid_at": now_iso,
                    "mollie_payment_id": fake_payment_id,
                    "mollie_status": "paid",
                    "mollie_mode": "test_qa_simulated",
                    "payment_method": "mollie",
                    "payment_method_used": "creditcard",
                    "updated_at": now_iso,
                },
                "$push": {
                    "status_history": {
                        "status": "paid",
                        "at": now_iso,
                        "source": "qa_simulated_webhook",
                        "payment_id": fake_payment_id,
                    }
                },
            },
        )

    refreshed = await db.orders.find_one({"id": order_id}, {"_id": 0})

    # 1. 50 % share to ledger
    ledger_status = "skipped"
    try:
        from routes.billing import log_order_share_on_paid
        await log_order_share_on_paid(refreshed)
        ledger_status = "ok"
    except Exception as e:
        logger.exception("ledger log failed")
        ledger_status = f"error: {str(e)[:80]}"

    # 2. Confirmation emails
    email_status = {"client": "skipped", "admin": "skipped"}
    try:
        from routes.emails import send_order_confirmation, send_admin_new_order
        client_res = await send_order_confirmation(refreshed, site)
        admin_res = await send_admin_new_order(refreshed, site)
        email_status = {"client": client_res, "admin": admin_res}
    except Exception as e:
        logger.exception("emails send failed")
        email_status = {"error": str(e)[:160]}

    # 3. admin_notifications entry
    notif_inserted = False
    try:
        await db.admin_notifications.insert_one({
            "id": str(_uuid.uuid4()),
            "type": "new_order",
            "site_id": refreshed.get("site_id"),
            "site_name": refreshed.get("site_name"),
            "order_id": refreshed.get("id"),
            "order_number": refreshed.get("order_number"),
            "total": float(refreshed.get("total") or 0),
            "currency": refreshed.get("currency", "EUR"),
            "customer_email": ((refreshed.get("customer") or {}).get("email")),
            "customer_lang": ((refreshed.get("customer") or {}).get("lang"))
                            or (refreshed.get("language")),
            "title": f"Nouvelle commande #{refreshed.get('order_number')}",
            "message": f"{refreshed.get('site_name','Site')} · "
                       f"{float(refreshed.get('total') or 0):.2f} "
                       f"{refreshed.get('currency','EUR')}",
            "read": False,
            "created_at": now_iso,
            "_qa_simulated": True,
        })
        notif_inserted = True
    except Exception:
        logger.exception("notif insert failed")

    return {
        "ok": True,
        "order_id": order_id,
        "order_number": refreshed.get("order_number"),
        "status": refreshed.get("status"),
        "paid_at": refreshed.get("paid_at"),
        "customer_lang_detected": (
            (refreshed.get("customer") or {}).get("lang")
            or refreshed.get("language")
        ),
        "ledger": ledger_status,
        "emails": email_status,
        "admin_notification_inserted": notif_inserted,
    }
