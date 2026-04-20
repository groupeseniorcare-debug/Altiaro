"""
Concept Factory — Backend regression tests.
Covers: auth (httpOnly cookies), niches catalog, countries, sites creation with
niche_slug, steps auto-progression (no admin gating), LLM 402 budget handling.
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://senior-france.preview.emergentagent.com").rstrip("/")
ADMIN_EMAIL = "admin@conceptfactory.fr"
ADMIN_PASSWORD = "Factory2026!"


# ---- Fixtures ----
@pytest.fixture(scope="session")
def admin_session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login",
               json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
               timeout=15)
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    # Ensure httpOnly cookies set
    cookies = {c.name: c for c in s.cookies}
    assert "access_token" in cookies, f"access_token cookie missing: {list(cookies)}"
    assert "refresh_token" in cookies, "refresh_token cookie missing"
    # Note: requests cookie jar doesn't expose HttpOnly flag, but we verify via Set-Cookie header
    set_cookie_hdr = r.headers.get("set-cookie", "")
    assert "HttpOnly" in set_cookie_hdr, f"HttpOnly flag missing in Set-Cookie: {set_cookie_hdr[:300]}"
    data = r.json()
    assert data["email"] == ADMIN_EMAIL
    assert data["role"] == "admin"
    return s


# ---- Auth ----
class TestAuth:
    def test_login_returns_user_and_cookies(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/auth/me", timeout=10)
        assert r.status_code == 200
        assert r.json()["email"] == ADMIN_EMAIL

    def test_login_bad_password(self):
        r = requests.post(f"{BASE_URL}/api/auth/login",
                          json={"email": ADMIN_EMAIL, "password": "wrong!"},
                          timeout=10)
        assert r.status_code == 401
        assert "incorrect" in r.json().get("detail", "").lower() or "mot de passe" in r.json().get("detail", "").lower()

    def test_niches_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/niches", timeout=10)
        assert r.status_code == 401

    def test_countries_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/countries", timeout=10)
        assert r.status_code == 401


# ---- Niche Engine ----
class TestNiches:
    def test_list_20_niches_sorted_by_rank(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/niches", timeout=15)
        assert r.status_code == 200
        niches = r.json()
        assert len(niches) == 20, f"Expected 20 niches, got {len(niches)}"
        # sorted asc by rank
        ranks = [n["rank"] for n in niches]
        assert ranks == sorted(ranks), f"Niches not sorted by rank: {ranks}"
        # Required fields
        required = {"name", "rank", "ecf_score", "total_volume_monthly", "country_metrics", "keywords", "suppliers", "hero", "slug"}
        for n in niches:
            missing = required - set(n.keys())
            assert not missing, f"Niche {n.get('slug')} missing fields: {missing}"
            assert isinstance(n["country_metrics"], dict)
            assert set(n["country_metrics"].keys()) == {"FR", "DE", "CH", "BE", "UK", "NL"}

    def test_niche_detail_canne_pliante(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/niches/canne-pliante-premium", timeout=10)
        assert r.status_code == 200
        niche = r.json()
        assert niche["slug"] == "canne-pliante-premium"
        assert niche["hero"] is True
        cm = niche["country_metrics"]
        assert len(cm) == 6
        for code in ["FR", "DE", "CH", "BE", "UK", "NL"]:
            assert code in cm
            for key in ["volume", "cpc", "kd", "cpa_target", "seasonality"]:
                assert key in cm[code], f"Country {code} missing {key}"

    def test_niche_not_found(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/niches/slug-inexistant", timeout=10)
        assert r.status_code == 404

    def test_countries_list(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/countries", timeout=10)
        assert r.status_code == 200
        countries = r.json()
        codes = {c["code"] for c in countries}
        assert codes == {"FR", "DE", "CH", "BE", "UK", "NL"}, f"Got {codes}"
        for c in countries:
            for k in ["code", "name", "flag", "currency"]:
                assert k in c


# ---- Sites + Steps ----
class TestSitesAndSteps:
    @pytest.fixture(scope="class")
    def created_site(self, admin_session):
        payload = {
            "name": "TEST_Niche Site Autoprog",
            "niche": "Seniors France",
            "niche_slug": "canne-pliante-premium",
            "domain": "test-autoprog.fr",
        }
        r = admin_session.post(f"{BASE_URL}/api/sites", json=payload, timeout=20)
        assert r.status_code == 200, r.text
        site = r.json()
        assert site["niche_slug"] == "canne-pliante-premium"
        assert site["progress_total"] == 50
        yield site
        # Teardown
        admin_session.delete(f"{BASE_URL}/api/sites/{site['id']}", timeout=10)

    def test_site_creation_persists_niche_slug(self, admin_session, created_site):
        r = admin_session.get(f"{BASE_URL}/api/sites/{created_site['id']}", timeout=10)
        assert r.status_code == 200
        assert r.json()["niche_slug"] == "canne-pliante-premium"

    def test_step_auto_progression(self, admin_session, created_site):
        # Fetch steps
        r = admin_session.get(f"{BASE_URL}/api/sites/{created_site['id']}/steps", timeout=10)
        assert r.status_code == 200
        steps = r.json()
        assert len(steps) == 50
        step1 = next(s for s in steps if s["number"] == 1)
        step2 = next(s for s in steps if s["number"] == 2)
        assert step1["status"] == "in_progress"
        assert step2["status"] == "locked"

        # Patch step1 with notes
        r = admin_session.patch(
            f"{BASE_URL}/api/steps/{step1['id']}",
            json={"deliverable_notes": "TEST auto-progression deliverable"},
            timeout=10,
        )
        assert r.status_code == 200

        # Submit step1
        r = admin_session.post(f"{BASE_URL}/api/steps/{step1['id']}/submit", timeout=10)
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "validated"

        # Verify step2 now in_progress
        r = admin_session.get(f"{BASE_URL}/api/steps/{step2['id']}", timeout=10)
        assert r.status_code == 200
        assert r.json()["status"] == "in_progress", f"Next step should auto-unlock, got {r.json()['status']}"

    def test_submit_without_deliverable_fails(self, admin_session, created_site):
        r = admin_session.get(f"{BASE_URL}/api/sites/{created_site['id']}/steps", timeout=10)
        steps = r.json()
        # step2 should now be in_progress (from prev test) with no deliverable
        step2 = next(s for s in steps if s["number"] == 2)
        if step2["status"] != "in_progress":
            pytest.skip("Step 2 not in expected state (order dependency)")
        r = admin_session.post(f"{BASE_URL}/api/steps/{step2['id']}/submit", timeout=10)
        assert r.status_code == 400
        assert "livrable" in r.json().get("detail", "").lower()


# ---- LLM budget handling ----
class TestLLMExecute:
    def test_execute_budget_or_success(self, admin_session):
        # Create a throwaway site
        r = admin_session.post(f"{BASE_URL}/api/sites",
                               json={"name": "TEST_LLM", "niche": "Seniors",
                                     "niche_slug": "canne-pliante-premium"},
                               timeout=15)
        assert r.status_code == 200
        site = r.json()
        try:
            r = admin_session.get(f"{BASE_URL}/api/sites/{site['id']}/steps", timeout=10)
            step1 = next(s for s in r.json() if s["number"] == 1)
            r = admin_session.post(
                f"{BASE_URL}/api/steps/{step1['id']}/execute",
                json={"model_provider": "anthropic",
                      "model_name": "claude-sonnet-4-5-20250929"},
                timeout=90,
            )
            # Accept 200 (LLM worked) OR 402 (budget exceeded) OR 401 (invalid key)
            assert r.status_code in (200, 402, 401), f"Unexpected status {r.status_code}: {r.text}"
            if r.status_code == 402:
                detail = r.json().get("detail", "")
                assert "budget" in detail.lower(), f"402 should mention budget: {detail}"
                # must be French-clear
                assert any(w in detail.lower() for w in ["épuisé", "recharger", "profile"]), \
                    f"402 message should be French-clear: {detail}"
        finally:
            admin_session.delete(f"{BASE_URL}/api/sites/{site['id']}", timeout=10)
