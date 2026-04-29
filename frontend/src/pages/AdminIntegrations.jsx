import React, { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowLeft,
  ArrowsClockwise,
  CheckCircle,
  Warning,
  XCircle,
  Plugs,
  ArrowSquareOut,
  SpinnerGap,
  Info,
  Link as LinkIcon,
} from "@phosphor-icons/react";
import { api, apiCall } from "../lib/api";
import { useAuth } from "../lib/auth";
import GscMultiSitePanel from "../components/admin/GscMultiSitePanel";

/**
 * Admin · Santé de la plateforme (Phase 3).
 *
 * Ping en temps réel des 10 intégrations Altiaro via
 * `GET /api/admin/integrations/health`. Polling 60 s (pause si onglet inactif).
 * Une card par intégration, actions contextuelles selon le statut.
 *
 * Préservation des data-testids historiques d'AE (`admin-ali-*`) via alias
 * sur la carte AliExpress.
 */

const STATUS_COLOR = {
  ok: {
    bg: "bg-emerald-50",
    border: "border-emerald-200",
    text: "text-emerald-700",
    Icon: CheckCircle,
    label: "Opérationnel",
  },
  warning: {
    bg: "bg-amber-50",
    border: "border-amber-200",
    text: "text-amber-700",
    Icon: Warning,
    label: "Action requise",
  },
  error: {
    bg: "bg-rose-50",
    border: "border-rose-200",
    text: "text-rose-700",
    Icon: XCircle,
    label: "Erreur",
  },
  not_configured: {
    bg: "bg-neutral-100",
    border: "border-neutral-200",
    text: "text-neutral-600",
    Icon: Info,
    label: "Non configuré",
  },
};

function timeAgo(isoDate) {
  if (!isoDate) return "—";
  const t = new Date(isoDate).getTime();
  const secs = Math.max(0, Math.floor((Date.now() - t) / 1000));
  if (secs < 60) return `il y a ${secs}s`;
  const mins = Math.floor(secs / 60);
  if (mins < 60) return `il y a ${mins} min`;
  const hrs = Math.floor(mins / 60);
  return `il y a ${hrs} h`;
}

