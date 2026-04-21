import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, apiCall } from "../lib/api";
import Layout from "../components/Layout";
import {
  CurrencyEur,
  ShoppingBag,
  TrendUp,
  Bank,
  CreditCard,
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

const fmtNum = (n) =>
  Number(n || 0).toLocaleString("fr-FR").replace(/,/g, " ");

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
        <div className="p-8 flex items-center gap-3 text-[#78716C]">
          <ArrowClockwise size={16} className="animate-spin" /> Chargement du tableau de bord…
        </div>
      </Layout>
    );
  }

  if (!data) {
    return (
      <Layout>
        <div className="p-8 text-[#BE123C]">Impossible de charger les KPIs.</div>
      </Layout>
    );
  }

  const setupComplete = data.setup?.banking_ready;
  const hasSites = data.sites.total > 0;

  return (
    <Layout>
      <div className="p-8 md:p-12 max-w-[1400px]">
        {/* Header */}
        <div className="flex items-start justify-between mb-10 flex-wrap gap-4">
          <div>
            <div className="text-[11px] uppercase tracking-widest text-[#78716C] mb-2">
              Vue globale · Concepteur
            </div>
            <h1 className="font-heading text-4xl font-semibold text-[#1C1917]">Dashboard</h1>
            <p className="text-[#57534E] mt-1">
              {hasSites
                ? `${data.sites.total} site${data.sites.total > 1 ? "s" : ""} · ${data.orders.paid} commande${data.orders.paid > 1 ? "s" : ""} payée${data.orders.paid > 1 ? "s" : ""}`
                : "Lance ton premier site en quelques minutes."}
            </p>
          </div>
          <button
            onClick={() => navigate("/sites/new")}
            data-testid="dash-launch-site"
            className="h-12 px-5 rounded-full bg-gradient-to-r from-[#F59E0B] to-[#EA580C] hover:brightness-110 text-white font-medium text-sm flex items-center gap-2 shadow-sm"
          >
            <Rocket size={16} weight="fill" /> Lancer un site
          </button>
        </div>

        {/* Setup banner */}
        {!setupComplete && (
          <div
            className="bg-gradient-to-r from-[#FEF3C7] to-[#FEFCE8] border border-[#FDE68A] rounded-2xl p-5 mb-6 flex items-start gap-4"
            data-testid="setup-banner"
          >
            <div className="w-10 h-10 rounded-full bg-[#D97706]/10 flex items-center justify-center shrink-0">
              <Warning size={20} weight="fill" className="text-[#D97706]" />
            </div>
            <div className="flex-1">
              <div className="font-medium text-[#78350F] mb-1">
                Finalise ta configuration pour toucher tes versements
              </div>
              <div className="flex items-center gap-4 text-sm text-[#92400E] flex-wrap">
                {!data.setup.has_card && <span>❌ Carte bancaire manquante (prélèvement Ads)</span>}
                {data.setup.has_card && <span>✓ Carte OK</span>}
                {!data.setup.has_iban && <span>❌ IBAN manquant (virement versements)</span>}
                {data.setup.has_iban && <span>✓ IBAN OK</span>}
              </div>
            </div>
            <Link
              to="/billing"
              data-testid="setup-goto-account"
              className="h-10 px-4 rounded-full bg-[#D97706] hover:bg-[#B45309] text-white text-sm font-medium flex items-center gap-1 shrink-0"
            >
              Compléter <ArrowRight size={14} />
            </Link>
          </div>
        )}

        {/* KPI Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <KpiCard
            testId="kpi-revenue"
            label="Chiffre d'affaires"
            value={fmtEur(data.revenue.total_eur)}
            sub={`${fmtEur(data.revenue.last_30d_eur)} ces 30j`}
            icon={CurrencyEur}
            accent="#EA580C"
          />
          <KpiCard
            testId="kpi-orders"
            label="Commandes"
            value={fmtNum(data.orders.paid)}
            sub={`${data.orders.pending} en attente · ${data.orders.refunded} remboursées`}
            icon={ShoppingBag}
            accent="#2563EB"
          />
          <KpiCard
            testId="kpi-margin"
            label="Part Concepteur reçue"
            value={fmtEur(data.balance.order_share_paid_eur)}
            sub={`Net à virer : ${fmtEur(data.balance.net_due_eur)}`}
            icon={TrendUp}
            accent="#047857"
          />
          <KpiCard
            testId="kpi-refunds"
            label="Retours"
            value={`${data.refunds.rate_pct}%`}
            sub={`${data.refunds.count} · ${fmtEur(data.refunds.amount_eur)}`}
            icon={Receipt}
            accent={data.refunds.rate_pct > 8 ? "#BE123C" : "#78716C"}
          />
        </div>

        {/* Next events */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
          <NextEventCard
            testId="next-payout"
            label="Prochain versement Mollie"
            date={data.next_events.payout.date}
            amount={data.next_events.payout.amount_eur}
            status={data.next_events.payout.status}
            statusOkLabel="Programmé"
            statusBlockedLabel="IBAN manquant"
            icon={ArrowDown}
            color="#047857"
          />
          <NextEventCard
            testId="next-debit"
            label="Prochain prélèvement Ads"
            date={data.next_events.debit.date}
            amount={data.next_events.debit.amount_eur}
            status={data.next_events.debit.status}
            statusOkLabel="Programmé"
            statusBlockedLabel="Carte manquante"
            icon={ArrowUp}
            color="#BE123C"
          />
        </div>

        {/* Sites list */}
        <div className="bg-white rounded-2xl border border-[#E7E5E4] p-6">
          <div className="flex items-center justify-between mb-5">
            <div>
              <div className="text-[11px] uppercase tracking-widest text-[#78716C]">Mes sites</div>
              <h2 className="font-heading text-xl font-semibold text-[#1C1917]">
                {data.sites.total} site{data.sites.total > 1 ? "s" : ""} ({data.sites.active} actif
                {data.sites.active > 1 ? "s" : ""})
              </h2>
            </div>
            <Link
              to="/sites"
              data-testid="dash-goto-sites"
              className="text-sm text-[#EA580C] hover:underline font-medium"
            >
              Voir tout →
            </Link>
          </div>

          {data.sites.total === 0 ? (
            <div className="py-12 text-center border-2 border-dashed border-[#E7E5E4] rounded-xl">
              <Storefront size={40} weight="thin" className="mx-auto text-[#D6D3D1] mb-3" />
              <div className="text-[#78716C] mb-4">Aucun site pour l'instant.</div>
              <Link
                to="/sites/new"
                data-testid="dash-empty-launch"
                className="inline-flex items-center gap-2 h-11 px-5 rounded-full bg-gradient-to-r from-[#F59E0B] to-[#EA580C] text-white font-medium text-sm"
              >
                <Rocket size={16} weight="fill" /> Lancer ton 1er site
              </Link>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {data.sites.items.slice(0, 9).map((s) => (
                <Link
                  key={s.id}
                  to={`/sites/${s.id}`}
                  data-testid={`dash-site-${s.id}`}
                  className="block p-4 rounded-xl border border-[#E7E5E4] bg-[#FAF7F2] hover:border-[#EA580C] hover:bg-white transition"
                >
                  <div className="flex items-center justify-between mb-1">
                    <div className="font-medium text-[#1C1917] truncate pr-2">{s.name}</div>
                    {s.ads_active ? (
                      <span className="text-[10px] uppercase tracking-wider font-semibold px-2 py-0.5 rounded-full bg-[#D1FAE5] text-[#047857]">
                        ● Actif
                      </span>
                    ) : (
                      <span className="text-[10px] uppercase tracking-wider font-semibold px-2 py-0.5 rounded-full bg-[#F5F2EB] text-[#78716C]">
                        En pause
                      </span>
                    )}
                  </div>
                  {s.domain && (
                    <div className="font-mono text-xs text-[#78716C] truncate">{s.domain}</div>
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

function KpiCard({ label, value, sub, icon: Icon, accent = "#EA580C", testId }) {
  return (
    <div
      className="bg-white rounded-2xl border border-[#E7E5E4] p-5 hover:border-[#D6D3D1] transition"
      data-testid={testId}
    >
      <div className="flex items-start justify-between mb-4">
        <div className="text-[11px] uppercase tracking-widest text-[#78716C] font-medium">
          {label}
        </div>
        <div
          className="w-9 h-9 rounded-lg flex items-center justify-center"
          style={{ background: `${accent}14` }}
        >
          <Icon size={18} weight="duotone" color={accent} />
        </div>
      </div>
      <div
        className="text-3xl font-semibold tracking-tight leading-tight"
        style={{ fontFamily: 'Georgia, serif' }}
      >
        {value}
      </div>
      {sub && <div className="text-xs text-[#78716C] mt-1.5">{sub}</div>}
    </div>
  );
}

function NextEventCard({ label, date, amount, status, statusOkLabel, statusBlockedLabel, icon: Icon, color, testId }) {
  const blocked = status && status.startsWith("blocked");
  return (
    <div className="bg-white rounded-2xl border border-[#E7E5E4] p-5" data-testid={testId}>
      <div className="flex items-start justify-between mb-3">
        <div className="text-[11px] uppercase tracking-widest text-[#78716C] font-medium">
          {label}
        </div>
        <div
          className="w-9 h-9 rounded-lg flex items-center justify-center"
          style={{ background: `${color}14` }}
        >
          <Icon size={18} weight="bold" color={color} />
        </div>
      </div>
      <div className="flex items-baseline gap-3 mb-2">
        <div
          className="text-3xl font-semibold tracking-tight"
          style={{ fontFamily: 'Georgia, serif', color }}
        >
          {fmtEur(amount)}
        </div>
      </div>
      <div className="flex items-center gap-2 text-xs">
        <Clock size={12} weight="bold" className="text-[#78716C]" />
        <span className="text-[#57534E]">{fmtDate(date)}</span>
        {blocked ? (
          <span className="ml-auto font-semibold text-[#BE123C] flex items-center gap-1">
            <Warning size={11} weight="fill" />
            {statusBlockedLabel}
          </span>
        ) : (
          <span className="ml-auto font-medium text-[#047857] flex items-center gap-1">
            <CheckCircle size={11} weight="fill" />
            {statusOkLabel}
          </span>
        )}
      </div>
    </div>
  );
}
