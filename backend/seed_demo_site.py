"""
Seed demo site — Phase 2 (option simple, inline au boot backend).

Crée un site "Démo Altiaro" + 3 produits + design minimal si :
  - env RUN_SEED_DEMO=true
  - ET aucun site avec slug `demo-altiaro` n'existe déjà (idempotent)

Appelé depuis server.py @app.on_event("startup") après les seeds users.
"""
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

from seed_niches import NICHES


DEMO_SLUG = "demo-altiaro"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _demo_products(site_id: str) -> list:
    now = _now_iso()
    base = [
        ("Enfile-bas confort Premium", 19.90, "https://picsum.photos/seed/altiaro-demo-1/600/600"),
        ("Enfile-bas Pro inox renforcé", 29.90, "https://picsum.photos/seed/altiaro-demo-2/600/600"),
        ("Kit 2-en-1 enfile-bas + chausse-pied", 39.90, "https://picsum.photos/seed/altiaro-demo-3/600/600"),
    ]
    products = []
    for idx, (title_fr, price, image) in enumerate(base, start=1):
        products.append({
            "id": str(uuid.uuid4()),
            "site_id": site_id,
            "name": {"fr": title_fr, "en": "", "de": "", "nl": ""},
            "description": {
                "fr": f"Produit démo #{idx} — données factices pour tests UX. Fiche complète à rédiger.",
                "en": "", "de": "", "nl": "",
            },
            "price": price,
            "cost_price_ht": round(price * 0.18, 2),  # marge fictive ~80%
            "vat_rate": None,
            "compare_at_price": round(price * 1.4, 2),
            "currency": "EUR",
            "images": [image],
            "stock": None,
            "supplier_url": "",
            "sku": f"DEMO-{idx:03d}",
            "status": "active",
            "featured": idx == 1,
            "category": "",
            "tags": ["demo"],
            "bundles_with": [],
            "created_at": now,
            "updated_at": now,
            "created_by": "seed-script",
        })
    return products


def _demo_design(site_id: str, site_name: str) -> dict:
    """Minimal design doc (stored inline in sites.design).

    Only fields needed at boot time — About/FAQ/Contact/Livraison/Retours body
    vide : ils seront remplis soit via legal_templates.render_legal, soit via
    l'endpoint `POST /sites/:id/design/generate-pages` (Claude).
    """
    from altiaro_legal import (
        render_mentions_legales,
        render_cgu,
        render_confidentialite,
        render_cookies,
    )
    now = _now_iso()
    return {
        "updated_at": now,
        "template_mode": "monochrome",
        "published": False,
        "brand": {
            "name": site_name,
            "baseline": "L'aide au quotidien qui change la vie",
            "logo_url": None,
            "primary_color": "#B84B31",
            "secondary_color": "#E9C46A",
            "bg_color": "#FAF7F2",
            "text_color": "#1C1917",
            "accent_color": "#2A9D8F",
            "font_heading": "Fraunces",
            "font_body": "Inter",
        },
        "pages": {
            # Pages légales (templates déterministes)
            "mentions_legales": {"title": "Mentions légales", "body": render_mentions_legales(), "slug": "mentions"},
            "cgv": {"title": "Conditions générales de vente", "body": render_cgu(), "slug": "cgv"},
            "confidentialite": {"title": "Politique de confidentialité", "body": render_confidentialite(), "slug": "confidentialite"},
            "cookies": {"title": "Politique cookies", "body": render_cookies(), "slug": "cookies"},
            # Placeholders pour About/FAQ/Contact (à générer via /sites/:id/design/generate-pages)
            "about": {"title": "À propos", "body": "", "slug": "about"},
            "faq": {"title": "FAQ", "body": "", "slug": "faq", "items": []},
            "contact": {"title": "Contact", "body": "", "slug": "contact"},
            "livraison": {"title": "Livraison", "body": "", "slug": "livraison"},
            "retours": {"title": "Retours & remboursements", "body": "", "slug": "retours"},
        },
        "seeded_at": now,
        "seeded_demo": True,
    }


async def seed_demo_site_if_needed(db, logger) -> Optional[str]:
    """Idempotent : n'agit que si le flag env est on ET aucun site demo n'existe.

    Returns the created site_id or None.
    """
    if os.environ.get("RUN_SEED_DEMO", "").lower() not in ("true", "1", "yes"):
        return None

    # Skip if a site with slug demo-altiaro already exists
    existing = await db.sites.find_one({"slug": DEMO_SLUG})
    if existing:
        logger.info(f"[SEED] Demo site already exists: slug={DEMO_SLUG}, id={existing.get('id')}")
        return existing.get("id")

    # Find concepteur owner
    concepteur_email = os.environ.get("CONCEPTEUR_EMAIL", "concepteur@conceptfactory.fr")
    concepteur = await db.users.find_one({"email": concepteur_email})
    if not concepteur:
        logger.warning(f"[SEED] Cannot create demo site : concepteur user {concepteur_email} not found")
        return None

    owner_id = str(concepteur["_id"])  # user id = str(ObjectId), cf. deps.serialize_user
    first_niche = NICHES[0] if NICHES else None
    if not first_niche:
        logger.warning("[SEED] Cannot create demo site : no niche seeded yet")
        return None

    site_id = str(uuid.uuid4())
    now = _now_iso()
    site_doc = {
        "id": site_id,
        "name": "Démo Altiaro",
        "slug": DEMO_SLUG,
        "niche": first_niche["name"],
        "niche_slug": first_niche["slug"],
        "analysis_id": None,
        "selected_countries": ["FR"],
        "daily_budget_eur": 30,
        "domain": "",
        "shopify_url": "",
        "operator_id": owner_id,
        "notes": "Site démo auto-généré au boot (RUN_SEED_DEMO=true). Peut être supprimé sans risque.",
        "vat_rate": 0.20,
        "status": "draft",
        "created_at": now,
        "created_by": owner_id,
    }
    await db.sites.insert_one(site_doc)

    # Seed steps (journey)
    try:
        from seed_prompts import get_seed_steps_for_site
        steps = get_seed_steps_for_site(site_id)
        if steps:
            await db.steps.insert_many(steps)
    except Exception as e:
        logger.warning(f"[SEED] steps insert failed : {e}")

    # Seed 3 products
    products = _demo_products(site_id)
    await db.products.insert_many(products)

    # Seed minimal design + legal pages inline inside the site doc
    # (design is stored as a nested field in `sites`, not as a separate collection).
    design = _demo_design(site_id, site_doc["name"])
    await db.sites.update_one({"id": site_id}, {"$set": {"design": design}})

    logger.info(f"[SEED] Demo site created: id={site_id}, slug={DEMO_SLUG}, 3 products")
    return site_id
