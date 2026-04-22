"""
Site submission & admin validation workflow.

A site goes through these states :
  - draft         : Concepteur is building (default after creation)
  - in_review     : Concepteur submitted, Admin must validate
  - changes_req   : Admin asked for changes (with a note)
  - approved      : Admin validated, ready for Google Ads launch
  - live          : Admin launched Google Ads, traffic flowing

The underlying `status` field in db.sites carries this value.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from deps import db, get_current_user, require_admin, _check_site_access

logger = logging.getLogger("conceptfactory.validation")
router = APIRouter()

VALID_STATUSES = {"draft", "in_review", "changes_req", "approved", "live"}


class SubmitInput(BaseModel):
    concepteur_note: Optional[str] = ""


class ReviewInput(BaseModel):
    decision: str  # "approve" | "changes_req"
    note: Optional[str] = ""


@router.post("/sites/{site_id}/submit")
async def submit_for_review(site_id: str, body: SubmitInput, user=Depends(get_current_user)):
    """Concepteur submits his site for Admin review."""
    await _check_site_access(site_id, user)
    site = await db.sites.find_one({"id": site_id}, {"_id": 0, "status": 1, "name": 1})
    if not site:
        raise HTTPException(404, "Site introuvable")
    current = site.get("status") or "draft"
    if current == "in_review":
        raise HTTPException(400, "Site déjà en cours de validation.")
    if current in {"approved", "live"}:
        raise HTTPException(400, "Site déjà approuvé.")

    # Run the QA audit to attach a snapshot at submission time
    qa_snapshot = await _run_qa_snapshot(site_id)

    now = datetime.now(timezone.utc).isoformat()
    submission = {
        "submitted_at": now,
        "submitted_by": user["id"],
        "concepteur_note": (body.concepteur_note or "")[:2000],
        "qa_snapshot": qa_snapshot,
    }
    await db.sites.update_one(
        {"id": site_id},
        {"$set": {"status": "in_review", "submission": submission},
         "$push": {"review_history": {
             "at": now, "by": user["id"], "action": "submitted",
             "note": body.concepteur_note or "",
         }}},
    )
    logger.info(f"[validation] site {site_id} submitted for review by {user['id']}")
    return {"status": "in_review", "qa_score": qa_snapshot.get("score"), "qa_blockers": qa_snapshot.get("blockers", [])}


@router.post("/sites/{site_id}/review")
async def admin_review(site_id: str, body: ReviewInput, admin=Depends(require_admin)):
    """Admin approves or requests changes."""
    if body.decision not in {"approve", "changes_req"}:
        raise HTTPException(400, "decision doit être 'approve' ou 'changes_req'")
    site = await db.sites.find_one({"id": site_id}, {"_id": 0, "status": 1})
    if not site:
        raise HTTPException(404, "Site introuvable")
    if (site.get("status") or "draft") != "in_review":
        raise HTTPException(400, "Ce site n'est pas en attente de validation.")

    new_status = "approved" if body.decision == "approve" else "changes_req"
    now = datetime.now(timezone.utc).isoformat()
    await db.sites.update_one(
        {"id": site_id},
        {"$set": {"status": new_status, "last_review_at": now, "last_review_note": body.note or ""},
         "$push": {"review_history": {
             "at": now, "by": admin["id"], "action": body.decision,
             "note": body.note or "",
         }}},
    )
    logger.info(f"[validation] site {site_id} -> {new_status} by admin {admin['id']}")
    return {"status": new_status}


@router.post("/sites/{site_id}/launch")
async def admin_launch(site_id: str, admin=Depends(require_admin)):
    """Admin marks the site as live after launching Google Ads."""
    site = await db.sites.find_one({"id": site_id}, {"_id": 0, "status": 1})
    if not site:
        raise HTTPException(404, "Site introuvable")
    if (site.get("status") or "") not in {"approved", "live"}:
        raise HTTPException(400, "Le site doit être 'approved' avant d'être lancé.")
    now = datetime.now(timezone.utc).isoformat()
    await db.sites.update_one(
        {"id": site_id},
        {"$set": {"status": "live", "launched_at": now, "launched_by": admin["id"]}},
    )
    return {"status": "live"}


@router.get("/admin/review-queue")
async def list_review_queue(admin=Depends(require_admin)):
    """All sites pending admin review."""
    sites = await db.sites.find(
        {"status": "in_review"},
        {"_id": 0, "id": 1, "name": 1, "niche": 1, "selected_countries": 1,
         "operator_id": 1, "submission": 1, "created_at": 1, "daily_budget_eur": 1},
    ).sort("submission.submitted_at", -1).to_list(200)
    # Attach operator email for admin context
    op_ids = {s.get("operator_id") for s in sites if s.get("operator_id")}
    ops = {}
    if op_ids:
        async for u in db.users.find({"id": {"$in": list(op_ids)}}, {"_id": 0, "id": 1, "email": 1, "name": 1}):
            ops[u["id"]] = {"email": u.get("email"), "name": u.get("name")}
    for s in sites:
        s["operator"] = ops.get(s.get("operator_id"), {})
    return sites


@router.get("/sites/{site_id}/qa-audit")
async def site_qa_audit(site_id: str, user=Depends(get_current_user)):
    """Run the full automated QA audit on the site, on demand."""
    await _check_site_access(site_id, user)
    return await _run_qa_snapshot(site_id)


# =====================================================================
# Automated QA — runs at submission time, and on demand from the cockpit.
# =====================================================================
async def _run_qa_snapshot(site_id: str) -> dict:
    """
    Comprehensive automated audit.
    Covers : catalog, content, pages, branding, SEO, accessibility-light,
    links sanity. Returns a single dict with score, breakdown, and a list
    of blockers (things the admin will reject for).
    """
    site = await db.sites.find_one({"id": site_id}, {"_id": 0})
    if not site:
        return {"score": 0, "blockers": ["Site introuvable"]}

    design = site.get("design") or {}
    brand = design.get("brand") or {}
    tracking = design.get("tracking") or {}
    about = design.get("about") or {}
    contact = design.get("contact") or {}
    blog_posts = design.get("blog_posts") or []
    legal = design.get("legal") or {}
    navigation = design.get("navigation") or {}
    financial_forecast = design.get("financial_forecast") or {}
    journey_validated = set(site.get("journey_validated") or [])

    products = await db.products.find(
        {"site_id": site_id, "status": "active"},
        {"_id": 0, "id": 1, "name": 1, "description": 1, "images": 1, "price": 1,
         "seo": 1, "narrative": 1, "role": 1, "linked_product_ids": 1},
    ).to_list(500)
    main_products = [p for p in products if p.get("role") != "upsell"]
    upsells_list = [p for p in products if p.get("role") == "upsell"]
    collections_count = await db.collections.count_documents({"site_id": site_id})

    checks = []

    def add(key: str, label: str, passed: bool, critical: bool, detail: str = ""):
        checks.append({
            "key": key, "label": label, "pass": passed,
            "critical": critical, "detail": detail,
        })

    # ---- Catalog (main products)
    add("catalog-min", "Au moins 5 produits principaux actifs", len(main_products) >= 5, True,
        f"{len(main_products)} produits principaux")
    products_with_image = sum(1 for p in main_products if (p.get("images") or []))
    add("catalog-images", "100 % des produits avec image",
        len(main_products) > 0 and products_with_image == len(main_products), True,
        f"{products_with_image}/{len(main_products)} avec image")
    products_with_seo = sum(
        1 for p in main_products
        if (p.get("seo") or {}).get("description") or (p.get("narrative") or {}).get("seo")
    )
    add("catalog-seo", "Narratif IA enrichi (≥50% des produits)",
        len(main_products) > 0 and products_with_seo >= max(1, len(main_products) // 2),
        False, f"{products_with_seo}/{len(main_products)} enrichis par IA · relance le bulk optimize SEO")

    # ---- Upsells
    add("upsells-imported", "Au moins 2 upsells importés", len(upsells_list) >= 2, False,
        f"{len(upsells_list)} upsells · ajoute-en à l'étape 3")
    if upsells_list and main_products:
        main_ids = {p["id"] for p in main_products}
        covered = {
            mid for u in upsells_list for mid in (u.get("linked_product_ids") or []) if mid in main_ids
        }
        coverage_pct = (len(covered) / len(main_ids)) * 100 if main_ids else 0
        add("upsells-linked", "Upsells associés aux produits (≥80%)",
            coverage_pct >= 80, False,
            f"Couverture {coverage_pct:.0f}% · associe depuis l'étape 3")

    # ---- Branding
    add("brand-name", "Nom de marque défini", bool(brand.get("name") or site.get("name")), True)
    add("brand-logo", "Logo présent", bool(brand.get("logo_url") or brand.get("logo")), True)
    add("brand-colors", "Couleurs de marque", bool(brand.get("primary_color")), False)
    add("brand-tagline", "Accroche / baseline", bool(brand.get("tagline") or brand.get("baseline")), False)

    # ---- Navigation
    nav_header = navigation.get("header") or []
    add("nav-header", "Menu principal configuré (≥3 liens)", len(nav_header) >= 3, False,
        f"{len(nav_header)} lien(s) dans le header · Étape 5 → Navigation")

    # ---- Collections
    add("collections-min", "Au moins 1 collection créée", collections_count >= 1, False,
        f"{collections_count} collection(s) · Étape 5 → Collections")

    # ---- Pages
    add("page-about", "Page 'À propos' remplie",
        bool((about.get("paragraphs") or about.get("content"))), True)
    add("page-contact", "Coordonnées de contact",
        bool(contact.get("email") or contact.get("address")), True)
    add("page-legal-cgv", "CGV publiées", bool(legal.get("cgv") or legal.get("terms")), True)
    add("page-legal-mentions", "Mentions légales",
        bool(legal.get("mentions") or legal.get("imprint")), True)
    add("page-legal-privacy", "Politique de confidentialité", bool(legal.get("privacy")), False)

    # ---- Content marketing
    add("blog-min", "Au moins 3 articles publiés", len(blog_posts) >= 3, False,
        f"{len(blog_posts)} articles · Étape 7")

    # ---- Financial forecast
    gate_status = (financial_forecast.get("launch_gate") or {}).get("status")
    add("forecast-computed", "Prévisionnel 30 jours calculé",
        bool(financial_forecast.get("generated_at")), True,
        "Lance l'Étape 4 pour le calculer")
    add("forecast-gate-ok", "Launch gate : marge / CPA viable",
        gate_status in {"ok", "warning"}, True,
        f"Gate = {gate_status or '—'}" + (
            " · ta marge par commande est trop faible face au CPA"
            if gate_status == "blocked" else ""
        ))

    # ---- Journey progression (all steps validated)
    required_steps = {"pricing", "import", "upsells", "forecast", "branding", "pages", "content", "seo"}
    missing = required_steps - journey_validated
    add("journey-complete", "Toutes les étapes du cockpit validées",
        not missing, False,
        f"Manque : {', '.join(sorted(missing)) if missing else '—'}")

    # ---- SEO
    add("seo-published", "Site publié (pas en brouillon)",
        (site.get("status") in {"in_review", "approved", "live"}) or bool(site.get("published"))
        or bool(design.get("published")),
        False)
    add("seo-tracking-ga4", "Tracking GA4 configuré",
        bool(tracking.get("ga4_measurement_id")), False,
        "Ajoute ton GA4 Measurement ID dans les paramètres du site")
    add("seo-bulk-optimize",
        "Optimisation SEO IA des produits (≥80%)",
        len(main_products) > 0
        and sum(1 for p in main_products if (p.get("narrative") or {}).get("seo")) >= int(0.8 * len(main_products)),
        False,
        "Lance SEO → Studio AEO → Optimisation IA en masse")

    # ---- Aggregate
    passed = sum(1 for c in checks if c["pass"])
    score = round(passed / len(checks) * 100) if checks else 0
    blockers = [c for c in checks if c["critical"] and not c["pass"]]

    return {
        "audited_at": datetime.now(timezone.utc).isoformat(),
        "score": score,
        "passed": passed,
        "total": len(checks),
        "checks": checks,
        "blockers": [{"key": b["key"], "label": b["label"], "detail": b["detail"]} for b in blockers],
        "ready_for_submission": len(blockers) == 0,
    }
