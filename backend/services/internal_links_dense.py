"""TÂCHE 3.3 — Internal linking dense (Sprint 5 SEO).

Calcule un graphe de maillage croisé entre :
    - Produits ↔ Articles blog (Jaccard sur tokens normalisés)
    - Produits ↔ Buyer guides / Top lists / Comparisons
    - Articles blog ↔ Produits (auto-suggestions)

Persiste les liens dans :
    - product.related_blog_posts = [{slug, title, score}]   (top 3-5)
    - blog_post.related_products = [{slug, title, score}]  (top 2-3)
    - product.related_landings = [{slug, title, kind}]     (top 2-3)

Ces champs sont ensuite consommés par :
    - routes/prerender.py (PDP) → injecte HTML <section>articles connexes</section>
    - storefront PDP component (frontend) → sidebar produits

API publique : `rebuild_internal_links(site_id)` à appeler après chaque
launch ou lors d'un job batch (ex: SEO refresh worker).
"""
from __future__ import annotations

import logging
import re
from collections import Counter
from typing import Any, Dict, List

from deps import db

logger = logging.getLogger("altiaro.internal_links_dense")

# Mots-outils (stop-words) à filtrer pour le calcul Jaccard
_STOP_FR = {
    "le", "la", "les", "un", "une", "des", "de", "du", "et", "ou", "à", "au",
    "aux", "ce", "cet", "cette", "ces", "pour", "par", "sur", "dans", "avec",
    "sans", "que", "qui", "dont", "où", "comment", "pourquoi", "quand", "vous",
    "nous", "ils", "elles", "ils", "il", "elle", "se", "sa", "son", "ses",
    "mon", "ma", "mes", "leur", "leurs", "notre", "votre", "est", "sont", "ont",
    "été", "être", "avoir", "fait", "plus", "moins", "tres", "très", "bien",
    "même", "aussi", "comme", "tout", "tous", "toute", "toutes", "ne", "pas",
    "y", "en",
}
_STOP_EN = {
    "the", "a", "an", "and", "or", "of", "to", "for", "in", "on", "with",
    "without", "is", "are", "was", "were", "be", "been", "have", "has", "had",
    "this", "that", "these", "those", "it", "its", "their", "our", "your",
    "what", "how", "why", "when", "where", "you", "we", "they", "he", "she",
    "from", "by", "at", "as", "but", "not", "no", "yes", "all", "any", "more",
    "most", "less", "very", "so", "too", "also", "than", "then", "if", "up",
    "down", "out", "over",
}
_STOP = _STOP_FR | _STOP_EN

_TOKEN_RE = re.compile(r"[a-zA-Zàâäéèêëïîôöùûüÿç]{3,}", re.IGNORECASE)


def _tokenize(text: str) -> List[str]:
    if not text:
        return []
    if isinstance(text, dict):
        # multilingue → concatène toutes les langues
        text = " ".join(str(v) for v in text.values() if isinstance(v, str))
    out = [t.lower() for t in _TOKEN_RE.findall(str(text))]
    return [t for t in out if t not in _STOP and len(t) >= 4]


def _jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def _flat_text(d: Dict[str, Any], keys: List[str]) -> str:
    parts = []
    for k in keys:
        v = d.get(k)
        if isinstance(v, dict):
            parts.extend(str(x) for x in v.values() if isinstance(x, str))
        elif isinstance(v, list):
            for it in v:
                if isinstance(it, str):
                    parts.append(it)
                elif isinstance(it, dict):
                    parts.extend(str(x) for x in it.values() if isinstance(x, str))
        elif isinstance(v, str):
            parts.append(v)
    return " ".join(parts)


def _pick_lang_str(v: Any, lang: str = "fr") -> str:
    if isinstance(v, dict):
        return v.get(lang) or v.get("fr") or v.get("en") or next(iter(v.values()), "") or ""
    return str(v or "")


