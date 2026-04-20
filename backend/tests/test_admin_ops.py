"""
Phase 4 — Admin Ops Center + rate-limit + refactor non-regression tests.

Covers:
- Non-regression on existing endpoints (auth, sites, public shop, orders site-level, dashboard, meta, niches)
- NEW admin endpoints: GET /api/admin/orders, GET /api/admin/orders/stats,
  PATCH /api/admin/orders/{id}, GET /api/admin/orders/export.csv
- Rate-limit 10/IP/10min on public order creation
- _meta_ip leak check (public + admin) + status_history leak on public lookup

NOTE: The backend is reached via the public REACT_APP_BACKEND_URL.
"""
import os
import time
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://senior-france.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"
ADMIN_EMAIL = "admin@conceptfactory.fr"
ADMIN_PASSWORD = "Factory2026!"


# -----------------------------
# Shared fixtures
# -----------------------------
@pytest.fixture(scope="session")
def admin_session():
    """Authenticated admin requests session (cookie-based)."""
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=30)
    assert r.status_code == 200, f"Admin login failed: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="session")
def test_site(admin_session):
    """Create a test site; cleanup at end of session."""
    payload = {"name": f"TEST_P4_{uuid.uuid4().hex[:6]}", "niche": "Mobilite-seniors"}
    r = admin_session.post(f"{API}/sites", json=payload, timeout=30)
    assert r.status_code in (200, 201), f"Create site failed: {r.status_code} {r.text}"
    site = r.json()
    yield site
    try:
        admin_session.delete(f"{API}/sites/{site['id']}", timeout=30)
    except Exception:
        pass


@pytest.fixture(scope="session")
def test_product(admin_session, test_site):
    """Create an active product for checkout tests."""
    payload = {
        "name": {"fr": "TEST Produit", "en": "TEST Product", "de": "", "nl": ""},
        "description": {"fr": "desc", "en": "desc", "de": "", "nl": ""},
        "price": 29.90,
        "currency": "EUR",
        "images": ["https://via.placeholder.com/300"],
        "status": "active",
        "featured": True,
    }
    r = admin_session.post(f"{API}/sites/{test_site['id']}/products", json=payload, timeout=30)
    assert r.status_code in (200, 201), f"Create product failed: {r.status_code} {r.text}"
    return r.json()


# -----------------------------
# Non-regression after refactor
# -----------------------------
class TestNonRegression:
    def test_auth_me(self, admin_session):
        r = admin_session.get(f"{API}/auth/me", timeout=30)
        assert r.status_code == 200
        assert r.json()["email"] == ADMIN_EMAIL

    def test_auth_login_wrong_password(self):
        r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": "wrong"}, timeout=30)
        assert r.status_code == 401

    def test_sites_list(self, admin_session):
        r = admin_session.get(f"{API}/sites", timeout=30)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_site_get(self, admin_session, test_site):
        r = admin_session.get(f"{API}/sites/{test_site['id']}", timeout=30)
        assert r.status_code == 200
        assert r.json()["id"] == test_site["id"]

    def test_steps_list(self, admin_session, test_site):
        r = admin_session.get(f"{API}/sites/{test_site['id']}/steps", timeout=30)
        assert r.status_code == 200
        steps = r.json()
        assert isinstance(steps, list)
        assert len(steps) == 50  # 50 steps seed

    def test_products_list(self, admin_session, test_site, test_product):
        r = admin_session.get(f"{API}/sites/{test_site['id']}/products", timeout=30)
        assert r.status_code == 200
        ids = [p["id"] for p in r.json()]
        assert test_product["id"] in ids

    def test_niches_catalog(self, admin_session):
        r = admin_session.get(f"{API}/niches", timeout=30)
        assert r.status_code == 200
        assert len(r.json()) >= 1

    def test_dashboard(self, admin_session):
        r = admin_session.get(f"{API}/dashboard/kpis", timeout=30)
        assert r.status_code == 200

    def test_meta_phases(self, admin_session):
        r = admin_session.get(f"{API}/meta/phases", timeout=30)
        assert r.status_code == 200

    def test_public_site(self, test_site):
        r = requests.get(f"{API}/public/sites/{test_site['id']}", timeout=30)
        assert r.status_code == 200
        assert r.json()["id"] == test_site["id"]

    def test_public_products(self, test_site, test_product):
        r = requests.get(f"{API}/public/sites/{test_site['id']}/products", timeout=30)
        assert r.status_code == 200
        assert any(p["id"] == test_product["id"] for p in r.json())

    def test_site_level_orders_requires_auth(self, test_site):
        r = requests.get(f"{API}/sites/{test_site['id']}/orders", timeout=30)
        assert r.status_code == 401


