"""Sprint 4 — Endpoints de réparation & backfill sur le contenu magique.

Contient :
  - POST /api/sites/{site_id}/magic/content/relink
        Rejoue le maillage interne Jaccard sur les blog_posts existants
        (sans régénérer le contenu). Utile pour les sites créés avant
        Sprint 1.3 dont les `internal_links` sont vides. Coût LLM : 0.

  - POST /api/sites/{site_id}/magic/content/repair?lang={code}
        Sprint 4 part B — Comble les traductions manquantes d'une langue
        cible. Pour chaque blog_post FR du site, détecte s'il existe un
        équivalent `(site_id, cluster_id, lang)` déjà traduit. S'il manque,
        re-traduit via Claude Haiku avec retry exponentiel (jusqu'à 3×).
        Idempotent, persiste uniquement les succès.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from deps import db, get_current_user, _check_site_access

router = APIRouter()
logger = logging.getLogger("altiaro.relink")

TARGET_LANGS_VALID = {"en", "de", "nl", "it", "es"}


class RelinkInput(BaseModel):
    lang: Optional[str] = None


@router.post("/sites/{site_id}/magic/content/relink", tags=["sprint4"])
async def magic_content_relink(site_id: str,
                                payload: RelinkInput = RelinkInput(),
                                user: dict = Depends(get_current_user)):
    """Rejoue _apply_internal_linking sur les blog_posts existants."""
    await _check_site_access(site_id, user)
    site = await db.sites.find_one({"id": site_id}, {"_id": 0})
    if not site:
        raise HTTPException(404, "Site introuvable")

    target_lang = (payload.lang or
                   (site.get("primary_locale") or "fr-FR").split("-")[0]
                   ).lower()

    posts = await db.blog_posts.find(
        {"site_id": site_id, "lang": target_lang},
        {"_id": 0},
    ).to_list(500)
    if not posts:
        return {"ok": False, "reason": "no_posts_for_lang", "lang": target_lang}

    pillar = next((p for p in posts if p.get("role") == "pillar"), None)
    if not pillar:
        return {"ok": False, "reason": "no_pillar_post", "posts_total": len(posts)}

    from services.magic_content_pipeline import _apply_internal_linking
    await _apply_internal_linking(posts, pillar)

    updated = await db.blog_posts.count_documents(
        {"site_id": site_id, "lang": target_lang,
         "role": {"$ne": "pillar"},
         "internal_links": {"$exists": True, "$ne": []}},
    )
    return {
        "ok": True,
        "lang": target_lang,
        "posts_total": len(posts),
        "pillar_slug": pillar.get("slug"),
        "non_pillars_with_links": updated,
    }


# ─── Sprint 4 Part B — /magic/content/repair ──────────────────────────────
async def _translate_article_direct(fr_doc: dict, lang: str, brand: str,
                                     quality_tier: str = "standard",
                                     timeout: float = 180.0) -> Optional[dict]:
    """Variant de `_translate_article` qui accepte `quality_tier` pour permettre
    d'escalader vers Sonnet (premium) sur les retries des articles longs qui
    tronquent en Haiku (observed: pillars ~10k chars → output > 4k tokens).
    """
    import json as _json
    from services.llm_resilience import safe_claude_json
    lang_full = {"en": "anglais", "de": "allemand", "nl": "néerlandais",
                 "it": "italien", "es": "espagnol"}.get(lang, lang)
    system = (f"Tu es traducteur SEO expert. Tu traduis depuis le français vers "
              f"{lang_full} en préservant les intentions SEO (mots-clés, tone-of-voice, "
              "structure H2/H3). Tu renvoies EXCLUSIVEMENT du JSON strict.")

    fr_title = (fr_doc.get("title") or {}).get("fr", "")
    fr_meta_t = (fr_doc.get("meta_title") or {}).get("fr", "")
    fr_meta_d = (fr_doc.get("meta_description") or {}).get("fr", "")
    fr_excerpt = (fr_doc.get("excerpt") or {}).get("fr", "")
    fr_aeo = (fr_doc.get("aeo_snippet") or {}).get("fr", "")
    fr_body = (fr_doc.get("body_md") or {}).get("fr", "")
    fr_faq = fr_doc.get("faq") or []
    fr_faq_compact = [{"q": (f.get("q") or {}).get("fr", ""),
                       "a": (f.get("a") or {}).get("fr", "")}
                      for f in fr_faq]

    user = (
        f"Traduis fidèlement cet article de {brand} en {lang_full}. Conserve toute la "
        "structure markdown (## H2, ### H3, **gras**, listes). Adapte le slug pour "
        f"référencer naturellement en {lang_full} (kebab-case, sans accent).\n\n"
        f"ARTICLE FR :\n"
        f"TITLE: {fr_title}\n"
        f"META_TITLE: {fr_meta_t}\n"
        f"META_DESC: {fr_meta_d}\n"
        f"EXCERPT: {fr_excerpt}\n"
        f"AEO_SNIPPET: {fr_aeo}\n\n"
        f"BODY:\n{fr_body}\n\n"
        f"FAQ: {_json.dumps(fr_faq_compact, ensure_ascii=False)}\n\n"
        "JSON STRICT :\n"
        "{\n"
        '  "slug": "...", "title": "...", "meta_title": "...", "meta_description": "...",\n'
        '  "excerpt": "...", "aeo_snippet": "...", "body_md": "...",\n'
        '  "faq": [{"q": "...", "a": "..."}, ...]\n'
        "}"
    )
    try:
        out = await safe_claude_json(
            system=system, user=user,
            quality_tier=quality_tier,
            request_id=f"repair-{lang}-{fr_doc.get('id', '')[:8]}",
            timeout=timeout,
        )
    except Exception as e:
        logger.warning(f"[repair-direct] translate {lang} failed on "
                       f"{fr_doc.get('slug')}: {str(e)[:120]}")
        return None
    if not isinstance(out, dict) or not out.get("body_md"):
        return None
    return out


async def _translate_with_retry(fr_doc: dict, lang: str, brand: str,
                                 max_attempts: int = 3) -> Optional[dict]:
    """Wrap translation with exponential backoff + quality escalation.

    Strategy :
      attempt 1 : Haiku standard, timeout 180s
      attempt 2 : Haiku standard (after 2s delay) — transient errors ok
      attempt 3 : Sonnet premium (after 4s delay) — for long pillars that
                  truncate in Haiku's 4096 token output.
    Returns the translated dict, or None after `max_attempts` failures.
    """
    delay = 2.0
    for attempt in range(1, max_attempts + 1):
        quality = "premium" if attempt >= 3 else "standard"
        try:
            tr = await _translate_article_direct(
                fr_doc, lang, brand,
                quality_tier=quality,
                timeout=240.0 if quality == "premium" else 180.0,
            )
            if isinstance(tr, dict) and tr.get("body_md"):
                if attempt > 1:
                    logger.info(f"[repair] {fr_doc.get('slug')} {lang} succeeded "
                                f"on attempt {attempt} (quality={quality})")
                return tr
            logger.warning(f"[repair] {fr_doc.get('slug')} {lang} attempt {attempt} "
                           f"(quality={quality}) returned empty body_md")
        except asyncio.TimeoutError:
            logger.warning(f"[repair] {fr_doc.get('slug')} {lang} attempt {attempt} "
                           f"(quality={quality}) timed out")
        except Exception as e:
            logger.warning(f"[repair] {fr_doc.get('slug')} {lang} attempt {attempt} "
                           f"(quality={quality}) exception: {str(e)[:120]}")
        if attempt < max_attempts:
            await asyncio.sleep(delay)
            delay *= 2   # 2s → 4s
    return None


@router.post("/sites/{site_id}/magic/content/repair", tags=["sprint4"])
async def magic_content_repair(site_id: str, lang: str,
                                user: dict = Depends(get_current_user)):
    """Sprint 4 — rejoue uniquement les traductions manquantes pour `lang`.

    Logique :
      1. Prend tous les blog_posts FR du site (langue source canonique).
      2. Pour chaque FR, vérifie s'il existe un doc `(site_id, cluster_id,
         lang)` déjà persisté.
      3. S'il manque → re-traduit via `_translate_article` avec retry
         exponentiel (2s, 4s, 8s), jusqu'à 3 essais par article.
      4. Insère le doc traduit (`_build_translated_doc`).

    Idempotent : ne retraduit jamais un article déjà présent dans la langue.
    Best-effort : les échecs persistants sont retournés dans `failed` pour
    audit ultérieur.
    """
    await _check_site_access(site_id, user)
    lang = (lang or "").lower()
    if lang not in TARGET_LANGS_VALID:
        raise HTTPException(
            400,
            f"Langue cible invalide. Valides : {sorted(TARGET_LANGS_VALID)}",
        )

    site = await db.sites.find_one({"id": site_id}, {"_id": 0})
    if not site:
        raise HTTPException(404, "Site introuvable")
    brand = site.get("name") or "la marque"

    # FR posts = source de vérité
    fr_posts = await db.blog_posts.find(
        {"site_id": site_id, "lang": "fr"},
        {"_id": 0},
    ).to_list(500)
    if not fr_posts:
        return {"ok": False, "reason": "no_fr_posts", "lang": lang,
                "repaired_count": 0, "failed_count": 0}

    # Récupère les cluster_ids déjà traduits dans la langue cible
    existing_lang_docs = await db.blog_posts.find(
        {"site_id": site_id, "lang": lang},
        {"_id": 0, "cluster_id": 1, "source_post_id": 1},
    ).to_list(500)
    existing_cluster_ids = {d.get("cluster_id") for d in existing_lang_docs if d.get("cluster_id")}
    existing_source_ids = {d.get("source_post_id") for d in existing_lang_docs if d.get("source_post_id")}

    # Déduis les FR posts pour lesquels la langue manque
    missing = []
    for fr in fr_posts:
        cluster_id = fr.get("cluster_id")
        post_id = fr.get("id")
        already = False
        if cluster_id and cluster_id in existing_cluster_ids:
            # Vérifier qu'il y a bien un doc avec ce cluster + lang matching source_post_id
            # sinon on considère qu'il manque quand même (cluster_id partagé mais source différente)
            pass
        if post_id and post_id in existing_source_ids:
            already = True
        if not already:
            missing.append(fr)

    logger.info(f"[repair] site={site_id[:8]} lang={lang} "
                f"fr_total={len(fr_posts)} already={len(fr_posts) - len(missing)} "
                f"missing={len(missing)}")

    if not missing:
        return {
            "ok": True,
            "lang": lang,
            "fr_total": len(fr_posts),
            "already_translated": len(fr_posts),
            "repaired_count": 0,
            "failed_count": 0,
            "message": f"All FR posts already translated in {lang}",
        }

    # Translate with retry, concurrency limited to 3 (Claude rate)
    from services.magic_content_pipeline import _build_translated_doc
    sema = asyncio.Semaphore(3)
    repaired = []
    failed = []

    async def _repair_one(fr_doc: dict):
        async with sema:
            tr = await _translate_with_retry(fr_doc, lang, brand, max_attempts=3)
            if not tr:
                failed.append({"slug": fr_doc.get("slug"), "id": fr_doc.get("id")})
                return
            clone = _build_translated_doc(fr_doc, tr, lang,
                                          fr_doc.get("cluster_id") or "")
            # Protection double-insert (concurrent call racing)
            already = await db.blog_posts.find_one(
                {"site_id": site_id, "lang": lang,
                 "source_post_id": fr_doc.get("id")},
                {"_id": 0, "id": 1},
            )
            if already:
                return
            await db.blog_posts.insert_one(clone)
            repaired.append({"slug": clone.get("slug"), "source_slug": fr_doc.get("slug")})

    await asyncio.gather(*(_repair_one(fr) for fr in missing))

    # Update the available_langs of the site if we repaired something
    if repaired:
        new_langs = set(site.get("available_langs") or [])
        new_langs.add(lang)
        await db.sites.update_one(
            {"id": site_id},
            {"$set": {"available_langs": sorted(new_langs)}},
        )

    return {
        "ok": True,
        "lang": lang,
        "fr_total": len(fr_posts),
        "already_translated": len(fr_posts) - len(missing),
        "attempted": len(missing),
        "repaired_count": len(repaired),
        "failed_count": len(failed),
        "repaired": repaired,
        "failed": failed,
    }
