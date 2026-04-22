"""
Iteration 19 — Cockpit Tools (pricing-analysis, financial-forecast, upsell-recommendations).
Validates new linear 9-step Cockpit Journey endpoints + site-scoping.
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://senior-france.preview.emergentagent.com").rstrip("/")
TEST_SITE_ID = "65964cb0-7a1a-4c11-9644-1ad8f2371d48"

CONCEPTEUR = {"email": "concepteur@conceptfactory.fr", "password": "Concepteur2026!"}
ADMIN = {"email": "admin@conceptfactory.fr", "password": "Factory2026!"}


def _login(creds):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json=creds, timeout=15)
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text[:200]}"
    return s


@pytest.fixture(scope="module")
def concepteur_session():
    return _login(CONCEPTEUR)


@pytest.fixture(scope="module")
def admin_session():
    return _login(ADMIN)


# -----------------------------------------------------------
# GET endpoints — empty state
# -----------------------------------------------------------
class TestCockpitGetEmpty:
    def test_pricing_get_empty_returns_dict(self, concepteur_session):
        r = concepteur_session.get(f"{BASE_URL}/api/sites/{TEST_SITE_ID}/pricing-analysis", timeout=15)
        assert r.status_code == 200, r.text[:200]
        data = r.json()
        assert isinstance(data, dict)
        # New site - should be empty {} OR {} stored from previous run; allow either but no error
        # Acceptable: {} or has generated_at
        if data:
            assert "generated_at" in data or data == {}

    def test_forecast_get_empty(self, concepteur_session):
        r = concepteur_session.get(f"{BASE_URL}/api/sites/{TEST_SITE_ID}/financial-forecast", timeout=15)
        assert r.status_code == 200
        assert isinstance(r.json(), dict)

    def test_upsells_get_empty(self, concepteur_session):
        r = concepteur_session.get(f"{BASE_URL}/api/sites/{TEST_SITE_ID}/upsell-recommendations", timeout=15)
        assert r.status_code == 200
        assert isinstance(r.json(), dict)


# -----------------------------------------------------------
# POST endpoints — error cases when no products
# -----------------------------------------------------------
class TestCockpitPostNoProducts:
    def test_forecast_post_no_products_returns_400(self, concepteur_session):
        r = concepteur_session.post(
            f"{BASE_URL}/api/sites/{TEST_SITE_ID}/financial-forecast",
            json={"site_id": TEST_SITE_ID},
            timeout=20,
        )
        assert r.status_code == 400, f"Expected 400, got {r.status_code}: {r.text[:200]}"
        assert "produit" in r.text.lower()

    def test_upsells_post_no_products_returns_400(self, concepteur_session):
        r = concepteur_session.post(
            f"{BASE_URL}/api/sites/{TEST_SITE_ID}/upsell-recommendations",
            json={"site_id": TEST_SITE_ID},
            timeout=20,
        )
        assert r.status_code == 400, f"Expected 400, got {r.status_code}: {r.text[:200]}"


# -----------------------------------------------------------
# Pricing POST — Claude integration (graceful 502 acceptable)
# -----------------------------------------------------------
class TestPricingClaude:
    def test_pricing_post_returns_snapshot_or_502(self, concepteur_session):
        r = concepteur_session.post(
            f"{BASE_URL}/api/sites/{TEST_SITE_ID}/pricing-analysis",
            json={"site_id": TEST_SITE_ID},
            timeout=120,
        )
        # 502 (LLM key exhausted) is acceptable per handoff
        assert r.status_code in (200, 402, 502), f"Unexpected status: {r.status_code} {r.text[:300]}"
        if r.status_code == 200:
            data = r.json()
            assert "generated_at" in data
            assert "market_overview" in data or "competitors" in data or "recommended_ranges" in data
            assert data.get("niche") or data.get("countries")

            # Verify persistence via GET
            r2 = concepteur_session.get(f"{BASE_URL}/api/sites/{TEST_SITE_ID}/pricing-analysis", timeout=15)
            assert r2.status_code == 200
            saved = r2.json()
            assert saved.get("generated_at") == data["generated_at"]


# -----------------------------------------------------------
# Site-scoping — Concepteur cannot access other sites
# -----------------------------------------------------------
class TestSiteScoping:
    def test_concepteur_cannot_access_foreign_site_pricing(self, concepteur_session, admin_session):
        # Find a site NOT owned by concepteur
        r = admin_session.get(f"{BASE_URL}/api/sites", timeout=15)
        assert r.status_code == 200
        all_sites = r.json()
        # Get concepteur's user id
        me = concepteur_session.get(f"{BASE_URL}/api/auth/me", timeout=15).json()
        concepteur_id = me.get("id")

        foreign = None
        for s in all_sites:
            if s.get("operator_id") and s.get("operator_id") != concepteur_id and s.get("id") != TEST_SITE_ID:
                foreign = s
                break
            if not s.get("operator_id") and s.get("id") != TEST_SITE_ID:
                foreign = s
                break
        if not foreign:
            pytest.skip("No foreign site found to test scoping")

        r = concepteur_session.get(
            f"{BASE_URL}/api/sites/{foreign['id']}/pricing-analysis", timeout=15
        )
        assert r.status_code in (403, 404), f"Expected 403/404, got {r.status_code}"

    def test_concepteur_can_access_own_site(self, concepteur_session):
        r = concepteur_session.get(f"{BASE_URL}/api/sites/{TEST_SITE_ID}/pricing-analysis", timeout=15)
        assert r.status_code == 200


# -----------------------------------------------------------
# Unauth check
# -----------------------------------------------------------
class TestAuthRequired:
    def test_pricing_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/sites/{TEST_SITE_ID}/pricing-analysis", timeout=15)
        assert r.status_code in (401, 403), f"Expected 401/403, got {r.status_code}"
