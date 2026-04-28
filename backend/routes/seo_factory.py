"""Phase B6+B7 — Factory keywords + landings + AEO pages.
MVP minimal : extraction long-tail, clustering, génération landing.
Les appels lourds sont plafonnés par budget."""
from __future__ import annotations
import logging, uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from deps import db, get_current_user
from services.llm_resilience import safe_claude_json

router = APIRouter(tags=["seo-factory"])
logger = logging.getLogger("altiaro.seo_factory")

INTENTS = ["buy", "review", "compare", "price", "size", "material", "alternative", "vs", "shipping", "return"]


class DiscoverInput(BaseModel):
    product_id: Optional[str] = None
    locale: str = "fr-FR"
    target_count: int = 50


class ClusterInput(BaseModel):
    locale: str = "fr-FR"
    max_clusters: int = 20


class LandingsInput(BaseModel):
    cluster_ids: Optional[List[str]] = None
    locale: str = "fr-FR"
    max_landings: int = 5


async def _check_owner(site_id: str, user: dict):
    s = await db.sites.find_one({"id": site_id}, {"_id": 0, "operator_id": 1, "id": 1, "name": 1, "niche": 1})
    if not s:
        raise HTTPException(404, "Site introuvable")
    if user.get("role") != "admin" and s.get("operator_id") != user.get("id"):
        raise HTTPException(403, "Accès interdit")
    return s


