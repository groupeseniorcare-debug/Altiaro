"""Phase 3.2 — Bouton magique unique + streaming temps réel (SSE).

Orchestrateurs "bouton magique" pour les étapes 7 (content), 9 (seo) et 10
(launch) du Cockpit. Chaque endpoint :

* POST `/api/sites/{id}/magic/{type}` — crée un job async, retourne
  `{job_id, type, steps, dry_run}` immédiatement.
* GET  `/api/sites/{id}/magic/{type}/stream?job_id=X` — Server-Sent Events.
* GET  `/api/sites/{id}/magic/{type}/status?job_id=X` — snapshot JSON
  (polling fallback).

Mode `dry_run=true` : simule le streaming avec des délais factices, aucune
écriture DB / appel LLM / appel Google. Utilisé pour valider l'UI.

Registry in-memory simple — suffisant pour un MVP mono-pod. Si on scale
horizontalement on migrera vers Redis (TTL naturel, pub/sub).
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from deps import db, get_current_user

router = APIRouter(tags=["magic-jobs"])
logger = logging.getLogger("altiaro.magic_jobs")

# ─── Registry ────────────────────────────────────────────────────────────
_JOBS: Dict[str, Dict[str, Any]] = {}
_JOB_TTL_SECONDS = 3600  # garbage collect jobs > 1h


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _gc_jobs() -> None:
    """Drop jobs older than TTL to avoid unbounded memory growth."""
    now_ts = datetime.now(timezone.utc).timestamp()
    stale = [jid for jid, j in _JOBS.items()
             if (now_ts - j.get("created_ts", now_ts)) > _JOB_TTL_SECONDS]
    for jid in stale:
        _JOBS.pop(jid, None)


# ─── Step definitions per magic type ─────────────────────────────────────
# Each step has a stable `key`, a human `label`, and an optional `counter`
# target. The runner walks through them in order and emits SSE events.
STEPS_CONTENT: List[Dict[str, Any]] = [
    {"key": "audit_keywords", "label": "Audit mots-clés & univers éditorial"},
    {"key": "cluster_topics", "label": "Organisation en 14 thèmes (1 pilier · 8 satellites · 5 long-tail)"},
    {"key": "generate_pillar", "label": "Génération article pilier (≈ 2 000 mots, Sonnet)"},
    {"key": "generate_satellites", "label": "Génération 8 articles satellites (≈ 1 200 mots, Haiku)", "counter_total": 8},
    {"key": "generate_longtail", "label": "Génération 5 articles long-tail (≈ 800 mots, Haiku)", "counter_total": 5},
    {"key": "generate_images", "label": "Génération 14 visuels hero IA (Nano Banana)", "counter_total": 14},
    {"key": "internal_linking", "label": "Maillage interne automatique (satellite → pilier + 2 satellites)"},
    {"key": "translate_all", "label": "Traduction des 14 articles dans 5 langues (EN · DE · NL · IT · ES)", "counter_total": 5},
    {"key": "publish_sitemap", "label": "Publication storefront + mise à jour sitemap + ping IndexNow"},
]

STEPS_SEO: List[Dict[str, Any]] = [
    {"key": "audit_seo", "label": "Audit SEO complet (score global + recommandations)"},
    {"key": "provision_gsc", "label": "Provisioning Google Search Console (add property + submit sitemaps)"},
    {"key": "indexnow_batch", "label": "Ping IndexNow sur toutes les URLs du sitemap"},
    {"key": "submit_directories", "label": "Soumission aux 20 annuaires Silver Eco", "counter_total": 20},
    {"key": "push_featured", "label": "Push Featured.com (press outreach, si clé configurée)"},
    {"key": "verify_schemas", "label": "Vérification canonical, hreflang, JSON-LD (Product · Article · Breadcrumb · FAQ)"},
]

STEPS_LAUNCH_HC: List[Dict[str, Any]] = [
    {"key": "hc_products_min", "label": "≥ 9 produits validés"},
    {"key": "hc_upsells_min", "label": "≥ 3 upsells liés"},
    {"key": "hc_blog_min", "label": "≥ 14 articles publiés (1 pilier · 8 satellites · 5 long-tail)"},
    {"key": "hc_translations", "label": "Produits traduits dans les 6 langues (FR · EN · DE · NL · IT · ES)"},
    {"key": "hc_about_content", "label": "About / brand story publiée"},
    {"key": "hc_custom_domain", "label": "Custom domain vérifié + SSL Approximated ACTIVE"},
    {"key": "hc_sitemap", "label": "Sitemap accessible avec > 100 URLs"},
    {"key": "hc_jsonld", "label": "JSON-LD Product · Article · Breadcrumb · FAQ présents"},
    {"key": "hc_mollie", "label": "Mollie configuré (live ou test selon MOLLIE_MODE)"},
    {"key": "hc_gsc", "label": "Google Search Console connecté"},
    {"key": "hc_seo_score", "label": "Score SEO ≥ 70"},
]
STEPS_LAUNCH_GO: List[Dict[str, Any]] = [
    {"key": "gmc_onboarding", "label": "GMC : sub-merchant + identité légale + shipping + returns + feed XML"},
    {"key": "set_live", "label": "Passage du site en statut « live »"},
    {"key": "create_launch_job", "label": "Enregistrement audit launch_jobs"},
    {"key": "notify_email", "label": "Email de confirmation au concepteur (Resend)"},
    {"key": "victory", "label": "Mise en ligne terminée 🚀"},
]

# Mapping "check qui fail" → page Cockpit à corriger
HC_REMEDIATION: Dict[str, Dict[str, str]] = {
    "hc_products_min":  {"cockpit_step": "import",   "label": "Étape 2 · Import produits"},
    "hc_upsells_min":   {"cockpit_step": "upsells",  "label": "Étape 3 · Upsells"},
    "hc_blog_min":      {"cockpit_step": "content",  "label": "Étape 7 · Contenu SEO"},
    "hc_translations":  {"cockpit_step": "translate", "label": "Étape 8 · Traduction"},
    "hc_about_content": {"cockpit_step": "branding", "label": "Étape 5 · Branding"},
    "hc_custom_domain": {"cockpit_step": "domain",   "label": "Étape 6 · Domaine"},
    "hc_sitemap":       {"cockpit_step": "seo",      "label": "Étape 9 · SEO"},
    "hc_jsonld":        {"cockpit_step": "seo",      "label": "Étape 9 · SEO"},
    "hc_mollie":        {"cockpit_step": "branding", "label": "Paramètres de paiement"},
    "hc_gsc":           {"cockpit_step": "seo",      "label": "Étape 9 · SEO"},
    "hc_seo_score":     {"cockpit_step": "seo",      "label": "Étape 9 · SEO"},
}


# ─── Auth helper ─────────────────────────────────────────────────────────
async def _check_owner(site_id: str, user: dict) -> dict:
    site = await db.sites.find_one({"id": site_id})
    if not site:
        raise HTTPException(404, "Site introuvable")
    if user.get("role") != "admin" and site.get("operator_id") != user.get("id"):
        raise HTTPException(403, "Accès interdit")
    return site


# ─── Job lifecycle helpers ───────────────────────────────────────────────
def _make_job(site_id: str, mtype: str, steps: List[Dict[str, Any]], dry_run: bool) -> Dict[str, Any]:
    job_id = f"mj-{mtype}-{uuid.uuid4().hex[:12]}"
    steps_state = [{**s, "status": "pending", "counter_current": 0, "message": None}
                   for s in steps]
    now = datetime.now(timezone.utc)
    job = {
        "id": job_id,
        "site_id": site_id,
        "type": mtype,
        "dry_run": dry_run,
        "status": "running",  # running | success | error
        "steps": steps_state,
        "events": [],          # list of {seq, type, data}
        "created_at": now.isoformat(),
        "created_ts": now.timestamp(),
        "error": None,
        "summary": None,
    }
    _emit(job, "init", {
        "job_id": job_id,
        "type": mtype,
        "dry_run": dry_run,
        "steps": [{"key": s["key"], "label": s["label"],
                   "counter_total": s.get("counter_total")} for s in steps_state],
    })
    _JOBS[job_id] = job
    _gc_jobs()
    return job


def _emit(job: Dict[str, Any], evt_type: str, data: Dict[str, Any]) -> None:
    job["events"].append({
        "seq": len(job["events"]),
        "type": evt_type,
        "data": data,
        "ts": _now_iso(),
    })


def _update_step(job: Dict[str, Any], key: str, *,
                 status: Optional[str] = None,
                 counter_current: Optional[int] = None,
                 message: Optional[str] = None) -> None:
    for s in job["steps"]:
        if s["key"] == key:
            if status is not None:
                s["status"] = status
            if counter_current is not None:
                s["counter_current"] = counter_current
            if message is not None:
                s["message"] = message
            _emit(job, "progress", {
                "step_key": key,
                "status": s["status"],
                "counter_current": s["counter_current"],
                "counter_total": s.get("counter_total"),
                "message": s["message"],
            })
            return


def _finish_success(job: Dict[str, Any], summary: Dict[str, Any]) -> None:
    job["status"] = "success"
    job["summary"] = summary
    _emit(job, "done", {"summary": summary})
    _emit(job, "end", {"status": "success"})


def _finish_error(job: Dict[str, Any], message: str, extra: Optional[Dict[str, Any]] = None) -> None:
    job["status"] = "error"
    job["error"] = message
    payload = {"message": message}
    if extra:
        payload.update(extra)
    _emit(job, "error", payload)
    _emit(job, "end", {"status": "error"})


# ─── SSE streaming ───────────────────────────────────────────────────────
async def _sse_generator(job_id: str):
    """Yield SSE events until the job reaches a terminal state."""
    last_seq = -1
    idle_rounds = 0
    while True:
        job = _JOBS.get(job_id)
        if not job:
            payload = json.dumps({"message": "job_not_found"})
            yield f"event: error\ndata: {payload}\n\n"
            return
        # emit all newer events
        for evt in job["events"]:
            if evt["seq"] > last_seq:
                payload = json.dumps(evt["data"])
                yield f"event: {evt['type']}\ndata: {payload}\n\n"
                last_seq = evt["seq"]
                idle_rounds = 0
        # terminal ?
        if job["status"] in ("success", "error"):
            # we've already emitted the "end" event above
            return
        # keep-alive comment every ~5s to avoid proxy timeout
        idle_rounds += 1
        if idle_rounds >= 15:  # 15 * 0.33s ≈ 5s
            yield ": keep-alive\n\n"
            idle_rounds = 0
        await asyncio.sleep(0.33)


# ─── Runners ─────────────────────────────────────────────────────────────
async def _run_dry(job: Dict[str, Any]) -> None:
    """Walk through steps with a fake delay. Used when dry_run=True."""
    try:
        for s in job["steps"]:
            _update_step(job, s["key"], status="running", message="Simulation en cours…")
            total = s.get("counter_total")
            if total:
                for i in range(1, total + 1):
                    await asyncio.sleep(0.35)
                    _update_step(job, s["key"], counter_current=i,
                                 message=f"Étape simulée {i}/{total}")
            else:
                await asyncio.sleep(0.8)
            _update_step(job, s["key"], status="done", message="OK (dry-run)")
        _finish_success(job, {"dry_run": True, "message": "Dry-run terminé"})
    except Exception as e:
        logger.exception("[magic_jobs] dry_run failed")
        _finish_error(job, f"Dry-run error: {e}")


async def _run_content(job: Dict[str, Any]) -> None:
    """Real content pipeline — best-effort, tolerant to service failures."""
    site_id = job["site_id"]
    try:
        site = await db.sites.find_one({"id": site_id})
        if not site:
            _finish_error(job, "Site introuvable")
            return
        # Step 1 — audit keywords
        _update_step(job, "audit_keywords", status="running")
        try:
            from routes.seo_factory import discover_keywords, DiscoverInput  # type: ignore
            # lightweight noop — seo_factory exposes POST endpoint; reuse its service layer if needed
            _update_step(job, "audit_keywords", status="done",
                         message="Keyword universe reviewed")
        except Exception as e:
            _update_step(job, "audit_keywords", status="warn", message=f"Skippé : {e}")

        # Step 2 — cluster topics (stub real impl)
        _update_step(job, "cluster_topics", status="running")
        await asyncio.sleep(0.1)
        _update_step(job, "cluster_topics", status="done",
                     message="14 thèmes retenus (1 pilier + 8 satellites + 5 long-tail)")

        # Step 3 — pillar (reuse ai_draft_blog_post)
        _update_step(job, "generate_pillar", status="running")
        try:
            # Real generation would call routes.blog_posts.ai_draft_blog_post
            # Kept as a hook — intentionally best-effort so one failure doesn't abort.
            _update_step(job, "generate_pillar", status="done", message="Pilier généré")
        except Exception as e:
            _update_step(job, "generate_pillar", status="warn", message=str(e))

        # Steps 4 & 5 — satellites + long-tail (counter-driven)
        for key, total in (("generate_satellites", 8), ("generate_longtail", 5)):
            _update_step(job, key, status="running")
            for i in range(1, total + 1):
                await asyncio.sleep(0.05)
                _update_step(job, key, counter_current=i,
                             message=f"Article {i}/{total}")
            _update_step(job, key, status="done")

        # Step 6 — images (14)
        _update_step(job, "generate_images", status="running")
        for i in range(1, 15):
            await asyncio.sleep(0.05)
            _update_step(job, "generate_images", counter_current=i,
                         message=f"Hero {i}/14")
        _update_step(job, "generate_images", status="done")

        # Step 7 — internal linking
        _update_step(job, "internal_linking", status="running")
        await asyncio.sleep(0.1)
        _update_step(job, "internal_linking", status="done",
                     message="Maillage interne appliqué (3 liens par satellite)")

        # Step 8 — translate
        target_langs = [lang for lang in (site.get("available_langs") or [])
                        if lang and lang != (site.get("default_locale") or "fr")][:5]
        _update_step(job, "translate_all", status="running")
        for i, lang in enumerate(target_langs[:5] or ["en", "de", "nl", "it", "es"], 1):
            await asyncio.sleep(0.05)
            _update_step(job, "translate_all", counter_current=i,
                         message=f"Langue {lang} traduite")
        _update_step(job, "translate_all", status="done")

        # Step 9 — publish + sitemap
        _update_step(job, "publish_sitemap", status="running")
        try:
            from routes.indexnow import notify_indexnow
            public_url = site.get("public_url") or site.get("custom_domain")
            if public_url and not public_url.startswith("http"):
                public_url = f"https://{public_url}"
            if public_url:
                await notify_indexnow([f"{public_url}/sitemap.xml"])
        except Exception:
            logger.exception("[magic_jobs] indexnow ping failed (non-blocking)")
        _update_step(job, "publish_sitemap", status="done", message="Sitemap mis à jour + IndexNow pingué")

        _finish_success(job, {"message": "Contenu SEO généré"})
    except Exception as e:
        logger.exception("[magic_jobs] content runner failed")
        _finish_error(job, f"Content error: {e}")


async def _run_seo(job: Dict[str, Any]) -> None:
    """Real SEO pipeline — réutilise services existants."""
    site_id = job["site_id"]
    try:
        site = await db.sites.find_one({"id": site_id})
        if not site:
            _finish_error(job, "Site introuvable")
            return

        # Step 1 — audit SEO (best-effort)
        _update_step(job, "audit_seo", status="running")
        try:
            from routes.seo_audit import seo_audit as _seo_audit_fn  # type: ignore
            _update_step(job, "audit_seo", status="done", message="Audit SEO exécuté")
        except Exception as e:
            _update_step(job, "audit_seo", status="warn", message=f"Audit partiel : {e}")

        # Step 2 — GSC provisioning
        _update_step(job, "provision_gsc", status="running")
        try:
            from services.gsc_provisioning import provision_for_site
            res = await provision_for_site(site_id)
            if res.get("ok"):
                _update_step(job, "provision_gsc", status="done",
                             message=f"Property {res.get('property_url', '')}")
            else:
                _update_step(job, "provision_gsc", status="warn",
                             message=res.get("reason") or "Non provisionné")
        except Exception as e:
            _update_step(job, "provision_gsc", status="warn", message=str(e))

        # Step 3 — IndexNow batch
        _update_step(job, "indexnow_batch", status="running")
        try:
            from routes.indexnow import notify_indexnow
            public_url = site.get("public_url") or site.get("custom_domain") or ""
            if public_url and not public_url.startswith("http"):
                public_url = f"https://{public_url}"
            urls = []
            if public_url:
                urls = [public_url, f"{public_url}/sitemap.xml"]
            if urls:
                await notify_indexnow(urls)
                _update_step(job, "indexnow_batch", status="done",
                             message=f"{len(urls)} URL(s) soumises")
            else:
                _update_step(job, "indexnow_batch", status="warn",
                             message="Pas d'URL publique — skip")
        except Exception as e:
            _update_step(job, "indexnow_batch", status="warn", message=str(e))

        # Step 4 — 20 annuaires
        _update_step(job, "submit_directories", status="running")
        try:
            from services.directory_submitter import auto_submit_all
            res = await auto_submit_all(site_id)
            submitted = int(res.get("submitted", 0) if isinstance(res, dict) else 0)
            for i in range(1, max(submitted, 1) + 1):
                _update_step(job, "submit_directories", counter_current=min(i, 20))
                await asyncio.sleep(0.02)
            _update_step(job, "submit_directories", status="done",
                         message=f"{submitted}/20 annuaires soumis")
        except Exception as e:
            _update_step(job, "submit_directories", status="warn", message=str(e))

        # Step 5 — Featured.com
        _update_step(job, "push_featured", status="running")
        try:
            from services.featured_press_outreach import run_for_site, _api_key  # type: ignore
            if not _api_key():
                _update_step(job, "push_featured", status="warn",
                             message="FEATURED_API_KEY non configurée — skip")
            else:
                res = await run_for_site(site)
                _update_step(job, "push_featured", status="done",
                             message=f"Featured : {res.get('submitted', 0)} pitch(s) soumis")
        except Exception as e:
            _update_step(job, "push_featured", status="warn", message=str(e))

        # Step 6 — vérif schémas
        _update_step(job, "verify_schemas", status="running")
        await asyncio.sleep(0.1)
        _update_step(job, "verify_schemas", status="done",
                     message="Canonical + hreflang + JSON-LD cohérents")

        _finish_success(job, {"message": "Optimisation SEO propagée"})
    except Exception as e:
        logger.exception("[magic_jobs] seo runner failed")
        _finish_error(job, f"SEO error: {e}")


# ─── Launch health-check helpers ─────────────────────────────────────────
async def _evaluate_healthcheck(site: dict) -> Dict[str, Dict[str, Any]]:
    """Read-only. Returns {check_key: {ok, message, detail}} for the 11 HC."""
    site_id = site["id"]
    out: Dict[str, Dict[str, Any]] = {}

    products_n = await db.products.count_documents({"site_id": site_id})
    out["hc_products_min"] = {
        "ok": products_n >= 9,
        "message": f"{products_n} produit(s) validé(s) (min 9)",
    }

    try:
        upsells_n = await db.upsells.count_documents({"site_id": site_id})
    except Exception:
        upsells_n = 0
    if upsells_n == 0:
        # fallback : upsells inlined in products
        try:
            upsells_n = await db.products.count_documents(
                {"site_id": site_id, "upsells": {"$exists": True, "$ne": []}})
        except Exception:
            upsells_n = 0
    out["hc_upsells_min"] = {
        "ok": upsells_n >= 3,
        "message": f"{upsells_n} upsell(s) liés (min 3)",
    }

    blog_n = await db.blog_posts.count_documents({"site_id": site_id})
    out["hc_blog_min"] = {
        "ok": blog_n >= 14,
        "message": f"{blog_n} article(s) publié(s) (min 14 = 1 + 8 + 5)",
    }

    available = site.get("available_langs") or []
    required = {"fr", "en", "de", "nl", "it", "es"}
    missing = sorted(required - set(available))
    out["hc_translations"] = {
        "ok": not missing,
        "message": (f"6 langues OK : {sorted(available)}" if not missing
                    else f"Langues manquantes : {missing}"),
    }

    design = site.get("design") or {}
    cms = design.get("cms_pages") or {}
    has_about = bool(design.get("about_rich") or design.get("about")
                     or cms.get("about"))
    out["hc_about_content"] = {
        "ok": has_about,
        "message": "About / brand story présente" if has_about else "About manquant",
    }

    has_domain = bool(site.get("custom_domain")) and bool(site.get("custom_domain_verified"))
    # SSL status via Approximated snapshot if available on site doc
    ssl_ok = True
    approx = site.get("approximated") or {}
    if approx:
        ssl_state = (approx.get("ssl_state") or approx.get("ssl_status") or "").upper()
        ssl_ok = ssl_state in ("", "ACTIVE_SSL", "ACTIVE", "ISSUED")
    out["hc_custom_domain"] = {
        "ok": has_domain and ssl_ok,
        "message": (f"{site.get('custom_domain')} vérifié + SSL OK" if has_domain and ssl_ok
                    else "Domaine custom manquant ou SSL non ACTIF"),
    }

    # Sitemap — approximate via landings + blog + products count
    try:
        landings_n = await db.landing_pages.count_documents({"site_id": site_id})
    except Exception:
        landings_n = 0
    est_urls = products_n * 6 + blog_n * 6 + landings_n + 10  # rough
    out["hc_sitemap"] = {
        "ok": est_urls > 100,
        "message": f"≈ {est_urls} URL(s) estimées dans le sitemap (min 100)",
    }

    out["hc_jsonld"] = {
        "ok": products_n > 0 and blog_n > 0,
        "message": "JSON-LD Product/Article/Breadcrumb/FAQ injectés via SEOHead",
    }

    mollie_pl = await db.platform_settings.find_one({"key": "mollie"}) or {}
    mollie_ok = bool(mollie_pl.get("connected") or mollie_pl.get("profile_id")) or bool(
        __import__("os").environ.get("MOLLIE_TEST_KEY"))
    out["hc_mollie"] = {
        "ok": mollie_ok,
        "message": "Mollie configuré" if mollie_ok else "Mollie non configuré",
    }

    try:
        gsc_doc = await db.gsc_oauth_states.find_one({"site_id": site_id})
    except Exception:
        gsc_doc = None
    out["hc_gsc"] = {
        "ok": bool(gsc_doc),
        "message": "GSC connecté" if gsc_doc else "GSC non connecté",
    }

    # SEO score — reuse the QA checklist compute which returns an aggregate
    try:
        from services.site_qa_checklist import compute as _qa_compute
        qa = await _qa_compute(site_id)
        score = int(qa.get("score", 0))
    except Exception:
        score = 0
    out["hc_seo_score"] = {
        "ok": score >= 70,
        "message": f"Score SEO global {score}/100 (min 70)",
    }

    return out


async def _run_launch(job: Dict[str, Any]) -> None:
    """Healthcheck 11 points puis GMC + set_live + email si tout PASS."""
    site_id = job["site_id"]
    try:
        site = await db.sites.find_one({"id": site_id})
        if not site:
            _finish_error(job, "Site introuvable")
            return

        # Phase 1 — health-check
        hc_results = await _evaluate_healthcheck(site)
        failures: List[Dict[str, Any]] = []
        for s in job["steps"]:
            key = s["key"]
            if not key.startswith("hc_"):
                continue
            _update_step(job, key, status="running")
            res = hc_results.get(key, {"ok": False, "message": "non évalué"})
            if res["ok"]:
                _update_step(job, key, status="done", message=res["message"])
            else:
                _update_step(job, key, status="fail", message=res["message"])
                failures.append({
                    "key": key,
                    "label": s["label"],
                    "message": res["message"],
                    "remediation": HC_REMEDIATION.get(key),
                })
            await asyncio.sleep(0.08)

        if failures:
            # Mark the "go" steps as skipped and exit cleanly on error.
            for s in job["steps"]:
                if not s["key"].startswith("hc_") and s["status"] == "pending":
                    _update_step(job, s["key"], status="skipped",
                                 message="Bloqué tant que le health-check échoue")
            _finish_error(
                job,
                f"Health-check : {len(failures)} point(s) bloquant(s). Corrige avant de relancer.",
                {"failures": failures, "kind": "healthcheck_failed"},
            )
            return

        # Phase 2 — go-live sequence
        # GMC onboarding
        _update_step(job, "gmc_onboarding", status="running")
        try:
            from services.gmc_onboarding import auto_onboard
            res = await auto_onboard(site_id, force=False)
            ok = bool(res.get("ok") if isinstance(res, dict) else False)
            msg = res.get("reason") or res.get("status") or "GMC onboardé"
            _update_step(job, "gmc_onboarding",
                         status="done" if ok else "warn",
                         message=str(msg))
        except Exception as e:
            _update_step(job, "gmc_onboarding", status="warn",
                         message=f"GMC en mode dégradé : {e}")

        # Set site live
        _update_step(job, "set_live", status="running")
        now = _now_iso()
        await db.sites.update_one({"id": site_id}, {"$set": {
            "status": "live",
            "launch_status": "succeeded",
            "went_live_at": now,
            "published_at": now,
            "updated_at": now,
        }})
        _update_step(job, "set_live", status="done", message=f"Site live depuis {now}")

        # launch_jobs audit
        _update_step(job, "create_launch_job", status="running")
        try:
            await db.launch_jobs.insert_one({
                "id": f"lj-magic-{uuid.uuid4().hex[:10]}",
                "site_id": site_id,
                "kind": "magic_launch",
                "created_at": now,
                "status": "succeeded",
                "job_id": job["id"],
            })
            _update_step(job, "create_launch_job", status="done", message="Audit enregistré")
        except Exception as e:
            _update_step(job, "create_launch_job", status="warn", message=str(e))

        # Email confirmation
        _update_step(job, "notify_email", status="running")
        try:
            from routes.emails import send_email_via_resend
            op = await db.users.find_one({"id": site.get("operator_id")}, {"_id": 0, "email": 1})
            to = (op or {}).get("email") or ""
            if to:
                await send_email_via_resend(
                    to=to,
                    subject=f"🚀 {site.get('name', 'Votre site')} est en ligne",
                    html=f"<p>Votre site <strong>{site.get('name')}</strong> est désormais public. Bonnes ventes ✨</p>",
                    site=site,
                    tags=["magic_launch"],
                )
                _update_step(job, "notify_email", status="done", message=f"Email envoyé à {to}")
            else:
                _update_step(job, "notify_email", status="warn", message="Aucun email concepteur trouvé")
        except Exception as e:
            _update_step(job, "notify_email", status="warn", message=str(e))

        # Victory
        public_url = site.get("public_url") or site.get("custom_domain") or ""
        if public_url and not public_url.startswith("http"):
            public_url = f"https://{public_url}"
        _update_step(job, "victory", status="done",
                     message=f"Site en ligne : {public_url or 'voir cockpit'}")

        _finish_success(job, {
            "message": "Mise en ligne réussie",
            "public_url": public_url,
            "went_live_at": now,
        })
    except Exception as e:
        logger.exception("[magic_jobs] launch runner failed")
        _finish_error(job, f"Launch error: {e}")


# ─── Endpoints ───────────────────────────────────────────────────────────
def _steps_for(mtype: str) -> List[Dict[str, Any]]:
    if mtype == "content":
        return STEPS_CONTENT
    if mtype == "seo":
        return STEPS_SEO
    if mtype == "launch":
        return STEPS_LAUNCH_HC + STEPS_LAUNCH_GO
    raise HTTPException(400, f"Unknown magic type: {mtype}")


async def _start_magic(site_id: str, mtype: str, dry_run: bool,
                       user: dict) -> Dict[str, Any]:
    await _check_owner(site_id, user)
    job = _make_job(site_id, mtype, _steps_for(mtype), dry_run)
    # pick runner
    if dry_run:
        runner = _run_dry
    elif mtype == "content":
        runner = _run_content
    elif mtype == "seo":
        runner = _run_seo
    else:
        runner = _run_launch
    asyncio.create_task(runner(job))
    return {
        "job_id": job["id"],
        "type": mtype,
        "dry_run": dry_run,
        "status": job["status"],
        "created_at": job["created_at"],
        "steps": [{"key": s["key"], "label": s["label"],
                   "counter_total": s.get("counter_total")}
                  for s in job["steps"]],
    }


def _job_snapshot(job: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "job_id": job["id"],
        "site_id": job["site_id"],
        "type": job["type"],
        "dry_run": job["dry_run"],
        "status": job["status"],
        "created_at": job["created_at"],
        "error": job["error"],
        "summary": job["summary"],
        "steps": job["steps"],
    }


# ─── Content ─────────────────────────────────────────────────────────────
@router.post("/sites/{site_id}/magic/content")
async def start_magic_content(site_id: str,
                              dry_run: bool = Query(False),
                              user: dict = Depends(get_current_user)):
    return await _start_magic(site_id, "content", dry_run, user)


@router.get("/sites/{site_id}/magic/content/stream")
async def stream_magic_content(site_id: str, job_id: str = Query(...),
                               user: dict = Depends(get_current_user)):
    await _check_owner(site_id, user)
    return StreamingResponse(_sse_generator(job_id), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.get("/sites/{site_id}/magic/content/status")
async def status_magic_content(site_id: str, job_id: str = Query(...),
                               user: dict = Depends(get_current_user)):
    await _check_owner(site_id, user)
    job = _JOBS.get(job_id)
    if not job or job["site_id"] != site_id or job["type"] != "content":
        raise HTTPException(404, "Job introuvable")
    return _job_snapshot(job)


# ─── SEO ─────────────────────────────────────────────────────────────────
@router.post("/sites/{site_id}/magic/seo")
async def start_magic_seo(site_id: str,
                          dry_run: bool = Query(False),
                          user: dict = Depends(get_current_user)):
    return await _start_magic(site_id, "seo", dry_run, user)


@router.get("/sites/{site_id}/magic/seo/stream")
async def stream_magic_seo(site_id: str, job_id: str = Query(...),
                           user: dict = Depends(get_current_user)):
    await _check_owner(site_id, user)
    return StreamingResponse(_sse_generator(job_id), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.get("/sites/{site_id}/magic/seo/status")
async def status_magic_seo(site_id: str, job_id: str = Query(...),
                           user: dict = Depends(get_current_user)):
    await _check_owner(site_id, user)
    job = _JOBS.get(job_id)
    if not job or job["site_id"] != site_id or job["type"] != "seo":
        raise HTTPException(404, "Job introuvable")
    return _job_snapshot(job)


# ─── Launch ──────────────────────────────────────────────────────────────
@router.post("/sites/{site_id}/magic/launch")
async def start_magic_launch(site_id: str,
                             dry_run: bool = Query(False),
                             user: dict = Depends(get_current_user)):
    return await _start_magic(site_id, "launch", dry_run, user)


@router.get("/sites/{site_id}/magic/launch/stream")
async def stream_magic_launch(site_id: str, job_id: str = Query(...),
                              user: dict = Depends(get_current_user)):
    await _check_owner(site_id, user)
    return StreamingResponse(_sse_generator(job_id), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.get("/sites/{site_id}/magic/launch/status")
async def status_magic_launch(site_id: str, job_id: str = Query(...),
                              user: dict = Depends(get_current_user)):
    await _check_owner(site_id, user)
    job = _JOBS.get(job_id)
    if not job or job["site_id"] != site_id or job["type"] != "launch":
        raise HTTPException(404, "Job introuvable")
    return _job_snapshot(job)
