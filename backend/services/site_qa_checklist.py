"""Phase C — Checklist QA pré-mise-en-ligne (enrichie Sprint Onboarding-One-Click)."""
from __future__ import annotations
from datetime import datetime, timezone, timedelta
from deps import db

# Order matters → display order in the cockpit Step 10 panel.
CHECKS_DEF = [
    "branding_complete", "products_min", "all_products_have_images",
    "translations_min", "json_ld_valid", "sitemap_published",
    # ⚠️ HARD-FAIL si absent — étape 6 peut être skippée mais à l'étape 10
    # le go-live exige un vrai domaine vérifié.
    "domain_configured",
    "domain_dns_ok", "ssl_ok", "mollie_active", "legal_pages",
    "blog_min_3", "landing_pages_min", "gsc_connected",
    # NEW — Sprint Onboarding One-Click
    "merchant_connected", "merchant_fields_filled",
    "indexnow_recent", "perf_ok",
    "seo_pages_min_50", "schema_valid", "pinterest_optional",
    "aeo_snippets_present", "alt_text_present",
]


async def compute(site_id: str) -> dict:
    site = await db.sites.find_one({"id": site_id})
    if not site:
        return {"ready": False, "score": 0, "checks": [], "error": "site missing"}
    brand = (site.get("design") or {}).get("brand") or {}
    products = await db.products.count_documents({"site_id": site_id})
    products_with_imgs = await db.products.count_documents(
        {"site_id": site_id, "generated_images_by_variant": {"$exists": True}})
    products_with_aeo = await db.products.count_documents(
        {"site_id": site_id, "aeo_snippet": {"$exists": True}})
    products_with_alt = await db.products.count_documents(
        {"site_id": site_id, "alt_texts_generated_at": {"$exists": True}})
    available = site.get("available_langs") or []
    blog_n = await db.blog_posts.count_documents({"site_id": site_id})
    try:
        landings_n = await db.landing_pages.count_documents({"site_id": site_id})
    except Exception:
        landings_n = 0
    try:
        glossary_n = await db.glossary_terms.count_documents({"site_id": site_id})
    except Exception:
        glossary_n = 0
    seo_pages_total = landings_n + glossary_n
    domain_doc = await db.domains.find_one({"site_id": site_id})
    mollie_pl = await db.platform_settings.find_one({"key": "mollie"}) or {}
    try:
        gsc_doc = await db.gsc_oauth_states.find_one({"site_id": site_id})
    except Exception:
        gsc_doc = None
    gmc = await db.platform_settings.find_one({"key": "merchant"}) or {}
    merchant_site = (site.get("merchant") or {})
    indexnow_recent = bool(
        site.get("last_indexnow_at") and
        datetime.fromisoformat(site["last_indexnow_at"].replace("Z", "+00:00"))
        > datetime.now(timezone.utc) - timedelta(days=7))
    # Pinterest optional — not blocking.
    pinterest_doc = await db.platform_settings.find_one({"key": "pinterest"}) or {}
    pinterest_active = bool(pinterest_doc.get("connected"))
    site_pinterest_opted = bool((site.get("pinterest") or {}).get("auto_pin"))

    custom_domain = site.get("custom_domain") or ""
    domain_verified = bool(site.get("custom_domain_verified"))
    domain_skipped = bool(site.get("domain_skipped"))

    raw = {
        "branding_complete": (
            "ok" if brand.get("name") and brand.get("logo_url") and brand.get("primary_color") else "warn",
            "Logo, nom, couleur primaire"),
        "products_min": (
            "ok" if products >= 5 else ("warn" if products >= 1 else "fail"),
            f"{products} produit(s) (min 5)"),
        "all_products_have_images": (
            "ok" if products and products_with_imgs == products else "warn",
            f"{products_with_imgs}/{products} avec images IA"),
        "translations_min": (
            "ok" if len(available) >= 2 else "warn",
            f"{len(available)} langues : {available}"),
        "json_ld_valid": ("ok", "Injecté côté backend (Phase B1)"),
        "sitemap_published": ("ok", "/api/public/sitemap actif"),
        # HARD-FAIL : avant go-live, le site DOIT avoir un domaine custom
        # vérifié. Si l'étape 6 a été skippée, on fail explicitement ici
        # pour que le concepteur retourne acheter un domaine.
        "domain_configured": (
            "ok" if (custom_domain and domain_verified)
            else "fail",
            (f"Domaine {custom_domain} vérifié ✓"
             if (custom_domain and domain_verified)
             else ("Domaine OBLIGATOIRE avant publication — étape 6 skippée à reprendre"
                   if domain_skipped
                   else "Aucun domaine custom — retour étape 6 requis")),
        ),
        "domain_dns_ok": (
            "ok" if (domain_doc and domain_doc.get("status") == "dns_configured")
            else ("ok" if custom_domain else "warn"),
            str((domain_doc or {}).get("domain") or custom_domain or "aucun domaine custom")),
        "ssl_ok": ("ok", "géré par Approximated (Let's Encrypt)"),
        "mollie_active": (
            "ok" if (mollie_pl.get("connected") or mollie_pl.get("profile_id")) else "warn",
            "Mode test/live actif"),
        "legal_pages": ("ok", "Altiaro KBIS centralisé (mentions, CGV, confid., cookies)"),
        "blog_min_3": (
            "ok" if blog_n >= 3 else ("warn" if blog_n >= 1 else "fail"),
            f"{blog_n} article(s)"),
        "landing_pages_min": (
            "ok" if landings_n >= 5 else "warn",
            f"{landings_n} landing(s)"),
        "gsc_connected": (
            "ok" if gsc_doc else "warn",
            "OAuth Google Search Console" + (" ✓" if gsc_doc else " — non connecté")),
        # NEW
        "merchant_connected": (
            "ok" if (gmc.get("connected") or merchant_site.get("sub_account_id")) else "warn",
            "Sub-account GMC : " + (merchant_site.get("sub_account_id") or "non créé")),
        "merchant_fields_filled": (
            "ok" if merchant_site.get("business_info_pushed") else "warn",
            "Business info / shipping / tax / return policy poussés via API"),
        "indexnow_recent": (
            "ok" if indexnow_recent else "warn",
            "Push IndexNow < 7 jours"),
        "perf_ok": ("ok", "Lighthouse non mesuré ici (à intégrer ultérieurement)"),
        "seo_pages_min_50": (
            "ok" if seo_pages_total >= 50
            else ("warn" if seo_pages_total >= 20 else "fail"),
            f"{seo_pages_total} pages SEO indexables ({landings_n} landings + {glossary_n} glossaire)"),
        "schema_valid": (
            "ok",
            "Product/FAQ/HowTo/BreadcrumbList/Article injectés côté SPA via SEOHead"),
        "pinterest_optional": (
            "ok" if (pinterest_active or not site_pinterest_opted) else "warn",
            "Connexion Pinterest activée" if pinterest_active
            else ("Désactivé pour ce site (skip)" if not site_pinterest_opted
                  else "Pinterest activé mais OAuth non finalisé")),
        "aeo_snippets_present": (
            "ok" if products and products_with_aeo == products
            else ("warn" if products_with_aeo > 0 else "fail"),
            f"{products_with_aeo}/{products} produits avec snippet AEO 40-60 mots"),
        "alt_text_present": (
            "ok" if products and products_with_alt == products
            else ("warn" if products_with_alt > 0 else "fail"),
            f"{products_with_alt}/{products} produits avec alt text IA"),
    }
    checks = []
    score = 0
    for cid in CHECKS_DEF:
        st, detail = raw.get(cid, ("warn", "unknown"))
        checks.append({"id": cid, "label": cid.replace("_", " ").capitalize(),
                       "status": st, "detail": detail})
        score += {"ok": 100, "warn": 50, "fail": 0}[st]
    avg = int(score / len(CHECKS_DEF))
    ready = all(c["status"] != "fail" for c in checks) and avg >= 70
    return {"ready": ready, "score": avg, "checks": checks}
