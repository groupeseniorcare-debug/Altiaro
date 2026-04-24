import React, { useEffect, useState } from "react";
import { api, apiCall } from "../lib/api";
import { Microphone, CheckCircle, XCircle, Sparkle } from "@phosphor-icons/react";

/**
 * AI Citation Tracker — mesure hebdomadaire combien de fois la marque est
 * citée par un panel IA (Claude) sur les questions AEO du site.
 */
export default function CitationTrackerPanel({ siteId }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);

  const load = async () => {
    const { data: res } = await apiCall(() =>
      api.get(`/sites/${siteId}/citation-tracker`)
    );
    setData(res || { last_run: null, history: [] });
    setLoading(false);
  };

  useEffect(() => { load(); }, [siteId]);

  const runNow = async () => {
    if (!window.confirm(
      "Lancer une mesure de citation IA ?\n\n" +
      "• 6 questions testées par Claude (panel IA)\n" +
      "• Mesure si la marque est mentionnée dans la réponse\n" +
      "• Coût : ~0,10 € LLM · Durée : ~45 s"
    )) return;
    setRunning(true);
    const { data: res, error, rawDetail } = await apiCall(() =>
      api.post(`/sites/${siteId}/citation-tracker/run`, { max_questions: 6 })
    );
    setRunning(false);
    if (error) {
      window.alert(rawDetail?.detail || error);
      return;
    }
    if (res?.status === "failed") {
      window.alert(res.error || "Mesure échouée");
      return;
    }
    if (res?.status === "noop") {
      window.alert(res.message);
      return;
    }
    load();
  };

  if (loading || !data) return null;
  const last = data.last_run;
  const history = data.history || [];

  // Build sparkline
  const points = history.map((h, i) => ({ x: i, y: h.rate }));
  const maxX = Math.max(points.length - 1, 1);
  const sparkline = points.map((p) => {
    const x = (p.x / maxX) * 100;
    const y = 100 - p.y; // invert so higher rate = higher visually
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(" ");

  return (
    <div
      data-testid="citation-tracker-panel"
      className="p-6 md:p-7"
      style={{ borderTop: "1px solid #E5E5E5" }}
    >
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_1.4fr] gap-10">
        {/* Left — current rate + CTA */}
        <div>
          <div className="flex items-center gap-3 mb-3">
            <span className="h-px w-8 bg-neutral-900" />
            <span className="text-[10px] uppercase tracking-[0.35em] text-neutral-900 font-medium">
              Citation Tracker IA
            </span>
          </div>
          <div className="flex items-baseline gap-2">
            <div
              className="text-[52px] leading-none text-neutral-900 tabular-nums"
              style={{ fontFamily: "'Fraunces', Georgia, serif" }}
            >
              {last ? `${last.rate}` : "—"}
            </div>
            {last && <div className="text-[12px] text-neutral-500">%</div>}
          </div>
          <p className="text-[13px] text-neutral-600 mt-3 leading-[1.55] max-w-sm">
            Pourcentage de réponses IA (panel Claude) qui citent votre marque
            sur les questions AEO de vos produits. Objectif : ≥ 30 % à 3 mois,
            ≥ 60 % à 12 mois.
          </p>

          {/* Sparkline */}
          {history.length >= 2 && (
            <div className="mt-5" data-testid="citation-sparkline">
              <div className="text-[10px] uppercase tracking-[0.3em] text-neutral-500 mb-2">
                Historique ({history.length} semaines)
              </div>
              <svg viewBox="0 0 100 100" className="w-full h-16" preserveAspectRatio="none">
                <polyline
                  points={sparkline}
                  fill="none"
                  stroke="#0A0A0A"
                  strokeWidth="1.5"
                  vectorEffect="non-scaling-stroke"
                />
                {points.map((p, i) => (
                  <circle
                    key={i}
                    cx={(p.x / maxX) * 100}
                    cy={100 - p.y}
                    r="1.2"
                    fill="#0A0A0A"
                  />
                ))}
              </svg>
            </div>
          )}

          <button
            onClick={runNow}
            disabled={running}
            data-testid="citation-tracker-run"
            className="mt-6 h-11 px-5 bg-neutral-900 hover:bg-black disabled:opacity-60 text-white text-[12.5px] font-semibold flex items-center gap-2 transition"
            style={{ borderRadius: "2px" }}
          >
            <Microphone size={14} weight="fill" className={running ? "animate-pulse" : ""} />
            {running ? "Mesure en cours (45 s)…" : "Mesurer maintenant"}
            {!running && <Sparkle size={13} weight="fill" />}
          </button>
          {last?.at && (
            <div className="mt-3 text-[11px] text-neutral-400">
              Dernière mesure : {new Date(last.at).toLocaleDateString("fr-FR", { day: "numeric", month: "long", year: "numeric" })}
            </div>
          )}
        </div>

        {/* Right — detail per question */}
        <div>
          <div className="text-[10px] uppercase tracking-[0.35em] text-neutral-500 mb-4">
            Résultats détaillés
          </div>
          {last && last.results ? (
            <ul className="space-y-3" data-testid="citation-tracker-results">
              {last.results.slice(0, 6).map((r, i) => (
                <li key={i} className="flex items-start gap-3">
                  {r.cited ? (
                    <CheckCircle size={16} weight="fill" className="text-emerald-600 shrink-0 mt-[3px]" />
                  ) : (
                    <XCircle size={16} weight="regular" className="text-neutral-300 shrink-0 mt-[3px]" />
                  )}
                  <div className="min-w-0 flex-1">
                    <div className={`text-[13px] leading-[1.45] ${r.cited ? "text-neutral-900 font-medium" : "text-neutral-600"}`}>
                      {r.question}
                    </div>
                    {r.answer && (
                      <div className="text-[11.5px] text-neutral-500 mt-1 line-clamp-2 leading-[1.4]">
                        {r.answer}
                      </div>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          ) : (
            <div
              className="p-5 text-[12.5px] text-neutral-600 leading-[1.6]"
              style={{ background: "#F5F5F5", borderRadius: "2px" }}
            >
              Aucune mesure encore effectuée. Lance un premier run pour établir
              le baseline — puis reviens chaque semaine pour voir la progression
              au fur et à mesure que tes contenus AEO sont absorbés par les
              moteurs IA.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
