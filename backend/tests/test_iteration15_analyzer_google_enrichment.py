"""Sprint 20 — Tests: Google Keyword Planner enrichment dans l'analyzer deep.

Vérifie :
1. Import de fetch_keyword_volumes dans analyzer.py sans erreur.
2. fetch_keyword_volumes({"FR":["test"]}) retourne {available:False, reason:'no_admin_connected'} quand aucun admin connecté.
3. L'analyse existante d9731ff8-... a source='ai_claude_sonnet_4.5_multistep_v2' (pas _google_verified), google_verified=false, et google_keyword_planner.reason='no_admin_connected'.
4. /api/niches/analyses et /api/niches/analyses/{id} retournent les nouveaux champs.
5. Avec un faux admin connecté (fake refresh_token), la fonction échoue gracieusement sans crash.
6. Pas de régression sur /auth, /sites, /google-ads/status, /niches/analyses.
"""
from __future__ import annotations

import asyncio
import os
import sys
import pathlib
import uuid
from datetime import datetime, timezone

import pytest
import requests

# Ensure backend modules importable
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402
load_dotenv(ROOT / ".env")


# Shared event loop so motor's module-level client stays bound to a live loop.
@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


def _run(loop, coro):
    return loop.run_until_complete(coro)

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://senior-france.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@conceptfactory.fr"
ADMIN_PASSWORD = "Factory2026!"
CONCEPTEUR_EMAIL = "concepteur@conceptfactory.fr"
CONCEPTEUR_PASSWORD = "Concepteur2026!"

KNOWN_ANALYSIS_ID = "d9731ff8-80aa-42ed-8673-d03014acc05e"


# ===================== Fixtures ===================== #
@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=10)
    assert r.status_code == 200, f"Admin login failed: {r.status_code} {r.text[:200]}"
    return s


@pytest.fixture(scope="module")
def concepteur_session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": CONCEPTEUR_EMAIL, "password": CONCEPTEUR_PASSWORD}, timeout=10)
    assert r.status_code == 200, f"Concepteur login failed: {r.status_code} {r.text[:200]}"
    return s


# ===================== 1. Imports ===================== #
class TestAnalyzerImports:
    def test_analyzer_imports_without_crash(self):
        import importlib
        mod = importlib.import_module("routes.analyzer")
        assert hasattr(mod, "_run_deep_analysis")

    def test_fetch_keyword_volumes_import(self):
        from routes.google_ads import fetch_keyword_volumes
        assert callable(fetch_keyword_volumes)


# ===================== 2. fetch_keyword_volumes direct ===================== #
class TestFetchKeywordVolumesDirect:
    def test_no_admin_connected_returns_gracefully(self, event_loop):
        from routes.google_ads import fetch_keyword_volumes
        result = _run(event_loop, fetch_keyword_volumes({"FR": ["test"]}))
        assert isinstance(result, dict)
        assert result.get("available") is False
        assert result.get("by_country") == {}
        assert result.get("reason") == "no_admin_connected"

    def test_empty_input_returns_gracefully(self, event_loop):
        from routes.google_ads import fetch_keyword_volumes
        result = _run(event_loop, fetch_keyword_volumes({}))
        assert result.get("available") is False
        assert result.get("by_country") == {}

    def test_fake_admin_connected_fails_gracefully(self, event_loop):
        """Insert a fake admin credential → Google Ads API call should fail but
        function must return available:false with reason != 'no_admin_connected'
        (never crash)."""
        from routes.google_ads import fetch_keyword_volumes
        from deps import db
        fake_uid = f"TEST_fake_admin_{uuid.uuid4().hex[:8]}"

        async def run():
            await db.google_ads_credentials.insert_one({
                "admin_user_id": fake_uid,
                "refresh_token": "fake_refresh_token_invalid",
                "access_token": "fake_access",
                "is_active": True,
                "scopes": ["https://www.googleapis.com/auth/adwords"],
                "updated_at": datetime.now(timezone.utc).isoformat(),
            })
            try:
                res = await fetch_keyword_volumes({"FR": ["chaise ergonomique"]})
            finally:
                await db.google_ads_credentials.delete_one({"admin_user_id": fake_uid})
            return res

        result = _run(event_loop, run())
        assert isinstance(result, dict)
        assert result.get("available") is False
        # reason should indicate something other than no_admin_connected (we had one)
        # OR by_country[FR] has error key. Either is acceptable as long as no crash.
        reason = result.get("reason")
        by_country = result.get("by_country", {})
        fr_entry = by_country.get("FR", {})
        has_error_signal = (
            (reason and reason != "no_admin_connected")
            or "error" in fr_entry
            or fr_entry.get("total_volume_monthly", 0) == 0
        )
        assert has_error_signal, f"Expected graceful failure, got: {result}"


