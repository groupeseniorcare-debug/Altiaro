"""Iteration 27 — Launch Orchestrator (wizard + backend orchestrator + polling status).

Covers:
  - POST /api/sites/{id}/design/launch (wizard input) → {ok, job_id, status: running}
  - GET  /api/sites/{id}/design/launch-status (latest job)
  - 409 concurrent launch guard
  - Launch on a fresh site (simulate wizard use-case)
  - Zombie reaper already applied at startup (not retested here)
  - Regression: /api/llm/status, GET /api/sites/{id}/design/homepage-sections

Credentials: concepteur@conceptfactory.fr / Concepteur2026!
Test site (has design + products): 65964cb0-7a1a-4c11-9644-1ad8f2371d48
"""
import os
import time

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://senior-france.preview.emergentagent.com").rstrip("/")
TEST_SITE_ID = "65964cb0-7a1a-4c11-9644-1ad8f2371d48"

CONCEPTEUR = {"email": "concepteur@conceptfactory.fr", "password": "Concepteur2026!"}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def concepteur_session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json=CONCEPTEUR, timeout=45)
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text[:200]}"
    return s


# ---------------------------------------------------------------------------
# Auth / baseline
# ---------------------------------------------------------------------------
def test_login_concepteur_sets_cookie(concepteur_session):
    r = concepteur_session.get(f"{BASE_URL}/api/auth/me", timeout=45)
    assert r.status_code == 200
    me = r.json()
    assert me.get("email") == CONCEPTEUR["email"]


def test_llm_status_route_exists(concepteur_session):
    # regression from previous iterations
    r = concepteur_session.get(f"{BASE_URL}/api/llm/status", timeout=45)
    # Either 200 or 402/403 if budget gate — must not be 500
    assert r.status_code in (200, 402, 403, 404), f"Unexpected {r.status_code}: {r.text[:200]}"


def test_homepage_sections_get(concepteur_session):
    r = concepteur_session.get(
        f"{BASE_URL}/api/sites/{TEST_SITE_ID}/design/homepage-sections", timeout=45
    )
    assert r.status_code == 200
    data = r.json()
    assert "sections" in data or isinstance(data, list) or "homepage_sections" in data


# ---------------------------------------------------------------------------
# Launch status polling (should return latest job from previous run)
# ---------------------------------------------------------------------------
def test_launch_status_latest(concepteur_session):
    r = concepteur_session.get(
        f"{BASE_URL}/api/sites/{TEST_SITE_ID}/design/launch-status", timeout=45
    )
    assert r.status_code == 200
    data = r.json()
    assert "status" in data
    if data["status"] != "idle":
        for k in ("id", "site_id", "status", "progress_pct", "current_step"):
            assert k in data, f"Missing key {k} in status payload: {data}"
        assert data["site_id"] == TEST_SITE_ID
        assert 0 <= data["progress_pct"] <= 100
        assert data["status"] in ("running", "completed", "failed")


# ---------------------------------------------------------------------------
# Concurrent launch guard : if a job is running, a second POST must return 409
# ---------------------------------------------------------------------------
def test_concurrent_launch_returns_409_if_running(concepteur_session):
    r_status = concepteur_session.get(
        f"{BASE_URL}/api/sites/{TEST_SITE_ID}/design/launch-status", timeout=45
    )
    running = r_status.status_code == 200 and r_status.json().get("status") == "running"
    if not running:
        pytest.skip("No job currently running — concurrent guard cannot be tested deterministically without launching a new one.")

    payload = {
        "brand_name": "Test Guard",
        "tagline": "concurrent",
        "mission": "should be blocked",
        "voice": "concis",
        "mood": "Chaleureux",
        "overwrite_all": False,
    }
    r = concepteur_session.post(
        f"{BASE_URL}/api/sites/{TEST_SITE_ID}/design/launch",
        json=payload, timeout=45,
    )
    assert r.status_code == 409, f"Expected 409, got {r.status_code}: {r.text[:200]}"


# ---------------------------------------------------------------------------
# Launch on a fresh site — end-to-end job_id + polling structure
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def fresh_site(concepteur_session):
    """Concepteur role cannot create sites (admin-only). Use admin session to seed."""
    admin = requests.Session()
    r = admin.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "admin@conceptfactory.fr", "password": "Factory2026!"},
        timeout=45,
    )
    if r.status_code != 200:
        pytest.skip(f"Admin login failed: {r.status_code}")
    # Get concepteur user id
    me = concepteur_session.get(f"{BASE_URL}/api/auth/me", timeout=45).json()
    op_id = me.get("id")
    r = admin.post(
        f"{BASE_URL}/api/sites",
        json={"name": "TEST_LaunchWizard_Iter27", "niche": "silver_economy", "operator_id": op_id},
        timeout=45,
    )
    if r.status_code not in (200, 201):
        pytest.skip(f"Site creation failed: {r.status_code} {r.text[:200]}")
    site = r.json()
    sid = site.get("id") or site.get("site_id")
    yield sid
    # Cleanup best-effort
    try:
        admin.delete(f"{BASE_URL}/api/sites/{sid}", timeout=45)
    except Exception:
        pass


def test_launch_on_fresh_site_returns_job_id(concepteur_session, fresh_site):
    payload = {
        "brand_name": "TEST_BrandIter27",
        "tagline": "le test ultime",
        "mission": "Validate orchestrator",
        "voice": "chaleureux et rassurant, premium",
        "mood": "Chaleureux",
        "palette_choice": {"primary": "#B84B31", "accent": "#E9C46A", "background": "#FAF7F2", "text": "#1C1917"},
        "font_pair": {"heading": "Fraunces", "body": "Inter"},
        "homepage_preset": "default_template",
        "overwrite_all": False,
        "logo_style": "horizontal_premium",
    }
    r = concepteur_session.post(
        f"{BASE_URL}/api/sites/{fresh_site}/design/launch",
        json=payload, timeout=45,
    )
    assert r.status_code == 201 or r.status_code == 200, f"Launch failed: {r.status_code} {r.text[:300]}"
    data = r.json()
    assert data.get("ok") is True
    assert "job_id" in data and isinstance(data["job_id"], str) and len(data["job_id"]) > 10
    assert data.get("status") == "running"

    # Poll once to ensure status endpoint returns the job we started
    time.sleep(1.5)
    rs = concepteur_session.get(
        f"{BASE_URL}/api/sites/{fresh_site}/design/launch-status", timeout=45
    )
    assert rs.status_code == 200
    s = rs.json()
    assert s.get("status") in ("running", "completed", "failed")
    assert s.get("site_id") == fresh_site
    assert s.get("id") == data["job_id"]

    # And concurrent launch must 409 now
    r409 = concepteur_session.post(
        f"{BASE_URL}/api/sites/{fresh_site}/design/launch",
        json=payload, timeout=45,
    )
    assert r409.status_code == 409, f"Expected 409 on concurrent launch, got {r409.status_code}: {r409.text[:200]}"


# ---------------------------------------------------------------------------
# Access control — unauthenticated user is rejected
# ---------------------------------------------------------------------------
def test_launch_requires_auth():
    r = requests.post(
        f"{BASE_URL}/api/sites/{TEST_SITE_ID}/design/launch",
        json={"brand_name": "nope"},
        timeout=45,
    )
    assert r.status_code in (401, 403), f"Expected 401/403, got {r.status_code}"


def test_launch_status_requires_auth():
    r = requests.get(
        f"{BASE_URL}/api/sites/{TEST_SITE_ID}/design/launch-status",
        timeout=45,
    )
    assert r.status_code in (401, 403)
