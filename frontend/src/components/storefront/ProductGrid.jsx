import React, { useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { Check, ShoppingBagOpen, Star, ArrowRight, CheckCircle } from "@phosphor-icons/react";
import { pickLang, t } from "../../lib/i18n";
import { designAccents, formatPrice } from "./storefrontUtils";
import { addToCart } from "../../lib/cart";
import { getPrimaryImage } from "../../lib/productImage";

const DEMO_PRODUCTS = [
  { id: "demo-1", name: "Fauteuil releveur Confort Plus", price: 899, compare_at_price: 1199, currency: "EUR", images: ["https://images.unsplash.com/photo-1555041469-a586c61ea9bc?w=700&auto=format&fit=crop"], featured: true,
    highlights: ["Moteur silencieux", "Inclinaison 160°", "Tissu anti-taches", "Garantie 3 ans"] },
  { id: "demo-2", name: "Déambulateur 4 roues ultra-léger", price: 149, currency: "EUR", images: ["https://images.unsplash.com/photo-1584515933487-779824d29309?w=700&auto=format&fit=crop"],
    highlights: ["Ultra-léger 6,4 kg", "Pliage en 2 sec", "Frein main", "Sac inclus"] },
  { id: "demo-3", name: "Matelas médical à mémoire de forme", price: 599, currency: "EUR", images: ["https://images.unsplash.com/photo-1505693416388-ac5ce068fe85?w=700&auto=format&fit=crop"],
    highlights: ["Mémoire haute densité", "Housse déhoussable", "Anti-escarres", "Hypoallergénique"] },
  { id: "demo-4", name: "Barres d'appui salle de bain (x2)", price: 59, currency: "EUR", images: ["https://images.unsplash.com/photo-1620626011761-996317b8d101?w=700&auto=format&fit=crop"],
    highlights: ["Charge 130 kg", "Acier inoxydable", "Montage facile", "Grip antidérapant"] },
  { id: "demo-5", name: "Pilulier électronique connecté", price: 79, compare_at_price: 99, currency: "EUR", images: ["https://images.unsplash.com/photo-1550572017-edd951b55104?w=700&auto=format&fit=crop"],
    highlights: ["28 cases", "Rappel sonore", "App mobile", "Batterie 6 mois"] },
  { id: "demo-6", name: "Téléphone senior à grosses touches", price: 89, currency: "EUR", images: ["https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=700&auto=format&fit=crop"],
    highlights: ["Touches XL", "Ampli volume 40 dB", "SOS programmable", "Prise en main simple"] },
];

/**
 * Extracts 3-4 short "highlights" (bullet points) from a product.
 * Priority: product.highlights → product.key_benefits → product.attributes → derived.
 */
function getHighlights(p, lang) {
  const raw = p.highlights || p.key_benefits || p.bullets || [];
  const list = raw
    .map((h) => (typeof h === "string" ? h : pickLang(h, lang) || h?.fr || ""))
    .filter(Boolean);
  if (list.length >= 2) return list.slice(0, 4);
  // Fall back to attributes (e.g. "Matière: cuir", "Couleur: gris") → first 3
  const attrs = Array.isArray(p.attributes) ? p.attributes : [];
  if (attrs.length) {
    return attrs
      .slice(0, 4)
      .map((a) => (a.label && a.value ? `${a.label} : ${a.value}` : a.value || a.label))
      .filter(Boolean);
  }
  // Derived generic premium promises — always works as a last resort
  const generic = [];
  if (p.compare_at_price && p.compare_at_price > p.price) {
    generic.push({ fr: "Bon rapport qualité/prix", en: "Great value", de: "Gutes Preis-Leistungs-Verhältnis", nl: "Goede prijs-kwaliteitverhouding", it: "Ottimo rapporto qualità-prezzo", es: "Buena relación calidad-precio" }[lang] || "Bon rapport qualité/prix");
  }
  generic.push(t(lang, "free_shipping_72h"));
  generic.push(t(lang, "trust_warranty_2y"));
  generic.push(t(lang, "trust_returns_14d"));
  return generic.slice(0, 4);
}

function ProductCard({ product: p, siteId, primary, accent, divider, textMuted, textFaint, fontHeading, hasReal, lang }) {
  const [added, setAdded] = useState(false);
  const highlights = getHighlights(p, lang);
  const href = hasReal ? `/shop/${siteId}/product/${p.id}` : `/shop/${siteId}`;

  const onAdd = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (!hasReal) return;
    addToCart(siteId, p, lang, 1);
    setAdded(true);
    window.dispatchEvent(new Event("cf_cart_open"));
    setTimeout(() => setAdded(false), 1800);
  };

  const name = pickLang(p.name, lang) || p.name;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-60px" }}
      transition={{ duration: 0.6 }}
      className="group"
      data-testid={`product-card-${p.id}`}
    >
      <div
        className="relative overflow-hidden transition-all duration-500 hover:shadow-[0_20px_60px_-20px_rgba(0,0,0,0.18)] hover:-translate-y-1 flex flex-col h-full"
        style={{ background: accent, borderRadius: "2px" }}
      >
        {/* Image */}
        <Link to={href} className="block">
          <div className="aspect-square relative overflow-hidden bg-white">
            {(() => { const _src = getPrimaryImage(p); return _src ? (
              <img
                src={_src}
                alt={name}
                loading="lazy"
                className="absolute inset-0 w-full h-full object-cover transition-transform duration-700 ease-out group-hover:scale-[1.04]"
              />
            ) : (
              <div className="w-full h-full flex items-center justify-center" style={{ color: textFaint }}>
                <ShoppingBagOpen size={60} weight="thin" />
              </div>
            ); })()}
            {/* Badges */}
            {p.featured && (
              <div
                className="absolute top-4 left-4 bg-white text-[10px] uppercase tracking-[0.22em] font-semibold px-2.5 py-1.5 flex items-center gap-1"
                style={{ borderRadius: "2px", color: primary }}
              >
                <Star size={10} weight="fill" style={{ color: "#F5B800" }} /> {t(lang, "featured")}
              </div>
            )}
            {p.compare_at_price && p.compare_at_price > p.price && (
              <div
                className="absolute top-4 right-4 text-white text-[11px] font-semibold px-2.5 py-1 tracking-tight"
                style={{ background: primary, borderRadius: "2px" }}
              >
                −{Math.round((1 - p.price / p.compare_at_price) * 100)}%
              </div>
            )}
          </div>
        </Link>

        {/* Body */}
        <div className="p-5 md:p-6 flex flex-col flex-1">
          <Link to={href} className="block">
            <div
              className="text-[16px] md:text-[18px] font-normal leading-snug tracking-tight line-clamp-2 min-h-[52px]"
              style={{ fontFamily: `"${fontHeading}", serif`, color: primary }}
            >
              {name}
            </div>
          </Link>

          {/* Highlights list — bullet checks, quick-scan premium vibes */}
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

          {/* Price + CTA row pinned to the bottom */}
          <div
            className="mt-auto pt-5 flex items-end justify-between gap-3"
            style={{ borderTop: `1px solid ${divider}`, marginTop: "1.25rem" }}
          >
            <div>
              <div className="flex items-baseline gap-2">
                <span className="text-[18px] font-semibold tabular-nums leading-none" style={{ color: primary }}>
                  {formatPrice(p.price, p.currency, lang)}
                </span>
                {p.compare_at_price && p.compare_at_price > p.price && (
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
                to={href}
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

export function ProductGrid({ siteId, products, loading, design, lang }) {
  const { primary, accent, divider, textMuted, textFaint, fontHeading } = designAccents(design);
  const hasReal = products && products.length > 0;
  const displayed = hasReal ? products : DEMO_PRODUCTS;

  return (
    <section id="products" className="max-w-7xl mx-auto px-6 md:px-10 py-24 md:py-36 bg-white" data-testid="products-section">
      <div className="flex items-end justify-between flex-wrap gap-6 mb-14 md:mb-20">
        <div>
          <div className="flex items-center gap-3 mb-5">
            <span className="h-px w-10" style={{ background: primary }} />
            <span className="text-[11px] uppercase tracking-[0.4em]" style={{ color: primary }}>
              {t(lang, "hero_edition")}
            </span>
          </div>
          <h2
            className="text-[40px] md:text-[56px] lg:text-[64px] leading-[1.02] tracking-[-0.02em]"
            style={{ fontFamily: `"${fontHeading}", serif`, color: primary }}
          >
            {t(lang, "our_collection")}.
          </h2>
        </div>
        <div className="text-[12px] uppercase tracking-[0.3em]" style={{ color: textMuted }}>
          {hasReal ? `${products.length} ${products.length > 1 ? t(lang, "product_references") : t(lang, "product_reference")}` : t(lang, "product_preview_template")}
        </div>
      </div>

      {loading ? (
        <div
          className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5 md:gap-6"
          data-testid="products-grid-skeleton"
          aria-busy="true"
          aria-label="Chargement des produits"
        >
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="animate-pulse" style={{ background: accent, borderRadius: "2px" }}>
              <div className="aspect-square bg-stone-200/60" />
              <div className="p-6">
                <div className="h-4 bg-stone-200/60 w-4/5 mb-3" />
                <div className="h-3 bg-stone-200/60 w-3/5 mb-1.5" />
                <div className="h-3 bg-stone-200/60 w-2/3 mb-1.5" />
                <div className="h-3 bg-stone-200/60 w-1/2" />
                <div className="h-10 bg-stone-200/60 mt-6" />
              </div>
            </div>
          ))}
        </div>
      ) : (() => {
        const n = displayed.length;
        let gridCls = "grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5 md:gap-6";
        let wrapCls = "";
        if (hasReal && n === 1) {
          gridCls = "grid grid-cols-1 gap-6";
          wrapCls = "max-w-md mx-auto";
        } else if (hasReal && n === 2) {
          gridCls = "grid grid-cols-1 sm:grid-cols-2 gap-5 md:gap-6";
          wrapCls = "max-w-3xl mx-auto";
        }
        return (
          <div className={wrapCls}>
            <div className={gridCls} data-testid="products-grid">
              {displayed.map((p) => (
                <ProductCard
                  key={p.id}
                  product={p}
                  siteId={siteId}
                  primary={primary}
                  accent={accent}
                  divider={divider}
                  textMuted={textMuted}
                  textFaint={textFaint}
                  fontHeading={fontHeading}
                  hasReal={hasReal}
                  lang={lang}
                />
              ))}
            </div>
          </div>
        );
      })()}
    </section>
  );
}
