import React, { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import axios from "axios";
import { ShoppingBagOpen, Plus, Sparkle } from "@phosphor-icons/react";
import { pickLang, t } from "../../lib/i18n";
import { addToCart } from "../../lib/cart";
import { BACKEND_URL, designAccents, formatPrice } from "./storefrontUtils";
import { getPrimaryImage } from "../../lib/productImage";

/**
 * Upsells : accessoires complémentaires sélectionnés à l'étape 3 du cockpit
 * et associés au produit principal affiché (ou à ceux d'une commande passée).
 * Source API : GET /public/sites/{id}/products/{pid}/upsells  (fiche produit)
 *              POST /public/sites/{id}/upsells-for-products  (post-purchase)
 */
export default function UpsellsRecommendations({
  mode = "product",       // "product" | "post_purchase"
  productId = null,
  productIds = null,      // array for post_purchase
  title = null,
  subtitle = null,
  lang = "fr",
  design = null,
  onAddToCart = null,     // optional tracking callback
}) {
  const { siteId } = useParams();
  const { primary, fontHeading } = designAccents(design);
  const [items, setItems] = useState([]);
  const [addedIds, setAddedIds] = useState({});

  useEffect(() => {
    if (!siteId) return;
    if (mode === "product" && productId) {
      axios
        .get(`${BACKEND_URL}/api/public/sites/${siteId}/products/${productId}/upsells?limit=4`)
        .then(({ data }) => setItems(Array.isArray(data) ? data : []))
        .catch(() => setItems([]));
    } else if (mode === "post_purchase" && productIds?.length) {
      axios
        .post(`${BACKEND_URL}/api/public/sites/${siteId}/upsells-for-products?limit=6`, {
          product_ids: productIds,
        })
        .then(({ data }) => setItems(Array.isArray(data) ? data : []))
        .catch(() => setItems([]));
    } else {
      setItems([]);
    }
  }, [siteId, mode, productId, JSON.stringify(productIds || [])]);

  if (!items.length) return null;

  const handleAdd = (p) => {
    addToCart(siteId, p, lang, 1);
    setAddedIds((prev) => ({ ...prev, [p.id]: true }));
    window.dispatchEvent(new Event("cf_cart_open"));
    if (onAddToCart) {
      try { onAddToCart(p); } catch (_) { /* noop */ }
    }
    setTimeout(() => setAddedIds((prev) => ({ ...prev, [p.id]: false })), 1800);
  };

  const resolvedTitle = title || (mode === "post_purchase" ? t(lang, "upsell_complete_order") : t(lang, "upsell_often_bought"));
  const resolvedSubtitle =
    subtitle ||
    (mode === "post_purchase" ? t(lang, "upsell_subtitle_post") : t(lang, "upsell_subtitle_related"));

  return (
    <section
      className="py-14 md:py-16 border-t"
      style={{ borderColor: "#E7E5E4" }}
      data-testid={`upsells-${mode}`}
    >
      <div className="flex items-end justify-between gap-4 mb-8 flex-wrap">
        <div>
          <div
            className="text-[11px] uppercase tracking-[0.2em] mb-3 flex items-center gap-2"
            style={{ color: primary }}
          >
            <Sparkle size={12} weight="fill" /> Recommandation
          </div>
          <h2
            className="text-3xl md:text-4xl"
            style={{ fontFamily: `"${fontHeading}", serif`, color: "#1C1917" }}
          >
            {resolvedTitle}
          </h2>
          <p className="text-sm text-neutral-500 mt-2 max-w-xl">{resolvedSubtitle}</p>
        </div>
      </div>

      <div
        className="flex sm:grid sm:grid-cols-2 lg:grid-cols-4 gap-4 md:gap-5 -mx-6 sm:mx-0 px-6 sm:px-0 overflow-x-auto sm:overflow-visible snap-x snap-mandatory sm:snap-none scroll-smooth pb-2 sm:pb-0"
        data-testid="upsells-carousel"
      >
        {items.map((p) => {
          const name = pickLang(p.name, lang) || p.name;
          const added = addedIds[p.id];
          return (
            <div
              key={p.id}
              data-testid={`upsell-card-${p.id}`}
              className="bg-white rounded-2xl overflow-hidden border border-[#E7E5E4] hover:border-neutral-900 transition flex flex-col snap-center shrink-0 w-[72vw] sm:w-auto"
            >
              <Link
                to={`/shop/${siteId}/product/${p.id}`}
                className="aspect-square bg-[#F5F2EB] relative overflow-hidden group block"
              >
                {(() => { const _src = getPrimaryImage(p); return _src ? (
                  <img
                    src={_src}
                    alt={name}
                    loading="lazy"
                    className="w-full h-full object-cover group-hover:scale-[1.04] transition-transform duration-700"
                  />
                ) : (
                  <div className="w-full h-full flex items-center justify-center text-neutral-300">
                    <ShoppingBagOpen size={40} weight="thin" />
                  </div>
                ); })()}
              </Link>
              <div className="p-4 flex-1 flex flex-col">
                <Link
                  to={`/shop/${siteId}/product/${p.id}`}
                  className="text-[14px] font-semibold leading-tight text-neutral-900 hover:opacity-70 line-clamp-2"
                  style={{ fontFamily: `"${fontHeading}", serif` }}
                >
                  {name}
                </Link>
                <div className="mt-auto pt-3 flex items-end justify-between gap-2">
                  <div className="text-base font-semibold" style={{ color: primary }}>
                    {formatPrice(p.price, p.currency, lang)}
                  </div>
                  <button
                    onClick={() => handleAdd(p)}
                    data-testid={`upsell-add-${p.id}`}
                    className={`h-9 px-3 rounded-lg text-xs font-medium flex items-center gap-1.5 transition ${
                      added
                        ? "bg-emerald-100 text-emerald-800"
                        : "bg-neutral-900 hover:bg-neutral-800 text-white"
                    }`}
                  >
                    {added ? "Ajouté ✓" : (<><Plus size={12} weight="bold" /> Ajouter</>)}
                  </button>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
