"""
Phase 3 — Étape 7 cockpit : traduction multi-langue d'un site.

Toutes les zones de texte du site (brand, navigation, sections homepage,
produits, blog posts, SEO meta) sont traduites de la langue source du site
(`site.primary_lang`, default 'fr') vers les langues cibles via Claude
Sonnet 4.5. Le résultat est stocké en place sous une structure multilang
`{fr: "...", en: "...", de: "...", ...}` afin que le frontend (qui sait
déjà gérer ces dicts via `pickLang`) bascule automatiquement quand
l'utilisateur change de drapeau.

Idempotent : si la cible existe déjà ET overwrite=false → skip.
Async : le travail se fait en background (asyncio task), un task_id
permet de poller l'avancement. Cap budget ~3 $/site.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel

from deps import db, get_current_user
from services.llm_resilience import safe_claude_json

router = APIRouter(tags=["translation"])
logger = logging.getLogger("conceptfactory.translate")

SUPPORTED_LANGS = ["fr", "en", "de", "nl", "it", "es"]
LANG_LABELS = {
    "fr": "français", "en": "English", "de": "Deutsch",
    "nl": "Nederlands", "it": "italiano", "es": "español",
}

# Structures persisted in memory + DB by task_id.
TRANSLATE_TASKS: Dict[str, Dict[str, Any]] = {}


class TranslateInput(BaseModel):
    target_langs: List[str]
    overwrite: bool = False


def _is_multilang_dict(v: Any) -> bool:
    return isinstance(v, dict) and any(k in SUPPORTED_LANGS for k in v.keys())


def _get_source_text(value: Any, source_lang: str) -> Optional[str]:
    """Extracts the source-language text from a string or multilang dict."""
    if isinstance(value, str) and value.strip():
        return value
    if isinstance(value, dict):
        for k in (source_lang, "fr", "en"):
            v = value.get(k)
            if isinstance(v, str) and v.strip():
                return v
    return None


def _set_lang(value: Any, source_lang: str, target_lang: str, translated: str) -> Dict[str, str]:
    """Returns a dict with source + target text, preserving any existing langs."""
    out: Dict[str, str] = {}
    if isinstance(value, dict):
        for k, v in value.items():
            if k in SUPPORTED_LANGS and isinstance(v, str):
                out[k] = v
    src = _get_source_text(value, source_lang)
    if src:
        out.setdefault(source_lang, src)
    out[target_lang] = translated
    return out


async def _translate_batch(
    items: List[Dict[str, str]],   # [{key, text}]
    source_lang: str,
    target_lang: str,
    request_id: str,
) -> Dict[str, str]:
    """Translates a batch of {key,text} via one Claude Sonnet call.

    Returns a dict {key: translated_text}.
    """
    if not items:
        return {}
    payload = {it["key"]: it["text"] for it in items}
    system = (
        f"Tu es un traducteur premium e-commerce. Tu traduis fidèlement de "
        f"{LANG_LABELS.get(source_lang, source_lang)} vers {LANG_LABELS.get(target_lang, target_lang)}. "
        f"Tu PRÉSERVES le ton, la longueur, la ponctuation, les emojis, les balises HTML "
        f"légères (<strong>, <em>, <br/>, <p>, <ul>, <li>) et les sauts de ligne. "
        f"Tu NE traduis PAS les noms propres de marque, les villes, les codes "
        f"techniques (SKU, hex colors, slugs, URLs). "
        f"Tu réponds STRICTEMENT en JSON valide de la forme {{\"<key>\": \"<traduction>\"}} "
        f"avec EXACTEMENT les mêmes clés. Pas de markdown, pas de commentaires."
    )
    user_msg = f"INPUT à traduire:\n{json.dumps(payload, ensure_ascii=False)}"
    try:
        out = await safe_claude_json(
            system=system,
            user=user_msg,
            quality_tier="premium",   # Sonnet 4.5 — qualité brand-grade
            request_id=request_id,
            timeout=120,
        )
    except Exception as e:
        logger.error(f"[translate] LLM call failed for {target_lang}: {str(e)[:160]}")
        return {}
    if isinstance(out, dict):
        return {k: v for k, v in out.items() if isinstance(v, str)}
    return {}


def _collect_strings_from_section(prefix: str, value: Any, source_lang: str, target_lang: str,
                                   overwrite: bool, out: List[Dict[str, str]]):
    """Walks a nested object and collects translatable strings into `out`."""
    if isinstance(value, str):
        if value.strip() and len(value) <= 5000:
            out.append({"key": prefix, "text": value})
    elif isinstance(value, dict):
        # If it looks like a multilang dict
        if _is_multilang_dict(value) and target_lang in value and not overwrite:
            return  # already translated
        if _is_multilang_dict(value):
            src = _get_source_text(value, source_lang)
            if src and (overwrite or target_lang not in value):
                out.append({"key": prefix, "text": src})
            return
        # Recurse into normal dict
        for k, v in value.items():
            _collect_strings_from_section(f"{prefix}.{k}", v, source_lang, target_lang, overwrite, out)
    elif isinstance(value, list):
        for i, item in enumerate(value):
            _collect_strings_from_section(f"{prefix}[{i}]", item, source_lang, target_lang, overwrite, out)


def _apply_translation_at_path(root: Any, path: str, source_lang: str,
                                target_lang: str, translated: str) -> bool:
    """Sets the target lang at the given dotted path. Returns True on success."""
    # Path tokenizer : "a.b[2].c"
    tokens: List[Any] = []
    buf = ""
    i = 0
    while i < len(path):
        c = path[i]
        if c == ".":
            if buf:
                tokens.append(buf); buf = ""
        elif c == "[":
            if buf:
                tokens.append(buf); buf = ""
            j = path.index("]", i)
            tokens.append(int(path[i + 1 : j]))
            i = j
        else:
            buf += c
        i += 1
    if buf:
        tokens.append(buf)

    cur = root
    for tk in tokens[:-1]:
        try:
            cur = cur[tk]
        except (KeyError, IndexError, TypeError):
            return False
    last = tokens[-1]
    try:
        existing = cur[last] if (isinstance(cur, dict) or isinstance(cur, list)) else None
    except (KeyError, IndexError, TypeError):
        existing = None
    new_val = _set_lang(existing, source_lang, target_lang, translated)
    try:
        cur[last] = new_val
        return True
    except Exception:
        return False


async def _translate_site_async(site_id: str, target_langs: List[str], overwrite: bool, task_id: str):
    """Background worker — translates the site to each target lang sequentially."""
    task = TRANSLATE_TASKS[task_id]
    try:
        site = await db.sites.find_one({"id": site_id})
        if not site:
            task["status"] = "failed"; task["error"] = "site not found"; return
        source_lang = site.get("primary_lang") or "fr"
        # Load related docs
        products = await db.products.find({"site_id": site_id}).to_list(length=None)
        blog_posts = await db.blog_posts.find({"site_id": site_id}).to_list(length=None)
        task["totals"] = {
            "site_fields": 0,
            "products": len(products),
            "blog_posts": len(blog_posts),
        }

        spent_usd = 0.0
        cap_usd = 3.0
        request_id = f"translate-{site_id[:8]}-{task_id[:6]}"

        # Per-product fields keys we want to capture (paths inside the product dict).
        SITE_PATHS = [
            "design.brand.tagline",
            "design.brand.manifesto",
            "design.brand.workshop_story",
            "design.brand.values_caption",
            "design.brand.heritage",
            "design.hero.headline",
            "design.hero.subline",
            "design.hero.cta_label",
            "design.benefits",
            "design.testimonials",
            "design.faq",
            "design.about",
            "design.contact",
            "design.values",
            "design.process",
            "design.manifesto",
            "design.brand_story",
            "design.editorial_blocks",
            "design.navigation.header",
            "design.navigation.footer",
            "seo_meta",
        ]
        PRODUCT_PATHS = [
            "name", "description", "tagline", "short_description", "narrative",
            "usps", "how_to_steps", "product_faq", "editorial_cards",
            "benefits", "specs", "seo",
        ]
        BLOG_PATHS = ["title", "excerpt", "body", "meta_title", "meta_description"]

        for tlang in target_langs:
            if tlang == source_lang or tlang not in SUPPORTED_LANGS:
                task["progress"][tlang] = "skipped"; continue
            if spent_usd >= cap_usd:
                task["progress"][tlang] = "skipped_budget"; continue
            task["progress"][tlang] = "running"
            t0 = time.time()
            translated_keys = 0
            try:
                # ===== 1) site root fields =====
                items: List[Dict[str, str]] = []
                for path in SITE_PATHS:
                    cur: Any = site
                    for tok in path.split("."):
                        cur = (cur or {}).get(tok) if isinstance(cur, dict) else None
                    if cur is not None:
                        _collect_strings_from_section(path, cur, source_lang, tlang, overwrite, items)
                if items:
                    BATCH = 25
                    site_updates: Dict[str, str] = {}
                    for i in range(0, len(items), BATCH):
                        chunk = items[i:i + BATCH]
                        out = await _translate_batch(chunk, source_lang, tlang, request_id)
                        # Approx cost : 0.005 $ per 1k input chars × ~3 (output)
                        chars = sum(len(it["text"]) for it in chunk)
                        spent_usd += min(0.05, chars / 1000 * 0.018)
                        for it in chunk:
                            tx = out.get(it["key"])
                            if tx:
                                site_updates[it["key"]] = tx
                    # Apply on a copy then save
                    if site_updates:
                        for path, tx in site_updates.items():
                            _apply_translation_at_path(site, path, source_lang, tlang, tx)
                        await db.sites.update_one(
                            {"id": site_id},
                            {"$set": {"design": site.get("design"),
                                      "seo_meta": site.get("seo_meta"),
                                      "updated_at": datetime.now(timezone.utc).isoformat()}}
                        )
                        task["totals"]["site_fields"] += len(site_updates)
                        translated_keys += len(site_updates)

                # ===== 2) products =====
                for prod in products:
                    if spent_usd >= cap_usd:
                        break
                    items = []
                    for path in PRODUCT_PATHS:
                        cur = prod.get(path)
                        if cur is not None:
                            _collect_strings_from_section(path, cur, source_lang, tlang, overwrite, items)
                    if not items:
                        continue
                    BATCH = 30
                    prod_updates: Dict[str, str] = {}
                    for i in range(0, len(items), BATCH):
                        chunk = items[i:i + BATCH]
                        out = await _translate_batch(chunk, source_lang, tlang, request_id)
                        chars = sum(len(it["text"]) for it in chunk)
                        spent_usd += min(0.05, chars / 1000 * 0.018)
                        for it in chunk:
                            tx = out.get(it["key"])
                            if tx:
                                prod_updates[it["key"]] = tx
                    if prod_updates:
                        for path, tx in prod_updates.items():
                            _apply_translation_at_path(prod, path, source_lang, tlang, tx)
                        await db.products.update_one(
                            {"id": prod["id"]},
                            {"$set": {p: prod.get(p) for p in PRODUCT_PATHS if p in prod}}
                        )
                        translated_keys += len(prod_updates)

                # ===== 3) blog posts =====
                for bp in blog_posts:
                    if spent_usd >= cap_usd:
                        break
                    items = []
                    for path in BLOG_PATHS:
                        cur = bp.get(path)
                        if cur is not None:
                            _collect_strings_from_section(path, cur, source_lang, tlang, overwrite, items)
                    if not items:
                        continue
                    out = await _translate_batch(items, source_lang, tlang, request_id)
                    chars = sum(len(it["text"]) for it in items)
                    spent_usd += min(0.10, chars / 1000 * 0.018)
                    bp_updates: Dict[str, str] = {}
                    for it in items:
                        tx = out.get(it["key"])
                        if tx:
                            bp_updates[it["key"]] = tx
                    if bp_updates:
                        for path, tx in bp_updates.items():
                            _apply_translation_at_path(bp, path, source_lang, tlang, tx)
                        await db.blog_posts.update_one(
                            {"id": bp["id"]},
                            {"$set": {p: bp.get(p) for p in BLOG_PATHS if p in bp}}
                        )
                        translated_keys += len(bp_updates)

                task["progress"][tlang] = "done"
                task.setdefault("translated_keys_per_lang", {})[tlang] = translated_keys
                task["spent_usd"] = round(spent_usd, 4)
                logger.info(f"[translate] {tlang} done — {translated_keys} keys, "
                            f"{time.time()-t0:.1f}s, spent={spent_usd:.3f}$")
            except Exception as e:
                logger.exception(f"[translate] {tlang} failed")
                task["progress"][tlang] = f"failed:{str(e)[:80]}"

        # Mark which langs are now available on the site
        available = set(site.get("available_langs") or [source_lang])
        for tlang in target_langs:
            if task["progress"].get(tlang) == "done":
                available.add(tlang)
        await db.sites.update_one(
            {"id": site_id},
            {"$set": {"available_langs": sorted(available),
                      "last_translated_at": datetime.now(timezone.utc).isoformat()}}
        )
        task["status"] = "completed"
        task["spent_usd"] = round(spent_usd, 4)
        task["completed_at"] = datetime.now(timezone.utc).isoformat()
    except Exception as e:
        logger.exception("[translate] task failed")
        task["status"] = "failed"
        task["error"] = str(e)[:200]


@router.post("/sites/{site_id}/translate")
async def start_translation(
    site_id: str,
    data: TranslateInput,
    background: BackgroundTasks,
    user: dict = Depends(get_current_user),
):
    """Lance la traduction d'un site vers une ou plusieurs langues cibles."""
    site = await db.sites.find_one({"id": site_id}, {"_id": 0, "id": 1, "operator_id": 1, "primary_lang": 1})
    if not site:
        raise HTTPException(404, "Site introuvable")
    if user.get("role") != "admin" and site.get("operator_id") != user.get("id"):
        raise HTTPException(403, "Accès interdit")

    target_langs = [t for t in (data.target_langs or []) if t in SUPPORTED_LANGS]
    if not target_langs:
        raise HTTPException(400, f"target_langs requis. Valides : {SUPPORTED_LANGS}")
    source_lang = site.get("primary_lang") or "fr"
    target_langs = [t for t in target_langs if t != source_lang]
    if not target_langs:
        raise HTTPException(400, f"Aucune langue cible (source = {source_lang})")

    task_id = uuid.uuid4().hex[:12]
    TRANSLATE_TASKS[task_id] = {
        "task_id": task_id,
        "site_id": site_id,
        "source_lang": source_lang,
        "target_langs": target_langs,
        "overwrite": bool(data.overwrite),
        "status": "queued",
        "progress": {t: "queued" for t in target_langs},
        "spent_usd": 0.0,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "totals": {},
    }
    background.add_task(_translate_site_async, site_id, target_langs, bool(data.overwrite), task_id)
    return {
        "ok": True,
        "task_id": task_id,
        "queued_langs": target_langs,
        "eta_seconds": 60 * len(target_langs),
        "status_url": f"/api/sites/{site_id}/translate/status?task_id={task_id}",
    }


