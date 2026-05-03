"""AEO (Answer Engine Optimization) — génère 15-25 Q/R conversationnelles par
produit + mots-clés conversationnels pour maximiser les citations par ChatGPT,
Claude, Perplexity, Gemini.

Entrypoints :
- POST /api/products/{id}/aeo-enrich                   → enrich 1 produit
- POST /api/sites/{id}/products/aeo-enrich-bulk        → bulk en background
- GET  /api/sites/{id}/products/aeo-enrich-bulk/{job}  → polling
- GET  /api/sites/{id}/aeo-readiness                   → score AEO du site
"""
from __future__ import annotations
import asyncio
import logging
import os
import re
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from deps import db, get_current_user
from routes.product_narrative import _call_claude_json, _pick_text

router = APIRouter()
logger = logging.getLogger("conceptfactory.aeo")


def _aeo_system_prompt() -> str:
    return (
        "Tu es un expert AEO (Answer Engine Optimization) spécialisé dans les "
        "citations par ChatGPT, Claude, Perplexity, Gemini et Google SGE. "
        "Tu écris des Q/R conversationnelles, directes, qui matchent exactement "
        "la façon dont les gens tapent leurs questions dans les moteurs IA. "
        "Tu renvoies UNIQUEMENT du JSON valide."
    )


def _aeo_user_prompt(product: dict, site: dict) -> str:
    name = _pick_text(product.get("name") or "")
    desc = _pick_text(product.get("description") or product.get("short_description") or "")[:600]
    price = product.get("price") or 0
    category = product.get("category") or site.get("niche") or ""
    narrative = product.get("narrative") or {}
    existing_faq = narrative.get("faq") or []
    existing_q = [(f.get("question") or f.get("q") or "") for f in existing_faq]
    already = "\n".join(f"- {q}" for q in existing_q if q)[:500]

    return f"""PRODUIT : {name}
CATÉGORIE : {category}
PRIX : {price} €
DESCRIPTION : {desc}

QUESTIONS DÉJÀ EXISTANTES (à ne PAS redupliquer) :
{already or "(aucune)"}

TÂCHE : rédige **18 à 22 questions/réponses** supplémentaires qui couvrent TOUS les
patterns conversationnels des moteurs IA 2026. Chaque réponse doit :
- Faire 40-80 mots
- Commencer par LA RÉPONSE (pas « Bien sûr, … »)
- Inclure au moins 1 donnée chiffrée quand pertinent (prix, délais, normes, dimensions)
- Ne jamais citer de marque concurrente

COUVRE OBLIGATOIREMENT CES PATTERNS :
1. Comparaison : « Quelle différence entre [produit] et [alternative courante] ? »
2. Prix/Budget : « Combien coûte [produit] ? », « [Produit] pas cher, ça existe ? »
3. Meilleur pour : « Quel [produit] pour [personne/usage spécifique] ? »
4. Quand/Pourquoi : « À partir de quel âge utiliser ? », « Quand faut-il changer ? »
5. Comment : « Comment choisir ? », « Comment installer ? »
6. Remboursement : « Est-ce remboursé par la Sécu/mutuelle ? (LPPR) »
7. Livraison : « Combien de temps pour livrer ? »
8. Garantie : « Combien d'années de garantie ? »
9. Entretien : « Comment entretenir ? »
10. Sécurité/Normes : « Est-ce aux normes CE/LPPR ? »
11. Problème courant : « [Problème spécifique] : est-ce possible avec ce produit ? »
12. Alternative : « Quelles alternatives pour [situation] ? »
13. Public : « Convient aux personnes de petite/grande taille ? », « Convient à deux personnes ? »
14. Retour : « Puis-je retourner si ça ne convient pas ? »
15. Accompagnement : « Peut-on être aidé pour choisir ? »

AJOUTE AUSSI 10-15 mots-clés conversationnels longue-traîne utilisés dans les prompts IA
(ex : « meilleur fauteuil releveur pour petit gabarit 2026 »).

RETOURNE CE JSON EXACT :
{{
  "faq": [
    {{"question": "Question conversationnelle directe", "answer": "Réponse 40-80 mots"}},
    ...18 à 22 items...
  ],
  "conversational_keywords": [
    "longue-traîne 1",
    "longue-traîne 2",
    ...10 à 15 items...
  ]
}}"""


