"""Iteration 18 — Customer order detail + guest tracking.

Validates new endpoints:
  - GET  /api/public/sites/{sid}/customers/orders/{order_id}   (customer JWT)
  - GET  /api/public/sites/{sid}/orders/{order_number}?email=  (guest tracking)

Data prerequisites (already seeded):
  - Site Sereniva: d7d84968-0a2e-44c4-880b-f5af736cc86d
  - Customer   : buyer.demo@altiaro.fr / Buyer2026!
  - Orders     : ALT-DEMO-0001 (shipped), ALT-DEMO-0002 (delivered, with pending review invitation)
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://senior-france.preview.emergentagent.com").rstrip("/")
SITE_ID = "d7d84968-0a2e-44c4-880b-f5af736cc86d"
CUST_EMAIL = "buyer.demo@altiaro.fr"
CUST_PWD = "Buyer2026!"
ORDER_SHIPPED = "ALT-DEMO-0001"
ORDER_DELIVERED = "ALT-DEMO-0002"


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def customer_auth(session):
    r = session.post(
        f"{BASE_URL}/api/public/sites/{SITE_ID}/customers/login",
        json={"email": CUST_EMAIL, "password": CUST_PWD},
    )
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    data = r.json()
    assert "token" in data and data["customer"]["email"] == CUST_EMAIL
    return data


@pytest.fixture(scope="module")
def auth_headers(customer_auth):
    return {"Authorization": f"Bearer {customer_auth['token']}", "Content-Type": "application/json"}


# ------------------------------------------------------------------ #
#  Customer /me + /orders (sanity)                                   #
# ------------------------------------------------------------------ #
class TestCustomerSanity:
    def test_me(self, session, auth_headers):
        r = session.get(f"{BASE_URL}/api/public/sites/{SITE_ID}/customers/me", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["email"] == CUST_EMAIL

    def test_orders_list_contains_seeded(self, session, auth_headers):
        r = session.get(f"{BASE_URL}/api/public/sites/{SITE_ID}/customers/orders", headers=auth_headers)
        assert r.status_code == 200
        orders = r.json()
        numbers = {o.get("order_number") for o in orders}
        assert ORDER_SHIPPED in numbers, f"Missing {ORDER_SHIPPED} in {numbers}"
        assert ORDER_DELIVERED in numbers, f"Missing {ORDER_DELIVERED} in {numbers}"


# ------------------------------------------------------------------ #
#  GET /customers/orders/{order_id} (authenticated detail)           #
# ------------------------------------------------------------------ #
class TestCustomerOrderDetail:
    def test_detail_by_order_number_delivered(self, session, auth_headers):
        r = session.get(
            f"{BASE_URL}/api/public/sites/{SITE_ID}/customers/orders/{ORDER_DELIVERED}",
            headers=auth_headers,
        )
        assert r.status_code == 200, r.text
        o = r.json()
        assert o["order_number"] == ORDER_DELIVERED
        assert o["status"] == "delivered"
        # Enriched items
        assert isinstance(o.get("items"), list) and len(o["items"]) > 0
        for it in o["items"]:
            assert "product_image" in it
            assert "product_name_current" in it
        # Review invitations present
        assert "review_invitations" in o
        assert isinstance(o["review_invitations"], list)
        assert len(o["review_invitations"]) >= 1, "Expected pending review invitation on delivered order"
        inv = o["review_invitations"][0]
        assert "token" in inv and "product_id" in inv
        # status_history field present (array)
        assert "status_history" in o and isinstance(o["status_history"], list)

    def test_detail_by_id(self, session, auth_headers):
        # First fetch order by number to get id
        r0 = session.get(
            f"{BASE_URL}/api/public/sites/{SITE_ID}/customers/orders/{ORDER_SHIPPED}",
            headers=auth_headers,
        )
        assert r0.status_code == 200
        oid = r0.json()["id"]
        r = session.get(
            f"{BASE_URL}/api/public/sites/{SITE_ID}/customers/orders/{oid}",
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert r.json()["order_number"] == ORDER_SHIPPED

    def test_detail_shipped_has_tracking(self, session, auth_headers):
        r = session.get(
            f"{BASE_URL}/api/public/sites/{SITE_ID}/customers/orders/{ORDER_SHIPPED}",
            headers=auth_headers,
        )
        assert r.status_code == 200
        o = r.json()
        assert o["status"] == "shipped"
        # review_invitations likely empty for non-delivered
        assert "review_invitations" in o

    def test_detail_requires_auth(self, session):
        r = session.get(f"{BASE_URL}/api/public/sites/{SITE_ID}/customers/orders/{ORDER_SHIPPED}")
        assert r.status_code == 401

    def test_detail_invalid_token(self, session):
        r = session.get(
            f"{BASE_URL}/api/public/sites/{SITE_ID}/customers/orders/{ORDER_SHIPPED}",
            headers={"Authorization": "Bearer invalid.jwt.token"},
        )
        assert r.status_code == 401

    def test_detail_nonexistent_order(self, session, auth_headers):
        r = session.get(
            f"{BASE_URL}/api/public/sites/{SITE_ID}/customers/orders/NOPE-9999",
            headers=auth_headers,
        )
        assert r.status_code == 404


# ------------------------------------------------------------------ #
#  GET /public/sites/{sid}/orders/{order_number}  (guest)            #
# ------------------------------------------------------------------ #
class TestGuestTracking:
    def test_no_email_returns_400(self, session):
        r = session.get(f"{BASE_URL}/api/public/sites/{SITE_ID}/orders/{ORDER_SHIPPED}")
        assert r.status_code == 400, f"Expected 400 (email required) got {r.status_code}: {r.text}"

    def test_empty_email_returns_400(self, session):
        r = session.get(f"{BASE_URL}/api/public/sites/{SITE_ID}/orders/{ORDER_SHIPPED}?email=")
        assert r.status_code == 400

    def test_wrong_email_returns_403(self, session):
        r = session.get(
            f"{BASE_URL}/api/public/sites/{SITE_ID}/orders/{ORDER_SHIPPED}",
            params={"email": "someone.else@example.com"},
        )
        assert r.status_code == 403

    def test_correct_email_returns_order(self, session):
        r = session.get(
            f"{BASE_URL}/api/public/sites/{SITE_ID}/orders/{ORDER_SHIPPED}",
            params={"email": CUST_EMAIL},
        )
        assert r.status_code == 200
        o = r.json()
        assert o["order_number"] == ORDER_SHIPPED
        assert o["status"] == "shipped"
        # Items enriched
        for it in o.get("items", []):
            assert "product_image" in it

    def test_nonexistent_order_returns_404(self, session):
        r = session.get(
            f"{BASE_URL}/api/public/sites/{SITE_ID}/orders/NOPE-9999",
            params={"email": CUST_EMAIL},
        )
        assert r.status_code == 404

    def test_case_insensitive_email(self, session):
        r = session.get(
            f"{BASE_URL}/api/public/sites/{SITE_ID}/orders/{ORDER_SHIPPED}",
            params={"email": CUST_EMAIL.upper()},
        )
        assert r.status_code == 200