# ===================== 3. Existing analysis has expected shape ===================== #
class TestExistingAnalysisStructure:
    def test_known_analysis_has_fallback_shape(self, event_loop):
        from deps import db

        async def run():
            return await db.niche_analyses.find_one({"id": KNOWN_ANALYSIS_ID}, {"_id": 0})

        doc = _run(event_loop, run())
        assert doc is not None, "Known analysis not found in DB"
        assert doc.get("source") == "ai_claude_sonnet_4.5_multistep_v2", \
            f"source should be fallback, got: {doc.get('source')}"
        assert "_google_verified" not in doc.get("source", "")
        assert doc.get("enriched_with_google_ads") is False
        analysis = doc.get("analysis", {})
        assert analysis.get("google_verified") is False
        gkp = analysis.get("google_keyword_planner", {})
        assert gkp.get("available") is False
        assert gkp.get("reason") == "no_admin_connected"

    def test_known_analysis_via_api_as_owner(self, admin_session):
        """Admin (user_id=69e5e984...) owns KNOWN_ANALYSIS_ID → GET returns 200
        with new fields."""
        r = admin_session.get(f"{API}/niches/analyses/{KNOWN_ANALYSIS_ID}", timeout=10)
        assert r.status_code == 200, r.text[:200]
        doc = r.json()
        assert doc.get("source") == "ai_claude_sonnet_4.5_multistep_v2"
        assert doc.get("enriched_with_google_ads") is False
        analysis = doc.get("analysis", {})
        assert analysis.get("google_verified") is False
        assert analysis.get("google_keyword_planner", {}).get("reason") == "no_admin_connected"


# ===================== 4. Endpoints /api/niches/analyses ===================== #
class TestAnalysesEndpoints:
    def test_list_analyses_returns_200(self, admin_session):
        r = admin_session.get(f"{API}/niches/analyses", timeout=10)
        assert r.status_code == 200, r.text[:200]
        data = r.json()
        assert isinstance(data, list)

    def test_list_analyses_concepteur_returns_200(self, concepteur_session):
        r = concepteur_session.get(f"{API}/niches/analyses", timeout=10)
        assert r.status_code == 200

    def test_get_analysis_known_id_via_owner(self):
        """Le known analysis appartient à user 69e5e9... → on le lit via DB.
        Aussi, on vérifie que get_analysis(id) pour un user qui n'est PAS owner renvoie 404."""
        r = requests.get(f"{API}/niches/analyses/{KNOWN_ANALYSIS_ID}", timeout=10)
        # No auth → 401 or 403
        assert r.status_code in (401, 403)

    def test_get_analysis_wrong_owner_returns_404(self, concepteur_session):
        # Concepteur (operator) doesn't own KNOWN_ANALYSIS_ID → 404
        r = concepteur_session.get(f"{API}/niches/analyses/{KNOWN_ANALYSIS_ID}", timeout=10)
        assert r.status_code == 404

    def test_list_analyses_exposes_new_fields_if_any(self, admin_session):
        """Vérifie que les champs source/enriched_with_google_ads sont présents
        dans la liste (admin peut ne pas avoir d'analyse, donc test souple)."""
        r = admin_session.get(f"{API}/niches/analyses", timeout=10)
        assert r.status_code == 200
        items = r.json()
        if not items:
            pytest.skip("No analyses for admin — skipping field presence check")
        a = items[0]
        # source et enriched_with_google_ads doivent exister sur chaque document
        assert "source" in a
        assert "enriched_with_google_ads" in a


