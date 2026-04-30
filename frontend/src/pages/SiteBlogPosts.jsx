import React, { useEffect, useState, useCallback } from "react";
import { useParams, Link, useSearchParams } from "react-router-dom";
import {
  Sparkle, ArrowLeft, CheckCircle, ArrowRight, Robot,
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