async def _aeo_enrich_one(product: dict, site: dict) -> tuple[Optional[dict], Optional[str]]:
    """Retourne (aeo_payload, error_code). error_code : no_key|budget_exceeded|invalid_json|upstream|timeout|None"""
    system = _aeo_system_prompt()
    user = _aeo_user_prompt(product, site)
    data, err = await _call_claude_json(system, user, timeout=90)
    if err:
        return None, err
    # Validate shape
    faq = data.get("faq") or []
    if not isinstance(faq, list) or len(faq) < 8:
        return None, "invalid_json"
    ck = data.get("conversational_keywords") or []
    if not isinstance(ck, list):
        ck = []
    # Keep only valid-shaped entries
    faq_clean = [
        {"question": str(f.get("question", "")).strip(), "answer": str(f.get("answer", "")).strip()}
        for f in faq
        if isinstance(f, dict) and f.get("question") and f.get("answer")
    ]
    ck_clean = [str(k).strip() for k in ck if k][:20]
    return {
        "faq": faq_clean,
        "conversational_keywords": ck_clean,
        "enriched_at": datetime.now(timezone.utc).isoformat(),
    }, None


@router.post("/products/{product_id}/aeo-enrich")
async def aeo_enrich_one(product_id: str, user=Depends(get_current_user)):
    """Génère 18-22 Q/R AEO + mots-clés conversationnels. Fusionne avec la FAQ existante."""
    product = await db.products.find_one({"id": product_id}, {"_id": 0})
    if not product:
        raise HTTPException(404, "Produit introuvable")
    site = await db.sites.find_one({"id": product["site_id"]}, {"_id": 0})
    if not site:
        raise HTTPException(404, "Site introuvable")

    payload, err = await _aeo_enrich_one(product, site)
    if err == "budget_exceeded":
        raise HTTPException(402, "Budget LLM épuisé — rechargez la clé Emergent.")
    if err:
        raise HTTPException(502, f"IA indisponible : {err}")

    # Merge with existing FAQ (dedup by question, case-insensitive)
    narrative = product.get("narrative") or {}
    existing = narrative.get("faq") or []
    existing_normalized = {(f.get("question") or f.get("q") or "").strip().lower() for f in existing}
    merged_faq = list(existing)
    for f in payload["faq"]:
        if f["question"].strip().lower() not in existing_normalized:
            merged_faq.append(f)

    await db.products.update_one(
        {"id": product_id},
        {"$set": {
            "narrative.faq": merged_faq,
            "narrative.conversational_keywords": payload["conversational_keywords"],
            "narrative.aeo_enriched_at": payload["enriched_at"],
        }},
    )

    return {
        "ok": True,
        "added_faq": len(merged_faq) - len(existing),
        "total_faq": len(merged_faq),
        "conversational_keywords": payload["conversational_keywords"],
    }


class BulkAeoInput(BaseModel):
    force: bool = False  # Reenrich even products already enriched
    max_products: int = 50


