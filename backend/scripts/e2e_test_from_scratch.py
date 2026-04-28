"""
Phase 2.7.1 — Test E2E from-scratch (PRÉPARÉ, NON LANCÉ).

Lance ceci uniquement après réarmement du budget LLM (Nano Banana actuellement
en soft-overdraft). Coût estimé : ~5–10 $ (logo + hero + 6 produits × 8 styles
× ~3 variantes en moyenne).

Scénario :
  1. Crée 1 site de test (slug = e2e-test-{ts}, niche = "Fauteuils releveurs")
  2. Importe 3 produits de catégories différentes :
       - 1 fauteuil releveur (kind seated_furniture)
       - 1 coussin lombaire (kind cushion)
       - 1 couverture chauffante (kind blanket)
     via les datasets AliExpress déjà cataloguers (réutilise des fixtures
     Altea ou un dataset minimal).
  3. Marque le 1er produit comme `featured=True` (pilote → review_photos).
  4. POST `/sites/{id}/design/launch-auto?overwrite=false`
  5. Polling toutes les 10 s sur `launch_jobs.{id}` jusqu'à `completed*`.
  6. Audit final :
       - 9 sections page produit pilote rendues (probe DOM externe nécessaire,
         le script ne fait que la partie back).
       - `product.how_to_steps_meta.product_kind` ∈ {seated_furniture, cushion, blanket}
         pour les 3 produits respectivement.
       - `generated_images_by_variant` propre (1 entry par style, dédupé).
       - `design.brand.workshop_story` + `design.brand.workshop_image` set.
       - `pilot.review_photos` 4 URLs.

Usage :
    cd /app/backend
    python -m scripts.e2e_test_from_scratch --go        # lance vraiment
    python -m scripts.e2e_test_from_scratch --dry-run   # juste vérifie le scénario
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")

PRODUCT_FIXTURES: List[Dict[str, Any]] = [
    {
        "kind_hint": "seated_furniture",
        "name_fr": "Fauteuil releveur électrique massage",
        "name_en": "Electric rise & recline armchair with massage",
        "price": 1099.00,
        "category": "Fauteuils-Releveurs",
        "ae_id": "1005006xxxxx-fauteuil",  # remplace par un vrai ID si besoin
        "image_url": "https://ae01.alicdn.com/kf/SAMPLE-ARMCHAIR.jpg",
        "role": "main",
        "featured": True,
        "variants": ["Black", "White", "Brown"],
    },
    {
        "kind_hint": "cushion",
        "name_fr": "Coussin lombaire ergonomique",
        "name_en": "Ergonomic lumbar support cushion",
        "price": 49.90,
        "category": "Accessoires",
        "ae_id": "1005006xxxxx-cushion",
        "image_url": "https://ae01.alicdn.com/kf/SAMPLE-CUSHION.jpg",
        "role": "main",
        "featured": False,
        "variants": ["Grey", "Beige"],
    },
    {
        "kind_hint": "blanket",
        "name_fr": "Couverture chauffante électrique",
        "name_en": "Electric heated blanket",
        "price": 89.00,
        "category": "Accessoires",
        "ae_id": "1005006xxxxx-blanket",
        "image_url": "https://ae01.alicdn.com/kf/SAMPLE-BLANKET.jpg",
        "role": "main",
        "featured": False,
        "variants": ["Beige", "Grey"],
    },
]


async def _create_site(db, operator_id: str) -> str:
    site_id = str(uuid.uuid4())
    slug = f"e2e-test-{int(time.time())}"
    now = datetime.now(timezone.utc).isoformat()
    site = {
        "id": site_id,
        "slug": slug,
        "name": f"E2E Test {slug}",
        "operator_id": operator_id,
        "status": "draft",
        "niche": "Fauteuils releveurs électriques",
        "created_at": now,
        "updated_at": now,
        "design": {"brand": {"name": f"E2E {slug}"}},
        "owner_role": "operator",
    }
    await db.sites.insert_one(site)
    print(f"[create_site] {site_id} (slug={slug})")
    return site_id


async def _import_products(db, site_id: str) -> List[str]:
    out_ids = []
    now = datetime.now(timezone.utc).isoformat()
    for fix in PRODUCT_FIXTURES:
        pid = str(uuid.uuid4())
        doc = {
            "id": pid,
            "site_id": site_id,
            "name": {"fr": fix["name_fr"], "en": fix["name_en"]},
            "price": fix["price"],
            "currency": "EUR",
            "category": fix["category"],
            "role": fix["role"],
            "featured": fix["featured"],
            "ae_id": fix["ae_id"],
            "images": [fix["image_url"]],
            "original_images": [fix["image_url"]],
            "variants": [{"properties": [c]} for c in fix["variants"]],
            "status": "active",
            "created_at": now,
            "updated_at": now,
            "_e2e_kind_hint": fix["kind_hint"],
        }
        await db.products.insert_one(doc)
        out_ids.append(pid)
        print(f"[import_product] {pid[:8]} kind_hint={fix['kind_hint']} role={fix['role']} featured={fix['featured']}")
    return out_ids


async def _trigger_launch_auto(http_base: str, site_id: str, jwt: str) -> str:
    import httpx
    async with httpx.AsyncClient(timeout=60) as cli:
        r = await cli.post(
            f"{http_base}/api/sites/{site_id}/design/launch-auto",
            params={"overwrite": "false"},
            headers={"Authorization": f"Bearer {jwt}"},
        )
        r.raise_for_status()
        data = r.json()
        return data["job_id"]


async def _poll_job(db, job_id: str, max_wait_s: int = 1800) -> Dict[str, Any]:
    t0 = time.time()
    while time.time() - t0 < max_wait_s:
        lj = await db.launch_jobs.find_one({"id": job_id}, {"_id": 0})
        if lj and lj.get("status", "").startswith("completed"):
            return lj
        await asyncio.sleep(10)
    raise TimeoutError(f"launch_job {job_id} did not complete within {max_wait_s}s")


async def _audit(db, site_id: str, product_ids: List[str]) -> Dict[str, Any]:
    site = await db.sites.find_one({"id": site_id}, {"_id": 0})
    brand = (site.get("design") or {}).get("brand") or {}
    out = {
        "brand_name": brand.get("name"),
        "workshop_story_set": bool(brand.get("workshop_story")),
        "workshop_image_set": bool(brand.get("workshop_image")),
        "products": [],
    }
    for pid in product_ids:
        p = await db.products.find_one({"id": pid}, {"_id": 0})
        gibv = p.get("generated_images_by_variant") or {}
        meta = p.get("how_to_steps_meta") or {}
        # Verify dedup invariant : 1 style max per variant
        dedup_ok = True
        for color, items in gibv.items():
            styles = [i.get("style") for i in items if isinstance(i, dict)]
            if len(styles) != len(set(styles)):
                dedup_ok = False
        out["products"].append({
            "id": pid[:8],
            "kind_hint": p.get("_e2e_kind_hint"),
            "detected_kind": meta.get("product_kind"),
            "section_title_fr": (meta.get("section_title") or {}).get("fr"),
            "variants_with_8_styles": [c for c, items in gibv.items() if len(items) == 8],
            "variants_partial": [(c, len(items)) for c, items in gibv.items() if len(items) < 8],
            "dedup_ok": dedup_ok,
            "review_photos_count": len(p.get("review_photos") or []),
            "featured": p.get("featured", False),
        })
    return out


async def main(go: bool, http_base: str, jwt: str | None):
    c = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = c[os.environ.get("DB_NAME", "altiaro_dev")]

    if not go:
        print("=== DRY RUN ===")
        print("Scénario :")
        print("  1. Création site test → 1 doc dans `sites`")
        print(f"  2. Import {len(PRODUCT_FIXTURES)} produits → {len(PRODUCT_FIXTURES)} docs dans `products`")
        for f in PRODUCT_FIXTURES:
            print(f"     - {f['kind_hint']:18s} | featured={f['featured']} | variants={f['variants']}")
        print("  3. POST /sites/{id}/design/launch-auto?overwrite=false")
        print("  4. Polling launch_job (max 30 min)")
        print("  5. Audit final : workshop_story+image, HowTo kind detection × 3, dedup, review_photos")
        print("\nCoût estimé : ~5-10 $ Nano Banana + ~0,5 $ Haiku")
        print("Lancer avec --go pour exécuter.")
        return

    # Réel
    operator = await db.users.find_one({"role": "operator"}, {"_id": 0, "id": 1})
    if not operator:
        raise RuntimeError("No operator user found in DB")
    site_id = await _create_site(db, operator["id"])
    pids = await _import_products(db, site_id)

    if not jwt:
        raise RuntimeError("--jwt required for --go (operator JWT)")
    job_id = await _trigger_launch_auto(http_base, site_id, jwt)
    print(f"[launch-auto] job_id={job_id}")
    final = await _poll_job(db, job_id)
    print(f"[poll] status={final.get('status')} duration={final.get('duration_s')}")

    audit = await _audit(db, site_id, pids)
    import json
    print("\n=== E2E AUDIT ===")
    print(json.dumps(audit, indent=2, default=str))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--go", action="store_true", help="Lance vraiment (sinon dry-run)")
    parser.add_argument("--http-base", default="http://127.0.0.1:8001")
    parser.add_argument("--jwt", default=os.environ.get("OPERATOR_JWT", ""))
    args = parser.parse_args()
    asyncio.run(main(args.go, args.http_base, args.jwt or None))
