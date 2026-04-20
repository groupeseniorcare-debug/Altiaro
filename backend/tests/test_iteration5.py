"""Iteration 5: ads-copy generator + blocks refactor regression."""
import os, csv, io, sys, pytest, requests
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
    user = _login(s, CONC)
    return s, user


@pytest.fixture(scope="module")
def admin():
    s = requests.Session()
    user = _login(s, ADMIN)
    return s, user


@pytest.fixture(scope="module")
def site_id(concepteur):
    s, _ = concepteur
    r = s.get(f"{BASE}/api/sites", timeout=15)
    assert r.status_code == 200
    sites = r.json()
    assert sites, "Concepteur must have at least one site"
    return sites[0]["id"]


# ---------- META / BLOCKS ----------
def test_meta_blocks(concepteur):
    s, _ = concepteur
    r = s.get(f"{BASE}/api/meta/blocks", timeout=15)
    assert r.status_code == 200
    blocks = r.json()
    ids = [b["id"] for b in blocks]
    assert ids == ["template", "products", "seo", "marketing"]
    for b in blocks:
        assert b["name"] and b["emoji"] and isinstance(b["phases"], list) and b["phases"]


def test_meta_phases_backward_compat(concepteur):
    s, _ = concepteur
    r = s.get(f"{BASE}/api/meta/phases", timeout=15)
    assert r.status_code == 200
    phases = r.json()
    assert len(phases) == 15
    for p in phases:
        assert p["block"] in {"template", "products", "seo", "marketing"}


def test_steps_have_block_fields(concepteur, site_id):
    s, _ = concepteur
    r = s.get(f"{BASE}/api/sites/{site_id}/steps", timeout=15)
    assert r.status_code == 200
    steps = r.json()
    assert len(steps) == 50
    for st in steps:
        assert st.get("block") in {"template", "products", "seo", "marketing"}, st
        assert st.get("block_name") and st.get("block_emoji")
        assert isinstance(st.get("block_order"), int)


def test_backfill_all_steps_have_block(admin):
    """Scan steps across all sites — none should lack block after backfill."""
    s, _ = admin
    r = s.get(f"{BASE}/api/sites", timeout=15)
    assert r.status_code == 200
    sites = r.json()
    bad = 0
    total = 0
    for site in sites[:5]:  # sample 5 sites
        rs = s.get(f"{BASE}/api/sites/{site['id']}/steps", timeout=15)
        if rs.status_code == 200:
            for st in rs.json():
                total += 1
                if not st.get("block"):
                    bad += 1
    assert bad == 0, f"{bad}/{total} steps missing block"
    assert total >= 50


# ---------- ADS COPY ----------
def test_generate_fr_ads_copy(concepteur, site_id):
    s, _ = concepteur
    payload = {"country": "FR", "language": "fr", "tone": "rassurant", "product_focus": "coussin orthopédique"}
    r = s.post(f"{BASE}/api/sites/{site_id}/ads-copy/generate", json=payload, timeout=120)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["country"] == "FR" and d["language"] == "fr"
    data = d["data"]
    assert len(data["headlines"]) == 15
    assert all(len(h) <= 30 for h in data["headlines"]), [(h, len(h)) for h in data["headlines"]]
    assert len(data["descriptions"]) == 4
    assert all(len(x) <= 90 for x in data["descriptions"])
    assert len(data["keywords"]) >= 20
    assert isinstance(data["sitelinks"], list) and len(data["sitelinks"]) >= 1
    assert isinstance(data["callouts"], list) and len(data["callouts"]) >= 1
    assert "_id" not in d
    # persist copy_id for downstream tests
    pytest.fr_copy_id = d["id"]


def test_generate_de_ads_copy(concepteur, site_id):
    s, _ = concepteur
    payload = {"country": "DE", "language": "de", "tone": "premium"}
    r = s.post(f"{BASE}/api/sites/{site_id}/ads-copy/generate", json=payload, timeout=120)
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    assert all(len(h) <= 30 for h in data["headlines"])
    assert all(len(x) <= 90 for x in data["descriptions"])


