"""
Altiaro — FastAPI orchestrator.
Monte les routers modulaires définis dans /app/backend/routes/.
"""
import os
import logging
import uuid
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

# Google OAuth scope relaxation.
# Quand on enchaîne plusieurs OAuth Google (Ads puis Merchant puis GSC),
# Google retourne dans le token les scopes précédemment accordés en plus du
# scope demandé (comportement de include_granted_scopes=true). La lib
# google-auth-oauthlib refuse sinon l'échange avec "Scope has changed".
# Ce flag relax oauthlib pour tolérer le sur-ensemble de scopes.
# DOIT être posé AVANT l'import de google_auth_oauthlib / oauthlib.
os.environ.setdefault("OAUTHLIB_RELAX_TOKEN_SCOPE", "1")

from datetime import datetime, timezone

from fastapi import FastAPI, APIRouter
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware

from deps import db, client, ADMIN_EMAIL, ADMIN_PASSWORD, FRONTEND_URL, UPLOAD_DIR, hash_password, verify_password
from seed_niches import seed_niches
from seed_prompts import BLOCKS, PHASE_TO_BLOCK

from routes import auth as auth_routes
from routes import users as users_routes
from routes import sites as sites_routes
from routes import steps as steps_routes
from routes import products as products_routes
from routes import orders as orders_routes
from routes import public_shop as public_routes
from routes import niches as niches_routes
from routes import dashboard as dashboard_routes
from routes import meta as meta_routes
from routes import uploads as uploads_routes
from routes import search as search_routes
from routes import customers as customers_routes
from routes import storefront_search as storefront_search_routes
from routes import analyzer as analyzer_routes
from routes import ads_copy as ads_copy_routes
from routes import duplicate as duplicate_routes
from routes import site_domain as domain_routes
from routes import scale as scale_routes
from routes import empire as empire_routes
from routes import blocks_execute as blocks_execute_routes
from routes import copilot as copilot_routes
from routes import payments as payments_routes
from routes import mollie_oauth as mollie_oauth_routes  # Lot E — Mollie Connect multi-tenant
from routes import billing as billing_routes
from routes import design as design_routes
from routes import sourcing as sourcing_routes
from routes import seo as seo_routes
from routes import wizard as wizard_routes
from routes import google_ads as google_ads_routes
from routes import opportunity as opportunity_routes
from routes import emails as emails_routes
from routes import ovh_domains as domains_routes
from routes import quick_scan as quick_scan_routes
from routes import concepteur_cockpit as concepteur_cockpit_routes
from routes import platform as platform_routes
from routes import admin_health as admin_health_routes
from routes import auth_signup as auth_signup_routes
from routes import product_narrative as product_narrative_routes
from routes import product_bundles as product_bundles_routes
from routes import blog_posts as blog_posts_routes
from routes import reviews_hook as reviews_hook_routes
from routes import indexnow as indexnow_routes
from routes import seo_audit as seo_audit_routes
from routes import seo_studio as seo_studio_routes
from routes import aliexpress as aliexpress_routes
from routes import validation as validation_routes
from routes import cockpit_tools as cockpit_tools_routes
from routes import product_images as product_images_routes
from routes import launch as launch_routes
from routes import seo_coach as seo_coach_routes
from routes import gsc as gsc_routes
from routes import aeo as aeo_routes
from routes import internal_linking as internal_linking_routes
from routes import citation_tracker as citation_tracker_routes
from routes import ae_deals_watcher as ae_deals_watcher_routes
from routes import testimonials_ai as testimonials_ai_routes
from routes import merchant as merchant_routes
from routes import resend_domain as resend_domain_routes
from routes import journey_gating as journey_gating_routes
from routes import analytics as analytics_routes
from routes import seo_automation as seo_automation_routes
from routes import google_ads_manual as google_ads_manual_routes
from routes import upsells_ai as upsells_ai_routes
from routes import admin_llm_health as admin_llm_health_routes
from routes import legal as legal_routes
from routes import product_content_admin as product_content_admin_routes
from routes import ai_tweak as ai_tweak_routes
from routes import product_image_regen as product_image_regen_routes  # Phase 2.7.3 — régénération ciblée d'1 image
from routes import translate as translate_routes  # Phase 3 — traduction multi-langue (étape 7)
from routes import blog_queue as blog_queue_routes  # Phase A2 — file d'attente blog
from routes import seo_factory as seo_factory_routes  # Phase B6 — factory mots-clés / landings
from routes import site_qa as site_qa_routes  # Phase C — checklist QA + go-live
from routes import geo as geo_routes_finalisation  # Phase D' — détection pays/devise
from routes import automation as automation_routes  # Refonte UX — toggles automatisation
from routes import well_known as well_known_routes  # Google Site Verification (altiaro.com)
from routes import google_master as google_master_routes  # Master OAuth + auto-provisioning
from routes import public_legal as public_legal_routes  # Fallback HTML SSR /legal/* (altiaro.com prod)
from routes import admin_reset as admin_reset_routes  # Reset site → étape 5 + launch instructions

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("conceptfactory")

app = FastAPI(
    title="Altiaro API",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)
api = APIRouter(prefix="/api")

