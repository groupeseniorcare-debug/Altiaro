"""X1 — Back-fill contenu IA sur les 8 produits Altea (hors pilote).

Pour chaque produit :
  1. Analyse Vision multi-images source → source_vision_lock (5 sous-champs)
  2. Régen USPs (Haiku, ancré Vision + matériau canonique FR + termes interdits)
  3. Régen HowTo (Haiku, 3-4 étapes, ancrées Vision)
  4. Régen FAQ (Haiku, 5 Q/R, sujets livraison/retours/garantie interdits)
  5. Patch narrative.subheadline + description pour remplacer termes incohérents
     par le matériau canonique FR (microsuède → cuir synthétique, etc.)

Idempotent (overwrite=True). Budget cap hardcodé 1,50 $ (marge).

Usage :
    cd /app/backend && python -m scripts.x1_backfill_altea_content 2>&1 | tee /tmp/x1.log
"""
from __future__ import annotations
import asyncio
import base64
import io
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Add backend/ to sys.path so we can import services
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv  # noqa: E402
load_dotenv(str(Path(__file__).resolve().parent.parent / ".env"))

import httpx  # noqa: E402
from motor.motor_asyncio import AsyncIOMotorClient  # noqa: E402
from PIL import Image  # noqa: E402

from services.image_qa import analyze_source_product_multi  # noqa: E402
from services.product_content_ai import (  # noqa: E402
    generate_product_usps,
    generate_product_how_to,
    generate_product_faq,
)

SITE_ID = "6867223e-7ea5-45a7-815a-300cd89b7656"
PILOT_ID = "2a31bb75-4dcf-424d-ab2f-cda6b88303fb"
BUDGET_CAP_USD = 1.50

# Rough cost estimates (used only for cap tracking)
COST = {
    "vision_multi": 0.010,
    "haiku_usps":    0.005,
    "haiku_howto":   0.004,
    "haiku_faq":     0.006,
}


def _canonical_mat_fr(mat_en: str) -> tuple[str, list[str]]:
    """Maps English Vision-detected material to canonical French label +
    list of FORBIDDEN terms (incoherent synonyms) for this material family.
    Returns (canonical_fr, forbidden_fr_terms)."""
    if not mat_en:
        return ("", [])
    m = mat_en.lower()
    if "pu leather" in m or ("leather" in m and "real" not in m and "top-grain" not in m and "genuine" not in m):
        return ("cuir synthétique", ["microsuède", "microsuede", "microfibre", "suède", "velours", "lin", "tissu"])
    if "top-grain" in m or "real leather" in m or "genuine leather" in m:
        return ("cuir véritable", ["microsuède", "microsuede", "microfibre", "PU", "simili", "tissu"])
    if "microsuede" in m or "suede-like" in m or "microfiber suede" in m:
        return ("microsuède", ["cuir", "leather", "velours", "lin"])
    if "velvet" in m:
        return ("velours", ["cuir", "leather", "microsuède", "tissu uni"])
    if "linen" in m:
        return ("lin", ["cuir", "leather", "PU", "microsuède", "velours"])
    if "cotton" in m:
        return ("coton", ["cuir", "leather", "PU", "microsuède"])
    if "flannel" in m or "sherpa" in m or "fleece" in m:
        return ("flanelle doublée sherpa", ["cuir", "leather", "PU"])
    if "woven" in m or "fabric" in m:
        return ("tissu", ["cuir", "leather", "PU", "simili", "microsuède"])
    if "foam" in m or "memory foam" in m:
        return ("mousse à mémoire de forme", ["cuir", "leather", "PU", "microsuède"])
    if "polyester" in m or "poly" in m:
        return ("polyester tissé", ["cuir", "leather", "PU", "microsuède"])
    return ("", [])


async def _fetch_image_b64(url: str, timeout: float = 12.0) -> str | None:
    """Download an image and return its base64 string (max 3 MB, re-encoded)."""
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=timeout) as client:
            r = await client.get(url)
            r.raise_for_status()
            raw = r.content
            # Re-encode via PIL to normalize + shrink
            img = Image.open(io.BytesIO(raw)).convert("RGB")
            img.thumbnail((1024, 1024))
            out = io.BytesIO()
            img.save(out, format="JPEG", quality=85)
            return base64.b64encode(out.getvalue()).decode("ascii")
    except Exception as e:
        print(f"    [img fetch err] {url[:80]} :: {str(e)[:120]}")
        return None


def _patch_legacy_narrative(text: str, canonical_fr: str, forbidden: list[str]) -> tuple[str, int]:
    """Replace forbidden terms in a legacy narrative string with the
    canonical material FR. Returns (new_text, n_replacements)."""
    if not text or not canonical_fr:
        return (text, 0)
    new = text
    n = 0
    for f in forbidden:
        # Match 'microsuède' (with or without accents, case-insensitive) as whole word
        pat = re.compile(rf"\b{re.escape(f)}\b", re.IGNORECASE)
        new, k = pat.subn(canonical_fr, new)
        n += k
    return (new, n)


