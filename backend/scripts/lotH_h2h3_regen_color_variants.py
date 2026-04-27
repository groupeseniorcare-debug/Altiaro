"""Lot H Fix 2+3 — POC + régénération masse des images de variantes couleur.

Pour chaque produit "main" du site Altea, génère via Nano Banana img-to-img
les images des couleurs autres que la "default" (la 1ère variante = celle dont
les images existent déjà dans `generated_images`).

Stratégie économique :
  - Couleur DEFAULT → COPIE les `generated_images` existants (0 cost LLM)
  - Autres couleurs → régénère studio + lifestyle + closeup via img-to-img

Hard cap budget : MAX_LLM_CALLS = 70 (env ~$3.50 à 0.05$/image).
Si dépassé → arrêt prématuré + rapport.

Stockage DB :
  product.generated_images_by_variant: {
    "black": [{style, url, color, color_label, generated_at, source_style, tweak}, ...],
    "white": [...],
    "brown": [...]
  }

Usage :
    cd /app/backend && python -m scripts.lotH_h2h3_regen_color_variants --site-id <uuid>
    cd /app/backend && python -m scripts.lotH_h2h3_regen_color_variants --product-id <uuid>  # POC 1 produit
    cd /app/backend && python -m scripts.lotH_h2h3_regen_color_variants --site-id <uuid> --max-products 1  # POC
    cd /app/backend && python -m scripts.lotH_h2h3_regen_color_variants --site-id <uuid> --dry-run
    cd /app/backend && python -m scripts.lotH_h2h3_regen_color_variants --site-id <uuid> --resume  # skip already done
"""
import argparse
import asyncio
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")

from motor.motor_asyncio import AsyncIOMotorClient  # noqa: E402

from services.color_variant_images import (  # noqa: E402
    slugify_color,
    generate_color_variant_image,
    detect_product_kind,
    color_label_to_english,
    _fetch_image_b64,
)

ALTEA_DEFAULT = "6867223e-7ea5-45a7-815a-300cd89b7656"

# Hard cap to protect the budget : 70 calls × ~0.05$ = ~$3.50 max
MAX_LLM_CALLS_DEFAULT = 70


def _color_value_from_variant(variant: dict) -> str | None:
    """Extracts the color value from a variant. Schema: properties[0] is the color
    after the H1 audit (ships_from removed)."""
    props = variant.get("properties") or []
    if not props:
        return None
    return str(props[0]).strip() if props[0] else None


