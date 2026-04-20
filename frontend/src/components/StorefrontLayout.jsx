import React, { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import axios from "axios";
import { LANGUAGES, t } from "../lib/i18n";
import { readCart, cartTotals } from "../lib/cart";
import { ShoppingBag, Phone, ShieldCheck, Truck } from "@phosphor-icons/react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export default function StorefrontLayout({ children, lang, setLang, site }) {
  const { siteId } = useParams();
  const [cartCount, setCartCount] = useState(0);

  useEffect(() => {
    const update = () => setCartCount(cartTotals(readCart(siteId)).itemsCount);
    update();
    window.addEventListener("cf_cart_updated", update);
    return () => window.removeEventListener("cf_cart_updated", update);
  }, [siteId]);

  const shopRoot = `/shop/${siteId}`;

  return (
    <div className="min-h-screen flex flex-col bg-[#FDFBF7]" data-testid="storefront-layout">
      {/* Trust bar */}
      <div className="bg-[#1C1917] text-white text-[13px]">
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
            className="bg-transparent border border-white/20 rounded px-2 py-0.5 text-[12px] hover:bg-white/10 cursor-pointer outline-none"
          >
            {LANGUAGES.map((l) => (
              <option key={l.code} value={l.code} className="text-[#1C1917]">
                {l.flag} {l.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Header */}
      <header className="bg-white border-b border-[#E7E5E4] sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-6 py-5 flex items-center justify-between">
          <Link to={shopRoot} className="group" data-testid="shop-logo">
            <div className="font-heading text-2xl font-semibold text-[#1C1917] group-hover:text-[#B84B31] transition">
              {site?.name || "…"}
            </div>
            {site?.niche_data?.tagline && (
              <div className="text-xs text-[#78716C] mt-0.5 hidden md:block">
                {site.niche_data.tagline}
              </div>
            )}
          </Link>

          <Link
            to={`${shopRoot}/cart`}
            data-testid="cart-button"
            className="relative flex items-center gap-2 h-11 px-4 rounded-full bg-[#FDFBF7] hover:bg-[#F5F2EB] border border-[#E7E5E4] transition group"
          >
            <ShoppingBag size={20} weight="regular" className="text-[#1C1917]" />
            <span className="text-sm font-medium text-[#1C1917]">{t(lang, "cart")}</span>
            {cartCount > 0 && (
              <span
                data-testid="cart-count"
                className="absolute -top-1.5 -right-1.5 min-w-[22px] h-[22px] rounded-full bg-[#B84B31] text-white text-[11px] font-semibold flex items-center justify-center px-1.5"
              >
                {cartCount}
              </span>
            )}
          </Link>
        </div>
      </header>

      <main className="flex-1">{children}</main>

      <footer className="border-t border-[#E7E5E4] bg-white mt-20">
        <div className="max-w-6xl mx-auto px-6 py-8 text-center text-sm text-[#78716C]">
          <div className="font-heading text-lg text-[#1C1917] mb-2">{site?.name}</div>
          <div>
            © {new Date().getFullYear()} · {t(lang, "secure_checkout")} ·{" "}
            {t(lang, "support_seniors")}
          </div>
        </div>
      </footer>
    </div>
  );
}

export async function fetchPublicSite(siteId) {
  const { data } = await axios.get(`${BACKEND_URL}/api/public/sites/${siteId}`);
  return data;
}
