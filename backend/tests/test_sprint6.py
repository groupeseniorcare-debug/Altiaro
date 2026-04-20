"""Sprint 6 backend regression — Niche Analyzer IA + Operator sites + Resync."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")

ADMIN_CREDS = {"email": "admin@conceptfactory.fr", "password": "Factory2026!"}
OP_CREDS = {"email": "concepteur@conceptfactory.fr", "password": "Concepteur2026!"}


def _login(creds):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json=creds, timeout=20)
    assert r.status_code == 200, f"login failed {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def admin():
    return _login(ADMIN_CREDS)


@pytest.fixture(scope="module")
def operator():
    return _login(OP_CREDS)


# ----- Router ordering guard: /niches/analyses should NOT collide with /niches/{slug} -----
def test_route_ordering_analyses_not_matching_slug(admin):
    # /niches/analyses must hit analyzer router (returns list), not niches slug lookup (which would 404)
    r = admin.get(f"{BASE_URL}/api/niches/analyses", timeout=15)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_analyses_auth_required():
    r = requests.get(f"{BASE_URL}/api/niches/analyses", timeout=10)
    assert r.status_code in (401, 403)


# ----- GET /api/niches/analyses (history) -----
def test_history_empty_or_trimmed(operator):
    r = operator.get(f"{BASE_URL}/api/niches/analyses", timeout=15)
    assert r.status_code == 200
    items = r.json()
    assert isinstance(items, list)
    for a in items:
        # summary trimmed shape
        assert "analysis" not in a  # list view removed full analysis
        if "analysis_summary" in a:
            s = a["analysis_summary"]
            for key in ("name", "overall_verdict", "slug"):
                assert key in s


def test_history_get_unknown_id_404(operator):
    r = operator.get(f"{BASE_URL}/api/niches/analyses/nope-xyz", timeout=15)
    assert r.status_code == 404


# ----- POST /api/niches/analyze — handles LLM budget gracefully -----
def test_analyze_requires_auth():
    r = requests.post(f"{BASE_URL}/api/niches/analyze", json={"product": "fauteuil"}, timeout=15)
    assert r.status_code in (401, 403)


def test_analyze_validates_input(operator):
    r = operator.post(f"{BASE_URL}/api/niches/analyze", json={"product": "a"}, timeout=15)
    assert r.status_code == 422  # min_length=2


@pytest.mark.analyzer
def test_analyze_full_flow_or_graceful_402(operator):
    """Full analyze call — accept real 200 OR graceful 402/504 if LLM budget/timeout."""
    r = operator.post(
        f"{BASE_URL}/api/niches/analyze",
        json={"product": "coussin orthopédique mémoire de forme"},
        timeout=120,
    )
    assert r.status_code in (200, 402, 502, 504), f"unexpected {r.status_code}: {r.text[:300]}"
    if r.status_code == 200:
        doc = r.json()
        for key in ("id", "user_id", "analysis", "created_at"):
            assert key in doc, f"missing {key}"
        a = doc["analysis"]
        for key in ("name", "country_metrics", "overall_verdict",
                    "total_volume_monthly", "avg_cpc_eur", "go_countries", "slug",
                    "synthesis_per_country"):
            assert key in a, f"missing analysis.{key}"
        # 6 countries present
        assert set(a["country_metrics"].keys()) >= {"FR", "DE", "CH", "BE", "UK", "NL"}
        assert a["overall_verdict"] in ("GO", "MAYBE", "NOGO")

        # persisted: GET /analyses/{id}
        doc_id = doc["id"]
        g = operator.get(f"{BASE_URL}/api/niches/analyses/{doc_id}", timeout=15)
        assert g.status_code == 200
        assert g.json()["id"] == doc_id
    else:
        # Must have french error
        assert "detail" in r.json()


def test_analysis_scoped_per_user(admin, operator):
    # operator cannot fetch admin's analysis doc and vice-versa
    r = admin.get(f"{BASE_URL}/api/niches/analyses", timeout=15)
    admin_items = r.json() if r.status_code == 200 else []
    if admin_items:
        admin_id = admin_items[0]["id"]
        r2 = operator.get(f"{BASE_URL}/api/niches/analyses/{admin_id}", timeout=15)
        assert r2.status_code == 404  # scoped lookup


# ----- POST /api/sites — operator can now create sites -----
def test_operator_can_create_site(operator):
    payload = {
        "name": "TEST_S6_OperatorSite",
        "niche": "Test Niche S6",
        "niche_slug": "test-niche-s6",
        "selected_countries": ["FR", "DE"],
        # daily_budget_eur intentionally omitted -> auto = 2*30 = 60
    }
    r = operator.post(f"{BASE_URL}/api/sites", json=payload, timeout=20)
    assert r.status_code == 200, r.text
    site = r.json()
    assert site["daily_budget_eur"] == 60, f"auto-budget wrong: {site['daily_budget_eur']}"
    assert site["selected_countries"] == ["FR", "DE"]
    # operator_id must be auto-assigned to caller (operator cannot impersonate)
    me = operator.get(f"{BASE_URL}/api/auth/me", timeout=10).json()
    assert site["operator_id"] == me["id"]
    # Cleanup as admin
    return site["id"]


def test_operator_cannot_assign_other_operator(operator, admin):
    me = operator.get(f"{BASE_URL}/api/auth/me", timeout=10).json()
    payload = {
        "name": "TEST_S6_TryImpersonate",
        "niche": "x",
        "selected_countries": ["FR"],
        "daily_budget_eur": 30,
        "operator_id": "some-other-id",
    }
    r = operator.post(f"{BASE_URL}/api/sites", json=payload, timeout=20)
    assert r.status_code == 200  # allowed but operator_id forced to self
    site = r.json()
    assert site["operator_id"] == me["id"]


def test_admin_can_assign_operator_id(admin, operator):
    me = operator.get(f"{BASE_URL}/api/auth/me", timeout=10).json()
    payload = {
        "name": "TEST_S6_AdminCreatesForOp",
        "niche": "y",
        "selected_countries": ["FR", "DE", "UK"],
        "operator_id": me["id"],
    }
    r = admin.post(f"{BASE_URL}/api/sites", json=payload, timeout=20)
    assert r.status_code == 200
    site = r.json()
    assert site["operator_id"] == me["id"]
    assert site["daily_budget_eur"] == 90  # 3*30


# ----- POST /sites/{id}/products/{pid}/resync -----
def test_resync_404_product_not_found(operator):
    # create site first
    r = operator.post(f"{BASE_URL}/api/sites", json={
        "name": "TEST_S6_ResyncHost", "niche": "z", "selected_countries": ["FR"]
    }, timeout=20)
    assert r.status_code == 200
    site_id = r.json()["id"]
    r = operator.post(
        f"{BASE_URL}/api/sites/{site_id}/products/unknown-pid/resync",
        timeout=15,
    )
    assert r.status_code == 404


def test_resync_400_when_no_supplier_url(operator):
    r = operator.post(f"{BASE_URL}/api/sites", json={
        "name": "TEST_S6_ResyncNoUrl", "niche": "z", "selected_countries": ["FR"]
    }, timeout=20)
    site_id = r.json()["id"]
    # create a product with no supplier_url
    pr = operator.post(f"{BASE_URL}/api/sites/{site_id}/products", json={
        "name": {"fr": "TEST prod", "en": "TEST prod", "de": "", "nl": ""},
        "description": {"fr": "d", "en": "d", "de": "", "nl": ""},
        "price": 49.9, "currency": "EUR", "images": [],
        "sku": "TESTS6", "status": "draft", "featured": False,
    }, timeout=20)
    assert pr.status_code == 200, pr.text
    pid = pr.json()["id"]
    r = operator.post(
        f"{BASE_URL}/api/sites/{site_id}/products/{pid}/resync", timeout=15
    )
    assert r.status_code == 400
    assert "URL fournisseur" in r.json()["detail"]
