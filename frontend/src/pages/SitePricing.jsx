import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { ArrowLeft, CurrencyEur, Sparkle, ArrowClockwise, Info } from "@phosphor-icons/react";
import { api, apiCall } from "../lib/api";
import NextStepCTA from "../components/NextStepCTA";

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
    const { data, error } = await apiCall(() => api.post(`/sites/${siteId}/pricing-analysis`, { site_id: siteId }));
    setLoading(false);
    if (error) { window.alert(error); return; }
    setPricing(data);
  };

  return (
    <div className="min-h-screen bg-[#FAF7F2]">
      <div className="max-w-5xl mx-auto px-6 md:px-10 py-8">
        <Link to={`/sites/${siteId}`} className="inline-flex items-center gap-2 text-sm text-neutral-600 hover:text-neutral-900 mb-6">
          <ArrowLeft size={14} /> Retour au cockpit
        </Link>

        <div className="mb-8">
          <div className="text-[11px] uppercase tracking-[0.2em] text-neutral-500 mb-2 flex items-center gap-2">
            <CurrencyEur size={12} weight="bold" /> Étape 1 · Analyse concurrence &amp; pricing
          </div>
          <h1 className="text-3xl md:text-4xl font-semibold text-neutral-900" style={{ fontFamily: "'Fraunces', serif" }}>
            Prix recommandés pour ta niche
          </h1>
          <p className="text-sm text-neutral-500 mt-2 max-w-2xl">
            Claude analyse la concurrence (prix moyens, positionnement, points forts) et te recommande des fourchettes optimales pour maximiser la conversion.
          </p>
        </div>

        <div className="flex justify-end mb-5">
          <button
            onClick={run}
            disabled={loading}
            data-testid="pricing-run"
            className="h-11 px-5 rounded-xl bg-neutral-900 hover:bg-neutral-800 text-white text-sm font-medium flex items-center gap-2 disabled:opacity-60"
          >
            {loading ? <ArrowClockwise size={14} className="animate-spin" /> : <Sparkle size={14} weight="fill" />}
            {loading ? "Analyse en cours (30-60s)…" : (pricing ? "Relancer l'analyse" : "Lancer l'analyse IA")}
          </button>
        </div>

        {pricing ? (
          <div className="space-y-5" data-testid="pricing-result">
            <div className="bg-white border border-neutral-200 rounded-2xl p-5">
              <div className="text-[11px] uppercase tracking-widest text-neutral-500 mb-2">Vue d'ensemble du marché</div>
              <p className="text-sm text-neutral-800 leading-relaxed">{pricing.market_overview}</p>
            </div>

            {pricing.competitors?.length > 0 && (
              <div className="bg-white border border-neutral-200 rounded-2xl p-5">
                <div className="text-[11px] uppercase tracking-widest text-neutral-500 mb-3">Concurrents identifiés</div>
                <div className="grid md:grid-cols-2 gap-3">
                  {pricing.competitors.map((c, i) => (
                    <div key={i} className="p-3 rounded-xl bg-[#FDFBF7] border border-neutral-100">
                      <div className="flex items-baseline justify-between gap-2">
                        <div className="font-semibold text-sm text-neutral-900">{c.name}</div>
                        <div className="font-mono text-xs text-neutral-700">{c.price_range}</div>
                      </div>
                      <div className="text-[11px] uppercase tracking-widest text-neutral-500 mt-1">{c.positioning}</div>
                      <div className="text-xs text-neutral-600 mt-1">{c.strengths}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {pricing.recommended_ranges?.length > 0 && (
              <div className="bg-white border border-neutral-200 rounded-2xl p-5">
                <div className="text-[11px] uppercase tracking-widest text-neutral-500 mb-3">Fourchettes recommandées</div>
                <div className="space-y-3">
                  {pricing.recommended_ranges.map((r, i) => (
                    <div key={i} className="p-4 rounded-xl bg-[#FDFBF7] border border-neutral-100">
                      <div className="font-semibold text-neutral-900 mb-2">{r.product_type}</div>
                      <div className="grid grid-cols-3 gap-3 mb-3">
                        <Tier label="Entrée" price={r.entry_eur} color="neutral" />
                        <Tier label="Sweet spot" price={r.sweet_spot_eur} color="emerald" />
                        <Tier label="Premium" price={r.premium_eur} color="amber" />
                      </div>
                      <div className="text-xs text-neutral-600 leading-relaxed">{r.rationale}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="grid md:grid-cols-2 gap-5">
              {pricing.margin_advice && (
                <div className="bg-emerald-50 border border-emerald-200 rounded-2xl p-5">
                  <div className="text-[11px] uppercase tracking-widest text-emerald-700 font-medium mb-1">Marge recommandée</div>
                  <div className="text-sm text-emerald-900">{pricing.margin_advice}</div>
                </div>
              )}
              {pricing.strategic_notes?.length > 0 && (
                <div className="bg-sky-50 border border-sky-200 rounded-2xl p-5">
                  <div className="text-[11px] uppercase tracking-widest text-sky-700 font-medium mb-2">Conseils tactiques</div>
                  <ul className="space-y-1.5 text-sm text-sky-900">
                    {pricing.strategic_notes.map((n, i) => <li key={i} className="flex gap-2"><span>•</span>{n}</li>)}
                  </ul>
                </div>
              )}
            </div>

            <div className="text-[11px] text-neutral-400 text-right">
              Généré le {new Date(pricing.generated_at).toLocaleString("fr-FR")}
            </div>
          </div>
        ) : !loading ? (
          <div className="bg-white border border-neutral-200 rounded-2xl p-10 text-center">
            <Info size={36} weight="duotone" className="mx-auto text-neutral-400 mb-3" />
            <div className="font-medium text-neutral-900 mb-1">Aucune analyse encore</div>
            <div className="text-sm text-neutral-500">Clique sur « Lancer l'analyse IA » — 30 à 60 secondes.</div>
          </div>
        ) : null}

        <NextStepCTA siteId={siteId} currentKey="pricing" />
      </div>
    </div>
  );
}

function Tier({ label, price, color }) {
  const palette = {
    neutral: "bg-neutral-100 border-neutral-200 text-neutral-900",
    emerald: "bg-emerald-100 border-emerald-300 text-emerald-900",
    amber: "bg-amber-100 border-amber-300 text-amber-900",
  };
  return (
    <div className={`p-3 rounded-lg border ${palette[color]} text-center`}>
      <div className="text-[10px] uppercase tracking-widest font-medium mb-1 opacity-75">{label}</div>
      <div className="text-xl font-semibold" style={{ fontFamily: "'Fraunces', serif" }}>{price}€</div>
    </div>
  );
}
