"""
Proxy provisioning — Caddy admin API client.

Architecture cible (Phase 4 — Tâche 1) :

    Visiteur (mon-shop.fr)
        ↓ HTTPS
    Caddy proxy (VPS plateforme, dédié) — `proxy.altiaro.com`
        - Reçoit la requête, termine TLS via certificat Let's Encrypt
          (mode `on-demand TLS` ou liste explicite gérée par Altiaro)
        - Forward HTTPS → pod Emergent avec `X-Forwarded-Host: mon-shop.fr`
        ↓
    Pod Altiaro (Emergent)
        - custom_domain_middleware lit X-Forwarded-Host
        - Réécrit /  → /shop/{site_id}/
        - Sert le storefront

Pourquoi Caddy plutôt que Cloudflare for SaaS :
  - Caddy = libre, gratuit, illimité (Let's Encrypt rate limit 50 certs/sem
    par registrable domain — non pertinent puisque chaque concepteur a son
    propre registrable).
  - Caddy admin API permet d'ajouter des hosts à chaud sans reload.
  - On garde la souveraineté (pas de dépendance à un service tiers payant
    comme CF for SaaS, ~$2/mois/domaine custom au-delà de 100).

Limite identifiée :
  - Le pod Emergent termine déjà le TLS pour `altiaro.com`. Donc on ne peut
    PAS faire pointer un domaine custom directement vers le pod (Cloudflare
    Emergent renverrait une 526 / SAN mismatch). D'où la nécessité d'une
    couche Caddy intermédiaire qui termine le TLS pour les domaines custom
    AVANT le pod.

Ce module fournit :
  - `add_domain(host, target_pod_url)` : ajoute un hostname dans la config
    live de Caddy via son admin API (pas de reload, latence < 1 s).
  - `remove_domain(host)` : retire un hostname.
  - `domain_status(host)` : retourne le statut TLS (issued / pending / fail).
  - `is_proxy_configured()` : vérifie que le proxy est joignable.

Variables d'environnement attendues :
  - `PROXY_ADMIN_URL`    : URL admin Caddy (default `http://proxy.altiaro.com:2019`)
  - `PROXY_ADMIN_TOKEN`  : token d'auth (recommandé en prod, header `Authorization: Bearer`)
  - `PROXY_TARGET_POD`   : URL backend du pod Emergent vers lequel forwarder
                           (ex: `https://altiaro-pod.emergentagent.com`)
  - `PROXY_FALLBACK_MODE`: `cloudflare-saas` | `manual` (utilisé par
                           `add_domain` si Caddy admin indisponible)
"""
from __future__ import annotations

import logging
import os
from typing import Any, Optional

import httpx

logger = logging.getLogger("altiaro.proxy_provisioning")


PROXY_ADMIN_URL = os.environ.get("PROXY_ADMIN_URL", "").rstrip("/")
PROXY_ADMIN_TOKEN = os.environ.get("PROXY_ADMIN_TOKEN", "").strip()
PROXY_TARGET_POD = os.environ.get(
    "PROXY_TARGET_POD",
    "https://altiaro-pod.emergentagent.com",
).rstrip("/")
PROXY_FALLBACK_MODE = os.environ.get("PROXY_FALLBACK_MODE", "manual").strip()

# ID du serveur Caddy à viser (généralement "srv0"). Configurable au cas où.
CADDY_SERVER_ID = os.environ.get("PROXY_CADDY_SERVER_ID", "srv0")


def is_proxy_configured() -> bool:
    return bool(PROXY_ADMIN_URL)


def _admin_headers() -> dict:
    h = {"Content-Type": "application/json"}
    if PROXY_ADMIN_TOKEN:
        h["Authorization"] = f"Bearer {PROXY_ADMIN_TOKEN}"
    return h


def _route_id_for_host(host: str) -> str:
    return f"altiaro_route_{host.replace('.', '_')}"


def _build_route_payload(host: str, target_pod_url: Optional[str] = None) -> dict:
    """Construit la définition Caddy d'une route reverse-proxy pour un host.

    Hôte ↔ `host_match` ; reverse-proxy vers le pod Emergent avec préservation
    du Host original via `X-Forwarded-Host`. Caddy gère le TLS automatiquement
    (Let's Encrypt) tant que le DNS pointe sur le proxy.
    """
    target = (target_pod_url or PROXY_TARGET_POD).rstrip("/")
    # On strip le préfixe scheme pour upstream
    upstream = target.replace("https://", "").replace("http://", "")
    return {
        "@id": _route_id_for_host(host),
        "match": [{"host": [host, f"www.{host}"]}],
        "handle": [
            {
                "handler": "reverse_proxy",
                "upstreams": [{"dial": upstream + ":443"}],
                "transport": {
                    "protocol": "http",
                    "tls": {},
                },
                "headers": {
                    "request": {
                        "set": {
                            "X-Forwarded-Host": ["{http.request.host}"],
                            "X-Forwarded-Proto": ["https"],
                            "X-Real-IP": ["{http.request.remote.host}"],
                            "Host": [upstream],
                        }
                    }
                },
            }
        ],
        "terminal": True,
    }


