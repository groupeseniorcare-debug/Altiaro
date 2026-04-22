import React, { useEffect, useState, useMemo } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import axios from "axios";
import { getToken, getCustomer, clearSession, authHeaders } from "../lib/customerAuth";
import StorefrontLayout, { useSiteData } from "../components/StorefrontLayout";
import { User, Receipt, SignOut, Package, CaretRight, FunnelSimple } from "@phosphor-icons/react";

const BACKEND = process.env.REACT_APP_BACKEND_URL;

const STATUS_FILTERS = [
  { key: "all", label: "Toutes" },
  { key: "active", label: "En cours" },
  { key: "delivered", label: "Livrées" },
  { key: "cancelled", label: "Archivées" },
];

export default function StorefrontAccount() {
  const { siteId } = useParams();
  const nav = useNavigate();
  const site = useSiteData(siteId);
  const [customer, setCustomer] = useState(getCustomer(siteId));
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all");

  useEffect(() => {
    if (!getToken(siteId)) {
      nav(`/shop/${siteId}/account/login`);
      return;
    }
    Promise.all([
      axios.get(`${BACKEND}/api/public/sites/${siteId}/customers/me`, { headers: authHeaders(siteId) }),
      axios.get(`${BACKEND}/api/public/sites/${siteId}/customers/orders`, { headers: authHeaders(siteId) }),
    ])
      .then(([a, b]) => {
        setCustomer(a.data);
        setOrders(b.data || []);
      })
      .catch(() => {
        clearSession(siteId);
        nav(`/shop/${siteId}/account/login`);
      })
      .finally(() => setLoading(false));
  }, [siteId, nav]);

  const logout = () => {
    clearSession(siteId);
    nav(`/shop/${siteId}`);
  };

  const filteredOrders = useMemo(() => {
    if (filter === "all") return orders;
    if (filter === "active") return orders.filter((o) => ["pending_payment", "paid", "shipped"].includes(o.status));
    if (filter === "delivered") return orders.filter((o) => o.status === "delivered");
    if (filter === "cancelled") return orders.filter((o) => ["cancelled", "refunded"].includes(o.status));
    return orders;
  }, [orders, filter]);

  if (!site || loading) return null;
  const primary = site.design?.brand?.primary_color || "#1C1917";

  const statusLabel = {
    pending_payment: { label: "En attente de paiement", color: "bg-amber-100 text-amber-800" },
    paid: { label: "Payée", color: "bg-blue-100 text-blue-800" },
    shipped: { label: "Expédiée", color: "bg-indigo-100 text-indigo-800" },
    delivered: { label: "Livrée", color: "bg-emerald-100 text-emerald-800" },
    cancelled: { label: "Annulée", color: "bg-neutral-100 text-neutral-600" },
    refunded: { label: "Remboursée", color: "bg-neutral-100 text-neutral-600" },
  };

  return (
    <StorefrontLayout site={site}>
      <div className="max-w-4xl mx-auto py-16 px-6">
        <div className="flex items-center justify-between mb-10">
          <div>
            <div className="text-xs uppercase tracking-widest text-neutral-500 mb-1">Mon compte</div>
            <h1 className="text-3xl" style={{ fontFamily: site.design?.brand?.font_heading || "Fraunces, serif" }}>
              Bonjour {customer?.first_name || ""}
            </h1>
          </div>
          <button onClick={logout} data-testid="cust-logout"
            className="h-10 px-4 rounded-lg border border-neutral-300 text-sm flex items-center gap-2 hover:bg-neutral-50">
            <SignOut size={14} /> Se déconnecter
          </button>
        </div>

        <div className="bg-white border border-neutral-200 rounded-2xl p-6 mb-8">
          <div className="text-sm text-neutral-500 mb-3 flex items-center gap-2">
            <User size={14} /> Mes informations
          </div>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <div className="text-xs uppercase text-neutral-500 mb-1">Prénom Nom</div>
              <div className="font-medium">{customer?.first_name} {customer?.last_name}</div>
            </div>
            <div>
              <div className="text-xs uppercase text-neutral-500 mb-1">Email</div>
              <div className="font-medium">{customer?.email}</div>
            </div>
            {customer?.phone && (
              <div>
                <div className="text-xs uppercase text-neutral-500 mb-1">Téléphone</div>
                <div className="font-medium">{customer.phone}</div>
              </div>
            )}
          </div>
        </div>

        <div className="bg-white border border-neutral-200 rounded-2xl p-6" data-testid="cust-orders">
          <div className="flex items-center justify-between gap-4 mb-5 flex-wrap">
            <div className="text-sm text-neutral-500 flex items-center gap-2">
              <Receipt size={14} /> Mes commandes ({orders.length})
            </div>
            {orders.length > 0 && (
              <div className="flex items-center gap-1 text-xs" data-testid="order-filter">
                <FunnelSimple size={12} className="text-neutral-400 mr-1" />
                {STATUS_FILTERS.map((f) => (
                  <button
                    key={f.key}
                    onClick={() => setFilter(f.key)}
                    data-testid={`filter-${f.key}`}
                    className={`h-8 px-3 rounded-full text-[12px] font-medium transition ${
                      filter === f.key
                        ? "bg-neutral-900 text-white"
                        : "bg-neutral-50 text-neutral-600 hover:bg-neutral-100"
                    }`}
                  >
                    {f.label}
                  </button>
                ))}
              </div>
            )}
          </div>

          {orders.length === 0 ? (
            <div className="text-center py-10 text-neutral-500">
              <Package size={32} weight="duotone" className="mx-auto mb-2 opacity-50" />
              Aucune commande pour l'instant.
              <Link to={`/shop/${siteId}`} className="block mt-3 text-sm font-medium underline">Découvrir la boutique</Link>
            </div>
          ) : filteredOrders.length === 0 ? (
            <div className="text-center py-10 text-neutral-400 text-sm">
              Aucune commande dans ce filtre.
            </div>
          ) : (
            <div className="space-y-3">
              {filteredOrders.map((o) => {
                const s = statusLabel[o.status] || { label: o.status, color: "bg-neutral-100 text-neutral-700" };
                const orderKey = o.id || o.order_number;
                return (
                  <Link
                    key={orderKey}
                    to={`/shop/${siteId}/account/orders/${orderKey}`}
                    data-testid={`order-row-${o.order_number}`}
                    className="flex items-center justify-between gap-3 p-4 rounded-xl border border-neutral-200 hover:border-neutral-900 hover:shadow-sm transition group"
                  >
                    <div className="min-w-0">
                      <div className="font-mono text-sm font-semibold text-neutral-900">{o.order_number}</div>
                      <div className="text-xs text-neutral-500 mt-0.5">
                        {new Date(o.created_at).toLocaleDateString("fr-FR", { day: "2-digit", month: "long", year: "numeric" })}
                        {" · "}{(o.items || []).length} article{(o.items || []).length > 1 ? "s" : ""}
                      </div>
                    </div>
                    <div className="flex items-center gap-4">
                      <div className="text-right">
                        <div className="font-semibold tabular-nums text-neutral-900">{o.total?.toFixed(2)} €</div>
                        <span className={`inline-block mt-1 text-[10px] font-medium px-2 py-0.5 rounded-full ${s.color}`}>{s.label}</span>
                      </div>
                      <CaretRight size={16} className="text-neutral-300 group-hover:text-neutral-700 transition flex-shrink-0" />
                    </div>
                  </Link>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </StorefrontLayout>
  );
}
