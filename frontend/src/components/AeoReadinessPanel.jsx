import React, { useEffect, useState } from "react";
import { api, apiCall } from "../lib/api";
import { Sparkle, CheckCircle, XCircle, ArrowRight } from "@phosphor-icons/react";

/**
 * AEO Readiness panel — score 0-100 local + checklist + bouton d'enrichissement
 * bulk de tous les produits du site.
 */
export default function AeoReadinessPanel({ siteId }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [job, setJob] = useState(null);
  const [bulkBusy, setBulkBusy] = useState(false);

  const load = async () => {
    const { data: res } = await apiCall(() => api.get(`/sites/${siteId}/aeo-readiness`));
    setData(res || null);
    setLoading(false);
  };

  useEffect(() => { load(); }, [siteId]);

  const pollBulk = (jobId) => {
    const start = Date.now();
    const tick = async () => {
      const { data: j } = await apiCall(() =>
        api.get(`/sites/${siteId}/products/aeo-enrich-bulk/${jobId}`)
      );
      if (j) setJob(j);
      if (j && (j.status === "done" || j.status === "failed")) {
        setBulkBusy(false);
        load();
        return;
      }
      if (Date.now() - start < 5 * 60 * 1000) {
        setTimeout(tick, 6000);
      } else {
        setBulkBusy(false);
        load();
      }
    };
    setTimeout(tick, 4000);
  };

  const bulkEnrich = async () => {
    if (!window.confirm(
      "Enrichir en AEO tous les produits non-enrichis ?\n\n" +
      "• Ajoute 18-22 Q/R conversationnelles + mots-clés AEO par produit\n" +
      "• Coût : ~0,05 € LLM par produit\n" +
      "• Durée : ~25 s par produit (3 en parallèle)"
    )) return;
    setBulkBusy(true);
    setJob(null);
    const { data: res, error, rawDetail } = await apiCall(() =>
      api.post(`/sites/${siteId}/products/aeo-enrich-bulk`, { force: false, max_products: 50 })
    );
    if (error) {
      setBulkBusy(false);
      window.alert(rawDetail?.detail || error);
      return;
    }
    if (res?.status === "noop") {
      setBulkBusy(false);
      window.alert(res.message);
      return;
    }
    pollBulk(res.job_id);
  };

  if (loading || !data) return null;
  const { score, products_ready, products_total, ready_pct, avg_qa_per_product, conversational_keywords_total, checklist } = data;

  return (
    <div
      data-testid="aeo-readiness-panel"
      className="p-6 md:p-7"
      style={{ borderTop: "1px solid #E5E5E5" }}
    >
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_1.4fr] gap-10">
        {/* Left — score + CTA */}
        <div>
          <div className="flex items-center gap-3 mb-3">
            <span className="h-px w-8 bg-neutral-900" />
            <span className="text-[10px] uppercase tracking-[0.35em] text-neutral-900 font-medium">
              AEO Readiness
            </span>
          </div>
          <div className="flex items-baseline gap-3">
            <div
              className="text-[52px] leading-none text-neutral-900 tabular-nums"
              style={{ fontFamily: "'Fraunces', Georgia, serif" }}
            >
              {score}
            </div>
            <div className="text-[12px] text-neutral-500">/ 100</div>
          </div>
          <p className="text-[13px] text-neutral-600 mt-3 leading-[1.55] max-w-sm">
            Score local basé sur le volume de Q/R par produit, les mots-clés
            conversationnels, le schema et le contenu editorial — directement
            aspiré par ChatGPT, Perplexity, Gemini.
          </p>

          {/* Progress bar */}
          <div className="mt-5 h-1 bg-neutral-200 overflow-hidden" style={{ borderRadius: "1px" }}>
            <div
              className="h-full bg-neutral-900 transition-all duration-700"
              style={{ width: `${Math.max(4, Math.min(100, score))}%` }}
            />
          </div>
          <div className="flex justify-between text-[10px] uppercase tracking-[0.2em] text-neutral-400 mt-2">
            <span>Débutant</span>
            <span>Pro</span>
            <span>Élite</span>
          </div>

          {/* Bulk enrich CTA */}
          <button
            onClick={bulkEnrich}
            disabled={bulkBusy || products_total === 0}
            data-testid="aeo-bulk-btn"
            className="mt-6 h-11 px-5 bg-neutral-900 hover:bg-black disabled:opacity-60 text-white text-[12.5px] font-semibold flex items-center gap-2 transition"
            style={{ borderRadius: "2px" }}
          >
            <Sparkle size={14} weight="fill" className={bulkBusy ? "animate-pulse" : ""} />
            {bulkBusy
              ? `Enrichissement… ${job?.processed ?? 0}/${job?.total ?? "?"}`
              : "Enrichir tous les produits en AEO"}
            {!bulkBusy && <ArrowRight size={13} weight="bold" />}
          </button>
          {job?.status === "done" && (
            <div className="mt-3 text-[11.5px] text-emerald-700 font-medium">
              ✓ {job.enriched} produit(s) enrichi(s){job.failed ? ` · ${job.failed} échec(s)` : ""}
            </div>
          )}
          {job?.status === "failed" && job?.error && (
            <div className="mt-3 text-[11.5px] text-rose-700 font-medium">
              Échec : {job.error}
            </div>
          )}
        </div>

        {/* Right — checklist */}
        <div data-testid="aeo-checklist">
          <div className="text-[10px] uppercase tracking-[0.35em] text-neutral-500 mb-4">
            Signaux détectés
          </div>
          <ul className="space-y-3">
            {checklist.map((c) => (
              <li key={c.key} className="flex items-start gap-3 text-[13px]">
                {c.ok ? (
                  <CheckCircle size={16} weight="fill" className="text-emerald-600 shrink-0 mt-[2px]" />
                ) : (
                  <XCircle size={16} weight="regular" className="text-neutral-300 shrink-0 mt-[2px]" />
                )}
                <span className={c.ok ? "text-neutral-900" : "text-neutral-500"}>
                  {c.label}
                </span>
              </li>
            ))}
          </ul>
          <div
            className="mt-5 p-4 text-[12px] leading-[1.6]"
            style={{ background: "#F5F5F5", borderRadius: "2px" }}
          >
            <span className="font-semibold text-neutral-900">Comment ça aide ? </span>
            <span className="text-neutral-600">
              Plus de Q/R conversationnelles = plus de matches quand un utilisateur
              demande à ChatGPT « quel [produit] pour [besoin] ? ». Votre site
              devient la source citée dans la réponse IA.
            </span>
          </div>
          {products_total > 0 && (
            <div className="mt-3 text-[11px] text-neutral-400">
              {products_ready} / {products_total} produits AEO-ready · {avg_qa_per_product} Q/R moy · {conversational_keywords_total} keywords
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
