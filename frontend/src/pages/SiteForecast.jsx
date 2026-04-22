import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import {
  ArrowLeft, ChartLineUp, Sparkle, ArrowClockwise, TrendUp, Warning, CheckCircle,
  Info, Globe, Lightbulb, ArrowUp, Question, Receipt, CaretDown, Calculator,
  LockSimple, Rocket,
} from "@phosphor-icons/react";
import { api, apiCall } from "../lib/api";

const SCENARIO_META = {
  pessimistic: { color: "text-rose-700", bg: "bg-rose-50", border: "border-rose-200", accent: "#BE123C" },
  realistic:   { color: "text-neutral-900", bg: "bg-white", border: "border-neutral-900", accent: "#1C1917" },
  optimistic: { color: "text-emerald-700", bg: "bg-emerald-50", border: "border-emerald-200", accent: "#047857" },
};
const VERDICT_META = {
  healthy:    { label: "Projet rentable", Icon: CheckCircle, bg: "bg-emerald-50", border: "border-emerald-200", text: "text-emerald-800", fill: "text-emerald-600" },
  acceptable: { label: "Projet viable, à optimiser", Icon: TrendUp, bg: "bg-amber-50", border: "border-amber-200", text: "text-amber-800", fill: "text-amber-600" },
  risky:      { label: "Pivot recommandé", Icon: Warning, bg: "bg-rose-50", border: "border-rose-200", text: "text-rose-800", fill: "text-rose-600" },
};
const SEVERITY_META = {
  success: { Icon: CheckCircle, color: "text-emerald-700", bg: "bg-emerald-50", border: "border-emerald-200" },
  info:    { Icon: Lightbulb, color: "text-sky-700", bg: "bg-sky-50", border: "border-sky-200" },
  warning: { Icon: Warning, color: "text-amber-700", bg: "bg-amber-50", border: "border-amber-200" },
};

const fmtEur = (n, dec = 0) =>
  (Number(n) || 0).toLocaleString("fr-FR", { minimumFractionDigits: dec, maximumFractionDigits: dec }) + " €";
const fmtNum = (n) => (Number(n) || 0).toLocaleString("fr-FR");
const fmtPct = (n, dec = 1) => `${(Number(n) || 0).toFixed(dec)} %`;

