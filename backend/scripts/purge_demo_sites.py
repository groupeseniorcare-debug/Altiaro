"""
Purge totale des 3 sites de démo + leurs données dérivées + uploads scopés.

Préserve : users, niches, countries, platform_settings, google_ads_credentials,
aliexpress_oauth_callbacks, gsc_oauth_states, email_log, resend_dns_operations,
billing_profiles, login_attempts.

Usage :
  cd /app/backend
  python -m scripts.purge_demo_sites             # purge les 3 sites de démo connus
  python -m scripts.purge_demo_sites <site_id>   # purge un site précis
  python -m scripts.purge_demo_sites --all       # purge TOUS les sites (et tout leur contenu lié)
"""
import argparse
import asyncio
import os
import shutil
import sys
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))
load_dotenv(BACKEND_DIR / ".env")

from motor.motor_asyncio import AsyncIOMotorClient  # noqa: E402

# Collections où chaque doc a un champ site_id à supprimer
SCOPED_COLLECTIONS = [
    "products",
    "storefront_events",
    "orders",
    "blog_posts",
    "steps",
    "quick_scans",
    "quick_scan_groups",
    "emerging_keywords",
    "content_gaps",
    "seo_weekly_reports",
    "seo_automation_log",
    "ledger",
    "google_ads_exports",
    "google_ads_oauth_state",
    "ae_deals_history",
    "admin_notifications",
    "ads_copy",
    "block_outputs",
    "designs",
    "financials",
    "leads",
    "domains",
    "gsc_oauth_states",  # retraité plus bas (peut être global)
    "merchant_oauth_states",
    "review_invitations",
    "site_seo_alerts",
    "site_seo_history",
    "ae_deals_dismissed",
    "site_seo_audit",
]

# Collections globales préservées (ne JAMAIS toucher même si elles ont un site_id)
PRESERVED_COLLECTIONS = {
    "users", "niches", "countries", "platform_settings",
    "google_ads_credentials", "aliexpress_oauth_callbacks",
    "email_log", "resend_dns_operations", "billing_profiles",
    "login_attempts", "platform_health",
    "copilot_messages",  # scoped user, pas site
    "niche_analyses",    # scoped user, pas site
}

DEFAULT_DEMO_SITES = [
    "cc58f41b-285b-4007-8cb2-06b50d3baff6",  # Démo Altiaro
    "d33a5795-7a19-4a03-86a2-ef83ea19db9b",  # Projet Fauteuil releveur
]


async def collect_related_uuids(db, site_ids: list[str]) -> set[str]:
    """Récupère tous les UUIDs liés aux sites (design_id, product_id, etc.)
    pour pouvoir nettoyer les uploads dont le filename embedde un de ces UUIDs."""
    uuids: set[str] = set(site_ids)
    # design.id de chaque site
    async for s in db.sites.find({"id": {"$in": site_ids}}, {"_id": 0, "id": 1, "design": 1}):
        d = s.get("design") or {}
        if isinstance(d, dict) and d.get("id"):
            uuids.add(str(d["id"]))
    # product ids de chaque site
    async for p in db.products.find({"site_id": {"$in": site_ids}}, {"_id": 0, "id": 1}):
        if p.get("id"):
            uuids.add(str(p["id"]))
    return uuids


async def purge_site(db, site_id: str, dry_run: bool = False) -> dict:
    deleted: dict[str, int] = {}

    # 1) Supprime le site lui-même (par champ id, le _id est un UUID custom)
    res = await db.sites.delete_many({"id": site_id}) if not dry_run else None
    deleted["sites"] = res.deleted_count if res else await db.sites.count_documents({"id": site_id})

    # 2) Pour chaque collection scoped : supprime tout ce qui a site_id
    for col in SCOPED_COLLECTIONS:
        if col in PRESERVED_COLLECTIONS:
            continue
        try:
            n = await db[col].count_documents({"site_id": site_id})
            if n == 0:
                continue
            if not dry_run:
                r = await db[col].delete_many({"site_id": site_id})
                deleted[col] = r.deleted_count
            else:
                deleted[col] = n
        except Exception as e:
            deleted[col] = f"ERR: {e}"

    return deleted


