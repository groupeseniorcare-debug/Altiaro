import React, { useEffect, useState } from "react";
import { api, apiCall } from "../lib/api";
import { TagSimple, CurrencyEur, Fire, X, DownloadSimple, ArrowSquareOut } from "@phosphor-icons/react";

/**
 * AliExpress Deals panel — affiche les produits dont le prix a chuté cette
 * semaine dans la niche du site. Le Concepteur peut dismiss, importer, ou
 * ouvrir la fiche AliExpress directement.
 */
export default function AeDealsPanel({ siteId }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);
  const [filter, setFilter] = useState("new");

  const load = async () => {
    const { data: res } = await apiCall(() =>
      api.get(`/sites/${siteId}/deals?status=${filter}`)
    );
    setData(res || { deals: [], last_scan: {} });
    setLoading(false);
  };

  useEffect(() => { load(); }, [siteId, filter]);

  const scan = async () => {
    setScanning(true);
    const { error, rawDetail } = await apiCall(() =>
      api.post(`/sites/${siteId}/deals/scan`, {})
    );
    setScanning(false);
    if (error) {
      window.alert(rawDetail?.detail || error);
      return;
    }
    load();
  };

  const changeStatus = async (item_id, status) => {
    await apiCall(() => api.post(`/sites/${siteId}/deals/${item_id}/status`, { status }));
    load();
  };

  if (loading) return null;
  const deals = data.deals || [];
  const last = data.last_scan || {};

  return (
    <div
      data-testid="ae-deals-panel"
      className="bg-white p-6 md:p-7 mt-6"
      style={{ border: "1px solid #E5E5E5", borderRadius: "2px" }}
    >
      <div className="flex items-start justify-between gap-6 pb-5 mb-5" style={{ borderBottom: "1px solid #E5E5E5" }}>
        <div>
          <div className="flex items-center gap-3 mb-2">
            <span className="h-px w-8 bg-neutral-900" />
            <span className="text-[10px] uppercase tracking-[0.35em] text-neutral-900 font-medium">
              Deals AliExpress
            </span>
          </div>
          <div
            className="text-[22px] md:text-[26px] text-neutral-900 leading-tight"
            style={{ fontFamily: "'Fraunces', Georgia, serif" }}
          >
            Bonnes affaires détectées cette semaine
          </div>
          <p className="text-[13px] text-neutral-500 mt-1.5 max-w-2xl leading-[1.55]">
            Scan hebdo (mardi 06:00 UTC) des produits AliExpress dans ta niche
            dont le prix a baissé de ≥ 20 % avec ≥ 500 commandes. Ajoute-les
            à ton catalogue en 1 clic.
          </p>
        </div>
        <button
          data-testid="ae-deals-scan"
          onClick={scan}
          disabled={scanning}
          className="shrink-0 h-10 px-5 bg-neutral-900 hover:bg-black disabled:opacity-60 text-white text-[12px] font-semibold tracking-wide flex items-center gap-2"
          style={{ borderRadius: "2px" }}
        >
          <Fire size={14} weight={scanning ? "regular" : "fill"} className={scanning ? "animate-pulse" : ""} />
          {scanning ? "Scan en cours…" : "Scanner maintenant"}
        </button>
      </div>

      {/* Filter tabs */}
      <div className="flex items-center gap-1 mb-5" data-testid="ae-deals-filter">
        {[
          ["new", "Nouveaux"],
          ["imported", "Importés"],
          ["dismissed", "Ignorés"],
        ].map(([k, label]) => (
          <button
            key={k}
            onClick={() => setFilter(k)}
            data-testid={`ae-deals-filter-${k}`}
            className={`h-8 px-3 text-[11px] font-medium uppercase tracking-wider transition ${
              filter === k
                ? "bg-neutral-900 text-white"
                : "bg-neutral-100 text-neutral-600 hover:bg-neutral-200"
            }`}
            style={{ borderRadius: "2px" }}
          >
            {label}
          </button>
        ))}
        {last.last_scan_at && (
          <span className="ml-auto text-[11px] text-neutral-400">
            Dernier scan : {new Date(last.last_scan_at).toLocaleDateString("fr-FR", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}
            {typeof last.last_scan_scanned === "number" && (
              <span> · {last.last_scan_scanned} produits scannés · {last.last_scan_deals || 0} deals</span>
            )}
          </span>
        )}
      </div>

      {/* Deals list */}
      {deals.length === 0 ? (
        <div
          className="p-8 text-center text-[13px] text-neutral-500"
          style={{ background: "#F5F5F5", borderRadius: "2px" }}
        >
          {filter === "new" ? (
            <>Aucun deal actif — lance un scan pour détecter les baisses de prix de la semaine.</>
          ) : filter === "imported" ? (
            <>Aucun deal importé pour l'instant.</>
          ) : (
            <>Aucun deal ignoré.</>
          )}
        </div>
      ) : (
        <ul className="grid grid-cols-1 md:grid-cols-2 gap-4" data-testid="ae-deals-list">
          {deals.map((d) => (
            <li
              key={d.item_id}
              className="flex gap-4 p-4 hover:bg-neutral-50 transition"
              style={{ border: "1px solid #E5E5E5", borderRadius: "2px" }}
              data-testid={`ae-deal-${d.item_id}`}
            >
              <div className="w-24 h-24 shrink-0 overflow-hidden" style={{ background: "#F5F5F5", borderRadius: "2px" }}>
                {d.image ? (
                  <img src={d.image} alt={d.title} className="w-full h-full object-cover" loading="lazy" />
                ) : (
                  <div className="w-full h-full flex items-center justify-center text-neutral-300">
                    <TagSimple size={30} weight="thin" />
                  </div>
                )}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-start justify-between gap-2 mb-1">
                  <span
                    className="inline-flex items-center gap-1 px-2 py-0.5 text-[11px] font-semibold tabular-nums"
                    style={{ background: "#0A0A0A", color: "#fff", borderRadius: "2px" }}
                  >
                    <Fire size={11} weight="fill" /> −{d.drop_pct}%
                  </span>
                  <span className="text-[10px] text-neutral-400 uppercase tracking-wider">{d.orders.toLocaleString()} cmd</span>
                </div>
                <div className="text-[13px] text-neutral-900 line-clamp-2 leading-[1.4] font-medium" title={d.title}>
                  {d.title}
                </div>
                <div className="flex items-baseline gap-2 mt-2">
                  <span
                    className="text-[18px] text-neutral-900 tabular-nums"
                    style={{ fontFamily: "'Fraunces', Georgia, serif" }}
                  >
                    {d.price_eur.toFixed(2).replace(".", ",")} €
                  </span>
                  <span className="text-[12px] text-neutral-400 line-through tabular-nums">
                    {d.previous_price_eur.toFixed(2).replace(".", ",")} €
                  </span>
                </div>
                {filter === "new" && (
                  <div className="flex items-center gap-1 mt-3">
                    {d.item_url && (
                      <a
                        href={d.item_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="h-8 px-3 bg-neutral-100 hover:bg-neutral-200 text-[11px] font-medium tracking-wide flex items-center gap-1.5 text-neutral-700"
                        style={{ borderRadius: "2px" }}
                        data-testid={`ae-deal-open-${d.item_id}`}
                      >
                        <ArrowSquareOut size={11} weight="bold" /> Voir
                      </a>
                    )}
                    <button
                      onClick={() => changeStatus(d.item_id, "imported")}
                      className="h-8 px-3 bg-neutral-900 hover:bg-black text-white text-[11px] font-medium tracking-wide flex items-center gap-1.5"
                      style={{ borderRadius: "2px" }}
                      data-testid={`ae-deal-import-${d.item_id}`}
                    >
                      <DownloadSimple size={11} weight="bold" /> Importé
                    </button>
                    <button
                      onClick={() => changeStatus(d.item_id, "dismissed")}
                      className="h-8 w-8 bg-neutral-100 hover:bg-neutral-200 text-neutral-500 flex items-center justify-center transition"
                      style={{ borderRadius: "2px" }}
                      data-testid={`ae-deal-dismiss-${d.item_id}`}
                      title="Ignorer"
                    >
                      <X size={12} weight="bold" />
                    </button>
                  </div>
                )}
                {filter !== "new" && (
                  <button
                    onClick={() => changeStatus(d.item_id, "new")}
                    className="mt-3 text-[11px] text-neutral-500 hover:text-neutral-900 underline-offset-2 hover:underline"
                  >
                    Remettre dans les nouveaux
                  </button>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
