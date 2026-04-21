import React, { useEffect, useState, useCallback } from "react";
import { api, apiCall } from "../lib/api";
import Layout from "../components/Layout";
import {
  Package,
  MagnifyingGlass,
  DownloadSimple,
  ArrowClockwise,
  X,
  CheckCircle,
  Truck,
  XCircle,
  ArrowCounterClockwise,
  CurrencyEur,
  Copy,
  ArrowSquareOut,
} from "@phosphor-icons/react";

const STATUS_META = {
  pending_payment: { label: "Paiement en attente", bg: "#FEF3C7", text: "#854D0E", Icon: CurrencyEur },
  paid:            { label: "Payée",               bg: "#DBEAFE", text: "#1E40AF", Icon: CheckCircle },
  shipped:         { label: "Expédiée",            bg: "#E0E7FF", text: "#3730A3", Icon: Truck },
  delivered:       { label: "Livrée",              bg: "#DCF5E7", text: "#166534", Icon: CheckCircle },
  cancelled:       { label: "Annulée",             bg: "#FFE4E6", text: "#9F1239", Icon: XCircle },
  refunded:        { label: "Remboursée",          bg: "#F5F5F4", text: "#57534E", Icon: ArrowCounterClockwise },
};

const STATUS_ORDER = ["pending_payment", "paid", "shipped", "delivered", "cancelled", "refunded"];

const formatDate = (iso) => {
  if (!iso) return "";
  const d = new Date(iso);
  return d.toLocaleDateString("fr-FR", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });
};

