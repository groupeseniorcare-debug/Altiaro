import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import {
  ArrowLeft, PaintBrush, CheckCircle, Storefront as StoreIcon, Rocket, Sparkle, ArrowClockwise,
} from "@phosphor-icons/react";
import { api, apiCall } from "../lib/api";
import BrandingContent from "../components/BrandingContent";
import BrandWizard from "../components/BrandWizard";
import LaunchProgress from "../components/LaunchProgress";
import { TABS } from "../components/site-design/constants";
import LivePreview from "../components/site-design/LivePreview";
import IdentityTab from "../components/site-design/IdentityTab";
import NavigationTab from "../components/site-design/NavigationTab";
import CollectionsTab from "../components/site-design/CollectionsTab";

export default function SiteDesign() {
  const { id: siteId } = useParams();
  const [design, setDesign] = useState(null);
  const [site, setSite] = useState(null);
  const [siteName, setSiteName] = useState("");
  const [loading, setLoading] = useState(true);
  const [publishing, setPublishing] = useState(false);
  const [tab, setTab] = useState("identity");
  const [previewKey, setPreviewKey] = useState(Date.now());
  const [previewOpen, setPreviewOpen] = useState(true);
  // Enrich-homepage one-shot
  const [enriching, setEnriching] = useState(false);
  const [enrichToast, setEnrichToast] = useState("");
  // Wizard / launch state
  const [mode, setMode] = useState("auto"); // "wizard" | "advanced" | "auto"
  const [launchJobId, setLaunchJobId] = useState(null);

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

  useEffect(() => { reload(); /* eslint-disable-next-line */ }, [siteId]);

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

  if (loading) return <div className="min-h-screen bg-[#FAF7F2] p-10 text-neutral-500">Chargement…</div>;

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
    return (
      <div className="min-h-screen bg-[#FAF7F2] py-10">
        <div className="max-w-[1600px] mx-auto px-6 md:px-10">
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
          <BrandWizard
            site={site || { id: siteId, name: siteName, design }}
            onLaunched={(jobId) => setLaunchJobId(jobId)}
            onExit={() => setMode("advanced")}
          />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#FAF7F2]">
      <div className="max-w-[1600px] mx-auto px-6 md:px-10 py-8">
        <Link to={`/sites/${siteId}`} className="inline-flex items-center gap-2 text-sm text-neutral-600 hover:text-neutral-900 mb-6">
          <ArrowLeft size={14} /> Retour au cockpit
        </Link>

        <div className="mb-6 flex items-start justify-between gap-6 flex-wrap">
          <div>
            <div className="text-[11px] uppercase tracking-[0.2em] text-neutral-500 mb-2 flex items-center gap-2">
              <PaintBrush size={12} weight="bold" /> Étape 5 · Studio de marque
            </div>
            <h1 className="text-3xl md:text-4xl font-semibold text-neutral-900" style={{ fontFamily: "'Fraunces', serif" }}>
              {siteName || "Ton site"}
            </h1>
            <p className="text-sm text-neutral-500 mt-2 max-w-2xl">
              Identité visuelle, navigation, collections et contenu — tout pour une boutique cohérente de bout en bout.
            </p>
          </div>
          <div className="flex gap-2 items-center flex-wrap">
            {/* Template mode toggle — Monochrome (default) vs Brand palette */}
            <div
              className="h-11 rounded-xl p-1 flex items-center gap-0.5 border"
              style={{ borderColor: "#E5E5E5", background: "#FAFAFA" }}
              data-testid="template-mode-toggle"
            >
              {[
                { key: "monochrome", label: "Monochrome" },
                { key: "brand", label: "Palette" },
              ].map((opt) => {
                const active = (design?.template_mode || "monochrome") === opt.key;
                return (
                  <button
                    key={opt.key}
                    onClick={async () => {
                      const { error } = await apiCall(() =>
                        api.patch(`/sites/${siteId}/design/template-mode`, { mode: opt.key })
                      );
                      if (error) { window.alert(error); return; }
                      await reload();
                    }}
                    data-testid={`tmpl-mode-${opt.key}`}
                    className={`h-9 px-3 rounded-lg text-xs font-medium transition ${
                      active
                        ? "bg-white text-neutral-900 shadow-sm"
                        : "text-neutral-500 hover:text-neutral-800"
                    }`}
                    title={opt.key === "monochrome"
                      ? "Blanc, noir, gris · style éditorial magazine"
                      : "Utilise les couleurs de ton identité de marque"}
                  >
                    {opt.label}
                  </button>
                );
              })}
            </div>
            <button
              onClick={enrichHomepage}
              disabled={enriching}
              data-testid="ai-enrich-homepage"
              title="Remplace les fallbacks (presse, fondateur, manifeste…) par de vraies données IA"
              className="h-11 px-4 rounded-xl bg-gradient-to-r from-amber-500 to-rose-500 hover:brightness-110 text-white text-sm font-medium flex items-center gap-2 shadow-md disabled:opacity-60"
            >
              {enriching ? <ArrowClockwise size={14} className="animate-spin" /> : <Sparkle size={14} weight="fill" />}
              {enriching ? "Enrichissement IA…" : "✨ Enrichir la homepage"}
            </button>
            <button
              onClick={() => setMode("wizard")}
              data-testid="switch-to-wizard"
              title="Relancer le wizard pour régénérer tout le site"
              className="h-11 px-4 rounded-xl bg-gradient-to-r from-violet-600 to-indigo-600 hover:brightness-110 text-white text-sm font-medium flex items-center gap-2 shadow-md"
            >
              <Rocket size={14} weight="fill" /> Relancer le wizard
            </button>
            {hasDesign && (
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
            <a
              href={`/shop/${siteId}`}
              target="_blank"
              rel="noreferrer"
              className="h-11 px-5 rounded-xl bg-white border border-neutral-300 hover:border-neutral-900 text-neutral-900 text-sm font-medium flex items-center gap-2"
            >
              <StoreIcon size={14} /> Voir storefront
            </a>
          </div>
        </div>

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
              onClick={() => setTab(key)}
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
      </div>
    </div>
  );
}
