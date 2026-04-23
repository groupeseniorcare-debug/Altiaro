"""Iteration 21 — Studio de marque (Étape 5) regression tests.

Focus:
- GET  /api/sites/{id}/design            (must return {design, site_id, site_name})
- POST /api/sites/{id}/design/seed-legal (must create 3 legal_pages: cgv/mentions/confidentialite)
- GET  /api/sites/{id}/navigation        (must return header + footer)
- POST /api/sites/{id}/design/ai-field   (can timeout — accept 200 or 504/502)
- POST /api/sites/{id}/navigation/ai-optimize      (accept 200 or 502/504)
- POST /api/sites/{id}/collections/ai-suggest      (accept 200 or 502/504)
"""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # Fallback: read from frontend/.env
    try:
        with open("/app/frontend/.env") as f:
            for line in f:
                if line.startswith("REACT_APP_BACKEND_URL="):
                    BASE_URL = line.split("=", 1)[1].strip().rstrip("/")
                    break
    except Exception:
        pass

CONCEPTEUR = {"email": "concepteur@conceptfactory.fr", "password": "Concepteur2026!"}


@pytest.fixture(scope="module")
def auth_session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json=CONCEPTEUR, timeout=30)
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text[:300]}"
    return s


@pytest.fixture(scope="module")
def site_id(auth_session):
    # Find or create a test site
    r = auth_session.get(f"{BASE_URL}/api/sites", timeout=30)
    assert r.status_code == 200, f"GET /sites: {r.status_code}"
    sites = r.json()
    if isinstance(sites, dict):
        sites = sites.get("items") or sites.get("sites") or []
    if sites:
        return sites[0]["id"]
    # Create a site if none exists
    payload = {"name": "Test Studio Iter21", "niche": "fauteuils releveurs", "selected_countries": ["FR"]}
    r = auth_session.post(f"{BASE_URL}/api/sites", json=payload, timeout=60)
    assert r.status_code in (200, 201), f"Create site failed: {r.status_code} {r.text[:300]}"
    return r.json()["id"]


# --- Core design getters ---
def test_get_design_returns_expected_shape(auth_session, site_id):
    r = auth_session.get(f"{BASE_URL}/api/sites/{site_id}/design", timeout=30)
    assert r.status_code == 200, r.text[:300]
    data = r.json()
    assert "design" in data
    assert "site_id" in data
    assert data["site_id"] == site_id
    assert "site_name" in data


def test_get_navigation_returns_header_and_footer(auth_session, site_id):
    r = auth_session.get(f"{BASE_URL}/api/sites/{site_id}/navigation", timeout=30)
    assert r.status_code == 200, r.text[:300]
    nav = r.json()
    assert "header" in nav and isinstance(nav["header"], list)
    assert "footer" in nav and isinstance(nav["footer"], list)
    # defaults: at least 1 item each
    assert len(nav["header"]) >= 1
    assert len(nav["footer"]) >= 1


# --- Seed legal (no LLM, must always succeed) ---
def test_seed_legal_creates_three_pages(auth_session, site_id):
    r = auth_session.post(f"{BASE_URL}/api/sites/{site_id}/design/seed-legal", json={}, timeout=30)
    assert r.status_code == 200, f"seed-legal failed: {r.status_code} {r.text[:300]}"
    data = r.json()
    assert data.get("ok") is True
    pages = set(data.get("pages") or [])
    assert {"cgv", "mentions_legales", "confidentialite"}.issubset(pages), f"Missing legal pages: {pages}"

    # Verify persistence
    r2 = auth_session.get(f"{BASE_URL}/api/sites/{site_id}/design", timeout=30)
    assert r2.status_code == 200
    design = (r2.json() or {}).get("design") or {}
    legal = design.get("legal_pages") or {}
    for key in ("cgv", "mentions_legales", "confidentialite"):
        assert key in legal, f"Legal page '{key}' not persisted"
        assert legal[key].get("body_md"), f"Legal page '{key}' has no body"


# --- AI endpoints (may timeout — accept 200 or transient upstream errors) ---
ACCEPTABLE_LLM_CODES = {200, 402, 502, 504}


def test_ai_field_tagline_accepts_200_or_upstream_error(auth_session, site_id):
    t0 = time.time()
    try:
        r = auth_session.post(
            f"{BASE_URL}/api/sites/{site_id}/design/ai-field",
            json={"field": "tagline"},
            timeout=75,
        )
    except requests.Timeout:
        pytest.skip("ai-field tagline timed out (>75s) — acceptable for LLM call")
        return
    elapsed = time.time() - t0
    print(f"ai-field tagline: {r.status_code} in {elapsed:.1f}s")
    assert r.status_code in ACCEPTABLE_LLM_CODES, f"Unexpected: {r.status_code} {r.text[:200]}"
    if r.status_code == 200:
        data = r.json()
        assert data.get("ok") is True
        assert data.get("field") == "tagline"
        assert "value" in data
        assert isinstance(data["value"], str) and len(data["value"]) > 0


def test_ai_field_invalid_field_returns_400(auth_session, site_id):
    r = auth_session.post(
        f"{BASE_URL}/api/sites/{site_id}/design/ai-field",
        json={"field": "nonexistent_field"},
        timeout=30,
    )
    assert r.status_code == 400, f"Expected 400 for invalid field, got {r.status_code}"


def test_ai_nav_optimize_accepts_200_or_error(auth_session, site_id):
    try:
        r = auth_session.post(
            f"{BASE_URL}/api/sites/{site_id}/navigation/ai-optimize",
            timeout=75,
        )
    except requests.Timeout:
        pytest.skip("ai-nav-optimize timed out (>75s) — acceptable")
        return
    print(f"ai-nav-optimize: {r.status_code}")
    assert r.status_code in ACCEPTABLE_LLM_CODES, f"Unexpected: {r.status_code} {r.text[:200]}"
    if r.status_code == 200:
        data = r.json()
        assert "navigation" in data
        assert "header" in data["navigation"]
        assert "footer" in data["navigation"]


def test_ai_collections_suggest_accepts_200_or_error(auth_session, site_id):
    try:
        r = auth_session.post(
            f"{BASE_URL}/api/sites/{site_id}/collections/ai-suggest",
            timeout=75,
        )
    except requests.Timeout:
        pytest.skip("ai-collections-suggest timed out (>75s) — acceptable")
        return
    print(f"ai-collections-suggest: {r.status_code}")
    assert r.status_code in ACCEPTABLE_LLM_CODES, f"Unexpected: {r.status_code} {r.text[:200]}"
    if r.status_code == 200:
        data = r.json()
        assert "suggestions" in data
        assert isinstance(data["suggestions"], list)
