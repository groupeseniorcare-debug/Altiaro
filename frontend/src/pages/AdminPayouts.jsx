import React, { useEffect, useState, useCallback } from "react";
import { Link } from "react-router-dom";
import Layout from "../components/Layout";
import { api, apiCall } from "../lib/api";
import {
  Bank,
  Copy,
  CheckCircle,
  XCircle,
  CaretDown,
  CaretUp,
  CalendarBlank,
  Warning,
  ArrowClockwise,
  CurrencyEur,
  ClockCountdown,
  Receipt,
  Sparkle,
} from "@phosphor-icons/react";

const fmt = (n) =>
  new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR", maximumFractionDigits: 2 }).format(
    Number(n) || 0
  );

const fmtDate = (iso) => {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleDateString("fr-FR", { day: "numeric", month: "long", year: "numeric" });
};

export default function AdminPayouts() {
  const [preview, setPreview] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [expanded, setExpanded] = useState({});
  const [copiedIban, setCopiedIban] = useState(null);
  const [tab, setTab] = useState("pending"); // pending | history
  const [toast, setToast] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    const [p, h] = await Promise.all([
      apiCall(() => api.get("/admin/billing/payouts-preview")),
      apiCall(() => api.get("/admin/billing/payouts-history?limit=200")),
    ]);
    if (p.data) setPreview(p.data);
    if (h.data) setHistory(h.data.items || []);
    setLoading(false);
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const pendingPayouts = history.filter((e) => e.status === "pending");
  const paidPayouts = history.filter((e) => e.status === "paid");

  const runPayouts = async () => {
    if (!window.confirm("Générer la liste des virements à effectuer ? Les soldes positifs seront figés en 'à virer'.")) return;
    setRunning(true);
    const { data, error } = await apiCall(() => api.post("/admin/billing/run-payouts"));
    setRunning(false);
    if (error) return setToast(`❌ ${error}`);
    setToast(`✓ ${data.payouts_created} virement(s) générés — ${fmt(data.total_eur)}`);
    await load();
    setTimeout(() => setToast(""), 4000);
  };

  const markPaid = async (id) => {
    const { error } = await apiCall(() => api.post(`/admin/billing/payouts/${id}/mark-paid`));
    if (error) return setToast(`❌ ${error}`);
    setToast("✓ Marqué comme payé");
    await load();
    setTimeout(() => setToast(""), 3000);
  };

  const cancelPayout = async (id) => {
    if (!window.confirm("Annuler ce virement ? Le solde repartira sur le prochain cycle.")) return;
    const { error } = await apiCall(() => api.post(`/admin/billing/payouts/${id}/cancel`));
    if (error) return setToast(`❌ ${error}`);
    setToast("✓ Annulé");
    await load();
    setTimeout(() => setToast(""), 3000);
  };

  const copyIban = (iban, userId) => {
    if (!iban) return;
    navigator.clipboard.writeText(iban.replace(/\s+/g, "")).then(() => {
      setCopiedIban(userId);
      setTimeout(() => setCopiedIban(null), 1800);
    });
  };

  if (loading) {
    return (
      <Layout>
        <div className="p-8 text-zinc-500">Chargement…</div>
      </Layout>
    );
  }

  const rows = preview?.rows || [];
  const totalDue = preview?.total_due_eur || 0;
  const nextCycle = preview?.next_cycle_date;

  return (
    <Layout>
      <div className="p-6 md:p-10 max-w-[1500px]">
        {/* Header */}
        <div className="mb-8 animate-fade-up">
          <div className="text-[11px] uppercase tracking-widest text-zinc-500 mb-2">Administration · Trésorerie</div>
          <h1 className="text-3xl font-semibold text-zinc-100">Virements Concepteurs</h1>
          <p className="text-zinc-400 mt-2 max-w-2xl">
            Liste des virements à effectuer, par Concepteur. Formule&nbsp;: <strong>50% × marge brute HT</strong> (CA HT − Prix d'achat HT),
            calculée automatiquement les 1<sup>er</sup> et 15 de chaque mois.
          </p>
        </div>

        {/* KPI row */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <KpiCard
            icon={CurrencyEur}
            color="#B84B31"
            label="À virer maintenant"
            value={fmt(pendingPayouts.reduce((s, p) => s + Number(p.amount || 0), 0))}
            hint={`${pendingPayouts.length} virement(s) en attente`}
            testId="kpi-to-pay"
          />
          <KpiCard
            icon={Sparkle}
            color="#047857"
            label="Aperçu prochain cycle"
            value={fmt(totalDue)}
            hint={`${rows.length} Concepteur(s) concerné(s)`}
            testId="kpi-preview"
          />
          <KpiCard
            icon={CalendarBlank}
            color="#0E7490"
            label="Prochain cycle automatique"
            value={fmtDate(nextCycle)}
            hint="Génération auto 03h00 UTC"
            testId="kpi-next-cycle"
          />
          <KpiCard
            icon={CheckCircle}
            color="#166534"
            label="Déjà versé (total)"
            value={fmt(paidPayouts.reduce((s, p) => s + Number(p.amount || 0), 0))}
            hint={`${paidPayouts.length} virement(s) exécuté(s)`}
            testId="kpi-paid-total"
          />
        </div>

        {/* Actions bar */}
        <div className="flex flex-wrap items-center gap-3 mb-6">
          <button
            onClick={load}
            className="h-10 px-4 rounded-xl border border-zinc-800 bg-zinc-950 hover:border-[#B84B31] text-sm flex items-center gap-2 transition"
            data-testid="refresh-btn"
          >
            <ArrowClockwise size={14} /> Actualiser
          </button>
          <button
            onClick={runPayouts}
            disabled={running || rows.length === 0}
            className="h-10 px-5 rounded-xl bg-white hover:bg-zinc-200 text-black text-sm font-medium flex items-center gap-2 transition disabled:opacity-40"
            data-testid="run-payouts-btn"
          >
            {running ? "Génération..." : (
              <>
                <Sparkle size={14} weight="fill" /> Générer les virements du cycle
              </>
            )}
          </button>
          {toast && (
            <div className="px-3 py-1.5 rounded-lg bg-[#DCF5E7] text-[#166534] text-sm border border-[#86EFAC]" data-testid="toast">
              {toast}
            </div>
          )}
        </div>

        {/* Tabs */}
        <div className="border-b border-zinc-800 mb-6 flex gap-6">
          <TabButton active={tab === "pending"} onClick={() => setTab("pending")} testId="tab-pending">
            <ClockCountdown size={16} /> À effectuer ({pendingPayouts.length})
          </TabButton>
          <TabButton active={tab === "preview"} onClick={() => setTab("preview")} testId="tab-preview">
            <Sparkle size={16} /> Aperçu prochain cycle ({rows.length})
          </TabButton>
          <TabButton active={tab === "history"} onClick={() => setTab("history")} testId="tab-history">
            <Receipt size={16} /> Historique ({paidPayouts.length})
          </TabButton>
        </div>

        {/* Tab : À effectuer maintenant (pending payouts figés) */}
        {tab === "pending" && (
          <PendingTable
            items={pendingPayouts}
            onMarkPaid={markPaid}
            onCancel={cancelPayout}
            copyIban={copyIban}
            copiedIban={copiedIban}
          />
        )}

        {/* Tab : Preview prochain cycle */}
        {tab === "preview" && (
          <PreviewTable
            rows={rows}
            expanded={expanded}
            setExpanded={setExpanded}
            copyIban={copyIban}
            copiedIban={copiedIban}
          />
        )}

        {/* Tab : Historique */}
        {tab === "history" && <HistoryTable items={paidPayouts} />}
      </div>
    </Layout>
  );
}

/* ---------- Sub-components ---------- */

function KpiCard({ icon: Icon, color, label, value, hint, testId }) {
  return (
    <div
      className="bg-zinc-950 rounded-md border border-zinc-800 p-5 hover:shadow-md transition"
      data-testid={testId}
    >
      <div className="flex items-center gap-2 mb-3">
        <div
          className="w-9 h-9 rounded-lg flex items-center justify-center"
          style={{ background: `${color}18`, color }}
        >
          <Icon size={18} weight="fill" />
        </div>
        <div className="text-[11px] uppercase tracking-widest text-zinc-500">{label}</div>
      </div>
      <div className="text-xl font-semibold text-zinc-100 tabular-nums">{value}</div>
      <div className="text-xs text-zinc-500 mt-1">{hint}</div>
    </div>
  );
}

function TabButton({ active, onClick, children, testId }) {
  return (
    <button
      onClick={onClick}
      data-testid={testId}
      className={`flex items-center gap-2 py-3 text-sm font-medium border-b-2 transition -mb-px ${
        active ? "border-[#B84B31] text-zinc-100" : "border-transparent text-zinc-500 hover:text-zinc-100"
      }`}
    >
      {children}
    </button>
  );
}

function EmptyState({ title, subtitle }) {
  return (
    <div className="bg-zinc-950 rounded-md border border-dashed border-zinc-800 p-16 text-center">
      <Bank size={40} weight="thin" className="mx-auto text-zinc-700 mb-3" />
      <div className="text-base font-medium text-zinc-100">{title}</div>
      <div className="text-sm text-zinc-500 mt-1.5">{subtitle}</div>
    </div>
  );
}

function PendingTable({ items, onMarkPaid, onCancel, copyIban, copiedIban }) {
  if (items.length === 0) {
    return (
      <EmptyState
        title="Aucun virement à effectuer pour l'instant"
        subtitle="Les virements seront générés automatiquement le 1er et le 15 de chaque mois, ou manuellement via le bouton ci-dessus."
      />
    );
  }
  return (
    <div className="bg-zinc-950 rounded-md border border-zinc-800 overflow-hidden" data-testid="pending-table">
      <table className="w-full">
        <thead className="bg-black text-[11px] uppercase tracking-widest text-zinc-500">
          <tr>
            <th className="text-left px-5 py-3">Concepteur</th>
            <th className="text-left px-5 py-3">IBAN</th>
            <th className="text-right px-5 py-3">Montant</th>
            <th className="text-right px-5 py-3">Généré le</th>
            <th className="text-right px-5 py-3">Actions</th>
          </tr>
        </thead>
        <tbody>
          {items.map((p) => (
            <tr key={p.id} className="border-t border-zinc-800 hover:bg-black transition" data-testid={`pending-row-${p.id}`}>
              <td className="px-5 py-4">
                <div className="font-medium text-zinc-100">{p.concepteur_name || p.holder_name || "—"}</div>
                <div className="text-xs text-zinc-500">{p.concepteur_email || ""}</div>
              </td>
              <td className="px-5 py-4">
                <div className="font-mono text-sm text-zinc-100">{maskIban(p.iban)}</div>
                <div className="text-xs text-zinc-500">{p.bic ? `BIC ${p.bic}` : ""} · {p.holder_name}</div>
              </td>
              <td className="px-5 py-4 text-right">
                <div className="text-base font-semibold text-zinc-100 tabular-nums">{fmt(p.amount)}</div>
              </td>
              <td className="px-5 py-4 text-right text-sm text-zinc-500 tabular-nums">{fmtDate(p.created_at)}</td>
              <td className="px-5 py-4">
                <div className="flex items-center gap-1.5 justify-end">
                  <button
                    onClick={() => copyIban(p.iban, p.id)}
                    data-testid={`copy-iban-${p.id}`}
                    className="h-9 px-3 rounded-lg border border-zinc-800 hover:border-[#B84B31] text-xs flex items-center gap-1.5 transition"
                  >
                    {copiedIban === p.id ? (
                      <><CheckCircle size={12} weight="fill" className="text-emerald-400" /> Copié</>
                    ) : (
                      <><Copy size={12} /> IBAN</>
                    )}
                  </button>
                  <button
                    onClick={() => onMarkPaid(p.id)}
                    data-testid={`mark-paid-${p.id}`}
                    className="h-9 px-3 rounded-lg bg-white hover:bg-zinc-200 text-black text-xs font-medium flex items-center gap-1.5 transition"
                  >
                    <CheckCircle size={12} weight="fill" /> Marquer payé
                  </button>
                  <button
                    onClick={() => onCancel(p.id)}
                    data-testid={`cancel-${p.id}`}
                    title="Annuler"
                    className="h-9 w-9 rounded-lg border border-zinc-800 hover:border-[#BE123C] hover:text-red-400 text-zinc-500 flex items-center justify-center transition"
                  >
                    <XCircle size={14} />
                  </button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function PreviewTable({ rows, expanded, setExpanded, copyIban, copiedIban }) {
  if (rows.length === 0) {
    return (
      <EmptyState
        title="Aucune marge à distribuer actuellement"
        subtitle="Les Concepteurs doivent avoir des commandes payées avec prix d'achat renseigné pour apparaître ici."
      />
    );
  }
  return (
    <div className="space-y-3" data-testid="preview-list">
      {rows.map((r) => {
        const open = !!expanded[r.user_id];
        return (
          <div key={r.user_id} className="bg-zinc-950 rounded-md border border-zinc-800 overflow-hidden">
            <div className="p-5 flex items-center gap-4 flex-wrap md:flex-nowrap">
              <div className="flex-1 min-w-0">
                <div className="text-base font-semibold text-zinc-100">{r.name || "Concepteur"}</div>
                <div className="text-sm text-zinc-500">{r.email}</div>
              </div>
              <MiniStat label="Commandes" value={r.orders_count} />
              <MiniStat label="CA HT" value={fmt(r.revenue_ht_total)} />
              <MiniStat label="Achats HT" value={fmt(r.cost_ht_total)} />
              <MiniStat label="Marge HT" value={fmt(r.gross_margin_ht_total)} color="#047857" />
              <div className="text-right">
                <div className="text-[11px] uppercase tracking-widest text-zinc-500">À virer</div>
                <div className="text-xl font-bold text-zinc-100 tabular-nums" data-testid={`net-due-${r.user_id}`}>
                  {fmt(r.net_due_eur)}
                </div>
              </div>
              <button
                onClick={() => setExpanded((e) => ({ ...e, [r.user_id]: !open }))}
                data-testid={`toggle-${r.user_id}`}
                className="h-10 w-10 rounded-lg border border-zinc-800 hover:border-[#B84B31] text-zinc-500 flex items-center justify-center transition"
              >
                {open ? <CaretUp size={16} /> : <CaretDown size={16} />}
              </button>
            </div>

            {open && (
              <div className="border-t border-zinc-800 bg-black p-5 space-y-4">
                {/* IBAN block */}
                {r.has_iban ? (
                  <div className="bg-zinc-950 rounded-xl border border-zinc-800 p-4 flex items-center gap-3 flex-wrap">
                    <Bank size={18} className="text-zinc-500" />
                    <div className="flex-1 min-w-[200px]">
                      <div className="text-[11px] uppercase tracking-widest text-zinc-500">IBAN</div>
                      <div className="font-mono text-sm text-zinc-100 break-all">{formatIban(r.iban)}</div>
                      <div className="text-xs text-zinc-500 mt-0.5">
                        {r.holder_name} {r.bic ? `· BIC ${r.bic}` : ""} {r.iban_bank_name ? `· ${r.iban_bank_name}` : ""}
                      </div>
                    </div>
                    <button
                      onClick={() => copyIban(r.iban, r.user_id)}
                      data-testid={`copy-iban-preview-${r.user_id}`}
                      className="h-10 px-4 rounded-xl border border-zinc-800 hover:border-[#B84B31] text-sm flex items-center gap-2 transition"
                    >
                      {copiedIban === r.user_id ? (
                        <><CheckCircle size={14} weight="fill" className="text-emerald-400" /> Copié !</>
                      ) : (
                        <><Copy size={14} /> Copier l'IBAN</>
                      )}
                    </button>
                  </div>
                ) : (
                  <div className="bg-red-500/10 border border-[#FCA5A5] rounded-xl p-4 flex items-center gap-2 text-sm text-red-400">
                    <Warning size={16} weight="fill" /> Ce Concepteur n'a pas encore enregistré son IBAN — le virement ne sera pas déclenché automatiquement.
                  </div>
                )}

                {/* Ventilation par site */}
                {r.site_breakdown && r.site_breakdown.length > 0 && (
                  <div className="bg-zinc-950 rounded-xl border border-zinc-800 overflow-hidden">
                    <div className="px-4 py-3 border-b border-zinc-800 text-[11px] uppercase tracking-widest text-zinc-500">
                      Ventilation par site
                    </div>
                    <table className="w-full text-sm">
                      <thead className="bg-black text-[11px] uppercase tracking-wider text-zinc-500">
                        <tr>
                          <th className="text-left px-4 py-2">Site</th>
                          <th className="text-right px-4 py-2">Commandes</th>
                          <th className="text-right px-4 py-2">CA HT</th>
                          <th className="text-right px-4 py-2">Achats HT</th>
                          <th className="text-right px-4 py-2">Marge HT</th>
                          <th className="text-right px-4 py-2">Part 50%</th>
                        </tr>
                      </thead>
                      <tbody>
                        {r.site_breakdown.map((s) => (
                          <tr key={s.site_id} className="border-t border-zinc-800">
                            <td className="px-4 py-2">
                              <Link to={`/sites/${s.site_id}`} className="text-zinc-100 hover:text-zinc-100 transition">
                                {s.site_name}
                              </Link>
                            </td>
                            <td className="px-4 py-2 text-right tabular-nums">{s.orders}</td>
                            <td className="px-4 py-2 text-right tabular-nums">{fmt(s.revenue_ht)}</td>
                            <td className="px-4 py-2 text-right tabular-nums">{fmt(s.cost_ht)}</td>
                            <td className="px-4 py-2 text-right tabular-nums font-medium text-emerald-400">{fmt(s.gross_margin_ht)}</td>
                            <td className="px-4 py-2 text-right tabular-nums font-semibold text-zinc-100">{fmt(s.concepteur_share)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

function HistoryTable({ items }) {
  if (items.length === 0) {
    return <EmptyState title="Aucun virement exécuté pour l'instant" subtitle="Les virements marqués comme payés apparaîtront ici." />;
  }
  return (
    <div className="bg-zinc-950 rounded-md border border-zinc-800 overflow-hidden" data-testid="history-table">
      <table className="w-full">
        <thead className="bg-black text-[11px] uppercase tracking-widest text-zinc-500">
          <tr>
            <th className="text-left px-5 py-3">Concepteur</th>
            <th className="text-left px-5 py-3">IBAN</th>
            <th className="text-right px-5 py-3">Montant</th>
            <th className="text-right px-5 py-3">Payé le</th>
            <th className="text-right px-5 py-3">Par</th>
          </tr>
        </thead>
        <tbody>
          {items.map((p) => (
            <tr key={p.id} className="border-t border-zinc-800 hover:bg-black transition">
              <td className="px-5 py-4">
                <div className="font-medium text-zinc-100">{p.concepteur_name || p.holder_name}</div>
                <div className="text-xs text-zinc-500">{p.concepteur_email || ""}</div>
              </td>
              <td className="px-5 py-4 font-mono text-sm text-zinc-500">{maskIban(p.iban)}</td>
              <td className="px-5 py-4 text-right font-heading tabular-nums text-emerald-400">{fmt(p.amount)}</td>
              <td className="px-5 py-4 text-right text-sm text-zinc-500 tabular-nums">{fmtDate(p.paid_at)}</td>
              <td className="px-5 py-4 text-right text-xs text-zinc-500">{p.paid_by || "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function MiniStat({ label, value, color }) {
  return (
    <div className="text-right px-3 border-r border-zinc-800 last:border-0">
      <div className="text-[10px] uppercase tracking-widest text-zinc-500">{label}</div>
      <div className="font-heading text-sm font-semibold tabular-nums" style={{ color: color || "#1C1917" }}>
        {value}
      </div>
    </div>
  );
}

function maskIban(iban) {
  if (!iban) return "—";
  const s = iban.replace(/\s+/g, "");
  if (s.length < 8) return s;
  return `${s.slice(0, 4)} •••• •••• •••• ${s.slice(-4)}`;
}

function formatIban(iban) {
  if (!iban) return "";
  return iban.replace(/\s+/g, "").replace(/(.{4})/g, "$1 ").trim();
}