# Mount all routers
api.include_router(auth_routes.router)
api.include_router(users_routes.router)
api.include_router(sites_routes.router)
api.include_router(steps_routes.router)
api.include_router(products_routes.router)
api.include_router(orders_routes.router)
api.include_router(public_routes.router)
api.include_router(analyzer_routes.router)  # must be registered BEFORE niches to avoid /niches/{slug} conflict
api.include_router(ads_copy_routes.router)
api.include_router(duplicate_routes.router)
api.include_router(domain_routes.router)
api.include_router(scale_routes.router)
api.include_router(empire_routes.router)
api.include_router(blocks_execute_routes.router)
api.include_router(copilot_routes.router)
api.include_router(payments_routes.router)
api.include_router(mollie_oauth_routes.router)  # Lot E — Mollie Connect OAuth
api.include_router(billing_routes.router)
api.include_router(design_routes.router)
api.include_router(sourcing_routes.router)
api.include_router(seo_routes.router)
api.include_router(wizard_routes.router)
api.include_router(google_ads_routes.router)
api.include_router(opportunity_routes.router)
api.include_router(emails_routes.router)
api.include_router(domains_routes.router)
api.include_router(quick_scan_routes.router)
api.include_router(concepteur_cockpit_routes.router)
api.include_router(platform_routes.router)
api.include_router(admin_health_routes.router)
api.include_router(auth_signup_routes.router)
api.include_router(niches_routes.router)
api.include_router(dashboard_routes.router)
api.include_router(meta_routes.router)
api.include_router(uploads_routes.router)
api.include_router(search_routes.router)
api.include_router(customers_routes.router)
api.include_router(storefront_search_routes.router)
api.include_router(product_narrative_routes.router)
api.include_router(product_bundles_routes.router)
api.include_router(blog_posts_routes.router)
api.include_router(reviews_hook_routes.router)
api.include_router(indexnow_routes.router)
api.include_router(seo_audit_routes.router)
api.include_router(seo_studio_routes.router)
api.include_router(aliexpress_routes.router)
api.include_router(validation_routes.router)
api.include_router(cockpit_tools_routes.router)
api.include_router(product_images_routes.router)
api.include_router(launch_routes.router)
api.include_router(seo_coach_routes.router)
api.include_router(gsc_routes.router)
api.include_router(aeo_routes.router)
api.include_router(internal_linking_routes.router)
api.include_router(citation_tracker_routes.router)
api.include_router(ae_deals_watcher_routes.router)
api.include_router(testimonials_ai_routes.router)
api.include_router(merchant_routes.router)
api.include_router(resend_domain_routes.router)
api.include_router(journey_gating_routes.router)
api.include_router(analytics_routes.router)
api.include_router(seo_automation_routes.router)
api.include_router(google_ads_manual_routes.router)
api.include_router(upsells_ai_routes.router)
api.include_router(admin_llm_health_routes.router)
api.include_router(admin_llm_health_routes.public_router)
api.include_router(legal_routes.public_router)
api.include_router(legal_routes.admin_router)
api.include_router(product_content_admin_routes.router)  # Lot I — admin back-fill tagline + USPs
api.include_router(ai_tweak_routes.router)  # Phase 2.5 (Tâche B) — AI tweak site design (Sonnet)
api.include_router(product_image_regen_routes.router)  # Phase 2.7.3 — régénération ciblée d'1 image
api.include_router(translate_routes.router)  # Phase 3 — traduction multi-langue (étape 7)
api.include_router(blog_queue_routes.router)  # Phase A2 — file d'attente blog
api.include_router(seo_factory_routes.router)  # Phase B6 — factory mots-clés / landings
api.include_router(site_qa_routes.router)  # Phase C — checklist QA + go-live
api.include_router(geo_routes_finalisation.router)  # Phase D' — détection pays/devise
api.include_router(automation_routes.router)  # Refonte UX — toggles automatisation
api.include_router(well_known_routes.router)  # Google Site Verification (altiaro.com)
api.include_router(google_master_routes.router)  # Master OAuth + auto-provisioning
api.include_router(admin_reset_routes.router)  # Admin reset + launch instructions

# IMPORTANT — Routes /legal/* HTML server-side : montées DIRECTEMENT sur `app`
# (pas sur le router /api). Sur le preview Kubernetes l'ingress route /legal/*
# au frontend port 3000, donc ces routes ne sont jamais appelées côté preview ;
# le SPA React continue de gérer. Sur prod altiaro.com (Emergent Native Deploy
# où FastAPI sert aussi le frontend statique), elles assurent un HTML 200
# valide pour Google Merchant Center MCA même si le bundle JS est figé.
app.include_router(public_legal_routes.router)


@app.on_event("startup")
async def _reap_stale_launch_jobs():
    """Mark zombie launch_jobs (running when server was killed) as failed.
    Otherwise a concurrent-launch guard would block new runs forever."""
    try:
        from deps import db
        from datetime import datetime, timezone
        res = await db.launch_jobs.update_many(
            {"status": "running"},
            {"$set": {
                "status": "failed",
                "error": "Serveur redémarré pendant la génération",
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }},
        )
        if res.modified_count:
            logger.info(f"[startup] reaped {res.modified_count} zombie launch_jobs")
    except Exception as e:
        logger.warning(f"[startup] launch_jobs reaper failed: {e}")


