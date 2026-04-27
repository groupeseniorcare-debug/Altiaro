"""Lot C — Régénération massive img-to-img des 6 produits "main" Altea.

Contraintes utilisateur :
- Image #1 = STUDIO (image principale, fond ivoire/blanc cassé, position partiellement reclined)
- Image #2 = LIFESTYLE (appartement haussmannien parisien, golden hour, footrest sorti, sans personne)
- Image #3 = CLOSEUP (gros plan sur les détails premium)
- Préfixe systématique IDENTITY_PRESERVATION renforcé
- Backup ancien dans generated_images_legacy_textonly (rollback)
- Coût hard cap : $5 (cible $3.60)

Usage : python3 /app/backend/scripts/lot_c_regen_altea_images.py
"""
import asyncio
import base64
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, '/app/backend')
from dotenv import load_dotenv
load_dotenv('/app/backend/.env')

import httpx
from motor.motor_asyncio import AsyncIOMotorClient

ALTEA = '6867223e-7ea5-45a7-815a-300cd89b7656'
PRODUCTS_AI_DIR = Path('/app/backend/uploads/products_ai')

# ───────────────────────────────────────────────────────────────────────
# PROMPTS — identity preservation reinforced
# ───────────────────────────────────────────────────────────────────────
IDENTITY_HEADER = (
    "PRESERVE EXACT IDENTITY OF THE PRODUCT IN THE REFERENCE IMAGE. "
    "The chair MUST be visually identical to the source : same model, same color, same fabric, "
    "same dimensions, same accessories, same control panel, same footrest mechanism, "
    "same side pockets, same headrest, same stitching pattern, same proportions. "
    "Do NOT redesign, modify, improve, restyle, or update the chair. "
    "ONLY the surrounding scene, lighting, and camera angle should differ. "
    "The chair must be photo-realistically reproduced from the reference. "
)

STYLES = [
    {
        "slug": "studio",
        "prompt": (
            f"{IDENTITY_HEADER}"
            "Generate a high-end studio product photography of THIS EXACT chair shown in the reference image. "
            "Background : seamless gradient from warm ivory (#F5F2EB top) to soft anthracite (#1F1F1F bottom), no texture, no clutter. "
            "Camera : 50mm at f/8, perfect three-quarter view (slightly from the right), eye-level. "
            "Position : the chair is in PARTIAL RECLINE position (footrest slightly raised ~20°, backrest slightly tilted) — "
            "showing the recline mechanism without being fully extended. This is the hero shot for the product page. "
            "Lighting : large softbox at 45° upper-left + subtle rim light upper-right, soft natural shadow under the chair. "
            "Style : Apple-product-page minimalist aesthetic, ultra-clean, ultra-sharp focus, photo-realistic, 4K, "
            "no logo, no text, no watermark, no background distraction."
        ),
    },
    {
        "slug": "lifestyle",
        "prompt": (
            f"{IDENTITY_HEADER}"
            "Generate a professional lifestyle product photography of THIS EXACT chair shown in the reference image, "
            "placed in a setting. Setting : an elegant Haussmann-style Parisian apartment living room. "
            "Specific decor : herringbone parquet flooring (point de Hongrie), white marble fireplace with classical moldings on the wall, "
            "large window on the left letting in soft golden-hour daylight (warm 2700K, sunset glow), "
            "ivory linen curtains gently translucent, a brass design lamp, leather-bound classical books on a shelf, "
            "neutral color palette (cream, gold, anthracite). "
            "Position : the chair is in FULLY RECLINED position with footrest extended (showing the function in use). "
            "Camera : 35mm at f/4, slight low angle (camera ~1m height), rule-of-thirds composition. "
            "NO PERSON in the frame, only the chair in its premium contextual setting. "
            "Style : editorial luxury minimal, Architectural Digest magazine aesthetic, photorealistic, sharp focus, "
            "4K, premium silver economy aesthetic, high dynamic range, no logo, no text overlay."
        ),
    },
    {
        "slug": "closeup",
        "prompt": (
            f"{IDENTITY_HEADER}"
            "Generate a closeup detail product photography of THIS EXACT chair shown in the reference image. "
            "Crop : tight macro on the upper-right armrest area, showing in detail : the leather/fabric stitching pattern, "
            "the cup holder if visible in source, the side pocket with the remote control nestled inside, "
            "and the subtle curvature of the seat back. The textures must be photoREALISTIC : grain of the upholstery, seam threads, "
            "metal hinge if visible. Lighting : warm grazing light from upper-left at 30°, revealing the fabric weave and stitching, "
            "soft fill from the right. "
            "Camera : 100mm macro lens at f/2.8, very shallow depth of field (only the foreground stitching in sharp focus, "
            "background slightly blurred). "
            "Style : editorial macro photography, focus stacked on the stitching, premium quality magazine ad aesthetic, "
            "photorealistic, 4K, no text, no watermark."
        ),
    },
]


async def _download_ae_image_b64(url: str, client: httpx.AsyncClient) -> str | None:
    """Télécharge l'image AE source et retourne le base64 brut (sans data-uri prefix)."""
    if not url:
        return None
    try:
        r = await client.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=30, follow_redirects=True)
        if r.status_code == 200 and r.content:
            return base64.b64encode(r.content).decode('ascii')
    except Exception as e:
        print(f"  ⚠️  AE download failed for {url[:80]}: {e}")
    return None


