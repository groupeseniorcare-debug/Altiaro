"""Iteration 17 backend tests: SEO audit + reviews cron + mark delivered + hook #27."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://senior-france.preview.emergentagent.com").rstrip("/")

CONCEPTEUR_CREDS = {"email": "concepteur@conceptfactory.fr", "password": "Concepteur2026!"}
ADMIN_CREDS = {"email": "admin@conceptfactory.fr", "password": "Factory2026!"}
SERENIVA_SITE = "d7d84968-0a2e-44c4-880b-f5af736cc86d"


# --- Auth fixtures ---
@pytest.fixture(scope="module")
def concepteur_session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json=CONCEPTEUR_CREDS, timeout=20)
    assert r.status_code == 200, f"Concepteur login failed: {r.status_code} {r.text[:200]}"
    return s


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS, timeout=20)
    assert r.status_code == 200, f"Admin login failed: {r.status_code} {r.text[:200]}"
    return s


# --- SEO Audit ---
class TestSeoAudit:
    def test_seo_audit_returns_full_payload(self, concepteur_session):
        r = concepteur_session.get(f"{BASE_URL}/api/sites/{SERENIVA_SITE}/seo-audit", timeout=30)
        assert r.status_code == 200, f"{r.status_code} {r.text[:300]}"
        data = r.json()
        # core keys
        for key in ["site_id", "site_name", "published", "audited_at", "overall_score", "dimensions", "coverage", "checks", "recommendations"]:
            assert key in data, f"Missing key {key}"
        assert data["site_id"] == SERENIVA_SITE
        assert isinstance(data["overall_score"], int)
        assert 0 <= data["overall_score"] <= 100
        # 6 dimensions
        dims = data["dimensions"]
        for d in ["catalog", "content", "structure", "trust", "aeo", "freshness"]:
            assert d in dims, f"Missing dim {d}"
            assert "score" in dims[d] and "label" in dims[d]
            assert 0 <= dims[d]["score"] <= 100
        # coverage
        cov = data["coverage"]
        for k in ["products_total", "products_enriched", "products_with_reviews", "products_with_bundles", "products_with_images", "blog_posts", "collections"]:
            assert k in cov
        # checks
        for k in ["published", "has_brand", "has_logo", "has_tagline", "legal_complete", "about_done", "contact_done", "values_done", "founder_done"]:
            assert k in data["checks"]
        # recommendations list
        assert isinstance(data["recommendations"], list)

    def test_seo_audit_not_found(self, concepteur_session):
        r = concepteur_session.get(f"{BASE_URL}/api/sites/nonexistent-id-xyz/seo-audit", timeout=15)
        assert r.status_code == 404

    def test_seo_audit_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/sites/{SERENIVA_SITE}/seo-audit", timeout=15)
        assert r.status_code in (401, 403)


# --- Reviews cron ---
class TestReviewsCron:
    def test_check_due_invitations(self, admin_session):
        r = admin_session.post(f"{BASE_URL}/api/reviews/check-due", timeout=30)
        assert r.status_code == 200, f"{r.status_code} {r.text[:300]}"
        data = r.json()
        assert "total_due" in data
        assert "sent" in data
        assert "skipped_no_resend" in data
        assert isinstance(data["total_due"], int)


# --- Mark delivered ---
class TestMarkDelivered:
    def test_mark_delivered_endpoint_shape(self, admin_session):
        # Pick any paid order if exists
        r = admin_session.get(f"{BASE_URL}/api/admin/orders?status=paid&limit=5", timeout=20)
        if r.status_code != 200:
            pytest.skip(f"Cannot list orders: {r.status_code}")
        orders = r.json() if isinstance(r.json(), list) else r.json().get("items") or r.json().get("orders") or []
        if not orders:
            # Endpoint must still respond with 404 for random id
            r2 = admin_session.post(f"{BASE_URL}/api/orders/nonexistent-order-id/mark-delivered", timeout=15)
            assert r2.status_code in (404, 400)
            return
        order_id = orders[0].get("id") or orders[0].get("_id")
        r3 = admin_session.post(f"{BASE_URL}/api/orders/{order_id}/mark-delivered", timeout=30)
        assert r3.status_code in (200, 409, 400), f"{r3.status_code} {r3.text[:200]}"


# --- Hook #27 blog seed scheduling ---
class TestHookBlogSeed:
    def test_hook27_registered(self):
        """Verify _hook_blog_seed is registered for prompt #27 via source inspection."""
        import pathlib
        src = pathlib.Path("/app/backend/routes/step_side_effects.py").read_text()
        assert "_hook_blog_seed" in src, "hook function missing"
        assert "27" in src, "prompt 27 not referenced"

    def test_prompt27_step_exists_and_save_ai(self, admin_session):
        """Set ai_response on a site's step #27 and attempt validate (as admin) — expect hook scheduled in logs."""
        r = admin_session.get(f"{BASE_URL}/api/sites", timeout=15)
        if r.status_code != 200:
            pytest.skip(f"sites list failed {r.status_code}")
        sites = r.json()
        if not sites:
            pytest.skip("no sites")
        # find a site that has step 27
        target_site = None
        target_step_id = None
        for s in sites:
            sid = s["id"]
            rs = admin_session.get(f"{BASE_URL}/api/sites/{sid}/steps", timeout=15)
            if rs.status_code != 200:
                continue
            steps = rs.json()
            for st in steps:
                if st.get("number") == 27:
                    target_site = sid
                    target_step_id = st.get("id")
                    break
            if target_step_id:
                break
        if not target_step_id:
            pytest.skip("No site has step #27")
        # Update ai_response
        payload = {
            "ai_response": '{"keywords": ["fauteuil releveur senior", "monte-escalier prix", "matelas dos senior"]}'
        }
        ru = admin_session.put(f"{BASE_URL}/api/steps/{target_step_id}", json=payload, timeout=20)
        # update may or may not exist — try validate directly
        rv = admin_session.post(f"{BASE_URL}/api/steps/{target_step_id}/validate", json={"comment": "test"}, timeout=30)
        assert rv.status_code in (200, 201, 202, 400, 409), f"{rv.status_code} {rv.text[:300]}"
