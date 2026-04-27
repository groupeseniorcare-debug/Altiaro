"""Lot G Fix 1 — Génère 3 portraits ADDITIONNELS pour porter la liste à 6 :
Sylvain B. (76, Toulouse), Catherine R. (69, Genève), Roland L. (81, Lille).
Plus 3 textes courts (manuels, déterministes, 0 LLM texte).
"""
import asyncio, os, sys, time, uuid
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, '/app/backend')
from dotenv import load_dotenv
load_dotenv('/app/backend/.env')
from motor.motor_asyncio import AsyncIOMotorClient

ALTEA = '6867223e-7ea5-45a7-815a-300cd89b7656'
TESTI_DIR = Path('/app/backend/uploads/testimonials_ai')

REALISM = (
    "Hyperrealistic editorial portrait photography, NOT digital art, NOT cartoon, "
    "NOT 3D render, NOT painterly, NOT AI-looking. Real human skin texture with "
    "natural pores, fine wrinkles, asymmetric features, age spots where appropriate. "
    "Professional photography, 85mm f/1.8 lens, shallow depth of field, "
    "soft natural lighting, no over-saturation, no plastic skin. "
    "Documentary candid moment, real photograph aesthetic. "
)

PORTRAITS = [
    {
        "id": str(uuid.uuid4()), "name": "Sylvain B.", "city": "Toulouse", "age": 76,
        "rating": 5, "verified": True,
        "text": "Mon dos me jouait des tours depuis ma retraite. Avec le fauteuil, je me lève sans douleur, et l'inclinaison massante a remplacé mes séances chez le kiné. Un investissement qui change le quotidien.",
        "prompt": (f"{REALISM}"
            "Candid editorial portrait of a French man in his mid-70s sitting in a sunlit garden in southern France (Toulouse area). "
            "He has short white hair, a trimmed white moustache, light wrinkles, weathered tan skin from years outdoors, "
            "warm calm smile facing camera, kind blue-grey eyes. He wears a light blue linen short-sleeved shirt and beige chinos, "
            "holding pruning shears. Setting : Provençal-style garden with terracotta pots, lavender bushes, olive tree in background, "
            "warm afternoon golden sunlight from upper-left, ochre stone wall behind. "
            "Style : sun-drenched warm palette (terracotta, ochre, sage green), film grain, slight Mediterranean documentary feel, real photograph."),
    },
    {
        "id": str(uuid.uuid4()), "name": "Catherine R.", "city": "Genève", "age": 69,
        "rating": 5, "verified": True,
        "text": "Architecte d'intérieur, j'avais des exigences précises sur les matériaux et les lignes. Le fauteuil Altea s'est fondu dans mon salon contemporain comme une signature. Discret, ergonomique, élégant.",
        "prompt": (f"{REALISM}"
            "Candid editorial portrait of a Swiss-French woman aged 69 in a contemporary minimalist Geneva living room. "
            "She has chin-length straight grey hair (natural, well-kept), refined silver square-frame eyeglasses, "
            "elegant fine wrinkles, cheekbones visible, calm intelligent expression with a subtle confident smile, looking slightly away from camera (3/4 profile). "
            "She wears a soft cream cashmere turtleneck and dark slim trousers, sitting on a black leather Eames-style lounge chair. "
            "Setting : minimalist Geneva apartment with floor-to-ceiling glass windows showing mountain view in background (out of focus), "
            "concrete walls, modernist art piece, oak parquet, soft daylight diffused from the right. "
            "Style : Scandinavian editorial, Wallpaper magazine aesthetic, cool muted palette (grey, cream, charcoal), real photograph aesthetic."),
    },
    {
        "id": str(uuid.uuid4()), "name": "Roland L.", "city": "Lille", "age": 81,
        "rating": 5, "verified": True,
        "text": "À 81 ans, on n'a plus envie de se battre avec des télécommandes compliquées. Deux boutons, c'est parfait. Et le service après-vente m'a rappelé sous 4 heures pour un réglage. C'est rare aujourd'hui.",
        "prompt": (f"{REALISM}"
            "Candid editorial portrait of a French elderly man aged 81 sitting in a traditional French northern living room (Lille area). "
            "He has thinning white hair, a kind weathered face with deep natural wrinkles, a gentle thoughtful smile facing camera, warm brown eyes. "
            "He wears a beige cardigan over a striped shirt, holding a folded newspaper (La Voix du Nord). "
            "Setting : a traditional Belle Époque French interior — burgundy velvet armchair he is sitting in, dark wooden bookshelf with classical books, "
            "porcelain side lamp, oil paintings on flowery patterned wallpaper, lace doilies on the side table, "
            "soft afternoon window light from the left, cozy warm atmosphere. "
            "Style : northern French nostalgic warmth, soft muted vintage palette (burgundy, cream, gold), film grain, "
            "Robert Doisneau documentary aesthetic, real photograph."),
    },
]

async def main():
    from services.llm_resilience import safe_nano_banana_bytes
    c = AsyncIOMotorClient(os.environ['MONGO_URL'])
    db = c[os.environ.get('DB_NAME','altiaro_dev')]

    site = await db.sites.find_one({'id': ALTEA}, {'_id':0,'design.testimonials_premium':1})
    existing = (site.get('design',{}) or {}).get('testimonials_premium') or []
    print(f"Existing testimonials: {len(existing)} (cible : 6)")

    new_to_add = []
    t0 = time.time()
    for i, p in enumerate(PORTRAITS):
        try:
            print(f"\n[{i+1}/3] {p['name']} — {p['city']}")
            t1 = time.time()
            img = await safe_nano_banana_bytes(p['prompt'], timeout=180,
                request_id=f"lotG-fix1-{i}", session_id=f"lotG-fix1-{i}")
        except Exception as e:
            print(f"  ❌ {type(e).__name__}: {e}")
            continue
        if not img:
            print(f"  ⚠️  null after {time.time()-t1:.1f}s")
            continue
        fname = f"t_{ALTEA}_g6_{i}_{uuid.uuid4().hex[:8]}.png"
        (TESTI_DIR / fname).write_bytes(img)
        url = f"/api/uploads/testimonials_ai/{fname}"
        print(f"  ✅ {fname} ({len(img)}B) in {time.time()-t1:.1f}s")
        new_to_add.append({
            'id': p['id'], 'name': p['name'], 'city': p['city'], 'age': p['age'],
            'text': p['text'], 'rating': p['rating'], 'verified': p['verified'],
            'image': url,
            'image_regenerated_at': datetime.now(timezone.utc).isoformat(),
        })
    print(f"\nGenerated {len(new_to_add)}/3 in {time.time()-t0:.1f}s, ~${len(new_to_add)*0.20:.2f}")

    # Append au tableau existant pour avoir 6 témoins
    final = existing + new_to_add
    await db.sites.update_one({'id': ALTEA},
        {'$set': {'design.testimonials_premium': final}})
    print(f"DB updated: design.testimonials_premium count = {len(final)}")

asyncio.run(main())