async def run():
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[os.environ.get("DB_NAME", "altiaro_dev")]

    cursor = db.products.find(
        {"site_id": SITE_ID, "status": "active", "id": {"$ne": PILOT_ID}},
        {"_id": 0},
    )
    products = await cursor.to_list(50)
    print(f"==== X1 Back-fill — {len(products)} produits cibles ====")

    # Fetch brand once (site design)
    site = await db.sites.find_one({"id": SITE_ID}, {"_id": 0, "design.brand": 1})
    brand = ((site or {}).get("design") or {}).get("brand") or {}

    total_cost = 0.0
    summary = []

    for idx, p in enumerate(products, 1):
        pid = p["id"]
        nm = p.get("name") or {}
        nm_fr = nm.get("fr") if isinstance(nm, dict) else nm
        print(f"\n---- [{idx}/8] {pid[:8]}  {(nm_fr or '')[:60]} ----")

        row = {"id": pid, "name": nm_fr, "svl_material": None, "canonical_fr": None,
               "usps_ok": False, "howto_ok": False, "faq_ok": False,
               "patched_subheadline": 0, "patched_description": 0, "cost": 0.0}

        # ========== STEP 1 : Vision multi-source ==========
        try:
            srcs = []
            for u in (p.get("original_images") or p.get("images") or [])[:6]:
                if isinstance(u, str) and u:
                    srcs.append(u)
            if not srcs and p.get("original_image"):
                srcs.append(p["original_image"])

            b64s = []
            for u in srcs[:6]:
                b = await _fetch_image_b64(u)
                if b:
                    b64s.append(b)
            if not b64s:
                raise RuntimeError("no source images downloadable")

            # use color hint from first variant if any
            variants = p.get("variants") or []
            color_hint = None
            if variants and isinstance(variants[0], dict):
                props = variants[0].get("properties") or []
                if props and props[0]:
                    color_hint = str(props[0])

            svl = await analyze_source_product_multi(
                b64s, color_hint=color_hint, request_id=f"x1-svl-{pid[:8]}",
            )
            await db.products.update_one(
                {"id": pid},
                {"$set": {
                    "source_vision_lock": svl,
                    "source_vision_lock_updated_at": datetime.now(timezone.utc).isoformat(),
                    "source_vision_lock_n_images": len(b64s),
                }},
            )
            total_cost += COST["vision_multi"]
            row["cost"] += COST["vision_multi"]
            row["svl_material"] = svl.get("material", "")[:120]
            print(f"  [1] Vision multi({len(b64s)} src) material={svl.get('material','')[:100]!r}")

            canonical_fr, forbidden = _canonical_mat_fr(svl.get("material", ""))
            row["canonical_fr"] = canonical_fr or "(no mapping)"
        except Exception as e:
            print(f"  [1] ❌ Vision failed: {str(e)[:200]}")
            svl = {}
            canonical_fr, forbidden = ("", [])

        # Re-fetch the product (now has source_vision_lock)
        fresh = await db.products.find_one({"id": pid}, {"_id": 0})

        # ========== STEP 2 : USPs ==========
        try:
            usps = await generate_product_usps(fresh, brand, request_id=f"x1-usps-{pid[:8]}")
            if usps and len(usps) >= 3:
                max_title = max(len(u.get("title", "")) for u in usps)
                max_desc = max(len(u.get("description", "")) for u in usps)
                # Check coherence : no forbidden term in title+desc
                text_blob = " ".join(u.get("title", "") + " " + u.get("description", "") for u in usps).lower()
                has_forbidden = any(f.lower() in text_blob for f in forbidden)
                if has_forbidden:
                    print(f"  [2] ⚠️ USPs contain forbidden term after Haiku")
                await db.products.update_one(
                    {"id": pid},
                    {"$set": {
                        "usps": usps,
                        "usps_generated_at": datetime.now(timezone.utc).isoformat(),
                    }},
                )
                total_cost += COST["haiku_usps"]
                row["cost"] += COST["haiku_usps"]
                row["usps_ok"] = True
                row["usps_max_title"] = max_title
                row["usps_max_desc"] = max_desc
                row["usps_forbidden"] = has_forbidden
                print(f"  [2] USPs: {len(usps)} items, max_title={max_title}, max_desc={max_desc}, forbidden={has_forbidden}")
        except Exception as e:
            print(f"  [2] ❌ USPs failed: {str(e)[:200]}")

        # ========== STEP 3 : HowTo (Phase 2.6 Tâche C — adaptatif kind) ==========
        try:
            howto = await generate_product_how_to(fresh, brand, n_steps=4, request_id=f"x1-howto-{pid[:8]}")
            steps = (howto or {}).get("steps") or []
            meta = {
                "section_title": (howto or {}).get("section_title") or {},
                "product_kind":  (howto or {}).get("product_kind") or "generic",
            }
            if steps and len(steps) >= 3:
                text_blob = " ".join(s.get("title", "") + " " + s.get("description", "") for s in steps).lower()
                has_forbidden = any(f.lower() in text_blob for f in forbidden)
                await db.products.update_one(
                    {"id": pid},
                    {"$set": {
                        "how_to_steps": steps,
                        "how_to_steps_meta": meta,
                        "how_to_steps_generated_at": datetime.now(timezone.utc).isoformat(),
                    }},
                )
                total_cost += COST["haiku_howto"]
                row["cost"] += COST["haiku_howto"]
                row["howto_ok"] = True
                row["howto_forbidden"] = has_forbidden
                row["howto_kind"] = meta["product_kind"]
                print(f"  [3] HowTo: {len(steps)} steps (kind={meta['product_kind']}), forbidden={has_forbidden}")
        except Exception as e:
            print(f"  [3] ❌ HowTo failed: {str(e)[:200]}")

        # ========== STEP 4 : FAQ ==========
        try:
            faq = await generate_product_faq(fresh, brand, n_questions=5, request_id=f"x1-faq-{pid[:8]}")
            if faq and len(faq) >= 3:
                text_blob = " ".join(f.get("question", "") + " " + f.get("answer", "") for f in faq).lower()
                has_forbidden = any(t.lower() in text_blob for t in forbidden)
                await db.products.update_one(
                    {"id": pid},
                    {"$set": {
                        "faq_product": faq,
                        "faq_product_generated_at": datetime.now(timezone.utc).isoformat(),
                    }},
                )
                total_cost += COST["haiku_faq"]
                row["cost"] += COST["haiku_faq"]
                row["faq_ok"] = True
                row["faq_forbidden"] = has_forbidden
                print(f"  [4] FAQ: {len(faq)} items, forbidden={has_forbidden}")
        except Exception as e:
            print(f"  [4] ❌ FAQ failed: {str(e)[:200]}")

        # ========== STEP 5 : Patch narrative legacy ==========
        if canonical_fr and forbidden:
            patches = {}
            # subheadline (dict {fr,en,de,...})
            sh = (fresh.get("narrative") or {}).get("subheadline") or {}
            if isinstance(sh, dict):
                sh_fr = sh.get("fr", "")
                new_sh, n_sh = _patch_legacy_narrative(sh_fr, canonical_fr, forbidden)
                if n_sh:
                    patches["narrative.subheadline.fr"] = new_sh
                    row["patched_subheadline"] = n_sh
                    print(f"  [5] patched narrative.subheadline.fr ({n_sh} replacements)")

            # description (sometimes dict, sometimes plain string)
            desc = fresh.get("description")
            if isinstance(desc, dict):
                desc_fr = desc.get("fr", "")
                new_desc, n_desc = _patch_legacy_narrative(desc_fr, canonical_fr, forbidden)
                if n_desc:
                    patches["description.fr"] = new_desc
                    row["patched_description"] = n_desc
                    print(f"  [5] patched description.fr ({n_desc} replacements)")
            elif isinstance(desc, str) and desc:
                new_desc, n_desc = _patch_legacy_narrative(desc, canonical_fr, forbidden)
                if n_desc:
                    patches["description"] = new_desc
                    row["patched_description"] = n_desc
                    print(f"  [5] patched description ({n_desc} replacements)")

            if patches:
                patches["narrative_legacy_patched_at"] = datetime.now(timezone.utc).isoformat()
                await db.products.update_one({"id": pid}, {"$set": patches})

        summary.append(row)

        # Budget cap check
        if total_cost > BUDGET_CAP_USD:
            print(f"\n⚠️ BUDGET CAP HIT at {total_cost:.3f} USD, stopping.")
            break

        # Gentle rate-limit pause between products
        await asyncio.sleep(1.5)

    print(f"\n==== SUMMARY — total_cost={total_cost:.3f} USD ====\n")
    print(f"{'id':10} {'canonical_fr':22} usps howto faq  patch_sh patch_desc forbidden")
    for r in summary:
        any_forbidden = any([r.get("usps_forbidden"), r.get("howto_forbidden"), r.get("faq_forbidden")])
        print(f"  {r['id'][:8]} {(r.get('canonical_fr') or '')[:22]:22} "
              f"{'✅' if r['usps_ok'] else '❌'}   "
              f"{'✅' if r['howto_ok'] else '❌'}    "
              f"{'✅' if r['faq_ok'] else '❌'}   "
              f"{r.get('patched_subheadline',0):4d}    {r.get('patched_description',0):4d}      "
              f"{'⚠️' if any_forbidden else '—'}")

    # persist a json report for the main agent
    with open("/tmp/x1_report.json", "w") as f:
        json.dump({"summary": summary, "total_cost_usd": total_cost}, f, indent=2, ensure_ascii=False)
    print(f"\nReport written to /tmp/x1_report.json")


if __name__ == "__main__":
    asyncio.run(run())
