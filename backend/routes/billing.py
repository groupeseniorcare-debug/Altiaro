"""
Billing module pour Altiaro.

Gère :
- Mandats CB (via Mollie "first payment" 0.01€ + sequenceType=first → mandate_id stocké)
- IBAN + BIC + holder_name pour payouts
- Activation des Ads par site (admin toggle)
- Ledger financier : ad_debit, order_share, payout
- Prélèvements hebdo automatiques (50% dépense pub 7j)
- Payouts bi-mensuels (1er + 15) : preview, mark as paid, export SEPA XML
"""
from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from deps import db, get_current_user, require_admin, FRONTEND_URL

logger = logging.getLogger("conceptfactory.billing")
router = APIRouter()


# ============ Mollie helpers ============ #
def _mollie_client():
    from mollie.api.client import Client
    mode = (os.environ.get("MOLLIE_MODE") or "test").lower()
    key = os.environ.get("MOLLIE_LIVE_KEY" if mode == "live" else "MOLLIE_TEST_KEY") or ""
    if not key:
        raise HTTPException(status_code=500, detail="Clé Mollie manquante.")
    c = Client()
    c.set_api_key(key)
    return c, mode


async def _get_or_create_mollie_customer(user: dict) -> str:
    """Returns the Mollie customer_id for this user, creating one if needed."""
    existing = await db.billing_profiles.find_one({"user_id": user["id"]}, {"_id": 0})
    if existing and existing.get("mollie_customer_id"):
        return existing["mollie_customer_id"]
    client, _ = _mollie_client()
    try:
        customer = client.customers.create({
            "name": user.get("name") or user.get("email"),
            "email": user.get("email"),
            "metadata": {"user_id": user["id"], "role": user.get("role")},
        })
    except Exception as e:
        logger.exception("Mollie customer creation failed")
        raise HTTPException(status_code=502, detail=f"Mollie : {str(e)[:200]}")
    now = datetime.now(timezone.utc).isoformat()
    await db.billing_profiles.update_one(
        {"user_id": user["id"]},
        {
            "$set": {
                "mollie_customer_id": customer.id,
                "updated_at": now,
            },
            "$setOnInsert": {
                "user_id": user["id"],
                "created_at": now,
            },
        },
        upsert=True,
    )
    return customer.id


# ============ Card Mandate ============ #
class CardSetupInput(BaseModel):
    # empty body — user is logged in, we know who they are
    pass


@router.post("/billing/card/setup")
async def billing_card_setup(request: Request, user: dict = Depends(get_current_user)):
    """Crée un first payment 0.01€ pour obtenir un mandat carte.
    L'utilisateur est redirigé vers Mollie pour saisir sa CB."""
    customer_id = await _get_or_create_mollie_customer(user)
    client, mode = _mollie_client()
    redirect_url = f"{FRONTEND_URL}/billing?setup=done"
    webhook_url = str(request.url_for("mollie_webhook"))

    try:
        payment = client.payments.create({
            "amount": {"currency": "EUR", "value": "0.01"},
            "description": f"Autorisation CB Altiaro — {user.get('email')}",
            "customerId": customer_id,
            "sequenceType": "first",
            "method": "creditcard",
            "redirectUrl": redirect_url,
            "webhookUrl": webhook_url,
            "metadata": {
                "purpose": "card_mandate_setup",
                "user_id": user["id"],
            },
        })
    except Exception as e:
        logger.exception("Mollie first payment failed")
        raise HTTPException(status_code=502, detail=f"Mollie : {str(e)[:200]}")

    # Track the pending setup on the billing profile
    await db.billing_profiles.update_one(
        {"user_id": user["id"]},
        {"$set": {
            "pending_setup_payment_id": payment.id,
            "mode": mode,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }},
    )
    return {
        "payment_id": payment.id,
        "checkout_url": payment.checkout_url,
        "mode": mode,
    }


@router.get("/billing/card")
async def billing_card_status(user: dict = Depends(get_current_user)):
    prof = await db.billing_profiles.find_one({"user_id": user["id"]}, {"_id": 0})
    if not prof:
        return {"has_card": False, "status": "none"}
    return {
        "has_card": bool(prof.get("mandate_id")),
        "status": prof.get("mandate_status") or ("pending" if prof.get("pending_setup_payment_id") else "none"),
        "card_last4": prof.get("card_last4"),
        "card_brand": prof.get("card_brand"),
        "mandate_id": prof.get("mandate_id"),
        "mode": prof.get("mode"),
        "setup_at": prof.get("mandate_created_at"),
    }


