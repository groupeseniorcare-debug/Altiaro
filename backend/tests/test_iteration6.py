"""Iteration 6: site duplication + custom domain management regression."""
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
def site_id(concepteur):
    r = concepteur.get(f"{BASE}/api/sites", timeout=15)
    assert r.status_code == 200
    sites = r.json()
    assert sites, "Concepteur needs at least one site"
    return sites[0]["id"]


# ===================== DUPLICATION ===================== #
def test_duplicate_preserves_50_steps_and_clones_products(concepteur, site_id):
    # Count source products
    src_prod = concepteur.get(f"{BASE}/api/sites/{site_id}/products", timeout=15).json()
    src_count = len(src_prod)

    r = concepteur.post(
        f"{BASE}/api/sites/{site_id}/duplicate",
        json={"name": f"Clone-{uuid.uuid4().hex[:6]}", "copy_products": True},
        timeout=30,
    )
    assert r.status_code == 200, r.text
    new_site = r.json()
    assert new_site["id"] != site_id
    assert new_site.get("duplicated_from") == site_id
    assert new_site["progress_total"] == 50, "should seed 50 fresh steps"
    assert new_site["progress_validated"] == 0
    assert new_site.get("products_cloned") == src_count

    # Verify new site is accessible to the concepteur
    check = concepteur.get(f"{BASE}/api/sites/{new_site['id']}", timeout=15)
    assert check.status_code == 200

    # Cloned products must be in draft and tagged cloned_from
    clones = concepteur.get(f"{BASE}/api/sites/{new_site['id']}/products", timeout=15).json()
    assert len(clones) == src_count
    for p in clones:
        assert p["status"] == "draft"
        assert p.get("cloned_from") is not None

    # Cleanup via admin
    admin_s = requests.Session()
    _login(admin_s, ADMIN)
    admin_s.delete(f"{BASE}/api/sites/{new_site['id']}", timeout=15)


def test_duplicate_without_products_has_empty_catalog(concepteur, site_id):
    r = concepteur.post(
        f"{BASE}/api/sites/{site_id}/duplicate",
        json={"name": f"Nude-{uuid.uuid4().hex[:6]}", "copy_products": False},
        timeout=30,
    )
    assert r.status_code == 200, r.text
    new_site = r.json()
    assert new_site.get("products_cloned") == 0
    prods = concepteur.get(f"{BASE}/api/sites/{new_site['id']}/products", timeout=15).json()
    assert prods == []

    admin_s = requests.Session()
    _login(admin_s, ADMIN)
    admin_s.delete(f"{BASE}/api/sites/{new_site['id']}", timeout=15)


def test_duplicate_cross_user_forbidden(concepteur, admin):
    # Admin creates a site owned by an operator that is NOT the concepteur
    new_op = f"opdup-{uuid.uuid4().hex[:6]}@conceptfactory.fr"
    admin.post(
        f"{BASE}/api/users",
        json={"email": new_op, "name": "OpDup", "password": "Temp2026!", "role": "operator"},
        timeout=15,
    )
    users = admin.get(f"{BASE}/api/users", timeout=15).json()
    op_id = next((u["id"] for u in users if u["email"] == new_op), None)
    assert op_id

    admin_site = admin.post(
        f"{BASE}/api/sites",
        json={"name": f"Other-{uuid.uuid4().hex[:6]}", "niche": "test", "operator_id": op_id},
        timeout=15,
    ).json()

    # Concepteur cannot duplicate a site he doesn't own
    r = concepteur.post(
        f"{BASE}/api/sites/{admin_site['id']}/duplicate",
        json={},
        timeout=15,
    )
    assert r.status_code == 403

    # Cleanup
    admin.delete(f"{BASE}/api/sites/{admin_site['id']}", timeout=15)


# ===================== CUSTOM DOMAIN ===================== #
def test_domain_get_returns_cname_target(concepteur, site_id):
    r = concepteur.get(f"{BASE}/api/sites/{site_id}/domain", timeout=15)
    assert r.status_code == 200, r.text
    d = r.json()
    assert "cname_target" in d
    assert "instructions" in d
    assert d["instructions"]["type"] == "CNAME"


def test_domain_set_invalid_rejected(concepteur, site_id):
    for bad in ["", "no dots", "http://broken", "a" * 260 + ".com", "-invalid.com"]:
        r = concepteur.post(
            f"{BASE}/api/sites/{site_id}/domain",
            json={"custom_domain": bad},
            timeout=10,
        )
        assert r.status_code in (400, 422), f"{bad!r} should be rejected, got {r.status_code}"


def test_domain_set_valid_and_clear(concepteur, site_id):
    dom = f"test-{uuid.uuid4().hex[:6]}.example.com"
    r = concepteur.post(
        f"{BASE}/api/sites/{site_id}/domain",
        json={"custom_domain": dom},
        timeout=10,
    )
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["custom_domain"] == dom
    assert d["custom_domain_verified"] is False

    # Verify will fail (no real DNS), but must return 200 with verified=False
    v = concepteur.post(f"{BASE}/api/sites/{site_id}/domain/verify", timeout=20)
    assert v.status_code == 200, v.text
    assert v.json()["verified"] is False

    # Cleanup
    d2 = concepteur.delete(f"{BASE}/api/sites/{site_id}/domain", timeout=10)
    assert d2.status_code == 200


def test_domain_uniqueness(admin, concepteur, site_id):
    dom = f"unique-{uuid.uuid4().hex[:6]}.example.com"
    r = concepteur.post(
        f"{BASE}/api/sites/{site_id}/domain",
        json={"custom_domain": dom},
        timeout=10,
    )
    assert r.status_code == 200

    # Admin creates another site and tries to use the same domain
    other = admin.post(
        f"{BASE}/api/sites",
        json={"name": f"Other-{uuid.uuid4().hex[:6]}", "niche": "x"},
        timeout=15,
    ).json()
    conflict = admin.post(
        f"{BASE}/api/sites/{other['id']}/domain",
        json={"custom_domain": dom},
        timeout=10,
    )
    assert conflict.status_code == 409

    admin.delete(f"{BASE}/api/sites/{other['id']}", timeout=15)
    concepteur.delete(f"{BASE}/api/sites/{site_id}/domain", timeout=10)


def test_public_resolve_requires_verified(concepteur, site_id):
    dom = f"pub-{uuid.uuid4().hex[:6]}.example.com"
    concepteur.post(
        f"{BASE}/api/sites/{site_id}/domain",
        json={"custom_domain": dom},
        timeout=10,
    )
    # Not verified → 404
    r = requests.get(f"{BASE}/api/public/domains/resolve", params={"host": dom}, timeout=10)
    assert r.status_code == 404

    concepteur.delete(f"{BASE}/api/sites/{site_id}/domain", timeout=10)
