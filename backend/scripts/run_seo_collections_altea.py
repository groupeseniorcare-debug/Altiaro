"""TÂCHE 3.4 — Lance l'enrichissement des collections SEO sur Altea."""
import asyncio
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, "/app/backend")

ALTEA_ID = "6867223e-7ea5-45a7-815a-300cd89b7656"


async def main():
    print(f"[col_seo] {datetime.now(timezone.utc).isoformat()} START")
    from services.seo_collections import enrich_collections_seo
    res = await enrich_collections_seo(
        ALTEA_ID, generate_derived=True, concurrency=2,
    )
    print(f"[col_seo] DONE: {res}")


if __name__ == "__main__":
    asyncio.run(main())
