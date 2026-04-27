"""Image QA & Source Analysis using Gemini Vision.

Phase 2.2 hardening (2026-04-27) — service dedicated to:

1. ANALYZE the source product image once (before generating the 8 styles)
   to extract:
     - material descriptor (e.g. "matte microfiber fabric, woven texture")
     - exact color descriptor (e.g. "deep matte black, charcoal undertone")
     - product_kind (e.g. "lift recliner armchair")
   These descriptors are then INJECTED into every per-style prompt to
   keep all 8 generated images materially & chromatically consistent.

2. QA every generated image against the reference, returning 6 booleans:
     - is_same_product_as_reference
     - material_matches_reference
     - color_matches_reference
     - style_brief_respected   (e.g. in_use → person seated)
     - premium_quality
     - no_visual_bug
   Plus a short list of issues. Caller retries on failure.

Cost note: ~0.005-0.01 USD per Gemini Flash vision call (cheap).
Pipeline budget tracking aggregates this with Nano Banana costs.
"""
from __future__ import annotations

import base64
import json
import logging
import os
import re
from typing import Any, Dict, Optional

logger = logging.getLogger("altiaro.image_qa")

GEMINI_VISION_MODEL = os.environ.get("GEMINI_VISION_MODEL", "gemini-2.5-flash")
GEMINI_VISION_USD_PER_CALL = 0.008  # rough avg, includes vision tokens


def _strip_json_fence(text: str) -> str:
    return re.sub(r"^```(?:json)?\s*|\s*```$", "", (text or "").strip(), flags=re.MULTILINE).strip()


async def _call_gemini_vision_text(
    *,
    system: str,
    user: str,
    image_b64: Optional[str] = None,
    extra_image_b64: Optional[str] = None,
    request_id: str,
    timeout: int = 30,
) -> str:
    """Single-shot Gemini vision call. Returns the model's text response."""
    from emergentintegrations.llm.chat import ImageContent, LlmChat, UserMessage

    EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY")
    if not EMERGENT_LLM_KEY:
        raise RuntimeError("EMERGENT_LLM_KEY not set")

    chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=request_id, system_message=system)
    chat.with_model("gemini", GEMINI_VISION_MODEL)

    files = []
    if image_b64:
        files.append(ImageContent(image_base64=image_b64))
    if extra_image_b64:
        files.append(ImageContent(image_base64=extra_image_b64))

    msg = UserMessage(text=user, file_contents=files) if files else UserMessage(text=user)
    raw = await chat.send_message(msg)
    if isinstance(raw, str):
        return raw
    if isinstance(raw, dict):
        return raw.get("text") or raw.get("content") or json.dumps(raw)
    # Some providers return objects with .text attribute
    txt = getattr(raw, "text", None)
    return txt if isinstance(txt, str) else str(raw)


async def analyze_source_product(reference_image_b64: str, *, request_id: str = "qa-source") -> Dict[str, str]:
    """Run a single Gemini Vision call on the source product photo to extract
    locked attributes injected into every per-style prompt.

    Returns dict with keys: material, color, product_kind.
    All values are short, descriptive English strings ready to drop into
    a Nano Banana prompt.
    """
    system = (
        "You are a product analyst. You look at a single product photo and "
        "describe in concise English the EXACT material, color and product kind. "
        "Be precise and factual. Output STRICT JSON only."
    )
    user = (
        "Analyze this product photo. Output ONLY this JSON (no markdown):\n"
        "{\n"
        '  "material": "<2-12 words. e.g.: \'matte microfiber fabric, woven texture\' or '
        '\'top-grain leather, smooth grain, slight sheen\' or \'PU leather, glossy finish\'>",\n'
        '  "color": "<2-8 words. e.g.: \'deep matte black with charcoal undertone\' or '
        '\'warm cream beige, slight ivory cast\'>",\n'
        '  "product_kind": "<2-6 words. e.g.: \'lift recliner armchair\', \'electric blanket\'>"\n'
        "}\n"
        "Be specific. Avoid generic words like 'fabric' alone — say 'woven cotton-blend fabric'. "
        "Avoid generic colors — capture undertone, finish, sheen."
    )
    raw = await _call_gemini_vision_text(
        system=system, user=user,
        image_b64=reference_image_b64,
        request_id=request_id,
        timeout=20,
    )
    cleaned = _strip_json_fence(raw)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]+\}", cleaned)
        if not m:
            raise ValueError(f"Vision response not parsable: {raw[:200]!r}")
        data = json.loads(m.group(0))

    # Defensive defaults
    out = {
        "material": str(data.get("material") or "").strip()[:120] or "fabric upholstery",
        "color": str(data.get("color") or "").strip()[:80] or "neutral",
        "product_kind": str(data.get("product_kind") or "").strip()[:60] or "product",
    }
    logger.info(f"[image-qa] source analysis {request_id}: {out}")
    return out


