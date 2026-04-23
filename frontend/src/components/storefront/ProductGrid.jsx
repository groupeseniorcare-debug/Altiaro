import React from "react";
import { Link } from "react-router-dom";
import { ShoppingBagOpen, Star } from "@phosphor-icons/react";
import { pickLang, t } from "../../lib/i18n";
import { designAccents, formatPrice } from "./storefrontUtils";

const DEMO_PRODUCTS = [
  { id: "demo-1", name: "Fauteuil releveur Confort Plus", price: 899, compare_at_price: 1199, currency: "EUR", images: ["https://images.unsplash.com/photo-1555041469-a586c61ea9bc?w=700&auto=format&fit=crop"], featured: true },
  { id: "demo-2", name: "Déambulateur 4 roues ultra-léger", price: 149, currency: "EUR", images: ["https://images.unsplash.com/photo-1584515933487-779824d29309?w=700&auto=format&fit=crop"] },
  { id: "demo-3", name: "Matelas médical à mémoire de forme", price: 599, currency: "EUR", images: ["https://images.unsplash.com/photo-1505693416388-ac5ce068fe85?w=700&auto=format&fit=crop"] },
  { id: "demo-4", name: "Barres d'appui salle de bain (x2)", price: 59, currency: "EUR", images: ["https://images.unsplash.com/photo-1620626011761-996317b8d101?w=700&auto=format&fit=crop"] },
  { id: "demo-5", name: "Pilulier électronique connecté", price: 79, compare_at_price: 99, currency: "EUR", images: ["https://images.unsplash.com/photo-1550572017-edd951b55104?w=700&auto=format&fit=crop"] },
  { id: "demo-6", name: "Téléphone senior à grosses touches", price: 89, currency: "EUR", images: ["https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=700&auto=format&fit=crop"] },
];

export function ProductGrid({ siteId, products, loading, design, lang }) {
  const { primary, fontHeading } = designAccents(design);
  const hasReal = products && products.length > 0;
  const displayed = hasReal ? products : DEMO_PRODUCTS;

  return (
    <section id="products" className="max-w-7xl mx-auto px-6 md:px-10 py-20 md:py-24" data-testid="products-section">
      <div className="flex items-baseline justify-between mb-12">
        <div>
          <div className="text-[11px] uppercase tracking-[0.2em] text-neutral-500 mb-3">Best-sellers</div>
          <h2
            className="text-4xl md:text-5xl"
            style={{ fontFamily: `"${fontHeading}", serif`, color: "#1C1917" }}
          >
            {t(lang, "our_collection")}
          </h2>
        </div>
        <div className="text-sm text-[#78716C] hidden md:block">
          {hasReal ? `${products.length} ${products.length > 1 ? "produits" : "produit"}` : "Aperçu du template"}
        </div>
      </div>

      {loading ? (
        <div
          className="grid grid-cols-2 lg:grid-cols-3 gap-5 md:gap-8"
          data-testid="products-grid-skeleton"
          aria-busy="true"
          aria-label="Chargement des produits"
        >
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="animate-pulse">
              <div className="aspect-square rounded-2xl bg-stone-200/80 mb-4" />
              <div className="h-4 bg-stone-200/80 rounded w-4/5 mb-2" />
              <div className="h-4 bg-stone-200/80 rounded w-1/3" />
            </div>
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-2 lg:grid-cols-3 gap-5 md:gap-8" data-testid="products-grid">
          {displayed.map((p) => (
            <Link
              key={p.id}
              to={hasReal ? `/shop/${siteId}/product/${p.id}` : `/shop/${siteId}`}
              data-testid={`product-card-${p.id}`}
              className="group block"
            >
              <div className="aspect-square bg-[#F5F2EB] rounded-2xl overflow-hidden relative mb-4">
                {p.images?.[0] ? (
                  <img
                    src={p.images[0]}
                    alt={pickLang(p.name, lang) || p.name}
                    loading="lazy"
                    className="w-full h-full object-cover group-hover:scale-[1.04] transition-transform duration-700 ease-out"
                  />
                ) : (
                  <div className="w-full h-full flex items-center justify-center text-[#D6D3D1]">
                    <ShoppingBagOpen size={56} weight="thin" />
                  </div>
                )}
                {p.featured && (
                  <div
                    className="absolute top-4 left-4 text-white text-[10px] uppercase tracking-widest font-semibold px-3 py-1.5 rounded-full backdrop-blur-sm flex items-center gap-1"
                    style={{ background: `${primary}dd` }}
                  >
                    <Star size={10} weight="fill" /> {t(lang, "featured")}
                  </div>
                )}
                {p.compare_at_price && p.compare_at_price > p.price && (
                  <div
                    className="absolute top-4 right-4 text-white text-[11px] font-semibold px-2.5 py-1 rounded-full"
                    style={{ background: "#1C1917" }}
                  >
                    -{Math.round((1 - p.price / p.compare_at_price) * 100)}%
                  </div>
                )}
              </div>
              <div>
                <div
                  className="text-[15px] md:text-lg font-semibold leading-tight mb-1 group-hover:opacity-70 transition text-neutral-900"
                  style={{ fontFamily: `"${fontHeading}", serif` }}
                >
                  {pickLang(p.name, lang) || p.name}
                </div>
                <div className="flex items-baseline gap-2 mt-2">
                  <span className="text-lg md:text-xl font-semibold" style={{ color: primary }}>
                    {formatPrice(p.price, p.currency, lang)}
                  </span>
                  {p.compare_at_price && (
                    <span className="text-sm line-through text-[#A8A29E]">
                      {formatPrice(p.compare_at_price, p.currency, lang)}
                    </span>
                  )}
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </section>
  );
}