async def process_product(
    db,
    site_id: str,
    product: dict,
    *,
    dry_run: bool = False,
    resume: bool = False,
    max_calls_remaining: int = MAX_LLM_CALLS_DEFAULT,
) -> tuple[int, int]:
    """Process one product : generate color variant images.

    Returns (calls_made, images_added).
    """
    pid = product["id"]
    name = product.get("name") or {}
    name_str = name.get("fr") if isinstance(name, dict) else str(name)
    print(f"\n→ Product {pid[:8]} — {name_str[:60]}")

    variants = product.get("variants") or []
    if not variants:
        print("  ⏭  no variants — skip")
        return (0, 0)

    # Extract color list
    colors = []
    seen = set()
    for v in variants:
        c = _color_value_from_variant(v)
        if c and c.lower() not in seen:
            seen.add(c.lower())
            colors.append(c)
    if not colors:
        print("  ⏭  no color in variants — skip")
        return (0, 0)
    print(f"  Colors detected: {colors}")

    if len(colors) <= 1:
        print(f"  ⏭  only 1 color ({colors[0]}) — no variant set needed")
        return (0, 0)

    # Default color = first variant (the one Altea images are based on)
    default_color = colors[0]
    default_slug = slugify_color(default_color)
    other_colors = colors[1:]

    # Existing generated_images (default color) — used as reference + copied to default slug
    gi = product.get("generated_images") or []
    if not gi:
        print("  ⏭  no generated_images — cannot use as reference")
        return (0, 0)
    print(f"  Default color: {default_color} ({len(gi)} styles existing)")

    # Build the existing variant set (resume support)
    existing_by_variant = product.get("generated_images_by_variant") or {}
    if resume and existing_by_variant.get(default_slug) and all(
        existing_by_variant.get(slugify_color(c)) for c in other_colors
    ):
        print(f"  ⏭  already complete (resume mode) — skip")
        return (0, 0)

    new_by_variant: dict = dict(existing_by_variant)  # start from existing

    # 1) Default color : copy existing generated_images (0 LLM cost)
    if not new_by_variant.get(default_slug) or not resume:
        copies = []
        for img in gi:
            copies.append({
                "style": img.get("style"),
                "url": img.get("url"),  # reuse the same file
                "color": default_color,
                "color_label": default_color,
                "generated_at": img.get("created_at") or datetime.now(timezone.utc).isoformat(),
                "source_style": img.get("style"),
                "tweak": "default-copy-from-generated_images",
            })
        new_by_variant[default_slug] = copies
        print(f"  ✓ Default color {default_slug}: {len(copies)} images (copied, 0 cost)")
    else:
        print(f"  ⏭  Default color {default_slug} already done")

    # 2) Other colors : regenerate via img-to-img
    product_kind = detect_product_kind(name)
    default_color_en = color_label_to_english(default_color)
    calls_made = 0
    images_added = 0

    # Pick the "studio" image as canonical reference (cleanest background, most identity-preserving)
    ref_image = next((img for img in gi if img.get("style") == "studio"), gi[0])
    ref_b64 = await _fetch_image_b64(ref_image.get("url"))
    if not ref_b64:
        print(f"  ❌ Reference image cannot be loaded: {ref_image.get('url')}")
        return (0, 0)
    print(f"  Reference loaded: {ref_image.get('url').split('/')[-1]} ({len(ref_b64)//1024} KB b64)")

    for color in other_colors:
        slug = slugify_color(color)
        target_color_en = color_label_to_english(color)
        print(f"\n  → Color {color} (slug={slug}, en={target_color_en})")

        if resume and new_by_variant.get(slug) and len(new_by_variant[slug]) >= len(gi):
            print(f"    ⏭  already done in resume mode")
            continue

        color_imgs = []
        for img in gi:
            style = img.get("style", "studio")
            if max_calls_remaining - calls_made <= 0:
                print(f"    ⏹  HARD CAP reached, stopping")
                break

            if dry_run:
                print(f"    [DRY] would generate {style} for {color}")
                calls_made += 1
                color_imgs.append({
                    "style": style,
                    "url": f"/api/uploads/products_ai/{pid}/variants/{slug}/{style}_DRY.png",
                    "color": color,
                    "color_label": color,
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "source_style": style,
                    "tweak": "img-to-img-color",
                })
                continue

            try:
                url = await generate_color_variant_image(
                    product_id=pid,
                    color_slug=slug,
                    color_label=color,
                    target_color_label=target_color_en,
                    original_color_label=default_color_en,
                    style=style,
                    reference_image_b64=ref_b64,
                    product_kind=product_kind,
                )
            except Exception as e:
                print(f"    ❌ generate failed for {style} : {e}")
                if "budget" in str(e).lower():
                    print("    🚨 BUDGET EXHAUSTED — abort")
                    raise
                continue

            calls_made += 1
            if not url:
                print(f"    ⚠  {style} returned None")
                continue

            color_imgs.append({
                "style": style,
                "url": url,
                "color": color,
                "color_label": color,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "source_style": style,
                "tweak": "img-to-img-color",
            })
            images_added += 1
            print(f"    ✓ {style} → {url.split('/')[-1]}")

        if color_imgs:
            new_by_variant[slug] = color_imgs

    # Persist to DB
    if not dry_run and (calls_made > 0 or new_by_variant != existing_by_variant):
        await db.products.update_one(
            {"id": pid},
            {"$set": {
                "generated_images_by_variant": new_by_variant,
                "generated_images_by_variant_updated_at": datetime.now(timezone.utc).isoformat(),
            }},
        )
        print(f"\n  ✓ DB updated for {pid[:8]}: {len(new_by_variant)} colors stored")

    return (calls_made, images_added)


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--site-id", default=ALTEA_DEFAULT)
    parser.add_argument("--product-id", default=None, help="Single product POC")
    parser.add_argument("--max-products", type=int, default=None, help="Limit number of products")
    parser.add_argument("--max-calls", type=int, default=MAX_LLM_CALLS_DEFAULT, help="Hard cap LLM calls")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--resume", action="store_true", help="Skip products already done")
    args = parser.parse_args()

    c = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = c[os.environ.get("DB_NAME", "altiaro_dev")]

    print(f"=== Lot H — Color variant image regen ===")
    print(f"Mode: {'DRY-RUN' if args.dry_run else 'LIVE'}")
    print(f"Site: {args.site_id[:8]}")
    print(f"Hard cap LLM calls: {args.max_calls} (~${args.max_calls * 0.05:.2f})")

    # Build the product query
    query = {}
    if args.product_id:
        query["id"] = args.product_id
    else:
        query["site_id"] = args.site_id
        query["role"] = "main"

    cursor = db.products.find(query, {"_id": 0})
    products = await cursor.to_list(length=20)
    print(f"Products to process: {len(products)}")
    if args.max_products:
        products = products[:args.max_products]
        print(f"  (limited to {args.max_products})")

    total_calls = 0
    total_images = 0
    for p in products:
        if total_calls >= args.max_calls:
            print(f"\n🚨 HARD CAP {args.max_calls} reached — stopping after {total_calls} calls")
            break
        try:
            calls, imgs = await process_product(
                db, args.site_id, p,
                dry_run=args.dry_run,
                resume=args.resume,
                max_calls_remaining=args.max_calls - total_calls,
            )
        except Exception as e:
            if "budget" in str(e).lower():
                print(f"🚨 BUDGET EXHAUSTED — abort all")
                break
            raise
        total_calls += calls
        total_images += imgs

    cost_est = total_calls * 0.05
    print(f"\n=== SUMMARY ===")
    print(f"Total LLM calls: {total_calls}")
    print(f"Total images added: {total_images}")
    print(f"Estimated cost: ~${cost_est:.2f}")


if __name__ == "__main__":
    asyncio.run(main())
