"""
Chantier 7 — Seed d'events factices dans db.storefront_events pour tester le
dashboard sans avoir à simuler un vrai parcours d'achat.

Usage :
  cd /app/backend
  python -m scripts.seed_analytics <site_id> [--events 50] [--days 7] [--no-purge]

Comportement :
  - Charge les vrais produits actifs du site (db.products.find status='active')
  - Si aucun produit → log un warning et abort (un seed sans vrais produits
    crée des events orphelins qui ne matchent jamais le catalogue dans les
    pipelines d'agrégation, ce qui faussait Top Produits et l'onglet Produits)
  - PURGE auto avant re-seed (idempotent) : supprime les events seed précédents
    (session_id startswith 'seed-' OU meta.seed=True OU product_id orphelin)
  - Insère les nouveaux events avec des UUIDs produit RÉELS

Exemple :
  python -m scripts.seed_analytics d33a5795-7a19-4a03-86a2-ef83ea19db9b --events 100 --days 30
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

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))
load_dotenv(BACKEND_DIR / ".env")

from motor.motor_asyncio import AsyncIOMotorClient  # noqa: E402

COUNTRIES = ["FR", "BE", "LU", "DE", "NL", "IT", "ES", "UK", "CH"]
LANGS = {"FR": "fr", "BE": "fr", "LU": "fr", "DE": "de", "NL": "nl",
         "IT": "it", "ES": "es", "UK": "en", "CH": "fr"}
PATHS = ["/", "/collection/mobilite", "/collection/confort", "/about", "/faq"]


async def _purge_old_seed_and_orphans(db, site_id: str, real_pids: set[str]) -> int:
    """Supprime les events factices précédents pour ce site :
       - tous les events dont session_id commence par 'seed-' (notre marker)
       - + les events avec meta.seed=True
       - + les events purchase/atc/begin_checkout dont le product_id ne matche
         AUCUN vrai produit du site (orphelins issus d'un autre script de seed)
    """
    deleted = 0
    res = await db.storefront_events.delete_many({
        "site_id": site_id,
        "$or": [
            {"session_id": {"$regex": "^seed-"}},
            {"meta.seed": True},
            {
                "product_id": {"$nin": list(real_pids), "$ne": None},
                "event": {"$in": ["product_view", "add_to_cart", "begin_checkout", "purchase"]},
            },
        ],
    })
    deleted = res.deleted_count
    return deleted


async def seed(site_id: str, n_events: int, days: int, do_purge: bool = True) -> int:
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]

    site = await db.sites.find_one({"id": site_id}, {"_id": 0, "id": 1, "name": 1})
    if not site:
        print(f"ERROR: site_id {site_id} not found in DB")
        return 0

    products = await db.products.find(
        {"site_id": site_id, "status": "active"},
        {"_id": 0, "id": 1, "price": 1, "name": 1},
    ).to_list(length=50)

    if not products:
        print(f"⚠ WARNING: site {site_id} ({site['name']}) has 0 active products. "
              f"Skipping seed (would only generate orphan events).")
        print(f"  → Importe d'abord des produits via le cockpit ou la sourcing page,")
        print(f"    puis re-lance ce script.")
        return 0

    real_pids = {p["id"] for p in products}

    if do_purge:
        deleted = await _purge_old_seed_and_orphans(db, site_id, real_pids)
        if deleted:
            print(f"✓ Purged {deleted} old seed/orphan events before re-seeding")

    now = datetime.now(timezone.utc)
    sessions_count = max(n_events // 3, 6)
    docs = []
    for _ in range(sessions_count):
        session_id = f"seed-{uuid.uuid4().hex[:12]}"
        country = random.choices(COUNTRIES, weights=[30, 10, 2, 20, 10, 8, 6, 10, 4])[0]
        lang = LANGS.get(country, "fr")
        day_offset = random.randint(0, max(days - 1, 0))
        hour_offset = random.randint(8, 22)
        base_t = now - timedelta(days=day_offset, hours=24 - hour_offset)

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
        prod_price = float(prod.get("price") or random.choice([29, 49, 79, 129, 249]))
        t = base_t
        for ev in path_taken:
            t = t + timedelta(minutes=random.randint(1, 4))
            doc = {
                "_id": str(uuid.uuid4()),
                "site_id": site_id,
                "event": ev,
                "session_id": session_id,
                "product_id": prod["id"] if ev in ("product_view", "add_to_cart", "begin_checkout", "purchase") else None,
                "value": prod_price if ev in ("add_to_cart", "begin_checkout", "purchase") else None,
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
    print(f"  Real products used : {len(real_pids)}")
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
    parser.add_argument("--no-purge", action="store_true",
                        help="Ne pas purger les events seed précédents avant insert")
    args = parser.parse_args()
    asyncio.run(seed(args.site_id, args.events, args.days, do_purge=not args.no_purge))


if __name__ == "__main__":
    main()