async def add_domain(host: str, target_pod_url: Optional[str] = None) -> dict:
    """Ajoute (ou met à jour) une route Caddy pour `host` ET `www.host`.

    Idempotent : si la route existe déjà avec le même `@id`, elle est PUT-replace.

    Returns:
        {
          "ok": bool,
          "host": str,
          "tls_status": "pending" | "issued" | "unknown",
          "fallback": str | None,
        }
    """
    host = (host or "").strip().lower()
    if not host:
        return {"ok": False, "host": "", "error": "empty host"}
    if not is_proxy_configured():
        logger.warning(
            f"[proxy] PROXY_ADMIN_URL non configuré → impossible d'ajouter "
            f"{host}. Fallback={PROXY_FALLBACK_MODE}"
        )
        return {
            "ok": False,
            "host": host,
            "error": "proxy_admin_url_missing",
            "fallback": PROXY_FALLBACK_MODE,
        }

    payload = _build_route_payload(host, target_pod_url)
    route_id = _route_id_for_host(host)
    base = PROXY_ADMIN_URL
    headers = _admin_headers()

    # Stratégie Caddy admin :
    #   1) PUT /id/{route_id} pour replace si existe déjà
    #   2) Sinon POST sur la liste de routes du serveur srv0
    async with httpx.AsyncClient(timeout=10.0) as cli:
        try:
            r = await cli.put(f"{base}/id/{route_id}", json=payload, headers=headers)
            if r.status_code in (200, 201, 204):
                logger.info(f"[proxy] {host} route updated (PUT) status={r.status_code}")
                return {"ok": True, "host": host, "tls_status": "pending", "method": "put"}
            # Si la route n'existe pas encore (404), POST sur la liste
            if r.status_code == 404:
                routes_url = (
                    f"{base}/config/apps/http/servers/{CADDY_SERVER_ID}/routes"
                )
                r2 = await cli.post(routes_url, json=payload, headers=headers)
                if r2.status_code in (200, 201, 204):
                    logger.info(f"[proxy] {host} route created (POST) status={r2.status_code}")
                    return {"ok": True, "host": host, "tls_status": "pending", "method": "post"}
                logger.warning(
                    f"[proxy] {host} POST failed status={r2.status_code} body={r2.text[:200]}"
                )
                return {
                    "ok": False,
                    "host": host,
                    "error": f"caddy_post_failed_{r2.status_code}",
                    "detail": r2.text[:200],
                }
            logger.warning(
                f"[proxy] {host} PUT failed status={r.status_code} body={r.text[:200]}"
            )
            return {
                "ok": False,
                "host": host,
                "error": f"caddy_put_failed_{r.status_code}",
                "detail": r.text[:200],
            }
        except (httpx.HTTPError, httpx.ConnectError) as e:
            logger.error(f"[proxy] {host} caddy admin unreachable: {e}")
            return {
                "ok": False,
                "host": host,
                "error": "caddy_admin_unreachable",
                "detail": str(e)[:200],
                "fallback": PROXY_FALLBACK_MODE,
            }


async def remove_domain(host: str) -> dict:
    host = (host or "").strip().lower()
    if not host or not is_proxy_configured():
        return {"ok": False, "host": host, "error": "not_configured"}
    route_id = _route_id_for_host(host)
    async with httpx.AsyncClient(timeout=5.0) as cli:
        try:
            r = await cli.delete(
                f"{PROXY_ADMIN_URL}/id/{route_id}",
                headers=_admin_headers(),
            )
            if r.status_code in (200, 204, 404):  # 404 = déjà absent, OK
                return {"ok": True, "host": host}
            return {"ok": False, "host": host, "error": f"caddy_{r.status_code}"}
        except httpx.HTTPError as e:
            return {"ok": False, "host": host, "error": str(e)[:200]}


async def domain_status(host: str) -> dict:
    """Récupère le statut SSL d'un host depuis Caddy.

    Caddy expose `/pki/ca/local/certificates` et `/load` mais pas d'endpoint
    direct "is cert issued for X". On infère via la config live + un HEAD sur
    le host (si 200 → cert OK, si 526 → pending).
    """
    host = (host or "").strip().lower()
    if not host:
        return {"ok": False, "tls_status": "unknown"}
    if not is_proxy_configured():
        return {"ok": False, "tls_status": "unknown", "error": "not_configured"}
    async with httpx.AsyncClient(timeout=5.0, verify=True) as cli:
        try:
            r = await cli.get(f"https://{host}/api/health", follow_redirects=False)
            if r.status_code == 200:
                return {"ok": True, "tls_status": "issued", "host": host}
            return {"ok": True, "tls_status": "issued_but_5xx", "host": host, "code": r.status_code}
        except httpx.ConnectError as e:
            msg = str(e).lower()
            if "ssl" in msg or "tls" in msg or "certificate" in msg:
                return {"ok": True, "tls_status": "pending", "host": host, "detail": str(e)[:120]}
            return {"ok": False, "tls_status": "unreachable", "host": host, "detail": str(e)[:120]}
        except httpx.HTTPError as e:
            return {"ok": False, "tls_status": "error", "detail": str(e)[:120]}
