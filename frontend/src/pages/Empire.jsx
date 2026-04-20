import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, apiCall } from "../lib/api";
import Layout from "../components/Layout";
import {
  Globe,
  Coins,
  TrendUp,
  Warning,
  Storefront,
  Package,
  Megaphone,
  Rocket,
  ClockClockwise,
  MapPin,
  CaretRight,
  ArrowClockwise,
  Info,
} from "@phosphor-icons/react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
} from "recharts";

const COUNTRY_COLORS = {
  FR: "#B84B31",
  DE: "#D97706",
  CH: "#047857",
  BE: "#7C3AED",
  UK: "#0369A1",
  NL: "#EAB308",
  UNKNOWN: "#A8A29E",
};

const COUNTRY_EMOJI = {
  FR: "🇫🇷", DE: "🇩🇪", CH: "🇨🇭", BE: "🇧🇪",
  UK: "🇬🇧", NL: "🇳🇱", LU: "🇱🇺",
};

const ALERT_COLORS = {
  critical: { bg: "#FFE4E6", text: "#BE123C", icon: Warning },
  warning: { bg: "#FEF3C7", text: "#B45309", icon: Warning },
  info: { bg: "#DBEAFE", text: "#0369A1", icon: Info },
};

function formatEuro(v) {
  return `${Math.round(v || 0).toLocaleString("fr-FR")}€`;
}

