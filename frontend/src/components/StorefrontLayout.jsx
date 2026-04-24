import React, { useEffect, useState } from "react";
import { Link, useParams, useNavigate } from "react-router-dom";
import axios from "axios";
import { LANGUAGES, t } from "../lib/i18n";
import LanguageSwitcher from "./storefront/LanguageSwitcher";
import { readCart, cartTotals } from "../lib/cart";
import { getCustomer } from "../lib/customerAuth";
import CartDrawer from "./CartDrawer";
import StorefrontTracking from "./storefront/StorefrontTracking";
import { sanitizeBrandText } from "../lib/brandText";
import {
  ShoppingBag, Phone, ShieldCheck, Truck, MagnifyingGlass, User,
  List, X, FacebookLogo, InstagramLogo, YoutubeLogo, LinkedinLogo,
  CreditCard, EnvelopeSimple, MapPin, CaretRight,
} from "@phosphor-icons/react";

const BACKEND_URL = "";

/* ------- Nav items (pages naturelles du template) ------- */
const navItems = (shopRoot, lang) => [
  { label: t(lang, "nav_shop"),        href: `${shopRoot}` },
  { label: t(lang, "nav_collections"), href: `${shopRoot}/collections` },
  { label: t(lang, "nav_journal"),     href: `${shopRoot}/blog` },
  { label: t(lang, "nav_about"),       href: `${shopRoot}/about` },
  { label: t(lang, "nav_contact"),     href: `${shopRoot}/contact` },
];

