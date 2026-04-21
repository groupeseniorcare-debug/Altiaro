import React, { useEffect, useState, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { api, apiCall } from "../lib/api";
import Layout from "../components/Layout";
import KeywordFinder from "../components/KeywordFinder";
import {
  ArrowLeft,
  CheckCircle,
  ArrowClockwise,
  Sparkle,
  Eye,
  Palette,
  PencilSimple,
  CaretDown,
  CaretRight,
  MagnifyingGlass,
  Lightning,
  CheckFat,
  X,
} from "@phosphor-icons/react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const SECTIONS = [
  {
    id: "identity",
    title: "1. Identité de marque",
    icon: "✨",
    desc: "Nom, tagline, brand story. Claude invente une marque unique.",
  },
  {
    id: "positioning",
    title: "2. Positionnement",
    icon: "🎯",
    desc: "Promesse, USPs, voix, cible. Base de toute la com.",
  },
  {
    id: "hero",
    title: "3. Hero homepage",
    icon: "🌟",
    desc: "Headline + subtitle + CTA + trust line (style Apple/Dyson).",
  },
  {
    id: "benefits",
    title: "4. Bénéfices (4 blocs)",
    icon: "💎",
    desc: "Blocs de réassurance avec icônes (livraison, garantie, SAV...).",
  },
  {
    id: "testimonials",
    title: "5. Témoignages clients",
    icon: "⭐",
    desc: "5 avis réalistes cohérents avec le persona et le pays.",
  },
  {
    id: "faq",
    title: "6. FAQ",
    icon: "❓",
    desc: "7 questions/réponses (produit, livraison, retour).",
  },
  {
    id: "seo",
    title: "7. SEO homepage",
    icon: "🔍",
    desc: "Meta title, description, keywords transactionnels.",
  },
];

