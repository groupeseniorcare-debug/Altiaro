"""Pinterest publication service — real implementation.

Le PAT (`PINTEREST_APP_SECRET` préfixé `pina_`) sert directement comme
Bearer token sur l'API v5. Pas de flow OAuth utilisateur à gérer.

Variables env :
    PINTEREST_APP_ID      : id app Pinterest (info, pas utilisé pour signer)
    PINTEREST_APP_SECRET  : Personal Access Token Pinterest (Bearer)

Endpoints utilisés :
    GET  /v5/user_account
    GET  /v5/boards
    POST /v5/boards
    POST /v5/pins
    DELETE /v5/boards/{board_id}

Persistance :
    site.marketing.pinterest = {
        enabled, board_id, board_url, board_name,
        pins_published, last_pin_at, last_error,
    }
    db.pinterest_pins = collection des pins publiés.
"""
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

logger = logging.getLogger("altiaro.pinterest")

API_BASE = "https://api.pinterest.com/v5"
_TIMEOUT = httpx.Timeout(20.0, connect=10.0)


def _token() -> Optional[str]:
    return os.environ.get("PINTEREST_APP_SECRET") or None


def _headers() -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {_token()}",
        "Content-Type": "application/json",
        "User-Agent": "Altiaro-Pinterest/1.0",
    }


async def _req(method: str, path: str, **kw) -> Dict[str, Any]:
    if not _token():
        return {"ok": False, "reason": "missing_token"}
    url = f"{API_BASE}{path}"
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as cli:
            r = await cli.request(method, url, headers=_headers(), **kw)
        if r.status_code >= 400:
            return {"ok": False, "status": r.status_code, "error": r.text[:400]}
        return {"ok": True, "status": r.status_code,
                "data": r.json() if r.content else {}}
    except Exception as e:
        return {"ok": False, "reason": "http_error", "error": str(e)[:300]}


async def is_configured() -> bool:
    if not _token():
        return False
    res = await _req("GET", "/user_account")
    return bool(res.get("ok"))


async def get_user_account() -> Dict[str, Any]:
    return await _req("GET", "/user_account")


def _name(v: Any, lang: str = "fr") -> str:
    if isinstance(v, dict):
        return v.get(lang) or v.get("fr") or v.get("en") or next(iter(v.values()), "")
    return str(v or "")


async def _generate_pin_description(product: Dict[str, Any], site: Dict[str, Any]) -> Dict[str, Any]:
    """Renvoie {description (max 500c), hashtags (5-7)}.

    Préfère réutiliser `aeo_snippet` (40-60 mots déjà premium) + 5-7 hashtags
    générés via Claude (Haiku, court, pas cher).
    """
    name = _name(product.get("name"))
    aeo = product.get("aeo_snippet") or _name(
        (product.get("narrative") or {}).get("subheadline")
    ) or _name(product.get("description"))[:200]
    niche = site.get("niche") or ""
    brand = (site.get("design") or {}).get("brand", {}).get("name") or site.get("name") or ""
    try:
        data = await safe_claude_json(
            "Tu generes des hashtags Pinterest specifiques et premium, sans diese, "
            "JSON strict en sortie. Tu reponds en francais.",
            f"Produit : {name}\nMarque : {brand}\nNiche : {niche}\n\n"
            f"Genere 6 hashtags Pinterest courts (1-3 mots, sans diese) "
            f"qui maximisent la decouvrabilite niche premium. "
            f"JSON : {{\"tags\": [\"...\"]}}",
            quality_tier="standard",
            session_id=f"pin-{(product.get('id') or '')[:8]}",
            timeout=40, request_id="pin-tags",
        )
        tags = [str(t).strip().replace("#", "") for t in (data.get("tags") or []) if t][:6]
    except Exception:
        tags = [niche, brand, "premium", "qualite"]
        tags = [t for t in tags if t]
    desc = aeo
    if tags:
        desc = (desc + "\n\n" + " ".join(f"#{t.replace(' ', '')}" for t in tags))[:500]
    return {"description": desc, "hashtags": tags}