@router.delete("/billing/card")
async def billing_card_revoke(user: dict = Depends(get_current_user)):
    prof = await db.billing_profiles.find_one({"user_id": user["id"]}, {"_id": 0})
    if not prof or not prof.get("mandate_id"):
        return {"ok": True, "revoked": False}
    client, _ = _mollie_client()
    try:
        client.customer_mandates.with_parent_id(prof["mollie_customer_id"]).delete(prof["mandate_id"])
    except Exception as e:
        logger.warning(f"Mollie revoke mandate failed (ignored) : {e}")
    await db.billing_profiles.update_one(
        {"user_id": user["id"]},
        {"$unset": {
            "mandate_id": "",
            "mandate_status": "",
            "card_last4": "",
            "card_brand": "",
            "mandate_created_at": "",
            "pending_setup_payment_id": "",
        }},
    )
    return {"ok": True, "revoked": True}


# ============ IBAN ============ #
class IbanInput(BaseModel):
    iban: str = Field(..., min_length=10, max_length=40)
    bic: Optional[str] = None
    holder_name: str = Field(..., min_length=2, max_length=80)


def _validate_iban(iban: str) -> dict:
    """Returns {iban_normalized, bic, country, bank_name} or raises 400."""
    from schwifty import IBAN
    try:
        parsed = IBAN(iban, allow_invalid=False)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"IBAN invalide : {str(e)[:120]}")
    return {
        "iban": parsed.compact,
        "bic": parsed.bic.compact if parsed.bic else None,
        "country_code": parsed.country_code,
        "bank_name": getattr(parsed, "bank_name", None) or "",
    }


def _mask_iban(iban: str) -> str:
    """FR7630003000000000001234567 → FR76 XXXX XXXX XXXX XXXX 4567"""
    if not iban:
        return ""
    s = iban.replace(" ", "")
    if len(s) < 8:
        return s
    return f"{s[:4]} XXXX XXXX XXXX XXXX {s[-4:]}"


@router.post("/billing/iban")
async def billing_iban_set(data: IbanInput, user: dict = Depends(get_current_user)):
    parsed = _validate_iban(data.iban)
    bic = (data.bic or parsed.get("bic") or "").upper().strip()
    now = datetime.now(timezone.utc).isoformat()
    await db.billing_profiles.update_one(
        {"user_id": user["id"]},
        {
            "$set": {
                "iban": parsed["iban"],
                "iban_masked": _mask_iban(parsed["iban"]),
                "bic": bic,
                "iban_country": parsed["country_code"],
                "iban_bank_name": parsed.get("bank_name"),
                "iban_holder_name": data.holder_name.strip(),
                "iban_updated_at": now,
                "updated_at": now,
            },
            "$setOnInsert": {"user_id": user["id"], "created_at": now},
        },
        upsert=True,
    )
    return await billing_iban_get(user)


@router.get("/billing/iban")
async def billing_iban_get(user: dict = Depends(get_current_user)):
    prof = await db.billing_profiles.find_one({"user_id": user["id"]}, {"_id": 0})
    if not prof or not prof.get("iban"):
        return {"has_iban": False}
    return {
        "has_iban": True,
        "iban_masked": prof.get("iban_masked"),
        "bic": prof.get("bic"),
        "country": prof.get("iban_country"),
        "bank_name": prof.get("iban_bank_name"),
        "holder_name": prof.get("iban_holder_name"),
        "updated_at": prof.get("iban_updated_at"),
    }


@router.delete("/billing/iban")
async def billing_iban_delete(user: dict = Depends(get_current_user)):
    await db.billing_profiles.update_one(
        {"user_id": user["id"]},
        {"$unset": {
            "iban": "", "iban_masked": "", "bic": "", "iban_country": "",
            "iban_bank_name": "", "iban_holder_name": "", "iban_updated_at": "",
        }},
    )
    return {"ok": True}


