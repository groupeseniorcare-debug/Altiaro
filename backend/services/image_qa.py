"""Image QA & Source Analysis using Gemini Vision.

Phase 2.2 v3 hardening (2026-04-27 — user feedback) :

1. ANALYZE the source product image(s) once (multi-image consolidated call)
   to extract a `source_vision_lock` dict with 5 sub-fields :
     - product_kind            (precise category + sub-category)
     - material                (precise material with visible markers)
     - color                   (primary color + alt color observed)
     - silhouette_signature    (3-5 unique distinctive traits)
     - unique_features_visible (technical elements visible : remote, USB, etc.)
   These descriptors are then INJECTED into every per-style Nano Banana prompt
   to keep all 8 generated images materially, chromatically AND structurally
   consistent with the reference.

2. QA every generated image with 6 STRICT booleans :
     - is_same_product_silhouette
     - material_match_source
     - color_match_source
     - style_brief_respected
     - premium_quality
     - no_visual_bug
   Plus a short list of issues. Caller retries up to 3 times on failure.
   If still failing, image is NOT persisted and fallback to source AE image
   should be applied at the storefront level.

Cost note: ~0.005-0.01 USD per Gemini Flash vision call (cheap).
"""
from __future__ import annotations

import base64
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Sequence

logger = logging.getLogger("altiaro.image_qa")

GEMINI_VISION_MODEL = os.environ.get("GEMINI_VISION_MODEL", "gemini-2.5-flash")
GEMINI_VISION_USD_PER_CALL = 0.008  # rough avg, includes vision tokens

# 6 strict QA booleans — keys MUST match exactly the storefront/admin contract.
QA_CHECK_KEYS: List[str] = [
    "is_same_product_silhouette",
    "material_match_source",
    "color_match_source",
    "style_brief_respected",
    "premium_quality",
    "no_visual_bug",
]


def _strip_json_fence(text: str) -> str:
    return re.sub(r"^```(?:json)?\s*|\s*```$", "", (text or "").strip(), flags=re.MULTILINE).strip()


async def _call_gemini_vision_text(
    *,
    system: str,
    user: str,
    images_b64: Optional[Sequence[str]] = None,
    request_id: str,
    timeout: int = 30,
) -> str:
    """Single-shot Gemini vision call with N images. Returns the model's text response."""
    from emergentintegrations.llm.chat import ImageContent, LlmChat, UserMessage

    EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY")
    if not EMERGENT_LLM_KEY:
        raise RuntimeError("EMERGENT_LLM_KEY not set")

    chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=request_id, system_message=system)
    chat.with_model("gemini", GEMINI_VISION_MODEL)

    files = []
    for b64 in (images_b64 or []):
        if b64:
            files.append(ImageContent(image_base64=b64))

    msg = UserMessage(text=user, file_contents=files) if files else UserMessage(text=user)
    raw = await chat.send_message(msg)
    if isinstance(raw, str):
        return raw
    if isinstance(raw, dict):
        return raw.get("text") or raw.get("content") or json.dumps(raw)
    txt = getattr(raw, "text", None)
    return txt if isinstance(txt, str) else str(raw)


