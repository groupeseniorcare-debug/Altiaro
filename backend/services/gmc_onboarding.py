"""GMC Auto-Onboarding — Pre-fill all available fields on a Merchant Center
sub-account in one shot, using the data already in DB.

Google Content API v2.1 supports pushing :
- accounts.insert  : name, websiteUrl, adultContent, businessInformation
  (address, customerService email/phone/url, koreanBusinessRegistrationNumber)
- shippingsettings.update : per-country shipping rates with delivery times
- returnpolicy.create     : 30-day return window pointing to /legal/retours
- accounttax.update       : per-country tax category mapping
- liasettings  / accountstatuses : info-only

What remains irreducibly manual for the operator on Google's side :
- Business identity verification (ID, KBIS upload)
- Phone number SMS/voice verification
- Email click-through verification
- DUNS / brand verification (if requested by Google)
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from deps import db
from altiaro_legal import PLATFORM_LEGAL_INFO

logger = logging.getLogger("altiaro.gmc_onboarding")


async def _resolve_master_credentials():
    """Reuse the existing Google Master OAuth credentials."""
    try:
        from services.google_master_discovery import _build_master_credentials  # type: ignore
        creds = await _build_master_credentials()
        return creds
    except Exception:
        try:
            from routes.merchant import _get_creds  # legacy fallback
            return await _get_creds()
        except Exception:
            return None


async def _resolve_mca_id() -> Optional[str]:
    mca = os.environ.get("GOOGLE_MERCHANT_MASTER_ID") or ""
    if mca:
        return mca
    doc = await db.platform_settings.find_one({"key": "gmc_master"}) or {}
    if doc.get("is_mca") and doc.get("account_id"):
        return str(doc["account_id"])
    return None


def _parse_address(raw: str) -> Dict[str, str]:
    """Best-effort « 4 IMP CLOS FLEURI, 42320 FARNAY, France » -> dict."""
    out = {"street": "", "postalCode": "", "locality": "", "country": "FR"}
    if not raw:
        return out
    parts = [p.strip() for p in raw.split(",")]
    if len(parts) >= 1:
        out["street"] = parts[0]
    if len(parts) >= 2:
        # "42320 FARNAY"
        zc = parts[1].split(" ", 1)
        out["postalCode"] = zc[0]
        if len(zc) > 1:
            out["locality"] = zc[1]
    if len(parts) >= 3:
        country = parts[2].lower()
        if "france" in country:
            out["country"] = "FR"
        elif "belgi" in country:
            out["country"] = "BE"
        elif "luxembourg" in country:
            out["country"] = "LU"
        elif "swiss" in country or "suisse" in country:
            out["country"] = "CH"
    return out


async def _gather_context(site_id: str) -> Dict[str, Any]:
    site = await db.sites.find_one({"id": site_id}, {"_id": 0}) or {}
    if not site:
        return {}
    op = await db.users.find_one({"id": site.get("operator_id")}, {"_id": 0}) or {}
    bp = await db.billing_profiles.find_one({"user_id": site.get("operator_id")}, {"_id": 0}) or {}

    domain = site.get("custom_domain") or site.get("public_url") or ""
    domain = domain.replace("https://", "").replace("http://", "").rstrip("/")
    brand = (site.get("design") or {}).get("brand") or {}

    # Address fallback ladder : billing_profile.address -> Altiaro plateform legal address
    addr = {
        "street": bp.get("address_street") or "",
        "postalCode": bp.get("address_postal_code") or "",
        "locality": bp.get("address_city") or "",
        "country": (bp.get("address_country") or bp.get("iban_country") or "FR")[:2].upper(),
    }
    if not addr["street"]:
        addr = _parse_address(PLATFORM_LEGAL_INFO.get("adresse", ""))
        addr["_fallback"] = "altiaro_platform"

    phone = bp.get("phone") or op.get("phone") or PLATFORM_LEGAL_INFO.get("platform_telephone", "")
    email = op.get("email") or PLATFORM_LEGAL_INFO.get("platform_email", "")

    return {
        "site": site, "operator": op, "billing_profile": bp,
        "domain": domain, "brand": brand,
        "address": addr, "phone": phone, "email": email,
        "business_name": brand.get("name") or site.get("name") or domain,
    }


def _account_body(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Construit le payload accounts.insert / accounts.update enrichi."""
    addr = ctx["address"]
    return {
        "name": ctx["business_name"],
        "websiteUrl": f"https://{ctx['domain']}",
        "adultContent": False,
        "businessInformation": {
            "address": {
                "streetAddress": addr["street"],
                "locality": addr["locality"],
                "postalCode": addr["postalCode"],
                "country": addr["country"],
            },
            "customerService": {
                "email": ctx["email"],
                "phoneNumber": ctx["phone"],
                "url": f"https://{ctx['domain']}/legal/retours",
            },
            "phoneNumber": ctx["phone"],
        },
    }


