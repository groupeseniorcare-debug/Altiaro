"""Concepteur cockpit — KPIs globaux + ledger unifié + édition profil société.

Ces endpoints agrègent ce qui existe déjà (orders, ledger, billing_profiles,
payouts, sites) pour fournir au Concepteur une vue claire sans qu'il ait à
recoller les morceaux entre 3 pages.

Toutes les routes sont scopées au user connecté (son `id` = `operator_id` sur
les sites). Un Admin qui tape ces endpoints voit SES propres KPIs, pas ceux
d'un autre user (pour ça il a `/admin/billing/overview`).
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from deps import db, get_current_user

logger = logging.getLogger("conceptfactory.concepteur_cockpit")
router = APIRouter()


# ============ DASHBOARD KPIs ============ #
def _sum(items: list, key: str) -> float:
    return round(sum(float(i.get(key) or 0) for i in items), 2)


@router.get("/concepteur/dashboard")
async def get_dashboard_kpis(user: dict = Depends(get_current_user)):
    """KPIs consolidés sur tous les sites du Concepteur."""
    user_id = user["id"]
    now = datetime.now(timezone.utc)
    iso_30d_ago = (now - timedelta(days=30)).isoformat()
    iso_7d_ago = (now - timedelta(days=7)).isoformat()

    # Sites owned by the user
    sites = await db.sites.find(
        {"operator_id": user_id}, {"_id": 0, "id": 1, "name": 1, "status": 1,
                                    "ads_active": 1, "domain": 1}
    ).to_list(500)
    site_ids = [s["id"] for s in sites]

    # Orders on those sites
    orders = await db.orders.find(
        {"site_id": {"$in": site_ids}}, {"_id": 0}
    ).to_list(10000) if site_ids else []

    paid_orders = [o for o in orders if o.get("status") in ("paid", "shipped", "delivered")]
    pending_orders = [o for o in orders if o.get("status") == "pending_payment"]
    refunded_orders = [o for o in orders if o.get("status") == "refunded"]
    paid_30d = [o for o in paid_orders if (o.get("paid_at") or o.get("created_at", "")) >= iso_30d_ago]
    paid_7d = [o for o in paid_orders if (o.get("paid_at") or o.get("created_at", "")) >= iso_7d_ago]

    revenue_total = _sum(paid_orders, "total")
    revenue_30d = _sum(paid_30d, "total")
    revenue_7d = _sum(paid_7d, "total")
    refunds_total = _sum(refunded_orders, "total")

    # Ledger for the user (balance, next payout, pending ad debits)
    ledger = await db.ledger.find({"concepteur_id": user_id}, {"_id": 0}).to_list(5000)
    order_share_paid = _sum([e for e in ledger if e.get("type") == "order_share" and e.get("status") == "paid"], "amount")
    payouts_done = _sum([e for e in ledger if e.get("type") == "payout" and e.get("status") == "paid"], "amount")
    payouts_pending = _sum([e for e in ledger if e.get("type") == "payout" and e.get("status") == "pending"], "amount")
    ad_debits_paid = _sum([e for e in ledger if e.get("type") == "ad_debit" and e.get("status") == "paid"], "amount")
    ad_debits_pending = _sum([e for e in ledger if e.get("type") == "ad_debit" and e.get("status") in ("pending", "failed")], "amount")

    net_due = round(order_share_paid - payouts_done - payouts_pending, 2)

    # Next events estimation
    # Next payout: every 15 days (bi-mensuel). If last payout > 15d ago → expected soon.
    last_payout = max(
        [e for e in ledger if e.get("type") == "payout"],
        key=lambda e: e.get("created_at", ""),
        default=None,
    )
    if last_payout:
        try:
            last_date = datetime.fromisoformat(last_payout["created_at"].replace("Z", "+00:00"))
            next_payout_at = (last_date + timedelta(days=15)).date().isoformat()
        except Exception:
            next_payout_at = (now + timedelta(days=15)).date().isoformat()
    else:
        next_payout_at = (now + timedelta(days=15)).date().isoformat()

    # Next debit: weekly, next Monday
    days_until_monday = (7 - now.weekday()) % 7 or 7
    next_debit_at = (now + timedelta(days=days_until_monday)).date().isoformat()
    # Estimate next debit amount: sum of ads_active sites × daily_budget × 7 × 50%
    active_sites = [s for s in sites if s.get("ads_active")]
    # fetch daily budgets
    active_sites_full = await db.sites.find(
        {"id": {"$in": [s["id"] for s in active_sites]}},
        {"_id": 0, "id": 1, "daily_budget_eur": 1, "selected_countries": 1}
    ).to_list(500) if active_sites else []
    next_debit_amount = round(sum(
        float(s.get("daily_budget_eur") or len(s.get("selected_countries") or []) * 30)
        for s in active_sites_full
    ) * 7 * 0.5, 2)

    # Check if user has banking set up
    profile = await db.billing_profiles.find_one({"user_id": user_id}, {"_id": 0})
    has_iban = bool(profile and profile.get("iban"))
    has_card = bool(profile and profile.get("mandate_id"))

    return {
        "sites": {
            "total": len(sites),
            "active": len([s for s in sites if s.get("ads_active")]),
            "paused": len([s for s in sites if not s.get("ads_active")]),
            "items": sites[:20],
        },
        "orders": {
            "total": len(orders),
            "paid": len(paid_orders),
            "pending": len(pending_orders),
            "refunded": len(refunded_orders),
            "paid_30d": len(paid_30d),
            "paid_7d": len(paid_7d),
        },
        "revenue": {
            "total_eur": revenue_total,
            "last_30d_eur": revenue_30d,
            "last_7d_eur": revenue_7d,
            "avg_order_eur": round(revenue_total / max(len(paid_orders), 1), 2),
        },
        "refunds": {
            "count": len(refunded_orders),
            "amount_eur": refunds_total,
            "rate_pct": round((len(refunded_orders) / max(len(paid_orders), 1)) * 100, 1),
        },
        "balance": {
            "order_share_paid_eur": round(order_share_paid, 2),
            "payouts_done_eur": round(payouts_done, 2),
            "payouts_pending_eur": round(payouts_pending, 2),
            "net_due_eur": net_due,
            "ad_debits_paid_eur": round(ad_debits_paid, 2),
            "ad_debits_pending_eur": round(ad_debits_pending, 2),
        },
        "next_events": {
            "payout": {
                "date": next_payout_at,
                "amount_eur": net_due if net_due > 0 else 0,
                "status": "scheduled" if has_iban else "blocked_no_iban",
            },
            "debit": {
                "date": next_debit_at,
                "amount_eur": next_debit_amount,
                "status": "scheduled" if has_card else "blocked_no_card",
            },
        },
        "setup": {
            "has_card": has_card,
            "has_iban": has_iban,
            "banking_ready": has_card and has_iban,
        },
    }


# ============ FINANCE LEDGER UNIFIÉ ============ #
@router.get("/concepteur/finance/ledger")
async def get_finance_ledger(
    site_id: Optional[str] = None,
    type_filter: Optional[str] = Query(None, alias="type"),  # "payout" | "ad_debit" | "order_share"
    since: Optional[str] = None,   # ISO date
    until: Optional[str] = None,
    limit: int = 500,
    user: dict = Depends(get_current_user),
):
    """Ledger unifié du Concepteur : versements (payouts) + prélèvements (ad_debits)
    + parts commandes (order_share), avec filtres site/type/période + totaux.
    """
    user_id = user["id"]
    q = {"concepteur_id": user_id}
    if site_id:
        q["site_id"] = site_id
    if type_filter:
        q["type"] = type_filter
    if since:
        q["created_at"] = {"$gte": since}
    if until:
        q.setdefault("created_at", {})["$lte"] = until

    entries = await db.ledger.find(q, {"_id": 0}).sort("created_at", -1).limit(min(limit, 2000)).to_list(min(limit, 2000))

    # Enrich with site name
    site_ids = list({e.get("site_id") for e in entries if e.get("site_id")})
    sites = await db.sites.find(
        {"id": {"$in": site_ids}}, {"_id": 0, "id": 1, "name": 1}
    ).to_list(500) if site_ids else []
    site_by_id = {s["id"]: s.get("name", "—") for s in sites}
    for e in entries:
        e["site_name"] = site_by_id.get(e.get("site_id"), "—")

    # Totaux
    totals = {
        "credits": {  # rentrées
            "order_share": _sum([e for e in entries if e.get("type") == "order_share"], "amount"),
            "count_order_share": len([e for e in entries if e.get("type") == "order_share"]),
        },
        "debits": {   # sorties
            "ad_debit_paid": _sum([e for e in entries if e.get("type") == "ad_debit" and e.get("status") == "paid"], "amount"),
            "ad_debit_pending": _sum([e for e in entries if e.get("type") == "ad_debit" and e.get("status") != "paid"], "amount"),
            "count_ad_debit": len([e for e in entries if e.get("type") == "ad_debit"]),
        },
        "payouts": {  # virements
            "paid": _sum([e for e in entries if e.get("type") == "payout" and e.get("status") == "paid"], "amount"),
            "pending": _sum([e for e in entries if e.get("type") == "payout" and e.get("status") == "pending"], "amount"),
            "count": len([e for e in entries if e.get("type") == "payout"]),
        },
    }
    return {
        "entries": entries,
        "totals": totals,
        "filters": {
            "site_id": site_id,
            "type": type_filter,
            "since": since,
            "until": until,
        },
        "count": len(entries),
    }


# ============ PROFIL SOCIÉTÉ ============ #
class CompanyProfileInput(BaseModel):
    company_name: Optional[str] = Field(None, max_length=200)
    company_legal_form: Optional[str] = Field(None, max_length=40)  # SARL, SAS, EI, etc.
    siret: Optional[str] = Field(None, max_length=20)
    vat_number: Optional[str] = Field(None, max_length=30)
    address_line1: Optional[str] = Field(None, max_length=200)
    address_line2: Optional[str] = Field(None, max_length=200)
    postal_code: Optional[str] = Field(None, max_length=20)
    city: Optional[str] = Field(None, max_length=100)
    country_code: Optional[str] = Field(None, max_length=2)
    phone: Optional[str] = Field(None, max_length=30)


@router.get("/billing/company")
async def get_company_profile(user: dict = Depends(get_current_user)):
    profile = await db.billing_profiles.find_one({"user_id": user["id"]}, {"_id": 0})
    if not profile:
        return {"has_profile": False}
    return {
        "has_profile": True,
        "company_name": profile.get("company_name", ""),
        "company_legal_form": profile.get("company_legal_form", ""),
        "siret": profile.get("siret", ""),
        "vat_number": profile.get("vat_number", ""),
        "address_line1": profile.get("address_line1", ""),
        "address_line2": profile.get("address_line2", ""),
        "postal_code": profile.get("postal_code", ""),
        "city": profile.get("city", ""),
        "country_code": profile.get("country_code", "FR"),
        "phone": profile.get("phone", ""),
        "updated_at": profile.get("company_updated_at"),
    }


@router.patch("/billing/company")
async def update_company_profile(
    data: CompanyProfileInput, user: dict = Depends(get_current_user)
):
    # Normalise SIRET (strip spaces)
    siret = (data.siret or "").replace(" ", "").strip()
    if siret and (not siret.isdigit() or len(siret) != 14):
        raise HTTPException(400, "SIRET invalide (14 chiffres attendus).")
    # Normalise VAT
    vat = (data.vat_number or "").replace(" ", "").upper().strip()
    now = datetime.now(timezone.utc).isoformat()
    payload = {
        "company_name": (data.company_name or "").strip(),
        "company_legal_form": (data.company_legal_form or "").strip(),
        "siret": siret,
        "vat_number": vat,
        "address_line1": (data.address_line1 or "").strip(),
        "address_line2": (data.address_line2 or "").strip(),
        "postal_code": (data.postal_code or "").strip(),
        "city": (data.city or "").strip(),
        "country_code": (data.country_code or "FR").upper().strip()[:2],
        "phone": (data.phone or "").strip(),
        "company_updated_at": now,
        "updated_at": now,
    }
    await db.billing_profiles.update_one(
        {"user_id": user["id"]},
        {"$set": payload, "$setOnInsert": {"user_id": user["id"], "created_at": now}},
        upsert=True,
    )
    return await get_company_profile(user)