# -------------------------------------------------------------------------
# 1. SOURCE ANALYSIS — multi-image consolidated
# -------------------------------------------------------------------------
async def analyze_source_product_multi(
    reference_images_b64: Sequence[str],
    *,
    color_hint: Optional[str] = None,
    request_id: str = "qa-source-multi",
) -> Dict[str, Any]:
    """Multi-image Gemini Vision analysis to build a `source_vision_lock` dict
    with 5 sub-fields. Pass up to 6 source photos (AliExpress/CJ).

    Returns:
        {
          "product_kind":            "<2-12 words>",
          "material":                "<6-25 words, with visible markers>",
          "color":                   "<primary + alt observed>",
          "silhouette_signature":    "<3-5 distinctive traits, comma-separated>",
          "unique_features_visible": "<technical elements visible, comma-separated>",
          "raw":                     "<full JSON returned by the model>"  (debug)
        }
    """
    if not reference_images_b64:
        raise ValueError("analyze_source_product_multi: no reference images provided")

    # Cap to 6 images max to keep the call cheap & focused
    imgs = [b for b in reference_images_b64 if b][:6]
    n = len(imgs)

    color_line = (
        f"\nThe target color we will render is: {color_hint}. "
        f"Identify if this color is visible in the source images and describe it precisely. "
        f"Also list ALL OTHER colors observed across the source set."
        if color_hint else
        "\nList ALL colors observed across the source set."
    )

    system = (
        "You are a senior product analyst for a premium e-commerce brand. "
        "You receive several product photos of the SAME item (different angles, "
        "different stages, sometimes different colors of the same model). "
        "You must produce a SINGLE consolidated technical description in English, "
        "precise enough to drive an image generator to reproduce the EXACT same product. "
        "Output STRICT JSON only, no markdown, no commentary."
    )
    user = (
        f"You will see {n} reference photo(s) of the same product (same model, "
        f"possibly different colors/angles).{color_line}\n\n"
        "Output ONLY this JSON (no markdown):\n"
        "{\n"
        '  "product_kind": "<exact category + sub-category, 2-12 words. '
        'e.g.: \\"electric lift recliner armchair with massage function\\", '
        '\\"cordless electric blanket throw\\">",\n'
        '  "material": "<6-25 words. PRECISE material with VISIBLE MARKERS. '
        'Distinguish: real top-grain leather (visible pores, irregular grain) / '
        'PU leather (uniform plastic-like sheen, no pores) / microsuede / suede-like microfiber '
        '(matte, slight textile weave, no leather grain) / woven fabric / velvet / linen / canvas. '
        'e.g.: \\"suede-like microfiber fabric, matte finish, slight textile weave, no grain pattern, soft hand-feel appearance\\">",\n'
        '  "color": "<primary color in detail + alt colors observed across the set. '
        'e.g.: \\"primary: black charcoal matte ; alt observed: brown cognac, beige sand\\">",\n'
        '  "silhouette_signature": "<3-5 unique distinctive traits separated by \\" ; \\". '
        'These are the FORMAL traits that define the product identity. '
        'e.g.: \\"wide square armrests with stitched seams ; split backrest cushion with two vertical panels ; chrome metal base with 4 splayed legs ; integrated headrest with ergonomic curve ; capitonnage tufting on seat cushion only\\">",\n'
        '  "unique_features_visible": "<all visible technical elements, comma separated. '
        'e.g.: \\"wired remote control with 4 buttons, lift mechanism scissor on the base, USB charging port on right armrest, side pocket on left, no visible label\\">"\n'
        "}\n\n"
        "Be SPECIFIC and FACTUAL. Avoid generic words. If a feature is not visible, do not invent it. "
        "Distinguish leather vs PU leather vs microsuede vs fabric with visible markers."
    )

    raw = await _call_gemini_vision_text(
        system=system, user=user,
        images_b64=imgs,
        request_id=request_id,
        timeout=30,
    )
    cleaned = _strip_json_fence(raw)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]+\}", cleaned)
        if not m:
            raise ValueError(f"Vision response not parsable: {raw[:300]!r}")
        data = json.loads(m.group(0))

    out = {
        "product_kind":            str(data.get("product_kind") or "").strip()[:160] or "product",
        "material":                str(data.get("material") or "").strip()[:300] or "fabric upholstery",
        "color":                   str(data.get("color") or "").strip()[:200] or "neutral",
        "silhouette_signature":    str(data.get("silhouette_signature") or "").strip()[:600] or "",
        "unique_features_visible": str(data.get("unique_features_visible") or "").strip()[:400] or "",
    }
    logger.info(f"[image-qa] multi-source analysis {request_id} ({n} imgs): {out}")
    return out


# Backward-compat single-image wrapper (used by older callers)
async def analyze_source_product(
    reference_image_b64: str,
    *,
    request_id: str = "qa-source",
) -> Dict[str, str]:
    """Single-image wrapper around `analyze_source_product_multi`. Returns the
    legacy 3-key dict {material, color, product_kind} for backward compat.
    """
    full = await analyze_source_product_multi(
        [reference_image_b64], request_id=request_id,
    )
    return {
        "material":     full["material"][:120] or "fabric upholstery",
        "color":        full["color"][:80] or "neutral",
        "product_kind": full["product_kind"][:60] or "product",
    }


