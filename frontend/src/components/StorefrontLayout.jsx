import React, { useEffect, useState } from "react";
import { Link, useParams, useNavigate } from "react-router-dom";
import axios from "axios";
import { LANGUAGES, t } from "../lib/i18n";
import { readCart, cartTotals } from "../lib/cart";
import { getCustomer } from "../lib/customerAuth";
import CartDrawer from "./CartDrawer";
import { ShoppingBag, Phone, ShieldCheck, Truck, MagnifyingGlass, User } from "@phosphor-icons/react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export default function StorefrontLayout({ children, lang, setLang, site, design }) {
  const { siteId } = useParams();
  const navigate = useNavigate();
  const [cartCount, setCartCount] = useState(0);
  const [customer, setCustomer] = useState(() => (siteId ? getCustomer(siteId) : null));
  const [searchQ, setSearchQ] = useState("");

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
  const primary = brand.primary_color || "#B84B31";
  const accent = brand.accent_color || "#F5F2EB";
  const bg = brand.background_color || "#FDFBF7";
  const textCol = brand.text_color || "#1C1917";
  const fontHeading = brand.font_heading || "Fraunces";
  const fontBody = brand.font_body || "Inter";
  const logoUrl = brand.logo_url ? `${BACKEND_URL}${brand.logo_url}` : null;
  const logoText = brand.logo_text || site?.name || "…";
  const brandTaglineRaw = design?.brand?.tagline;
  const tagline = typeof brandTaglineRaw === "string"
    ? brandTaglineRaw
    : (brandTaglineRaw?.[lang] || brandTaglineRaw?.fr || site?.niche_data?.tagline);

  const footer = design?.footer;
  const footerTagline = (footer?.tagline?.[lang]) || (footer?.tagline?.fr);
  const footerCols = footer?.columns || [];

  const cssVars = {
    "--cf-primary": primary,
    "--cf-accent": accent,
    "--cf-bg": bg,
    "--cf-text": textCol,
    "--cf-font-heading": `"${fontHeading}", serif`,
    "--cf-font-body": `"${fontBody}", system-ui, sans-serif`,
  };

  // Google Fonts link for the chosen fonts (loaded once per page)
  const fontsQuery = encodeURIComponent(`${fontHeading}:wght@400;500;600;700|${fontBody}:wght@400;500;600`);

  return (
    <div
      className="storefront-root min-h-screen flex flex-col"
      style={{ ...cssVars, background: bg, color: textCol, fontFamily: `"${fontBody}", system-ui, sans-serif` }}
      data-testid="storefront-layout"
    >
      <link rel="stylesheet" href={`https://fonts.googleapis.com/css2?family=${fontsQuery}&display=swap`} />
      {/* Trust bar */}
      <div className="text-neutral-900 text-[13px]" style={{ background: textCol }}>
        <div className="max-w-6xl mx-auto px-6 py-2 flex items-center justify-between flex-wrap gap-2">
          <div className="flex items-center gap-5">
            <span className="flex items-center gap-1.5">
              <Truck size={14} weight="bold" /> {t(lang, "free_shipping_above")}
            </span>
            <span className="hidden md:flex items-center gap-1.5">
              <ShieldCheck size={14} weight="bold" /> {t(lang, "secure_checkout")}
            </span>
            <span className="hidden md:flex items-center gap-1.5">
              <Phone size={14} weight="bold" /> {t(lang, "support_seniors")}
            </span>
          </div>
          <select
            value={lang}
            onChange={(e) => setLang(e.target.value)}
            data-testid="lang-switcher"
            className="bg-transparent border border-neutral-900/20 rounded px-2 py-0.5 text-[12px] hover:bg-neutral-900/10 cursor-pointer outline-none"
          >
            {LANGUAGES.map((l) => (
              <option key={l.code} value={l.code} style={{ color: textCol }}>
                {l.flag} {l.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Header */}
      <header className="bg-white border-b sticky top-0 z-10" style={{ borderColor: "#E7E5E4" }}>
        <div className="max-w-6xl mx-auto px-6 py-5 flex items-center justify-between">
          <Link to={shopRoot} className="group flex items-center gap-3" data-testid="shop-logo">
            {logoUrl && (
              <img
                src={logoUrl}
                alt={logoText}
                className="w-11 h-11 rounded-lg object-cover border"
                style={{ borderColor: "#E7E5E4" }}
              />
            )}
            <div>
              <div
                className="font-semibold text-2xl leading-tight transition"
                style={{ fontFamily: `"${fontHeading}", serif`, color: textCol }}
              >
                <span className="group-hover:text-[var(--cf-primary)]">{logoText}</span>
              </div>
              {tagline && (
                <div className="text-xs mt-0.5 hidden md:block" style={{ color: "#78716C" }}>
                  {tagline}
                </div>
              )}
            </div>
          </Link>

          <div className="flex items-center gap-2">
            {/* Search */}
            <form onSubmit={(e) => { e.preventDefault(); if (searchQ.trim().length >= 2) navigate(`${shopRoot}/search?q=${encodeURIComponent(searchQ)}`); }}
              className="hidden md:flex relative">
              <MagnifyingGlass size={16} className="absolute left-3 top-1/2 -translate-y-1/2" style={{ color: "#78716C" }} />
              <input
                value={searchQ}
                onChange={(e) => setSearchQ(e.target.value)}
                placeholder="Rechercher…"
                data-testid="header-search"
                className="h-11 pl-9 pr-3 w-48 rounded-full border text-sm focus:outline-none focus:ring-1 focus:ring-neutral-400"
                style={{ borderColor: "#E7E5E4", background: "#fff", color: textCol }}
              />
            </form>
            {/* Account */}
            <Link
              to={customer ? `${shopRoot}/account` : `${shopRoot}/account/login`}
              data-testid="header-account"
              className="flex items-center gap-2 h-11 px-3 rounded-full border transition hover:bg-neutral-50"
              style={{ borderColor: "#E7E5E4" }}
              title={customer ? `${customer.first_name} ${customer.last_name}` : "Se connecter"}
            >
              <User size={18} weight="regular" style={{ color: textCol }} />
              <span className="text-sm font-medium hidden lg:inline" style={{ color: textCol }}>
                {customer ? (customer.first_name || "Mon compte") : "Se connecter"}
              </span>
            </Link>
            <button
              type="button"
              onClick={() => window.dispatchEvent(new Event("cf_cart_open"))}
              data-testid="cart-button"
              className="relative flex items-center gap-2 h-11 px-4 rounded-full border transition group"
              style={{ background: accent, borderColor: "#E7E5E4" }}
            >
              <ShoppingBag size={20} weight="regular" style={{ color: textCol }} />
              <span className="text-sm font-medium" style={{ color: textCol }}>{t(lang, "cart")}</span>
              {cartCount > 0 && (
                <span
                  data-testid="cart-count"
                  className="absolute -top-1.5 -right-1.5 min-w-[22px] h-[22px] rounded-full text-white text-[11px] font-semibold flex items-center justify-center px-1.5"
                  style={{ background: primary }}
                >
                  {cartCount}
                </span>
              )}
            </button>
          </div>
        </div>
      </header>

      <main className="flex-1">{children}</main>

      <CartDrawer design={design} />

      <footer className="border-t bg-white mt-20" style={{ borderColor: "#E7E5E4" }}>
        <div className="max-w-6xl mx-auto px-6 py-10 grid grid-cols-1 md:grid-cols-4 gap-8">
          <div className="md:col-span-1">
            <div
              className="font-semibold text-xl mb-1"
              style={{ fontFamily: `"${fontHeading}", serif`, color: textCol }}
            >
              {logoText}
            </div>
            {footerTagline && (
              <p className="text-sm mt-1" style={{ color: "#78716C" }}>
                {footerTagline}
              </p>
            )}
          </div>
          {footerCols.slice(0, 3).map((col, idx) => {
            const colTitle = col?.title?.[lang] || col?.title?.fr || "";
            return (
              <div key={idx}>
                <div className="text-[11px] uppercase tracking-widest mb-3" style={{ color: "#78716C" }}>
                  {colTitle}
                </div>
                <ul className="space-y-1.5">
                  {(col.links || []).map((lnk, i) => {
                    const label = lnk?.label?.[lang] || lnk?.label?.fr || "";
                    const href = lnk?.href?.startsWith("/shop") ? lnk.href : `${shopRoot}${lnk.href || ""}`;
                    return (
                      <li key={i}>
                        <Link to={href} className="text-sm hover:underline" style={{ color: textCol }}>
                          {label}
                        </Link>
                      </li>
                    );
                  })}
                </ul>
              </div>
            );
          })}
        </div>
        <div className="border-t py-6 text-center text-xs" style={{ borderColor: "#E7E5E4", color: "#78716C" }}>
          © {new Date().getFullYear()} {logoText} ·{" "}
          <Link to={`${shopRoot}/cgv`} className="hover:underline">CGV</Link> ·{" "}
          <Link to={`${shopRoot}/mentions`} className="hover:underline">Mentions légales</Link> ·{" "}
          <Link to={`${shopRoot}/confidentialite`} className="hover:underline">Confidentialité</Link>
        </div>
      </footer>
    </div>
  );
}

export async function fetchPublicSite(siteId) {  const { data } = await axios.get(`${BACKEND_URL}/api/public/sites/${siteId}`);
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
