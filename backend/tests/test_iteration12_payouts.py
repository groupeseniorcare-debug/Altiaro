"""
Sprint 13 — Tests pour le système de payouts (virements bi-mensuels).

Couverture :
- POST /api/sites/{id}/products avec cost_price_ht
- PATCH /api/sites/{id}/products/{id} met à jour cost_price_ht
- POST /api/public/sites/{id}/orders calcule subtotal_ht/cost_ht/gross_margin_ht/vat_rate
- log_order_share_on_paid loggue 50% * gross_margin_ht
- GET /api/admin/billing/payouts-preview structure complète + site_breakdown
- POST /api/admin/billing/run-payouts crée payouts pending pour Concepteurs avec IBAN
- POST /api/admin/billing/payouts/{id}/mark-paid → status=paid
- POST /api/admin/billing/payouts/{id}/cancel → status=cancelled
- GET /api/admin/billing/payouts-history enrichi avec concepteur_name/email
- mark-paid retire le Concepteur du preview
- run-payouts skippe les Concepteurs sans IBAN
- VAT auto-déduit du 1er pays du site (FR=20%, DE=19%, BE/NL=21%, UK=20%, CH=7.7%)
- GET /api/admin/notifications + POST /api/admin/notifications/{id}/read
"""
import os
import sys
import uuid
import asyncio
import pytest
import requests
from datetime import datetime, timezone

# Load backend/.env so we can import routes.billing (needs MONGO_URL/DB_NAME)
def _load_backend_env():
    try:
        with open("/app/backend/.env") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                if k and k not in os.environ:
                    os.environ[k] = v
    except Exception:
        pass

_load_backend_env()

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # Fallback to frontend env file load
    try:
        with open("/app/frontend/.env") as f:
            for line in f:
                if line.startswith("REACT_APP_BACKEND_URL="):
                    BASE_URL = line.split("=", 1)[1].strip().strip('"').rstrip("/")
                    break
    except Exception:
        pass

API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@conceptfactory.fr"
ADMIN_PWD = "Factory2026!"
CONCEPTEUR_EMAIL = "concepteur@conceptfactory.fr"
CONCEPTEUR_PWD = "Concepteur2026!"


# ----------------- Fixtures ----------------- #
@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PWD}, timeout=30)
    if r.status_code != 200:
        pytest.skip(f"Admin login failed: {r.status_code} {r.text[:200]}")
    return s


@pytest.fixture(scope="module")
def concepteur_session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": CONCEPTEUR_EMAIL, "password": CONCEPTEUR_PWD}, timeout=30)
    if r.status_code != 200:
        pytest.skip(f"Concepteur login failed: {r.status_code} {r.text[:200]}")
    return s


@pytest.fixture(scope="module")
def concepteur_site(concepteur_session):
    """Récupère le 1er site du concepteur."""
    r = concepteur_session.get(f"{API}/sites", timeout=30)
    assert r.status_code == 200, r.text
    sites = r.json()
    assert sites, "Concepteur n'a aucun site"
    return sites[0]


@pytest.fixture(scope="module")
def db():
    """Direct MongoDB access for cleanup + log_order_share_on_paid trigger."""
    sys.path.insert(0, "/app/backend")
    from motor.motor_asyncio import AsyncIOMotorClient
    mongo_url = os.environ.get("MONGO_URL")
    db_name = os.environ.get("DB_NAME")
    if not mongo_url or not db_name:
        # Read backend/.env directly
        with open("/app/backend/.env") as f:
            for line in f:
                if line.startswith("MONGO_URL=") and not mongo_url:
                    mongo_url = line.split("=", 1)[1].strip().strip('"')
                if line.startswith("DB_NAME=") and not db_name:
                    db_name = line.split("=", 1)[1].strip().strip('"')
    client = AsyncIOMotorClient(mongo_url)
    return client[db_name]


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


