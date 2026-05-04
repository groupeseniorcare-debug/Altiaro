import React, { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import axios from "axios";
import { ArrowRight, ShoppingBag } from "@phosphor-icons/react";
import { BACKEND_URL, designAccents } from "./storefrontUtils";
import { getPrimaryImage } from "../../lib/productImage";
import { pickLang } from "../../lib/i18n";
import { useShopSiteId } from "../../lib/shopSiteId";

/**
 * Phase 3.2 chantier D — Section « Accessoires & compléments ».
 *
 * Affiche tous les upsells actifs du site (GET /public/sites/{id}/upsells).
 * Rendu horizontal scrollable sur mobile, grille 3/4 col sur desktop.
 * Si aucun upsell disponible → la section est masquée (silent).
 */
export default function StorefrontAccessories({ lang = "fr", design, currentProductId = null, title = "Accessoires & compléments", subtitle = "Pensés pour prolonger votre expérience au quotidien." }) {
  const siteId = useShopSiteId();
  const { primary, fontHeading } = designAccents(design);
  const [items, setItems] = useState([]);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    if (!siteId) return;
    axios.get(`${BACKEND_URL}/api/public/sites/${siteId}/upsells?limit=12`)
      .then(({ data }) => {
        const filtered = (data || []).filter((p) => p.id !== currentProductId);
        setItems(filtered);
      })
      .catch(() => setItems([]))
      .finally(() => setLoaded(true));
  }, [siteId, currentProductId]);

  if (!loaded) return null;
  if (items.length === 0) return null;

  return (
    <section className="py-16 md:py-20" style={{ background: "#F5F2EB" }} data-testid="storefront-accessories">
      <div className="max-w-7xl mx-auto px-6 md:px-10">
        <div className="flex items-end justify-between flex-wrap gap-4 mb-10">
          <div>
            <div className="text-[11px] uppercase tracking-[0.2em] text-neutral-500 mb-3">Pour compléter votre sélection</div>
            <h2 className="text-3xl md:text-4xl" style={{ fontFamily: `"${fontHeading}", serif`, color: "#1C1917" }}>
              {title}
            </h2>
            {subtitle && (
              <p className="mt-2 text-sm text-neutral-600 max-w-xl">{subtitle}</p>
            )}
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5 md:gap-6">
          {items.slice(0, 8).map((p) => {
            const img = getPrimaryImage(p);
            const name = pickLang(p.name, lang) || "Accessoire";
            const price = typeof p.price === "number" ? p.price.toFixed(2).replace(".", ",") : "";
            const href = `/shop/${siteId}/product/${p.slug || p.id}`;
            return (
              <Link
                key={p.id}
                to={href}
                className="group block bg-white rounded-2xl overflow-hidden border border-neutral-200 hover:shadow-md transition"
                data-testid={`accessory-card-${p.id}`}
              >
                <div className="aspect-square bg-white overflow-hidden">
                  {img ? (
                    <img src={img.startsWith("http") ? img : `${BACKEND_URL}${img}`}
                         alt={name}
                         loading="lazy"
                         className="w-full h-full object-cover group-hover:scale-[1.03] transition duration-500" />
                  ) : (
                    <div className="w-full h-full bg-neutral-100" />
                  )}
                </div>
                <div className="p-4">
                  <div className="text-sm font-medium text-neutral-900 line-clamp-2 min-h-[2.5rem]" style={{ fontFamily: `"${fontHeading}", serif` }}>
                    {name}
                  </div>
                  <div className="mt-2 flex items-center justify-between">
                    <div className="text-base font-semibold" style={{ color: primary }}>
                      {price} €
                    </div>
                    <span className="inline-flex items-center gap-1 text-xs text-neutral-500 group-hover:text-neutral-900 transition">
                      <ShoppingBag size={14} /> Découvrir
                      <ArrowRight size={12} weight="bold" className="group-hover:translate-x-0.5 transition" />
                    </span>
                  </div>
                </div>
              </Link>
            );
          })}
        </div>
      </div>
    </section>
  );
}
