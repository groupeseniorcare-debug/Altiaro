import React, { useEffect, useState, useRef } from "react";
import {
  Rocket, CheckCircle, ArrowClockwise, XCircle, Sparkle, Warning, Heartbeat, Clock,
} from "@phosphor-icons/react";
import { api, apiCall } from "../lib/api";

const POLL_INTERVAL_MS = 2500;

/**
 * LaunchProgress — plein écran premium pendant la génération IA de la boutique.
 *
 * UX zéro friction :
 *  - phase_label lisible par phase (pas de jargon technique)
 *  - compteur temps écoulé + âge du dernier heartbeat
 *  - micro-étape : "Image 4/8 · Produit 2 sur 9"
 *  - détection stale (heartbeat > 3 min) avec bouton "Relancer la génération"
 *  - style Luxury Minimal (ivoire, Cormorant Garamond)
 */
export default function LaunchProgress({ siteId, jobId, onDone, onFailed, onAbort }) {
  const [job, setJob] = useState(null);
  const [history, setHistory] = useState([]);
  const [llmHealth, setLlmHealth] = useState(null);
  const [resuming, setResuming] = useState(false);
  const [restarting, setRestarting] = useState(false);
  const seenLabels = useRef(new Set());

  // ─── Polling du job ──────────────────────────────────────────
  useEffect(() => {
    let cancelled = false;
    let timer = null;
    const tick = async () => {
      if (cancelled) return;
      const { data } = await apiCall(() =>
        api.get(`/sites/${siteId}/design/launch-status${jobId ? `?job_id=${jobId}` : ""}`),
      );
      if (cancelled) return;
      if (!data) return;
      setJob(data);

      // Journal : phase_label + current_item_label (dédupliqué)
      const nextEntries = [];
      if (data.phase_label && !seenLabels.current.has(data.phase_label)) {
        seenLabels.current.add(data.phase_label);
        nextEntries.push(data.phase_label);
      }
      if (data.current_item_label && !seenLabels.current.has(data.current_item_label)) {
        seenLabels.current.add(data.current_item_label);
        nextEntries.push(data.current_item_label);
      }
      if (nextEntries.length > 0) setHistory((p) => [...p, ...nextEntries]);

      const st = data.status;
      if (st === "completed") {
        timer = setTimeout(() => !cancelled && onDone?.(), 1200);
      } else if (st === "completed_with_degraded") {
        // l'utilisateur doit cliquer "Continuer"
      } else if (st === "failed" && !data.resumable) {
        timer = setTimeout(() => !cancelled && onFailed?.(data.error), 1800);
      } else {
        timer = setTimeout(tick, POLL_INTERVAL_MS);
      }
    };
    tick();
    return () => { cancelled = true; if (timer) clearTimeout(timer); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [siteId, jobId]);

  // ─── Polling LLM health ──────────────────────────────────────
  useEffect(() => {
    let cancelled = false;
    const poll = async () => {
      const { data } = await apiCall(() => api.get(`/platform/llm-health`));
      if (!cancelled && data) setLlmHealth(data);
      if (!cancelled) setTimeout(poll, 30000);
    };
    poll();
    return () => { cancelled = true; };
  }, []);

  const handleResume = async () => {
    if (!job?.id || resuming) return;
    setResuming(true);
    try {
      const { error } = await apiCall(() =>
        api.post(`/sites/${siteId}/design/launch-jobs/${job.id}/resume`),
      );
      if (error) window.alert(`Reprise impossible : ${error}`);
    } finally { setResuming(false); }
  };

  const handleRestart = async () => {
    if (restarting) return;
    setRestarting(true);
    try {
      const { error } = await apiCall(() =>
        api.post(`/sites/${siteId}/design/launch-restart`),
      );
      if (error) {
        window.alert(`Relance impossible : ${error}`);
      } else {
        // Reset local
        seenLabels.current = new Set();
        setHistory([]);
        setJob(null);
      }
    } finally { setRestarting(false); }
  };

  const pct = Math.max(1, Math.min(100, Number(job?.progress_pct ?? job?.progress ?? 1)));
  const status = job?.status || "running";
  const phaseLabel = job?.phase_label || "Démarrage de la génération…";
  const phaseRange = job?.phase_range || { min: 0, max: 100 };
  const phaseIndex = (() => {
    const phases = [10, 25, 55, 75, 90, 100];
    return phases.findIndex((hi) => pct < hi) + 1 || phases.length;
  })();
  const itemsDone = job?.items_done;
  const itemsTotal = job?.items_total;
  const currentItem = job?.current_item_label;
  const elapsedS = Number(job?.elapsed_seconds || 0);
  const hbAge = job?.last_heartbeat_age_seconds;
  const isStale = !!job?.is_stale;
  const degradedSteps = job?.degraded_steps || [];
  const isResumable = job?.resumable === true;
  const completedWithDegraded = status === "completed_with_degraded";

  const fmtDuration = (s) => {
    if (!s || s < 0) return "—";
    const m = Math.floor(s / 60);
    const sec = Math.floor(s % 60);
    if (m === 0) return `${sec}s`;
    return `${m}m ${String(sec).padStart(2, "0")}s`;
  };

  // Estimation temps restant : règle de 3 sur la progression observée
  const etaS = (() => {
    if (pct <= 1 || elapsedS < 8 || status !== "running") return null;
    return Math.round((elapsedS / pct) * (100 - pct));
  })();

  const llmPill = (() => {
    if (!llmHealth) return null;
    const overall = llmHealth?.overall;
    const claudeState = llmHealth?.breakers?.claude?.state;
    const recent60 = llmHealth?.breakers?.claude?.recent_failures_60s || 0;
    if (claudeState === "OPEN" || overall === "down")
      return { label: "Service IA en panne — reprise auto active", color: "bg-rose-100 border-rose-200 text-rose-800" };
    if (claudeState === "HALF_OPEN" || overall === "degraded" || recent60 >= 3)
      return { label: `IA ralentie (${recent60} reprises sur 60 s)`, color: "bg-amber-100 border-amber-200 text-amber-800" };
    return { label: "IA opérationnelle", color: "bg-emerald-100 border-emerald-200 text-emerald-800" };
  })();

  const degradedLabel = (key) => ({
    testimonials_premium: "Témoignages premium (3 portraits IA)",
    cms_pages: "Pages éditoriales (À propos, Contact)",
    "content-hero": "Hero de la home",
    "content-benefits": "Bénéfices & réassurance",
    "content-testimonials": "Témoignages home",
    "content-faq": "FAQ optimisée",
    "content-about": "Page À propos",
    "content-contact": "Page Contact",
    navigation: "Mega menu de navigation",
    "hero-image": "Image hero IA",
    collections: "Collections IA",
  }[key] || key);

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center p-6 overflow-y-auto"
      style={{ background: "#F5F2EB" }}
      data-testid="launch-progress"
    >
      <div className="max-w-xl w-full">
        {/* Bandeau santé IA + Job ID */}
        <div className="flex items-center justify-between mb-6 gap-3">
          {llmPill ? (
            <div
              className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10.5px] font-semibold uppercase tracking-wider border ${llmPill.color}`}
              data-testid="launch-llm-health-pill"
            >
              <Heartbeat size={11} weight="fill" />
              {llmPill.label}
            </div>
          ) : <div />}
          {job?.id && (
            <div className="text-[10px] uppercase tracking-[0.25em] text-neutral-500 font-mono">
              job {job.id.slice(0, 8)}
            </div>
          )}
        </div>

        {/* Icône */}
        <div className="flex items-center justify-center mb-6">
          <div className="w-16 h-16 rounded-2xl bg-white border border-[#E8E2D5] flex items-center justify-center shadow-sm">
            {status === "completed" ? (
              <CheckCircle size={32} weight="fill" className="text-emerald-600" />
            ) : completedWithDegraded ? (
              <Warning size={32} weight="fill" className="text-amber-600" />
            ) : status === "failed" ? (
              <XCircle size={32} weight="fill" className="text-rose-600" />
            ) : (
              <Rocket size={32} weight="duotone" className="text-neutral-800" />
            )}
          </div>
        </div>

        {/* Titre */}
        <div className="text-center mb-4">
          <div className="text-[10.5px] uppercase tracking-[0.3em] text-neutral-500 mb-3">
            {status === "completed" ? "Génération terminée"
              : completedWithDegraded ? `Site prêt · ${degradedSteps.length} élément(s) en mode standard`
              : status === "failed" ? "Erreur de génération"
              : `Phase ${phaseIndex} sur 6 · ${phaseRange.min}–${phaseRange.max}%`}
          </div>
          <h1
            className="text-[34px] md:text-[40px] leading-[1.1] tracking-[-0.01em] text-neutral-900"
            style={{ fontFamily: "'Cormorant Garamond','Cormorant',Georgia,serif", fontWeight: 500 }}
          >
            {status === "completed" ? "Votre boutique est prête."
              : completedWithDegraded ? "Votre boutique est en ligne."
              : status === "failed" ? "La génération a été interrompue."
              : phaseLabel}
          </h1>
          {status === "running" && currentItem && (
            <p className="text-[13.5px] text-neutral-600 mt-2.5" data-testid="launch-current-item">
              {currentItem}
              {typeof itemsDone === "number" && typeof itemsTotal === "number" && itemsTotal > 0 && (
                <span className="text-neutral-400"> · {itemsDone}/{itemsTotal}</span>
              )}
            </p>
          )}
        </div>

        {/* Barre de progression */}
        <div className="mt-6">
          <div className="flex items-center justify-between text-[11px] text-neutral-500 mb-2 tabular-nums">
            <span className="uppercase tracking-wider">{phaseLabel}</span>
            <span className="font-mono">{pct}%</span>
          </div>
          <div className="h-2.5 rounded-full bg-[#E8E2D5] overflow-hidden" data-testid="launch-progress-bar">
            <div
              className={`h-full transition-all duration-500 ${
                status === "failed" ? "bg-rose-500"
                  : completedWithDegraded ? "bg-amber-500"
                  : status === "completed" ? "bg-emerald-600"
                  : "bg-neutral-900"
              }`}
              style={{ width: `${pct}%` }}
            />
          </div>

          {/* Temps écoulé + ETA + fraîcheur heartbeat */}
          <div className="mt-3 flex items-center gap-4 text-[11.5px] text-neutral-500 tabular-nums">
            <span className="flex items-center gap-1.5">
              <Clock size={12} weight="duotone" /> {fmtDuration(elapsedS)} écoulées
            </span>
            {etaS != null && (
              <span className="text-neutral-400">~ {fmtDuration(etaS)} restantes</span>
            )}
            {status === "running" && hbAge != null && (
              <span
                className={`ml-auto text-[10px] uppercase tracking-wider ${
                  hbAge > 60 ? "text-amber-700" : "text-neutral-400"
                }`}
              >
                IA active il y a {hbAge}s
              </span>
            )}
          </div>
        </div>

        {/* Journal des phases */}
        {status !== "failed" && history.length > 0 && (
          <div className="mt-6 bg-white rounded-xl border border-[#E8E2D5] p-4 max-h-[32vh] overflow-y-auto">
            <div className="text-[9.5px] uppercase tracking-[0.3em] text-neutral-500 mb-3">
              Journal
            </div>
            <ul className="space-y-2 text-[13px] text-neutral-700">
              {history.map((h, i) => {
                const isLast = i === history.length - 1 && status === "running";
                return (
                  <li key={i} className="flex items-start gap-2">
                    {isLast ? (
                      <Sparkle size={14} className="text-neutral-900 animate-pulse mt-0.5 flex-shrink-0" />
                    ) : (
                      <CheckCircle size={14} weight="fill" className="text-emerald-600 mt-0.5 flex-shrink-0" />
                    )}
                    <span className={isLast ? "text-neutral-900" : "text-neutral-500"}>{h}</span>
                  </li>
                );
              })}
            </ul>
          </div>
        )}

        {/* Bandeau STALE — job bloqué > 3 min */}
        {status === "running" && isStale && (
          <div
            className="mt-6 p-4 rounded-xl bg-amber-50 border border-amber-200"
            data-testid="launch-stale-warning"
          >
            <div className="text-sm font-semibold text-amber-900 mb-1 flex items-center gap-1.5">
              <Warning size={14} weight="fill" /> Le traitement semble stoppé
            </div>
            <div className="text-[12.5px] text-amber-800 mb-3 leading-relaxed">
              Aucune activité détectée depuis {Math.floor((hbAge || 180) / 60)} minute(s).
              Vous pouvez relancer la génération depuis le début en toute sécurité —
              les étapes précédentes validées seront conservées.
            </div>
            <div className="flex gap-2">
              <button
                onClick={handleRestart}
                disabled={restarting}
                data-testid="launch-restart-button"
                className="h-9 px-4 rounded-lg bg-neutral-900 hover:bg-neutral-800 text-white text-[12px] font-semibold inline-flex items-center gap-1.5 disabled:opacity-60"
              >
                <ArrowClockwise size={12} weight="bold" />
                {restarting ? "Relance en cours…" : "Relancer la génération"}
              </button>
              <button
                onClick={() => onAbort?.()}
                className="h-9 px-4 rounded-lg bg-white border border-neutral-300 hover:border-neutral-400 text-neutral-700 text-[12px] font-medium"
              >
                Fermer
              </button>
            </div>
          </div>
        )}

        {/* Étapes dégradées */}
        {degradedSteps.length > 0 && (
          <div
            className="mt-6 p-4 rounded-xl bg-amber-50 border border-amber-200"
            data-testid="launch-degraded-steps-list"
          >
            <div className="flex items-center gap-2 text-amber-900 font-semibold mb-2 text-[13px]">
              <Warning size={14} weight="fill" />
              {degradedSteps.length} élément{degradedSteps.length > 1 ? "s" : ""} en mode standard
            </div>
            <ul className="space-y-1.5 text-[12px] text-amber-800 mb-3">
              {degradedSteps.map((d, i) => (
                <li key={i} className="flex items-start gap-2">
                  <span className="inline-block w-1.5 h-1.5 rounded-full bg-amber-500 mt-1.5 flex-shrink-0" />
                  <span>
                    <strong className="text-amber-900">{degradedLabel(d.step)}</strong>
                    <span className="text-amber-700"> — {d.reason || "non disponible"}</span>
                  </span>
                </li>
              ))}
            </ul>
            {(completedWithDegraded || isResumable) && (
              <button
                onClick={handleResume}
                disabled={resuming}
                data-testid="launch-resume-degraded-button"
                className="h-9 px-4 rounded-lg bg-neutral-900 hover:bg-neutral-800 text-white text-[12px] font-semibold inline-flex items-center gap-1.5 disabled:opacity-60"
              >
                <ArrowClockwise size={12} weight="bold" />
                {resuming ? "Reprise…" : "Relancer les éléments dégradés"}
              </button>
            )}
          </div>
        )}

        {/* Continuer vers la boutique (mode degraded) */}
        {completedWithDegraded && (
          <div className="mt-4 flex justify-center">
            <button
              onClick={() => onDone?.()}
              data-testid="launch-continue-with-degraded"
              className="h-10 px-5 rounded-lg bg-neutral-900 hover:bg-neutral-800 text-white text-[13px] font-semibold"
            >
              Continuer vers la boutique
            </button>
          </div>
        )}

        {/* Erreur */}
        {status === "failed" && (
          <div className="mt-6 p-4 rounded-xl bg-rose-50 border border-rose-200 text-[13px] text-rose-900">
            <div className="font-semibold mb-1">Détail : {job?.error || "Erreur inconnue."}</div>
            <div className="text-[12px] text-rose-800/80 mb-3">
              {isResumable
                ? "Le système peut reprendre la génération à partir du dernier point d'avancement."
                : "Vous pouvez relancer une génération propre depuis zéro."}
            </div>
            <div className="flex gap-2">
              {isResumable && (
                <button
                  onClick={handleResume}
                  disabled={resuming}
                  data-testid="launch-resume-button"
                  className="h-9 px-4 rounded-lg bg-neutral-900 hover:bg-neutral-800 text-white text-[12px] font-semibold inline-flex items-center gap-1.5 disabled:opacity-60"
                >
                  <ArrowClockwise size={12} weight="bold" />
                  {resuming ? "Reprise…" : "Reprendre la génération"}
                </button>
              )}
              <button
                onClick={handleRestart}
                disabled={restarting}
                data-testid="launch-restart-after-fail"
                className="h-9 px-4 rounded-lg bg-white border border-neutral-300 hover:border-neutral-400 text-neutral-800 text-[12px] font-semibold inline-flex items-center gap-1.5 disabled:opacity-60"
              >
                <ArrowClockwise size={12} weight="bold" />
                {restarting ? "Relance…" : "Tout relancer depuis zéro"}
              </button>
              <button
                onClick={() => onFailed?.(job?.error)}
                className="h-9 px-4 rounded-lg bg-transparent hover:bg-neutral-100 text-neutral-700 text-[12px] font-medium"
              >
                Fermer
              </button>
            </div>
          </div>
        )}

        {/* Conseil pendant la génération */}
        {status === "running" && !isStale && (
          <div className="mt-6 text-center text-[11.5px] text-neutral-500">
            Temps total estimé : 3 à 10 min selon votre catalogue. Laissez cette fenêtre ouverte.
          </div>
        )}
      </div>
    </div>
  );
}