async def _run_bulk_aeo_job(site_id: str, job_id: str, force: bool, max_products: int):
    """Background worker — enrichit jusqu'à N produits en parallèle (3 à la fois)."""
    await db.aeo_jobs.update_one({"id": job_id}, {"$set": {"status": "running"}})
    try:
        query = {"site_id": site_id, "status": "active"}
        if not force:
            query["narrative.aeo_enriched_at"] = {"$exists": False}
        products = await db.products.find(query, {"_id": 0}).limit(max_products).to_list(max_products)
        site = await db.sites.find_one({"id": site_id}, {"_id": 0}) or {}

        total = len(products)
        await db.aeo_jobs.update_one({"id": job_id}, {"$set": {"total": total}})
        if total == 0:
            await db.aeo_jobs.update_one({"id": job_id}, {"$set": {
                "status": "done", "processed": 0, "enriched": 0,
                "finished_at": datetime.now(timezone.utc).isoformat(),
            }})
            return

        semaphore = asyncio.Semaphore(3)  # throttle concurrency
        processed = 0
        enriched = 0
        failed = 0
        budget_hit = False

        async def _worker(p):
            nonlocal processed, enriched, failed, budget_hit
            async with semaphore:
                if budget_hit:
                    return
                payload, err = await _aeo_enrich_one(p, site)
                if err == "budget_exceeded":
                    budget_hit = True
                    return
                if err or not payload:
                    failed += 1
                    processed += 1
                    return
                narrative = p.get("narrative") or {}
                existing = narrative.get("faq") or []
                existing_q = {(f.get("question") or f.get("q") or "").strip().lower() for f in existing}
                merged = list(existing) + [
                    f for f in payload["faq"]
                    if f["question"].strip().lower() not in existing_q
                ]
                await db.products.update_one(
                    {"id": p["id"]},
                    {"$set": {
                        "narrative.faq": merged,
                        "narrative.conversational_keywords": payload["conversational_keywords"],
                        "narrative.aeo_enriched_at": payload["enriched_at"],
                    }},
                )
                enriched += 1
                processed += 1
                await db.aeo_jobs.update_one(
                    {"id": job_id},
                    {"$set": {"processed": processed, "enriched": enriched, "failed": failed}},
                )

        await asyncio.gather(*(_worker(p) for p in products))

        final_status = "done" if not budget_hit else "failed"
        update = {
            "status": final_status,
            "processed": processed, "enriched": enriched, "failed": failed,
            "finished_at": datetime.now(timezone.utc).isoformat(),
        }
        if budget_hit:
            update["error"] = "Budget LLM épuisé — rechargez la clé Emergent."
        await db.aeo_jobs.update_one({"id": job_id}, {"$set": update})
    except Exception as e:
        logger.exception("bulk AEO job crashed")
        await db.aeo_jobs.update_one({"id": job_id}, {"$set": {
            "status": "failed", "error": str(e)[:300],
            "finished_at": datetime.now(timezone.utc).isoformat(),
        }})


@router.post("/sites/{site_id}/products/aeo-enrich-bulk")
async def aeo_enrich_bulk(site_id: str, body: BulkAeoInput, user=Depends(get_current_user)):
    site = await db.sites.find_one({"id": site_id}, {"_id": 0})
    if not site:
        raise HTTPException(404, "Site introuvable")

    # Count eligible products upfront for UI
    q = {"site_id": site_id, "status": "active"}
    if not body.force:
        q["narrative.aeo_enriched_at"] = {"$exists": False}
    eligible = await db.products.count_documents(q)
    if eligible == 0:
        return {
            "status": "noop",
            "message": "Tous les produits sont déjà enrichis AEO. Utilise `force: true` pour relancer.",
            "eligible": 0,
        }

    job_id = str(uuid.uuid4())
    await db.aeo_jobs.insert_one({
        "id": job_id,
        "site_id": site_id,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "total": min(eligible, body.max_products),
        "processed": 0, "enriched": 0, "failed": 0,
        "force": body.force,
    })
    asyncio.create_task(_run_bulk_aeo_job(site_id, job_id, body.force, body.max_products))
    return {
        "status": "started",
        "job_id": job_id,
        "eligible": eligible,
        "will_process": min(eligible, body.max_products),
        "message": f"{min(eligible, body.max_products)} produit(s) à enrichir — ~{min(eligible, body.max_products) * 25}s estimées.",
    }


@router.get("/sites/{site_id}/products/aeo-enrich-bulk/{job_id}")
async def aeo_bulk_status(site_id: str, job_id: str, user=Depends(get_current_user)):
    job = await db.aeo_jobs.find_one({"id": job_id, "site_id": site_id}, {"_id": 0})
    if not job:
        raise HTTPException(404, "Job introuvable")
    return job


