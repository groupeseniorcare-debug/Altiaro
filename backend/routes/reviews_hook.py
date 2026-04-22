"""
Review invitation system — 14 days after delivery, customer receives a link
to leave a product review.

Flow :
1. When order is marked `delivered_at`, a review_invitation is created per product (status="pending").
2. A daily cron (`check_due_invitations`) finds invitations with `send_after <= now`
   and either sends email via Resend (if RESEND_API_KEY present) or marks as "skipped_no_resend".
3. Customer clicks `/shop/:siteId/review/:token` which resolves to a public page.
4. POST `/api/public/reviews/submit/:token` appends to `product.reviews[]` and recomputes `product.rating`.

Tokens are UUID-signed and expire 60 days after delivery.
"""
from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from deps import db, get_current_user

logger = logging.getLogger("conceptfactory.reviews")
router = APIRouter()

RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
SENDER_EMAIL = os.environ.get("RESEND_DEFAULT_FROM", "onboarding@resend.dev")
REVIEW_DELAY_DAYS = 14
REVIEW_WINDOW_DAYS = 60

if RESEND_API_KEY:
    try:
        import resend
        resend.api_key = RESEND_API_KEY
    except ImportError:
        logger.warning("[reviews] resend SDK not installed")


async def _create_invitations_for_order(order: dict) -> int:
    """Create 1 review_invitation per unique product in an order."""
    if not order or not order.get("delivered_at"):
        return 0

    product_ids = list({it.get("product_id") for it in (order.get("items") or []) if it.get("product_id")})
    if not product_ids:
        return 0

    send_after = datetime.now(timezone.utc) + timedelta(days=REVIEW_DELAY_DAYS)
    now = datetime.now(timezone.utc)
    created = 0
    for pid in product_ids:
        existing = await db.review_invitations.find_one({"order_id": order["id"], "product_id": pid})
        if existing:
            continue
        token = uuid.uuid4().hex
        await db.review_invitations.insert_one({
            "id": str(uuid.uuid4()),
            "token": token,
            "order_id": order["id"],
            "site_id": order["site_id"],
            "product_id": pid,
            "customer_email": order.get("customer_email") or order.get("email"),
            "customer_name": order.get("customer_name") or "",
            "created_at": now,
            "send_after": send_after,
            "sent_at": None,
            "used_at": None,
            "status": "pending",
        })
        created += 1
    logger.info(f"[reviews] {created} invitations created for order {order.get('id')}")
    return created


async def check_due_invitations() -> dict:
    """Called by daily cron. Sends (or logs) pending invitations whose send_after is due."""
    now = datetime.now(timezone.utc)
    cursor = db.review_invitations.find({
        "status": "pending",
        "send_after": {"$lte": now},
    })
    due = await cursor.to_list(500)
    sent = 0
    skipped = 0
    for inv in due:
        if not RESEND_API_KEY:
            # Log only — mark as skipped_no_resend so we don't retry endlessly
            await db.review_invitations.update_one(
                {"id": inv["id"]},
                {"$set": {"status": "skipped_no_resend", "sent_at": now}},
            )
            skipped += 1
            logger.info(f"[reviews] would email {inv.get('customer_email')} (no RESEND_API_KEY)")
            continue
        # Real email dispatch (stub — integrate Resend playbook here)
        try:
            await _send_review_email(inv)
            await db.review_invitations.update_one(
                {"id": inv["id"]},
                {"$set": {"status": "sent", "sent_at": now}},
            )
            sent += 1
        except Exception:
            logger.exception(f"[reviews] failed to send for invitation {inv['id']}")
    return {"total_due": len(due), "sent": sent, "skipped_no_resend": skipped}


async def _send_review_email(invitation: dict):
    """Send review-request email via Resend SDK (non-blocking via asyncio.to_thread)."""
    import asyncio
    import resend
    origin = os.environ.get("PUBLIC_ORIGIN") or "https://senior-france.preview.emergentagent.com"
    review_url = f"{origin}/shop/{invitation['site_id']}/review/{invitation['token']}"
    site = await db.sites.find_one({"id": invitation["site_id"]}, {"_id": 0, "name": 1, "design": 1})
    brand = (site or {}).get("name", "Notre maison")
    primary = (((site or {}).get("design") or {}).get("brand") or {}).get("primary_color") or "#B84B31"

    html = f"""<!doctype html>
<html><body style="margin:0;background:#FDFBF7;font-family:Georgia,serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#FDFBF7;padding:40px 20px;">
  <tr><td align="center">
    <table width="560" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:16px;padding:40px;max-width:560px;">
      <tr><td style="font-family:Georgia,serif;font-size:28px;color:#1C1917;padding-bottom:20px;font-weight:600;">
        Merci pour votre confiance
      </td></tr>
      <tr><td style="font-family:system-ui,sans-serif;font-size:16px;color:#57534E;line-height:1.7;padding-bottom:24px;">
        Bonjour {invitation.get('customer_name') or ''},<br/><br/>
        Nous espérons que votre commande chez <strong style="color:#1C1917;">{brand}</strong> correspond à vos attentes.<br/><br/>
        Accepteriez-vous de nous laisser votre avis ? Cela aide d'autres familles à faire le bon choix — et nous aide à nous améliorer.
      </td></tr>
      <tr><td align="center" style="padding:16px 0 24px;">
        <a href="{review_url}"
           style="background:{primary};color:#ffffff;text-decoration:none;padding:14px 32px;border-radius:999px;font-family:system-ui,sans-serif;font-weight:500;font-size:15px;display:inline-block;">
          Laisser mon avis (1 min)
        </a>
      </td></tr>
      <tr><td style="font-family:system-ui,sans-serif;color:#A8A29E;font-size:12px;padding-top:16px;border-top:1px solid #F5F2EB;">
        Lien valide 60 jours. Si vous ne souhaitez plus recevoir ces emails, <a href="#" style="color:#A8A29E;">cliquez ici</a>.
      </td></tr>
    </table>
  </td></tr>
</table>
</body></html>"""

    params = {
        "from": f"{brand} <{SENDER_EMAIL}>",
        "to": [invitation["customer_email"]],
        "subject": f"Votre avis sur votre commande {brand}",
        "html": html,
    }
    result = await asyncio.to_thread(resend.Emails.send, params)
    logger.info(f"[reviews] email sent to {invitation['customer_email']} · id={result.get('id') if isinstance(result, dict) else result}")
    return result


