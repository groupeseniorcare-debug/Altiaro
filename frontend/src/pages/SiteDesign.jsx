import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import {
  ArrowLeft, PaintBrush, Sparkle, ArrowClockwise, CheckCircle, Image as ImageIcon,
  Palette, ChatCenteredText, Storefront as StoreIcon, UploadSimple,
  List, Rows, Stack, TextT, Plus, Trash, PencilSimple, ArrowRight,
  DotsSixVertical, Link as LinkIcon, Heart,
} from "@phosphor-icons/react";
import { api, apiCall } from "../lib/api";
import BrandingContent from "../components/BrandingContent";

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
  const [siteName, setSiteName] = useState("");
  const [loading, setLoading] = useState(true);
  const [publishing, setPublishing] = useState(false);
  const [tab, setTab] = useState("identity");

  const reload = async () => {
    const { data } = await apiCall(() => api.get(`/sites/${siteId}/design`));
    if (data) {
      setDesign(data.design || null);
      setSiteName(data.site_name || "");
    }
    setLoading(false);
  };

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

  return (
    <div className="min-h-screen bg-[#FAF7F2]">
      <div className="max-w-6xl mx-auto px-6 md:px-10 py-8">
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

        {/* Tab content */}
        {tab === "identity" && (
          <IdentityTab
            siteId={siteId}
            design={design}
            onReload={reload}
            hasDesign={hasDesign}
          />
        )}
        {tab === "navigation" && <NavigationTab siteId={siteId} />}
        {tab === "collections" && <CollectionsTab siteId={siteId} />}
        {tab === "content" && <BrandingContent siteId={siteId} design={design} onReload={reload} />}
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
          <Field label="Nom de marque">
            <input type="text" value={form.name} onChange={(e) => update("name", e.target.value)}
              data-testid="brand-name" maxLength={40}
              className="w-full h-10 px-3 rounded-lg border border-neutral-200 bg-white text-lg font-semibold focus:outline-none focus:border-neutral-900"
              style={{ fontFamily: "'Fraunces', serif" }} />
          </Field>
          <Field label="Tagline / baseline (≤ 80 car.)">
            <input type="text" value={form.tagline} onChange={(e) => update("tagline", e.target.value)}
              data-testid="brand-tagline" maxLength={80}
              placeholder="Le confort au quotidien, simplement."
              className="w-full h-10 px-3 rounded-lg border border-neutral-200 bg-white text-sm italic focus:outline-none focus:border-neutral-900" />
          </Field>
          <Field label="Ton de voix">
            <input type="text" value={form.voice} onChange={(e) => update("voice", e.target.value)}
              data-testid="brand-voice" maxLength={200}
              placeholder="Chaleureux, rassurant, expert, tutoiement"
              className="w-full h-10 px-3 rounded-lg border border-neutral-200 bg-white text-sm focus:outline-none focus:border-neutral-900" />
          </Field>
          <Field label="Histoire / storytelling">
            <textarea value={form.story} onChange={(e) => update("story", e.target.value)}
              data-testid="brand-story" rows={4} maxLength={500}
              placeholder="Fondée en 2024 pour offrir aux seniors des solutions pratiques à prix juste…"
              className="w-full p-3 rounded-lg border border-neutral-200 bg-white text-sm focus:outline-none focus:border-neutral-900 resize-y" />
          </Field>
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
        <div className="flex items-center justify-between mb-4">
          <div className="text-[11px] uppercase tracking-widest text-neutral-500 flex items-center gap-1">
            <Palette size={11} /> Palette de couleurs
          </div>
          <div className="text-[11px] text-neutral-400">Utilisée partout sur le storefront</div>
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
        <div className="text-[11px] uppercase tracking-widest text-neutral-500 mb-3 flex items-center gap-1">
          <TextT size={11} /> Typographie
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
function NavigationTab({ siteId }) {
  const [nav, setNav] = useState({ header: [], footer: [] });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    apiCall(() => api.get(`/sites/${siteId}/navigation`)).then(({ data }) => {
      if (data) setNav(data);
    });
  }, [siteId]);

  const addItem = (where) => {
    setNav((n) => ({ ...n, [where]: [...n[where], { label: "Nouveau lien", href: "/", external: false }] }));
  };
  const updateItem = (where, idx, key, value) => {
    setNav((n) => ({ ...n, [where]: n[where].map((it, i) => i === idx ? { ...it, [key]: value } : it) }));
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
  };

  return (
    <div className="space-y-5" data-testid="navigation-tab">
      {["header", "footer"].map((where) => (
        <div key={where} className="bg-white border border-neutral-200 rounded-2xl p-5">
          <div className="flex items-center justify-between mb-4">
            <div>
              <div className="text-[11px] uppercase tracking-widest text-neutral-500">Menu {where === "header" ? "principal (header)" : "pied de page"}</div>
              <div className="text-sm text-neutral-500">{nav[where].length} lien{nav[where].length > 1 ? "s" : ""} · glisse ↑↓ pour réordonner</div>
            </div>
            <button onClick={() => addItem(where)}
              data-testid={`nav-add-${where}`}
              className="h-9 px-3 rounded-lg bg-neutral-900 text-white text-xs font-medium flex items-center gap-1.5">
              <Plus size={12} weight="bold" /> Ajouter
            </button>
          </div>
          <div className="space-y-2">
            {nav[where].length === 0 && (
              <div className="text-sm text-neutral-400 italic py-4">Aucun lien. Clique sur Ajouter.</div>
            )}
            {nav[where].map((item, idx) => (
              <div key={idx} className="flex items-center gap-2 bg-neutral-50 rounded-lg p-2">
                <DotsSixVertical size={16} className="text-neutral-400 cursor-grab" />
                <input type="text" value={item.label}
                  onChange={(e) => updateItem(where, idx, "label", e.target.value)}
                  data-testid={`nav-${where}-label-${idx}`}
                  placeholder="Intitulé"
                  className="flex-1 h-9 px-3 rounded border border-neutral-200 bg-white text-sm" />
                <input type="text" value={item.href}
                  onChange={(e) => updateItem(where, idx, "href", e.target.value)}
                  data-testid={`nav-${where}-href-${idx}`}
                  placeholder="/lien"
                  className="flex-1 h-9 px-3 rounded border border-neutral-200 bg-white text-sm font-mono" />
                <label className="text-xs text-neutral-500 flex items-center gap-1 whitespace-nowrap">
                  <input type="checkbox" checked={item.external}
                    onChange={(e) => updateItem(where, idx, "external", e.target.checked)}
                    data-testid={`nav-${where}-external-${idx}`} />
                  Externe
                </label>
                <button onClick={() => moveItem(where, idx, -1)}
                  className="w-7 h-7 rounded hover:bg-neutral-200 text-neutral-600 flex items-center justify-center text-xs"
                  title="Monter">↑</button>
                <button onClick={() => moveItem(where, idx, 1)}
                  className="w-7 h-7 rounded hover:bg-neutral-200 text-neutral-600 flex items-center justify-center text-xs"
                  title="Descendre">↓</button>
                <button onClick={() => removeItem(where, idx)}
                  data-testid={`nav-${where}-delete-${idx}`}
                  className="w-7 h-7 rounded hover:bg-red-100 text-red-500 flex items-center justify-center">
                  <Trash size={12} />
                </button>
              </div>
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

// ==========================================================================
// TAB 3 — COLLECTIONS
// ==========================================================================
function CollectionsTab({ siteId }) {
  const [collections, setCollections] = useState([]);
  const [products, setProducts] = useState([]);
  const [editing, setEditing] = useState(null);
  const [busy, setBusy] = useState(false);

  const reload = async () => {
    const [cRes, pRes] = await Promise.all([
      apiCall(() => api.get(`/sites/${siteId}/collections`)),
      apiCall(() => api.get(`/sites/${siteId}/products`)),
    ]);
    setCollections(Array.isArray(cRes.data) ? cRes.data : []);
    setProducts(Array.isArray(pRes.data) ? pRes.data.filter((p) => p.role !== "upsell") : []);
  };
  useEffect(() => { reload(); /* eslint-disable-next-line */ }, [siteId]);

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
  };

  const del = async (id) => {
    if (!window.confirm("Supprimer cette collection ?")) return;
    const { error } = await apiCall(() => api.delete(`/sites/${siteId}/collections/${id}`));
    if (error) { window.alert(error); return; }
    await reload();
  };

  return (
    <div className="space-y-5" data-testid="collections-tab">
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