export default function PromptStudio() {
  const { id: siteId } = useParams();
  const navigate = useNavigate();
  const [state, setState] = useState(null);
  const [loading, setLoading] = useState(true);
  const [expandedSection, setExpandedSection] = useState("identity");
  const [promptEdits, setPromptEdits] = useState({});
  const [generated, setGenerated] = useState({});
  const [running, setRunning] = useState(null);
  const [applying, setApplying] = useState(null);
  const [showPreview, setShowPreview] = useState(false);
  const [paletteModal, setPaletteModal] = useState(false);
  const [palettes, setPalettes] = useState([]);
  const [palettesLoading, setPalettesLoading] = useState(false);
  const [customColor, setCustomColor] = useState("#B84B31");
  const [kwModal, setKwModal] = useState(false);
  const [previewTick, setPreviewTick] = useState(0);

  const load = useCallback(async () => {
    const { data } = await apiCall(() =>
      api.get(`/sites/${siteId}/design/studio-state`)
    );
    if (data) {
      setState(data);
      // Seed prompt edits with defaults
      setPromptEdits((prev) => {
        const next = { ...prev };
        Object.entries(data.default_prompts || {}).forEach(([k, v]) => {
          if (!next[k]) next[k] = v;
        });
        return next;
      });
    }
    setLoading(false);
  }, [siteId]);

  useEffect(() => {
    load();
  }, [load]);

  const runPrompt = async (sectionId) => {
    setRunning(sectionId);
    const { data, error } = await apiCall(() =>
      api.post(`/sites/${siteId}/design/prompt/run`, {
        section: sectionId,
        prompt: promptEdits[sectionId] || null,
      })
    );
    setRunning(null);
    if (error) {
      window.alert("Erreur : " + error);
      return;
    }
    setGenerated((prev) => ({ ...prev, [sectionId]: data.data }));
  };

  const applyGenerated = async (sectionId) => {
    if (!generated[sectionId]) return;
    setApplying(sectionId);
    const { error } = await apiCall(() =>
      api.post(`/sites/${siteId}/design/prompt/apply`, {
        section: sectionId,
        data: generated[sectionId],
      })
    );
    setApplying(null);
    if (error) {
      window.alert("Erreur : " + error);
      return;
    }
    await load();
    setPreviewTick((x) => x + 1);
  };

  const suggestPalettes = async () => {
    setPalettesLoading(true);
    const { data, error } = await apiCall(() =>
      api.post(`/sites/${siteId}/design/palette/suggest`, {})
    );
    setPalettesLoading(false);
    if (error) {
      window.alert("Erreur : " + error);
      return;
    }
    setPalettes(data.palettes || []);
  };

  const applyPalette = async (p) => {
    await apiCall(() =>
      api.post(`/sites/${siteId}/design/palette/apply`, {
        primary_color: p.primary_color,
        secondary_color: p.secondary_color,
        background_color: p.background_color,
        text_color: p.text_color,
        font_heading: p.font_heading,
        font_body: p.font_body,
      })
    );
    await load();
    setPreviewTick((x) => x + 1);
    setPaletteModal(false);
  };

  const applyCustomColor = async () => {
    await apiCall(() =>
      api.post(`/sites/${siteId}/design/palette/apply`, {
        primary_color: customColor,
      })
    );
    await load();
    setPreviewTick((x) => x + 1);
    setPaletteModal(false);
  };

  if (loading) {
    return (
      <Layout>
        <div className="p-12 text-[#78716C]">Chargement du Studio…</div>
      </Layout>
    );
  }

  const filledCount = Object.values(state?.sections || {}).filter((s) => s.filled).length;
  const percent = Math.round((filledCount / SECTIONS.length) * 100);
  const brandColor = state?.brand?.primary_color || "#B84B31";
  const previewUrl = `${BACKEND_URL}/shop/${siteId}?studio=${previewTick}`;

  return (
    <Layout>
      <div className="p-8 md:p-12 max-w-[1200px]">
        <button
          onClick={() => navigate(`/sites/${siteId}`)}
          className="flex items-center gap-2 text-sm text-[#78716C] hover:text-[#1C1917] mb-6 transition"
          data-testid="studio-back"
        >
          <ArrowLeft size={16} /> Retour au site
        </button>

        <div className="bg-gradient-to-br from-[#1C1917] via-[#44403C] to-[#7C3AED] rounded-2xl p-8 mb-6 text-white">
          <div className="flex items-start justify-between gap-6">
            <div>
              <div className="text-[11px] uppercase tracking-widest text-white/60 mb-2">
                Prompt Studio · Wizard IA par section
              </div>
              <h1 className="font-heading text-4xl font-semibold mb-2">
                Construis ta boutique, section par section
              </h1>
              <p className="text-white/80 max-w-2xl">
                Chaque prompt est pré-rempli avec les données de ton analyse + tes produits.
                Édite si tu veux, génère, preview, applique.{" "}
                {state?.site_name && (
                  <>
                    Site : <strong>{state.site_name}</strong>
                  </>
                )}
              </p>
            </div>
            <div className="text-right min-w-[200px]">
              <div className="text-[11px] uppercase tracking-widest text-white/60">Avancement</div>
              <div className="font-heading text-5xl font-semibold">{percent}%</div>
              <div className="text-sm text-white/70">
                {filledCount} / {SECTIONS.length} sections
              </div>
              <div className="flex gap-2 mt-3 justify-end">
                <button
                  onClick={() => setPaletteModal(true)}
                  data-testid="studio-palette-btn"
                  className="h-9 px-3 rounded-lg bg-white/10 hover:bg-white/20 border border-white/20 text-xs font-medium flex items-center gap-1.5"
                >
                  <Palette size={14} weight="bold" />
                  Palette
                </button>
                <button
                  onClick={() => setKwModal(true)}
                  data-testid="studio-keywords-btn"
                  className="h-9 px-3 rounded-lg bg-white/10 hover:bg-white/20 border border-white/20 text-xs font-medium flex items-center gap-1.5"
                >
                  <MagnifyingGlass size={14} weight="bold" />
                  Mots-clés
                </button>
                <button
                  onClick={() => setShowPreview(true)}
                  data-testid="studio-preview-btn"
                  className="h-9 px-3 rounded-lg bg-white text-[#1C1917] text-xs font-medium flex items-center gap-1.5"
                >
                  <Eye size={14} weight="fill" />
                  Voir live
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Current brand palette preview */}
        {state?.brand?.primary_color && (
          <div className="bg-white rounded-xl border border-[#E7E5E4] p-4 mb-5 flex items-center gap-4">
            <div className="flex gap-2">
              {[
                state.brand.background_color || "#FDFBF7",
                state.brand.primary_color,
                state.brand.secondary_color || "#78716C",
                state.brand.text_color || "#1C1917",
              ].map((c, i) => (
                <div
                  key={i}
                  className="w-10 h-10 rounded-lg border border-[#E7E5E4] shadow-sm"
                  style={{ backgroundColor: c }}
                  title={c}
                />
              ))}
            </div>
            <div className="flex-1">
              <div className="text-xs text-[#78716C] uppercase tracking-wider">Palette actuelle</div>
              <div className="text-sm font-medium">
                {state.brand.name || "Marque non générée"}
                {state.brand.tagline && ` — ${state.brand.tagline}`}
              </div>
            </div>
            <div className="text-xs text-[#78716C]">
              Font: {state.brand.font_heading || "Fraunces"} / {state.brand.font_body || "Inter"}
            </div>
          </div>
        )}

        <div className="space-y-3">
          {SECTIONS.map((section) => {
            const sState = state?.sections?.[section.id] || {};
            const isExpanded = expandedSection === section.id;
            const gen = generated[section.id];
            return (
              <div
                key={section.id}
                data-testid={`studio-section-${section.id}`}
                className={`bg-white rounded-xl border transition ${
                  sState.filled ? "border-[#D1FAE5]" : "border-[#E7E5E4]"
                }`}
              >
                <button
                  onClick={() => setExpandedSection(isExpanded ? null : section.id)}
                  className="w-full p-5 flex items-center gap-4 text-left"
                >
                  <div
                    className={`w-10 h-10 rounded-lg flex items-center justify-center text-lg shrink-0 ${
                      sState.filled ? "bg-[#D1FAE5]" : "bg-[#F5F2EB]"
                    }`}
                  >
                    {sState.filled ? (
                      <CheckCircle size={20} weight="fill" className="text-[#047857]" />
                    ) : (
                      <span>{section.icon}</span>
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="font-heading text-lg font-semibold text-[#1C1917]">
                      {section.title}
                    </div>
                    <div className="text-xs text-[#78716C] mt-0.5">{section.desc}</div>
                  </div>
                  {sState.filled && !isExpanded && (
                    <span className="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full bg-[#D1FAE5] text-[#047857] font-medium mr-2">
                      ✓ Rempli
                    </span>
                  )}
                  {isExpanded ? <CaretDown size={16} /> : <CaretRight size={16} />}
                </button>

                {isExpanded && (
                  <div className="px-5 pb-5 border-t border-[#F5F2EB] pt-4 space-y-3">
                    <div>
                      <label className="block text-xs font-semibold text-[#57534E] mb-1.5 uppercase tracking-wider">
                        Prompt (éditable)
                      </label>
                      <textarea
                        value={promptEdits[section.id] || ""}
                        onChange={(e) =>
                          setPromptEdits((prev) => ({ ...prev, [section.id]: e.target.value }))
                        }
                        rows={4}
                        data-testid={`studio-prompt-${section.id}`}
                        className="w-full px-3 py-2 rounded-lg border border-[#E7E5E4] bg-[#FAF7F2] text-sm focus:outline-none focus:border-[#7C3AED] font-mono"
                      />
                    </div>

                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => runPrompt(section.id)}
                        disabled={running === section.id}
                        data-testid={`studio-run-${section.id}`}
                        className="h-10 px-4 rounded-lg bg-[#7C3AED] hover:bg-[#6D28D9] disabled:opacity-60 text-white text-sm font-medium flex items-center gap-2"
                      >
                        {running === section.id ? (
                          <>
                            <ArrowClockwise size={14} className="animate-spin" />
                            Claude génère…
                          </>
                        ) : (
                          <>
                            <Lightning size={14} weight="fill" />
                            Générer
                          </>
                        )}
                      </button>
                      {gen && (
                        <button
                          onClick={() => applyGenerated(section.id)}
                          disabled={applying === section.id}
                          data-testid={`studio-apply-${section.id}`}
                          className="h-10 px-4 rounded-lg bg-[#047857] hover:bg-[#065F46] disabled:opacity-60 text-white text-sm font-medium flex items-center gap-2"
                        >
                          {applying === section.id ? (
                            <ArrowClockwise size={14} className="animate-spin" />
                          ) : (
                            <CheckFat size={14} weight="fill" />
                          )}
                          Appliquer au site
                        </button>
                      )}
                    </div>

                    {gen && (
                      <div className="mt-2 bg-[#FAF7F2] rounded-lg p-4 border border-[#E7E5E4]">
                        <div className="text-xs font-semibold text-[#57534E] mb-2 uppercase tracking-wider">
                          Résultat Claude
                        </div>
                        <pre
                          className="text-xs text-[#1C1917] whitespace-pre-wrap font-mono max-h-96 overflow-y-auto"
                          data-testid={`studio-result-${section.id}`}
                        >
                          {JSON.stringify(gen, null, 2)}
                        </pre>
                      </div>
                    )}

                    {sState.filled && !gen && (
                      <div className="text-xs text-[#78716C] bg-[#FAF7F2] rounded-lg px-3 py-2 border border-dashed border-[#E7E5E4]">
                        Cette section est déjà remplie sur ton site. Regénère pour la remplacer.
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Palette modal */}
      {paletteModal && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
          onClick={() => setPaletteModal(false)}
        >
          <div
            className="bg-white rounded-2xl w-full max-w-3xl max-h-[90vh] flex flex-col shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between px-6 py-4 border-b border-[#E7E5E4]">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-[#F97316] to-[#B84B31] flex items-center justify-center">
                  <Palette size={18} weight="bold" color="#fff" />
                </div>
                <div>
                  <div className="font-heading font-semibold">Palette de couleurs</div>
                  <div className="text-xs text-[#78716C]">
                    3 propositions IA ou palette custom
                  </div>
                </div>
              </div>
              <button
                onClick={() => setPaletteModal(false)}
                className="w-8 h-8 rounded-lg hover:bg-[#F5F2EB] flex items-center justify-center"
              >
                <X size={16} />
              </button>
            </div>

            <div className="overflow-y-auto p-6">
              <button
                onClick={suggestPalettes}
                disabled={palettesLoading}
                data-testid="studio-palette-suggest"
                className="w-full h-11 mb-5 rounded-lg bg-[#7C3AED] hover:bg-[#6D28D9] disabled:opacity-60 text-white text-sm font-medium flex items-center justify-center gap-2"
              >
                {palettesLoading ? (
                  <>
                    <ArrowClockwise size={14} className="animate-spin" />
                    Claude réfléchit…
                  </>
                ) : (
                  <>
                    <Sparkle size={14} weight="fill" />
                    Proposer 3 palettes IA
                  </>
                )}
              </button>

              {palettes.map((p, i) => (
                <div
                  key={i}
                  data-testid={`studio-palette-${i}`}
                  className="mb-3 p-4 border border-[#E7E5E4] rounded-xl hover:border-[#7C3AED] transition"
                >
                  <div className="flex items-start justify-between mb-2">
                    <div>
                      <div className="font-medium text-[#1C1917]">{p.name}</div>
                      <div className="text-xs text-[#78716C]">{p.description}</div>
                    </div>
                    <button
                      onClick={() => applyPalette(p)}
                      data-testid={`studio-palette-apply-${i}`}
                      className="h-8 px-3 rounded-lg bg-[#1C1917] hover:bg-[#44403C] text-white text-xs font-medium"
                    >
                      Appliquer
                    </button>
                  </div>
                  <div className="flex gap-1.5 items-center">
                    {[p.background_color, p.primary_color, p.secondary_color, p.text_color].map(
                      (c, j) => (
                        <div
                          key={j}
                          className="flex-1 h-12 rounded-lg border border-[#E7E5E4]"
                          style={{ backgroundColor: c }}
                          title={c}
                        />
                      )
                    )}
                  </div>
                  <div className="text-[10px] text-[#78716C] mt-2 font-mono">
                    Fonts : {p.font_heading} / {p.font_body}
                  </div>
                </div>
              ))}

              <div className="mt-6 p-4 bg-[#FAF7F2] rounded-xl">
                <div className="text-xs font-semibold uppercase tracking-wider text-[#57534E] mb-2">
                  Ou choisis ta couleur principale libre
                </div>
                <div className="flex items-center gap-3">
                  <input
                    type="color"
                    value={customColor}
                    onChange={(e) => setCustomColor(e.target.value)}
                    data-testid="studio-palette-custom-color"
                    className="w-14 h-14 rounded-lg cursor-pointer border border-[#E7E5E4]"
                  />
                  <input
                    type="text"
                    value={customColor}
                    onChange={(e) => setCustomColor(e.target.value)}
                    className="flex-1 h-10 px-3 rounded-lg border border-[#E7E5E4] font-mono text-sm"
                  />
                  <button
                    onClick={applyCustomColor}
                    data-testid="studio-palette-custom-apply"
                    className="h-10 px-4 rounded-lg bg-[#1C1917] hover:bg-[#44403C] text-white text-sm font-medium"
                  >
                    Appliquer
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Live preview modal */}
      {showPreview && (
        <div className="fixed inset-0 z-50 bg-black/70 p-4 flex flex-col">
          <div className="bg-[#1C1917] text-white px-4 py-3 flex items-center justify-between rounded-t-xl">
            <div className="flex items-center gap-3">
              <Eye size={18} weight="fill" />
              <div>
                <div className="font-medium text-sm">Preview Live · {state?.site_name}</div>
                <div className="text-xs text-white/60 font-mono">{previewUrl}</div>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <a
                href={previewUrl}
                target="_blank"
                rel="noreferrer"
                className="h-8 px-3 rounded-lg bg-white/10 hover:bg-white/20 text-xs font-medium flex items-center gap-1"
              >
                Ouvrir dans un onglet →
              </a>
              <button
                onClick={() => setShowPreview(false)}
                data-testid="studio-preview-close"
                className="w-8 h-8 rounded-lg hover:bg-white/10 flex items-center justify-center"
              >
                <X size={16} />
              </button>
            </div>
          </div>
          <iframe
            key={previewTick}
            src={previewUrl}
            title="preview"
            className="flex-1 w-full bg-white rounded-b-xl border-0"
            data-testid="studio-preview-iframe"
          />
        </div>
      )}

      {/* Keyword finder modal */}
      {kwModal && (
        <KeywordFinder
          initialSeed={state?.site_name || ""}
          initialCountry="FR"
          onClose={() => setKwModal(false)}
        />
      )}
    </Layout>
  );
}