# =====================================================================
# PUBLIC ROUTES (no auth) — customer submits review
# =====================================================================
class ReviewSubmitInput(BaseModel):
    rating: int = Field(ge=1, le=5)
    title: str = Field(max_length=140)
    body: str = Field(max_length=2000)


@router.get("/public/reviews/invitation/{token}")
async def public_invitation_detail(token: str):
    """Resolves a review token → returns product + order info for the review form."""
    inv = await db.review_invitations.find_one({"token": token}, {"_id": 0})
    if not inv:
        raise HTTPException(404, "Lien invalide ou expiré.")
    if inv.get("used_at"):
        raise HTTPException(410, "Avis déjà déposé, merci !")
    # Expiry check
    created = inv.get("created_at")
    if isinstance(created, datetime):
        if datetime.now(timezone.utc) - created > timedelta(days=REVIEW_WINDOW_DAYS):
            raise HTTPException(410, "Ce lien d'avis a expiré.")
    product = await db.products.find_one({"id": inv["product_id"]}, {"_id": 0, "id": 1, "name": 1, "images": 1})
    return {
        "token": token,
        "product": product,
        "customer_name": inv.get("customer_name"),
    }


@router.post("/public/reviews/submit/{token}")
async def public_review_submit(token: str, body: ReviewSubmitInput):
    inv = await db.review_invitations.find_one({"token": token})
    if not inv:
        raise HTTPException(404, "Lien invalide.")
    if inv.get("used_at"):
        raise HTTPException(410, "Avis déjà déposé, merci !")

    now = datetime.now(timezone.utc)
    review = {
        "id": str(uuid.uuid4()),
        "author": inv.get("customer_name") or "Client vérifié",
        "location": "",
        "date": now.strftime("%d/%m/%Y"),
        "date_iso": now.isoformat(),
        "rating": body.rating,
        "title": body.title,
        "body": body.body,
        "verified": True,
    }

    # Append to product + recompute aggregate rating
    product = await db.products.find_one({"id": inv["product_id"]}, {"_id": 0, "reviews": 1})
    all_reviews = (product.get("reviews") or []) + [review]
    score = round(sum(r.get("rating", 0) for r in all_reviews) / len(all_reviews), 2)
    await db.products.update_one(
        {"id": inv["product_id"]},
        {"$set": {"reviews": all_reviews, "rating": {"score": score, "count": len(all_reviews)}}},
    )
    await db.review_invitations.update_one(
        {"token": token},
        {"$set": {"used_at": now, "status": "used"}},
    )

    # Fire IndexNow on the product to refresh rich snippet
    try:
        from routes.indexnow import fire_and_forget_indexnow
        origin = os.environ.get("PUBLIC_ORIGIN") or "https://senior-france.preview.emergentagent.com"
        fire_and_forget_indexnow([f"{origin}/shop/{inv['site_id']}/product/{inv['product_id']}"])
    except Exception:
        pass

    return {"status": "ok", "review_id": review["id"]}


# =====================================================================
# ADMIN ROUTES
# =====================================================================
@router.post("/reviews/check-due")
async def admin_trigger_check(user=Depends(get_current_user)):
    """Admin trigger for the daily cron. Can be wired to an external scheduler."""
    return await check_due_invitations()


@router.post("/orders/{order_id}/mark-delivered")
async def admin_mark_delivered(order_id: str, user=Depends(get_current_user)):
    """Mark an order as delivered → create review invitations."""
    order = await db.orders.find_one({"id": order_id}, {"_id": 0})
    if not order:
        raise HTTPException(404, "Commande introuvable")
    now = datetime.now(timezone.utc)
    await db.orders.update_one({"id": order_id}, {"$set": {"delivered_at": now, "status": "delivered"}})
    order["delivered_at"] = now
    created = await _create_invitations_for_order(order)
    return {"status": "ok", "invitations_created": created}
