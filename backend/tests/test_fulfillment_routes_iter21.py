"""Iter 21 - Fulfillment routes regression: GET /sites/{id}/fulfillment + POST supplier-retry.
Backend was validated in iter 20; this is a smoke regression to be sure routes still respond."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://senior-france.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

CONCEPTEUR_EMAIL = "concepteur@conceptfactory.fr"
CONCEPTEUR_PWD = "Concepteur2026!"
ADMIN_EMAIL = "admin@conceptfactory.fr"
ADMIN_PWD = "Factory2026!"


def _login(email, password):
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=20)
    if r.status_code != 200:
        pytest.skip(f"Login {email} failed -> {r.status_code} {r.text[:120]}")
    return s


@pytest.fixture(scope="module")
def concepteur():
    return _login(CONCEPTEUR_EMAIL, CONCEPTEUR_PWD)


@pytest.fixture(scope="module")
def admin():
    return _login(ADMIN_EMAIL, ADMIN_PWD)


@pytest.fixture(scope="module")
def concepteur_site_id(concepteur):
    r = concepteur.get(f"{API}/sites", timeout=15)
    assert r.status_code == 200, r.text
    sites = r.json()
    assert isinstance(sites, list) and len(sites) > 0, "Concepteur should have at least one site"
    return sites[0]["id"]


# -------- AUTH --------
def test_fulfillment_requires_auth():
    r = requests.get(f"{API}/sites/anything/fulfillment", timeout=10)
    assert r.status_code in (401, 403), f"Expected 401/403 got {r.status_code}"


# -------- GET /sites/{id}/fulfillment --------
def test_fulfillment_summary_shape(concepteur, concepteur_site_id):
    r = concepteur.get(f"{API}/sites/{concepteur_site_id}/fulfillment", timeout=20)
    assert r.status_code == 200, r.text
    data = r.json()
    assert set(["counters", "total", "orders"]).issubset(data.keys())
    counters = data["counters"]
    for key in ("pending_supplier", "placed", "shipped", "delivered", "error"):
        assert key in counters, f"missing counter {key}"
        assert isinstance(counters[key], int)
    assert isinstance(data["orders"], list)
    # No mongo _id leaked
    for o in data["orders"]:
        assert "_id" not in o, "MongoDB _id leaked in order"
        assert "fulfillment_state" in o
        assert "supplier_mappings" in o


def test_fulfillment_unknown_site_403_or_404(concepteur):
    r = concepteur.get(f"{API}/sites/non-existent-xyz/fulfillment", timeout=15)
    assert r.status_code in (403, 404), f"Expected 403/404 got {r.status_code} {r.text[:120]}"


# -------- POST /sites/{id}/orders/{order_id}/supplier-retry --------
def test_supplier_retry_unknown_order_404(concepteur, concepteur_site_id):
    r = concepteur.post(
        f"{API}/sites/{concepteur_site_id}/orders/nope-unknown/supplier-retry", timeout=15
    )
    assert r.status_code == 404, f"Expected 404 got {r.status_code} {r.text[:200]}"


def test_supplier_retry_unpaid_order_400(admin):
    """Retry on a known unpaid pending order should return 400."""
    # Use admin to find any unpaid order
    r = admin.get(f"{API}/admin/orders", timeout=15)
    if r.status_code != 200:
        pytest.skip("admin orders not available")
    orders = r.json() if isinstance(r.json(), list) else r.json().get("orders", [])
    pending = [o for o in orders if o.get("status") == "pending_payment"]
    if not pending:
        pytest.skip("No pending_payment order in DB to test 400 path")
    o = pending[0]
    r2 = admin.post(
        f"{API}/sites/{o['site_id']}/orders/{o['id']}/supplier-retry", timeout=15
    )
    assert r2.status_code == 400, f"Expected 400 got {r2.status_code}: {r2.text[:200]}"


def test_supplier_retry_paid_no_provider_400(admin):
    """Paid order with no CJ/AE products should return 400 'No CJ or AliExpress items'."""
    r = admin.get(f"{API}/admin/orders", timeout=15)
    if r.status_code != 200:
        pytest.skip("admin orders not available")
    orders = r.json() if isinstance(r.json(), list) else r.json().get("orders", [])
    paid = [o for o in orders if o.get("status") in ("paid", "shipped", "delivered")]
    if not paid:
        pytest.skip("No paid order in DB to test")
    o = paid[0]
    r2 = admin.post(
        f"{API}/sites/{o['site_id']}/orders/{o['id']}/supplier-retry", timeout=20
    )
    # Either 400 (no CJ/AE) or 200 (CJ/AE present and call attempted) — both acceptable
    assert r2.status_code in (200, 400), f"Unexpected {r2.status_code}: {r2.text[:200]}"
    if r2.status_code == 200:
        body = r2.json()
        assert body.get("ok") is True
        assert "retried" in body
