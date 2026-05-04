"""Phase 3.3 Bloc 3 — Reset SOFT du site pilote Altea.

Purge les 23 `db.blog_posts` structurellement cassés (lang=null, titres
allemands, pas de JSON-LD ni de translations) pour repartir propre avant le
run réel de `magic/content`.

CONSERVÉ :
    - products (9 principaux + 3 upsells + images IA)
    - custom_domain, custom_domain_verified, approximated SSL
    - design.brand, design.color_palette, design.hero, design.cms_pages
    - OAuth tokens (AliExpress, Google Master, GSC, GMC)
    - orders, customers, storefront_events

PURGÉ :
    - db.blog_posts du site Altea (collection)
    - design.blog_posts (array legacy éventuellement présent dans sites.design)
    - manual_step_overrides, seo_score, qa_status
    - launch_status, published_at, went_live_at → reset staging

Usage :
    # Dry-run (par défaut, aucune écriture)
    python3 -m scripts.reset_altea_soft

    # Vraie exécution
    python3 -m scripts.reset_altea_soft --execute
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from datetime import datetime, timezone

# Allow running as a standalone script from the backend/ directory.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from motor.motor_asyncio import AsyncIOMotorClient  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

ALTEA_ID = "6867223e-7ea5-45a7-815a-300cd89b7656"


async def main(execute: bool) -> int:
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[os.environ.get("DB_NAME", "altiaro_dev")]

    print(f"=== Altea soft-reset — mode = {'EXECUTE' if execute else 'DRY-RUN'} ===")
    site = await db.sites.find_one({"id": ALTEA_ID}, {"_id": 0, "name": 1, "status": 1,
                                                      "launch_status": 1, "qa_status": 1})
    if not site:
        print(f"❌ Site Altea {ALTEA_ID[:8]}… introuvable.")
        return 1
    print(f"Site trouvé : {site.get('name')}  ·  status={site.get('status')}  ·  launch={site.get('launch_status')}  ·  qa={site.get('qa_status')}")

    # --- Blog posts collection -------------------------------------------
    blog_n = await db.blog_posts.count_documents({"site_id": ALTEA_ID})
    print(f"\n[blog_posts] collection  : {blog_n} document(s) à supprimer")

    # --- Legacy inline blog array ----------------------------------------
    inline = await db.sites.find_one({"id": ALTEA_ID}, {"_id": 0, "design.blog_posts": 1})
    inline_n = len(((inline or {}).get("design") or {}).get("blog_posts") or [])
    print(f"[design.blog_posts] inline: {inline_n} entrée(s) legacy à purger")

    # --- Fields à remettre à zéro ----------------------------------------
    unset_fields = [
        "manual_step_overrides",
        "seo_score",
        "qa_status",
        "launch_status",
        "published_at",
        "went_live_at",
        "gmc_onboarded",
    ]
    print(f"[site fields] à unset    : {unset_fields}")
    print("[site.status] staging (forcé)")

    if not execute:
        print("\n✓ Dry-run terminé. Relance avec --execute pour appliquer.")
        return 0

    # --- Execute ---------------------------------------------------------
    now = datetime.now(timezone.utc).isoformat()

    res_blog = await db.blog_posts.delete_many({"site_id": ALTEA_ID})
    print(f"\n✓ db.blog_posts : {res_blog.deleted_count} supprimé(s)")

    await db.sites.update_one({"id": ALTEA_ID}, {
        "$set": {
            "status": "staging",
            "updated_at": now,
            "soft_reset_at": now,
            "design.blog_posts": [],
        },
        "$unset": {f: "" for f in unset_fields},
    })
    print("✓ sites.update  : status→staging + champs unset + design.blog_posts=[]")

    # Verify
    blog_after = await db.blog_posts.count_documents({"site_id": ALTEA_ID})
    site_after = await db.sites.find_one({"id": ALTEA_ID}, {"_id": 0, "status": 1,
                                                             "launch_status": 1, "qa_status": 1})
    print("\n=== État final ===")
    print(f"db.blog_posts              : {blog_after}")
    print(f"site.status                : {site_after.get('status')}")
    print(f"site.launch_status         : {site_after.get('launch_status')}")
    print(f"site.qa_status             : {site_after.get('qa_status')}")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Soft-reset Altea pour permettre un rerun propre de magic/content.")
    parser.add_argument("--execute", action="store_true",
                        help="Applique réellement les modifications (sinon dry-run).")
    args = parser.parse_args()
    sys.exit(asyncio.run(main(args.execute)))
