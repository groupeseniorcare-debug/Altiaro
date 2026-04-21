import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api, apiCall } from "../lib/api";
import { useAuth } from "../lib/auth";
import Layout from "../components/Layout";
import AdminFinances from "./Finances";
import {
  ArrowDown,
  ArrowUp,
  ArrowClockwise,
  ArrowsLeftRight,
  Bank,
  CheckCircle,
  Clock,
  CurrencyEur,
  FunnelSimple,
  Receipt,
  Warning,
  XCircle,
} from "@phosphor-icons/react";

const fmtEur = (n) =>
  new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR" }).format(n || 0);

const fmtDate = (iso) => {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    return d.toLocaleDateString("fr-FR", { day: "2-digit", month: "short", year: "numeric" });
  } catch {
    return iso;
  }
};

const TYPE_META = {
  order_share: {
    label: "Part commande",
    flow: "credit",
    icon: ArrowDown,
    color: "#047857",
    bg: "#D1FAE5",
  },
  payout: {
    label: "Versement Mollie",
    flow: "payout",
    icon: Bank,
    color: "#2563EB",
    bg: "#DBEAFE",
  },
  ad_debit: {
    label: "Prélèvement Ads",
    flow: "debit",
    icon: ArrowUp,
    color: "#BE123C",
    bg: "#FFE4E6",
  },
};

const STATUS_META = {
  paid: { label: "Payé", color: "#047857", icon: CheckCircle },
  pending: { label: "En attente", color: "#D97706", icon: Clock },
  failed: { label: "Échec", color: "#BE123C", icon: XCircle },
  scheduled: { label: "Programmé", color: "#2563EB", icon: Clock },
};

const presets = [
  { label: "7 jours", days: 7 },
  { label: "30 jours", days: 30 },
  { label: "90 jours", days: 90 },
  { label: "Cette année", days: null, since: () => new Date(new Date().getFullYear(), 0, 1) },
  { label: "Tout", days: null },
];

export default function Finance() {
  const { user } = useAuth();
  if (user && user.role === "admin") return <AdminFinances />;
  return <ConcepteurFinance />;
}

