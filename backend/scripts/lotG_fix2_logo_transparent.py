"""Lot G Fix 2 — Régénère le logo Altea SUR FOND TRANSPARENT (alpha channel).
Puis régénère les favicons en préservant la transparence pour 192/512.
"""
import asyncio, os, sys, time, uuid
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, '/app/backend')
from dotenv import load_dotenv
load_dotenv('/app/backend/.env')
from motor.motor_asyncio import AsyncIOMotorClient

ALTEA = '6867223e-7ea5-45a7-815a-300cd89b7656'
LOGO_DIR = Path('/app/backend/uploads/logos')

LOGO_PROMPT = (
    "Transparent PNG with alpha channel. Generate ONLY the brand logo 'Altea' as a wordmark, "
    "no background, no scene, no decoration. Pure isolated logo on a 100% transparent canvas. "
    "Style: serif elegant wordmark in Cormorant Garamond style, thin lines, sophisticated, "
    "anthracite color (#2A2A2A), letterspacing comfortable. Below the wordmark, in tiny uppercase Manrope, "
    "the tagline 'MAISON FRANÇAISE' in light grey. NO BACKGROUND COLOR, NO SHAPE BEHIND THE LETTERS — "
    "the area outside the letters MUST BE FULLY TRANSPARENT (alpha=0). "
    "Output: PNG with proper transparency, perfectly centered. Aspect ratio 4:1 (wide horizontal). "
    "No frame, no border, no glow, no shadow — just the letters in anthracite on pure transparency."
)

async def main():
    from services.llm_resilience import safe_nano_banana_bytes
    from services.favicon_generator import regenerate_and_persist_favicons
    c = AsyncIOMotorClient(os.environ['MONGO_URL'])
    db = c[os.environ.get('DB_NAME','altiaro_dev')]

    print(f"Génération logo Altea transparent...")
    t0 = time.time()
    try:
        img = await safe_nano_banana_bytes(LOGO_PROMPT, timeout=180,
            request_id=f"lotG-fix2-logo", session_id=f"lotG-fix2-logo")
    except Exception as e:
        print(f"❌ {type(e).__name__}: {e}"); return
    if not img:
        print(f"⚠️  null after {time.time()-t0:.1f}s"); return

    # Validation rapide alpha — si l'image générée n'a pas d'alpha, on conserve quand même
    # (Nano Banana ne respecte pas toujours la consigne de transparence)
    fname = f"logo_{ALTEA}_transparent_{uuid.uuid4().hex[:8]}.png"
    (LOGO_DIR / fname).write_bytes(img)
    url = f"/api/uploads/logos/{fname}"
    print(f"✅ {fname} ({len(img)}B) in {time.time()-t0:.1f}s")

    # Vérif alpha channel via Pillow
    from PIL import Image
    with Image.open(LOGO_DIR / fname) as im:
        has_alpha = im.mode in ('RGBA','LA') or (im.mode == 'P' and 'transparency' in im.info)
        print(f"  has_alpha: {has_alpha} (mode={im.mode})")
        if not has_alpha:
            print(f"  ⚠️  Logo n'a pas d'alpha channel → on garde quand même mais le bg sera là")

    await db.sites.update_one({'id': ALTEA},
        {'$set': {
            'design.brand.logo_url': url,
            'design.brand.logo_method': 'img2img-transparent-bg',
            'design.brand.logo_updated_at': datetime.now(timezone.utc).isoformat(),
        }})
    print(f"\nDB updated: design.brand.logo_url = {url}")

    # Régénère les favicons depuis ce nouveau logo
    print(f"\nRégénération favicons depuis nouveau logo...")
    favicons = await regenerate_and_persist_favicons(ALTEA)
    print(f"Generated {len(favicons)} favicon sizes:")
    for slug, u in favicons.items():
        print(f"  - {slug}: {u}")

asyncio.run(main())
