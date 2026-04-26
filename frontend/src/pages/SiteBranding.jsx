import React, { useEffect, useState } from "react";
import { useParams, Link, useSearchParams } from "react-router-dom";
import { ArrowLeft, ArrowRight, CheckCircle, Storefront as StoreIcon, Rocket, Palette } from "@phosphor-icons/react";
import NextStepCTA from "../components/NextStepCTA";
import { api, apiCall } from "../lib/api";
import IdentityTab from "../components/site-design/IdentityTab";
import LivePreview from "../components/site-design/LivePreview";
import BrandWizard from "../components/BrandWizard";
import LaunchProgress from "../components/LaunchProgress";
import SiteDesignAdvanced from "../components/advanced/SiteDesignAdvanced";
import {
  HeroEditor,
  BenefitsEditor,
  TestimonialsEditor,
} from "../components/BrandingContent";
import HomepageSectionsEditor from "../components/HomepageSectionsEditor";

/**
 * Étape 5 — Identité & design.
 * Tout ce qui est VISUEL : marque, logo, palette, typo + homepage (hero,
 * sections, bénéfices, témoignages). PAS de pages légales (= Étape 6).
 *
 * Phase 2 unification : la page expose 2 onglets.
 *   - "Essentiel" (défaut) — les 6 sections linéaires (identité, homepage,
 *     hero, benefits, testimonials, footer background).
 *   - "Avancé" — l'ancienne `pages/SiteDesign.jsx` absorbée (studio de marque
 *     tabulé : identity / navigation / collections / content). Lazy-mounted
 *     pour ne pas double-fetch `/sites/:id/design` inutilement.
 *
 * Support query string `?tab=simple|avance`. Le paramètre `?step=5` envoyé
 * par le CockpitJourney force l'onglet "simple" (entrée par défaut de l'étape).
 */
