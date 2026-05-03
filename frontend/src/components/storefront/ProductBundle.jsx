/**
 * Lot I (Phase 2.1) Fix I4 — Bundle "Souvent achetés ensemble" — 3 slots stricts.
 *
 * Slots fixes (décision user Q3 2026-04-27) :
 * - Slot 1 = produit principal de la page (toujours, non décochable)
 * - Slots 2 et 3 = 2 produits réellement importés depuis AE/CJ avec
 *   `role ∈ {upsell, accessory, accessoire, addon}`. PAS d'IA-suggéré
 *   hors panier d'imports.
 *
 * Si <2 accessoires existent sur le site → la section entière est masquée
 * (pas de demo fallback, pas d'image générique Unsplash).
 *
 * Images : `getPrimaryImage()` strict → renvoie l'image IA Nano Banana
 * (priorité generated_images.url). Jamais l'image AliExpress brute.
 *
 * Total = somme des 3 prix (pas de discount auto, décision user — voir Phase 4).
 *
 * Composant partagé → propagation auto sur tous les sites.
 */
import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import axios from "axios";
import { Plus, Check, ShoppingBag, ShoppingBagOpen } from "@phosphor-icons/react";
import { pickLang, t } from "../../lib/i18n";
import { BACKEND_URL, designAccents, formatPrice } from "./storefrontUtils";
import { addToCart } from "../../lib/cart";
import { toast } from "sonner";
import { getPrimaryImage, hasAiImage } from "../../lib/productImage";
import { useShopSiteId } from "../../lib/shopSiteId";

// Roles considered as "companion" products for bundling
const COMPANION_ROLES = new Set(["upsell", "accessory", "accessoire", "addon"]);
const isCompanion = (p) => COMPANION_ROLES.has((p?.role || "").toLowerCase());
// Phase 2.5 Tâche F — filtre strict : un accessoire bundle doit avoir une
// image IA Nano Banana (sinon on affiche une vignette AE watermarkée).
const isPremiumCompanion = (p) => isCompanion(p) && hasAiImage(p);