# =====================================================================
# AEO Readiness — score global calculé sur les signaux AEO du site
# =====================================================================
@router.get("/sites/{site_id}/aeo-readiness")
async def aeo_readiness(site_id: str, user=Depends(get_current_user)):
    """Score 0-100 + checklist détaillée des signaux AEO du site.
    Calcul local, zéro coût LLM."""
    site = await db.sites.find_one({"id": site_id}, {"_id": 0})
    if not site:
        raise HTTPException(404, "Site introuvable")

    design = site.get("design") or {}
    products = await db.products.find(
        {"site_id": site_id, "status": "active"},
        {"_id": 0, "narrative": 1},
    ).to_list(500)

    total_products = len(products)
    # 1. % products with ≥10 Q/R (AEO-ready)
    ready = sum(
        1 for p in products
        if len((p.get("narrative") or {}).get("faq") or []) >= 10
    )
    ready_pct = round((ready / total_products * 100)) if total_products else 0

    # 2. Average Q/A per product
    avg_qa = round(
        sum(len((p.get("narrative") or {}).get("faq") or []) for p in products) / total_products
    ) if total_products else 0

    # 3. Conversational keywords total
    total_ck = sum(
        len((p.get("narrative") or {}).get("conversational_keywords") or [])
        for p in products
    )

    # 4. llms-full.txt & llms.txt always available (computed on the fly)
    has_llms = True
    # 5. Organization schema with contactPoint present
    has_contact = bool((design.get("contact") or {}).get("support_phone"))
    # 6. Blog posts count (longer content = more AEO real estate)
    blog_count = len(design.get("blog_posts") or [])
    # 7. Sitemap XML images enabled — always ON after our upgrade
    has_img_sitemap = True

    # --- Score composition (weighted) ---
    score = 0
    score += round(ready_pct * 0.35)     # 35 % : produits AEO-ready
    score += min(20, avg_qa)             # 20 pts max : richesse FAQ moy (≥20 Q/A = plein)
    score += min(15, total_ck // 4)      # 15 pts max : keywords conversationnels (60+ = plein)
    score += 10 if has_llms else 0       # 10 pts : llms-full.txt présent
    score += 10 if has_contact else 0    # 10 pts : Organization contactPoint
    score += min(10, blog_count)         # 10 pts max : 10 articles blog = plein
    score = min(100, score)

    checklist = [
        {"key": "products_ready", "ok": ready_pct >= 70, "label": f"Produits AEO-ready (≥10 Q/R) : {ready}/{total_products} ({ready_pct}%)"},
        {"key": "avg_qa", "ok": avg_qa >= 15, "label": f"Moyenne de Q/R par produit : {avg_qa}"},
        {"key": "conversational_kw", "ok": total_ck >= 40, "label": f"Mots-clés conversationnels totaux : {total_ck}"},
        {"key": "llms_full", "ok": has_llms, "label": "llms-full.txt activé (standard AEO)"},
        {"key": "contact_schema", "ok": has_contact, "label": "Organization schema : téléphone support"},
        {"key": "blog_posts", "ok": blog_count >= 5, "label": f"Articles de blog publiés : {blog_count}"},
        {"key": "image_sitemap", "ok": has_img_sitemap, "label": "Sitemap images activé (Google Image + Gemini)"},
    ]

    return {
        "score": score,
        "products_ready": ready,
        "products_total": total_products,
        "ready_pct": ready_pct,
        "avg_qa_per_product": avg_qa,
        "conversational_keywords_total": total_ck,
        "blog_posts": blog_count,
        "checklist": checklist,
    }



# =====================================================================
# AEO SNIPPETS (Sprint 1) — 40-60 mots, optimisés pour réponses directes
# Google SGE / ChatGPT / Claude / Perplexity / Gemini
# =====================================================================
class BulkSnippetInput(BaseModel):
    force: bool = False
    max_products: int = 50


async def _generate_aeo_snippet(product: dict, site: dict) -> Optional[str]:
    """Génère un snippet 40-60 mots répondant directement à 'Pourquoi choisir X ?'."""
    name = _pick_text(product.get("name") or "")
    narrative = product.get("narrative") or {}
    subhead = _pick_text(narrative.get("subheadline") or "")
    usps = narrative.get("usps") or narrative.get("benefits") or []
    usps_txt = ", ".join(_pick_text(u) for u in usps[:5] if u)
    category = _pick_text(product.get("category") or site.get("niche") or "")
    brand = _pick_text((site.get("design") or {}).get("brand", {}).get("name") or site.get("name") or "")

    system = (
        "Tu es un rédacteur SEO/AEO expert. Tu écris des réponses courtes, "
        "directes et factuelles, optimisées pour Google SGE et les moteurs IA. "
        "Réponds UNIQUEMENT en JSON strict."
    )
    user = (
        f"Produit : {name}\n"
        f"Marque : {brand}\n"
        f"Catégorie : {category}\n"
        f"Accroche : {subhead}\n"
        f"USPs : {usps_txt}\n\n"
        "Rédige un snippet AEO de 40-60 mots MAXIMUM répondant directement "
        "à la question : « Pourquoi choisir ce produit ? ».\n"
        "Ton premium, factuel, USPs concrètes, aucun superlatif creux.\n"
        "Format JSON : {\"snippet\": \"...\"}"
    )
    data, err = await _call_claude_json(system, user, timeout=40)
    if err or not isinstance(data, dict):
        return None
    s = (data.get("snippet") or "").strip()
    # Trim to roughly 60 words if Claude over-shoots.
    words = s.split()
    if len(words) > 65:
        s = " ".join(words[:60])
    return s or None


async def _run_bulk_snippets_job(site_id: str, job_id: str, force: bool, max_products: int):
    await db.aeo_jobs.update_one({"id": job_id}, {"$set": {"status": "running"}})
    try:
        query = {"site_id": site_id, "status": "active"}
        if not force:
            query["aeo_snippet"] = {"$exists": False}
        products = await db.products.find(query, {"_id": 0}).limit(max_products).to_list(max_products)
        site = await db.sites.find_one({"id": site_id}, {"_id": 0}) or {}
        sem = asyncio.Semaphore(4)
        done = 0
        budget_hit = False

        async def _one(p):
            nonlocal done, budget_hit
            if budget_hit:
                return
            async with sem:
                try:
                    snippet = await _generate_aeo_snippet(p, site)
                except Exception as e:
                    msg = str(e)
                    if "402" in msg or "budget" in msg.lower():
                        budget_hit = True
                    return
                if snippet:
                    await db.products.update_one(
                        {"id": p["id"]},
                        {"$set": {
                            "aeo_snippet": snippet,
                            "aeo_snippet_at": datetime.now(timezone.utc).isoformat(),
                        }},
                    )
                    done += 1
                    await db.aeo_jobs.update_one({"id": job_id}, {"$inc": {"progress": 1}})

        await asyncio.gather(*[_one(p) for p in products])
        await db.aeo_jobs.update_one(
            {"id": job_id},
            {"$set": {
                "status": "completed",
                "done": done,
                "total": len(products),
                "budget_hit": budget_hit,
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }},
        )
    except Exception as e:
        logger.exception("[aeo-snippets] bulk job crashed")
        await db.aeo_jobs.update_one(
            {"id": job_id},
            {"$set": {"status": "failed", "error": str(e)[:300]}},
        )


@router.post("/sites/{site_id}/products/aeo-snippet-bulk")
async def aeo_snippet_bulk(site_id: str, body: BulkSnippetInput,
                           user=Depends(get_current_user)):
    """Sprint 1 — Génère le snippet 40-60 mots pour tous les produits du site."""
    site = await db.sites.find_one({"id": site_id}, {"_id": 0, "id": 1, "operator_id": 1})
    if not site:
        raise HTTPException(404, "Site introuvable")
    if user.get("role") != "admin" and site.get("operator_id") != user.get("id"):
        raise HTTPException(403, "Accès interdit")

    job_id = str(uuid.uuid4())
    await db.aeo_jobs.insert_one({
        "id": job_id, "site_id": site_id, "type": "aeo_snippet",
        "status": "queued", "progress": 0,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    asyncio.create_task(_run_bulk_snippets_job(site_id, job_id, body.force, body.max_products))
    return {"ok": True, "job_id": job_id}


@router.get("/sites/{site_id}/products/aeo-snippet-bulk/{job_id}")
async def aeo_snippet_bulk_status(site_id: str, job_id: str,
                                  user=Depends(get_current_user)):
    doc = await db.aeo_jobs.find_one({"id": job_id, "site_id": site_id}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Job introuvable")
    return doc
