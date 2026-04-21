"""Sprint 19 — Google Ads Center admin-only tests.

Scope:
- Status/markets endpoints: admin vs non-admin (role-based access)
- OAuth start returns authorization_url with expected fields
- OAuth callback without code redirects to error page
- Disconnect: admin-only, sets is_active=false
- Login Customer ID validation (10 digits, with/without hyphens)
- list_customers / keyword-ideas / campaigns: 401 when not connected
- Regression smoke tests on auth/sites endpoints
"""
import os
import re
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://senior-france.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN = {"email": "admin@conceptfactory.fr", "password": "Factory2026!"}
OPERATOR = {"email": "concepteur@conceptfactory.fr", "password": "Concepteur2026!"}


# ---------- fixtures ----------
@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json=ADMIN, timeout=15)
    if r.status_code != 200:
        pytest.skip(f"Admin login failed: {r.status_code} {r.text[:200]}")
    return s


@pytest.fixture(scope="module")
def operator_session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json=OPERATOR, timeout=15)
    if r.status_code != 200:
        pytest.skip(f"Operator login failed: {r.status_code} {r.text[:200]}")
    return s


@pytest.fixture(scope="module")
def anon_session():
    return requests.Session()


# ---------- /google-ads/status ----------
class TestStatus:
    def test_status_admin_ok(self, admin_session):
        r = admin_session.get(f"{API}/google-ads/status", timeout=10)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["config_ready"] is True, "GOOGLE_ADS_* env vars must be present"
        assert "connected" in data
        # No refresh_token yet in DB
        assert data["connected"] is False

    def test_status_operator_403(self, operator_session):
        r = operator_session.get(f"{API}/google-ads/status", timeout=10)
        assert r.status_code == 403, r.text

    def test_status_anon_401(self, anon_session):
        r = anon_session.get(f"{API}/google-ads/status", timeout=10)
        assert r.status_code in (401, 403), r.text


# ---------- /google-ads/markets ----------
class TestMarkets:
    def test_markets_admin(self, admin_session):
        r = admin_session.get(f"{API}/google-ads/markets", timeout=10)
        assert r.status_code == 200
        data = r.json()
        markets = data["markets"]
        assert isinstance(markets, list)
        assert len(markets) == 8
        codes = {m["code"] for m in markets}
        assert codes == {"FR", "DE", "BE", "NL", "UK", "CH", "ES", "IT"}
        for m in markets:
            assert "geo" in m and "lang" in m and "name" in m

    def test_markets_operator_403(self, operator_session):
        r = operator_session.get(f"{API}/google-ads/markets", timeout=10)
        assert r.status_code == 403


# ---------- /google-ads/oauth/start ----------
class TestOAuthStart:
    def test_oauth_start_admin(self, admin_session):
        r = admin_session.get(f"{API}/google-ads/oauth/start", timeout=10)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "authorization_url" in data
        url = data["authorization_url"]
        assert url.startswith("https://accounts.google.com/o/oauth2/auth")
        assert "client_id=" in url
        assert "redirect_uri=" in url
        assert "state=" in url
        assert "scope=" in url
        assert "adwords" in url  # URL-encoded scope contains 'adwords'
        assert data.get("state")

    def test_oauth_start_operator_403(self, operator_session):
        r = operator_session.get(f"{API}/google-ads/oauth/start", timeout=10)
        assert r.status_code == 403


# ---------- /google-ads/oauth/callback ----------
class TestOAuthCallback:
    def test_callback_missing_code_redirects_error(self, anon_session):
        # Callback is a public redirect endpoint (no auth)
        r = anon_session.get(f"{API}/google-ads/oauth/callback", timeout=10, allow_redirects=False)
        assert r.status_code in (302, 307)
        loc = r.headers.get("location", "")
        assert "/admin/google-ads" in loc
        assert "status=error" in loc

    def test_callback_error_param_redirects_error(self, anon_session):
        r = anon_session.get(
            f"{API}/google-ads/oauth/callback?error=access_denied",
            timeout=10, allow_redirects=False,
        )
        assert r.status_code in (302, 307)
        loc = r.headers.get("location", "")
        assert "status=error" in loc
        assert "access_denied" in loc


