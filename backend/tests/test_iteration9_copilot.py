"""
Iteration 9 — AI Copilot (ReAct) backend tests.

Focus on non-LLM surface:
- /copilot/tools visibility (admin 9, concepteur 8)
- /copilot/sessions CRUD (list/get/delete)
- validation branches that run without LLM (via copilot.routes handlers directly)
- ONE minimal LLM call to /copilot/chat "Liste mes sites" to verify tool chaining
  (may be skipped if budget=402 or timeout).

Credentials from /app/memory/test_credentials.md.
"""
import asyncio
import os
import uuid


# Ensure backend/.env is loaded so direct imports of routes.copilot work (needs MONGO_URL etc.)
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[1] / ".env")
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
assert BASE_URL, "REACT_APP_BACKEND_URL missing"

ADMIN = {"email": "admin@conceptfactory.fr", "password": "Factory2026!"}
CONC = {"email": "concepteur@conceptfactory.fr", "password": "Concepteur2026!"}


def _login(creds):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json=creds, timeout=30)
    assert r.status_code == 200, f"login failed {r.status_code} {r.text[:120]}"
    return s


@pytest.fixture(scope="module")
def admin_sess():
    return _login(ADMIN)


@pytest.fixture(scope="module")
def conc_sess():
    return _login(CONC)


# ---------------- /copilot/tools ---------------- #
class TestTools:
    def test_concepteur_sees_8_tools_no_empire(self, conc_sess):
        r = conc_sess.get(f"{BASE_URL}/api/copilot/tools", timeout=15)
        assert r.status_code == 200
        data = r.json()
        names = {t["name"] for t in data}
        assert len(data) == 8, f"expected 8 tools for concepteur, got {len(data)}: {names}"
        assert "empire_overview" not in names
        # required concepteur tools
        for n in ["list_my_sites", "get_site_details", "get_site_orders",
                  "get_site_products", "update_product_price",
                  "batch_update_prices", "search_sites", "list_scale_family"]:
            assert n in names, f"missing tool {n}"

    def test_admin_sees_9_tools_including_empire(self, admin_sess):
        r = admin_sess.get(f"{BASE_URL}/api/copilot/tools", timeout=15)
        assert r.status_code == 200
        data = r.json()
        names = {t["name"] for t in data}
        assert len(data) == 9, f"expected 9 tools for admin, got {len(data)}: {names}"
        assert "empire_overview" in names
        empire = next(t for t in data if t["name"] == "empire_overview")
        assert empire["admin_only"] is True

    def test_tools_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/copilot/tools", timeout=15)
        assert r.status_code in (401, 403)


