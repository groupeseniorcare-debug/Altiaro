"""Test direct du nouveau helper DS aliexpress.ds.product.get.
Usage : python3 /app/backend/scripts/debug_ae_ds.py
"""
import asyncio
import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
load_dotenv(Path(__file__).resolve().parent.parent / ".env")


async def main():
    from routes.sourcing import _ae_ds_product_detail
    from routes.aliexpress import _signed_post, SYNC_API_URL

    test_pids = [
        "1005005817186631",  # PID réel présent dans ae_deals_history
        "1005008472011766",  # idem
        "1005006840516334",  # PID du user (peut-être retiré)
    ]
    for pid in test_pids:
        print(f"\n=== TEST pid={pid} ===")
        # 1. appel brut pour voir la réponse
        try:
            raw = await _signed_post(
                SYNC_API_URL,
                {
                    "method": "aliexpress.ds.product.get",
                    "product_id": pid,
                    "ship_to_country": "FR",
                    "target_currency": "USD",
                    "target_language": "EN",
                },
                site_id=None,
            )
            # Montre les clés top-level + extrait base_info
            print("top keys:", list(raw.keys()))
            payload = raw.get("aliexpress_ds_product_get_response") or raw
            result = payload.get("result") or payload
            base = result.get("ae_item_base_info_dto") or {}
            if base:
                print("subject:", base.get("subject"))
                print("sale_price:", base.get("sale_price"))
                print("currency_code:", base.get("currency_code"))
                print("main_image_url:", (base.get("main_image_url") or "")[:80])
            else:
                print("RAW RESULT (300c):", json.dumps(result, indent=2, ensure_ascii=False)[:300])
        except Exception as e:
            print(f"EXCEPTION raw: {type(e).__name__}: {str(e)[:300]}")

        # 2. appel via notre helper normalisé
        try:
            detail = await _ae_ds_product_detail(pid, site_id=None)
            if detail:
                print("  normalised OK →")
                print(f"    title      : {detail['title'][:80]}")
                print(f"    cost_usd   : {detail['cost_usd']}")
                print(f"    sku        : {detail['sku']}")
                print(f"    images     : {len(detail['images'])} URLs, first = {(detail['main_image'] or '')[:60]}")
            else:
                print("  normalised → None (product not found)")
        except Exception as e:
            print(f"  EXCEPTION normalised: {type(e).__name__}: {str(e)[:300]}")


if __name__ == "__main__":
    asyncio.run(main())
