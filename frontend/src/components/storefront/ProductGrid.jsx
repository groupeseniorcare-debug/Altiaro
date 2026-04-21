import React from "react";
import { Link } from "react-router-dom";
import { ShoppingBagOpen } from "@phosphor-icons/react";
import { pickLang, t } from "../../lib/i18n";
import { designAccents, formatPrice } from "./storefrontUtils";

export function ProductGrid({ siteId, products, loading, design, lang }) {
  const { primary, fontHeading } = designAccents(design);

  return (
    <section id="products" className="max-w-6xl mx-auto px-6 md:px-10 pb-24">
      <div className="flex items-baseline justify-between mb-10">
        <h2
          className="text-3xl md:text-4xl font-semibold tracking-tight"
          style={{ fontFamily: `"${fontHeading}", serif` }}
        >
          {t(lang, "our_collection")}
        </h2>
        <div className="text-sm text-[#78716C]">
          {products.length} {products.length > 1 ? "produits" : "produit"}
        </div>
      </div>

      {loading ? (
        <div className="py-20 text-center text-[#78716C]">…</div>
      ) : products.length === 0 ? (
        <div className="py-20 text-center text-[#78716C] bg-white rounded-2xl border border-dashed border-[#E7E5E4]">
          {t(lang, "no_products")}
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 md:gap-8" data-testid="products-grid">
          {products.map((p) => (
            <Link
              key={p.id}
              to={`/shop/${siteId}/product/${p.id}`}
              data-testid={`product-card-${p.id}`}
              className="group block"
            >
              <div className="aspect-square bg-[#F5F2EB] rounded-2xl overflow-hidden relative mb-4">
                {p.images?.[0] ? (
                  <img
                    src={p.images[0]}
                    alt={pickLang(p.name, lang)}
                    className="w-full h-full object-cover group-hover:scale-[1.04] transition-transform duration-700 ease-out"
                  />
                ) : (
                  <div className="w-full h-full flex items-center justify-center text-[#D6D3D1]">
                    <ShoppingBagOpen size={56} weight="thin" />
                  </div>
                )}
                {p.featured && (
                  <div
                    className="absolute top-4 left-4 text-white text-[10px] uppercase tracking-widest font-semibold px-3 py-1.5 rounded-full backdrop-blur-sm"
                    style={{ background: `${primary}dd` }}
                  >
                    ★ {t(lang, "featured")}
                  </div>
                )}
              </div>
              <div>
                <div
                  className="text-lg font-semibold leading-tight mb-1 group-hover:opacity-70 transition"
                  style={{ fontFamily: `"${fontHeading}", serif` }}
                >
                  {pickLang(p.name, lang)}
                </div>
                <div className="flex items-baseline gap-2 mt-2">
                  <span className="text-xl font-semibold" style={{ color: primary }}>
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