# -----------------------------
# NEW: Admin Ops Center
# -----------------------------
def _build_order_payload(product):
    return {
        "items": [{"product_id": product["id"], "name": "TEST", "price": product["price"], "quantity": 2}],
        "customer": {"name": "TEST Client", "email": "TEST_client@example.com", "phone": "+33600000001"},
        "shipping_address": {
            "line1": "1 rue de Test", "postal_code": "75001",
            "city": "Paris", "country": "France", "country_code": "FR",
        },
        "language": "fr",
        "notes": "",
    }


class TestAdminOrders:
    @pytest.fixture(scope="class")
    def sample_order(self, test_site, test_product):
        payload = _build_order_payload(test_product)
        r = requests.post(f"{API}/public/sites/{test_site['id']}/orders", json=payload, timeout=30)
        assert r.status_code == 200, f"Create order failed: {r.status_code} {r.text}"
        return r.json()

    def test_admin_orders_requires_auth(self):
        r = requests.get(f"{API}/admin/orders", timeout=30)
        assert r.status_code == 401

    def test_admin_orders_requires_admin_role(self):
        # anonymous → 401; operator-role not covered here (would need a seeded op)
        r = requests.get(f"{API}/admin/orders/stats", timeout=30)
        assert r.status_code == 401

    def test_admin_orders_list_shape(self, admin_session, sample_order):
        r = admin_session.get(f"{API}/admin/orders", timeout=30)
        assert r.status_code == 200
        body = r.json()
        assert "total" in body and "items" in body
        assert isinstance(body["items"], list)
        assert body["total"] >= 1

    def test_admin_orders_no_meta_ip_leak(self, admin_session, sample_order):
        r = admin_session.get(f"{API}/admin/orders", timeout=30)
        assert r.status_code == 200
        for item in r.json()["items"]:
            assert "_meta_ip" not in item, f"_meta_ip leaked in admin/orders item: {item}"

    def test_admin_orders_filter_by_status(self, admin_session, sample_order):
        r = admin_session.get(f"{API}/admin/orders", params={"status": "pending_payment"}, timeout=30)
        assert r.status_code == 200
        for item in r.json()["items"]:
            assert item["status"] == "pending_payment"

    def test_admin_orders_filter_by_site(self, admin_session, test_site, sample_order):
        r = admin_session.get(f"{API}/admin/orders", params={"site_id": test_site["id"]}, timeout=30)
        assert r.status_code == 200
        for item in r.json()["items"]:
            assert item["site_id"] == test_site["id"]

    def test_admin_orders_filter_by_q(self, admin_session, sample_order):
        r = admin_session.get(f"{API}/admin/orders", params={"q": sample_order["order_number"]}, timeout=30)
        assert r.status_code == 200
        assert any(it["order_number"] == sample_order["order_number"] for it in r.json()["items"])

    def test_admin_orders_stats_shape(self, admin_session):
        r = admin_session.get(f"{API}/admin/orders/stats", timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert "by_status" in data
        assert "total_count" in data
        assert "total_revenue" in data
        expected_statuses = {"pending_payment", "paid", "shipped", "delivered", "cancelled", "refunded"}
        assert expected_statuses.issubset(set(data["by_status"].keys()))
        for st, v in data["by_status"].items():
            assert "count" in v and "revenue" in v

    def test_admin_patch_order_valid_transition(self, admin_session, sample_order):
        # pending_payment → paid (allowed)
        r = admin_session.patch(
            f"{API}/admin/orders/{sample_order['id']}",
            json={"status": "paid", "note": "Test paid"},
            timeout=30,
        )
        assert r.status_code == 200, f"Transition failed: {r.status_code} {r.text}"
        body = r.json()
        assert body["status"] == "paid"
        assert isinstance(body.get("status_history"), list) and len(body["status_history"]) >= 1
        last = body["status_history"][-1]
        assert last["from"] == "pending_payment"
        assert last["to"] == "paid"
        assert last.get("note") == "Test paid"
        assert "at" in last and "by" in last

    def test_admin_patch_order_invalid_transition(self, admin_session, sample_order):
        # After previous test, order is paid → pending_payment should be rejected
        r = admin_session.patch(
            f"{API}/admin/orders/{sample_order['id']}",
            json={"status": "pending_payment", "note": "illegal"},
            timeout=30,
        )
        assert r.status_code == 400

    def test_admin_patch_order_invalid_status(self, admin_session, sample_order):
        r = admin_session.patch(
            f"{API}/admin/orders/{sample_order['id']}",
            json={"status": "not_a_status", "note": ""},
            timeout=30,
        )
        assert r.status_code == 400

    def test_admin_patch_order_not_found(self, admin_session):
        r = admin_session.patch(
            f"{API}/admin/orders/{uuid.uuid4()}",
            json={"status": "paid", "note": ""},
            timeout=30,
        )
        assert r.status_code == 404

    def test_admin_orders_export_csv(self, admin_session):
        r = admin_session.get(f"{API}/admin/orders/export.csv", timeout=30)
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("text/csv")
        assert "attachment" in r.headers.get("content-disposition", "").lower()
        # First line must be the header
        first_line = r.text.splitlines()[0]
        assert "order_number" in first_line
        assert "customer_email" in first_line
        assert "total" in first_line


# -----------------------------
# NEW: Public order lookup — no leaks
# -----------------------------
class TestPublicOrderNoLeak:
    def test_public_lookup_no_meta_ip_and_no_status_history(self, test_site, test_product, admin_session):
        # create & advance to have status_history present in DB
        payload = _build_order_payload(test_product)
        r = requests.post(f"{API}/public/sites/{test_site['id']}/orders", json=payload, timeout=30)
        assert r.status_code == 200
        order = r.json()
        # ensure creator response itself has no _meta_ip
        assert "_meta_ip" not in order
        # push a status change to generate history
        rp = admin_session.patch(
            f"{API}/admin/orders/{order['id']}",
            json={"status": "paid", "note": "noleak"},
            timeout=30,
        )
        assert rp.status_code == 200
        # public lookup must not expose _meta_ip nor status_history
        rl = requests.get(
            f"{API}/public/sites/{test_site['id']}/orders/{order['order_number']}",
            timeout=30,
        )
        assert rl.status_code == 200
        body = rl.json()
        assert "_meta_ip" not in body, f"_meta_ip leaked in public lookup: {body}"
        assert "status_history" not in body, f"status_history leaked in public lookup: {body}"


# -----------------------------
# NEW: Rate limit 10/IP/10min
# -----------------------------
class TestRateLimit:
    def test_rate_limit_11th_request_returns_429(self, test_site, test_product):
        """Create 10 orders fast, then the 11th must 429.
        This shares the backend's view of the caller IP (ingress), so we rely on count_documents
        on _meta_ip. Depending on prior tests, we might already have some orders from this IP
        in the 10-min window; therefore we loop until 429 within at most 12 extra attempts.
        """
        payload = _build_order_payload(test_product)
        session = requests.Session()
        hit_429 = False
        last_status = None
        for _ in range(12):
            r = session.post(f"{API}/public/sites/{test_site['id']}/orders", json=payload, timeout=30)
            last_status = r.status_code
            if r.status_code == 429:
                hit_429 = True
                break
            assert r.status_code == 200, f"Unexpected status during rate-limit probe: {r.status_code} {r.text}"
        assert hit_429, f"Expected 429 after 10 recent orders, last status={last_status}"
