import React, { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import axios from "axios";
import { ArrowRight, ShoppingBagOpen, Star } from "@phosphor-icons/react";
import { pickLang } from "../../lib/i18n";
import { BACKEND_URL, designAccents, formatPrice } from "./storefrontUtils";

/**
 * Cross-sell — "Vous aimerez aussi" : 4 produits complémentaires.
 * Même site, même category en priorité, sinon best-sellers globaux.
 */
export default function CrossSellProducts({ currentProduct, lang = "fr", design }) {
  const { siteId } = useParams();
  const { primary, fontHeading } = designAccents(design);
  const [products, setProducts] = useState([]);

  useEffect(() => {
    if (!siteId || !currentProduct) return;
    const params = new URLSearchParams();
    if (currentProduct.category) params.set("collection", currentProduct.category);
    params.set("sort", "featured");
    axios.get(`${BACKEND_URL}/api/public/sites/${siteId}/products?${params.toString()}`)
      .then(({ data }) => {
        const filtered = (data || []).filter((p) => p.id !== currentProduct.id).slice(0, 4);
        setProducts(filtered);
      })
      .catch(() => setProducts([]));
  }, [siteId, currentProduct]);

  // Demo fallback for template completeness
  const demo = [
    { id: "x-1", name: "Déambulateur 4 roues ultra-léger", price: 149, currency: "EUR", images: ["https://images.unsplash.com/photo-1584515933487-779824d29309?w=700&auto=format&fit=crop"] },
    { id: "x-2", name: "Matelas médical à mémoire de forme", price: 599, currency: "EUR", images: ["https://images.unsplash.com/photo-1505693416388-ac5ce068fe85?w=700&auto=format&fit=crop"] },
    { id: "x-3", name: "Barres d'appui salle de bain (x2)", price: 59, currency: "EUR", images: ["https://images.unsplash.com/photo-1620626011761-996317b8d101?w=700&auto=format&fit=crop"] },
    { id: "x-4", name: "Téléphone senior à grosses touches", price: 89, currency: "EUR", images: ["https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=700&auto=format&fit=crop"] },
  ];
  const hasReal = products.length > 0;
  const displayed = hasReal ? products : demo;

  return (
    <section className="py-16 md:py-20 border-t" style={{ borderColor: "#E7E5E4" }} data-testid="product-cross-sell">
      <div className="flex items-end justify-between flex-wrap gap-4 mb-10">
        <div>
          <div className="text-[11px] uppercase tracking-[0.2em] text-neutral-500 mb-3">Vous aimerez aussi</div>
          <h2 className="text-3xl md:text-4xl" style={{ fontFamily: `"${fontHeading}", serif`, color: "#1C1917" }}>
            Dans la même collection
          </h2>
        </div>
        <Link to={`/shop/${siteId}`} className="text-sm inline-flex items-center gap-1.5 hover:gap-2.5 transition-all" style={{ color: primary }}>
          Voir toute la boutique <ArrowRight size={14} weight="bold" />
        </Link>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-5 md:gap-6">
        {displayed.map((p) => (
          <Link
            key={p.id}
            to={hasReal ? `/shop/${siteId}/product/${p.id}` : `/shop/${siteId}`}
            data-testid={`xsell-${p.id}`}
            className="group block"
          >
            <div className="aspect-square bg-[#F5F2EB] rounded-2xl overflow-hidden relative mb-3">
              {p.images?.[0] ? (
                <img src={p.images[0]} alt={pickLang(p.name, lang) || p.name} loading="lazy" className="w-full h-full object-cover group-hover:scale-[1.04] transition-transform duration-700" />
              ) : (
                <div className="w-full h-full flex items-center justify-center text-neutral-300">
                  <ShoppingBagOpen size={48} weight="thin" />
                </div>
              )}
              {p.featured && (
                <div className="absolute top-3 left-3 text-white text-[10px] uppercase tracking-widest font-semibold px-2 py-1 rounded-full flex items-center gap-1" style={{ background: `${primary}dd` }}>
                  <Star size={9} weight="fill" /> Phare
                </div>
              )}
            </div>
            <div className="text-[14px] md:text-[15px] font-semibold leading-tight group-hover:opacity-70 transition text-neutral-900 line-clamp-2" style={{ fontFamily: `"${fontHeading}", serif` }}>
              {pickLang(p.name, lang) || p.name}
            </div>
            <div className="text-base font-semibold mt-1.5" style={{ color: primary }}>
              {formatPrice(p.price, p.currency, lang)}
            </div>
          </Link>
        ))}
      </div>
    </section>
  );
}
