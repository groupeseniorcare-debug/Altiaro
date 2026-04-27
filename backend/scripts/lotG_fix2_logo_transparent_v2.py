"""Lot G Fix 2 — Logo Altea transparent + propagation aux favicons.

Stratégie en 2 étapes :
1) Si le logo source actuel est en mode RGB (Nano Banana n'a pas respecté
   `transparent background`), on applique le fallback Pillow
   `remove_white_background()` pour obtenir une vraie alpha channel.
   On ré-écrit le PNG nettoyé en place (overwrite avec backup).
2) Régénère les 5 favicons depuis ce logo nettoyé via
   `regenerate_and_persist_favicons()` qui utilise désormais
   `ensure_alpha_channel()` (sécurité supplémentaire).

Idempotent : peut être réexécuté plusieurs fois sans effet de bord.
Aucun appel LLM (le logo source img2img a déjà été généré au tour précédent).
Cost : 0 €.

Usage :
    cd /app/backend && python -m scripts.lotG_fix2_logo_transparent_v2
    cd /app/backend && python -m scripts.lotG_fix2_logo_transparent_v2 --site-id <uuid>
    cd /app/backend && python -m scripts.lotG_fix2_logo_transparent_v2 --all  # tous les sites en DB
"""
import argparse
import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")

from motor.motor_asyncio import AsyncIOMotorClient  # noqa: E402
from PIL import Image  # noqa: E402

from services.favicon_generator import (  # noqa: E402
    ensure_alpha_channel,
    regenerate_and_persist_favicons,
)

ALTEA_DEFAULT = "6867223e-7ea5-45a7-815a-300cd89b7656"
UPLOAD_DIR = Path("/app/backend/uploads")


def _resolve_logo_path(logo_url: str) -> Path | None:
    if not logo_url:
        return None
    rel = logo_url.split("/api/uploads/", 1)
    if len(rel) != 2:
        return None
    p = (UPLOAD_DIR / rel[1]).resolve()
    if not str(p).startswith(str(UPLOAD_DIR.resolve())):
        return None
    return p if p.exists() else None


async def fix_one_site(db, site_id: str) -> bool:
    """Applique le fix sur un site donné. Returns True si succès."""
    site = await db.sites.find_one(
        {"id": site_id},
        {"_id": 0, "design.brand.logo_url": 1, "design.brand.name": 1},
    )
    if not site:
        print(f"  ❌ Site {site_id[:8]} introuvable")
        return False

    brand = (site.get("design") or {}).get("brand") or {}
    logo_url = brand.get("logo_url")
    if not logo_url:
        print(f"  ⚠️  Site {site_id[:8]} ({brand.get('name','?')}) sans logo_url, skip")
        return False

    src = _resolve_logo_path(logo_url)
    if not src:
        print(f"  ❌ Logo file introuvable on disk: {logo_url}")
        return False

    # Étape 1 : nettoyage alpha channel
    print(f"\n→ Site {site_id[:8]} ({brand.get('name','?')})")
    print(f"  logo source: {src.name}")
    with Image.open(src) as orig:
        orig.load()
        mode_before = orig.mode
        size_before = orig.size

    cleaned = ensure_alpha_channel(src)
    print(f"  mode: {mode_before} → {cleaned.mode}, size: {size_before}")

    # Backup avant overwrite (idempotence safety)
    backup = src.with_suffix(".rgb-backup.png")
    if not backup.exists():
        with Image.open(src) as orig:
            orig.save(backup, format="PNG")
        print(f"  backup → {backup.name}")
    else:
        print("  backup already exists, skip")

    # Sauvegarde du logo nettoyé en place (overwrite)
    cleaned.save(src, format="PNG", optimize=True)
    print(f"  ✅ logo cleaned saved (RGBA), {src.stat().st_size}B")

    # Étape 2 : regen favicons depuis le logo nettoyé
    print("  → regenerating 5 favicons...")
    favicons = await regenerate_and_persist_favicons(site_id)
    if not favicons:
        print("  ❌ favicon regeneration failed")
        return False
    for slug, u in favicons.items():
        print(f"    {slug}: {u}")

    # Note la timestamp de l'opération
    await db.sites.update_one(
        {"id": site_id},
        {
            "$set": {
                "design.brand.logo_method": "img2img-pillow-cleaned",
                "design.brand.logo_alpha_fixed_at": datetime.now(timezone.utc).isoformat(),
            }
        },
    )
    return True


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--site-id", default=ALTEA_DEFAULT)
    parser.add_argument("--all", action="store_true", help="Migrer TOUS les sites en DB")
    args = parser.parse_args()

    c = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = c[os.environ.get("DB_NAME", "altiaro_dev")]

    if args.all:
        print("=== Migration de TOUS les sites ===")
        n_ok = 0
        n_total = 0
        async for s in db.sites.find({}, {"_id": 0, "id": 1}):
            n_total += 1
            if await fix_one_site(db, s["id"]):
                n_ok += 1
        print(f"\n✅ Done: {n_ok}/{n_total} sites migrated")
    else:
        ok = await fix_one_site(db, args.site_id)
        print(f"\n{'✅' if ok else '❌'} {args.site_id[:8]}")


if __name__ == "__main__":
    asyncio.run(main())
