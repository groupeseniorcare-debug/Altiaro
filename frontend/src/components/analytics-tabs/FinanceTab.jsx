import React, { useEffect, useState, useCallback, useMemo } from "react";
import {
  CurrencyEur, Wallet, TrendUp, CalendarBlank, CircleNotch, ArrowUp, ArrowDown, Minus,
} from "@phosphor-icons/react";
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
} from "recharts";
import { api, apiCall } from "../../lib/api";

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

export default function FinanceTab({ siteId, isAdmin }) {
  const [overview, setOverview] = useState(null);
  const [balance, setBalance] = useState(null);
  const [ledger, setLedger] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    const [ov, bal, led] = await Promise.all([
      apiCall(() => api.get(`/sites/${siteId}/analytics/overview?range=30d`)),
      apiCall(() => api.get(`/billing/balance`)),
      apiCall(() => api.get(`/billing/ledger`)),
    ]);
    if (!ov.error) setOverview(ov.data);
    if (!bal.error) setBalance(bal.data);
    if (!led.error) {
      const arr = Array.isArray(led.data) ? led.data : (led.data?.entries || led.data?.ledger || []);
      setLedger(arr.filter(e => !siteId || e.site_id === siteId || !e.site_id).slice(0, 10));
    }
    setLoading(false);
  }, [siteId]);

  useEffect(() => { load(); }, [load]);

  const marginGross = useMemo(() => {
    // Marge brute = somme des gross_margin_ht du ledger sur 30j, sinon fallback revenue*40%
    if (ledger && ledger.length) {
      const sum = ledger.reduce((s, e) => s + Number(e.gross_margin_ht || 0), 0);
      if (sum > 0) return sum;
    }
    const total = overview?.revenue?.total || 0;
    return Math.round(total * 0.4 * 100) / 100;
  }, [ledger, overview]);

  const ca30 = overview?.revenue?.total || 0;
  const pendingPayout = balance?.pending_payout_eur || balance?.pending || 0;
  const nextPayoutDate = balance?.next_payout_date || null;

  return (
    <div data-testid="finance-tab">
      {loading ? (
        <div className="py-20 text-neutral-500 text-sm flex items-center justify-center gap-2">
          <CircleNotch size={16} className="animate-spin" /> Chargement finance…
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8" data-testid="finance-kpis">
            <KpiCard
              icon={CurrencyEur}
              label="CA 30 jours"
              value={`${ca30.toLocaleString("fr-FR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} €`}
              sub={`${overview?.revenue?.orders_count || 0} commandes · AOV ${overview?.revenue?.aov || 0} €`}
              delta={overview?.vs_previous?.revenue_pct}
              testId="kpi-ca"
            />
            <KpiCard
              icon={TrendUp}
              label="Marge brute (30j)"
              value={`${marginGross.toLocaleString("fr-FR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} €`}
              sub={ca30 > 0 ? `${Math.round((marginGross / ca30) * 100)}% du CA` : "—"}
              testId="kpi-margin"
            />
            <KpiCard
              icon={Wallet}
              label="Payout en attente"
              value={`${Number(pendingPayout).toLocaleString("fr-FR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} €`}
              sub="Solde non encore viré"
              testId="kpi-pending"
            />
            <KpiCard
              icon={CalendarBlank}
              label="Prochain payout"
              value={nextPayoutDate ? new Date(nextPayoutDate).toLocaleDateString("fr-FR") : "1er / 15 du mois"}
              sub="Virement SEPA bi-mensuel"
              testId="kpi-next-payout"
            />
          </div>

          {overview?.daily && overview.daily.length > 0 && (
            <div className="bg-white rounded-xl border border-neutral-200 p-5 mb-8" data-testid="finance-daily">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-semibold text-neutral-900">Revenu quotidien (30j)</h3>
                <span className="text-[11px] text-neutral-500">Source : storefront_events</span>
              </div>
              <div className="w-full h-[240px]">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={overview.daily} margin={{ top: 5, right: 10, bottom: 5, left: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f5f5f4" />
                    <XAxis dataKey="date" tick={{ fontSize: 11, fill: "#737373" }} />
                    <YAxis tick={{ fontSize: 11, fill: "#737373" }} />
                    <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8 }} />
                    <Line type="monotone" dataKey="revenue" name="Revenu (€)" stroke="#B84B31" strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          <div className="bg-white rounded-xl border border-neutral-200 overflow-hidden">
            <div className="p-5 border-b border-neutral-100">
              <h3 className="text-sm font-semibold text-neutral-900 mb-1">Payouts récents</h3>
              <p className="text-[11px] text-neutral-500">Derniers mouvements du ledger (limit 10)</p>
            </div>
            {ledger.length === 0 ? (
              <div className="py-10 px-6 text-center text-sm text-neutral-500" data-testid="finance-ledger-empty">
                Aucun mouvement encore enregistré pour ce site.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-[11px] uppercase tracking-widest text-neutral-500 bg-neutral-50 text-left">
                      <th className="py-3 px-4 font-medium">Date</th>
                      <th className="py-3 px-4 font-medium">Type</th>
                      <th className="py-3 px-4 font-medium">Description</th>
                      <th className="py-3 px-4 text-right font-medium">Montant</th>
                      <th className="py-3 px-4 font-medium">Statut</th>
                      {isAdmin && <th className="py-3 px-4 text-right font-medium">Commission Altiaro</th>}
                    </tr>
                  </thead>
                  <tbody>
                    {ledger.map((e) => {
                      const dt = e.created_at ? new Date(e.created_at) : null;
                      const amount = Number(e.amount ?? e.gross_margin_ht ?? 0);
                      const commission = Number(e.gross_margin_ht || 0) / 2;
                      return (
                        <tr key={e.id || `${e.order_id}-${e.type}`} className="border-t border-neutral-100">
                          <td className="py-3 px-4 text-neutral-600">{dt ? dt.toLocaleDateString("fr-FR") : "—"}</td>
                          <td className="py-3 px-4 text-neutral-700">{e.type || "—"}</td>
                          <td className="py-3 px-4 text-neutral-600 max-w-sm truncate">{e.description || e.order_number || "—"}</td>
                          <td className="py-3 px-4 text-right tabular-nums font-medium text-neutral-900">
                            {amount.toFixed(2)} €
                          </td>
                          <td className="py-3 px-4 text-neutral-600 capitalize">{e.status || "—"}</td>
                          {isAdmin && (
                            <td className="py-3 px-4 text-right tabular-nums text-neutral-500">
                              {commission > 0 ? `${commission.toFixed(2)} €` : "—"}
                            </td>
                          )}
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