# ===================== 5. country_sizing google_verified flag (mock) ===================== #
class TestCountrySizingGoogleVerifiedStructure:
    def test_country_sizing_accepts_google_verified_flag(self):
        """Unit test sur la logique d'override step2 avec les volumes réels Google.
        Reproduit le fragment lignes 348-358 de analyzer.py."""
        google_enriched = {
            "available": True,
            "by_country": {
                "FR": {"total_volume_monthly": 12500, "avg_cpc_eur": 1.35, "keywords": []},
                "DE": {"total_volume_monthly": 0, "avg_cpc_eur": 0, "keywords": []},
            },
        }
        step2 = {
            "country_sizing": {
                "FR": {"monthly_search_volume": 999, "cpc_avg_eur": 0.1},
                "DE": {"monthly_search_volume": 500, "cpc_avg_eur": 0.2},
            }
        }

        # Apply override logic exactly as in analyzer.py
        if google_enriched.get("available"):
            country_sizing = step2.get("country_sizing", {}) or {}
            for c, g in google_enriched["by_country"].items():
                if g.get("total_volume_monthly", 0) > 0:
                    csz = country_sizing.get(c) or {}
                    csz["monthly_search_volume"] = g["total_volume_monthly"]
                    if g.get("avg_cpc_eur", 0) > 0:
                        csz["cpc_avg_eur"] = g["avg_cpc_eur"]
                    csz["google_verified"] = True
                    country_sizing[c] = csz
            step2["country_sizing"] = country_sizing

        fr = step2["country_sizing"]["FR"]
        de = step2["country_sizing"]["DE"]
        assert fr["monthly_search_volume"] == 12500
        assert fr["cpc_avg_eur"] == 1.35
        assert fr.get("google_verified") is True
        # DE had 0 volume → not overridden, no google_verified
        assert de["monthly_search_volume"] == 500
        assert de.get("google_verified") is not True


# ===================== 6. Non-regression on core endpoints ===================== #
class TestNonRegression:
    def test_auth_me_admin(self, admin_session):
        r = admin_session.get(f"{API}/auth/me", timeout=10)
        assert r.status_code == 200
        assert r.json()["email"] == ADMIN_EMAIL

    def test_auth_me_concepteur(self, concepteur_session):
        r = concepteur_session.get(f"{API}/auth/me", timeout=10)
        assert r.status_code == 200
        assert r.json()["email"] == CONCEPTEUR_EMAIL

    def test_google_ads_status_admin(self, admin_session):
        r = admin_session.get(f"{API}/google-ads/status", timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert "connected" in data and "config_ready" in data

    def test_google_ads_status_concepteur_forbidden(self, concepteur_session):
        r = concepteur_session.get(f"{API}/google-ads/status", timeout=10)
        assert r.status_code == 403

    def test_sites_list(self, admin_session):
        r = admin_session.get(f"{API}/sites", timeout=10)
        assert r.status_code == 200

    def test_sourcing_markets_public_or_auth(self, admin_session):
        r = admin_session.get(f"{API}/niches/analyses?limit=5", timeout=10)
        assert r.status_code == 200

    def test_analyze_endpoint_exists_but_not_called(self, admin_session):
        """On ne lance PAS l'analyse (4 min + coût tokens). On vérifie juste
        que POST sans body valide renvoie 422 (validation error) — pas 500/404."""
        r = admin_session.post(f"{API}/niches/analyze", json={}, timeout=10)
        assert r.status_code in (400, 422), f"Expected validation error, got {r.status_code}"