async def _run_citation_tracker_all_sites(logger_=None):
    """Run citation tracker weekly for every site that has at least one
    enriched product (AEO Q/R already generated). Skips if LLM budget
    exhausted."""
    from datetime import datetime as _dt, timezone as _tz
    log = logger_ or logger
    ran = 0
    skipped = 0
    budget_hit = False
    cursor = db.sites.find(
        {"design.seo_coach.citation_auto_enabled": {"$ne": False}},
        {"_id": 0, "id": 1, "design.brand.name": 1, "name": 1, "custom_domain": 1},
    )
    sites = await cursor.to_list(500)
    log.info(f"[citation_tracker] scanning {len(sites)} sites")
    for s in sites:
        if budget_hit:
            skipped += 1
            continue
        has_aeo = await db.products.find_one(
            {"site_id": s["id"], "narrative.aeo_enriched_at": {"$exists": True}},
            {"_id": 0, "id": 1},
        )
        if not has_aeo:
            skipped += 1
            continue
        try:
            from routes.citation_tracker import (
                _pick_questions, _ask_claude_panel, _mentions_brand, _pick_text,
            )
            brand_name = _pick_text((s.get("design") or {}).get("brand", {}).get("name") or s.get("name") or "")
            if not brand_name:
                skipped += 1
                continue
            products = await db.products.find(
                {"site_id": s["id"], "status": "active"},
                {"_id": 0, "name": 1, "narrative": 1},
            ).to_list(60)
            questions = _pick_questions(s, products, max_questions=5)
            if not questions:
                skipped += 1
                continue
            results = []
            hit = 0
            for q in questions:
                answer, err = await _ask_claude_panel(q)
                if err == "budget_exceeded":
                    budget_hit = True
                    break
                if err or not answer:
                    results.append({"question": q, "answer": None, "cited": False, "error": err})
                    continue
                cited = _mentions_brand(answer, brand_name, s.get("custom_domain") or "")
                if cited:
                    hit += 1
                results.append({"question": q, "answer": answer[:400], "cited": cited})
            if budget_hit:
                break
            total = len(results)
            rate = round((hit / total) * 100) if total else 0
            snapshot = {
                "at": _dt.now(_tz.utc).isoformat(),
                "rate": rate,
                "hit": hit,
                "total": total,
                "brand_name": brand_name,
                "results": results,
            }
            await db.sites.update_one(
                {"id": s["id"]},
                {
                    "$set": {"design.seo_coach.last_citation_run": snapshot},
                    "$push": {"design.seo_coach.citation_history": {
                        "$each": [{"at": snapshot["at"], "rate": rate, "hit": hit, "total": total}],
                        "$slice": -26,
                    }},
                },
            )
            ran += 1
        except Exception:
            log.exception(f"[citation_tracker] site {s['id']} crashed")
    return {"ran": ran, "skipped": skipped, "budget_hit": budget_hit}


