"""Iteration 22 regression suite.
Covers:
- Navigation persisted via PUT /api/sites/{id}/navigation and echoed by public /navigation.
- PATCH /api/sites/{id}/design/section/{section} — valid (hero) + invalid (garbage).
- POST /api/products/{id}/generate-image — Nano Banana. 200 or 402/502/504 acceptable.
- GET /api/uploads/products_ai/{file} serves a real PNG on success.
- Regression: GET /api/sites/{id}/design, /api/platform/llm-status, auth me.
"""
import os, time, pytest, requests

def _load_base():
    v = os.environ.get("REACT_APP_BACKEND_URL")
    if not v:
        env_path = "/app/frontend/.env"
        if os.path.exists(env_path):
            for line in open(env_path):
                if line.startswith("REACT_APP_BACKEND_URL="):
                    v = line.split("=", 1)[1].strip().strip('"')
                    break
    assert v, "REACT_APP_BACKEND_URL missing"
    return v.rstrip("/")

BASE = _load_base()
SITE = "65964cb0-7a1a-4c11-9644-1ad8f2371d48"
PRODUCT = "447e666d-5db0-4e73-9e94-949a30db9cfd"
EMAIL = "concepteur@conceptfactory.fr"
PWD = "Concepteur2026!"


@pytest.fixture(scope="session")
def sess():
    s = requests.Session()
    r = s.post(f"{BASE}/api/auth/login", json={"email": EMAIL, "password": PWD}, timeout=30)
    assert r.status_code == 200, f"login failed {r.status_code} {r.text[:300]}"
    return s


# ---------- Regression basics ----------
def test_auth_me(sess):
    r = sess.get(f"{BASE}/api/auth/me", timeout=15)
    assert r.status_code == 200
    assert r.json().get("email") == EMAIL


def test_llm_status(sess):
    r = sess.get(f"{BASE}/api/platform/llm-status", timeout=30)
    assert r.status_code == 200
    body = r.json()
    assert "has_budget" in body or "status" in body or "model" in body


def test_get_design(sess):
    r = sess.get(f"{BASE}/api/sites/{SITE}/design", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "design" in data
    assert data.get("site_id") == SITE


# ---------- #5: PATCH /design/section/{section} ----------
def test_patch_section_hero_valid(sess):
    payload = {"data": {"title": "TEST_hero_title_iter22", "subtitle": "TEST subtitle", "cta_primary": "Découvrir"}}
    r = sess.patch(f"{BASE}/api/sites/{SITE}/design/section/hero", json=payload, timeout=20)
    assert r.status_code == 200, r.text[:300]
    body = r.json()
    assert body.get("ok") is True
    assert body.get("section") == "hero"
    # verify persistence
    r2 = sess.get(f"{BASE}/api/sites/{SITE}/design", timeout=20)
    hero = r2.json().get("design", {}).get("hero", {})
    assert hero.get("title") == "TEST_hero_title_iter22"


def test_patch_section_invalid_returns_400(sess):
    r = sess.patch(f"{BASE}/api/sites/{SITE}/design/section/garbage", json={"x": 1}, timeout=15)
    assert r.status_code == 400, f"expected 400 got {r.status_code} {r.text[:200]}"


# ---------- #1: Navigation PUT → public GET echoes header ----------
def test_navigation_put_persists_and_public_returns_header(sess):
    custom_header = [
        {"label": "TEST Accueil", "href": "/"},
        {"label": "TEST Mobilité", "href": "/categorie/mobilite"},
        {"label": "TEST Blog", "href": "/blog"},
    ]
    custom_footer = [{"label": "TEST CGV", "href": "/cgv"}]
    payload = {"header": custom_header, "footer": custom_footer}
    r = sess.put(f"{BASE}/api/sites/{SITE}/navigation", json=payload, timeout=20)
    assert r.status_code in (200, 201), f"PUT nav failed {r.status_code} {r.text[:300]}"

    # Public GET (no auth) should echo custom nav
    r2 = requests.get(f"{BASE}/api/public/sites/{SITE}/navigation", timeout=20)
    assert r2.status_code == 200, r2.text[:300]
    nav = r2.json()
    header = nav.get("header") or nav.get("data", {}).get("header") or []
    labels = [h.get("label") for h in header if isinstance(h, dict)]
    assert any("TEST Accueil" == lbl for lbl in labels), f"custom nav not echoed: {labels}"


# ---------- #4: Nano Banana product image ----------
def test_generate_product_image(sess):
    r = sess.post(
        f"{BASE}/api/products/{PRODUCT}/generate-image",
        json={"style": "lifestyle"},
        timeout=90,
    )
    # Accept 200 OR 402 (budget) OR 502/504 (Google Nano Banana flaky) per brief
    assert r.status_code in (200, 402, 502, 504), f"unexpected {r.status_code}: {r.text[:300]}"
    if r.status_code == 200:
        body = r.json()
        assert "url" in body, body
        assert body.get("style") == "lifestyle"
        url = body["url"]
        # Serve the image
        full = url if url.startswith("http") else f"{BASE}{url}"
        r2 = requests.get(full, timeout=30)
        assert r2.status_code == 200
        assert r2.headers.get("content-type", "").startswith("image/")
        assert len(r2.content) > 10_000  # non-empty PNG
    else:
        pytest.skip(f"Nano Banana returned {r.status_code} (acceptable flake)")


def test_uploads_products_ai_directory_exists(sess):
    # Touch endpoint with a non-existent file → 404 (proves handler mounted)
    r = requests.get(f"{BASE}/api/uploads/products_ai/__does_not_exist__.png", timeout=10)
    assert r.status_code in (404, 403), f"expected 404, got {r.status_code}"
