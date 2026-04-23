import React, { useEffect, useState, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import {
  ArrowLeft, ArrowClockwise, Truck, CheckCircle, Warning, Clock, Package,
  ArrowSquareOut, Copy,
} from "@phosphor-icons/react";
import { api, apiCall } from "../lib/api";

const STATE_META = {
  pending_supplier: { label: "En attente", color: "bg-amber-100 text-amber-800", Icon: Clock },
  placed: { label: "Commandé fournisseur", color: "bg-blue-100 text-blue-800", Icon: Package },
  shipped: { label: "Expédié", color: "bg-indigo-100 text-indigo-800", Icon: Truck },
  delivered: { label: "Livré", color: "bg-emerald-100 text-emerald-800", Icon: CheckCircle },
  error: { label: "Erreur", color: "bg-red-100 text-red-800", Icon: Warning },
};

export default function SiteFulfillment() {
  const { id: siteId } = useParams();
  const [site, setSite] = useState(null);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [retrying, setRetrying] = useState(null);
  const [syncing, setSyncing] = useState(false);

  const load = useCallback(async () => {
    const [sRes, fRes] = await Promise.all([
      apiCall(() => api.get(`/sites/${siteId}`)),
      apiCall(() => api.get(`/sites/${siteId}/fulfillment`)),
    ]);
    if (sRes.data) setSite(sRes.data);
    if (fRes.data) setData(fRes.data);
    setLoading(false);
  }, [siteId]);

  useEffect(() => { load(); }, [load]);

  const retryOrder = async (orderId) => {
    setRetrying(orderId);
    const { data: res, error } = await apiCall(() =>
      api.post(`/sites/${siteId}/orders/${orderId}/supplier-retry`)
    );
    setRetrying(null);
    if (error) { window.alert(error); return; }
    window.alert(`Retry OK :\n${JSON.stringify(res.retried, null, 2)}`);
    load();
  };

  const copy = (text) => { navigator.clipboard.writeText(text); };

  if (loading) return <div className="min-h-screen bg-[#FAF7F2] p-10 text-neutral-500">Chargement…</div>;

  const counters = data?.counters || {};
  const orders = data?.orders || [];

  return (
    <div className="min-h-screen bg-[#FAF7F2]">
      <div className="max-w-[1600px] mx-auto px-6 md:px-10 py-8">
        <Link to={`/sites/${siteId}`} className="inline-flex items-center gap-2 text-sm text-neutral-600 hover:text-neutral-900 mb-6">
          <ArrowLeft size={14} /> Retour au cockpit
        </Link>

        <div className="flex items-start justify-between gap-6 flex-wrap mb-8">
          <div>
            <div className="text-[11px] uppercase tracking-[0.2em] text-neutral-500 mb-2 flex items-center gap-2">
              <Truck size={12} weight="bold" /> Fulfillment · Suivi commandes fournisseur
            </div>
            <h1 className="text-3xl md:text-4xl font-semibold text-neutral-900" style={{ fontFamily: "'Fraunces', serif" }}>
              {site?.name}
            </h1>
            <p className="text-sm text-neutral-500 mt-2 max-w-2xl">
              Commandes clients payées, leurs commandes fournisseur CJ / AliExpress et le suivi tracking remontant automatiquement.
            </p>
          </div>
          <button
            onClick={load}
            disabled={syncing}
            data-testid="fulfill-refresh"
            className="h-10 px-4 rounded-lg bg-white border border-neutral-200 hover:border-neutral-900 text-sm font-medium flex items-center gap-2 transition"
          >
            <ArrowClockwise size={14} className={syncing ? "animate-spin" : ""} /> Rafraîchir
          </button>
        </div>

        {/* Counters */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-8">
          {["pending_supplier", "placed", "shipped", "delivered", "error"].map((k) => {
            const meta = STATE_META[k];
            const n = counters[k] || 0;
            return (
              <div key={k} className="bg-white border border-neutral-200 rounded-2xl p-4" data-testid={`count-${k}`}>
                <div className="flex items-center gap-2 mb-2">
                  <div className={`w-7 h-7 rounded-lg flex items-center justify-center ${meta.color}`}>
                    <meta.Icon size={14} weight="bold" />
                  </div>
                  <div className="text-[10px] uppercase tracking-wider text-neutral-500 font-semibold">{meta.label}</div>
                </div>
                <div className="text-2xl font-semibold text-neutral-900">{n}</div>
              </div>
            );
          })}
        </div>

        {orders.length === 0 ? (
          <div className="bg-white border border-dashed border-neutral-200 rounded-2xl p-10 text-center">
            <Truck size={28} weight="duotone" className="mx-auto text-neutral-400 mb-3" />
            <p className="text-sm text-neutral-500">
              Aucune commande payée pour l'instant. Dès qu'un client paye sur ton storefront, la commande fournisseur sera créée automatiquement et apparaîtra ici.
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {orders.map((o) => {
              const state = o.fulfillment_state;
              const meta = STATE_META[state];
              const maps = o.supplier_mappings || [];
              return (
                <div
                  key={o.id}
                  data-testid={`fulfill-order-${o.id}`}
                  className="bg-white border border-neutral-200 rounded-2xl p-5"
                >
                  <div className="flex items-start justify-between gap-4 flex-wrap">
                    <div className="flex-1 min-w-[240px]">
                      <div className="flex items-center gap-2 mb-1">
                        <div className="font-mono text-sm font-semibold text-neutral-900">{o.order_number}</div>
                        <span className={`text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded-full font-medium ${meta.color}`}>
                          {meta.label}
                        </span>
                      </div>
                      <div className="text-xs text-neutral-500">
                        {o.customer?.name || "—"} · {o.customer?.email || "—"}
                      </div>
                      <div className="text-xs text-neutral-500 mt-0.5">
                        {new Date(o.created_at).toLocaleString("fr-FR")} · <strong className="text-neutral-700">{o.total?.toFixed(2)} {o.currency}</strong>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {state === "error" || state === "pending_supplier" ? (
                        <button
                          onClick={() => retryOrder(o.id)}
                          disabled={retrying === o.id}
                          data-testid={`retry-${o.id}`}
                          className="h-9 px-3 rounded-lg bg-neutral-900 hover:bg-neutral-800 text-white text-xs font-medium flex items-center gap-1.5 disabled:opacity-50"
                        >
                          {retrying === o.id
                            ? <><ArrowClockwise size={12} className="animate-spin" /> Tentative…</>
                            : <><ArrowClockwise size={12} /> Réessayer</>
                          }
                        </button>
                      ) : null}
                    </div>
                  </div>

                  {/* Supplier mapping rows */}
                  {maps.length > 0 && (
                    <div className="mt-4 pt-4 border-t border-neutral-100 space-y-2">
                      {maps.map((m, i) => (
                        <div key={i} className="flex items-center gap-3 text-xs">
                          <span className="px-2 py-0.5 rounded-full bg-neutral-100 font-medium uppercase tracking-wider text-[10px]">
                            {m.provider}
                          </span>
                          <span className="font-mono text-neutral-700">
                            {m.supplier_order_id || "—"}
                            {m.supplier_order_id && (
                              <button onClick={() => copy(m.supplier_order_id)}
                                className="ml-1.5 text-neutral-400 hover:text-neutral-900"
                                title="Copier">
                                <Copy size={10} />
                              </button>
                            )}
                          </span>
                          <span className="text-neutral-500">·</span>
                          <span className="text-neutral-700">{m.status}</span>
                          {m.tracking_number && (
                            <>
                              <span className="text-neutral-500">·</span>
                              <span className="text-neutral-700">
                                <Truck size={11} className="inline mr-1" />
                                {m.carrier || "Colis"} <span className="font-mono">{m.tracking_number}</span>
                              </span>
                            </>
                          )}
                          {m.last_sync_at && (
                            <span className="text-neutral-400 ml-auto">
                              sync : {new Date(m.last_sync_at).toLocaleTimeString("fr-FR")}
                            </span>
                          )}
                        </div>
                      ))}
                    </div>
                  )}

                  {maps.length === 0 && state === "pending_supplier" && (
                    <div className="mt-4 pt-4 border-t border-neutral-100 text-xs text-amber-700 bg-amber-50 rounded-lg p-3 flex items-start gap-2">
                      <Warning size={14} weight="fill" className="flex-shrink-0 mt-0.5" />
                      <div>
                        Aucune commande fournisseur créée. Cela peut arriver si le produit
                        n'expédie pas vers le pays du client, ou si l'API a échoué au moment
                        du paiement. Clique <strong>Réessayer</strong> ou va vérifier la fiche produit.
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
