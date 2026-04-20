"""
Concept Factory — FastAPI orchestrator.
Monte les routers modulaires définis dans /app/backend/routes/.
"""
import os
import logging
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

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
from routes import analyzer as analyzer_routes
from routes import ads_copy as ads_copy_routes
from routes import duplicate as duplicate_routes
from routes import domain as domain_routes

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("conceptfactory")

app = FastAPI(title="Concept Factory API")
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
api.include_router(niches_routes.router)
api.include_router(dashboard_routes.router)
api.include_router(meta_routes.router)
api.include_router(uploads_routes.router)
api.include_router(search_routes.router)


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

    # Seed niche catalog (idempotent)
    try:
        seeded = await seed_niches(db)
        logger.info(f"Seeded {seeded} niches in catalog")
    except Exception:
        logger.exception("Failed to seed niches catalog")

    # Backfill block info on existing steps (idempotent migration)
    try:
        missing_block = await db.steps.count_documents({"block": {"$exists": False}})
        if missing_block > 0:
            logger.info(f"Backfilling block info on {missing_block} steps...")
            for phase_code, block_id in PHASE_TO_BLOCK.items():
                meta = BLOCKS[block_id]
                await db.steps.update_many(
                    {"phase": phase_code, "block": {"$exists": False}},
                    {"$set": {
                        "block": block_id,
                        "block_name": meta["name"],
                        "block_order": meta["order"],
                        "block_emoji": meta["emoji"],
                    }},
                )
            logger.info("Block backfill complete.")
    except Exception:
        logger.exception("Failed block backfill migration")

    # Seed admin user
    existing = await db.users.find_one({"email": ADMIN_EMAIL})
    if existing is None:
        await db.users.insert_one({
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


@app.on_event("shutdown")
async def shutdown():
    client.close()


app.include_router(api)
app.mount("/api/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

# CORS
cors_origins_env = os.environ.get("CORS_ORIGINS", "")
cors_origins = [o.strip() for o in cors_origins_env.split(",") if o.strip()]
if not cors_origins:
    cors_origins = [FRONTEND_URL]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
