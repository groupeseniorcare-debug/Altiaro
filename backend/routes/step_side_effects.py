"""
Step side-effects : actions automatiques déclenchées à la validation d'une étape clé.

Principe : quand un Concepteur valide une étape, on appelle Claude une 2e fois avec un
prompt d'extraction JSON spécifique à cette étape. La réponse structurée est persistée
dans `sites.design.*` ou la collection `products`, et devient immédiatement visible
dans le storefront.

Étapes clés branchées :
- #6  → Identité visuelle → `sites.design.brand` (couleurs, fonts, tagline)
- #9  → Documents légaux clé en main → `sites.design.legal_pages` (CGV / mentions / RGPD)
- #16 → Import catalogue CSV haute qualité (20 produits) → collection `products`
- #17 → Scaffold React headless → marque `sites.design.template_applied = true`
         et copie les couleurs du #6 dans le storefront.

Fire-and-forget : les hooks sont lancés en background, n'ont pas le droit de
faire échouer la validation même en cas d'erreur.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from deps import db

logger = logging.getLogger("conceptfactory.step_side_effects")
EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")

# Mapping number → handler name
_HANDLERS: dict[int, str] = {
    5: "rename_site",
    6: "brand_book",
    9: "legal_docs",
    16: "product_import",
    17: "template_scaffold",
}


_JSON_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```\s*$", re.MULTILINE)


def _strip_json_fence(text: str) -> str:
    return _JSON_FENCE_RE.sub("", (text or "").strip()).strip()


async def _call_claude(system: str, user: str) -> Optional[dict]:
    """Single-shot Claude call returning a dict (or None on failure)."""
    if not EMERGENT_LLM_KEY:
        logger.warning("No EMERGENT_LLM_KEY, side-effect extraction skipped")
        return None
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        chat = (
            LlmChat(
                api_key=EMERGENT_LLM_KEY,
                session_id=f"side-effect-{uuid.uuid4().hex[:8]}",
                system_message=system,
            )
            .with_model("anthropic", "claude-sonnet-4-5-20250929")
        )
        raw = await asyncio.wait_for(chat.send_message(UserMessage(text=user)), timeout=90)
        raw_text = raw if isinstance(raw, str) else str(raw)
        stripped = _strip_json_fence(raw_text)
        return json.loads(stripped)
    except (asyncio.TimeoutError, json.JSONDecodeError) as e:
        logger.error(f"Side-effect Claude call failed : {e}")
        return None
    except Exception:
        logger.exception("Side-effect Claude unexpected error")
        return None


def _step_content(step: dict) -> str:
    """Concatène tous les livrables texte disponibles pour l'étape."""
    parts = [
        step.get("ai_response") or "",
        step.get("deliverable_notes") or "",
    ]
    return "\n\n".join(p for p in parts if p).strip()


# =====================================================================
# Hook #5 — Nom de marque retenu → sites.name + sites.niche_slug
# =====================================================================
def _slugify(text: str) -> str:
    import unicodedata
    s = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return s[:50] or "site"


async def _hook_rename_site(step: dict) -> None:
    content = _step_content(step)
    if not content:
        logger.info(f"[side-effect #5] no content, skipping")
        return

    site = await db.sites.find_one({"id": step["site_id"]}, {"_id": 0})
    niche = (site or {}).get("niche") or ""
    current_name = (site or {}).get("name") or ""

    system = (
        "Tu extrais le NOM DE MARQUE DÉFINITIF retenu par le Concepteur depuis un livrable de naming. "
        "Tu renvoies UNIQUEMENT du JSON valide."
    )
    user = f"""Livrable étape #5 (génération nom de marque + domaine + INPI) — niche : {niche}
Nom actuel provisoire : « {current_name} »

---
{content[:5000]}
---

Extrait au JSON EXACTEMENT :
{{
  "brand_name": "Nom de marque retenu par le Concepteur (le gagnant final, pas la short-list)",
  "tagline": "Signature de marque courte FR (3-8 mots)",
  "domain": "nom-domaine.fr ou .com retenu (sans https://)"
}}

Règles :
- Si le livrable propose plusieurs candidats, choisis celui marqué comme "TOP 1" / "retenu" / "validé" / "choix final".
- Si rien n'est explicitement retenu, prends le premier nom de la liste finale.
- brand_name : juste le nom commercial, sans slogan ni extension de domaine.
- Uniquement le JSON."""
    data = await _call_claude(system, user)
    if not data or not isinstance(data, dict):
        logger.warning(f"[side-effect #5] extraction failed for site {step['site_id']}")
        return

    brand_name = str(data.get("brand_name") or "").strip()
    if not brand_name or brand_name.lower() == current_name.lower():
        logger.info(f"[side-effect #5] brand_name unchanged ('{brand_name}' == '{current_name}'), skipping")
        return

    slug = _slugify(brand_name)
    updates: dict[str, Any] = {
        "name": brand_name,
        "niche_slug": slug,
        "renamed_at": datetime.now(timezone.utc).isoformat(),
    }
    tagline = str(data.get("tagline") or "").strip()
    if tagline:
        updates["design.brand.tagline"] = tagline
        updates["design.brand.logo_text"] = brand_name
    domain = str(data.get("domain") or "").strip().lower().replace("https://", "").replace("http://", "").rstrip("/")
    if domain and "." in domain:
        updates["target_domain"] = domain

    await db.sites.update_one({"id": step["site_id"]}, {"$set": updates})
    logger.info(f"[side-effect #5] site {step['site_id']} renamed : '{current_name}' → '{brand_name}' (slug={slug}, domain={domain or 'n/a'})")


