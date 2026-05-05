"""UA-routing edge-level middleware (Phase 1 — 2026-05-04).

Objectif : quand un bot SEO ou un LLM crawler tape un domaine custom Altiaro
(ex `altea-home.com`) sur un path indexable, on lui sert directement du HTML
prerenderé au lieu du SPA React (qui serait illisible sans rendu JS).

Stratégie : middleware ASGI monté EN AMONT de `custom_domain_rewrite`. Il
détecte :
    1. Un User-Agent reconnu comme bot (Googlebot, GPTBot, ClaudeBot, etc.)
    2. Un Host custom (résolu via le même cache que custom_domain_middleware)
    3. Un path indexable (/, /about, /products/*, /buyer-guides/*, /glossary/*,
       /comparisons/*, /top-lists/*, /longtail/*, /blog/*, /collections/*)

Si tous les critères sont réunis → on appelle directement la fonction
`prerender_html(site, path)` et on retourne `HTMLResponse` avec headers
`X-Prerender: 1` + `Cache-Control: public, max-age=300`.

Sinon → on laisse passer la requête vers le middleware suivant (custom_domain
rewrite, puis SPA React).

⚠️ ZÉRO impact sur les utilisateurs humains : un visiteur Chrome/Firefox/Safari
n'a JAMAIS son User-Agent matché par la regex bots, donc il continue à
recevoir le SPA exactement comme avant.
"""
from __future__ import annotations

import logging
import re

from starlette.responses import HTMLResponse, Response

from custom_domain_middleware import _resolve_site_for_host, _host_is_platform
from deps import db
from routes.prerender import prerender_html, is_indexable_path

logger = logging.getLogger("altiaro.prerender_routing")

# Liste exhaustive des bots SEO + LLM crawlers supportés.
# Regex compilée case-insensitive — match si le User-Agent CONTIENT l'un des
# tokens ci-dessous (les bots respectent leur "user-agent string" canonique).
_BOT_TOKENS = (
    # Search engines
    "Googlebot", "Bingbot", "DuckDuckBot", "YandexBot", "Slurp",
    "Baiduspider",
    # Social / sharing previewers
    "FacebookExternalHit", "Twitterbot", "LinkedInBot",
    "DiscordBot", "Slackbot", "TelegramBot", "WhatsApp",
    # LLM / AI crawlers
    "GPTBot", "ChatGPT-User", "OAI-SearchBot",
    "ClaudeBot", "Claude-Web", "anthropic-ai",
    "PerplexityBot", "CCBot", "Google-Extended",
    "Applebot", "YouBot", "AmazonBot", "Bytespider",
)

_BOT_RE = re.compile(
    "(" + "|".join(re.escape(t) for t in _BOT_TOKENS) + ")",
    re.IGNORECASE,
)

# Path pattern pour URLs plateforme `/shop/{site_id}/{rest}` (preview Emergent
# ou tout host plateforme). Regex stricte : site_id doit être un UUID v4 (36
# chars : 8-4-4-4-12 hex). Ça évite de matcher accidentellement /shop/cart ou
# autres paths plateforme.
_SHOP_PATH_RE = re.compile(
    r"^/shop/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})(?:/(.*))?$",
    re.IGNORECASE,
)


def _is_bot_ua(user_agent: str) -> bool:
    """True si le User-Agent matche un bot SEO ou LLM crawler connu."""
    if not user_agent:
        return False
    return _BOT_RE.search(user_agent) is not None


async def prerender_routing(request, call_next):
    """Middleware ASGI : intercepte les requêtes bot vers domaines custom
    OU vers URLs plateforme `/shop/{site_id}/...` (preview Emergent).

    Ordre de check (rapide → cher) :
      1. Méthode GET (les bots ne POST jamais sur des pages indexables).
      2. User-Agent matche `_BOT_RE`.
      3. Path est indexable OU est une URL `/shop/{site_id}/{rest}`.
      4a. (custom domain) Host n'est pas un host plateforme + résout vers site.
      4b. (preview/platform) Path commence par `/shop/{site_id}/...` →
          extrait `site_id` du path et réécrit le path en `/{rest}`.
      5. `prerender_html(site, path)` retourne un HTML.

    Si l'un des checks échoue → passthrough vers `call_next` (= comportement
    normal : custom_domain_rewrite puis SPA React).
    """
    scope = request.scope
    headers = request.headers

    # 1) Méthode (les bots font GET ; on ignore POST/PUT/etc.)
    if scope.get("method") != "GET":
        return await call_next(request)

    # 2) User-Agent
    ua = (headers.get("user-agent") or "").strip()
    if not _is_bot_ua(ua):
        return await call_next(request)

    # 3-4) Routing : 2 modes possibles
    path = scope.get("path", "/") or "/"

    # Mode A : URL plateforme `/shop/{site_id}/{rest}` (preview ou custom path)
    site = None
    target_path = path
    shop_match = _SHOP_PATH_RE.match(path)
    if shop_match:
        site_id_from_path = shop_match.group(1)
        rest = shop_match.group(2) or ""
        target_path = "/" + rest if rest else "/"
        # Si pas indexable on laisse passer
        if not is_indexable_path(target_path):
            return await call_next(request)
        site = await db.sites.find_one({"id": site_id_from_path}, {"_id": 0})
        if not site:
            return await call_next(request)
    else:
        # Mode B : custom domain (host résout vers un site Altiaro)
        if not is_indexable_path(path):
            return await call_next(request)
        # Priorité 1 : Apx-Incoming-Host (Approximated, source de vérité)
        # Priorité 2 : X-Forwarded-Host / X-Original-Host (chaîne de proxies)
        # Priorité 3 : Host header (souvent réécrit par l'ingress Emergent)
        forwarded = (
            headers.get("apx-incoming-host")
            or headers.get("x-forwarded-host")
            or headers.get("x-original-host")
            or ""
        ).strip().lower()
        raw_host = (headers.get("host") or "").strip().lower()
        host = (forwarded or raw_host).split(":")[0]
        if not host or _host_is_platform(host):
            return await call_next(request)
        site_id = await _resolve_site_for_host(host)
        if not site_id:
            return await call_next(request)
        site = await db.sites.find_one({"id": site_id}, {"_id": 0})
        if not site:
            return await call_next(request)

    # 5) Génération HTML prerender
    try:
        body = await prerender_html(site, target_path)
    except Exception as e:
        host_log = (headers.get("host") or "").strip().lower()
        logger.warning(f"[prerender-routing] {host_log}{path} → {target_path} failed: {str(e)[:200]}")
        return await call_next(request)

    if not body:
        # Path non supporté pour ce site (ex slug introuvable) → fallback SPA.
        return await call_next(request)

    host_log = (headers.get("host") or "").strip().lower()
    logger.info(f"[prerender-routing] bot={ua[:40]!r} host={host_log} path={path} target={target_path} → SSR served")
    return HTMLResponse(
        content=body,
        headers={
            "X-Prerender": "1",
            "X-Prerender-Source": "altiaro-edge",
            "X-Prerender-Target-Path": target_path,
            "Cache-Control": "public, max-age=300, s-maxage=300",
            "Vary": "User-Agent",
        },
    )
