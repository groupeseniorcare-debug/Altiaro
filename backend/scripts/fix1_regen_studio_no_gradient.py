"""Fix 1 — Régénération des 6 images STUDIO Altea avec fond uniforme ivoire
(suppression du gradient anthracite qui assombrit le bas des cards produits).

Préserve les images lifestyle + closeup existantes. Ne touche que studio
(remplacement direct dans generated_images[0]).

Coût : ~$1.20 (6 × Nano Banana img-to-img).
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

IDENTITY_HEADER = (
    "PRESERVE EXACT IDENTITY OF THE PRODUCT IN THE REFERENCE IMAGE. "
    "The chair MUST be visually identical to the source: same model, same color, same fabric, "
    "same dimensions, same accessories, same control panel, same footrest mechanism, "
    "same side pockets, same headrest, same stitching, same proportions. "
    "Do NOT redesign, modify, improve, restyle, or update the chair. "
    "ONLY the surrounding scene, lighting, and camera angle should differ. "
)

STUDIO_PROMPT = (
    f"{IDENTITY_HEADER}"
    "Generate a high-end studio product photography of THIS EXACT chair shown in the reference image. "
    "Background: clean uniform soft warm ivory (#F5F2EB), perfectly even, NO GRADIENT, no vignette, "
    "no dark zones at the bottom or edges, no shadows on the wall. The chair is fully lit and centered. "
    "Camera: 50mm at f/8, three-quarter view (slightly from the right), eye-level. "
    "Position: the chair is in PARTIAL RECLINE position (footrest slightly raised ~20°, backrest "
    "slightly tilted) — showing the recline mechanism without being fully extended. "
    "Lighting: large softbox at 45° upper-left + subtle rim light upper-right + soft fill bottom — "
    "very soft natural shadow ONLY directly under the chair (floating effect, no harsh shadow). "
    "Style: Apple-product-page minimalist aesthetic, ultra-clean, ultra-sharp focus, photorealistic, 4K. "
    "No logo, no text, no background distraction, NO DARK GRADIENT AT THE BOTTOM."
)


async def _download_b64(url: str, client: httpx.AsyncClient):
    try:
        r = await client.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=30, follow_redirects=True)
        if r.status_code == 200 and r.content:
            return base64.b64encode(r.content).decode('ascii')
    except Exception:
        pass
    return None


async def main():
    from services.llm_resilience import safe_nano_banana_bytes

    c = AsyncIOMotorClient(os.environ['MONGO_URL'])
    db = c[os.environ.get('DB_NAME', 'altiaro_dev')]

    products = []
    async for p in db.products.find({
        'site_id': ALTEA, 'role': 'main', 'status': 'active',
    }).sort('id', 1):
        products.append(p)
    print(f"Total produits 'main' actifs Altea : {len(products)}")

    total_t0 = time.time()
    success = 0

    async with httpx.AsyncClient() as client:
        for i, p in enumerate(products, 1):
            pid = p['id']
            nm = p.get('name')
            title = nm.get('fr', '?') if isinstance(nm, dict) else nm
            print(f"\n[{i}/{len(products)}] {pid[:8]} {title[:50]}")

            ae_imgs = p.get('images') or []
            src = ae_imgs[0] if ae_imgs else None
            src_url = src if isinstance(src, str) else (src.get('url') if isinstance(src, dict) else None)
            if not src_url:
                print(f"  ❌ no AE source")
                continue
            img_b64 = await _download_b64(src_url, client)
            if not img_b64:
                print(f"  ❌ AE download failed")
                continue

            t0 = time.time()
            try:
                bytes_ = await safe_nano_banana_bytes(
                    STUDIO_PROMPT,
                    reference_image_b64=img_b64,
                    timeout=180,
                    request_id=f"fix1-studio-{pid[:8]}",
                    session_id=f"fix1-{pid[:8]}",
                )
            except Exception as e:
                print(f"  ❌ {type(e).__name__}: {e}")
                continue

            elapsed = time.time() - t0
            if not bytes_:
                print(f"  ⚠️  null after {elapsed:.1f}s")
                continue

            # Save new studio with v2 marker
            fname = f"p_{pid}_studio_v2_{uuid.uuid4().hex[:8]}.png"
            fpath = PRODUCTS_AI_DIR / fname
            fpath.write_bytes(bytes_)
            new_url = f"/api/uploads/products_ai/{fname}"
            print(f"  ✅ {fname} ({len(bytes_)}B) in {elapsed:.1f}s")

            # Replace ONLY the studio entry in generated_images (preserve lifestyle + closeup)
            current = p.get('generated_images') or []
            updated = []
            replaced = False
            for g in current:
                if isinstance(g, dict) and g.get('style') == 'studio' and not replaced:
                    updated.append({
                        'url': new_url,
                        'style': 'studio',
                        'tweak': 'fix1-no-gradient',
                        'method': 'img-to-img',
                        'created_at': datetime.now(timezone.utc).isoformat(),
                    })
                    replaced = True
                else:
                    updated.append(g)
            if not replaced:
                updated.insert(0, {
                    'url': new_url, 'style': 'studio', 'tweak': 'fix1-no-gradient',
                    'method': 'img-to-img',
                    'created_at': datetime.now(timezone.utc).isoformat(),
                })
            await db.products.update_one(
                {'id': pid},
                {'$set': {
                    'generated_images': updated,
                    'generated_images_updated_at': datetime.now(timezone.utc).isoformat(),
                }}
            )
            success += 1
            await asyncio.sleep(2)

    elapsed_total = time.time() - total_t0
    print(f"\n=== SUMMARY ===")
    print(f"  Total: {elapsed_total:.0f}s")
    print(f"  Success: {success}/{len(products)}")
    print(f"  Estimated cost: ~${success * 0.20:.2f}")


if __name__ == '__main__':
    asyncio.run(main())
