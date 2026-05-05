"""TÂCHE 3.6 — Worker E-E-A-T refresh des articles blog (Sprint 5 SEO).

Pour chaque article > 60 jours :
    - met à jour `dateModified` dans le JSON-LD Article (via updated_at)
    - ajoute 100-200 mots de contenu récent (LLM Claude Haiku, faits 2026)
    - refresh la date publié dans schema.org

À planifier en mensuel via APScheduler.
"""
from __future__ import annotations

import asyncio
import logging
import os
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from deps import db

logger = logging.getLogger("altiaro.eeat_refresh")

_REFRESH_PROMPT = """Tu es un expert SEO E-E-A-T. Voici un article blog publié il y a {age_days} jours :

TITRE : {title}
RÉSUMÉ : {excerpt}

Génère 1 PARAGRAPHE de 100-150 mots à insérer en fin d'article (avant la FAQ),
qui :
- ajoute une donnée chiffrée 2026 OU une référence récente (institution, étude, presse)
- met à jour la perspective sans dénigrer le contenu existant
- garde le ton initial (factuel, expertise)
- inclut 1 lien externe en markdown vers une source crédible (service-public.fr, INSEE, OMS, ameli.fr, etc.)

RÉPONSE FORMAT JSON STRICT :
{{
  "addendum_md": "## Mise à jour {year}\\n\\n[paragraphe 100-150 mots avec [ancre](url)]"
}}
"""


async def _generate_addendum(
    *, title: str, excerpt: str, age_days: int, year: int = 2026,
    timeout_s: float = 50.0,
) -> Optional[str]:
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
    except Exception:
        return None
    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        return None
    prompt = _REFRESH_PROMPT.format(
        title=title[:200], excerpt=excerpt[:300], age_days=age_days, year=year,
    )
    try:
        chat = LlmChat(
            api_key=api_key,
            session_id=f"eeat_refresh_{title[:30]}",
            system_message="Tu es expert SEO E-E-A-T. JSON strict.",
        ).with_model("anthropic", "claude-haiku-4-5-20251001")
        resp = await asyncio.wait_for(
            chat.send_message(UserMessage(text=prompt)), timeout=timeout_s,
        )
        if not resp:
            return None
        text = resp.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```\s*$", "", text)
        import json as _json
        data = _json.loads(text)
        return data.get("addendum_md")
    except Exception as e:
        logger.warning(f"[eeat_refresh] LLM failed: {str(e)[:140]}")
        return None


async def refresh_old_blog_posts(
    site_id: Optional[str] = None,
    *, age_days_threshold: int = 60,
    limit: int = 50,
    concurrency: int = 2,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Refresh articles blog > age_days_threshold pour booster E-E-A-T.

    Si `site_id` None → traite tous les sites. Sinon scope unique.
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(days=age_days_threshold)).isoformat()
    query: Dict[str, Any] = {
        "$or": [
            {"updated_at": {"$lt": cutoff}},
            {"created_at": {"$lt": cutoff}, "updated_at": {"$exists": False}},
        ],
        "status": {"$in": ["published", None]},
    }
    if site_id:
        query["site_id"] = site_id

    candidates = await db.blog_posts.find(
        query,
        {"_id": 0, "id": 1, "site_id": 1, "title": 1, "excerpt": 1,
         "body_md": 1, "body": 1, "language": 1, "lang": 1,
         "updated_at": 1, "created_at": 1, "eeat_refreshed_at": 1},
    ).limit(limit).to_list(limit)

    if dry_run:
        return {"ok": True, "dry_run": True, "candidates": len(candidates)}

    sem = asyncio.Semaphore(concurrency)
    refreshed = 0
    skipped = 0
    failed = 0

    async def _process(bp):
        nonlocal refreshed, skipped, failed
        async with sem:
            # Skip if recently refreshed
            last_refresh = bp.get("eeat_refreshed_at")
            if last_refresh:
                try:
                    last_dt = datetime.fromisoformat(last_refresh.replace("Z", "+00:00"))
                    if (datetime.now(timezone.utc) - last_dt).days < 30:
                        skipped += 1
                        return
                except Exception:
                    pass

            lang = bp.get("language") or bp.get("lang") or "fr"
            title_raw = bp.get("title") or ""
            if isinstance(title_raw, dict):
                title_raw = title_raw.get(lang) or title_raw.get("fr") or next(iter(title_raw.values()), "")
            excerpt_raw = bp.get("excerpt") or ""
            if isinstance(excerpt_raw, dict):
                excerpt_raw = excerpt_raw.get(lang) or excerpt_raw.get("fr") or ""

            created = bp.get("created_at") or bp.get("updated_at") or ""
            try:
                created_dt = datetime.fromisoformat(str(created).replace("Z", "+00:00"))
                age_days = (datetime.now(timezone.utc) - created_dt).days
            except Exception:
                age_days = 90

            addendum = await _generate_addendum(
                title=str(title_raw), excerpt=str(excerpt_raw), age_days=age_days,
            )
            if not addendum:
                failed += 1
                return

            now_iso = datetime.now(timezone.utc).isoformat()

            # Append to body_md (multilingue ou string)
            body_field = "body_md" if "body_md" in bp else "body"
            body_val = bp.get(body_field) or ""
            if isinstance(body_val, dict):
                cur = body_val.get(lang) or ""
                body_val[lang] = cur + "\n\n" + addendum
                new_body = body_val
            else:
                new_body = str(body_val) + "\n\n" + addendum

            await db.blog_posts.update_one(
                {"id": bp["id"]},
                {"$set": {
                    body_field: new_body,
                    "updated_at": now_iso,
                    "eeat_refreshed_at": now_iso,
                    "eeat_refresh_count": (bp.get("eeat_refresh_count") or 0) + 1,
                }},
            )
            refreshed += 1

    await asyncio.gather(*[_process(bp) for bp in candidates], return_exceptions=True)

    return {
        "ok": True,
        "candidates": len(candidates),
        "refreshed": refreshed,
        "skipped_recent": skipped,
        "failed": failed,
    }
