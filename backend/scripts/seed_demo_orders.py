"""
Seed de commandes 'paid' pour la démo dashboard Finance.

Crée 3 commandes propres pour un site :
- status='paid', payment_status='paid'
- created_at = datetime UTC réel (pas string), dans la fenêtre 30j
- total_eur réaliste, items avec vrais produits du site

Idempotent : purge les anciennes commandes seed (order_number commence par 'SEED-')
avant d'insérer les nouvelles.

Usage :
  cd /app/backend
  python -m scripts.seed_demo_orders <site_id> [--count 3]
"""
import argparse
import asyncio
import os
import random
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))
load_dotenv(BACKEND_DIR / ".env")

from motor.motor_asyncio import AsyncIOMotorClient  # noqa: E402

DEMO_CUSTOMERS = [
    ("Marie Durand", "marie.durand@example.fr", "FR"),
    ("Thomas Klein", "thomas.klein@example.de", "DE"),
    ("Sophie Bernard", "sophie.bernard@example.fr", "FR"),
    ("Lucas De Vries", "lucas.devries@example.nl", "NL"),
    ("Giulia Rossi", "giulia.rossi@example.it", "IT"),
]


async def seed(site_id: str, count: int) -> int:
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]

    site = await db.sites.find_one({"id": site_id}, {"_id": 0, "id": 1, "name": 1})
    if not site:
        print(f"ERROR: site_id {site_id} not found")
        return 0

    products = await db.products.find(
        {"site_id": site_id, "status": "active"},
        {"_id": 0, "id": 1, "name": 1, "price": 1},
    ).to_list(length=20)
    if not products:
        print("⚠ Site has no active products, can't seed orders")
        return 0

    # Purge anciens orders seed
    purged = await db.orders.delete_many({"site_id": site_id, "order_number": {"$regex": "^SEED-"}})
    if purged.deleted_count:
        print(f"✓ Purged {purged.deleted_count} old seed orders")

    # Génère N commandes réparties sur les 30 derniers jours
    now = datetime.now(timezone.utc)
    docs = []
    for i in range(count):
        days_back = random.randint(1, 28)
        hours_back = random.randint(0, 23)
        created = now - timedelta(days=days_back, hours=hours_back)
        # 1 à 3 items par commande
        n_items = random.randint(1, 3)
        chosen = random.sample(products, min(n_items, len(products)))
        items = []
        subtotal = 0.0
        for p in chosen:
            qty = random.randint(1, 2)
            unit_price = float(p.get("price") or 39.0)
            line_total = round(unit_price * qty, 2)
            subtotal += line_total
            name = p.get("name")
            title = name.get("fr") if isinstance(name, dict) else str(name or "")
            items.append({
                "product_id": p["id"],
                "title": title,
                "quantity": qty,
                "unit_price_eur": unit_price,
                "line_total_eur": line_total,
            })
        shipping = round(random.choice([0.0, 4.99, 6.99]), 2)
        total = round(subtotal + shipping, 2)
        customer_name, customer_email, country = random.choice(DEMO_CUSTOMERS)
        order_id = str(uuid.uuid4())
        order_number = f"SEED-{int(created.timestamp())}-{random.randint(1000, 9999)}"
        doc = {
            "id": order_id,
            "site_id": site_id,
            "order_number": order_number,
            "customer_name": customer_name,
            "customer_email": customer_email,
            "shipping_country": country,
            "country": country,
            "currency": "EUR",
            "items": items,
            "subtotal_eur": round(subtotal, 2),
            "shipping_eur": shipping,
            "total": total,
            "total_eur": total,
            "status": "paid",
            "payment_status": "paid",
            "fulfillment_status": random.choice(["pending", "shipped", "delivered"]),
            "created_at": created,           # datetime UTC, pas string
            "paid_at": created + timedelta(minutes=random.randint(1, 15)),
            "source": "seed_demo",
        }
        docs.append(doc)

    if docs:
        await db.orders.insert_many(docs)
    print(f"✓ Inserted {len(docs)} demo orders for site {site_id} ({site['name']})")
    for d in docs:
        items_str = ", ".join(f"{i['quantity']}× {i['title'][:30]}" for i in d["items"])
        print(f"    · {d['order_number']} · {d['total']:.2f} € · {d['shipping_country']} · {d['created_at'].date()} · {items_str}")
    return len(docs)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("site_id")
    parser.add_argument("--count", type=int, default=3)
    args = parser.parse_args()
    asyncio.run(seed(args.site_id, args.count))


if __name__ == "__main__":
    main()
