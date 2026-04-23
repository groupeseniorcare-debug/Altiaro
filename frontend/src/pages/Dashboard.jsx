import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, apiCall } from "../lib/api";
import { useAuth } from "../lib/auth";
import ConcepteurDashboard from "./ConcepteurDashboard";
import Layout from "../components/Layout";
import {
  CurrencyEur,
  TrendUp,
  Storefront,
  CheckCircle,
  Warning,
  Plus,
  ArrowRight,
} from "@phosphor-icons/react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";

const fmt = (n, suffix = "€") =>
  new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 0 }).format(n || 0) + (suffix ? " " + suffix : "");

function StatCard({ label, value, sub, icon: Icon, delay = 0, testId }) {
  return (
    <div
      className={`bg-white rounded-xl border border-neutral-200 p-6 animate-fade-up-delay-${delay}`}
      data-testid={testId}
    >
      <div className="flex items-start justify-between mb-4">
        <div className="text-[11px] uppercase tracking-widest text-neutral-500 font-medium">
          {label}
        </div>
        <div className="w-9 h-9 rounded-lg bg-neutral-200 flex items-center justify-center">
          <Icon size={18} weight="duotone" color="#B84B31" />
        </div>
      </div>
      <div className="font-heading text-3xl font-semibold text-neutral-900 tracking-tight">{value}</div>
      {sub && <div className="text-sm text-neutral-500 mt-1">{sub}</div>}
    </div>
  );
}

export default function Dashboard() {
  const { user } = useAuth();
  // Route concepteurs to the dedicated dashboard with their KPIs/ledger/next events.
  if (user && user.role !== "admin") {
    return <ConcepteurDashboard />;
  }
  return <AdminDashboard />;
}

