import React, { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import axios from "axios";
import { ArrowRight } from "@phosphor-icons/react";
import { t } from "../../lib/i18n";
import { BACKEND_URL, designAccents } from "./storefrontUtils";
import ProductCard from "./ProductCard";
import { hasAiImage } from "../../lib/productImage";
import { useShopSiteId } from "../../lib/shopSiteId";

/**
 * Cross-sell — "Vous aimerez aussi" : 4 produits complémentaires.
 * Phase 2.5 Tâche F — utilise `<ProductCard variant="default">`, exactement
 * le même composant que la Home, pour un rendu visuel strictement identique
 * (proportions, typos, micro-animations, CTA double).
 * Même site, même category en priorité, sinon best-sellers globaux.
 */
export default function CrossSellProducts({ currentProduct, lang = "fr", design }) {
  const siteId = useShopSiteId();
  const { primary, fontHeading } = designAccents(design);
  const [products, setProducts] = useState([]);

  useEffect(() => {
    if (!siteId || !currentProduct) return;
    const params = new URLSearchParams();
    if (currentProduct.category) params.set("collection", currentProduct.category);
    params.set("sort", "featured");
    axios.get(`${BACKEND_URL}/api/public/sites/${siteId}/products?${params.toString()}`)
      .then(({ data }) => {
        // Phase 2.5 Tâche F — filtre strict image IA (pas de watermark AE).
        const filtered = (data || [])
          .filter((p) => p.id !== currentProduct.id)
          .filter(hasAiImage)
          .slice(0, 3);
        setProducts(filtered);
      })
      .catch(() => setProducts([]));
  }, [siteId, currentProduct]);

  // Phase 2.5 Tâche F — pas de demo fallback pour éviter les mix qualité IA / Unsplash.
  // Si le site a <3 produits supplémentaires → section masquée proprement.
  if (products.length < 2) return null;

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
          {t(lang, "collections_see_all")} <ArrowRight size={14} weight="bold" />
        </Link>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5 md:gap-6">
        {products.map((p) => (
          <ProductCard
            key={p.id}
            product={p}
            siteId={siteId}
            lang={lang}
            design={design}
            variant="default"
            testId={`xsell-${p.id}`}
          />
        ))}
      </div>
    </section>
  );
}