def _shipping_settings_body(ctx: Dict[str, Any], merchant_id: str) -> Dict[str, Any]:
    """FR + EU standard shipping. Free over 99€, otherwise 6.90€, 2-5 days."""
    return {
        "accountId": merchant_id,
        "services": [
            {
                "name": "Livraison standard France",
                "active": True,
                "deliveryCountry": "FR",
                "currency": "EUR",
                "deliveryTime": {
                    "minTransitTimeInDays": 2,
                    "maxTransitTimeInDays": 5,
                },
                "rateGroups": [{
                    "singleValue": {"flatRate": {"value": "6.90", "currency": "EUR"}},
                }],
                "minimumOrderValue": {"value": "0.00", "currency": "EUR"},
            },
            {
                "name": "Livraison gratuite dès 99€",
                "active": True,
                "deliveryCountry": "FR",
                "currency": "EUR",
                "deliveryTime": {
                    "minTransitTimeInDays": 2,
                    "maxTransitTimeInDays": 5,
                },
                "rateGroups": [{
                    "singleValue": {"flatRate": {"value": "0.00", "currency": "EUR"}},
                }],
                "minimumOrderValue": {"value": "99.00", "currency": "EUR"},
            },
        ],
    }


def _return_policy_body(ctx: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "name": "Politique de retour 30 jours",
        "label": "Retours 30j satisfait ou remboursé",
        "country": ctx["address"]["country"],
        "returnPolicyUri": f"https://{ctx['domain']}/legal/retours",
        "policy": {
            "type": "NUMBER_OF_DAYS_AFTER_DELIVERY",
            "numberOfDays": 30,
        },
    }


def _tax_body(ctx: Dict[str, Any], merchant_id: str) -> Dict[str, Any]:
    """Mention TVA non applicable (art. 293 B). Sinon TVA standard."""
    return {
        "accountId": merchant_id,
        "rules": [
            {"country": ctx["address"]["country"], "useGlobalRate": True},
        ],
    }