# ============ Ads activation (admin) ============ #
@router.post("/admin/sites/{site_id}/ads/activate")
async def admin_ads_activate(site_id: str, admin: dict = Depends(require_admin)):
    site = await db.sites.find_one({"id": site_id}, {"_id": 0})
    if not site:
        raise HTTPException(status_code=404, detail="Site introuvable")
    operator_id = site.get("operator_id")
    if operator_id:
        prof = await db.billing_profiles.find_one({"user_id": operator_id}, {"_id": 0})
        if not prof or not prof.get("mandate_id"):
            raise HTTPException(
                status_code=400,
                detail="Le Concepteur n'a pas encore validé sa CB. Activation des Ads bloquée.",
            )
    now = datetime.now(timezone.utc).isoformat()
    await db.sites.update_one(
        {"id": site_id},
        {"$set": {
            "ads_active": True,
            "ads_activated_at": now,
            "updated_at": now,
        }},
    )
    return {"ok": True, "site_id": site_id, "ads_active": True, "ads_activated_at": now}


@router.post("/admin/sites/{site_id}/ads/deactivate")
async def admin_ads_deactivate(site_id: str, admin: dict = Depends(require_admin)):
    now = datetime.now(timezone.utc).isoformat()
    await db.sites.update_one(
        {"id": site_id},
        {"$set": {
            "ads_active": False,
            "ads_deactivated_at": now,
            "updated_at": now,
        }},
    )
    return {"ok": True, "site_id": site_id, "ads_active": False}


# ============ Ledger & balance ============ #
async def _log_ledger(entry: dict):
    entry.setdefault("id", str(uuid.uuid4()))
    entry.setdefault("created_at", datetime.now(timezone.utc).isoformat())
    await db.ledger.insert_one(entry)


async def _compute_balance(user_id: str) -> dict:
    """Somme ledger pour un Concepteur (vue financière).

    - owed_share = total des parts Concepteur sur commandes payées (50% marge brute HT)
    - payouts_scheduled = somme des payouts pending/paid déjà loggés
    - net_due = owed_share - payouts_scheduled  → ce qui reste à virer
    - paid_ad_debits / pending_ad_debits : affichés pour info (collectés séparément via CB)
    """
    entries = await db.ledger.find({"concepteur_id": user_id}, {"_id": 0}).to_list(5000)
    pending_debits = 0.0
    paid_debits = 0.0
    order_share = 0.0
    gross_margin_ht_total = 0.0
    revenue_ht_total = 0.0
    cost_ht_total = 0.0
    orders_count = 0
    payouts = 0.0
    for e in entries:
        amount = float(e.get("amount") or 0)
        t = e.get("type")
        status = e.get("status", "pending")
        if t == "ad_debit":
            if status == "paid":
                paid_debits += amount
            elif status in ("pending", "failed"):
                pending_debits += amount
        elif t == "order_share" and status == "paid":
            order_share += amount
            gross_margin_ht_total += float(e.get("gross_margin_ht") or 0)
            revenue_ht_total += float(e.get("revenue_ht") or 0)
            cost_ht_total += float(e.get("cost_ht") or 0)
            orders_count += 1
        elif t == "payout" and status in ("paid", "pending"):
            payouts += amount
    net_due = order_share - payouts   # ad_debits collectés séparément via CB → pas de netting
    return {
        "revenue_ht_total": round(revenue_ht_total, 2),
        "cost_ht_total": round(cost_ht_total, 2),
        "gross_margin_ht_total": round(gross_margin_ht_total, 2),
        "orders_count": orders_count,
        "order_share_total": round(order_share, 2),         # = 50% × marge brute HT
        "paid_ad_debits_total": round(paid_debits, 2),      # info seulement
        "pending_ad_debits_total": round(pending_debits, 2),
        "payouts_total": round(payouts, 2),
        "net_due_to_concepteur": round(net_due, 2),
    }


@router.get("/billing/balance")
async def billing_balance(user: dict = Depends(get_current_user)):
    bal = await _compute_balance(user["id"])
    return bal


@router.get("/billing/ledger")
async def billing_ledger(limit: int = 100, user: dict = Depends(get_current_user)):
    entries = (
        await db.ledger.find({"concepteur_id": user["id"]}, {"_id": 0})
        .sort("created_at", -1)
        .limit(min(limit, 500))
        .to_list(min(limit, 500))
    )
    return entries


