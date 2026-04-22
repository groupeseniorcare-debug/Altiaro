import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { ArrowLeft, ChartLineUp, Sparkle, ArrowClockwise, TrendUp, Warning, CheckCircle } from "@phosphor-icons/react";
import { api, apiCall } from "../lib/api";

export default function SiteForecast() {
  const { id: siteId } = useParams();
  const [forecast, setForecast] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    apiCall(() => api.get(`/sites/${siteId}/financial-forecast`)).then(({ data }) => {
      if (data && data.generated_at) setForecast(data);
    });
  }, [siteId]);

  const run = async () => {
    setLoading(true);
    const { data, error } = await apiCall(() =>
      api.post(`/sites/${siteId}/financial-forecast`, {
        site_id: siteId,
        daily_budget_total_eur: 30,
        concepteur_share_eur: 15,
      })
    );
    setLoading(false);
    if (error) { window.alert(error); return; }
    setForecast(data);
  };

  const verdictMeta = forecast ? {
    healthy:    { label: "Projet rentable", Icon: CheckCircle, bg: "bg-emerald-50", border: "border-emerald-200", text: "text-emerald-800", fill: "text-emerald-600" },
    acceptable: { label: "Projet viable, à optimiser", Icon: TrendUp, bg: "bg-amber-50", border: "border-amber-200", text: "text-amber-800", fill: "text-amber-600" },
    risky:      { label: "Pivot recommandé", Icon: Warning, bg: "bg-rose-50", border: "border-rose-200", text: "text-rose-800", fill: "text-rose-600" },
  }[forecast.verdict] : null;

  return (
    <div className="min-h-screen bg-[#FAF7F2]">
      <div className="max-w-5xl mx-auto px-6 md:px-10 py-8">
        <Link to={`/sites/${siteId}`} className="inline-flex items-center gap-2 text-sm text-neutral-600 hover:text-neutral-900 mb-6">
          <ArrowLeft size={14} /> Retour au cockpit
        </Link>

        <div className="mb-8">
          <div className="text-[11px] uppercase tracking-[0.2em] text-neutral-500 mb-2 flex items-center gap-2">
            <ChartLineUp size={12} weight="bold" /> Étape 4 · Prévisionnel 30 jours
          </div>
          <h1 className="text-3xl md:text-4xl font-semibold text-neutral-900" style={{ fontFamily: "'Fraunces', serif" }}>
            Ton étude financière
          </h1>
          <p className="text-sm text-neutral-500 mt-2 max-w-2xl">
            Calcul basé sur ton catalogue réel, le coût/conversion estimé par Google sur tes marchés, et un budget Altiaro de 30€/jour/marché (15 toi + 15 Altiaro).
          </p>
        </div>

        <div className="flex justify-end mb-5">
          <button
            onClick={run}
            disabled={loading}
            data-testid="forecast-run"
            className="h-11 px-5 rounded-xl bg-neutral-900 hover:bg-neutral-800 text-white text-sm font-medium flex items-center gap-2 disabled:opacity-60"
          >
            {loading ? <ArrowClockwise size={14} className="animate-spin" /> : <Sparkle size={14} weight="fill" />}
            {loading ? "Calcul…" : (forecast ? "Recalculer" : "Calculer le prévisionnel")}
          </button>
        </div>

        {forecast ? (
          <div className="space-y-5" data-testid="forecast-result">
            {verdictMeta && (
              <div className={`rounded-2xl border p-5 ${verdictMeta.bg} ${verdictMeta.border} flex items-start gap-3`}>
                <verdictMeta.Icon size={24} weight="fill" className={verdictMeta.fill + " flex-shrink-0 mt-0.5"} />
                <div>
                  <div className={`text-lg font-semibold ${verdictMeta.text}`}>{verdictMeta.label}</div>
                  <div className={`text-sm ${verdictMeta.text} opacity-90 mt-0.5`}>
                    ROAS prévisionnel <strong>{forecast.projection.roas}x</strong> · {forecast.projection.estimated_conversions} conversions estimées sur 30 jours
                  </div>
                </div>
              </div>
            )}

            <div className="grid md:grid-cols-2 gap-5">
              <div className="bg-white border border-neutral-200 rounded-2xl p-5">
                <div className="text-[11px] uppercase tracking-widest text-neutral-500 mb-3">Budget publicitaire</div>
                <div className="space-y-2 text-sm">
                  <Row label="Marchés" value={forecast.markets.join(", ") || "—"} />
                  <Row label="Budget / jour / marché" value={`${forecast.budget.daily_per_market_eur}€`} />
                  <Row label="Budget total / jour" value={`${forecast.budget.total_daily_eur}€`} />
                  <Row label="Budget total / 30 jours" value={`${forecast.budget.total_monthly_eur}€`} highlight />
                  <div className="pt-2 mt-2 border-t border-neutral-100 space-y-1">
                    <Row label="Ta part (30 jours)" value={`${forecast.budget.concepteur_monthly_eur}€`} />
                    <Row label="Part Altiaro (30 jours)" value={`${forecast.budget.platform_monthly_eur}€`} small />
                  </div>
                </div>
              </div>

              <div className="bg-white border border-neutral-200 rounded-2xl p-5">
                <div className="text-[11px] uppercase tracking-widest text-neutral-500 mb-3">Projection revenue</div>
                <div className="space-y-2 text-sm">
                  <Row label="Ventes estimées (30j)" value={forecast.projection.estimated_conversions} />
                  <Row label="Chiffre d'affaires" value={`${forecast.projection.estimated_revenue_eur.toLocaleString("fr-FR")}€`} highlight />
                  <Row label="Coût marchandise" value={`- ${forecast.projection.estimated_cogs_eur.toLocaleString("fr-FR")}€`} />
                  <Row label="Livraison" value={`- ${forecast.projection.estimated_shipping_eur.toLocaleString("fr-FR")}€`} />
                  <div className="pt-2 mt-2 border-t border-neutral-100">
                    <Row label="Marge brute" value={`${forecast.projection.gross_margin_eur.toLocaleString("fr-FR")}€`} highlight />
                    <Row label="Marge nette pour toi" value={`${forecast.projection.net_margin_concepteur_eur.toLocaleString("fr-FR")}€`} small />
                  </div>
                </div>
              </div>
            </div>

            <div className="bg-white border border-neutral-200 rounded-2xl p-5">
              <div className="text-[11px] uppercase tracking-widest text-neutral-500 mb-3">Hypothèses de calcul</div>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
                <Stat label="Prix moyen catalogue" value={`${forecast.assumptions.avg_retail_price_eur}€`} />
                <Stat label="Coût moyen fournisseur" value={`${forecast.assumptions.avg_supplier_cost_eur}€`} />
                <Stat label="Livraison moyenne" value={`${forecast.assumptions.avg_shipping_cost_eur}€`} />
                <Stat label="Coût/Conv (Google)" value={`${forecast.assumptions.estimated_cpa_eur}€`} warn />
                <Stat label="Seuil de rentabilité" value={`${forecast.assumptions.break_even_cpa_eur}€`} />
                <Stat label="Produits actifs" value={forecast.assumptions.active_products} />
              </div>
              <div className="mt-4 text-xs text-neutral-500 leading-relaxed">
                <strong>ROAS</strong> = Chiffre d'affaires / Budget Ads. Un ROAS ≥ 2,5 est considéré sain en dropshipping.
                <br />Le Coût/Conv est estimé par Google Keyword Planner sur tes marchés ciblés.
              </div>
            </div>

            <div className="text-[11px] text-neutral-400 text-right">
              Généré le {new Date(forecast.generated_at).toLocaleString("fr-FR")}
            </div>
          </div>
        ) : !loading ? (
          <div className="bg-white border border-neutral-200 rounded-2xl p-10 text-center">
            <ChartLineUp size={36} weight="duotone" className="mx-auto text-neutral-400 mb-3" />
            <div className="font-medium text-neutral-900 mb-1">Aucun prévisionnel encore</div>
            <div className="text-sm text-neutral-500">Clique sur « Calculer le prévisionnel » — instantané.</div>
          </div>
        ) : null}
      </div>
    </div>
  );
}

function Row({ label, value, highlight, small }) {
  return (
    <div className="flex items-baseline justify-between">
      <span className={`text-neutral-500 ${small ? "text-xs" : ""}`}>{label}</span>
      <span className={`tabular-nums ${highlight ? "font-semibold text-neutral-900 text-base" : "text-neutral-800"} ${small ? "text-xs" : ""}`}>{value}</span>
    </div>
  );
}

function Stat({ label, value, warn }) {
  return (
    <div>
      <div className="text-[11px] uppercase tracking-widest text-neutral-500 mb-1">{label}</div>
      <div className={`text-lg font-semibold ${warn ? "text-amber-700" : "text-neutral-900"}`} style={{ fontFamily: "'Fraunces', serif" }}>{value}</div>
    </div>
  );
}
