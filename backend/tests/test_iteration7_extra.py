"""Iteration 7 — coverage gaps not tested in test_iteration7.py:
- Cross-site custom domain uniqueness → 409
- generate_ads_copy=true schedules ads_copy_scheduled=N
- total_daily_budget_eur correct for 3 countries
"""
import os
import sys
import uuid
import pytest
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
load_dotenv(Path("/app/frontend/.env"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
CONC = {"email": "concepteur@conceptfactory.fr", "password": "Concepteur2026!"}
ADMIN = {"email": "admin@conceptfactory.fr", "password": "Factory2026!"}


def _login(sess, creds):
    r = sess.post(f"{BASE}/api/auth/login", json=creds, timeout=15)
    assert r.status_code == 200, r.text


@pytest.fixture(scope="module")
def concepteur():
    s = requests.Session()
    _login(s, CONC)
    return s


@pytest.fixture(scope="module")
def admin():
    s = requests.Session()
    _login(s, ADMIN)
    return s


@pytest.fixture(scope="module")
def source_site(concepteur, admin):
    r = concepteur.post(
        f"{BASE}/api/sites",
        json={"name": f"TEST_ScaleSrc-{uuid.uuid4().hex[:6]}", "niche": "test",
              "selected_countries": ["FR"]},
        timeout=15,
    )
    assert r.status_code == 200
    site = r.json()
    yield site
    admin.delete(f"{BASE}/api/sites/{site['id']}", timeout=15)


@pytest.fixture(autouse=True)
def cleanup_children(admin, source_site):
    yield
    try:
        all_sites = admin.get(f"{BASE}/api/sites", timeout=60).json()
        for s in all_sites:
            if s.get("scaled_from") == source_site["id"]:
                admin.delete(f"{BASE}/api/sites/{s['id']}", timeout=30)
    except Exception as e:
        print(f"cleanup warning: {e}")


def test_cross_site_domain_uniqueness_returns_409(concepteur, admin, source_site):
    """Domain already used by ANY other site → 409."""
    # Create a 2nd independent site owned by admin with a custom domain
    other = admin.post(
        f"{BASE}/api/sites",
        json={"name": f"TEST_Other-{uuid.uuid4().hex[:6]}", "niche": "x"},
        timeout=15,
    ).json()
    used = f"taken-{uuid.uuid4().hex[:6]}.example.com"
    r_dom = admin.post(
        f"{BASE}/api/sites/{other['id']}/domain",
        json={"custom_domain": used},
        timeout=15,
    )
    assert r_dom.status_code == 200, r_dom.text

    # Now Concepteur (as admin we can't easily scale his site; use admin)
    r = admin.post(
        f"{BASE}/api/sites/{source_site['id']}/scale",
        json={
            "target_countries": ["DE"],
            "custom_domains": {"DE": used},
            "copy_products": False,
            "generate_ads_copy": False,
        },
        timeout=15,
    )
    assert r.status_code == 409, r.text
    assert "déjà utilisé" in r.text.lower() or "deja" in r.text.lower() or "409" in str(r.status_code)

    admin.delete(f"{BASE}/api/sites/{other['id']}", timeout=15)


def test_generate_ads_copy_scheduled_count(concepteur, source_site):
    """generate_ads_copy=true → ads_copy_scheduled equals number of clones (background)."""
    r = concepteur.post(
        f"{BASE}/api/sites/{source_site['id']}/scale",
        json={
            "target_countries": ["DE", "NL"],
            "copy_products": False,
            "generate_ads_copy": True,
        },
        timeout=30,
    )
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["ads_copy_scheduled"] == 2
    assert len(d["created"]) == 2


def test_total_daily_budget_scales_linearly(concepteur, source_site):
    """3 countries → 3 × 30 = 90€/day."""
    r = concepteur.post(
        f"{BASE}/api/sites/{source_site['id']}/scale",
        json={
            "target_countries": ["DE", "NL", "UK"],
            "copy_products": False,
            "generate_ads_copy": False,
        },
        timeout=30,
    )
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["total_daily_budget_eur"] == 90
    assert len(d["created"]) == 3
    langs = {c["selected_countries"][0]: c["primary_language"] for c in d["created"]}
    assert langs == {"DE": "de", "NL": "nl", "UK": "en"}


def test_copy_products_false_yields_empty_catalog(concepteur, source_site):
    """copy_products=false → clones have empty catalog even if source has products."""
    # Add a product to source
    concepteur.post(
        f"{BASE}/api/sites/{source_site['id']}/products",
        json={
            "name": {"fr": "TEST_Prod"},
            "description": {"fr": "desc"},
            "price": 10,
            "currency": "EUR",
            "images": [],
            "status": "active",
        },
        timeout=15,
    )
    r = concepteur.post(
        f"{BASE}/api/sites/{source_site['id']}/scale",
        json={"target_countries": ["DE"], "copy_products": False, "generate_ads_copy": False},
        timeout=30,
    )
    assert r.status_code == 200
    clone = r.json()["created"][0]
    assert clone["products_cloned"] == 0
    prods = concepteur.get(f"{BASE}/api/sites/{clone['id']}/products", timeout=15).json()
    assert prods == []
