import React, { useEffect, useState } from "react";
import { Link as LinkIcon, CheckCircle, ArrowSquareOut } from "@phosphor-icons/react";
import { api, apiCall } from "../lib/api";

/**
 * Compact "Connect AliExpress" card for the cockpit.
 * - Read-only status probe
 * - Opens OAuth in a new tab
 * - Auto-refreshes when the tab regains focus (after callback)
 */
export default function AliExpressConnect({ siteId }) {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(false);

  const load = async () => {
    const { data } = await apiCall(() => api.get(`/sites/${siteId}/aliexpress/status`));
    if (data) setStatus(data);
  };

  useEffect(() => {
    load();
    const onFocus = () => load();
    window.addEventListener("focus", onFocus);
    return () => window.removeEventListener("focus", onFocus);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [siteId]);

  const connect = async () => {
    setLoading(true);
    const { data, error } = await apiCall(() => api.get(`/aliexpress/authorize-url`, { params: { site_id: siteId } }));
    setLoading(false);
    if (error || !data?.authorize_url) {
      alert(error || "Impossible de démarrer la connexion AliExpress.");
      return;
    }
    window.open(data.authorize_url, "_blank", "noopener");
  };

  const disconnect = async () => {
    if (!window.confirm("Déconnecter ce site d'AliExpress ?")) return;
    await apiCall(() => api.post(`/sites/${siteId}/aliexpress/disconnect`));
    load();
  };

  if (!status) return null;

  if (!status.configured_server_side) {
    return (
      <div className="rounded-xl border border-amber-200 bg-amber-50 text-amber-900 px-4 py-3 text-xs" data-testid="ali-not-configured">
        AliExpress non configuré côté serveur (APP_KEY/SECRET manquants).
      </div>
    );
  }

  if (status.connected) {
    return (
      <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 flex items-center justify-between gap-3" data-testid="ali-connected">
        <div className="flex items-center gap-3 min-w-0">
          <CheckCircle size={20} weight="fill" className="text-emerald-600 flex-shrink-0" />
          <div className="min-w-0">
            <div className="text-sm font-medium text-emerald-900">AliExpress connecté</div>
            <div className="text-[11px] text-emerald-800 truncate">
              {status.user_nick ? `Compte : ${status.user_nick} · ` : ""}
              Connecté le {status.connected_at ? new Date(status.connected_at).toLocaleDateString("fr-FR") : "—"}
            </div>
          </div>
        </div>
        <button
          onClick={disconnect}
          data-testid="ali-disconnect"
          className="h-8 px-3 rounded-lg bg-white border border-emerald-200 text-xs font-medium text-neutral-700 hover:border-rose-300 hover:text-rose-700"
        >
          Déconnecter
        </button>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-neutral-200 bg-white px-4 py-3 flex items-center justify-between gap-3" data-testid="ali-disconnected">
      <div className="flex items-center gap-3 min-w-0">
        <div className="w-9 h-9 rounded-lg bg-orange-50 flex items-center justify-center flex-shrink-0">
          <LinkIcon size={18} weight="duotone" className="text-orange-600" />
        </div>
        <div className="min-w-0">
          <div className="text-sm font-medium text-neutral-900">AliExpress Dropshipping</div>
          <div className="text-[11px] text-neutral-500">Importez produits, commandez automatiquement, suivez les colis.</div>
        </div>
      </div>
      <button
        onClick={connect}
        disabled={loading}
        data-testid="ali-connect-btn"
        className="h-9 px-3 rounded-lg bg-neutral-900 hover:bg-neutral-800 text-white text-xs font-medium flex items-center gap-1.5 transition disabled:opacity-60 flex-shrink-0"
      >
        {loading ? "…" : "Connecter"} <ArrowSquareOut size={12} weight="bold" />
      </button>
    </div>
  );
}
