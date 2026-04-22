import React, { useEffect, useState } from "react";
import {
  Sparkle, CheckCircle, XCircle, ArrowClockwise, Robot, Flag,
  MagnifyingGlass, Lightbulb, ArrowSquareOut, BookOpen,
} from "@phosphor-icons/react";
import { api, apiCall } from "../lib/api";

const scoreColor = (s) => {
  if (s >= 80) return { ring: "#10b981", text: "text-emerald-700", label: "Excellent" };
  if (s >= 65) return { ring: "#f59e0b", text: "text-amber-700", label: "Bon" };
  if (s >= 40) return { ring: "#f97316", text: "text-orange-700", label: "Moyen" };
  return { ring: "#e11d48", text: "text-rose-700", label: "Faible" };
};

/**
 * SEO/AEO Studio — advanced tab: AEO readiness, keyword strategy, bulk AI optimization.
 */
export default function SeoStudioPanel({ siteId }) {
  const [aeo, setAeo] = useState(null);
  const [kw, setKw] = useState(null);
  const [bulkRunning, setBulkRunning] = useState(false);
  const [bulkMsg, setBulkMsg] = useState("");

  const load = async () => {
    const [a, k] = await Promise.all([
      apiCall(() => api.get(`/sites/${siteId}/seo/aeo-readiness`)),
      apiCall(() => api.get(`/sites/${siteId}/seo/keyword-strategy`)),
    ]);
    if (a.data) setAeo(a.data);
    if (k.data) setKw(k.data);
  };
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [siteId]);

  const runBulkOptimize = async (force = false) => {
    if (!window.confirm(force
      ? "Régénérer les metadata SEO de TOUS les produits (même ceux déjà optimisés) ?"
      : "Lancer l'optimisation IA pour les produits qui n'ont pas encore de SEO metadata ?")) return;
    setBulkRunning(true);
    setBulkMsg("");
    const { data, error } = await apiCall(() =>
      api.post(`/sites/${siteId}/seo/bulk-optimize`, { force, only_missing: !force })
    );
    setBulkRunning(false);
    if (error) { window.alert(error); return; }
    setBulkMsg(data?.message || `Optimisation lancée sur ${data?.queued_products || 0} produits.`);
    // Auto-reload after 90s to reflect progress
    setTimeout(() => { load(); }, 90_000);
  };

  if (!aeo) return <div className="text-sm text-neutral-500 py-6">Chargement AEO…</div>;

  const aeoColor = scoreColor(aeo.score);

  return (
    <div className="space-y-6" data-testid="seo-studio">
      {/* AEO score + checklist */}
      <div className="bg-white border border-neutral-200 rounded-2xl p-6">
        <div className="flex items-start justify-between gap-5 mb-5 flex-wrap">
          <div>
            <div className="text-[11px] uppercase tracking-[0.2em] text-neutral-500 mb-2 flex items-center gap-1">
              <Robot size={12} weight="bold" /> Studio AEO · Answer Engine Optimization
            </div>
            <h2 className="text-2xl font-semibold text-neutral-900" style={{ fontFamily: "'Fraunces', serif" }}>
              Prêt pour les IA & Google Overview
            </h2>
            <p className="text-sm text-neutral-500 mt-1 max-w-xl">
              Score de préparation pour ChatGPT, Perplexity, Gemini et les AI Overview de Google.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <div className="relative w-24 h-24">
              <svg viewBox="0 0 36 36" className="w-24 h-24 -rotate-90">
                <circle cx="18" cy="18" r="15.915" fill="none" stroke="#E7E5E4" strokeWidth="3" />
                <circle cx="18" cy="18" r="15.915" fill="none" stroke={aeoColor.ring} strokeWidth="3"
                  strokeDasharray={`${aeo.score} ${100 - aeo.score}`} strokeDashoffset="0" strokeLinecap="round" />
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <div className="text-2xl font-semibold" style={{ fontFamily: "'Fraunces', serif" }}>{aeo.score}</div>
              </div>
            </div>
            <div>
              <div className={`text-sm font-semibold uppercase ${aeoColor.text}`}>{aeoColor.label}</div>
              <div className="text-xs text-neutral-500">
                {aeo.coverage.products_with_seo_meta}/{aeo.coverage.products_total} produits
              </div>
            </div>
          </div>
        </div>

        <div className="space-y-2">
          {aeo.checks.map((c) => (
            <div key={c.key} data-testid={`aeo-check-${c.key}`}
              className={`flex items-start gap-3 p-3 rounded-lg border ${c.ok ? "bg-emerald-50 border-emerald-100" : "bg-neutral-50 border-neutral-200"}`}>
              {c.ok ? (
                <CheckCircle size={18} weight="fill" className="text-emerald-600 shrink-0 mt-0.5" />
              ) : (
                <XCircle size={18} weight="fill" className="text-neutral-400 shrink-0 mt-0.5" />
              )}
              <div className="flex-1 min-w-0">
                <div className={`text-sm font-medium ${c.ok ? "text-emerald-900" : "text-neutral-800"}`}>{c.label}</div>
                {!c.ok && <div className="text-xs text-neutral-600 mt-0.5">{c.how_to_fix}</div>}
              </div>
              <div className="text-[10px] uppercase tracking-widest text-neutral-400 shrink-0">
                {c.weight} pts
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Bulk AI optimize */}
      <div className="bg-gradient-to-br from-violet-50 to-indigo-50 border border-violet-200 rounded-2xl p-5" data-testid="bulk-optimize-card">
        <div className="flex items-start gap-3 mb-3">
          <div className="w-10 h-10 rounded-xl bg-violet-600 flex items-center justify-center shrink-0">
            <Sparkle size={18} weight="fill" className="text-white" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-sm font-semibold text-violet-900">Optimisation IA en masse</div>
            <div className="text-xs text-violet-800/80 mt-0.5">
              Claude génère pour chaque produit : titre SEO (≤60 car), meta description (≤155 car), 5 mots-clés
              long-tail (transactionnel + informationnel), alt-texts pour chaque image, et 3 Q/R pour le schema FAQ (AEO).
            </div>
          </div>
        </div>
        <div className="flex gap-2 flex-wrap">
          <button onClick={() => runBulkOptimize(false)} disabled={bulkRunning}
            data-testid="bulk-optimize-missing"
            className="h-10 px-4 rounded-lg bg-violet-600 hover:bg-violet-700 text-white text-sm font-medium flex items-center gap-2 disabled:opacity-60">
            {bulkRunning ? <ArrowClockwise size={14} className="animate-spin" /> : <Sparkle size={14} weight="fill" />}
            Optimiser les produits manquants
          </button>
          <button onClick={() => runBulkOptimize(true)} disabled={bulkRunning}
            data-testid="bulk-optimize-all"
            className="h-10 px-4 rounded-lg bg-white border border-violet-300 hover:border-violet-600 text-violet-700 text-sm font-medium">
            Tout régénérer
          </button>
        </div>
        {bulkMsg && (
          <div className="mt-3 text-xs text-violet-800 bg-white/60 rounded-lg px-3 py-2 flex items-center gap-2">
            <CheckCircle size={14} weight="fill" className="text-violet-600" /> {bulkMsg}
          </div>
        )}
      </div>

      {/* Keyword strategy */}
      {kw && (
        <div className="bg-white border border-neutral-200 rounded-2xl p-5" data-testid="keyword-strategy">
          <div className="flex items-center gap-2 mb-4">
            <MagnifyingGlass size={14} weight="bold" />
            <h3 className="font-semibold text-neutral-900" style={{ fontFamily: "'Fraunces', serif" }}>
              Stratégie mots-clés par marché
            </h3>
          </div>
          {Object.keys(kw.per_market).length === 0 || Object.values(kw.per_market).every((m) => m.total === 0) ? (
            <div className="text-sm text-neutral-500 italic p-4 bg-neutral-50 rounded-lg">
              Aucune donnée Google Keyword Planner encore. Lance une Niche Analysis depuis l'étape 1 pour débloquer les mots-clés par marché.
            </div>
          ) : (
            <div className="space-y-5">
              {Object.entries(kw.per_market).map(([cc, m]) => (
                <div key={cc} data-testid={`kw-market-${cc}`}>
                  <div className="flex items-center gap-2 mb-2">
                    <Flag size={14} weight="duotone" />
                    <span className="font-mono font-semibold">{cc}</span>
                    <span className="text-xs text-neutral-500">{m.total} mots-clés{!m.has_data && " (données estimées)"}</span>
                  </div>
                  <div className="grid md:grid-cols-2 gap-3">
                    <KwBucket label="Transactionnel" hint="Intent d'achat — prioriser sur les produits" items={m.transactional} color="emerald" />
                    <KwBucket label="Informationnel" hint="Intent de recherche — prioriser sur le blog" items={m.informational} color="sky" />
                  </div>
                </div>
              ))}
              {kw.blog_suggestions?.length > 0 && (
                <div className="pt-4 border-t border-neutral-100">
                  <div className="text-[11px] uppercase tracking-widest text-neutral-500 mb-2 flex items-center gap-1">
                    <BookOpen size={11} /> Suggestions d'articles blog (gap informationnel)
                  </div>
                  <div className="space-y-1">
                    {kw.blog_suggestions.map((s, i) => (
                      <div key={i} className="flex items-center justify-between text-sm py-1">
                        <div><strong className="font-mono text-xs bg-neutral-100 px-1.5 py-0.5 rounded mr-2">{s.country}</strong>{s.suggested_title}</div>
                        <span className="text-xs text-neutral-500 font-mono">{s.volume.toLocaleString("fr-FR")}/mo</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Technical links */}
      <div className="bg-white border border-neutral-200 rounded-2xl p-5">
        <div className="text-[11px] uppercase tracking-widest text-neutral-500 mb-3 flex items-center gap-1">
          <Lightbulb size={11} /> Fichiers techniques (auto-générés)
        </div>
        <div className="grid md:grid-cols-3 gap-3 text-sm">
          {[
            ["sitemap.xml", `/api/public/sites/${siteId}/sitemap.xml`, "Multi-pays + hreflang"],
            ["robots.txt", `/api/public/sites/${siteId}/robots.txt`, "Indexation autorisée"],
            ["llms.txt", `/api/public/sites/${siteId}/llms.txt`, "Pour IA (ChatGPT, Perplexity)"],
          ].map(([label, href, hint]) => (
            <a key={label} href={href} target="_blank" rel="noreferrer"
              data-testid={`tech-file-${label}`}
              className="block p-3 rounded-lg bg-neutral-50 hover:bg-neutral-100 border border-neutral-200 group">
              <div className="flex items-center justify-between">
                <div className="font-mono font-medium text-neutral-900 text-sm">/{label}</div>
                <ArrowSquareOut size={12} className="text-neutral-400 group-hover:text-neutral-900" />
              </div>
              <div className="text-[11px] text-neutral-500 mt-0.5">{hint}</div>
            </a>
          ))}
        </div>
      </div>
    </div>
  );
}

function KwBucket({ label, hint, items, color }) {
  const palette = color === "emerald"
    ? { bg: "bg-emerald-50", border: "border-emerald-100", text: "text-emerald-800", chip: "bg-emerald-100 text-emerald-800" }
    : { bg: "bg-sky-50", border: "border-sky-100", text: "text-sky-800", chip: "bg-sky-100 text-sky-800" };
  return (
    <div className={`${palette.bg} ${palette.border} border rounded-xl p-3`}>
      <div className={`text-xs font-semibold ${palette.text}`}>{label}</div>
      <div className="text-[10px] text-neutral-500 mb-2">{hint}</div>
      {items.length === 0 ? (
        <div className="text-xs text-neutral-400 italic">—</div>
      ) : (
        <div className="flex flex-wrap gap-1">
          {items.slice(0, 10).map((it, i) => (
            <span key={i} className={`${palette.chip} text-[11px] px-2 py-0.5 rounded-full font-medium`}
              title={`Volume: ${it.volume}/mo · CPC: ${it.cpc}€`}>
              {it.keyword}
              {it.volume > 0 && <span className="opacity-60"> · {it.volume.toLocaleString("fr-FR")}</span>}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
