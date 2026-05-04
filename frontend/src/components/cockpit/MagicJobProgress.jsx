import React, { useEffect, useRef, useState, useCallback } from "react";
import { CheckCircle, CircleNotch, Hourglass, Warning, Sparkle, Rocket, XCircle } from "@phosphor-icons/react";
import { api, apiCall } from "../../lib/api";

/**
 * Phase 3.2 — bouton magique unique + streaming temps réel.
 *
 * Props :
 *   siteId, magicEndpoint (ex: `/sites/{id}/magic/content`),
 *   streamEndpoint, statusEndpoint,
 *   magicButtonLabel (ex: "Générer le contenu SEO complet"),
 *   whenIdleHint (texte à afficher avant le premier clic),
 *   onSuccess(summary) callback,
 *   dryRun (bool) — si true, appelle avec ?dry_run=true
 *
 * États : idle → running (SSE live) → success | error.
 */
export default function MagicJobProgress({
  siteId,
  magicEndpoint,
  streamEndpoint,
  statusEndpoint,
  magicButtonLabel = "Lancer la génération",
  whenIdleHint = "",
  onSuccess,
  dryRun = false,
}) {
  const [state, setState] = useState("idle");   // idle | running | success | error
  const [jobId, setJobId] = useState(null);
  const [steps, setSteps] = useState([]);        // [{key, label, status, counter_current, counter_total, message}]
  const [errorMsg, setErrorMsg] = useState("");
  const [summary, setSummary] = useState(null);
  const [failures, setFailures] = useState([]);  // health-check failures (Step 10)
  const esRef = useRef(null);
  const pollRef = useRef(null);

  // Clean up SSE + polling on unmount
  useEffect(() => () => {
    if (esRef.current) { try { esRef.current.close(); } catch (_) {} }
    if (pollRef.current) { clearInterval(pollRef.current); }
  }, []);

  const applyEvent = useCallback((type, data) => {
    if (type === "init") {
      setSteps(((data && data.steps) || []).map((s) => ({
        ...s, status: "pending", counter_current: 0, message: null,
      })));
    } else if (type === "progress") {
      setSteps((prev) => prev.map((s) => (
        s.key === data.step_key
          ? { ...s,
              status: data.status || s.status,
              counter_current: data.counter_current ?? s.counter_current,
              counter_total: data.counter_total ?? s.counter_total,
              message: data.message ?? s.message }
          : s
      )));
    } else if (type === "done") {
      setSummary(data && data.summary);
      setState("success");
      if (onSuccess) onSuccess(data && data.summary);
      // emit cockpit journey refresh so StepLayout "Continuer" unlocks
      try { window.dispatchEvent(new CustomEvent("cf_steps_changed")); } catch (_) {}
    } else if (type === "error") {
      setErrorMsg((data && data.message) || "Une erreur est survenue");
      if (data && Array.isArray(data.failures)) setFailures(data.failures);
      setState("error");
    }
  }, [onSuccess]);

  const startPolling = useCallback((jid) => {
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      const { data, error } = await apiCall(() => api.get(`${statusEndpoint}?job_id=${jid}`));
      if (error || !data) return;
      setSteps(data.steps || []);
      if (data.status === "success") {
        clearInterval(pollRef.current);
        pollRef.current = null;
        setSummary(data.summary); setState("success");
        if (onSuccess) onSuccess(data.summary);
        try { window.dispatchEvent(new CustomEvent("cf_steps_changed")); } catch (_) {}
      } else if (data.status === "error") {
        clearInterval(pollRef.current); pollRef.current = null;
        setErrorMsg(data.error || "Erreur inconnue"); setState("error");
      }
    }, 1200);
  }, [statusEndpoint, onSuccess]);

  const start = useCallback(async () => {
    setState("running"); setSteps([]); setErrorMsg(""); setSummary(null); setFailures([]);
    const url = `${magicEndpoint}${dryRun ? "?dry_run=true" : ""}`;
    const { data, error } = await apiCall(() => api.post(url));
    if (error || !data || !data.job_id) {
      setErrorMsg(error || "Impossible de lancer le job"); setState("error"); return;
    }
    setJobId(data.job_id);
    // Init steps from response so UI shows rows immediately (even before first SSE event)
    setSteps((data.steps || []).map((s) => ({
      ...s, status: "pending", counter_current: 0, message: null,
    })));

    // Try SSE first — fall back to polling on failure
    try {
      const backend = process.env.REACT_APP_BACKEND_URL || "";
      const streamUrl = `${backend}/api${streamEndpoint}?job_id=${data.job_id}`;
      const es = new EventSource(streamUrl, { withCredentials: true });
      esRef.current = es;
      const handler = (type) => (e) => {
        try {
          const d = e.data ? JSON.parse(e.data) : {};
          applyEvent(type, d);
        } catch (_) {}
      };
      es.addEventListener("init", handler("init"));
      es.addEventListener("progress", handler("progress"));
      es.addEventListener("done", handler("done"));
      es.addEventListener("error", handler("error"));
      es.addEventListener("end", () => { try { es.close(); } catch (_) {} });
      es.onerror = () => { try { es.close(); } catch (_) {} startPolling(data.job_id); };
    } catch (_) {
      startPolling(data.job_id);
    }
  }, [magicEndpoint, streamEndpoint, dryRun, applyEvent, startPolling]);

  const retry = () => { setState("idle"); setSteps([]); setErrorMsg(""); setFailures([]); };

  return (
    <div className="max-w-3xl mx-auto">
      {state === "idle" && (
        <div className="py-16 text-center" data-testid="magic-idle">
          {whenIdleHint && (
            <p className="text-sm text-neutral-600 mb-6 max-w-xl mx-auto">{whenIdleHint}</p>
          )}
          <button
            onClick={start}
            data-testid="magic-start-btn"
            className="inline-flex items-center gap-2 h-14 px-8 rounded-2xl bg-neutral-900 hover:bg-neutral-800 text-white font-medium text-base shadow-sm transition"
          >
            <Sparkle size={18} weight="fill" />
            {magicButtonLabel}
          </button>
        </div>
      )}

      {(state === "running" || state === "success" || state === "error") && (
        <div className="bg-white border border-neutral-200 rounded-2xl p-6" data-testid="magic-progress">
          <div className="space-y-2">
            {steps.map((s) => {
              const isRunning = s.status === "running";
              const isDone = s.status === "done";
              const isWarn = s.status === "warn";
              const isFail = s.status === "fail";
              const isSkip = s.status === "skipped";
              const Icon = isDone ? CheckCircle
                          : isRunning ? CircleNotch
                          : isFail ? XCircle
                          : isWarn ? Warning
                          : Hourglass;
              const iconCls = isDone ? "text-emerald-600"
                            : isRunning ? "text-neutral-900 animate-spin"
                            : isFail ? "text-rose-600"
                            : isWarn ? "text-amber-600"
                            : isSkip ? "text-neutral-300"
                            : "text-neutral-300";
              return (
                <div
                  key={s.key}
                  className={`flex items-start gap-3 py-2 px-3 rounded-lg ${isRunning ? "bg-neutral-50" : ""}`}
                  data-testid={`magic-step-${s.key}`}
                  data-status={s.status}
                >
                  <Icon size={18} weight={isDone || isFail ? "fill" : "regular"} className={`${iconCls} flex-shrink-0 mt-0.5`} />
                  <div className="flex-1 min-w-0">
                    <div className={`text-sm ${isDone ? "text-neutral-500" : isSkip ? "text-neutral-400 line-through" : "text-neutral-900"}`}>
                      {s.label}
                      {s.counter_total && (
                        <span className="ml-2 text-xs text-neutral-500 font-mono">
                          {s.counter_current || 0}/{s.counter_total}
                        </span>
                      )}
                    </div>
                    {s.message && (
                      <div className={`text-xs mt-0.5 ${isFail ? "text-rose-600" : "text-neutral-500"}`}>{s.message}</div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {state === "success" && (
            <div className="mt-5 rounded-xl bg-emerald-50 border border-emerald-200 p-4 flex items-center gap-3" data-testid="magic-success">
              <Rocket size={20} weight="fill" className="text-emerald-700" />
              <div className="text-sm text-emerald-900">
                {summary?.message || "Génération terminée"}
                {summary?.public_url && (
                  <a href={summary.public_url} target="_blank" rel="noreferrer" className="ml-2 underline">
                    Voir le site
                  </a>
                )}
              </div>
            </div>
          )}

          {state === "error" && (
            <div className="mt-5 rounded-xl bg-rose-50 border border-rose-200 p-4" data-testid="magic-error">
              <div className="flex items-center gap-2 text-sm text-rose-900 font-medium">
                <Warning size={18} weight="fill" /> {errorMsg}
              </div>
              {failures.length > 0 && (
                <ul className="mt-3 space-y-1.5 text-sm text-rose-900">
                  {failures.map((f) => (
                    <li key={f.key} className="flex items-start gap-2">
                      <XCircle size={14} weight="fill" className="text-rose-600 mt-0.5" />
                      <span className="flex-1">
                        <strong>{f.label}</strong> — {f.message}
                        {f.remediation && (
                          <a href={`/sites/${siteId}/${f.remediation.cockpit_step === "import" ? "aliexpress/import" : f.remediation.cockpit_step}`}
                             className="ml-2 text-rose-700 underline">
                            → {f.remediation.label}
                          </a>
                        )}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
              <button
                onClick={retry}
                className="mt-4 h-10 px-4 rounded-lg bg-white border border-rose-300 text-rose-700 text-sm font-medium hover:bg-rose-100"
                data-testid="magic-retry-btn"
              >
                Réessayer
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
