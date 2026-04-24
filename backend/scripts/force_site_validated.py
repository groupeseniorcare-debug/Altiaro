"""
DEV helper — Force un site à l'état "all steps completed" pour permettre de
tester le Dashboard Analytics (Chantier 7) sans avoir à finir manuellement
les 9 étapes du cockpit.

⚠️  NE PAS utiliser en production. Bypass la logique métier.

Usage :
  python -m scripts.force_site_validated <site_id>
  python -m scripts.force_site_validated <site_id> --revert

Ce script injecte le minimum de data en DB pour que compute_step_statuses()
renvoie completed=True pour chaque checker. Le `--revert` supprime les flags
injectés (sauf ceux qui existaient légitimement).
"""
import argparse
import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))
load_dotenv(BACKEND_DIR / ".env")

from motor.motor_asyncio import AsyncIOMotorClient  # noqa: E402

MARKER = "__dev_force_validated__"


async def force(site_id: str, revert: bool) -> None:
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]

    site = await db.sites.find_one({"id": site_id}, {"_id": 0})
    if not site:
        print(f"ERROR: site_id {site_id} not found")
        return

    if revert:
        await db.sites.update_one(
            {"id": site_id},
            {"$unset": {MARKER: "", "design.financial_forecast": "", "design.qa": ""},
             "$set": {"status": "active"}},
        )
        # Retirer les 5 produits + upsells seedés
        await db.products.delete_many({"site_id": site_id, "_dev_seed": True})
        await db.quick_scans.delete_many({"site_id": site_id, "_dev_seed": True})
        # Ne PAS retirer design.pages / design.blog_posts — on ignore si
        # certains avaient été créés légitimement. Les flags injectés par dev
        # restent donc (idempotent : on peut re-appliquer).
        print(f"✓ Reverted {site_id} (status → active, dev-seed products removed)")
        return

    now = datetime.now(timezone.utc).isoformat()
    patches = {MARKER: True}

    # 1. pricing : design.pricing_analysis.generated_at
    design = site.get("design") or {}
    if not (design.get("pricing_analysis") or {}).get("generated_at"):
        patches["design.pricing_analysis"] = {
            "generated_at": now,
            "niche": site.get("niche") or "niche",
            "competitors": [{"name": f"Concurrent {i}"} for i in range(5)],
            "recommended_ranges": [{"label": "Gamme A", "min": 50, "max": 150}] * 3,
        }

    # 2. import : 5 produits minimum avec shipping_countries_supported
    pcount = await db.products.count_documents({"site_id": site_id, "status": "active"})
    if pcount < 5:
        to_create = 5 - pcount
        seo_cc = site.get("seo_countries") or ["FR", "BE", "LU", "CH", "DE", "AT", "UK", "IE", "NL", "IT", "ES"]
        for i in range(to_create):
            pid = f"dev-{uuid.uuid4().hex[:10]}"
            await db.products.insert_one({
                "id": pid,
                "site_id": site_id,
                "name": {"fr": f"Produit test {i + 1}"},
                "description": {"fr": "Produit factice pour tester le dashboard."},
                "price": 79 + i * 20,
                "status": "active",
                "image": None,
                "shipping_countries_supported": seo_cc,
                "category": "test",
                "_dev_seed": True,
                "created_at": now,
            })

    # 3. upsells : 3 produits avec is_upsell=True
    ucount = await db.products.count_documents({"site_id": site_id, "is_upsell": True})
    if ucount < 3:
        await db.products.update_many(
            {"site_id": site_id, "_dev_seed": True},
            {"$set": {"is_upsell": True}},
            # Limit via upstream — motor doesn't support limit on updates, workaround:
        )
        # Workaround : query 3 ids and bulk update (motor-safe)
        ids = await db.products.find(
            {"site_id": site_id, "_dev_seed": True},
            {"_id": 0, "id": 1},
        ).limit(3).to_list(3)
        if ids:
            await db.products.update_many(
                {"site_id": site_id, "id": {"$in": [d["id"] for d in ids]}},
                {"$set": {"is_upsell": True}},
            )

    # 4. forecast : site.design.financial_forecast.generated_at
    if not (design.get("financial_forecast") or {}).get("generated_at"):
        patches["design.financial_forecast"] = {
            "generated_at": now,
            "summary": {"monthly_revenue": 12500, "roas": 3.2, "break_even_month": 3},
        }

    # 5. branding : design.published=true
    if not design.get("published"):
        patches["design.published"] = True
        patches["design.brand"] = design.get("brand") or {
            "name": site.get("name"),
            "tagline": {"fr": "Tagline dev"},
        }

    # 6. pages : 4 pages légales + 3 éditoriales, toutes non-vides
    pages_in = design.get("pages") or {}
    required = ["mentions_legales", "cgv", "confidentialite", "cookies", "about", "faq", "contact"]
    if not all(pages_in.get(k) for k in required):
        filler = "Contenu factice pour validation cockpit — section remplie pour débloquer l'étape pages."
        patches["design.pages"] = {
            "mentions_legales": {"body": {"fr": filler}},
            "cgv":              {"body": {"fr": filler}},
            "confidentialite":  {"body": {"fr": filler}},
            "cookies":          {"body": {"fr": filler}},
            "about":            {"headline": {"fr": "À propos"}, "paragraphs": [{"fr": filler}]},
            "faq":              {"items": [{"q": "Question ?", "a": filler}]},
            "contact":          {"email": "contact@test.com", "body": {"fr": filler}},
        }

    # 7. content : 1 pillar + 3 satellites
    posts = design.get("blog_posts") or []
    pillar = any(p.get("type") == "pillar" for p in posts)
    satellites = sum(1 for p in posts if p.get("type") != "pillar")
    if not pillar or satellites < 3:
        new_posts = list(posts)
        if not pillar:
            new_posts.append({
                "id": str(uuid.uuid4()),
                "slug": "pillar-dev",
                "title": "Article pilier dev",
                "type": "pillar",
                "body": "# Pilier\n\nContenu factice pour validation cockpit étape 7.",
                "excerpt": "Pilier dev",
                "published_at": now[:10],
            })
        while sum(1 for p in new_posts if p.get("type") != "pillar") < 3:
            idx = sum(1 for p in new_posts if p.get("type") != "pillar") + 1
            new_posts.append({
                "id": str(uuid.uuid4()),
                "slug": f"satellite-dev-{idx}",
                "title": f"Article satellite {idx}",
                "type": "satellite",
                "body": f"Contenu satellite {idx}.",
                "excerpt": f"Satellite {idx}",
                "published_at": now[:10],
            })
        patches["design.blog_posts"] = new_posts

    # 8. seo : score ≥ 70 via design.seo_score
    if (design.get("seo_score") or 0) < 70:
        patches["design.seo_score"] = 85
        patches["design.seo_audit"] = {"score": 85, "updated_at": now}

    # 9. qa : status=approved → étape terminale validée par l'admin
    if (site.get("status") or "").lower() not in ("approved", "published", "live"):
        patches["status"] = "approved"
        patches["qa_audit"] = {
            "submitted": True,
            "submitted_at": now,
            "ready_for_submission": True,
            "score": 90,
        }

    await db.sites.update_one({"id": site_id}, {"$set": patches})
    print(f"✓ Bumped site {site_id} to all-completed state.")
    print("  Run /api/sites/{id}/journey to confirm `all_completed: true`.")
    print("  Run `python -m scripts.force_site_validated {id} --revert` to rollback.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("site_id")
    parser.add_argument("--revert", action="store_true")
    args = parser.parse_args()
    asyncio.run(force(args.site_id, args.revert))


if __name__ == "__main__":
    main()
