import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api, apiCall } from "../lib/api";
import ProductImportPanel from "../components/ProductImportPanel";
import AeDealsPanel from "../components/AeDealsPanel";
import StepLayout from "../components/cockpit/StepLayout";
import { useStepGuard } from "../lib/useStepGuard";

/**
 * Sourcing — étape 2 (import catalogue).
 * Phase 3.1 (2026-05-04) — wrap StepLayout.
 */
export default function Sourcing() {
  const { id: siteId } = useParams();
  const { allowed, checking } = useStepGuard(siteId, "import");
  const [site, setSite] = useState(null);

  useEffect(() => {
    if (!siteId) return;
    (async () => {
      const { data } = await apiCall(() => api.get(`/sites/${siteId}`));
      if (data) setSite(data);
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
      stepKey="import"
      title="Import du catalogue"
      subtitle="Constitue ton catalogue à partir d'AliExpress ou manuellement."
      estimatedTime="~5 min"
      whatItDoes="Recherche les meilleurs produits de ta niche sur AliExpress (filtres volume, marge, shipping EU), sélectionne 5 à 15 hero products, importe-les en un clic. L'IA reformule automatiquement les titres, descriptions, SEO et génère des images premium à la marque. Les deals AliExpress pertinents sont surfacés en bas de page."
    >
      {site && (
        <div className="text-[13px] text-neutral-600 mb-5">
          {nicheHint ? <>Niche&nbsp;: <strong className="text-neutral-900">{nicheHint}</strong> · </> : null}
          Pays cibles&nbsp;: <strong className="text-neutral-900">{targetCountries.join(" · ") || "aucun défini"}</strong>
        </div>
      )}

      <ProductImportPanel
        siteId={siteId}
        variant="main"
        nicheHint={nicheHint}
        targetCountries={targetCountries}
      />

      <div className="mt-10" data-testid="sourcing-ae-deals-section">
        <AeDealsPanel siteId={siteId} />
      </div>
    </StepLayout>
  );
}
