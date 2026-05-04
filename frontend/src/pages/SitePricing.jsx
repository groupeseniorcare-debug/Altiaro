import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { Sparkle } from "@phosphor-icons/react";
import { api, apiCall } from "../lib/api";
import StepLayout from "../components/cockpit/StepLayout";

/**
 * SitePricing (Phase 3.0 — pilote UX refonte)
 *
 * Wrappée dans <StepLayout /> pour donner la nouvelle charte « Luxury Minimal ».
 * Logique métier inchangée : lecture + déclenchement de l'analyse pricing IA.
 */
export default function SitePricing() {
  const { id: siteId } = useParams();
  const [pricing, setPricing] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    apiCall(() => api.get(`/sites/${siteId}/pricing-analysis`)).then(({ data }) => {
      if (data && data.generated_at) setPricing(data);
    });
  }, [siteId]);

  const run = async () => {
    setLoading(true);
    const { data, error } = await apiCall(() =>
      api.post(`/sites/${siteId}/pricing-analysis`, { site_id: siteId })
    );
    setLoading(false);
    if (error) {
      window.alert(error);
      return;
    }
    setPricing(data);
    // Signale au reste de l'app qu'une étape a bougé (bascule du journey).
    window.dispatchEvent(new CustomEvent("cf_steps_changed"));
  };

  const hasAnalysis = !!(pricing && pricing.generated_at);

  return (
    <StepLayout
      siteId={siteId}
      stepKey="pricing"
      title="Pricing & positionnement concurrentiel"
      subtitle="L'IA scanne les prix concurrents et te propose un placement optimal pour ta niche."
      estimatedTime="~2 min"
      whatItDoes="Claude identifie 3 à 5 concurrents directs (Google Shopping + AliExpress), analyse leurs prix actuels, et te suggère une fourchette de pricing premium alignée sur ton positionnement marque. Tu obtiens aussi un coût d'acquisition cible pour tes campagnes Google Ads."
      magicButton={{
        label: loading
          ? "Analyse en cours (30–60 s)…"
          : hasAnalysis
          ? "Relancer l'analyse"
          : "Lancer l'analyse IA",
        onClick: run,
        loading,
        disabled: loading,
        icon: <Sparkle size={14} weight="fill" />,
      }}
    >
      {hasAnalysis ? (
        <PricingResult pricing={pricing} />
      ) : !loading ? (
        <EmptyState />
      ) : (
        <LoadingState />
      )}
    </StepLayout>
  );
}

/* ------------------------------------------------------------------------ */
/* Sub-components                                                            */
/* ------------------------------------------------------------------------ */

function EmptyState() {
  return (
    <div
      className="bg-white/70 border border-neutral-200 rounded-2xl p-12 text-center"
      data-testid="pricing-empty"
    >
      <div
        className="text-3xl mb-3 text-neutral-400"
        style={{ fontFamily: "'Fraunces', serif" }}
      >
        —
      </div>
      <div className="font-medium text-neutral-900 mb-1">Aucune analyse encore</div>
      <div className="text-sm text-neutral-500 max-w-md mx-auto">
        Clique sur <em>« Lancer l'analyse IA »</em> en bas à droite. Claude identifie les
        concurrents de ta niche et revient avec trois fourchettes de prix.
      </div>
    </div>
  );
}

function LoadingState() {
  return (
    <div
      className="bg-white/70 border border-neutral-200 rounded-2xl p-12 text-center"
      data-testid="pricing-loading"
    >
      <div className="inline-block w-8 h-8 rounded-full border-2 border-neutral-300 border-t-neutral-900 animate-spin mb-4" />
      <div className="font-medium text-neutral-900 mb-1">Analyse en cours…</div>
      <div className="text-sm text-neutral-500">
        Claude consulte les concurrents et écrit tes fourchettes de prix. 30 à 60 secondes.
      </div>
    </div>
  );
}