def test_generate_invalid_country(concepteur, site_id):
    s, _ = concepteur
    r = s.post(f"{BASE}/api/sites/{site_id}/ads-copy/generate", json={"country": "XX"}, timeout=20)
    assert r.status_code == 400


def test_list_ads_copy(concepteur, site_id):
    s, _ = concepteur
    r = s.get(f"{BASE}/api/sites/{site_id}/ads-copy", timeout=15)
    assert r.status_code == 200
    items = r.json()
    assert isinstance(items, list) and len(items) >= 2
    # sorted desc by created_at
    times = [i["created_at"] for i in items]
    assert times == sorted(times, reverse=True)
    for it in items:
        assert "_id" not in it


def test_get_ads_copy_detail(concepteur, site_id):
    s, _ = concepteur
    cid = pytest.fr_copy_id
    r = s.get(f"{BASE}/api/sites/{site_id}/ads-copy/{cid}", timeout=15)
    assert r.status_code == 200
    d = r.json()
    assert d["id"] == cid and "_id" not in d


def test_export_csv(concepteur, site_id):
    s, _ = concepteur
    cid = pytest.fr_copy_id
    r = s.get(f"{BASE}/api/sites/{site_id}/ads-copy/{cid}/export.csv", timeout=15)
    assert r.status_code == 200
    assert "text/csv" in r.headers.get("content-type", "")
    rows = list(csv.reader(io.StringIO(r.text)))
    assert rows[0] == ["Type", "Index", "Text", "Character count"]
    types = {row[0] for row in rows[1:]}
    assert {"Headline", "Description", "Keyword", "NegativeKeyword", "Callout"}.issubset(types)


def test_cross_site_forbidden(admin, concepteur):
    """Concepteur must NOT access admin-owned site's ads-copy."""
    s_admin, _ = admin
    # find a site NOT owned by concepteur
    all_sites = s_admin.get(f"{BASE}/api/sites", timeout=15).json()
    s_conc, me = concepteur
    mine = {x["id"] for x in s_conc.get(f"{BASE}/api/sites", timeout=15).json()}
    foreign = next((x for x in all_sites if x["id"] not in mine), None)
    if not foreign:
        pytest.skip("No foreign site available")
    r = s_conc.post(
        f"{BASE}/api/sites/{foreign['id']}/ads-copy/generate",
        json={"country": "FR"}, timeout=20,
    )
    assert r.status_code in (403, 404)


def test_delete_ads_copy(concepteur, site_id):
    s, _ = concepteur
    cid = pytest.fr_copy_id
    r = s.delete(f"{BASE}/api/sites/{site_id}/ads-copy/{cid}", timeout=15)
    assert r.status_code == 200
    r2 = s.get(f"{BASE}/api/sites/{site_id}/ads-copy/{cid}", timeout=15)
    assert r2.status_code == 404


# ---------- REGRESSION ----------
def test_health(concepteur):
    s, _ = concepteur
    assert s.get(f"{BASE}/api/health", timeout=10).status_code == 200


def test_sites_list_regression(concepteur):
    s, _ = concepteur
    assert s.get(f"{BASE}/api/sites", timeout=10).status_code == 200


def test_truncate_unit():
    from routes.ads_copy import _truncate, _validate_and_sanitize
    assert _truncate("a" * 100, 30).endswith("…") and len(_truncate("a" * 100, 30)) == 30
    clean = _validate_and_sanitize({
        "headlines": ["x" * 50] * 20,
        "descriptions": ["y" * 200] * 6,
        "keywords": ["kw"] * 50,
        "negative_keywords": ["n"] * 40,
        "sitelinks": [{"title": "t" * 50, "desc1": "d" * 50, "desc2": "d" * 50, "url_suffix": "/x"}] * 10,
        "callouts": ["c" * 40] * 20,
    })
    assert len(clean["headlines"]) == 15 and all(len(h) <= 30 for h in clean["headlines"])
    assert len(clean["descriptions"]) == 4 and all(len(d) <= 90 for d in clean["descriptions"])
    assert len(clean["keywords"]) == 40
    assert all(len(s["title"]) <= 25 for s in clean["sitelinks"])
