import React, { useEffect, useState, useCallback, useMemo } from "react";
import {
  ArrowUp, ArrowDown, Minus, Users, CurrencyEur,
  TrendUp, Package, MapPin, EnvelopeSimple, CircleNotch, Rocket,
} from "@phosphor-icons/react";
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer,
  CartesianGrid, Legend,
} from "recharts";
import { api, apiCall } from "../../lib/api";

const RANGES = [
  { key: "7d", label: "7 jours" },
  { key: "30d", label: "30 jours" },
  { key: "90d", label: "90 jours" },
];

const FUNNEL_LABELS = {
  product_view: "Vues produit",
  add_to_cart: "Ajouts panier",
  begin_checkout: "Checkouts démarrés",
  purchase: "Achats",
};

const COUNTRY_FLAGS = {
  FR: "🇫🇷", BE: "🇧🇪", LU: "🇱🇺", CH: "🇨🇭",
  DE: "🇩🇪", AT: "🇦🇹", UK: "🇬🇧", IE: "🇮🇪",
  NL: "🇳🇱", IT: "🇮🇹", ES: "🇪🇸", PT: "🇵🇹", FI: "🇫🇮",
};

function Delta({ value }) {
  if (value == null) return <span className="text-xs text-neutral-400">—</span>;
  if (value === 0) return <span className="text-xs text-neutral-500 inline-flex items-center gap-0.5"><Minus size={11} /> 0%</span>;
  const up = value > 0;
  return (
    <span className={`text-xs inline-flex items-center gap-0.5 ${up ? "text-emerald-600" : "text-red-500"}`}>
      {up ? <ArrowUp size={11} weight="bold" /> : <ArrowDown size={11} weight="bold" />}
      {Math.abs(value)}%
    </span>
  );
}

function KpiCard({ icon: Icon, label, value, sub, delta, testId }) {
  return (
    <div className="bg-white rounded-xl border border-neutral-200 p-5" data-testid={testId}>
      <div className="flex items-center justify-between mb-3">
        <div className="w-9 h-9 rounded-lg bg-neutral-100 flex items-center justify-center">
          <Icon size={18} weight="duotone" className="text-neutral-700" />
        </div>
        <Delta value={delta} />
      </div>
      <div className="text-[11px] uppercase tracking-widest text-neutral-500 mb-1">{label}</div>
      <div className="text-2xl font-semibold text-neutral-900 tabular-nums" style={{ fontFamily: "'Fraunces', serif" }}>
        {value}
      </div>
      {sub && <div className="text-xs text-neutral-500 mt-0.5">{sub}</div>}
    </div>
  );
}

function FunnelStep({ step, maxCount }) {
  const pct = maxCount > 0 ? Math.round((step.count / maxCount) * 100) : 0;
  return (
    <div className="relative">
      <div className="flex items-baseline justify-between mb-1.5">
        <div>
          <div className="text-sm font-medium text-neutral-900">{FUNNEL_LABELS[step.event] || step.event}</div>
          {step.drop_off_pct != null && step.drop_off_pct > 0 && (
            <div className="text-[11px] text-red-500">−{step.drop_off_pct}% vs étape précédente</div>
          )}
        </div>
        <div className="text-right">
          <div className="text-xl font-semibold text-neutral-900 tabular-nums">{step.count.toLocaleString("fr-FR")}</div>
          <div className="text-[10px] text-neutral-500">{step.sessions} sessions</div>
        </div>
      </div>
      <div className="h-2 rounded-full bg-neutral-100 overflow-hidden">
        <div
          className="h-full bg-gradient-to-r from-[#B84B31] to-emerald-500 transition-all"
          style={{ width: `${Math.max(pct, 2)}%` }}
        />
      </div>
    </div>
  );
}

