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

        # 1st of every month at 06:00 UTC — Blog cluster mensuel (1 pilier + 4 satellites)
        async def _scheduled_monthly_blog_cluster():
            logger.info("[scheduler] monthly blog cluster run start")
            try:
                from routes.blog_posts import run_monthly_clusters_for_all_sites
                result = await run_monthly_clusters_for_all_sites()
                logger.info(f"[scheduler] monthly blog cluster : {result}")
            except Exception:
                logger.exception("[scheduler] monthly blog cluster failed")

        scheduler.add_job(
            _scheduled_monthly_blog_cluster,
            CronTrigger(day=1, hour=6, minute=0),
            id="monthly_blog_cluster", replace_existing=True, misfire_grace_time=7200,
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
            "APScheduler started : 12 jobs · weekly_debits · bimonthly_payouts · "
            "reviews_check_due · ae_tracking_sync · cj_tracking_sync (2h) · "
            "opportunity_scan · dns_auto_config (5min) · monthly_blog_cluster · "
            "weekly_seo_coach · citation_tracker_weekly · ae_deals_watch · "
            "merchant_daily_sync (04h UTC)"
        )
    except Exception:
        logger.exception("Failed to start APScheduler")


async def try_auto_configure_dns() -> dict:
    """Scanne les domaines en statut 'purchased' et tente la config DNS automatiquement.

    Appelé par APScheduler toutes les 5 min. Idempotent : si la zone OVH n'est pas
    encore créée (~10 min post-achat), l'erreur ResourceNotFoundError est ignorée
    et on retentera au cycle suivant. Après 30 min d'échec, bascule en
    `dns_auto_failed` (intervention manuelle requise).
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

    for d in pending:
        domain = d.get("domain")
        if not domain:
            continue
        try:
            import asyncio as _aio
            from routes.ovh_domains import _client, PLATFORM_IP
            import ovh
            if not PLATFORM_IP:
                break
            client = _client()
            try:
                await _aio.to_thread(
                    client.post, f"/domain/zone/{domain}/record",
                    fieldType="A", subDomain="", target=PLATFORM_IP, ttl=300,
                )
                try:
                    await _aio.to_thread(
                        client.post, f"/domain/zone/{domain}/record",
                        fieldType="CNAME", subDomain="www", target=f"{domain}.", ttl=300,
                    )
                except Exception:
                    pass
                await _aio.to_thread(client.post, f"/domain/zone/{domain}/refresh")
                await db.domains.update_one(
                    {"domain": domain},
                    {"$set": {"status": "dns_configured",
                              "dns_configured_at": now.isoformat(),
                              "dns_auto": True}},
                )
                await db.sites.update_one(
                    {"domain": domain},
                    {"$set": {"domain_status": "active", "updated_at": now.isoformat()}},
                )
                configured.append(domain)
                try:
                    from routes.emails import _build_domain_email_html, send_email_via_resend, RESEND_OWNER_EMAIL
                    site = await db.sites.find_one({"id": d.get("site_id")}, {"_id": 0})
                    user = await db.users.find_one({"id": d.get("purchased_by")}, {"_id": 0})
                    recipient = (user or {}).get("email") or RESEND_OWNER_EMAIL
                    if recipient and site:
                        body = f"""<div style="background:#D1FAE5;border:1px solid #A7F3D0;border-radius:8px;padding:14px 16px;margin:16px 0;"><div style="font-size:13px;color:#065F46;line-height:1.5;">🌍 <strong>Ton site est en ligne sur {domain} !</strong><br>La propagation DNS peut prendre 5 à 30 min supplémentaires avant d'être visible partout. Tu peux tester dès maintenant.</div></div>"""
                        html = await _build_domain_email_html(
                            domain=domain, site=site,
                            title=f"🌍 {domain} est vivant !",
                            intro=f"Bonne nouvelle : la zone DNS vient d'être configurée automatiquement pour <strong>{site.get('name','')}</strong>.",
                            body_html=body, cta_label="Voir mon site",
                            cta_url=f"https://{domain}",
                            preheader="Ton domaine est actif",
                        )
                        await send_email_via_resend(to=recipient, subject=f"🌍 {domain} est en ligne", html=html, site=site, tags=["domain_live"])
                except Exception:
                    logger.exception("domain_live email failed")
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