export default function Orders() {
  const [stats, setStats] = useState(null);
  const [orders, setOrders] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({ status: "", q: "" });
  const [selectedOrder, setSelectedOrder] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    const params = new URLSearchParams();
    if (filters.status) params.set("status", filters.status);
    if (filters.q) params.set("q", filters.q);
    const [statsRes, listRes] = await Promise.all([
      apiCall(() => api.get("/admin/orders/stats")),
      apiCall(() => api.get(`/admin/orders?${params.toString()}`)),
    ]);
    if (statsRes.data) setStats(statsRes.data);
    if (listRes.data) {
      setOrders(listRes.data.items || []);
      setTotal(listRes.data.total || 0);
    }
    setLoading(false);
  }, [filters]);

  useEffect(() => { load(); }, [load]);

  const handleExport = () => {
    const params = new URLSearchParams();
    if (filters.status) params.set("status", filters.status);
    const url = `${process.env.REACT_APP_BACKEND_URL}/api/admin/orders/export.csv?${params.toString()}`;
    window.open(url, "_blank");
  };

  return (
    <Layout>
      <div className="p-8 md:p-12 max-w-[1400px]">
        <div className="mb-8 animate-fade-up flex items-start justify-between gap-4">
          <div>
            <div className="text-[11px] uppercase tracking-widest text-[#78716C] mb-2">Ops Center</div>
            <h1 className="font-heading text-4xl font-semibold text-[#1C1917]">Commandes</h1>
            <p className="text-[#57534E] mt-2 max-w-xl">
              Toutes les commandes, tous les sites. Change le statut, copie l'URL fournisseur pour
              passer la commande chez CJ/BigBuy/AliExpress.
            </p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={load}
              data-testid="refresh-orders"
              className="h-11 px-4 rounded-xl bg-white border border-[#E7E5E4] hover:border-[#B84B31] text-[#1C1917] text-sm font-medium flex items-center gap-2 transition"
            >
              <ArrowClockwise size={16} /> Actualiser
            </button>
            <button
              onClick={handleExport}
              data-testid="export-csv"
              className="h-11 px-4 rounded-xl bg-[#1C1917] hover:bg-[#44403C] text-neutral-900 text-sm font-medium flex items-center gap-2 transition"
            >
              <DownloadSimple size={16} weight="bold" /> Export CSV
            </button>
          </div>
        </div>

        {/* Stats grid */}
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3 mb-6" data-testid="orders-stats">
            <StatCard
              label="Total"
              count={stats.total_count}
              revenue={stats.total_revenue}
              active={filters.status === ""}
              onClick={() => setFilters({ ...filters, status: "" })}
            />
            {STATUS_ORDER.map((s) => (
              <StatCard
                key={s}
                label={STATUS_META[s].label}
                count={stats.by_status[s]?.count || 0}
                revenue={stats.by_status[s]?.revenue || 0}
                accent={STATUS_META[s].text}
                bg={STATUS_META[s].bg}
                active={filters.status === s}
                onClick={() => setFilters({ ...filters, status: s })}
                testId={`stat-${s}`}
              />
            ))}
          </div>
        )}

        {/* Search */}
        <div className="mb-4 flex items-center gap-3">
          <div className="relative flex-1 max-w-md">
            <MagnifyingGlass size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[#78716C]" />
            <input
              value={filters.q}
              onChange={(e) => setFilters({ ...filters, q: e.target.value })}
              placeholder="Rechercher par n° de commande, email ou nom..."
              data-testid="orders-search"
              className="w-full h-11 pl-10 pr-4 rounded-xl border border-[#E7E5E4] bg-white focus:ring-2 focus:ring-[#B84B31]/30 focus:border-[#B84B31] outline-none text-sm"
            />
          </div>
          {filters.q && (
            <button onClick={() => setFilters({ ...filters, q: "" })} className="text-sm text-[#78716C] hover:text-[#1C1917]">
              Effacer
            </button>
          )}
        </div>

        {/* Table */}
        <div className="bg-white rounded-2xl border border-[#E7E5E4] overflow-hidden">
          {loading ? (
            <div className="p-12 text-center text-[#78716C]">…</div>
          ) : orders.length === 0 ? (
            <div className="p-16 text-center">
              <Package size={48} weight="thin" className="mx-auto text-[#D6D3D1] mb-3" />
              <div className="text-[#78716C]">Aucune commande{filters.status ? ` avec le statut "${STATUS_META[filters.status]?.label}"` : ""}.</div>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm" data-testid="orders-table">
                <thead className="bg-[#FDFBF7] text-[11px] uppercase tracking-widest text-[#78716C]">
                  <tr>
                    <th className="text-left px-5 py-3 font-medium">N° / Date</th>
                    <th className="text-left px-5 py-3 font-medium">Client</th>
                    <th className="text-left px-5 py-3 font-medium">Site</th>
                    <th className="text-right px-5 py-3 font-medium">Articles</th>
                    <th className="text-right px-5 py-3 font-medium">Total</th>
                    <th className="text-left px-5 py-3 font-medium">Pays</th>
                    <th className="text-left px-5 py-3 font-medium">Statut</th>
                  </tr>
                </thead>
                <tbody>
                  {orders.map((o) => {
                    const m = STATUS_META[o.status] || STATUS_META.pending_payment;
                    return (
                      <tr
                        key={o.id}
                        onClick={() => setSelectedOrder(o)}
                        data-testid={`order-row-${o.order_number}`}
                        className="border-t border-[#F5F2EB] hover:bg-[#FDFBF7] cursor-pointer transition"
                      >
                        <td className="px-5 py-3.5">
                          <div className="font-mono font-medium text-[#1C1917]">{o.order_number}</div>
                          <div className="text-xs text-[#78716C]">{formatDate(o.created_at)}</div>
                        </td>
                        <td className="px-5 py-3.5">
                          <div className="font-medium text-[#1C1917]">{o.customer?.name}</div>
                          <div className="text-xs text-[#78716C]">{o.customer?.email}</div>
                        </td>
                        <td className="px-5 py-3.5 text-[#57534E]">{o.site_name}</td>
                        <td className="px-5 py-3.5 text-right tabular-nums">
                          {o.items?.reduce((a, b) => a + b.quantity, 0)}
                        </td>
                        <td className="px-5 py-3.5 text-right tabular-nums font-medium text-[#1C1917]">
                          {o.total?.toFixed(2)}€
                        </td>
                        <td className="px-5 py-3.5 text-[#57534E]">{o.shipping_address?.country_code}</td>
                        <td className="px-5 py-3.5">
                          <span
                            className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-medium whitespace-nowrap"
                            style={{ backgroundColor: m.bg, color: m.text }}
                          >
                            <m.Icon size={11} weight="bold" /> {m.label}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {total > orders.length && (
          <div className="text-xs text-[#78716C] mt-3 text-center">
            {orders.length} / {total} commandes affichées
          </div>
        )}
      </div>

      {selectedOrder && (
        <OrderDetail
          order={selectedOrder}
          onClose={() => setSelectedOrder(null)}
          onUpdated={(o) => {
            setSelectedOrder(o);
            load();
          }}
        />
      )}
    </Layout>
  );
}

function StatCard({ label, count, revenue, active, accent, bg, onClick, testId }) {
  return (
    <button
      onClick={onClick}
      data-testid={testId || "stat-total"}
      className={`text-left p-3.5 rounded-xl border transition-all duration-200 ${
        active
          ? "border-[#B84B31] shadow-sm bg-white"
          : "border-[#E7E5E4] bg-white hover:border-[#B84B31]/40"
      }`}
    >
      <div className="flex items-center gap-1.5">
        {bg && <div className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: accent }} />}
        <div className="text-[10px] uppercase tracking-widest text-[#78716C] truncate">{label}</div>
      </div>
      <div className="font-heading text-xl font-semibold text-[#1C1917] mt-1 tabular-nums">
        {count}
      </div>
      <div className="text-[11px] text-[#78716C] tabular-nums">{(revenue || 0).toFixed(0)}€</div>
    </button>
  );
}

/* =========================================================
 * ORDER DETAIL SLIDE-IN
 * ========================================================= */
function OrderDetail({ order, onClose, onUpdated }) {
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [note, setNote] = useState("");
  const [copied, setCopied] = useState(null);

  const TRANSITIONS = {
    pending_payment: ["paid", "cancelled"],
    paid: ["shipped", "refunded", "cancelled"],
    shipped: ["delivered", "refunded"],
    delivered: ["refunded"],
    cancelled: [],
    refunded: [],
  };

  const allowed = TRANSITIONS[order.status] || [];

  const changeStatus = async (newStatus) => {
    setSaving(true);
    setError("");
    const { data, error: err } = await apiCall(() =>
      api.patch(`/admin/orders/${order.id}`, { status: newStatus, note })
    );
    setSaving(false);
    if (err) setError(err);
    else {
      setNote("");
      onUpdated(data);
    }
  };

  const copyToClipboard = (text, key) => {
    navigator.clipboard.writeText(text);
    setCopied(key);
    setTimeout(() => setCopied(null), 1500);
  };

  const m = STATUS_META[order.status] || STATUS_META.pending_payment;

  return (
    <div className="fixed inset-0 z-50 flex" data-testid="order-detail-panel">
      <div className="flex-1 bg-neutral-900/40" onClick={onClose} />
      <div className="w-full max-w-xl bg-[#FDFBF7] h-full overflow-y-auto shadow-2xl animate-slide-in-right">
        <div className="sticky top-0 bg-white border-b border-[#E7E5E4] px-6 py-4 flex items-center justify-between z-10">
          <div>
            <div className="text-[11px] uppercase tracking-widest text-[#78716C]">{order.site_name}</div>
            <div className="font-heading text-lg font-semibold text-[#1C1917] font-mono">
              {order.order_number}
            </div>
          </div>
          <button onClick={onClose} className="p-2 rounded-lg hover:bg-[#F5F2EB]" data-testid="close-detail">
            <X size={20} />
          </button>
        </div>

        <div className="p-6 space-y-5">
          <div
            className="flex items-center gap-2 px-3 py-2 rounded-lg w-fit"
            style={{ backgroundColor: m.bg, color: m.text }}
            data-testid="order-status-badge"
          >
            <m.Icon size={14} weight="bold" />
            <span className="text-sm font-medium">{m.label}</span>
          </div>

          {/* Customer */}
          <Section title="Client">
            <div className="flex items-center justify-between">
              <div>
                <div className="font-medium text-[#1C1917]">{order.customer?.name}</div>
                <div className="text-sm text-[#57534E]">{order.customer?.email}</div>
                {order.customer?.phone && (
                  <div className="text-sm text-[#57534E]">{order.customer.phone}</div>
                )}
              </div>
              <button
                onClick={() => copyToClipboard(order.customer?.email, "email")}
                className="text-xs text-[#B84B31] hover:underline flex items-center gap-1"
              >
                <Copy size={12} /> {copied === "email" ? "Copié" : "Copier email"}
              </button>
            </div>
          </Section>

          {/* Shipping */}
          <Section title="Livraison">
            <div className="text-sm text-[#1C1917]">
              {order.shipping_address?.line1}
              {order.shipping_address?.line2 && <div>{order.shipping_address.line2}</div>}
              <div>
                {order.shipping_address?.postal_code} {order.shipping_address?.city}
              </div>
              <div className="text-[#57534E]">{order.shipping_address?.country}</div>
            </div>
            <button
              onClick={() =>
                copyToClipboard(
                  [
                    order.customer?.name,
                    order.shipping_address?.line1,
                    order.shipping_address?.line2,
                    `${order.shipping_address?.postal_code} ${order.shipping_address?.city}`,
                    order.shipping_address?.country,
                  ].filter(Boolean).join("\n"),
                  "addr"
                )
              }
              className="mt-3 text-xs text-[#B84B31] hover:underline flex items-center gap-1"
              data-testid="copy-address"
            >
              <Copy size={12} /> {copied === "addr" ? "Copié" : "Copier l'adresse complète"}
            </button>
          </Section>

          {/* Items + fournisseur */}
          <Section title="Articles + fournisseurs">
            <div className="space-y-3">
              {order.items?.map((it, idx) => (
                <div key={idx} className="flex items-center gap-3 p-3 rounded-lg bg-[#FDFBF7]">
                  {it.image ? (
                    <img src={it.image} alt={it.name} className="w-12 h-12 rounded object-cover" />
                  ) : (
                    <div className="w-12 h-12 rounded bg-[#F5F2EB]" />
                  )}
                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-[#1C1917] truncate">{it.name}</div>
                    <div className="text-xs text-[#78716C]">
                      {it.quantity} × {it.price.toFixed(2)}€
                    </div>
                  </div>
                  {it.supplier_url ? (
                    <a
                      href={it.supplier_url}
                      target="_blank"
                      rel="noreferrer"
                      data-testid={`supplier-link-${idx}`}
                      className="flex items-center gap-1 text-xs text-[#B84B31] hover:underline whitespace-nowrap"
                    >
                      Fournisseur <ArrowSquareOut size={12} />
                    </a>
                  ) : (
                    <span className="text-xs text-[#A8A29E]">(pas d'URL)</span>
                  )}
                </div>
              ))}
            </div>
          </Section>

          {/* Totals */}
          <Section title="Total">
            <Row label="Sous-total" value={`${order.subtotal?.toFixed(2)}€`} />
            <Row label="Livraison" value={order.shipping_fee === 0 ? "Offerte" : `${order.shipping_fee?.toFixed(2)}€`} />
            <div className="h-px bg-[#E7E5E4] my-2" />
            <Row label={<b>Total</b>} value={<b>{order.total?.toFixed(2)}€</b>} />
          </Section>

          {/* Status history */}
          {order.status_history?.length > 0 && (
            <Section title="Historique">
              <div className="space-y-2">
                {order.status_history.map((h, idx) => (
                  <div key={idx} className="text-sm text-[#57534E] border-l-2 border-[#E7E5E4] pl-3">
                    <div>
                      <span className="text-[#78716C]">{STATUS_META[h.from]?.label}</span> →{" "}
                      <span className="font-medium text-[#1C1917]">{STATUS_META[h.to]?.label}</span>
                    </div>
                    <div className="text-xs text-[#78716C]">{formatDate(h.at)}</div>
                    {h.note && <div className="text-xs italic mt-0.5">« {h.note} »</div>}
                  </div>
                ))}
              </div>
            </Section>
          )}

          {/* Status actions */}
          {allowed.length > 0 ? (
            <Section title="Changer le statut">
              <textarea
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder="Note interne (optionnel)..."
                rows={2}
                data-testid="status-note"
                className="w-full px-3 py-2 rounded-lg border border-[#E7E5E4] bg-white focus:ring-2 focus:ring-[#B84B31]/30 focus:border-[#B84B31] outline-none resize-none text-sm"
              />
              <div className="flex flex-wrap gap-2 mt-3">
                {allowed.map((s) => {
                  const meta = STATUS_META[s];
                  return (
                    <button
                      key={s}
                      onClick={() => changeStatus(s)}
                      disabled={saving}
                      data-testid={`change-to-${s}`}
                      className="h-10 px-4 rounded-xl text-sm font-medium transition-all duration-200 active:scale-[0.98] disabled:opacity-60"
                      style={{ backgroundColor: meta.bg, color: meta.text }}
                    >
                      → {meta.label}
                    </button>
                  );
                })}
              </div>
              {error && <div className="mt-2 text-sm text-[#BE123C]">{error}</div>}
            </Section>
          ) : (
            <div className="text-center text-sm text-[#78716C] italic">
              Statut terminal — plus de transitions possibles.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function Section({ title, children }) {
  return (
    <div className="bg-white rounded-xl border border-[#E7E5E4] p-4">
      <div className="text-[11px] uppercase tracking-widest text-[#78716C] mb-2">{title}</div>
      {children}
    </div>
  );
}

function Row({ label, value }) {
  return (
    <div className="flex items-center justify-between text-sm py-0.5">
      <span className="text-[#57534E]">{label}</span>
      <span className="text-[#1C1917] tabular-nums">{value}</span>
    </div>
  );
}
