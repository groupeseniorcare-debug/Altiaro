import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import {
  ArrowLeft, PaintBrush, Sparkle, ArrowClockwise, CheckCircle, Image as ImageIcon,
  Palette, ChatCenteredText, Storefront as StoreIcon, UploadSimple,
  List, Rows, Stack, TextT, Plus, Trash, PencilSimple, ArrowRight,
  DotsSixVertical, Link as LinkIcon, Heart, Rocket, Gear,
} from "@phosphor-icons/react";
import { api, apiCall } from "../lib/api";
import BrandingContent from "../components/BrandingContent";
import BrandWizard from "../components/BrandWizard";
import LaunchProgress from "../components/LaunchProgress";

const TABS = [
  { key: "identity", label: "Identité", Icon: PaintBrush },
  { key: "navigation", label: "Navigation", Icon: List },
  { key: "collections", label: "Collections", Icon: Stack },
  { key: "content", label: "Pages & contenu", Icon: ChatCenteredText },
];

const FONT_PAIRS = [
  { heading: "Fraunces", body: "Inter", label: "Éditorial · chaleureux" },
  { heading: "Playfair Display", body: "Source Sans Pro", label: "Classique · premium" },
  { heading: "DM Serif Display", body: "DM Sans", label: "Moderne · élégant" },
  { heading: "Cormorant Garamond", body: "Lato", label: "Luxe · discret" },
  { heading: "Montserrat", body: "Open Sans", label: "Sobre · lisible" },
  { heading: "Lora", body: "Roboto", label: "Premium · accessible" },
];

const PALETTE_PRESETS = [
  { name: "Sénior chaleureux", primary: "#B84B31", secondary: "#E9C46A", bg: "#FAF7F2", text: "#1C1917", accent: "#2A9D8F" },
  { name: "Médical rassurant",  primary: "#1D6A96", secondary: "#81C3D7", bg: "#F7FAFC", text: "#1E293B", accent: "#F59E0B" },
  { name: "Nature apaisant",    primary: "#2A9D8F", secondary: "#E9C46A", bg: "#F5F5F0", text: "#264653", accent: "#E76F51" },
  { name: "Luxe minimal",       primary: "#1A1A1A", secondary: "#C9A66B", bg: "#FFFFFF", text: "#1A1A1A", accent: "#8B0000" },
  { name: "Bien-être doux",     primary: "#D4A5A5", secondary: "#F5E6D3", bg: "#FDFBF7", text: "#3E2723", accent: "#8B7355" },
];

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
          <div className="flex gap-2 items-center">
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

// ==========================================================================
// Live preview — sticky iframe that refreshes on each save/regen
// ==========================================================================
function LivePreview({ siteId, previewKey, onClose, onRefresh }) {
  const src = `/shop/${siteId}?preview=1&v=${previewKey}`;
  return (
    <div className="hidden xl:block" data-testid="live-preview">
      <div className="sticky top-6">
        <div className="bg-white border border-neutral-200 rounded-2xl overflow-hidden shadow-sm">
          <div className="flex items-center justify-between px-3 py-2 border-b border-neutral-100 bg-neutral-50">
            <div className="flex items-center gap-2 text-xs text-neutral-600">
              <div className="flex gap-1">
                <span className="w-2.5 h-2.5 rounded-full bg-red-400" />
                <span className="w-2.5 h-2.5 rounded-full bg-amber-400" />
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-400" />
              </div>
              <span className="font-mono truncate max-w-[180px]">/shop/{siteId.slice(0, 8)}…</span>
            </div>
            <div className="flex items-center gap-1">
              <button onClick={onRefresh} title="Rafraîchir"
                data-testid="preview-refresh"
                className="w-7 h-7 rounded hover:bg-neutral-200 text-neutral-600 flex items-center justify-center">
                <ArrowClockwise size={12} />
              </button>
              <a href={src} target="_blank" rel="noreferrer" title="Ouvrir en nouvel onglet"
                data-testid="preview-external"
                className="w-7 h-7 rounded hover:bg-neutral-200 text-neutral-600 flex items-center justify-center">
                <StoreIcon size={12} />
              </a>
              <button onClick={onClose} title="Fermer l'aperçu"
                data-testid="preview-close"
                className="w-7 h-7 rounded hover:bg-neutral-200 text-neutral-600 flex items-center justify-center text-xs">
                ✕
              </button>
            </div>
          </div>
          <iframe
            key={previewKey}
            src={src}
            title="Aperçu storefront"
            data-testid="preview-iframe"
            className="w-full h-[720px] bg-white"
            loading="lazy"
          />
        </div>
        <div className="text-[11px] text-neutral-400 mt-2 text-center">
          L'aperçu se rafraîchit à chaque modification enregistrée.
        </div>
      </div>
    </div>
  );
}