function AdminDashboard() {
  const [kpis, setKpis] = useState(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";

  useEffect(() => {
    (async () => {
      const { data } = await apiCall(() => api.get("/dashboard/kpis"));
      setKpis(data);
      setLoading(false);
    })();
  }, []);

  return (
    <Layout>
      <div className="p-8 md:p-12 max-w-[1600px] mx-auto w-full">
        <div className="flex items-start justify-between mb-10 animate-fade-up">
          <div>
            <div className="text-[11px] uppercase tracking-widest text-neutral-500 mb-2">Overview</div>
            <h1 className="text-3xl font-semibold text-neutral-900">Tableau de bord</h1>
            <p className="text-neutral-600 mt-2">
              Vision consolidée de votre portefeuille de marques.
            </p>
          </div>
          <button
            onClick={() => navigate("/sites/new")}
            data-testid="create-site-btn-dashboard"
            className="h-11 px-5 rounded-xl bg-neutral-900 hover:bg-neutral-800 text-white font-medium transition-all duration-200 flex items-center gap-2 active:scale-[0.98] shadow-sm"
          >
            {isAdmin ? (
              <>
                <Plus size={18} weight="bold" /> Lancer un site
              </>
            ) : (
              <>
                <Storefront size={18} weight="bold" /> Mes sites
              </>
            )}
          </button>
        </div>

        {loading ? (
          <div data-testid="dashboard-skeleton" aria-busy="true">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5 mb-10">
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="bg-white rounded-xl border border-neutral-200 p-6">
                  <div className="h-3 w-24 bg-stone-200 rounded animate-pulse mb-4" />
                  <div className="h-8 w-32 bg-stone-200 rounded animate-pulse mb-2" />
                  <div className="h-3 w-20 bg-stone-200 rounded animate-pulse" />
                </div>
              ))}
            </div>
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="lg:col-span-2 bg-white rounded-xl border border-neutral-200 p-6 h-[320px] animate-pulse" />
              <div className="bg-white rounded-xl border border-neutral-200 p-6 h-[320px] animate-pulse" />
            </div>
          </div>
        ) : (
          <>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5 mb-10">
              <StatCard
                label="Chiffre d'affaires total"
                value={fmt(kpis.totals.total_revenue)}
                sub={`${kpis.totals.total_orders || 0} commandes`}
                icon={CurrencyEur}
                delay={1}
                testId="kpi-revenue"
              />
              <StatCard
                label="Marge nette globale"
                value={fmt(kpis.totals.total_margin)}
                sub={`Après pub, achats, autres coûts`}
                icon={TrendUp}
                delay={2}
                testId="kpi-margin"
              />
              <StatCard
                label="Dépense publicitaire"
                value={fmt(kpis.totals.total_ad_spend)}
                sub={`ROAS global ${kpis.totals.roas_global}×`}
                icon={Storefront}
                delay={3}
                testId="kpi-ad-spend"
              />
              <StatCard
                label="Sites actifs"
                value={`${kpis.totals.active_sites} / ${kpis.totals.sites_count}`}
                sub={`Avancement global ${kpis.totals.global_progress_pct}%`}
                icon={CheckCircle}
                delay={4}
                testId="kpi-sites"
              />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-10">
              <div className="lg:col-span-2 bg-white rounded-xl border border-neutral-200 p-6">
                <div className="flex items-center justify-between mb-6">
                  <div>
                    <div className="text-[11px] uppercase tracking-widest text-neutral-500">
                      Évolution mensuelle
                    </div>
                    <h2 className="font-heading text-xl font-semibold text-neutral-900 mt-1">
                      Revenu vs Dépense publicitaire
                    </h2>
                  </div>
                </div>
                <div className="h-64">
                  {kpis.monthly_trend?.length ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={kpis.monthly_trend}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#E7E5E4" />
                        <XAxis dataKey="month" stroke="#78716C" fontSize={12} />
                        <YAxis stroke="#78716C" fontSize={12} />
                        <Tooltip
                          contentStyle={{ background: "white", border: "1px solid #E7E5E4", borderRadius: 8 }}
                        />
                        <Line type="monotone" dataKey="revenue" stroke="#B84B31" strokeWidth={2.5} name="Revenu" dot={{ fill: "#B84B31", r: 4 }} />
                        <Line type="monotone" dataKey="ad_spend" stroke="#78716C" strokeWidth={2} name="Pub" dot={{ fill: "#78716C", r: 3 }} />
                        <Line type="monotone" dataKey="margin" stroke="#047857" strokeWidth={2} name="Marge" dot={{ fill: "#047857", r: 3 }} />
                      </LineChart>
                    </ResponsiveContainer>
                  ) : (
                    <div className="h-full flex items-center justify-center text-neutral-500 text-sm">
                      Aucune donnée financière saisie pour l'instant.
                    </div>
                  )}
                </div>
              </div>

              <div className="bg-white rounded-xl border border-neutral-200 p-6">
                <div className="text-[11px] uppercase tracking-widest text-neutral-500 mb-1">
                  Workflow global
                </div>
                <h2 className="font-heading text-xl font-semibold text-neutral-900 mb-5">
                  Avancement des étapes
                </h2>
                <div className="space-y-4">
                  <div>
                    <div className="flex justify-between text-sm mb-1.5">
                      <span className="text-neutral-600">Validées</span>
                      <span className="font-medium text-emerald-400">{kpis.totals.validated_steps}</span>
                    </div>
                    <div className="h-2 bg-neutral-200 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-[#047857] rounded-full transition-all duration-500"
                        style={{ width: `${kpis.totals.global_progress_pct}%` }}
                      />
                    </div>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-neutral-600">En attente validation</span>
                    <span className="font-medium text-[#0369A1]">{kpis.totals.pending_validations}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-neutral-600">Total étapes</span>
                    <span className="font-medium text-neutral-900">{kpis.totals.total_steps}</span>
                  </div>
                  {kpis.totals.pending_validations > 0 && (
                    <button
                      onClick={() => navigate("/validations")}
                      data-testid="dashboard-validations-cta"
                      className="w-full mt-3 h-10 rounded-lg border border-neutral-200 bg-[#E0F2FE] text-[#0369A1] text-sm font-medium flex items-center justify-center gap-1.5 hover:bg-[#BAE6FD] transition"
                    >
                      <Warning size={16} weight="fill" />
                      {kpis.totals.pending_validations} validation{kpis.totals.pending_validations > 1 ? "s" : ""} en attente
                    </button>
                  )}
                </div>
              </div>
            </div>

            <div className="bg-white rounded-xl border border-neutral-200 overflow-hidden">
              <div className="px-6 py-5 border-b border-neutral-200 flex items-center justify-between">
                <div>
                  <div className="text-[11px] uppercase tracking-widest text-neutral-500">Portefeuille</div>
                  <h2 className="font-heading text-xl font-semibold text-neutral-900 mt-1">Vos sites</h2>
                </div>
                <button
                  onClick={() => navigate("/sites")}
                  className="text-sm text-neutral-900 hover:text-[#993D26] font-medium flex items-center gap-1"
                  data-testid="dashboard-all-sites-link"
                >
                  Voir tous <ArrowRight size={14} />
                </button>
              </div>
              {kpis.per_site.length === 0 ? (
                <div className="p-10 text-center">
                  <div className="text-neutral-500 mb-4">Aucun site créé pour l'instant.</div>
                  <button
                    onClick={() => navigate("/sites/new")}
                    data-testid="create-first-site-btn"
                    className="h-11 px-5 rounded-xl bg-neutral-900 hover:bg-neutral-800 text-white font-medium transition inline-flex items-center gap-2"
                  >
                    <Plus size={18} weight="bold" /> Lancer votre premier site
                  </button>
                </div>
              ) : (
                <table className="w-full">
                  <thead className="bg-white">
                    <tr>
                      <th className="text-left px-6 py-3 text-[11px] uppercase tracking-widest text-neutral-500 font-medium">Site</th>
                      <th className="text-left px-6 py-3 text-[11px] uppercase tracking-widest text-neutral-500 font-medium">Niche</th>
                      <th className="text-left px-6 py-3 text-[11px] uppercase tracking-widest text-neutral-500 font-medium">Avancement</th>
                      <th className="text-right px-6 py-3 text-[11px] uppercase tracking-widest text-neutral-500 font-medium">CA</th>
                      <th className="text-right px-6 py-3 text-[11px] uppercase tracking-widest text-neutral-500 font-medium">Marge</th>
                      <th className="text-right px-6 py-3 text-[11px] uppercase tracking-widest text-neutral-500 font-medium">ROAS</th>
                    </tr>
                  </thead>
                  <tbody>
                    {kpis.per_site.map((s) => (
                      <tr
                        key={s.id}
                        onClick={() => navigate(`/sites/${s.id}`)}
                        className="border-t border-neutral-200 hover:bg-white cursor-pointer transition"
                        data-testid={`site-row-${s.id}`}
                      >
                        <td className="px-6 py-4">
                          <div className="font-medium text-neutral-900">{s.name}</div>
                          <div className="text-xs text-neutral-500 mt-0.5">
                            {s.current_step_title ? `Étape ${s.current_step_number} · ${s.current_step_title.substring(0, 40)}` : "Non démarré"}
                          </div>
                        </td>
                        <td className="px-6 py-4 text-sm text-neutral-600">{s.niche}</td>
                        <td className="px-6 py-4 w-56">
                          <div className="flex items-center gap-3">
                            <div className="flex-1 h-2 bg-neutral-200 rounded-full overflow-hidden">
                              <div
                                className="h-full bg-white rounded-full transition-all"
                                style={{ width: `${s.progress_pct}%` }}
                              />
                            </div>
                            <span className="text-xs font-medium text-neutral-600 min-w-[40px] text-right">
                              {s.progress_pct}%
                            </span>
                          </div>
                        </td>
                        <td className="px-6 py-4 text-right font-medium text-neutral-900">{fmt(s.revenue)}</td>
                        <td className="px-6 py-4 text-right font-medium text-emerald-400">{fmt(s.margin)}</td>
                        <td className="px-6 py-4 text-right font-medium text-neutral-900">
                          {s.ad_spend > 0 ? `${(s.revenue / s.ad_spend).toFixed(2)}×` : "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </>
        )}
      </div>
    </Layout>
  );
}