function PricingResult({ pricing }) {
  return (
    <div className="space-y-6" data-testid="pricing-result">
      {/* Verdict / market overview */}
      <div className="bg-white border border-neutral-200 rounded-2xl p-6">
        <div className="text-[10px] uppercase tracking-[0.22em] text-neutral-500 mb-3 font-medium">
          Vue d'ensemble du marché
        </div>
        <p className="text-[15px] text-neutral-800 leading-relaxed">
          {pricing.market_overview}
        </p>
      </div>

      {/* Concurrents */}
      {pricing.competitors?.length > 0 && (
        <div className="bg-white border border-neutral-200 rounded-2xl p-6">
          <div className="text-[10px] uppercase tracking-[0.22em] text-neutral-500 mb-4 font-medium">
            Concurrents identifiés
          </div>
          <div className="grid md:grid-cols-2 gap-3">
            {pricing.competitors.map((c, i) => (
              <div key={i} className="p-4 rounded-xl bg-[#FAF7F0] border border-neutral-100">
                <div className="flex items-baseline justify-between gap-2">
                  <div className="font-semibold text-[15px] text-neutral-900">{c.name}</div>
                  <div className="font-mono text-xs text-neutral-700 tabular-nums">{c.price_range}</div>
                </div>
                <div className="text-[10px] uppercase tracking-[0.18em] text-neutral-500 mt-1.5 font-medium">
                  {c.positioning}
                </div>
                <div className="text-xs text-neutral-600 mt-2 leading-relaxed">{c.strengths}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Fourchettes recommandées */}
      {pricing.recommended_ranges?.length > 0 && (
        <div className="bg-white border border-neutral-200 rounded-2xl p-6">
          <div className="text-[10px] uppercase tracking-[0.22em] text-neutral-500 mb-4 font-medium">
            Fourchettes recommandées
          </div>
          <div className="space-y-4">
            {pricing.recommended_ranges.map((r, i) => (
              <div key={i} className="p-5 rounded-xl bg-[#FAF7F0] border border-neutral-100">
                <div
                  className="font-semibold text-lg text-neutral-900 mb-3"
                  style={{ fontFamily: "'Fraunces', serif" }}
                >
                  {r.product_type}
                </div>
                <div className="grid grid-cols-3 gap-3 mb-4">
                  <Tier label="Entrée" price={r.entry_eur} color="neutral" />
                  <Tier label="Sweet spot" price={r.sweet_spot_eur} color="emerald" />
                  <Tier label="Premium" price={r.premium_eur} color="amber" />
                </div>
                <div className="text-[13px] text-neutral-600 leading-relaxed">{r.rationale}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Marge + conseils */}
      <div className="grid md:grid-cols-2 gap-4">
        {pricing.margin_advice && (
          <div className="bg-emerald-50/70 border border-emerald-200 rounded-2xl p-5">
            <div className="text-[10px] uppercase tracking-[0.22em] text-emerald-700 font-medium mb-1.5">
              Marge recommandée
            </div>
            <div className="text-sm text-emerald-900 leading-relaxed">{pricing.margin_advice}</div>
          </div>
        )}
        {pricing.strategic_notes?.length > 0 && (
          <div className="bg-sky-50/70 border border-sky-200 rounded-2xl p-5">
            <div className="text-[10px] uppercase tracking-[0.22em] text-sky-700 font-medium mb-2">
              Conseils tactiques
            </div>
            <ul className="space-y-1.5 text-sm text-sky-900">
              {pricing.strategic_notes.map((n, i) => (
                <li key={i} className="flex gap-2 leading-relaxed">
                  <span className="text-sky-400">•</span>
                  {n}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      <div className="text-[11px] text-neutral-400 text-right pt-2 tabular-nums">
        Généré le {formatDateTime(pricing.generated_at)}
      </div>
    </div>
  );
}

function Tier({ label, price, color }) {
  const palette = {
    neutral: "bg-white border-neutral-200 text-neutral-900",
    emerald: "bg-emerald-50 border-emerald-300 text-emerald-900",
    amber: "bg-amber-50 border-amber-300 text-amber-900",
  };
  return (
    <div className={`p-3 rounded-lg border ${palette[color]} text-center`}>
      <div className="text-[9px] uppercase tracking-[0.22em] font-medium mb-1.5 opacity-70">
        {label}
      </div>
      <div
        className="text-2xl font-normal tabular-nums"
        style={{ fontFamily: "'Fraunces', serif" }}
      >
        {price} €
      </div>
    </div>
  );
}
