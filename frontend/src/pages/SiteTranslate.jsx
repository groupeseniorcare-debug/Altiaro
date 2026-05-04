import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { CheckCircle, Translate, ArrowsClockwise, Warning } from "@phosphor-icons/react";
import { api, apiCall } from "../lib/api";
import StepLayout from "../components/cockpit/StepLayout";

const FLAGS = { fr: "🇫🇷", en: "🇬🇧", de: "🇩🇪", nl: "🇳🇱", it: "🇮🇹", es: "🇪🇸" };

export default function SiteTranslate() {
  const { id: siteId } = useParams();
  const [state, setState] = useState(null);
  const [loading, setLoading] = useState(true);
  const [task, setTask] = useState(null);
  const [pickedLangs, setPickedLangs] = useState([]);
  const [overwrite, setOverwrite] = useState(false);
  const [running, setRunning] = useState(false);

  const loadState = async () => {
    setLoading(true);
    const { data } = await apiCall(() => api.get(`/sites/${siteId}/translate/state`));
    setState(data);
    setLoading(false);
  };
  useEffect(() => { loadState(); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, [siteId]);

  const togglePick = (lang) => {
    setPickedLangs((prev) =>
      prev.includes(lang) ? prev.filter((l) => l !== lang) : [...prev, lang]
    );
  };

  const startTranslate = async () => {
    if (!pickedLangs.length) return;
    setRunning(true);
    setTask(null);
    const { data, error } = await apiCall(() =>
      api.post(`/sites/${siteId}/translate`, { target_langs: pickedLangs, overwrite })
    );
    if (error) { setRunning(false); alert(error); return; }
    const { task_id } = data;
    let notFoundStreak = 0;
    const poll = async () => {
      const { data: st, status } = await apiCall(() =>
        api.get(`/sites/${siteId}/translate/status?task_id=${task_id}`)
      );
      if (status === 404 || (!st && !status)) {
        notFoundStreak += 1;
        if (notFoundStreak >= 3) {
          setRunning(false);
          setTask({ status: "failed", error: "Tâche introuvable (serveur redémarré ?)" });
          return;
        }
        setTimeout(poll, 5000);
        return;
      }
      notFoundStreak = 0;
      setTask(st);
      if (st && (st.status === "completed" || st.status === "failed")) {
        setRunning(false);
        await loadState();
        window.dispatchEvent(new CustomEvent("cf_steps_changed"));
        return;
      }
      setTimeout(poll, 5000);
    };
    poll();
  };

  if (loading || !state) {
    return (
      <div className="min-h-screen bg-[#F5F2EB] flex items-center justify-center">
        <div className="text-sm text-neutral-500">Chargement…</div>
      </div>
    );
  }

  const { primary_lang, available_langs = [], supported_langs = [], lang_labels = {}, counts = {} } = state;

  return (
    <StepLayout
      siteId={siteId}
      stepKey="translate"
      title="Traduction multilingue"
      subtitle={`Le site est rédigé en ${FLAGS[primary_lang] || ""} ${lang_labels[primary_lang] || primary_lang}. Sélectionne les langues à ajouter.`}
      estimatedTime="~2 min/langue"
      whatItDoes="Claude Sonnet traduit brand, sections homepage, fiches produits, articles blog et SEO meta dans chaque langue cible. Idempotent : les langues déjà traduites sont skippées sauf overwrite. Coût ~0,5-1 $ par langue."
      magicButton={{
        label: running
          ? `Traduction… ${task?.spent_usd ? `(${task.spent_usd.toFixed(2)} $)` : ""}`
          : pickedLangs.length
          ? `Traduire ${pickedLangs.length} langue(s)`
          : "Sélectionne ≥ 1 langue",
        onClick: startTranslate,
        loading: running,
        disabled: !pickedLangs.length || running,
        icon: <Translate size={14} weight="bold" />,
      }}
    >
      <div className="bg-white rounded-2xl border border-neutral-200 p-5 mb-6 text-sm text-neutral-600 grid grid-cols-3 gap-4">
        <div><div className="uppercase text-[10px] tracking-widest text-neutral-400">Produits</div><div className="text-2xl font-light text-neutral-900 mt-1">{counts.products}</div></div>
        <div><div className="uppercase text-[10px] tracking-widest text-neutral-400">Articles blog</div><div className="text-2xl font-light text-neutral-900 mt-1">{counts.blog_posts}</div></div>
        <div><div className="uppercase text-[10px] tracking-widest text-neutral-400">Langues</div><div className="text-2xl font-light text-neutral-900 mt-1">{available_langs.length}/{supported_langs.length}</div></div>
      </div>

      <div className="bg-white rounded-2xl border border-neutral-200 p-5 mb-6">
        <div className="text-xs uppercase tracking-widest text-neutral-500 mb-3">Disponibilité par langue</div>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3" data-testid="lang-grid">
          {supported_langs.map((lang) => {
            const isSource = lang === primary_lang;
            const isAvailable = available_langs.includes(lang);
            const isPicked = pickedLangs.includes(lang);
            const isRunning = task?.progress?.[lang] === "running";
            const taskState = task?.progress?.[lang];
            return (
              <button
                key={lang}
                type="button"
                disabled={isSource || running}
                onClick={() => togglePick(lang)}
                data-testid={`lang-${lang}`}
                className={`flex items-center gap-3 px-4 py-3 rounded-xl border transition text-left ${
                  isSource
                    ? "bg-emerald-50 border-emerald-200 text-emerald-900"
                    : isPicked
                    ? "bg-neutral-900 text-white border-neutral-900"
                    : isAvailable
                    ? "bg-emerald-50 border-emerald-200 text-emerald-900"
                    : "bg-white border-neutral-300 text-neutral-700 hover:border-neutral-900"
                } ${isSource || running ? "cursor-default" : "cursor-pointer"}`}
              >
                <span className="text-2xl">{FLAGS[lang]}</span>
                <span className="flex-1">
                  <div className="font-medium">{lang_labels[lang] || lang}</div>
                  <div className={`text-xs ${isPicked ? "text-white/70" : "text-neutral-500"}`}>
                    {isSource ? "Langue source" : isAvailable ? "Traduit" : "Non traduit"}
                    {taskState === "running" && " · en cours…"}
                    {taskState === "done"    && " · ✓"}
                    {taskState === "skipped_budget" && " · skip (budget)"}
                    {typeof taskState === "string" && taskState.startsWith("failed") && " · échec"}
                  </div>
                </span>
                {isAvailable && !isPicked && <CheckCircle size={18} weight="fill" className="text-emerald-500" />}
                {isRunning && <ArrowsClockwise size={18} className="animate-spin" />}
              </button>
            );
          })}
        </div>

        <label className="mt-5 flex items-center gap-2 text-sm text-neutral-600 cursor-pointer">
          <input
            type="checkbox" checked={overwrite}
            onChange={(e) => setOverwrite(e.target.checked)}
            data-testid="overwrite-toggle"
          />
          Re-traduire les langues déjà traduites (overwrite)
        </label>
      </div>

      {task?.status === "failed" && (
        <div className="mt-5 p-4 rounded-2xl bg-rose-50 border border-rose-200 text-sm text-rose-900 flex items-start gap-2">
          <Warning size={16} weight="fill" className="text-rose-500 mt-0.5" />
          <div>Échec : {task.error || "raison inconnue"}.</div>
        </div>
      )}
      {task?.status === "completed" && (
        <div className="mt-5 p-4 rounded-2xl bg-emerald-50 border border-emerald-200 text-sm text-emerald-900 flex items-start gap-2">
          <CheckCircle size={16} weight="fill" className="text-emerald-500 mt-0.5" />
          <div>
            Traduction terminée — {Object.entries(task.progress || {}).filter(([, v]) => v === "done").length} langue(s) ajoutée(s).
            Coût total : {(task.spent_usd ?? 0).toFixed(3)} $.
          </div>
        </div>
      )}
    </StepLayout>
  );
}