# =====================================================================
# Hook #6 — Identité visuelle → design.brand
# =====================================================================
async def _hook_brand_book(step: dict) -> None:
    content = _step_content(step)
    if not content:
        logger.info(f"[side-effect #6] no content for step {step.get('id')}, skipping")
        return

    site = await db.sites.find_one({"id": step["site_id"]}, {"_id": 0})
    niche = (site or {}).get("niche") or (site or {}).get("name") or ""

    system = (
        "Tu extrais un brand book depuis un livrable d'identité visuelle rédigé en français. "
        "Tu renvoies UNIQUEMENT du JSON valide, sans markdown. "
        "Valeurs par défaut acceptables si info manquante."
    )
    user = f"""Livrable brand book (étape #6) :
---
{content[:6000]}
---

Niche du site : {niche}

Extrait au JSON EXACTEMENT ce schéma :
{{
  "primary_color": "#RRGGBB",      // couleur dominante (CTA, liens)
  "accent_color": "#RRGGBB",       // couleur secondaire (surlignages, fonds)
  "background_color": "#RRGGBB",   // fond général (blanc cassé/crème recommandé)
  "text_color": "#RRGGBB",         // texte principal (très foncé)
  "font_heading": "NomFont",       // famille titres (Google Fonts) ex: Fraunces, Playfair Display, Lora
  "font_body": "NomFont",          // famille body ex: Inter, DM Sans
  "tagline": "Signature marque courte en FR (3-6 mots)",
  "logo_text": "Nom de marque retenu (sans slogan)",
  "voice_keywords": ["mot1","mot2","mot3"]  // 3-5 adjectifs du ton de marque
}}

Uniquement le JSON."""
    data = await _call_claude(system, user)
    if not data or not isinstance(data, dict):
        logger.warning(f"[side-effect #6] extraction failed for site {step['site_id']}")
        return

    # Whitelist fields
    brand = {
        k: data[k]
        for k in [
            "primary_color", "accent_color", "background_color", "text_color",
            "font_heading", "font_body", "tagline", "logo_text", "voice_keywords",
        ]
        if k in data and data[k]
    }
    if not brand:
        return
    await db.sites.update_one(
        {"id": step["site_id"]},
        {"$set": {
            "design.brand": {**(site.get("design", {}).get("brand") or {}), **brand},
            "design.brand_applied_at": datetime.now(timezone.utc).isoformat(),
            "design.published": True,
        }},
    )
    logger.info(f"[side-effect #6] brand applied to site {step['site_id']} : {list(brand.keys())}")