// ==========================================================================
// TAB 1 — IDENTITY
// ==========================================================================
function IdentityTab({ siteId, design, onReload, hasDesign }) {
  const brand = design?.brand || {};
  const [generating, setGenerating] = useState(false);
  const [genStatus, setGenStatus] = useState("");
  const [initialBrief, setInitialBrief] = useState("");
  const [logoUploading, setLogoUploading] = useState(false);
  const [regeneratingLogo, setRegeneratingLogo] = useState(false);
  const [logoPrompt, setLogoPrompt] = useState("");
  const [saving, setSaving] = useState(false);
  const [skipEmpty, setSkipEmpty] = useState(false);
  const [aiField, setAiField] = useState(null); // key of the field currently being AI-generated
  const [aiTweak, setAiTweak] = useState({});   // { name: "...", tagline: "...", ... }
  const effectiveHasDesign = hasDesign || skipEmpty;
  const [form, setForm] = useState({
    name: brand.name || "",
    tagline: brand.tagline || brand.baseline || "",
    voice: brand.voice || "",
    story: brand.story || "",
    primary_color: brand.primary_color || brand.palette?.primary || "#B84B31",
    secondary_color: brand.secondary_color || brand.palette?.secondary || "#E9C46A",
    background_color: brand.background_color || brand.palette?.background || "#FAF7F2",
    text_color: brand.text_color || brand.palette?.text || "#1C1917",
    accent_color: brand.accent_color || brand.palette?.accent || "#2A9D8F",
    font_heading: brand.font_heading || "Fraunces",
    font_body: brand.font_body || "Inter",
  });

  useEffect(() => {
    setForm({
      name: brand.name || "",
      tagline: brand.tagline || brand.baseline || "",
      voice: brand.voice || "",
      story: brand.story || "",
      primary_color: brand.primary_color || brand.palette?.primary || "#B84B31",
      secondary_color: brand.secondary_color || brand.palette?.secondary || "#E9C46A",
      background_color: brand.background_color || brand.palette?.background || "#FAF7F2",
      text_color: brand.text_color || brand.palette?.text || "#1C1917",
      accent_color: brand.accent_color || brand.palette?.accent || "#2A9D8F",
      font_heading: brand.font_heading || "Fraunces",
      font_body: brand.font_body || "Inter",
    });
  }, [design]); // eslint-disable-line

  const update = (key, value) => setForm((f) => ({ ...f, [key]: value }));

  const saveBrand = async () => {
    setSaving(true);
    const { error } = await apiCall(() => api.patch(`/sites/${siteId}/design/brand`, form));
    setSaving(false);
    if (error) { window.alert(error); return; }
    await onReload();
  };

  const applyPreset = (preset) => {
    setForm((f) => ({
      ...f,
      primary_color: preset.primary,
      secondary_color: preset.secondary,
      background_color: preset.bg,
      text_color: preset.text,
      accent_color: preset.accent,
    }));
  };

  const applyFontPair = (pair) => {
    setForm((f) => ({ ...f, font_heading: pair.heading, font_body: pair.body }));
  };

  const aiGenerate = async (field) => {
    setAiField(field);
    const { data, error } = await apiCall(() =>
      api.post(`/sites/${siteId}/design/ai-field`, { field, tweak: aiTweak[field] || "" })
    );
    setAiField(null);
    if (error) { window.alert(error); return; }
    // For text fields, update the local form immediately
    if (field === "name") update("name", data.value);
    else if (field === "tagline") update("tagline", data.value);
    else if (field === "voice") update("voice", data.value);
    else if (field === "story") update("story", data.value);
    else if (field === "palette") {
      const v = data.value || {};
      setForm((f) => ({
        ...f,
        primary_color: v.primary || f.primary_color,
        secondary_color: v.secondary || f.secondary_color,
        accent_color: v.accent || f.accent_color,
        background_color: v.background || f.background_color,
        text_color: v.text || f.text_color,
      }));
    } else if (field === "font_pair") {
      const v = data.value || {};
      setForm((f) => ({
        ...f,
        font_heading: v.heading || f.font_heading,
        font_body: v.body || f.font_body,
      }));
    }
    await onReload();
  };

  const generateAll = async () => {
    if (hasDesign && !window.confirm("Un design existe déjà. Tout régénérer ?")) return;
    setGenerating(true);
    setGenStatus("Démarrage…");
    const { error } = await apiCall(() =>
      api.post(`/sites/${siteId}/design/generate`, { with_logo: true, tweak: initialBrief })
    );
    if (error) {
      setGenerating(false);
      setGenStatus("");
      window.alert(`Démarrage échoué : ${error}`);
      return;
    }
    setInitialBrief("");
    setGenStatus("Génération IA en cours (30-90s)…");
    const poll = async () => {
      const { data: s } = await apiCall(() => api.get(`/sites/${siteId}/design/generate/status`));
      if (s?.status === "running") { setTimeout(poll, 3000); return; }
      if (s?.status === "done") { setGenerating(false); setGenStatus(""); await onReload(); return; }
      if (s?.status === "failed") { setGenerating(false); setGenStatus(""); window.alert(`Échec : ${s?.error || ""}`); return; }
      setGenerating(false); setGenStatus("");
    };
    setTimeout(poll, 3000);
  };

  const uploadLogo = async (file) => {
    if (!file) return;
    setLogoUploading(true);
    const fd = new FormData();
    fd.append("file", file);
    const { data: upData, error: upErr } = await apiCall(() =>
      api.post(`/uploads/image`, fd, { headers: { "Content-Type": "multipart/form-data" } })
    );
    if (upErr || !upData?.url) { setLogoUploading(false); window.alert(upErr || "Upload échoué"); return; }
    const { error } = await apiCall(() =>
      api.post(`/sites/${siteId}/design/brand/logo`, { logo_url: upData.url })
    );
    setLogoUploading(false);
    if (error) { window.alert(error); return; }
    await onReload();
  };

  const regenerateLogo = async () => {
    setRegeneratingLogo(true);
    const { error } = await apiCall(() =>
      api.post(`/sites/${siteId}/design/regenerate/logo`, { tweak: logoPrompt })
    );
    setRegeneratingLogo(false);
    if (error) { window.alert(error); return; }
    setLogoPrompt("");
    await onReload();
  };

  if (!effectiveHasDesign) {
    return (
      <div className="bg-white border border-neutral-200 rounded-2xl p-10 text-center" data-testid="design-empty">
        <PaintBrush size={40} weight="duotone" className="mx-auto text-neutral-400 mb-4" />
        <h2 className="text-xl font-semibold text-neutral-900 mb-2" style={{ fontFamily: "'Fraunces', serif" }}>
          Ton site n'a pas encore d'identité
        </h2>
        <p className="text-sm text-neutral-600 max-w-lg mx-auto mb-6">
          Laisse Claude générer une première version complète (<strong>nom + baseline</strong>, <strong>palette</strong>, <strong>logo</strong>, <strong>hero + bénéfices + FAQ + témoignages + à propos + SEO</strong>).
          <br />Tu pourras tout éditer ligne par ligne ensuite, ou <button onClick={() => setSkipEmpty(true)}
            data-testid="skip-to-editor"
            className="underline text-neutral-900 hover:text-neutral-600">remplir manuellement →</button>
        </p>
        <div className="max-w-xl mx-auto">
          <textarea
            value={initialBrief}
            onChange={(e) => setInitialBrief(e.target.value)}
            placeholder="(Optionnel) brief · ex. « marque haut de gamme, ton chaleureux, cible 70+ urbains »"
            className="w-full min-h-[72px] p-3 rounded-lg border border-neutral-300 bg-white text-sm resize-y mb-3"
            data-testid="design-initial-brief"
          />
          <button
            onClick={generateAll}
            disabled={generating}
            data-testid="design-generate"
            className="h-11 px-6 rounded-xl bg-neutral-900 hover:bg-neutral-800 text-white text-sm font-medium inline-flex items-center gap-2 disabled:opacity-60"
          >
            {generating ? <ArrowClockwise size={14} className="animate-spin" /> : <Sparkle size={14} weight="fill" />}
            {generating ? (genStatus || "Génération…") : "Générer mon site (IA)"}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="identity-tab">
      {/* Brand basics + Logo */}
      <div className="grid lg:grid-cols-3 gap-5">
        <div className="lg:col-span-2 bg-white border border-neutral-200 rounded-2xl p-5 space-y-4">
          <div className="text-[11px] uppercase tracking-widest text-neutral-500 flex items-center gap-1">
            <Heart size={11} weight="fill" /> Identité de marque
          </div>
          <AiField label="Nom de marque" field="name" aiField={aiField} tweak={aiTweak.name} setTweak={(v) => setAiTweak({ ...aiTweak, name: v })} onGenerate={() => aiGenerate("name")}>
            <input type="text" value={form.name} onChange={(e) => update("name", e.target.value)}
              data-testid="brand-name" maxLength={40}
              className="w-full h-10 px-3 rounded-lg border border-neutral-200 bg-white text-lg font-semibold focus:outline-none focus:border-neutral-900"
              style={{ fontFamily: "'Fraunces', serif" }} />
          </AiField>
          <AiField label="Tagline / baseline (≤ 80 car.)" field="tagline" aiField={aiField} tweak={aiTweak.tagline} setTweak={(v) => setAiTweak({ ...aiTweak, tagline: v })} onGenerate={() => aiGenerate("tagline")}>
            <input type="text" value={form.tagline} onChange={(e) => update("tagline", e.target.value)}
              data-testid="brand-tagline" maxLength={80}
              placeholder="Le confort au quotidien, simplement."
              className="w-full h-10 px-3 rounded-lg border border-neutral-200 bg-white text-sm italic focus:outline-none focus:border-neutral-900" />
          </AiField>
          <AiField label="Ton de voix" field="voice" aiField={aiField} tweak={aiTweak.voice} setTweak={(v) => setAiTweak({ ...aiTweak, voice: v })} onGenerate={() => aiGenerate("voice")}>
            <input type="text" value={form.voice} onChange={(e) => update("voice", e.target.value)}
              data-testid="brand-voice" maxLength={200}
              placeholder="Chaleureux, rassurant, expert, tutoiement"
              className="w-full h-10 px-3 rounded-lg border border-neutral-200 bg-white text-sm focus:outline-none focus:border-neutral-900" />
          </AiField>
          <AiField label="Histoire / storytelling" field="story" aiField={aiField} tweak={aiTweak.story} setTweak={(v) => setAiTweak({ ...aiTweak, story: v })} onGenerate={() => aiGenerate("story")}>
            <textarea value={form.story} onChange={(e) => update("story", e.target.value)}
              data-testid="brand-story" rows={4} maxLength={500}
              placeholder="Fondée en 2024 pour offrir aux seniors des solutions pratiques à prix juste…"
              className="w-full p-3 rounded-lg border border-neutral-200 bg-white text-sm focus:outline-none focus:border-neutral-900 resize-y" />
          </AiField>
        </div>

        {/* Logo */}
        <div className="bg-white border border-neutral-200 rounded-2xl p-5">
          <div className="text-[11px] uppercase tracking-widest text-neutral-500 mb-3 flex items-center gap-1">
            <ImageIcon size={11} weight="duotone" /> Logo
          </div>
          <div className="flex justify-center mb-3">
            {brand.logo_url ? (
              <img src={brand.logo_url} alt="logo" className="h-32 w-32 object-contain rounded-xl bg-neutral-50 border border-neutral-200 p-3" />
            ) : (
              <div className="h-32 w-32 rounded-xl bg-neutral-100 border border-neutral-200 flex items-center justify-center text-neutral-400">
                <ImageIcon size={40} weight="duotone" />
              </div>
            )}
          </div>
          <label className="cursor-pointer w-full h-9 px-3 rounded-lg border border-neutral-200 hover:border-neutral-900 flex items-center justify-center gap-1.5 text-xs text-neutral-700 mb-2">
            <UploadSimple size={12} /> {logoUploading ? "Upload…" : "Uploader mon logo"}
            <input type="file" accept="image/*" className="hidden" data-testid="logo-upload"
              onChange={(e) => uploadLogo(e.target.files?.[0])} />
          </label>
          <input type="text" value={logoPrompt} onChange={(e) => setLogoPrompt(e.target.value)}
            data-testid="logo-prompt"
            placeholder="Prompt logo (ex. « minimaliste, monoline »)"
            className="w-full h-9 px-3 rounded-lg border border-neutral-200 bg-white text-xs mb-2" />
          <button onClick={regenerateLogo} disabled={regeneratingLogo}
            data-testid="regen-logo"
            className="w-full h-9 rounded-lg bg-neutral-900 hover:bg-neutral-800 text-white text-xs font-medium flex items-center justify-center gap-1.5 disabled:opacity-60">
            {regeneratingLogo ? <ArrowClockwise size={12} className="animate-spin" /> : <Sparkle size={12} weight="fill" />}
            {regeneratingLogo ? "Génération…" : "Générer avec Nano Banana"}
          </button>
        </div>
      </div>

      {/* Palette */}
      <div className="bg-white border border-neutral-200 rounded-2xl p-5">
        <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
          <div className="text-[11px] uppercase tracking-widest text-neutral-500 flex items-center gap-1">
            <Palette size={11} /> Palette de couleurs
          </div>
          <div className="flex items-center gap-2">
            <div className="text-[11px] text-neutral-400">Utilisée partout sur le storefront</div>
            <button
              onClick={() => aiGenerate("palette")}
              disabled={aiField === "palette"}
              data-testid="ai-palette"
              className="h-8 px-3 rounded-lg bg-violet-600 hover:bg-violet-700 text-white text-xs font-medium flex items-center gap-1.5 disabled:opacity-60"
            >
              {aiField === "palette" ? <ArrowClockwise size={12} className="animate-spin" /> : <Sparkle size={12} weight="fill" />}
              Palette IA
            </button>
          </div>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-4">
          <ColorPicker label="Primary" value={form.primary_color} onChange={(v) => update("primary_color", v)} />
          <ColorPicker label="Secondary" value={form.secondary_color} onChange={(v) => update("secondary_color", v)} />
          <ColorPicker label="Accent" value={form.accent_color} onChange={(v) => update("accent_color", v)} />
          <ColorPicker label="Background" value={form.background_color} onChange={(v) => update("background_color", v)} />
          <ColorPicker label="Texte" value={form.text_color} onChange={(v) => update("text_color", v)} />
        </div>
        <div className="border-t border-neutral-100 pt-4">
          <div className="text-[11px] uppercase tracking-widest text-neutral-500 mb-2">Presets Silver Economy</div>
          <div className="flex flex-wrap gap-2">
            {PALETTE_PRESETS.map((p) => (
              <button key={p.name} onClick={() => applyPreset(p)}
                data-testid={`preset-${p.name.replace(/\s/g, "-")}`}
                className="flex items-center gap-2 h-9 px-2 rounded-full border border-neutral-200 hover:border-neutral-900 transition bg-white text-xs">
                <div className="flex -space-x-1">
                  {[p.primary, p.secondary, p.accent].map((c) => (
                    <div key={c} className="w-4 h-4 rounded-full border border-white" style={{ background: c }} />
                  ))}
                </div>
                {p.name}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Typography */}
      <div className="bg-white border border-neutral-200 rounded-2xl p-5">
        <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
          <div className="text-[11px] uppercase tracking-widest text-neutral-500 flex items-center gap-1">
            <TextT size={11} /> Typographie
          </div>
          <button
            onClick={() => aiGenerate("font_pair")}
            disabled={aiField === "font_pair"}
            data-testid="ai-fonts"
            className="h-8 px-3 rounded-lg bg-violet-600 hover:bg-violet-700 text-white text-xs font-medium flex items-center gap-1.5 disabled:opacity-60"
          >
            {aiField === "font_pair" ? <ArrowClockwise size={12} className="animate-spin" /> : <Sparkle size={12} weight="fill" />}
            Proposer des typos IA
          </button>
        </div>
        <div className="grid md:grid-cols-2 gap-3 mb-4">
          <Field label="Heading">
            <input type="text" value={form.font_heading} onChange={(e) => update("font_heading", e.target.value)}
              data-testid="font-heading" className="w-full h-10 px-3 rounded-lg border border-neutral-200 bg-white text-sm font-mono" />
          </Field>
          <Field label="Body">
            <input type="text" value={form.font_body} onChange={(e) => update("font_body", e.target.value)}
              data-testid="font-body" className="w-full h-10 px-3 rounded-lg border border-neutral-200 bg-white text-sm font-mono" />
          </Field>
        </div>
        <div className="text-[11px] uppercase tracking-widest text-neutral-500 mb-2">Pairs recommandées</div>
        <div className="grid md:grid-cols-2 gap-2">
          {FONT_PAIRS.map((p) => (
            <button key={p.label} onClick={() => applyFontPair(p)}
              data-testid={`font-pair-${p.heading}`}
              className="text-left h-auto p-3 rounded-xl border border-neutral-200 hover:border-neutral-900 transition bg-white">
              <div className="text-lg" style={{ fontFamily: `'${p.heading}', serif` }}>{p.heading}</div>
              <div className="text-xs" style={{ fontFamily: `'${p.body}', sans-serif` }}>+ {p.body}</div>
              <div className="text-[10px] text-neutral-500 mt-1">{p.label}</div>
            </button>
          ))}
        </div>
      </div>

      {/* Save bar */}
      <div className="sticky bottom-4 bg-neutral-900 text-white rounded-2xl p-4 flex items-center justify-between gap-3 shadow-xl z-30">
        <div className="text-sm">
          <span className="opacity-70">N'oublie pas d'enregistrer tes modifications →</span>
        </div>
        <button onClick={saveBrand} disabled={saving}
          data-testid="save-brand"
          className="h-10 px-5 rounded-lg bg-white text-neutral-900 hover:bg-neutral-100 text-sm font-semibold flex items-center gap-2 disabled:opacity-60">
          {saving ? <ArrowClockwise size={14} className="animate-spin" /> : <CheckCircle size={14} weight="fill" />}
          {saving ? "Enregistrement…" : "Enregistrer l'identité"}
        </button>
      </div>
    </div>
  );
}

// ==========================================================================
// TAB 2 — NAVIGATION
// ==========================================================================
function NavigationTab({ siteId, onChange }) {
  const [nav, setNav] = useState({ header: [], footer: [] });
  const [saving, setSaving] = useState(false);
  const [optimizing, setOptimizing] = useState(false);
  const [aiRationale, setAiRationale] = useState("");
  const [collections, setCollections] = useState([]);
  const [products, setProducts] = useState([]);

  useEffect(() => {
    apiCall(() => api.get(`/sites/${siteId}/navigation`)).then(({ data }) => {
      if (data) setNav(data);
    });
    apiCall(() => api.get(`/sites/${siteId}/collections`)).then(({ data }) => {
      if (Array.isArray(data)) setCollections(data);
    });
    apiCall(() => api.get(`/sites/${siteId}/products`)).then(({ data }) => {
      if (Array.isArray(data)) setProducts(data.filter((p) => p.status !== "deleted"));
    });
  }, [siteId]);

  const aiOptimize = async () => {
    if (!window.confirm("Laisser l'IA reconstruire ta navigation (header + footer) à partir de ton catalogue ? Tes liens actuels seront remplacés.")) return;
    setOptimizing(true);
    const { data, error } = await apiCall(() => api.post(`/sites/${siteId}/navigation/ai-optimize`, {}));
    setOptimizing(false);
    if (error) { window.alert(error); return; }
    if (data?.navigation) setNav(data.navigation);
    setAiRationale(data?.rationale || "");
    onChange?.();
  };

  const addItem = (where, template = {}) => {
    setNav((n) => ({
      ...n,
      [where]: [...n[where], { label: "Nouveau lien", href: "/", external: false, ...template }],
    }));
  };
  const updateItem = (where, idx, patch) => {
    setNav((n) => ({
      ...n,
      [where]: n[where].map((it, i) => (i === idx ? { ...it, ...patch } : it)),
    }));
  };
  const removeItem = (where, idx) => {
    setNav((n) => ({ ...n, [where]: n[where].filter((_, i) => i !== idx) }));
  };
  const moveItem = (where, idx, dir) => {
    setNav((n) => {
      const copy = [...n[where]];
      const ni = idx + dir;
      if (ni < 0 || ni >= copy.length) return n;
      [copy[idx], copy[ni]] = [copy[ni], copy[idx]];
      return { ...n, [where]: copy };
    });
  };
  const save = async () => {
    setSaving(true);
    const { error } = await apiCall(() => api.put(`/sites/${siteId}/navigation`, nav));
    setSaving(false);
    if (error) { window.alert(error); return; }
    window.alert("Navigation enregistrée");
    onChange?.();
  };

  return (
    <div className="space-y-5" data-testid="navigation-tab">
      <div className="bg-gradient-to-br from-violet-50 to-indigo-50 border border-violet-200 rounded-2xl p-5">
        <div className="flex items-start gap-3 flex-wrap">
          <div className="w-10 h-10 rounded-xl bg-violet-600 flex items-center justify-center shrink-0">
            <Sparkle size={18} weight="fill" className="text-white" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-sm font-semibold text-violet-900">Navigation optimisée par l'IA</div>
            <div className="text-xs text-violet-800/80 mt-0.5">
              Claude analyse ton catalogue, tes collections, tes upsells et ta niche pour bâtir une nav orientée conversion (max 5 items header, hiérarchie claire, libellés vendeurs).
            </div>
            {aiRationale && (
              <div className="mt-2 text-[11px] text-violet-800 bg-white/60 rounded-lg p-2 italic">
                <strong>Rationale IA :</strong> {aiRationale}
              </div>
            )}
          </div>
          <button
            onClick={aiOptimize}
            disabled={optimizing}
            data-testid="ai-nav-optimize"
            className="h-10 px-4 rounded-lg bg-violet-600 hover:bg-violet-700 text-white text-sm font-medium flex items-center gap-2 disabled:opacity-60"
          >
            {optimizing ? <ArrowClockwise size={14} className="animate-spin" /> : <Sparkle size={14} weight="fill" />}
            {optimizing ? "Optimisation…" : "Optimiser avec l'IA"}
          </button>
        </div>
      </div>
      {["header", "footer"].map((where) => (
        <div key={where} className="bg-white border border-neutral-200 rounded-2xl p-5">
          <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
            <div>
              <div className="text-[11px] uppercase tracking-widest text-neutral-500">
                Menu {where === "header" ? "principal (header)" : "pied de page"}
              </div>
              <div className="text-sm text-neutral-500">
                {nav[where].length} lien{nav[where].length > 1 ? "s" : ""} · glisse ↑↓ pour réordonner
              </div>
            </div>
            <div className="flex gap-2">
              <button onClick={() => addItem(where)}
                data-testid={`nav-add-${where}`}
                className="h-9 px-3 rounded-lg bg-neutral-900 text-white text-xs font-medium flex items-center gap-1.5">
                <Plus size={12} weight="bold" /> Lien simple
              </button>
              {where === "header" && (
                <button
                  onClick={() => addItem(where, {
                    label: "Nos produits", href: "/collections", type: "mega", children: [],
                  })}
                  data-testid="nav-add-mega"
                  className="h-9 px-3 rounded-lg bg-violet-600 hover:bg-violet-700 text-white text-xs font-medium flex items-center gap-1.5">
                  <Stack size={12} weight="bold" /> Mega menu
                </button>
              )}
            </div>
          </div>
          <div className="space-y-2">
            {nav[where].length === 0 && (
              <div className="text-sm text-neutral-400 italic py-4">Aucun lien. Clique sur Ajouter.</div>
            )}
            {nav[where].map((item, idx) => (
              <NavRow
                key={idx}
                item={item}
                where={where}
                idx={idx}
                siteId={siteId}
                collections={collections}
                products={products}
                onUpdate={(patch) => updateItem(where, idx, patch)}
                onRemove={() => removeItem(where, idx)}
                onMoveUp={() => moveItem(where, idx, -1)}
                onMoveDown={() => moveItem(where, idx, 1)}
              />
            ))}
          </div>
        </div>
      ))}
      <div className="sticky bottom-4 bg-neutral-900 text-white rounded-2xl p-4 flex items-center justify-between gap-3 shadow-xl z-30">
        <div className="text-sm opacity-70">Les changements s'appliquent au storefront après enregistrement.</div>
        <button onClick={save} disabled={saving}
          data-testid="save-navigation"
          className="h-10 px-5 rounded-lg bg-white text-neutral-900 hover:bg-neutral-100 text-sm font-semibold flex items-center gap-2 disabled:opacity-60">
          {saving ? <ArrowClockwise size={14} className="animate-spin" /> : <CheckCircle size={14} weight="fill" />}
          {saving ? "Enregistrement…" : "Enregistrer la navigation"}
        </button>
      </div>
    </div>
  );
}

// ---------------- NavRow : link picker + mega-menu children editor ----------------
const LINK_TYPES = [
  { value: "home",        label: "Accueil",              href: "/" },
  { value: "shop",        label: "Toute la boutique",    href: "/" },
  { value: "collections", label: "Toutes collections",   href: "/collections" },
  { value: "collection",  label: "Une collection…",      href: "" },
  { value: "product",     label: "Un produit…",          href: "" },
  { value: "blog",        label: "Journal / Blog",       href: "/blog" },
  { value: "about",       label: "À propos",             href: "/about" },
  { value: "contact",     label: "Contact",              href: "/contact" },
  { value: "faq",         label: "FAQ",                  href: "/faq" },
  { value: "search",      label: "Recherche",            href: "/search" },
  { value: "cgv",         label: "CGV",                  href: "/cgv" },
  { value: "mentions",    label: "Mentions légales",     href: "/mentions" },
  { value: "confidentialite", label: "Confidentialité",  href: "/confidentialite" },
  { value: "cookies",     label: "Cookies",              href: "/cookies" },
  { value: "livraison",   label: "Livraison",            href: "/livraison" },
  { value: "retours",     label: "Retours",              href: "/retours" },
  { value: "mediation",   label: "Médiation",            href: "/mediation" },
  { value: "url",         label: "URL personnalisée",    href: "" },
];

function detectLinkType(href = "", collections = [], products = []) {
  const h = (href || "").trim();
  if (/^https?:\/\//.test(h)) return "url";
  if (h === "/" || h === "") return "home";
  if (h === "/collections") return "collections";
  if (h.startsWith("/collections/")) return "collection";
  if (h.startsWith("/product/")) return "product";
  const known = ["blog", "about", "contact", "faq", "search", "cgv", "mentions", "confidentialite", "cookies", "livraison", "retours", "mediation"];
  for (const k of known) if (h === `/${k}`) return k;
  return "url";
}

function NavRow({ item, where, idx, siteId, collections, products, onUpdate, onRemove, onMoveUp, onMoveDown }) {
  const [expanded, setExpanded] = useState(false);
  const isMega = item.type === "mega";
  const linkType = detectLinkType(item.href, collections, products);

  const applyLinkType = (type) => {
    const preset = LINK_TYPES.find((l) => l.value === type);
    if (!preset) return;
    if (type === "collection") {
      const first = collections[0];
      onUpdate({ href: first ? `/collections/${first.slug}` : "/collections/", external: false });
    } else if (type === "product") {
      const first = products[0];
      onUpdate({ href: first ? `/product/${first.id}` : "/product/", external: false });
    } else if (type === "url") {
      onUpdate({ href: "https://", external: true });
    } else {
      onUpdate({ href: preset.href, external: false });
    }
  };

  return (
    <div className="bg-neutral-50 rounded-xl border border-neutral-100">
      <div className="flex items-center gap-2 p-2 flex-wrap md:flex-nowrap">
        <DotsSixVertical size={16} className="text-neutral-400 hidden md:block" />
        {isMega && (
          <span className="text-[10px] px-2 py-0.5 rounded-full bg-violet-100 text-violet-700 font-medium whitespace-nowrap">
            Mega menu
          </span>
        )}
        <input
          type="text"
          value={item.label}
          onChange={(e) => onUpdate({ label: e.target.value })}
          data-testid={`nav-${where}-label-${idx}`}
          placeholder="Intitulé"
          className="flex-1 min-w-[140px] h-9 px-3 rounded border border-neutral-200 bg-white text-sm"
        />
        <select
          value={linkType}
          onChange={(e) => applyLinkType(e.target.value)}
          data-testid={`nav-${where}-type-${idx}`}
          className="h-9 px-2 rounded border border-neutral-200 bg-white text-xs w-40"
        >
          {LINK_TYPES.map((l) => (
            <option key={l.value} value={l.value}>{l.label}</option>
          ))}
        </select>
        {linkType === "collection" && (
          <select
            value={item.href}
            onChange={(e) => onUpdate({ href: e.target.value })}
            data-testid={`nav-${where}-collection-${idx}`}
            className="h-9 px-2 rounded border border-neutral-200 bg-white text-xs min-w-[140px]"
          >
            <option value="">— choisir —</option>
            {collections.map((c) => (
              <option key={c.id} value={`/collections/${c.slug}`}>{c.name}</option>
            ))}
          </select>
        )}
        {linkType === "product" && (
          <select
            value={item.href}
            onChange={(e) => onUpdate({ href: e.target.value })}
            data-testid={`nav-${where}-product-${idx}`}
            className="h-9 px-2 rounded border border-neutral-200 bg-white text-xs min-w-[160px]"
          >
            <option value="">— choisir —</option>
            {products.slice(0, 100).map((p) => (
              <option key={p.id} value={`/product/${p.id}`}>
                {p.name?.fr || p.name?.en || "(sans nom)"}
              </option>
            ))}
          </select>
        )}
        {linkType === "url" && (
          <input
            type="url"
            value={item.href}
            onChange={(e) => onUpdate({ href: e.target.value })}
            data-testid={`nav-${where}-href-${idx}`}
            placeholder="https://…"
            className="h-9 px-3 rounded border border-neutral-200 bg-white text-sm font-mono min-w-[160px]"
          />
        )}
        <div className="flex items-center gap-1 ml-auto">
          {isMega && (
            <button
              onClick={() => setExpanded((v) => !v)}
              data-testid={`nav-${where}-expand-${idx}`}
              className="w-7 h-7 rounded hover:bg-neutral-200 text-neutral-600 flex items-center justify-center text-xs"
              title="Éditer les vignettes"
            >
              {expanded ? "▾" : "▸"}
            </button>
          )}
          <button onClick={onMoveUp}
            className="w-7 h-7 rounded hover:bg-neutral-200 text-neutral-600 flex items-center justify-center text-xs"
            title="Monter">↑</button>
          <button onClick={onMoveDown}
            className="w-7 h-7 rounded hover:bg-neutral-200 text-neutral-600 flex items-center justify-center text-xs"
            title="Descendre">↓</button>
          <button onClick={onRemove}
            data-testid={`nav-${where}-delete-${idx}`}
            className="w-7 h-7 rounded hover:bg-red-100 text-red-500 flex items-center justify-center">
            <Trash size={12} />
          </button>
        </div>
      </div>
      {isMega && expanded && (
        <MegaMenuEditor
          item={item}
          onUpdate={onUpdate}
          collections={collections}
          products={products}
        />
      )}
    </div>
  );
}

function MegaMenuEditor({ item, onUpdate, collections, products }) {
  const children = Array.isArray(item.children) ? item.children : [];
  const addChild = (template) => {
    onUpdate({ children: [...children, { label: "", href: "", image: "", ...template }] });
  };
  const updateChild = (i, patch) => {
    onUpdate({ children: children.map((c, j) => (j === i ? { ...c, ...patch } : c)) });
  };
  const removeChild = (i) => {
    onUpdate({ children: children.filter((_, j) => j !== i) });
  };
  const autoFromCollections = () => {
    const cards = collections.slice(0, 6).map((c) => ({
      label: c.name,
      href: `/collections/${c.slug}`,
      image: c.cover_image || "",
    }));
    onUpdate({ children: cards });
  };
  const autoFromProducts = () => {
    const cards = products
      .filter((p) => p.images?.length)
      .slice(0, 6)
      .map((p) => ({
        label: p.name?.fr || p.name?.en || "(sans nom)",
        href: `/product/${p.id}`,
        image: p.images?.[0] || "",
      }));
    onUpdate({ children: cards });
  };

  return (
    <div className="border-t border-neutral-200 p-3 bg-white rounded-b-xl">
      <div className="flex items-center justify-between mb-2 flex-wrap gap-2">
        <div className="text-[11px] uppercase tracking-widest text-neutral-500">
          Vignettes ({children.length}/6) · affichées au survol sur desktop, tap sur mobile
        </div>
        <div className="flex gap-1">
          <button onClick={autoFromCollections}
            data-testid="mega-auto-collections"
            className="h-7 px-2 rounded border border-violet-200 text-violet-700 hover:bg-violet-50 text-[11px]">
            ⚡ Auto-collections
          </button>
          <button onClick={autoFromProducts}
            data-testid="mega-auto-products"
            className="h-7 px-2 rounded border border-violet-200 text-violet-700 hover:bg-violet-50 text-[11px]">
            ⚡ Auto-produits
          </button>
          <button onClick={() => addChild({})}
            data-testid="mega-add-card"
            className="h-7 px-2 rounded bg-neutral-900 text-white text-[11px]">
            + Vignette
          </button>
        </div>
      </div>
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-2">
        {children.map((c, i) => (
          <div key={i} className="border border-neutral-200 rounded-lg p-2 bg-neutral-50">
            <div className="aspect-[4/3] rounded bg-white border border-neutral-200 mb-2 overflow-hidden flex items-center justify-center">
              {c.image ? (
                <img src={c.image} alt="" className="w-full h-full object-cover" />
              ) : (
                <ImageIcon size={24} weight="duotone" className="text-neutral-400" />
              )}
            </div>
            <input type="text" value={c.label}
              onChange={(e) => updateChild(i, { label: e.target.value })}
              placeholder="Libellé"
              data-testid={`mega-child-label-${i}`}
              className="w-full h-8 px-2 rounded border border-neutral-200 bg-white text-xs mb-1" />
            <input type="text" value={c.href}
              onChange={(e) => updateChild(i, { href: e.target.value })}
              placeholder="/collections/xxx ou /product/yyy"
              data-testid={`mega-child-href-${i}`}
              className="w-full h-8 px-2 rounded border border-neutral-200 bg-white text-xs font-mono mb-1" />
            <input type="text" value={c.image}
              onChange={(e) => updateChild(i, { image: e.target.value })}
              placeholder="URL image"
              data-testid={`mega-child-image-${i}`}
              className="w-full h-8 px-2 rounded border border-neutral-200 bg-white text-xs mb-1" />
            <div className="flex justify-end">
              <button onClick={() => removeChild(i)}
                data-testid={`mega-child-delete-${i}`}
                className="text-[11px] text-red-500 hover:underline flex items-center gap-1">
                <Trash size={10} /> Retirer
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ==========================================================================
// TAB 3 — COLLECTIONS
// ==========================================================================
function CollectionsTab({ siteId, onChange }) {
  const [collections, setCollections] = useState([]);
  const [products, setProducts] = useState([]);
  const [editing, setEditing] = useState(null);
  const [busy, setBusy] = useState(false);
  const [suggesting, setSuggesting] = useState(false);
  const [suggestions, setSuggestions] = useState(null);

  const reload = async () => {
    const [cRes, pRes] = await Promise.all([
      apiCall(() => api.get(`/sites/${siteId}/collections`)),
      apiCall(() => api.get(`/sites/${siteId}/products`)),
    ]);
    setCollections(Array.isArray(cRes.data) ? cRes.data : []);
    setProducts(Array.isArray(pRes.data) ? pRes.data.filter((p) => p.role !== "upsell") : []);
  };
  useEffect(() => { reload(); /* eslint-disable-next-line */ }, [siteId]);

  const aiSuggest = async () => {
    setSuggesting(true);
    const { data, error } = await apiCall(() => api.post(`/sites/${siteId}/collections/ai-suggest`, {}));
    setSuggesting(false);
    if (error) { window.alert(error); return; }
    setSuggestions(data?.suggestions || []);
  };

  const createFromSuggestion = async (s) => {
    const { error } = await apiCall(() =>
      api.post(`/sites/${siteId}/collections`, {
        name: s.name,
        description: s.description,
        product_ids: s.product_ids,
        featured: !!s.featured,
      })
    );
    if (error) { window.alert(error); return; }
    setSuggestions((prev) => (prev || []).filter((x) => x.name !== s.name));
    await reload();
    onChange?.();
  };

  const newCollection = () => setEditing({
    name: "Nouvelle collection", slug: "", description: "", cover_image: "",
    product_ids: [], featured: false,
  });

  const save = async () => {
    setBusy(true);
    const payload = {
      name: editing.name, slug: editing.slug || undefined,
      description: editing.description || "", cover_image: editing.cover_image || null,
      product_ids: editing.product_ids || [], featured: !!editing.featured,
    };
    const isEdit = !!editing.id;
    const { error } = await apiCall(() =>
      isEdit
        ? api.patch(`/sites/${siteId}/collections/${editing.id}`, payload)
        : api.post(`/sites/${siteId}/collections`, payload)
    );
    setBusy(false);
    if (error) { window.alert(error); return; }
    setEditing(null);
    await reload();
    onChange?.();
  };

  const del = async (id) => {
    if (!window.confirm("Supprimer cette collection ?")) return;
    const { error } = await apiCall(() => api.delete(`/sites/${siteId}/collections/${id}`));
    if (error) { window.alert(error); return; }
    await reload();
    onChange?.();
  };

  return (
    <div className="space-y-5" data-testid="collections-tab">
      {/* AI suggestion bar */}
      <div className="bg-gradient-to-br from-violet-50 to-indigo-50 border border-violet-200 rounded-2xl p-5">
        <div className="flex items-start gap-3 flex-wrap">
          <div className="w-10 h-10 rounded-xl bg-violet-600 flex items-center justify-center shrink-0">
            <Sparkle size={18} weight="fill" className="text-white" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-sm font-semibold text-violet-900">Laisser l'IA proposer des collections</div>
            <div className="text-xs text-violet-800/80 mt-0.5">
              Claude regroupe tes produits par usage/gamme et propose 3-5 collections clés en main.
              Tu choisis celles que tu gardes.
            </div>
          </div>
          <button
            onClick={aiSuggest}
            disabled={suggesting}
            data-testid="ai-collections-suggest"
            className="h-10 px-4 rounded-lg bg-violet-600 hover:bg-violet-700 text-white text-sm font-medium flex items-center gap-2 disabled:opacity-60"
          >
            {suggesting ? <ArrowClockwise size={14} className="animate-spin" /> : <Sparkle size={14} weight="fill" />}
            {suggesting ? "Analyse IA…" : "Proposer des collections IA"}
          </button>
        </div>
        {suggestions && suggestions.length > 0 && (
          <div className="mt-4 grid md:grid-cols-2 gap-3" data-testid="ai-suggestions-list">
            {suggestions.map((s) => (
              <div key={s.name} className="bg-white rounded-xl border border-violet-200 p-3">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <div className="font-semibold text-sm">{s.name} {s.featured && <span className="ml-1 text-[10px] bg-amber-100 text-amber-800 px-1.5 py-0.5 rounded-full">vedette</span>}</div>
                    <div className="text-[11px] text-neutral-500 mt-0.5">{s.description}</div>
                    <div className="text-[11px] text-violet-700 mt-1">{s.product_ids?.length || 0} produit(s) assigné(s)</div>
                  </div>
                  <button
                    onClick={() => createFromSuggestion(s)}
                    data-testid={`create-suggestion-${s.name}`}
                    className="h-8 px-3 rounded-lg bg-neutral-900 hover:bg-neutral-800 text-white text-xs font-medium flex items-center gap-1"
                  >
                    <Plus size={11} weight="bold" /> Créer
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
        {suggestions && suggestions.length === 0 && (
          <div className="mt-3 text-xs text-violet-700 italic">Toutes les suggestions ont été créées ou aucune proposée. Importe plus de produits pour de meilleures suggestions.</div>
        )}
      </div>

      <div className="bg-white border border-neutral-200 rounded-2xl p-5">
        <div className="flex items-center justify-between mb-4">
          <div>
            <div className="text-[11px] uppercase tracking-widest text-neutral-500">Collections</div>
            <div className="text-sm text-neutral-500">
              {collections.length} collection{collections.length > 1 ? "s" : ""} · visibles sur <code className="text-[11px] bg-neutral-100 px-1 rounded">/collections</code>
            </div>
          </div>
          <button onClick={newCollection}
            data-testid="new-collection"
            className="h-9 px-3 rounded-lg bg-neutral-900 text-white text-xs font-medium flex items-center gap-1.5">
            <Plus size={12} weight="bold" /> Nouvelle collection
          </button>
        </div>
        {collections.length === 0 ? (
          <div className="text-sm text-neutral-400 italic py-8 text-center">
            Aucune collection encore. Crée par exemple "Fauteuils releveurs", "Loupes & lecture", "Cuisine sénior"…
          </div>
        ) : (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-3">
            {collections.map((c) => (
              <div key={c.id} data-testid={`collection-${c.id}`}
                className="border border-neutral-200 rounded-xl overflow-hidden hover:border-neutral-900 transition bg-white">
                <div className="aspect-video bg-neutral-100 relative">
                  {c.cover_image ? (
                    <img src={c.cover_image} alt="" className="w-full h-full object-cover" />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-neutral-400">
                      <Stack size={32} weight="duotone" />
                    </div>
                  )}
                  {c.featured && (
                    <span className="absolute top-2 left-2 text-[10px] px-2 py-0.5 rounded-full bg-amber-100 text-amber-900 font-medium">vedette</span>
                  )}
                </div>
                <div className="p-3">
                  <div className="font-semibold text-neutral-900 text-sm">{c.name}</div>
                  <div className="text-xs text-neutral-500 mt-0.5">
                    {c.product_ids?.length || 0} produit{(c.product_ids?.length || 0) > 1 ? "s" : ""} · /{c.slug}
                  </div>
                  {c.description && <div className="text-xs text-neutral-600 mt-2 line-clamp-2">{c.description}</div>}
                  <div className="flex gap-2 mt-3">
                    <button onClick={() => setEditing({ ...c })}
                      data-testid={`edit-collection-${c.id}`}
                      className="flex-1 h-8 rounded-lg bg-neutral-900 hover:bg-neutral-800 text-white text-xs font-medium flex items-center justify-center gap-1">
                      <PencilSimple size={10} /> Éditer
                    </button>
                    <button onClick={() => del(c.id)}
                      data-testid={`delete-collection-${c.id}`}
                      className="w-8 h-8 rounded-lg border border-neutral-200 hover:border-red-300 text-neutral-500 hover:text-red-400 flex items-center justify-center">
                      <Trash size={11} />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {editing && (
        <CollectionEditor
          col={editing}
          products={products}
          onClose={() => setEditing(null)}
          onSave={save}
          onChange={(patch) => setEditing((e) => ({ ...e, ...patch }))}
          busy={busy}
        />
      )}
    </div>
  );
}

function CollectionEditor({ col, products, onClose, onSave, onChange, busy }) {
  const toggleProduct = (pid) => {
    const ids = col.product_ids || [];
    onChange({ product_ids: ids.includes(pid) ? ids.filter((x) => x !== pid) : [...ids, pid] });
  };
  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-neutral-900/40 p-4" onClick={onClose}>
      <div className="bg-white rounded-2xl max-w-3xl w-full max-h-[85vh] overflow-auto p-6" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-start justify-between mb-4">
          <div>
            <div className="text-[11px] uppercase tracking-widest text-neutral-500 mb-1">
              {col.id ? "Modifier la collection" : "Nouvelle collection"}
            </div>
            <h3 className="text-xl font-semibold" style={{ fontFamily: "'Fraunces', serif" }}>
              {col.name || "(sans nom)"}
            </h3>
          </div>
          <button onClick={onClose} className="w-8 h-8 rounded-lg hover:bg-neutral-100 text-neutral-500">✕</button>
        </div>
        <div className="grid md:grid-cols-2 gap-4 mb-5">
          <Field label="Nom">
            <input type="text" value={col.name} onChange={(e) => onChange({ name: e.target.value })}
              data-testid="col-name" maxLength={80}
              className="w-full h-10 px-3 rounded-lg border border-neutral-200 bg-white text-sm" />
          </Field>
          <Field label="Slug (URL)">
            <input type="text" value={col.slug || ""} onChange={(e) => onChange({ slug: e.target.value })}
              data-testid="col-slug" placeholder="auto-généré"
              className="w-full h-10 px-3 rounded-lg border border-neutral-200 bg-white text-sm font-mono" />
          </Field>
        </div>
        <Field label="Description">
          <textarea value={col.description || ""} onChange={(e) => onChange({ description: e.target.value })}
            data-testid="col-description" rows={3} maxLength={300}
            placeholder="Description courte affichée en haut de la collection…"
            className="w-full p-3 rounded-lg border border-neutral-200 bg-white text-sm resize-y mb-4" />
        </Field>
        <Field label="Image de couverture (URL)">
          <input type="text" value={col.cover_image || ""} onChange={(e) => onChange({ cover_image: e.target.value })}
            data-testid="col-cover" placeholder="https://…"
            className="w-full h-10 px-3 rounded-lg border border-neutral-200 bg-white text-sm mb-4" />
        </Field>
        <label className="flex items-center gap-2 text-sm text-neutral-700 mb-4">
          <input type="checkbox" checked={!!col.featured}
            onChange={(e) => onChange({ featured: e.target.checked })}
            data-testid="col-featured" />
          Mettre en vedette sur la page d'accueil
        </label>

        <div className="border-t border-neutral-100 pt-4 mb-2">
          <div className="text-[11px] uppercase tracking-widest text-neutral-500 mb-2">
            Produits dans cette collection ({(col.product_ids || []).length} / {products.length})
          </div>
          <div className="flex flex-wrap gap-2 max-h-60 overflow-auto">
            {products.length === 0 ? (
              <div className="text-sm text-neutral-400 italic">Importe des produits d'abord à l'étape 2.</div>
            ) : products.map((p) => {
              const active = (col.product_ids || []).includes(p.id);
              return (
                <button key={p.id} onClick={() => toggleProduct(p.id)}
                  data-testid={`col-product-${p.id}`}
                  className={`flex items-center gap-2 h-9 px-3 rounded-full border text-xs font-medium transition ${
                    active ? "bg-neutral-900 text-white border-neutral-900" : "bg-white border-neutral-200 hover:border-neutral-900 text-neutral-700"
                  }`}>
                  {p.images?.[0] && <img src={p.images[0]} alt="" className="w-5 h-5 rounded object-cover" />}
                  {(p.name?.fr || p.name?.en || "(sans nom)").slice(0, 40)}
                  {active && <CheckCircle size={10} weight="fill" />}
                </button>
              );
            })}
          </div>
        </div>
        <div className="flex justify-end gap-2 mt-5">
          <button onClick={onClose}
            className="h-10 px-4 rounded-lg bg-white border border-neutral-200 hover:border-neutral-400 text-sm">
            Annuler
          </button>
          <button onClick={onSave} disabled={busy || !col.name}
            data-testid="col-save"
            className="h-10 px-5 rounded-lg bg-neutral-900 hover:bg-neutral-800 text-white text-sm font-semibold flex items-center gap-2 disabled:opacity-60">
            {busy ? <ArrowClockwise size={14} className="animate-spin" /> : <CheckCircle size={14} weight="fill" />}
            Enregistrer
          </button>
        </div>
      </div>
    </div>
  );
}

// ==========================================================================
// Helpers
// ==========================================================================
function AiField({ label, field, aiField, tweak, setTweak, onGenerate, children }) {
  const busy = aiField === field;
  const [showTweak, setShowTweak] = useState(false);
  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <div className="text-[11px] uppercase tracking-widest text-neutral-500">{label}</div>
        <div className="flex items-center gap-1">
          {showTweak && (
            <input
              type="text"
              value={tweak || ""}
              onChange={(e) => setTweak(e.target.value)}
              placeholder="Brief IA (optionnel)"
              className="h-7 px-2 rounded border border-violet-200 bg-white text-[11px] w-48"
              data-testid={`ai-tweak-${field}`}
            />
          )}
          <button
            onClick={() => setShowTweak((v) => !v)}
            className="h-7 w-7 rounded-lg hover:bg-neutral-100 text-neutral-500 flex items-center justify-center text-xs"
            title="Ajouter un brief"
            data-testid={`ai-tweak-toggle-${field}`}
          >+</button>
          <button
            onClick={onGenerate}
            disabled={busy}
            data-testid={`ai-${field}`}
            className="h-7 px-2 rounded-lg bg-violet-600 hover:bg-violet-700 text-white text-[11px] font-medium flex items-center gap-1 disabled:opacity-60"
          >
            {busy ? <ArrowClockwise size={10} className="animate-spin" /> : <Sparkle size={10} weight="fill" />}
            IA
          </button>
        </div>
      </div>
      {children}
    </div>
  );
}

function Field({ label, children }) {
  return (
    <div>
      <div className="text-[11px] uppercase tracking-widest text-neutral-500 mb-1">{label}</div>
      {children}
    </div>
  );
}

function ColorPicker({ label, value, onChange }) {
  return (
    <div>
      <div className="text-[11px] uppercase tracking-widest text-neutral-500 mb-1">{label}</div>
      <div className="flex items-center gap-2 h-10 px-2 rounded-lg border border-neutral-200 bg-white">
        <input type="color" value={value} onChange={(e) => onChange(e.target.value)}
          data-testid={`color-${label.toLowerCase()}`}
          className="w-8 h-8 rounded cursor-pointer border-0" />
        <input type="text" value={value} onChange={(e) => onChange(e.target.value)}
          className="flex-1 bg-transparent outline-none text-xs font-mono" />
      </div>
    </div>
  );
}