async def regen_one_product(db, client, product, idx, total):
    from services.llm_resilience import safe_nano_banana_bytes, LLMUnavailableError

    pid = product['id']
    nm = product.get('name')
    title = nm.get('fr', '?') if isinstance(nm, dict) else (nm or '?')
    print(f"\n══════════════════════════════════════════════════════════════════════")
    print(f"[{idx}/{total}] Product {pid[:8]} — {title[:55]}")
    print(f"══════════════════════════════════════════════════════════════════════")

    # 1. Source AE image
    ae_imgs = product.get('images') or []
    src = ae_imgs[0] if ae_imgs else None
    src_url = src if isinstance(src, str) else (src.get('url') if isinstance(src, dict) else None)
    if not src_url:
        print(f"  ❌ No AE source image — skipped (img2img required)")
        return None
    print(f"  AE source: {src_url[:90]}")

    img_b64 = await _download_ae_image_b64(src_url, client)
    if not img_b64:
        print(f"  ❌ AE download failed — skipped")
        return None
    print(f"  AE bytes: {len(img_b64) * 3 // 4}, b64 head: {img_b64[:12]}...")

    # 2. Backup anciennes images si pas déjà fait (idempotent)
    if not product.get('generated_images_legacy_textonly'):
        await db.products.update_one(
            {'id': pid},
            {'$set': {'generated_images_legacy_textonly': product.get('generated_images') or []}}
        )
        print(f"  ✓ Backup anciennes ({len(product.get('generated_images') or [])} imgs) → generated_images_legacy_textonly")

    # 3. Générer 3 nouvelles images dans l'ordre studio/lifestyle/closeup
    new_imgs = []
    for style_def in STYLES:
        slug = style_def['slug']
        prompt = style_def['prompt']
        t0 = time.time()
        try:
            img_bytes = await safe_nano_banana_bytes(
                prompt,
                reference_image_b64=img_b64,
                timeout=180,
                request_id=f"lotC-{slug}-{pid[:8]}",
                session_id=f"lotC-{pid[:8]}-{slug}",
            )
        except LLMUnavailableError as e:
            print(f"  ❌ {slug} LLM unavailable: {e}")
            continue
        except Exception as e:
            print(f"  ❌ {slug} EXCEPTION: {type(e).__name__}: {e}")
            continue
        elapsed = time.time() - t0
        if not img_bytes:
            print(f"  ⚠️  {slug} null after {elapsed:.1f}s (degraded)")
            continue
        # Save to disk
        fname = f"p_{pid}_{slug}_{uuid.uuid4().hex[:8]}.png"
        fpath = PRODUCTS_AI_DIR / fname
        fpath.write_bytes(img_bytes)
        url = f"/api/uploads/products_ai/{fname}"
        new_imgs.append({
            'url': url,
            'style': slug,
            'tweak': 'img-to-img',
            'created_at': datetime.now(timezone.utc).isoformat(),
        })
        print(f"  ✅ {slug:<10} {len(img_bytes):>7}B  {elapsed:.1f}s  {url}")

    # 4. Persist : new images replace old, studio first (image principale via getPrimaryImage)
    if not new_imgs:
        print(f"  ❌ No new images generated — DB not updated")
        return None
    await db.products.update_one(
        {'id': pid},
        {'$set': {
            'generated_images': new_imgs,
            'generated_images_updated_at': datetime.now(timezone.utc).isoformat(),
            'generated_images_method': 'img-to-img',
        }}
    )
    print(f"  ✅ DB updated : {len(new_imgs)} images, studio={new_imgs[0]['style']==('studio')}")
    return new_imgs


async def main():
    c = AsyncIOMotorClient(os.environ['MONGO_URL'])
    db = c[os.environ.get('DB_NAME', 'altiaro_dev')]

    products = []
    async for p in db.products.find({
        'site_id': ALTEA,
        'role': 'main',
        'status': 'active',
    }).sort('id', 1):
        products.append(p)
    print(f"Total produits 'main' actifs Altea : {len(products)}")
    if not products:
        print("Aucun produit à traiter")
        return

    total_t0 = time.time()
    summary = []
    async with httpx.AsyncClient() as client:
        for i, p in enumerate(products, 1):
            res = await regen_one_product(db, client, p, i, len(products))
            summary.append({
                'pid': p['id'],
                'title': (p.get('name') or {}).get('fr', '?') if isinstance(p.get('name'), dict) else p.get('name', '?'),
                'count': len(res) if res else 0,
            })
            # Sleep 2s entre produits pour ne pas saturer le proxy
            await asyncio.sleep(2)

    elapsed_total = time.time() - total_t0
    success_imgs = sum(s['count'] for s in summary)
    print(f"\n══════════════════════════════════════════════════════════════════════")
    print(f"  RÉGÉNÉRATION ALTEA TERMINÉE")
    print(f"══════════════════════════════════════════════════════════════════════")
    print(f"  Total time     : {elapsed_total:.0f}s ({elapsed_total/60:.1f} min)")
    print(f"  Total images   : {success_imgs}/{len(products)*3}")
    print(f"  Estimated cost : ~${success_imgs * 0.20:.2f}")
    print(f"")
    print(f"  Per product :")
    for s in summary:
        ok = '✅' if s['count'] == 3 else ('⚠️ ' if s['count'] > 0 else '❌')
        print(f"    {ok} {s['pid'][:8]} ({s['count']}/3) {s['title'][:55]}")


if __name__ == '__main__':
    asyncio.run(main())
