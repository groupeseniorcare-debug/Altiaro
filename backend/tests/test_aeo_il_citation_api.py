"""API tests for AEO readiness, Internal Linking, and Citation Tracker endpoints.

Tests auth + 404 + graceful LLM budget handling.
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://senior-france.preview.emergentagent.com").rstrip("/")
SITE_ID = "65964cb0-7a1a-4c11-9644-1ad8f2371d48"
BAD_ID = "00000000-0000-0000-0000-000000000000"
EMAIL = "concepteur@conceptfactory.fr"
PWD = "Concepteur2026!"


@pytest.fixture(scope="module")
def client():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": EMAIL, "password": PWD}, timeout=15)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    return s


# --- AEO Readiness ---
class TestAeoReadiness:
    def test_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/sites/{SITE_ID}/aeo-readiness", timeout=15)
        assert r.status_code == 401, f"expected 401, got {r.status_code}"

    def test_404_on_unknown_site(self, client):
        r = client.get(f"{BASE_URL}/api/sites/{BAD_ID}/aeo-readiness", timeout=15)
        assert r.status_code == 404

    def test_returns_score_and_checklist(self, client):
        r = client.get(f"{BASE_URL}/api/sites/{SITE_ID}/aeo-readiness", timeout=20)
        assert r.status_code == 200, r.text
        d = r.json()
        assert "score" in d and isinstance(d["score"], int)
        assert 0 <= d["score"] <= 100
        assert "checklist" in d and isinstance(d["checklist"], list)
        assert len(d["checklist"]) == 7
        keys = {c["key"] for c in d["checklist"]}
        assert {"products_ready", "avg_qa", "conversational_kw", "llms_full",
                "contact_schema", "blog_posts", "image_sitemap"}.issubset(keys)
        for c in d["checklist"]:
            assert "label" in c and "ok" in c


# --- AEO Enrich one — only auth + 404 (skip LLM call) ---
class TestAeoEnrichOne:
    def test_requires_auth(self):
        r = requests.post(f"{BASE_URL}/api/products/doesnotmatter/aeo-enrich", timeout=15)
        assert r.status_code == 401

    def test_404_on_unknown_product(self, client):
        r = client.post(f"{BASE_URL}/api/products/{BAD_ID}/aeo-enrich", timeout=15)
        assert r.status_code == 404


# --- Internal Linking ---
class TestInternalLinkingAutoInject:
    def test_requires_auth(self):
        r = requests.post(f"{BASE_URL}/api/sites/{SITE_ID}/internal-linking/auto-inject",
                          json={"dry_run": True}, timeout=20)
        assert r.status_code == 401

    def test_404_on_unknown_site(self, client):
        r = client.post(f"{BASE_URL}/api/sites/{BAD_ID}/internal-linking/auto-inject",
                        json={"dry_run": True}, timeout=20)
        assert r.status_code == 404

    def test_dry_run_returns_expected_stats(self, client):
        r = client.post(
            f"{BASE_URL}/api/sites/{SITE_ID}/internal-linking/auto-inject",
            json={"dry_run": True, "max_links_per_post": 6, "max_links_per_product": 3},
            timeout=30,
        )
        assert r.status_code == 200, r.text
        d = r.json()
        # either noop (no targets) or stats payload
        if d.get("status") == "noop":
            assert "link_map_size" in d
            return
        for k in ("blog_posts_scanned", "products_scanned", "link_map_size",
                  "total_links_added", "finished_at", "dry_run"):
            assert k in d, f"missing {k} in {d}"
        assert d["dry_run"] is True
        assert isinstance(d["link_map_size"], int)
        assert isinstance(d["total_links_added"], int)


class TestInternalLinkingStats:
    def test_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/sites/{SITE_ID}/internal-linking/stats", timeout=15)
        assert r.status_code == 401

    def test_404_on_unknown_site(self, client):
        r = client.get(f"{BASE_URL}/api/sites/{BAD_ID}/internal-linking/stats", timeout=15)
        assert r.status_code == 404

    def test_returns_stats(self, client):
        r = client.get(f"{BASE_URL}/api/sites/{SITE_ID}/internal-linking/stats", timeout=20)
        assert r.status_code == 200, r.text
        d = r.json()
        for k in ("total_outgoing_internal_links", "orphan_pages", "most_linked", "last_run_at"):
            assert k in d, f"missing {k} in {d}"
        assert isinstance(d["orphan_pages"], list)
        assert isinstance(d["most_linked"], list)
        assert isinstance(d["total_outgoing_internal_links"], int)


# --- Citation Tracker ---
class TestCitationTracker:
    def test_get_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/sites/{SITE_ID}/citation-tracker", timeout=15)
        assert r.status_code == 401

    def test_get_404_on_unknown_site(self, client):
        r = client.get(f"{BASE_URL}/api/sites/{BAD_ID}/citation-tracker", timeout=15)
        assert r.status_code == 404

    def test_get_returns_last_run_and_history(self, client):
        r = client.get(f"{BASE_URL}/api/sites/{SITE_ID}/citation-tracker", timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert "last_run" in d
        assert "history" in d
        assert isinstance(d["history"], list)

    def test_run_requires_auth(self):
        r = requests.post(f"{BASE_URL}/api/sites/{SITE_ID}/citation-tracker/run",
                          json={"max_questions": 2}, timeout=15)
        assert r.status_code == 401

    def test_run_404_on_unknown_site(self, client):
        r = client.post(f"{BASE_URL}/api/sites/{BAD_ID}/citation-tracker/run",
                        json={"max_questions": 2}, timeout=15)
        assert r.status_code == 404

    def test_run_handles_llm_budget_gracefully(self, client):
        """Either returns 200 with status=noop/failed/success or 402. No 500."""
        r = client.post(
            f"{BASE_URL}/api/sites/{SITE_ID}/citation-tracker/run",
            json={"max_questions": 2}, timeout=180,
        )
        assert r.status_code in (200, 400, 402), f"unexpected {r.status_code}: {r.text[:300]}"
        if r.status_code == 200:
            d = r.json()
            # valid shapes: noop message, failed with error, or snapshot with rate
            assert any(k in d for k in ("status", "rate", "at"))
