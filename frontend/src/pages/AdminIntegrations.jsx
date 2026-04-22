import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, CheckCircle, Link as LinkIcon, ArrowSquareOut, Storefront } from "@phosphor-icons/react";
import { api, apiCall } from "../lib/api";
import { useAuth } from "../lib/auth";

/**
 * Admin-only page — platform integrations.
 * AliExpress is connected ONCE here and every Altiaro store inherits automatically.
 */
export default function AdminIntegrations() {
  const { user } = useAuth();
  const [aliStatus, setAliStatus] = useState(null);
  const [loading, setLoading] = useState(false);

  const loadAli = async () => {
    const { data } = await apiCall(() => api.get("/admin/aliexpress/status"));
    if (data) setAliStatus(data);
  };

  useEffect(() => {
    loadAli();
    const onFocus = () => loadAli();
    window.addEventListener("focus", onFocus);
    return () => window.removeEventListener("focus", onFocus);
  }, []);

  const connectAli = async () => {
    setLoading(true);
    const { data, error } = await apiCall(() => api.get("/admin/aliexpress/authorize-url"));
    setLoading(false);
    if (error || !data?.authorize_url) {
      window.alert(error || "Impossible de démarrer la connexion.");
      return;
    }
    window.open(data.authorize_url, "_blank", "noopener");
  };

  const disconnectAli = async () => {
    if (!window.confirm("Déconnecter AliExpress au niveau plateforme ? Tous les imports + commandes auto s'arrêteront.")) return;
    await apiCall(() => api.post("/admin/aliexpress/disconnect"));
    loadAli();
  };

  if (user && user.role !== "admin") {
    return (
      <div className="min-h-screen bg-[#FAF7F2] flex items-center justify-center">
        <div className="text-neutral-500">Accès réservé à l'administrateur.</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#FAF7F2]">
      <div className="max-w-4xl mx-auto px-6 md:px-10 py-8">
        <Link
          to="/"
          className="inline-flex items-center gap-2 text-sm text-neutral-600 hover:text-neutral-900 mb-6"
          data-testid="admin-int-back"
        >
          <ArrowLeft size={14} /> Retour au dashboard
        </Link>

        <div className="mb-8">
          <div className="text-[11px] uppercase tracking-[0.2em] text-neutral-500 mb-2">Admin · Intégrations plateforme</div>
          <h1 className="text-3xl md:text-4xl font-semibold text-neutral-900" style={{ fontFamily: "'Fraunces', serif" }}>
            Intégrations Altiaro
          </h1>
          <p className="text-sm text-neutral-500 mt-2 max-w-2xl">
            Ces intégrations sont partagées entre tous les sites de la plateforme. Les Concepteurs n'ont rien à configurer — ils en bénéficient automatiquement.
          </p>
        </div>

        {/* AliExpress card */}
        <div className="bg-white border border-neutral-200 rounded-2xl p-6 mb-6" data-testid="admin-ali-card">
          <div className="flex items-start justify-between gap-4 flex-wrap">
            <div className="flex items-start gap-4 min-w-0">
              <div className="w-12 h-12 rounded-xl bg-orange-50 flex items-center justify-center flex-shrink-0">
                <Storefront size={22} weight="duotone" className="text-orange-600" />
              </div>
              <div className="min-w-0">
                <div className="text-lg font-semibold text-neutral-900">AliExpress Dropshipping</div>
                <div className="text-sm text-neutral-500 mt-0.5 max-w-lg">
                  Connecte le compte Altiaro maître. Toutes les commandes des boutiques Concepteurs seront placées sur ce compte.
                </div>
              </div>
            </div>
            {!aliStatus ? null : aliStatus.connected ? (
              <span className="inline-flex items-center gap-1.5 h-8 px-3 rounded-full bg-emerald-50 text-emerald-700 text-xs font-medium border border-emerald-200" data-testid="admin-ali-badge-connected">
                <CheckCircle size={14} weight="fill" /> Connecté
              </span>
            ) : (
              <span className="inline-flex items-center gap-1.5 h-8 px-3 rounded-full bg-neutral-100 text-neutral-700 text-xs font-medium" data-testid="admin-ali-badge-disconnected">
                Non connecté
              </span>
            )}
          </div>

          {aliStatus && aliStatus.connected && (
            <div className="mt-5 pt-5 border-t border-neutral-100 grid grid-cols-2 md:grid-cols-3 gap-4 text-sm" data-testid="admin-ali-details">
              <Detail label="Compte AliExpress" value={aliStatus.user_nick || "—"} />
              <Detail label="Connecté le" value={aliStatus.connected_at ? new Date(aliStatus.connected_at).toLocaleDateString("fr-FR") : "—"} />
              <Detail label="Expire le" value={aliStatus.expires_at ? new Date(aliStatus.expires_at).toLocaleDateString("fr-FR") : "—"} />
            </div>
          )}

          <div className="mt-5 pt-5 border-t border-neutral-100 flex gap-2">
            {aliStatus && aliStatus.connected ? (
              <button
                onClick={disconnectAli}
                data-testid="admin-ali-disconnect"
                className="h-10 px-4 rounded-xl bg-white border border-neutral-200 hover:border-rose-300 hover:text-rose-700 text-sm font-medium text-neutral-700"
              >
                Déconnecter
              </button>
            ) : (
              <button
                onClick={connectAli}
                disabled={loading || !aliStatus?.configured_server_side}
                data-testid="admin-ali-connect"
                className="h-10 px-4 rounded-xl bg-neutral-900 hover:bg-neutral-800 text-white text-sm font-medium flex items-center gap-2 disabled:opacity-60"
              >
                <LinkIcon size={14} weight="bold" /> Connecter AliExpress <ArrowSquareOut size={12} weight="bold" />
              </button>
            )}
            {aliStatus && !aliStatus.configured_server_side && (
              <div className="text-xs text-amber-700 flex items-center">ALIEXPRESS_APP_KEY/SECRET manquants dans .env</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function Detail({ label, value }) {
  return (
    <div>
      <div className="text-[11px] uppercase tracking-widest text-neutral-500 mb-1">{label}</div>
      <div className="text-sm font-medium text-neutral-900">{value}</div>
    </div>
  );
}
