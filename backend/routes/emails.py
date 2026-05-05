"""Transactional emails via Resend (Sprint 22).

Chaque email est envoyé dans le contexte d'un site spécifique :
- Le logo + nom + couleur primaire du site apparaissent dans l'email
- Tous les liens pointent vers l'URL réelle de CE site (custom domain ou fallback)
- L'adresse "from" utilise le domaine du site si vérifié dans Resend,
  sinon fallback sur RESEND_DEFAULT_FROM (onboarding@resend.dev pour les tests)

Templates disponibles :
- order_confirmation (client) → après paiement Mollie OK
- shipping_update (client)    → quand tracking_number ajouté
- admin_new_order (admin)     → sur chaque commande payée
- return_request (concepteur) → client demande un retour
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Optional

import resend
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr

from deps import db, get_current_user
from services.email_i18n import t as i18n_t, detect_order_lang, normalize_lang, infer_brand_tone, t_tone

logger = logging.getLogger("conceptfactory.emails")
router = APIRouter()

RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
DEFAULT_FROM = os.environ.get("RESEND_DEFAULT_FROM", "onboarding@resend.dev")
ADMIN_EMAIL = os.environ.get("RESEND_ADMIN_EMAIL", "admin@conceptfactory.fr")
# As long as no verified domain, Resend only allows sending to the account owner's email
RESEND_OWNER_EMAIL = os.environ.get("RESEND_OWNER_EMAIL", "")

if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY


# ============== ASSET URL HELPERS (TÂCHE 2 — emails personnalisés) ============== #
def _absolute_url(url: str, public_origin: str) -> str:
    """Convert relative URL to absolute, using site public URL.

    Examples
    --------
        '/api/uploads/logos/foo.png' + 'https://altea-home.com'
            → 'https://altea-home.com/api/uploads/logos/foo.png'
        'https://other.cdn/img.png' → unchanged
        '' → ''
    """
    if not url:
        return ""
    u = str(url).strip()
    if u.startswith("http://") or u.startswith("https://") or u.startswith("data:"):
        return u
    if u.startswith("//"):
        return "https:" + u
    base = (public_origin or "").rstrip("/")
    if not base:
        base = (os.environ.get("PUBLIC_FRONTEND_URL") or
                os.environ.get("FRONTEND_URL") or "").rstrip("/")
    if not u.startswith("/"):
        u = "/" + u
    return f"{base}{u}"


def _resolve_brand_assets(site: dict, public_origin: str) -> dict:
    """Extract brand visuals usable in an email.

    Returns dict with:
        brand_name      : str
        logo_url        : str (absolute)
        primary         : str (hex, fallback #B84B31)
        accent          : str (hex)
        contact_url     : str (absolute)
    """
    design = (site or {}).get("design") or {}
    brand = design.get("brand") or {}
    palette = design.get("color_palette") or {}

    brand_name = (site.get("name") or brand.get("name") or "Boutique")

    # Prefer wordmark over icon-only logo for emails (more recognizable in inbox)
    raw_logo = (
        brand.get("logo_wordmark_url")
        or brand.get("logo_url")
        or design.get("logo_wordmark_url")
        or design.get("logo_url")
        or ""
    )
    logo_url = _absolute_url(raw_logo, public_origin)

    primary = (
        brand.get("primary_color")
        or palette.get("primary")
        or design.get("primary_color")
        or "#B84B31"
    )
    accent = (
        brand.get("accent_color")
        or palette.get("accent")
        or design.get("accent_color")
        or primary
    )
    contact_url = f"{(public_origin or '').rstrip('/')}/contact"

    return {
        "brand_name": brand_name,
        "logo_url": logo_url,
        "primary": primary,
        "accent": accent,
        "contact_url": contact_url,
    }


def _resolve_legal_footer(site: dict, lang: str = "fr") -> str:
    """Build the legal HTML footer for emails.

    Strategy :
        1. If site.design.legal_info has SIREN/SIRET/company_name → use it
        2. Else fallback on Altiaro centralized legal info (via altiaro_legal)
    """
    legal_info = ((site or {}).get("design") or {}).get("legal_info") or {}
    company = (legal_info.get("company_name")
               or legal_info.get("legal_name")
               or "")
    siren = legal_info.get("siren") or ""
    siret = legal_info.get("siret") or ""
    address = legal_info.get("address") or ""

    if company and (siren or siret):
        bits = [company]
        if siren:
            bits.append(f"SIREN {siren}")
        if siret and siret != siren:
            bits.append(f"SIRET {siret}")
        if address:
            bits.append(address)
        return " · ".join(bits)

    # Fallback Altiaro centralized
    try:
        from altiaro_legal import get_platform_legal_info
        info = get_platform_legal_info()
        bits = [info.get("legal_name") or "Altiaro SAS"]
        if info.get("siren"):
            bits.append(f"SIREN {info['siren']}")
        addr = info.get("address_line") or info.get("address") or ""
        if addr:
            bits.append(addr)
        return " · ".join(bits)
    except Exception:
        return "Altiaro SAS · France"


# ============== SITE URL RESOLUTION ============== #
async def get_site_public_url(site: dict) -> str:
    """Retourne l'URL publique d'un site : domaine custom si validé, sinon fallback."""
    domain = (site.get("domain") or "").strip()
    if domain:
        scheme = "https://" if not domain.startswith("http") else ""
        return f"{scheme}{domain}".rstrip("/")
    frontend = os.environ.get("FRONTEND_URL", "https://senior-france.preview.emergentagent.com")
    return f"{frontend}/shop/{site.get('id')}"


async def get_site_from_email(site: dict) -> tuple:
    """Retourne (from_addr, reply_to, dkim_verified) pour ce site.

    Stratégie :
        1. Si le domaine custom du site est vérifié dans Resend (DKIM ok),
           on peut envoyer DEPUIS `noreply@{domain}` → Reply-To `contact@{domain}`.
        2. Sinon, fallback DEFAULT_FROM (Altiaro/Resend) avec Reply-To
           `contact@{domain}` pour rediriger les réponses vers la boutique.
    """
    raw = (site.get("custom_domain") or site.get("domain") or "")
    domain = raw.replace("https://", "").replace("http://", "").rstrip("/")
    brand = site.get("name") or "Boutique"
    if not domain:
        return DEFAULT_FROM, None, False
    reply_to = f"contact@{domain}"
    try:
        domains_resp = await asyncio.to_thread(resend.Domains.list)
        verified_names = {d.get("name") for d in (domains_resp.get("data") or [])
                          if d.get("status") == "verified"}
        for name in verified_names:
            if name and (domain == name or domain.endswith(f".{name}")):
                # DKIM verified for this domain → send from custom address
                return f"{brand} <noreply@{name}>", reply_to, True
    except Exception as e:
        logger.warning(f"Resend domain check failed: {e}")
    # Fallback : send via Altiaro DEFAULT_FROM but Reply-To set on shop contact
    return DEFAULT_FROM, reply_to, False


# ============== TEMPLATE SHELL (inline CSS, table-based) ============== #
def _email_shell(brand_name: str, logo_url: str, primary: str,
                 site_url: str, inner_html: str, preheader: str = "",
                 lang: str = "fr",
                 signature_html: str = "",
                 legal_footer: str = "",
                 accent: str = "") -> str:
    lang = normalize_lang(lang)
    contact_html = i18n_t("shell.contact_us_html", lang=lang,
                          contact_url=f"{site_url}/contact", primary=primary)
    logo_block = (
        f'<img src="{logo_url}" alt="{brand_name}" '
        f'style="max-width:200px;max-height:60px;height:auto;display:block;">'
        if logo_url else
        f'<div style="font-family:Georgia,serif;font-size:28px;font-weight:600;color:{primary};">'
        f'{brand_name}</div>'
    )
    sig_block = (
        f'<p style="color:#57534E;font-size:14px;line-height:1.6;margin:24px 0 8px 0;font-style:italic;">'
        f'{signature_html}</p>'
        if signature_html else ""
    )
    legal_block = (
        f'<p style="margin:8px 0 0 0;font-size:10px;color:#A8A29E;line-height:1.5;">{legal_footer}</p>'
        if legal_footer else ""
    )
    accent_bar = accent or primary
    return f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{brand_name}</title>
</head>
<body style="margin:0;padding:0;background:#F5F2EB;font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif;color:#1C1917;">
<span style="display:none!important;opacity:0;height:0;width:0;overflow:hidden;">{preheader}</span>
<table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#F5F2EB;padding:32px 16px;">
  <tr>
    <td align="center">
      <table width="600" cellpadding="0" cellspacing="0" border="0" style="max-width:600px;background:#FFFFFF;border-radius:16px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.04);">
        <tr>
          <td style="height:4px;background:{accent_bar};font-size:0;line-height:0;">&nbsp;</td>
        </tr>
        <tr>
          <td style="padding:32px 32px 16px 32px;border-bottom:1px solid #E7E5E4;" align="left">
            <a href="{site_url}" style="text-decoration:none;">{logo_block}</a>
          </td>
        </tr>
        <tr>
          <td style="padding:32px;">
            {inner_html}
            {sig_block}
          </td>
        </tr>
        <tr>
          <td style="padding:24px 32px;background:#FAF7F2;border-top:1px solid #E7E5E4;text-align:center;">
            <p style="margin:0 0 8px 0;font-size:13px;color:#57534E;">
              {contact_html}
            </p>
            <p style="margin:0;font-size:11px;color:#A8A29E;">
              © {datetime.now(timezone.utc).year} {brand_name} · <a href="{site_url}" style="color:#A8A29E;text-decoration:none;">{site_url.replace('https://', '').replace('http://', '')}</a>
            </p>
            {legal_block}
          </td>
        </tr>
      </table>
    </td>
  </tr>
</table>
</body>
</html>"""


# ============== CORE SENDER ============== #
async def send_email_via_resend(to: str, subject: str, html: str,
                                 site: Optional[dict] = None,
                                 tags: Optional[list] = None) -> dict:
    """Envoie un email via Resend. Ne lève JAMAIS d'exception au caller pour
    ne pas casser le flow orders. Log en cas d'échec + persiste la tentative.
    """
    if not RESEND_API_KEY:
        logger.warning("RESEND_API_KEY missing — email skipped")
        return {"sent": False, "reason": "no_api_key"}

    if site:
        from_addr, reply_to, dkim_ok = await get_site_from_email(site)
    else:
        from_addr, reply_to, dkim_ok = DEFAULT_FROM, None, False
    params = {
        "from": from_addr,
        "to": [to],
        "subject": subject,
        "html": html,
    }
    if reply_to:
        params["reply_to"] = [reply_to]
    if tags:
        # Resend tags: only ASCII letters, numbers, underscores, or dashes allowed
        import re as _re
        clean_tags = []
        for tg in tags:
            cleaned = _re.sub(r"[^A-Za-z0-9_\-]", "_", str(tg))[:60]
            if cleaned:
                clean_tags.append({"name": cleaned, "value": "1"})
        if clean_tags:
            params["tags"] = clean_tags

    try:
        res = await asyncio.to_thread(resend.Emails.send, params)
        email_id = res.get("id") if isinstance(res, dict) else None
        await db.email_log.insert_one({
            "to": to,
            "from": from_addr,
            "reply_to": reply_to,
            "dkim_verified": dkim_ok,
            "subject": subject,
            "tags": tags or [],
            "site_id": (site or {}).get("id"),
            "email_id": email_id,
            "status": "sent",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        logger.info(f"[email] sent to {to}: {subject} (id={email_id})")
        return {"sent": True, "email_id": email_id, "from": from_addr,
                "reply_to": reply_to, "dkim_verified": dkim_ok}
    except Exception as e:
        logger.exception("Resend send failed")
        await db.email_log.insert_one({
            "to": to,
            "from": from_addr,
            "reply_to": reply_to,
            "subject": subject,
            "tags": tags or [],
            "site_id": (site or {}).get("id"),
            "status": "failed",
            "error": str(e)[:500],
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        return {"sent": False, "reason": str(e)[:200]}


# ============== TEMPLATE HELPERS ============== #
def _eur(v: float) -> str:
    return f"{float(v or 0):.2f} €".replace(".", ",")


def _order_rows_html(order: dict, lang: str = "fr") -> str:
    items = order.get("items") or []
    quantity_label = i18n_t("order_confirmation.quantity", lang=lang)
    rows = []
    for it in items:
        name = it.get("name") or ""
        if isinstance(name, dict):
            name = name.get(lang) or name.get("fr") or name.get("en") or "Produit"
        qty = int(it.get("quantity") or 1)
        price = float(it.get("price") or 0)
        line_total = qty * price
        rows.append(f"""
        <tr>
          <td style="padding:12px 0;border-bottom:1px solid #F5F2EB;">
            <strong style="color:#1C1917;font-size:14px;">{name}</strong><br>
            <span style="color:#78716C;font-size:12px;">{quantity_label} : {qty}</span>
          </td>
          <td style="padding:12px 0;border-bottom:1px solid #F5F2EB;text-align:right;font-family:monospace;font-size:14px;">{_eur(line_total)}</td>
        </tr>""")
    return "".join(rows)


async def build_order_confirmation_html(order: dict, site: dict) -> str:
    lang = detect_order_lang(order, site)
    tone = infer_brand_tone(site)
    site_url = await get_site_public_url(site)
    assets = _resolve_brand_assets(site, site_url)
    brand = assets["brand_name"]
    logo = assets["logo_url"]
    primary = assets["primary"]
    accent = assets["accent"]

    customer_name = ((order.get("customer") or {}).get("name")
                     or i18n_t("shell.greeting_fallback", lang=lang))
    order_number = order.get("order_number") or order.get("id", "")[:8].upper()
    subtotal = float(order.get("subtotal") or 0)
    shipping = float(order.get("shipping_total") or order.get("shipping_fee") or 0)
    tax = float(order.get("tax_total") or order.get("tax") or 0)
    total = float(order.get("total") or 0)
    order_url = f"{site_url}/account/orders/{order.get('id')}"

    title = t_tone("order_confirmation.title_with_name", tone=tone, lang=lang,
                    customer_name=customer_name)
    confirmed_text = t_tone("order_confirmation.confirmed_text", tone=tone, lang=lang,
                             order_number=order_number)
    your_order = i18n_t("order_confirmation.your_order", lang=lang)
    sub_label = i18n_t("order_confirmation.subtotal", lang=lang)
    ship_label = i18n_t("order_confirmation.shipping", lang=lang)
    tax_label = i18n_t("order_confirmation.tax", lang=lang)
    total_label = i18n_t("order_confirmation.total", lang=lang)
    track_label = i18n_t("order_confirmation.track_my_order", lang=lang)
    legal_notice = i18n_t("order_confirmation.legal_notice", lang=lang, brand=brand)
    security_notice = i18n_t("order_confirmation.security_notice", lang=lang)
    preheader = i18n_t("order_confirmation.preheader", lang=lang, order_number=order_number)
    signature = t_tone("shell.signature", tone=tone, lang=lang, brand=brand)
    legal_footer = _resolve_legal_footer(site, lang=lang)

    inner = f"""
<h1 style="font-family:Georgia,serif;font-size:26px;font-weight:600;color:#1C1917;margin:0 0 8px 0;line-height:1.2;">{title}</h1>
<p style="color:#57534E;font-size:15px;line-height:1.6;margin:0 0 24px 0;">
  {confirmed_text}
</p>

<div style="background:#FAF7F2;border-radius:12px;padding:20px 20px 8px 20px;margin:24px 0;border-left:3px solid {primary};">
  <h2 style="font-family:Georgia,serif;font-size:16px;margin:0 0 12px 0;color:#1C1917;">{your_order}</h2>
  <table width="100%" cellpadding="0" cellspacing="0" border="0">
    {_order_rows_html(order, lang=lang)}
    <tr><td style="padding:10px 0 4px 0;color:#78716C;font-size:13px;">{sub_label}</td><td style="padding:10px 0 4px 0;text-align:right;font-family:monospace;font-size:13px;">{_eur(subtotal)}</td></tr>
    <tr><td style="padding:2px 0;color:#78716C;font-size:13px;">{ship_label}</td><td style="padding:2px 0;text-align:right;font-family:monospace;font-size:13px;">{_eur(shipping)}</td></tr>
    <tr><td style="padding:2px 0 12px 0;color:#78716C;font-size:13px;">{tax_label}</td><td style="padding:2px 0 12px 0;text-align:right;font-family:monospace;font-size:13px;">{_eur(tax)}</td></tr>
    <tr><td style="padding:12px 0 0 0;border-top:2px solid #1C1917;font-weight:600;font-size:15px;">{total_label}</td><td style="padding:12px 0 0 0;text-align:right;border-top:2px solid #1C1917;font-family:monospace;font-size:18px;font-weight:600;color:{primary};">{_eur(total)}</td></tr>
  </table>
</div>

<table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin:24px 0;">
  <tr><td align="center">
    <a href="{order_url}" style="display:inline-block;padding:14px 28px;background:{primary};color:#FFFFFF;text-decoration:none;border-radius:999px;font-weight:500;font-size:14px;">{track_label} →</a>
  </td></tr>
</table>

<p style="color:#78716C;font-size:12px;line-height:1.6;margin:24px 0 0 0;">
  {legal_notice}<br>
  {security_notice}
</p>
"""
    return _email_shell(brand, logo, primary, site_url, inner,
                        preheader=preheader, lang=lang,
                        signature_html=signature,
                        legal_footer=legal_footer,
                        accent=accent)


async def build_shipping_update_html(order: dict, site: dict,
                                     tracking_number: str, carrier: str = "") -> str:
    lang = detect_order_lang(order, site)
    tone = infer_brand_tone(site)
    site_url = await get_site_public_url(site)
    assets = _resolve_brand_assets(site, site_url)
    brand = assets["brand_name"]
    logo = assets["logo_url"]
    primary = assets["primary"]
    accent = assets["accent"]

    customer_name = ((order.get("customer") or {}).get("name")
                     or i18n_t("shell.greeting_fallback", lang=lang))
    order_number = order.get("order_number") or order.get("id", "")[:8].upper()
    carrier_label = carrier or i18n_t("shipping_update.default_carrier", lang=lang)

    title = i18n_t("shipping_update.title_with_name", lang=lang, customer_name=customer_name)
    body_text = i18n_t("shipping_update.body_text", lang=lang,
                       order_number=order_number, carrier=carrier_label)
    tracking_label = i18n_t("shipping_update.tracking_label", lang=lang)
    help_text = i18n_t("shipping_update.help_text", lang=lang)
    preheader = i18n_t("shipping_update.preheader", lang=lang,
                       order_number=order_number, tracking=tracking_number)
    signature = t_tone("shell.signature", tone=tone, lang=lang, brand=brand)
    legal_footer = _resolve_legal_footer(site, lang=lang)

    inner = f"""
<h1 style="font-family:Georgia,serif;font-size:26px;font-weight:600;color:#1C1917;margin:0 0 8px 0;line-height:1.2;">{title}</h1>
<p style="color:#57534E;font-size:15px;line-height:1.6;margin:0 0 24px 0;">
  {body_text}
</p>

<div style="background:#FAF7F2;border-radius:12px;padding:24px;margin:24px 0;text-align:center;border-left:3px solid {primary};">
  <div style="font-size:12px;color:#78716C;text-transform:uppercase;letter-spacing:1.5px;margin-bottom:8px;">{tracking_label}</div>
  <div style="font-family:monospace;font-size:20px;font-weight:600;color:#1C1917;letter-spacing:1px;">{tracking_number}</div>
</div>

<p style="color:#78716C;font-size:13px;line-height:1.6;margin:16px 0;">
  {help_text}
</p>
"""
    return _email_shell(brand, logo, primary, site_url, inner,
                        preheader=preheader, lang=lang,
                        signature_html=signature,
                        legal_footer=legal_footer,
                        accent=accent)


async def build_admin_new_order_html(order: dict, site: dict) -> str:
    brand = site.get("name") or "Boutique"
    primary = "#1C1917"
    site_url = await get_site_public_url(site)
    order_number = order.get("order_number") or order.get("id", "")[:8].upper()
    total = float(order.get("total") or 0)
    customer = (order.get("customer") or {})
    country = (order.get("shipping_address") or {}).get("country") or "-"
    margin_ht = 0
    try:
        items = order.get("items") or []
        for it in items:
            price = float(it.get("price") or 0)
            cost = float(it.get("cost_price_ht") or 0)
            qty = int(it.get("quantity") or 1)
            margin_ht += (price / 1.2 - cost) * qty  # estimation HT
    except Exception:
        pass

    inner = f"""
<h1 style="font-family:Georgia,serif;font-size:22px;font-weight:600;color:#1C1917;margin:0 0 16px 0;">🎉 Nouvelle commande sur {brand}</h1>

<table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#FAF7F2;border-radius:12px;padding:16px;margin:16px 0;">
  <tr><td style="padding:8px;color:#78716C;font-size:13px;">Commande</td><td style="padding:8px;text-align:right;font-family:monospace;font-size:14px;font-weight:600;">#{order_number}</td></tr>
  <tr><td style="padding:8px;color:#78716C;font-size:13px;">Site</td><td style="padding:8px;text-align:right;font-size:13px;">{brand}</td></tr>
  <tr><td style="padding:8px;color:#78716C;font-size:13px;">Client</td><td style="padding:8px;text-align:right;font-size:13px;">{customer.get('name','')} &lt;{customer.get('email','')}&gt;</td></tr>
  <tr><td style="padding:8px;color:#78716C;font-size:13px;">Pays livraison</td><td style="padding:8px;text-align:right;font-size:13px;">{country}</td></tr>
  <tr><td style="padding:8px;color:#78716C;font-size:13px;">Total TTC</td><td style="padding:8px;text-align:right;font-family:monospace;font-size:14px;font-weight:600;">{_eur(total)}</td></tr>
  <tr><td style="padding:8px;color:#78716C;font-size:13px;">Marge brute HT estimée</td><td style="padding:8px;text-align:right;font-family:monospace;font-size:14px;color:#047857;font-weight:600;">{_eur(margin_ht)}</td></tr>
</table>

<p style="color:#78716C;font-size:12px;margin:16px 0 0 0;">
  50% de la marge sera virée au Concepteur lors du prochain virement (1er/15 du mois).
</p>
"""
    return _email_shell("Altiaro Admin", "", primary, site_url, inner,
                        preheader=f"Nouvelle commande #{order_number} — {_eur(total)}")


# ============== HIGH-LEVEL SEND HELPERS (used by orders flow) ============== #
async def send_order_confirmation(order: dict, site: dict) -> dict:
    if not (order.get("customer") or {}).get("email"):
        return {"sent": False, "reason": "no_customer_email"}
    lang = detect_order_lang(order, site)
    html = await build_order_confirmation_html(order, site)
    order_number = order.get("order_number") or order.get("id", "")[:8].upper()
    subject = i18n_t("order_confirmation.subject", lang=lang,
                      brand=site.get("name", "")) + f" · #{order_number}"
    return await send_email_via_resend(
        to=order["customer"]["email"],
        subject=subject,
        html=html, site=site,
        tags=["order_confirmation", f"site:{site.get('id','')[:8]}", f"lang:{lang}"],
    )


async def send_shipping_update(order: dict, site: dict,
                               tracking_number: str, carrier: str = "") -> dict:
    if not (order.get("customer") or {}).get("email"):
        return {"sent": False, "reason": "no_customer_email"}
    lang = detect_order_lang(order, site)
    html = await build_shipping_update_html(order, site, tracking_number, carrier)
    order_number = order.get("order_number") or order.get("id", "")[:8].upper()
    subject = "📦 " + i18n_t("shipping_update.subject", lang=lang,
                              brand=site.get("name", "")) + f" · #{order_number}"
    return await send_email_via_resend(
        to=order["customer"]["email"],
        subject=subject,
        html=html, site=site,
        tags=["shipping_update", f"lang:{lang}"],
    )


async def send_admin_new_order(order: dict, site: dict) -> dict:
    html = await build_admin_new_order_html(order, site)
    order_number = order.get("order_number") or order.get("id", "")[:8].upper()
    total = float(order.get("total") or 0)
    # In Resend sandbox mode (no verified domain), we must send to the owner email
    recipient = RESEND_OWNER_EMAIL or ADMIN_EMAIL
    return await send_email_via_resend(
        to=recipient,
        subject=f"💰 Commande #{order_number} · {_eur(total)} · {site.get('name','')}",
        html=html, site=site,
        tags=["admin_notification"],
    )


# ============== DOMAIN PURCHASE EMAILS ============== #
async def _build_domain_email_html(*, domain: str, site: dict, title: str,
                                   intro: str, body_html: str,
                                   cta_label: str = "", cta_url: str = "",
                                   preheader: str = "") -> str:
    brand = site.get("name") or "Altiaro"
    design = site.get("design") or {}
    logo = (design.get("brand") or {}).get("logo_url") or ""
    primary = (design.get("brand") or {}).get("primary_color") or "#2563EB"
    site_url = await get_site_public_url(site)
    cta_block = (
        f"""
<table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin:24px 0;">
  <tr><td align="center">
    <a href="{cta_url}" style="display:inline-block;padding:14px 28px;background:{primary};color:#FFFFFF;text-decoration:none;border-radius:999px;font-weight:500;font-size:14px;">{cta_label} →</a>
  </td></tr>
</table>"""
        if cta_label and cta_url else ""
    )
    inner = f"""
<h1 style="font-family:Georgia,serif;font-size:26px;font-weight:600;color:#1C1917;margin:0 0 8px 0;line-height:1.2;">{title}</h1>
<p style="color:#57534E;font-size:15px;line-height:1.6;margin:0 0 20px 0;">{intro}</p>

<div style="background:#FAF7F2;border-radius:12px;padding:20px;margin:24px 0;text-align:center;">
  <div style="font-size:11px;color:#78716C;text-transform:uppercase;letter-spacing:1.5px;margin-bottom:8px;">Domaine</div>
  <div style="font-family:monospace;font-size:22px;font-weight:600;color:{primary};letter-spacing:0.5px;">{domain}</div>
</div>

{body_html}
{cta_block}

<p style="color:#A8A29E;font-size:11px;line-height:1.6;margin:32px 0 0 0;">
  Altiaro facture et gère pour toi l'achat chez OVH. Renouvellement automatique chaque année au même prix.
</p>
"""
    return _email_shell(brand, logo, primary, site_url, inner, preheader=preheader)


async def send_domain_purchased(domain_record: dict, site: dict, user: dict) -> dict:
    """Envoyé au Concepteur juste après le succès OVH (via webhook Mollie)."""
    recipient = (user or {}).get("email") or RESEND_OWNER_EMAIL
    if not recipient:
        return {"sent": False, "reason": "no_recipient"}
    domain = domain_record.get("domain") or ""
    price = domain_record.get("platform_price_eur") or 0
    dns_url = f"{os.environ.get('FRONTEND_URL', '')}/sites/{site.get('id')}/domains"
    body = f"""
<div style="background:#D1FAE5;border:1px solid #A7F3D0;border-radius:8px;padding:14px 16px;margin:16px 0;">
  <div style="font-size:13px;color:#065F46;line-height:1.5;">
    ✅ <strong>Paiement confirmé</strong> — {_eur(price)} facturés via Mollie.<br>
    ✅ <strong>Achat OVH</strong> effectué sous ton compte Altiaro.<br>
    ⏳ <strong>DNS</strong> : la zone se crée chez OVH dans 5 à 15 minutes. Dès qu'elle est prête, clique sur <em>"Configurer DNS"</em> depuis la console et ton site <strong>{site.get('name','')}</strong> sera en ligne sur <strong>{domain}</strong>.
  </div>
</div>
<p style="color:#57534E;font-size:14px;line-height:1.6;margin:16px 0 0 0;">
  Si tu veux, on peut t'envoyer un rappel dans 15 min pour lancer la configuration DNS en 1 clic.
</p>
"""
    html = await _build_domain_email_html(
        domain=domain, site=site,
        title=f"🎉 {domain} est à toi",
        intro=f"Bonne nouvelle ! Ton domaine vient d'être acheté pour le site <strong>{site.get('name','')}</strong>. Dernière étape : la configuration DNS (5-15 min).",
        body_html=body,
        cta_label="Configurer les DNS",
        cta_url=dns_url,
        preheader=f"{domain} acheté · prochaine étape : DNS",
    )
    return await send_email_via_resend(
        to=recipient,
        subject=f"🎉 Ton domaine {domain} est prêt",
        html=html, site=site,
        tags=["domain_purchased"],
    )


async def send_domain_purchase_failed(domain_record: dict, site: dict, user: dict,
                                      error: str) -> dict:
    """Envoyé au Concepteur si le paiement Mollie a réussi mais l'achat OVH a échoué."""
    recipient = (user or {}).get("email") or RESEND_OWNER_EMAIL
    if not recipient:
        return {"sent": False, "reason": "no_recipient"}
    domain = domain_record.get("domain") or ""
    price = domain_record.get("platform_price_eur") or 0
    body = f"""
<div style="background:#FFE4E6;border:1px solid #FECDD3;border-radius:8px;padding:14px 16px;margin:16px 0;">
  <div style="font-size:13px;color:#9F1239;line-height:1.5;">
    ⚠️ Le paiement Mollie de <strong>{_eur(price)}</strong> est bien reçu, mais l'achat chez OVH a échoué :<br>
    <code style="font-family:monospace;background:#FFFFFF;padding:2px 6px;border-radius:4px;font-size:12px;">{(error or '')[:200]}</code>
  </div>
</div>
<p style="color:#57534E;font-size:14px;line-height:1.6;margin:16px 0;">
  <strong>Pas de panique</strong> : on a tout loggé, ton paiement est sécurisé. L'équipe Altiaro va :
</p>
<ol style="color:#57534E;font-size:14px;line-height:1.8;padding-left:20px;margin:0 0 16px 0;">
  <li>Relancer manuellement l'achat OVH dans les 24 h,</li>
  <li>Ou te rembourser intégralement si le domaine n'est plus disponible.</li>
</ol>
<p style="color:#57534E;font-size:14px;line-height:1.6;margin:16px 0 0 0;">
  On te tient au courant très vite par email.
</p>
"""
    html = await _build_domain_email_html(
        domain=domain, site=site,
        title="Achat OVH en attente d'intervention",
        intro=f"Ton paiement pour <strong>{domain}</strong> a bien été reçu, mais une erreur technique bloque l'achat chez OVH.",
        body_html=body,
        preheader=f"{domain} — paiement OK, achat OVH à relancer",
    )
    return await send_email_via_resend(
        to=recipient,
        subject=f"⚠️ {domain} — paiement OK, achat OVH à relancer",
        html=html, site=site,
        tags=["domain_purchase_failed"],
    )


# ============== API ROUTES (for manual testing + admin) ============== #
class TestEmailInput(BaseModel):
    to: EmailStr
    site_id: Optional[str] = None
    template: str = "order_confirmation"  # or shipping_update, admin_new_order


@router.post("/emails/test")
async def test_email(data: TestEmailInput, user: dict = Depends(get_current_user)):
    """Envoie un email test avec un faux order pour valider le template/delivery."""
    if user.get("role") != "admin":
        raise HTTPException(403, "Admin only")
    if not RESEND_API_KEY:
        raise HTTPException(503, "RESEND_API_KEY non configurée dans backend/.env")
    site = None
    if data.site_id:
        site = await db.sites.find_one({"id": data.site_id}, {"_id": 0})
    if not site:
        site = {
            "id": "demo-site",
            "name": "Boutique Démo",
            "domain": "",
            "design": {"brand": {"primary_color": "#B84B31", "logo_url": ""}},
            "selected_countries": ["FR"],
        }
    fake_order = {
        "id": "demo-order-id",
        "order_number": "DEMO123",
        "customer": {"name": "Marie Dubois", "email": data.to},
        "items": [
            {"name": {"fr": "Fauteuil releveur électrique — gris anthracite"},
             "quantity": 1, "price": 749.00, "cost_price_ht": 280.00},
            {"name": {"fr": "Coussin ergonomique mémoire de forme"},
             "quantity": 2, "price": 39.90, "cost_price_ht": 11.50},
        ],
        "subtotal": 828.80, "shipping_total": 0, "tax_total": 138.13, "total": 828.80,
        "shipping_address": {"country": "FR"},
    }
    if data.template == "shipping_update":
        result = await send_shipping_update(fake_order, site, "1Z999AA10123456784", "La Poste")
    elif data.template == "admin_new_order":
        result = await send_admin_new_order(fake_order, site)
    else:
        result = await send_order_confirmation(fake_order, site)
    return result


@router.get("/emails/log")
async def email_log(user: dict = Depends(get_current_user), limit: int = 50):
    if user.get("role") != "admin":
        raise HTTPException(403, "Admin only")
    cursor = db.email_log.find({}, {"_id": 0}).sort("created_at", -1).limit(limit)
    return {"emails": await cursor.to_list(limit)}


@router.get("/emails/domains")
async def list_resend_domains(user: dict = Depends(get_current_user)):
    """Liste les domaines configurés dans Resend avec leur statut de vérification."""
    if user.get("role") != "admin":
        raise HTTPException(403, "Admin only")
    if not RESEND_API_KEY:
        raise HTTPException(503, "RESEND_API_KEY manquante")
    try:
        res = await asyncio.to_thread(resend.Domains.list)
        return {"domains": res.get("data") or [], "default_from": DEFAULT_FROM}
    except Exception as e:
        raise HTTPException(502, f"Resend API error: {str(e)[:200]}")
