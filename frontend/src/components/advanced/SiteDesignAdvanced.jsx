import React, { useEffect, useState } from "react";
import { useParams, Link, useSearchParams } from "react-router-dom";
import {
  ArrowLeft, PaintBrush, CheckCircle, Storefront as StoreIcon, Rocket, Sparkle, ArrowClockwise, DotsThreeOutline,
} from "@phosphor-icons/react";
import { api, apiCall } from "../../lib/api";
import BrandingContent from "../BrandingContent";
import BrandWizard from "../BrandWizard";
import LaunchProgress from "../LaunchProgress";
import { TABS } from "../site-design/constants";
import LivePreview from "../site-design/LivePreview";
import IdentityTab from "../site-design/IdentityTab";
import NavigationTab from "../site-design/NavigationTab";
import CollectionsTab from "../site-design/CollectionsTab";

/**
 * SiteDesignAdvanced — anciennement `pages/SiteDesign.jsx`.
 *
 * Absorbé en Phase 2 comme onglet "Avancé" de SiteBranding. N'est plus exposé
 * directement comme page. La route `/sites/:id/design` redirige vers
 * `/sites/:id/branding?tab=avance` (voir App.js).
 *
 * Props :
 * - `embedded` (boolean, défaut `false`) — quand `true`, masque le wrapper
 *   min-h-screen, le bouton retour cockpit, le titre principal et les CTAs
 *   "Publier" / "Voir storefront" (déjà présents dans le parent SiteBranding).
 *   Le secondary-actions menu (template-mode, enrich-homepage, relaunch-wizard)
 *   et les 4 onglets internes (identity / navigation / collections / content)
 *   sont toujours affichés.
 */
