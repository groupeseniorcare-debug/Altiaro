import React, { useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { api, apiCall } from "../lib/api";
import Layout from "../components/Layout";
import {
  ArrowLeft,
  TrendUp,
  Fire,
  CheckCircle,
  ArrowClockwise,
  Sparkle,
  ArrowRight,
  Circle,
  Warning,
} from "@phosphor-icons/react";

const COUNTRY_FLAGS = {
  FR: "🇫🇷", DE: "🇩🇪", BE: "🇧🇪", NL: "🇳🇱",
  UK: "🇬🇧", CH: "🇨🇭", ES: "🇪🇸", IT: "🇮🇹",
};

export default function Opportunities() {
  const navigate = useNavigate();
  const [alerts, setAlerts] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);
  const [scanResult, setScanResult] = useState(null);
  const [filter, setFilter] = useState("all"); // all | unread

  const load = useCallback(async () => {
    const { data } = await apiCall(() =>
      api.get(`/opportunities/alerts?unread_only=${filter === "unread"}&limit=100`)
    );
    if (data) {
      setAlerts(data.alerts || []);
      setUnreadCount(data.unread_count || 0);
    }
    setLoading(false);
  }, [filter]);

  useEffect(() => {
    load();
  }, [load]);

  const handleAck = async (alertId) => {
    await apiCall(() =>
      api.post(`/opportunities/alerts/${alertId}/ack`, { acknowledged: true })
    );
    load();
  };

  const runScanNow = async () => {
    setScanning(true);
    setScanResult(null);
    const { data, error } = await apiCall(() =>
      api.post("/opportunities/scan-now")
    );
    setScanning(false);
    if (error) {
      setScanResult({ error });
      return;
    }
    setScanResult(data);
    load();
  };

  return (
    <Layout>
      <div className="p-8 md:p-12 max-w-[1200px]">
        <button
          onClick={() => navigate("/")}
          className="flex items-center gap-2 text-sm text-[#78716C] hover:text-[#1C1917] mb-6 transition"
          data-testid="opp-back"
        >
          <ArrowLeft size={16} /> Tableau de bord
        </button>

        <div className="flex items-start justify-between gap-8 mb-6">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <div className="w-11 h-11 rounded-lg bg-gradient-to-br from-[#F97316] to-[#EF4444] flex items-center justify-center">
                <Fire size={22} weight="fill" color="#fff" />
              </div>
              <span className="text-[11px] uppercase tracking-widest text-[#78716C]">
                Sprint 21 · Admin only
              </span>
            </div>
            <h1 className="font-heading text-4xl font-semibold text-[#1C1917] mb-1">
              Opportunités détectées
            </h1>
            <p className="text-[#57534E]">
              Chaque lundi 5h UTC, on re-scanne les niches analysées et on te signale les{" "}
              <strong>spikes de volume Google &gt; 30%</strong> en temps réel.
            </p>
          </div>
          <button
            onClick={runScanNow}
            disabled={scanning}
            data-testid="opp-scan-now"
            className="h-11 px-4 rounded-xl bg-gradient-to-r from-[#F97316] to-[#EF4444] text-white text-sm font-medium flex items-center gap-2 transition disabled:opacity-60"
          >
            {scanning ? (
              <>
                <ArrowClockwise size={14} className="animate-spin" /> Scan en cours…
              </>
            ) : (
              <>
                <Sparkle size={14} weight="fill" /> Scanner maintenant
              </>
            )}
          </button>
        </div>

        {scanResult && (
          <div
            data-testid="opp-scan-result"
            className={`mb-4 p-3 rounded-lg text-sm flex items-start gap-2 ${
              scanResult.error
                ? "bg-[#FFE4E6] text-[#BE123C]"
                : "bg-[#D1FAE5] text-[#047857]"
            }`}
          >
            {scanResult.error ? (
              <>
                <Warning size={14} weight="fill" className="mt-0.5" />
                <div>Erreur : {scanResult.error}</div>
              </>
            ) : (
              <>
                <CheckCircle size={14} weight="fill" className="mt-0.5" />
                <div>
                  Scan terminé · {scanResult.scanned} analyses vérifiées ·{" "}
                  <strong>{scanResult.new_alerts} nouvelle(s) alerte(s)</strong>{" "}
                  · {scanResult.errors} erreurs · {scanResult.skipped_no_google} skip (Google pas prêt)
                </div>
              </>
            )}
          </div>
        )}

        <div className="flex items-center gap-2 mb-5">
          <button
            onClick={() => setFilter("all")}
            data-testid="opp-filter-all"
            className={`h-8 px-3 rounded-full text-xs font-medium transition ${
              filter === "all"
                ? "bg-[#1C1917] text-white"
                : "bg-white border border-[#E7E5E4] text-[#57534E] hover:border-[#1C1917]"
            }`}
          >
            Toutes ({alerts.length})
          </button>
          <button
            onClick={() => setFilter("unread")}
            data-testid="opp-filter-unread"
            className={`h-8 px-3 rounded-full text-xs font-medium transition flex items-center gap-1.5 ${
              filter === "unread"
                ? "bg-[#F97316] text-white"
                : "bg-white border border-[#E7E5E4] text-[#57534E] hover:border-[#F97316]"
            }`}
          >
            Non lues{" "}
            {unreadCount > 0 && (
              <span className="bg-white/30 px-1.5 rounded-full text-[10px] font-bold">
                {unreadCount}
              </span>
            )}
          </button>
        </div>

        {loading ? (
          <div className="py-12 text-center text-sm text-[#78716C]">Chargement…</div>
        ) : alerts.length === 0 ? (
          <div className="bg-white rounded-xl border border-dashed border-[#E7E5E4] p-12 text-center">
            <TrendUp size={32} weight="duotone" className="mx-auto mb-3 text-[#A8A29E]" />
            <div className="font-medium text-[#1C1917] mb-1">Aucune alerte pour l'instant</div>
            <p className="text-sm text-[#78716C] max-w-md mx-auto">
              Dès qu'une niche déjà analysée voit son volume Google grimper de +30% ou plus, tu la
              verras ici. Clique "Scanner maintenant" pour forcer un scan immédiat.
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {alerts.map((alert) => (
              <div
                key={alert.id}
                data-testid={`opp-alert-${alert.id}`}
                className={`bg-white rounded-xl border p-5 transition ${
                  alert.acknowledged ? "border-[#E7E5E4] opacity-70" : "border-[#F97316]/40 shadow-sm"
                }`}
              >
                <div className="flex items-start gap-4">
                  <div
                    className={`w-12 h-12 rounded-xl flex items-center justify-center shrink-0 ${
                      alert.acknowledged
                        ? "bg-[#F5F2EB]"
                        : "bg-gradient-to-br from-[#F97316] to-[#EF4444]"
                    }`}
                  >
                    {alert.acknowledged ? (
                      <CheckCircle size={22} weight="fill" className="text-[#78716C]" />
                    ) : (
                      <Fire size={22} weight="fill" className="text-white" />
                    )}
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap mb-1">
                      <span className="text-2xl">{COUNTRY_FLAGS[alert.country] || "🌍"}</span>
                      <div className="font-heading text-lg font-semibold text-[#1C1917]">
                        {alert.product_input}
                      </div>
                      <span
                        className="text-[11px] uppercase tracking-wider px-2 py-0.5 rounded-full font-semibold"
                        style={{
                          backgroundColor: alert.change_pct >= 100 ? "#EF4444" : "#F59E0B",
                          color: "#fff",
                        }}
                      >
                        +{alert.change_pct}% vol
                      </span>
                    </div>

                    <div className="flex flex-wrap gap-4 text-sm text-[#57534E] mb-3">
                      <div>
                        Volume :{" "}
                        <span className="font-mono text-[#78716C]">
                          {alert.volume_before.toLocaleString("fr-FR")}
                        </span>{" "}
                        →{" "}
                        <span className="font-mono font-semibold text-[#1C1917]">
                          {alert.volume_now.toLocaleString("fr-FR")}
                        </span>{" "}
                        /mois
                      </div>
                      <div>
                        CPC moy : <strong>{alert.avg_cpc_eur?.toFixed(2)}€</strong>
                      </div>
                    </div>

                    {alert.top_keywords?.length > 0 && (
                      <div className="flex flex-wrap gap-1.5 mb-3">
                        {alert.top_keywords.slice(0, 5).map((k, i) => (
                          <span
                            key={i}
                            className="text-[11px] px-2 py-0.5 rounded-full bg-[#FAF7F2] border border-[#E7E5E4] text-[#57534E]"
                            title={`${k.volume.toLocaleString("fr-FR")} recherches/mois · ${k.competition}`}
                          >
                            {k.keyword}{" "}
                            <span className="text-[#A8A29E]">
                              ({k.volume.toLocaleString("fr-FR")})
                            </span>
                          </span>
                        ))}
                      </div>
                    )}

                    <div className="flex items-center gap-2 flex-wrap text-xs">
                      <button
                        onClick={() => navigate(`/niches/analysis/${alert.analysis_id}`)}
                        data-testid={`opp-open-analysis-${alert.id}`}
                        className="h-8 px-3 rounded-lg bg-[#1C1917] hover:bg-[#44403C] text-white font-medium flex items-center gap-1.5 transition"
                      >
                        Voir l'analyse <ArrowRight size={12} weight="bold" />
                      </button>
                      {!alert.acknowledged && (
                        <button
                          onClick={() => handleAck(alert.id)}
                          data-testid={`opp-ack-${alert.id}`}
                          className="h-8 px-3 rounded-lg bg-white border border-[#E7E5E4] hover:border-[#047857] text-[#57534E] font-medium flex items-center gap-1.5 transition"
                        >
                          <CheckCircle size={12} /> Marquer vue
                        </button>
                      )}
                      <span className="text-[11px] text-[#78716C] ml-auto">
                        Détectée le {alert.detected_at?.slice(0, 16).replace("T", " ")}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </Layout>
  );
}