async def create_board_for_site(site_id: str) -> Dict[str, Any]:
    """Crée un board Pinterest pour ce site. Idempotent.

    Si `site.marketing.pinterest.board_id` existe déjà → no-op.
    """
    site = await db.sites.find_one({"id": site_id}, {"_id": 0})
    if not site:
        return {"ok": False, "reason": "site_not_found"}

    pin_state = (site.get("marketing") or {}).get("pinterest") or {}
    if pin_state.get("board_id"):
        return {"ok": True, "action": "noop", "board_id": pin_state["board_id"],
                "board_url": pin_state.get("board_url")}

    brand = (site.get("design") or {}).get("brand") or {}
    brand_name = brand.get("name") or site.get("name") or "Altiaro"
    niche = site.get("niche") or ""
    board_name = f"{brand_name} — {niche.title()[:60]}"[:50]
    description = (
        ((site.get("about_rich") or {}).get("tagline")
         or f"{brand_name} : {niche}")[:500]
    )

    res = await _req("POST", "/boards", json={
        "name": board_name,
        "description": description,
        "privacy": "PUBLIC",
    })
    if not res.get("ok"):
        return res

    data = res["data"]
    board_id = data.get("id")
    user_acc = await get_user_account()
    username = (user_acc.get("data") or {}).get("username") or ""
    board_url = f"https://www.pinterest.com/{username}/{board_name.lower().replace(' ', '-').replace('--', '-')[:50]}/"

    await db.sites.update_one(
        {"id": site_id},
        {"$set": {
            "marketing.pinterest.board_id": board_id,
            "marketing.pinterest.board_name": board_name,
            "marketing.pinterest.board_url": board_url,
            "marketing.pinterest.board_created_at": datetime.now(timezone.utc).isoformat(),
        }},
    )
    return {"ok": True, "action": "created", "board_id": board_id,
            "board_url": board_url, "board_name": board_name}


def _build_image_url(image: Any, request_base: str = "") -> Optional[str]:
    """Returns the absolute HTTPS URL of an image."""
    url = image.get("url") if isinstance(image, dict) else image
    if not url:
        return None
    if url.startswith("http://") or url.startswith("https://"):
        return url
    # /api/uploads/... → backend public URL
    base = request_base or os.environ.get("PUBLIC_ORIGIN") or os.environ.get("PUBLIC_FRONTEND_URL") or ""
    if base and url.startswith("/"):
        return base.rstrip("/") + url
    return None


async def pin_product(site: Dict[str, Any], product: Dict[str, Any],
                      image_url: str, board_id: str) -> Dict[str, Any]:
    domain = site.get("custom_domain") or ""
    slug = product.get("slug") or product.get("id")
    link = f"https://{domain}/products/{slug}" if domain else None
    name = _name(product.get("name"))[:100]
    desc_data = await _generate_pin_description(product, site)

    body: Dict[str, Any] = {
        "board_id": board_id,
        "title": name,
        "description": desc_data["description"],
        "alt_text": (product.get("generated_images") or [{}])[0].get("alt_text") or name,
        "media_source": {
            "source_type": "image_url",
            "url": image_url,
        },
    }
    if link:
        body["link"] = link
    res = await _req("POST", "/pins", json=body)
    if res.get("ok"):
        pin_data = res["data"]
        await db.pinterest_pins.insert_one({
            "id": str(uuid.uuid4()),
            "site_id": site["id"],
            "product_id": product.get("id"),
            "product_slug": product.get("slug"),
            "board_id": board_id,
            "pin_id": pin_data.get("id"),
            "image_url": image_url,
            "link": link,
            "description": desc_data["description"],
            "hashtags": desc_data["hashtags"],
            "posted_at": datetime.now(timezone.utc).isoformat(),
        })
    return res


async def publish_first_batch(site_id: str, max_pins: int = 20) -> Dict[str, Any]:
    """Crée le board s'il n'existe pas + publie jusqu'à max_pins images
    depuis les produits actifs, 2 images max par produit.
    """
    site = await db.sites.find_one({"id": site_id}, {"_id": 0})
    if not site:
        return {"ok": False, "reason": "site_not_found"}
    board = await create_board_for_site(site_id)
    if not board.get("ok"):
        return {"ok": False, "step": "create_board", **board}
    board_id = board["board_id"]

    public_origin = os.environ.get("PUBLIC_ORIGIN") or os.environ.get("PUBLIC_FRONTEND_URL") or ""
    products = await db.products.find(
        {"site_id": site_id, "status": "active"},
        {"_id": 0, "id": 1, "slug": 1, "name": 1, "aeo_snippet": 1,
         "narrative": 1, "description": 1, "generated_images": 1, "images": 1},
    ).to_list(50)

    posted = 0
    failed: List[Dict[str, Any]] = []
    pin_results: List[Dict[str, Any]] = []
    for p in products:
        if posted >= max_pins:
            break
        imgs = p.get("generated_images") or []
        if not imgs:
            imgs = [{"url": u} for u in (p.get("images") or []) if isinstance(u, str)]
        # 2 images max per product to diversify the board
        for im in imgs[:2]:
            if posted >= max_pins:
                break
            url = _build_image_url(im, public_origin)
            if not url:
                continue
            res = await pin_product(site, p, url, board_id)
            if res.get("ok"):
                posted += 1
                pin_results.append({
                    "product": p.get("slug"),
                    "pin_id": (res.get("data") or {}).get("id"),
                })
            else:
                failed.append({
                    "product": p.get("slug"), "image": url,
                    "status": res.get("status"), "error": res.get("error", "")[:200],
                })
            # Pinterest rate limit ~50 req/min — petite pause
            await asyncio.sleep(1.0)

    now = datetime.now(timezone.utc).isoformat()
    await db.sites.update_one(
        {"id": site_id},
        {"$set": {
            "marketing.pinterest.enabled": True,
            "marketing.pinterest.pins_published": posted,
            "marketing.pinterest.last_pin_at": now,
            "marketing.pinterest.last_error": (failed[0].get("error") if failed else None),
        }},
    )
    return {
        "ok": True,
        "site_id": site_id,
        "board_id": board_id,
        "board_url": board.get("board_url"),
        "pins_published": posted,
        "pins_failed": len(failed),
        "failed_samples": failed[:3],
        "pin_results": pin_results,
    }