export default function SiteBranding() {
  const { id: siteId } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  // Priority : step=5 (CockpitJourney) forces simple. Otherwise tab=avance|simple.
  const forcedSimple = searchParams.get("step") === "5";
  const urlTab = searchParams.get("tab");
  const initialTab = forcedSimple || !urlTab || urlTab === "simple" ? "simple" : "advanced";
  const [brandingTab, setBrandingTab] = useState(initialTab);
  const [site, setSite] = useState(null);
  const [design, setDesign] = useState(null);
  const [loading, setLoading] = useState(true);
  const [publishing, setPublishing] = useState(false);
  const [previewKey, setPreviewKey] = useState(Date.now());
  const [previewOpen, setPreviewOpen] = useState(true);
  const [mode, setMode] = useState("auto");
  const [launchJobId, setLaunchJobId] = useState(null);

  // Sync tab <-> URL. Keep ?step=5 if present (cockpit deep link).
  const switchBrandingTab = (next) => {
    setBrandingTab(next);
    const params = new URLSearchParams(searchParams);
    if (next === "simple") params.delete("tab");
    else params.set("tab", next === "advanced" ? "avance" : next);
    setSearchParams(params, { replace: true });
  };

  const reload = async () => {
    const [{ data: s }, { data: d }] = await Promise.all([
      apiCall(() => api.get(`/sites/${siteId}`)),
      apiCall(() => api.get(`/sites/${siteId}/design`)),
    ]);
    if (s) setSite(s);
    if (d) setDesign(d);
    setPreviewKey(Date.now());
    setLoading(false);
  };

  // `reload` est stable dans la portée de ce composant et dépend uniquement de siteId.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { reload(); }, [siteId]);

  const togglePublish = async () => {
    setPublishing(true);
    const { error } = await apiCall(() =>
      api.patch(`/sites/${siteId}/design/publish`, { published: !design?.published })
    );
    setPublishing(false);
    if (error) return window.alert(error);
    await reload();
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#FAFAFA] flex items-center justify-center">
        <div className="text-sm text-neutral-500">Chargement…</div>
      </div>
    );
  }

  const hasDesign = !!design && (design.brand?.name || design.template_id);

  // Live-launch wizard (keep existing behaviour)
  if (mode === "wizard") {
    return (
      <BrandWizard
        siteId={siteId}
        onLaunch={(jobId) => { setLaunchJobId(jobId); setMode("auto"); }}
        onCancel={() => setMode("auto")}
      />
    );
  }
  if (launchJobId) {
    return (
      <LaunchProgress
        siteId={siteId}
        jobId={launchJobId}
        onDone={() => { setLaunchJobId(null); reload(); }}
      />
    );
  }

  return (
    <div className="min-h-screen bg-[#FAFAFA]">
      <div className="max-w-[1600px] mx-auto px-6 md:px-10 py-8">
        <Link
          to={`/sites/${siteId}`}
          className="inline-flex items-center gap-2 text-sm text-neutral-600 hover:text-neutral-900 mb-6"
          data-testid="back-to-cockpit"
        >
          <ArrowLeft size={14} /> Retour au cockpit
        </Link>

        {/* Banner */}
        <div
          data-testid="step5-header"
          className="mb-8 bg-white p-6 md:p-7"
          style={{ border: "1px solid #E5E5E5", borderRadius: "4px" }}
        >
          <div className="flex items-start justify-between gap-6 flex-wrap">
            <div className="flex-1 min-w-0">
              <div className="text-[10px] uppercase tracking-[0.3em] text-neutral-500 mb-2 font-medium">
                Étape 5 — Identité & design
              </div>
              <div
                className="text-[26px] md:text-[32px] text-neutral-900 leading-tight"
                style={{ fontFamily: "'Fraunces', Georgia, serif" }}
              >
                {site?.name || "Votre marque"}
              </div>
              <p className="text-[13px] text-neutral-600 mt-2 leading-[1.55] max-w-2xl">
                Nom commercial, baseline, voix éditoriale, logo IA, palette,
                typographie — puis la homepage (hero, sections, bénéfices,
                témoignages). Tout est vivant : chaque modification se reflète
                en temps réel dans l'aperçu à droite.
              </p>
              <div className="mt-4 flex items-center gap-3 flex-wrap">
                {hasDesign ? (
                  <span className="inline-flex items-center gap-1.5 text-[11px] font-medium text-emerald-700 bg-emerald-50 px-2.5 py-1" style={{ borderRadius: "2px" }}>
                    <CheckCircle size={11} weight="fill" /> Identité générée
                  </span>
                ) : (
                  <button
                    onClick={() => setMode("wizard")}
                    data-testid="relaunch-wizard"
                    className="h-10 px-4 bg-neutral-900 hover:bg-black text-white text-[13px] font-semibold flex items-center gap-2"
                    style={{ borderRadius: "2px" }}
                  >
                    <Rocket size={14} weight="fill" /> Générer mon site (IA)
                  </button>
                )}
                <Link
                  to={`/sites/${siteId}/pages?step=6`}
                  data-testid="goto-step6"
                  className="h-10 px-4 bg-white border text-[13px] font-medium text-neutral-900 flex items-center gap-2 hover:border-neutral-900 transition"
                  style={{ borderColor: "#E5E5E5", borderRadius: "2px" }}
                >
                  Étape suivante · Rédiger les pages <ArrowRight size={12} />
                </Link>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {hasDesign && (
                <button
                  onClick={togglePublish}
                  disabled={publishing}
                  data-testid="publish-btn"
                  className={`h-10 px-4 text-[13px] font-semibold flex items-center gap-2 disabled:opacity-60 ${
                    design?.published
                      ? "bg-emerald-600 hover:bg-emerald-700 text-white"
                      : "bg-neutral-900 hover:bg-black text-white"
                  }`}
                  style={{ borderRadius: "2px" }}
                >
                  {design?.published ? <><CheckCircle size={13} weight="fill" /> Publié</> : "Publier"}
                </button>
              )}
              <a
                href={`/shop/${siteId}`}
                target="_blank"
                rel="noreferrer"
                className="h-10 px-4 text-[13px] font-medium flex items-center gap-2 bg-white border text-neutral-900 hover:border-neutral-900"
                style={{ borderColor: "#E5E5E5", borderRadius: "2px" }}
                data-testid="preview-storefront"
              >
                <StoreIcon size={13} /> Voir storefront
              </a>
            </div>
          </div>
        </div>

        {/* Tab selector — Phase 2 unification : "Essentiel" (défaut, linéaire) vs "Avancé" (studio tabulé absorbé depuis l'ancien /design) */}
        <div
          className="mb-6 inline-flex gap-1 p-1 bg-white border"
          style={{ borderColor: "#E5E5E5", borderRadius: "4px" }}
          role="tablist"
        >
          <button
            type="button"
            role="tab"
            aria-selected={brandingTab === "simple"}
            data-testid="tab-branding-simple"
            onClick={() => switchBrandingTab("simple")}
            className={`h-9 px-4 text-[13px] font-medium transition ${
              brandingTab === "simple"
                ? "bg-neutral-900 text-white"
                : "text-neutral-600 hover:bg-neutral-50"
            }`}
            style={{ borderRadius: "3px" }}
          >
            Essentiel
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={brandingTab === "advanced"}
            data-testid="tab-branding-advanced"
            onClick={() => switchBrandingTab("advanced")}
            className={`h-9 px-4 text-[13px] font-medium transition ${
              brandingTab === "advanced"
                ? "bg-neutral-900 text-white"
                : "text-neutral-600 hover:bg-neutral-50"
            }`}
            style={{ borderRadius: "3px" }}
          >
            Avancé
          </button>
        </div>

        {brandingTab === "simple" && (
        <>
        <div className="grid grid-cols-1 lg:grid-cols-[1fr_480px] gap-8">
          <div className="space-y-10">
            {/* Identité */}
            <section data-testid="section-identity">
              <SectionHeader
                number="1"
                title="Identité de marque"
                subtitle="Nom, baseline, voix, logo, couleurs, typographie."
              />
              <IdentityTab siteId={siteId} design={design} onReload={reload} onChange={() => setPreviewKey(Date.now())} />
            </section>

            {/* Homepage sections ordering */}
            <section data-testid="section-homepage">
              <SectionHeader
                number="2"
                title="Sections de la page d'accueil"
                subtitle="Choisissez les blocs et leur ordre sur la home."
              />
              <HomepageSectionsEditor siteId={siteId} onChange={() => setPreviewKey(Date.now())} />
            </section>

            {/* Hero editor */}
            <section data-testid="section-hero">
              <SectionHeader
                number="3"
                title="Hero (premier écran)"
                subtitle="Titre principal, sous-titre, CTA, visuel d'ouverture."
              />
              <HeroImageCard siteId={siteId} design={design} onReload={reload} />
              <HeroEditor siteId={siteId} design={design} onReload={reload} onSaved={() => setPreviewKey(Date.now())} />
            </section>

            {/* Benefits */}
            <section data-testid="section-benefits">
              <SectionHeader
                number="4"
                title="Bénéfices clés"
                subtitle="Les 3-4 promesses fortes affichées sous le hero."
              />
              <BenefitsEditor siteId={siteId} design={design} onReload={reload} onSaved={() => setPreviewKey(Date.now())} />
            </section>

            {/* Testimonials */}
            <section data-testid="section-testimonials">
              <SectionHeader
                number="5"
                title="Témoignages"
                subtitle="Social proof client sur la page d'accueil."
              />
              <TestimonialsAiCard siteId={siteId} design={design} onReload={reload} />
              <TestimonialsEditor siteId={siteId} design={design} onReload={reload} onSaved={() => setPreviewKey(Date.now())} />
            </section>

            {/* Footer background image */}
            <section data-testid="section-footer-bg">
              <SectionHeader
                number="6"
                title="Image de fond du footer"
                subtitle="Visuel qui apparaît derrière les liens du footer (overlay sombre automatique)."
              />
              <FooterBackgroundCard siteId={siteId} design={design} onReload={reload} />
            </section>

            {/* Footer CTA */}
            <div
              data-testid="footer-cta"
              className="mt-10 p-6 flex items-center justify-between gap-4 flex-wrap bg-white"
              style={{ border: "1px solid #E5E5E5", borderRadius: "4px" }}
            >
              <div>
                <div
                  className="text-[19px] text-neutral-900"
                  style={{ fontFamily: "'Fraunces', Georgia, serif" }}
                >
                  Prochaine étape : vos pages essentielles
                </div>
                <p className="text-[12.5px] text-neutral-500 mt-1">À propos, FAQ, Contact, CGV, Livraison, Retours — en 1 clic avec l'IA.</p>
              </div>
              <Link
                to={`/sites/${siteId}/pages?step=6`}
                data-testid="goto-step6-footer"
                className="h-11 px-5 bg-neutral-900 hover:bg-black text-white text-[13px] font-semibold flex items-center gap-2"
                style={{ borderRadius: "2px" }}
              >
                Étape 6 · Rédiger les pages <ArrowRight size={13} weight="bold" />
              </Link>
            </div>
          </div>

          {/* Live preview */}
          <aside className="hidden lg:block">
            <div className="sticky top-6">
              <div className="text-[10px] uppercase tracking-[0.3em] text-neutral-500 mb-3 font-medium flex items-center gap-2">
                <Palette size={11} /> Aperçu en direct
              </div>
              <LivePreview siteId={siteId} previewKey={previewKey} />
            </div>
          </aside>
        </div>

        {!previewOpen && (
          <button
            onClick={() => setPreviewOpen(true)}
            className="fixed bottom-6 right-6 z-40 h-12 px-5 rounded-full bg-neutral-900 hover:bg-neutral-800 text-white text-sm font-medium flex items-center gap-2 shadow-xl"
          >
            <StoreIcon size={14} weight="fill" /> Aperçu live
          </button>
        )}
        </>
        )}

        {brandingTab === "advanced" && (
          <div data-testid="branding-advanced-panel">
            <SiteDesignAdvanced embedded={true} />
          </div>
        )}

        <NextStepCTA siteId={siteId} currentKey="branding" />
      </div>
    </div>
  );
}

