"""TÂCHE 1 — End-to-end smoke test du tunnel commande sur Altea.

1. Crée un order public via l'API (POST /api/public/sites/{id}/orders)
2. Simule un webhook 'paid' via /api/admin/qa/simulate-paid-webhook (admin)
3. Vérifie en DB :
   - orders.status = paid
   - email_log : entry order_confirmation envoyée
   - admin_notifications : entry "new_order"

Tous les logs vont sur stdout pour audit.
"""
from __future__ import annotations

import asyncio
import os
import sys
import json
from datetime import datetime, timezone

import httpx

sys.path.insert(0, "/app/backend")
from motor.motor_asyncio import AsyncIOMotorClient

BASE_URL = "http://localhost:8001"
ALTEA_ID = "6867223e-7ea5-45a7-815a-300cd89b7656"
PRODUCT_ID = "2a31bb75-4dcf-424d-ab2f-cda6b88303fb"
ADMIN_EMAIL = "admin@conceptfactory.fr"
ADMIN_PASSWORD = "Factory2026!"

# Customer test (FR lang to validate detect_order_lang)
TEST_CUSTOMER = {
    "name": "QA Tunnel",
    "email": os.environ.get("RESEND_OWNER_EMAIL")
              or "owner@altiaro.com",
    "phone": "+33600000001",
    "lang": "fr",
}
TEST_ADDRESS = {
    "name": "QA Tunnel",
    "line1": "1 rue de la République",
    "city": "Paris",
    "postal_code": "75001",
    "country": "FR",
    "country_code": "FR",
}


async def main():
    print(f"[smoke] {datetime.now(timezone.utc).isoformat()} START\n")

    # Login admin to get cookies for QA endpoint
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=60) as cli:
        r_login = await cli.post("/api/auth/login",
                                  json={"email": ADMIN_EMAIL,
                                        "password": ADMIN_PASSWORD})
        assert r_login.status_code == 200, f"login failed: {r_login.text}"
        # Cookies set with Secure flag → httpx won't replay on http://
        # Extract access_token manually from Set-Cookie header.
        access_token = None
        for set_cookie in r_login.headers.get_list("set-cookie") if hasattr(r_login.headers, "get_list") else []:
            if set_cookie.startswith("access_token="):
                access_token = set_cookie.split(";", 1)[0].split("=", 1)[1]
                break
        if not access_token:
            # Fallback : iterate raw cookies dict
            access_token = r_login.cookies.get("access_token")
        if not access_token:
            # Last resort : parse manually from raw header
            raw = r_login.headers.get("set-cookie", "")
            for piece in raw.split(", "):
                if piece.startswith("access_token="):
                    access_token = piece.split(";", 1)[0].split("=", 1)[1]
                    break
        admin_headers = {"Cookie": f"access_token={access_token}"} if access_token else {}
        print(f"[smoke] admin login OK  token={access_token[:30] if access_token else 'NONE'}...")

        # 1. Create order
        order_payload = {
            "items": [{
                "product_id": PRODUCT_ID,
                "name": "Fauteuil releveur électrique avec massage",
                "price": 1211.18,
                "quantity": 1,
                "currency": "EUR",
            }],
            "customer": TEST_CUSTOMER,
            "shipping_address": TEST_ADDRESS,
            "language": "fr",
            "notes": "QA tunnel test",
        }
        r_order = await cli.post(
            f"/api/public/sites/{ALTEA_ID}/orders",
            json=order_payload,
            headers={"x-forwarded-for": "127.0.0.99"},
        )
        if r_order.status_code != 200:
            print(f"[smoke] order create FAILED {r_order.status_code}: {r_order.text[:300]}")
            return
        order = r_order.json()
        order_id = order["id"]
        order_number = order["order_number"]
        print(f"[smoke] order created  id={order_id[:8]}  number={order_number}  total={order.get('total')}€  status={order.get('status')}")

        # 2. Simulate webhook paid
        r_sim = await cli.post(
            f"/api/admin/qa/simulate-paid-webhook?order_id={order_id}",
            headers=admin_headers,
        )
        if r_sim.status_code != 200:
            print(f"[smoke] simulate-paid FAILED {r_sim.status_code}: {r_sim.text[:300]}")
            return
        sim = r_sim.json()
        print(f"[smoke] simulate-paid OK")
        print(json.dumps(sim, indent=2, ensure_ascii=False))

    # 3. DB checks
    c = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = c[os.environ["DB_NAME"]]
    db_order = await db.orders.find_one({"id": order_id}, {"_id": 0})
    print("\n[smoke] DB orders entry:")
    print(f"  status            : {db_order.get('status')}")
    print(f"  paid_at           : {db_order.get('paid_at')}")
    print(f"  customer.lang     : {(db_order.get('customer') or {}).get('lang')}")
    print(f"  language          : {db_order.get('language')}")
    print(f"  mollie_payment_id : {db_order.get('mollie_payment_id')}")
    print(f"  payment_method    : {db_order.get('payment_method')}")

    email_logs = await db.email_log.find(
        {"site_id": ALTEA_ID,
         "tags.0": {"$in": [{"name": "order_confirmation", "value": "1"},
                             {"name": "admin_notification", "value": "1"}]}},
        {"_id": 0},
    ).sort("created_at", -1).limit(5).to_list(5)
    # Use raw query — tags check may not match. Refetch broadly
    email_logs = await db.email_log.find(
        {"site_id": ALTEA_ID},
        {"_id": 0},
    ).sort("created_at", -1).limit(4).to_list(4)
    print(f"\n[smoke] DB email_log (last 4 for site):")
    for e in email_logs:
        tags = e.get("tags") or []
        tag_names = [t.get("name") if isinstance(t, dict) else str(t) for t in tags]
        print(f"  - {e.get('created_at')} | {e.get('status')} | to={e.get('to')} | "
              f"from={e.get('from')} | reply_to={e.get('reply_to')} | dkim={e.get('dkim_verified')} | "
              f"tags={tag_names} | subject={e.get('subject','')[:80]}")

    notifs = await db.admin_notifications.find(
        {"order_id": order_id},
        {"_id": 0},
    ).to_list(5)
    print(f"\n[smoke] DB admin_notifications for this order : {len(notifs)} entries")
    for n in notifs:
        print(f"  - type={n.get('type')} title={n.get('title')} customer_lang={n.get('customer_lang')}")

    print(f"\n[smoke] DONE {datetime.now(timezone.utc).isoformat()}")


if __name__ == "__main__":
    asyncio.run(main())