# ============ Admin billing cockpit ============ #
@router.get("/admin/billing/overview")
async def admin_billing_overview(admin: dict = Depends(require_admin)):
    operators = await db.users.find({"role": "operator"}, {"password": 0, "password_hash": 0}).to_list(1000)
    for op in operators:
        op["id"] = str(op.pop("_id"))
    profiles = await db.billing_profiles.find({}, {"_id": 0}).to_list(1000)
    prof_by_user = {p["user_id"]: p for p in profiles}
    rows = []
    for op in operators:
        bal = await _compute_balance(op["id"])
        prof = prof_by_user.get(op["id"], {})
        rows.append({
            "user_id": op["id"],
            "email": op.get("email"),
            "name": op.get("name"),
            "has_card": bool(prof.get("mandate_id")),
            "card_brand": prof.get("card_brand"),
            "card_last4": prof.get("card_last4"),
            "has_iban": bool(prof.get("iban")),
            "iban_masked": prof.get("iban_masked"),
            "holder_name": prof.get("iban_holder_name"),
            **bal,
        })
    return {"count": len(rows), "operators": rows}


# ============ Weekly debits / Bi-monthly payouts ============ #
async def _run_weekly_debits_inner(since_days: int = 7) -> dict:
    """Pour chaque site ads_active, calcule dépense 7j = daily_budget × 7,
    prélève 50% via Mollie recurring payment sur le mandate du Concepteur.
    Stocke ledger + trace chaque paiement."""
    client, _ = _mollie_client()
    since_dt = datetime.now(timezone.utc) - timedelta(days=since_days)
    sites = await db.sites.find(
        {"ads_active": True, "ads_activated_at": {"$exists": True}},
        {"_id": 0},
    ).to_list(5000)

    results = {"sites_considered": 0, "debits_created": 0, "errors": [], "details": []}
    for site in sites:
        activated = site.get("ads_activated_at")
        if activated and activated > since_dt.isoformat():
            # ads activated within the window → prorata
            # compute days since activation in window
            start = datetime.fromisoformat(activated.replace("Z", "+00:00")) if isinstance(activated, str) else since_dt
            days = max(1, min(since_days, (datetime.now(timezone.utc) - start).days or 1))
        else:
            days = since_days
        daily_budget = float(site.get("daily_budget_eur") or 0)
        if daily_budget <= 0:
            continue
        results["sites_considered"] += 1
        gross_week = daily_budget * days
        concepteur_share = round(gross_week * 0.5, 2)
        if concepteur_share < 0.01:
            continue
        operator_id = site.get("operator_id")
        if not operator_id:
            continue

        prof = await db.billing_profiles.find_one({"user_id": operator_id}, {"_id": 0})
        if not prof or not prof.get("mandate_id") or not prof.get("mollie_customer_id"):
            results["errors"].append({"site_id": site["id"], "reason": "no_mandate"})
            continue

        # Create recurring payment on mandate
        try:
            payment = client.payments.create({
                "amount": {"currency": "EUR", "value": f"{concepteur_share:.2f}"},
                "description": f"Pub 7j — {site.get('name', 'site')} — 50% de {gross_week:.2f}€",
                "customerId": prof["mollie_customer_id"],
                "mandateId": prof["mandate_id"],
                "sequenceType": "recurring",
                "metadata": {
                    "purpose": "weekly_ad_debit",
                    "site_id": site["id"],
                    "concepteur_id": operator_id,
                    "period_days": days,
                    "gross_week": gross_week,
                },
            })
            await _log_ledger({
                "concepteur_id": operator_id,
                "site_id": site["id"],
                "site_name": site.get("name"),
                "type": "ad_debit",
                "status": "pending",
                "amount": concepteur_share,
                "currency": "EUR",
                "mollie_payment_id": payment.id,
                "period_days": days,
                "gross_week": gross_week,
                "description": f"Prélèvement pub 7j ({days}j réels)",
            })
            results["debits_created"] += 1
            results["details"].append({
                "site_id": site["id"],
                "site_name": site.get("name"),
                "concepteur_id": operator_id,
                "amount": concepteur_share,
                "payment_id": payment.id,
            })
        except Exception as e:
            logger.exception(f"Weekly debit failed for site {site['id']}")
            results["errors"].append({"site_id": site["id"], "reason": str(e)[:200]})

    return results


@router.post("/admin/billing/run-weekly-debits")
async def admin_run_weekly_debits(since_days: int = 7, admin: dict = Depends(require_admin)):
    """Déclenche manuellement le job hebdo. Normalement appelé par APScheduler."""
    return await _run_weekly_debits_inner(since_days)


