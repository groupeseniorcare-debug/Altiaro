import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, apiCall } from "../lib/api";
import {
  ChartLineUp,
  GoogleLogo,
  CheckCircle,
  ArrowRight,
  Warning,
} from "@phosphor-icons/react";
import useMasterGoogleStatus from "../hooks/useMasterGoogleStatus";

/**
 * GSC connect/metrics band.
 *
 * Comportement 2026-04-29 :
 *  - Si master OAuth Altiaro est connecté (`google_master.connected === true`)
 *    → affiche un statut PASSIF "Search Console géré par la plateforme".
 *    Aucun bouton "Connecter GSC" dans ce cas.
 *  - Sinon, comportement legacy (CTA connect, métriques 28 jours, déco).
 */
export default function GSCConnectCard({ siteId }) {
  const master = useMasterGoogleStatus();
  const [status, setStatus] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(false);

  const masterCovered = master.connected && master.services?.gsc;

  useEffect(() => {
    let cancelled = false;
    (async () => {
      // Si master OAuth couvre GSC, on tente quand même de lire les métriques
      // (provisioning a peut-être déjà déclaré le site dans GSC).
      const { data } = await apiCall(() =>
        api.get(`/sites/${siteId}/gsc/status`),
      );
      if (cancelled) return;
      setStatus(data || null);
      if (data?.connected) {
        const { data: m } = await apiCall(() =>
          api.get(`/sites/${siteId}/gsc/metrics?days=28`),
        );
        if (!cancelled && m) setMetrics(m);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [siteId]);

  const connect = async () => {
    setLoading(true);
    const { data, error, rawDetail } = await apiCall(() =>
      api.get(`/sites/${siteId}/gsc/connect`),
    );
    setLoading(false);
    if (error) {
      window.alert(rawDetail?.detail || error);
      return;
    }
    if (data?.authorization_url) {
      window.open(data.authorization_url, "_blank", "noopener,noreferrer");
    }
  };

  // ---- Cas Master OAuth couvre GSC : statut passif ----
  if (masterCovered) {
    const avg = metrics?.avg_position;
    const avgLabel = avg ? avg.toFixed(1) : "—";
    return (
      <div
        className="px-6 md:px-7 py-4 bg-[#FDFCF9]"
        style={{ borderTop: "1px solid #E5E5E5" }}
        data-testid="gsc-master-managed"
      >
        <div className="flex items-center gap-2 mb-3 text-[10px] uppercase tracking-[0.3em] text-neutral-500">
          <CheckCircle size={12} weight="fill" className="text-emerald-700" />
          Search Console géré par la plateforme Altiaro
        </div>
        {metrics ? (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Stat label="Position moyenne" value={avgLabel} Icon={ChartLineUp} />
            <Stat
              label="Clics"
              value={metrics.clicks?.toLocaleString("fr-FR") || "0"}
            />
            <Stat
              label="Impressions"
              value={metrics.impressions?.toLocaleString("fr-FR") || "0"}
            />
            <Stat label="CTR" value={`${metrics.ctr ?? 0}%`} />
          </div>
        ) : (
          <div className="text-[12px] text-neutral-500">
            Données Google Search Console disponibles dès la propagation DNS
            (généralement 24–48 h après la mise en ligne).
          </div>
        )}
      </div>
    );
  }

  if (!status) return null;

  // Case 1 — Not configured at platform level (missing env vars)
  if (!status.configured) {
    return (
      <div
        className="px-6 md:px-7 py-3 flex items-start gap-2.5 bg-[#F5F5F5]"
        style={{ borderTop: "1px solid #E5E5E5" }}
        data-testid="gsc-not-configured"
      >
        <Warning
          size={14}
          weight="regular"
          className="text-neutral-500 shrink-0 mt-[2px]"
        />
        <div className="text-[11.5px] text-neutral-600 leading-[1.55]">
          Position Google — l'intégration Search Console sera activée dès
          que l'admin connectera le compte Google maître Altiaro
          (
          <Link
            to="/admin/google/master-auth"
            className="underline text-neutral-900"
          >
            ouvrir
          </Link>
          ).
        </div>
      </div>
    );
  }

  // Case 2 — Configured but not connected for this site (legacy path)
  if (!status.connected) {
    return (
      <div
        className="px-6 md:px-7 py-4 bg-[#F5F5F5] flex items-center gap-4 flex-wrap justify-between"
        style={{ borderTop: "1px solid #E5E5E5" }}
        data-testid="gsc-connect-cta"
      >
        <div className="flex items-start gap-3">
          <GoogleLogo
            size={18}
            weight="bold"
            className="text-neutral-900 shrink-0 mt-[2px]"
          />
          <div>
            <div className="text-[12.5px] font-semibold text-neutral-900">
              Search Console (mode manuel)
            </div>
            <div className="text-[11.5px] text-neutral-600 mt-0.5">
              Mode legacy. Pour la méthode recommandée, demande à l'admin de
              connecter le compte Google maître.
            </div>
          </div>
        </div>
        <button
          onClick={connect}
          disabled={loading}
          data-testid="gsc-connect-btn"
          className="h-9 px-4 bg-neutral-900 hover:bg-black text-white text-[12px] font-semibold flex items-center gap-2 transition disabled:opacity-60"
          style={{ borderRadius: "2px" }}
        >
          {loading ? "Ouverture…" : "Connecter (legacy)"}
          <ArrowRight size={12} weight="bold" />
        </button>
      </div>
    );
  }

  // Case 3 — Connected (legacy)
  const avg = metrics?.avg_position;
  const avgLabel = avg ? avg.toFixed(1) : "—";
  return (
    <div
      className="px-6 md:px-7 py-4 bg-[#F5F5F5]"
      style={{ borderTop: "1px solid #E5E5E5" }}
      data-testid="gsc-connected"
    >
      <div className="flex items-center gap-2 mb-3 text-[10px] uppercase tracking-[0.3em] text-neutral-500">
        <CheckCircle size={12} weight="fill" className="text-emerald-600" />
        Google Search Console · {status.property_url}
      </div>
      {metrics ? (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Stat label="Position moyenne" value={avgLabel} Icon={ChartLineUp} />
          <Stat
            label="Clics"
            value={metrics.clicks?.toLocaleString("fr-FR") || "0"}
          />
          <Stat
            label="Impressions"
            value={metrics.impressions?.toLocaleString("fr-FR") || "0"}
          />
          <Stat label="CTR" value={`${metrics.ctr ?? 0}%`} />
        </div>
      ) : (
        <div className="text-[12px] text-neutral-500">
          Chargement des métriques Google…
        </div>
      )}
    </div>
  );
}

function Stat({ label, value, Icon }) {
  return (
    <div>
      <div className="text-[9px] uppercase tracking-[0.3em] text-neutral-500 mb-1 flex items-center gap-1">
        {Icon ? <Icon size={10} weight="bold" /> : null}
        {label}
      </div>
      <div
        className="text-[22px] md:text-[26px] leading-none text-neutral-900"
        style={{ fontFamily: "'Fraunces', Georgia, serif" }}
      >
        {value}
      </div>
    </div>
  );
}