export default function AdminIntegrations() {
  const { user } = useAuth();
  const [integrations, setIntegrations] = useState([]);
  const [checkedAt, setCheckedAt] = useState(null);
  const [loading, setLoading] = useState(false);
  const [cardLoading, setCardLoading] = useState({}); // {key: true}
  const [errorModal, setErrorModal] = useState(null); // integration object or null
  const [oauthToast, setOauthToast] = useState(null); // {service, status, message}
  const pollRef = useRef(null);

  const fetchHealth = useCallback(async (force = false) => {
    setLoading(true);
    const q = force ? "?force=true" : "";
    const { data } = await apiCall(() => api.get(`/admin/integrations/health${q}`));
    setLoading(false);
    if (data?.integrations) {
      setIntegrations(data.integrations);
      setCheckedAt(data.checked_at);
    }
  }, []);

  const pingOne = useCallback(async (key) => {
    setCardLoading((s) => ({ ...s, [key]: true }));
    const { data } = await apiCall(() => api.get(`/admin/integrations/${key}/ping?force=true`));
    setCardLoading((s) => ({ ...s, [key]: false }));
    if (data) {
      setIntegrations((prev) => prev.map((i) => (i.key === key ? data : i)));
    }
  }, []);

  const connectOne = useCallback(async (key) => {
    setCardLoading((s) => ({ ...s, [key]: true }));
    const { data, error } = await apiCall(() => api.post(`/admin/integrations/${key}/connect`));
    setCardLoading((s) => ({ ...s, [key]: false }));
    if (error || !data) {
      window.alert(error || "Impossible de démarrer la connexion.");
      return;
    }
    // OAuth flow → full page redirect (préserve cookies httpOnly SameSite=None).
    // Popup + noopener cassait la session admin : le cookie n'était pas
    // réinjecté sur le callback, et la page /admin/integrations ne se
    // rafraîchissait pas automatiquement au retour.
    if (data.authorize_url) {
      window.location.href = data.authorize_url;
      return;
    }
    // Docs externes (non-OAuth) → nouvelle fenêtre OK
    if (data.docs_url) {
      if (data.docs_url.startsWith("http")) {
        window.open(data.docs_url, "_blank", "noopener");
      } else {
        window.alert(data.message || "Voir la documentation : " + data.docs_url);
      }
    }
  }, []);

  const disconnectAli = async () => {
    if (!window.confirm("Déconnecter AliExpress au niveau plateforme ? Tous les imports + commandes auto s'arrêteront.")) return;
    await apiCall(() => api.post("/admin/aliexpress/disconnect"));
    pingOne("aliexpress");
  };

  // Initial load + polling 60s (paused when tab not visible)
  useEffect(() => {
    fetchHealth(false);
    const tick = () => {
      if (document.visibilityState === "visible") fetchHealth(false);
    };
    pollRef.current = setInterval(tick, 60_000);
    const onFocus = () => fetchHealth(false);
    window.addEventListener("focus", onFocus);
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
      window.removeEventListener("focus", onFocus);
    };
  }, [fetchHealth]);

  // Parse OAuth callback querystrings (?google_ads=connected, ?merchant=connected,
  // ?aliexpress=connected, etc.) pour afficher un toast immédiat + force refresh.
  useEffect(() => {
    if (typeof window === "undefined") return;
    const qs = new URLSearchParams(window.location.search);
    const services = ["google_ads", "merchant", "aliexpress", "gsc"];
    for (const svc of services) {
      const val = qs.get(svc);
      if (!val) continue;
      const serviceLabels = {
        google_ads: "Google Ads",
        merchant: "Google Merchant Center",
        aliexpress: "AliExpress",
        gsc: "Google Search Console",
      };
      const label = serviceLabels[svc] || svc;
      if (val === "connected") {
        setOauthToast({ service: svc, status: "ok", message: `${label} connecté avec succès.` });
      } else if (val === "error") {
        const reason = qs.get("reason") || "inconnu";
        setOauthToast({ service: svc, status: "error", message: `${label} : échec OAuth (${reason}).` });
      }
      // Clean URL (sans reload)
      window.history.replaceState({}, "", window.location.pathname);
      // Force refresh immédiat pour voir la card passer ok/error
      fetchHealth(true);
      // Auto-dismiss toast après 8s
      setTimeout(() => setOauthToast(null), 8000);
      break;
    }
  }, [fetchHealth]);

  if (user && user.role !== "admin") {
    return (
      <div className="min-h-screen bg-[#FAF7F2] flex items-center justify-center">
        <div className="text-neutral-500">Accès réservé à l'administrateur.</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#FAF7F2]">
      <div className="max-w-[1400px] mx-auto px-6 md:px-10 py-8">
        {oauthToast && (
          <div
            data-testid={`oauth-toast-${oauthToast.service}`}
            className={`mb-6 px-4 py-3 rounded-xl border flex items-center gap-3 ${
              oauthToast.status === "ok"
                ? "bg-emerald-50 border-emerald-200 text-emerald-900"
                : "bg-rose-50 border-rose-200 text-rose-900"
            }`}
          >
            {oauthToast.status === "ok" ? (
              <CheckCircle size={20} weight="duotone" />
            ) : (
              <XCircle size={20} weight="duotone" />
            )}
            <span className="text-sm font-medium">{oauthToast.message}</span>
            <button
              onClick={() => setOauthToast(null)}
              className="ml-auto text-xs opacity-70 hover:opacity-100"
            >
              ✕
            </button>
          </div>
        )}

        <Link
          to="/"
          className="inline-flex items-center gap-2 text-sm text-neutral-600 hover:text-neutral-900 mb-6"
          data-testid="admin-int-back"
        >
          <ArrowLeft size={14} /> Retour au dashboard
        </Link>

        <div className="mb-8 flex items-start justify-between gap-4 flex-wrap" data-testid="integrations-header">
          <div>
            <div className="text-[11px] uppercase tracking-[0.2em] text-neutral-500 mb-2">Admin · Santé de la plateforme</div>
            <h1 className="text-3xl md:text-4xl font-semibold text-neutral-900" style={{ fontFamily: "'Fraunces', serif" }}>
              Intégrations Altiaro
            </h1>
            <p className="text-sm text-neutral-500 mt-2 max-w-2xl">
              État en temps réel des 10 intégrations utilisées par la plateforme. Rafraîchi automatiquement toutes les 60 secondes.
            </p>
          </div>
          <div className="flex items-center gap-3">
            {checkedAt && (
              <div className="text-xs text-neutral-500">
                Dernière vérification : <span className="font-medium text-neutral-700">{timeAgo(checkedAt)}</span>
              </div>
            )}
            <button
              onClick={() => fetchHealth(true)}
              disabled={loading}
              data-testid="refresh-all-btn"
              className="h-10 px-4 rounded-xl bg-neutral-900 hover:bg-neutral-800 text-white text-sm font-medium flex items-center gap-2 disabled:opacity-60"
            >
              {loading ? (
                <SpinnerGap size={14} weight="bold" className="animate-spin" />
              ) : (
                <ArrowsClockwise size={14} weight="bold" />
              )}
              Rafraîchir
            </button>
          </div>
        </div>

        {integrations.length === 0 && loading && (
          <div className="py-20 text-center text-neutral-500">
            <SpinnerGap size={24} weight="bold" className="animate-spin mx-auto mb-2" />
            Chargement…
          </div>
        )}

        {/* Refonte UX — Connexion GSC multi-sites depuis l'admin */}
        <GscMultiSitePanel />

        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {integrations.map((it) => (
            <IntegrationCard
              key={it.key}
              int={it}
              loading={!!cardLoading[it.key]}
              onTest={() => pingOne(it.key)}
              onConnect={() => connectOne(it.key)}
              onDisconnect={it.key === "aliexpress" ? disconnectAli : null}
              onShowError={() => setErrorModal(it)}
            />
          ))}
        </div>

        {errorModal && (
          <ErrorModal
            int={errorModal}
            onClose={() => setErrorModal(null)}
            onRetest={() => {
              pingOne(errorModal.key);
              setErrorModal(null);
            }}
          />
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------- //
// IntegrationCard — presentation component                          //
// ---------------------------------------------------------------- //
function IntegrationCard({ int, loading, onTest, onConnect, onDisconnect, onShowError }) {
  const style = STATUS_COLOR[int.status] || STATUS_COLOR.not_configured;
  const StatusIcon = style.Icon;

  // AliExpress : alias testids historiques pour non-régression
  const isAE = int.key === "aliexpress";
  const legacyBadgeTestid = isAE
    ? int.connected
      ? "admin-ali-badge-connected"
      : "admin-ali-badge-disconnected"
    : undefined;

  return (
    <div
      className="bg-white border border-neutral-200 rounded-2xl p-5 flex flex-col"
      data-testid={`integration-card-${int.key}`}
      {...(isAE ? { "data-testid-legacy": "admin-ali-card" } : {})}
    >
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-start gap-3 min-w-0">
          <div className={`w-10 h-10 rounded-xl ${style.bg} ${style.border} border flex items-center justify-center flex-shrink-0`}>
            <Plugs size={18} weight="duotone" className={style.text} />
          </div>
          <div className="min-w-0">
            <div className="text-[15px] font-semibold text-neutral-900 leading-tight">{int.name}</div>
            <div className="text-[11px] uppercase tracking-widest text-neutral-400 mt-0.5">{int.key}</div>
          </div>
        </div>
        <span
          className={`inline-flex items-center gap-1 h-7 px-2.5 rounded-full ${style.bg} ${style.border} border ${style.text} text-[11px] font-medium whitespace-nowrap`}
          data-testid={`integration-status-${int.key}`}
        >
          <StatusIcon size={12} weight="fill" /> {style.label}
        </span>
      </div>

      {/* Message */}
      <div className="text-sm text-neutral-700 mb-4 min-h-[40px]">
        {loading ? (
          <span className="inline-flex items-center gap-2 text-neutral-500">
            <SpinnerGap size={12} weight="bold" className="animate-spin" /> Ping en cours…
          </span>
        ) : (
          int.message
        )}
      </div>

      {/* Details (optional) */}
      {int.details && Object.keys(int.details).length > 0 && (
        <div className="text-[11px] text-neutral-500 space-y-0.5 mb-3 border-t border-neutral-100 pt-3"
             data-testid={isAE && int.connected ? "admin-ali-details" : undefined}>
          {Object.entries(int.details).slice(0, 3).map(([k, v]) => (
            <div key={k} className="flex items-center gap-2">
              <span className="uppercase tracking-widest text-neutral-400">{k}</span>
              <span className="font-medium text-neutral-700">{formatDetail(v)}</span>
            </div>
          ))}
        </div>
      )}

      {/* Actions */}
      <div className="mt-auto pt-3 border-t border-neutral-100 flex flex-wrap gap-2">
        {renderActions({ int, loading, onTest, onConnect, onDisconnect, onShowError })}
      </div>

      {/* Footer : last checked + duration */}
      <div className="mt-3 flex items-center justify-between text-[11px] text-neutral-400">
        <span>{timeAgo(int.last_checked)}</span>
        <span>{int.duration_ms}ms{int.cached ? " · cache" : ""}</span>
      </div>
    </div>
  );
}

function formatDetail(v) {
  if (v === null || v === undefined) return "—";
  if (typeof v === "boolean") return v ? "oui" : "non";
  if (typeof v === "number") return v.toLocaleString("fr-FR");
  if (Array.isArray(v)) return v.slice(0, 3).join(", ") + (v.length > 3 ? `… (+${v.length - 3})` : "");
  if (typeof v === "object") return JSON.stringify(v).slice(0, 40);
  return String(v);
}

function renderActions({ int, loading, onTest, onConnect, onDisconnect, onShowError }) {
  const baseBtn = "h-9 px-3 rounded-lg text-[13px] font-medium flex items-center gap-1.5 disabled:opacity-60";
  const primary = `${baseBtn} bg-neutral-900 hover:bg-neutral-800 text-white`;
  const secondary = `${baseBtn} bg-white border border-neutral-200 hover:border-neutral-400 text-neutral-700`;
  const danger = `${baseBtn} bg-white border border-neutral-200 hover:border-rose-300 hover:text-rose-700 text-neutral-700`;

  const isAE = int.key === "aliexpress";

  // not_configured → uniquement le lien docs
  if (int.status === "not_configured") {
    return (
      <button
        onClick={onConnect}
        className={primary}
        data-testid={`integration-action-${int.key}`}
      >
        <LinkIcon size={12} weight="bold" />
        {int.requires_oauth ? "Comment connecter" : "Comment configurer"}
        <ArrowSquareOut size={11} weight="bold" />
      </button>
    );
  }

  // warning (OAuth à finaliser) → "Connecter"
  if (int.status === "warning" && !int.connected && int.requires_oauth) {
    return (
      <>
        <button
          onClick={onConnect}
          disabled={loading}
          className={primary}
          data-testid={isAE ? "admin-ali-connect" : `integration-action-${int.key}`}
        >
          <LinkIcon size={12} weight="bold" /> Connecter <ArrowSquareOut size={11} weight="bold" />
        </button>
      </>
    );
  }

  // warning connected (ex: Resend sandbox, OVH sans platform_ip) → "Tester" + éventuel "Détails"
  if (int.status === "warning") {
    return (
      <>
        <button
          onClick={onTest}
          disabled={loading}
          className={secondary}
          data-testid={`integration-action-${int.key}`}
        >
          <ArrowsClockwise size={12} weight="bold" /> Retester
        </button>
        {int.docs_url && (
          <button
            onClick={onConnect}
            className={secondary}
          >
            <ArrowSquareOut size={11} weight="bold" /> Détails
          </button>
        )}
      </>
    );
  }

  // error → "Retester" + "Voir les détails"
  if (int.status === "error") {
    return (
      <>
        <button
          onClick={onTest}
          disabled={loading}
          className={primary}
          data-testid={`integration-action-${int.key}`}
        >
          <ArrowsClockwise size={12} weight="bold" /> Retester
        </button>
        <button
          onClick={onShowError}
          className={secondary}
        >
          <Info size={12} weight="bold" /> Détails
        </button>
      </>
    );
  }

  // ok → "Tester" (+ "Déconnecter" si OAuth)
  return (
    <>
      <button
        onClick={onTest}
        disabled={loading}
        className={secondary}
        data-testid={`integration-action-${int.key}`}
      >
        <ArrowsClockwise size={12} weight="bold" /> Tester
      </button>
      {int.requires_oauth && int.connected && onDisconnect && (
        <button
          onClick={onDisconnect}
          className={danger}
          data-testid={isAE ? "admin-ali-disconnect" : `integration-disconnect-${int.key}`}
        >
          Déconnecter
        </button>
      )}
    </>
  );
}

// ---------------------------------------------------------------- //
// ErrorModal — shows raw message + details on error state           //
// ---------------------------------------------------------------- //
function ErrorModal({ int, onClose, onRetest }) {
  return (
    <div
      className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4"
      onClick={onClose}
      data-testid="integration-error-modal"
    >
      <div
        className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center gap-2 mb-3">
          <XCircle size={18} weight="fill" className="text-rose-600" />
          <h3 className="text-lg font-semibold text-neutral-900">{int.name}</h3>
        </div>
        <div className="text-sm text-neutral-700 mb-3">{int.message}</div>
        {int.details && Object.keys(int.details).length > 0 && (
          <div className="bg-neutral-50 rounded-xl p-3 mb-4 border border-neutral-200">
            <div className="text-[10px] uppercase tracking-widest text-neutral-400 mb-1">Détails</div>
            <pre className="text-[11px] text-neutral-700 whitespace-pre-wrap font-mono">
              {JSON.stringify(int.details, null, 2)}
            </pre>
          </div>
        )}
        <div className="text-[11px] text-neutral-500 mb-4">
          Vérifié {timeAgo(int.last_checked)} · {int.duration_ms}ms
        </div>
        <div className="flex gap-2">
          <button
            onClick={onRetest}
            className="h-10 px-4 rounded-xl bg-neutral-900 hover:bg-neutral-800 text-white text-sm font-medium flex items-center gap-2"
          >
            <ArrowsClockwise size={13} weight="bold" /> Retester maintenant
          </button>
          <button
            onClick={onClose}
            className="h-10 px-4 rounded-xl bg-white border border-neutral-200 hover:border-neutral-400 text-neutral-700 text-sm font-medium"
          >
            Fermer
          </button>
        </div>
      </div>
    </div>
  );
}