export default function Empire() {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [days, setDays] = useState(30);
  const [refreshing, setRefreshing] = useState(false);

  const load = async () => {
    setRefreshing(true);
    const { data } = await apiCall(() => api.get(`/admin/empire?days=${days}`));
    if (data) setData(data);
    setLoading(false);
    setRefreshing(false);
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [days]);

  if (loading) {
    return (
      <Layout>
        <div className="p-8 text-[#78716C]">Chargement de l'Empire…</div>
      </Layout>
    );
  }

  if (!data) {
    return (
      <Layout>
        <div className="p-8 text-[#BE123C]">Erreur de chargement.</div>
      </Layout>
    );
  }

  const t = data.totals;

  return (
    <Layout>
      <div className="p-6 md:p-12 max-w-[1600px]">
        <div className="flex items-start justify-between gap-4 mb-8 flex-wrap">
          <div>
            <div className="text-[11px] uppercase tracking-widest text-[#78716C] mb-2 flex items-center gap-2">
              <Globe size={13} weight="duotone" /> Dashboard Empire · Admin only
            </div>
            <h1 className="font-heading text-4xl font-semibold text-[#1C1917]">
              Vue macro cross-pays
            </h1>
            <p className="text-[#57534E] mt-2 max-w-2xl">
              KPIs agrégés, breakdown par pays, familles scalées, alertes auto.
              Données temps réel sur {days} derniers jours.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <select
              value={days}
              onChange={(e) => setDays(parseInt(e.target.value))}
              data-testid="days-select"
              className="h-10 px-3 rounded-lg border border-[#E7E5E4] bg-white text-sm"
            >
              <option value={7}>7 jours</option>
              <option value={30}>30 jours</option>
              <option value={90}>90 jours</option>
              <option value={365}>1 an</option>
            </select>
            <button
              onClick={load}
              disabled={refreshing}
              data-testid="refresh-empire"
              className="h-10 px-3 rounded-lg bg-white border border-[#E7E5E4] hover:border-[#B84B31] text-sm font-medium flex items-center gap-2 transition disabled:opacity-50"
            >
              <ArrowClockwise size={14} className={refreshing ? "animate-spin" : ""} />
              Actualiser
            </button>
          </div>
        </div>

        {/* Hero KPIs */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <HeroCard
            testid="kpi-gmv"
            label="GMV total"
            value={formatEuro(t.total_gmv)}
            sub={`${t.total_orders} commandes · AOV ${formatEuro(t.aov)}`}
            icon={Coins}
            color="#B84B31"
          />
          <HeroCard
            testid="kpi-admin-share"
            label="Ta part (50%)"
            value={formatEuro(t.admin_share)}
            sub="Revenu fondateur"
            icon={TrendUp}
            color="#047857"
            highlight
          />
          <HeroCard
            testid="kpi-concepteur-share"
            label="Part Concepteurs"
            value={formatEuro(t.concepteur_share)}
            sub="Rémunération équipe"
            icon={Storefront}
            color="#7C3AED"
          />
          <HeroCard
            testid="kpi-sites"
            label="Empire"
            value={`${t.total_sites}`}
            sub={`${t.active_sites} actifs · ${t.niche_analyses} analyses · ${t.ads_campaigns} ads`}
            icon={Rocket}
            color="#D97706"
          />
        </div>

        {/* Recent period + secondary row */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8 text-sm">
          <div className="bg-white rounded-xl border border-[#E7E5E4] p-4" data-testid="kpi-recent-gmv">
            <div className="text-xs uppercase tracking-wider text-[#78716C]">
              GMV {days}j
            </div>
            <div className="font-heading text-2xl font-semibold text-[#1C1917]">
              {formatEuro(t.recent_gmv)}
            </div>
            <div className="text-xs text-[#78716C] mt-1">
              {t.recent_orders} commandes sur la période
            </div>
          </div>
          <div className="bg-white rounded-xl border border-[#E7E5E4] p-4">
            <div className="text-xs uppercase tracking-wider text-[#78716C]">
              Alertes actives
            </div>
            <div className="font-heading text-2xl font-semibold text-[#BE123C]">
              {data.alerts.length}
            </div>
            <div className="text-xs text-[#78716C] mt-1">
              cf. section ci-dessous
            </div>
          </div>
          <div className="bg-white rounded-xl border border-[#E7E5E4] p-4">
            <div className="text-xs uppercase tracking-wider text-[#78716C]">
              Familles scalées
            </div>
            <div className="font-heading text-2xl font-semibold text-[#1C1917]">
              {data.families.length}
            </div>
            <div className="text-xs text-[#78716C] mt-1">
              sources dupliquées cross-pays
            </div>
          </div>
          <div className="bg-white rounded-xl border border-[#E7E5E4] p-4">
            <div className="text-xs uppercase tracking-wider text-[#78716C]">
              À traiter
            </div>
            <div className="font-heading text-2xl font-semibold text-[#D97706]">
              {data.pending_orders.length}
            </div>
            <div className="text-xs text-[#78716C] mt-1">
              commandes en attente
            </div>
          </div>
        </div>

        {/* Charts row */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5 mb-8">
          <div className="bg-white rounded-2xl border border-[#E7E5E4] p-5 lg:col-span-2" data-testid="chart-timeseries">
            <h3 className="font-heading text-sm font-semibold text-[#1C1917] mb-4 uppercase tracking-wider">
              Evolution GMV · {days}j
            </h3>
            <div style={{ width: "100%", height: 260 }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={data.timeseries}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#F5F2EB" />
                  <XAxis
                    dataKey="date"
                    tickFormatter={(d) => d.slice(5)}
                    tick={{ fontSize: 10, fill: "#78716C" }}
                  />
                  <YAxis tick={{ fontSize: 10, fill: "#78716C" }} />
                  <Tooltip
                    contentStyle={{ background: "#1C1917", border: "none", borderRadius: 8 }}
                    labelStyle={{ color: "#FFF" }}
                    itemStyle={{ color: "#FFF" }}
                    formatter={(v, n) => [n === "revenue" ? formatEuro(v) : v, n]}
                  />
                  <Line type="monotone" dataKey="revenue" stroke="#B84B31" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="bg-white rounded-2xl border border-[#E7E5E4] p-5" data-testid="chart-countries">
            <h3 className="font-heading text-sm font-semibold text-[#1C1917] mb-4 uppercase tracking-wider">
              Répartition pays
            </h3>
            {data.per_country.length === 0 ? (
              <div className="text-sm text-[#78716C] h-[260px] flex items-center justify-center text-center">
                Aucune commande encore.
              </div>
            ) : (
              <div style={{ width: "100%", height: 220 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={data.per_country}
                      dataKey="revenue"
                      nameKey="code"
                      innerRadius={50}
                      outerRadius={80}
                      paddingAngle={2}
                    >
                      {data.per_country.map((c) => (
                        <Cell key={c.code} fill={COUNTRY_COLORS[c.code] || COUNTRY_COLORS.UNKNOWN} />
                      ))}
                    </Pie>
                    <Tooltip formatter={(v) => formatEuro(v)} />
                    <Legend
                      wrapperStyle={{ fontSize: 11 }}
                      formatter={(val) => `${COUNTRY_EMOJI[val] || "🌍"} ${val}`}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>
        </div>

        {/* 2-col : per country table + alerts */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 mb-8">
          <section className="bg-white rounded-2xl border border-[#E7E5E4] p-5" data-testid="section-per-country">
            <div className="flex items-center gap-2 mb-4">
              <MapPin size={16} weight="duotone" className="text-[#B84B31]" />
              <h3 className="font-heading text-sm font-semibold uppercase tracking-wider">
                Performance par pays
              </h3>
            </div>
            {data.per_country.length === 0 ? (
              <div className="text-sm text-[#78716C] text-center py-8">
                Pas encore de données géographiques.
              </div>
            ) : (
              <div className="space-y-2">
                {data.per_country.map((c) => (
                  <div
                    key={c.code}
                    className="flex items-center gap-3 p-3 rounded-lg hover:bg-[#FAF7F2] transition"
                    data-testid={`country-row-${c.code}`}
                  >
                    <div className="text-2xl">{COUNTRY_EMOJI[c.code] || "🌍"}</div>
                    <div className="flex-1 min-w-0">
                      <div className="font-medium text-sm text-[#1C1917]">{c.name}</div>
                      <div className="text-xs text-[#78716C]">
                        {c.orders} cmd · AOV {formatEuro(c.aov)} · {c.unique_cities} villes
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="font-heading font-semibold text-[#1C1917]">
                        {formatEuro(c.revenue)}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>

          <section className="bg-white rounded-2xl border border-[#E7E5E4] p-5" data-testid="section-alerts">
            <div className="flex items-center gap-2 mb-4">
              <Warning size={16} weight="duotone" className="text-[#D97706]" />
              <h3 className="font-heading text-sm font-semibold uppercase tracking-wider">
                Alertes auto ({data.alerts.length})
              </h3>
            </div>
            {data.alerts.length === 0 ? (
              <div className="text-sm text-[#047857] text-center py-8 flex flex-col items-center gap-2">
                <div className="text-4xl">🎉</div>
                Tout est sous contrôle — aucune alerte.
              </div>
            ) : (
              <div className="space-y-1.5 max-h-[350px] overflow-y-auto">
                {data.alerts.map((a, i) => {
                  const cfg = ALERT_COLORS[a.severity] || ALERT_COLORS.info;
                  const Icon = cfg.icon;
                  return (
                    <button
                      key={`${a.site_id}-${i}`}
                      type="button"
                      onClick={() => navigate(`/sites/${a.site_id}`)}
                      data-testid={`alert-${a.site_id}-${a.type}`}
                      className="w-full text-left p-3 rounded-lg border border-[#F5F2EB] hover:border-[#E7E5E4] transition flex items-start gap-3"
                      style={{ background: cfg.bg + "20" }}
                    >
                      <Icon size={16} weight="fill" className="shrink-0 mt-0.5" style={{ color: cfg.text }} />
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-medium text-[#1C1917] truncate">
                          {a.site_name}
                        </div>
                        <div className="text-xs text-[#57534E]">{a.message}</div>
                      </div>
                      <CaretRight size={14} className="text-[#78716C] shrink-0 mt-1" />
                    </button>
                  );
                })}
              </div>
            )}
          </section>
        </div>

        {/* Families + top products */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 mb-8">
          <section className="bg-white rounded-2xl border border-[#E7E5E4] p-5" data-testid="section-families">
            <div className="flex items-center gap-2 mb-4">
              <Rocket size={16} weight="fill" className="text-[#B84B31]" />
              <h3 className="font-heading text-sm font-semibold uppercase tracking-wider">
                Familles scalées cross-pays ({data.families.length})
              </h3>
            </div>
            {data.families.length === 0 ? (
              <div className="text-sm text-[#78716C] text-center py-8">
                Aucune famille. Va sur un site et clique <strong>"Scaler 6 pays"</strong>.
              </div>
            ) : (
              <div className="space-y-2">
                {data.families.map((f) => (
                  <div
                    key={f.source_id || f.source_name}
                    className="p-3 rounded-lg border border-[#F5F2EB] hover:border-[#B84B31]/40 transition cursor-pointer"
                    onClick={() => f.source_id && navigate(`/sites/${f.source_id}`)}
                    data-testid={`family-${f.source_id}`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <div className="font-medium text-sm text-[#1C1917] truncate flex-1">
                        {f.source_name}
                      </div>
                      <div className="font-heading font-semibold text-[#B84B31]">
                        {formatEuro(f.total_revenue)}
                      </div>
                    </div>
                    <div className="flex items-center gap-1.5 text-xs text-[#78716C] flex-wrap">
                      <span className="font-mono">
                        {f.total_sites} sites · {f.total_orders} cmd
                      </span>
                      {f.countries.map((cc) => (
                        <span key={cc} className="text-sm">
                          {COUNTRY_EMOJI[cc] || cc}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>

          <section className="bg-white rounded-2xl border border-[#E7E5E4] p-5" data-testid="section-top-products">
            <div className="flex items-center gap-2 mb-4">
              <Package size={16} weight="duotone" className="text-[#047857]" />
              <h3 className="font-heading text-sm font-semibold uppercase tracking-wider">
                Top produits cross-sites
              </h3>
            </div>
            {data.top_products.length === 0 ? (
              <div className="text-sm text-[#78716C] text-center py-8">
                Aucune vente encore enregistrée.
              </div>
            ) : (
              <div className="space-y-2">
                {data.top_products.map((p, i) => (
                  <div
                    key={p.product_id}
                    className="flex items-center gap-3 p-3 rounded-lg bg-[#FAF7F2]"
                    data-testid={`top-product-${i}`}
                  >
                    <div className="w-8 h-8 rounded-full bg-[#1C1917] text-white flex items-center justify-center font-heading font-semibold text-sm">
                      {i + 1}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="font-medium text-sm text-[#1C1917] truncate">
                        {p.name || "—"}
                      </div>
                      <div className="text-xs text-[#78716C]">{p.quantity} vendus</div>
                    </div>
                    <div className="font-heading font-semibold text-[#1C1917]">
                      {formatEuro(p.revenue)}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>
        </div>

        {/* Pending orders */}
        <section className="bg-white rounded-2xl border border-[#E7E5E4] p-5 mb-8" data-testid="section-pending-orders">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <ClockClockwise size={16} weight="duotone" className="text-[#D97706]" />
              <h3 className="font-heading text-sm font-semibold uppercase tracking-wider">
                Commandes à traiter ({data.pending_orders.length})
              </h3>
            </div>
            <button
              onClick={() => navigate("/orders")}
              className="text-xs text-[#B84B31] hover:underline"
              data-testid="goto-orders"
            >
              Voir toutes →
            </button>
          </div>
          {data.pending_orders.length === 0 ? (
            <div className="text-sm text-[#78716C] text-center py-6">
              Aucune commande en attente. ✨
            </div>
          ) : (
            <div className="space-y-1.5">
              {data.pending_orders.map((o) => (
                <div
                  key={o.id}
                  className="flex items-center gap-3 p-2.5 rounded-lg hover:bg-[#FAF7F2] transition"
                >
                  <span
                    className={`px-2 py-0.5 rounded-full text-[10px] uppercase tracking-wider font-semibold ${
                      o.status === "pending_payment"
                        ? "bg-[#FEF3C7] text-[#B45309]"
                        : "bg-[#DBEAFE] text-[#0369A1]"
                    }`}
                  >
                    {o.status}
                  </span>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-mono text-[#1C1917] truncate">
                      {o.order_number}
                    </div>
                    <div className="text-xs text-[#78716C] truncate">
                      {o.site_name} · {new Date(o.created_at).toLocaleString("fr-FR")}
                    </div>
                  </div>
                  <div className="font-heading font-semibold text-[#1C1917]">
                    {formatEuro(o.total)}
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        <div className="text-xs text-[#78716C] text-center">
          Dashboard généré le {new Date(data.generated_at).toLocaleString("fr-FR")}
        </div>
      </div>
    </Layout>
  );
}

function HeroCard({ testid, label, value, sub, icon: Icon, color, highlight }) {
  return (
    <div
      className={`rounded-2xl p-5 ${
        highlight ? "bg-gradient-to-br from-[#1C1917] to-[#44403C] text-white" : "bg-white border border-[#E7E5E4]"
      }`}
      data-testid={testid}
    >
      <div className="flex items-center gap-2 mb-2">
        <div
          className={`w-7 h-7 rounded-lg flex items-center justify-center ${
            highlight ? "bg-white/10" : ""
          }`}
          style={!highlight ? { background: color + "18" } : {}}
        >
          <Icon size={14} weight="duotone" color={highlight ? "#FFF" : color} />
        </div>
        <div
          className={`text-[10px] uppercase tracking-widest ${
            highlight ? "text-white/60" : "text-[#78716C]"
          }`}
        >
          {label}
        </div>
      </div>
      <div
        className={`font-heading text-3xl font-semibold ${
          highlight ? "text-white" : "text-[#1C1917]"
        }`}
      >
        {value}
      </div>
      <div
        className={`text-xs mt-1.5 ${highlight ? "text-white/70" : "text-[#78716C]"}`}
      >
        {sub}
      </div>
    </div>
  );
}
