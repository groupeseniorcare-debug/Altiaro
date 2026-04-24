"""
Chantier 7 — Seed d'events factices dans db.storefront_events pour tester le
dashboard sans avoir à simuler un vrai parcours d'achat.

Usage :
  cd /app/backend
  python -m scripts.seed_analytics <site_id> [--events 50] [--days 7]

Exemple :
  python -m scripts.seed_analytics d33a5795-7a19-4a03-86a2-ef83ea19db9b --events 60 --days 7

Respecte la même shape que l'endpoint /track → tous les events passent par
les agrégations du dashboard sans modification.
"""
import argparse
import asyncio
import hashlib
import os
import random
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

# Permet d'exécuter depuis /app/backend ou /app
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))
load_dotenv(BACKEND_DIR / ".env")

from motor.motor_asyncio import AsyncIOMotorClient  # noqa: E402

COUNTRIES = ["FR", "BE", "LU", "DE", "NL", "IT", "ES", "UK", "CH"]
LANGS = {"FR": "fr", "BE": "fr", "LU": "fr", "DE": "de", "NL": "nl", "IT": "it", "ES": "es", "UK": "en", "CH": "fr"}
PATHS = ["/", "/collection/mobilite", "/collection/confort", "/about", "/faq"]


async def seed(site_id: str, n_events: int, days: int) -> int:
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]

    site = await db.sites.find_one({"id": site_id}, {"_id": 0, "id": 1, "name": 1})
    if not site:
        print(f"ERROR: site_id {site_id} not found in DB")
        return 0

    products = await db.products.find(
        {"site_id": site_id, "status": "active"},
        {"_id": 0, "id": 1, "price": 1},
    ).to_list(length=50)
    if not products:
        # Pas de produit réel → on génère 3 product_ids factices pour que les
        # graphes "top produits" ne soient pas vides
        products = [{"id": f"seed-prod-{i}", "price": random.choice([29, 49, 79, 129, 249])} for i in range(3)]

    now = datetime.now(timezone.utc)
    # Génère N sessions distinctes ; chaque session donne 2 à 6 events en
    # séquence sur une fenêtre "days"
    sessions_count = max(n_events // 3, 6)
    docs = []
    for _ in range(sessions_count):
        session_id = f"seed-{uuid.uuid4().hex[:12]}"
        country = random.choices(COUNTRIES, weights=[30, 10, 2, 20, 10, 8, 6, 10, 4])[0]
        lang = LANGS.get(country, "fr")
        day_offset = random.randint(0, max(days - 1, 0))
        hour_offset = random.randint(8, 22)
        base_t = now - timedelta(days=day_offset, hours=24 - hour_offset)

        # Parcours simulé : page_view → (product_view?) → (atc?) → (checkout?) → (purchase?)
        path_taken = ["page_view"]
        if random.random() < 0.75:
            path_taken.append("product_view")
        if random.random() < 0.25:
            path_taken.append("add_to_cart")
        if "add_to_cart" in path_taken and random.random() < 0.45:
            path_taken.append("begin_checkout")
        if "begin_checkout" in path_taken and random.random() < 0.55:
            path_taken.append("purchase")

        prod = random.choice(products)
        t = base_t
        for ev in path_taken:
            t = t + timedelta(minutes=random.randint(1, 4))
            doc = {
                "_id": str(uuid.uuid4()),
                "site_id": site_id,
                "event": ev,
                "session_id": session_id,
                "product_id": prod["id"] if ev in ("product_view", "add_to_cart", "begin_checkout", "purchase") else None,
                "value": float(prod["price"]) if ev in ("add_to_cart", "begin_checkout", "purchase") else None,
                "currency": "EUR" if ev in ("add_to_cart", "begin_checkout", "purchase") else None,
                "path": random.choice(PATHS) if ev == "page_view" else f"/product/{prod['id']}",
                "referrer": random.choice(["", "https://www.google.com/", "https://www.google.fr/", ""]),
                "country": country,
                "lang": lang,
                "user_agent": "Mozilla/5.0 (seed)",
                "ip_hash": hashlib.sha256(f"seed-{session_id}".encode()).hexdigest()[:32],
                "created_at": t,
                "meta": {"seed": True},
            }
            docs.append(doc)
            if len(docs) >= n_events:
                break
        if len(docs) >= n_events:
            break

    if not docs:
        print("No events generated")
        return 0

    result = await db.storefront_events.insert_many(docs)
    print(f"✓ Inserted {len(result.inserted_ids)} events for site {site_id} ({site['name']})")
    by_ev: dict = {}
    for d in docs:
        by_ev[d["event"]] = by_ev.get(d["event"], 0) + 1
    for ev, n in by_ev.items():
        print(f"    · {ev:15s} → {n}")
    return len(result.inserted_ids)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("site_id")
    parser.add_argument("--events", type=int, default=50)
    parser.add_argument("--days", type=int, default=7)
    args = parser.parse_args()
    asyncio.run(seed(args.site_id, args.events, args.days))


if __name__ == "__main__":
    main()
