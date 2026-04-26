import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { ArrowLeft, Stack } from "@phosphor-icons/react";
import { api, apiCall } from "../lib/api";
import ProductImportPanel from "../components/ProductImportPanel";
import NextStepCTA from "../components/NextStepCTA";
import { useStepGuard } from "../lib/useStepGuard";

/**
 * Upsells page — étape 3.
 * Chantier 4 : utilise <ProductImportPanel variant="upsell" /> (même logique que
 * l'import principal, mais : pré-remplit la recherche avec "niche + accessoires",
 * tagge les produits importés comme type="upsell", affiche un encadré spécifique).
 */
export default function SiteUpsells() {
  const { id: siteId } = useParams();
  const { allowed, checking } = useStepGuard(siteId, "upsells");
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
            <Stack size={12} weight="bold" /> Étape 3 · Upsells & accessoires
          </div>
          <h1 className="text-2xl md:text-3xl font-semibold text-neutral-900" style={{ fontFamily: "'Fraunces', serif" }}>
            Ajouter des accessoires complémentaires
          </h1>
          <p className="text-sm text-neutral-600 mt-2">
            {nicheHint ? <>Niche&nbsp;: <strong>{nicheHint}</strong> · </> : null}
            Pays cibles&nbsp;: <strong>{targetCountries.join(" · ") || "aucun défini"}</strong> · Minimum 3 upsells pour débloquer l'étape 4 (prévisionnel).
          </p>
        </div>

        <ProductImportPanel
          siteId={siteId}
          variant="upsell"
          nicheHint={nicheHint}
          targetCountries={targetCountries}
        />

        <NextStepCTA siteId={siteId} currentKey="upsells" />
      </div>
    </div>
  );
}