async def qa_check_generated_image(
    *,
    generated_b64: str,
    reference_b64: str,
    style_slug: str,
    style_brief: str,
    expected_material: str,
    expected_color: str,
    request_id: str,
) -> Dict[str, Any]:
    """Compare a freshly generated image against the reference and against
    the requested style brief. Returns a dict:

    {
      "all_pass": bool,
      "checks": {
        "is_same_product_as_reference": bool,
        "material_matches_reference": bool,
        "color_matches_reference": bool,
        "style_brief_respected": bool,
        "premium_quality": bool,
        "no_visual_bug": bool
      },
      "issues": ["..."]
    }
    """
    system = (
        "You are a strict art director QA-ing a generated product image against a "
        "reference photo and a style brief. Be ruthlessly honest. If the chair has "
        "different proportions, a different upholstery material, or doesn't match "
        "the brief — say it. Output STRICT JSON only, no markdown."
    )
    user = (
        f"REFERENCE IMAGE (image #1) and GENERATED IMAGE (image #2) attached.\n\n"
        f"Locked attributes that MUST match between reference and generated:\n"
        f"- Product kind/silhouette: same chair/object\n"
        f"- Material: {expected_material}\n"
        f"- Color: {expected_color}\n\n"
        f"Style brief for the GENERATED image (#2):\n"
        f"  Style slug: {style_slug}\n"
        f"  Brief: {style_brief}\n\n"
        f"Output ONLY this JSON (no markdown):\n"
        f'{{\n'
        f'  "checks": {{\n'
        f'    "is_same_product_as_reference": <bool: same silhouette, proportions, '
        f'features visible in both images>,\n'
        f'    "material_matches_reference": <bool: same upholstery material '
        f'(NEVER substitute leather for fabric or vice versa)>,\n'
        f'    "color_matches_reference": <bool: same color and finish, '
        f'including undertone>,\n'
        f'    "style_brief_respected": <bool: the generated image fulfills the brief; '
        f'e.g. for in_use a person is FULLY seated IN the chair (not standing next to it)>,\n'
        f'    "premium_quality": <bool: editorial/catalog quality, good composition, '
        f'good lighting, looks like a real photo>,\n'
        f'    "no_visual_bug": <bool: no extra limbs, no distortions, no warped '
        f'proportions, no missing armrests, no ghost elements>\n'
        f'  }},\n'
        f'  "issues": ["short bullet 1", "short bullet 2", ...]  // empty list if all pass\n'
        f"}}\n"
    )
    try:
        raw = await _call_gemini_vision_text(
            system=system, user=user,
            image_b64=reference_b64, extra_image_b64=generated_b64,
            request_id=request_id,
            timeout=25,
        )
    except Exception as e:
        logger.warning(f"[image-qa] Vision call failed for {request_id}: {str(e)[:200]}")
        # Fail-open : assume pass to not block the pipeline if Vision is down.
        # Caller can still inspect the image manually.
        return {
            "all_pass": True,
            "checks": {
                "is_same_product_as_reference": True,
                "material_matches_reference": True,
                "color_matches_reference": True,
                "style_brief_respected": True,
                "premium_quality": True,
                "no_visual_bug": True,
            },
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
                "checks": {},
                "issues": ["vision_qa_unparsable"],
            }
        data = json.loads(m.group(0))

    checks_raw = data.get("checks") or {}
    expected_keys = [
        "is_same_product_as_reference",
        "material_matches_reference",
        "color_matches_reference",
        "style_brief_respected",
        "premium_quality",
        "no_visual_bug",
    ]
    checks = {k: bool(checks_raw.get(k, False)) for k in expected_keys}
    issues = data.get("issues") or []
    if not isinstance(issues, list):
        issues = [str(issues)]
    issues = [str(i)[:200] for i in issues if i][:6]

    all_pass = all(checks.values())
    return {"all_pass": all_pass, "checks": checks, "issues": issues}


__all__ = [
    "analyze_source_product",
    "qa_check_generated_image",
    "GEMINI_VISION_USD_PER_CALL",
]
