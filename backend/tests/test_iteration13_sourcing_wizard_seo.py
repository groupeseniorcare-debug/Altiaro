"""Sprint 16+17 tests — Sourcing CJ/AE, Wizard 10 steps, SEO (sitemap/robots/merchant-feed)."""
import os
import re
import pytest
import requests
import xml.etree.ElementTree as ET

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://senior-france.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@conceptfactory.fr"
ADMIN_PWD = "Factory2026!"


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PWD}, timeout=15)
    assert r.status_code == 200, f"Login admin failed: {r.status_code} {r.text[:200]}"
    return s


@pytest.fixture(scope="module")
def site_id(admin_session):
    r = admin_session.get(f"{API}/sites", timeout=15)
    assert r.status_code == 200
    data = r.json()
    sites = data if isinstance(data, list) else data.get("sites", [])
    assert sites, "No site available"
    return sites[0]["id"]


# ========= SOURCING =========

class TestSourcing:
    def test_providers_list(self, admin_session):
        r = admin_session.get(f"{API}/sourcing/providers", timeout=10)
        assert r.status_code == 200, r.text[:200]
        data = r.json()
        assert "providers" in data
        providers = data["providers"]
        assert len(providers) == 2
        ids = {p["id"] for p in providers}
        assert ids == {"cj", "aliexpress"}
        # Expect enabled False because no keys configured
        for p in providers:
            assert p["enabled"] is False
            assert "setup_steps" in p
            assert "setup_url" in p

    def test_search_empty_keyword_400(self, admin_session):
        r = admin_session.post(f"{API}/sourcing/search", json={"keyword": "   "}, timeout=10)
        assert r.status_code == 400

    def test_search_returns_empty_no_500(self, admin_session):
        r = admin_session.post(f"{API}/sourcing/search",
                               json={"keyword": "massage chair", "country": "FR"}, timeout=15)
        assert r.status_code == 200, f"Got {r.status_code}: {r.text[:200]}"
        d = r.json()
        assert d["count"] == 0
        assert d["results"] == []
        assert d["providers_available"] == {"cj": False, "aliexpress": False}

    def test_import_product(self, admin_session, site_id):
        payload = {
            "provider": "cj",
            "product_id": "TEST123XYZ",
            "title": "TEST Seat Cushion Premium",
            "image": "https://example.com/img.jpg",
            "price_eur": 49.90,
            "cost_eur": 12.50,
            "supplier_url": "https://cj.test/p/TEST123",
            "sku": "TEST-CJ-1",
        }
        r = admin_session.post(f"{API}/sites/{site_id}/sourcing/import",
                               json=payload, timeout=15)
        assert r.status_code == 200, r.text[:200]
        d = r.json()
        assert d["ok"] is True
        prod = d["product"]
        # _id must be excluded
        assert "_id" not in prod
        assert prod["cost_price_ht"] == 12.50
        assert prod["price"] == 49.90
        assert prod["site_id"] == site_id
        assert prod["source"]["provider"] == "cj"
        assert prod["source"]["product_id"] == "TEST123XYZ"
        assert prod["status"] == "draft"
        # name multilingue
        assert prod["name"]["fr"] == "TEST Seat Cushion Premium"


# ========= WIZARD =========