async def disable_for_site(site_id: str, *, delete_board: bool = False) -> Dict[str, Any]:
    site = await db.sites.find_one({"id": site_id}, {"_id": 0, "marketing": 1})
    if not site:
        return {"ok": False, "reason": "site_not_found"}
    pin_state = (site.get("marketing") or {}).get("pinterest") or {}
    board_id = pin_state.get("board_id")
    deleted_pins = await db.pinterest_pins.delete_many({"site_id": site_id})
    board_deleted = None
    if board_id and delete_board:
        r = await _req("DELETE", f"/boards/{board_id}")
        board_deleted = bool(r.get("ok"))
    await db.sites.update_one(
        {"id": site_id},
        {"$set": {
            "marketing.pinterest.enabled": False,
            "marketing.pinterest.disabled_at": datetime.now(timezone.utc).isoformat(),
        }, "$unset": {
            "marketing.pinterest.board_id": "",
            "marketing.pinterest.board_url": "",
            "marketing.pinterest.board_name": "",
        } if delete_board else {}},
    )
    return {"ok": True, "deleted_pins_db": deleted_pins.deleted_count, "board_deleted": board_deleted}


async def get_site_status(site_id: str) -> Dict[str, Any]:
    site = await db.sites.find_one({"id": site_id}, {"_id": 0, "marketing": 1})
    if not site:
        return {"ok": False, "reason": "site_not_found"}
    pin_state = (site.get("marketing") or {}).get("pinterest") or {}
    pins_count = await db.pinterest_pins.count_documents({"site_id": site_id})
    return {
        "ok": True,
        "site_id": site_id,
        "enabled": bool(pin_state.get("enabled")),
        "board_id": pin_state.get("board_id"),
        "board_url": pin_state.get("board_url"),
        "board_name": pin_state.get("board_name"),
        "pins_count_db": pins_count,
        "pins_published": pin_state.get("pins_published", 0),
        "last_pin_at": pin_state.get("last_pin_at"),
        "last_error": pin_state.get("last_error"),
    }


async def auto_pin_tick() -> Dict[str, Any]:
    """Cron tick : pour chaque site enabled, publie 1 pin supplémentaire (image
    non encore postée). Idéal en cron 5x/jour pour drip-feed."""
    if not _token():
        return {"ok": False, "reason": "missing_token"}
    sites = await db.sites.find(
        {"marketing.pinterest.enabled": True},
        {"_id": 0, "id": 1, "name": 1, "custom_domain": 1, "design": 1,
         "niche": 1, "marketing": 1, "about_rich": 1},
    ).to_list(200)
    public_origin = os.environ.get("PUBLIC_ORIGIN") or ""
    out: List[Dict[str, Any]] = []
    for site in sites:
        board_id = (site.get("marketing") or {}).get("pinterest", {}).get("board_id")
        if not board_id:
            continue
        already = {
            d.get("image_url")
            async for d in db.pinterest_pins.find(
                {"site_id": site["id"]}, {"_id": 0, "image_url": 1}
            )
        }
        # Pick first product image not yet pinned
        pinned_one = False
        async for p in db.products.find(
            {"site_id": site["id"], "status": "active"}, {"_id": 0}
        ):
            for im in (p.get("generated_images") or [])[:4]:
                url = _build_image_url(im, public_origin)
                if not url or url in already:
                    continue
                await pin_product(site, p, url, board_id)
                pinned_one = True
                break
            if pinned_one:
                break
        out.append({"site_id": site["id"], "pinned": pinned_one})
    return {"ok": True, "results": out}
