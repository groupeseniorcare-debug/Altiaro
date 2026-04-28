/**
 * Phase 2.5 (Tâche B) — Panel AI Tweak dans le cockpit étape 5.
 *
 * Zone de texte libre : le concepteur décrit en langage naturel la modif
 * souhaitée (palette, ton, nav, sections). L'endpoint
 * `POST /api/sites/{siteId}/design/ai-tweak` appelle Claude Sonnet 4.5,
 * produit un diff ciblé sur une whitelist de champs, applique en DB et
 * retourne le résumé. Undo disponible via snapshot_id retourné.
 */
import React, { useState } from "react";
import { MagicWand, ArrowCounterClockwise, Check, X } from "@phosphor-icons/react";
import { api } from "../../lib/api";

export default function AiTweakPanel({ siteId, onApplied }) {
  const [prompt, setPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [err, setErr] = useState(null);
  const [lastSnapshot, setLastSnapshot] = useState(null);

  const examples = [
    "Change la palette en ivoire, terracotta et noir charbon",
    "Rend le ton des pages produit plus chaleureux",
    "Remplace la typo de titre par Fraunces",
    "Ajoute un lien 'Notre savoir-faire' dans la nav principale",
  ];

  async function submit() {
    if (!prompt.trim()) return;
    setLoading(true); setErr(null); setResult(null);
    try {
      const r = await api.post(`/sites/${siteId}/design/ai-tweak`, { prompt: prompt.trim() });
      setResult(r.data);
      if (r.data?.snapshot_id) setLastSnapshot(r.data.snapshot_id);
      if (r.data?.ok && r.data?.changes_applied > 0 && typeof onApplied === "function") {
        onApplied(r.data);
      }
    } catch (e) {
      setErr(e?.response?.data?.detail || e?.message || "Erreur inconnue");
    } finally { setLoading(false); }
  }

  async function undo() {
    if (!lastSnapshot) return;
    setLoading(true); setErr(null);
    try {
      const r = await api.post(`/sites/${siteId}/design/ai-tweak/undo`, null, {
        params: { snapshot_id: lastSnapshot },
      });
      setResult({ ok: true, summary: `↩️ ${r.data.reverted} champ(s) restauré(s)`, changes_applied: r.data.reverted, changes: [] });
      setLastSnapshot(null);
      if (typeof onApplied === "function") onApplied({ reverted: true });
    } catch (e) {
      setErr(e?.response?.data?.detail || e?.message || "Undo impossible");
    } finally { setLoading(false); }
  }

  return (
    <div
      className="mt-5 p-6 md:p-7 rounded-2xl border border-neutral-200 bg-white"
      data-testid="ai-tweak-panel"
    >
      <div className="flex items-start gap-4 mb-4">
        <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-indigo-500/15 to-violet-500/10 border border-indigo-200/50 flex items-center justify-center flex-shrink-0">
          <MagicWand size={20} weight="duotone" className="text-indigo-600" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-[10px] uppercase tracking-[0.2em] text-indigo-600 font-semibold mb-1">
            Ajuster avec l'IA
          </div>
          <h3 className="text-lg font-light leading-tight" style={{ fontFamily: "'Fraunces', Georgia, serif" }}>
            Dis-moi ce que tu veux changer, je le fais.
          </h3>
          <p className="text-[13px] text-neutral-500 mt-1.5 leading-relaxed">
            Claude Sonnet 4.5 modifie la palette, la typo, le ton, la navigation ou les sections en langage naturel.
            Seuls les champs de design sont modifiables. Undo disponible 48&nbsp;h.
          </p>
        </div>
      </div>

      <textarea
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        placeholder="Ex : Change la palette en ivoire et terracotta, ton plus chaleureux sur les produits…"
        rows={3}
        disabled={loading}
        data-testid="ai-tweak-textarea"
        className="w-full p-4 rounded-xl border border-neutral-200 bg-neutral-50 focus:bg-white focus:border-indigo-300 focus:ring-2 focus:ring-indigo-100 outline-none text-[14px] resize-none transition-all disabled:opacity-60"
      />

      <div className="mt-2 flex flex-wrap gap-1.5">
        {examples.map((e, i) => (
          <button
            key={i}
            onClick={() => setPrompt(e)}
            className="text-[11px] px-2.5 py-1 rounded-full bg-neutral-100 text-neutral-600 hover:bg-indigo-50 hover:text-indigo-700 transition-colors"
            type="button"
          >
            {e}
          </button>
        ))}
      </div>

      <div className="mt-4 flex items-center gap-3">
        <button
          onClick={submit}
          disabled={loading || !prompt.trim()}
          data-testid="ai-tweak-submit"
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-neutral-900 text-white font-medium text-sm hover:bg-neutral-800 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
        >
          <MagicWand size={16} weight="bold" />
          {loading ? "Analyse en cours…" : "Appliquer"}
        </button>
        {lastSnapshot && (
          <button
            onClick={undo}
            disabled={loading}
            data-testid="ai-tweak-undo"
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-neutral-100 text-neutral-700 font-medium text-sm hover:bg-neutral-200 transition-all"
          >
            <ArrowCounterClockwise size={14} weight="bold" />
            Annuler le dernier
          </button>
        )}
      </div>

      {err && (
        <div className="mt-4 p-3 rounded-lg bg-red-50 border border-red-200 text-[13px] text-red-700 flex gap-2">
          <X size={16} className="mt-0.5 flex-shrink-0" /> {err}
        </div>
      )}
      {result && !err && (
        <div
          className={`mt-4 p-4 rounded-lg border text-[13px] ${result.ok ? "bg-emerald-50 border-emerald-200 text-emerald-900" : "bg-amber-50 border-amber-200 text-amber-900"}`}
          data-testid="ai-tweak-result"
        >
          <div className="flex items-start gap-2 font-medium mb-2">
            {result.ok ? <Check size={16} weight="bold" className="text-emerald-700 mt-0.5" /> : <X size={16} className="text-amber-700 mt-0.5" />}
            <div>{result.summary || (result.ok ? `${result.changes_applied} changement(s) appliqué(s)` : (result.refused || "Modification refusée"))}</div>
          </div>
          {Array.isArray(result.changes) && result.changes.length > 0 && (
            <ul className="space-y-1.5 pl-6 text-[12.5px]">
              {result.changes.slice(0, 10).map((c, i) => (
                <li key={i} className="leading-snug">
                  <code className="bg-white/60 px-1.5 py-0.5 rounded text-[11.5px]">{c.path}</code>
                  {" — "}
                  <span className="text-neutral-600">{c.rationale}</span>
                </li>
              ))}
            </ul>
          )}
          {Array.isArray(result.changes_rejected) && result.changes_rejected.length > 0 && (
            <div className="mt-2 text-[11.5px] text-neutral-500">
              {result.changes_rejected.length} changement(s) rejeté(s) (champ non autorisé)
            </div>
          )}
        </div>
      )}
    </div>
  );
}
