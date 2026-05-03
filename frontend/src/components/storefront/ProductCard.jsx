/**
 * Lot G Fix 12 (CORRIGÉ) — Card produit RICHE unifiée, source de vérité unique
 * pour la Home, les Collections, le Search, les Cross-sells, les futurs sites
 * créés par le pipeline.
 *
 * 🚨 Incident historique : la 1ʳᵉ tentative du Fix G12 avait inversé la logique
 * (cards simples Collection appliquées à la Home, ce qui appauvrissait la Home).
 * Cette version restaure le rendu RICHE de la Home et le propage à toutes
 * les pages produits.
 *
 * Design (Aesop / Hermès / Apple Watch) :
 *   ┌────────────────────────────┐
 *   │ aspect-square (image AI)   │  ← badges featured ⭐ / promo −X%
 *   ├────────────────────────────┤
 *   │ Titre Cormorant            │
 *   │ ✓ Highlight 1              │
 *   │ ✓ Highlight 2              │
 *   │ ✓ Highlight 3              │
 *   │ ✓ Highlight 4              │
 *   │ ──────────────────────     │
 *   │ Prix XL · "Livraison off." │  → [Voir] [+ panier]
 *   └────────────────────────────┘
 *
 * Modes :
 *   variant="default"   → rendu riche complet (Home, Collection, Search)
 *   variant="compact"   → mini-card sans CTA (cross-sell, bundle sidebar)
 *
 * Le composant ne fournit PAS de grid : c'est la responsabilité du parent.
 */
