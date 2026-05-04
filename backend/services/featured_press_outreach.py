"""Featured.com (ex-HARO modern equivalent) — Press Outreach Worker.

Docs : https://featured.com/help/api
Auth : Bearer FEATURED_API_KEY (.env)

Le pipeline quotidien (cron 09h00 UTC) :
  1. Pour chaque site avec `marketing.featured.enabled=true` :
     a. Fetch les questions ouvertes des journalistes matching keywords du site.
     b. Filtre par pertinence vs niche.
     c. Pour chaque question pertinente : génère via Claude une réponse 100-200
        mots, ton premium, factuel, citation experte.
     d. POST la réponse via API Featured.
     e. Persiste dans `db.featured_responses`.
  2. Tracking pickup : check 24h plus tard si la réponse a été publiée
     (champ `picked_at` + `published_url` populated).

L'API Featured étant en évolution permanente, ce module est codé défensivement
autour d'endpoints REST raisonnablement standards. Si la signature change,
la seule fonction à ajuster est `_request()`.
”””
from __future__ import annotations

import asyncio
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

from deps import db
from services.llm_resilience import safe_claude_json

logger = logging.getLogger("altiaro.featured")

FEATURED_API_BASE = os.environ.get("FEATURED_API_BASE", "https://api.featured.com/v1")
_TIMEOUT = httpx.Timeout(20.0, connect=10.0)


def _api_key() -> Optional[str]:
    return os.environ.get("FEATURED_API_KEY") or None


async def _request(method: str, path: str, **kw) -> Dict[str, Any]:
    key = _api_key()
    if not key:
        return {"ok": False, "reason": "missing_api_key"}
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "User-Agent": "Altiaro-Featured-Worker/1.0",
    }
    headers.update(kw.pop("headers", {}) or {})
    url = f"{FEATURED_API_BASE}{path}"
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as cli:
            r = await cli.request(method, url, headers=headers, **kw)
        if r.status_code >= 400:
            return {"ok": False, "status": r.status_code, "error": r.text[:300]}
        return {"ok": True, "status": r.status_code, "data": r.json() if r.content else {}}
    except Exception as e:
        return {"ok": False, "reason": "http_error", "error": str(e)[:300]}


async def fetch_pending_queries(keywords: List[str]) -> List[Dict[str, Any]]:
    """Renvoie les queries ouvertes matching un keyword."""
    if not keywords:
        return []
    out: List[Dict[str, Any]] = []
    seen: set = set()
    for kw in keywords[:5]:
        res = await _request("GET", "/queries", params={"keyword": kw, "status": "open", "limit": 25})
        if not res.get("ok"):
            continue
        items = (res.get("data") or {}).get("items") or (res.get("data") if isinstance(res.get("data"), list) else [])
        for q in items or []:
            qid = q.get("id") or q.get("query_id")
            if qid and qid not in seen:
                seen.add(qid)
                out.append(q)
    return out


def _q_text(q: Dict[str, Any]) -> str:
    return q.get("question") or q.get("prompt") or q.get("title") or ""


def filter_relevant(queries: List[Dict[str, Any]], niche: str) -> List[Dict[str, Any]]:
    """Heuristique simple : retient les queries dont le texte contient un
    mot de la niche. Pas de NLP fancy - si trop strict, l'utilisateur
    elargira `keywords` dans `marketing.featured.keywords`."""
    if not niche:
        return queries
    needles = [w.lower() for w in niche.split() if len(w) > 3]
    if not needles:
        return queries
    out = []
    for q in queries:
        t = _q_text(q).lower()
        if any(n in t for n in needles):
            out.append(q)
    return out


async def generate_expert_response(query: Dict[str, Any], brand_context: Dict[str, Any]) -> Optional[str]:
    system = (
        "Tu rédiges des réponses presse pour un journaliste qui prépare un article. "
        "Ton : expert, factuel, citation premium. Pas de jargon, pas de superlatif vide."
    )
    user = (
        f"Question journaliste : \"{_q_text(query)}\"\n\n"
        f"Marque source : {brand_context.get('brand_name')} ({brand_context.get('domain')})\n"
        f"Niche : {brand_context.get('niche')}\n"
        f"Tagline : {brand_context.get('tagline','')}\n\n"
        "Rédige une réponse de 100-200 mots maximum, ton premium expert. "
        "Inclus 1 statistique ou fait concret vérifiable. "
        "Termine par une mention discrète de la marque sous forme « Source : … ». "
        "Format JSON : {\"response\": \"...\"}"
    )
    try:
        data = await safe_claude_json(
            system, user, quality_tier="standard",
            session_id=f"featured-{(query.get('id') or '')[:12]}",
            timeout=60, request_id="featured",
        )
        return (data.get("response") or "").strip() or None
    except Exception as e:
        logger.warning(f"[featured] gen response failed: {str(e)[:200]}")
        return None


async def submit_response(query_id: str, response_text: str,
                          expert_name: str = "Altiaro Editorial Team") -> Dict[str, Any]:
    body = {
        "query_id": query_id,
        "response": response_text,
        "expert_name": expert_name,
        "expert_title": "Équipe éditoriale",
    }
    return await _request("POST", "/responses", json=body)


async def track_published(query_id: str) -> Dict[str, Any]:
    """Check si la réponse a été utilisée par un journaliste."""
    return await _request("GET", f"/queries/{query_id}/status")


async def run_for_site(site: dict) -> Dict[str, Any]:
    site_id = site["id"]
    marketing = (site.get("marketing") or {}).get("featured") or {}
    if not marketing.get("enabled"):
        return {"ok": False, "reason": "site_not_enabled"}
    keywords = marketing.get("keywords") or [site.get("niche", "")]
    queries = await fetch_pending_queries(keywords)
    relevant = filter_relevant(queries, site.get("niche", ""))
    brand = (site.get("design") or {}).get("brand") or {}
    ctx = {
        "brand_name": brand.get("name") or site.get("name"),
        "domain": site.get("custom_domain"),
        "niche": site.get("niche"),
        "tagline": (site.get("about_rich") or {}).get("tagline"),
    }
    sent = 0
    for q in relevant[:6]:  # cap 6/jour pour rester sous le freemium
        text = await generate_expert_response(q, ctx)
        if not text:
            continue
        sub = await submit_response(q.get("id") or q.get("query_id"), text)
        await db.featured_responses.insert_one({
            "id": str(uuid.uuid4()),
            "site_id": site_id,
            "query_id": q.get("id") or q.get("query_id"),
            "query_text": _q_text(q)[:500],
            "response_text": text,
            "submitted_at": datetime.now(timezone.utc).isoformat(),
            "submit_result": sub,
            "picked": False,
        })
        if sub.get("ok"):
            sent += 1
    return {
        "ok": True, "site_id": site_id,
        "queries_seen": len(queries), "queries_relevant": len(relevant),
        "responses_sent": sent,
    }


async def daily_tick() -> Dict[str, Any]:
    """Cron entry. Itere sur tous les sites avec featured.enabled=true."""
    if not _api_key():
        return {"ok": False, "reason": "missing_api_key"}
    sites = await db.sites.find(
        {"marketing.featured.enabled": True},
        {"_id": 0, "id": 1, "name": 1, "niche": 1, "design": 1,
         "custom_domain": 1, "about_rich": 1, "marketing": 1},
    ).to_list(200)
    res: List[Dict[str, Any]] = []
    for s in sites:
        try:
            r = await run_for_site(s)
            res.append(r)
        except Exception as e:
            res.append({"site_id": s.get("id"), "ok": False, "error": str(e)[:200]})
    return {"ok": True, "sites_processed": len(sites), "results": res}
