"""Test direct _ae_call pour diagnostiquer l'erreur 'produit introuvable'.
Usage : python3 /app/backend/scripts/debug_ae_call.py"""
import asyncio
import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

# Ensure backend root on path so we can import sourcing helpers
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# 3 tests — 1 PID réel (populaire AliExpress) + 1 URL mobile + 1 link court
TEST_PIDS = [
    "1005006840516334",  # URL donnée par le user
    "3256805672410600",  # PID aléatoire qui devrait exister
]


async def main():
    from routes.sourcing import _ae_call, AE_APP_KEY, AE_APP_SECRET, AE_TRACKING_ID, AE_BASE
    print(f"AE_APP_KEY      : {AE_APP_KEY[:6] + '***' if AE_APP_KEY else 'MISSING'}")
    print(f"AE_APP_SECRET   : {'set (' + str(len(AE_APP_SECRET)) + ' chars)' if AE_APP_SECRET else 'MISSING'}")
    print(f"AE_TRACKING_ID  : {AE_TRACKING_ID or '(empty)'}")
    print(f"AE_BASE         : {AE_BASE}")
    print()

    for pid in TEST_PIDS:
        print(f"=== TEST pid={pid} ===")
        try:
            resp = await _ae_call(
                "aliexpress.affiliate.productdetail.get",
                {
                    "product_ids": pid,
                    "target_currency": "USD",
                    "target_language": "EN",
                    "tracking_id": AE_TRACKING_ID or "default",
                },
            )
            print("keys at root:", list(resp.keys())[:5])
            print("FULL RAW RESPONSE (truncated 1500c):")
            print(json.dumps(resp, indent=2, ensure_ascii=False)[:1500])
        except Exception as e:
            print(f"EXCEPTION: {type(e).__name__}: {e}")
        print()


if __name__ == "__main__":
    asyncio.run(main())
