"""Iteration 7: scale-6-pays (multi-country mass duplication)."""
import os
import sys
import uuid
import time
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
    return r.json()


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
    """Creates a fresh source site for scaling tests (isolated from other tests)."""
    r = concepteur.post(
        f"{BASE}/api/sites",
        json={
            "name": f"ScaleSource-{uuid.uuid4().hex[:6]}",
            "niche": "test scale",
            "selected_countries": ["FR"],
        },
        timeout=15,
    )
    assert r.status_code == 200, r.text
    site = r.json()
    yield site
    admin.delete(f"{BASE}/api/sites/{site['id']}", timeout=15)


@pytest.fixture(autouse=True)
def cleanup_scaled_children(admin, source_site):
    """Delete any scaled children after each test (so each test starts clean)."""
    yield
    all_sites = admin.get(f"{BASE}/api/sites", timeout=15).json()
    for s in all_sites:
        if s.get("scaled_from") == source_site["id"]:
            admin.delete(f"{BASE}/api/sites/{s['id']}", timeout=15)


def test_scale_to_2_countries(concepteur, source_site):
    r = concepteur.post(
        f"{BASE}/api/sites/{source_site['id']}/scale",
        json={
            "target_countries": ["DE", "NL"],
            "copy_products": False,
            "generate_ads_copy": False,
        },
        timeout=30,
    )
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["source_site_id"] == source_site["id"]
    assert d["scale_batch_id"]
    assert len(d["created"]) == 2
    assert d["total_daily_budget_eur"] == 60
    assert d["ads_copy_scheduled"] == 0

    countries = {c["selected_countries"][0] for c in d["created"]}
    assert countries == {"DE", "NL"}

    # All clones have fresh steps
    for clone in d["created"]:
        assert clone["progress_total"] == 50
        assert clone["progress_validated"] == 0
        assert clone["daily_budget_eur"] == 30
        assert clone["scaled_from"] == source_site["id"]
        assert clone["primary_language"] in {"fr", "de", "en", "nl"}

    # German clone should have German as primary language
    de = next(c for c in d["created"] if c["selected_countries"][0] == "DE")
    assert de["primary_language"] == "de"
    nl = next(c for c in d["created"] if c["selected_countries"][0] == "NL")
    assert nl["primary_language"] == "nl"


def test_scale_rejects_invalid_country(concepteur, source_site):
    r = concepteur.post(
        f"{BASE}/api/sites/{source_site['id']}/scale",
        json={"target_countries": ["XX"], "copy_products": False, "generate_ads_copy": False},
        timeout=15,
    )
    assert r.status_code == 400


def test_scale_rejects_empty_list(concepteur, source_site):
    r = concepteur.post(
        f"{BASE}/api/sites/{source_site['id']}/scale",
        json={"target_countries": [], "copy_products": False, "generate_ads_copy": False},
        timeout=15,
    )
    assert r.status_code == 422  # pydantic min_length=1


def test_scale_with_custom_domains(concepteur, source_site):
    dom_de = f"scale-de-{uuid.uuid4().hex[:6]}.example.com"
    dom_nl = f"scale-nl-{uuid.uuid4().hex[:6]}.example.com"
    r = concepteur.post(
        f"{BASE}/api/sites/{source_site['id']}/scale",
        json={
            "target_countries": ["DE", "NL"],
            "custom_domains": {"DE": dom_de, "NL": dom_nl},
            "copy_products": False,
            "generate_ads_copy": False,
        },
        timeout=30,
    )
    assert r.status_code == 200, r.text
    d = r.json()
    domains = {c["selected_countries"][0]: c.get("custom_domain") for c in d["created"]}
    assert domains["DE"] == dom_de
    assert domains["NL"] == dom_nl


def test_scale_rejects_invalid_domain(concepteur, source_site):
    r = concepteur.post(
        f"{BASE}/api/sites/{source_site['id']}/scale",
        json={
            "target_countries": ["DE"],
            "custom_domains": {"DE": "not a valid domain"},
            "copy_products": False,
            "generate_ads_copy": False,
        },
        timeout=15,
    )
    assert r.status_code == 400


def test_scale_rejects_duplicate_domain_across_countries(concepteur, source_site):
    same = f"dup-{uuid.uuid4().hex[:6]}.example.com"
    r = concepteur.post(
        f"{BASE}/api/sites/{source_site['id']}/scale",
        json={
            "target_countries": ["DE", "NL"],
            "custom_domains": {"DE": same, "NL": same},
            "copy_products": False,
            "generate_ads_copy": False,
        },
        timeout=15,
    )
    assert r.status_code == 400


def test_scale_siblings_endpoint(concepteur, source_site):
    # Scale to 2 countries first
    r = concepteur.post(
        f"{BASE}/api/sites/{source_site['id']}/scale",
        json={"target_countries": ["DE", "NL"], "copy_products": False, "generate_ads_copy": False},
        timeout=30,
    )
    assert r.status_code == 200
    batch_id = r.json()["scale_batch_id"]

    # From source perspective
    r2 = concepteur.get(f"{BASE}/api/sites/{source_site['id']}/scale-siblings", timeout=15)
    assert r2.status_code == 200
    d = r2.json()
    assert d["source_id"] == source_site["id"]
    siblings_ids = {s["id"] for s in d["siblings"]}
    assert source_site["id"] in siblings_ids
    assert len(siblings_ids) == 3  # source + 2 clones

    # From a clone perspective
    clone_id = next(s["id"] for s in d["siblings"] if s["id"] != source_site["id"])
    r3 = concepteur.get(f"{BASE}/api/sites/{clone_id}/scale-siblings", timeout=15)
    assert r3.status_code == 200
    d2 = r3.json()
    assert d2["batch_id"] == batch_id


def test_scale_copies_products_as_draft(concepteur, source_site):
    # Add a product to source first
    concepteur.post(
        f"{BASE}/api/sites/{source_site['id']}/products",
        json={
            "name": {"fr": "Test Prod", "en": "", "de": "", "nl": ""},
            "description": {"fr": "desc"},
            "price": 99.99,
            "currency": "EUR",
            "images": [],
            "status": "active",
        },
        timeout=15,
    )
    r = concepteur.post(
        f"{BASE}/api/sites/{source_site['id']}/scale",
        json={"target_countries": ["DE"], "copy_products": True, "generate_ads_copy": False},
        timeout=30,
    )
    assert r.status_code == 200
    clone = r.json()["created"][0]
    assert clone["products_cloned"] == 1

    prods = concepteur.get(f"{BASE}/api/sites/{clone['id']}/products", timeout=15).json()
    assert len(prods) == 1
    assert prods[0]["status"] == "draft"
    assert prods[0]["cloned_from"] is not None


def test_scale_requires_access(concepteur, admin):
    """Concepteur cannot scale a site he doesn't own."""
    admin_site = admin.post(
        f"{BASE}/api/sites",
        json={"name": f"AdminOnly-{uuid.uuid4().hex[:6]}", "niche": "x"},
        timeout=15,
    ).json()
    r = concepteur.post(
        f"{BASE}/api/sites/{admin_site['id']}/scale",
        json={"target_countries": ["DE"], "copy_products": False, "generate_ads_copy": False},
        timeout=15,
    )
    assert r.status_code == 403
    admin.delete(f"{BASE}/api/sites/{admin_site['id']}", timeout=15)
