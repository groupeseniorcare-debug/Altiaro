import React, { useEffect, useState } from "react";
import { api, apiCall } from "../lib/api";
import {
  ChartLineUp, GoogleLogo, CheckCircle, ArrowRight, Warning,
} from "@phosphor-icons/react";

/**
 * GSC connect/metrics band — shown inside PulseSEOWidget footer.
 * Replaces the "non_connecte" placeholder once the Concepteur has linked
 * Google Search Console.
 */
export default function GSCConnectCard({ siteId }) {
  const [status, setStatus] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(false);

  const load = async () => {
    const { data } = await apiCall(() => api.get(`/sites/${siteId}/gsc/status`));
    setStatus(data || null);
    if (data?.connected) {
      const { data: m } = await apiCall(() => api.get(`/sites/${siteId}/gsc/metrics?days=28`));
      if (m) setMetrics(m);
    }
  };

  useEffect(() => { load(); }, [siteId]);

  const connect = async () => {
    setLoading(true);
    const { data, error, rawDetail } = await apiCall(() =>
      api.get(`/sites/${siteId}/gsc/connect`)
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

  const disconnect = async () => {
    if (!window.confirm("Déconnecter Google Search Console de ce site ?")) return;
    await apiCall(() => api.post(`/sites/${siteId}/gsc/disconnect`));
    setStatus(null);
    setMetrics(null);
    load();
  };

  if (!status) return null;

  // Case 1 — Not configured at platform level (missing env vars)
  if (!status.configured) {
    return (
      <div
        className="px-6 md:px-7 py-3 flex items-start gap-2.5 bg-[#F5F5F5]"
        style={{ borderTop: "1px solid #E5E5E5" }}
        data-testid="gsc-not-configured"
      >
        <Warning size={14} weight="regular" className="text-neutral-500 shrink-0 mt-[2px]" />
        <div className="text-[11.5px] text-neutral-600 leading-[1.55]">
          Position Google — l'intégration Search Console sera activée dès que vous
          fournirez les clés Google Cloud (voir <code className="text-neutral-900">docs/GSC_SETUP.md</code>).
        </div>
      </div>
    );
  }

  // Case 2 — Configured but not connected for this site
  if (!status.connected) {
    return (
      <div
        className="px-6 md:px-7 py-4 bg-[#F5F5F5] flex items-center gap-4 flex-wrap justify-between"
        style={{ borderTop: "1px solid #E5E5E5" }}
        data-testid="gsc-connect-cta"
      >
        <div className="flex items-start gap-3">
          <GoogleLogo size={18} weight="bold" className="text-neutral-900 shrink-0 mt-[2px]" />
          <div>
            <div className="text-[12.5px] font-semibold text-neutral-900">
              Branchez Google Search Console
            </div>
            <div className="text-[11.5px] text-neutral-600 mt-0.5">
              Affichez votre position moyenne Google réelle, vos clics et impressions.
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
          {loading ? "Ouverture…" : "Connecter GSC"} <ArrowRight size={12} weight="bold" />
        </button>
      </div>
    );
  }

  // Case 3 — Connected
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
          <Stat label="Clics" value={metrics.clicks?.toLocaleString("fr-FR") || "0"} />
          <Stat label="Impressions" value={metrics.impressions?.toLocaleString("fr-FR") || "0"} />
          <Stat label="CTR" value={`${metrics.ctr ?? 0}%`} />
        </div>
      ) : (
        <div className="text-[12px] text-neutral-500">Chargement des métriques Google…</div>
      )}
      <div className="mt-3 text-right">
        <button
          onClick={disconnect}
          className="text-[10.5px] uppercase tracking-[0.2em] text-neutral-400 hover:text-neutral-900"
          data-testid="gsc-disconnect"
        >
          Déconnecter
        </button>
      </div>
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