@router.get("/admin/billing/payouts-preview")
async def admin_payouts_preview(admin: dict = Depends(require_admin)):
    """Liste des virements à effectuer pour chaque Concepteur.

    Formule : 50% × marge brute HT (CA HT − Prix d'achat HT), déduction faite
    des payouts déjà loggés (pending ou paid).
    """
    operators = await db.users.find({"role": "operator"}, {"password": 0, "password_hash": 0}).to_list(1000)
    for op in operators:
        op["id"] = str(op.pop("_id"))

    # Pré-charge tous les sites par operator pour la ventilation
    all_sites = await db.sites.find({}, {"_id": 0, "id": 1, "name": 1, "operator_id": 1}).to_list(5000)
    sites_by_op: dict[str, list[dict]] = {}
    for s in all_sites:
        sites_by_op.setdefault(s.get("operator_id") or "", []).append(s)

    rows = []
    total_due = 0.0
    for op in operators:
        bal = await _compute_balance(op["id"])
        net = bal["net_due_to_concepteur"]
        if net <= 0.009:
            continue   # rien à verser

        prof = await db.billing_profiles.find_one({"user_id": op["id"]}, {"_id": 0}) or {}

        # Ventilation par site : marge brute HT cumul + part Concepteur par site
        site_breakdown = []
        for s in sites_by_op.get(op["id"], []):
            agg = await db.ledger.aggregate([
                {"$match": {
                    "concepteur_id": op["id"],
                    "site_id": s["id"],
                    "type": "order_share",
                    "status": "paid",
                }},
                {"$group": {
                    "_id": None,
                    "share": {"$sum": "$amount"},
                    "revenue_ht": {"$sum": "$revenue_ht"},
                    "cost_ht": {"$sum": "$cost_ht"},
                    "gross_margin_ht": {"$sum": "$gross_margin_ht"},
                    "orders": {"$sum": 1},
                }},
            ]).to_list(1)
            if agg and agg[0]["share"]:
                a = agg[0]
                site_breakdown.append({
                    "site_id": s["id"],
                    "site_name": s.get("name"),
                    "orders": a.get("orders") or 0,
                    "revenue_ht": round(a.get("revenue_ht") or 0, 2),
                    "cost_ht": round(a.get("cost_ht") or 0, 2),
                    "gross_margin_ht": round(a.get("gross_margin_ht") or 0, 2),
                    "concepteur_share": round(a.get("share") or 0, 2),
                })
        site_breakdown.sort(key=lambda x: x["concepteur_share"], reverse=True)

        rows.append({
            "user_id": op["id"],
            "email": op.get("email"),
            "name": op.get("name"),
            "net_due_eur": net,
            "has_iban": bool(prof.get("iban")),
            "iban": prof.get("iban") or None,           # plein en clair pour copier-coller
            "iban_masked": prof.get("iban_masked"),
            "holder_name": prof.get("iban_holder_name"),
            "bic": prof.get("bic"),
            "iban_bank_name": prof.get("iban_bank_name"),
            "site_breakdown": site_breakdown,
            **bal,
        })
        total_due += net
    rows.sort(key=lambda r: r["net_due_eur"], reverse=True)

    # Prochain cycle (1er ou 15 du mois)
    now = datetime.now(timezone.utc)
    if now.day < 15:
        next_cycle = now.replace(day=15, hour=0, minute=0, second=0, microsecond=0)
    else:
        y, m = now.year, now.month + 1
        if m > 12:
            m = 1
            y += 1
        next_cycle = now.replace(year=y, month=m, day=1, hour=0, minute=0, second=0, microsecond=0)

    return {
        "count": len(rows),
        "total_due_eur": round(total_due, 2),
        "next_cycle_date": next_cycle.date().isoformat(),
        "now": now.isoformat(),
        "rows": rows,
    }


@router.get("/admin/billing/payouts-history")
async def admin_payouts_history(limit: int = 100, admin: dict = Depends(require_admin)):
    """Historique des payouts (pending + paid), triés du plus récent au plus ancien."""
    entries = await db.ledger.find(
        {"type": "payout"}, {"_id": 0}
    ).sort("created_at", -1).limit(min(limit, 500)).to_list(min(limit, 500))
    # Enrichir avec nom du Concepteur
    by_uid = {e["concepteur_id"] for e in entries if e.get("concepteur_id")}
    from bson import ObjectId
    users_lookup: dict[str, dict] = {}
    for uid in by_uid:
        try:
            u = await db.users.find_one({"_id": ObjectId(uid)}, {"name": 1, "email": 1})
            if u:
                users_lookup[uid] = {"name": u.get("name"), "email": u.get("email")}
        except Exception:
            pass
    for e in entries:
        u = users_lookup.get(e.get("concepteur_id"))
        if u:
            e["concepteur_name"] = u.get("name")
            e["concepteur_email"] = u.get("email")
    return {"count": len(entries), "items": entries}


