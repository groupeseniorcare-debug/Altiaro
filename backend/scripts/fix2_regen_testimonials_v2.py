"""Fix 2 — Régénération des 3 portraits testimonials premium Altea avec
contextes très différents pour éviter l'effet "trop IA".
"""
import asyncio
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, '/app/backend')
from dotenv import load_dotenv
load_dotenv('/app/backend/.env')

from motor.motor_asyncio import AsyncIOMotorClient

ALTEA = '6867223e-7ea5-45a7-815a-300cd89b7656'
TESTI_DIR = Path('/app/backend/uploads/testimonials_ai')
TESTI_DIR.mkdir(parents=True, exist_ok=True)

REALISM_PREFIX = (
    "Hyperrealistic editorial portrait photography, NOT digital art, NOT cartoon, "
    "NOT 3D render, NOT painterly, NOT AI-looking. Real human skin texture with "
    "natural pores, fine wrinkles, asymmetric features, age spots where appropriate. "
    "Natural human imperfections that make the photo feel real. "
    "Professional photography lens (85mm f/1.8), shallow depth of field, "
    "soft natural lighting, no over-saturation, no plastic skin. "
    "Documentary candid moment, not a posed studio shot. "
    "The image must look like a real photograph taken by a documentary photographer, "
    "not a generated image. "
)

PORTRAITS = [
    {
        "name": "Margot V.",
        "city": "Lyon",
        "age": 71,
        "prompt": (
            f"{REALISM_PREFIX}"
            "Candid editorial portrait of a French woman in her early 70s, sitting on a deep burgundy velvet sofa "
            "in a chic Parisian apartment in winter. She has short greying chestnut hair (natural color, not dyed), "
            "soft natural face wrinkles, a warm gentle smile facing camera, kind eyes. "
            "She holds a steaming porcelain tea cup in her hands, with a knit wool plaid blanket on her lap "
            "and an open hardcover book resting on it. "
            "Setting : a softly lit Parisian living room, large window on the left letting in cold winter daylight, "
            "vintage brass floor lamp, parquet floor, off-white walls with classical moldings. "
            "Style : warm cinematic palette (cream, burgundy, soft amber), film grain, "
            "Hasselblad documentary aesthetic, real photograph not AI."
        ),
    },
    {
        "name": "Heinrich M.",
        "city": "Munich",
        "age": 74,
        "prompt": (
            f"{REALISM_PREFIX}"
            "Candid editorial portrait of a German man in his mid-70s, sitting on a sunny apartment balcony "
            "in Munich on a spring morning. He has short white hair, fine reading glasses, "
            "natural age wrinkles around the eyes (crow's feet), a relaxed slight smile, looking softly into the distance "
            "(NOT directly at camera, three-quarter profile). "
            "He wears a beige knit wool sweater over a light blue shirt collar. "
            "On a small wooden bistro table in front of him : an espresso cup with milk foam, "
            "a folded German newspaper (Süddeutsche Zeitung visible). "
            "Setting : terracotta clay potted plants on the balcony floor, view of a green courtyard garden "
            "with chestnut trees in the background slightly out of focus, warm golden morning light from the right. "
            "Style : warm earth tones, documentary feel, slight film grain, "
            "shot on Leica M-series, real photograph aesthetic."
        ),
    },
    {
        "name": "Isabelle D.",
        "city": "Bruxelles",
        "age": 68,
        "prompt": (
            f"{REALISM_PREFIX}"
            "Candid three-quarter standing editorial portrait of a Belgian woman aged 68, "
            "in a modern minimalist Brussels apartment with abundant natural daylight. "
            "She has shoulder-length ash blond hair (natural with grey strands, slightly wavy), "
            "natural fine face lines, a complicit dynamic smile facing camera, expressive eyes. "
            "She wears a crisp white silk blouse with subtle pearl button details and a colorful silk scarf "
            "(amber, ochre, deep teal pattern) tied loosely around her neck. "
            "Posture : standing relaxed, hands gently resting on a marble kitchen island, "
            "slight three-quarter angle toward camera, energetic vibe. "
            "Setting : a modern open-space Belgian apartment with floor-to-ceiling windows on the left, "
            "concrete-and-oak architectural features, large green tropical plants (monstera, ficus), "
            "minimalist white walls, soft diffused daylight. "
            "Style : Scandinavian editorial, contemporary documentary, real photograph aesthetic, "
            "shot on Fujifilm GFX, fine film grain, no over-saturation."
        ),
    },
]


async def main():
    from services.llm_resilience import safe_nano_banana_bytes
    c = AsyncIOMotorClient(os.environ['MONGO_URL'])
    db = c[os.environ.get('DB_NAME', 'altiaro_dev')]

    site = await db.sites.find_one({'id': ALTEA}, {'_id': 0, 'design.testimonials_premium': 1})
    existing = (site.get('design', {}) or {}).get('testimonials_premium') or []
    print(f"Existing testimonials_premium: {len(existing)}")

    new_items = []
    total_t0 = time.time()

    for i, portrait_def in enumerate(PORTRAITS):
        t0 = time.time()
        print(f"\n--- [{i+1}/3] {portrait_def['name']} — {portrait_def['city']} ---")
        try:
            img_bytes = await safe_nano_banana_bytes(
                portrait_def['prompt'],
                timeout=180,
                request_id=f"fix2-portrait-{i}",
                session_id=f"fix2-{ALTEA[:8]}-{i}",
            )
        except Exception as e:
            print(f"  ❌ EXCEPTION: {type(e).__name__}: {e}")
            # Keep existing item if possible
            if i < len(existing):
                new_items.append(existing[i])
            continue

        elapsed = time.time() - t0
        if not img_bytes:
            print(f"  ⚠️  null after {elapsed:.1f}s")
            if i < len(existing):
                new_items.append(existing[i])
            continue

        # Save with new name
        fname = f"t_{ALTEA}_v2_{i}_{uuid.uuid4().hex[:8]}.png"
        fpath = TESTI_DIR / fname
        fpath.write_bytes(img_bytes)
        url = f"/api/uploads/testimonials_ai/{fname}"
        print(f"  ✅ {fname} ({len(img_bytes)} bytes) in {elapsed:.1f}s")

        # Build new item, keep text from existing if possible (else use defaults)
        existing_item = existing[i] if i < len(existing) else {}
        new_item = {
            **existing_item,  # keep id, text, rating, verified
            'name': portrait_def['name'],
            'city': portrait_def['city'],
            'age': portrait_def['age'],
            'image': url,
            'image_regenerated_at': datetime.now(timezone.utc).isoformat(),
        }
        new_items.append(new_item)

    elapsed_total = time.time() - total_t0

    # Update DB
    await db.sites.update_one(
        {'id': ALTEA},
        {'$set': {'design.testimonials_premium': new_items}}
    )

    print(f"\n=== SUMMARY ===")
    print(f"  Total time: {elapsed_total:.1f}s")
    print(f"  New portraits: {sum(1 for n in new_items if n.get('image_regenerated_at'))}/3")
    print(f"  Estimated cost: ~${sum(1 for n in new_items if n.get('image_regenerated_at')) * 0.20:.2f}")
    for n in new_items:
        print(f"  - {n.get('name'):<15} {n.get('city'):<12} age={n.get('age')} {n.get('image')[:80]}")


if __name__ == '__main__':
    asyncio.run(main())
