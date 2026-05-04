import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api, apiCall } from "../lib/api";
import ProductImportPanel from "../components/ProductImportPanel";
import UpsellSuggestionsPanel from "../components/UpsellSuggestionsPanel";
import StepLayout from "../components/cockpit/StepLayout";
import { useStepGuard } from "../lib/useStepGuard";

/**
 * Upsells page — étape 3 (Phase 3.1 — wrappée dans StepLayout).
 */
export default function SiteUpsells() {
  const { id: siteId } = useParams();
  const { allowed, checking } = useStepGuard(siteId, "upsells");
  const [site, setSite] = useState(null);
  const [productsCount, setProductsCount] = useState(0);

  useEffect(() => {
    if (!siteId) return;
    (async () => {
      const { data } = await apiCall(() => api.get(`/sites/${siteId}`));
      if (data) setSite(data);
      const { data: prods } = await apiCall(() => api.get(`/sites/${siteId}/products`));
      if (Array.isArray(prods)) {
        setProductsCount(prods.filter((p) => p.status !== "deleted").length);
      }
    })();
  }, [siteId]);

  if (checking) {
    return (
      <div className="min-h-screen bg-[#F5F2EB] flex items-center justify-center">
        <div className="text-sm text-neutral-500">Vérification des prérequis…</div>
      </div>
    );
  }
  if (!allowed) return null;

  const targetCountries =
    site?.selected_countries || site?.countries || (site?.country ? [site.country] : []);
  const nicheHint = site?.niche_name || site?.niche?.name || site?.name || "";

  return (
    <StepLayout
      siteId={siteId}
      stepKey="upsells"
      title="Upsells & accessoires"
      subtitle="Ajoute des produits complémentaires pour augmenter le panier moyen."
      estimatedTime="~3 min"
      whatItDoes="L'IA identifie 3 à 5 accessoires cohérents avec tes produits principaux (câbles, housses, consommables, extensions de garantie…). Ils seront proposés en cross-sell sur la fiche produit et en post-purchase. Minimum 3 upsells requis pour débloquer le prévisionnel financier."
    >
      <div className="text-[13px] text-neutral-600 mb-5">
        {nicheHint ? <>Niche&nbsp;: <strong className="text-neutral-900">{nicheHint}</strong> · </> : null}
        Pays cibles&nbsp;: <strong className="text-neutral-900">{targetCountries.join(" · ") || "aucun défini"}</strong>
      </div>

      <ProductImportPanel
        siteId={siteId}
        variant="upsell"
        nicheHint={nicheHint}
        targetCountries={targetCountries}
      />

      <div className="mt-8">
        <UpsellSuggestionsPanel siteId={siteId} productsCount={productsCount} />
      </div>
    </StepLayout>
  );
}