@app.on_event("startup")
async def startup():
    # Indexes
    await db.users.create_index("email", unique=True)
    await db.sites.create_index("created_at")
    await db.steps.create_index([("site_id", 1), ("number", 1)])
    await db.financials.create_index([("site_id", 1), ("month", 1)], unique=True)
    await db.login_attempts.create_index("identifier")
    await db.niches.create_index("slug", unique=True)
    await db.niches.create_index("rank")
    await db.countries.create_index("code", unique=True)
    await db.products.create_index([("site_id", 1), ("status", 1)])
    await db.products.create_index("created_at")
    await db.orders.create_index([("site_id", 1), ("created_at", -1)])
    await db.orders.create_index("order_number", unique=True)
    await db.orders.create_index([("_meta_ip", 1), ("created_at", -1)])
    await db.niche_analyses.create_index([("user_id", 1), ("created_at", -1)])
    await db.ads_copy.create_index([("site_id", 1), ("created_at", -1)])
    # Custom domain routing — unique per verified site
    await db.sites.create_index(
        "custom_domain",
        unique=True,
        partialFilterExpression={"custom_domain": {"$type": "string"}},
    )
    await db.block_outputs.create_index([("site_id", 1), ("block_id", 1), ("created_at", -1)])
    await db.copilot_messages.create_index([("user_id", 1), ("session_id", 1), ("ts_seq", 1)])
    await db.billing_profiles.create_index("user_id", unique=True)
    await db.ledger.create_index([("concepteur_id", 1), ("created_at", -1)])
    await db.ledger.create_index([("type", 1), ("status", 1)])

    # Chantier 7 — Storefront events (analytics interne)
    await db.storefront_events.create_index([("site_id", 1), ("created_at", -1)])
    await db.storefront_events.create_index([("site_id", 1), ("event", 1), ("created_at", -1)])
    await db.storefront_events.create_index([("site_id", 1), ("session_id", 1)])

    # Seed niche catalog (idempotent)
    try:
        seeded = await seed_niches(db)
        logger.info(f"Seeded {seeded} niches in catalog")
    except Exception:
        logger.exception("Failed to seed niches catalog")

    # Migrate existing steps to the current BLOCKS / PHASE_TO_BLOCK mapping.
    # Force re-apply so the 4→8 block reorganization updates existing sites.
    try:
        # Detect mismatches : any step whose block doesn't match the current mapping
        valid_block_ids = set(BLOCKS.keys())
        needs_migration = await db.steps.count_documents({
            "$or": [
                {"block": {"$exists": False}},
                {"block": {"$nin": list(valid_block_ids)}},
            ]
        })
        if needs_migration > 0:
            logger.info(f"Re-mapping {needs_migration} steps to new 8-block structure...")
        # Always re-apply (idempotent) — cheap and ensures consistency with seed_prompts
        for phase_code, block_id in PHASE_TO_BLOCK.items():
            meta = BLOCKS[block_id]
            await db.steps.update_many(
                {"phase": phase_code},
                {"$set": {
                    "block": block_id,
                    "block_name": meta["name"],
                    "block_order": meta["order"],
                    "block_emoji": meta["emoji"],
                }},
            )
        # Re-sync prompt/title/summary from seed_prompts.PROMPTS (keeps enriched prompts in sync)
        from seed_prompts import PROMPTS
        for p in PROMPTS:
            await db.steps.update_many(
                {"number": p["number"]},
                {"$set": {
                    "title": p["title"],
                    "summary": p["summary"],
                    "prompt": p["prompt"],
                }},
            )
        logger.info(f"Block mapping synchronized + {len(PROMPTS)} prompts refreshed.")
    except Exception:
        logger.exception("Failed block migration")

    # Seed admin user
    existing = await db.users.find_one({"email": ADMIN_EMAIL})
    if existing is None:
        await db.users.insert_one({
            "id": str(uuid.uuid4()),  # Phase 6 : UUID stable pour référence externe
            "email": ADMIN_EMAIL,
            "password_hash": hash_password(ADMIN_PASSWORD),
            "name": "Admin",
            "role": "admin",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        logger.info(f"Seeded admin user {ADMIN_EMAIL}")
    elif not verify_password(ADMIN_PASSWORD, existing["password_hash"]):
        await db.users.update_one(
            {"email": ADMIN_EMAIL},
            {"$set": {"password_hash": hash_password(ADMIN_PASSWORD)}},
        )
        logger.info(f"Updated admin password for {ADMIN_EMAIL}")

    # Seed demo Concepteur user (idempotent)
    CONCEPTEUR_EMAIL = os.environ.get("CONCEPTEUR_EMAIL", "concepteur@conceptfactory.fr")
    CONCEPTEUR_PASSWORD = os.environ.get("CONCEPTEUR_PASSWORD", "Concepteur2026!")
    existing_c = await db.users.find_one({"email": CONCEPTEUR_EMAIL})
    if existing_c is None:
        await db.users.insert_one({
            "id": str(uuid.uuid4()),  # Phase 6 : UUID stable pour référence externe
            "email": CONCEPTEUR_EMAIL,
            "password_hash": hash_password(CONCEPTEUR_PASSWORD),
            "name": "Marie Concepteur",
            "role": "operator",
            "status": "active",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        logger.info(f"Seeded Concepteur user {CONCEPTEUR_EMAIL}")
    elif not verify_password(CONCEPTEUR_PASSWORD, existing_c["password_hash"]):
        await db.users.update_one(
            {"email": CONCEPTEUR_EMAIL},
            {"$set": {"password_hash": hash_password(CONCEPTEUR_PASSWORD), "status": "active"}},
        )
        logger.info(f"Updated Concepteur password for {CONCEPTEUR_EMAIL}")

    # Phase 6 · Backfill UUID id sur users legacy (idempotent, non destructif).
    # Contexte : avant Phase 6, les users seedés n'avaient pas de champ "id" UUID.
    # Leur RBAC continue d'utiliser str(_id) via deps.serialize_user (inchangé pour
    # préserver la compat des sites existants qui ont operator_id = str(ObjectId)).
    # Ce UUID sert uniquement comme alias stable utilisable par les scripts externes.
    try:
        import uuid as _uuid
        backfill_cursor = db.users.find({"id": {"$exists": False}}, {"_id": 1, "email": 1})
        backfill_count = 0
        async for u in backfill_cursor:
            new_uuid = str(_uuid.uuid4())
            await db.users.update_one({"_id": u["_id"]}, {"$set": {"id": new_uuid}})
            backfill_count += 1
            logger.info(f"[phase6-backfill] user {u.get('email')} got uuid id={new_uuid}")
        if backfill_count:
            logger.info(f"[phase6-backfill] {backfill_count} user(s) got a stable UUID id")
    except Exception:
        logger.exception("[phase6-backfill] skipped due to error (non-blocking)")

    # ---------- Seed demo site (Phase 2) ---------- #
    try:
        from seed_demo_site import seed_demo_site_if_needed
        await seed_demo_site_if_needed(db, logger)
    except Exception as e:
        logger.warning(f"[SEED] demo site failed : {e}")

    # ---------- APScheduler : weekly debits + bi-monthly payouts ---------- #
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from apscheduler.triggers.cron import CronTrigger
        from routes.billing import _run_weekly_debits_inner, admin_payouts_preview, admin_run_payouts

        scheduler = AsyncIOScheduler(timezone="UTC")

        async def _scheduled_weekly_debits():
            logger.info("[scheduler] weekly debits start")
            try:
                result = await _run_weekly_debits_inner(7)
                logger.info(f"[scheduler] weekly debits done : {result}")
            except Exception:
                logger.exception("[scheduler] weekly debits failed")

        async def _scheduled_bimonthly_payouts_run():
            """Le 1er et 15 du mois à 03h UTC : calcule la preview + crée
            automatiquement les entrées 'payout pending' dans le ledger afin que
            l'Admin voie directement la liste des virements à effectuer."""
            logger.info("[scheduler] bimonthly payouts — auto generate pending entries")
            try:
                fake_admin = {"role": "admin", "id": "scheduler", "email": "system"}
                result = await admin_run_payouts(fake_admin)
                # Notification (toast) — stocke un log d'alerte pour l'admin
                from datetime import datetime as _dt, timezone as _tz
                await db.admin_notifications.insert_one({
                    "id": str(__import__("uuid").uuid4()),
                    "type": "payouts_ready",
                    "payouts_created": result.get("payouts_created", 0),
                    "total_eur": result.get("total_eur", 0),
                    "read": False,
                    "created_at": _dt.now(_tz.utc).isoformat(),
                })
                logger.info(f"[scheduler] bimonthly payouts : {result}")
            except Exception:
                logger.exception("[scheduler] bimonthly payouts run failed")

        # Monday 03:00 UTC
        scheduler.add_job(
            _scheduled_weekly_debits,
            CronTrigger(day_of_week="mon", hour=3, minute=0),
            id="weekly_debits", replace_existing=True, misfire_grace_time=3600,
        )
        # 1st and 15th of every month at 03:00 UTC
        scheduler.add_job(
            _scheduled_bimonthly_payouts_run,
            CronTrigger(day="1,15", hour=3, minute=0),
            id="bimonthly_payouts", replace_existing=True, misfire_grace_time=3600,
        )

        # Daily 04:00 UTC — Review invitation dispatch (14 days post-delivery)
        async def _scheduled_reviews_check():
            try:
                from routes.reviews_hook import check_due_invitations
                result = await check_due_invitations()
                logger.info(f"[scheduler] reviews check : {result}")
            except Exception:
                logger.exception("[scheduler] reviews check failed")
        scheduler.add_job(
            _scheduled_reviews_check,
            CronTrigger(hour=4, minute=0),
            id="reviews_check_due", replace_existing=True, misfire_grace_time=3600,
        )

        # Daily 05:30 UTC — AliExpress tracking sync for all open order mappings
        async def _scheduled_ae_tracking_sync():
            try:
                from routes.aliexpress import sync_all_aliexpress_tracking
                result = await sync_all_aliexpress_tracking()
                logger.info(f"[scheduler] AliExpress tracking sync : {result}")
            except Exception:
                logger.exception("[scheduler] AliExpress tracking sync failed")
        scheduler.add_job(
            _scheduled_ae_tracking_sync,
            CronTrigger(hour=5, minute=30),
            id="ae_tracking_sync", replace_existing=True, misfire_grace_time=3600,
        )

        # Phase 2.7.4 — every 6 hours, proactively refresh the platform-level
        # AliExpress access_token. AE access tokens last 24h and refresh
        # tokens last only 48h ; with a 6h cycle we rotate the refresh token
        # 8× before it can ever expire, so the platform stays connected
        # forever without manual reconnect. If both tokens are dead, we drop
        # an admin_notification so a human can re-OAuth.
        async def _scheduled_ae_token_refresh():
            try:
                from routes.aliexpress import _refresh_access_token, _get_platform_settings
                pl = await _get_platform_settings()
                if not pl.get("refresh_token"):
                    logger.info("[scheduler] AE token refresh skipped (no refresh_token)")
                    return
                resp = await _refresh_access_token()
                logger.info(
                    f"[scheduler] AE token refreshed OK — new expires_in={resp.get('expires_in')}s "
                    f"refresh_expires_in={resp.get('refresh_expires_in')}s"
                )
            except Exception as e:
                msg = str(e)[:200]
                logger.error(f"[scheduler] AE token refresh FAILED : {msg}")
                # Drop a single admin notification (idempotent on the day)
                try:
                    from datetime import datetime as _dt, timezone as _tz
                    today = _dt.now(_tz.utc).date().isoformat()
                    notif_id = f"ae-reconnect-needed-{today}"
                    await db.admin_notifications.update_one(
                        {"id": notif_id},
                        {"$set": {
                            "id": notif_id,
                            "kind": "ae_reconnect_needed",
                            "severity": "warning",
                            "title": "AliExpress nécessite un reconnect manuel",
                            "body": ("Le refresh proactif a échoué. Le refresh_token AE est "
                                     "probablement mort. Allez dans Admin → Intégrations → "
                                     f"Reconnecter AliExpress. Détail : {msg}"),
                            "created_at": _dt.now(_tz.utc).isoformat(),
                            "read": False,
                        }},
                        upsert=True,
                    )
                except Exception:
                    logger.exception("[scheduler] failed to write ae_reconnect_needed notif")
        scheduler.add_job(
            _scheduled_ae_token_refresh,
            CronTrigger(hour="*/6", minute=37),
            id="ae_token_refresh_h6", replace_existing=True, misfire_grace_time=3600,
        )

        # Every 2h — CJ Dropshipping tracking sync (faster than AE because CJ updates
        # statuses more granularly; keeps customer-facing tracking fresh).
        async def _scheduled_cj_tracking_sync():
            try:
                from routes.sourcing import sync_all_cj_tracking
                result = await sync_all_cj_tracking()
                logger.info(f"[scheduler] CJ tracking sync : {result}")
            except Exception:
                logger.exception("[scheduler] CJ tracking sync failed")
        scheduler.add_job(
            _scheduled_cj_tracking_sync,
            CronTrigger(hour="*/2", minute=15),
            id="cj_tracking_sync", replace_existing=True, misfire_grace_time=1800,
        )

        # Every 5 min — auto-resume des launch_jobs failed+resumable=true
        # (Phase 0 résilience LLM). Tente une seule reprise par job dans
        # les 30 min qui suivent l'échec, et seulement si le breaker Claude
        # est revenu CLOSED ou HALF_OPEN.
        async def _scheduled_auto_resume_launch_jobs():
            try:
                from routes.launch import auto_resume_failed_jobs
                await auto_resume_failed_jobs()
            except Exception:
                logger.exception("[scheduler] auto_resume_launch_jobs failed")

        scheduler.add_job(
            _scheduled_auto_resume_launch_jobs,
            CronTrigger(minute="*/5"),
            id="auto_resume_launch_jobs", replace_existing=True, misfire_grace_time=120,
        )

        # Monday 05:00 UTC — Scan opportunités Google (détection spikes)
        async def _scheduled_opportunity_scan():
            logger.info("[scheduler] opportunity scan start")
            try:
                from routes.opportunity import scan_opportunities
                result = await scan_opportunities()
                logger.info(f"[scheduler] opportunity scan done : {result}")
            except Exception:
                logger.exception("[scheduler] opportunity scan failed")

        scheduler.add_job(
            _scheduled_opportunity_scan,
            CronTrigger(day_of_week="mon", hour=5, minute=0),
            id="opportunity_scan", replace_existing=True, misfire_grace_time=3600,
        )

        # Every 5 min — Auto-config DNS pour les domaines 'purchased'
        scheduler.add_job(
            try_auto_configure_dns,
            "interval", minutes=5,
            id="dns_auto_config", replace_existing=True, misfire_grace_time=300,
        )

        # ==================================================================
        #  Phase 6 — Automatisations SEO/AEO agressives (remplace blog mensuel)
        # ==================================================================
        from routes.seo_automation import (
            run_blog_auto_batch, run_emerging_keywords_scan,
            run_content_refresh_monthly, run_internal_linking_weekly,
            run_gsc_position_alerts, run_paa_faq_enrichment,
            run_content_gap_monthly, run_sitemap_republish_ondemand,
            run_seo_weekly_report, ensure_seo_automation_indexes,
        )
        # Indexes Phase 6 (idempotent)
        await ensure_seo_automation_indexes()
        # Indexes Phase 7 (idempotent)
        from routes.google_ads_manual import ensure_gads_manual_indexes
        await ensure_gads_manual_indexes()
        # Indexes Phase 8 — Upsells AI suggestions (idempotent)
        from routes.upsells_ai import ensure_indexes as ensure_upsells_ai_indexes
        await ensure_upsells_ai_indexes()

        async def _wrap_cron(fn, name: str):
            logger.info(f"[scheduler] {name} start")
            try:
                r = await fn()
                logger.info(f"[scheduler] {name} : {r}")
            except Exception:
                logger.exception(f"[scheduler] {name} failed")

        # (1) Blog auto 3x/semaine — Mon/Wed/Fri 06:00 UTC
        scheduler.add_job(
            lambda: _wrap_cron(run_blog_auto_batch, "blog_auto_weekly_batch"),
            CronTrigger(day_of_week="mon,wed,fri", hour=6, minute=0),
            id="blog_auto_weekly_batch", replace_existing=True, misfire_grace_time=7200,
        )
        # (2) Emerging keywords — Mon 07:00 UTC
        scheduler.add_job(
            lambda: _wrap_cron(run_emerging_keywords_scan, "emerging_keywords_scan"),
            CronTrigger(day_of_week="mon", hour=7, minute=0),
            id="emerging_keywords_scan", replace_existing=True, misfire_grace_time=3600,
        )
        # (3) Content refresh — 1st of month 08:00 UTC
        scheduler.add_job(
            lambda: _wrap_cron(run_content_refresh_monthly, "content_refresh_monthly"),
            CronTrigger(day=1, hour=8, minute=0),
            id="content_refresh_monthly", replace_existing=True, misfire_grace_time=7200,
        )
        # (4) Internal linking — Tue 09:00 UTC
        scheduler.add_job(
            lambda: _wrap_cron(run_internal_linking_weekly, "internal_linking_weekly"),
            CronTrigger(day_of_week="tue", hour=9, minute=0),
            id="internal_linking_weekly", replace_existing=True, misfire_grace_time=3600,
        )
        # (5) GSC position alerts — Daily 09:00 UTC
        scheduler.add_job(
            lambda: _wrap_cron(run_gsc_position_alerts, "gsc_position_alerts_daily"),
            CronTrigger(hour=9, minute=0),
            id="gsc_position_alerts_daily", replace_existing=True, misfire_grace_time=3600,
        )
        # (6) PAA / FAQ enrichment — Thu 10:00 UTC
        scheduler.add_job(
            lambda: _wrap_cron(run_paa_faq_enrichment, "paa_faq_enrichment_weekly"),
            CronTrigger(day_of_week="thu", hour=10, minute=0),
            id="paa_faq_enrichment_weekly", replace_existing=True, misfire_grace_time=7200,
        )
        # (7) Content gap — 15th of month 11:00 UTC
        scheduler.add_job(
            lambda: _wrap_cron(run_content_gap_monthly, "content_gap_monthly"),
            CronTrigger(day=15, hour=11, minute=0),
            id="content_gap_monthly", replace_existing=True, misfire_grace_time=7200,
        )
        # (8) Sitemap republish on-demand — every 10 min
        scheduler.add_job(
            lambda: _wrap_cron(run_sitemap_republish_ondemand, "sitemap_republish_ondemand"),
            "interval", minutes=10,
            id="sitemap_republish_ondemand", replace_existing=True, misfire_grace_time=600,
        )
        # (9) SEO weekly report — Sun 20:00 UTC
        scheduler.add_job(
            lambda: _wrap_cron(run_seo_weekly_report, "seo_weekly_report"),
            CronTrigger(day_of_week="sun", hour=20, minute=0),
            id="seo_weekly_report", replace_existing=True, misfire_grace_time=3600,
        )

        # ==================================================================
        #  Phase A2 + B6 + B7 + E' — Mission Finalisation Altiaro
        # ==================================================================
        # Indexes for new collections (idempotent)
        try:
            await db.blog_jobs.create_index([("status", 1), ("created_at", 1)])
            await db.blog_jobs.create_index([("site_id", 1), ("created_at", -1)])
            await db.keyword_universe.create_index([("site_id", 1), ("locale", 1), ("keyword", 1)], unique=True)
            await db.keyword_universe.create_index([("site_id", 1), ("pillar_id", 1)])
            await db.keyword_clusters.create_index([("site_id", 1), ("locale", 1)])
            await db.landing_pages.create_index([("site_id", 1), ("slug", 1)])
            await db.landing_pages.create_index([("cluster_id", 1)])
            await db.aeo_pages.create_index([("site_id", 1), ("slug", 1)])
        except Exception:
            logger.exception("[startup] indexes blog_jobs/keyword_universe failed")

        # Phase A2 — Worker blog : tick toutes les 30 s
        from services.blog_worker import tick as _blog_worker_tick

        async def _scheduled_blog_worker():
            try:
                await _blog_worker_tick()
            except Exception:
                logger.exception("[scheduler] blog_worker tick failed")

        scheduler.add_job(
            _scheduled_blog_worker,
            "interval", seconds=30,
            id="blog_worker_tick", replace_existing=True, misfire_grace_time=60,
        )

        # Phase B6 — Génération automatique de landing pages (limitée par budget)
        async def _scheduled_landings_daily():
            try:
                from routes.seo_factory import generate_landings, LandingsInput
                limit_per_site = int(os.environ.get("LANDINGS_PER_DAY_PER_SITE", "5"))
                if limit_per_site <= 0:
                    return
                # Itère sur les sites validés/lives
                async for s in db.sites.find(
                    {"status": {"$in": ["live", "validated"]}},
                    {"_id": 0, "id": 1, "operator_id": 1, "available_langs": 1},
                ):
                    site_id = s["id"]
                    langs = s.get("available_langs") or ["fr"]
                    primary = langs[0] if langs else "fr"
                    locale = {"fr": "fr-FR", "en": "en-GB", "de": "de-DE",
                              "nl": "nl-NL", "it": "it-IT", "es": "es-ES"}.get(primary, "fr-FR")
                    fake_admin = {"role": "admin", "id": "scheduler"}
                    try:
                        await generate_landings(
                            site_id,
                            LandingsInput(locale=locale, max_landings=limit_per_site),
                            user=fake_admin,
                        )
                    except Exception:
                        logger.exception(f"[landings_daily] site={site_id[:8]} crashed")
            except Exception:
                logger.exception("[scheduler] landings_daily failed")

        scheduler.add_job(
            _scheduled_landings_daily,
            CronTrigger(hour=2, minute=30),
            id="landing_pages_generation_daily", replace_existing=True, misfire_grace_time=3600,
        )

        # Phase B4 — IndexNow daily resync à 1h00
        async def _scheduled_indexnow_daily_resync():
            try:
                from routes.indexnow import notify_indexnow
                async for s in db.sites.find(
                    {"status": "live"},
                    {"_id": 0, "id": 1, "public_url": 1, "custom_domain": 1},
                ):
                    base = s.get("public_url") or s.get("custom_domain") or ""
                    if not base:
                        continue
                    if not base.startswith("http"):
                        base = f"https://{base}"
                    try:
                        await notify_indexnow([base, f"{base}/sitemap.xml", f"{base}/blog"])
                        await db.sites.update_one(
                            {"id": s["id"]},
                            {"$set": {"last_indexnow_at": datetime.now(timezone.utc).isoformat()}},
                        )
                    except Exception:
                        logger.exception(f"[indexnow_daily] site {s['id'][:8]} failed")
            except Exception:
                logger.exception("[scheduler] indexnow_daily_resync failed")

        scheduler.add_job(
            _scheduled_indexnow_daily_resync,
            CronTrigger(hour=1, minute=0),
            id="indexnow_daily_resync", replace_existing=True, misfire_grace_time=3600,
        )

        # Phase E' — Material consistency check hebdomadaire (samedi 12h UTC)
        async def _scheduled_material_consistency_check():
            try:
                from scripts.purge_material_consistency import scan_all_sites
                result = await scan_all_sites(apply=False)
                logger.info(f"[scheduler] material_consistency_check : {result}")
            except Exception:
                logger.exception("[scheduler] material_consistency_check failed")

        scheduler.add_job(
            _scheduled_material_consistency_check,
            CronTrigger(day_of_week="sat", hour=12, minute=0),
            id="material_consistency_check_weekly", replace_existing=True, misfire_grace_time=7200,
        )

        # Every Monday at 08:00 UTC (09h CET) — Coach SEO weekly digest email
        async def _scheduled_weekly_seo_coach():
            logger.info("[scheduler] weekly SEO coach digest run start")
            try:
                from routes.seo_coach import send_weekly_seo_digests
                result = await send_weekly_seo_digests()
                logger.info(f"[scheduler] weekly SEO coach : {result}")
            except Exception:
                logger.exception("[scheduler] weekly SEO coach failed")

        scheduler.add_job(
            _scheduled_weekly_seo_coach,
            CronTrigger(day_of_week="mon", hour=8, minute=0),
            id="weekly_seo_coach", replace_existing=True, misfire_grace_time=3600,
        )

        # Every Thursday at 08:00 UTC (09h CET) — AI Citation Tracker run
        async def _scheduled_citation_tracker():
            logger.info("[scheduler] citation tracker weekly run start")
            try:
                result = await _run_citation_tracker_all_sites(logger)
                logger.info(f"[scheduler] citation tracker : {result}")
            except Exception:
                logger.exception("[scheduler] citation tracker failed")

        scheduler.add_job(
            _scheduled_citation_tracker,
            CronTrigger(day_of_week="thu", hour=8, minute=0),
            id="citation_tracker_weekly", replace_existing=True, misfire_grace_time=3600,
        )

        # Every Tuesday at 06:00 UTC — AliExpress Deals Watcher
        async def _scheduled_ae_deals_watch():
            logger.info("[scheduler] AliExpress deals watch start")
            try:
                from routes.ae_deals_watcher import scan_all_sites
                result = await scan_all_sites()
                logger.info(f"[scheduler] AliExpress deals : {result}")
            except Exception:
                logger.exception("[scheduler] AliExpress deals failed")

        scheduler.add_job(
            _scheduled_ae_deals_watch,
            CronTrigger(day_of_week="tue", hour=6, minute=0),
            id="ae_deals_watch", replace_existing=True, misfire_grace_time=3600,
        )

        # Daily 04:00 UTC — Google Merchant Center full re-sync
        # Skip silencieux si pas connecté (voir routes.merchant.daily_merchant_sync)
        async def _scheduled_merchant_daily_sync():
            logger.info("[scheduler] merchant daily sync start")
            try:
                from routes.merchant import daily_merchant_sync
                await daily_merchant_sync()
                logger.info("[scheduler] merchant daily sync done")
            except Exception:
                logger.exception("[scheduler] merchant daily sync failed")

        scheduler.add_job(
            _scheduled_merchant_daily_sync,
            CronTrigger(hour=4, minute=0),
            id="merchant_daily_sync", replace_existing=True, misfire_grace_time=3600,
        )

        scheduler.start()
        app.state.scheduler = scheduler
        logger.info(
            "APScheduler started : 24 jobs · weekly_debits · bimonthly_payouts · "
            "reviews_check_due · ae_tracking_sync · cj_tracking_sync (2h) · "
            "opportunity_scan · dns_auto_config (5min) · "
            "weekly_seo_coach · citation_tracker_weekly · ae_deals_watch · "
            "merchant_daily_sync · [Phase 6] blog_auto_weekly_batch (Mon/Wed/Fri) · "
            "emerging_keywords_scan · content_refresh_monthly · internal_linking_weekly · "
            "gsc_position_alerts_daily · paa_faq_enrichment_weekly · content_gap_monthly · "
            "sitemap_republish_ondemand (10min) · seo_weekly_report · "
            "[Mission Final] blog_worker_tick (30s) · landing_pages_generation_daily · "
            "indexnow_daily_resync · material_consistency_check_weekly"
        )
    except Exception:
        logger.exception("Failed to start APScheduler")


async def try_auto_configure_dns() -> dict:
    """Scanne les domaines en statut 'purchased' et déclenche le provisioning
    Approximated + OVH DNS automatiquement.

    Appelé par APScheduler toutes les 5 min. Idempotent : si la zone OVH n'est
    pas encore créée (~10 min post-achat), l'erreur ResourceNotFoundError est
    ignorée et on retentera au cycle suivant. Après 30 min d'échec, bascule en
    `dns_auto_failed` (intervention manuelle requise).

    2026-05-01 : bascule vers Approximated. Pour chaque domaine acheté, on
    appelle `site_domain._provision_approximated(site_id, domain)` qui :
      1. crée le vhost Approximated (idempotent)
      2. pousse les A records OVH vers les cluster IPs Approximated
      3. refresh la zone OVH
      4. lance un poller 60s × 15 min qui flip `custom_domain_verified=true`
         dès que apx_hit && is_resolving && has_ssl
    """
    from datetime import datetime, timedelta, timezone
    from deps import db

    now = datetime.now(timezone.utc)
    cutoff = (now - timedelta(minutes=30)).isoformat()
    pending = await db.domains.find(
        {"status": "purchased"}, {"_id": 0, "domain": 1, "site_id": 1,
                                    "ovh_purchased_at": 1, "purchased_by": 1}
    ).to_list(50)
    configured, retrying, failed = [], [], []

    if not pending:
        return {"configured": [], "retrying": [], "failed": []}

    from routes.site_domain import _provision_approximated
    from services import approximated_provisioning as apx
    from services import ovh_dns

    if not apx.is_configured():
        logger.warning("[dns-auto] Approximated not configured — skipping cycle")
        return {"configured": [], "retrying": [], "failed": [],
                "skipped": "APPROXIMATED_API_KEY missing"}

    import ovh  # for exception class

    for d in pending:
        domain = d.get("domain")
        site_id = d.get("site_id")
        if not domain or not site_id:
            continue
        try:
            # Make sure the OVH zone actually exists — otherwise skip until next cycle.
            try:
                if ovh_dns.is_configured():
                    await ovh_dns.list_records(domain)  # 404 if zone not yet created
            except ovh.exceptions.ResourceNotFoundError:
                if (d.get("ovh_purchased_at") or "") < cutoff:
                    await db.domains.update_one(
                        {"domain": domain},
                        {"$set": {"status": "dns_auto_failed",
                                  "dns_error": "Zone OVH non créée après 30 min"}},
                    )
                    failed.append(domain)
                else:
                    retrying.append(domain)
                continue

            # Main path : Approximated vhost + OVH DNS push + poller.
            await db.sites.update_one(
                {"id": site_id},
                {"$set": {"custom_domain": domain}},
            )
            report = await _provision_approximated(site_id, domain)
            await db.domains.update_one(
                {"domain": domain},
                {"$set": {"status": "dns_configured",
                          "dns_configured_at": now.isoformat(),
                          "dns_auto": True,
                          "dns_provisioning_report": report}},
            )
            await db.sites.update_one(
                {"domain": domain},
                {"$set": {"domain_status": "active",
                          "updated_at": now.isoformat()}},
            )
            configured.append(domain)

            # Notify the concepteur by email (best-effort)
            try:
                from routes.emails import (
                    _build_domain_email_html,
                    send_email_via_resend,
                    RESEND_OWNER_EMAIL,
                )
                site = await db.sites.find_one({"id": site_id}, {"_id": 0})
                user = await db.users.find_one({"id": d.get("purchased_by")}, {"_id": 0})
                recipient = (user or {}).get("email") or RESEND_OWNER_EMAIL
                if recipient and site:
                    body = (
                        f"""<div style="background:#D1FAE5;border:1px solid #A7F3D0;"""
                        f"""border-radius:8px;padding:14px 16px;margin:16px 0;">"""
                        f"""<div style="font-size:13px;color:#065F46;line-height:1.5;">"""
                        f"""🌍 <strong>Ton site est en ligne sur {domain} !</strong><br>"""
                        f"""Le certificat SSL est émis automatiquement (1-2 min)."""
                        f"""</div></div>"""
                    )
                    html = await _build_domain_email_html(
                        domain=domain, site=site,
                        title=f"🌍 {domain} est vivant !",
                        intro=(f"Bonne nouvelle : DNS + SSL configurés automatiquement "
                               f"pour <strong>{site.get('name','')}</strong>."),
                        body_html=body, cta_label="Voir mon site",
                        cta_url=f"https://{domain}",
                        preheader="Ton domaine est actif",
                    )
                    await send_email_via_resend(
                        to=recipient,
                        subject=f"🌍 {domain} est en ligne",
                        html=html, site=site, tags=["domain_live"],
                    )
            except Exception:
                logger.exception("domain_live email failed")
        except Exception as e:
            logger.exception(f"auto-config DNS failed for {domain}")
            failed.append(f"{domain}:{str(e)[:60]}")

    if configured or retrying or failed:
        logger.info(
            f"[dns-auto] configured={configured} retrying={retrying} failed={failed}"
        )
    return {"configured": configured, "retrying": retrying, "failed": failed}


@app.on_event("shutdown")
async def shutdown():
    try:
        scheduler = getattr(app.state, "scheduler", None)
        if scheduler and scheduler.running:
            scheduler.shutdown(wait=False)
    except Exception:
        logger.exception("Failed to stop scheduler")
    client.close()


app.include_router(api)
app.mount("/api/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

# CORS
cors_origins_env = os.environ.get("CORS_ORIGINS", "")
cors_origins = [o.strip() for o in cors_origins_env.split(",") if o.strip()]

# Custom-domain host routing (altea-home.com & co → /shop/{site_id}/…)
# Monté avant CORS pour que la réécriture de path se fasse au plus tôt.
from custom_domain_middleware import custom_domain_rewrite  # noqa: E402
app.middleware("http")(custom_domain_rewrite)

# Wildcard mode with credentials: use allow_origin_regex to echo request origin
# (Starlette refuses to send ACAO:<origin> when allow_origins=["*"] and credentials=True,
# and browsers reject ACAO:* with credentials. The regex form sidesteps both issues.)
if cors_origins == ["*"] or not cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=".*",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