export default function SiteDesignAdvanced({ embedded = false }) {
  const { id: siteId } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const urlTab = searchParams.get("tab") || "identity";
  const currentStep = searchParams.get("step"); // "5" | "6" | null
  const [design, setDesign] = useState(null);
  const [site, setSite] = useState(null);
  const [siteName, setSiteName] = useState("");
  const [loading, setLoading] = useState(true);
  const [publishing, setPublishing] = useState(false);
  const [tab, setTab] = useState(urlTab);
  const [previewKey, setPreviewKey] = useState(Date.now());
  const [previewOpen, setPreviewOpen] = useState(true);
  const [secondaryOpen, setSecondaryOpen] = useState(false);
  // Enrich-homepage one-shot
  const [enriching, setEnriching] = useState(false);
  const [enrichToast, setEnrichToast] = useState("");
  // Wizard / launch state
  const [mode, setMode] = useState("auto"); // "wizard" | "advanced" | "auto"
  const [launchJobId, setLaunchJobId] = useState(null);

  // Sync tab with URL query param (so cockpit journey links land on the right tab)
  useEffect(() => {
    if (urlTab && urlTab !== tab) {
      setTab(urlTab);
    }
  }, [urlTab]); // eslint-disable-line

  const switchTab = (k) => {
    setTab(k);
    const params = new URLSearchParams(searchParams);
    params.set("tab", k);
    setSearchParams(params, { replace: true });
  };

  const reload = async () => {
    const { data } = await apiCall(() => api.get(`/sites/${siteId}/design`));
    if (data) {
      setDesign(data.design || null);
      setSiteName(data.site_name || "");
      setSite(data.site || { id: siteId, name: data.site_name, design: data.design });
    }
    setLoading(false);
    setPreviewKey(Date.now());
  };

  // Check if an orchestration job is already running on mount
  useEffect(() => {
    apiCall(() => api.get(`/sites/${siteId}/design/launch-status`)).then(({ data }) => {
      if (data?.status === "running") {
        setLaunchJobId(data.id);
      }
    });
  }, [siteId]);

  // `reload` est stable dans la portée de ce composant et dépend uniquement de siteId.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { reload(); }, [siteId]);

  const togglePublish = async () => {
    setPublishing(true);
    const { data, error } = await apiCall(() =>
      api.post(`/sites/${siteId}/design/publish`, {})
    );
    setPublishing(false);
    if (error) { window.alert(error); return; }
    setDesign((d) => ({ ...(d || {}), published: data?.published ?? !d?.published }));
  };

  const enrichHomepage = async () => {
    setEnriching(true);
    setEnrichToast("");
    const { data, error } = await apiCall(() =>
      api.post(`/sites/${siteId}/design/ai-enrich-homepage`, {})
    );
    setEnriching(false);
    if (error) {
      setEnrichToast(`Échec : ${error}`);
      return;
    }
    const { enriched = {} } = data || {};
    setEnrichToast(
      `✓ Homepage enrichie — ${enriched.press_mentions_count || 0} médias · portrait fondateur · manifeste · ${enriched.values_count || 0} valeurs`
    );
    await reload();
    setTimeout(() => setEnrichToast(""), 6000);
  };

  const [pagesBusy, setPagesBusy] = useState(false);
  const pollPagesJob = (jobId) => {
    const startAt = Date.now();
    const maxMs = 4 * 60 * 1000;
    const tick = async () => {
      const { data, error } = await apiCall(() =>
        api.get(`/sites/${siteId}/design/generate-pages/${jobId}`)
      );
      if (error) { setPagesBusy(false); setEnrichToast(`Échec : ${error}`); return; }
      if (data.status === "done") {
        setPagesBusy(false);
        const pages = (data.generated_pages || []).join(", ");
        setEnrichToast(`✓ Pages générées : ${pages}`);
        await reload();
        setTimeout(() => setEnrichToast(""), 6000);
        return;
      }
      if (data.status === "failed") {
        setPagesBusy(false);
        setEnrichToast(`Échec : ${data.error || "erreur inconnue"}`);
        return;
      }
      if (Date.now() - startAt < maxMs) {
        setTimeout(tick, 8000);
      } else {
        setPagesBusy(false);
        setEnrichToast("Timeout — recharge dans 1 min si les pages ne sont pas là.");
      }
    };
    setTimeout(tick, 5000);
  };

  const generatePages = async () => {
    // NOTE — Duplicate: canonical access via /sites/:id/pages (CockpitJourney step 6).
    // Kept here for legacy "Avancé" tab, no functional loss.
    if (!window.confirm(
      "Générer le contenu IA des 5 pages statiques (À propos, Contact, Livraison, Retours, FAQ) ?\n\n" +
      "• Durée : environ 60-120 s (en arrière-plan)\n" +
      "• Copy éditorial ton magazine, pensé pour votre niche"
    )) return;
    setPagesBusy(true);
    setEnrichToast("");
    const { data, error, rawDetail } = await apiCall(() =>
      api.post(`/sites/${siteId}/design/generate-pages`, {})
    );
    if (error) { setPagesBusy(false); setEnrichToast(`Échec : ${rawDetail?.detail || error}`); return; }
    setEnrichToast(data?.message || "Rédaction IA lancée…");
    if (data?.job_id) pollPagesJob(data.job_id);
  };

  if (loading) {
    return embedded
      ? <div className="p-6 text-neutral-500">Chargement…</div>
      : <div className="min-h-screen bg-[#FAF7F2] p-10 text-neutral-500">Chargement…</div>;
  }

  const brand = design?.brand || {};
  const hasDesign = !!(brand.name || brand.tagline || brand.baseline || brand.logo_url || brand.primary_color);

  // Orchestration progress screen takes over everything
  if (launchJobId) {
    return (
      <LaunchProgress
        siteId={siteId}
        jobId={launchJobId}
        onDone={() => { setLaunchJobId(null); setMode("advanced"); reload(); }}
        onFailed={() => { setLaunchJobId(null); setMode("advanced"); reload(); }}
      />
    );
  }

  // Wizard is the default view when the design has barely been touched AND the user hasn't
  // explicitly switched to advanced. Once a design exists, we default to advanced.
  const shouldShowWizard = mode === "wizard" || (mode === "auto" && !hasDesign);

  if (shouldShowWizard) {
    const wizardInner = (
      <>
        {!embedded && (
          <>
            <Link to={`/sites/${siteId}`} className="inline-flex items-center gap-2 text-sm text-neutral-600 hover:text-neutral-900 mb-6">
              <ArrowLeft size={14} /> Retour au cockpit
            </Link>
            <div className="text-center mb-8">
              <div className="text-[11px] uppercase tracking-[0.3em] text-violet-600 mb-2 font-medium">Étape 5 · Studio de marque</div>
              <h1 className="text-3xl md:text-4xl font-semibold text-neutral-900">Génère ta boutique sur-mesure en 2 minutes</h1>
              <p className="text-sm text-neutral-500 mt-2 max-w-xl mx-auto">
                Réponds à quelques questions. L'IA prend ensuite en charge logo, palette, homepage, fiches produits, narrative + images premium.
              </p>
            </div>
          </>
        )}
        <BrandWizard
          site={site || { id: siteId, name: siteName, design }}
          onLaunched={(jobId) => setLaunchJobId(jobId)}
          onExit={() => setMode("advanced")}
        />
      </>
    );
    return embedded
      ? <div className="py-4">{wizardInner}</div>
      : (
        <div className="min-h-screen bg-[#FAF7F2] py-10">
          <div className="max-w-[1600px] mx-auto px-6 md:px-10">{wizardInner}</div>
        </div>
      );
  }

  const mainInner = (
    <>
      {!embedded && (
        <Link to={`/sites/${siteId}`} className="inline-flex items-center gap-2 text-sm text-neutral-600 hover:text-neutral-900 mb-6">
          <ArrowLeft size={14} /> Retour au cockpit
        </Link>
      )}

      <div className={`${embedded ? "mb-4" : "mb-6"} flex items-start justify-between gap-6 flex-wrap`}>
        {!embedded && (
          <div>
            <div className="text-[11px] uppercase tracking-[0.25em] text-neutral-500 mb-2 flex items-center gap-2 font-medium">
              <PaintBrush size={12} weight="bold" /> Studio de marque
            </div>
            <h1 className="text-3xl md:text-4xl font-semibold text-neutral-900" style={{ fontFamily: "'Fraunces', serif" }}>
              {siteName || "Ton site"}
            </h1>
          </div>
        )}
        <div className={`flex gap-2 items-center ${embedded ? "ml-auto" : ""}`}>
          {!embedded && hasDesign && (
            <button
              onClick={togglePublish}
              disabled={publishing}
              data-testid="design-publish"
              className={`h-11 px-5 rounded-xl text-sm font-medium flex items-center gap-2 disabled:opacity-60 ${
                design?.published
                  ? "bg-emerald-600 hover:bg-emerald-700 text-white"
                  : "bg-white border border-neutral-300 hover:border-neutral-900 text-neutral-900"
              }`}
            >
              {design?.published ? <><CheckCircle size={14} weight="fill" /> Publié</> : <>Publier</>}
            </button>
          )}
          {!embedded && (
            <a
              href={`/shop/${siteId}`}
              target="_blank"
              rel="noreferrer"
              className="h-11 px-5 rounded-xl bg-white border border-neutral-300 hover:border-neutral-900 text-neutral-900 text-sm font-medium flex items-center gap-2"
            >
              <StoreIcon size={14} /> Voir storefront
            </a>
          )}
          {/* Secondary actions menu — ALWAYS visible (unique value of advanced tab) */}
          <div className="relative">
            <button
              onClick={() => setSecondaryOpen((o) => !o)}
              data-testid="secondary-actions-btn"
              className="h-11 w-11 rounded-xl bg-white border border-neutral-300 hover:border-neutral-900 text-neutral-700 flex items-center justify-center"
              title="Actions avancées"
            >
              <DotsThreeOutline size={18} weight="bold" />
            </button>
            {secondaryOpen && (
              <>
                <div className="fixed inset-0 z-30" onClick={() => setSecondaryOpen(false)} />
                <div
                  data-testid="secondary-actions-menu"
                  className="absolute right-0 top-12 z-40 w-72 bg-white border shadow-xl py-1.5"
                  style={{ borderColor: "#E5E5E5", borderRadius: "4px" }}
                >
                  <div className="px-3 py-2 text-[10px] uppercase tracking-[0.25em] text-neutral-400 font-medium">Style du template</div>
                  {[
                    { key: "monochrome", label: "Monochrome", desc: "Blanc, noir, gris · éditorial" },
                    { key: "brand", label: "Palette", desc: "Couleurs de votre identité" },
                  ].map((opt) => {
                    const active = (design?.template_mode || "monochrome") === opt.key;
                    return (
                      <button
                        key={opt.key}
                        data-testid={`tmpl-mode-${opt.key}`}
                        onClick={async () => {
                          const { error } = await apiCall(() =>
                            api.patch(`/sites/${siteId}/design/template-mode`, { mode: opt.key })
                          );
                          if (error) { window.alert(error); return; }
                          setSecondaryOpen(false);
                          await reload();
                        }}
                        className={`w-full text-left px-3 py-2 hover:bg-neutral-50 flex items-center justify-between gap-3 ${
                          active ? "bg-neutral-50" : ""
                        }`}
                      >
                        <div>
                          <div className="text-[13px] font-medium text-neutral-900">{opt.label}</div>
                          <div className="text-[11px] text-neutral-500">{opt.desc}</div>
                        </div>
                        {active && <CheckCircle size={14} weight="fill" className="text-neutral-900" />}
                      </button>
                    );
                  })}
                  <div className="my-1.5 border-t" style={{ borderColor: "#F0F0F0" }} />
                  <button
                    onClick={() => { setSecondaryOpen(false); enrichHomepage(); }}
                    disabled={enriching}
                    data-testid="ai-enrich-homepage"
                    className="w-full text-left px-3 py-2 hover:bg-neutral-50 flex items-start gap-3 disabled:opacity-60"
                  >
                    <Sparkle size={14} weight="fill" className="text-amber-600 mt-0.5 shrink-0" />
                    <div>
                      <div className="text-[13px] font-medium text-neutral-900">Enrichir la homepage</div>
                      <div className="text-[11px] text-neutral-500">Remplace les fallbacks (presse, fondateur, manifeste)</div>
                    </div>
                  </button>
                  <button
                    onClick={() => { setSecondaryOpen(false); setMode("wizard"); }}
                    data-testid="switch-to-wizard"
                    className="w-full text-left px-3 py-2 hover:bg-neutral-50 flex items-start gap-3"
                  >
                    <Rocket size={14} weight="fill" className="text-violet-600 mt-0.5 shrink-0" />
                    <div>
                      <div className="text-[13px] font-medium text-neutral-900">Relancer le wizard complet</div>
                      <div className="text-[11px] text-neutral-500">Régénérer tout le site en 2 min</div>
                    </div>
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Contextual guidance banner based on active tab */}
      <TabGuidanceBanner
        tab={tab}
        currentStep={currentStep}
        hasDesign={hasDesign}
        hasAbout={!!(design?.pages?.about?.body || design?.pages?.about)}
        onGeneratePages={generatePages}
        pagesBusy={pagesBusy}
        onRelaunchWizard={() => setMode("wizard")}
      />

      {enrichToast && (
        <div
          data-testid="enrich-toast"
          className="mb-4 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900 flex items-start gap-2"
        >
          <Sparkle size={14} weight="fill" className="mt-0.5 shrink-0 text-emerald-600" />
          <div>{enrichToast}</div>
        </div>
      )}

      {/* Tabs nav */}
      <div className="bg-white rounded-2xl border border-neutral-200 p-1.5 mb-6 flex gap-1 overflow-x-auto">
        {TABS.map(({ key, label, Icon }) => (
          <button
            key={key}
            onClick={() => switchTab(key)}
            data-testid={`tab-${key}`}
            className={`h-10 px-4 rounded-xl text-sm font-medium flex items-center gap-2 whitespace-nowrap transition ${
              tab === key
                ? "bg-neutral-900 text-white"
                : "text-neutral-600 hover:bg-neutral-100"
            }`}
          >
            <Icon size={14} weight={tab === key ? "fill" : "duotone"} /> {label}
          </button>
        ))}
      </div>

      {/* Tab content + live preview side-by-side on desktop */}
      <div className={`grid gap-6 ${previewOpen ? "xl:grid-cols-[minmax(0,1fr)_420px]" : "grid-cols-1"}`}>
        <div className="min-w-0">
          {tab === "identity" && (
            <IdentityTab
              siteId={siteId}
              design={design}
              onReload={reload}
              hasDesign={hasDesign}
            />
          )}
          {tab === "navigation" && <NavigationTab siteId={siteId} onChange={reload} />}
          {tab === "collections" && <CollectionsTab siteId={siteId} onChange={reload} />}
          {tab === "content" && <BrandingContent siteId={siteId} design={design} onReload={reload} onChange={reload} />}
        </div>
        {previewOpen && (
          <LivePreview
            siteId={siteId}
            previewKey={previewKey}
            onClose={() => setPreviewOpen(false)}
            onRefresh={() => setPreviewKey(Date.now())}
          />
        )}
      </div>
      {!previewOpen && (
        <button
          onClick={() => setPreviewOpen(true)}
          data-testid="open-preview"
          className="fixed bottom-6 right-6 z-40 h-12 px-5 rounded-full bg-neutral-900 hover:bg-neutral-800 text-white text-sm font-medium flex items-center gap-2 shadow-xl"
        >
          <StoreIcon size={14} weight="fill" /> Aperçu live
        </button>
      )}
    </>
  );

  return embedded
    ? <div>{mainInner}</div>
    : (
      <div className="min-h-screen bg-[#FAF7F2]">
        <div className="max-w-[1600px] mx-auto px-6 md:px-10 py-8">{mainInner}</div>
      </div>
    );
}

/**
 * Contextual banner that tells the user EXACTLY what this tab is for + the
 * single next action to take. Shown at top of each tab — removes the
 * "j'ai 7 boutons et je comprends rien" confusion.
 */
function TabGuidanceBanner({ tab, currentStep, hasDesign, hasAbout, onGeneratePages, pagesBusy, onRelaunchWizard }) {
  const plans = {
    identity: {
      stepLabel: currentStep === "5" ? "Étape 5" : "Onglet",
      title: "Définissez votre identité de marque",
      subtitle: hasDesign
        ? "Votre marque a déjà un nom, une palette et une typo. Ajustez les détails ci-dessous — chaque champ enregistre tout seul."
        : "Pas encore d'identité ? Cliquez \"Relancer le wizard\" pour générer nom + logo + palette + homepage en 2 min, ou remplissez les champs manuellement.",
      cta: hasDesign ? null : { label: "⚡ Relancer le wizard IA", onClick: onRelaunchWizard, testid: "banner-relaunch-wizard" },
    },
    navigation: {
      stepLabel: "Onglet",
      title: "Menu du storefront",
      subtitle: "Choisissez les liens du header et du footer. Vous pouvez pointer vers une collection, un produit, une page, ou une URL custom.",
      cta: null,
    },
    collections: {
      stepLabel: "Onglet",
      title: "Rassemblez vos produits en collections",
      subtitle: "Une collection = un univers cohérent (ex. \"Confort quotidien\", \"Mobilité\"). Sélectionnez les produits concernés et publiez.",
      cta: null,
    },
    content: {
      stepLabel: currentStep === "6" ? "Étape 6" : "Onglet",
      title: "Rédigez les pages essentielles",
      subtitle: hasAbout
        ? "Les pages À propos, Contact, FAQ, Livraison et Retours sont déjà rédigées. Vous pouvez régénérer n'importe quelle section ci-dessous ou les éditer manuellement."
        : "Aucune page statique rédigée pour le moment. Un clic sur le bouton ci-dessous et l'IA rédige les 5 pages (À propos, Contact, Livraison, Retours, FAQ) en 60-120 s, ton éditorial magazine.",
      cta: hasAbout ? null : {
        label: pagesBusy ? "Rédaction IA en cours…" : "✨ Rédiger les 5 pages maintenant (IA)",
        onClick: onGeneratePages,
        testid: "banner-generate-pages",
        disabled: pagesBusy,
      },
    },
  };
  const plan = plans[tab] || plans.identity;
  return (
    <div
      data-testid="tab-guidance-banner"
      className="mb-6 bg-white p-5 md:p-6"
      style={{ border: "1px solid #E5E5E5", borderRadius: "4px" }}
    >
      <div className="flex flex-col md:flex-row md:items-center gap-4 md:gap-6">
        <div className="flex-1 min-w-0">
          <div className="text-[10px] uppercase tracking-[0.3em] text-neutral-500 mb-1.5 font-medium">
            {plan.stepLabel}
          </div>
          <div
            className="text-[19px] md:text-[22px] text-neutral-900 leading-tight"
            style={{ fontFamily: "'Fraunces', Georgia, serif" }}
          >
            {plan.title}
          </div>
          <p className="text-[13px] text-neutral-600 mt-1.5 leading-[1.55] max-w-2xl">
            {plan.subtitle}
          </p>
        </div>
        {plan.cta && (
          <button
            onClick={plan.cta.onClick}
            disabled={plan.cta.disabled}
            data-testid={plan.cta.testid}
            className="shrink-0 h-11 px-5 bg-neutral-900 hover:bg-black disabled:opacity-60 text-white text-[13px] font-semibold flex items-center gap-2 transition"
            style={{ borderRadius: "2px" }}
          >
            {plan.cta.disabled && <ArrowClockwise size={14} className="animate-spin" />}
            {plan.cta.label}
          </button>
        )}
      </div>
    </div>
  );
}