# ---------------- /copilot/sessions (empty user) ---------------- #
class TestSessionsList:
    def test_list_sessions_shape(self, conc_sess):
        r = conc_sess.get(f"{BASE_URL}/api/copilot/sessions", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        for s in data:
            assert "session_id" in s
            assert "message_count" in s
            assert "last_message_preview" in s

    def test_get_nonexistent_session_returns_empty(self, conc_sess):
        sid = f"does-not-exist-{uuid.uuid4()}"
        r = conc_sess.get(f"{BASE_URL}/api/copilot/sessions/{sid}", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert data["session_id"] == sid
        assert data["messages"] == []

    def test_delete_nonexistent_session_ok_zero(self, conc_sess):
        sid = f"ghost-{uuid.uuid4()}"
        r = conc_sess.delete(f"{BASE_URL}/api/copilot/sessions/{sid}", timeout=15)
        assert r.status_code == 200
        assert r.json().get("deleted") == 0


# ---------------- Minimal ReAct end-to-end (1 LLM call) ---------------- #
class TestChatReAct:
    """Single real LLM call. If budget is exhausted (402) or ingress 504, skip rather than fail."""

    def test_liste_mes_sites_invokes_list_my_sites_tool(self, conc_sess):
        payload = {"message": "Liste mes sites"}
        r = conc_sess.post(f"{BASE_URL}/api/copilot/chat", json=payload, timeout=180)
        if r.status_code in (402, 502, 503, 504):
            pytest.skip(f"LLM infra/budget gate: {r.status_code} {r.text[:120]}")
        assert r.status_code == 200, f"{r.status_code} {r.text[:200]}"
        data = r.json()
        assert "session_id" in data and data["session_id"]
        assert "final_answer" in data and isinstance(data["final_answer"], str)
        assert "tool_trace" in data and isinstance(data["tool_trace"], list)
        # At least one tool call should be list_my_sites or search_sites
        tool_names = [t.get("name") for t in data["tool_trace"]]
        assert any(n == "list_my_sites" for n in tool_names), (
            f"expected list_my_sites in trace, got {tool_names}"
        )

        # persist to sessions list
        sid = data["session_id"]
        r2 = conc_sess.get(f"{BASE_URL}/api/copilot/sessions/{sid}", timeout=15)
        assert r2.status_code == 200
        msgs = r2.json()["messages"]
        assert any(m["role"] == "user" for m in msgs)
        assert any(m["role"] == "assistant_final" for m in msgs)

        # cleanup
        conc_sess.delete(f"{BASE_URL}/api/copilot/sessions/{sid}", timeout=15)


# ---------------- Validation branches (direct handler, no LLM) ---------------- #
# We call tool handlers directly via asyncio.run to avoid burning LLM tokens on validation-only cases.
def _run(coro):
    return asyncio.new_event_loop().run_until_complete(coro) if False else asyncio.run(coro)


class TestHandlerValidation:
    def test_batch_update_rejects_pct_over_50(self):
        from routes.copilot import h_batch_update_prices
        res = asyncio.run(h_batch_update_prices({"id": "fake", "role": "admin"},
                                                {"site_id": "x", "pct_change": 99}))
        assert "error" in res and "50" in res["error"]

    def test_batch_update_rejects_pct_under_minus_50(self):
        from routes.copilot import h_batch_update_prices
        res = asyncio.run(h_batch_update_prices({"id": "fake", "role": "admin"},
                                                {"site_id": "x", "pct_change": -75}))
        assert "error" in res

    def test_batch_update_rejects_non_numeric(self):
        from routes.copilot import h_batch_update_prices
        res = asyncio.run(h_batch_update_prices({"id": "fake", "role": "admin"},
                                                {"site_id": "x", "pct_change": "abc"}))
        assert "error" in res

    def test_update_product_price_rejects_negative(self):
        from routes.copilot import h_update_product_price
        res = asyncio.run(h_update_product_price(
            {"id": "fake", "role": "admin"},
            {"site_id": "x", "product_id": "y", "new_price": -5}))
        assert "error" in res and "bornes" in res["error"]

    def test_update_product_price_rejects_over_100k(self):
        from routes.copilot import h_update_product_price
        res = asyncio.run(h_update_product_price(
            {"id": "fake", "role": "admin"},
            {"site_id": "x", "product_id": "y", "new_price": 999999}))
        assert "error" in res

    def test_update_product_price_rejects_non_numeric(self):
        from routes.copilot import h_update_product_price
        res = asyncio.run(h_update_product_price(
            {"id": "fake", "role": "admin"},
            {"site_id": "x", "product_id": "y", "new_price": "free"}))
        assert "error" in res and "nombre" in res["error"]

    def test_search_sites_rejects_empty_query(self):
        from routes.copilot import h_search_sites
        res = asyncio.run(h_search_sites({"id": "fake", "role": "admin"}, {"query": ""}))
        assert "error" in res

    def test_empire_overview_rejects_non_admin(self):
        from routes.copilot import h_empire_overview
        res = asyncio.run(h_empire_overview({"id": "x", "role": "operator"}, {}))
        assert "error" in res and "admin" in res["error"].lower()

    def test_cross_user_site_access_denied(self):
        """Concepteur cannot access a site whose operator_id != his id."""
        from routes.copilot import h_get_site_details
        fake_user = {"id": "nonexistent-user-" + uuid.uuid4().hex, "role": "operator"}
        res = asyncio.run(h_get_site_details(fake_user, {"site_id": "nonexistent-site-id"}))
        assert "error" in res and "accès refusé" in res["error"]