# =====================================================================
# Hook #9 — Documents légaux → design.legal_pages
# =====================================================================
async def _hook_legal_docs(step: dict) -> None:
    content = _step_content(step)
    if not content:
        logger.info(f"[side-effect #9] no content for step {step.get('id')}, skipping")
        return

    site = await db.sites.find_one({"id": step["site_id"]}, {"_id": 0})
    name = (site or {}).get("name") or "Boutique"

    system = (
        "Tu extrais les documents légaux d'un livrable juridique FR/EU. "
        "Tu renvoies UNIQUEMENT du JSON valide. Les body_md sont en markdown propre."
    )
    user = f"""Livrable documents légaux (étape #9) pour la boutique « {name} » :
---
{content[:10000]}
---

Extrait au JSON EXACTEMENT ce schéma :
{{
  "cgv": {{
    "title": "Conditions générales de vente",
    "body_md": "# CGV\\n\\nArticle 1 — ...\\n\\nArticle 2 — ...\\n..."
  }},
  "mentions_legales": {{
    "title": "Mentions légales",
    "body_md": "# Mentions légales\\n\\n..."
  }},
  "confidentialite": {{
    "title": "Politique de confidentialité",
    "body_md": "# Politique de confidentialité (RGPD)\\n\\n..."
  }}
}}

Règles :
- body_md en markdown GitHub (titres ##, listes, gras), rédigé en français propre.
- Chaque document 300-500 mots, concis et conforme B2C EU / loi Lemaire / RGPD.
- Si l'info manque dans le livrable, rédige toi-même du contenu juridique légitime et générique.
- Placeholders acceptés : [RAISON_SOCIALE], [ADRESSE], [SIREN], [TVA], [EMAIL_CONTACT], [TELEPHONE].

Uniquement le JSON."""
    data = await _call_claude(system, user)
    if not data or not isinstance(data, dict):
        logger.warning(f"[side-effect #9] extraction failed for site {step['site_id']}")
        return

    legal_pages: dict[str, dict] = {}
    for kind in ("cgv", "mentions_legales", "confidentialite"):
        doc = data.get(kind)
        if isinstance(doc, dict) and doc.get("body_md"):
            legal_pages[kind] = {
                "title": doc.get("title") or kind.replace("_", " ").title(),
                "body_md": str(doc["body_md"]).strip(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
    if not legal_pages:
        return

    await db.sites.update_one(
        {"id": step["site_id"]},
        {"$set": {
            "design.legal_pages": legal_pages,
            "design.legal_applied_at": datetime.now(timezone.utc).isoformat(),
            "design.published": True,
        }},
    )
    logger.info(f"[side-effect #9] {len(legal_pages)} legal pages applied to site {step['site_id']}")


# =====================================================================
# Hook #16 — Import catalogue 20 produits → collection products
# =====================================================================
async def _hook_product_import(step: dict) -> None:
    content = _step_content(step)
    if not content:
        logger.info(f"[side-effect #16] no content for step {step.get('id')}, skipping")
        return

    site = await db.sites.find_one({"id": step["site_id"]}, {"_id": 0})
    niche = (site or {}).get("niche") or (site or {}).get("name") or ""

    system = (
        "Tu extrais une liste de produits e-commerce depuis un livrable d'import catalogue. "
        "Tu renvoies UNIQUEMENT du JSON valide."
    )
    user = f"""Livrable catalogue produits (étape #16) — niche : {niche}
---
{content[:10000]}
---

Extrait au JSON EXACTEMENT ce schéma :
{{
  "products": [
    {{
      "name": "Nom produit commercial FR (40 caractères max)",
      "description": "Description vendeuse 150-300 mots, structure bénéfice/preuve/usage",
      "short_description": "Pitch en 1 phrase (120 caractères max)",
      "price_eur": 149.00,
      "compare_at_price_eur": 199.00,  // optionnel, prix barré
      "supplier_cost_eur": 42.00,
      "category": "Catégorie courte",
      "tags": ["tag1", "tag2"],
      "sku": "SKU-001",
      "weight_kg": 2.5,
      "stock": 50
    }}
  ]
}}

Règles :
- Extrais AU MOINS 5 produits réels du livrable.
- Descriptions concises 80-120 mots chacune, français commercial senior.
- Prix >= 50€, marge >= 60% (supplier_cost_eur <= 40% de price_eur).
- Pas de placeholder dans les descriptions finales.

Uniquement le JSON."""
    data = await _call_claude(system, user)
    if not data or not isinstance(data, dict):
        logger.warning(f"[side-effect #16] extraction failed for site {step['site_id']}")
        return
    items = data.get("products") or []
    if not isinstance(items, list) or not items:
        return

    now_iso = datetime.now(timezone.utc).isoformat()
    existing_count = await db.products.count_documents({"site_id": step["site_id"]})
    inserted = 0
    inserted_ids: list[str] = []
    for idx, p in enumerate(items[:20]):
        if not isinstance(p, dict) or not p.get("name"):
            continue
        try:
            price = float(p.get("price_eur") or 0)
            supplier = float(p.get("supplier_cost_eur") or 0)
            margin_pct = 0.0
            if price > 0:
                margin_pct = round(((price - supplier) / price) * 100, 1)
            pid = str(uuid.uuid4())
            doc = {
                "id": pid,
                "site_id": step["site_id"],
                "name": str(p["name"])[:120],
                "description": str(p.get("description") or "")[:6000],
                "short_description": str(p.get("short_description") or "")[:300],
                "price_eur": price,
                "compare_at_price_eur": float(p.get("compare_at_price_eur") or 0) or None,
                "supplier_cost_eur": supplier,
                "margin_pct": margin_pct,
                "category": str(p.get("category") or ""),
                "tags": [str(t) for t in (p.get("tags") or []) if t][:10],
                "sku": str(p.get("sku") or f"SKU-{existing_count + idx + 1:04d}"),
                "weight_kg": float(p.get("weight_kg") or 0),
                "stock": int(p.get("stock") or 0),
                "status": "draft",
                "source": "step_16_auto_import",
                "created_at": now_iso,
                "updated_at": now_iso,
            }
            await db.products.insert_one(doc)
            inserted += 1
            inserted_ids.append(pid)
        except Exception:
            logger.exception(f"[side-effect #16] product insert failed : {p}")
    logger.info(f"[side-effect #16] {inserted} products imported (site {step['site_id']})")

    # -------- Fire-and-forget narrative enrichment for each imported product --------
    if inserted_ids:
        try:
            from routes.product_narrative import enrich_product_narrative
            async def _enrich_all():
                for pid in inserted_ids:
                    try:
                        await enrich_product_narrative(pid, force=False)
                    except Exception:
                        logger.exception(f"[side-effect #16→narrative] failed pid={pid}")
            asyncio.create_task(_enrich_all())
            logger.info(f"[side-effect #16→narrative] queued {len(inserted_ids)} products for AI enrichment")
        except Exception:
            logger.exception("[side-effect #16→narrative] dispatch failed")

        # -------- Fire-and-forget IndexNow submission --------
        try:
            from routes.indexnow import fire_and_forget_indexnow, _origin
            origin = _origin()
            base = f"{origin}/shop/{step['site_id']}"
            urls = [base, f"{base}/collections"] + [f"{base}/product/{pid}" for pid in inserted_ids]
            fire_and_forget_indexnow(urls)
            logger.info(f"[side-effect #16→indexnow] submitted {len(urls)} URLs")
        except Exception:
            logger.exception("[side-effect #16→indexnow] dispatch failed")


# =====================================================================
# Hook #17 — Scaffold React → template Altiaro + re-applique brand
# =====================================================================
async def _hook_template_scaffold(step: dict) -> None:
    site = await db.sites.find_one({"id": step["site_id"]}, {"_id": 0})
    if not site:
        return
    design = site.get("design") or {}
    brand = design.get("brand") or {}
    # Defaults if brand from #6 was skipped
    defaults = {
        "primary_color": "#B84B31",
        "accent_color": "#F5F2EB",
        "background_color": "#FDFBF7",
        "text_color": "#1C1917",
        "font_heading": "Fraunces",
        "font_body": "Inter",
    }
    merged = {**defaults, **{k: v for k, v in brand.items() if v}}

    await db.sites.update_one(
        {"id": step["site_id"]},
        {"$set": {
            "design.brand": merged,
            "design.template_applied": True,
            "design.template_applied_at": datetime.now(timezone.utc).isoformat(),
            "design.template_name": "altiaro-premium-light",
            "design.published": True,
        }},
    )
    logger.info(f"[side-effect #17] template 'altiaro-premium-light' applied to site {step['site_id']}")


_DISPATCH = {
    "rename_site": _hook_rename_site,
    "brand_book": _hook_brand_book,
    "legal_docs": _hook_legal_docs,
    "product_import": _hook_product_import,
    "template_scaffold": _hook_template_scaffold,
}


async def run_side_effect(step: dict) -> None:
    """Point d'entrée appelé depuis steps.py après validation/submit."""
    num = step.get("number")
    handler_name = _HANDLERS.get(num)
    if not handler_name:
        return
    handler = _DISPATCH.get(handler_name)
    if not handler:
        return
    try:
        await handler(step)
    except Exception:
        logger.exception(f"[side-effect] handler {handler_name} crashed for step #{num}")


def schedule_side_effect(step: dict) -> None:
    """Fire-and-forget — ne bloque pas la validation côté user."""
    num = step.get("number")
    if num not in _HANDLERS:
        return
    try:
        loop = asyncio.get_event_loop()
        loop.create_task(run_side_effect(step))
        logger.info(f"[side-effect] scheduled for step #{num} (site {step.get('site_id')})")
    except Exception:
        logger.exception("[side-effect] scheduling failed")
