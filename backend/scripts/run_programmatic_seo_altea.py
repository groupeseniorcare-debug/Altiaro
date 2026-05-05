"""TÂCHE 3.1 — Lance la génération programmatic SEO en standalone.

Évite de saturer le worker FastAPI. À lancer en background avec :
    nohup python3 scripts/run_programmatic_seo_altea.py > /tmp/prog_seo.log 2>&1 &
"""
import asyncio
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, "/app/backend")

ALTEA_ID = "6867223e-7ea5-45a7-815a-300cd89b7656"


async def main():
    print(f"[prog_seo] {datetime.now(timezone.utc).isoformat()} START")
    from services.programmatic_seo import generate_programmatic_landings_for_site
    res = await generate_programmatic_landings_for_site(
        ALTEA_ID,
        max_per_product=30,
        concurrency=3,
        skip_if_exists=True,
        dry_run=False,
    )
    print(f"[prog_seo] DONE: {res}")


if __name__ == "__main__":
    asyncio.run(main())
