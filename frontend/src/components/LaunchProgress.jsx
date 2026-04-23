import React, { useEffect, useState } from "react";
import { Rocket, CheckCircle, ArrowClockwise, XCircle, Sparkle } from "@phosphor-icons/react";
import { api, apiCall } from "../lib/api";

const POLL_INTERVAL_MS = 2500;

export default function LaunchProgress({ siteId, jobId, onDone, onFailed }) {
  const [job, setJob] = useState(null);
  const [history, setHistory] = useState([]); // list of labels we've seen

  useEffect(() => {
    let cancelled = false;
    let timer = null;
    const tick = async () => {
      if (cancelled) return;
      const { data } = await apiCall(() =>
        api.get(`/sites/${siteId}/design/launch-status${jobId ? `?job_id=${jobId}` : ""}`)
      );
      if (cancelled) return;
      if (!data) return;
      setJob(data);
      if (data.current_label && !history.includes(data.current_label)) {
        setHistory((prev) => [...prev, data.current_label]);
      }
      if (data.status === "completed") {
        timer = setTimeout(() => !cancelled && onDone?.(), 1200);
      } else if (data.status === "failed") {
        timer = setTimeout(() => !cancelled && onFailed?.(data.error), 1200);
      } else {
        timer = setTimeout(tick, POLL_INTERVAL_MS);
      }
    };
    tick();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [siteId, jobId]);

  const pct = Math.max(1, Math.min(100, job?.progress_pct || 1));
  const status = job?.status || "running";
  const label = job?.current_label || "Démarrage de l'orchestration…";

  return (
    <div
      className="fixed inset-0 z-[100] bg-gradient-to-br from-neutral-950 via-violet-950 to-indigo-950 text-white flex items-center justify-center p-6"
      data-testid="launch-progress"
    >
      <div className="max-w-xl w-full">
        {/* Icon */}
        <div className="flex items-center justify-center mb-8">
          <div className="w-20 h-20 rounded-2xl bg-white/10 backdrop-blur-xl flex items-center justify-center shadow-2xl">
            {status === "completed" ? (
              <CheckCircle size={40} weight="fill" className="text-emerald-400" />
            ) : status === "failed" ? (
              <XCircle size={40} weight="fill" className="text-red-400" />
            ) : (
              <Rocket size={40} weight="fill" className="text-violet-300 animate-pulse" />
            )}
          </div>
        </div>

        {/* Title */}
        <div className="text-center mb-2">
          <div className="text-[11px] uppercase tracking-[0.3em] text-violet-300 mb-2">
            {status === "completed" ? "Génération terminée"
              : status === "failed" ? "Erreur de génération"
              : "Génération en cours"}
          </div>
          <h1 className="text-3xl md:text-4xl font-semibold leading-tight">
            {status === "completed" ? "Ta boutique est prête."
              : status === "failed" ? "Quelque chose s'est mal passé."
              : "L'IA façonne ton site sur-mesure"}
          </h1>
        </div>

        {/* Progress bar */}
        <div className="mt-8">
          <div className="flex items-center justify-between text-xs text-violet-200 mb-2">
            <span>{label}</span>
            <span className="font-mono">{pct}%</span>
          </div>
          <div className="h-3 rounded-full bg-white/10 overflow-hidden" data-testid="launch-progress-bar">
            <div
              className={`h-full transition-all duration-500 ${
                status === "failed" ? "bg-red-400"
                : status === "completed" ? "bg-emerald-400"
                : "bg-gradient-to-r from-violet-400 via-fuchsia-400 to-indigo-400"
              }`}
              style={{ width: `${pct}%` }}
            />
          </div>
        </div>

        {/* History log */}
        {status !== "failed" && (
          <div className="mt-8 bg-white/5 backdrop-blur-xl rounded-xl border border-white/10 p-4 max-h-[40vh] overflow-y-auto">
            <div className="text-[10px] uppercase tracking-widest text-violet-300 mb-2">
              Journal
            </div>
            <ul className="space-y-1.5 text-sm text-violet-100">
              {history.map((h, i) => (
                <li key={i} className="flex items-center gap-2">
                  {i < history.length - 1 || status === "completed" ? (
                    <CheckCircle size={14} weight="fill" className="text-emerald-400 shrink-0" />
                  ) : (
                    <Sparkle size={14} className="text-fuchsia-300 animate-pulse shrink-0" />
                  )}
                  <span className={i < history.length - 1 ? "opacity-70" : ""}>{h}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Error */}
        {status === "failed" && (
          <div className="mt-6 p-4 rounded-xl bg-red-500/20 border border-red-400/40 text-sm text-red-100">
            <strong className="font-semibold">Détail :</strong> {job?.error || "Erreur inconnue."}
            <div className="mt-2 text-xs text-red-200/80">
              Tu peux relancer depuis le Wizard ou passer en mode avancé pour corriger manuellement.
            </div>
          </div>
        )}

        {/* Loading hint */}
        {status === "running" && (
          <div className="mt-6 text-center text-xs text-violet-300/70">
            ⏱️ Temps estimé : 3-10 min selon le catalogue. Ne ferme pas cette page.
          </div>
        )}
      </div>
    </div>
  );
}