export default function StorefrontLayout({ children, lang, setLang, availableLangs, site, design }) {
  const { siteId } = useParams();
  const navigate = useNavigate();
  const [cartCount, setCartCount] = useState(0);
  const [customer, setCustomer] = useState(() => (siteId ? getCustomer(siteId) : null));
  const [searchQ, setSearchQ] = useState("");
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    const update = () => setCartCount(cartTotals(readCart(siteId)).itemsCount);
    const updateCust = () => setCustomer(getCustomer(siteId));
    update();
    updateCust();
    window.addEventListener("cf_cart_updated", update);
    window.addEventListener("alt_cust_session", updateCust);
    return () => {
      window.removeEventListener("cf_cart_updated", update);
      window.removeEventListener("alt_cust_session", updateCust);
    };
  }, [siteId]);

  const shopRoot = `/shop/${siteId}`;
  const brand = design?.brand || {};
  // Template mode — "monochrome" (default) vs "brand". See designAccents().
  const templateMode = design?.template_mode === "brand" ? "brand" : "monochrome";
  const primary = templateMode === "brand" ? (brand.text_color || "#0A0A0A") : "#0A0A0A";
  const accent = templateMode === "brand" ? (brand.accent_color || "#F5F5F5") : "#F5F5F5";
  const bg = templateMode === "brand" ? (brand.background_color || "#FFFFFF") : "#FFFFFF";
  const textCol = templateMode === "brand" ? (brand.text_color || "#0A0A0A") : "#0A0A0A";
  const brandAccent = brand.primary_color || "#0A0A0A";
  const fontHeading = brand.font_heading || "Fraunces";
  const fontBody = brand.font_body || "Inter";
  const logoUrl = brand.logo_url ? `${BACKEND_URL}${brand.logo_url}` : null;
  // Sanitize brand name / site name so stale DB entries containing markdown or
  // Claude preambles ("# Proposition de nom…") don't leak into <h1>s and copyright.
  // Priority: explicit logo_text > brand.name > site.name > fallback.
  const rawLogoCandidate = brand.logo_text || brand.name || site?.name || "";
  const logoText = sanitizeBrandText(rawLogoCandidate, 40) || "Maison";
  const brandTaglineRaw = design?.brand?.tagline;
  const taglineRaw = typeof brandTaglineRaw === "string"
    ? brandTaglineRaw
    : (brandTaglineRaw?.[lang] || brandTaglineRaw?.fr || site?.niche_data?.tagline);
  const tagline = taglineRaw ? sanitizeBrandText(taglineRaw, 80) : "";

  const footerTagline = design?.footer?.tagline?.[lang] || design?.footer?.tagline?.fr
    || "Des produits pensés pour bien vieillir chez soi, avec dignité.";
  const contact = design?.contact || {};
  const contactEmail = contact.email || "bonjour@boutique.fr";
  const contactPhone = contact.phone || "01 23 45 67 89";
  const contactHours = contact.hours || "Lun–Ven · 9h–18h";
  const contactAddress = contact.address || "";
  const social = design?.social || {};

  // Footer background image — prioritise Concepteur override, then site's
  // own hero, else a calm editorial default image applied to every new site.
  // Concepteurs can always swap it during Step 5 / Step 6.
  const DEFAULT_FOOTER_BG = "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=2400&q=80&auto=format&fit=crop";
  const heroImgRaw = design?.hero?.image || design?.hero?.background_image || null;
  const heroImg = heroImgRaw
    ? (heroImgRaw.startsWith("http") ? heroImgRaw : `${BACKEND_URL}${heroImgRaw}`)
    : null;
  const footerBgImage =
    design?.footer?.background_url
    || design?.lifestyle_image
    || heroImg
    || DEFAULT_FOOTER_BG;

  const cssVars = {
    "--cf-primary": primary,
    "--cf-accent": accent,
    "--cf-bg": bg,
    "--cf-text": textCol,
    "--cf-font-heading": `"${fontHeading}", serif`,
    "--cf-font-body": `"${fontBody}", system-ui, sans-serif`,
  };

  const fontsQuery = encodeURIComponent(
    `${fontHeading}:wght@400;500;600;700|${fontBody}:wght@400;500;600`
  );

  // Header & footer navigation — source of truth is design.navigation (configured in the Studio).
  // We fall back to the default template items only if nothing is configured yet.
  //
  // The AI navigation optimizer (and older generations) sometimes produce French-slug
  // aliases that don't match the live routes ("/a-propos" vs "/about", "/mentions-legales"
  // vs "/mentions", "/collections/slug" vs "/collection/slug"). We normalise them here so
  // Concepteurs never ship broken menus.
  const HREF_ALIASES = {
    "/a-propos": "/about",
    "/a_propos": "/about",
    "/apropos": "/about",
    "/qui-sommes-nous": "/about",
    "/qui-nous-sommes": "/about",
    "/notre-histoire": "/about",
    "/mentions-legales": "/mentions",
    "/mentions_legales": "/mentions",
    "/mentions-legal": "/mentions",
    "/politique-de-confidentialite": "/confidentialite",
    "/politique-confidentialite": "/confidentialite",
    "/privacy": "/confidentialite",
    "/cookies-policy": "/cookies",
    "/conditions-generales": "/cgv",
    "/conditions-generales-de-vente": "/cgv",
    "/terms": "/cgv",
    "/delivery": "/livraison",
    "/shipping": "/livraison",
    "/returns": "/retours",
    "/refunds": "/retours",
    "/questions": "/faq",
    "/help": "/faq",
    "/journal": "/blog",
    "/news": "/blog",
    "/press": "/blog",
    "/boutique": "",
    "/shop": "",
    "/home": "",
    "/accueil": "",
  };

  const rewriteHref = (href = "") => {
    if (!href) return shopRoot;
    // External links → keep as-is
    if (/^https?:\/\//.test(href)) return href;
    // Mega-menu placeholders → route to the aggregate collections page
    if (href === "#" || href === "#/") return `${shopRoot}/collections`;
    // Already shop-scoped → trust it
    if (href.startsWith(shopRoot)) return href;
    // Normalise path & query
    let path = href.startsWith("/") ? href : "/" + href;
    // Strip trailing slash (except for the root "/")
    if (path.length > 1 && path.endsWith("/")) path = path.slice(0, -1);
    // Alias lookup (exact match first)
    if (HREF_ALIASES[path] !== undefined) {
      return `${shopRoot}${HREF_ALIASES[path]}`;
    }
    // /collections/<slug> → the route is /collection/<slug> (singular). Keep the plural
    // root /collections because StorefrontCollections lists them all.
    const collMatch = path.match(/^\/collections\/(.+)$/);
    if (collMatch) {
      return `${shopRoot}/collection/${collMatch[1]}`;
    }
    return `${shopRoot}${path}`;
  };
  const configuredHeader = design?.navigation?.header;
  const configuredFooter = design?.navigation?.footer;
  const nav = (Array.isArray(configuredHeader) && configuredHeader.length
    ? configuredHeader
    : navItems(shopRoot, lang)
  ).map((n) => ({ ...n, href: rewriteHref(n.href) }));
  const footerLinks = (Array.isArray(configuredFooter) && configuredFooter.length
    ? configuredFooter
    : [
        { label: "CGV",                            href: `${shopRoot}/cgv` },
        { label: t(lang, "footer_legal_notice"),   href: `${shopRoot}/mentions` },
        { label: t(lang, "footer_privacy"),        href: `${shopRoot}/confidentialite` },
      ]
  ).map((n) => ({ ...n, href: rewriteHref(n.href) }));
  const onSearch = (e) => {
    e.preventDefault();
    if (searchQ.trim().length >= 2) {
      navigate(`${shopRoot}/search?q=${encodeURIComponent(searchQ)}`);
      setMobileOpen(false);
    }
  };

  return (
    <div
      className="storefront-root min-h-screen flex flex-col"
      style={{ ...cssVars, background: bg, color: textCol, fontFamily: `"${fontBody}", system-ui, sans-serif` }}
      data-testid="storefront-layout"
    >
      <link rel="stylesheet" href={`https://fonts.googleapis.com/css2?family=${fontsQuery}&display=swap`} />
      <link rel="preconnect" href="https://fonts.googleapis.com" />
      <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
      <link rel="preconnect" href="https://images.unsplash.com" crossOrigin="anonymous" />
      <link rel="preconnect" href="https://cf.cjdropshipping.com" crossOrigin="anonymous" />
      <link rel="dns-prefetch" href="https://images.unsplash.com" />
      <link rel="dns-prefetch" href="https://cf.cjdropshipping.com" />

      <StorefrontTracking site={site} />

      {/* ================= TRUST BAR ================= */}
      <div className="text-white text-[12px] tracking-[0.01em]" style={{ background: textCol }}>
        <div className="max-w-7xl mx-auto px-6 py-2.5 flex items-center justify-between flex-wrap gap-2">
          <div className="flex items-center divide-x divide-white/15">
            <span className="flex items-center gap-1.5 pr-5">
              <Truck size={13} weight="bold" /> {t(lang, "free_shipping_above")}
            </span>
            <span className="hidden md:flex items-center gap-1.5 px-5">
              <ShieldCheck size={13} weight="bold" /> {t(lang, "secure_checkout")}
            </span>
            <span className="hidden md:flex items-center gap-1.5 pl-5">
              <Phone size={13} weight="bold" /> {t(lang, "support_seniors")}
            </span>
          </div>
          <LanguageSwitcher
            lang={lang}
            setLang={setLang}
            availableLangs={availableLangs && availableLangs.length ? availableLangs : LANGUAGES.map((l) => l.code)}
            tone="light"
          />
        </div>
      </div>

      {/* ================= HEADER ================= */}
      <header className="bg-white/95 backdrop-blur-md sticky top-0 z-30 border-b" style={{ borderColor: "#EDEAE4" }}>
        {/* -------- Mobile layout (<lg) : hamburger LEFT · logo CENTER · cart RIGHT -------- */}
        <div className="lg:hidden max-w-7xl mx-auto px-4 py-3.5 grid grid-cols-[auto_1fr_auto] items-center gap-3">
          <button
            type="button"
            onClick={() => setMobileOpen(true)}
            data-testid="mobile-menu-open"
            aria-label="Ouvrir le menu"
            className="w-11 h-11 min-w-[44px] min-h-[44px] rounded-full border flex items-center justify-center active:scale-95 transition-transform"
            style={{ borderColor: "#E7E5E4" }}
          >
            <List size={20} style={{ color: textCol }} />
          </button>
          <Link to={shopRoot} className="flex items-center justify-center gap-2" data-testid="shop-logo-mobile">
            {logoUrl ? (
              <img
                src={logoUrl}
                alt={logoText}
                className="h-9 max-w-[160px] object-contain"
                style={{ mixBlendMode: "multiply", filter: "contrast(1.25) brightness(1.08)" }}
                loading="eager"
              />
            ) : (
              <div
                className="font-semibold text-lg truncate"
                style={{ fontFamily: `"${fontHeading}", serif`, color: textCol }}
              >
                {logoText}
              </div>
            )}
          </Link>
          <button
            type="button"
            onClick={() => window.dispatchEvent(new Event("cf_cart_open"))}
            data-testid="cart-button-mobile"
            aria-label={t(lang, "cart")}
            className="relative w-11 h-11 min-w-[44px] min-h-[44px] rounded-full border bg-white hover:bg-neutral-50 flex items-center justify-center active:scale-95 transition-all"
            style={{ borderColor: "#E7E5E4" }}
          >
            <ShoppingBag size={20} weight="regular" style={{ color: textCol }} />
            {cartCount > 0 && (
              <span
                className="absolute -top-1 -right-1 min-w-[20px] h-[20px] text-[10px] font-semibold rounded-full flex items-center justify-center px-1 text-white"
                style={{ background: primary }}
              >
                {cartCount}
              </span>
            )}
          </button>
        </div>

        {/* -------- Desktop layout (>=lg) -------- */}
        <div className="hidden lg:grid max-w-7xl mx-auto px-6 py-5 items-center gap-8 grid-cols-[auto_1fr_auto]">
          {/* LEFT — Logo */}
          <Link to={shopRoot} className="group flex items-center gap-3 shrink-0" data-testid="shop-logo">
            {logoUrl ? (
              <img
                src={logoUrl}
                alt={logoText}
                className="h-10 max-w-[220px] object-contain transition-transform group-hover:scale-[1.02]"
                style={{ mixBlendMode: "multiply", filter: "contrast(1.25) brightness(1.08)" }}
                loading="eager"
              />
            ) : (
              <div
                className="font-semibold text-2xl leading-tight transition"
                style={{ fontFamily: `"${fontHeading}", serif`, color: textCol }}
              >
                <span className="group-hover:text-[var(--cf-primary)]">{logoText}</span>
                {tagline && (
                  <div className="text-[11px] mt-0.5" style={{ color: "#78716C" }}>
                    {tagline}
                  </div>
                )}
              </div>
            )}
          </Link>

          {/* CENTER — Nav desktop */}
          <nav className="hidden lg:flex items-center justify-center gap-10" data-testid="header-nav">
            {nav.map((n, idx) => {
              const isMega = n.type === "mega" && Array.isArray(n.children) && n.children.length > 0;
              if (isMega) {
                return (
                  <div key={`${n.label}-${idx}`} className="group relative">
                    <Link
                      to={rewriteHref(n.href || "/collections")}
                      data-testid={`nav-mega-${n.label.toLowerCase()}`}
                      className="text-[14px] font-medium tracking-[0.01em] inline-flex items-center gap-1 py-2 relative after:absolute after:left-1/2 after:-translate-x-1/2 after:bottom-0 after:h-[1.5px] after:w-0 after:bg-current after:transition-all after:duration-300 group-hover:after:w-[calc(100%-8px)]"
                      style={{ color: textCol }}
                    >
                      {n.label}
                      <CaretRight size={10} className="rotate-90 opacity-60 transition-transform group-hover:rotate-[270deg]" />
                    </Link>
                    {/* Mega panel (desktop) — appears on hover */}
                    <div
                      className="invisible opacity-0 group-hover:visible group-hover:opacity-100 transition-opacity duration-150 absolute left-1/2 -translate-x-1/2 top-full pt-4 z-40 w-[min(90vw,720px)]"
                      data-testid={`mega-panel-${n.label.toLowerCase()}`}
                    >
                      <div className="bg-white rounded-2xl shadow-2xl border p-5 grid grid-cols-2 md:grid-cols-3 gap-3"
                        style={{ borderColor: "#E7E5E4" }}>
                        {n.children.map((c, i) => (
                          <Link
                            key={i}
                            to={rewriteHref(c.href)}
                            data-testid={`mega-card-${i}`}
                            className="group/card block rounded-xl border bg-[var(--cf-bg)] overflow-hidden hover:shadow-lg transition"
                            style={{ borderColor: "#E7E5E4" }}
                          >
                            <div className="aspect-[4/3] bg-neutral-100 overflow-hidden">
                              {c.image ? (
                                <img
                                  src={c.image}
                                  alt={c.label}
                                  className="w-full h-full object-cover transition-transform duration-300 group-hover/card:scale-105"
                                />
                              ) : (
                                <div className="w-full h-full flex items-center justify-center text-neutral-400 text-xs">
                                  (image)
                                </div>
                              )}
                            </div>
                            <div className="p-2.5 text-sm font-medium" style={{ color: textCol }}>
                              {c.label}
                            </div>
                          </Link>
                        ))}
                      </div>
                    </div>
                  </div>
                );
              }
              return (
                <Link
                  key={`${n.label}-${idx}`}
                  to={n.href}
                  data-testid={`nav-${n.label.toLowerCase()}`}
                  className="text-[14px] font-medium tracking-[0.01em] relative py-2 after:absolute after:left-1/2 after:-translate-x-1/2 after:bottom-0 after:h-[1.5px] after:w-0 after:bg-current after:transition-all after:duration-300 hover:after:w-full"
                  style={{ color: textCol }}
                >
                  {n.label}
                </Link>
              );
            })}
          </nav>

          {/* RIGHT — Actions */}
          <div className="flex items-center gap-2">
            <form onSubmit={onSearch} className="hidden xl:flex relative">
              <MagnifyingGlass size={16} className="absolute left-3 top-1/2 -translate-y-1/2" style={{ color: "#78716C" }} />
              <input
                value={searchQ}
                onChange={(e) => setSearchQ(e.target.value)}
                placeholder={t(lang, "search_placeholder")}
                data-testid="header-search"
                className="h-11 pl-9 pr-3 w-48 rounded-full border text-sm focus:outline-none focus:ring-1 focus:ring-neutral-400"
                style={{ borderColor: "#E7E5E4", background: "#fff", color: textCol }}
              />
            </form>
            {/* Search icon only (smaller screens) */}
            <button
              type="button"
              onClick={() => navigate(`${shopRoot}/search`)}
              className="xl:hidden w-11 h-11 min-w-[44px] min-h-[44px] rounded-full border flex items-center justify-center hover:bg-neutral-50 active:scale-95 transition-transform"
              style={{ borderColor: "#E7E5E4" }}
              data-testid="header-search-icon"
              aria-label={t(lang, "search_placeholder")}
            >
              <MagnifyingGlass size={18} style={{ color: textCol }} />
            </button>

            <Link
              to={customer ? `${shopRoot}/account` : `${shopRoot}/account/login`}
              data-testid="header-account"
              className="w-11 h-11 min-w-[44px] min-h-[44px] rounded-full border bg-white hover:bg-neutral-50 flex items-center justify-center transition active:scale-95"
              style={{ borderColor: "#E7E5E4" }}
              title={customer ? `${customer.first_name} ${customer.last_name}` : t(lang, "footer_login")}
              aria-label={customer ? t(lang, "footer_my_account") : t(lang, "footer_login")}
            >
              <User size={18} weight="regular" style={{ color: textCol }} />
            </Link>

            <button
              type="button"
              onClick={() => window.dispatchEvent(new Event("cf_cart_open"))}
              data-testid="cart-button"
              aria-label={t(lang, "cart")}
              className="relative w-11 h-11 min-w-[44px] min-h-[44px] rounded-full border bg-white hover:bg-neutral-50 flex items-center justify-center transition active:scale-95"
              style={{ borderColor: "#E7E5E4" }}
            >
              <ShoppingBag size={20} weight="regular" style={{ color: textCol }} />
              {cartCount > 0 && (
                <span
                  data-testid="cart-count"
                  className="absolute -top-1.5 -right-1.5 min-w-[22px] h-[22px] rounded-full text-white text-[11px] font-semibold flex items-center justify-center px-1.5 border-2 border-white"
                  style={{ background: primary }}
                >
                  {cartCount}
                </span>
              )}
            </button>

            {/* Mobile menu toggle (kept as a safety — hidden because desktop layout is >=lg only) */}
          </div>
        </div>
      </header>

      {/* ================= MOBILE MENU ================= */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 lg:hidden" data-testid="mobile-menu">
          <div className="absolute inset-0 bg-black/50" onClick={() => setMobileOpen(false)} />
          <div className="absolute top-0 left-0 w-[86%] max-w-sm h-full bg-white shadow-2xl flex flex-col animate-in slide-in-from-left">
            <div className="flex items-center justify-between p-5 border-b" style={{ borderColor: "#E7E5E4" }}>
              <div className="font-semibold text-lg" style={{ fontFamily: `"${fontHeading}", serif`, color: textCol }}>
                {logoText}
              </div>
              <button
                onClick={() => setMobileOpen(false)}
                className="w-10 h-10 min-w-[44px] min-h-[44px] rounded-full hover:bg-neutral-50 flex items-center justify-center active:scale-95 transition-transform"
                data-testid="mobile-menu-close"
                aria-label={t(lang, "close")}
              >
                <X size={20} style={{ color: textCol }} />
              </button>
            </div>
            <form onSubmit={onSearch} className="p-5 border-b" style={{ borderColor: "#E7E5E4" }}>
              <div className="relative">
                <MagnifyingGlass size={16} className="absolute left-4 top-1/2 -translate-y-1/2" style={{ color: "#78716C" }} />
                <input
                  value={searchQ}
                  onChange={(e) => setSearchQ(e.target.value)}
                  placeholder={t(lang, "search_placeholder")}
                  className="h-12 w-full pl-11 pr-4 rounded-full border text-sm focus:outline-none"
                  style={{ borderColor: "#E7E5E4" }}
                  data-testid="mobile-search"
                />
              </div>
            </form>
            <Link
              to={customer ? `${shopRoot}/account` : `${shopRoot}/account/login`}
              onClick={() => setMobileOpen(false)}
              data-testid="mobile-account"
              className="mx-5 my-3 flex items-center justify-between p-4 rounded-2xl border transition hover:bg-neutral-50"
              style={{ borderColor: "#E7E5E4" }}
            >
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full flex items-center justify-center shrink-0"
                  style={{ background: accent }}>
                  <User size={18} weight="regular" style={{ color: textCol }} />
                </div>
                <div>
                  <div className="text-sm font-semibold" style={{ color: textCol }}>
                    {customer ? (customer.first_name || t(lang, "footer_my_account")) : t(lang, "footer_login")}
                  </div>
                  <div className="text-xs opacity-60" style={{ color: textCol }}>
                    {customer ? t(lang, "account_subtitle_customer") : t(lang, "account_subtitle_guest")}
                  </div>
                </div>
              </div>
              <CaretRight size={14} style={{ color: "#A8A29E" }} />
            </Link>
            <nav className="flex-1 overflow-y-auto py-2">
              {nav.map((n, idx) => {
                const isMega = n.type === "mega" && Array.isArray(n.children) && n.children.length > 0;
                if (isMega) {
                  return (
                    <details key={`${n.label}-${idx}`} className="group border-b" style={{ borderColor: "#F5F2EB" }}>
                      <summary
                        data-testid={`mobile-nav-mega-${n.label.toLowerCase()}`}
                        className="flex items-center justify-between px-6 py-4 text-base font-medium cursor-pointer hover:bg-neutral-50 list-none"
                        style={{ color: textCol }}
                      >
                        {n.label}
                        <CaretRight
                          size={16}
                          className="transition-transform group-open:rotate-90"
                          style={{ color: "#A8A29E" }}
                        />
                      </summary>
                      <div className="grid grid-cols-2 gap-2 p-4 pt-0 bg-neutral-50/60">
                        {n.children.map((c, i) => (
                          <Link
                            key={i}
                            to={rewriteHref(c.href)}
                            onClick={() => setMobileOpen(false)}
                            data-testid={`mobile-mega-card-${i}`}
                            className="block rounded-xl border bg-white overflow-hidden"
                            style={{ borderColor: "#E7E5E4" }}
                          >
                            <div className="aspect-[4/3] bg-neutral-100 overflow-hidden">
                              {c.image && (
                                <img src={c.image} alt={c.label} className="w-full h-full object-cover" />
                              )}
                            </div>
                            <div className="p-2 text-xs font-medium truncate" style={{ color: textCol }}>
                              {c.label}
                            </div>
                          </Link>
                        ))}
                      </div>
                    </details>
                  );
                }
                return (
                  <Link
                    key={`${n.label}-${idx}`}
                    to={n.href}
                    onClick={() => setMobileOpen(false)}
                    data-testid={`mobile-nav-${n.label.toLowerCase()}`}
                    className="flex items-center justify-between px-6 py-4 text-base font-medium border-b transition hover:bg-neutral-50 min-h-[56px]"
                    style={{ color: textCol, borderColor: "#F5F2EB" }}
                  >
                    {n.label}
                    <CaretRight size={16} style={{ color: "#A8A29E" }} />
                  </Link>
                );
              })}
            </nav>
            <div className="p-5 border-t text-sm flex flex-col gap-2" style={{ borderColor: "#E7E5E4", color: "#57534E" }}>
              <a href={`mailto:${contactEmail}`} className="flex items-center gap-2 hover:opacity-70">
                <EnvelopeSimple size={16} /> {contactEmail}
              </a>
              <a href={`tel:${contactPhone.replace(/\s/g, "")}`} className="flex items-center gap-2 hover:opacity-70">
                <Phone size={16} /> {contactPhone}
              </a>
            </div>
          </div>
        </div>
      )}

      {/* ================= MAIN ================= */}
      <main className="flex-1">{children}</main>

      <CartDrawer design={design} />

      {/* Reassurance band — gray cards, above footer */}
      <section
        className="mt-24 bg-white"
        style={{ borderTop: "1px solid #E5E5E5", borderBottom: "1px solid #E5E5E5" }}
        data-testid="reassurance-band"
      >
        <div className="max-w-7xl mx-auto px-6 py-10 grid grid-cols-2 md:grid-cols-4 gap-6">
          {[
            { Icon: Truck,       title: t(lang, "trust_free_shipping"),  sub: { fr: "Partout en Europe", en: "Throughout Europe", de: "In ganz Europa", nl: "In heel Europa", it: "In tutta Europa", es: "Por toda Europa" }[lang] || "" },
            { Icon: ShieldCheck, title: t(lang, "trust_secure_payment"), sub: "CB, PayPal, Virement" },
            { Icon: Phone,       title: t(lang, "trust_human_service"),  sub: t(lang, "support_seniors") },
            { Icon: CreditCard,  title: t(lang, "trust_returns_14d"),    sub: { fr: "Satisfait ou remboursé", en: "Satisfied or refunded", de: "Zufrieden oder Geld zurück", nl: "Tevreden of geld terug", it: "Soddisfatti o rimborsati", es: "Satisfecho o reembolsado" }[lang] || "" },
          ].map((b, i) => (
            <div
              key={i}
              className="flex items-start gap-3 p-5"
              style={{ background: "#F5F5F5", borderRadius: "2px" }}
              data-testid={`footer-reassurance-${i}`}
            >
              <b.Icon size={22} weight="thin" style={{ color: "#0A0A0A" }} />
              <div>
                <div className="text-[13px] font-semibold" style={{ color: "#0A0A0A" }}>{b.title}</div>
                <div className="text-[12px] mt-0.5" style={{ color: "#737373" }}>{b.sub}</div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ================= FOOTER — Premium with site's own image ================= */}
      <footer
        className="pb-[env(safe-area-inset-bottom)] relative overflow-hidden"
        data-testid="storefront-footer"
      >
        {/* Background image — use site's hero image or first product image */}
        <div className="absolute inset-0">
          {footerBgImage ? (
            <img
              alt=""
              aria-hidden="true"
              className="w-full h-full object-cover"
              src={footerBgImage}
            />
          ) : (
            <div className="w-full h-full" style={{ background: "linear-gradient(135deg, #1a1a1a, #2a2a2a)" }} />
          )}
          <div className="absolute inset-0" style={{ background: "rgba(10, 10, 10, 0.78)" }} />
        </div>

        {/* Main footer columns — newsletter + 4 link groups */}
        <div className="relative z-10 max-w-7xl mx-auto px-6 pt-16 md:pt-20 pb-10 md:pb-14">
          <div className="grid grid-cols-1 lg:grid-cols-[1fr_1.4fr] gap-16 lg:gap-20">
            {/* Newsletter + Logo */}
            <div>
              {/* Brand logo — Fraunces text in white for guaranteed legibility on dark overlay.
                  The uploaded image logo is NOT used here because it may be dark on
                  transparent background (would be invisible) or already white (would
                  clash). Fraunces text always works. */}
              <div
                className="mb-8 text-[26px] md:text-[30px] font-semibold text-white leading-none"
                style={{ fontFamily: `"${fontHeading}", serif` }}
                data-testid="footer-brand-logo"
              >
                {logoText}
              </div>

              <h2
                data-testid="footer-newsletter-title"
                className="font-light text-white leading-[1.1] tracking-[-0.03em] mb-6"
                style={{ fontSize: "clamp(2rem, 4.2vw, 3.2rem)", fontFamily: `"${fontHeading}", serif` }}
              >
                {t(lang, "newsletter_title_line1")}<br />{t(lang, "newsletter_title_line2")}
              </h2>
              <p className="text-[14px] md:text-[15px] text-white/50 leading-[1.7] max-w-md mb-10">
                {t(lang, "newsletter_lead")}
              </p>
              <form
                data-testid="footer-newsletter-form"
                onSubmit={(e) => { e.preventDefault(); }}
                className="flex items-end gap-4 mb-4 max-w-md"
              >
                <div className="flex-1">
                  <input
                    placeholder={t(lang, "newsletter_placeholder")}
                    data-testid="footer-email-input"
                    className="w-full bg-transparent text-white text-[14px] placeholder:text-white/30 pb-3 border-b border-white/25 focus:border-white/60 outline-none transition-colors"
                    type="email"
                  />
                </div>
                <button
                  type="submit"
                  data-testid="footer-subscribe-btn"
                  className="group flex items-center gap-2.5 px-6 py-2.5 rounded-full glass-card text-white text-[13px] font-medium tracking-wide uppercase hover:bg-white/20 transition-all"
                >
                  {t(lang, "newsletter_subscribe")}
                  <span className="w-1.5 h-1.5 rounded-full bg-white group-hover:scale-125 transition-transform" />
                </button>
              </form>
              <p className="text-[12px] text-white/30 max-w-md">
                {t(lang, "newsletter_consent_prefix")}{" "}
                <Link to={`${shopRoot}/confidentialite`} className="text-white/60 underline underline-offset-2 hover:text-white/80 transition-colors">
                  {t(lang, "newsletter_consent_link")}.
                </Link>
              </p>

              {/* Contact infos */}
              <div className="mt-10 space-y-2 text-[13.5px]">
                <a href={`mailto:${contactEmail}`} className="flex items-center gap-2 text-white/70 hover:text-white transition">
                  <EnvelopeSimple size={14} /> {contactEmail}
                </a>
                <a href={`tel:${contactPhone.replace(/\s/g, "")}`} className="flex items-center gap-2 text-white/70 hover:text-white transition">
                  <Phone size={14} /> {contactPhone} · {contactHours}
                </a>
                {contactAddress && (
                  <div className="flex items-start gap-2 text-white/55">
                    <MapPin size={14} className="mt-0.5 shrink-0" /> <span>{contactAddress}</span>
                  </div>
                )}
              </div>

              {/* Social icons */}
              <div className="flex items-center gap-4 mt-6" data-testid="footer-social">
                {social.instagram && (
                  <a href={social.instagram} target="_blank" rel="noreferrer" className="text-white/40 hover:text-white transition-colors" aria-label="Instagram">
                    <InstagramLogo size={20} weight="regular" />
                  </a>
                )}
                {social.facebook && (
                  <a href={social.facebook} target="_blank" rel="noreferrer" className="text-white/40 hover:text-white transition-colors" aria-label="Facebook">
                    <FacebookLogo size={20} weight="regular" />
                  </a>
                )}
                {social.linkedin && (
                  <a href={social.linkedin} target="_blank" rel="noreferrer" className="text-white/40 hover:text-white transition-colors" aria-label="LinkedIn">
                    <LinkedinLogo size={20} weight="regular" />
                  </a>
                )}
                {social.youtube && (
                  <a href={social.youtube} target="_blank" rel="noreferrer" className="text-white/40 hover:text-white transition-colors" aria-label="YouTube">
                    <YoutubeLogo size={20} weight="regular" />
                  </a>
                )}
                {!social.instagram && !social.facebook && !social.linkedin && !social.youtube && (
                  <>
                    <span className="text-white/40" aria-label="Instagram"><InstagramLogo size={20} /></span>
                    <span className="text-white/40" aria-label="Facebook"><FacebookLogo size={20} /></span>
                    <span className="text-white/40" aria-label="LinkedIn"><LinkedinLogo size={20} /></span>
                  </>
                )}
              </div>
            </div>

            {/* Right column: 4 link groups */}
            <div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-x-8 gap-y-10">
                <FooterCol
                  title={t(lang, "footer_col_shop")}
                  items={[
                    { label: t(lang, "footer_all_products"),  href: `${shopRoot}` },
                    { label: t(lang, "nav_collections"),      href: `${shopRoot}/collections` },
                    { label: t(lang, "footer_new_arrivals"),  href: `${shopRoot}?sort=new` },
                    { label: t(lang, "footer_bestsellers"),   href: `${shopRoot}?sort=bestsellers` },
                  ]}
                />
                <FooterCol
                  title={t(lang, "footer_col_about")}
                  items={[
                    { label: t(lang, "footer_our_story"),     href: `${shopRoot}/about` },
                    { label: t(lang, "nav_journal"),          href: `${shopRoot}/blog` },
                    { label: t(lang, "footer_press"),         href: `${shopRoot}#press` },
                    { label: t(lang, "nav_contact"),          href: `${shopRoot}/contact` },
                  ]}
                />
                <FooterCol
                  title={t(lang, "footer_col_service")}
                  items={[
                    { label: t(lang, "section_faq"),          href: `${shopRoot}#faq` },
                    { label: t(lang, "shipping"),             href: `${shopRoot}/livraison` },
                    { label: t(lang, "footer_returns"),       href: `${shopRoot}/retours` },
                    { label: t(lang, "footer_track_order"),   href: `${shopRoot}/track` },
                    { label: customer ? t(lang, "footer_my_account") : t(lang, "footer_login"),
                      href: customer ? `${shopRoot}/account` : `${shopRoot}/account/login` },
                  ]}
                />
                <FooterCol
                  title={t(lang, "footer_col_legal")}
                  items={footerLinks.length > 0 ? footerLinks : [
                    { label: "CGV",                           href: `${shopRoot}/cgv` },
                    { label: t(lang, "footer_legal_notice"),  href: `${shopRoot}/mentions` },
                    { label: t(lang, "footer_privacy"),       href: `${shopRoot}/confidentialite` },
                    { label: t(lang, "footer_cookies"),       href: `${shopRoot}/cookies` },
                  ]}
                />
              </div>
            </div>
          </div>
        </div>

        {/* Divider hairline */}
        <div className="relative z-10 max-w-7xl mx-auto px-6">
          <div className="h-px bg-white/10" />
        </div>

        {/* Bottom bar — copyright + payments */}
        <div className="relative z-10 max-w-7xl mx-auto px-6 py-8">
          <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-8">
            <p data-testid="footer-copyright" className="text-[12px] text-white/40">
              © {new Date().getFullYear()} {logoText} — {t(lang, "footer_all_rights")}.
            </p>
            <div>
              <p className="text-[11px] font-medium uppercase tracking-[0.15em] text-white/30 mb-3">{t(lang, "trust_secure_payment")}</p>
              <div className="flex items-center gap-2.5 flex-wrap" data-testid="footer-payments">
                {["Visa", "Mastercard", "CB", "PayPal", "Apple Pay", "iDEAL", "Bancontact"].map((p) => (
                  <span
                    key={p}
                    className="h-8 px-2.5 glass-card flex items-center justify-center text-[11px] font-medium text-white/80"
                    style={{ borderRadius: "6px" }}
                  >
                    {p}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}

function FooterCol({ title, items }) {
  return (
    <div>
      <p className="text-[11px] font-medium uppercase tracking-[0.2em] text-white/40 mb-6">
        {title}
      </p>
      <div className="flex flex-col gap-4">
        {items.map((it, i) => (
          <Link
            key={i}
            to={it.href}
            className="text-[14px] text-white/60 hover:text-white transition-colors"
          >
            {it.label}
          </Link>
        ))}
      </div>
    </div>
  );
}

export async function fetchPublicSite(identifier) {
  // Phase 4 fix-up : l'identifier peut être soit un UUID, soit un slug humain
  // (ex: `demo-altiaro`). On route vers le bon endpoint backend.
  const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
  const path = UUID_RE.test(identifier)
    ? `/api/public/sites/${identifier}`
    : `/api/public/sites/by-slug/${encodeURIComponent(identifier)}`;
  const { data } = await axios.get(`${BACKEND_URL}${path}`);
  return data;
}

export function useSiteData(siteId) {
  const [site, setSite] = useState(null);
  useEffect(() => {
    if (!siteId) return;
    fetchPublicSite(siteId).then(setSite).catch(() => setSite(null));
  }, [siteId]);
  return site;
}
