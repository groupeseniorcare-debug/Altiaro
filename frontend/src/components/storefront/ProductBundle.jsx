import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import axios from "axios";
import { Plus, Check, ShoppingBag, ShoppingBagOpen } from "@phosphor-icons/react";
import { pickLang, t } from "../../lib/i18n";
import { BACKEND_URL, designAccents, formatPrice } from "./storefrontUtils";
import { addToCart } from "../../lib/cart";
import { toast } from "sonner";

/**
 * Product bundle — "Souvent achetés ensemble"
 * Sélectionne automatiquement 2 produits de la même category (fallback : 2 produits quelconques).
 * Offre -10% si les 3 produits sont achetés ensemble.
 *
 * Design : 3 cartes horizontales avec "+" entre elles, récap prix barré à droite.
 */
export default function ProductBundle({ currentProduct, lang = "fr", design }) {
  const { siteId } = useParams();
  const { primary, fontHeading } = designAccents(design);
  const [candidates, setCandidates] = useState([]);
  const [selected, setSelected] = useState({});

  useEffect(() => {
    if (!siteId || !currentProduct) return;

    // Priority 1 : explicit bundles_with configured (AI-suggested or manual)
    const bundleIds = currentProduct.bundles_with || [];
    if (bundleIds.length > 0) {
      Promise.all(
        bundleIds.slice(0, 2).map((pid) =>
          axios.get(`${BACKEND_URL}/api/public/sites/${siteId}/products/${pid}`)
            .then(({ data }) => data)
            .catch(() => null)
        )
      ).then((res) => {
        setCandidates(res.filter(Boolean));
      });
      return;
    }

    // Priority 2 : same category fallback
    const params = new URLSearchParams();
    if (currentProduct.category) params.set("collection", currentProduct.category);
    params.set("sort", "featured");
    axios.get(`${BACKEND_URL}/api/public/sites/${siteId}/products?${params.toString()}`)
      .then(({ data }) => {
        const filtered = (data || []).filter((p) => p.id !== currentProduct.id).slice(0, 2);
        setCandidates(filtered);
      })
      .catch(() => setCandidates([]));
  }, [siteId, currentProduct]);

  // Demo fallback if no other real products exist
  const demoFallback = [
    { id: "bundle-1", name: "Coussin ergonomique lombaire", price: 39, currency: "EUR", images: ["https://images.unsplash.com/photo-1568162603664-fcd658421851?w=500&auto=format&fit=crop"], _demo: true },
    { id: "bundle-2", name: "Protection anti-taches fauteuil", price: 29, currency: "EUR", images: ["https://images.unsplash.com/photo-1555041469-a586c61ea9bc?w=500&auto=format&fit=crop"], _demo: true },
  ];
  const hasReal = candidates.length > 0;
  const accessories = hasReal ? candidates : demoFallback;

  // Initial selection: all selected
  useEffect(() => {
    const init = {};
    accessories.forEach((p) => { init[p.id] = true; });
    init[currentProduct.id] = true;
    setSelected(init);
  // eslint-disable-next-line
  }, [currentProduct.id, accessories.map(a => a.id).join(",")]);

  if (!accessories.length) return null;

  const allItems = [currentProduct, ...accessories];
  const selectedItems = allItems.filter((p) => selected[p.id]);
  const subtotal = selectedItems.reduce((s, p) => s + (p.price || 0), 0);
  const DISCOUNT = selectedItems.length >= 2 ? 0.10 : 0; // 10% if at least 2 items
  const finalTotal = subtotal * (1 - DISCOUNT);
  const savings = subtotal - finalTotal;
  const currency = currentProduct.currency || "EUR";

  const toggle = (id) => {
    if (id === currentProduct.id) return; // current product always included
    setSelected((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const addAll = () => {
    selectedItems.forEach((p) => {
      if (p._demo) return;
      addToCart(siteId, {
        product_id: p.id,
        name: pickLang(p.name, lang) || p.name,
        price: p.price,
        currency: p.currency || currency,
        image: p.images?.[0],
        quantity: 1,
      });
      try { window.altiaroTrack?.addToCart?.(p, 1, lang); } catch (_) {}
    });
    toast.success(`${selectedItems.filter(p => !p._demo).length} produit(s) ajoutés au panier`);
  };

  return (
    <section className="py-14 border-t" style={{ borderColor: "#E7E5E4" }} data-testid="product-bundle">
      <div className="bg-[#F5F2EB] rounded-3xl p-6 md:p-10">
        <div className="flex items-center justify-between mb-8 flex-wrap gap-3">
          <div>
            <div className="text-[11px] uppercase tracking-[0.2em] text-neutral-500 mb-2">
              Pack économies
            </div>
            <h2 className="text-2xl md:text-3xl" style={{ fontFamily: `"${fontHeading}", serif`, color: "#1C1917" }}>
              Souvent achetés ensemble
            </h2>
          </div>
          {DISCOUNT > 0 && (
            <div
              className="px-3 py-1.5 rounded-full text-white text-xs font-semibold"
              style={{ background: primary }}
            >
              −{Math.round(DISCOUNT * 100)}% en lot
            </div>
          )}
        </div>

        {/* Items row */}
        <div className="flex items-center gap-3 md:gap-4 overflow-x-auto pb-2 -mx-6 px-6 md:mx-0 md:px-0">
          {allItems.map((p, i) => (
            <React.Fragment key={p.id}>
              {i > 0 && (
                <Plus size={22} weight="bold" className="shrink-0 text-neutral-400" />
              )}
              <BundleItem
                product={p}
                isCurrent={p.id === currentProduct.id}
                checked={selected[p.id]}
                onToggle={() => toggle(p.id)}
                lang={lang}
                primary={primary}
                fontHeading={fontHeading}
              />
            </React.Fragment>
          ))}
        </div>

        {/* Total + CTA */}
        <div className="mt-8 flex items-center justify-between flex-wrap gap-4 border-t border-neutral-200 pt-6">
          <div>
            <div className="text-sm text-neutral-600">
              Total pour les {selectedItems.length} article{selectedItems.length > 1 ? "s" : ""} :
            </div>
            <div className="flex items-baseline gap-3 mt-1">
              <span className="text-2xl md:text-3xl font-semibold" style={{ color: primary }}>
                {formatPrice(finalTotal, currency, lang)}
              </span>
              {savings > 0 && (
                <>
                  <span className="text-lg text-neutral-400 line-through">
                    {formatPrice(subtotal, currency, lang)}
                  </span>
                  <span className="text-sm font-medium text-emerald-700">
                    Économie {formatPrice(savings, currency, lang)}
                  </span>
                </>
              )}
            </div>
          </div>
          <button
            type="button"
            onClick={addAll}
            data-testid="bundle-add-all"
            className="inline-flex items-center gap-2 h-12 px-6 rounded-full text-white font-medium transition hover:opacity-90 active:scale-[0.98]"
            style={{ background: primary }}
          >
            <ShoppingBag size={18} weight="regular" />
            {t(lang, "bundle_add_to_cart")}
          </button>
        </div>
      </div>
    </section>
  );
}

function BundleItem({ product, isCurrent, checked, onToggle, lang, primary, fontHeading }) {
  return (
    <div className="flex items-center gap-3 bg-white rounded-2xl p-3 md:p-4 w-[220px] md:w-[260px] shrink-0" data-testid={`bundle-item-${product.id}`}>
      <div className="w-16 h-16 md:w-20 md:h-20 rounded-xl overflow-hidden bg-[#F5F2EB] shrink-0">
        {product.images?.[0] ? (
          <img src={product.images[0]} alt={pickLang(product.name, lang) || product.name} loading="lazy" className="w-full h-full object-cover" />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-neutral-300">
            <ShoppingBagOpen size={28} weight="thin" />
          </div>
        )}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-start gap-2 mb-1">
          <button
            type="button"
            onClick={onToggle}
            disabled={isCurrent}
            aria-label={checked ? "Retirer du pack" : "Ajouter au pack"}
            className={`w-5 h-5 rounded-md flex items-center justify-center border transition shrink-0 mt-0.5 ${
              checked ? "text-white" : "bg-white"
            } ${isCurrent ? "opacity-50 cursor-not-allowed" : "hover:scale-110"}`}
            style={{
              background: checked ? primary : undefined,
              borderColor: checked ? primary : "#E7E5E4",
            }}
          >
            {checked && <Check size={12} weight="bold" />}
          </button>
          <div className="text-[13px] md:text-sm font-medium leading-tight text-neutral-900 line-clamp-2" style={{ fontFamily: `"${fontHeading}", serif` }}>
            {pickLang(product.name, lang) || product.name}
          </div>
        </div>
        <div className="text-[13px] font-semibold pl-7" style={{ color: primary }}>
          {formatPrice(product.price, product.currency, lang)}
        </div>
        {isCurrent && (
          <div className="text-[10px] uppercase tracking-widest text-neutral-400 pl-7 mt-0.5">
            Cet article
          </div>
        )}
      </div>
    </div>
  );
}
