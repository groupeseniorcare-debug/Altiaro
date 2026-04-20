"""Financials + Dashboard KPIs."""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from deps import db, get_current_user, _check_site_access, _site_with_progress

router = APIRouter()


class FinancialInput(BaseModel):
    month: str
    revenue: float = 0
    ad_spend: float = 0
    cogs: float = 0
    other_costs: float = 0
    orders_count: int = 0
    notes: Optional[str] = ""


@router.get("/sites/{site_id}/financials")
async def list_financials(site_id: str, user: dict = Depends(get_current_user)):
    await _check_site_access(site_id, user)
    items = await db.financials.find({"site_id": site_id}, {"_id": 0}).sort("month", -1).to_list(60)
    return items


@router.post("/sites/{site_id}/financials")
async def upsert_financial(site_id: str, data: FinancialInput, user: dict = Depends(get_current_user)):
    await _check_site_access(site_id, user)
    margin = data.revenue - data.cogs - data.other_costs - data.ad_spend
    roas = round(data.revenue / data.ad_spend, 2) if data.ad_spend > 0 else 0
    doc = {
        "site_id": site_id,
        "month": data.month,
        "revenue": data.revenue,
        "ad_spend": data.ad_spend,
        "cogs": data.cogs,
        "other_costs": data.other_costs,
        "orders_count": data.orders_count,
        "margin": margin,
        "roas": roas,
        "notes": data.notes or "",
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "updated_by": user["id"],
    }
    await db.financials.update_one(
        {"site_id": site_id, "month": data.month},
        {"$set": doc, "$setOnInsert": {"created_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True,
    )
    return await db.financials.find_one({"site_id": site_id, "month": data.month}, {"_id": 0})


@router.get("/dashboard/kpis")
async def dashboard_kpis(user: dict = Depends(get_current_user)):
    site_query = {} if user["role"] == "admin" else {"operator_id": user["id"]}
    sites = await db.sites.find(site_query, {"_id": 0}).to_list(1000)
    site_ids = [s["id"] for s in sites]

    pipeline = [
        {"$match": {"site_id": {"$in": site_ids}}},
        {"$group": {
            "_id": None,
            "total_revenue": {"$sum": "$revenue"},
            "total_ad_spend": {"$sum": "$ad_spend"},
            "total_cogs": {"$sum": "$cogs"},
            "total_other_costs": {"$sum": "$other_costs"},
            "total_orders": {"$sum": "$orders_count"},
            "total_margin": {"$sum": "$margin"},
        }}
    ]
    agg = await db.financials.aggregate(pipeline).to_list(1)
    totals = agg[0] if agg else {
        "total_revenue": 0, "total_ad_spend": 0, "total_cogs": 0,
        "total_other_costs": 0, "total_orders": 0, "total_margin": 0,
    }
    totals.pop("_id", None)

    per_site = []
    for s in sites:
        fin = await db.financials.aggregate([
            {"$match": {"site_id": s["id"]}},
            {"$group": {
                "_id": None,
                "revenue": {"$sum": "$revenue"},
                "ad_spend": {"$sum": "$ad_spend"},
                "margin": {"$sum": "$margin"},
                "orders": {"$sum": "$orders_count"},
            }}
        ]).to_list(1)
        f = fin[0] if fin else {"revenue": 0, "ad_spend": 0, "margin": 0, "orders": 0}
        f.pop("_id", None)
        await _site_with_progress(s)
        per_site.append({**s, **f})

    trend = await db.financials.aggregate([
        {"$match": {"site_id": {"$in": site_ids}}},
        {"$group": {
            "_id": "$month",
            "revenue": {"$sum": "$revenue"},
            "ad_spend": {"$sum": "$ad_spend"},
            "margin": {"$sum": "$margin"},
        }},
        {"$sort": {"_id": 1}},
        {"$project": {"_id": 0, "month": "$_id", "revenue": 1, "ad_spend": 1, "margin": 1}},
    ]).to_list(24)

    total_steps = await db.steps.count_documents({"site_id": {"$in": site_ids}})
    validated_steps = await db.steps.count_documents({"site_id": {"$in": site_ids}, "status": "validated"})
    pending_steps = await db.steps.count_documents({"site_id": {"$in": site_ids}, "status": "awaiting_validation"})
    roas_global = round(totals["total_revenue"] / totals["total_ad_spend"], 2) if totals["total_ad_spend"] > 0 else 0

    return {
        "totals": {
            **totals,
            "sites_count": len(sites),
            "active_sites": sum(1 for s in sites if s.get("status") == "active"),
            "roas_global": roas_global,
            "total_steps": total_steps,
            "validated_steps": validated_steps,
            "pending_validations": pending_steps,
            "global_progress_pct": round((validated_steps / total_steps) * 100) if total_steps else 0,
        },
        "per_site": per_site,
        "monthly_trend": trend,
    }
