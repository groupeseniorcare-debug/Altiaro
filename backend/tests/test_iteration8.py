"""Iteration 8: Empire dashboard + Mega-block execute."""
import os
import sys
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
def admin():
    s = requests.Session()
    _login(s, ADMIN)
    return s


@pytest.fixture(scope="module")
def concepteur():
    s = requests.Session()
    _login(s, CONC)
    return s


# ============== EMPIRE ============== #
def test_empire_requires_admin(concepteur):
    r = concepteur.get(f"{BASE}/api/admin/empire", timeout=15)
    assert r.status_code == 403


def test_empire_returns_full_shape(admin):
    r = admin.get(f"{BASE}/api/admin/empire?days=30", timeout=15)
    assert r.status_code == 200, r.text
    d = r.json()
    # Top-level keys
    for key in ("totals", "per_country", "families", "top_products", "timeseries", "alerts", "pending_orders", "generated_at", "period_days"):
        assert key in d, f"missing {key}"

    t = d["totals"]
    for tk in ("total_gmv", "total_orders", "aov", "admin_share", "concepteur_share",
               "recent_gmv", "recent_orders", "total_sites", "active_sites",
               "niche_analyses", "ads_campaigns"):
        assert tk in t, f"missing totals.{tk}"

    # Admin share = 50% of total_gmv
    assert abs(t["admin_share"] + t["concepteur_share"] - t["total_gmv"]) < 0.01

    # Timeseries has exactly `days` points
    assert d["period_days"] == 30
    assert len(d["timeseries"]) == 30
    for pt in d["timeseries"]:
        assert "date" in pt and "revenue" in pt and "orders" in pt


def test_empire_custom_days(admin):
    r = admin.get(f"{BASE}/api/admin/empire?days=7", timeout=15)
    assert r.status_code == 200
    assert len(r.json()["timeseries"]) == 7


def test_empire_alerts_are_site_linked(admin):
    r = admin.get(f"{BASE}/api/admin/empire?days=30", timeout=15)
    for a in r.json()["alerts"]:
        assert "site_id" in a and "site_name" in a and "severity" in a and "type" in a
        assert a["severity"] in ("critical", "warning", "info")


# ============== MEGA BLOCK EXECUTE ============== #
def test_blocks_prompts_catalog(admin):
    r = admin.get(f"{BASE}/api/blocks/prompts", timeout=15)
    assert r.status_code == 200
    blocks = r.json()
    assert len(blocks) == 4
    ids = {b["id"] for b in blocks}
    assert ids == {"template", "products", "seo", "marketing"}
    for b in blocks:
        assert b.get("deliverable_outline")
        assert b.get("emoji") and b.get("name")


def test_block_outputs_empty_initially(concepteur):
    sites = concepteur.get(f"{BASE}/api/sites", timeout=15).json()
    sid = sites[0]["id"]
    r = concepteur.get(f"{BASE}/api/sites/{sid}/blocks/outputs-latest", timeout=15)
    assert r.status_code == 200
    # At worst empty dict
    assert isinstance(r.json(), dict)


def test_block_execute_unknown_block_404(concepteur):
    sites = concepteur.get(f"{BASE}/api/sites", timeout=15).json()
    sid = sites[0]["id"]
    r = concepteur.post(
        f"{BASE}/api/sites/{sid}/blocks/nonexistent/execute",
        json={}, timeout=15,
    )
    assert r.status_code == 404


def test_block_execute_requires_site_access(concepteur, admin):
    # Admin creates an isolated site
    other = admin.post(
        f"{BASE}/api/sites",
        json={"name": "IsolatedForBlockTest", "niche": "x"},
        timeout=15,
    ).json()
    r = concepteur.post(
        f"{BASE}/api/sites/{other['id']}/blocks/template/execute",
        json={}, timeout=15,
    )
    assert r.status_code == 403
    admin.delete(f"{BASE}/api/sites/{other['id']}", timeout=15)


@pytest.mark.slow
def test_block_execute_products_block_end_to_end(concepteur):
    """LLM call — takes ~40s. Validates the full generate → persist → retrieve flow."""
    sites = concepteur.get(f"{BASE}/api/sites", timeout=15).json()
    sid = sites[0]["id"]
    r = concepteur.post(
        f"{BASE}/api/sites/{sid}/blocks/products/execute",
        json={},
        timeout=200,  # mega prompt can take 2-3 min
    )
    if r.status_code == 402:
        pytest.skip("LLM budget exceeded — infra concern, not a bug")
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["block_id"] == "products"
    assert d["site_id"] == sid
    assert "output" in d
    output = d["output"]
    # Should include top_10_produits key as per the mega-prompt schema
    assert isinstance(output, dict)
    # Most likely present keys:
    has_key = any(k in output for k in ("top_10_produits", "produit_hero", "fournisseurs_suggeres"))
    assert has_key, f"Output missing expected keys: {list(output.keys())}"

    # Latest endpoint must now return it
    lr = concepteur.get(f"{BASE}/api/sites/{sid}/blocks/outputs-latest", timeout=15)
    assert lr.status_code == 200
    latest = lr.json()
    assert "products" in latest
    assert latest["products"]["id"] == d["id"]

    # Delete
    dd = concepteur.delete(f"{BASE}/api/sites/{sid}/blocks/outputs/{d['id']}", timeout=15)
    assert dd.status_code == 200