function SectionHeader({ number, title, subtitle }) {
  return (
    <div className="mb-4 flex items-start gap-4">
      <div
        className="shrink-0 w-9 h-9 flex items-center justify-center text-[14px] font-semibold tabular-nums text-neutral-900"
        style={{ background: "#F5F5F5", borderRadius: "2px", fontFamily: "'Fraunces', Georgia, serif" }}
      >
        {number}
      </div>
      <div>
        <div
          className="text-[18px] text-neutral-900 leading-tight"
          style={{ fontFamily: "'Fraunces', Georgia, serif" }}
        >
          {title}
        </div>
        <p className="text-[12px] text-neutral-500 mt-0.5">{subtitle}</p>
      </div>
    </div>
  );
}

/**
 * CTA card — génère avec l'IA 6 témoignages + portraits niche-adaptatifs.
 * Utilise Claude pour les textes et Nano Banana pour les photos.
 * Mode background : le bouton lance le job et le card poll `ai_status`
 * pour afficher la progression en temps réel (60-120 s).
 */
function TestimonialsAiCard({ siteId, design, onReload }) {
  const [busy, setBusy] = React.useState(false);
  const [toast, setToast] = React.useState("");
  const [progress, setProgress] = React.useState(null); // null | {status, elapsed, items, with_images}
  const pollRef = React.useRef(null);
  const existing = (design?.testimonials?.items || []).length;
  const aiAt = design?.testimonials?.ai_generated_at;
  const initialStatus = design?.testimonials?.ai_status;

  // Auto-poll if a job is already running (e.g. triggered by the wizard)
  React.useEffect(() => {
    if (initialStatus === "running" && !pollRef.current) {
      startPolling();
    }
    // Cleanup on unmount
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialStatus]);

  const startPolling = () => {
    if (pollRef.current) return;
    const startedAt = Date.now();
    setBusy(true);
    setProgress({ status: "running", elapsed: 0, items: 0, with_images: 0 });
    pollRef.current = setInterval(async () => {
      const { data } = await apiCall(() => api.get(`/sites/${siteId}/testimonials`));
      const elapsed = Math.floor((Date.now() - startedAt) / 1000);
      const status = data?.ai_status;
      const items = (data?.items || []).length;
      const withImages = data?.ai_with_images || 0;
      setProgress({ status, elapsed, items, with_images: withImages });
      if (status === "done" || status === "failed") {
        clearInterval(pollRef.current);
        pollRef.current = null;
        setBusy(false);
        if (status === "done") {
          setToast(`✅ ${items} témoignages générés · ${withImages} portraits IA`);
          await onReload();
        } else {
          setToast(`❌ Échec : ${data?.ai_error || "indisponible"}`);
        }
        setTimeout(() => { setToast(""); setProgress(null); }, 6000);
      }
    }, 4000);
  };

  const run = async (force) => {
    if (existing >= 3 && !force) {
      if (!window.confirm(
        `${existing} témoignages existent déjà. Les régénérer va les remplacer par 6 nouveaux générés par l'IA (textes + photos adaptés à votre niche). Continuer ?`
      )) return;
    }
    setToast("");
    const { error, rawDetail } = await apiCall(() =>
      api.post(`/sites/${siteId}/testimonials/ai-generate`, {
        count: 6,
        force: force || existing >= 3,
        skip_images: false,
      })
    );
    if (error) {
      setToast(rawDetail?.detail || error);
      return;
    }
    startPolling();
  };

  // Progress bar : roughly 120 s for 6 items + 6 portraits
  const estimatedTotal = 120;
  const pct = progress
    ? Math.min(100, Math.round((progress.elapsed / estimatedTotal) * 100))
    : 0;

  return (
    <div
      data-testid="testimonials-ai-card"
      className="mb-5 p-5 md:p-6 bg-white"
      style={{ border: "1px solid #E5E5E5", borderRadius: "4px" }}
    >
      <div className="flex items-start justify-between gap-6 flex-wrap">
        <div className="flex-1 min-w-0">
          <div className="text-[10px] uppercase tracking-[0.3em] text-neutral-500 mb-1.5 font-medium">
            Nano Banana + Claude
          </div>
          <div
            className="text-[17px] text-neutral-900 leading-tight"
            style={{ fontFamily: "'Fraunces', Georgia, serif" }}
          >
            Générer des témoignages niche-adaptés avec l'IA
          </div>
          <p className="text-[12.5px] text-neutral-600 mt-1.5 leading-[1.5] max-w-xl">
            6 témoignages authentiques (seniors + aidants) avec portraits
            photographiques générés selon votre niche et vos produits. Le
            texte et les images s'ajustent à chaque marque.
          </p>
          {aiAt && !busy && (
            <div className="text-[11px] text-neutral-400 mt-2">
              Dernier run IA : {new Date(aiAt).toLocaleString("fr-FR", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}
            </div>
          )}
        </div>
        <button
          onClick={() => run(false)}
          disabled={busy}
          data-testid="testimonials-ai-run"
          className="shrink-0 h-10 px-4 bg-neutral-900 hover:bg-black disabled:opacity-60 text-white text-[12.5px] font-semibold flex items-center gap-2"
          style={{ borderRadius: "2px" }}
        >
          {busy ? "Génération IA…" : existing >= 3 ? "Régénérer les avis (IA)" : "✨ Générer 6 avis + photos (IA)"}
        </button>
      </div>

      {/* Progress indicator — visible during the 60-120 s Nano Banana job */}
      {progress && progress.status === "running" && (
        <div className="mt-5" data-testid="testimonials-ai-progress">
          <div className="flex items-center justify-between text-[11px] mb-2">
            <span className="uppercase tracking-[0.25em] font-medium text-neutral-900">
              Génération en cours
            </span>
            <span className="tabular-nums text-neutral-500">
              {progress.elapsed}s <span className="text-neutral-300">/ ~{estimatedTotal}s</span>
            </span>
          </div>
          <div className="h-1.5 w-full overflow-hidden" style={{ background: "#F0F0F0", borderRadius: "999px" }}>
            <div
              className="h-full bg-neutral-900 transition-all duration-500"
              style={{ width: `${pct}%`, borderRadius: "999px" }}
            />
          </div>
          <div className="mt-2 flex items-center gap-2 text-[11.5px] text-neutral-500">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-neutral-900 opacity-60" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-neutral-900" />
            </span>
            {progress.items > 0
              ? `Textes rédigés · ${progress.with_images} portraits générés…`
              : "Claude rédige les 6 témoignages…"}
          </div>
        </div>
      )}

      {toast && (
        <div
          data-testid="testimonials-ai-toast"
          className={`mt-3 text-[12px] font-medium ${toast.startsWith("✅") ? "text-emerald-700" : "text-neutral-700"}`}
        >
          {toast}
        </div>
      )}
    </div>
  );
}

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "";
const DEFAULT_FOOTER_BG = "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=2400&q=80&auto=format&fit=crop";

function resolveImageUrl(raw) {
  if (!raw) return null;
  if (raw.startsWith("http://") || raw.startsWith("https://")) return raw;
  if (raw.startsWith("/api/")) return `${BACKEND_URL}${raw}`;
  return raw;
}

/**
 * Footer background image card — upload, URL custom, or reset to default.
 */
function FooterBackgroundCard({ siteId, design, onReload }) {
  const [busy, setBusy] = React.useState(false);
  const [urlInput, setUrlInput] = React.useState("");
  const [toast, setToast] = React.useState("");
  const current = design?.footer?.background_url || null;
  const effective = current || DEFAULT_FOOTER_BG;

  const uploadFile = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setBusy(true);
    setToast("");
    const fd = new FormData();
    fd.append("file", file);
    const { data, error, rawDetail } = await apiCall(() =>
      api.post(`/uploads/image`, fd, { headers: { "Content-Type": "multipart/form-data" } })
    );
    if (error) {
      setBusy(false);
      setToast(rawDetail?.detail || error);
      return;
    }
    await save(data.url);
    setBusy(false);
  };

  const save = async (url) => {
    const { error, rawDetail } = await apiCall(() =>
      api.post(`/sites/${siteId}/design/footer/background`, { background_url: url })
    );
    if (error) {
      setToast(rawDetail?.detail || error);
      return;
    }
    setToast("✅ Image du footer enregistrée");
    setUrlInput("");
    await onReload();
    setTimeout(() => setToast(""), 4000);
  };

  const reset = async () => {
    const { error } = await apiCall(() =>
      api.post(`/sites/${siteId}/design/footer/background`, { background_url: null })
    );
    if (error) { setToast(error); return; }
    setToast("✅ Image réinitialisée");
    await onReload();
    setTimeout(() => setToast(""), 4000);
  };

  return (
    <div
      data-testid="footer-bg-card"
      className="p-5 md:p-6 bg-white"
      style={{ border: "1px solid #E5E5E5", borderRadius: "4px" }}
    >
      {/* Preview */}
      <div
        className="relative overflow-hidden mb-4"
        style={{ aspectRatio: "21 / 9", borderRadius: "4px", background: "#0A0A0A" }}
        data-testid="footer-bg-preview"
      >
        <img
          src={resolveImageUrl(effective)}
          alt="Footer background"
          className="absolute inset-0 w-full h-full object-cover"
          loading="lazy"
        />
        <div className="absolute inset-0" style={{ background: "rgba(10, 10, 10, 0.78)" }} />
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-white/80 text-[11px] uppercase tracking-[0.35em] font-medium">
            Aperçu de l'overlay
          </span>
        </div>
        {!current && (
          <span
            className="absolute top-3 left-3 text-[10px] uppercase tracking-[0.2em] font-medium px-2 py-1 text-white/70"
            style={{ background: "rgba(255,255,255,0.1)", borderRadius: "2px", backdropFilter: "blur(6px)" }}
          >
            Image par défaut
          </span>
        )}
      </div>

      {/* Actions */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <label
          className="h-11 px-4 border cursor-pointer flex items-center justify-center gap-2 hover:border-neutral-900 transition text-[13px] font-medium text-neutral-900"
          style={{ borderColor: "#E5E5E5", borderRadius: "2px", opacity: busy ? 0.6 : 1 }}
          data-testid="footer-bg-upload-label"
        >
          <input type="file" accept="image/*" className="hidden" onChange={uploadFile} disabled={busy} data-testid="footer-bg-upload-input" />
          {busy ? "Upload en cours…" : "Téléverser une image"}
        </label>
        <div className="flex gap-2">
          <input
            type="url"
            placeholder="…ou coller une URL publique"
            value={urlInput}
            onChange={(e) => setUrlInput(e.target.value)}
            className="flex-1 h-11 px-3 border text-[13px] text-neutral-900 outline-none focus:border-neutral-900"
            style={{ borderColor: "#E5E5E5", borderRadius: "2px" }}
            data-testid="footer-bg-url-input"
          />
          <button
            onClick={() => urlInput && save(urlInput)}
            disabled={!urlInput || busy}
            className="h-11 px-4 bg-neutral-900 hover:bg-black disabled:opacity-40 text-white text-[12.5px] font-semibold"
            style={{ borderRadius: "2px" }}
            data-testid="footer-bg-url-save"
          >
            Enregistrer
          </button>
        </div>
      </div>
      {current && (
        <button
          onClick={reset}
          className="mt-3 text-[11.5px] text-neutral-500 hover:text-neutral-900 underline underline-offset-2"
          data-testid="footer-bg-reset"
        >
          Réinitialiser l'image (revenir à celle par défaut)
        </button>
      )}
      {toast && (
        <div
          className={`mt-3 text-[12px] font-medium ${toast.startsWith("✅") ? "text-emerald-700" : "text-rose-600"}`}
          data-testid="footer-bg-toast"
        >
          {toast}
        </div>
      )}
    </div>
  );
}

/**
 * Hero image card — shows current hero image + button to regenerate it via
 * Nano Banana with a progress indicator during the 20-60s generation.
 */
function HeroImageCard({ siteId, design, onReload }) {
  const [busy, setBusy] = React.useState(false);
  const [elapsed, setElapsed] = React.useState(0);
  const [toast, setToast] = React.useState("");
  const timerRef = React.useRef(null);
  const current = design?.hero?.image || null;

  React.useEffect(() => () => { if (timerRef.current) clearInterval(timerRef.current); }, []);

  const regen = async () => {
    if (current && !window.confirm("Régénérer une nouvelle image hero via Nano Banana ? Cela remplacera l'image actuelle.")) return;
    setBusy(true);
    setElapsed(0);
    setToast("");
    const startedAt = Date.now();
    timerRef.current = setInterval(() => {
      setElapsed(Math.floor((Date.now() - startedAt) / 1000));
    }, 1000);
    const { error, rawDetail } = await apiCall(() =>
      api.post(`/sites/${siteId}/design/generate-hero-image`, { tweak: "" })
    );
    clearInterval(timerRef.current);
    timerRef.current = null;
    setBusy(false);
    if (error) {
      setToast(rawDetail?.detail || error);
      return;
    }
    setToast("✅ Image hero régénérée");
    await onReload();
    setTimeout(() => setToast(""), 4000);
  };

  const estimatedTotal = 45;
  const pct = busy ? Math.min(100, Math.round((elapsed / estimatedTotal) * 100)) : 0;

  return (
    <div
      data-testid="hero-image-card"
      className="mb-5 p-5 md:p-6 bg-white"
      style={{ border: "1px solid #E5E5E5", borderRadius: "4px" }}
    >
      <div className="flex items-start justify-between gap-6 flex-wrap">
        <div className="flex items-start gap-4 flex-1 min-w-0">
          <div
            className="w-24 h-24 md:w-28 md:h-28 shrink-0 overflow-hidden"
            style={{ background: "#F5F5F5", borderRadius: "2px" }}
          >
            {current ? (
              <img src={resolveImageUrl(current)} alt="Hero" className="w-full h-full object-cover" loading="lazy" />
            ) : (
              <div className="w-full h-full flex items-center justify-center text-neutral-300 text-[10px] uppercase tracking-wider">
                Pas d'image
              </div>
            )}
          </div>
          <div className="min-w-0 flex-1">
            <div className="text-[10px] uppercase tracking-[0.3em] text-neutral-500 mb-1.5 font-medium">Nano Banana · lifestyle 3:2</div>
            <div className="text-[16px] text-neutral-900 leading-tight" style={{ fontFamily: "'Fraunces', Georgia, serif" }}>
              Image hero (premier écran)
            </div>
            <p className="text-[12.5px] text-neutral-600 mt-1.5 leading-[1.5]">
              Générée par IA au moment du wizard. Elle sert aussi de fallback pour le fond du footer si aucune image custom n'est définie.
            </p>
          </div>
        </div>
        <button
          onClick={regen}
          disabled={busy}
          data-testid="hero-image-regen"
          className="shrink-0 h-10 px-4 bg-neutral-900 hover:bg-black disabled:opacity-60 text-white text-[12.5px] font-semibold"
          style={{ borderRadius: "2px" }}
        >
          {busy ? "Génération…" : current ? "Régénérer (IA)" : "Générer (IA)"}
        </button>
      </div>

      {busy && (
        <div className="mt-5" data-testid="hero-image-progress">
          <div className="flex items-center justify-between text-[11px] mb-2">
            <span className="uppercase tracking-[0.25em] font-medium text-neutral-900">Nano Banana en cours</span>
            <span className="tabular-nums text-neutral-500">
              {elapsed}s <span className="text-neutral-300">/ ~{estimatedTotal}s</span>
            </span>
          </div>
          <div className="h-1.5 w-full overflow-hidden" style={{ background: "#F0F0F0", borderRadius: "999px" }}>
            <div
              className="h-full bg-neutral-900 transition-all duration-500"
              style={{ width: `${pct}%`, borderRadius: "999px" }}
            />
          </div>
        </div>
      )}

      {toast && (
        <div
          className={`mt-3 text-[12px] font-medium ${toast.startsWith("✅") ? "text-emerald-700" : "text-rose-600"}`}
          data-testid="hero-image-toast"
        >
          {toast}
        </div>
      )}
    </div>
  );
}