export default function SiteForecast() {
  const { id: siteId } = useParams();
  const [forecast, setForecast] = useState(null);
  const [loading, setLoading] = useState(false);
  const [dailyBudget, setDailyBudget] = useState(30);
  const [concepteurShare, setConcepteurShare] = useState(15);
  const [activeScenario, setActiveScenario] = useState("realistic");
  const [showFormulas, setShowFormulas] = useState(false);
  const [validating, setValidating] = useState(false);
  const [isValidated, setIsValidated] = useState(false);

  useEffect(() => {
    Promise.all([
      apiCall(() => api.get(`/sites/${siteId}/financial-forecast`)),
      apiCall(() => api.get(`/sites/${siteId}`)),
    ]).then(([fc, s]) => {
      if (fc.data && fc.data.generated_at) setForecast(fc.data);
      setIsValidated((s.data?.journey_validated || []).includes("forecast"));
    });
  }, [siteId]);

  const run = async () => {
    setLoading(true);
    const { data, error } = await apiCall(() =>
      api.post(`/sites/${siteId}/financial-forecast`, {
        site_id: siteId,
        daily_budget_total_eur: Number(dailyBudget),
        concepteur_share_eur: Number(concepteurShare),
      })
    );
    setLoading(false);
    if (error) { window.alert(error); return; }
    setForecast(data);
  };

  const verdict = forecast ? VERDICT_META[forecast.verdict] : null;
  const scen = forecast?.scenarios?.[activeScenario];
  const gate = forecast?.launch_gate;

  const validateStep = async () => {
    if (!gate || gate.status === "blocked") return;
    setValidating(true);
    const { error } = await apiCall(() =>
      api.post(`/sites/${siteId}/journey/validate-step`, { step: "forecast", validated: true })
    );
    setValidating(false);
    if (error) { window.alert(error); return; }
    setIsValidated(true);
  };

  return (
    <div className="min-h-screen bg-[#FAF7F2]">
      <div className="max-w-6xl mx-auto px-6 md:px-10 py-8">
        <Link to={`/sites/${siteId}`} className="inline-flex items-center gap-2 text-sm text-neutral-600 hover:text-neutral-900 mb-6">
          <ArrowLeft size={14} /> Retour au cockpit
        </Link>

        <div className="mb-8">
          <div className="text-[11px] uppercase tracking-[0.2em] text-neutral-500 mb-2 flex items-center gap-2">
            <ChartLineUp size={12} weight="bold" /> Étape 4 · Prévisionnel 30 jours
          </div>
          <h1 className="text-3xl md:text-4xl font-semibold text-neutral-900" style={{ fontFamily: "'Fraunces', serif" }}>
            Analyse financière complète
          </h1>
          <p className="text-sm text-neutral-500 mt-2 max-w-3xl">
            3 scénarios, détail par marché avec HT/TTC/TVA, compte de résultat consolidé, simulations what-if et recommandations actionnables.
          </p>
        </div>

        {/* Budget inputs */}
        <div className="bg-white border border-neutral-200 rounded-2xl p-5 mb-6 flex flex-wrap items-end gap-4">
          <BudgetInput label="Budget Ads / jour / marché" value={dailyBudget} onChange={setDailyBudget} testid="forecast-daily-budget" />
          <BudgetInput label="Ta part quotidienne (reste = Altiaro)" value={concepteurShare} onChange={setConcepteurShare} testid="forecast-concepteur-share" max={dailyBudget} />
          <button
            onClick={run}
            disabled={loading}
            data-testid="forecast-run"
            className="h-11 px-5 rounded-xl bg-neutral-900 hover:bg-neutral-800 text-white text-sm font-medium flex items-center gap-2 disabled:opacity-60 ml-auto"
          >
            {loading ? <ArrowClockwise size={14} className="animate-spin" /> : <Sparkle size={14} weight="fill" />}
            {loading ? "Calcul…" : (forecast ? "Recalculer" : "Calculer le prévisionnel")}
          </button>
        </div>

        {!forecast && !loading && (
          <div className="bg-white border border-dashed border-neutral-200 rounded-2xl p-12 text-center">
            <ChartLineUp size={40} weight="duotone" className="mx-auto text-neutral-400 mb-3" />
            <div className="text-base font-semibold text-neutral-900 mb-1" style={{ fontFamily: "'Fraunces', serif" }}>
              Aucun prévisionnel encore
            </div>
            <div className="text-sm text-neutral-500 max-w-md mx-auto">
              Clique sur « Calculer le prévisionnel » — résultat instantané avec 3 scénarios et tous tes marchés.
            </div>
          </div>
        )}

        {forecast && (
          <div className="space-y-6" data-testid="forecast-result">
            {/* LAUNCH GATE — the critical safety check */}
            {gate && (
              <LaunchGateBanner gate={gate} isValidated={isValidated} />
            )}

            {/* Verdict */}
            {verdict && (
              <div className={`rounded-2xl border p-5 ${verdict.bg} ${verdict.border} flex items-start gap-3`}>
                <verdict.Icon size={28} weight="fill" className={verdict.fill + " flex-shrink-0 mt-0.5"} />
                <div>
                  <div className={`text-lg font-semibold ${verdict.text}`}>{verdict.label}</div>
                  <div className={`text-sm ${verdict.text} opacity-90 mt-0.5`}>
                    Scénario réaliste : {fmtNum(forecast.scenarios.realistic.global.conversions)} ventes · CA HT{" "}
                    <strong>{fmtEur(forecast.scenarios.realistic.global.revenue_ht_eur)}</strong> · ROAS <strong>{forecast.scenarios.realistic.global.roas}x</strong>
                    {" · "}marge pour toi <strong>{fmtEur(forecast.scenarios.realistic.global.net_margin_concepteur_eur)}</strong>
                  </div>
                </div>
              </div>
            )}

            {/* 3 scenarios cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {["pessimistic", "realistic", "optimistic"].map((k) => {
                const s = forecast.scenarios[k];
                const m = SCENARIO_META[k];
                const isActive = activeScenario === k;
                return (
                  <button
                    key={k}
                    onClick={() => setActiveScenario(k)}
                    data-testid={`scenario-card-${k}`}
                    className={`text-left rounded-2xl border-2 p-5 transition ${
                      isActive ? `${m.border} shadow-md` : "border-neutral-200 hover:border-neutral-400"
                    } ${m.bg}`}
                  >
                    <div className="flex items-center justify-between mb-3">
                      <div className={`text-[10px] uppercase tracking-[0.2em] font-semibold ${m.color}`}>{s.label}</div>
                      {isActive && <div className="w-2 h-2 rounded-full" style={{ background: m.accent }} />}
                    </div>
                    <div className="text-3xl font-semibold tabular-nums leading-none" style={{ fontFamily: "'Fraunces', serif", color: m.accent }}>
                      {fmtEur(s.global.revenue_ht_eur)}
                    </div>
                    <div className="text-xs text-neutral-500 mt-1">CA HT / 30 jours</div>
                    <div className="text-[11px] text-neutral-400 tabular-nums mt-0.5">
                      ({fmtEur(s.global.revenue_ttc_eur)} TTC)
                    </div>
                    <div className="grid grid-cols-2 gap-2 mt-4 pt-3 border-t border-neutral-200/60 text-xs">
                      <Kpi label="ROAS" value={`${s.global.roas}x`} />
                      <Kpi label="Ventes" value={fmtNum(s.global.conversions)} />
                      <Kpi label="Marge brute HT" value={`${fmtEur(s.global.gross_margin_eur)} (${fmtPct(s.global.gross_margin_pct, 0)})`} />
                      <Kpi
                        label="Net pour toi"
                        value={fmtEur(s.global.net_margin_concepteur_eur)}
                        color={s.global.net_margin_concepteur_eur >= 0 ? "text-emerald-700" : "text-rose-700"}
                      />
                    </div>
                    <div className="text-[11px] text-neutral-500 mt-3 leading-relaxed">{s.description}</div>
                  </button>
                );
              })}
            </div>

            {/* Per-market detailed table */}
            {scen && (
              <div className="bg-white border border-neutral-200 rounded-2xl overflow-hidden">
                <div className="p-5 border-b border-neutral-100 flex items-start justify-between flex-wrap gap-3">
                  <div>
                    <div className="text-[11px] uppercase tracking-widest text-neutral-500 mb-1 flex items-center gap-1">
                      <Globe size={11} /> Détail par marché · scénario {scen.label.toLowerCase()}
                    </div>
                    <h2 className="text-xl font-semibold text-neutral-900" style={{ fontFamily: "'Fraunces', serif" }}>
                      Panier moyen {fmtEur(scen.params.avg_order_value_ttc_eur)} TTC
                      <span className="text-sm font-normal text-neutral-500 ml-2">dont {fmtEur(scen.params.cogs_per_order_eur)} de coût + {fmtEur(scen.params.shipping_cost_per_order_eur)} de livraison</span>
                    </h2>
                  </div>
                  <div className="text-xs text-neutral-500 flex gap-4 flex-wrap">
                    <Badge label="CR" value={`${scen.params.conv_rate_pct} %`} hint="Taux de conversion : % de clics qui achètent" />
                    <Badge label="Attach" value={`${scen.params.upsell_attach_rate_pct} %`} hint="% de commandes avec un upsell ajouté" />
                    <Badge label="Marge/cmde" value={fmtEur(scen.params.gross_per_order_eur)} hint="Gain brut par commande après coût et livraison" />
                  </div>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="bg-neutral-50 border-b border-neutral-200 text-[11px] uppercase tracking-wider text-neutral-600">
                      <tr>
                        <th className="text-left py-2 px-3">Marché</th>
                        <th className="text-right py-2 px-3">CPC</th>
                        <th className="text-right py-2 px-3">TVA</th>
                        <th className="text-right py-2 px-3">Ventes</th>
                        <th className="text-right py-2 px-3">CPA</th>
                        <th className="text-right py-2 px-3">CA TTC</th>
                        <th className="text-right py-2 px-3">CA HT</th>
                        <th className="text-right py-2 px-3">TVA collectée</th>
                        <th className="text-right py-2 px-3">Coût march.</th>
                        <th className="text-right py-2 px-3">Budget Ads</th>
                        <th className="text-right py-2 px-3">Marge brute</th>
                        <th className="text-right py-2 px-3">ROAS</th>
                        <th className="text-right py-2 px-3">Seuil rent.</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-neutral-100">
                      {Object.entries(scen.per_market).map(([cc, pm]) => (
                        <tr key={cc} data-testid={`market-row-${cc}`} className="hover:bg-neutral-50">
                          <td className="py-3 px-3 font-medium">
                            {cc}
                            {pm.competition_index > 70 && (
                              <span className="ml-1 text-[10px] px-1.5 py-0.5 rounded-full bg-amber-100 text-amber-800 font-medium">
                                saturé
                              </span>
                            )}
                          </td>
                          <td className="py-3 px-3 text-right font-mono text-neutral-700">{pm.cpc_eur.toFixed(2)} €</td>
                          <td className="py-3 px-3 text-right font-mono text-neutral-500 text-xs">{pm.vat_pct} %</td>
                          <td className="py-3 px-3 text-right font-mono font-semibold">{fmtNum(pm.monthly_conversions)}</td>
                          <td className="py-3 px-3 text-right font-mono text-neutral-600 text-xs">{fmtEur(pm.cpa_real_eur)}</td>
                          <td className="py-3 px-3 text-right font-mono text-neutral-700">{fmtEur(pm.revenue_ttc_eur)}</td>
                          <td className="py-3 px-3 text-right font-mono font-semibold text-neutral-900">{fmtEur(pm.revenue_ht_eur)}</td>
                          <td className="py-3 px-3 text-right font-mono text-neutral-500 text-xs">{fmtEur(pm.vat_collected_eur)}</td>
                          <td className="py-3 px-3 text-right font-mono text-rose-700 text-xs">- {fmtEur(pm.cogs_eur)}</td>
                          <td className="py-3 px-3 text-right font-mono text-rose-700 text-xs">- {fmtEur(pm.ad_spend_eur)}</td>
                          <td className={`py-3 px-3 text-right font-mono font-semibold ${pm.gross_margin_eur >= 0 ? "text-emerald-700" : "text-rose-700"}`}>
                            {fmtEur(pm.gross_margin_eur)}
                            <div className="text-[10px] font-normal opacity-70">{fmtPct(pm.gross_margin_pct, 0)}</div>
                          </td>
                          <td className={`py-3 px-3 text-right font-mono font-semibold ${pm.roas >= 2.5 ? "text-emerald-700" : pm.roas >= 1.8 ? "text-amber-700" : "text-rose-700"}`}>
                            {pm.roas}x
                          </td>
                          <td className="py-3 px-3 text-right font-mono text-neutral-500 text-xs">
                            {pm.break_even_monthly_conv !== null ? `${pm.break_even_monthly_conv} vtes` : "—"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                    <tfoot className="bg-neutral-900 text-white">
                      <tr>
                        <td className="py-3 px-3 text-[11px] uppercase tracking-widest">Global</td>
                        <td colSpan="2"></td>
                        <td className="py-3 px-3 text-right font-mono font-semibold">{fmtNum(scen.global.conversions)}</td>
                        <td className="py-3 px-3 text-right font-mono text-xs opacity-80">{fmtEur(scen.global.cpa_real_eur)}</td>
                        <td className="py-3 px-3 text-right font-mono">{fmtEur(scen.global.revenue_ttc_eur)}</td>
                        <td className="py-3 px-3 text-right font-mono font-bold">{fmtEur(scen.global.revenue_ht_eur)}</td>
                        <td className="py-3 px-3 text-right font-mono text-xs opacity-80">{fmtEur(scen.global.vat_collected_eur)}</td>
                        <td className="py-3 px-3 text-right font-mono text-xs opacity-80">- {fmtEur(scen.global.cogs_eur)}</td>
                        <td className="py-3 px-3 text-right font-mono text-xs opacity-80">- {fmtEur(scen.global.ad_spend_eur)}</td>
                        <td className="py-3 px-3 text-right font-mono font-bold">
                          {fmtEur(scen.global.gross_margin_eur)}
                          <div className="text-[10px] font-normal opacity-70">{fmtPct(scen.global.gross_margin_pct, 0)}</div>
                        </td>
                        <td className="py-3 px-3 text-right font-mono font-bold">{scen.global.roas}x</td>
                        <td className="py-3 px-3"></td>
                      </tr>
                    </tfoot>
                  </table>
                </div>
                <div className="p-4 border-t border-neutral-100 text-[11px] text-neutral-500 leading-relaxed">
                  <strong className="text-neutral-700">Seuil rent.</strong> = nombre de ventes minimum nécessaires par mois pour couvrir le budget Ads.
                  Si ton scénario {scen.label.toLowerCase()} passe au-dessus, tu es rentable.
                </div>
              </div>
            )}

            {/* Compte de résultat consolidé */}
            {scen && (
              <div className="bg-white border border-neutral-200 rounded-2xl overflow-hidden" data-testid="consolidated-pnl">
                <div className="p-5 border-b border-neutral-100 flex items-center gap-2">
                  <Receipt size={16} weight="duotone" className="text-neutral-700" />
                  <div>
                    <div className="text-[11px] uppercase tracking-widest text-neutral-500">Compte de résultat consolidé · 30 jours</div>
                    <h2 className="text-xl font-semibold text-neutral-900" style={{ fontFamily: "'Fraunces', serif" }}>
                      Cascade TTC → Net pour toi
                    </h2>
                  </div>
                </div>
                <div className="divide-y divide-neutral-100">
                  <PnlRow label="Chiffre d'affaires TTC" value={scen.global.revenue_ttc_eur} />
                  <PnlRow label="– TVA collectée" value={-scen.global.vat_collected_eur} muted description="Reversée à l'État (taux moyen pondéré)" />
                  <PnlRow label="= Chiffre d'affaires HT" value={scen.global.revenue_ht_eur} bold />
                  <PnlRow label="– Coût marchandises (achat fournisseur)" value={-scen.global.cogs_eur} muted description="Payé à CJ Dropshipping / AliExpress" />
                  <PnlRow label="– Frais de livraison" value={-scen.global.shipping_eur} muted description="Coût moyen transporteur · ~6 €/commande" />
                  <PnlRow label="– Budget publicitaire" value={-scen.global.ad_spend_eur} muted description="Google Ads · couvert 50/50 avec Altiaro" />
                  <PnlRow
                    label="= Marge brute"
                    value={scen.global.gross_margin_eur}
                    bold
                    accent={scen.global.gross_margin_eur >= 0 ? "emerald" : "rose"}
                    description={`${fmtPct(scen.global.gross_margin_pct, 1)} du CA HT`}
                  />
                  <PnlRow label="– Commission Altiaro (50%)" value={-scen.global.commission_altiaro_eur} muted description="Plateforme · couvre hébergement, IA, support" />
                  <PnlRow
                    label="= Marge nette pour toi"
                    value={scen.global.net_margin_concepteur_eur}
                    bold
                    xl
                    accent={scen.global.net_margin_concepteur_eur >= 0 ? "emerald" : "rose"}
                    description="Ce que tu encaisses réellement après tous les coûts"
                  />
                </div>
              </div>
            )}

            {/* Formules collapsible */}
            <div className="bg-neutral-50 rounded-2xl border border-neutral-200">
              <button
                onClick={() => setShowFormulas((v) => !v)}
                data-testid="toggle-formulas"
                className="w-full p-4 flex items-center justify-between text-sm font-medium text-neutral-700 hover:bg-neutral-100 transition"
              >
                <span className="flex items-center gap-2">
                  <Calculator size={14} weight="bold" /> Comment on calcule tout ça ?
                </span>
                <CaretDown size={14} className={`transition-transform ${showFormulas ? "rotate-180" : ""}`} />
              </button>
              {showFormulas && (
                <div className="px-4 pb-4 text-xs text-neutral-600 leading-relaxed space-y-2 border-t border-neutral-200">
                  <div className="mt-3"><strong>1. Clics/jour</strong> = budget Ads ÷ CPC (Google) · ex : 30 € ÷ 1,20 € = 25 clics</div>
                  <div><strong>2. Ventes/jour</strong> = clics × taux de conversion (CR) · Silver Eco réaliste ≈ 1,5 %</div>
                  <div><strong>3. Panier moyen (AOV)</strong> = prix produit principal + (attach rate × prix upsell remisé -20%)</div>
                  <div><strong>4. CA TTC / 30j</strong> = ventes × AOV · puis CA HT = CA TTC ÷ (1 + TVA marché)</div>
                  <div><strong>5. Marge brute</strong> = CA HT − coût marchandises − frais livraison − budget Ads</div>
                  <div><strong>6. Net pour toi</strong> = Marge brute × 50 % (l'autre 50 % = commission Altiaro qui finance la plateforme)</div>
                  <div><strong>7. ROAS</strong> = CA TTC ÷ budget Ads · <span className="text-emerald-700">≥ 2,5 x</span> = sain, <span className="text-amber-700">1,8-2,5 x</span> = acceptable, <span className="text-rose-700">{`< 1,8 x`}</span> = risqué</div>
                  <div><strong>8. CPA réel</strong> = budget Ads ÷ ventes · à comparer avec ta marge par commande</div>
                  <div className="pt-2 text-neutral-500 italic">
                    Les CPC Google sont extraits de ton Niche Analysis si elle existe (sinon fallback par pays). Les taux de conversion viennent de benchmarks Silver Economy 2024.
                  </div>
                </div>
              )}
            </div>

            {/* Catalog + Google data */}
            <div className="grid md:grid-cols-2 gap-5">
              <div className="bg-white border border-neutral-200 rounded-2xl p-5">
                <div className="text-[11px] uppercase tracking-widest text-neutral-500 mb-3">Ton catalogue</div>
                <div className="space-y-2 text-sm">
                  <Row label="Produits principaux" value={forecast.catalog.main_products_count} />
                  <Row label="Upsells" value={`${forecast.catalog.upsells_count} · couverture ${forecast.catalog.upsell_coverage_pct}%`} />
                  <div className="pt-2 mt-2 border-t border-neutral-100 space-y-1">
                    <Row label="Prix moyen produit TTC" value={fmtEur(forecast.catalog.avg_main_price_eur)} />
                    <Row label="Coût moyen produit HT" value={fmtEur(forecast.catalog.avg_main_cost_eur)} />
                    <Row label="Marge produit" value={fmtPct(forecast.catalog.avg_main_margin_pct)} highlight />
                  </div>
                  {forecast.catalog.upsells_count > 0 && (
                    <div className="pt-2 mt-2 border-t border-neutral-100 space-y-1">
                      <Row label="Prix upsell après -20%" value={fmtEur(forecast.catalog.avg_upsell_price_eur)} small />
                      <Row label="Coût upsell" value={fmtEur(forecast.catalog.avg_upsell_cost_eur)} small />
                      <Row label="Marge upsell" value={fmtPct(forecast.catalog.avg_upsell_margin_pct)} small />
                    </div>
                  )}
                </div>
              </div>

              <div className="bg-white border border-neutral-200 rounded-2xl p-5">
                <div className="text-[11px] uppercase tracking-widest text-neutral-500 mb-3 flex items-center gap-1">
                  <Globe size={11} /> Données Google par marché
                </div>
                <div className="space-y-2 text-sm">
                  {Object.entries(forecast.google_data.per_market).map(([cc, g]) => (
                    <div key={cc} className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-semibold w-10">{cc}</span>
                        {!g.has_real_data && (
                          <span className="text-[10px] text-amber-700 bg-amber-50 px-1.5 py-0.5 rounded-full" title="Fallback — lance une Niche Analysis">
                            estimé
                          </span>
                        )}
                      </div>
                      <div className="text-xs text-neutral-600 font-mono">
                        CPC <strong className="text-neutral-900">{g.cpc_eur.toFixed(2)}€</strong>
                        {g.volume_monthly > 0 && <> · vol <strong className="text-neutral-900">{fmtNum(g.volume_monthly)}</strong>/mo</>}
                        {g.competition_index > 0 && <> · comp <strong className="text-neutral-900">{g.competition_index}</strong></>}
                      </div>
                    </div>
                  ))}
                </div>
                {Object.values(forecast.google_data.per_market).some((g) => !g.has_real_data) && (
                  <div className="mt-3 text-[11px] text-amber-700 bg-amber-50 p-2 rounded-lg flex items-start gap-1.5">
                    <Info size={11} className="mt-0.5 shrink-0" />
                    <div>Lance une Niche Analysis depuis l'étape 1 pour avoir les CPC Google réels sur tous tes marchés.</div>
                  </div>
                )}
              </div>
            </div>

            {/* Sensitivity */}
            <div className="bg-gradient-to-br from-indigo-50 to-white border border-indigo-200 rounded-2xl p-5">
              <div className="flex items-center gap-2 mb-3">
                <ArrowUp size={14} weight="bold" className="text-indigo-700" />
                <div className="text-[11px] uppercase tracking-widest text-indigo-700 font-semibold">
                  Simulations · que se passe-t-il si…
                </div>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <Sensitivity label="Upsell attach +10 pts" value={forecast.sensitivity.revenue_gain_if_upsell_attach_plus_10pts_eur} hint="ajoute des upsells mieux ciblés à l'étape 3" />
                <Sensitivity label="Prix moyen +10 €" value={forecast.sensitivity.revenue_gain_if_avg_price_plus_10eur} hint="positionne-toi plus premium ou bundle" />
                <Sensitivity label="Budget Ads × 2" value={forecast.sensitivity.revenue_gain_if_daily_budget_doubled_eur} hint="si ROAS solide, scale avec confiance" />
              </div>
            </div>

            {/* Insights */}
            {forecast.insights?.length > 0 && (
              <div className="space-y-3" data-testid="forecast-insights">
                <div className="text-[11px] uppercase tracking-widest text-neutral-500 mb-1 flex items-center gap-1">
                  <Lightbulb size={11} /> Recommandations actionables
                </div>
                {forecast.insights.map((i, idx) => {
                  const m = SEVERITY_META[i.severity] || SEVERITY_META.info;
                  return (
                    <div key={idx} data-testid={`insight-${i.severity}-${idx}`} className={`border rounded-2xl p-4 flex gap-3 ${m.bg} ${m.border}`}>
                      <m.Icon size={18} weight="fill" className={`${m.color} flex-shrink-0 mt-0.5`} />
                      <div className="flex-1 min-w-0">
                        <div className={`text-sm font-semibold ${m.color}`}>{i.title}</div>
                        <div className="text-xs text-neutral-600 mt-1 leading-relaxed">{i.body}</div>
                        {i.products?.length > 0 && (
                          <div className="mt-2 space-y-1">
                            {i.products.map((p) => (
                              <div key={p.id} className="text-xs font-mono bg-white/60 rounded px-2 py-1 flex justify-between">
                                <span className="truncate mr-2">{p.name}</span>
                                <span className="text-rose-700 font-semibold shrink-0">marge {p.margin_pct}%</span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

            <div className="text-[11px] text-neutral-400 text-right">
              Généré le {new Date(forecast.generated_at).toLocaleString("fr-FR")}
            </div>

            {/* Launch validation CTA — only if gate allows */}
            {gate && gate.status !== "blocked" && !isValidated && (
              <div className="bg-neutral-900 text-white rounded-2xl p-6 flex items-center justify-between gap-4 flex-wrap">
                <div>
                  <div className="text-[11px] uppercase tracking-[0.2em] text-white/60 mb-1">
                    Prêt à lancer ?
                  </div>
                  <div className="text-lg font-semibold" style={{ fontFamily: "'Fraunces', serif" }}>
                    Valide l'étape 4 pour débloquer la suite du cockpit
                  </div>
                  <div className="text-sm text-white/70 mt-1 max-w-2xl">
                    Tu pourras toujours recalculer ton prévisionnel plus tard si tu modifies ton catalogue ou tes upsells.
                  </div>
                </div>
                <button
                  onClick={validateStep}
                  disabled={validating}
                  data-testid="validate-forecast-btn"
                  className="h-12 px-6 rounded-xl bg-white text-neutral-900 hover:bg-neutral-100 font-semibold text-sm flex items-center gap-2 disabled:opacity-60 transition"
                >
                  {validating
                    ? <><ArrowClockwise size={16} className="animate-spin" /> Validation…</>
                    : <><Rocket size={16} weight="fill" /> Valider l'étape 4</>}
                </button>
              </div>
            )}
            {isValidated && (
              <div className="bg-emerald-50 border border-emerald-200 rounded-2xl p-4 flex items-center gap-2 text-sm text-emerald-800" data-testid="forecast-validated-badge">
                <CheckCircle size={16} weight="fill" className="text-emerald-600" />
                Étape 4 validée · prochaine étape débloquée dans le cockpit
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ---------- Small UI components ----------
function BudgetInput({ label, value, onChange, testid, max }) {
  return (
    <div>
      <label className="block text-[11px] uppercase tracking-widest text-neutral-500 mb-1">{label}</label>
      <div className="flex items-center gap-2">
        <input
          type="number"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          data-testid={testid}
          className="h-10 w-24 px-3 rounded-lg border border-neutral-200 text-sm font-mono"
          min="5"
          max={max || 500}
        />
        <span className="text-sm text-neutral-600">€</span>
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

function Kpi({ label, value, color }) {
  return (
    <div>
      <div className="text-neutral-500 text-[10px] uppercase tracking-wider">{label}</div>
      <div className={`font-mono font-semibold ${color || "text-neutral-900"}`}>{value}</div>
    </div>
  );
}

function Badge({ label, value, hint }) {
  return (
    <span title={hint} className="inline-flex items-center gap-1 h-7 px-2 rounded-full bg-neutral-100 text-[11px]">
      <span className="text-neutral-500">{label}</span>
      <strong className="text-neutral-900">{value}</strong>
      {hint && <Question size={10} className="text-neutral-400" />}
    </span>
  );
}

function Sensitivity({ label, value, hint }) {
  return (
    <div className="bg-white border border-indigo-100 rounded-xl p-3" data-testid={`sens-${label.replace(/\s/g, "-")}`}>
      <div className="text-[10px] uppercase tracking-widest text-neutral-500 mb-1">{label}</div>
      <div className="text-xl font-semibold text-emerald-700 tabular-nums" style={{ fontFamily: "'Fraunces', serif" }}>
        +{fmtEur(value)}
      </div>
      <div className="text-[10px] text-neutral-500 mt-1">{hint}</div>
    </div>
  );
}

function LaunchGateBanner({ gate, isValidated }) {
  const META = {
    ok:      { Icon: CheckCircle, bg: "bg-emerald-50", border: "border-emerald-200", text: "text-emerald-900", fill: "text-emerald-600", label: "Feu vert pour lancer" },
    warning: { Icon: Warning, bg: "bg-amber-50", border: "border-amber-200", text: "text-amber-900", fill: "text-amber-600", label: "Lancement possible mais risqué" },
    blocked: { Icon: LockSimple, bg: "bg-rose-50", border: "border-rose-300", text: "text-rose-900", fill: "text-rose-600", label: "Lancement bloqué" },
  };
  const m = META[gate.status] || META.warning;
  return (
    <div className={`rounded-2xl border-2 p-5 ${m.bg} ${m.border}`} data-testid={`launch-gate-${gate.status}`}>
      <div className="flex items-start gap-3">
        <m.Icon size={28} weight="fill" className={`${m.fill} flex-shrink-0 mt-0.5`} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <div className={`text-lg font-semibold ${m.text}`} style={{ fontFamily: "'Fraunces', serif" }}>
              {m.label}
            </div>
            {isValidated && (
              <span className="text-[10px] uppercase tracking-widest font-semibold px-2 py-0.5 rounded-full bg-emerald-900 text-emerald-50">
                validé
              </span>
            )}
          </div>
          <div className={`text-sm ${m.text} opacity-90 mt-1 leading-relaxed`}>{gate.message}</div>

          <div className="grid grid-cols-3 gap-3 mt-4">
            <div className="bg-white/70 rounded-xl p-3 border border-white/60">
              <div className="text-[10px] uppercase tracking-widest text-neutral-500">Marge / commande HT</div>
              <div className="text-xl font-semibold text-neutral-900 tabular-nums" style={{ fontFamily: "'Fraunces', serif" }}>
                {fmtEur(gate.per_order_margin_ht_eur)}
              </div>
              <div className="text-[10px] text-neutral-500">CA HT − coûts − livraison</div>
            </div>
            <div className="bg-white/70 rounded-xl p-3 border border-white/60">
              <div className="text-[10px] uppercase tracking-widest text-neutral-500">Coût d'acquisition (CPA)</div>
              <div className="text-xl font-semibold text-neutral-900 tabular-nums" style={{ fontFamily: "'Fraunces', serif" }}>
                {fmtEur(gate.per_order_cpa_eur)}
              </div>
              <div className="text-[10px] text-neutral-500">Budget Ads par vente</div>
            </div>
            <div className="bg-white/70 rounded-xl p-3 border border-white/60">
              <div className="text-[10px] uppercase tracking-widest text-neutral-500">Net profit / vente</div>
              <div className={`text-xl font-semibold tabular-nums ${gate.per_order_net_profit_eur > 0 ? "text-emerald-700" : "text-rose-700"}`}
                   style={{ fontFamily: "'Fraunces', serif" }}>
                {gate.per_order_net_profit_eur >= 0 ? "+" : ""}{fmtEur(gate.per_order_net_profit_eur)}
              </div>
              <div className="text-[10px] text-neutral-500">
                ratio <strong>{gate.safety_ratio}×</strong> · seuil min {gate.min_safety_ratio_required}×
              </div>
            </div>
          </div>

          {gate.status === "blocked" && gate.blocker?.actions?.length > 0 && (
            <div className="mt-4 pt-4 border-t border-rose-200">
              <div className="text-xs font-semibold text-rose-900 mb-2">Comment débloquer :</div>
              <ul className="space-y-1.5" data-testid="gate-actions">
                {gate.blocker.actions.map((a, i) => (
                  <li key={i} className="text-sm text-rose-800 flex items-start gap-2">
                    <span className="w-5 h-5 rounded-full bg-rose-200 text-rose-900 text-[11px] font-bold flex items-center justify-center shrink-0 mt-0.5">
                      {i + 1}
                    </span>
                    {a}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function PnlRow({ label, value, muted, bold, xl, accent, description }) {
  const val = Number(value) || 0;
  const accentClass =
    accent === "emerald" ? "text-emerald-700" :
    accent === "rose" ? "text-rose-700" :
    muted ? "text-rose-600" :
    "text-neutral-900";
  return (
    <div className={`flex items-center justify-between px-5 py-${xl ? "4" : "3"} ${bold ? "bg-neutral-50" : ""}`}>
      <div>
        <div className={`${xl ? "text-base font-semibold" : bold ? "text-sm font-semibold" : "text-sm"} text-neutral-800`}>
          {label}
        </div>
        {description && <div className="text-[11px] text-neutral-500 mt-0.5">{description}</div>}
      </div>
      <div
        className={`tabular-nums font-mono ${xl ? "text-2xl font-bold" : bold ? "text-base font-bold" : "text-sm"} ${accentClass}`}
        style={xl ? { fontFamily: "'Fraunces', serif" } : {}}
      >
        {val < 0 ? `- ${fmtEur(-val)}` : fmtEur(val)}
      </div>
    </div>
  );
}
