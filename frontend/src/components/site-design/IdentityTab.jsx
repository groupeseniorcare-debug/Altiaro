import React, { useEffect, useState } from "react";
import {
  ArrowClockwise, CheckCircle, Image as ImageIcon, Palette, Sparkle, TextT,
  UploadSimple, Heart, PaintBrush,
} from "@phosphor-icons/react";
import { api, apiCall } from "../../lib/api";
import { FONT_PAIRS, PALETTE_PRESETS } from "./constants";
import { AiField, Field, ColorPicker } from "./shared";

export default function IdentityTab({ siteId, design, onReload, hasDesign }) {
  const brand = design?.brand || {};
  const [generating, setGenerating] = useState(false);
  const [genStatus, setGenStatus] = useState("");
  const [initialBrief, setInitialBrief] = useState("");
  const [logoUploading, setLogoUploading] = useState(false);
  const [regeneratingLogo, setRegeneratingLogo] = useState(false);
  const [logoPrompt, setLogoPrompt] = useState("");
  const [saving, setSaving] = useState(false);
  const [skipEmpty, setSkipEmpty] = useState(false);
  const [aiField, setAiField] = useState(null);
  const [aiTweak, setAiTweak] = useState({});
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