function ConcepteurFinance() {
  const [ledger, setLedger] = useState(null);
  const [loading, setLoading] = useState(true);
  const [sites, setSites] = useState([]);
  const [filters, setFilters] = useState({ site_id: "", type: "", since: "", until: "" });

  useEffect(() => {
    apiCall(() => api.get("/sites")).then(({ data }) => setSites(data || []));
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    const params = new URLSearchParams();
    if (filters.site_id) params.set("site_id", filters.site_id);
    if (filters.type) params.set("type", filters.type);
    if (filters.since) params.set("since", new Date(filters.since).toISOString());
    if (filters.until) {
      const end = new Date(filters.until);
      end.setHours(23, 59, 59, 999);
      params.set("until", end.toISOString());
    }
    params.set("limit", "500");
    const { data } = await apiCall(() => api.get(`/concepteur/finance/ledger?${params.toString()}`));
    setLedger(data);
    setLoading(false);
  }, [filters]);

  useEffect(() => {
    load();
  }, [load]);

  const applyPreset = (preset) => {
    const until = new Date();
    let since = null;
    if (preset.since) {
      since = preset.since();
    } else if (preset.days !== null) {
      since = new Date();
      since.setDate(since.getDate() - preset.days);
    }
    setFilters((f) => ({
      ...f,
      since: since ? since.toISOString().slice(0, 10) : "",
      until: preset.days !== null || preset.since ? until.toISOString().slice(0, 10) : "",
    }));
  };

  const totals = ledger?.totals;
  const netFlow = useMemo(() => {
    if (!totals) return 0;
    return (
      (totals.credits?.order_share || 0) -
      (totals.debits?.ad_debit_paid || 0) -
      (totals.payouts?.paid || 0)
    );
  }, [totals]);

  return (
    <Layout>
      <div className="p-8 md:p-10 max-w-[1400px]">
        {/* Header */}
        <div className="mb-6">
          <div className="text-[10px] uppercase tracking-[0.12em] text-neutral-500 font-medium mb-1.5">
            Ledger unifié
          </div>
          <h1 className="text-3xl font-semibold text-neutral-900 tracking-tight">Finance</h1>
          <p className="text-neutral-500 text-sm mt-1 max-w-xl">
            Toutes tes entrées et sorties : parts commandes, prélèvements Ads, versements Mollie.
            Filtre par site, période ou type.
          </p>
        </div>

        {/* Totals */}
        {totals && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <TotalCard
              testId="total-credits"
              label="Parts commandes"
              sub={`${totals.credits.count_order_share} transaction${totals.credits.count_order_share > 1 ? "s" : ""}`}
              value={fmtEur(totals.credits.order_share)}
              color="#047857"
              flow="Crédits"
              icon={ArrowDown}
            />
            <TotalCard
              testId="total-debits"
              label="Prélèvements Ads"
              sub={
                totals.debits.ad_debit_pending > 0
                  ? `+ ${fmtEur(totals.debits.ad_debit_pending)} en attente`
                  : `${totals.debits.count_ad_debit} prélèvement${totals.debits.count_ad_debit > 1 ? "s" : ""}`
              }
              value={fmtEur(totals.debits.ad_debit_paid)}
              color="#BE123C"
              flow="Débits"
              icon={ArrowUp}
            />
            <TotalCard
              testId="total-payouts"
              label="Versements Mollie"
              sub={
                totals.payouts.pending > 0
                  ? `+ ${fmtEur(totals.payouts.pending)} en attente`
                  : `${totals.payouts.count} virement${totals.payouts.count > 1 ? "s" : ""}`
              }
              value={fmtEur(totals.payouts.paid)}
              color="#2563EB"
              flow="Virés"
              icon={Bank}
            />
          </div>
        )}

        {/* Filters */}
        <div className="bg-white rounded-md border border-neutral-200 p-5 mb-5" data-testid="finance-filters">
          <div className="flex items-center gap-2 mb-4">
            <FunnelSimple size={16} className="text-neutral-500" />
            <div className="text-xs uppercase tracking-widest text-neutral-500 font-semibold">Filtres</div>
            <div className="ml-auto flex gap-2 flex-wrap">
              {presets.map((p) => (
                <button
                  key={p.label}
                  onClick={() => applyPreset(p)}
                  data-testid={`preset-${p.label}`}
                  className="h-8 px-3 rounded-full text-xs font-medium border border-neutral-200 text-neutral-600 hover:bg-neutral-100/40 hover:border-neutral-300 transition"
                >
                  {p.label}
                </button>
              ))}
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
            <FilterField label="Site">
              <select
                value={filters.site_id}
                onChange={(e) => setFilters({ ...filters, site_id: e.target.value })}
                data-testid="filter-site"
                className="w-full h-10 px-3 rounded-lg border border-neutral-200 bg-white text-sm focus:outline-none focus:border-neutral-300"
              >
                <option value="">Tous les sites</option>
                {sites.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>
            </FilterField>
            <FilterField label="Type">
              <select
                value={filters.type}
                onChange={(e) => setFilters({ ...filters, type: e.target.value })}
                data-testid="filter-type"
                className="w-full h-10 px-3 rounded-lg border border-neutral-200 bg-white text-sm focus:outline-none focus:border-neutral-300"
              >
                <option value="">Tous</option>
                <option value="order_share">Parts commandes</option>
                <option value="ad_debit">Prélèvements Ads</option>
                <option value="payout">Versements</option>
              </select>
            </FilterField>
            <FilterField label="Depuis">
              <input
                type="date"
                value={filters.since}
                onChange={(e) => setFilters({ ...filters, since: e.target.value })}
                data-testid="filter-since"
                className="w-full h-10 px-3 rounded-lg border border-neutral-200 bg-white text-sm focus:outline-none focus:border-neutral-300"
              />
            </FilterField>
            <FilterField label="Jusqu'au">
              <input
                type="date"
                value={filters.until}
                onChange={(e) => setFilters({ ...filters, until: e.target.value })}
                data-testid="filter-until"
                className="w-full h-10 px-3 rounded-lg border border-neutral-200 bg-white text-sm focus:outline-none focus:border-neutral-300"
              />
            </FilterField>
          </div>
          {(filters.site_id || filters.type || filters.since || filters.until) && (
            <div className="mt-3 flex items-center justify-between">
              <div className="text-xs text-neutral-600">
                {ledger?.count || 0} transactions · flux net :{" "}
                <strong style={{ color: netFlow >= 0 ? "#047857" : "#BE123C" }}>
                  {fmtEur(netFlow)}
                </strong>
              </div>
              <button
                onClick={() => setFilters({ site_id: "", type: "", since: "", until: "" })}
                data-testid="filter-clear"
                className="text-xs text-neutral-900 hover:underline"
              >
                Effacer les filtres
              </button>
            </div>
          )}
        </div>

        {/* Ledger table */}
        <div className="bg-white rounded-md border border-neutral-200 overflow-hidden" data-testid="ledger-table">
          {loading ? (
            <div className="p-12 text-center text-neutral-500 flex items-center gap-2 justify-center">
              <ArrowClockwise size={16} className="animate-spin" /> Chargement…
            </div>
          ) : ledger?.entries?.length === 0 ? (
            <div className="p-16 text-center">
              <Receipt size={40} weight="thin" className="mx-auto text-neutral-400 mb-3" />
              <div className="text-neutral-500 mb-1">Aucune transaction sur cette période.</div>
              <div className="text-xs text-neutral-400">
                Les entrées apparaîtront ici dès que tes sites réaliseront des ventes.
              </div>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-neutral-100/40 border-b border-neutral-200">
                  <tr>
                    <Th>Date</Th>
                    <Th>Type</Th>
                    <Th>Site</Th>
                    <Th>Détail</Th>
                    <Th>Statut</Th>
                    <Th align="right">Montant</Th>
                  </tr>
                </thead>
                <tbody>
                  {ledger.entries.map((e) => (
                    <LedgerRow key={e.id} entry={e} />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <div className="mt-6 p-4 rounded-md bg-neutral-100/40 border border-neutral-200">
          <div className="flex items-start gap-2 text-xs text-neutral-600 leading-relaxed">
            <Warning size={14} className="text-amber-400 shrink-0 mt-0.5" />
            <div>
              Les versements Mollie sont exécutés <strong>tous les 15 jours</strong> sur l'IBAN
              renseigné dans ton <Link to="/billing" className="text-neutral-900 underline">Compte</Link>.
              Les prélèvements Ads sont hebdomadaires (50% du budget dépensé).
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
}

function TotalCard({ label, value, sub, color, flow, icon: Icon, testId }) {
  return (
    <div
      className="rounded-md p-4 border bg-white"
      style={{ borderColor: "#27272A" }}
      data-testid={testId}
    >
      <div className="flex items-center justify-between mb-3">
        <div>
          <div className="text-[10px] uppercase tracking-[0.12em] font-semibold" style={{ color }}>
            {flow}
          </div>
          <div className="text-[11px] text-neutral-500 mt-0.5">{label}</div>
        </div>
        <Icon size={14} weight="bold" className="text-neutral-400" />
      </div>
      <div
        className="text-2xl font-semibold tracking-tight leading-none font-mono tabular-nums"
        style={{ color }}
      >
        {value}
      </div>
      <div className="text-[11px] text-neutral-500 mt-1.5">{sub}</div>
    </div>
  );
}

function FilterField({ label, children }) {
  return (
    <div>
      <label className="block text-[11px] uppercase tracking-widest text-neutral-500 font-medium mb-1">
        {label}
      </label>
      {children}
    </div>
  );
}

function Th({ children, align = "left" }) {
  return (
    <th
      className={`px-4 py-3 text-[11px] uppercase tracking-widest text-neutral-500 font-semibold text-${align}`}
    >
      {children}
    </th>
  );
}

function LedgerRow({ entry }) {
  const type = TYPE_META[entry.type] || {
    label: entry.type,
    icon: ArrowsLeftRight,
    color: "#78716C",
    bg: "#F5F2EB",
    flow: "credit",
  };
  const status = STATUS_META[entry.status] || STATUS_META.pending;
  const StatusIcon = status.icon;
  const TypeIcon = type.icon;
  const amountSign = type.flow === "credit" ? "+" : "−";
  const amountColor = type.flow === "credit" ? "#047857" : "#BE123C";

  return (
    <tr
      className="border-b border-neutral-200 hover:bg-neutral-100/40 transition"
      data-testid={`row-${entry.id}`}
    >
      <td className="px-4 py-3 text-neutral-600 whitespace-nowrap">{fmtDate(entry.created_at)}</td>
      <td className="px-4 py-3">
        <div className="flex items-center gap-2">
          <div
            className="w-7 h-7 rounded-full flex items-center justify-center"
            style={{ background: type.bg }}
          >
            <TypeIcon size={12} weight="bold" color={type.color} />
          </div>
          <span className="font-medium text-neutral-900">{type.label}</span>
        </div>
      </td>
      <td className="px-4 py-3 text-neutral-600">{entry.site_name || "—"}</td>
      <td className="px-4 py-3 text-xs text-neutral-500">
        {entry.note ||
          (entry.order_number ? `Cmd #${entry.order_number}` : entry.id.slice(0, 10))}
      </td>
      <td className="px-4 py-3">
        <span
          className="inline-flex items-center gap-1 text-xs font-medium"
          style={{ color: status.color }}
        >
          <StatusIcon size={12} weight="fill" />
          {status.label}
        </span>
      </td>
      <td
        className="px-4 py-3 text-right font-mono font-semibold"
        style={{ color: amountColor }}
      >
        {amountSign}
        {fmtEur(entry.amount)}
      </td>
    </tr>
  );
}
