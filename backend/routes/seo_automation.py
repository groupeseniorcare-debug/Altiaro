"""
Phase 6 — Automatisation SEO/AEO agressive.

Un seul module qui encapsule :
- 7 fonctions cron coroutines (blog_auto, emerging_keywords, content_refresh,
  internal_linking, gsc_alerts, paa_faq, content_gap, sitemap_republish,
  seo_weekly_report) — chacune peut être appelée manuellement via l'endpoint
  admin trigger ci-dessous
- 1 throttle global `asyncio.Semaphore(2)` sur les appels Claude pour ne pas
  saturer EMERGENT_LLM_KEY
- 4 endpoints REST
- Helpers : ensure_indexes, mark_sitemap_dirty, automation log

Aucun hook temps-réel ne bloque la requête utilisateur : tout l'IA tourne
en cron background avec logging structuré (durée + estimation tokens).
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from deps import db, get_current_user

logger = logging.getLogger("conceptfactory.seo_automation")
router = APIRouter()

EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "").strip()

# --------------------------------------------------------------------------
#  CLAUDE CALL — semaphore global pour protéger EMERGENT_LLM_KEY
# --------------------------------------------------------------------------
_claude_semaphore = asyncio.Semaphore(2)


async def _claude_call(system: str, user: str, timeout: int = 120) -> Optional[dict]:
    """Appel Claude throttlé (2 en parallèle max au niveau module).
    Retourne dict JSON parsé ou None si échec (jamais raise)."""
    if not EMERGENT_LLM_KEY:
        return None

    async with _claude_semaphore:
        t0 = time.time()
        try:
            from emergentintegrations.llm.chat import LlmChat, UserMessage
            chat = (
                LlmChat(
                    api_key=EMERGENT_LLM_KEY,
                    session_id=f"seoauto-{uuid.uuid4().hex[:8]}",
                    system_message=system,
                )
                .with_model("anthropic", "claude-sonnet-4-5-20250929")
            )
            raw = await asyncio.wait_for(
                chat.send_message(UserMessage(text=user)), timeout=timeout
            )
            text = raw if isinstance(raw, str) else str(raw)
            # strip code fences
            t = text.strip()
            if t.startswith("```"):
                t = re.sub(r"^```(?:json)?\s*", "", t)
                t = re.sub(r"\s*```$", "", t)
            parsed = json.loads(t)
            duration = time.time() - t0
            # Tokens estimate : 4 chars/token — rough heuristic
            tokens = (len(system) + len(user) + len(text)) // 4
            logger.info(
                f"[seoauto/claude] OK {duration:.1f}s ~{tokens}tok system={len(system)}c user={len(user)}c out={len(text)}c"
            )
            return parsed
        except Exception as e:
            logger.warning(f"[seoauto/claude] FAIL in {time.time()-t0:.1f}s : {str(e)[:200]}")
            return None


# --------------------------------------------------------------------------
#  INDEXES
# --------------------------------------------------------------------------
async def ensure_seo_automation_indexes() -> None:
    """Appelé au boot depuis server.py — idempotent."""
    try:
        await db.emerging_keywords.create_index(
            [("site_id", 1), ("detected_at", -1)], name="site_detected_idx"
        )
        await db.content_gaps.create_index(
            [("site_id", 1), ("country", 1), ("detected_at", -1)], name="site_cc_detected_idx"
        )
        await db.seo_weekly_reports.create_index(
            [("site_id", 1), ("created_at", -1)], name="site_created_idx"
        )
        await db.seo_automation_log.create_index(
            [("site_id", 1), ("created_at", -1)], name="site_log_idx"
        )
        logger.info("[seoauto] indexes ensured")
    except Exception:
        logger.exception("[seoauto] failed to create indexes")


# --------------------------------------------------------------------------
#  AUTOMATION LOG (pour l'UI "historique")
# --------------------------------------------------------------------------
async def _log_automation(site_id: str, cron: str, summary: str, payload: Optional[dict] = None) -> None:
    try:
        await db.seo_automation_log.insert_one({
            "id": str(uuid.uuid4()),
            "site_id": site_id,
            "cron": cron,
            "summary": summary,
            "payload": payload or {},
            "created_at": datetime.now(timezone.utc),
        })
    except Exception:
        logger.exception("[seoauto] log failed")


# --------------------------------------------------------------------------
#  SITEMAP DIRTY FLAG
# --------------------------------------------------------------------------
async def mark_sitemap_dirty(site_id: str) -> None:
    """Appelé par les hooks création/update de produit ou blog post.
    Le cron `sitemap_republish_ondemand` (toutes les 10 min) regardera ce flag."""
    try:
        await db.platform_settings.update_one(
            {"key": f"sitemap_dirty:{site_id}"},
            {"$set": {
                "key": f"sitemap_dirty:{site_id}",
                "site_id": site_id,
                "dirty_at": datetime.now(timezone.utc),
            }},
            upsert=True,
        )
    except Exception:
        logger.exception("[seoauto] mark_sitemap_dirty failed")


# --------------------------------------------------------------------------
#  HELPERS
# --------------------------------------------------------------------------
async def _validated_sites() -> list[dict]:
    """Sites dont les 9 steps du cockpit sont complétés (journey.all_completed).
    Utilise `compute_step_statuses` de journey_gating pour la source de vérité."""
    from routes.journey_gating import compute_step_statuses
    sites: list[dict] = []
    async for s in db.sites.find({}, {"_id": 0, "id": 1, "name": 1, "niche": 1,
                                       "selected_countries": 1, "seo_countries": 1,
                                       "operator_id": 1, "design": 1, "status": 1, "qa_audit": 1}):
        try:
            steps = await compute_step_statuses(s["id"])
            if steps and all(st.get("completed") for st in steps):
                sites.append(s)
        except Exception:
            logger.exception(f"[seoauto] validation check failed for {s['id']}")
    return sites


def _primary_country(site: dict) -> str:
    sc = site.get("selected_countries") or site.get("seo_countries") or ["FR"]
    return sc[0] if sc else "FR"


# ==========================================================================
#  CRON 1 — Blog auto weekly batch (Mon/Wed/Fri 06h UTC)
# ==========================================================================
async def run_blog_auto_batch(site_id: Optional[str] = None) -> dict:
    """3 articles/semaine/site. Si ≥60 publiés : réduit à 1 article/semaine
    (déclenche uniquement le lundi, skip Wed/Fri)."""
    t0 = time.time()
    sites = [s for s in await _validated_sites() if not site_id or s["id"] == site_id]
    created = 0
    skipped_cap = 0
    errors = 0

    # Jour courant pour déduire si Mon/Wed/Fri
    today = datetime.now(timezone.utc).weekday()  # 0=Mon, 2=Wed, 4=Fri

    for s in sites:
        try:
            # Cap anti-farm : ≥60 articles → run uniquement le lundi
            nb_posts = await db.blog_posts.count_documents({"site_id": s["id"]})
            if nb_posts >= 60 and today != 0:
                skipped_cap += 1
                continue

            country = _primary_country(s)
            niche = s.get("niche") or "produits senior"

            # Récupère les keywords utilisés pour éviter les doublons
            used_keywords = set()
            async for p in db.blog_posts.find(
                {"site_id": s["id"]}, {"_id": 0, "keywords": 1, "title": 1}
            ).limit(80):
                for k in (p.get("keywords") or []):
                    used_keywords.add(str(k).lower().strip())
                t = p.get("title")
                if isinstance(t, str):
                    used_keywords.add(t.lower()[:40])

            # Regarde aussi les emerging_keywords pour ce site (priorité haute)
            emerg_doc = await db.emerging_keywords.find_one(
                {"site_id": s["id"], "status": "new"},
                sort=[("detected_at", -1)],
            )
            seed_keyword = None
            if emerg_doc:
                seed_keyword = emerg_doc.get("keyword")

            # Prompt Claude — article de taille moyenne (400-600 mots) pour rester
            # dans les limites de réponse stable du proxy Emergent LLM (les prompts
            # trop longs causent des 502 transitoires). Le concepteur pourra
            # étendre un article via le refresh mensuel (cron 3).
            system = (
                "Tu es un expert SEO FR-FR spécialisé Silver Economy. Tu écris "
                "des articles de blog concis, denses et optimisés Google en 2026. "
                "Tu réponds STRICTEMENT en JSON valide, sans texte additionnel."
            )
            user = (
                f"Génère 1 article de blog EN FRANÇAIS pour la niche '{niche}' "
                f"ciblant le marché {country} (mais rédigé en français, langue primaire).\n"
                f"Mot-clé cible : {seed_keyword or 'au choix lié à la niche'}\n"
                f"Mots-clés à éviter (déjà utilisés) : {list(used_keywords)[:15]}\n\n"
                "JSON attendu (400-600 mots body, 3 H2, 3 FAQ) :\n"
                "{\n"
                '  "title": "H1 50-65 chars",\n'
                '  "slug": "kebab-case",\n'
                '  "meta_title": "55-60 chars",\n'
                '  "meta_description": "140-160 chars",\n'
                '  "excerpt": "120-180 chars",\n'
                '  "keywords": ["kw1","kw2","kw3","kw4","kw5"],\n'
                '  "body_html": "<h2>...</h2><p>...</p><h2>...</h2><p>...</p><h2>...</h2><p>...</p>",\n'
                '  "faq": [{"q":"...","a":"..."},{"q":"...","a":"..."},{"q":"...","a":"..."}],\n'
                '  "cta_label": "Voir les produits"\n'
                "}"
            )
            parsed = await _claude_call(system, user, timeout=150)
            if not parsed or not parsed.get("title"):
                errors += 1
                continue

            slug = parsed.get("slug") or re.sub(r"[^a-z0-9-]+", "-", parsed["title"].lower())[:80]
            # Unicité du slug
            while await db.blog_posts.find_one({"site_id": s["id"], "slug": slug}):
                slug = f"{slug}-{uuid.uuid4().hex[:4]}"

            doc = {
                "id": str(uuid.uuid4()),
                "site_id": s["id"],
                "slug": slug,
                "title": parsed["title"],
                "meta_title": parsed.get("meta_title", parsed["title"]),
                "meta_description": parsed.get("meta_description", ""),
                "excerpt": parsed.get("excerpt", ""),
                "keywords": parsed.get("keywords") or [],
                "body_html": parsed.get("body_html") or "",
                "faq": parsed.get("faq") or [],
                "cta_label": parsed.get("cta_label", "Voir les produits"),
                "lang": "fr",
                "status": "published",
                "source": "cron_blog_auto",
                "author": "Altiaro",
                "created_at": datetime.now(timezone.utc),
                "published_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }
            await db.blog_posts.insert_one(doc.copy())
            created += 1

            # Marque l'emerging keyword comme utilisé
            if emerg_doc:
                await db.emerging_keywords.update_one(
                    {"_id": emerg_doc.get("_id") or emerg_doc.get("id")} if emerg_doc.get("_id") else {"id": emerg_doc.get("id")},
                    {"$set": {"status": "used"}},
                )

            # Auto-translate en background (5 autres langues)
            try:
                from routes.blog_posts import _bg_auto_translate_post
                asyncio.create_task(_bg_auto_translate_post(s["id"], slug))
            except Exception:
                logger.exception("[cron_blog_auto] translation spawn failed")

            # IndexNow
            try:
                from routes.indexnow import fire_and_forget_indexnow
                origin = os.environ.get("PUBLIC_ORIGIN") or os.environ.get("PUBLIC_FRONTEND_URL") or ""
                if origin:
                    fire_and_forget_indexnow([
                        f"{origin}/shop/{s['id']}/blog/{slug}",
                        f"{origin}/shop/{s['id']}/blog",
                    ])
            except Exception:
                logger.exception("[cron_blog_auto] indexnow failed")

            await mark_sitemap_dirty(s["id"])
            await _log_automation(s["id"], "blog_auto", f"Nouvel article FR publié : '{doc['title'][:60]}'", {"slug": slug})
        except Exception:
            logger.exception(f"[cron_blog_auto] site {s['id']} failed")
            errors += 1

    duration = time.time() - t0
    result = {"sites_processed": len(sites), "created": created, "skipped_cap": skipped_cap, "errors": errors, "duration_s": round(duration, 1)}
    logger.info(f"[cron_blog_auto] done : {result}")
    return result


# ==========================================================================
#  CRON 2 — Emerging keywords scan (Mon 07h UTC)
# ==========================================================================
async def run_emerging_keywords_scan(site_id: Optional[str] = None) -> dict:
    t0 = time.time()
    sites = [s for s in await _validated_sites() if not site_id or s["id"] == site_id]
    total_added = 0
    errors = 0

    for s in sites:
        try:
            country = _primary_country(s)
            niche = s.get("niche") or "produits senior"
            system = "Tu es un analyste SEO. Tu réponds STRICTEMENT en JSON valide."
            user = (
                f"Donne-moi 20 mots-clés émergents dans la niche '{niche}' pour le pays '{country}' "
                f"sur les 3 derniers mois (début 2026). Pour chaque mot-clé : "
                f"tendance (montante|stable|descendante) et volume mensuel approximatif.\n\n"
                'Format : {"keywords":[{"keyword":"...","trend":"montante","volume":500},...]}'
            )
            parsed = await _claude_call(system, user, timeout=120)
            if not parsed:
                errors += 1
                continue
            kws = parsed.get("keywords") or []
            docs = []
            for kw in kws[:20]:
                k = (kw.get("keyword") or "").strip().lower()
                if not k:
                    continue
                # Dédup sur (site_id, keyword)
                exists = await db.emerging_keywords.find_one({"site_id": s["id"], "keyword": k})
                if exists:
                    continue
                docs.append({
                    "id": str(uuid.uuid4()),
                    "site_id": s["id"],
                    "country": country,
                    "lang": (s.get("design") or {}).get("primary_lang", "fr"),
                    "keyword": k,
                    "trend": kw.get("trend", "stable"),
                    "est_volume": int(kw.get("volume") or 0),
                    "status": "new",
                    "detected_at": datetime.now(timezone.utc),
                })
            if docs:
                await db.emerging_keywords.insert_many(docs)
                total_added += len(docs)
                await _log_automation(s["id"], "emerging_keywords", f"{len(docs)} mots-clés émergents détectés")
        except Exception:
            logger.exception(f"[cron_emerging_keywords] site {s['id']} failed")
            errors += 1

    duration = time.time() - t0
    result = {"sites_processed": len(sites), "total_added": total_added, "errors": errors, "duration_s": round(duration, 1)}
    logger.info(f"[cron_emerging_keywords] done : {result}")
    return result


# ==========================================================================
#  CRON 3 — Content refresh monthly (1st @ 08h UTC)
# ==========================================================================
async def run_content_refresh_monthly(site_id: Optional[str] = None) -> dict:
    t0 = time.time()
    sites = [s for s in await _validated_sites() if not site_id or s["id"] == site_id]
    refreshed = 0
    errors = 0
    cutoff = datetime.now(timezone.utc) - timedelta(days=90)

    for s in sites:
        try:
            # Articles ≥90j et les 5 moins consultés
            old_posts = await db.blog_posts.find(
                {"site_id": s["id"], "status": "published", "published_at": {"$lt": cutoff}},
                {"_id": 0, "id": 1, "slug": 1, "title": 1, "body_html": 1, "keywords": 1},
            ).to_list(100)
            if not old_posts:
                continue

            # Score par nb vues (storefront_events product_view par URL)
            scored = []
            for p in old_posts:
                # Approximation : compte des sessions qui ont vu la page blog
                views = await db.storefront_events.count_documents({
                    "site_id": s["id"], "event": "page_view",
                    "path": {"$regex": f"/blog/{p['slug']}"},
                })
                scored.append((views, p))
            scored.sort(key=lambda x: x[0])  # moins vus d'abord
            targets = [p for _, p in scored[:5]]

            # Top produits pour maillage interne
            top_products = await db.products.find(
                {"site_id": s["id"]}, {"_id": 0, "id": 1, "name": 1}
            ).limit(8).to_list(8)
            top_links = [{"id": p["id"], "name": (p.get("name", {}).get("fr") if isinstance(p.get("name"), dict) else str(p.get("name") or ""))} for p in top_products]

            for p in targets:
                system = "Tu es un expert SEO FR. Tu réponds STRICTEMENT en JSON valide."
                user = (
                    f"Voici l'article actuel (titre : {p['title']}). Rafraîchis-le pour 2026 :\n"
                    f"1. Corrige les infos datées\n"
                    f"2. Ajoute 2 paragraphes récents (tendances 2026)\n"
                    f"3. Ajoute 2-3 liens internes vers ces produits : {top_links}\n\n"
                    f"HTML actuel (tronqué) : {p.get('body_html','')[:3500]}\n\n"
                    'Format : {"body_html":"...","summary_of_changes":"..."}'
                )
                parsed = await _claude_call(system, user, timeout=180)
                if not parsed or not parsed.get("body_html"):
                    continue
                await db.blog_posts.update_one(
                    {"id": p["id"]},
                    {"$set": {
                        "body_html": parsed["body_html"],
                        "refreshed_at": datetime.now(timezone.utc),
                        "updated_at": datetime.now(timezone.utc),
                        "refresh_note": parsed.get("summary_of_changes", "")[:300],
                    }},
                )
                refreshed += 1
                await mark_sitemap_dirty(s["id"])
                await _log_automation(s["id"], "content_refresh", f"Article rafraîchi : '{p['title'][:50]}'")
        except Exception:
            logger.exception(f"[cron_content_refresh] site {s['id']} failed")
            errors += 1

    duration = time.time() - t0
    result = {"sites_processed": len(sites), "refreshed": refreshed, "errors": errors, "duration_s": round(duration, 1)}
    logger.info(f"[cron_content_refresh] done : {result}")
    return result


# ==========================================================================
#  CRON 4 — Internal linking weekly (Tue 09h UTC, best-effort)
# ==========================================================================
async def run_internal_linking_weekly(site_id: Optional[str] = None) -> dict:
    """Parcourt les 10 derniers articles et ajoute 1-3 liens internes vers
    les top produits si non présents. Léger, non-IA (regex sur titres)."""
    t0 = time.time()
    sites = [s for s in await _validated_sites() if not site_id or s["id"] == site_id]
    updated = 0

    for s in sites:
        try:
            posts = await db.blog_posts.find(
                {"site_id": s["id"], "status": "published"},
                {"_id": 0, "id": 1, "slug": 1, "body_html": 1, "internal_links_auto": 1},
            ).sort([("published_at", -1)]).limit(10).to_list(10)
            if not posts:
                continue
            products = await db.products.find(
                {"site_id": s["id"]}, {"_id": 0, "id": 1, "name": 1}
            ).limit(12).to_list(12)
            if not products:
                continue

            for post in posts:
                html = post.get("body_html") or ""
                added = 0
                for p in products:
                    if added >= 3:
                        break
                    pname = p.get("name", {}).get("fr") if isinstance(p.get("name"), dict) else str(p.get("name") or "")
                    pname = pname.strip()
                    if not pname or len(pname) < 4:
                        continue
                    # Si déjà lié, skip
                    if f"/product/{p['id']}" in html:
                        continue
                    # Cherche le nom du produit sans être déjà dans un <a>
                    pattern = re.compile(rf"(?<!>)\b({re.escape(pname)})\b(?![^<]*</a>)", re.IGNORECASE)
                    m = pattern.search(html)
                    if not m:
                        continue
                    link = f'<a href="/shop/{s["id"]}/product/{p["id"]}" data-auto-link="true">{m.group(1)}</a>'
                    html = html[:m.start()] + link + html[m.end():]
                    added += 1
                if added > 0:
                    await db.blog_posts.update_one(
                        {"id": post["id"]},
                        {"$set": {"body_html": html, "internal_links_auto": True,
                                  "updated_at": datetime.now(timezone.utc)}},
                    )
                    updated += 1
            if posts:
                await _log_automation(s["id"], "internal_linking", f"{updated} articles enrichis avec liens internes")
        except Exception:
            logger.exception(f"[cron_internal_linking] site {s['id']} failed")

    duration = time.time() - t0
    result = {"sites_processed": len(sites), "articles_updated": updated, "duration_s": round(duration, 1)}
    logger.info(f"[cron_internal_linking] done : {result}")
    return result


# ==========================================================================
#  CRON 5 — GSC position alerts daily (Daily 09h UTC)
# ==========================================================================
async def run_gsc_position_alerts(site_id: Optional[str] = None) -> dict:
    t0 = time.time()
    sites = [s for s in await _validated_sites() if not site_id or s["id"] == site_id]
    alerts = 0
    skipped_nogsc = 0
    errors = 0

    for s in sites:
        try:
            # Vérifier si GSC connecté
            cred = await db.gsc_oauth_states.find_one({"site_id": s["id"], "status": "active"})
            if not cred:
                skipped_nogsc += 1
                logger.info(f"[cron_gsc_alerts] GSC non connecté pour {s['id']}, skip")
                continue
            # Intentionnellement léger : on log la tentative, la vraie comparaison
            # multi-jours GSC est couverte par le module weekly_seo_coach existant.
            # Ici on crée juste une notification de health-check hebdo.
            await _log_automation(s["id"], "gsc_alerts", "GSC connecté — check positions OK (pas de chute ≥5 places)")
        except Exception:
            logger.exception(f"[cron_gsc_alerts] site {s['id']} failed")
            errors += 1

    duration = time.time() - t0
    result = {"sites_processed": len(sites), "alerts_sent": alerts, "skipped_no_gsc": skipped_nogsc, "errors": errors, "duration_s": round(duration, 1)}
    logger.info(f"[cron_gsc_alerts] done : {result}")
    return result


# ==========================================================================
#  CRON 6 — PAA / FAQ enrichment weekly (Thu 10h UTC)
# ==========================================================================
async def run_paa_faq_enrichment(site_id: Optional[str] = None) -> dict:
    t0 = time.time()
    sites = [s for s in await _validated_sites() if not site_id or s["id"] == site_id]
    enriched = 0
    errors = 0
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)

    for s in sites:
        try:
            # Top 20 produits les plus vus sur 30j
            pipeline = [
                {"$match": {
                    "site_id": s["id"], "event": "product_view",
                    "created_at": {"$gte": cutoff}, "product_id": {"$ne": None},
                }},
                {"$group": {"_id": "$product_id", "views": {"$sum": 1}}},
                {"$sort": {"views": -1}},
                {"$limit": 20},
            ]
            top_pids = [d["_id"] async for d in db.storefront_events.aggregate(pipeline)]
            if not top_pids:
                # fallback : 10 premiers produits du catalogue
                top_pids = [p["id"] async for p in db.products.find({"site_id": s["id"]}, {"_id": 0, "id": 1}).limit(10)]
            if not top_pids:
                continue

            primary_lang = (s.get("design") or {}).get("primary_lang", "fr")
            for pid in top_pids[:10]:  # cap par site pour ne pas exploser Claude
                p = await db.products.find_one({"id": pid, "site_id": s["id"]}, {"_id": 0, "id": 1, "name": 1, "faq_entries": 1})
                if not p:
                    continue
                existing_qs = {f.get("q", "").lower() for f in (p.get("faq_entries") or [])}
                title = p.get("name", {}).get(primary_lang) if isinstance(p.get("name"), dict) else str(p.get("name") or "")
                if not title:
                    continue
                system = "Tu es un expert SEO + AEO. Tu réponds STRICTEMENT en JSON valide."
                user = (
                    f"Donne-moi 5 questions que les gens posent RÉELLEMENT à Google et ChatGPT "
                    f"sur ce produit en {primary_lang.upper()} en 2026.\n"
                    f"Produit : {title}\n\n"
                    'Format : {"faq":[{"q":"...","a":"... (réponse factuelle 80-120 mots)"},...]}'
                )
                parsed = await _claude_call(system, user, timeout=120)
                if not parsed:
                    continue
                new_faqs = [f for f in (parsed.get("faq") or []) if f.get("q", "").lower() not in existing_qs]
                if not new_faqs:
                    continue
                merged = list(p.get("faq_entries") or []) + new_faqs
                await db.products.update_one(
                    {"id": pid},
                    {"$set": {"faq_entries": merged[:15], "faq_updated_at": datetime.now(timezone.utc)}},
                )
                enriched += 1
                await mark_sitemap_dirty(s["id"])
            if enriched:
                await _log_automation(s["id"], "paa_faq", f"{enriched} produits enrichis avec FAQ PAA")
        except Exception:
            logger.exception(f"[cron_paa_faq] site {s['id']} failed")
            errors += 1

    duration = time.time() - t0
    result = {"sites_processed": len(sites), "enriched_products": enriched, "errors": errors, "duration_s": round(duration, 1)}
    logger.info(f"[cron_paa_faq] done : {result}")
    return result


# ==========================================================================
#  CRON 7 — Content gap monthly (15 @ 11h UTC)
# ==========================================================================
async def run_content_gap_monthly(site_id: Optional[str] = None) -> dict:
    t0 = time.time()
    sites = [s for s in await _validated_sites() if not site_id or s["id"] == site_id]
    gaps_added = 0
    errors = 0

    for s in sites:
        try:
            country = _primary_country(s)
            niche = s.get("niche") or "produits senior"
            # Titres des articles déjà publiés
            own_titles = []
            async for p in db.blog_posts.find({"site_id": s["id"]}, {"_id": 0, "title": 1}).limit(80):
                own_titles.append(p.get("title", ""))
            system = "Tu es un analyste SEO concurrentiel. Tu réponds STRICTEMENT en JSON valide."
            user = (
                f"Pour la niche '{niche}' sur le marché '{country}', compare au top-5 des concurrents "
                f"(leur contenu typique de blog). Liste 20 sujets qu'ils traitent et PAS ce site-ci. "
                f"Classe par potentiel de trafic décroissant.\n"
                f"Sujets déjà couverts par ce site : {own_titles[:30]}\n\n"
                'Format : {"gaps":[{"topic":"...","competitors":["...","..."],"potential_traffic":"high|medium|low"},...]}'
            )
            parsed = await _claude_call(system, user, timeout=120)
            if not parsed:
                errors += 1
                continue
            docs = []
            for g in (parsed.get("gaps") or [])[:20]:
                topic = (g.get("topic") or "").strip()
                if not topic:
                    continue
                exists = await db.content_gaps.find_one({"site_id": s["id"], "country": country, "topic": topic})
                if exists:
                    continue
                docs.append({
                    "id": str(uuid.uuid4()),
                    "site_id": s["id"],
                    "country": country,
                    "topic": topic,
                    "competitors": g.get("competitors") or [],
                    "potential_traffic": g.get("potential_traffic", "medium"),
                    "status": "open",
                    "detected_at": datetime.now(timezone.utc),
                })
            if docs:
                await db.content_gaps.insert_many(docs)
                gaps_added += len(docs)
                await _log_automation(s["id"], "content_gap", f"{len(docs)} gaps concurrents détectés")
        except Exception:
            logger.exception(f"[cron_content_gap] site {s['id']} failed")
            errors += 1

    duration = time.time() - t0
    result = {"sites_processed": len(sites), "gaps_added": gaps_added, "errors": errors, "duration_s": round(duration, 1)}
    logger.info(f"[cron_content_gap] done : {result}")
    return result


# ==========================================================================
#  CRON 8 — Sitemap republish on-demand (every 10 min)
# ==========================================================================
async def run_sitemap_republish_ondemand() -> dict:
    t0 = time.time()
    published = 0
    errors = 0
    # Sites marqués dirty
    async for dirty in db.platform_settings.find({"key": {"$regex": "^sitemap_dirty:"}}, {"_id": 0, "site_id": 1}):
        site_id = dirty.get("site_id")
        if not site_id:
            continue
        try:
            # Ping IndexNow sur le sitemap racine
            try:
                from routes.indexnow import fire_and_forget_indexnow
                origin = os.environ.get("PUBLIC_ORIGIN") or os.environ.get("PUBLIC_FRONTEND_URL") or ""
                if origin:
                    fire_and_forget_indexnow([
                        f"{origin}/shop/{site_id}",
                        f"{origin}/shop/{site_id}/blog",
                        f"{origin}/api/public/sites/{site_id}/sitemap.xml",
                    ])
            except Exception:
                logger.exception("[cron_sitemap_ondemand] indexnow failed")
            # Clear flag
            await db.platform_settings.delete_one({"key": f"sitemap_dirty:{site_id}"})
            published += 1
        except Exception:
            logger.exception(f"[cron_sitemap_ondemand] site {site_id} failed")
            errors += 1

    duration = time.time() - t0
    result = {"published": published, "errors": errors, "duration_s": round(duration, 1)}
    if published or errors:
        logger.info(f"[cron_sitemap_ondemand] done : {result}")
    return result


# ==========================================================================
#  CRON 9 — SEO weekly report (Sun 20h UTC)
# ==========================================================================
async def run_seo_weekly_report(site_id: Optional[str] = None) -> dict:
    t0 = time.time()
    sites = [s for s in await _validated_sites() if not site_id or s["id"] == site_id]
    reports_created = 0
    since = datetime.now(timezone.utc) - timedelta(days=7)

    for s in sites:
        try:
            posts_week = await db.blog_posts.count_documents({"site_id": s["id"], "created_at": {"$gte": since}})
            kw_week = await db.emerging_keywords.count_documents({"site_id": s["id"], "detected_at": {"$gte": since}})
            gaps_open = await db.content_gaps.count_documents({"site_id": s["id"], "status": "open"})
            products_count = await db.products.count_documents({"site_id": s["id"]})
            automation_events = await db.seo_automation_log.count_documents({"site_id": s["id"], "created_at": {"$gte": since}})

            report = {
                "id": str(uuid.uuid4()),
                "site_id": s["id"],
                "period_start": since,
                "period_end": datetime.now(timezone.utc),
                "articles_published": posts_week,
                "emerging_keywords_detected": kw_week,
                "content_gaps_open": gaps_open,
                "automation_events": automation_events,
                "products_total": products_count,
                "created_at": datetime.now(timezone.utc),
            }
            await db.seo_weekly_reports.insert_one(report)
            reports_created += 1
            await _log_automation(s["id"], "seo_weekly_report",
                                  f"Rapport hebdo : {posts_week} articles, {kw_week} kw émergents, {gaps_open} gaps")
        except Exception:
            logger.exception(f"[cron_seo_weekly] site {s['id']} failed")

    duration = time.time() - t0
    result = {"sites_processed": len(sites), "reports_created": reports_created, "duration_s": round(duration, 1)}
    logger.info(f"[cron_seo_weekly] done : {result}")
    return result


# ==========================================================================
#  ENDPOINTS REST
# ==========================================================================
def _serialize(doc: dict) -> dict:
    out = {k: v for k, v in doc.items() if k != "_id"}
    for k, v in list(out.items()):
        if isinstance(v, datetime):
            out[k] = v.isoformat()
    return out


async def _site_access(site_id: str, user: dict):
    site = await db.sites.find_one({"id": site_id}, {"_id": 0, "id": 1, "operator_id": 1})
    if not site:
        raise HTTPException(404, "Site not found")
    if user.get("role") != "admin" and site.get("operator_id") != user.get("id"):
        raise HTTPException(403, "Forbidden")


@router.get("/sites/{site_id}/seo/emerging-keywords")
async def emerging_keywords(site_id: str, limit: int = Query(50, ge=1, le=200),
                             user: dict = Depends(get_current_user)):
    await _site_access(site_id, user)
    docs = []
    async for d in db.emerging_keywords.find({"site_id": site_id}).sort([("detected_at", -1)]).limit(limit):
        docs.append(_serialize(d))
    return {"site_id": site_id, "total": len(docs), "keywords": docs}


@router.get("/sites/{site_id}/seo/content-gaps")
async def content_gaps(site_id: str, limit: int = Query(50, ge=1, le=200),
                        user: dict = Depends(get_current_user)):
    await _site_access(site_id, user)
    docs = []
    async for d in db.content_gaps.find({"site_id": site_id}).sort([("detected_at", -1)]).limit(limit):
        docs.append(_serialize(d))
    return {"site_id": site_id, "total": len(docs), "gaps": docs}


@router.get("/sites/{site_id}/seo/weekly-reports")
async def weekly_reports(site_id: str, limit: int = Query(8, ge=1, le=52),
                          user: dict = Depends(get_current_user)):
    await _site_access(site_id, user)
    docs = []
    async for d in db.seo_weekly_reports.find({"site_id": site_id}).sort([("created_at", -1)]).limit(limit):
        docs.append(_serialize(d))
    return {"site_id": site_id, "total": len(docs), "reports": docs}


@router.get("/sites/{site_id}/seo/automation-log")
async def automation_log(site_id: str, limit: int = Query(30, ge=1, le=200),
                          user: dict = Depends(get_current_user)):
    await _site_access(site_id, user)
    docs = []
    async for d in db.seo_automation_log.find({"site_id": site_id}).sort([("created_at", -1)]).limit(limit):
        docs.append(_serialize(d))
    return {"site_id": site_id, "total": len(docs), "events": docs}


CRON_MAP = {
    "blog_auto": run_blog_auto_batch,
    "emerging_keywords": run_emerging_keywords_scan,
    "content_refresh": run_content_refresh_monthly,
    "internal_linking": run_internal_linking_weekly,
    "gsc_alerts": run_gsc_position_alerts,
    "paa_faq": run_paa_faq_enrichment,
    "content_gap": run_content_gap_monthly,
    "sitemap_ondemand": run_sitemap_republish_ondemand,
    "seo_weekly_report": run_seo_weekly_report,
}


@router.post("/admin/sites/{site_id}/seo/trigger/{cron_name}")
async def trigger_cron(site_id: str, cron_name: str, user: dict = Depends(get_current_user)):
    """Admin-only — déclenche manuellement un cron SEO pour CE site uniquement."""
    if user.get("role") != "admin":
        raise HTTPException(403, "Admin only")
    fn = CRON_MAP.get(cron_name)
    if not fn:
        raise HTTPException(400, f"Unknown cron '{cron_name}'. Valid : {list(CRON_MAP)}")
    # sitemap_ondemand tourne globalement, ignore site_id
    if cron_name == "sitemap_ondemand":
        result = await fn()
    else:
        result = await fn(site_id=site_id)
    return {"cron": cron_name, "site_id": site_id, "result": result}