async def rebuild_internal_links(site_id: str, *, lang: str = "fr") -> Dict[str, Any]:
    """Recalcule l'ensemble du maillage interne pour un site.

    Returns
    -------
        Stats dict {products_updated, blogs_updated, landings_indexed, ...}
    """
    products = await db.products.find(
        {"site_id": site_id, "status": "active"},
        {"_id": 0, "id": 1, "slug": 1, "name": 1, "description": 1, "tagline": 1,
         "usps": 1, "category": 1, "categories": 1, "aeo_snippet": 1},
    ).to_list(2000)

    blogs = await db.blog_posts.find(
        {"site_id": site_id, "status": {"$ne": "draft"}},
        {"_id": 0, "id": 1, "slug": 1, "title": 1, "intro": 1,
         "content": 1, "h2_outline": 1, "tags": 1},
    ).to_list(2000)

    landings = await db.landing_pages.find(
        {"site_id": site_id},
        {"_id": 0, "id": 1, "slug": 1, "h1": 1, "title": 1,
         "kind": 1, "intro": 1, "tags": 1},
    ).to_list(2000)

    logger.info(f"[ilinks] site={site_id[:8]} products={len(products)} "
                f"blogs={len(blogs)} landings={len(landings)}")

    # Tokenize all
    p_tokens: Dict[str, set] = {}
    p_meta: Dict[str, Dict[str, str]] = {}
    for p in products:
        tx = " ".join([
            _pick_lang_str(p.get("name"), lang),
            _pick_lang_str(p.get("tagline"), lang),
            _pick_lang_str(p.get("aeo_snippet"), lang),
            _pick_lang_str(p.get("description"), lang),
            _flat_text(p, ["usps", "categories"]) or "",
            p.get("category") or "",
        ])
        toks = set(_tokenize(tx))
        if toks:
            pid = p["id"]
            p_tokens[pid] = toks
            p_meta[pid] = {
                "id": pid,
                "slug": p.get("slug") or "",
                "title": _pick_lang_str(p.get("name"), lang)[:140],
            }

    b_tokens: Dict[str, set] = {}
    b_meta: Dict[str, Dict[str, str]] = {}
    for b in blogs:
        tx = " ".join([
            _pick_lang_str(b.get("title"), lang),
            _pick_lang_str(b.get("intro"), lang),
            _pick_lang_str(b.get("content"), lang)[:5000],
            _flat_text(b, ["h2_outline", "tags"]) or "",
        ])
        toks = set(_tokenize(tx))
        if toks:
            bid = b["id"]
            b_tokens[bid] = toks
            b_meta[bid] = {
                "id": bid,
                "slug": b.get("slug") or "",
                "title": _pick_lang_str(b.get("title"), lang)[:140],
            }

    l_tokens: Dict[str, set] = {}
    l_meta: Dict[str, Dict[str, str]] = {}
    for ld in landings:
        tx = " ".join([
            _pick_lang_str(ld.get("h1"), lang),
            _pick_lang_str(ld.get("title"), lang),
            _pick_lang_str(ld.get("intro"), lang),
            _flat_text(ld, ["tags"]) or "",
        ])
        toks = set(_tokenize(tx))
        if toks:
            lid = ld["id"]
            l_tokens[lid] = toks
            l_meta[lid] = {
                "id": lid,
                "slug": ld.get("slug") or "",
                "title": _pick_lang_str(ld.get("h1") or ld.get("title"), lang)[:140],
                "kind": ld.get("kind") or "longtail",
            }

    # Compute Product → Blog (top 5) and Product → Landing (top 3)
    products_updated = 0
    for pid, ptoks in p_tokens.items():
        # Top 5 blog
        blog_scored = [
            (bid, _jaccard(ptoks, btoks))
            for bid, btoks in b_tokens.items()
        ]
        blog_scored.sort(key=lambda x: x[1], reverse=True)
        related_blog = [
            {**b_meta[bid], "score": round(score, 3)}
            for bid, score in blog_scored[:5] if score > 0.02
        ]

        # Top 3 landing
        landing_scored = [
            (lid, _jaccard(ptoks, ltoks))
            for lid, ltoks in l_tokens.items()
        ]
        landing_scored.sort(key=lambda x: x[1], reverse=True)
        related_landings = [
            {**l_meta[lid], "score": round(score, 3)}
            for lid, score in landing_scored[:3] if score > 0.02
        ]

        if related_blog or related_landings:
            await db.products.update_one(
                {"id": pid},
                {"$set": {
                    "related_blog_posts": related_blog,
                    "related_landings": related_landings,
                }},
            )
            products_updated += 1

    # Compute Blog → Product (top 3) and Blog → Blog (top 3)
    blogs_updated = 0
    for bid, btoks in b_tokens.items():
        # Top 3 product
        prod_scored = [
            (pid, _jaccard(btoks, ptoks))
            for pid, ptoks in p_tokens.items()
        ]
        prod_scored.sort(key=lambda x: x[1], reverse=True)
        related_products = [
            {**p_meta[pid], "score": round(score, 3)}
            for pid, score in prod_scored[:3] if score > 0.02
        ]
        # Top 3 blog (excl. self)
        peer_scored = [
            (other_bid, _jaccard(btoks, otoks))
            for other_bid, otoks in b_tokens.items() if other_bid != bid
        ]
        peer_scored.sort(key=lambda x: x[1], reverse=True)
        related_blog_peers = [
            {**b_meta[other_bid], "score": round(score, 3)}
            for other_bid, score in peer_scored[:3] if score > 0.02
        ]

        if related_products or related_blog_peers:
            await db.blog_posts.update_one(
                {"id": bid},
                {"$set": {
                    "related_products": related_products,
                    "related_blog_posts": related_blog_peers,
                }},
            )
            blogs_updated += 1

    return {
        "ok": True,
        "site_id": site_id,
        "products_indexed": len(p_tokens),
        "blogs_indexed": len(b_tokens),
        "landings_indexed": len(l_tokens),
        "products_updated": products_updated,
        "blogs_updated": blogs_updated,
    }
