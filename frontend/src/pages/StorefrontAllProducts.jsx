import React, { useEffect, useState } from "react";
import axios from "axios";
import StorefrontLayout from "../components/StorefrontLayout";
import { BACKEND_URL, useSiteAndLang, designAccents } from "../components/storefront/storefrontUtils";
import { ProductGrid } from "../components/storefront/ProductGrid";
import SEOHead from "../components/SEOHead";
import { t } from "../lib/i18n";

/**
 * Phase 3.3 Fix 1.3 — Page « Tous les produits ».
 *
 * Affiche la grille complète des produits principaux (role != upsell) du site.
 * Accessible via `/shop/:siteId/products` (PlatformApp) ou `/products`
 * (CustomDomainApp).
 */
export default function StorefrontAllProducts() {
  const { siteId, site, design, lang } = useSiteAndLang();
  const { fontHeading } = designAccents(design);
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!siteId) return;
    axios.get(`${BACKEND_URL}/api/public/sites/${siteId}/products`)
      .then(({ data }) => setProducts(Array.isArray(data) ? data : []))
      .catch(() => setProducts([]))
      .finally(() => setLoading(false));
  }, [siteId]);

  const title = t(lang, "footer_all_products") || "Tous les produits";

  return (
    <StorefrontLayout site={site} design={design} lang={lang}>
      <SEOHead
        title={`${title} — ${site?.name || ""}`}
        description={`Découvrez l'intégralité de notre catalogue. ${products.length} produits sélectionnés.`}
      />
      <section className="py-16 md:py-20 bg-white" data-testid="storefront-all-products">
        <div className="max-w-7xl mx-auto px-6 md:px-10">
          <div className="mb-10">
            <div className="text-[11px] uppercase tracking-[0.2em] text-neutral-500 mb-3">Catalogue</div>
            <h1 className="text-3xl md:text-4xl text-neutral-900" style={{ fontFamily: `"${fontHeading}", serif` }}>
              {title}
            </h1>
            <p className="mt-2 text-sm text-neutral-600">
              {products.length} produit{products.length > 1 ? "s" : ""} disponible{products.length > 1 ? "s" : ""}.
            </p>
          </div>
          <ProductGrid siteId={siteId} products={products} loading={loading} design={design} lang={lang} />
        </div>
      </section>
    </StorefrontLayout>
  );
}