@router.post("/admin/billing/run-payouts")
async def admin_run_payouts(admin: dict = Depends(require_admin)):
    """Marque les soldes nets positifs comme 'payout pending' dans le ledger.
    N'exécute PAS le virement (fait manuellement par l'admin via SEPA XML)."""
    preview = await admin_payouts_preview(admin)
    now = datetime.now(timezone.utc).isoformat()
    created = 0
    for r in preview["rows"]:
        prof = await db.billing_profiles.find_one({"user_id": r["user_id"]}, {"_id": 0}) or {}
        if not prof.get("iban"):
            continue
        await _log_ledger({
            "concepteur_id": r["user_id"],
            "type": "payout",
            "status": "pending",
            "amount": r["net_due_eur"],
            "currency": "EUR",
            "description": f"Payout manuel prévu vers {prof.get('iban_masked')}",
            "iban": prof["iban"],
            "bic": prof.get("bic"),
            "holder_name": prof.get("iban_holder_name"),
            "scheduled_at": now,
        })
        created += 1
    return {"ok": True, "payouts_created": created, "total_eur": preview["total_due_eur"]}


@router.post("/admin/billing/payouts/{payout_id}/mark-paid")
async def admin_mark_payout_paid(payout_id: str, admin: dict = Depends(require_admin)):
    now = datetime.now(timezone.utc).isoformat()
    res = await db.ledger.update_one(
        {"id": payout_id, "type": "payout", "status": "pending"},
        {"$set": {"status": "paid", "paid_at": now, "paid_by": admin.get("email")}},
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Payout introuvable ou déjà traité.")
    return {"ok": True}


@router.post("/admin/billing/payouts/{payout_id}/cancel")
async def admin_cancel_payout(payout_id: str, admin: dict = Depends(require_admin)):
    """Annule un payout pending (remet le solde chez le Concepteur)."""
    now = datetime.now(timezone.utc).isoformat()
    res = await db.ledger.update_one(
        {"id": payout_id, "type": "payout", "status": "pending"},
        {"$set": {"status": "cancelled", "cancelled_at": now, "cancelled_by": admin.get("email")}},
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Payout introuvable ou déjà traité.")
    return {"ok": True}


# ============ Admin notifications (payouts_ready toast) ============ #
@router.get("/admin/notifications")
async def admin_notifications(unread_only: bool = False, admin: dict = Depends(require_admin)):
    q = {"read": False} if unread_only else {}
    items = await db.admin_notifications.find(q, {"_id": 0}).sort("created_at", -1).limit(50).to_list(50)
    return {"count": len(items), "items": items}


@router.post("/admin/notifications/{notif_id}/read")
async def admin_notification_mark_read(notif_id: str, admin: dict = Depends(require_admin)):
    await db.admin_notifications.update_one({"id": notif_id}, {"$set": {"read": True}})
    return {"ok": True}


@router.get("/admin/billing/payouts/sepa-xml")
async def admin_payouts_sepa_xml(admin: dict = Depends(require_admin)):
    """Génère un fichier SEPA PAIN.001.001.03 avec tous les payouts 'pending'."""
    payouts = await db.ledger.find(
        {"type": "payout", "status": "pending"}, {"_id": 0}
    ).to_list(5000)
    if not payouts:
        raise HTTPException(status_code=404, detail="Aucun payout en attente.")

    # Minimal SEPA Credit Transfer XML (PAIN.001.001.03)
    total = sum(float(p.get("amount") or 0) for p in payouts)
    now = datetime.now(timezone.utc)
    msg_id = f"CF-{now.strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}"
    pmt_id = f"PMT-{now.strftime('%Y%m%d')}"
    execution_date = now.date().isoformat()

    tx_xml = []
    for i, p in enumerate(payouts, 1):
        amount = float(p.get("amount") or 0)
        iban = (p.get("iban") or "").replace(" ", "")
        holder = (p.get("holder_name") or "Bénéficiaire").replace("&", "&amp;")
        bic = p.get("bic") or ""
        end_to_end = f"CF-{p.get('id','')[:16]}"
        tx_xml.append(f"""
      <CdtTrfTxInf>
        <PmtId><EndToEndId>{end_to_end}</EndToEndId></PmtId>
        <Amt><InstdAmt Ccy="EUR">{amount:.2f}</InstdAmt></Amt>
        {"<CdtrAgt><FinInstnId><BIC>" + bic + "</BIC></FinInstnId></CdtrAgt>" if bic else ""}
        <Cdtr><Nm>{holder}</Nm></Cdtr>
        <CdtrAcct><Id><IBAN>{iban}</IBAN></Id></CdtrAcct>
        <RmtInf><Ustrd>Altiaro - Part Concepteur</Ustrd></RmtInf>
      </CdtTrfTxInf>""".strip())

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pain.001.001.03">
  <CstmrCdtTrfInitn>
    <GrpHdr>
      <MsgId>{msg_id}</MsgId>
      <CreDtTm>{now.isoformat()}</CreDtTm>
      <NbOfTxs>{len(payouts)}</NbOfTxs>
      <CtrlSum>{total:.2f}</CtrlSum>
      <InitgPty><Nm>Altiaro</Nm></InitgPty>
    </GrpHdr>
    <PmtInf>
      <PmtInfId>{pmt_id}</PmtInfId>
      <PmtMtd>TRF</PmtMtd>
      <NbOfTxs>{len(payouts)}</NbOfTxs>
      <CtrlSum>{total:.2f}</CtrlSum>
      <ReqdExctnDt>{execution_date}</ReqdExctnDt>
      <Dbtr><Nm>Altiaro</Nm></Dbtr>
      <DbtrAcct><Id><IBAN>FR0000000000000000000000000</IBAN></Id></DbtrAcct>
      <DbtrAgt><FinInstnId><BIC>BNPAFRPPXXX</BIC></FinInstnId></DbtrAgt>
      {''.join(tx_xml)}
    </PmtInf>
  </CstmrCdtTrfInitn>
</Document>"""

    fname = f"concept-factory-payouts-{now.strftime('%Y%m%d')}.xml"
    return StreamingResponse(
        iter([xml.encode("utf-8")]),
        media_type="application/xml",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


# ============ Order share ledger (triggered by Mollie webhook for paid orders) ============ #
async def log_order_share_on_paid(order: dict):
    """Called by Mollie webhook when order transitions to paid.

    La part Concepteur = 50% × marge brute HT (CA HT − Prix d'achat HT).
    Si la commande n'a pas les champs HT (ex: commande legacy), on les recalcule
    à la volée avec les produits actuels comme fallback.
    """
    operator_id = None
    site = await db.sites.find_one({"id": order.get("site_id")}, {"_id": 0})
    if site:
        operator_id = site.get("operator_id")
    if not operator_id:
        return

    # Récupération des montants HT (snapshot à la commande)
    revenue_ht = float(order.get("subtotal_ht") or 0)
    cost_ht = float(order.get("cost_ht") or 0)
    gross_margin_ht = float(order.get("gross_margin_ht") or 0)

    # Fallback : recalcule à partir de `items` + VAT du site si snapshot absent
    if gross_margin_ht == 0 and (revenue_ht == 0 or cost_ht == 0):
        from tax_utils import site_vat_rate, compute_order_ht
        vat_rate = site_vat_rate(site)
        recomputed = compute_order_ht(order.get("items") or [], vat_rate)
        revenue_ht = recomputed["subtotal_ht"]
        cost_ht = recomputed["cost_ht"]
        gross_margin_ht = recomputed["gross_margin_ht"]

    # Part Concepteur : 50% de la marge brute (jamais négative)
    share = round(max(0.0, gross_margin_ht) * 0.5, 2)

    await _log_ledger({
        "concepteur_id": operator_id,
        "site_id": order.get("site_id"),
        "site_name": site.get("name") if site else None,
        "order_id": order.get("id"),
        "order_number": order.get("order_number"),
        "type": "order_share",
        "status": "paid",
        "amount": share,
        "revenue_ht": round(revenue_ht, 2),
        "cost_ht": round(cost_ht, 2),
        "gross_margin_ht": round(gross_margin_ht, 2),
        "gross_order_total": float(order.get("total") or 0),
        "currency": order.get("currency") or "EUR",
        "description": f"50% marge brute HT commande {order.get('order_number')}",
    })
