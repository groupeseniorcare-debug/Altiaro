"""
Phase 3 — Seed de traductions pour les produits d'un site de démo.

Ajoute `translations = {en: {name, description, short_description},
                       nl: {...}, de: {...}}` sur les produits actifs d'un site.

Pour le demo, on utilise des traductions statiques pré-écrites (pas d'appel LLM
pour garder l'idempotence et éviter les coûts). Le endpoint POST
/blog-posts/{slug}/translate reste la voie normale en prod — ici on fabrique
juste des data de test pour l'UI.

Usage :
  cd /app/backend
  python -m scripts.seed_product_translations <site_id>
  python -m scripts.seed_product_translations <site_id> --revert
"""
import argparse
import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))
load_dotenv(BACKEND_DIR / ".env")

from motor.motor_asyncio import AsyncIOMotorClient  # noqa: E402


# Bibliothèque de traductions canoniques pour les produits de test du site
# Fauteuil releveur (Silver Economy). Trois "modèles" génériques couvrent les
# produits seedés par force_site_validated.py.
TEMPLATES = {
    1: {
        "fr": {"name": "Fauteuil releveur premium",
               "short_description": "Assistance électrique, assise ergonomique, garantie 2 ans.",
               "description": "Un fauteuil releveur conçu pour le confort quotidien des seniors. Moteur silencieux, position zero-gravity, télécommande intuitive."},
        "en": {"name": "Premium lift chair",
               "short_description": "Powered lift, ergonomic seat, 2-year warranty.",
               "description": "A lift recliner designed for daily senior comfort. Silent motor, zero-gravity position, intuitive remote."},
        "nl": {"name": "Premium sta-op stoel",
               "short_description": "Elektrische hulp, ergonomische zitting, 2 jaar garantie.",
               "description": "Een sta-op fauteuil voor dagelijks comfort bij senioren. Geluidsarme motor, zero-gravity stand, intuïtieve afstandsbediening."},
        "de": {"name": "Premium-Aufstehsessel",
               "short_description": "Elektrische Aufstehhilfe, ergonomischer Sitz, 2 Jahre Garantie.",
               "description": "Ein Aufstehsessel für den täglichen Komfort von Senioren. Leiser Motor, Zero-Gravity-Position, intuitive Fernbedienung."},
        "it": {"name": "Poltrona alzapersona premium",
               "short_description": "Sollevamento elettrico, seduta ergonomica, garanzia 2 anni.",
               "description": "Una poltrona alzapersona pensata per il comfort quotidiano dei senior. Motore silenzioso, posizione zero-gravity, telecomando intuitivo."},
        "es": {"name": "Sillón elevador premium",
               "short_description": "Elevación eléctrica, asiento ergonómico, garantía de 2 años.",
               "description": "Sillón elevador diseñado para el confort diario de personas mayores. Motor silencioso, posición cero-gravedad, mando intuitivo."},
    },
    2: {
        "fr": {"name": "Matelas médicalisé confort",
               "short_description": "Mousse à mémoire, housse anti-allergène, remboursement LPPR possible.",
               "description": "Matelas médicalisé adapté au maintien à domicile. Mousse à mémoire de forme haute densité et housse lavable anti-allergène."},
        "en": {"name": "Medical comfort mattress",
               "short_description": "Memory foam, anti-allergen cover, possible NHS reimbursement.",
               "description": "Medical mattress suitable for home care. High-density memory foam and washable anti-allergen cover."},
        "nl": {"name": "Medisch comfort matras",
               "short_description": "Traagschuim, anti-allergeen hoes, mogelijk vergoeding.",
               "description": "Medisch matras geschikt voor thuiszorg. Hoge dichtheid traagschuim en wasbare anti-allergeen hoes."},
        "de": {"name": "Medizinische Komfortmatratze",
               "short_description": "Memory-Schaum, Anti-Allergen-Bezug, Kassenzuschuss möglich.",
               "description": "Medizinische Matratze für die häusliche Pflege. Hochdichter Memory-Schaum und waschbarer Anti-Allergen-Bezug."},
        "it": {"name": "Materasso medicale comfort",
               "short_description": "Memory foam, fodera anti-allergene, rimborso SSN possibile.",
               "description": "Materasso medicale per assistenza domiciliare. Memory foam ad alta densità e fodera lavabile anti-allergene."},
        "es": {"name": "Colchón médico confort",
               "short_description": "Espuma viscoelástica, funda hipoalergénica, posible reembolso.",
               "description": "Colchón médico adecuado para atención domiciliaria. Espuma viscoelástica de alta densidad y funda lavable hipoalergénica."},
    },
    3: {
        "fr": {"name": "Barre d'appui salle de bain",
               "short_description": "Installation sans perçage, charge max 120kg, inox brossé.",
               "description": "Barre d'appui premium pour salle de bain. Fixation ventouse haute performance, sans perçage, installation en 5 minutes."},
        "en": {"name": "Bathroom grab bar",
               "short_description": "No-drill install, max load 120kg, brushed stainless steel.",
               "description": "Premium bathroom grab bar. High-performance suction mount, no drilling, 5-minute install."},
        "nl": {"name": "Handgreep badkamer",
               "short_description": "Installatie zonder boren, max 120kg, geborsteld RVS.",
               "description": "Premium handgreep voor de badkamer. Krachtige zuignapbevestiging, zonder boren, installatie in 5 minuten."},
        "de": {"name": "Badezimmer-Haltegriff",
               "short_description": "Ohne Bohren, max. 120 kg, gebürsteter Edelstahl.",
               "description": "Premium-Haltegriff für das Badezimmer. Hochleistungs-Saugnapfhalterung, kein Bohren, Montage in 5 Minuten."},
        "it": {"name": "Maniglione da bagno",
               "short_description": "Installazione senza forare, max 120kg, acciaio spazzolato.",
               "description": "Maniglione premium da bagno. Fissaggio a ventosa ad alte prestazioni, senza forare, installato in 5 minuti."},
        "es": {"name": "Barra de apoyo para baño",
               "short_description": "Instalación sin taladrar, máx 120kg, acero inoxidable cepillado.",
               "description": "Barra de apoyo premium para baño. Fijación por ventosa de alto rendimiento, sin taladrar, instalación en 5 minutos."},
    },
}


