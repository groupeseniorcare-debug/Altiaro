import React, { useEffect, useState } from "react";
import { ShoppingBag, CheckCircle } from "@phosphor-icons/react";
import { pickLang, t } from "../../lib/i18n";
import { formatPrice } from "./storefrontUtils";

/**
 * Mobile sticky buy bar — apparaît au scroll quand le CTA principal sort du viewport.
 * Visible uniquement sur mobile (< md).
 */
export default function MobileStickyBuy({ product, onAdd, qty, added, design, lang }) {
  const [visible, setVisible] = useState(false);
  const primary = design?.brand?.primary_color || "#B84B31";

  useEffect(() => {
    const handler = () => {
      // Show when user has scrolled past ~600px
      setVisible(window.scrollY > 600);
    };
    window.addEventListener("scroll", handler, { passive: true });
    handler();
    return () => window.removeEventListener("scroll", handler);
  }, []);

  if (!visible || !product) return null;

  return (
    <div
      className="md:hidden fixed bottom-0 left-0 right-0 z-50 bg-white/90 backdrop-blur-xl border-t shadow-2xl px-4 py-3 pb-[calc(0.75rem+env(safe-area-inset-bottom))] flex items-center gap-3 animate-in slide-in-from-bottom"
      style={{ borderColor: "#E7E5E4" }}
      data-testid="mobile-sticky-buy"
    >
      {product.images?.[0] && (
        <img
          src={product.images[0]}
          alt={pickLang(product.name, lang) || product.name}
          className="w-12 h-12 rounded-lg object-cover shrink-0"
          loading="lazy"
        />
      )}
      <div className="flex-1 min-w-0">
        <div className="text-xs text-neutral-500 truncate">
          {pickLang(product.name, lang) || product.name}
        </div>
        <div className="flex items-baseline gap-2">
          <span className="text-base font-semibold" style={{ color: primary }}>
            {formatPrice(product.price, product.currency, lang)}
          </span>
          {product.compare_at_price && product.compare_at_price > product.price && (
            <span className="text-xs line-through text-neutral-400">
              {formatPrice(product.compare_at_price, product.currency, lang)}
            </span>
          )}
        </div>
      </div>
      <button
        type="button"
        onClick={onAdd}
        data-testid="sticky-buy-cta"
        className="h-12 min-h-[48px] px-5 rounded-full text-white font-semibold text-sm transition active:scale-[0.97] shrink-0 shadow-lg"
        style={{ background: added ? "#047857" : primary }}
      >
        {added ? (
          <span className="flex items-center gap-1.5">
            <CheckCircle size={16} weight="fill" /> Ajouté
          </span>
        ) : (
          <span className="flex items-center gap-1.5">
            <ShoppingBag size={16} />
            {t(lang, "add_to_cart")}
          </span>
        )}
      </button>
    </div>
  );
}
