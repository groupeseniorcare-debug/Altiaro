"""
Custom-domain host routing middleware.

Objectif : quand un visiteur tape `altea-home.com` (ou tout autre domaine
custom d'un site Altiaro), on veut servir le storefront correspondant
(`/shop/{site_id}/...`) automatiquement, sans que le visiteur voie le chemin
`/shop/{site_id}` dans l'URL.

Stratégie : middleware ASGI qui inspecte `Host:` header ; si l'hôte matche
un `db.sites.{*}.domain` (ou `custom_domain`), on réécrit le `scope["path"]`
en préfixant `/shop/{site_id}` AVANT que FastAPI ne dispatch.

Sont EXCLUS de la réécriture (= restent sur la plateforme Altiaro) :
  - les hôtes plateforme : `altiaro.com`, `*.altiaro.com`, `*.preview.emergentagent.com`, `localhost`
  - les chemins API : `/api/*`, `/legal/*`, `/static/*`, `/uploads/*`, `/docs/*`
  - les chemins SPA admin/cockpit : vide cadre, on laisse tout ce qui n'est
    pas explicitement un chemin storefront continuer vers la plateforme.

⚠️ Ce middleware NE fonctionne QUE si le domaine custom (via Cloudflare/DNS)
route bien le trafic HTTP jusqu'à ce pod. Si Cloudflare renvoie 522/timeout,
le middleware n'est jamais atteint.
"""
from __future__ import annotations

import logging
from typing import Optional

from deps import db

logger = logging.getLogger("altiaro.custom_domain")

# Hostnames toujours servis par la plateforme (jamais réécrits vers /shop/)
PLATFORM_HOSTS_SUFFIX = (
    "altiaro.com",
    ".preview.emergentagent.com",
    ".emergent.sh",
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
)

# Préfixes de path jamais réécrits (reste sur la plateforme quel que soit le Host)
SKIP_PATH_PREFIXES = (
    "/api/",
    "/legal/",
    "/legal",
    "/static/",
    "/uploads/",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/.well-known/",
    "/favicon",
    "/robots.txt",
    "/sitemap.xml",
    "/_redirects",
    "/_headers",
    "/shop/",  # déjà en forme canonique, ne pas toucher
)

# Sous un domaine custom (boutique concepteur), ces préfixes de path sont
# des chemins plateforme (Cockpit, Admin, auth plateforme). On ne veut PAS
# les exposer aux visiteurs du storefront : ils sont renvoyés vers la home
# boutique (`/shop/{site_id}/`).
PLATFORM_ONLY_PREFIXES = (
    "/admin",
    "/sites",          # Cockpit concepteur /sites/:id/...
    "/concepteur",
    "/signup",
    "/login",
    "/verify-email",
    "/niche",
    "/quick-scan",
    "/analyzer",
    "/opportunities",
    "/sourcing",
    "/finance",
    "/billing",
    "/orders",
    "/users",
    "/empire",
    "/domains",
    "/ads",
    "/dashboard",
    "/cockpit",
)

# Cache in-memory simple (hostname → site_id) pour éviter 1 query DB par requête.
# 5 min TTL grossier : un admin qui change le domain d'un site aura un léger
# délai avant le routing actif, acceptable.
_domain_cache: dict[str, tuple[str, float]] = {}
_CACHE_TTL_S = 300.0


async def _resolve_site_for_host(host: str) -> Optional[str]:
    """Retourne le site_id si le host custom matche un site Altiaro, sinon None."""
    import time
    host = (host or "").lower().strip()
    if not host:
        return None

    now = time.time()
    cached = _domain_cache.get(host)
    if cached and (now - cached[1]) < _CACHE_TTL_S:
        return cached[0] or None

    site = await db.sites.find_one(
        {"$or": [
            {"domain": host},
            {"custom_domain": host},
            {"domain": host.removeprefix("www.")},
            {"custom_domain": host.removeprefix("www.")},
        ]},
        {"_id": 0, "id": 1, "status": 1},
    )
    site_id = site.get("id") if site else None
    _domain_cache[host] = (site_id or "", now)
    return site_id


def _host_is_platform(host: str) -> bool:
    h = (host or "").lower().strip()
    if not h:
        return True
    h = h.split(":")[0]  # enlève le port
    for suffix in PLATFORM_HOSTS_SUFFIX:
        if h == suffix or h.endswith(suffix):
            return True
    return False


def _path_skipped(path: str) -> bool:
    p = path or "/"
    for pref in SKIP_PATH_PREFIXES:
        if p.startswith(pref):
            return True
    return False


def _is_platform_only_path(path: str) -> bool:
    """Chemins strictement plateforme (Cockpit, admin, auth) — interdits
    sous un domaine custom de boutique."""
    p = path or "/"
    for pref in PLATFORM_ONLY_PREFIXES:
        if p == pref or p.startswith(pref + "/") or p.startswith(pref + "?"):
            return True
    return False


async def custom_domain_rewrite(request, call_next):
    """Middleware ASGI : réécrit le path des requêtes arrivant sur un
    domaine custom pour qu'elles soient servies par le router storefront.

    Avant : GET altea-home.com/ → scope.path="/"
    Après : GET altea-home.com/ → scope.path="/shop/{altea_id}/"

    Sécurité : sous un domaine custom, les chemins plateforme (/admin, /sites,
    /concepteur, /login, /signup, etc.) sont redirigés vers la home boutique.
    Un visiteur de `altea-home.com` ne doit JAMAIS voir le Cockpit.
    """
    scope = request.scope
    host = request.headers.get("host", "") or ""
    path = scope.get("path", "/") or "/"

    # API et assets techniques : toujours servis tels quels (côté backend)
    if _path_skipped(path):
        return await call_next(request)

    # Host plateforme (altiaro.com, preview, localhost) : passthrough SPA
    if not host or _host_is_platform(host):
        return await call_next(request)

    # Host custom (ex: altea-home.com) → tenter la résolution
    site_id = await _resolve_site_for_host(host)
    if not site_id:
        # Host inconnu : on laisse passer (le front SPA servira un 404 sobre)
        return await call_next(request)

    # Garde-fou : sous un domaine boutique, les chemins plateforme sont
    # silencieusement redirigés vers la home boutique.
    if _is_platform_only_path(path):
        from starlette.responses import RedirectResponse
        logger.info(f"[custom-domain] {host}{path} → blocked (platform path), redirect /")
        return RedirectResponse(url="/", status_code=302)

    # Réécriture du path : on préfixe /shop/{site_id}
    new_path = f"/shop/{site_id}{path if path != '/' else ''}"
    scope["path"] = new_path
    scope["raw_path"] = new_path.encode("utf-8")
    try:
        logger.info(f"[custom-domain] {host}{path} → {new_path}")
    except Exception:
        pass
    return await call_next(request)
