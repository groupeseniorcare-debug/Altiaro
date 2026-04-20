"""Iter11 extras — covers paths that need direct DB manipulation:
- admin activate ads succeeds when mandate_id exists on billing_profile
- log_order_share_on_paid creates a ledger entry when an order is paid
"""
import os
import asyncio
import uuid
import pytest
import requests
import motor.motor_asyncio

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://senior-france.preview.emergentagent.com").rstrip("/")
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "launchos_database")

ADMIN = ("admin@conceptfactory.fr", "Factory2026!")
CONCEPTEUR = ("concepteur@conceptfactory.fr", "Concepteur2026!")


def _login(email, pw):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": pw}, timeout=15)
    assert r.status_code == 200
    return s


@pytest.fixture(scope="module")
def admin_sess():
    return _login(*ADMIN)


@pytest.fixture(scope="module")
def db():
    client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URL)
    return client[DB_NAME]


async def _get_concepteur_id(db):
    u = await db.users.find_one({"email": CONCEPTEUR[0]})
    return str(u["_id"]) if u else None


def test_activate_ads_succeeds_with_mandate(admin_sess, db):
    """Seed a fake mandate_id on concepteur's profile, then activation should succeed."""
    async def run():
        uid = await _get_concepteur_id(db)
        assert uid, "concepteur not found"
        # seed mandate
        await db.billing_profiles.update_one(
            {"user_id": uid},
            {"$set": {
                "user_id": uid,
                "mandate_id": "mdt_TEST_ITER11",
                "mandate_status": "valid",
                "mollie_customer_id": "cst_TEST_ITER11",
                "card_last4": "4242",
                "card_brand": "visa",
            }},
            upsert=True,
        )
        return uid

    uid = asyncio.get_event_loop().run_until_complete(run())

    # find a site owned by this operator
    r = admin_sess.get(f"{BASE_URL}/api/sites", timeout=10)
    sites = r.json()
    site = next((s for s in sites if s.get("operator_id") == uid), None)
    assert site, "no site for concepteur"

    r = admin_sess.post(f"{BASE_URL}/api/admin/sites/{site['id']}/ads/activate", timeout=10)
    assert r.status_code == 200, r.text[:300]
    data = r.json()
    assert data["ads_active"] is True
    assert data.get("ads_activated_at")

    # deactivate + cleanup mandate
    admin_sess.post(f"{BASE_URL}/api/admin/sites/{site['id']}/ads/deactivate", timeout=10)

    async def cleanup():
        await db.billing_profiles.update_one(
            {"user_id": uid},
            {"$unset": {"mandate_id": "", "mandate_status": "",
                        "mollie_customer_id": "", "card_last4": "", "card_brand": ""}},
        )
    asyncio.get_event_loop().run_until_complete(cleanup())


def test_order_share_hook_creates_ledger_entry(db):
    """Directly call log_order_share_on_paid to verify the webhook hook path."""
    import sys
    sys.path.insert(0, "/app/backend")
    from dotenv import load_dotenv
    load_dotenv("/app/backend/.env")
    from routes.billing import log_order_share_on_paid

    async def run():
        uid = await _get_concepteur_id(db)
        # find a site owned by concepteur
        site = await db.sites.find_one({"operator_id": uid})
        assert site, "no site"

        order_id = f"TEST_ORDER_{uuid.uuid4().hex[:8]}"
        order = {
            "id": order_id,
            "order_number": f"CF-TEST-{uuid.uuid4().hex[:6]}",
            "site_id": site["id"],
            "total": 100.00,
            "currency": "EUR",
        }
        # count before
        before = await db.ledger.count_documents({"concepteur_id": uid, "type": "order_share"})
        await log_order_share_on_paid(order)
        after = await db.ledger.count_documents({"concepteur_id": uid, "type": "order_share"})
        assert after == before + 1

        entry = await db.ledger.find_one({"order_id": order_id})
        assert entry is not None
        assert entry["type"] == "order_share"
        assert entry["status"] == "paid"
        assert abs(float(entry["amount"]) - 50.00) < 0.01
        assert entry["concepteur_id"] == uid

        # cleanup
        await db.ledger.delete_one({"order_id": order_id})

    asyncio.get_event_loop().run_until_complete(run())
