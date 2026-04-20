"""
Concept Factory — Phase 3 MVP shop regression tests.
Covers: products CRUD with i18n, public storefront listing (status=active only, featured sort),
public orders with server-side total recomputation, order lookup, admin orders listing.
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
assert BASE_URL, "REACT_APP_BACKEND_URL must be set"
ADMIN_EMAIL = "admin@conceptfactory.fr"
ADMIN_PASSWORD = "Factory2026!"


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login",
               json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
               timeout=15)
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def site(admin_session):
    """Create a test site and clean it up afterwards."""
    r = admin_session.post(f"{BASE_URL}/api/sites",
                           json={"name": "TEST_Shop Site P3", "niche": "Seniors",
                                 "niche_slug": "canne-pliante-premium"},
                           timeout=20)
    assert r.status_code == 200, r.text
    site = r.json()
    yield site
    # Teardown: delete site (also cascades steps/financials)
    admin_session.delete(f"{BASE_URL}/api/sites/{site['id']}", timeout=10)
    # Cleanup any remaining products/orders for this site
    # (server doesn't cascade these; we do it manually via direct admin calls)


# ---------------------------- PRODUCTS CRUD ----------------------------
class TestProductsCRUD:
    def test_list_products_requires_auth(self, site):
        r = requests.get(f"{BASE_URL}/api/sites/{site['id']}/products", timeout=10)
        assert r.status_code == 401

    def test_create_product_i18n(self, admin_session, site):
        payload = {
            "name": {"fr": "Canne pliante", "en": "Folding cane",
                     "de": "Faltstock", "nl": "Vouwstok"},
            "description": {"fr": "Légère et robuste", "en": "Light and sturdy",
                            "de": "Leicht und robust", "nl": "Licht en stevig"},
            "price": 29.90,
            "currency": "EUR",
            "images": ["https://example.com/cane.jpg"],
            "status": "active",
            "featured": False,
            "sku": "TEST-CANE-01",
        }
        r = admin_session.post(f"{BASE_URL}/api/sites/{site['id']}/products",
                               json=payload, timeout=15)
        assert r.status_code == 200, r.text
        p = r.json()
        assert p["id"]
        assert p["site_id"] == site["id"]
        assert p["name"]["fr"] == "Canne pliante"
        assert p["name"]["de"] == "Faltstock"
        assert p["price"] == 29.90
        assert p["status"] == "active"
        assert p["featured"] is False
        # Persistence: GET
        gr = admin_session.get(f"{BASE_URL}/api/sites/{site['id']}/products/{p['id']}", timeout=10)
        assert gr.status_code == 200
        assert gr.json()["sku"] == "TEST-CANE-01"
        site.setdefault("_products", []).append(p["id"])
        site["_active_id"] = p["id"]

    def test_create_second_featured_product(self, admin_session, site):
        payload = {
            "name": {"fr": "Loupe éclairante", "en": "Lit magnifier",
                     "de": "Beleuchtete Lupe", "nl": "Verlichte loep"},
            "price": 19.50,
            "images": ["https://example.com/loupe.jpg"],
            "status": "active",
            "featured": True,
        }
        r = admin_session.post(f"{BASE_URL}/api/sites/{site['id']}/products",
                               json=payload, timeout=15)
        assert r.status_code == 200, r.text
        p = r.json()
        assert p["featured"] is True
        site.setdefault("_products", []).append(p["id"])
        site["_featured_id"] = p["id"]

    def test_create_draft_product_should_not_leak_public(self, admin_session, site):
        payload = {
            "name": {"fr": "Brouillon", "en": "Draft", "de": "Entwurf", "nl": "Concept"},
            "price": 10.0,
            "status": "draft",
        }
        r = admin_session.post(f"{BASE_URL}/api/sites/{site['id']}/products",
                               json=payload, timeout=15)
        assert r.status_code == 200
        p = r.json()
        assert p["status"] == "draft"
        site.setdefault("_products", []).append(p["id"])
        site["_draft_id"] = p["id"]

    def test_list_products_admin_sees_all(self, admin_session, site):
        r = admin_session.get(f"{BASE_URL}/api/sites/{site['id']}/products", timeout=10)
        assert r.status_code == 200
        items = r.json()
        # Should include active + featured + draft
        assert len(items) >= 3
        statuses = {i["status"] for i in items}
        assert "draft" in statuses
        assert "active" in statuses

    def test_patch_product_partial(self, admin_session, site):
        pid = site["_active_id"]
        r = admin_session.patch(
            f"{BASE_URL}/api/sites/{site['id']}/products/{pid}",
            json={"price": 34.90, "featured": True},
            timeout=10,
        )
        assert r.status_code == 200
        p = r.json()
        assert p["price"] == 34.90
        assert p["featured"] is True
        # Other fields untouched
        assert p["sku"] == "TEST-CANE-01"

    def test_patch_status_to_draft_hides_from_public(self, admin_session, site):
        pid = site["_active_id"]
        r = admin_session.patch(
            f"{BASE_URL}/api/sites/{site['id']}/products/{pid}",
            json={"status": "draft"},
            timeout=10,
        )
        assert r.status_code == 200
        assert r.json()["status"] == "draft"
        # Public detail should now 404
        pr = requests.get(
            f"{BASE_URL}/api/public/sites/{site['id']}/products/{pid}",
            timeout=10,
        )
        assert pr.status_code == 404
        # Restore to active for later tests
        admin_session.patch(
            f"{BASE_URL}/api/sites/{site['id']}/products/{pid}",
            json={"status": "active"},
            timeout=10,
        )

    def test_delete_product_then_404(self, admin_session, site):
        # Create a throwaway
        r = admin_session.post(
            f"{BASE_URL}/api/sites/{site['id']}/products",
            json={"name": {"fr": "Jetable"}, "price": 1.0, "status": "active"},
            timeout=10,
        )
        pid = r.json()["id"]
        dr = admin_session.delete(
            f"{BASE_URL}/api/sites/{site['id']}/products/{pid}", timeout=10,
        )
        assert dr.status_code == 200
        gr = admin_session.get(
            f"{BASE_URL}/api/sites/{site['id']}/products/{pid}", timeout=10,
        )
        assert gr.status_code == 404


# ---------------------------- PUBLIC STOREFRONT ----------------------------
class TestPublicStorefront:
    def test_public_site_no_auth(self, site):
        r = requests.get(f"{BASE_URL}/api/public/sites/{site['id']}", timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert data["id"] == site["id"]
        assert data["name"] == "TEST_Shop Site P3"
        # niche_data should be populated since niche_slug set
        assert "niche_data" in data
        assert data["niche_data"] is not None
        assert "name" in data["niche_data"]

    def test_public_site_404(self):
        r = requests.get(f"{BASE_URL}/api/public/sites/does-not-exist", timeout=10)
        assert r.status_code == 404

    def test_public_products_only_active_and_featured_first(self, site):
        r = requests.get(f"{BASE_URL}/api/public/sites/{site['id']}/products", timeout=10)
        assert r.status_code == 200
        items = r.json()
        # Only active products should appear
        for p in items:
            assert p["status"] == "active", f"Draft leaked: {p}"
        # Draft must not appear
        ids = {p["id"] for p in items}
        assert site["_draft_id"] not in ids, "Draft product leaked into public listing"
        # Featured must come first
        assert len(items) >= 2
        assert items[0]["featured"] is True, f"First item not featured: {items[0]}"

    def test_public_product_detail_active_only(self, site):
        # Featured product is active, should be accessible
        r = requests.get(
            f"{BASE_URL}/api/public/sites/{site['id']}/products/{site['_featured_id']}",
            timeout=10,
        )
        assert r.status_code == 200
        # Draft product should 404
        r2 = requests.get(
            f"{BASE_URL}/api/public/sites/{site['id']}/products/{site['_draft_id']}",
            timeout=10,
        )
        assert r2.status_code == 404


# ---------------------------- PUBLIC ORDERS ----------------------------
class TestPublicOrders:
    def _order_payload(self, site, items, total_hint=999.99):
        return {
            "items": items,
            "customer": {"name": "Jean Dupont", "email": "TEST_jean@example.fr",
                         "phone": "+33612345678"},
            "shipping_address": {"line1": "1 rue de Paris", "city": "Paris",
                                 "postal_code": "75001", "country": "France",
                                 "country_code": "FR"},
            "language": "fr",
            "notes": "Sonner deux fois",
        }

    def test_order_empty_items_400(self, site):
        payload = self._order_payload(site, items=[])
        r = requests.post(f"{BASE_URL}/api/public/sites/{site['id']}/orders",
                          json=payload, timeout=10)
        assert r.status_code == 400

    def test_order_invalid_site_404(self, site):
        payload = self._order_payload(site, items=[{
            "product_id": "x", "name": "x", "price": 10, "quantity": 1, "currency": "EUR"
        }])
        r = requests.post(f"{BASE_URL}/api/public/sites/nonexistent-site-id/orders",
                          json=payload, timeout=10)
        assert r.status_code == 404

    def test_order_under_50_has_shipping_fee(self, site):
        items = [{"product_id": site["_featured_id"], "name": "Loupe",
                  "price": 19.50, "quantity": 1, "currency": "EUR"}]
        payload = self._order_payload(site, items=items)
        r = requests.post(f"{BASE_URL}/api/public/sites/{site['id']}/orders",
                          json=payload, timeout=15)
        assert r.status_code == 200, r.text
        o = r.json()
        assert o["subtotal"] == 19.50
        assert o["shipping_fee"] == 4.90
        assert o["total"] == round(19.50 + 4.90, 2)
        assert o["order_number"].startswith("CF-")
        parts = o["order_number"].split("-")
        assert len(parts) == 3  # CF-{ts}-{hex}
        assert o["status"] == "pending_payment"
        assert o["currency"] == "EUR"
        site["_order_number_under"] = o["order_number"]

    def test_order_50_plus_free_shipping(self, site):
        items = [{"product_id": site["_featured_id"], "name": "Loupe",
                  "price": 19.50, "quantity": 3, "currency": "EUR"}]  # 58.50
        payload = self._order_payload(site, items=items)
        r = requests.post(f"{BASE_URL}/api/public/sites/{site['id']}/orders",
                          json=payload, timeout=15)
        assert r.status_code == 200, r.text
        o = r.json()
        assert o["subtotal"] == round(19.50 * 3, 2)
        assert o["shipping_fee"] == 0
        assert o["total"] == round(58.50, 2)
        site["_order_number_free"] = o["order_number"]

    def test_server_recomputes_total_ignoring_client_hint(self, site):
        """Even if client sent a fraudulent 'total' field, server recomputes from items."""
        items = [{"product_id": site["_featured_id"], "name": "Loupe",
                  "price": 19.50, "quantity": 1, "currency": "EUR"}]
        payload = self._order_payload(site, items=items)
        # Inject malicious total — server must IGNORE it
        payload["total"] = 0.01
        payload["subtotal"] = 0.01
        payload["shipping_fee"] = 0
        r = requests.post(f"{BASE_URL}/api/public/sites/{site['id']}/orders",
                          json=payload, timeout=15)
        assert r.status_code == 200, r.text
        o = r.json()
        assert o["subtotal"] == 19.50, f"Server trusted client subtotal: {o}"
        assert o["shipping_fee"] == 4.90
        assert o["total"] == round(19.50 + 4.90, 2)

    def test_order_lookup_by_number(self, site):
        num = site["_order_number_free"]
        r = requests.get(f"{BASE_URL}/api/public/sites/{site['id']}/orders/{num}",
                         timeout=10)
        assert r.status_code == 200
        o = r.json()
        assert o["order_number"] == num
        assert o["total"] == 58.50

    def test_order_lookup_unknown_404(self, site):
        r = requests.get(f"{BASE_URL}/api/public/sites/{site['id']}/orders/CF-0-XXXX",
                         timeout=10)
        assert r.status_code == 404

    def test_admin_orders_list(self, admin_session, site):
        r = admin_session.get(f"{BASE_URL}/api/sites/{site['id']}/orders", timeout=10)
        assert r.status_code == 200
        orders = r.json()
        assert len(orders) >= 3  # at least the 3 successful orders
        numbers = {o["order_number"] for o in orders}
        assert site["_order_number_under"] in numbers
        assert site["_order_number_free"] in numbers

    def test_admin_orders_requires_auth(self, site):
        r = requests.get(f"{BASE_URL}/api/sites/{site['id']}/orders", timeout=10)
        assert r.status_code == 401
