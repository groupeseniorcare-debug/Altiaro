"""OVH domain integration (Sprint 24).

Flow Concepteur :
1. Vérifier la disponibilité d'un nom de domaine + voir le prix (affiché avec markup plateforme)
2. Acheter en 1 clic via Mollie (prix plateforme = prix OVH + markup fixe)
3. Backend utilise l'API OVH pour acheter sur ton compte OVH + configure DNS
4. Domaine automatiquement lié au site du Concepteur (CNAME/A → notre infra)

Flow Admin :
- Voir la liste de tous les domaines achetés + renouveler + transférer

Prix (markup plateforme, configurable via PLATFORM_DOMAIN_MARKUP_EUR env) :
- Prix final = prix OVH TTC + markup (par défaut 10€/an)
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Optional

import ovh
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from deps import db, get_current_user, _check_site_access

logger = logging.getLogger("conceptfactory.domains")
router = APIRouter()

OVH_ENDPOINT = os.environ.get("OVH_ENDPOINT", "ovh-eu")
OVH_APP_KEY = os.environ.get("OVH_APP_KEY", "")
OVH_APP_SECRET = os.environ.get("OVH_APP_SECRET", "")
OVH_CONSUMER_KEY = os.environ.get("OVH_CONSUMER_KEY", "")
MARKUP_EUR = float(os.environ.get("PLATFORM_DOMAIN_MARKUP_EUR", "10"))
PLATFORM_IP = os.environ.get("PLATFORM_SITE_IP", "")

# Supported TLDs we expose to Concepteurs (we hide risky / expensive ones)
ALLOWED_TLDS = {".fr", ".com", ".net", ".shop", ".store", ".eu", ".be", ".de",
                ".it", ".es", ".nl", ".co", ".io", ".boutique"}


def _require_config():
    if not (OVH_APP_KEY and OVH_APP_SECRET and OVH_CONSUMER_KEY):
        raise HTTPException(503, "OVH non configuré côté serveur.")


def _client() -> ovh.Client:
    _require_config()
    return ovh.Client(
        endpoint=OVH_ENDPOINT,
        application_key=OVH_APP_KEY,
        application_secret=OVH_APP_SECRET,
        consumer_key=OVH_CONSUMER_KEY,
    )


def _normalise_domain(name: str) -> str:
    return (name or "").strip().lower().replace("https://", "").replace("http://", "").rstrip("/")


def _tld_of(domain: str) -> str:
    parts = domain.split(".")
    if len(parts) < 2:
        return ""
    return "." + parts[-1]


# ============== AVAILABILITY + PRICE ============== #
class CheckInput(BaseModel):
    domain: str


@router.post("/domains/check")
async def check_domain(data: CheckInput, user: dict = Depends(get_current_user)):
    """Vérifie si un domaine est disponible + retourne le prix plateforme."""
    domain = _normalise_domain(data.domain)
    if "." not in domain:
        raise HTTPException(400, "Renseigne un domaine complet (ex: maboutique.fr)")
    tld = _tld_of(domain)
    if tld not in ALLOWED_TLDS:
        raise HTTPException(400, f"Extension non supportée. Valides : {sorted(ALLOWED_TLDS)}")

    client = _client()
    import asyncio as _aio
    try:
        # Step 1: create a cart (mandatory to get a quote)
        cart = await _aio.to_thread(
            client.post, "/order/cart",
            ovhSubsidiary="FR", description="cf-check-domain",
        )
        cart_id = cart["cartId"]
        # Step 2: add the domain to see if it's available + at what price
        items = await _aio.to_thread(
            client.post, f"/order/cart/{cart_id}/domain",
            domain=domain,
        )
        item = items if isinstance(items, dict) else (items[0] if items else {})
        # prices
        ovh_price_ttc = 0.0
        for p in item.get("prices", []):
            if p.get("label") == "TOTAL":
                ovh_price_ttc = float(p.get("price", {}).get("value") or 0)
                break
        platform_price = round(ovh_price_ttc + MARKUP_EUR, 2) if ovh_price_ttc else None
        # Cleanup the cart (we'll recreate at purchase)
        try:
            await _aio.to_thread(client.delete, f"/order/cart/{cart_id}")
        except Exception:
            pass
        return {
            "domain": domain,
            "tld": tld,
            "available": bool(ovh_price_ttc > 0),
            "ovh_price_ttc_eur": ovh_price_ttc,
            "platform_price_eur": platform_price,
            "markup_eur": MARKUP_EUR,
            "currency": "EUR",
        }
    except ovh.exceptions.APIError as e:
        logger.warning(f"OVH check domain failed: {e}")
        raise HTTPException(502, f"OVH API : {str(e)[:200]}")
    except Exception as e:
        logger.exception("check_domain failed")
        raise HTTPException(500, str(e)[:200])


# ============== PURCHASE ============== #
class PurchaseInput(BaseModel):
    domain: str
    site_id: str


@router.post("/domains/purchase")
async def purchase_domain(data: PurchaseInput,
                          user: dict = Depends(get_current_user)):
    """Achète un domaine via OVH et l'attache au site.

    ⚠️ Cet endpoint déclenche un VRAI paiement depuis le moyen de paiement
    enregistré sur ton compte OVH (Admin). Pour l'instant nous facturons
    UNIQUEMENT l'Admin côté OVH. Le markup de 10€ sera facturé au Concepteur
    séparément (à brancher sur Mollie dans un sprint suivant).
    """
    await _check_site_access(data.site_id, user)
    domain = _normalise_domain(data.domain)
    tld = _tld_of(domain)
    if tld not in ALLOWED_TLDS:
        raise HTTPException(400, f"Extension non supportée : {tld}")

    # Idempotency: refuse if domain already purchased
    existing = await db.domains.find_one({"domain": domain}, {"_id": 0})
    if existing and existing.get("status") in ("purchased", "active"):
        raise HTTPException(400, "Ce domaine est déjà acheté.")

    client = _client()
    import asyncio as _aio
    try:
        # 1. cart
        cart = await _aio.to_thread(
            client.post, "/order/cart",
            ovhSubsidiary="FR",
            description=f"cf-site-{data.site_id[:8]}-{domain}",
        )
        cart_id = cart["cartId"]
        # 2. assign cart to customer (the OVH account owning the API key)
        await _aio.to_thread(client.post, f"/order/cart/{cart_id}/assign")
        # 3. add domain
        items = await _aio.to_thread(
            client.post, f"/order/cart/{cart_id}/domain",
            domain=domain,
        )
        item = items if isinstance(items, dict) else (items[0] if items else {})
        item_id = item.get("itemId")
        if not item_id:
            raise HTTPException(502, "OVH n'a pas retourné d'itemId.")
        # 4. checkout
        checkout = await _aio.to_thread(
            client.post, f"/order/cart/{cart_id}/checkout",
            autoPayWithPreferredPaymentMethod=True,
            waiveRetractationPeriod=True,
        )
        order_id = checkout.get("orderId")
        # 5. persist in our DB (domain = attached to site)
        doc = {
            "id": f"dom-{domain.replace('.', '-')}-{data.site_id[:8]}",
            "domain": domain,
            "tld": tld,
            "site_id": data.site_id,
            "purchased_by": user.get("id"),
            "purchased_at": datetime.now(timezone.utc).isoformat(),
            "ovh_cart_id": cart_id,
            "ovh_order_id": order_id,
            "ovh_item_id": item_id,
            "ovh_price_ttc_eur": float((item.get("prices", [{}])[-1].get("price") or {}).get("value") or 0),
            "platform_price_eur": None,  # billing Mollie : à brancher
            "status": "purchased",  # purchased → dns_pending → active
        }
        await db.domains.insert_one(dict(doc))
        # 6. attach domain to site (it will be fully active once DNS is configured)
        await db.sites.update_one(
            {"id": data.site_id},
            {"$set": {"domain": domain, "domain_status": "purchased",
                      "updated_at": datetime.now(timezone.utc).isoformat()}},
        )
        doc.pop("_id", None)
        return {"ok": True, "domain_record": doc, "next_step": "Configure DNS via /domains/configure-dns"}
    except ovh.exceptions.APIError as e:
        logger.exception("OVH purchase failed")
        raise HTTPException(502, f"OVH API : {str(e)[:300]}")


# ============== DNS CONFIG ============== #
@router.post("/domains/{domain}/configure-dns")
async def configure_dns(domain: str, user: dict = Depends(get_current_user)):
    """Configure la zone DNS pour pointer le domaine vers notre plateforme.

    Ajoute :
    - A record @ → PLATFORM_SITE_IP
    - CNAME www → @

    Requiert que le domaine soit dans l'état "purchased" (la zone OVH met
    en général 5-15 min à être créée après achat).
    """
    domain = _normalise_domain(domain)
    record = await db.domains.find_one({"domain": domain}, {"_id": 0})
    if not record:
        raise HTTPException(404, "Domaine inconnu.")
    if user.get("role") != "admin":
        if record.get("site_id"):
            await _check_site_access(record["site_id"], user)
    if not PLATFORM_IP:
        raise HTTPException(503, "PLATFORM_SITE_IP non configurée côté serveur.")

    client = _client()
    import asyncio as _aio
    try:
        # A record @ → PLATFORM_IP
        await _aio.to_thread(
            client.post, f"/domain/zone/{domain}/record",
            fieldType="A", subDomain="", target=PLATFORM_IP, ttl=300,
        )
        # CNAME www → @
        try:
            await _aio.to_thread(
                client.post, f"/domain/zone/{domain}/record",
                fieldType="CNAME", subDomain="www", target=f"{domain}.", ttl=300,
            )
        except Exception as e:
            logger.warning(f"CNAME www failed (might already exist): {e}")
        # Refresh
        await _aio.to_thread(client.post, f"/domain/zone/{domain}/refresh")
        await db.domains.update_one(
            {"domain": domain},
            {"$set": {"status": "dns_configured",
                      "dns_configured_at": datetime.now(timezone.utc).isoformat()}},
        )
        await db.sites.update_one(
            {"domain": domain},
            {"$set": {"domain_status": "active",
                      "updated_at": datetime.now(timezone.utc).isoformat()}},
        )
        return {"ok": True, "domain": domain, "platform_ip": PLATFORM_IP}
    except ovh.exceptions.ResourceNotFoundError:
        raise HTTPException(409, "La zone DNS n'est pas encore créée. Réessaye dans 10 min.")
    except ovh.exceptions.APIError as e:
        logger.exception("DNS config failed")
        raise HTTPException(502, f"OVH API : {str(e)[:300]}")


# ============== LIST / MANAGE ============== #
@router.get("/domains")
async def list_my_domains(user: dict = Depends(get_current_user)):
    q = {} if user.get("role") == "admin" else {"purchased_by": user.get("id")}
    cursor = db.domains.find(q, {"_id": 0}).sort("purchased_at", -1).limit(200)
    return {"domains": await cursor.to_list(200)}


@router.get("/domains/{domain}/dns")
async def get_dns_zone(domain: str, user: dict = Depends(get_current_user)):
    domain = _normalise_domain(domain)
    record = await db.domains.find_one({"domain": domain}, {"_id": 0})
    if not record:
        raise HTTPException(404, "Domaine inconnu.")
    if user.get("role") != "admin" and record.get("site_id"):
        await _check_site_access(record["site_id"], user)
    client = _client()
    import asyncio as _aio
    try:
        ids = await _aio.to_thread(client.get, f"/domain/zone/{domain}/record")
        records = []
        for rid in ids[:50]:
            try:
                r = await _aio.to_thread(client.get, f"/domain/zone/{domain}/record/{rid}")
                records.append(r)
            except Exception:
                pass
        return {"domain": domain, "records": records}
    except ovh.exceptions.APIError as e:
        raise HTTPException(502, f"OVH API : {str(e)[:200]}")


@router.get("/domains/config-status")
async def config_status(user: dict = Depends(get_current_user)):
    """Indique si l'intégration OVH est fonctionnelle."""
    status = {
        "config_ready": bool(OVH_APP_KEY and OVH_APP_SECRET and OVH_CONSUMER_KEY),
        "endpoint": OVH_ENDPOINT,
        "markup_eur": MARKUP_EUR,
        "platform_ip_configured": bool(PLATFORM_IP and PLATFORM_IP != "0.0.0.0"),
    }
    # Probe auth
    if status["config_ready"]:
        try:
            client = _client()
            import asyncio as _aio
            me = await _aio.to_thread(client.get, "/me")
            status["ovh_account"] = me.get("nichandle")
            status["auth_ok"] = True
        except Exception as e:
            status["auth_ok"] = False
            status["auth_error"] = str(e)[:200]
    return status