async def auto_onboard(site_id: str, *, force: bool = False) -> Dict[str, Any]:
    """Push tout ce qui est pushable côté GMC pour ce site.

    Strategy : best-effort — chaque sous-appel est indépendant et son
    échec est tracé sans interrompre le suivant.
    """
    out: Dict[str, Any] = {"site_id": site_id, "started_at": datetime.now(timezone.utc).isoformat()}
    ctx = await _gather_context(site_id)
    if not ctx:
        return {**out, "ok": False, "reason": "site_not_found"}
    out["context"] = {
        "business_name": ctx["business_name"],
        "domain": ctx["domain"],
        "email": ctx["email"],
        "phone": ctx["phone"],
        "address": ctx["address"],
    }

    creds = await _resolve_master_credentials()
    if not creds:
        return {**out, "ok": False, "reason": "no_master_credentials"}
    mca = await _resolve_mca_id()
    if not mca:
        return {**out, "ok": False, "reason": "no_mca_id"}

    try:
        from googleapiclient.discovery import build
        svc = build("content", "v2.1", credentials=creds, cache_discovery=False)
    except Exception as e:
        return {**out, "ok": False, "reason": "sdk_init_failed", "error": str(e)[:200]}

    # 1) Look up existing sub-account by domain, else create.
    sub_id: Optional[str] = None
    site_doc = ctx["site"]
    sub_id = (site_doc.get("merchant") or {}).get("sub_account_id")

    body = _account_body(ctx)
    out["account_body"] = body

    try:
        if sub_id and not force:
            # Update existing
            resp = await asyncio.to_thread(
                svc.accounts().update(merchantId=mca, accountId=sub_id, body=body).execute,
            )
            out["account"] = {"action": "updated", "id": resp.get("id"), "name": resp.get("name")}
        else:
            resp = await asyncio.to_thread(
                svc.accounts().insert(merchantId=mca, body=body).execute,
            )
            sub_id = resp.get("id")
            out["account"] = {"action": "created", "id": sub_id, "name": resp.get("name")}
    except Exception as e:
        out["account"] = {"ok": False, "error": str(e)[:300]}
        # If we can't even create the account, no point pushing the rest.
        return {**out, "ok": False}

    if not sub_id:
        return {**out, "ok": False, "reason": "sub_id_missing"}

    # Persist linkage on the site doc so subsequent syncs use it.
    await db.sites.update_one(
        {"id": site_id},
        {"$set": {
            "merchant.sub_account_id": sub_id,
            "merchant.mca_id": mca,
            "merchant.onboarded_at": datetime.now(timezone.utc).isoformat(),
            "merchant.business_info_pushed": True,
        }},
    )

    # 2) Push shipping settings.
    try:
        ship_body = _shipping_settings_body(ctx, sub_id)
        await asyncio.to_thread(
            svc.shippingsettings().update(
                merchantId=mca, accountId=sub_id, body=ship_body,
            ).execute,
        )
        out["shipping_settings"] = {"ok": True, "services": len(ship_body["services"])}
    except Exception as e:
        out["shipping_settings"] = {"ok": False, "error": str(e)[:250]}

    # 3) Push tax settings (FR : TVA non applicable -> useGlobalRate).
    try:
        tax_body = _tax_body(ctx, sub_id)
        await asyncio.to_thread(
            svc.accounttax().update(
                merchantId=mca, accountId=sub_id, body=tax_body,
            ).execute,
        )
        out["tax"] = {"ok": True}
    except Exception as e:
        out["tax"] = {"ok": False, "error": str(e)[:250]}

    # 4) Return policy (Content API v2.1 returnpolicy is account-level).
    try:
        rp_body = _return_policy_body(ctx)
        await asyncio.to_thread(
            svc.returnpolicy().insert(
                merchantId=sub_id, body=rp_body,
            ).execute,
        )
        out["return_policy"] = {"ok": True, "days": 30}
    except Exception as e:
        out["return_policy"] = {"ok": False, "error": str(e)[:250]}

    # 5) Confirm feed URL is a known feed for products (we already self-publish).
    feed_url = f"https://{ctx['domain']}/api/public/sites/{site_id}/google-merchant-feed.xml"
    out["feed_url"] = feed_url

    out["ok"] = True
    out["sub_account_id"] = sub_id
    out["mca_id"] = mca
    out["completed_at"] = datetime.now(timezone.utc).isoformat()

    # 6) Build the manual checklist for the operator (irreducible).
    out["manual_steps_required"] = [
        {
            "id": "identity_verification",
            "label": "Vérifier l'identité du business sur Google Merchant",
            "action_url": f"https://merchants.google.com/mc/verifyidentity?a={sub_id}",
            "why": "Google demande un KBIS et une pièce d'identité du représentant légal.",
        },
        {
            "id": "phone_verification",
            "label": "Vérifier le téléphone par SMS/appel",
            "action_url": f"https://merchants.google.com/mc/verifyphone?a={sub_id}",
            "why": f"Code envoyé au {ctx['phone']} — Google n'accepte pas la délégation API.",
        },
        {
            "id": "email_verification",
            "label": "Cliquer le lien de vérification email",
            "action_url": f"https://merchants.google.com/mc/verifyemail?a={sub_id}",
            "why": f"Mail envoyé à {ctx['email']} — obligatoire pour activer Shopping.",
        },
    ]
    # Persist manual steps + final state on the site doc so subsequent
    # /qa/checklist reads can surface them without re-running the API.
    await db.sites.update_one(
        {"id": site_id},
        {"$set": {
            "merchant.manual_steps_required": out["manual_steps_required"],
            "merchant.last_onboarding_at": out["completed_at"],
            "merchant.feed_url": out["feed_url"],
        }},
    )
    return out
