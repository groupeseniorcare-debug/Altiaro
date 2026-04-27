/**
 * Lot G Fix 12 (CORRIGÉ) — ProductGrid réutilise désormais le composant
 * `ProductCard` riche extrait, source de vérité unique pour TOUTES les pages
 * produits du storefront. Plus de duplication de rendu inline.
 *
 * Ce composant gère :
 *   - le wrapper section (header éditorial, eyebrow, h2)
 *   - la grille responsive (1/2/3 cols)
 *   - le skeleton loading
 *   - les cas N=1 / N=2 (centrage compact)
 *   - les DEMO_PRODUCTS quand aucun produit réel n'est dispo
 */
import React from "react";
import { t } from "../../lib/i18n";
import { designAccents } from "./storefrontUtils";
import ProductCard from "./ProductCard";

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

export function ProductGrid({ siteId, products, loading, design, lang }) {
  const { primary, accent, textMuted, fontHeading } = designAccents(design);
  const hasReal = products && products.length > 0;
  const displayed = hasReal ? products : DEMO_PRODUCTS;

  return (
    <section
      id="products"
      className="max-w-7xl mx-auto px-6 md:px-10 py-24 md:py-36 bg-white"
      data-testid="products-section"
    >
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
          {hasReal
            ? `${products.length} ${products.length > 1 ? t(lang, "product_references") : t(lang, "product_reference")}`
            : t(lang, "product_preview_template")}
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
                  lang={lang}
                  design={design}
                  variant="default"
                  hasReal={hasReal}
                />
              ))}
            </div>
          </div>
        );
      })()}
    </section>
  );
}

export default ProductGrid;
