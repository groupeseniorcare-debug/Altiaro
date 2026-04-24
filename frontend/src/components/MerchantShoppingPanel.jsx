import React, { useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { api, apiCall } from "../lib/api";
import {
  ShoppingCart,
  ArrowClockwise,
  Warning,
  CheckCircle,
  XCircle,
  Link as LinkIcon,
  X as XIcon,
  Gear,
} from "@phosphor-icons/react";

/**
 * MerchantShoppingPanel — Admin-only.
 * Affiche le statut Google Merchant Center pour un site :
 *  - Statut global plateforme (connecté / non connecté)
 *  - Dernière sync (OK/KO/partial)
 *  - Bouton "Sync now" → POST /api/sites/{id}/merchant/sync
 *  - Bouton "Voir les erreurs" → modal détail des dernières erreurs
 *  - Si pas connecté : lien /admin/integrations
 *
 * Data-testids : merchant-panel, merchant-sync-btn, merchant-status, merchant-errors-btn
 */
export default function MerchantShoppingPanel({ siteId, isAdmin }) {
  const navigate = useNavigate();
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [lastSyncResult, setLastSyncResult] = useState(null);
  const [showErrorsModal, setShowErrorsModal] = useState(false);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    if (!siteId || !isAdmin) return;
    setLoading(true);
    setError(null);
    const { data, error: err } = await apiCall(() =>
      api.get(`/sites/${siteId}/merchant/status`)
    );
    if (err) {
      setError(err);
    } else {
      setStatus(data);
    }
    setLoading(false);
  }, [siteId, isAdmin]);

  useEffect(() => {
    load();
  }, [load]);

  const handleSync = async () => {
    if (syncing) return;
    setSyncing(true);
    setLastSyncResult(null);
    const { data, error: err } = await apiCall(() =>
      api.post(`/sites/${siteId}/merchant/sync`, {})
    );
    if (err) {
      setLastSyncResult({ ok: false, message: err });
    } else {
      setLastSyncResult(data);
    }
    setSyncing(false);
    // Re-fetch status pour afficher la nouvelle date de sync
    await load();
  };

  // Admin-only : ne rien afficher pour les concepteurs
  if (!isAdmin) return null;

  if (loading && !status) {
    return (
      <div
        data-testid="merchant-panel"
        className="bg-white rounded-xl border border-neutral-200 p-6"
      >
        <div className="flex items-center gap-3 mb-4">
          <ShoppingCart size={20} weight="duotone" color="#4285F4" />
          <h3 className="text-lg font-semibold text-neutral-900">
            Google Shopping
          </h3>
        </div>
        <div className="text-sm text-neutral-500">Chargement du statut…</div>
      </div>
    );
  }

  if (error) {
    return (
      <div
        data-testid="merchant-panel"
        className="bg-white rounded-xl border border-neutral-200 p-6"
      >
        <div className="flex items-center gap-3 mb-4">
          <ShoppingCart size={20} weight="duotone" color="#4285F4" />
          <h3 className="text-lg font-semibold text-neutral-900">
            Google Shopping
          </h3>
        </div>
        <div className="flex items-center gap-2 text-sm text-rose-700">
          <Warning size={16} weight="duotone" />
          {error}
        </div>
      </div>
    );
  }

  const connected = !!status?.connected;
  const merchantId = status?.merchant_id;
  const lastSync = status?.last_sync;
  const productsActive = status?.products_active ?? 0;
  const published = !!status?.site_published;

  const syncedOk = lastSync?.products_pushed_ok ?? 0;
  const syncedErr = lastSync?.products_pushed_err ?? 0;
  const lastSyncAt = lastSync?.finished_at;
  const errors = lastSync?.errors || [];

  // Statut visuel
  let statusBadge;
  if (!connected) {
    statusBadge = {
      label: "Non connecté",
      icon: XCircle,
      bg: "#F5F5F5",
      text: "#57534E",
    };
  } else if (!merchantId) {
    statusBadge = {
      label: "Merchant ID manquant",
      icon: Warning,
      bg: "#FEF3C7",
      text: "#B45309",
    };
  } else if (!lastSync) {
    statusBadge = {
      label: "Connecté · en attente",
      icon: CheckCircle,
      bg: "#E0F2FE",
      text: "#0369A1",
    };
  } else if (syncedErr > 0 && syncedOk === 0) {
    statusBadge = {
      label: "Dernière sync en échec",
      icon: XCircle,
      bg: "#FFE4E6",
      text: "#BE123C",
    };
  } else if (syncedErr > 0) {
    statusBadge = {
      label: "Sync partielle",
      icon: Warning,
      bg: "#FEF3C7",
      text: "#B45309",
    };
  } else {
    statusBadge = {
      label: "Sync OK",
      icon: CheckCircle,
      bg: "#D1FAE5",
      text: "#047857",
    };
  }

  const BadgeIcon = statusBadge.icon;

  return (
    <>
      <div
        data-testid="merchant-panel"
        className="bg-white rounded-xl border border-neutral-200 p-6"
      >
        <div className="flex items-start justify-between gap-4 mb-5">
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 rounded-lg bg-[#EAF4FE] flex items-center justify-center">
              <ShoppingCart size={20} weight="duotone" color="#4285F4" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-neutral-900">
                Google Shopping
              </h3>
              <p className="text-sm text-neutral-500 mt-0.5">
                Push automatique du catalogue vers Merchant Center · admin only
              </p>
            </div>
          </div>
          <span
            data-testid="merchant-status"
            className="flex items-center gap-1.5 text-xs uppercase tracking-widest px-2.5 py-1 rounded-full"
            style={{ background: statusBadge.bg, color: statusBadge.text }}
          >
            <BadgeIcon size={12} weight="bold" />
            {statusBadge.label}
          </span>
        </div>

        {!connected && (
          <div
            data-testid="merchant-not-connected"
            className="bg-[#FAFAF9] border border-neutral-200 rounded-lg p-4 flex items-center justify-between gap-4"
          >
            <div className="flex items-start gap-3">
              <Warning size={18} weight="duotone" color="#B45309" className="mt-0.5" />
              <div>
                <div className="text-sm font-medium text-neutral-900 mb-1">
                  Merchant Center non connecté au niveau plateforme
                </div>
                <div className="text-xs text-neutral-600">
                  Connectez-vous avec Google depuis le tableau de bord des
                  intégrations pour activer le push automatique du catalogue.
                </div>
              </div>
            </div>
            <button
              onClick={() => navigate("/admin/integrations")}
              data-testid="merchant-goto-integrations"
              className="h-9 px-4 rounded-lg bg-neutral-900 hover:bg-neutral-800 text-white text-xs font-medium flex items-center gap-1.5 transition whitespace-nowrap"
            >
              <Gear size={14} weight="bold" />
              Connecter Merchant Center
            </button>
          </div>
        )}

        {connected && (
          <>
            {/* 4 KPIs */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">
              <StatCard
                label="Merchant ID"
                value={merchantId || "—"}
                muted={!merchantId}
              />
              <StatCard
                label="Produits actifs"
                value={productsActive}
                muted={productsActive === 0}
              />
              <StatCard
                label="Dernière sync · OK"
                value={lastSync ? syncedOk : "—"}
                tone={lastSync && syncedOk > 0 ? "success" : "neutral"}
              />
              <StatCard
                label="Dernière sync · KO"
                value={lastSync ? syncedErr : "—"}
                tone={lastSync && syncedErr > 0 ? "error" : "neutral"}
              />
            </div>

            {/* Meta line */}
            <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-neutral-500 mb-5">
              {lastSyncAt && (
                <span>
                  Dernière sync : {formatSyncDate(lastSyncAt)}
                </span>
              )}
              {!lastSyncAt && (
                <span>Aucune synchronisation effectuée pour ce site</span>
              )}
              <span>·</span>
              <span>
                Site{" "}
                {published ? (
                  <span className="text-emerald-700 font-medium">publié</span>
                ) : (
                  <span className="text-amber-700 font-medium">non publié</span>
                )}
              </span>
            </div>

            {/* Actions */}
            <div className="flex flex-wrap items-center gap-2">
              <button
                onClick={handleSync}
                disabled={syncing || !merchantId || !published || productsActive === 0}
                data-testid="merchant-sync-btn"
                className="h-10 px-4 rounded-xl bg-neutral-900 hover:bg-neutral-800 text-white text-sm font-medium flex items-center gap-2 transition disabled:opacity-40 disabled:cursor-not-allowed"
              >
                <ArrowClockwise
                  size={16}
                  weight="bold"
                  className={syncing ? "animate-spin" : ""}
                />
                {syncing ? "Synchronisation…" : "Sync now"}
              </button>
              {errors.length > 0 && (
                <button
                  onClick={() => setShowErrorsModal(true)}
                  data-testid="merchant-errors-btn"
                  className="h-10 px-4 rounded-xl bg-white border border-rose-200 hover:border-rose-400 text-rose-700 text-sm font-medium flex items-center gap-2 transition"
                >
                  <Warning size={16} weight="duotone" />
                  Voir les erreurs ({errors.length})
                </button>
              )}
              {!merchantId && (
                <div className="text-xs text-amber-700 flex items-center gap-1.5 ml-1">
                  <Warning size={13} weight="duotone" />
                  Renseignez le Merchant ID dans /admin/integrations
                </div>
              )}
              {merchantId && !published && (
                <div className="text-xs text-neutral-500 flex items-center gap-1.5 ml-1">
                  <LinkIcon size={13} />
                  Publiez le site pour activer le push
                </div>
              )}
            </div>

            {/* Dernier résultat de sync manuelle */}
            {lastSyncResult && (
              <div
                className={`mt-4 p-3 rounded-lg border text-sm ${
                  lastSyncResult.ok
                    ? "bg-emerald-50 border-emerald-200 text-emerald-900"
                    : "bg-rose-50 border-rose-200 text-rose-900"
                }`}
              >
                {lastSyncResult.ok ? (
                  <>
                    ✓ Sync lancée · {lastSyncResult.pushed_ok ?? 0} OK /{" "}
                    {lastSyncResult.pushed_err ?? 0} erreurs
                    {lastSyncResult.message ? ` · ${lastSyncResult.message}` : ""}
                  </>
                ) : (
                  <>
                    ✕ {lastSyncResult.message || lastSyncResult.error || "Erreur"}
                  </>
                )}
              </div>
            )}
          </>
        )}
      </div>

      {/* Modal erreurs */}
      {showErrorsModal && (
        <ErrorsModal
          errors={errors}
          onClose={() => setShowErrorsModal(false)}
        />
      )}
    </>
  );
}

function StatCard({ label, value, tone = "neutral", muted = false }) {
  const toneClasses = {
    neutral: "bg-neutral-50 border-neutral-200 text-neutral-900",
    success: "bg-emerald-50 border-emerald-200 text-emerald-900",
    error: "bg-rose-50 border-rose-200 text-rose-900",
  };
  return (
    <div
      className={`rounded-lg border px-3 py-3 ${toneClasses[tone]} ${
        muted ? "opacity-60" : ""
      }`}
    >
      <div className="text-[10px] uppercase tracking-widest opacity-70 mb-1">
        {label}
      </div>
      <div className="text-sm font-semibold truncate">{value}</div>
    </div>
  );
}

function ErrorsModal({ errors, onClose }) {
  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-2xl max-w-2xl w-full max-h-[80vh] flex flex-col shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between p-5 border-b border-neutral-200">
          <div className="flex items-center gap-2">
            <Warning size={20} weight="duotone" color="#BE123C" />
            <h3 className="text-lg font-semibold text-neutral-900">
              Erreurs de la dernière synchronisation
            </h3>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-lg hover:bg-neutral-100 flex items-center justify-center transition"
            data-testid="merchant-errors-close"
          >
            <XIcon size={16} />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-5 space-y-3">
          {errors.length === 0 && (
            <div className="text-sm text-neutral-500">
              Aucune erreur à afficher.
            </div>
          )}
          {errors.map((e, i) => (
            <div
              key={i}
              className="bg-rose-50 border border-rose-200 rounded-lg p-3"
            >
              <div className="flex items-start justify-between gap-2 mb-1">
                <span className="text-xs font-mono uppercase text-rose-900 font-semibold">
                  {e.google_code || "error"}
                </span>
                {e.offerId && (
                  <span className="text-xs text-neutral-600 font-mono">
                    SKU {e.offerId}
                  </span>
                )}
              </div>
              <div className="text-sm text-rose-900">
                {e.message || "Erreur sans détail"}
              </div>
            </div>
          ))}
        </div>
        <div className="p-4 border-t border-neutral-200 text-xs text-neutral-500">
          Les 10 premières erreurs remontées par Google Content API v2.1.
        </div>
      </div>
    </div>
  );
}

function formatSyncDate(iso) {
  try {
    const d = new Date(iso);
    return d.toLocaleString("fr-FR", {
      day: "2-digit",
      month: "short",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}
