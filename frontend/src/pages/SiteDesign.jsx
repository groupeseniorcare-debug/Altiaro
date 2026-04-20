import React, { useEffect, useState, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import Layout from "../components/Layout";
import { api, apiCall } from "../lib/api";
import {
  Sparkle,
  ArrowsClockwise,
  Eye,
  EyeSlash,
  CheckCircle,
  CaretLeft,
  PaintBrush,
  Image as ImageIcon,
  Palette,
  TextT,
  ListChecks,
  Chat,
  Question,
  FileText,
  Storefront as StorefrontIcon,
  Star,
} from "@phosphor-icons/react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const SECTIONS = [
  { key: "brand", label: "Identité de marque", icon: PaintBrush, desc: "Couleurs, polices, logo" },
  { key: "hero", label: "Hero (accueil)", icon: TextT, desc: "Titre, sous-titre, CTA" },
  { key: "benefits", label: "Bénéfices", icon: ListChecks, desc: "4 points forts" },
  { key: "testimonials", label: "Témoignages", icon: Chat, desc: "3 avis clients" },
  { key: "faq", label: "FAQ", icon: Question, desc: "10 questions/réponses" },
  { key: "about", label: "À propos", icon: FileText, desc: "Page À propos" },
  { key: "contact", label: "Contact", icon: FileText, desc: "Page contact" },
  { key: "seo", label: "SEO", icon: FileText, desc: "Meta titles & descriptions" },
  { key: "logo", label: "Logo graphique", icon: ImageIcon, desc: "Régénérer via IA image" },
];