@router.post("/sites/{site_id}/seo/keywords/discover")
async def discover_keywords(site_id: str, data: DiscoverInput, user: dict = Depends(get_current_user)):
    site = await _check_owner(site_id, user)
    products = await db.products.find({"site_id": site_id}, {"_id": 0, "id": 1, "name": 1, "category": 1}).to_list(length=None)
    if not products:
        raise HTTPException(400, "Site sans produits")
    target_products = [p for p in products if not data.product_id or p["id"] == data.product_id]
    keywords_total = 0
    for p in target_products[:5]:  # cap : 5 produits / appel
        name = p.get("name")
        if isinstance(name, dict):
            name = name.get("fr") or name.get("en") or "produit"
        prompt = (
            f"Génère {min(data.target_count, 50)} requêtes long-tail Google pour le produit '{name}' "
            f"(niche: {site.get('niche','')}, locale: {data.locale}). "
            f"Couvre les intents: {', '.join(INTENTS)}. "
            f"Format JSON: {{keywords: [{{q, intent, volume_est (10-10000), difficulty (0-100)}}]}}"
        )
        try:
            out = await safe_claude_json(
                system="Stratège SEO expert long-tail. JSON strict.",
                user=prompt, quality_tier="speed", request_id=f"kw-{site_id[:8]}-{p['id'][:6]}", timeout=90,
            )
        except Exception as e:
            logger.warning(f"[seo-factory] discover failed for {p['id'][:8]}: {str(e)[:120]}")
            continue
        kws = (out or {}).get("keywords") or []
        for kw in kws:
            if not isinstance(kw, dict) or not kw.get("q"):
                continue
            doc = {
                "id": str(uuid.uuid4()),
                "site_id": site_id,
                "product_id": p["id"],
                "locale": data.locale,
                "keyword": kw["q"][:250],
                "intent": kw.get("intent", "buy"),
                "search_volume_est": int(kw.get("volume_est") or 100),
                "difficulty_est": int(kw.get("difficulty") or 30),
                "pillar_id": None,
                "status": "discovered",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            await db.keyword_universe.update_one(
                {"site_id": site_id, "locale": data.locale, "keyword": doc["keyword"]},
                {"$setOnInsert": doc},
                upsert=True,
            )
            keywords_total += 1
    return {"ok": True, "keywords_added": keywords_total}


@router.post("/sites/{site_id}/seo/keywords/cluster")
async def cluster_keywords(site_id: str, data: ClusterInput, user: dict = Depends(get_current_user)):
    await _check_owner(site_id, user)
    kws = await db.keyword_universe.find({"site_id": site_id, "locale": data.locale, "pillar_id": None}, {"_id": 0}).to_list(length=500)
    if not kws:
        return {"ok": True, "clusters_created": 0}
    listing = [{"id": k["id"], "q": k["keyword"], "intent": k["intent"]} for k in kws[:200]]
    prompt = (
        f"Regroupe ces {len(listing)} mots-clés en {data.max_clusters} clusters sémantiques. "
        f"Chaque cluster = 5-15 mots-clés proches partageant un même angle de page. "
        f"Format JSON: {{clusters: [{{slug, title, intent, keyword_ids: [...]}}]}}\n\nINPUT:{listing}"
    )
    try:
        out = await safe_claude_json(
            system="Stratège SEO. JSON strict.",
            user=prompt, quality_tier="premium", request_id=f"cluster-{site_id[:8]}", timeout=120,
        )
    except Exception as e:
        raise HTTPException(502, f"Clustering échoué: {str(e)[:120]}")
    clusters = (out or {}).get("clusters") or []
    created = 0
    for c in clusters:
        cid = str(uuid.uuid4())
        await db.keyword_clusters.insert_one({
            "id": cid, "site_id": site_id, "locale": data.locale,
            "slug": c.get("slug") or f"cluster-{cid[:6]}",
            "title": c.get("title", ""), "intent": c.get("intent", "buy"),
            "keyword_count": len(c.get("keyword_ids") or []),
            "landing_status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        for kid in c.get("keyword_ids") or []:
            await db.keyword_universe.update_one({"id": kid, "site_id": site_id}, {"$set": {"pillar_id": cid}})
        created += 1
    return {"ok": True, "clusters_created": created}


@router.post("/sites/{site_id}/seo/landings/generate")
async def generate_landings(site_id: str, data: LandingsInput, user: dict = Depends(get_current_user)):
    site = await _check_owner(site_id, user)
    q = {"site_id": site_id, "locale": data.locale, "landing_status": "pending"}
    if data.cluster_ids:
        q["id"] = {"$in": data.cluster_ids}
    clusters = await db.keyword_clusters.find(q, {"_id": 0}).limit(data.max_landings).to_list(length=data.max_landings)
    created = []
    for c in clusters:
        kws = await db.keyword_universe.find({"pillar_id": c["id"]}, {"_id": 0, "keyword": 1}).to_list(length=20)
        kw_text = ", ".join(k["keyword"] for k in kws)
        prompt = (
            f"Crée une landing page SEO premium 1500+ mots ciblant : {c.get('title','')}. "
            f"Mots-clés à couvrir : {kw_text}. Marque : {site.get('name','')} ({site.get('niche','')}). "
            f"Langue : {data.locale}. Format JSON: {{h1, intro_html, sections: [{{h2, body_html}}], faq: [{{q,a}}], cta_label, meta_title, meta_description}}."
        )
        try:
            out = await safe_claude_json(
                system="Rédacteur SEO premium. JSON strict.",
                user=prompt, quality_tier="premium", request_id=f"landing-{c['id'][:8]}", timeout=180,
            )
        except Exception as e:
            logger.warning(f"[seo-factory] landing failed for cluster {c['id'][:8]}: {str(e)[:120]}")
            continue
        if not isinstance(out, dict) or not out.get("h1"):
            continue
        lid = str(uuid.uuid4())
        doc = {
            "id": lid, "site_id": site_id, "cluster_id": c["id"], "locale": data.locale,
            "slug": c.get("slug") or f"landing-{lid[:6]}",
            "h1": out.get("h1"), "intro_html": out.get("intro_html", ""),
            "sections": out.get("sections", []), "faq": out.get("faq", []),
            "cta_label": out.get("cta_label", ""),
            "meta_title": out.get("meta_title", ""), "meta_description": out.get("meta_description", ""),
            "status": "published",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await db.landing_pages.insert_one(doc)
        await db.keyword_clusters.update_one({"id": c["id"]}, {"$set": {"landing_status": "generated", "landing_id": lid}})
        created.append({"id": lid, "slug": doc["slug"], "h1": doc["h1"]})
    return {"ok": True, "landings_created": len(created), "landings": created}


@router.get("/sites/{site_id}/seo/factory/state")
async def factory_state(site_id: str, user: dict = Depends(get_current_user)):
    await _check_owner(site_id, user)
    return {
        "keywords_total": await db.keyword_universe.count_documents({"site_id": site_id}),
        "keywords_by_locale": {l: await db.keyword_universe.count_documents({"site_id": site_id, "locale": l}) for l in ["fr-FR", "en-GB", "de-DE", "nl-NL", "it-IT", "es-ES"]},
        "clusters_total": await db.keyword_clusters.count_documents({"site_id": site_id}),
        "landings_total": await db.landing_pages.count_documents({"site_id": site_id}),
    }
