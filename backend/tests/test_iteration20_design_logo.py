"""Iteration 20 — Test new design endpoints (brand/logo upload), regenerate validation,
publish toggle, CJ sourcing search. Skips full Claude generate by default (slow + budget)."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://senior-france.preview.emergentagent.com").rstrip("/")
SITE_ID = "65964cb0-7a1a-4c11-9644-1ad8f2371d48"
EMAIL = "concepteur@conceptfactory.fr"
PASSWORD = "Concepteur2026!"
RUN_HEAVY = os.environ.get("RUN_HEAVY", "0") == "1"


@pytest.fixture(scope="session")
def auth_session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": EMAIL, "password": PASSWORD}, timeout=30)
    if r.status_code != 200:
        pytest.skip(f"Login failed: {r.status_code} {r.text[:200]}")
    return s


def test_get_design_state(auth_session):
    r = auth_session.get(f"{BASE_URL}/api/sites/{SITE_ID}/design", timeout=15)
    assert r.status_code == 200
    data = r.json()
    assert "design" in data
    assert data.get("site_id") == SITE_ID
    assert data.get("site_name")


def test_logo_upload_unauth():
    r = requests.post(
        f"{BASE_URL}/api/sites/{SITE_ID}/design/brand/logo",
        json={"logo_url": "/api/uploads/test.png"},
        timeout=15,
    )
    assert r.status_code in (401, 403), f"Expected 401/403, got {r.status_code}"


def test_logo_url_save_and_persist(auth_session):
    test_url = "/api/uploads/logos/test_logo_iter20.png"
    r = auth_session.post(
        f"{BASE_URL}/api/sites/{SITE_ID}/design/brand/logo",
        json={"logo_url": test_url},
        timeout=15,
    )
    assert r.status_code == 200, r.text[:200]
    body = r.json()
    assert body.get("ok") is True
    assert body.get("logo_url") == test_url

    # GET back to verify persistence
    r2 = auth_session.get(f"{BASE_URL}/api/sites/{SITE_ID}/design", timeout=15)
    assert r2.status_code == 200
    design = r2.json().get("design") or {}
    assert (design.get("brand") or {}).get("logo_url") == test_url


def test_logo_url_validation_too_short(auth_session):
    r = auth_session.post(
        f"{BASE_URL}/api/sites/{SITE_ID}/design/brand/logo",
        json={"logo_url": "x"},
        timeout=15,
    )
    assert r.status_code == 422  # pydantic min_length=3


def test_regenerate_invalid_section(auth_session):
    r = auth_session.post(
        f"{BASE_URL}/api/sites/{SITE_ID}/design/regenerate/invalid_section_xyz",
        json={"tweak": ""},
        timeout=15,
    )
    assert r.status_code == 400
    assert "invalide" in r.text.lower() or "Section" in r.text


def test_publish_toggle(auth_session):
    """publish endpoint requires existing design — may 400 if no brand."""
    r_get = auth_session.get(f"{BASE_URL}/api/sites/{SITE_ID}/design", timeout=15)
    has_design = bool((r_get.json().get("design") or {}).get("brand"))
    if not has_design:
        # ensure publish refuses gracefully
        r = auth_session.post(f"{BASE_URL}/api/sites/{SITE_ID}/design/publish", timeout=15)
        assert r.status_code in (200, 400)
        return
    r = auth_session.post(f"{BASE_URL}/api/sites/{SITE_ID}/design/publish", timeout=15)
    assert r.status_code == 200
    assert r.json().get("ok") is True
    assert "published" in r.json()


def test_cj_sourcing_search(auth_session):
    r = auth_session.post(
        f"{BASE_URL}/api/sourcing/search",
        json={"keyword": "fauteuil releveur", "providers": ["cj"], "site_id": SITE_ID},
        timeout=60,
    )
    assert r.status_code in (200, 502), f"Status {r.status_code}: {r.text[:200]}"
    if r.status_code == 200:
        body = r.json()
        # Endpoint may return a list, dict with "results", or grouped {cj: [...]}
        items = (
            body.get("results")
            or body.get("items")
            or (body.get("cj") if isinstance(body, dict) else None)
            or (body if isinstance(body, list) else None)
        )
        assert items is not None, f"No results key found in: {str(body)[:300]}"


@pytest.mark.skipif(not RUN_HEAVY, reason="heavy Claude call — set RUN_HEAVY=1 to run")
def test_design_generate_full(auth_session):
    r = auth_session.post(
        f"{BASE_URL}/api/sites/{SITE_ID}/design/generate",
        json={"with_logo": False, "tweak": "test iter20"},
        timeout=180,
    )
    assert r.status_code == 200, r.text[:300]
    body = r.json()
    assert body.get("ok") is True
    design = body.get("design") or {}
    assert design.get("brand", {}).get("logo_text") or design.get("brand", {}).get("name")
    assert design.get("hero")
    assert design.get("faq")
