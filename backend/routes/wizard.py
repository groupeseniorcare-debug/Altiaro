"""Wizard 10 étapes (Sprint 16bis) — orchestre le setup guidé d'un site.

Chaque étape a un statut : pending | done. Le wizard est juste un état + navigation,
les actions concrètes (analyse deep, sourcing, design IA, publish) sont déléguées aux
routes existantes.

Collection: wizard_state (doc par site_id).
"""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from deps import db, get_current_user, _check_site_access

router = APIRouter()

DEFAULT_STEPS = [
    {"id": "product",       "title": "Produit & niche",       "icon": "🎯",
     "desc": "Définir le produit phare et lancer une analyse deep multi-pays."},
    {"id": "countries",     "title": "Pays cibles",           "icon": "🌍",
     "desc": "Sélectionner les marchés (FR/DE/BE/NL/CH/UK)."},
    {"id": "sourcing",      "title": "Sourcing produits",      "icon": "📦",
     "desc": "Importer des fiches depuis CJ Dropshipping et/ou AliExpress."},
    {"id": "pricing",       "title": "Pricing & marges",      "icon": "💶",
     "desc": "Fixer les prix HT et vérifier la marge brute (×2.5 minimum recommandé)."},
    {"id": "positioning",   "title": "Positionnement / voix", "icon": "🎭",
     "desc": "Ton rassurant senior-friendly ou premium, nom de marque, promesse."},
    {"id": "identity",      "title": "Identité visuelle + design IA", "icon": "🎨",
     "desc": "Générer logo (Nano Banana) + structure de site (Claude 4.5)."},
    {"id": "seo",           "title": "SEO multi-pays",        "icon": "🔍",
     "desc": "Mots-clés, title/description, hreflang, sitemap auto."},
    {"id": "content",       "title": "Contenu & pages",       "icon": "📝",
     "desc": "Vérifier hero / bénéfices / FAQ / about / témoignages."},
    {"id": "legal",         "title": "Pages légales",         "icon": "⚖️",
     "desc": "CGV, Mentions légales, Confidentialité (auto par pays)."},
    {"id": "publish",       "title": "Publication",           "icon": "🚀",
     "desc": "Passer le site en published et éventuellement brancher un domaine custom."},
]


async def _get_state(site_id: str) -> dict:
    doc = await db.wizard_state.find_one({"site_id": site_id}, {"_id": 0})
    if not doc:
        doc = {
            "site_id": site_id,
            "steps": {s["id"]: {"status": "pending", "data": {}} for s in DEFAULT_STEPS},
            "current": "product",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        await db.wizard_state.insert_one(dict(doc))
        doc.pop("_id", None)
    return doc


async def _auto_mark(site_id: str, state: dict) -> dict:
    """Auto-détection des étapes déjà complétées en scrutant la DB."""
    site = await db.sites.find_one({"id": site_id}, {"_id": 0})
    if not site:
        return state
    steps = state.get("steps") or {}
    # product : niche non vide
    if site.get("niche"):
        steps.setdefault("product", {"status": "pending", "data": {}})
        if steps["product"]["status"] == "pending":
            steps["product"]["status"] = "done"
    # countries : selected_countries renseigné
    if site.get("selected_countries"):
        steps.setdefault("countries", {"status": "pending", "data": {}})
        if steps["countries"]["status"] == "pending":
            steps["countries"]["status"] = "done"
    # sourcing : au moins 1 produit dans le site
    pcount = await db.products.count_documents({"site_id": site_id})
    if pcount > 0:
        steps.setdefault("sourcing", {"status": "pending", "data": {}})
        if steps["sourcing"]["status"] == "pending":
            steps["sourcing"]["status"] = "done"
        # pricing : marge > 0 sur au moins 1 produit
        has_margin = await db.products.find_one(
            {"site_id": site_id, "cost_price_ht": {"$gt": 0}}, {"_id": 0, "id": 1}
        )
        if has_margin:
            steps.setdefault("pricing", {"status": "pending", "data": {}})
            if steps["pricing"]["status"] == "pending":
                steps["pricing"]["status"] = "done"
    # identity + content : design présent
    design = (site.get("design") or {})
    if design.get("brand") or design.get("hero"):
        for k in ("identity", "positioning", "content"):
            steps.setdefault(k, {"status": "pending", "data": {}})
            if steps[k]["status"] == "pending":
                steps[k]["status"] = "done"
    # seo : design.seo renseigné
    if design.get("seo"):
        steps.setdefault("seo", {"status": "pending", "data": {}})
        if steps["seo"]["status"] == "pending":
            steps["seo"]["status"] = "done"
    # legal : design.legal présent
    if design.get("legal") or design.get("cgv"):
        steps.setdefault("legal", {"status": "pending", "data": {}})
        if steps["legal"]["status"] == "pending":
            steps["legal"]["status"] = "done"
    # publish : design.published
    if design.get("published"):
        steps.setdefault("publish", {"status": "pending", "data": {}})
        if steps["publish"]["status"] == "pending":
            steps["publish"]["status"] = "done"

    state["steps"] = steps
    return state


@router.get("/sites/{site_id}/wizard")
async def get_wizard(site_id: str, user: dict = Depends(get_current_user)):
    await _check_site_access(site_id, user)
    state = await _get_state(site_id)
    state = await _auto_mark(site_id, state)
    await db.wizard_state.update_one(
        {"site_id": site_id},
        {"$set": {"steps": state["steps"],
                  "updated_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True,
    )
    done = sum(1 for s in state["steps"].values() if s.get("status") == "done")
    return {
        "site_id": site_id,
        "definition": DEFAULT_STEPS,
        "steps": state["steps"],
        "current": state.get("current", "product"),
        "progress": {"done": done, "total": len(DEFAULT_STEPS),
                     "percent": round(done / len(DEFAULT_STEPS) * 100)},
    }


class MarkStepInput(BaseModel):
    status: Optional[str] = "done"  # done | pending
    data: Optional[dict] = None
    advance_to: Optional[str] = None


@router.post("/sites/{site_id}/wizard/step/{step_id}")
async def mark_step(site_id: str, step_id: str, data: MarkStepInput,
                    user: dict = Depends(get_current_user)):
    await _check_site_access(site_id, user)
    valid_ids = {s["id"] for s in DEFAULT_STEPS}
    if step_id not in valid_ids:
        raise HTTPException(400, f"Étape inconnue : {step_id}")
    state = await _get_state(site_id)
    step = state["steps"].get(step_id, {"status": "pending", "data": {}})
    step["status"] = data.status or "done"
    if data.data:
        step["data"] = {**(step.get("data") or {}), **data.data}
    state["steps"][step_id] = step
    if data.advance_to and data.advance_to in valid_ids:
        state["current"] = data.advance_to
    await db.wizard_state.update_one(
        {"site_id": site_id},
        {"$set": {"steps": state["steps"], "current": state.get("current"),
                  "updated_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True,
    )
    return {"ok": True, "step": step, "current": state.get("current")}
