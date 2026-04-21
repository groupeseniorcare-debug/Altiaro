import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, apiCall } from "../lib/api";
import Layout from "../components/Layout";
import {
  CurrencyEur,
  ShoppingBag,
  TrendUp,
  Warning,
  CheckCircle,
  Rocket,
  ArrowRight,
  ArrowClockwise,
  Clock,
  Storefront,
  Receipt,
  ArrowDown,
  ArrowUp,
} from "@phosphor-icons/react";

const fmtEur = (n) =>
  new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR" }).format(n || 0);

const fmtNum = (n) => Number(n || 0).toLocaleString("fr-FR").replace(/,/g, " ");

const fmtDate = (iso) => {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString("fr-FR", {
      day: "numeric",
      month: "short",
      year: "numeric",
    });
  } catch {
    return iso;
  }
};

export default function ConcepteurDashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    apiCall(() => api.get("/concepteur/dashboard"))
      .then(({ data: d }) => setData(d))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <Layout>
        <div className="p-8 flex items-center gap-2 text-zinc-500 text-sm">
          <ArrowClockwise size={14} className="animate-spin" /> Chargement du tableau de bord…
        </div>
      </Layout>
    );
  }

  if (!data) {
    return (
      <Layout>
        <div className="p-8 text-red-400">Impossible de charger les KPIs.</div>
      </Layout>
    );
  }

  const setupComplete = data.setup?.banking_ready;
  const hasSites = data.sites.total > 0;

  return (
    <Layout>
      <div className="p-8 md:p-10 max-w-[1400px]">
        {/* Header */}
        <div className="flex items-start justify-between mb-8 flex-wrap gap-4">
          <div>
            <div className="text-[10px] uppercase tracking-[0.12em] text-zinc-500 font-medium mb-1.5">
              Vue globale
            </div>
            <h1 className="text-3xl font-semibold text-zinc-100 tracking-tight">Dashboard</h1>
            <p className="text-zinc-500 text-sm mt-1">
              {hasSites
                ? `${data.sites.total} site${data.sites.total > 1 ? "s" : ""} · ${data.orders.paid} commande${data.orders.paid > 1 ? "s" : ""} payée${data.orders.paid > 1 ? "s" : ""}`
                : "Lance ton premier site en quelques minutes."}
            </p>
          </div>
          <button
            onClick={() => navigate("/sites/new")}
            data-testid="dash-launch-site"
            className="h-9 px-4 rounded-md bg-zinc-950 hover:bg-zinc-200 text-black text-[13px] font-medium flex items-center gap-1.5 transition-colors"
          >
            <Rocket size={14} weight="fill" /> Lancer un site
          </button>
        </div>

        {/* Setup banner */}
        {!setupComplete && (
          <div
            className="bg-zinc-950 border border-zinc-800 rounded-md p-4 mb-5 flex items-start gap-3"
            data-testid="setup-banner"
          >
            <Warning size={16} weight="fill" className="text-amber-400 shrink-0 mt-0.5" />
            <div className="flex-1 text-sm">
              <div className="font-medium text-zinc-100 mb-1">Finalise ta configuration</div>
              <div className="flex items-center gap-4 text-xs text-zinc-400 flex-wrap">
                {!data.setup.has_card && <span>Carte bancaire manquante (prélèvement Ads)</span>}
                {data.setup.has_card && <span className="text-emerald-400">✓ Carte OK</span>}
                <span className="text-zinc-700">·</span>
                {!data.setup.has_iban && <span>IBAN manquant (virement versements)</span>}
                {data.setup.has_iban && <span className="text-emerald-400">✓ IBAN OK</span>}
              </div>
            </div>
            <Link
              to="/billing"
              data-testid="setup-goto-account"
              className="h-8 px-3 rounded-md bg-zinc-950 text-black text-xs font-medium flex items-center gap-1 shrink-0 hover:bg-zinc-200 transition"
            >
              Compléter <ArrowRight size={12} />
            </Link>
          </div>
        )}

        {/* KPI Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3 mb-3">
          <KpiCard
            testId="kpi-revenue"
            label="Chiffre d'affaires"
            value={fmtEur(data.revenue.total_eur)}
            sub={`${fmtEur(data.revenue.last_30d_eur)} · 30j`}
            icon={CurrencyEur}
          />
          <KpiCard
            testId="kpi-orders"
            label="Commandes"
            value={fmtNum(data.orders.paid)}
            sub={`${data.orders.pending} en attente · ${data.orders.refunded} remboursées`}
            icon={ShoppingBag}
          />
          <KpiCard
            testId="kpi-margin"
            label="Part reçue"
            value={fmtEur(data.balance.order_share_paid_eur)}
            sub={`Net à virer · ${fmtEur(data.balance.net_due_eur)}`}
            icon={TrendUp}
          />
          <KpiCard
            testId="kpi-refunds"
            label="Taux retours"
            value={`${data.refunds.rate_pct}%`}
            sub={`${data.refunds.count} · ${fmtEur(data.refunds.amount_eur)}`}
            icon={Receipt}
            alert={data.refunds.rate_pct > 8}
          />
        </div>

        {/* Next events */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-8">
          <NextEventCard
            testId="next-payout"
            label="Prochain versement"
            date={data.next_events.payout.date}
            amount={data.next_events.payout.amount_eur}
            status={data.next_events.payout.status}
            statusBlockedLabel="IBAN manquant"
            icon={ArrowDown}
            flow="in"
          />
          <NextEventCard
            testId="next-debit"
            label="Prochain prélèvement Ads"
            date={data.next_events.debit.date}
            amount={data.next_events.debit.amount_eur}
            status={data.next_events.debit.status}
            statusBlockedLabel="Carte manquante"
            icon={ArrowUp}
            flow="out"
          />
        </div>

        {/* Sites list */}
        <div className="bg-zinc-950 border border-zinc-900 rounded-md p-5">
          <div className="flex items-center justify-between mb-4">
            <div>
              <div className="text-[10px] uppercase tracking-[0.12em] text-zinc-500 font-medium mb-0.5">
                Mes sites
              </div>
              <h2 className="text-lg font-semibold text-zinc-100 tracking-tight">
                {data.sites.total} site{data.sites.total > 1 ? "s" : ""}
                {data.sites.total > 0 && (
                  <span className="text-zinc-500 text-sm font-normal ml-2">
                    · {data.sites.active} actif{data.sites.active > 1 ? "s" : ""}
                  </span>
                )}
              </h2>
            </div>
            {data.sites.total > 0 && (
              <Link
                to="/sites"
                data-testid="dash-goto-sites"
                className="text-xs text-zinc-400 hover:text-zinc-100 font-medium"
              >
                Voir tout →
              </Link>
            )}
          </div>

          {data.sites.total === 0 ? (
            <div className="py-12 text-center rounded-md border border-dashed border-zinc-800">
              <Storefront size={32} weight="thin" className="mx-auto text-zinc-700 mb-3" />
              <div className="text-sm text-zinc-400 mb-1">Aucun site pour l'instant</div>
              <div className="text-xs text-zinc-600 mb-5">Lance ton 1er site en 3 étapes</div>
              <Link
                to="/sites/new"
                data-testid="dash-empty-launch"
                className="inline-flex items-center gap-1.5 h-9 px-4 rounded-md bg-zinc-950 hover:bg-zinc-200 text-black text-[13px] font-medium"
              >
                <Rocket size={14} weight="fill" /> Lancer
              </Link>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
              {data.sites.items.slice(0, 9).map((s) => (
                <Link
                  key={s.id}
                  to={`/sites/${s.id}`}
                  data-testid={`dash-site-${s.id}`}
                  className="block p-3 rounded-md border border-zinc-800 bg-zinc-900/30 hover:border-zinc-700 hover:bg-zinc-900 transition-colors"
                >
                  <div className="flex items-center justify-between mb-0.5">
                    <div className="font-medium text-sm text-zinc-100 truncate pr-2">{s.name}</div>
                    {s.ads_active ? (
                      <span className="text-[9px] uppercase tracking-wider font-semibold px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                        ● Actif
                      </span>
                    ) : (
                      <span className="text-[9px] uppercase tracking-wider font-semibold px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-500 border border-zinc-800">
                        Pause
                      </span>
                    )}
                  </div>
                  {s.domain && (
                    <div className="font-mono text-[11px] text-zinc-500 truncate">{s.domain}</div>
                  )}
                </Link>
              ))}
            </div>
          )}
        </div>
      </div>
    </Layout>
  );
}

