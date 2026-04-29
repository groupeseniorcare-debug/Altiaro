/**
 * Phase 3 — Étape 7 cockpit : Traduction multi-langue.
 *
 * Permet au concepteur de lancer la traduction du site (brand, sections,
 * produits, blog) vers EN/DE/NL/IT/ES via Claude Sonnet 4.5.
 * Idempotent (skip langues déjà traduites sauf overwrite).
 * Coût ~0,5-1 $ par langue, cap ~3 $/site.
 */
import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { ArrowLeft, CheckCircle, Translate, ArrowsClockwise, Warning } from "@phosphor-icons/react";
import { api, apiCall } from "../lib/api";
import Layout from "../components/Layout";
import { StepValidateCTA } from "../components/StepPageHeader";
import { buildOnValidate } from "../lib/journeySteps";

const FLAGS = { fr: "🇫🇷", en: "🇬🇧", de: "🇩🇪", nl: "🇳🇱", it: "🇮🇹", es: "🇪🇸" };

export default function SiteTranslate() {
  const { id: siteId } = useParams();
  const navigate = useNavigate();
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
  useEffect(() => { loadState(); }, [siteId]);

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
    if (error) {
      setRunning(false);
      alert(error);
      return;
    }
    const { task_id } = data;
    // Poll status — auto-stop si 404 répétés (task perdu suite à restart backend)
    let notFoundStreak = 0;
    const poll = async () => {
      const { data: st, status } = await apiCall(() =>
        api.get(`/sites/${siteId}/translate/status?task_id=${task_id}`),
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
        return;
      }
      setTimeout(poll, 5000);
    };
    poll();
  };

  if (loading || !state) {
    return <Layout><div className="p-10 text-sm text-neutral-500">Chargement…</div></Layout>;
  }

  const { primary_lang, available_langs = [], supported_langs = [], lang_labels = {}, counts = {} } = state;

  return (
    <Layout>
      <div className="p-6 md:p-10 max-w-[1100px] mx-auto w-full">
        <button
          onClick={() => navigate(`/sites/${siteId}`)}
          className="flex items-center gap-2 text-sm text-neutral-500 hover:text-neutral-900 mb-5 transition"
          data-testid="back-to-cockpit"
        >
          <ArrowLeft size={16} /> Retour au cockpit
        </button>

        <header className="mb-8">
          <div className="text-[11px] uppercase tracking-[0.2em] text-neutral-500 mb-2">Étape 8 · Traduction multi-langue</div>
          <h1 className="text-3xl md:text-4xl font-light text-neutral-900 tracking-tight">Traduire ce site</h1>
          <p className="text-sm text-neutral-600 max-w-2xl mt-3 leading-relaxed">
            Le site est rédigé en <span className="font-semibold">{FLAGS[primary_lang]} {lang_labels[primary_lang]}</span>.
            Sélectionnez les langues cibles pour générer brand, sections homepage, fiches produits, blog et SEO meta dans
            chaque langue. Les traductions s'affichent automatiquement quand un visiteur change de drapeau.
            <span className="ml-1 text-neutral-400">~0,5-1 $ par langue.</span>
          </p>
        </header>

        {/* Catalogue */}
        <div className="bg-white rounded-2xl border border-neutral-200 p-5 mb-6 text-sm text-neutral-600 grid grid-cols-3 gap-4">
          <div><div className="uppercase text-[10px] tracking-widest text-neutral-400">Produits</div><div className="text-2xl font-light text-neutral-900 mt-1">{counts.products}</div></div>
          <div><div className="uppercase text-[10px] tracking-widest text-neutral-400">Articles blog</div><div className="text-2xl font-light text-neutral-900 mt-1">{counts.blog_posts}</div></div>
          <div><div className="uppercase text-[10px] tracking-widest text-neutral-400">Langues</div><div className="text-2xl font-light text-neutral-900 mt-1">{available_langs.length}/{supported_langs.length}</div></div>
        </div>

        {/* Lang grid */}
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

        <div className="flex items-center justify-between gap-4">
          <div className="text-xs text-neutral-500">
            {pickedLangs.length === 0 ? "Sélectionnez au moins une langue cible." : (
              <>Sélection : {pickedLangs.map((l) => FLAGS[l]).join(" ")} ({pickedLangs.length})</>
            )}
            {task?.spent_usd != null && <span className="ml-3 text-neutral-700">Coût session : {task.spent_usd.toFixed(3)} $</span>}
          </div>
          <button
            onClick={startTranslate}
            disabled={!pickedLangs.length || running}
            data-testid="start-translate"
            className="h-11 px-6 rounded-full text-sm font-semibold text-white bg-neutral-900 hover:bg-neutral-800 disabled:opacity-50 inline-flex items-center gap-2"
          >
            <Translate size={16} weight="bold" />
            {running ? `Traduction… ${task?.spent_usd ? `(${task.spent_usd.toFixed(2)}$)` : ""}` : "Lancer la traduction"}
          </button>
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
              Traduction terminée — {Object.entries(task.progress || {}).filter(([_,v]) => v==="done").length} langue(s) ajoutée(s).
              Coût total : {(task.spent_usd ?? 0).toFixed(3)} $.
            </div>
          </div>
        )}

        {/* Validation finale étape 8 — Traduction multilingue */}
        <StepValidateCTA
          currentStepKey="translate"
          nextStepNumber={9}
          nextStepLabel="Score SEO & connexions Google"
          nextStepHref={`/sites/${siteId}/seo`}
          canValidate={(available_langs || []).length >= 3}
          missingConditions={
            (available_langs || []).length >= 3
              ? []
              : [
                  `Au moins 3 langues actives (actuel : ${(available_langs || []).length})`,
                ]
          }
          onValidate={buildOnValidate(siteId, "translate", loadState)}
        />
      </div>
    </Layout>
  );
}