export default function SiteDesign() {
  const { id: siteId } = useParams();
  const [site, setSite] = useState(null);
  const [design, setDesign] = useState(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [regenerating, setRegenerating] = useState({});
  const [tweak, setTweak] = useState("");
  const [sectionTweak, setSectionTweak] = useState({});
  const [toast, setToast] = useState("");
  const [publishing, setPublishing] = useState(false);
  const [previewKey, setPreviewKey] = useState(0);

  const load = useCallback(async () => {
    setLoading(true);
    const s = await apiCall(() => api.get(`/sites/${siteId}`));
    if (s.data) setSite(s.data);
    const d = await apiCall(() => api.get(`/sites/${siteId}/design`));
    if (d.data) setDesign(d.data.design);
    setLoading(false);
  }, [siteId]);

  useEffect(() => {
    load();
  }, [load]);

  const triggerToast = (msg) => {
    setToast(msg);
    setTimeout(() => setToast(""), 3500);
  };

  const generate = async (withLogo = true) => {
    if (design && !window.confirm("Régénérer TOUT le design ? Le contenu actuel sera écrasé.")) return;
    setGenerating(true);
    const { data, error } = await apiCall(() =>
      api.post(`/sites/${siteId}/design/generate`, { tweak: tweak.trim(), with_logo: withLogo }),
    );
    setGenerating(false);
    if (error) return triggerToast(`✗ ${error}`);
    setDesign(data.design);
    setTweak("");
    setPreviewKey((k) => k + 1);
    triggerToast("✓ Design généré par l'IA !");
  };

  const regenerate = async (section) => {
    setRegenerating((r) => ({ ...r, [section]: true }));
    const { data, error } = await apiCall(() =>
      api.post(`/sites/${siteId}/design/regenerate/${section}`, { tweak: sectionTweak[section] || "" }),
    );
    setRegenerating((r) => ({ ...r, [section]: false }));
    if (error) return triggerToast(`✗ ${error}`);
    if (section === "logo") {
      setDesign((d) => ({ ...d, brand: { ...(d?.brand || {}), logo_url: data.logo_url } }));
    } else {
      setDesign((d) => ({ ...d, [section]: data[section] }));
    }
    setSectionTweak((t) => ({ ...t, [section]: "" }));
    setPreviewKey((k) => k + 1);
    triggerToast(`✓ Section « ${section} » régénérée`);
  };

  const togglePublish = async () => {
    setPublishing(true);
    const target = !design?.published;
    const { error } = await apiCall(() =>
      api.post(`/sites/${siteId}/design/publish?publish=${target}`),
    );
    setPublishing(false);
    if (error) return triggerToast(`✗ ${error}`);
    setDesign((d) => ({ ...(d || {}), published: target, published_at: target ? new Date().toISOString() : null }));
    triggerToast(target ? "✓ Site publié !" : "Site dépublié");
    setPreviewKey((k) => k + 1);
  };

  if (loading) {
    return <Layout><div className="p-8 text-[#78716C]">Chargement…</div></Layout>;
  }

  const published = !!design?.published;
  const previewUrl = `${BACKEND_URL ? "" : ""}/shop/${siteId}?_=${previewKey}`;

  return (
    <Layout>
      <div className="flex h-[calc(100vh-64px)]">
        {/* LEFT : contrôles */}
        <aside className="w-[440px] border-r border-[#E7E5E4] bg-[#FDFBF7] overflow-y-auto">
          <div className="p-6">
            <Link
              to={`/sites/${siteId}`}
              className="text-sm text-[#78716C] hover:text-[#1C1917] flex items-center gap-1 mb-3"
              data-testid="back-to-site"
            >
              <CaretLeft size={14} /> Retour au site
            </Link>
            <div className="flex items-center gap-2 mb-2">
              <StorefrontIcon size={20} weight="fill" className="text-[#B84B31]" />
              <h1 className="font-heading text-2xl font-semibold text-[#1C1917]">Design IA</h1>
            </div>
            <p className="text-xs text-[#78716C] mb-4">
              {site?.name} · {site?.niche}
            </p>

            {/* Status banner */}
            {design && (
              <div className={`rounded-xl border p-3 mb-5 text-sm flex items-center justify-between ${
                published ? "bg-[#DCF5E7] border-[#86EFAC] text-[#166534]" : "bg-[#FEF3C7] border-[#FDE68A] text-[#854D0E]"
              }`} data-testid="publish-status">
                <div className="flex items-center gap-2">
                  {published ? <CheckCircle size={16} weight="fill" /> : <EyeSlash size={16} />}
                  {published ? "Publié sur la boutique" : "Brouillon (non publié)"}
                </div>
                <button
                  onClick={togglePublish}
                  disabled={publishing}
                  data-testid="toggle-publish"
                  className="text-xs underline hover:no-underline disabled:opacity-50"
                >
                  {published ? "Dépublier" : "Publier"}
                </button>
              </div>
            )}

            {/* Full generate */}
            <div className="bg-white rounded-2xl border border-[#E7E5E4] p-5 mb-5">
              <div className="flex items-center gap-2 mb-1">
                <Sparkle size={16} weight="fill" className="text-[#B84B31]" />
                <div className="font-heading font-semibold text-[#1C1917]">Générer mon site complet</div>
              </div>
              <p className="text-xs text-[#78716C] mb-3">
                L'IA produit tout : couleurs, hero, pages, FAQ, SEO… en 1 clic.
              </p>
              <textarea
                value={tweak}
                onChange={(e) => setTweak(e.target.value)}
                placeholder="Directive (optionnel) ex: « ton chaleureux, palette bleu médical »"
                rows={2}
                data-testid="full-tweak"
                className="w-full text-sm px-3 py-2 rounded-lg border border-[#E7E5E4] outline-none focus:border-[#B84B31] mb-3"
              />
              <button
                onClick={() => generate(true)}
                disabled={generating}
                data-testid="generate-full-btn"
                className="w-full h-11 rounded-xl bg-[#1C1917] hover:bg-[#44403C] text-white text-sm font-medium flex items-center justify-center gap-2 disabled:opacity-50 transition"
              >
                {generating ? (
                  <><ArrowsClockwise size={14} className="animate-spin" /> Génération… (30-60s)</>
                ) : (
                  <><Sparkle size={14} weight="fill" /> {design ? "Régénérer tout" : "Générer avec l'IA"}</>
                )}
              </button>
            </div>

            {/* Sections regenerate */}
            {design && (
              <div className="space-y-2">
                <div className="text-[11px] uppercase tracking-widest text-[#78716C] mb-2">Régénérer par section</div>
                {SECTIONS.map((s) => (
                  <SectionRegen
                    key={s.key}
                    section={s}
                    tweak={sectionTweak[s.key] || ""}
                    setTweak={(v) => setSectionTweak((t) => ({ ...t, [s.key]: v }))}
                    onRegen={() => regenerate(s.key)}
                    loading={!!regenerating[s.key]}
                    value={design[s.key]}
                    brand={design.brand}
                  />
                ))}
              </div>
            )}
          </div>
        </aside>

        {/* RIGHT : preview iframe */}
        <main className="flex-1 bg-[#EAE7E1] relative">
          <div className="h-12 border-b border-[#E7E5E4] bg-white px-5 flex items-center justify-between">
            <div className="flex items-center gap-2 text-sm text-[#78716C]">
              <Eye size={14} /> Aperçu en direct {published ? "(version publiée)" : "(brouillon — visible uniquement pour toi)"}
            </div>
            <button
              onClick={() => setPreviewKey((k) => k + 1)}
              className="text-xs text-[#78716C] hover:text-[#1C1917] flex items-center gap-1"
              data-testid="reload-preview"
            >
              <ArrowsClockwise size={12} /> Recharger
            </button>
          </div>
          {design ? (
            <iframe
              key={previewKey}
              src={previewUrl}
              title="preview"
              data-testid="preview-iframe"
              className="w-full h-[calc(100%-48px)] bg-white"
            />
          ) : (
            <div className="h-[calc(100%-48px)] flex items-center justify-center">
              <div className="text-center max-w-sm">
                <Sparkle size={40} weight="thin" className="mx-auto text-[#B84B31] mb-3" />
                <div className="font-heading text-xl font-semibold text-[#1C1917] mb-2">
                  Ta boutique est prête pour sa métamorphose
                </div>
                <p className="text-sm text-[#78716C]">
                  Clique sur « Générer avec l'IA » à gauche. En 60 secondes, Claude produit l'identité
                  complète (couleurs, hero, pages, FAQ, SEO, logo) adaptée à ta niche.
                </p>
              </div>
            </div>
          )}

          {toast && (
            <div
              className="absolute bottom-5 right-5 px-4 py-3 rounded-xl bg-[#1C1917] text-white text-sm shadow-lg animate-fade-up"
              data-testid="toast"
            >
              {toast}
            </div>
          )}
        </main>
      </div>
    </Layout>
  );
}

/* -------- Section accordion -------- */
function SectionRegen({ section, tweak, setTweak, onRegen, loading, value, brand }) {
  const [open, setOpen] = useState(false);
  const Icon = section.icon;
  const filled = section.key === "logo" ? !!brand?.logo_url : !!value;
  return (
    <div className="bg-white rounded-xl border border-[#E7E5E4]" data-testid={`section-${section.key}`}>
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full p-3 flex items-center gap-3 text-left hover:bg-[#FDFBF7] transition"
      >
        <div className="w-8 h-8 rounded-lg bg-[#FDFBF7] flex items-center justify-center">
          <Icon size={15} weight="fill" className="text-[#B84B31]" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-sm font-medium text-[#1C1917] flex items-center gap-1.5">
            {section.label}
            {filled && <CheckCircle size={12} weight="fill" className="text-[#047857]" />}
          </div>
          <div className="text-[11px] text-[#78716C]">{section.desc}</div>
        </div>
        <span className="text-[#78716C] text-xs">{open ? "−" : "+"}</span>
      </button>
      {open && (
        <div className="px-3 pb-3 pt-1 border-t border-[#E7E5E4]">
          {section.key === "brand" && brand && <BrandPreview brand={brand} />}
          {section.key === "logo" && brand?.logo_url && (
            <img
              src={`${BACKEND_URL}${brand.logo_url}`}
              alt="logo"
              className="w-20 h-20 rounded-lg border border-[#E7E5E4] my-2 object-cover"
              data-testid="logo-preview"
            />
          )}
          <textarea
            value={tweak}
            onChange={(e) => setTweak(e.target.value)}
            placeholder={
              section.key === "logo"
                ? "Ex: « icône coeur stylisé, ton chaleureux »"
                : "Ajustement (optionnel)"
            }
            rows={2}
            data-testid={`tweak-${section.key}`}
            className="w-full text-[13px] px-2.5 py-2 rounded-lg border border-[#E7E5E4] outline-none mt-1"
          />
          <button
            onClick={onRegen}
            disabled={loading}
            data-testid={`regen-${section.key}`}
            className="mt-2 w-full h-9 rounded-lg bg-[#FDFBF7] hover:bg-[#F5F2EB] border border-[#E7E5E4] text-xs font-medium flex items-center justify-center gap-1.5 disabled:opacity-50"
          >
            {loading ? (
              <><ArrowsClockwise size={11} className="animate-spin" /> Régénération…</>
            ) : (
              <><Sparkle size={11} weight="fill" /> Régénérer</>
            )}
          </button>
        </div>
      )}
    </div>
  );
}

function BrandPreview({ brand }) {
  return (
    <div className="my-2 p-3 rounded-lg bg-[#FDFBF7] border border-[#E7E5E4]" data-testid="brand-preview">
      <div className="flex items-center gap-2 mb-2">
        <ColorChip color={brand.primary_color} label="Primaire" />
        <ColorChip color={brand.accent_color} label="Accent" />
      </div>
      <div className="text-xs text-[#78716C]">
        {brand.font_heading} · {brand.font_body}
      </div>
    </div>
  );
}

function ColorChip({ color, label }) {
  return (
    <div className="flex items-center gap-1.5">
      <div className="w-5 h-5 rounded-full border border-[#E7E5E4]" style={{ background: color }} />
      <span className="text-[11px] text-[#78716C]">{label}</span>
    </div>
  );
}