class TestWizard:
    def test_get_wizard_10_steps(self, admin_session, site_id):
        r = admin_session.get(f"{API}/sites/{site_id}/wizard", timeout=10)
        assert r.status_code == 200, r.text[:200]
        d = r.json()
        assert len(d["definition"]) == 10
        ids = [s["id"] for s in d["definition"]]
        expected = ["product", "countries", "sourcing", "pricing", "positioning",
                    "identity", "seo", "content", "legal", "publish"]
        assert ids == expected
        assert d["progress"]["total"] == 10
        assert "percent" in d["progress"]
        assert d["current"] in set(expected)

    def test_auto_detect_sourcing_done(self, admin_session, site_id):
        # After sourcing import, 'sourcing' and 'pricing' steps should auto mark
        r = admin_session.get(f"{API}/sites/{site_id}/wizard", timeout=10)
        d = r.json()
        assert d["steps"]["sourcing"]["status"] == "done", "sourcing should auto-mark after import"
        assert d["steps"]["pricing"]["status"] == "done", "pricing should auto-mark when cost_price_ht>0"

    def test_mark_step_done_and_pending(self, admin_session, site_id):
        # Mark positioning done
        r = admin_session.post(f"{API}/sites/{site_id}/wizard/step/positioning",
                               json={"status": "done", "advance_to": "identity"}, timeout=10)
        assert r.status_code == 200, r.text[:200]
        d = r.json()
        assert d["ok"] is True
        assert d["step"]["status"] == "done"
        assert d["current"] == "identity"
        # Reopen (pending)
        r2 = admin_session.post(f"{API}/sites/{site_id}/wizard/step/positioning",
                                json={"status": "pending"}, timeout=10)
        assert r2.status_code == 200
        assert r2.json()["step"]["status"] == "pending"

    def test_invalid_step_400(self, admin_session, site_id):
        r = admin_session.post(f"{API}/sites/{site_id}/wizard/step/__unknown__",
                               json={"status": "done"}, timeout=10)
        assert r.status_code == 400


# ========= SEO =========

class TestSEO:
    def test_sitemap_valid_xml_with_hreflang(self, admin_session, site_id):
        r = requests.get(f"{API}/public/sites/{site_id}/sitemap.xml", timeout=10)
        assert r.status_code == 200, r.text[:200]
        assert "application/xml" in r.headers.get("content-type", "")
        root = ET.fromstring(r.content)
        assert root.tag.endswith("urlset")
        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9",
              "xhtml": "http://www.w3.org/1999/xhtml"}
        urls = root.findall("sm:url", ns)
        assert len(urls) >= 7  # home + about + faq + contact + cgv + mentions + conf
        # At least one url has hreflang alternates
        alts = root.findall(".//xhtml:link", ns)
        assert len(alts) > 0, "No hreflang alternate links found"
        # Each has hreflang and href attrs
        for a in alts[:3]:
            assert a.get("hreflang")
            assert a.get("href")

    def test_robots_txt(self, site_id):
        r = requests.get(f"{API}/public/sites/{site_id}/robots.txt", timeout=10)
        assert r.status_code == 200
        assert "text/plain" in r.headers.get("content-type", "")
        body = r.text
        assert "User-agent: *" in body
        assert "Sitemap:" in body
        assert f"/api/public/sites/{site_id}/sitemap.xml" in body

    @pytest.mark.parametrize("country,expected_currency", [
        ("FR", "EUR"), ("DE", "EUR"), ("BE", "EUR"),
        ("NL", "EUR"), ("UK", "GBP"), ("CH", "CHF"),
    ])
    def test_merchant_feed_per_country(self, site_id, country, expected_currency):
        r = requests.get(f"{API}/public/sites/{site_id}/merchant-feed.xml?country={country}",
                         timeout=15)
        assert r.status_code == 200, r.text[:200]
        assert "application/xml" in r.headers.get("content-type", "")
        body = r.text
        # Valid XML
        root = ET.fromstring(r.content)
        assert root.tag == "rss"
        assert root.get("version") == "2.0"
        # Namespace declared
        assert "xmlns:g=" in body
        # Channel title contains country code
        channel = root.find("channel")
        assert channel is not None
        title = channel.find("title").text or ""
        assert country in title
        # Items check (if any products active)
        items = channel.findall("item")
        if items:
            # Check raw body for g: prefixed tags (ET normalizes namespace)
            for tag in ["<g:id>", "<g:title>", "<g:price>", "<g:link>", "<g:availability>"]:
                assert tag in body, f"{tag} missing in merchant feed"
            assert expected_currency in body


# ========= Regression =========

class TestRegression:
    def test_auth_me(self, admin_session):
        r = admin_session.get(f"{API}/auth/me", timeout=10)
        assert r.status_code == 200
        assert r.json()["email"] == ADMIN_EMAIL

    def test_sites_list(self, admin_session):
        r = admin_session.get(f"{API}/sites", timeout=10)
        assert r.status_code == 200

    def test_products_list(self, admin_session, site_id):
        r = admin_session.get(f"{API}/sites/{site_id}/products", timeout=10)
        assert r.status_code in (200,)
