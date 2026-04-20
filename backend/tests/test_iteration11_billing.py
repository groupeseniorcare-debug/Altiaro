"""Iteration 11 — Billing (Sprint 12) tests.
Covers: /api/billing/card*, /api/billing/iban*, /api/billing/balance, /api/billing/ledger,
admin ads activate/deactivate, admin billing overview, payouts preview, SEPA XML.
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://senior-france.preview.emergentagent.com").rstrip("/")

ADMIN_EMAIL = "admin@conceptfactory.fr"
ADMIN_PW = "Factory2026!"
CONCEPTEUR_EMAIL = "concepteur@conceptfactory.fr"
CONCEPTEUR_PW = "Concepteur2026!"

VALID_IBAN = "FR1420041010050500013M02606"


def _login(email, pw):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": pw}, timeout=15)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text[:200]}"
    return s


@pytest.fixture(scope="module")
def concepteur():
    return _login(CONCEPTEUR_EMAIL, CONCEPTEUR_PW)


@pytest.fixture(scope="module")
def admin():
    return _login(ADMIN_EMAIL, ADMIN_PW)


# ========== Card (concepteur) ==========
class TestCard:
    def test_card_status_initial(self, concepteur):
        # Ensure clean state
        concepteur.delete(f"{BASE_URL}/api/billing/card", timeout=10)
        r = concepteur.get(f"{BASE_URL}/api/billing/card", timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert data["has_card"] is False
        assert data["status"] in ("none", "pending")

    def test_card_setup(self, concepteur):
        r = concepteur.post(f"{BASE_URL}/api/billing/card/setup", json={}, timeout=30)
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        assert "payment_id" in data and data["payment_id"].startswith("tr_")
        assert "checkout_url" in data and "mollie.com" in data["checkout_url"]
        assert data["mode"] in ("test", "live")

    def test_card_status_after_setup(self, concepteur):
        r = concepteur.get(f"{BASE_URL}/api/billing/card", timeout=10)
        assert r.status_code == 200
        assert r.json()["status"] == "pending"

    def test_card_setup_idempotent_customer(self, concepteur):
        # Second setup call should not re-create Mollie customer - we just confirm it succeeds
        r = concepteur.post(f"{BASE_URL}/api/billing/card/setup", json={}, timeout=30)
        assert r.status_code == 200
        assert r.json()["payment_id"].startswith("tr_")

    def test_card_delete(self, concepteur):
        r = concepteur.delete(f"{BASE_URL}/api/billing/card", timeout=10)
        assert r.status_code == 200
        assert r.json().get("ok") is True


# ========== IBAN ==========
class TestIban:
    def test_iban_invalid_rejected(self, concepteur):
        r = concepteur.post(
            f"{BASE_URL}/api/billing/iban",
            json={"iban": "INVALID123", "holder_name": "Marie Concepteur"},
            timeout=10,
        )
        assert r.status_code == 400

    def test_iban_valid_save(self, concepteur):
        r = concepteur.post(
            f"{BASE_URL}/api/billing/iban",
            json={"iban": VALID_IBAN, "holder_name": "Marie Concepteur"},
            timeout=10,
        )
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        assert data["has_iban"] is True
        assert data["bic"] == "PSSTFRPP"
        # schwifty bank_name is 'LA BANQUE POSTALE' - tolerate casing
        assert (data.get("bank_name") or "").upper().startswith("LA BANQUE POSTALE") or data.get("bank_name") == ""

    def test_iban_get_masked(self, concepteur):
        r = concepteur.get(f"{BASE_URL}/api/billing/iban", timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert data["has_iban"] is True
        masked = data["iban_masked"]
        assert masked.startswith("FR14"), masked
        assert masked.endswith("2606"), masked
        assert "XXXX" in masked
        assert data["holder_name"] == "Marie Concepteur"

    def test_iban_delete(self, concepteur):
        r = concepteur.delete(f"{BASE_URL}/api/billing/iban", timeout=10)
        assert r.status_code == 200
        # Re-set for downstream tests
        concepteur.post(
            f"{BASE_URL}/api/billing/iban",
            json={"iban": VALID_IBAN, "holder_name": "Marie Concepteur"},
            timeout=10,
        )


# ========== Balance / Ledger ==========
class TestBalance:
    def test_balance_shape(self, concepteur):
        r = concepteur.get(f"{BASE_URL}/api/billing/balance", timeout=10)
        assert r.status_code == 200
        data = r.json()
        for k in ("order_share_total", "paid_ad_debits_total",
                  "pending_ad_debits_total", "payouts_total", "net_due_to_concepteur"):
            assert k in data, f"missing field {k}"

    def test_ledger_sorted_desc(self, concepteur):
        r = concepteur.get(f"{BASE_URL}/api/billing/ledger", timeout=10)
        assert r.status_code == 200
        entries = r.json()
        assert isinstance(entries, list)
        if len(entries) >= 2:
            dates = [e.get("created_at") for e in entries]
            assert dates == sorted(dates, reverse=True)


# ========== Admin ads activation ==========
class TestAdsActivation:
    @pytest.fixture(scope="class")
    def site_id(self, admin):
        # Find a site owned by the concepteur
        r = admin.get(f"{BASE_URL}/api/sites", timeout=10)
        assert r.status_code == 200
        sites = r.json()
        # pick first with operator_id set
        for s in sites:
            if s.get("operator_id"):
                return s["id"]
        pytest.skip("No site with operator_id available")

    def test_activate_blocked_without_mandate(self, admin, concepteur, site_id):
        # ensure concepteur has no mandate
        concepteur.delete(f"{BASE_URL}/api/billing/card", timeout=10)
        r = admin.post(f"{BASE_URL}/api/admin/sites/{site_id}/ads/activate", timeout=10)
        assert r.status_code == 400
        detail = r.json().get("detail", "")
        assert "CB" in detail or "Concepteur" in detail, f"expected French CB error, got: {detail}"

    def test_deactivate_ok(self, admin, site_id):
        r = admin.post(f"{BASE_URL}/api/admin/sites/{site_id}/ads/deactivate", timeout=10)
        assert r.status_code == 200
        assert r.json().get("ads_active") is False


# ========== Admin cockpit ==========
class TestAdminCockpit:
    def test_overview_admin(self, admin):
        r = admin.get(f"{BASE_URL}/api/admin/billing/overview", timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert "operators" in data and isinstance(data["operators"], list)
        if data["operators"]:
            row = data["operators"][0]
            for k in ("has_card", "has_iban", "net_due_to_concepteur", "email"):
                assert k in row

    def test_overview_forbidden_for_concepteur(self, concepteur):
        r = concepteur.get(f"{BASE_URL}/api/admin/billing/overview", timeout=10)
        assert r.status_code in (401, 403)

    def test_payouts_preview(self, admin):
        r = admin.get(f"{BASE_URL}/api/admin/billing/payouts-preview", timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert "rows" in data and "total_due_eur" in data

    def test_run_payouts(self, admin):
        r = admin.post(f"{BASE_URL}/api/admin/billing/run-payouts", timeout=10)
        assert r.status_code == 200
        assert "payouts_created" in r.json()

    def test_sepa_xml(self, admin):
        r = admin.get(f"{BASE_URL}/api/admin/billing/payouts/sepa-xml", timeout=10)
        # either 404 (no pending payouts) or 200 with xml
        assert r.status_code in (200, 404)
        if r.status_code == 200:
            assert "xml" in r.headers.get("content-type", "").lower()
            body = r.text
            assert "pain.001.001.03" in body
            assert "<CstmrCdtTrfInitn>" in body

    def test_run_weekly_debits_smoke(self, admin):
        # With no ads_active site or no mandate, this should return a clean result dict
        r = admin.post(f"{BASE_URL}/api/admin/billing/run-weekly-debits?since_days=7", timeout=30)
        assert r.status_code == 200
        data = r.json()
        for k in ("sites_considered", "debits_created", "errors"):
            assert k in data


# ========== Auth gate ==========
class TestAuthGate:
    def test_card_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/billing/card", timeout=10)
        assert r.status_code in (401, 403)

    def test_iban_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/billing/iban", timeout=10)
        assert r.status_code in (401, 403)
