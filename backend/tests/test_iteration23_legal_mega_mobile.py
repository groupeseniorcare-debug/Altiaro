"""Iteration 23 regression: 7 legal pages, mega menu storefront, navigation.
Brief items: (1) 7 legal keys (2) storefront legal routes (3-4) nav link picker + mega editor
(5) mega menu storefront rendering (6) mobile quick-wins (7) regression."""

import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
CONCEPTEUR_EMAIL = "concepteur@conceptfactory.fr"
CONCEPTEUR_PASSWORD = "Concepteur2026!"
SITE_ID = "65964cb0-7a1a-4c11-9644-1ad8f2371d48"
PRODUCT_ID = "447e666d-5db0-4e73-9e94-949a30db9cfd"

LEGAL_KEYS = {"cgv", "mentions_legales", "confidentialite", "cookies", "livraison", "retours", "mediation"}


@pytest.fixture(scope="module")
def auth_session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": CONCEPTEUR_EMAIL, "password": CONCEPTEUR_PASSWORD})
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    return s


# -------- Item 1: Legal pages (7 keys) --------
class TestLegalPages:
    def test_seed_legal_returns_7_keys(self, auth_session):
        r = auth_session.post(f"{BASE_URL}/api/sites/{SITE_ID}/design/seed-legal")
        assert r.status_code == 200, f"seed-legal failed: {r.text}"
        data = r.json()
        pages = set(data.get("pages") or [])
        assert pages >= LEGAL_KEYS, f"Missing legal keys. Got: {pages}"

    def test_public_design_exposes_7_legal(self, auth_session):
        r = requests.get(f"{BASE_URL}/api/public/sites/{SITE_ID}/design")
        assert r.status_code == 200
        body = r.json() or {}
        legal = (body.get("design") or body).get("legal_pages") or {}
        assert set(legal.keys()) >= LEGAL_KEYS, f"Public design missing legal keys. Got: {set(legal.keys())}"
        # Validate each page has title + body
        for k in LEGAL_KEYS:
            assert legal[k].get("title"), f"{k} missing title"
            assert legal[k].get("body_md"), f"{k} missing body_md"


# -------- Item 2: Storefront legal routes --------
class TestStorefrontLegalRoutes:
    @pytest.mark.parametrize("slug", ["cgv", "mentions-legales", "confidentialite", "cookies", "livraison", "retours", "mediation"])
    def test_storefront_legal_route_renders(self, slug):
        # These are SPA routes — index.html should be served (200). Not 404.
        r = requests.get(f"{BASE_URL}/shop/{SITE_ID}/{slug}", allow_redirects=True)
        assert r.status_code == 200, f"/shop/{SITE_ID}/{slug} returned {r.status_code}"


# -------- Item 5: Mega menu storefront rendering (backend persistence) --------
class TestNavigationMegaMenu:
    def test_put_nav_with_mega_persists(self, auth_session):
        mega_payload = {
            "header": [
                {"label": "Accueil", "type": "home", "href": "/"},
                {
                    "label": "TEST Mega",
                    "type": "mega",
                    "href": "#",
                    "children": [
                        {"label": "Col1", "href": "/collections/mobilite", "image": "https://picsum.photos/400/300"},
                        {"label": "Col2", "href": "/collections/confort", "image": "https://picsum.photos/400/301"},
                    ],
                },
            ],
            "footer": [{"label": "CGV", "type": "cgv", "href": "/cgv"}],
        }
        r = auth_session.put(f"{BASE_URL}/api/sites/{SITE_ID}/navigation", json=mega_payload)
        assert r.status_code == 200, f"PUT nav failed: {r.status_code} {r.text}"

    def test_public_nav_returns_mega(self):
        r = requests.get(f"{BASE_URL}/api/public/sites/{SITE_ID}/navigation")
        assert r.status_code == 200
        nav = r.json()
        header = nav.get("header") or []
        mega_items = [h for h in header if h.get("type") == "mega"]
        assert len(mega_items) >= 1, f"No mega item found in header. Got: {header}"
        mega = mega_items[0]
        assert mega.get("label") == "TEST Mega"
        assert len(mega.get("children") or []) >= 2

    def test_public_design_reflects_mega(self):
        r = requests.get(f"{BASE_URL}/api/public/sites/{SITE_ID}/design")
        assert r.status_code == 200
        body = r.json() or {}
        nav = (body.get("design") or body).get("navigation") or {}
        header = nav.get("header") or []
        mega_items = [h for h in header if h.get("type") == "mega"]
        assert len(mega_items) >= 1, f"design.navigation.header should expose mega item. Got header: {header}"


# -------- Item 7: Regression --------
class TestRegression:
    def test_llm_status(self, auth_session):
        r = auth_session.get(f"{BASE_URL}/api/platform/llm-status")
        assert r.status_code == 200

    def test_auth_me(self, auth_session):
        r = auth_session.get(f"{BASE_URL}/api/auth/me")
        assert r.status_code == 200
        assert r.json().get("email") == CONCEPTEUR_EMAIL

    def test_get_site_design(self, auth_session):
        r = auth_session.get(f"{BASE_URL}/api/sites/{SITE_ID}/design")
        assert r.status_code == 200

    def test_patch_section_hero(self, auth_session):
        payload = {"title": "Hero iter23", "subtitle": "Regression", "cta_primary": "Découvrir"}
        r = auth_session.patch(f"{BASE_URL}/api/sites/{SITE_ID}/design/section/hero", json=payload)
        assert r.status_code == 200

    def test_public_shop_endpoint(self):
        # /shop/{id} is an SPA route (frontend). Public design endpoint is canonical.
        r = requests.get(f"{BASE_URL}/api/public/sites/{SITE_ID}/design")
        assert r.status_code == 200
        body = r.json() or {}
        design = body.get("design") or body
        assert design.get("hero") is not None