import React, { useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import {
  Check,
  ShoppingBagOpen,
  Star,
  ArrowRight,
  CheckCircle,
} from "@phosphor-icons/react";
import { pickLang, t } from "../../lib/i18n";
import { productPath, shopPath } from "../../lib/shopUrls";
import { designAccents, formatPrice } from "./storefrontUtils";
import { addToCart } from "../../lib/cart";
import { getPrimaryImage } from "../../lib/productImage";

/**
 * Extrait 3-4 "highlights" courts (bullet points) d'un produit.
 * Priorité : product.highlights → product.key_benefits → product.attributes → générique.
 */
export function getHighlights(p, lang) {
  const raw = p.highlights || p.key_benefits || p.bullets || [];
  const list = raw
    .map((h) => (typeof h === "string" ? h : pickLang(h, lang) || h?.fr || ""))
    .filter(Boolean);
  if (list.length >= 2) return list.slice(0, 4);
  // Fallback : attributs ("Matière : cuir", "Couleur : gris") → 4 max
  const attrs = Array.isArray(p.attributes) ? p.attributes : [];
  if (attrs.length) {
    return attrs
      .slice(0, 4)
      .map((a) => (a.label && a.value ? `${a.label} : ${a.value}` : a.value || a.label))
      .filter(Boolean);
  }
  // Fallback ultime : USPs génériques marque
  const generic = [];
  if (p.compare_at_price && p.compare_at_price > p.price) {
    const valueLabel = {
      fr: "Bon rapport qualité/prix",
      en: "Great value",
      de: "Gutes Preis-Leistungs-Verhältnis",
      nl: "Goede prijs-kwaliteitverhouding",
      it: "Ottimo rapporto qualità-prezzo",
      es: "Buena relación calidad-precio",
    }[lang] || "Bon rapport qualité/prix";
    generic.push(valueLabel);
  }
  generic.push(t(lang, "free_shipping_72h"));
  generic.push(t(lang, "trust_warranty_2y"));
  generic.push(t(lang, "trust_returns_14d"));
  return generic.slice(0, 4);
}

export default function ProductCard({
  product,
  siteId,
  lang = "fr",
  design,
  variant = "default", // "default" (rich) | "compact" (no CTA)
  hasReal = true,      // false → DEMO mode (lien vers /shop/{id} au lieu de produit)
  testId,
  href, // override URL
}) {
  const [added, setAdded] = useState(false);
  if (!product) return null;
  const { primary, accent, divider, textMuted, textFaint, fontHeading } = designAccents(design);
  const p = product;

  const name = pickLang(p.name, lang) || p.name || "—";
  const url = href || (hasReal ? productPath(siteId, p) : shopPath(siteId));
  const imageSrc = getPrimaryImage(p);
  const isFeatured = !!p.featured;
  const hasPromo = !!p.compare_at_price && p.compare_at_price > p.price;
  const promoPct = hasPromo ? Math.round((1 - p.price / p.compare_at_price) * 100) : 0;
  const isCompact = variant === "compact";
  const highlights = isCompact ? [] : getHighlights(p, lang);

  const onAdd = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (!hasReal) return;
    addToCart(siteId, p, lang, 1);
    setAdded(true);
    window.dispatchEvent(new Event("cf_cart_open"));
    setTimeout(() => setAdded(false), 1800);
  };

  // ─── Variante COMPACT (cross-sell, bundle) ────────────────────────────
  if (isCompact) {
    return (
      <Link
        to={url}
        data-testid={testId || `product-card-compact-${p.id}`}
        className="group block focus:outline-none focus-visible:ring-2 focus-visible:ring-neutral-400 focus-visible:ring-offset-2"
      >
        <div className="aspect-square relative overflow-hidden bg-[#F5F2EB] rounded-xl mb-3">
          {imageSrc ? (
            <img
              src={imageSrc}
              alt={name}
              loading="lazy"
              className="absolute inset-0 w-full h-full object-cover transition-transform duration-700 ease-out group-hover:scale-[1.04]"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center" style={{ color: textFaint }}>
              <ShoppingBagOpen size={44} weight="thin" />
            </div>
          )}
          {isFeatured && (
            <div
              className="absolute top-3 left-3 bg-white/95 backdrop-blur-sm px-2 py-1 text-[9px] uppercase tracking-[0.22em] font-semibold rounded-full flex items-center gap-1"
              style={{ color: primary }}
            >
              <Star size={9} weight="fill" style={{ color: "#F5B800" }} /> {t(lang, "featured")}
            </div>
          )}
        </div>
        <div className="text-[14px] md:text-[15px] leading-tight tracking-tight line-clamp-2"
             style={{ fontFamily: `"${fontHeading}", serif`, fontWeight: 500, color: "#1a1a1a" }}>
          {name}
        </div>
        <div className="flex items-baseline gap-2 mt-1.5">
          <span className="text-[14px] md:text-[15px] font-semibold tabular-nums" style={{ color: primary }}>
            {formatPrice(p.price, p.currency, lang)}
          </span>
          {hasPromo && (
            <span className="text-[12px] line-through tabular-nums" style={{ color: textFaint }}>
              {formatPrice(p.compare_at_price, p.currency, lang)}
            </span>
          )}
        </div>
      </Link>
    );
  }

  // ─── Variante DEFAULT (riche, Home + Collection + Search) ────────────
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-60px" }}
      transition={{ duration: 0.5 }}
      className="group"
      data-testid={testId || `product-card-${p.id}`}
    >
      <div
        className="relative overflow-hidden transition-all duration-500 hover:shadow-[0_20px_60px_-20px_rgba(0,0,0,0.18)] hover:-translate-y-1 flex flex-col h-full"
        style={{ background: accent, borderRadius: "2px" }}
      >
        {/* Image — fond blanc pour faire ressortir le produit IA */}
        <Link to={url} className="block">
          <div className="aspect-square relative overflow-hidden bg-white">
            {imageSrc ? (
              <img
                src={imageSrc}
                alt={name}
                loading="lazy"
                className="absolute inset-0 w-full h-full object-cover transition-transform duration-700 ease-out group-hover:scale-[1.04]"
              />
            ) : (
              <div className="w-full h-full flex items-center justify-center" style={{ color: textFaint }}>
                <ShoppingBagOpen size={60} weight="thin" />
              </div>
            )}
            {/* Badge featured (top-left) */}
            {isFeatured && (
              <div
                className="absolute top-4 left-4 bg-white text-[10px] uppercase tracking-[0.22em] font-semibold px-2.5 py-1.5 flex items-center gap-1"
                style={{ borderRadius: "2px", color: primary }}
              >
                <Star size={10} weight="fill" style={{ color: "#F5B800" }} /> {t(lang, "featured")}
              </div>
            )}
            {/* Badge promo (top-right) */}
            {hasPromo && (
              <div
                className="absolute top-4 right-4 text-white text-[11px] font-semibold px-2.5 py-1 tracking-tight"
                style={{ background: primary, borderRadius: "2px" }}
              >
                −{promoPct}%
              </div>
            )}
          </div>
        </Link>

        {/* Body */}
        <div className="p-5 md:p-6 flex flex-col flex-1">
          <Link to={url} className="block">
            <div
              className="text-[16px] md:text-[18px] font-normal leading-snug tracking-tight line-clamp-2 min-h-[52px]"
              style={{ fontFamily: `"${fontHeading}", serif`, color: primary }}
            >
              {name}
            </div>
          </Link>

          {/* Highlights — 4 bullets premium quick-scan */}
          {highlights.length > 0 && (
            <ul className="mt-4 space-y-1.5" data-testid={`product-highlights-${p.id}`}>
              {highlights.slice(0, 4).map((h, i) => (
                <li
                  key={i}
                  className="flex items-start gap-2 text-[12.5px] leading-snug"
                  style={{ color: textMuted }}
                >
                  <Check
                    size={12}
                    weight="bold"
                    className="mt-[3px] shrink-0"
                    style={{ color: primary }}
                  />
                  <span className="line-clamp-1">{h}</span>
                </li>
              ))}
            </ul>
          )}

          {/* Price + dual CTA — pinned to bottom */}
          <div
            className="mt-auto pt-5 flex items-end justify-between gap-3"
            style={{ borderTop: `1px solid ${divider}`, marginTop: "1.25rem" }}
          >
            <div>
              <div className="flex items-baseline gap-2">
                <span className="text-[18px] font-semibold tabular-nums leading-none" style={{ color: primary }}>
                  {formatPrice(p.price, p.currency, lang)}
                </span>
                {hasPromo && (
                  <span className="text-[12px] line-through tabular-nums" style={{ color: textFaint }}>
                    {formatPrice(p.compare_at_price, p.currency, lang)}
                  </span>
                )}
              </div>
              <div className="text-[10px] uppercase tracking-[0.2em] mt-1.5" style={{ color: textFaint }}>
                {t(lang, "trust_free_shipping")}
              </div>
            </div>

            <div className="flex items-center gap-1.5">
              <Link
                to={url}
                title={t(lang, "product_view_detail")}
                aria-label={t(lang, "product_view_detail")}
                data-testid={`product-details-${p.id}`}
                className="w-11 h-11 border flex items-center justify-center transition hover:border-black"
                style={{ borderColor: divider, color: primary, borderRadius: "2px" }}
              >
                <ArrowRight size={15} weight="bold" />
              </Link>
              <button
                onClick={onAdd}
                disabled={added}
                data-testid={`product-add-to-cart-${p.id}`}
                className="h-11 px-4 text-white text-[12.5px] font-semibold flex items-center gap-2 transition-all hover:gap-2.5"
                style={{ background: primary, borderRadius: "2px" }}
              >
                {added ? (
                  <>
                    <CheckCircle size={14} weight="fill" /> {t(lang, "added_to_cart")}
                  </>
                ) : (
                  <>
                    {t(lang, "add_to_cart")}
                    <ShoppingBagOpen size={14} weight="bold" />
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