@router.get("/sites/{site_id}/translate/status")
async def translation_status(
    site_id: str,
    task_id: str = Query(...),
    user: dict = Depends(get_current_user),
):
    task = TRANSLATE_TASKS.get(task_id)
    if not task:
        raise HTTPException(404, f"Task {task_id} introuvable (peut-être expirée)")
    if task.get("site_id") != site_id:
        raise HTTPException(403, "task_id ne correspond pas à ce site")
    return task


@router.get("/sites/{site_id}/translate/state")
async def translation_state(
    site_id: str,
    user: dict = Depends(get_current_user),
):
    """Returns the per-language coverage of the site (% of multilang dicts
    populated for each target lang). Used by the cockpit to render the
    "✅ traduit / ❌ pas encore" badges."""
    site = await db.sites.find_one({"id": site_id})
    if not site:
        raise HTTPException(404, "Site introuvable")
    if user.get("role") != "admin" and site.get("operator_id") != user.get("id"):
        raise HTTPException(403, "Accès interdit")
    source_lang = site.get("primary_lang") or "fr"
    available = set(site.get("available_langs") or [source_lang])
    products = await db.products.count_documents({"site_id": site_id})
    blog_posts = await db.blog_posts.count_documents({"site_id": site_id})
    return {
        "site_id": site_id,
        "primary_lang": source_lang,
        "available_langs": sorted(available),
        "supported_langs": SUPPORTED_LANGS,
        "lang_labels": LANG_LABELS,
        "last_translated_at": site.get("last_translated_at"),
        "counts": {"products": products, "blog_posts": blog_posts},
    }