export default function ProductBundle({ currentProduct, lang = "fr", design }) {
  const siteId = useShopSiteId();
  const { primary, fontHeading } = designAccents(design);
  const [accessories, setAccessories] = useState([]);
  const [selected, setSelected] = useState({});
  const [loaded, setLoaded] = useState(false);

  // Fetch accessories — uses the dedicated `/upsells` public endpoint which
  // returns products with role=upsell (linked first, fallback to any upsell of
  // the site). Lot I I4 — strict: never any AI-suggested out-of-catalog item.
  useEffect(() => {
    if (!siteId || !currentProduct) return;

    // Priority 1 : explicit bundles_with configured (manual link)
    const bundleIds = currentProduct.bundles_with || [];
    if (bundleIds.length > 0) {
      Promise.all(
        bundleIds.slice(0, 2).map((pid) =>
          axios.get(`${BACKEND_URL}/api/public/sites/${siteId}/products/${pid}`)
            .then(({ data }) => data)
            .catch(() => null)
        )
      ).then((res) => {
        // Filter to keep only real companions WITH AI image (Phase 2.5 Tâche F).
        setAccessories(res.filter(Boolean).filter(isPremiumCompanion).slice(0, 2));
        setLoaded(true);
      });
      return;
    }

    // Priority 2 : public upsells endpoint (filters role=upsell server-side,
    // includes role-aware fallback to any upsell of the site)
    axios.get(`${BACKEND_URL}/api/public/sites/${siteId}/products/${currentProduct.id}/upsells?limit=6`)
      .then(({ data }) => {
        const candidates = (data || []).filter((p) => p.id !== currentProduct.id);
        // Phase 2.5 Tâche F — préférer les companions avec image IA.
        // Si <2 premium dispo → fallback sur les companions simples pour
        // préserver la fonction bundle sur les sites en transition.
        const premium = candidates.filter(isPremiumCompanion).slice(0, 2);
        const fallback = candidates.filter(isCompanion).slice(0, 2);
        setAccessories(premium.length >= 2 ? premium : fallback);
        setLoaded(true);
      })
      .catch(() => {
        setAccessories([]);
        setLoaded(true);
      });
  }, [siteId, currentProduct]);

  // Initial selection: all selected, current product locked
  useEffect(() => {
    const init = {};
    accessories.forEach((p) => { init[p.id] = true; });
    init[currentProduct.id] = true;
    setSelected(init);
    // eslint-disable-next-line
  }, [currentProduct.id, accessories.map(a => a.id).join(",")]);

  // Décision Q3 user : ne JAMAIS afficher de demo fallback. Si <2 accessoires
  // réels → section entièrement masquée pour ne pas tromper l'acheteur.
  if (!loaded) return null;
  if (accessories.length < 2) return null;

  const allItems = [currentProduct, ...accessories];
  const selectedItems = allItems.filter((p) => selected[p.id]);
  const total = selectedItems.reduce((s, p) => s + (p.price || 0), 0);
  const currency = currentProduct.currency || "EUR";

  const toggle = (id) => {
    if (id === currentProduct.id) return; // current product always included
    setSelected((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const addAll = () => {
    let count = 0;
    selectedItems.forEach((p) => {
      addToCart(siteId, {
        product_id: p.id,
        name: pickLang(p.name, lang) || p.name,
        price: p.price,
        currency: p.currency || currency,
        image: getPrimaryImage(p),
        quantity: 1,
      });
      count++;
      try { window.altiaroTrack?.addToCart?.(p, 1, lang); } catch (_) {}
    });
    const msg = count > 1
      ? t(lang, "bundle_added_n").replace("{n}", count)
      : t(lang, "bundle_added_one");
    toast.success(msg);
  };

  const totalLabel = selectedItems.length > 1
    ? t(lang, "bundle_total_for_n").replace("{n}", selectedItems.length)
    : t(lang, "bundle_total_for_one");

  return (
    <section className="py-14 border-t" style={{ borderColor: "#E7E5E4" }} data-testid="product-bundle">
      <div className="bg-[#F5F2EB] rounded-3xl p-6 md:p-10">
        <div className="mb-8">
          <div className="text-[11px] uppercase tracking-[0.2em] text-neutral-500 mb-2">
            {t(lang, "bundle_eyebrow")}
          </div>
          <h2 className="text-2xl md:text-3xl" style={{ fontFamily: `"${fontHeading}", serif`, color: "#1C1917" }}>
            {t(lang, "bundle_title")}
          </h2>
        </div>

        {/* Items — Phase 2.5 Tâche D :
            MOBILE (<md) → empilé verticalement, 1 card par ligne pleine largeur.
            DESKTOP (>=md) → 3 cards alignées avec "+" entre elles. */}
        <div className="flex flex-col md:flex-row md:items-center gap-3 md:gap-4">
          {allItems.map((p, i) => (
            <React.Fragment key={p.id}>
              {i > 0 && (
                <Plus
                  size={22}
                  weight="bold"
                  className="shrink-0 text-neutral-400 self-center hidden md:block"
                />
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
              {totalLabel}
            </div>
            <div className="flex items-baseline gap-3 mt-1">
              <span className="text-2xl md:text-3xl font-semibold" style={{ color: primary }}>
                {formatPrice(total, currency, lang)}
              </span>
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
  // Force getPrimaryImage → priorité images IA Nano Banana, jamais AE brutes
  const src = getPrimaryImage(product);
  return (
    <div
      className="flex items-center gap-3 bg-white rounded-2xl p-3 md:p-4 w-full md:w-[260px] md:shrink-0"
      data-testid={`bundle-item-${product.id}`}
    >
      <div className="w-16 h-16 md:w-20 md:h-20 rounded-xl overflow-hidden bg-[#F5F2EB] shrink-0">
        {src ? (
          <img src={src} alt={pickLang(product.name, lang) || product.name} loading="lazy" className="w-full h-full object-cover" />
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
            aria-label={checked ? t(lang, "bundle_remove_from_pack") : t(lang, "bundle_add_to_pack")}
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
          <div
            className="text-[13px] md:text-sm font-medium leading-tight text-neutral-900 line-clamp-2"
            style={{ fontFamily: `"${fontHeading}", serif` }}
          >
            {pickLang(product.name, lang) || product.name}
          </div>
        </div>
        <div className="text-[13px] font-semibold pl-7" style={{ color: primary }}>
          {formatPrice(product.price, product.currency, lang)}
        </div>
        {isCurrent && (
          <div className="text-[10px] uppercase tracking-widest text-neutral-400 pl-7 mt-0.5">
            {t(lang, "bundle_current_item")}
          </div>
        )}
      </div>
    </div>
  );
}
