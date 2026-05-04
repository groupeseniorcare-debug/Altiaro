import React, { useEffect, useState } from "react";
import axios from "axios";
import StorefrontLayout from "../components/StorefrontLayout";
import { BACKEND_URL, useSiteAndLang, designAccents } from "../components/storefront/storefrontUtils";
import StorefrontAccessories from "../components/storefront/StorefrontAccessories";
import SEOHead from "../components/SEOHead";

/**
 * Phase 3.3 Fix 1.4 — Page « Accessoires » dédiée.
 *
 * Affiche tous les upsells du site. Accessible via `/shop/:siteId/accessories`
 * (PlatformApp) ou `/accessories` (CustomDomainApp).
 */
export default function StorefrontAccessoriesPage() {
  const { siteId, site, design, lang } = useSiteAndLang();
  const { fontHeading } = designAccents(design);
  const [count, setCount] = useState(null);

  useEffect(() => {
    if (!siteId) return;
    axios.get(`${BACKEND_URL}/api/public/sites/${siteId}/upsells?limit=50`)
      .then(({ data }) => setCount(Array.isArray(data) ? data.length : 0))
      .catch(() => setCount(0));
  }, [siteId]);

  return (
    <StorefrontLayout site={site} design={design} lang={lang}>
      <SEOHead
        title={`Accessoires & compléments — ${site?.name || ""}`}
        description={"Accessoires et compléments pour prolonger votre expérience au quotidien."}
      />
      <section className="py-12 md:py-16 bg-white" data-testid="storefront-accessories-page">
        <div className="max-w-7xl mx-auto px-6 md:px-10">
          <div className="mb-6">
            <div className="text-[11px] uppercase tracking-[0.2em] text-neutral-500 mb-3">Compléments</div>
            <h1 className="text-3xl md:text-4xl text-neutral-900" style={{ fontFamily: `"${fontHeading}", serif` }}>
              Accessoires &amp; compléments
            </h1>
            {count != null && (
              <p className="mt-2 text-sm text-neutral-600">
                {count} accessoire{count > 1 ? "s" : ""} pensé{count > 1 ? "s" : ""} pour sublimer votre sélection.
              </p>
            )}
          </div>
        </div>
      </section>
      <StorefrontAccessories
        lang={lang}
        design={design}
        title="Notre sélection d'accessoires"
        subtitle="Finitions, essentiels et compagnons du quotidien, choisis pour leur exigence de détail."
      />
    </StorefrontLayout>
  );
}