function KpiCard({ label, value, sub, icon: Icon, alert = false, testId }) {
  return (
    <div
      className="bg-zinc-950 rounded-md border border-zinc-900 p-4 hover:border-zinc-800 transition-colors"
      data-testid={testId}
    >
      <div className="flex items-start justify-between mb-3">
        <div className="text-[10px] uppercase tracking-[0.12em] text-zinc-500 font-medium">
          {label}
        </div>
        <Icon size={14} className={alert ? "text-red-400" : "text-zinc-600"} weight="duotone" />
      </div>
      <div
        className={`text-2xl font-semibold tracking-tight leading-none font-mono tabular-nums ${
          alert ? "text-red-400" : "text-zinc-100"
        }`}
      >
        {value}
      </div>
      {sub && <div className="text-xs text-zinc-500 mt-2">{sub}</div>}
    </div>
  );
}

function NextEventCard({ label, date, amount, status, statusBlockedLabel, icon: Icon, flow, testId }) {
  const blocked = status && status.startsWith("blocked");
  return (
    <div className="bg-zinc-950 rounded-md border border-zinc-900 p-4" data-testid={testId}>
      <div className="flex items-start justify-between mb-3">
        <div className="text-[10px] uppercase tracking-[0.12em] text-zinc-500 font-medium">
          {label}
        </div>
        <Icon
          size={14}
          weight="bold"
          className={flow === "in" ? "text-emerald-400" : "text-zinc-500"}
        />
      </div>
      <div
        className={`text-2xl font-semibold tracking-tight leading-none font-mono tabular-nums mb-2 ${
          flow === "in" ? "text-emerald-400" : "text-zinc-100"
        }`}
      >
        {flow === "in" ? "+" : "−"}
        {fmtEur(amount)}
      </div>
      <div className="flex items-center gap-2 text-xs">
        <Clock size={10} weight="bold" className="text-zinc-600" />
        <span className="text-zinc-400">{fmtDate(date)}</span>
        {blocked ? (
          <span className="ml-auto font-medium text-red-400 flex items-center gap-1 text-[11px]">
            <Warning size={10} weight="fill" />
            {statusBlockedLabel}
          </span>
        ) : (
          <span className="ml-auto text-zinc-500 flex items-center gap-1 text-[11px]">
            <CheckCircle size={10} weight="fill" className="text-emerald-400" />
            Programmé
          </span>
        )}
      </div>
    </div>
  );
}
