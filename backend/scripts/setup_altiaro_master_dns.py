"""URGENT 1 — Pose le TXT DNS de vérification Google sur altiaro.com via OVH.

Usage : python -m scripts.setup_altiaro_master_dns [--domain altiaro.com] [--token ...]
"""
from __future__ import annotations
import argparse
import asyncio
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("altiaro.dns_setup")

from deps import db  # noqa: E402


def _ovh_client():
    import ovh
    return ovh.Client(
        endpoint=os.environ.get("OVH_ENDPOINT") or "ovh-eu",
        application_key=os.environ.get("OVH_APP_KEY"),
        application_secret=os.environ.get("OVH_APP_SECRET"),
        consumer_key=os.environ.get("OVH_CONSUMER_KEY"),
    )


async def add_txt_record(domain: str, target: str, sub_domain: str = "", ttl: int = 3600) -> dict:
    """Add (or skip if already present) a TXT record on the OVH zone of `domain`.

    Returns a dict {created: bool, record_id, existing_ids, refresh_ok}.
    """
    import ovh.exceptions
    client = _ovh_client()

    # 1) List existing records
    existing_ids = await asyncio.to_thread(
        client.get,
        f"/domain/zone/{domain}/record",
        fieldType="TXT",
        subDomain=sub_domain,
    )
    for rid in existing_ids or []:
        try:
            r = await asyncio.to_thread(client.get, f"/domain/zone/{domain}/record/{rid}")
            if (r or {}).get("target", "").strip().strip('"') == target.strip().strip('"'):
                logger.info(f"[ovh] TXT already present on {domain} (id={rid}) — skipping")
                # Still refresh in case a previous run left zone dirty
                try:
                    await asyncio.to_thread(client.post, f"/domain/zone/{domain}/refresh")
                except Exception:
                    pass
                return {"created": False, "record_id": rid, "existing_ids": existing_ids, "refresh_ok": True}
        except Exception:
            continue

    # 2) Create it
    try:
        created = await asyncio.to_thread(
            client.post, f"/domain/zone/{domain}/record",
            fieldType="TXT", subDomain=sub_domain, target=target, ttl=ttl,
        )
    except ovh.exceptions.APIError as e:
        logger.exception("[ovh] TXT create failed")
        raise RuntimeError(f"OVH TXT create failed: {e}") from e
    logger.info(f"[ovh] TXT created : id={created.get('id')} on {domain}")

    # 3) Refresh zone
    refresh_ok = True
    try:
        await asyncio.to_thread(client.post, f"/domain/zone/{domain}/refresh")
        logger.info(f"[ovh] zone {domain} refresh triggered")
    except Exception as e:
        logger.warning(f"[ovh] refresh failed (non-blocking) : {e}")
        refresh_ok = False

    return {"created": True, "record_id": created.get("id"), "existing_ids": existing_ids, "refresh_ok": refresh_ok}


async def verify_txt_propagated(domain: str, expected_substring: str, attempts: int = 6) -> bool:
    """Wait until DNS has propagated (best-effort, doesn't block forever)."""
    try:
        import dns.resolver  # type: ignore
    except Exception:
        logger.warning("[verify] dnspython not installed — skipping local check")
        return False
    resolver = dns.resolver.Resolver()
    resolver.nameservers = ["8.8.8.8", "1.1.1.1"]
    for i in range(attempts):
        try:
            answers = resolver.resolve(domain, "TXT", lifetime=4)
            for r in answers:
                txt = b"".join(r.strings).decode(errors="ignore") if hasattr(r, "strings") else str(r)
                if expected_substring in txt:
                    logger.info(f"[verify] TXT propagated after {i + 1} attempts")
                    return True
        except Exception as e:
            logger.info(f"[verify] attempt {i+1}/{attempts} : {e}")
        await asyncio.sleep(10)
    logger.warning("[verify] TXT not propagated yet (Google's verifier may still succeed via authoritative resolution)")
    return False


async def run(domain: str, token: str) -> dict:
    target = f'"google-site-verification={token}"'
    txt_target_raw = f"google-site-verification={token}"
    res = await add_txt_record(domain=domain, target=target)
    propagated = await verify_txt_propagated(domain, txt_target_raw, attempts=4)
    payload = {
        "provider": "ovh",
        "domain": domain,
        "records": [{
            "type": "TXT",
            "sub_domain": "",
            "target": target,
            "ttl": 3600,
            "id": res.get("record_id"),
            "created": res.get("created"),
        }],
        "propagation_observed": propagated,
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "google_token": token,
    }
    await db.platform_settings.update_one(
        {"key": "dns_master_verification"},
        {"$set": {"key": "dns_master_verification", **payload}},
        upsert=True,
    )
    return payload


async def _main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--domain", default="altiaro.com")
    parser.add_argument("--token",
                        default=os.environ.get("GOOGLE_SITE_VERIFICATION_ALTIARO", ""))
    args = parser.parse_args()
    if not args.token:
        raise SystemExit("GOOGLE_SITE_VERIFICATION_ALTIARO missing in env (or --token).")
    out = await run(args.domain, args.token)
    print("---DNS RESULT---")
    import json
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(_main())
