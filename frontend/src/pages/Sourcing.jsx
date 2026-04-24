import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { ArrowLeft, Package } from "@phosphor-icons/react";
import { api, apiCall } from "../lib/api";
import ProductImportPanel from "../components/ProductImportPanel";
import { useStepGuard } from "../lib/useStepGuard";

/**
 * Sourcing page — étape 2 (import catalogue).
 * Chantier 2 refonte : bascule sur <ProductImportPanel variant="main" />.
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
      <div className="min-h-screen bg-[#FAF7F2] flex items-center justify-center">
        <div className="text-sm text-neutral-500">Vérification des prérequis…</div>
      </div>
    );
  }
  if (!allowed) return null;

  const targetCountries =
    site?.selected_countries || site?.countries || (site?.country ? [site.country] : []);
  const nicheHint = site?.niche_name || site?.niche?.name || site?.name || "";

  return (
    <div className="min-h-screen bg-[#FAF7F2]">
      <div className="max-w-[1400px] mx-auto px-6 md:px-10 py-8">
        <Link
          to={`/sites/${siteId}`}
          className="inline-flex items-center gap-2 text-sm text-neutral-600 hover:text-neutral-900 mb-6"
          data-testid="back-to-site"
        >
          <ArrowLeft size={14} /> Retour au cockpit
        </Link>

        <div className="mb-7">
          <div className="text-[11px] uppercase tracking-[0.2em] text-neutral-500 mb-1 flex items-center gap-2">
            <Package size={12} weight="bold" /> Étape 2 · Import catalogue
          </div>
          <h1 className="text-2xl md:text-3xl font-semibold text-neutral-900" style={{ fontFamily: "'Fraunces', serif" }}>
            Constituer le catalogue du site
          </h1>
          {site && (
            <p className="text-sm text-neutral-600 mt-2">
              {nicheHint ? <>Niche&nbsp;: <strong>{nicheHint}</strong> · </> : null}
              Pays cibles&nbsp;: <strong>{targetCountries.join(" · ") || "aucun défini"}</strong>
            </p>
          )}
        </div>

        <ProductImportPanel
          siteId={siteId}
          variant="main"
          nicheHint={nicheHint}
          targetCountries={targetCountries}
        />
      </div>
    </div>
  );
}