# -------------------------------------------------------------------------
# 2. QA — 6 strict booleans against the source_vision_lock
# -------------------------------------------------------------------------
async def qa_check_generated_image(
    *,
    generated_b64: str,
    reference_b64: str,
    style_slug: str,
    style_brief: str,
    expected_material: str,
    expected_color: str,
    silhouette_signature: str = "",
    unique_features_visible: str = "",
    request_id: str,
) -> Dict[str, Any]:
    """Compare a freshly generated image against the source reference and
    against the requested style brief. Returns a dict :

    {
      "all_pass": bool,
      "checks": {
        "is_same_product_silhouette": bool,
        "material_match_source":      bool,
        "color_match_source":         bool,
        "style_brief_respected":      bool,
        "premium_quality":            bool,
        "no_visual_bug":              bool,
      },
      "issues": ["..."]
    }
    """
    silhouette_block = (
        f"\nSilhouette signature (key formal traits that DEFINE this product): "
        f"{silhouette_signature}"
        if silhouette_signature else ""
    )
    features_block = (
        f"\nUnique features that should be visible (where applicable to the framing): "
        f"{unique_features_visible}"
        if unique_features_visible else ""
    )

    system = (
        "You are a strict art director QA-ing a generated product image against a "
        "reference photo and a precise style brief. Be ruthlessly honest. "
        "If the silhouette differs, if the material is substituted (e.g. fabric→leather "
        "or vice-versa), if the color drifts, or if the brief is not respected — say it. "
        "Output STRICT JSON only, no markdown."
    )
    user = (
        "REFERENCE IMAGE (image #1) and GENERATED IMAGE (image #2) attached.\n\n"
        "Locked attributes that MUST match between reference and generated:\n"
        f"- Material: {expected_material}\n"
        f"- Color:    {expected_color}"
        f"{silhouette_block}"
        f"{features_block}\n\n"
        f"Style brief for the GENERATED image (#2):\n"
        f"  Style slug: {style_slug}\n"
        f"  Brief:      {style_brief}\n\n"
        "Output ONLY this JSON (no markdown):\n"
        "{\n"
        '  "checks": {\n'
        '    "is_same_product_silhouette": <bool: same silhouette signature, '
        'same proportions, same key formal traits, same number of armrests/cushions, '
        'same base structure as reference>,\n'
        '    "material_match_source": <bool: same upholstery material as reference. '
        'CRITICAL — never substitute leather for fabric or fabric for leather. '
        'Match grain/texture/weave/sheen exactly>,\n'
        '    "color_match_source": <bool: same color and finish (matte/satin/glossy), '
        'same undertone as reference>,\n'
        '    "style_brief_respected": <bool: the generated image fulfills the brief. '
        "For in_use → person FULLY seated IN the chair (back against backrest, bottom on seat). "
        "For wide_lifestyle → 16:9 horizontal panoramic. For closeup → macro on material. "
        'Aspect ratio and framing must match>,\n'
        '    "premium_quality": <bool: editorial/catalog quality, professional composition, '
        'professional lighting, looks like a real photo from a high-end magazine>,\n'
        '    "no_visual_bug": <bool: no extra/missing limbs, no warped or asymmetric proportions, '
        'no missing armrests, no ghost elements, no double objects, no distorted hands or face, '
        'no impossible geometry>\n'
        "  },\n"
        '  "issues": ["short bullet 1", "short bullet 2", ...]   // empty list if all pass\n'
        "}\n"
    )
    try:
        raw = await _call_gemini_vision_text(
            system=system, user=user,
            images_b64=[reference_b64, generated_b64],
            request_id=request_id,
            timeout=30,
        )
    except Exception as e:
        logger.warning(f"[image-qa] Vision call failed for {request_id}: {str(e)[:200]}")
        # Fail-CLOSED policy (Phase 2.2 v3) : on Vision outage we now REJECT
        # the image rather than waving it through, to prevent silent regressions.
        # Caller will retry; if persistent, the image will not be persisted.
        return {
            "all_pass": False,
            "checks": {k: False for k in QA_CHECK_KEYS},
            "issues": [f"vision_qa_unavailable: {str(e)[:120]}"],
            "vision_qa_skipped": True,
        }

    cleaned = _strip_json_fence(raw)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]+\}", cleaned)
        if not m:
            logger.warning(f"[image-qa] Vision response not JSON: {raw[:200]!r}")
            return {
                "all_pass": False,
                "checks": {k: False for k in QA_CHECK_KEYS},
                "issues": ["vision_qa_unparsable"],
            }
        data = json.loads(m.group(0))

    checks_raw = data.get("checks") or {}
    checks = {k: bool(checks_raw.get(k, False)) for k in QA_CHECK_KEYS}
    issues = data.get("issues") or []
    if not isinstance(issues, list):
        issues = [str(issues)]
    issues = [str(i)[:240] for i in issues if i][:8]

    all_pass = all(checks.values())
    return {"all_pass": all_pass, "checks": checks, "issues": issues}


__all__ = [
    "analyze_source_product",
    "analyze_source_product_multi",
    "qa_check_generated_image",
    "GEMINI_VISION_USD_PER_CALL",
    "QA_CHECK_KEYS",
]