export default function OverviewTab({ siteId, site, mailtoAds }) {
  const [range, setRange] = useState("30d");
  const [overview, setOverview] = useState(null);
  const [loading, setLoading] = useState(true);

  const loadOverview = useCallback(async () => {
    setLoading(true);
    const { data, error } = await apiCall(() => api.get(`/sites/${siteId}/analytics/overview?range=${range}`));
    if (!error) setOverview(data);
    setLoading(false);
  }, [siteId, range]);

  useEffect(() => { loadOverview(); }, [loadOverview]);

  const hasData = overview && overview.visitors?.unique_sessions > 0;
  const funnelSteps = useMemo(() => {
    if (!overview?.funnel) return [];
    const raw = [
      { event: "product_view",   count: overview.funnel.product_view,   sessions: 0, drop_off_pct: null },
      { event: "add_to_cart",    count: overview.funnel.add_to_cart,    sessions: 0, drop_off_pct: null },
      { event: "begin_checkout", count: overview.funnel.begin_checkout, sessions: 0, drop_off_pct: null },
      { event: "purchase",       count: overview.funnel.purchase,       sessions: 0, drop_off_pct: null },
    ];
    for (let i = 1; i < raw.length; i++) {
      const prev = raw[i - 1].count;
      if (prev > 0) raw[i].drop_off_pct = Math.round((1 - raw[i].count / prev) * 100 * 10) / 10;
    }
    return raw;
  }, [overview]);
  const maxFunnel = funnelSteps.reduce((m, s) => Math.max(m, s.count), 0);

  return (
    <div data-testid="overview-tab">
      <div className="flex justify-end mb-5">
        <div className="flex items-center gap-1 bg-neutral-100 p-1 rounded-lg" data-testid="range-selector">
          {RANGES.map((r) => (
            <button
              key={r.key}
              onClick={() => setRange(r.key)}
              className={`h-8 px-3 rounded-md text-xs font-medium transition ${
                range === r.key ? "bg-white text-neutral-900 shadow-sm" : "text-neutral-500 hover:text-neutral-900"
              }`}
              data-testid={`range-${r.key}`}
            >
              {r.label}
            </button>
          ))}
        </div>
      </div>

      {loading && !overview && (
        <div className="py-20 text-neutral-500 text-sm flex items-center justify-center gap-2">
          <CircleNotch size={16} className="animate-spin" /> Chargement des données…
        </div>
      )}

      {overview && !hasData && (
        <div className="bg-white rounded-2xl border border-neutral-200 p-10 text-center" data-testid="analytics-empty">
          <div className="w-16 h-16 mx-auto mb-5 rounded-2xl bg-emerald-50 border border-emerald-200 flex items-center justify-center">
            <Rocket size={28} weight="duotone" className="text-emerald-700" />
          </div>
          <h2 className="text-xl font-semibold text-neutral-900 mb-2" style={{ fontFamily: "'Fraunces', serif" }}>
            Ton site vient d'être validé 🎉
          </h2>
          <p className="text-sm text-neutral-600 max-w-md mx-auto mb-5">
            Les premiers visiteurs apparaîtront ici dès qu'ils arriveront. Tu peux déjà demander à
            l'équipe admin de lancer les campagnes Google Ads pour booster ton trafic.
          </p>
          <a
            href={mailtoAds}
            data-testid="empty-request-ads"
            className="inline-flex items-center gap-2 h-10 px-5 rounded-xl bg-neutral-900 hover:bg-neutral-800 text-white text-sm font-medium transition"
          >
            <EnvelopeSimple size={15} weight="duotone" /> Demander une campagne Ads
          </a>
        </div>
      )}

      {overview && hasData && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8" data-testid="kpi-grid">
            <KpiCard
              icon={Users}
              label="Visiteurs uniques"
              value={overview.visitors.unique_sessions.toLocaleString("fr-FR")}
              sub={`${overview.visitors.page_views.toLocaleString("fr-FR")} pages vues`}
              delta={overview.vs_previous?.visitors_pct}
              testId="kpi-visitors"
            />
            <KpiCard
              icon={TrendUp}
              label="Taux de conversion"
              value={`${overview.funnel.conversion_rate_pct}%`}
              sub={`${overview.funnel.purchase} achats sur ${overview.visitors.unique_sessions} sessions`}
              delta={overview.vs_previous?.conversion_pct}
              testId="kpi-conversion"
            />
            <KpiCard
              icon={CurrencyEur}
              label="Chiffre d'affaires"
              value={`${overview.revenue.total.toLocaleString("fr-FR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} €`}
              sub={`${overview.revenue.orders_count} commandes · AOV ${overview.revenue.aov} €`}
              delta={overview.vs_previous?.revenue_pct}
              testId="kpi-revenue"
            />
          </div>

          <div className="bg-white rounded-xl border border-neutral-200 p-5 mb-8" data-testid="daily-chart">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-semibold text-neutral-900">Évolution quotidienne</h3>
              <span className="text-[11px] text-neutral-500">Sessions & revenu · {overview.range}</span>
            </div>
            <div className="w-full h-[280px]">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={overview.daily} margin={{ top: 5, right: 10, bottom: 5, left: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f5f5f4" />
                  <XAxis dataKey="date" tick={{ fontSize: 11, fill: "#737373" }} />
                  <YAxis yAxisId="left" tick={{ fontSize: 11, fill: "#737373" }} />
                  <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 11, fill: "#737373" }} />
                  <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8 }} />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  <Line yAxisId="left" type="monotone" dataKey="sessions" name="Sessions" stroke="#0f172a" strokeWidth={2} dot={false} />
                  <Line yAxisId="right" type="monotone" dataKey="revenue" name="Revenu (€)" stroke="#B84B31" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
            <div className="bg-white rounded-xl border border-neutral-200 p-5" data-testid="funnel-panel">
              <h3 className="text-sm font-semibold text-neutral-900 mb-1">Entonnoir de conversion</h3>
              <p className="text-[11px] text-neutral-500 mb-5">Vues → panier → checkout → achat</p>
              <div className="space-y-5">
                {funnelSteps.map((s) => (
                  <FunnelStep key={s.event} step={s} maxCount={maxFunnel} />
                ))}
              </div>
            </div>

            <div className="bg-white rounded-xl border border-neutral-200 p-5" data-testid="top-countries">
              <h3 className="text-sm font-semibold text-neutral-900 mb-1 flex items-center gap-2">
                <MapPin size={14} /> Top pays
              </h3>
              <p className="text-[11px] text-neutral-500 mb-4">Sessions uniques par pays</p>
              {!overview.top_countries || overview.top_countries.length === 0 ? (
                <div className="text-xs text-neutral-400 py-6 text-center">Pas encore de données pays</div>
              ) : (
                <div className="space-y-2.5">
                  {overview.top_countries.map((c) => {
                    const max = overview.top_countries[0].sessions || 1;
                    const pct = Math.round((c.sessions / max) * 100);
                    return (
                      <div key={c.country} className="flex items-center gap-3">
                        <span className="text-base leading-none w-5">{COUNTRY_FLAGS[c.country] || "🌍"}</span>
                        <span className="text-xs text-neutral-700 w-8 font-mono">{c.country}</span>
                        <div className="flex-1 h-1.5 rounded-full bg-neutral-100 overflow-hidden">
                          <div className="h-full bg-neutral-900" style={{ width: `${pct}%` }} />
                        </div>
                        <span className="text-xs text-neutral-900 tabular-nums w-12 text-right">{c.sessions}</span>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>

          <div className="bg-white rounded-xl border border-neutral-200 p-5 mb-8" data-testid="top-products">
            <h3 className="text-sm font-semibold text-neutral-900 mb-1 flex items-center gap-2">
              <Package size={14} /> Top produits
            </h3>
            <p className="text-[11px] text-neutral-500 mb-4">Produits les plus consultés et vendus</p>
            {!overview.top_products || overview.top_products.length === 0 ? (
              <div className="text-xs text-neutral-400 py-6 text-center">Pas encore de vues produit</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-[11px] uppercase tracking-widest text-neutral-500 text-left">
                      <th className="pb-2 font-medium">Produit</th>
                      <th className="pb-2 font-medium text-right">Vues</th>
                      <th className="pb-2 font-medium text-right">Achats</th>
                      <th className="pb-2 font-medium text-right">Taux</th>
                    </tr>
                  </thead>
                  <tbody>
                    {overview.top_products.map((p) => {
                      const rate = p.views > 0 ? ((p.purchases / p.views) * 100).toFixed(1) : "—";
                      return (
                        <tr key={p.product_id} className="border-t border-neutral-100">
                          <td className="py-2.5">
                            <div className="flex items-center gap-3">
                              {p.image ? (
                                <img src={p.image} alt="" className="w-9 h-9 rounded-md object-cover bg-neutral-100" />
                              ) : (
                                <div className="w-9 h-9 rounded-md bg-neutral-100 flex items-center justify-center">
                                  <Package size={15} className="text-neutral-400" />
                                </div>
                              )}
                              <span className="text-neutral-900">{p.name}</span>
                            </div>
                          </td>
                          <td className="py-2.5 text-right tabular-nums">{p.views}</td>
                          <td className="py-2.5 text-right tabular-nums">{p.purchases}</td>
                          <td className="py-2.5 text-right tabular-nums text-neutral-500">{rate}{rate !== "—" ? "%" : ""}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          <div className="bg-gradient-to-br from-neutral-50 to-white rounded-xl border border-neutral-200 p-6 text-center">
            <p className="text-sm text-neutral-700 mb-3">
              Envie d'accélérer ? Demande à l'équipe admin de booster le trafic avec Google Ads.
            </p>
            <a
              href={mailtoAds}
              data-testid="cta-request-ads"
              className="inline-flex items-center gap-2 h-10 px-5 rounded-xl bg-neutral-900 hover:bg-neutral-800 text-white text-sm font-medium transition"
            >
              <EnvelopeSimple size={15} weight="duotone" /> Demander une campagne Ads
            </a>
          </div>
        </>
      )}
    </div>
  );
}
