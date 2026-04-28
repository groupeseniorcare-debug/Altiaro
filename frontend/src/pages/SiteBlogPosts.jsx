import React, { useEffect, useState } from "react";
import { useParams, Link, useSearchParams } from "react-router-dom";
import {
  Plus, PencilSimple, Trash, Sparkle, ArrowLeft, X, Eye,
  FloppyDisk, Warning, CheckCircle, Clock, CalendarBlank, Stack,
} from "@phosphor-icons/react";
import { api, apiCall } from "../lib/api";
import { useStepGuard } from "../lib/useStepGuard";
import NextStepCTA from "../components/NextStepCTA";

export default function SiteBlogPosts() {
  const [searchParams] = useSearchParams();
  const fromStep7 = searchParams.get("step") === "7";
  const { id: siteId } = useParams();
  const { allowed, checking } = useStepGuard(siteId, "content");
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(null);
  const [toast, setToast] = useState(null);
  const [aiOpen, setAiOpen] = useState(false);
  const [aiForm, setAiForm] = useState({ keyword: "", angle: "", length: "long" });
  const [aiLoading, setAiLoading] = useState(false);

  const load = async () => {
    setLoading(true);
    const { data } = await apiCall(() => api.get(`/sites/${siteId}/blog-posts`));
    setPosts(data || []);
    setLoading(false);
  };

  useEffect(() => { load(); }, [siteId]);

  // ===== Phase A2 — File d'attente blog (jobs asynchrones) =====
  const [queueJobs, setQueueJobs] = useState([]);
  const [queueCount, setQueueCount] = useState(3);
  const [queuePillar, setQueuePillar] = useState("buying_guide");
  const [enqueueBusy, setEnqueueBusy] = useState(false);

  const loadQueueJobs = async () => {
    const { data } = await apiCall(() =>
      api.get(`/sites/${siteId}/blog/jobs?status=queued,running,completed,failed`),
    );
    setQueueJobs((data && data.items) || []);
  };
  useEffect(() => {
    loadQueueJobs();
    const t = setInterval(loadQueueJobs, 5000);
    return () => clearInterval(t);
  }, [siteId]);

  const enqueueBlogJob = async () => {
    setEnqueueBusy(true);
    const { error } = await apiCall(() =>
      api.post(`/sites/${siteId}/blog/jobs`, {
        count: Math.max(1, Math.min(50, parseInt(queueCount) || 1)),
        pillar: queuePillar,
      }),
    );
    setEnqueueBusy(false);
    if (error) return showToast("error", error);
    showToast("ok", `${queueCount} article(s) ajoutés à la file. Le worker démarre dans 30 s max.`);
    loadQueueJobs();
    setTimeout(load, 5000);
  };
  // ============================================================

  const showToast = (type, msg) => {
    setToast({ type, msg });
    setTimeout(() => setToast(null), 5000);
  };

  const save = async () => {
    if (!editing?.title) return;
    const payload = { ...editing };
    if (editing._isNew) {
      const { data, error } = await apiCall(() => api.post(`/sites/${siteId}/blog-posts`, payload));
      if (error) return showToast("error", error);
      showToast("ok", "Article créé");
    } else {
      const { data, error } = await apiCall(() => api.patch(`/sites/${siteId}/blog-posts/${editing.slug}`, payload));
      if (error) return showToast("error", error);
      showToast("ok", "Article mis à jour");
    }
    setEditing(null);
    load();
  };

  const remove = async (post) => {
    if (!window.confirm(`Supprimer définitivement « ${post.title} » ?`)) return;
    const { error } = await apiCall(() => api.delete(`/sites/${siteId}/blog-posts/${post.slug}`));
    if (error) return showToast("error", error);
    showToast("ok", "Article supprimé");
    load();
  };

  const aiGenerate = async () => {
    if (!aiForm.keyword) return;
    setAiLoading(true);
    const { data, error } = await apiCall(() => api.post(`/sites/${siteId}/blog-posts/ai-draft`, aiForm));
    setAiLoading(false);
    if (error) return showToast("error", error);
    showToast("ok", `Article "${data.title}" généré par l'IA`);
    setAiOpen(false);
    setAiForm({ keyword: "", angle: "", length: "long" });
    load();
  };

  const [autoPlanLoading, setAutoPlanLoading] = useState(false);
  const [autoPlanJob, setAutoPlanJob] = useState(null);

  // Monthly cluster state
  const [clusterStatus, setClusterStatus] = useState(null);
  const [clusterBusy, setClusterBusy] = useState(false);

  const loadClusterStatus = async () => {
    const { data } = await apiCall(() => api.get(`/sites/${siteId}/blog-posts/cluster-status`));
    if (data) setClusterStatus(data);
  };

  useEffect(() => { loadClusterStatus(); }, [siteId]);

  const pollAutoPlan = async (jobId) => {
    // Poll every 8s up to 4 minutes
    const startAt = Date.now();
    const maxMs = 4 * 60 * 1000;
    const tick = async () => {
      const { data, error } = await apiCall(() => api.get(`/sites/${siteId}/blog-posts/auto-plan/${jobId}`));
      if (error) return;
      setAutoPlanJob(data);
      if (data.status === "done") {
        setAutoPlanLoading(false);
        setAutoPlanJob(null);
        showToast("ok", `Blog complet généré : « ${data.pillar_title} » + ${data.satellites_count} satellite(s).`);
        load();
        return;
      }
      if (data.status === "failed") {
        setAutoPlanLoading(false);
        setAutoPlanJob(null);
        showToast("error", `Génération échouée : ${data.error || "erreur inconnue"}`);
        return;
      }
      if (Date.now() - startAt < maxMs) {
        setTimeout(tick, 8000);
      } else {
        setAutoPlanLoading(false);
        setAutoPlanJob(null);
        showToast("error", "Timeout — recharge dans 1 min, les articles apparaîtront s'ils sont prêts.");
        load();
      }
    };
    setTimeout(tick, 5000);
  };

  const autoPlan = async (maxSatellites = 3) => {
    const msg =
      `Générer automatiquement 1 article pilier + ${maxSatellites} satellites depuis vos mots-clés SEO (Étape 8) ?\n\n` +
      `• Durée : environ 60 à 120 secondes (l'IA génère en arrière-plan)\n` +
      `• Les articles sont liés entre eux (internal linking)\n` +
      `• Ils sont publiés immédiatement sur /blog`;
    if (!window.confirm(msg)) return;
    setAutoPlanLoading(true);
    const { data, error, rawDetail } = await apiCall(() =>
      api.post(`/sites/${siteId}/blog-posts/auto-plan`, {
        country: "FR",
        max_satellites: maxSatellites,
      })
    );
    if (error) {
      setAutoPlanLoading(false);
      return showToast("error", rawDetail?.detail || error);
    }
    setAutoPlanJob({ ...data, status: "pending" });
    showToast("ok", data.message || "Génération lancée en arrière-plan.");
    pollAutoPlan(data.job_id);
  };

  const generateMonthlyCluster = async () => {
    const msg =
      `Générer le cluster de contenu de ce mois (1 pilier + 4 satellites) ?\n\n` +
      `• Les keywords déjà utilisés par vos articles sont automatiquement exclus\n` +
      `• Durée : 90 à 150 secondes (en arrière-plan)\n` +
      `• Boost direct des signaux E-E-A-T de Google & Perplexity`;
    if (!window.confirm(msg)) return;
    setClusterBusy(true);
    const { data, error, rawDetail } = await apiCall(() =>
      api.post(`/sites/${siteId}/blog-posts/cluster-monthly`, {
        country: "FR",
        satellites: 4,
      })
    );
    if (error) {
      setClusterBusy(false);
      return showToast("error", rawDetail?.detail || error);
    }
    setAutoPlanJob({ ...data, status: "pending" });
    setAutoPlanLoading(true);
    showToast("ok", data.message || "Cluster mensuel lancé.");
    pollAutoPlan(data.job_id);
    // Refresh cluster status
    setTimeout(loadClusterStatus, 1500);
    setClusterBusy(false);
  };

  const toggleAutoCluster = async () => {
    const nextState = !clusterStatus?.auto_enabled;
    const { data, error } = await apiCall(() =>
      api.post(`/sites/${siteId}/blog-posts/cluster-settings`, {
        auto_enabled: nextState,
        country: clusterStatus?.country || "FR",
        satellites: clusterStatus?.satellites || 4,
      })
    );
    if (error) return showToast("error", error);
    showToast(
      "ok",
      nextState
        ? "Publication automatique activée (1 cluster / mois)"
        : "Publication automatique désactivée",
    );
    loadClusterStatus();
  };

  const fmtDate = (iso) => {
    if (!iso) return "—";
    try {
      return new Date(iso).toLocaleDateString("fr-FR", {
        day: "numeric", month: "long", year: "numeric",
      });
    } catch (_e) {
      return iso;
    }
  };

  if (checking) {
    return (
      <div className="min-h-screen bg-[#FAF7F2] flex items-center justify-center">
        <div className="text-sm text-neutral-500">Vérification des prérequis…</div>
      </div>
    );
  }
  if (!allowed) return null;

  return (
    <div className="min-h-screen bg-[#FAF7F2]">
      <div className="max-w-[1600px] mx-auto px-6 md:px-10 py-8">
        <Link to={`/sites/${siteId}`} className="inline-flex items-center gap-2 text-sm text-neutral-600 hover:text-neutral-900 mb-6" data-testid="back-to-site">
          <ArrowLeft size={14} /> Retour au cockpit
        </Link>

        {/* Contextual guidance banner — Étape 7 */}
        <div
          data-testid="step7-guidance-banner"
          className="mb-8 bg-white p-5 md:p-6"
          style={{ border: "1px solid #E5E5E5", borderRadius: "4px" }}
        >
          <div className="flex flex-col md:flex-row md:items-center gap-4 md:gap-6">
            <div className="flex-1 min-w-0">
              <div className="text-[10px] uppercase tracking-[0.3em] text-neutral-500 mb-1.5 font-medium">
                {fromStep7 ? "Étape 7" : "Contenu éditorial"}
              </div>
              <div
                className="text-[19px] md:text-[22px] text-neutral-900 leading-tight"
                style={{ fontFamily: "'Fraunces', Georgia, serif" }}
              >
                Blog & contenu SEO
              </div>
              <p className="text-[13px] text-neutral-600 mt-1.5 leading-[1.55] max-w-2xl">
                Le blog nourrit le référencement de votre boutique et convertit les
                visiteurs informés en acheteurs. Deux options : <b>« Générer tout le blog »</b>
                lance un cluster SEO (1 article pilier + 3 satellites) en 1 clic,
                ou <b>« Rédiger 1 article »</b> pour un sujet précis.
                Un <b>cluster mensuel</b> peut aussi être activé (plus bas) pour
                publier automatiquement 5 articles chaque 1er du mois.
              </p>
            </div>
          </div>
        </div>

        {/* Phase A2 — File d'attente blog */}
        <div
          data-testid="blog-queue-panel"
          className="mb-8 bg-white p-5 md:p-6"
          style={{ border: "1px solid #E5E5E5", borderRadius: "4px" }}
        >
          <div className="flex items-start justify-between gap-4 flex-wrap">
            <div className="flex-1 min-w-[280px]">
              <div className="text-[10px] uppercase tracking-[0.3em] text-neutral-500 mb-1.5 font-medium">
                Phase A2 · File d'attente
              </div>
              <div className="text-[18px] text-neutral-900 leading-tight" style={{ fontFamily: "'Fraunces', Georgia, serif" }}>
                Production blog asynchrone
              </div>
              <p className="text-[13px] text-neutral-600 mt-1.5 leading-[1.55] max-w-2xl">
                Mettez plusieurs articles en file ; le worker en générera jusqu'à <b>3 en parallèle</b>
                toutes les 30 s, sans bloquer votre interface. Idéal pour préparer 10 à 50 articles d'un coup.
              </p>
            </div>
            <div className="flex items-end gap-2 flex-wrap">
              <div>
                <label className="block text-[10px] uppercase tracking-[0.2em] text-neutral-500 mb-1">Nombre</label>
                <input
                  type="number"
                  min={1}
                  max={50}
                  value={queueCount}
                  onChange={(e) => setQueueCount(e.target.value)}
                  className="h-11 w-20 px-3 rounded-xl bg-white border border-neutral-200 text-sm"
                  data-testid="blog-queue-count"
                />
              </div>
              <div>
                <label className="block text-[10px] uppercase tracking-[0.2em] text-neutral-500 mb-1">Type</label>
                <select
                  value={queuePillar}
                  onChange={(e) => setQueuePillar(e.target.value)}
                  className="h-11 px-3 rounded-xl bg-white border border-neutral-200 text-sm"
                  data-testid="blog-queue-pillar"
                >
                  <option value="buying_guide">Guide d'achat</option>
                  <option value="comparison">Comparatif / critères</option>
                  <option value="trends">Tendances</option>
                </select>
              </div>
              <button
                onClick={enqueueBlogJob}
                disabled={enqueueBusy}
                data-testid="blog-queue-enqueue"
                className="h-11 px-4 rounded-xl bg-[#1C1917] hover:bg-[#0A0A0A] text-white text-sm font-medium flex items-center gap-2 transition disabled:opacity-60"
              >
                <Sparkle size={16} weight="fill" />
                {enqueueBusy ? "Envoi…" : `Générer ${queueCount} article${queueCount > 1 ? "s" : ""}`}
              </button>
            </div>
          </div>

          {queueJobs.length > 0 && (
            <div className="mt-5 border-t border-neutral-100 pt-4">
              <div className="text-[10px] uppercase tracking-[0.2em] text-neutral-500 mb-3">
                Jobs récents ({queueJobs.length})
              </div>
              <div className="space-y-2 max-h-72 overflow-auto">
                {queueJobs.slice(0, 20).map((j) => (
                  <div
                    key={j.id}
                    data-testid={`blog-job-${j.status}`}
                    className="flex items-center justify-between gap-3 px-3 py-2 rounded-lg bg-neutral-50 text-[12px]"
                  >
                    <div className="flex items-center gap-2 min-w-0 flex-1">
                      <span
                        className={
                          j.status === "completed"
                            ? "h-2 w-2 rounded-full bg-emerald-500"
                            : j.status === "running"
                            ? "h-2 w-2 rounded-full bg-amber-500 animate-pulse"
                            : j.status === "failed"
                            ? "h-2 w-2 rounded-full bg-red-500"
                            : "h-2 w-2 rounded-full bg-neutral-300"
                        }
                      />
                      <span className="font-medium text-neutral-700 capitalize">{j.status}</span>
                      <span className="text-neutral-500 truncate">
                        · {j.pillar || "?"} · {j.articles_done || 0}/{j.articles_planned} articles
                        {j.language ? ` · ${j.language}` : ""}
                      </span>
                    </div>
                    <div className="text-neutral-400 text-[11px] tabular-nums whitespace-nowrap">
                      {j.progress || 0}%
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="flex items-end justify-between gap-4 mb-8 flex-wrap">
          <div>
            <div className="text-[11px] uppercase tracking-[0.2em] text-neutral-500 mb-2">Contenu éditorial</div>
            <h1 className="text-3xl md:text-4xl font-semibold text-neutral-900" style={{ fontFamily: "'Fraunces', serif" }}>
              Le Journal
            </h1>
            <p className="text-sm text-neutral-500 mt-2">
              Les articles alimentent la page `/blog` de votre boutique et participent au SEO.
            </p>
          </div>
          <div className="flex gap-2 flex-wrap">
            <a href={`/shop/${siteId}/blog`} target="_blank" rel="noreferrer"
               className="h-11 px-4 rounded-xl bg-white border border-neutral-200 hover:border-[#B84B31] text-neutral-900 text-sm font-medium flex items-center gap-2 transition" data-testid="preview-blog">
              <Eye size={16} /> Voir le blog
            </a>
            <button
              onClick={() => autoPlan(3)}
              disabled={autoPlanLoading}
              data-testid="auto-plan-btn"
              className="h-11 px-4 rounded-xl bg-gradient-to-br from-[#1C1917] to-[#44403C] hover:from-[#0A0A0A] text-white text-sm font-medium flex items-center gap-2 transition disabled:opacity-60"
              title="Génère 1 pilier + 3 satellites depuis vos mots-clés SEO"
            >
              <Sparkle size={16} weight="fill" />
              {autoPlanLoading ? "Génération en cours…" : "Générer tout le blog (IA)"}
            </button>
            <button onClick={() => setAiOpen(true)} data-testid="ai-draft-btn"
                    className="h-11 px-4 rounded-xl bg-white border border-neutral-200 hover:border-[#B84B31] text-neutral-900 text-sm font-medium flex items-center gap-2 transition">
              <Sparkle size={16} weight="duotone" /> Rédiger 1 article
            </button>
            <button onClick={() => setEditing({ _isNew: true, title: "", category: "Guide d'achat", read_minutes: 4, body: "" })} data-testid="new-post-btn"
                    className="h-11 px-4 rounded-xl bg-neutral-900 hover:bg-neutral-800 text-white text-sm font-medium flex items-center gap-2 transition">
              <Plus size={16} weight="bold" /> Nouvel article
            </button>
          </div>
        </div>

        {toast && (
          <div data-testid="blog-toast"
               className={`mb-5 px-4 py-3 rounded-xl text-sm font-medium flex items-center gap-2 ${
                 toast.type === "ok" ? "bg-emerald-50 text-emerald-900 border border-emerald-200" : "bg-rose-50 text-rose-900 border border-rose-200"
               }`}>
            {toast.type === "ok" ? <CheckCircle size={16} weight="fill" /> : <Warning size={16} weight="fill" />}
            {toast.msg}
          </div>
        )}

        {autoPlanLoading && (
          <div
            data-testid="auto-plan-progress"
            className="mb-5 px-4 py-3 rounded-xl border border-neutral-900/20 bg-white flex items-center gap-3 text-sm"
          >
            <Sparkle size={18} weight="fill" className="text-neutral-900 animate-pulse" />
            <div className="flex-1">
              <div className="font-semibold text-neutral-900">
                L'IA rédige votre blog complet…
              </div>
              <div className="text-xs text-neutral-500 mt-0.5">
                {autoPlanJob?.pillar_keyword
                  ? `Pilier : « ${autoPlanJob.pillar_keyword} » · ${autoPlanJob?.expected_count || "plusieurs"} article(s) en préparation`
                  : "Analyse des mots-clés SEO…"}
                {autoPlanJob?.status && autoPlanJob.status !== "pending" && ` · statut : ${autoPlanJob.status}`}
              </div>
            </div>
            <Clock size={18} weight="regular" className="text-neutral-400" />
          </div>
        )}

        {/* CLUSTER MENSUEL — carte premium monochrome éditoriale */}
        <div
          data-testid="monthly-cluster-card"
          className="mb-8 bg-white rounded-2xl overflow-hidden"
          style={{ border: "1px solid #E5E5E5" }}
        >
          <div className="grid grid-cols-1 md:grid-cols-[1.4fr_1fr]">
            {/* Left : content + CTA */}
            <div className="p-7 md:p-9" style={{ borderRight: "1px solid #E5E5E5" }}>
              <div className="flex items-center gap-3 mb-4">
                <span className="h-px w-8" style={{ background: "#0A0A0A" }} />
                <span className="text-[10px] uppercase tracking-[0.35em] font-medium text-neutral-900">
                  Cluster de contenu mensuel
                </span>
              </div>
              <h2
                className="text-[26px] md:text-[32px] leading-[1.1] tracking-[-0.015em] text-neutral-900 mb-4"
                style={{ fontFamily: "'Fraunces', Georgia, serif" }}
              >
                5 articles premium, publiés chaque mois sans effort.
              </h2>
              <p className="text-[14px] leading-[1.7] text-neutral-600 mb-6 max-w-xl">
                Un pilier de référence + 4 satellites finement liés entre eux. Les keywords
                déjà utilisés sont automatiquement exclus, pour cibler à chaque cycle les
                intentions de recherche <span className="font-semibold text-neutral-900">E-E-A-T</span> non encore couvertes.
                Effet cumulatif : <span className="font-semibold text-neutral-900">×3 sur le volume SEO en 90 jours</span>.
              </p>

              <div className="flex items-center gap-3 flex-wrap">
                <button
                  onClick={generateMonthlyCluster}
                  disabled={clusterBusy || autoPlanLoading}
                  data-testid="cluster-monthly-btn"
                  className="h-11 px-5 bg-neutral-900 hover:bg-black text-white text-[13px] font-semibold tracking-wide flex items-center gap-2 transition disabled:opacity-60"
                  style={{ borderRadius: "2px" }}
                >
                  <Stack size={16} weight="fill" />
                  {clusterBusy ? "Lancement…" : "Générer mon cluster mensuel"}
                </button>

                <label
                  className="flex items-center gap-2.5 h-11 px-4 cursor-pointer select-none text-[13px]"
                  style={{ border: "1px solid #E5E5E5", borderRadius: "2px" }}
                  data-testid="auto-cluster-toggle"
                >
                  <input
                    type="checkbox"
                    checked={!!clusterStatus?.auto_enabled}
                    onChange={toggleAutoCluster}
                    className="sr-only"
                  />
                  <span
                    className="w-9 h-5 rounded-full relative transition"
                    style={{ background: clusterStatus?.auto_enabled ? "#0A0A0A" : "#D4D4D4" }}
                  >
                    <span
                      className="absolute top-[2px] w-4 h-4 rounded-full bg-white transition-all"
                      style={{ left: clusterStatus?.auto_enabled ? "18px" : "2px" }}
                    />
                  </span>
                  <span className="font-medium text-neutral-900">Auto-publier chaque mois</span>
                </label>
              </div>
            </div>

            {/* Right : status / schedule */}
            <div className="p-7 md:p-9 bg-[#F5F5F5]">
              <div className="text-[10px] uppercase tracking-[0.35em] text-neutral-500 mb-4">
                Programme
              </div>
              <div className="space-y-4 text-[13px]">
                <div className="flex items-start gap-3">
                  <CalendarBlank size={16} weight="regular" className="text-neutral-900 mt-[2px] shrink-0" />
                  <div>
                    <div className="text-neutral-500">Prochain cluster automatique</div>
                    <div className="font-semibold text-neutral-900 mt-0.5">
                      {clusterStatus?.auto_enabled && clusterStatus?.next_scheduled_at
                        ? fmtDate(clusterStatus.next_scheduled_at)
                        : <span className="text-neutral-400 font-normal">Désactivé</span>}
                    </div>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <Clock size={16} weight="regular" className="text-neutral-900 mt-[2px] shrink-0" />
                  <div>
                    <div className="text-neutral-500">Dernier cluster lancé</div>
                    <div className="font-semibold text-neutral-900 mt-0.5">
                      {clusterStatus?.last_scheduled_run_at || clusterStatus?.last_manual_run_at
                        ? fmtDate(clusterStatus?.last_scheduled_run_at || clusterStatus?.last_manual_run_at)
                        : <span className="text-neutral-400 font-normal">Aucun encore</span>}
                    </div>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <Stack size={16} weight="regular" className="text-neutral-900 mt-[2px] shrink-0" />
                  <div>
                    <div className="text-neutral-500">Historique</div>
                    <div className="font-semibold text-neutral-900 mt-0.5">
                      {clusterStatus?.recent_jobs?.length || 0} cluster(s) sur ce site
                    </div>
                  </div>
                </div>
              </div>

              {clusterStatus?.recent_jobs?.length > 0 && (
                <div className="mt-5 pt-5" style={{ borderTop: "1px solid #E5E5E5" }}>
                  <div className="text-[10px] uppercase tracking-[0.35em] text-neutral-500 mb-3">
                    Runs récents
                  </div>
                  <ul className="space-y-2">
                    {clusterStatus.recent_jobs.slice(0, 3).map((j) => (
                      <li key={j.id} className="flex items-start justify-between gap-3 text-[12px]">
                        <span className="text-neutral-700 line-clamp-1 flex-1">
                          {j.pillar_title || j.pillar_keyword || "Cluster"}
                        </span>
                        <span
                          className={`shrink-0 text-[10px] uppercase tracking-wider px-2 py-0.5 ${
                            j.status === "done"
                              ? "bg-emerald-100 text-emerald-800"
                              : j.status === "failed"
                              ? "bg-rose-100 text-rose-800"
                              : "bg-neutral-200 text-neutral-700"
                          }`}
                          style={{ borderRadius: "2px" }}
                        >
                          {j.status}
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
        </div>

        {loading ? (
          <div className="text-center py-16 text-neutral-500">Chargement…</div>
        ) : posts.length === 0 ? (
          <div className="bg-white rounded-2xl border border-dashed border-neutral-200 p-12 text-center">
            <Sparkle size={40} weight="duotone" className="mx-auto mb-3 text-neutral-300" />
            <div className="font-semibold text-neutral-900 mb-2">Aucun article publié</div>
            <div className="text-sm text-neutral-500 mb-5">Démarrez votre SEO avec un premier guide. L'IA peut rédiger un article complet en 30 secondes.</div>
            <button onClick={() => setAiOpen(true)} className="inline-flex items-center gap-2 h-11 px-5 rounded-xl bg-neutral-900 text-white text-sm font-medium">
              <Sparkle size={16} weight="duotone" /> Commencer avec l'IA
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4" data-testid="blog-posts-list">
            {posts.map((p) => (
              <div key={p.slug} className="bg-white rounded-2xl border border-neutral-200 p-5" data-testid={`post-card-${p.slug}`}>
                <div className="flex items-start justify-between gap-3 mb-2">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 text-[11px] uppercase tracking-widest text-neutral-500 mb-2">
                      <span>{p.category}</span>
                      {p.read_minutes && <><span>·</span><Clock size={11} weight="bold" /> {p.read_minutes} min</>}
                      {p.ai_generated && <><span>·</span><Sparkle size={11} weight="fill" className="text-violet-600" /> IA</>}
                    </div>
                    <h3 className="font-semibold text-neutral-900 leading-tight mb-1">{p.title}</h3>
                    <p className="text-xs text-neutral-500 line-clamp-2">{p.excerpt}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2 mt-4 pt-3 border-t border-neutral-100">
                  <a href={`/shop/${siteId}/blog/${p.slug}`} target="_blank" rel="noreferrer"
                     className="flex-1 h-9 rounded-lg bg-white border border-neutral-200 hover:border-[#B84B31] text-[13px] text-neutral-700 flex items-center justify-center gap-1.5">
                    <Eye size={13} /> Voir
                  </a>
                  <button onClick={() => setEditing({ ...p })} data-testid={`edit-${p.slug}`}
                          className="flex-1 h-9 rounded-lg bg-white border border-neutral-200 hover:border-[#B84B31] text-[13px] text-neutral-900 flex items-center justify-center gap-1.5">
                    <PencilSimple size={13} /> Éditer
                  </button>
                  <button onClick={() => remove(p)} data-testid={`delete-${p.slug}`}
                          className="h-9 w-9 rounded-lg border border-neutral-200 hover:border-rose-300 hover:text-rose-600 text-neutral-500 flex items-center justify-center">
                    <Trash size={13} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Edit drawer */}
      {editing && (
        <div className="fixed inset-0 z-50 flex" data-testid="edit-drawer">
          <div className="flex-1 bg-black/40" onClick={() => setEditing(null)} />
          <div className="w-full max-w-2xl bg-white h-full overflow-y-auto shadow-2xl flex flex-col">
            <div className="flex items-center justify-between p-5 border-b border-neutral-100">
              <div className="font-semibold">{editing._isNew ? "Nouvel article" : "Modifier l'article"}</div>
              <button onClick={() => setEditing(null)} className="w-9 h-9 rounded-full hover:bg-neutral-100 flex items-center justify-center">
                <X size={18} />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-6 space-y-4">
              <Field label="Titre *" value={editing.title} onChange={(v) => setEditing({ ...editing, title: v })} testId="input-title" />
              <Field label="Catégorie" value={editing.category || ""} onChange={(v) => setEditing({ ...editing, category: v })} testId="input-category" />
              <Field label="Image (URL)" value={editing.image || ""} onChange={(v) => setEditing({ ...editing, image: v })} testId="input-image" />
              <Field label="Extrait (affiché sur les cards)" value={editing.excerpt || ""} onChange={(v) => setEditing({ ...editing, excerpt: v })} textarea rows={2} testId="input-excerpt" />
              <Field label="Contenu (Markdown — ## titres, **gras**, - puces)" value={editing.body || ""} onChange={(v) => setEditing({ ...editing, body: v })} textarea rows={15} testId="input-body" />
              <div className="grid grid-cols-2 gap-4">
                <Field label="Temps de lecture (min)" type="number" value={editing.read_minutes || 4} onChange={(v) => setEditing({ ...editing, read_minutes: Number(v) || 4 })} testId="input-read" />
                <Field label="Auteur" value={editing.author || ""} onChange={(v) => setEditing({ ...editing, author: v })} testId="input-author" />
              </div>
            </div>
            <div className="p-5 border-t border-neutral-100 flex gap-2">
              <button onClick={() => setEditing(null)} className="flex-1 h-11 rounded-xl border border-neutral-200 text-sm font-medium">Annuler</button>
              <button onClick={save} data-testid="save-post"
                      className="flex-1 h-11 rounded-xl bg-neutral-900 text-white text-sm font-medium flex items-center justify-center gap-1.5 hover:bg-neutral-800">
                <FloppyDisk size={15} /> Enregistrer
              </button>
            </div>
          </div>
        </div>
      )}

      {/* AI draft modal */}
      {aiOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-6 bg-black/50" data-testid="ai-modal">
          <div className="bg-white rounded-2xl w-full max-w-lg p-6 shadow-2xl">
            <div className="flex items-center gap-2 mb-4">
              <Sparkle size={20} weight="duotone" className="text-violet-600" />
              <h3 className="font-semibold text-lg">Rédiger avec l'IA</h3>
            </div>
            <p className="text-sm text-neutral-500 mb-5">L'IA rédige un article SEO optimisé (structure H2/H3, mini-FAQ, meta title/description) en ~30 secondes.</p>
            <div className="space-y-4">
              <Field label="Mot-clé cible *" placeholder="ex: fauteuil releveur remboursement" value={aiForm.keyword} onChange={(v) => setAiForm({ ...aiForm, keyword: v })} testId="ai-keyword" />
              <Field label="Angle (optionnel)" placeholder="ex: guide d'achat, FAQ, comparatif" value={aiForm.angle} onChange={(v) => setAiForm({ ...aiForm, angle: v })} testId="ai-angle" />
              <div>
                <label className="block text-[13px] font-medium text-neutral-900 mb-1.5">Longueur</label>
                <div className="flex gap-2">
                  {[{v:"short",l:"Court (600-800 mots)"},{v:"medium",l:"Moyen (1000-1400 mots)"},{v:"long",l:"Long (1800-2400 mots)"}].map((opt) => (
                    <button key={opt.v} onClick={() => setAiForm({ ...aiForm, length: opt.v })}
                            className={`flex-1 h-10 px-3 rounded-lg border text-[12px] font-medium transition ${aiForm.length === opt.v ? "bg-neutral-900 text-white border-neutral-900" : "bg-white border-neutral-200 text-neutral-600"}`}>
                      {opt.l}
                    </button>
                  ))}
                </div>
              </div>
            </div>
            <div className="flex gap-2 mt-6">
              <button onClick={() => setAiOpen(false)} className="flex-1 h-11 rounded-xl border border-neutral-200 text-sm font-medium">Annuler</button>
              <button onClick={aiGenerate} disabled={!aiForm.keyword || aiLoading} data-testid="ai-generate"
                      className="flex-1 h-11 rounded-xl bg-neutral-900 text-white text-sm font-medium disabled:opacity-50 flex items-center justify-center gap-1.5">
                <Sparkle size={14} weight={aiLoading ? "regular" : "fill"} className={aiLoading ? "animate-pulse" : ""} />
                {aiLoading ? "Rédaction…" : "Générer l'article"}
              </button>
            </div>
          </div>
        </div>
      )}
      <div className="max-w-7xl mx-auto px-6 md:px-10 pb-10">
        <NextStepCTA siteId={siteId} currentKey="content" />
      </div>
    </div>
  );
}

function Field({ label, value, onChange, textarea, rows = 3, type = "text", placeholder, testId }) {
  return (
    <div>
      <label className="block text-[13px] font-medium text-neutral-900 mb-1.5">{label}</label>
      {textarea ? (
        <textarea
          value={value || ""}
          onChange={(e) => onChange(e.target.value)}
          rows={rows}
          placeholder={placeholder}
          data-testid={testId}
          className="w-full px-3 py-2 rounded-lg border border-neutral-200 focus:outline-none focus:ring-2 focus:ring-neutral-300 text-sm font-mono resize-y"
        />
      ) : (
        <input
          type={type}
          value={value ?? ""}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          data-testid={testId}
          className="w-full h-11 px-3 rounded-lg border border-neutral-200 focus:outline-none focus:ring-2 focus:ring-neutral-300 text-sm"
        />
      )}
    </div>
  );
}