async def seed(site_id: str, revert: bool) -> None:
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]

    products = await db.products.find(
        {"site_id": site_id, "status": "active"},
        {"_id": 0, "id": 1, "name": 1, "translations": 1},
    ).sort("created_at", 1).to_list(length=50)

    if not products:
        print(f"ERROR: no active products found for site {site_id}")
        return

    if revert:
        n = await db.products.update_many(
            {"site_id": site_id, "translations": {"$exists": True}},
            {"$unset": {"translations": ""}},
        )
        print(f"✓ Removed translations from {n.modified_count} products of site {site_id}")
        return

    now = datetime.now(timezone.utc).isoformat()
    updated = 0
    for idx, p in enumerate(products):
        template_idx = (idx % 3) + 1       # 1, 2, 3, 1, 2, 3...
        tpl = TEMPLATES[template_idx]
        translations = {}
        for lg in ("en", "nl", "de", "it", "es"):
            translations[lg] = {
                **tpl[lg],
                "translated_at": now,
            }
        # Also unify `name`/`description` in dict style if not already (so
        # pickLang() finds them for current products pattern)
        current_name = p.get("name")
        current_name_fr = (
            current_name if isinstance(current_name, str)
            else (current_name or {}).get("fr") or tpl["fr"]["name"]
        )
        set_fields = {
            "translations": translations,
            "name": {"fr": current_name_fr, **{lg: tpl[lg]["name"] for lg in ("en", "nl", "de", "it", "es")}},
            "description": {"fr": tpl["fr"]["description"], **{lg: tpl[lg]["description"] for lg in ("en", "nl", "de", "it", "es")}},
            "short_description": {"fr": tpl["fr"]["short_description"], **{lg: tpl[lg]["short_description"] for lg in ("en", "nl", "de", "it", "es")}},
        }
        await db.products.update_one({"id": p["id"]}, {"$set": set_fields})
        updated += 1

    print(f"✓ Seeded translations for {updated} products of site {site_id}")
    print(f"  Languages: en, nl, de, it, es (fr preserved as source)")
    print(f"  Pattern   : product.translations.{{lang}} + product.name.{{lang}} (dict legacy)")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("site_id")
    parser.add_argument("--revert", action="store_true")
    args = parser.parse_args()
    asyncio.run(seed(args.site_id, args.revert))


if __name__ == "__main__":
    main()