# ----------------- TESTS Produits ----------------- #
class TestProductsCostHT:
    def test_create_product_with_cost_price_ht(self, concepteur_session, concepteur_site):
        site_id = concepteur_site["id"]
        payload = {
            "name": {"fr": "TEST_PROD_S13_A", "en": "", "de": "", "nl": ""},
            "description": {"fr": "test sprint13"},
            "price": 120.0,
            "cost_price_ht": 35.0,
            "currency": "EUR",
            "images": [],
            "stock": 100,
            "supplier_url": "",
            "sku": "TEST-S13-A",
            "status": "active",
        }
        r = concepteur_session.post(f"{API}/sites/{site_id}/products", json=payload, timeout=30)
        assert r.status_code in (200, 201), r.text
        prod = r.json()
        assert prod["price"] == 120.0
        assert prod["cost_price_ht"] == 35.0
        assert prod.get("id"), "Product should have an id"
        # GET to verify persistence
        r2 = concepteur_session.get(f"{API}/sites/{site_id}/products", timeout=30)
        assert r2.status_code == 200
        products = r2.json()
        match = [p for p in products if p["id"] == prod["id"]]
        assert match and match[0]["cost_price_ht"] == 35.0
        # Save for later tests
        pytest.shared_product_id = prod["id"]

    def test_update_product_cost_price_ht(self, concepteur_session, concepteur_site):
        site_id = concepteur_site["id"]
        pid = getattr(pytest, "shared_product_id", None)
        assert pid, "Product must be created first"
        r = concepteur_session.patch(
            f"{API}/sites/{site_id}/products/{pid}",
            json={"cost_price_ht": 40.0},
            timeout=30,
        )
        assert r.status_code in (200, 204), r.text
        # Verify
        r2 = concepteur_session.get(f"{API}/sites/{site_id}/products", timeout=30)
        match = [p for p in r2.json() if p["id"] == pid][0]
        assert match["cost_price_ht"] == 40.0


# ----------------- TESTS Public order avec snapshot HT ----------------- #
class TestPublicOrderHT:
    def test_create_public_order_calculates_ht(self, concepteur_session, concepteur_site):
        """Crée un produit, fait une commande publique, vérifie subtotal_ht/cost_ht/gross_margin_ht."""
        site_id = concepteur_site["id"]
        # Produit dédié
        payload = {
            "name": {"fr": "TEST_S13_ORDER", "en": "", "de": "", "nl": ""},
            "price": 120.0,
            "cost_price_ht": 35.0,
            "currency": "EUR",
            "images": [],
            "stock": 100,
            "sku": "TEST-S13-ORDER",
            "status": "active",
        }
        r = concepteur_session.post(f"{API}/sites/{site_id}/products", json=payload, timeout=30)
        assert r.status_code in (200, 201), r.text
        prod = r.json()
        pytest.shared_order_product_id = prod["id"]

        # Public order — 2 unités
        order_payload = {
            "items": [{
                "product_id": prod["id"],
                "name": "TEST_S13_ORDER",
                "price": 120.0,
                "quantity": 2,
                "currency": "EUR",
            }],
            "customer": {"name": "Test Buyer", "email": "buyer@test.com", "phone": "0600000000"},
            "shipping_address": {
                "line1": "1 rue test", "city": "Paris", "postal_code": "75001",
                "country": "France", "country_code": "FR",
            },
            "language": "fr",
        }
        r = requests.post(f"{API}/public/sites/{site_id}/orders", json=order_payload, timeout=30)
        assert r.status_code in (200, 201), r.text
        order = r.json()

        # Marie's site is Luméa Confort → FR → vat=0.20
        # 2 * 120 = 240 TTC
        # subtotal_ht = 240 / 1.20 = 200
        # cost_ht = 35 * 2 = 70
        # gross_margin_ht = 200 - 70 = 130
        assert order["subtotal"] == 240.0
        assert abs(order["subtotal_ht"] - 200.0) < 0.05, f"subtotal_ht={order['subtotal_ht']}"
        assert order["cost_ht"] == 70.0
        assert abs(order["gross_margin_ht"] - 130.0) < 0.05, f"gross_margin_ht={order['gross_margin_ht']}"
        # VAT rate présent
        assert "vat_rate" in order, "vat_rate missing"
        assert abs(float(order["vat_rate"]) - 0.20) < 0.001, f"vat_rate={order['vat_rate']}"
        pytest.shared_order = order


