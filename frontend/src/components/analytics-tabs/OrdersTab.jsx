import React, { useEffect, useState, useCallback, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { ShoppingCart, CircleNotch, Package, ArrowRight } from "@phosphor-icons/react";
import { api, apiCall } from "../../lib/api";

const STATUS_COLORS = {
  paid:     { bg: "bg-emerald-50",  text: "text-emerald-700",  label: "Payée" },
  pending:  { bg: "bg-amber-50",    text: "text-amber-700",    label: "En attente" },
  failed:   { bg: "bg-red-50",      text: "text-red-700",      label: "Échec" },
  refunded: { bg: "bg-neutral-100", text: "text-neutral-700",  label: "Remboursée" },
  shipped:  { bg: "bg-blue-50",     text: "text-blue-700",     label: "Expédiée" },
  delivered:{ bg: "bg-emerald-50",  text: "text-emerald-700",  label: "Livrée" },
  default:  { bg: "bg-neutral-100", text: "text-neutral-600",  label: null },
};

function StatusBadge({ status }) {
  const s = STATUS_COLORS[status] || { ...STATUS_COLORS.default, label: status || "—" };
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium ${s.bg} ${s.text}`}>
      {s.label || status}
    </span>
  );
}

export default function OrdersTab({ siteId }) {
  const navigate = useNavigate();
  const [orders, setOrders] = useState(null);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("all");

  const load = useCallback(async () => {
    setLoading(true);
    const { data, error } = await apiCall(() => api.get(`/sites/${siteId}/orders`));
    if (!error) {
      const arr = Array.isArray(data) ? data : (data?.orders || []);
      setOrders(arr);
    } else {
      setOrders([]);
    }
    setLoading(false);
  }, [siteId]);

  useEffect(() => { load(); }, [load]);

  const filtered = useMemo(() => {
    if (!orders) return [];
    if (statusFilter === "all") return orders;
    return orders.filter((o) => (o.payment_status || o.status) === statusFilter);
  }, [orders, statusFilter]);

  const FILTERS = [
    { key: "all",     label: "Toutes" },
    { key: "paid",    label: "Payées" },
    { key: "pending", label: "En attente" },
    { key: "failed",  label: "Échec" },
  ];

  return (
    <div data-testid="orders-tab">
      <div className="flex items-center justify-between gap-3 mb-5 flex-wrap">
        <div className="flex items-center gap-1 bg-neutral-100 p-1 rounded-lg">
          {FILTERS.map((f) => (
            <button
              key={f.key}
              onClick={() => setStatusFilter(f.key)}
              className={`h-8 px-3 rounded-md text-xs font-medium transition ${
                statusFilter === f.key ? "bg-white text-neutral-900 shadow-sm" : "text-neutral-500 hover:text-neutral-900"
              }`}
              data-testid={`orders-filter-${f.key}`}
            >
              {f.label}
            </button>
          ))}
        </div>
        <div className="text-xs text-neutral-500">
          {filtered.length} commande{filtered.length !== 1 ? "s" : ""} affichée{filtered.length !== 1 ? "s" : ""}
        </div>
      </div>

      <div className="bg-white rounded-xl border border-neutral-200 overflow-hidden">
        {loading ? (
          <div className="py-20 text-neutral-500 text-sm flex items-center justify-center gap-2">
            <CircleNotch size={16} className="animate-spin" /> Chargement des commandes…
          </div>
        ) : filtered.length === 0 ? (
          <div className="py-16 px-6 text-center" data-testid="orders-empty">
            <ShoppingCart size={36} weight="duotone" className="mx-auto text-neutral-400 mb-3" />
            <h3 className="text-base font-semibold text-neutral-900 mb-1">Aucune commande pour l'instant</h3>
            <p className="text-sm text-neutral-500 max-w-md mx-auto mb-4">
              Les commandes apparaîtront ici dès que tes premiers clients passeront sur le storefront public.
            </p>
            <button
              onClick={() => window.open(`/shop/${siteId}`, "_blank")}
              className="inline-flex items-center gap-2 h-9 px-4 rounded-lg border border-neutral-200 hover:bg-neutral-50 text-sm font-medium text-neutral-700 transition"
              data-testid="orders-view-storefront"
            >
              Voir le storefront <ArrowRight size={14} />
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-[11px] uppercase tracking-widest text-neutral-500 bg-neutral-50 text-left">
                  <th className="py-3 px-4 font-medium">N°</th>
                  <th className="py-3 px-4 font-medium">Date</th>
                  <th className="py-3 px-4 font-medium">Client</th>
                  <th className="py-3 px-4 font-medium text-right">Total</th>
                  <th className="py-3 px-4 font-medium">Paiement</th>
                  <th className="py-3 px-4 font-medium">Fulfillment</th>
                  <th className="py-3 px-4 font-medium">Pays</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((o) => {
                  const dt = o.created_at ? new Date(o.created_at) : null;
                  const customer = o.customer_email || o.customer?.email || o.customer?.first_name || "—";
                  return (
                    <tr
                      key={o.id || o.order_number}
                      onClick={() => navigate(`/sites/${siteId}/orders/${o.id || o.order_number}`)}
                      className="border-t border-neutral-100 hover:bg-neutral-50/60 cursor-pointer transition"
                      data-testid="order-row"
                    >
                      <td className="py-3 px-4 font-mono text-xs text-neutral-700">{o.order_number || String(o.id || "").slice(0, 8)}</td>
                      <td className="py-3 px-4 text-neutral-600">{dt ? dt.toLocaleDateString("fr-FR") : "—"}</td>
                      <td className="py-3 px-4 text-neutral-700">{customer}</td>
                      <td className="py-3 px-4 text-right tabular-nums font-medium text-neutral-900">
                        {o.total_eur != null ? `${Number(o.total_eur).toFixed(2)} €` : (o.total ? `${Number(o.total).toFixed(2)} €` : "—")}
                      </td>
                      <td className="py-3 px-4"><StatusBadge status={o.payment_status || o.status} /></td>
                      <td className="py-3 px-4"><StatusBadge status={o.fulfillment_status || "pending"} /></td>
                      <td className="py-3 px-4 text-neutral-600">{o.shipping_country || o.country || "—"}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
