import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import {
  ArrowLeft, PaintBrush, Sparkle, ArrowClockwise, CheckCircle, Info, Image as ImageIcon,
  Palette, ClipboardText, ChatCenteredText, Storefront as StoreIcon, UploadSimple,
} from "@phosphor-icons/react";
import { api, apiCall } from "../lib/api";

const REGEN_SECTIONS = [
  { key: "brand", label: "Nom + baseline", Icon: PaintBrush },
  { key: "logo", label: "Logo", Icon: ImageIcon },
  { key: "hero", label: "Hero page d'accueil", Icon: Sparkle },
  { key: "about", label: "À propos", Icon: ClipboardText },
  { key: "benefits", label: "Bénéfices clés", Icon: CheckCircle },
  { key: "faq", label: "FAQ", Icon: ChatCenteredText },
  { key: "testimonials", label: "Témoignages", Icon: ChatCenteredText },
  { key: "contact", label: "Contact", Icon: ChatCenteredText },
  { key: "seo", label: "SEO (title, description)", Icon: Sparkle },
];

export default function SiteDesign() {
  const { id: siteId } = useParams();
  const [design, setDesign] = useState(null);
  const [siteName, setSiteName] = useState("");
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [regenerating, setRegenerating] = useState(null);
  const [publishing, setPublishing] = useState(false);
  const [tweak, setTweak] = useState("");
  const [logoUploading, setLogoUploading] = useState(false);

  const reload = async () => {
    const { data } = await apiCall(() => api.get(`/sites/${siteId}/design`));
    if (data) {
      setDesign(data.design || null);
      setSiteName(data.site_name || "");
    }
    setLoading(false);
  };

  useEffect(() => { reload(); }, [siteId]); // eslint-disable-line

  const generateAll = async () => {
    if (design?.brand?.name && !window.confirm("Un design existe déjà. Tout régénérer ?")) return;
    setGenerating(true);
    const { error } = await apiCall(() =>
      api.post(`/sites/${siteId}/design/generate`, { with_logo: true, tweak })
    );
    setGenerating(false);
    if (error) { window.alert(`Génération échouée : ${error}`); return; }
    setTweak("");
    await reload();
  };

  const regenSection = async (section) => {
    setRegenerating(section);
    const { error } = await apiCall(() =>
      api.post(`/sites/${siteId}/design/regenerate/${section}`, { tweak: "" })
    );
    setRegenerating(null);
    if (error) { window.alert(`Régénération échouée : ${error}`); return; }
    await reload();
  };

  const togglePublish = async () => {
    setPublishing(true);
    const { data, error } = await apiCall(() =>
      api.post(`/sites/${siteId}/design/publish`, {})
    );
    setPublishing(false);
    if (error) { window.alert(error); return; }
    setDesign((d) => ({ ...(d || {}), published: data?.published ?? !d?.published }));
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
    await reload();
  };

  if (loading) {
    return <div className="min-h-screen bg-[#FAF7F2] p-10 text-neutral-500">Chargement…</div>;
  }

  const brand = design?.brand || {};
  const colors = brand.palette || {};
  const hero = design?.hero || {};
  const about = design?.about || {};
  const contact = design?.contact || {};
  const faq = design?.faq || [];
  const benefits = design?.benefits || [];
  const hasDesign = !!brand.name;

  return (
    <div className="min-h-screen bg-[#FAF7F2]">
      <div className="max-w-5xl mx-auto px-6 md:px-10 py-8">
        <Link to={`/sites/${siteId}`} className="inline-flex items-center gap-2 text-sm text-neutral-600 hover:text-neutral-900 mb-6">
          <ArrowLeft size={14} /> Retour au cockpit
        </Link>

        <div className="mb-8 flex items-start justify-between gap-6 flex-wrap">
          <div>
            <div className="text-[11px] uppercase tracking-[0.2em] text-neutral-500 mb-2 flex items-center gap-2">
              <PaintBrush size={12} weight="bold" /> Étapes 5 & 6 · Identité, pages & copywriting
            </div>
            <h1 className="text-3xl md:text-4xl font-semibold text-neutral-900" style={{ fontFamily: "'Fraunces', serif" }}>
              {siteName}
            </h1>
            <p className="text-sm text-neutral-500 mt-2 max-w-2xl">
              L'IA génère ton identité de marque, la structure du site (hero, bénéfices, FAQ, témoignages, à propos) et toutes tes pages légales. Tu peux régénérer chaque section indépendamment, ajuster avec un brief, et uploader ton propre logo.
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
                {design?.published ? <><CheckCircle size={14} weight="fill" /> Publié</> : <>Publier sur le storefront</>}
              </button>
            )}
            <a
              href={`/shop/${siteId}`}
              target="_blank"
              rel="noreferrer"
              className="h-11 px-5 rounded-xl bg-white border border-neutral-300 hover:border-neutral-900 text-neutral-900 text-sm font-medium flex items-center gap-2"
            >
              <StoreIcon size={14} /> Voir le storefront
            </a>
          </div>
        </div>

        {!hasDesign ? (
          <EmptyState
            tweak={tweak}
            setTweak={setTweak}
            onGenerate={generateAll}
            loading={generating}
          />
        ) : (
          <div className="space-y-6" data-testid="design-dashboard">
            {/* Brand block */}
            <div className="bg-white border border-neutral-200 rounded-2xl p-6">
              <div className="flex items-start justify-between gap-4 flex-wrap">
                <div className="flex-1 min-w-[240px]">
                  <div className="text-[11px] uppercase tracking-widest text-neutral-500 mb-2">Identité de marque</div>
                  <div className="text-2xl font-semibold text-neutral-900 mb-1" style={{ fontFamily: "'Fraunces', serif" }}>{brand.name}</div>
                  <div className="text-sm text-neutral-600 italic">{brand.baseline || "—"}</div>
                  {brand.voice && (
                    <div className="mt-3 text-xs text-neutral-500">
                      <span className="text-neutral-400 uppercase tracking-widest mr-2">Voix</span>{brand.voice}
                    </div>
                  )}
                </div>
                <div className="flex flex-col items-end gap-2">
                  {brand.logo_url ? (
                    <img src={brand.logo_url} alt="logo" className="h-20 w-20 object-contain rounded-xl bg-neutral-50 border border-neutral-200 p-2" />
                  ) : (
                    <div className="h-20 w-20 rounded-xl bg-neutral-100 border border-neutral-200 flex items-center justify-center text-neutral-400">
                      <ImageIcon size={28} weight="duotone" />
                    </div>
                  )}
                  <label className="cursor-pointer text-[11px] uppercase tracking-widest text-neutral-500 hover:text-neutral-900 flex items-center gap-1">
                    <UploadSimple size={12} /> {logoUploading ? "Upload…" : "Uploader un logo"}
                    <input
                      type="file"
                      accept="image/*"
                      className="hidden"
                      data-testid="logo-upload"
                      onChange={(e) => uploadLogo(e.target.files?.[0])}
                    />
                  </label>
                </div>
              </div>

              {Object.keys(colors).length > 0 && (
                <div className="mt-5 pt-4 border-t border-neutral-100">
                  <div className="text-[11px] uppercase tracking-widest text-neutral-500 mb-2 flex items-center gap-1.5"><Palette size={12} /> Palette</div>
                  <div className="flex gap-3 flex-wrap">
                    {Object.entries(colors).map(([k, v]) => (
                      <div key={k} className="flex items-center gap-2 bg-neutral-50 border border-neutral-200 rounded-full pl-1 pr-3 py-1">
                        <div className="w-6 h-6 rounded-full border border-white shadow" style={{ background: v }} />
                        <span className="text-xs text-neutral-700">{k}</span>
                        <span className="text-[10px] font-mono text-neutral-400">{v}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div className="mt-5 pt-4 border-t border-neutral-100 flex gap-2 flex-wrap">
                {REGEN_SECTIONS.map(({ key, label, Icon }) => (
                  <button
                    key={key}
                    onClick={() => regenSection(key)}
                    disabled={regenerating === key}
                    data-testid={`regen-${key}`}
                    className="h-9 px-3 rounded-lg bg-white border border-neutral-200 hover:border-neutral-900 text-xs font-medium text-neutral-700 flex items-center gap-1.5 disabled:opacity-60"
                  >
                    {regenerating === key ? <ArrowClockwise size={12} className="animate-spin" /> : <Icon size={12} weight="duotone" />}
                    {regenerating === key ? "…" : label}
                  </button>
                ))}
              </div>
            </div>

            {/* Hero preview */}
            {hero.title && (
              <Section title="Hero page d'accueil" testid="design-hero">
                <div className="text-xs text-neutral-500 mb-1">TITRE</div>
                <div className="text-xl font-semibold text-neutral-900" style={{ fontFamily: "'Fraunces', serif" }}>{hero.title}</div>
                {hero.subtitle && <div className="text-sm text-neutral-700 mt-2 leading-relaxed">{hero.subtitle}</div>}
                {hero.cta_label && <div className="mt-3 inline-block text-[11px] uppercase tracking-widest bg-neutral-100 px-2 py-1 rounded">CTA : {hero.cta_label}</div>}
              </Section>
            )}

            {/* Benefits */}
            {benefits.length > 0 && (
              <Section title={`${benefits.length} bénéfices clés`} testid="design-benefits">
                <div className="grid md:grid-cols-2 gap-3">
                  {benefits.map((b, i) => (
                    <div key={i} className="p-3 rounded-lg bg-neutral-50 border border-neutral-100">
                      <div className="font-medium text-sm text-neutral-900">{b.title || b.label}</div>
                      {b.description && <div className="text-xs text-neutral-600 mt-1">{b.description}</div>}
                    </div>
                  ))}
                </div>
              </Section>
            )}

            {/* About */}
            {(about.paragraphs || about.content) && (
              <Section title="À propos" testid="design-about">
                {about.title && <div className="font-semibold mb-2">{about.title}</div>}
                {Array.isArray(about.paragraphs)
                  ? about.paragraphs.map((p, i) => <p key={i} className="text-sm text-neutral-700 leading-relaxed mb-2">{p}</p>)
                  : <p className="text-sm text-neutral-700 leading-relaxed">{about.content}</p>}
              </Section>
            )}

            {/* FAQ */}
            {faq.length > 0 && (
              <Section title={`FAQ · ${faq.length} questions`} testid="design-faq">
                <div className="space-y-2">
                  {faq.map((q, i) => (
                    <details key={i} className="group bg-neutral-50 rounded-lg border border-neutral-100 p-3">
                      <summary className="cursor-pointer text-sm font-medium text-neutral-900">{q.question || q.q}</summary>
                      <p className="text-sm text-neutral-700 mt-2">{q.answer || q.a}</p>
                    </details>
                  ))}
                </div>
              </Section>
            )}

            {/* Contact */}
            {(contact.email || contact.phone) && (
              <Section title="Contact" testid="design-contact">
                {contact.email && <div className="text-sm">📧 {contact.email}</div>}
                {contact.phone && <div className="text-sm">📞 {contact.phone}</div>}
                {contact.address && <div className="text-sm">📍 {contact.address}</div>}
              </Section>
            )}

            {/* Legal injected server-side */}
            <Section title="Pages légales" testid="design-legal">
              <div className="grid md:grid-cols-3 gap-3 text-sm">
                {[
                  ["CGV", `/shop/${siteId}/cgv`],
                  ["Mentions légales", `/shop/${siteId}/mentions`],
                  ["Confidentialité", `/shop/${siteId}/confidentialite`],
                ].map(([label, href]) => (
                  <a
                    key={label}
                    href={href}
                    target="_blank"
                    rel="noreferrer"
                    className="block p-3 bg-neutral-50 hover:bg-neutral-100 rounded-lg border border-neutral-200 text-center"
                  >
                    <div className="font-medium text-neutral-900">{label}</div>
                    <div className="text-xs text-neutral-500 mt-0.5">Ouvrir ↗</div>
                  </a>
                ))}
              </div>
              <div className="text-xs text-neutral-500 mt-3 flex items-start gap-2">
                <Info size={14} weight="duotone" className="flex-shrink-0 mt-0.5" />
                <span>Générées automatiquement à partir des informations de ta société (Compte → infos société).</span>
              </div>
            </Section>

            {/* Brief + regenerate all */}
            <div className="bg-gradient-to-br from-amber-50 to-orange-50 border border-amber-200 rounded-2xl p-6">
              <div className="text-[11px] uppercase tracking-widest text-amber-700 mb-2 font-semibold">Régénérer TOUT avec un brief</div>
              <textarea
                value={tweak}
                onChange={(e) => setTweak(e.target.value)}
                placeholder="Ex. « ton plus chaleureux, mets l'accent sur l'installation offerte et la garantie 5 ans »"
                className="w-full min-h-[80px] p-3 rounded-lg border border-amber-300 bg-white text-sm resize-y"
                data-testid="design-brief"
              />
              <button
                onClick={generateAll}
                disabled={generating}
                data-testid="design-regen-all"
                className="mt-3 h-10 px-4 rounded-lg bg-amber-600 hover:bg-amber-700 text-white text-sm font-medium flex items-center gap-2 disabled:opacity-60"
              >
                {generating ? <ArrowClockwise size={14} className="animate-spin" /> : <Sparkle size={14} weight="fill" />}
                {generating ? "Régénération (60-90s)…" : "Régénérer avec ce brief"}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function Section({ title, children, testid }) {
  return (
    <div className="bg-white border border-neutral-200 rounded-2xl p-5" data-testid={testid}>
      <div className="text-[11px] uppercase tracking-widest text-neutral-500 mb-3">{title}</div>
      {children}
    </div>
  );
}

function EmptyState({ tweak, setTweak, onGenerate, loading }) {
  return (
    <div className="bg-white border border-neutral-200 rounded-2xl p-10 text-center" data-testid="design-empty">
      <PaintBrush size={40} weight="duotone" className="mx-auto text-neutral-400 mb-4" />
      <h2 className="text-xl font-semibold text-neutral-900 mb-2" style={{ fontFamily: "'Fraunces', serif" }}>
        Ton site n'a pas encore d'identité
      </h2>
      <p className="text-sm text-neutral-600 max-w-lg mx-auto mb-6">
        Claude va générer en une passe : <strong>nom de marque</strong>, <strong>baseline</strong>, <strong>palette de couleurs</strong>, <strong>logo</strong> (nano-banana), <strong>hero + bénéfices + FAQ + témoignages + à propos + contact + SEO</strong>. Pages légales (CGV, mentions, confidentialité) injectées automatiquement depuis ton profil société.
      </p>
      <div className="max-w-xl mx-auto">
        <textarea
          value={tweak}
          onChange={(e) => setTweak(e.target.value)}
          placeholder="(Optionnel) brief · ex. « marque haut de gamme, ton chaleureux, cible 70+ urbains »"
          className="w-full min-h-[72px] p-3 rounded-lg border border-neutral-300 bg-white text-sm resize-y mb-3"
          data-testid="design-initial-brief"
        />
        <button
          onClick={onGenerate}
          disabled={loading}
          data-testid="design-generate"
          className="h-11 px-6 rounded-xl bg-neutral-900 hover:bg-neutral-800 text-white text-sm font-medium inline-flex items-center gap-2 disabled:opacity-60"
        >
          {loading ? <ArrowClockwise size={14} className="animate-spin" /> : <Sparkle size={14} weight="fill" />}
          {loading ? "Génération en cours (60-90s)…" : "Générer mon site (IA)"}
        </button>
      </div>
    </div>
  );
}