def purge_uploads(site_ids: list[str], extra_uuids: set[str]) -> dict:
    """Supprime :
       - le dossier /app/backend/uploads/google_ads_exports/<site_id>
       - les fichiers heroes/logos/testimonials_ai/products_ai dont
         le 1er UUID dans le nom matche site_id ou design_id ou product_id
    """
    base = BACKEND_DIR / "uploads"
    out: dict[str, int] = {}

    # 1) Dossiers exports Google Ads scopés site_id
    for sid in site_ids:
        d = base / "google_ads_exports" / sid
        if d.exists():
            shutil.rmtree(d, ignore_errors=True)
            out[f"google_ads_exports/{sid}"] = 1

    # 2) Fichiers heroes/logos/testimonials_ai/products_ai
    SCAN_DIRS = ["heroes", "logos", "testimonials_ai", "products_ai"]
    for sub in SCAN_DIRS:
        d = base / sub
        if not d.exists():
            continue
        removed = 0
        for f in d.iterdir():
            if not f.is_file():
                continue
            stem = f.stem  # ex: hero_65964cb0-7a1a-4c11-9644-1ad8f2371d48_a6ea3b1b
            for u in extra_uuids:
                if u and u in stem:
                    try:
                        f.unlink()
                        removed += 1
                    except Exception:
                        pass
                    break
        if removed:
            out[f"uploads/{sub}"] = removed
    return out


async def list_remaining(db) -> dict:
    return {
        "sites": await db.sites.count_documents({}),
        "users": await db.users.count_documents({}),
        "niches": await db.niches.count_documents({}),
        "countries": await db.countries.count_documents({}),
        "products": await db.products.count_documents({}),
        "orders": await db.orders.count_documents({}),
        "storefront_events": await db.storefront_events.count_documents({}),
        "steps": await db.steps.count_documents({}),
        "blog_posts": await db.blog_posts.count_documents({}),
    }


async def main(target_site_ids: list[str], all_sites: bool, dry_run: bool):
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]

    if all_sites:
        target_site_ids = [s["id"] async for s in db.sites.find({}, {"_id": 0, "id": 1})]

    # Liste les sites trouvés
    print("=== Sites ciblés ===")
    found_sites = await db.sites.find(
        {"id": {"$in": target_site_ids}}, {"_id": 0, "id": 1, "name": 1, "status": 1}
    ).to_list(50)
    for s in found_sites:
        print(f"  · {s['id']} · {s.get('name')} · status={s.get('status')}")
    if not found_sites:
        print("  (aucun site trouvé en DB pour les IDs ciblés)")
        # On continue tout de même (orphan cleanup possible)

    # Collecte les UUIDs liés (design.id, product_id) pour le nettoyage uploads
    related = await collect_related_uuids(db, target_site_ids)
    print(f"\n=== UUIDs collectés pour nettoyage uploads : {len(related)} ===")

    print("\n=== Compteurs AVANT purge ===")
    before = await list_remaining(db)
    for k, v in before.items():
        print(f"  {k:25s} {v}")

    # Purge collection par collection, site par site
    print("\n=== Purge en cours ===")
    grand_total: dict[str, int] = {}
    for sid in target_site_ids:
        print(f"\n— site {sid}")
        d = await purge_site(db, sid, dry_run=dry_run)
        for k, v in d.items():
            print(f"    {k:25s} deleted={v}")
            if isinstance(v, int):
                grand_total[k] = grand_total.get(k, 0) + v

    # Uploads
    print("\n=== Purge uploads (filesystem) ===")
    if not dry_run:
        u = purge_uploads(target_site_ids, related)
        if u:
            for k, v in u.items():
                print(f"  {k:40s} removed={v}")
        else:
            print("  (rien à supprimer)")

    print("\n=== Compteurs APRÈS purge ===")
    after = await list_remaining(db)
    for k, v in after.items():
        delta = v - before.get(k, 0)
        sign = "" if delta == 0 else f" ({delta:+d})"
        print(f"  {k:25s} {v}{sign}")

    print("\n=== TOTAL DELETED PAR COLLECTION ===")
    for k in sorted(grand_total.keys()):
        print(f"  {k:25s} {grand_total[k]}")

    client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("site_ids", nargs="*",
                        help="Liste de site_ids à purger (vide = sites de démo connus)")
    parser.add_argument("--all", action="store_true", help="Purger TOUS les sites")
    parser.add_argument("--dry-run", action="store_true", help="Aucune écriture")
    args = parser.parse_args()
    targets = args.site_ids if args.site_ids else DEFAULT_DEMO_SITES
    asyncio.run(main(targets, args.all, args.dry_run))