# ----------------- TESTS log_order_share_on_paid ----------------- #
class TestLogOrderShareOnPaid:
    def test_log_order_share_uses_gross_margin_ht(self, db):
        """Trigger log_order_share_on_paid manuellement et vérifie share = 50% * gross_margin_ht."""
        order = getattr(pytest, "shared_order", None)
        assert order, "order fixture missing"
        # Cleanup any existing entry for this order
        _run(db.ledger.delete_many({"order_id": order["id"]}))
        # Import & trigger
        sys.path.insert(0, "/app/backend")
        from routes.billing import log_order_share_on_paid
        _run(log_order_share_on_paid(order))

        entry = _run(db.ledger.find_one({"order_id": order["id"], "type": "order_share"}))
        assert entry, "Ledger entry not created"
        # gross_margin_ht=130 → share=65
        assert entry["status"] == "paid"
        assert abs(entry["amount"] - 65.0) < 0.01, f"amount={entry['amount']}"
        assert abs(entry["gross_margin_ht"] - 130.0) < 0.05
        assert abs(entry["revenue_ht"] - 200.0) < 0.05
        assert abs(entry["cost_ht"] - 70.0) < 0.05
        # NOT the old (50% * total TTC = 120)
        assert entry["amount"] != 120.0


# ----------------- TESTS Payouts preview / run / mark-paid / cancel ----------------- #
class TestPayoutsFlow:
    def test_payouts_preview_structure(self, admin_session):
        r = admin_session.get(f"{API}/admin/billing/payouts-preview", timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "count" in data
        assert "total_due_eur" in data
        assert "next_cycle_date" in data
        assert "rows" in data
        assert isinstance(data["rows"], list)
        # Should have at least the concepteur with the 65€ entry from previous test
        marie = next((r for r in data["rows"] if r["email"] == CONCEPTEUR_EMAIL), None)
        assert marie, f"Marie not in preview rows: {[r['email'] for r in data['rows']]}"
        # Check fields
        for k in ("revenue_ht_total", "cost_ht_total", "gross_margin_ht_total",
                  "net_due_eur", "has_iban", "site_breakdown"):
            assert k in marie, f"missing key {k}"
        assert marie["has_iban"] is True
        assert marie["net_due_eur"] >= 65.0
        # net_due should be 50% * gross_margin_ht_total
        assert abs(marie["net_due_eur"] - 0.5 * marie["gross_margin_ht_total"]) < 0.05
        assert isinstance(marie["site_breakdown"], list)
        assert len(marie["site_breakdown"]) >= 1
        sb = marie["site_breakdown"][0]
        for k in ("site_id", "site_name", "revenue_ht", "cost_ht", "gross_margin_ht", "concepteur_share"):
            assert k in sb, f"site_breakdown missing {k}"
        # IBAN exposed
        assert marie.get("iban"), "IBAN should be in plain in preview"

    def test_run_payouts_creates_pending_entries(self, admin_session, db):
        # Cleanup existing pending payouts for marie
        marie_uid = _run(db.users.find_one({"email": CONCEPTEUR_EMAIL}))
        if marie_uid:
            uid = str(marie_uid["_id"])
            _run(db.ledger.delete_many({"concepteur_id": uid, "type": "payout"}))

        r = admin_session.post(f"{API}/admin/billing/run-payouts", timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["ok"] is True
        assert data["payouts_created"] >= 1
        pytest.shared_payouts_created = data["payouts_created"]

    def test_payouts_history_includes_pending(self, admin_session):
        r = admin_session.get(f"{API}/admin/billing/payouts-history?limit=50", timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert "items" in data
        # Find pending payout for marie
        marie_pending = [
            e for e in data["items"]
            if e.get("type") == "payout" and e.get("status") == "pending"
            and e.get("concepteur_email") == CONCEPTEUR_EMAIL
        ]
        assert marie_pending, f"No pending payout for marie. Items: {data['items'][:3]}"
        # Check enrichment
        p = marie_pending[0]
        assert p.get("concepteur_name"), "concepteur_name missing in history enrichment"
        assert p.get("concepteur_email") == CONCEPTEUR_EMAIL
        pytest.shared_payout_id = p["id"]

    def test_preview_excludes_after_run(self, admin_session):
        """Après run-payouts, le net_due de marie doit être 0 (payout pending compte dans payouts_total)."""
        r = admin_session.get(f"{API}/admin/billing/payouts-preview", timeout=30)
        data = r.json()
        marie = next((r for r in data["rows"] if r["email"] == CONCEPTEUR_EMAIL), None)
        # marie should not appear (net_due <= 0.009 → filtré)
        assert marie is None, f"Marie should be excluded from preview after run-payouts: {marie}"

    def test_mark_payout_paid(self, admin_session, db):
        pid = getattr(pytest, "shared_payout_id", None)
        assert pid
        r = admin_session.post(f"{API}/admin/billing/payouts/{pid}/mark-paid", timeout=30)
        assert r.status_code == 200, r.text
        # Verify in db
        entry = _run(db.ledger.find_one({"id": pid}))
        assert entry["status"] == "paid"
        assert entry.get("paid_by") == ADMIN_EMAIL
        assert entry.get("paid_at")

    def test_mark_paid_idempotency_404(self, admin_session):
        pid = getattr(pytest, "shared_payout_id", None)
        # second call should 404 (already paid, not pending)
        r = admin_session.post(f"{API}/admin/billing/payouts/{pid}/mark-paid", timeout=30)
        assert r.status_code == 404

    def test_cancel_payout(self, admin_session, db):
        """Crée un nouveau pending payout puis l'annule."""
        # Add a synthetic order_share so net_due > 0 again
        order = getattr(pytest, "shared_order", None)
        marie_uid = _run(db.users.find_one({"email": CONCEPTEUR_EMAIL}))
        uid = str(marie_uid["_id"])
        # New share entry
        new_id = str(uuid.uuid4())
        _run(db.ledger.insert_one({
            "id": new_id,
            "concepteur_id": uid,
            "site_id": order["site_id"],
            "type": "order_share",
            "status": "paid",
            "amount": 30.0,
            "revenue_ht": 60.0,
            "cost_ht": 0.0,
            "gross_margin_ht": 60.0,
            "order_id": f"TEST_S13_CANCEL_{uuid.uuid4().hex[:6]}",
            "currency": "EUR",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }))
        r = admin_session.post(f"{API}/admin/billing/run-payouts", timeout=30)
        assert r.status_code == 200
        # Find new pending
        h = admin_session.get(f"{API}/admin/billing/payouts-history?limit=50", timeout=30).json()
        pending = [e for e in h["items"] if e.get("status") == "pending" and e.get("concepteur_email") == CONCEPTEUR_EMAIL]
        assert pending
        new_payout_id = pending[0]["id"]
        # Cancel
        r = admin_session.post(f"{API}/admin/billing/payouts/{new_payout_id}/cancel", timeout=30)
        assert r.status_code == 200
        entry = _run(db.ledger.find_one({"id": new_payout_id}))
        assert entry["status"] == "cancelled"
        assert entry.get("cancelled_by") == ADMIN_EMAIL


# ----------------- TESTS Skip Concepteur sans IBAN ----------------- #
class TestPayoutsSkipNoIban:
    def test_run_payouts_skips_no_iban(self, admin_session, db):
        """Crée un user fictif operator avec order_share mais sans iban → skippé."""
        fake_uid = str(uuid.uuid4())
        # Insert fake operator user (use _id as ObjectId requires bson; use uuid string)
        # _compute_balance uses concepteur_id key in ledger, and admin_payouts_preview uses op["id"]
        # which is str(_id) → this won't match unless we insert with ObjectId
        from bson import ObjectId
        oid = ObjectId()
        _run(db.users.insert_one({
            "_id": oid,
            "email": f"TEST_NOIBAN_{uuid.uuid4().hex[:6]}@test.com",
            "name": "TEST No IBAN",
            "role": "operator",
            "password_hash": "$2b$12$test",
        }))
        uid_str = str(oid)
        # Add a paid order_share
        _run(db.ledger.insert_one({
            "id": str(uuid.uuid4()),
            "concepteur_id": uid_str,
            "type": "order_share",
            "status": "paid",
            "amount": 50.0,
            "gross_margin_ht": 100.0,
            "revenue_ht": 100.0,
            "cost_ht": 0.0,
            "currency": "EUR",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }))
        # Capture before
        before = admin_session.post(f"{API}/admin/billing/run-payouts", timeout=30).json()
        # Should NOT have created a payout for fake user (no iban)
        # Verify by counting payouts of fake_uid
        payouts_for_fake = _run(db.ledger.count_documents({"concepteur_id": uid_str, "type": "payout"}))
        assert payouts_for_fake == 0, f"Expected 0 payouts for no-IBAN user, got {payouts_for_fake}"
        # Cleanup
        _run(db.users.delete_one({"_id": oid}))
        _run(db.ledger.delete_many({"concepteur_id": uid_str}))


# ----------------- TESTS VAT auto par pays ----------------- #
class TestVATByCountry:
    def test_vat_rates_via_helper(self):
        sys.path.insert(0, "/app/backend")
        from tax_utils import site_vat_rate
        assert abs(site_vat_rate({"selected_countries": ["FR"]}) - 0.20) < 0.001
        assert abs(site_vat_rate({"selected_countries": ["DE"]}) - 0.19) < 0.001
        assert abs(site_vat_rate({"selected_countries": ["BE"]}) - 0.21) < 0.001
        assert abs(site_vat_rate({"selected_countries": ["NL"]}) - 0.21) < 0.001
        assert abs(site_vat_rate({"selected_countries": ["UK"]}) - 0.20) < 0.001
        assert abs(site_vat_rate({"selected_countries": ["CH"]}) - 0.077) < 0.001
        # Override priority
        assert abs(site_vat_rate({"vat_rate": 0.10, "selected_countries": ["FR"]}) - 0.10) < 0.001
        # Default fallback
        assert abs(site_vat_rate({}) - 0.20) < 0.001


# ----------------- TESTS Notifications admin ----------------- #
class TestAdminNotifications:
    def test_list_notifications(self, admin_session):
        r = admin_session.get(f"{API}/admin/notifications", timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert "count" in data and "items" in data

    def test_mark_notification_read(self, admin_session, db):
        # Insert a synthetic notification
        nid = str(uuid.uuid4())
        _run(db.admin_notifications.insert_one({
            "id": nid,
            "type": "test",
            "message": "TEST_S13_NOTIF",
            "read": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }))
        r = admin_session.post(f"{API}/admin/notifications/{nid}/read", timeout=30)
        assert r.status_code == 200
        notif = _run(db.admin_notifications.find_one({"id": nid}))
        assert notif["read"] is True
        # cleanup
        _run(db.admin_notifications.delete_one({"id": nid}))


# ----------------- TESTS Auth/Permission ----------------- #
class TestAuthGuards:
    def test_concepteur_cannot_access_payouts_preview(self, concepteur_session):
        r = concepteur_session.get(f"{API}/admin/billing/payouts-preview", timeout=30)
        assert r.status_code in (401, 403), f"Expected 401/403, got {r.status_code}"

    def test_concepteur_cannot_run_payouts(self, concepteur_session):
        r = concepteur_session.post(f"{API}/admin/billing/run-payouts", timeout=30)
        assert r.status_code in (401, 403)


# ----------------- Cleanup ----------------- #
@pytest.fixture(scope="module", autouse=True)
def _final_cleanup(request, db):
    yield
    # Remove TEST_S13 products + ledger entries
    try:
        _run(db.products.delete_many({"sku": {"$regex": "^TEST-S13"}}))
        _run(db.orders.delete_many({"items.name": {"$regex": "^TEST_S13"}}))
        _run(db.ledger.delete_many({"order_id": {"$regex": "^TEST_S13"}}))
        # Mark Marie's payouts as cancelled to leave clean state
        marie_uid = _run(db.users.find_one({"email": CONCEPTEUR_EMAIL}))
        if marie_uid:
            uid = str(marie_uid["_id"])
            _run(db.ledger.delete_many({"concepteur_id": uid, "type": "payout"}))
            # Also remove the synthetic order_share entries we added
            _run(db.ledger.delete_many({"concepteur_id": uid, "type": "order_share",
                                        "order_id": {"$regex": "^TEST_S13"}}))
    except Exception as e:
        print(f"Cleanup error: {e}")
