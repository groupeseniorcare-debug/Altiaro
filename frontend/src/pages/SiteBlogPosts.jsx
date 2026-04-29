import React, { useEffect, useState, useCallback } from "react";
import { useParams, Link, useSearchParams } from "react-router-dom";
import {
  Sparkle, ArrowLeft, CheckCircle, CaretDown, ArrowRight, Robot,
} from "@phosphor-icons/react";
import { api, apiCall } from "../lib/api";
import { useStepGuard } from "../lib/useStepGuard";
import { StepValidateCTA } from "../components/StepPageHeader";
import { buildOnValidate } from "../lib/journeySteps";

const LANG_FLAGS = {
  fr: "🇫🇷", en: "🇬🇧", de: "🇩🇪", es: "🇪🇸", it: "🇮🇹", nl: "🇳🇱",
};

export default function SiteBlogPosts() {
  const [searchParams] = useSearchParams();
  const fromStep = searchParams.get("step") === "7";
  const { id: siteId } = useParams();
  const { allowed, checking } = useStepGuard(siteId, "content");

  const [auto, setAuto] = useState(null);
  const [status, setStatus] = useState(null);
  const [posts, setPosts] = useState([]);
  const [queueJobs, setQueueJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filterLang, setFilterLang] = useState("all");
  const [search, setSearch] = useState("");
  const [busy, setBusy] = useState("");
  const [toast, setToast] = useState(null);
  const [advancedCount, setAdvancedCount] = useState(3);

  const showToast = (kind, msg) => {
    setToast({ kind, msg });
    setTimeout(() => setToast(null), 5500);
  };

  // ---------- Chargement initial ----------
  const loadAll = useCallback(async () => {
    setLoading(true);
    const [a, s, p, j] = await Promise.all([
      apiCall(() => api.get(`/sites/${siteId}/automation`)),
      apiCall(() => api.get(`/sites/${siteId}/automation/status`)),
      apiCall(() => api.get(`/sites/${siteId}/blog-posts`)),
      apiCall(() => api.get(`/sites/${siteId}/blog/jobs?status=queued,running,completed,failed`)),
    ]);
    setAuto(a.data || null);
    setStatus(s.data || null);
    setPosts(p.data || []);
    setQueueJobs((j.data && j.data.items) || []);
    setLoading(false);
  }, [siteId]);

  useEffect(() => { if (allowed) loadAll(); }, [allowed, loadAll]);

  // Polling jobs queue (5s) — uniquement si jobs en cours
  useEffect(() => {
    const hasActive = queueJobs.some((j) => ["queued", "running"].includes(j.status));
    if (!hasActive) return;
    const t = setInterval(async () => {
      const { data } = await apiCall(() =>
        api.get(`/sites/${siteId}/blog/jobs?status=queued,running,completed,failed`),
      );
      setQueueJobs((data && data.items) || []);
    }, 5000);
    return () => clearInterval(t);
  }, [siteId, queueJobs]);

  // ---------- Actions ----------
  const toggleAutomation = async () => {
    if (!auto) return;
    const next = !auto.content_enabled;
    setBusy("toggle");
    const { data, error } = await apiCall(() =>
      api.post(`/sites/${siteId}/automation/content`, { enabled: next }),
    );
    setBusy("");
    if (error) return showToast("error", error);
    setAuto(data);
    showToast("ok",
      next
        ? "Automatisation activée — vos articles seront générés automatiquement"
        : "Automatisation désactivée",
    );
  };

  const launchPillars = async () => {
    setBusy("pillars");
    const { error } = await apiCall(() =>
      api.post(`/sites/${siteId}/blog/jobs`, { count: 3, pillar: "buying_guide" }),
    );
    setBusy("");
    if (error) return showToast("error", error);
    showToast("ok", "Vos 3 premiers articles sont en cours de génération (5 min env.)");
    loadAll();
  };

  const generateMore = async () => {
    const n = Math.max(1, Math.min(50, parseInt(advancedCount) || 1));
    setBusy("generate");
    const { error } = await apiCall(() =>
      api.post(`/sites/${siteId}/blog/jobs`, { count: n, pillar: "trends" }),
    );
    setBusy("");
    if (error) return showToast("error", error);
    showToast("ok", `${n} article(s) en file. Worker démarre dans 30 s max.`);
    loadAll();
  };

  // ---------- Render guards ----------
  if (checking || loading) {
    return (
      <div className="min-h-screen bg-[#FAF7F2] flex items-center justify-center">
        <div className="text-sm text-neutral-500">Chargement…</div>
      </div>
    );
  }
  if (!allowed) return null;

  // ---------- Derived ----------
  const blogTotal = (status?.content?.blog_total) ?? posts.length;
  const isAutoOn = !!auto?.content_enabled;
  const showStarter = blogTotal < 3;
  const activeJobs = queueJobs.filter((j) => ["queued", "running"].includes(j.status));
  const filteredPosts = posts.filter((p) => {
    const langMatch = filterLang === "all" ? true : (p.language || p.lang) === filterLang;
    if (!langMatch) return false;
    if (!search) return true;
    const t = (p.title || "").toString().toLowerCase();
    return t.includes(search.toLowerCase());
  });

  return (
    <div className="min-h-screen bg-[#FAF7F2]">
      <div className="max-w-[1100px] mx-auto px-6 md:px-10 py-10">
        <Link to={`/sites/${siteId}`} className="inline-flex items-center gap-2 text-sm text-neutral-600 hover:text-neutral-900 mb-6" data-testid="blog-back">
          <ArrowLeft size={14} /> Retour au cockpit
        </Link>

        {/* Header */}
        <div className="mb-8">
          <div className="text-[11px] uppercase tracking-[0.2em] text-neutral-500 mb-2 flex items-center gap-2">
            <Sparkle size={12} weight="bold" /> Étape 7 · Contenu
          </div>
          <h1 className="text-3xl md:text-4xl font-semibold text-neutral-900" style={{ fontFamily: "'Fraunces', serif" }}>
            Contenu &amp; SEO automatisé
          </h1>
          <p className="text-sm text-neutral-500 mt-2 max-w-2xl">
            Articles de blog, pages d'atterrissage, FAQ — tout est généré et publié en
            arrière-plan. Vous n'avez rien à faire.
          </p>
        </div>

        {toast && (
          <div
            data-testid="blog-toast"
            className={`mb-6 rounded-xl border px-4 py-3 text-sm ${
              toast.kind === "ok"
                ? "border-emerald-200 bg-emerald-50 text-emerald-800"
                : "border-rose-200 bg-rose-50 text-rose-800"
            }`}
          >
            {toast.msg}
          </div>
        )}

        {/* Bloc 1 — Toggle automatisation */}
        <div
          className="bg-white rounded-2xl border border-neutral-200 p-6 mb-6"
          data-testid="automation-card"
        >
          <div className="flex items-start justify-between gap-4 flex-wrap">
            <div className="flex-1 min-w-[280px]">
              <div className="flex items-center gap-2 mb-2">
                <Robot size={20} weight="duotone" className="text-neutral-700" />
                <div className="text-[16px] font-semibold text-neutral-900">
                  Automatisation
                </div>
                <span
                  data-testid="automation-state"
                  className={`text-[10px] uppercase tracking-widest font-bold px-2 py-0.5 rounded-full ${
                    isAutoOn ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                             : "bg-neutral-100 text-neutral-600 border border-neutral-200"
                  }`}
                >
                  {isAutoOn ? "Active" : "Désactivée"}
                </span>
              </div>
              <p className="text-[13px] text-neutral-600 leading-[1.6]">
                Quand l'automatisation est active, Altiaro :
              </p>
              <ul className="text-[13px] text-neutral-700 mt-2 space-y-1 leading-[1.55]">
                <li>• Publie <strong>3 à 7 articles de blog</strong> par semaine selon votre niche</li>
                <li>• Crée jusqu'à <strong>50 pages d'atterrissage SEO</strong> ciblées par jour</li>
                <li>• Découvre <strong>200+ mots-clés long-tail</strong> par produit (français + 5 langues)</li>
                <li>• Enrichit vos <strong>FAQ</strong> avec les questions populaires Google (PAA)</li>
                <li>• <strong>Maille</strong> tout votre contenu automatiquement</li>
                <li>• Soumet à <strong>Google, Bing, Yandex</strong> en continu (IndexNow)</li>
                <li>• Détecte et comble les <strong>content gaps</strong> versus concurrents</li>
              </ul>
              <p className="text-[12px] text-neutral-500 mt-3 italic">
                Tout fonctionne en arrière-plan, 24/7, sans intervention.
              </p>
            </div>
            <Switch
              enabled={isAutoOn}
              busy={busy === "toggle"}
              onToggle={toggleAutomation}
              testId="automation-toggle"
            />
          </div>
          {status?.content && (
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mt-5 pt-5 border-t border-neutral-100">
              <Stat label="Articles publiés" value={status.content.blog_total} />
              <Stat label="Publiés sur 30 jours" value={status.content.blog_published_30d} />
              <Stat label="Pages SEO" value={status.content.landings_total} />
            </div>
          )}
        </div>

        {/* Bloc 2 — Démarrer maintenant (visible uniquement si <3 articles) */}
        {showStarter && (
          <div
            className="bg-gradient-to-br from-[#1C1917] to-[#44403C] text-white rounded-2xl p-6 mb-6"
            data-testid="starter-card"
          >
            <div className="flex items-start gap-4 flex-wrap">
              <div className="flex-1 min-w-[260px]">
                <div className="text-[11px] uppercase tracking-[0.3em] text-white/60 mb-2">
                  Démarrer maintenant
                </div>
                <div className="text-[20px] mb-1.5" style={{ fontFamily: "'Fraunces', serif" }}>
                  Publiez vos 3 premiers articles piliers
                </div>
                <p className="text-[13px] text-white/80 leading-[1.6] max-w-xl">
                  Vous n'avez encore aucun article ({blogTotal}/3). Lancez la génération
                  initiale : un guide d'achat, un comparatif et un article de tendances.
                  Compte ~5 minutes.
                </p>
              </div>
              <button
                onClick={launchPillars}
                disabled={busy === "pillars" || activeJobs.length > 0}
                data-testid="starter-launch"
                className="h-12 px-6 rounded-xl bg-white text-neutral-900 hover:bg-neutral-100 text-sm font-semibold flex items-center gap-2 transition disabled:opacity-60"
              >
                <Sparkle size={16} weight="fill" />
                {busy === "pillars" ? "Lancement…"
                  : activeJobs.length > 0 ? "Génération en cours…"
                  : "Générer mes 3 premiers articles"}
                {!busy && !activeJobs.length && <ArrowRight size={14} weight="bold" />}
              </button>
            </div>
          </div>
        )}

        {/* Bandeau jobs en cours */}
        {activeJobs.length > 0 && (
          <div
            className="bg-amber-50 border border-amber-200 rounded-xl px-4 py-3 mb-6 flex items-center gap-3"
            data-testid="active-jobs-banner"
          >
            <div className="h-2 w-2 rounded-full bg-amber-500 animate-pulse" />
            <div className="text-[13px] text-amber-900">
              <strong>{activeJobs.length} génération{activeJobs.length > 1 ? "s" : ""} en cours</strong>
              {" "}— vos articles seront prêts dans quelques minutes.
            </div>
          </div>
        )}

        {/* Bloc 3 — Liste des articles publiés */}
        <div className="bg-white rounded-2xl border border-neutral-200 p-6 mb-6">
          <div className="flex items-center justify-between gap-4 flex-wrap mb-5">
            <div className="text-[16px] font-semibold text-neutral-900 flex items-center gap-2">
              <CheckCircle size={18} weight="duotone" className="text-emerald-600" />
              Vos contenus publiés ({filteredPosts.length}{filterLang !== "all" || search ? ` / ${posts.length}` : ""})
            </div>
            <div className="flex items-center gap-2">
              <select
                value={filterLang}
                onChange={(e) => setFilterLang(e.target.value)}
                className="h-9 px-3 rounded-lg bg-white border border-neutral-200 text-[13px]"
                data-testid="filter-lang"
              >
                <option value="all">Toutes les langues</option>
                {Object.keys(LANG_FLAGS).map((lg) => (
                  <option key={lg} value={lg}>{LANG_FLAGS[lg]} {lg.toUpperCase()}</option>
                ))}
              </select>
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Rechercher…"
                className="h-9 px-3 rounded-lg bg-white border border-neutral-200 text-[13px] w-44"
                data-testid="filter-search"
              />
            </div>
          </div>

          {filteredPosts.length === 0 ? (
            <div className="py-10 text-center text-[13px] text-neutral-500">
              Aucun article{filterLang !== "all" || search ? " ne correspond à votre filtre" : " publié pour l'instant"}.
            </div>
          ) : (
            <div className="border border-neutral-100 rounded-xl overflow-hidden">
              <table className="w-full text-[13px]">
                <thead className="bg-neutral-50 text-[11px] uppercase tracking-widest text-neutral-500">
                  <tr>
                    <th className="text-left px-4 py-2.5 font-medium w-12">Lang</th>
                    <th className="text-left px-4 py-2.5 font-medium">Titre</th>
                    <th className="text-left px-4 py-2.5 font-medium w-28">Publié le</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredPosts.slice(0, 100).map((p, i) => {
                    const lg = (p.language || p.lang || "fr").toLowerCase();
                    const date = (p.published_at || p.created_at || "").split("T")[0];
                    return (
                      <tr
                        key={p.slug || p.id || i}
                        data-testid={`blog-row-${i}`}
                        className="border-t border-neutral-100 hover:bg-neutral-50"
                      >
                        <td className="px-4 py-3 text-[16px]">{LANG_FLAGS[lg] || "🌐"}</td>
                        <td className="px-4 py-3 text-neutral-900">{p.title || p.slug}</td>
                        <td className="px-4 py-3 text-neutral-500 text-[12px] tabular-nums">{date}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Mode avancé (collapse) */}
        <details className="bg-white rounded-2xl border border-neutral-200 mb-6" data-testid="advanced-mode">
          <summary className="cursor-pointer p-5 flex items-center justify-between text-[14px] font-medium text-neutral-700 hover:bg-neutral-50 rounded-2xl">
            <span className="flex items-center gap-2">
              <Sparkle size={14} weight="bold" /> Mode avancé
              <span className="text-[11px] text-neutral-400 font-normal">(pour les power users)</span>
            </span>
            <CaretDown size={14} weight="bold" />
          </summary>
          <div className="px-5 pb-5 pt-0 space-y-4">
            <div className="border-t border-neutral-100 pt-4">
              <div className="text-[12px] text-neutral-600 mb-2">
                Générer N articles supplémentaires maintenant :
              </div>
              <div className="flex items-center gap-2 flex-wrap">
                <input
                  type="number"
                  min={1}
                  max={50}
                  value={advancedCount}
                  onChange={(e) => setAdvancedCount(e.target.value)}
                  className="h-10 w-20 px-3 rounded-lg bg-white border border-neutral-200 text-sm"
                  data-testid="advanced-count"
                />
                <button
                  onClick={generateMore}
                  disabled={busy === "generate"}
                  data-testid="advanced-generate"
                  className="h-10 px-4 rounded-lg bg-neutral-900 hover:bg-neutral-800 text-white text-[13px] font-medium flex items-center gap-2 disabled:opacity-60"
                >
                  {busy === "generate" ? "Envoi…" : `Générer ${advancedCount} article${advancedCount > 1 ? "s" : ""}`}
                </button>
              </div>
            </div>

            <div className="border-t border-neutral-100 pt-4 grid grid-cols-2 md:grid-cols-4 gap-3">
              <Stat label="Total articles" value={status?.content?.blog_total ?? posts.length} small />
              <Stat label="Pages SEO publiées" value={status?.content?.landings_total ?? 0} small />
              <Stat label="Jobs en file" value={queueJobs.filter((j) => j.status === "queued").length} small />
              <Stat label="Jobs en cours" value={activeJobs.length} small />
            </div>

            {queueJobs.length > 0 && (
              <div className="border-t border-neutral-100 pt-4">
                <div className="text-[12px] text-neutral-600 mb-2">Tâches récentes :</div>
                <div className="space-y-1.5 max-h-60 overflow-auto">
                  {queueJobs.slice(0, 12).map((j) => (
                    <div key={j.id} className="flex items-center gap-2 text-[12px] text-neutral-700 px-3 py-1.5 bg-neutral-50 rounded-md">
                      <span
                        className={
                          j.status === "completed" ? "h-1.5 w-1.5 rounded-full bg-emerald-500" :
                          j.status === "running"   ? "h-1.5 w-1.5 rounded-full bg-amber-500 animate-pulse" :
                          j.status === "failed"    ? "h-1.5 w-1.5 rounded-full bg-rose-500" :
                                                     "h-1.5 w-1.5 rounded-full bg-neutral-300"
                        }
                      />
                      <span className="capitalize font-medium">{j.status}</span>
                      <span className="text-neutral-500">· {j.pillar || "?"} · {j.articles_done || 0}/{j.articles_planned}</span>
                      <span className="ml-auto tabular-nums text-neutral-400">{j.progress || 0}%</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </details>

        {/* Validation finale étape 7 — Contenu SEO (UN SEUL CTA, pas de doublon) */}
        <StepValidateCTA
          currentStepKey="content"
          nextStepNumber={8}
          nextStepLabel="Traduction multilingue"
          nextStepHref={`/sites/${siteId}/translate?step=8`}
          canValidate={
            (status?.content?.blog_published ?? 0) >= 3 &&
            !!auto?.content_enabled
          }
          missingConditions={[
            ...((status?.content?.blog_published ?? 0) >= 3
              ? []
              : [`Au moins 3 articles publiés (actuel : ${status?.content?.blog_published ?? 0})`]),
            ...(auto?.content_enabled
              ? []
              : ["Activer la publication automatique"]),
          ]}
          onValidate={buildOnValidate(siteId, "content", loadAll)}
        />
      </div>
    </div>
  );
}

// ---------- Composants utilitaires ----------
function Switch({ enabled, busy, onToggle, testId }) {
  return (
    <button
      onClick={onToggle}
      disabled={busy}
      data-testid={testId}
      aria-pressed={enabled}
      className={`relative inline-flex h-9 w-16 items-center rounded-full transition-colors disabled:opacity-60 ${
        enabled ? "bg-emerald-500" : "bg-neutral-300"
      }`}
    >
      <span
        className={`inline-block h-7 w-7 transform rounded-full bg-white shadow-md transition-transform ${
          enabled ? "translate-x-8" : "translate-x-1"
        }`}
      />
    </button>
  );
}

function Stat({ label, value, small }) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-[0.2em] text-neutral-500 mb-1">{label}</div>
      <div
        className={`text-neutral-900 ${small ? "text-[18px]" : "text-[24px]"} leading-none`}
        style={{ fontFamily: "'Fraunces', Georgia, serif" }}
      >
        {value ?? "—"}
      </div>
    </div>
  );
}