# ---------- /google-ads/login-customer-id ----------
class TestLoginCustomerId:
    def test_operator_forbidden(self, operator_session):
        r = operator_session.post(
            f"{API}/google-ads/login-customer-id",
            json={"login_customer_id": "1234567890"}, timeout=10,
        )
        assert r.status_code == 403

    def test_invalid_not_10_digits(self, admin_session):
        r = admin_session.post(
            f"{API}/google-ads/login-customer-id",
            json={"login_customer_id": "12345"}, timeout=10,
        )
        assert r.status_code == 400

    def test_invalid_non_digits(self, admin_session):
        r = admin_session.post(
            f"{API}/google-ads/login-customer-id",
            json={"login_customer_id": "ABCDEFGHIJ"}, timeout=10,
        )
        assert r.status_code == 400

    def test_valid_plain_10_digits(self, admin_session):
        r = admin_session.post(
            f"{API}/google-ads/login-customer-id",
            json={"login_customer_id": "1234567890"}, timeout=10,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["ok"] is True
        assert data["login_customer_id"] == "1234567890"

    def test_valid_with_hyphens(self, admin_session):
        r = admin_session.post(
            f"{API}/google-ads/login-customer-id",
            json={"login_customer_id": "123-456-7890"}, timeout=10,
        )
        assert r.status_code == 200, r.text
        assert r.json()["login_customer_id"] == "1234567890"


# ---------- /google-ads/customers ----------
class TestCustomers:
    def test_operator_403(self, operator_session):
        r = operator_session.get(f"{API}/google-ads/customers", timeout=15)
        assert r.status_code == 403

    def test_admin_not_connected_401(self, admin_session):
        r = admin_session.get(f"{API}/google-ads/customers", timeout=15)
        # No refresh_token stored → 401
        assert r.status_code == 401, r.text


# ---------- /google-ads/keyword-ideas ----------
class TestKeywordIdeas:
    def test_operator_403(self, operator_session):
        r = operator_session.post(
            f"{API}/google-ads/keyword-ideas",
            json={"customer_id": "1234567890", "seed_keywords": ["coussin"], "country": "FR"},
            timeout=15,
        )
        assert r.status_code == 403

    def test_admin_invalid_country(self, admin_session):
        r = admin_session.post(
            f"{API}/google-ads/keyword-ideas",
            json={"customer_id": "1234567890", "seed_keywords": ["test"], "country": "ZZ"},
            timeout=15,
        )
        assert r.status_code == 400, r.text

    def test_admin_not_connected_401(self, admin_session):
        r = admin_session.post(
            f"{API}/google-ads/keyword-ideas",
            json={"customer_id": "1234567890", "seed_keywords": ["coussin"], "country": "FR"},
            timeout=15,
        )
        # Valid country but no refresh_token → 401
        assert r.status_code == 401, r.text


# ---------- /google-ads/campaigns ----------
class TestCampaigns:
    def test_operator_403(self, operator_session):
        r = operator_session.post(
            f"{API}/google-ads/campaigns",
            json={"customer_id": "1234567890", "days": 30}, timeout=15,
        )
        assert r.status_code == 403

    def test_admin_not_connected_401(self, admin_session):
        r = admin_session.post(
            f"{API}/google-ads/campaigns",
            json={"customer_id": "1234567890", "days": 30}, timeout=15,
        )
        assert r.status_code == 401, r.text

    def test_payload_validation_missing_customer_id(self, admin_session):
        r = admin_session.post(f"{API}/google-ads/campaigns", json={"days": 30}, timeout=15)
        assert r.status_code == 422


# ---------- /google-ads/disconnect ----------
class TestDisconnect:
    def test_operator_403(self, operator_session):
        r = operator_session.post(f"{API}/google-ads/disconnect", timeout=10)
        assert r.status_code == 403

    def test_admin_ok(self, admin_session):
        # Must be called last-ish: marks is_active=false so subsequent
        # status call must still be connected=false
        r = admin_session.post(f"{API}/google-ads/disconnect", timeout=10)
        assert r.status_code == 200, r.text
        assert r.json()["ok"] is True

        # Verify persistence via status
        r2 = admin_session.get(f"{API}/google-ads/status", timeout=10)
        assert r2.status_code == 200
        assert r2.json()["connected"] is False


# ---------- Regression: existing routes ----------
class TestRegression:
    def test_auth_me_admin(self, admin_session):
        r = admin_session.get(f"{API}/auth/me", timeout=10)
        assert r.status_code == 200
        assert r.json()["role"] == "admin"

    def test_auth_me_operator(self, operator_session):
        r = operator_session.get(f"{API}/auth/me", timeout=10)
        assert r.status_code == 200
        assert r.json()["role"] in ("operator", "concepteur")

    def test_sites_list_admin(self, admin_session):
        r = admin_session.get(f"{API}/sites", timeout=10)
        assert r.status_code == 200
        assert isinstance(r.json(), list)
