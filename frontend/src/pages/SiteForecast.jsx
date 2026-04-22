import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import {
  ArrowLeft, ChartLineUp, Sparkle, ArrowClockwise, TrendUp, Warning, CheckCircle,
  Info, Globe, Lightbulb, ArrowUp,
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

const fmtEur = (n) => (Number(n) || 0).toLocaleString("fr-FR", { maximumFractionDigits: 0 }) + " €";
const fmtNum = (n) => (Number(n) || 0).toLocaleString("fr-FR");

export default function SiteForecast() {
  const { id: siteId } = useParams();
  const [forecast, setForecast] = useState(null);
  const [loading, setLoading] = useState(false);
  const [dailyBudget, setDailyBudget] = useState(30);
  const [concepteurShare, setConcepteurShare] = useState(15);
  const [activeScenario, setActiveScenario] = useState("realistic");

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
            3 scénarios · tous tes marchés
          </h1>
          <p className="text-sm text-neutral-500 mt-2 max-w-3xl">
            Projection calculée à partir de ton catalogue réel (prix / coûts / upsells), des CPC Google par marché,
            de 3 benchmarks Silver Economy et d'une vue consolidée pour décider s'il faut pivoter, ajuster tes upsells
            ou scale.
          </p>
        </div>

        {/* Budget inputs */}
        <div className="bg-white border border-neutral-200 rounded-2xl p-5 mb-6 flex flex-wrap items-end gap-4">
          <div>
            <label className="block text-[11px] uppercase tracking-widest text-neutral-500 mb-1">Budget Ads / jour / marché</label>
            <div className="flex items-center gap-2">
              <input
                type="number"
                value={dailyBudget}
                onChange={(e) => setDailyBudget(e.target.value)}
                data-testid="forecast-daily-budget"
                className="h-10 w-24 px-3 rounded-lg border border-neutral-200 text-sm font-mono"
                min="5" max="500"
              />
              <span className="text-sm text-neutral-600">€</span>
            </div>
          </div>
          <div>
            <label className="block text-[11px] uppercase tracking-widest text-neutral-500 mb-1">Ta part (reste = Altiaro)</label>
            <div className="flex items-center gap-2">
              <input
                type="number"
                value={concepteurShare}
                onChange={(e) => setConcepteurShare(e.target.value)}
                data-testid="forecast-concepteur-share"
                className="h-10 w-24 px-3 rounded-lg border border-neutral-200 text-sm font-mono"
                min="0" max={dailyBudget}
              />
              <span className="text-sm text-neutral-600">€</span>
            </div>
          </div>
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
            {/* Verdict */}
            {verdict && (
              <div className={`rounded-2xl border p-5 ${verdict.bg} ${verdict.border} flex items-start gap-3`}>
                <verdict.Icon size={28} weight="fill" className={verdict.fill + " flex-shrink-0 mt-0.5"} />
                <div>
                  <div className={`text-lg font-semibold ${verdict.text}`}>{verdict.label}</div>
                  <div className={`text-sm ${verdict.text} opacity-90 mt-0.5`}>
                    Scénario réaliste : ROAS <strong>{forecast.scenarios.realistic.global.roas}x</strong> ·{" "}
                    <strong>{fmtNum(forecast.scenarios.realistic.global.conversions)}</strong> ventes ·{" "}
                    marge nette pour toi <strong>{fmtEur(forecast.scenarios.realistic.global.net_margin_concepteur_eur)}</strong>
                  </div>
                </div>
              </div>
            )}

            {/* Scenario quick compare */}
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
                      <div className={`text-[10px] uppercase tracking-[0.2em] font-semibold ${m.color}`}>
                        {s.label}
                      </div>
                      {isActive && <div className="w-2 h-2 rounded-full" style={{ background: m.accent }} />}
                    </div>
                    <div className="text-3xl font-semibold tabular-nums" style={{ fontFamily: "'Fraunces', serif", color: m.accent }}>
                      {fmtEur(s.global.revenue_ttc_eur)}
                    </div>
                    <div className="text-xs text-neutral-500 mt-1">CA TTC / 30 jours</div>
                    <div className="grid grid-cols-2 gap-2 mt-4 pt-3 border-t border-neutral-200/60 text-xs">
                      <div>
                        <div className="text-neutral-500">ROAS</div>
                        <div className="font-mono font-semibold text-neutral-900">{s.global.roas}x</div>
                      </div>
                      <div>
                        <div className="text-neutral-500">Ventes</div>
                        <div className="font-mono font-semibold text-neutral-900">{fmtNum(s.global.conversions)}</div>
                      </div>
                      <div>
                        <div className="text-neutral-500">Marge brute</div>
                        <div className="font-mono font-semibold text-neutral-900">{fmtEur(s.global.gross_margin_eur)}</div>
                      </div>
                      <div>
                        <div className="text-neutral-500">Net (toi)</div>
                        <div className={`font-mono font-semibold ${s.global.net_margin_concepteur_eur >= 0 ? "text-emerald-700" : "text-rose-700"}`}>
                          {fmtEur(s.global.net_margin_concepteur_eur)}
                        </div>
                      </div>
                    </div>
                    <div className="text-[11px] text-neutral-500 mt-3 leading-relaxed">{s.description}</div>
                  </button>
                );
              })}
            </div>

            {/* Active scenario: per-market detail */}
            {scen && (
              <div className="bg-white border border-neutral-200 rounded-2xl overflow-hidden">
                <div className="p-5 border-b border-neutral-100 flex items-center justify-between flex-wrap gap-3">
                  <div>
                    <div className="text-[11px] uppercase tracking-widest text-neutral-500 mb-1 flex items-center gap-1">
                      <Globe size={11} /> Détail par marché
                    </div>
                    <h2 className="text-xl font-semibold text-neutral-900" style={{ fontFamily: "'Fraunces', serif" }}>
                      {scen.label} · panier moyen {fmtEur(scen.params.avg_order_value_eur)}
                    </h2>
                  </div>
                  <div className="text-xs text-neutral-500 flex gap-4">
                    <span>CR <strong>{scen.params.conv_rate_pct}%</strong></span>
                    <span>Upsell attach <strong>{scen.params.upsell_attach_rate_pct}%</strong></span>
                    <span>CPC x <strong>{scen.params.cpc_multiplier}</strong></span>
                  </div>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="bg-neutral-50 border-b border-neutral-200 text-[11px] uppercase tracking-wider text-neutral-600">
                      <tr>
                        <th className="text-left py-2 px-4">Marché</th>
                        <th className="text-right py-2 px-4">CPC</th>
                        <th className="text-right py-2 px-4">Clics/j</th>
                        <th className="text-right py-2 px-4">Ventes/30j</th>
                        <th className="text-right py-2 px-4">CA TTC</th>
                        <th className="text-right py-2 px-4">Budget Ads</th>
                        <th className="text-right py-2 px-4">Marge brute</th>
                        <th className="text-right py-2 px-4">ROAS</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-neutral-100">
                      {Object.entries(scen.per_market).map(([cc, pm]) => (
                        <tr key={cc} data-testid={`market-row-${cc}`} className="hover:bg-neutral-50">
                          <td className="py-3 px-4 font-medium">
                            {cc}
                            {pm.competition_index > 70 && (
                              <span className="ml-2 text-[10px] px-1.5 py-0.5 rounded-full bg-amber-100 text-amber-800 font-medium">
                                saturé
                              </span>
                            )}
                          </td>
                          <td className="py-3 px-4 text-right font-mono text-neutral-700">{pm.cpc_eur.toFixed(2)} €</td>
                          <td className="py-3 px-4 text-right font-mono text-neutral-700">{pm.daily_clicks}</td>
                          <td className="py-3 px-4 text-right font-mono font-semibold">{fmtNum(pm.monthly_conversions)}</td>
                          <td className="py-3 px-4 text-right font-mono font-semibold text-neutral-900">
                            {fmtEur(pm.revenue_ttc_eur)}
                          </td>
                          <td className="py-3 px-4 text-right font-mono text-neutral-500">- {fmtEur(pm.ad_spend_eur)}</td>
                          <td className={`py-3 px-4 text-right font-mono font-semibold ${pm.gross_margin_eur >= 0 ? "text-emerald-700" : "text-rose-700"}`}>
                            {fmtEur(pm.gross_margin_eur)}
                          </td>
                          <td className={`py-3 px-4 text-right font-mono font-semibold ${pm.roas >= 2.5 ? "text-emerald-700" : pm.roas >= 1.8 ? "text-amber-700" : "text-rose-700"}`}>
                            {pm.roas}x
                          </td>
                        </tr>
                      ))}
                    </tbody>
                    <tfoot className="bg-neutral-900 text-white">
                      <tr>
                        <td className="py-3 px-4 text-[11px] uppercase tracking-widest">Global</td>
                        <td className="py-3 px-4"></td>
                        <td className="py-3 px-4 text-right font-mono">{fmtNum(scen.global.clicks)}</td>
                        <td className="py-3 px-4 text-right font-mono font-semibold">{fmtNum(scen.global.conversions)}</td>
                        <td className="py-3 px-4 text-right font-mono font-bold">{fmtEur(scen.global.revenue_ttc_eur)}</td>
                        <td className="py-3 px-4 text-right font-mono opacity-80">- {fmtEur(scen.global.ad_spend_eur)}</td>
                        <td className="py-3 px-4 text-right font-mono font-bold">{fmtEur(scen.global.gross_margin_eur)}</td>
                        <td className="py-3 px-4 text-right font-mono font-bold">{scen.global.roas}x</td>
                      </tr>
                    </tfoot>
                  </table>
                </div>
              </div>
            )}

            {/* Catalog & Google data side-by-side */}
            <div className="grid md:grid-cols-2 gap-5">
              <div className="bg-white border border-neutral-200 rounded-2xl p-5">
                <div className="text-[11px] uppercase tracking-widest text-neutral-500 mb-3">Ton catalogue</div>
                <div className="space-y-2 text-sm">
                  <Row label="Produits principaux" value={forecast.catalog.main_products_count} />
                  <Row label="Upsells" value={`${forecast.catalog.upsells_count} · couverture ${forecast.catalog.upsell_coverage_pct}%`} />
                  <div className="pt-2 mt-2 border-t border-neutral-100 space-y-1">
                    <Row label="Prix moyen produit" value={fmtEur(forecast.catalog.avg_main_price_eur)} />
                    <Row label="Coût moyen produit" value={fmtEur(forecast.catalog.avg_main_cost_eur)} />
                    <Row label="Marge produit" value={`${forecast.catalog.avg_main_margin_pct}%`} highlight />
                  </div>
                  {forecast.catalog.upsells_count > 0 && (
                    <div className="pt-2 mt-2 border-t border-neutral-100 space-y-1">
                      <Row label="Prix upsell remisé (-20%)" value={fmtEur(forecast.catalog.avg_upsell_price_eur)} small />
                      <Row label="Marge upsell" value={`${forecast.catalog.avg_upsell_margin_pct}%`} small />
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
                          <span className="text-[10px] text-amber-700 bg-amber-50 px-1.5 py-0.5 rounded-full" title="Fallback par défaut">
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
                    <div>Certains marchés utilisent des CPC estimés. Lance une Niche Analysis pour des données Google réelles.</div>
                  </div>
                )}
              </div>
            </div>

            {/* Sensitivity analysis — what-if */}
            <div className="bg-gradient-to-br from-indigo-50 to-white border border-indigo-200 rounded-2xl p-5">
              <div className="flex items-center gap-2 mb-3">
                <ArrowUp size={14} weight="bold" className="text-indigo-700" />
                <div className="text-[11px] uppercase tracking-widest text-indigo-700 font-semibold">
                  Simulations · que se passe-t-il si…
                </div>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <Sensitivity
                  label="Upsell attach +10 pts"
                  value={forecast.sensitivity.revenue_gain_if_upsell_attach_plus_10pts_eur}
                  hint="ajoute des upsells mieux ciblés à l'étape 3"
                />
                <Sensitivity
                  label="Prix moyen +10 €"
                  value={forecast.sensitivity.revenue_gain_if_avg_price_plus_10eur}
                  hint="positionne-toi plus premium ou bundle"
                />
                <Sensitivity
                  label="Budget Ads × 2"
                  value={forecast.sensitivity.revenue_gain_if_daily_budget_doubled_eur}
                  hint="si ROAS solide, scale avec confiance"
                />
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
                    <div
                      key={idx}
                      data-testid={`insight-${i.severity}-${idx}`}
                      className={`border rounded-2xl p-4 flex gap-3 ${m.bg} ${m.border}`}
                    >
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
          </div>
        )}
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
