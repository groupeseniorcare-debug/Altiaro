import React, { useEffect, useState } from "react";
import {
  Sparkle, ArrowRight, ArrowLeft, CheckCircle, Rocket, Palette,
  TextT, Target, Package, ArrowClockwise, Warning, XCircle, MagicWand,
} from "@phosphor-icons/react";
import { api, apiCall } from "../lib/api";

/**
 * 5-step wizard that collects a brand brief and launches the full-site
 * orchestrator (logo, palette, homepage, about, contact, product narratives
 * + premium AI images for every imported product).
 */
const MOODS = [
  { key: "Éditorial", label: "Éditorial", desc: "Le Monde · Kinfolk · photo en lumière naturelle.",
    palettes: [{ primary: "#1C1917", accent: "#C2410C", background: "#FAF7F2", text: "#1C1917" }] },
  { key: "Minimaliste", label: "Minimaliste", desc: "Aesop · Muji · neutre et respirant.",
    palettes: [{ primary: "#0F172A", accent: "#64748B", background: "#FFFFFF", text: "#0F172A" }] },
  { key: "Chaleureux", label: "Chaleureux", desc: "Silver economy · tons terre, rassurants.",
    palettes: [{ primary: "#B84B31", accent: "#E9C46A", background: "#FAF7F2", text: "#1C1917" }] },
  { key: "Moderne", label: "Moderne", desc: "Dyson · Apple · tech & métal.",
    palettes: [{ primary: "#2563EB", accent: "#0EA5E9", background: "#F8FAFC", text: "#0F172A" }] },
];

const FONT_PAIRS = [
  { heading: "Fraunces", body: "Inter",        label: "Fraunces × Inter (luxe éditorial)" },
  { heading: "Playfair Display", body: "DM Sans", label: "Playfair × DM Sans (classique moderne)" },
  { heading: "Cormorant Garamond", body: "Manrope", label: "Cormorant × Manrope (hautement premium)" },
  { heading: "Libre Caslon Text", body: "Poppins", label: "Libre Caslon × Poppins (confortable)" },
];

export default function BrandWizard({ site, onLaunched, onExit }) {
  // Garde anti-crash : la page parente peut monter ce composant avant que
  // le fetch site soit résolu. On affiche un placeholder tant que la prop
  // n'est pas hydratée — sinon l'accès à site.id en JS lève "site is undefined"
  // (cf. crash étape 5 du 26 avr.).
  const siteId = site?.id;
  const [step, setStep] = useState(0);
  const [brandName, setBrandName] = useState(site?.design?.brand?.logo_text || site?.name || "");
  const [tagline, setTagline] = useState(site?.design?.brand?.tagline || "");
  const [mission, setMission] = useState(site?.design?.brand?.mission || "");
  const [voice, setVoice] = useState(site?.design?.brand?.voice || "chaleureux et rassurant, premium");
  const [mood, setMood] = useState("Chaleureux");
  const [paletteIdx, setPaletteIdx] = useState(0);
  const [fontPair, setFontPair] = useState(FONT_PAIRS[0]);
  const [overwrite, setOverwrite] = useState(false);
  const [launching, setLaunching] = useState(false);
  const [error, setError] = useState("");
  const [productsCount, setProductsCount] = useState(0);
  // AI pre-fill suggestions (Step 1) + budget status banner
  const [suggesting, setSuggesting] = useState(false);
  const [nameSuggestions, setNameSuggestions] = useState([]);
  const [suggestError, setSuggestError] = useState("");
  const [llmStatus, setLlmStatus] = useState("ok"); // "ok" | "budget_exhausted" | "checking"

  useEffect(() => {
    if (!siteId) return;
    apiCall(() => api.get(`/sites/${siteId}/products`)).then(({ data }) => {
      if (Array.isArray(data)) setProductsCount(data.filter((p) => p.status !== "deleted").length);
    });
    // Surface LLM budget status so the Concepteur doesn't spend time filling the
    // wizard only to hit a budget error at launch.
    apiCall(() => api.get(`/platform/llm-status`)).then(({ data }) => {
      if (data?.status) setLlmStatus(data.status);
    });
  }, [siteId]);

  if (!site || !siteId) {
    return (
      <div className="p-8 text-center text-neutral-500" data-testid="brand-wizard-loading">
        Chargement de l'identité de marque…
      </div>
    );
  }

  const fetchSuggestions = async () => {
    setSuggestError("");
    setSuggesting(true);
    const { data, error: err, rawDetail } = await apiCall(() =>
      api.post(`/sites/${siteId}/design/wizard-suggestions`, {})
    );
    setSuggesting(false);
    if (err) {
      const detail = rawDetail?.detail || err;
      setSuggestError(detail);
      if (/budget/i.test(detail) || /402/.test(detail)) setLlmStatus("budget_exhausted");
      return;
    }
    setNameSuggestions(data?.names || []);
    // Auto-fill empty fields so the user sees an instant result.
    if (!brandName.trim() && data?.names?.[0]) setBrandName(data.names[0]);
    if (!tagline.trim() && data?.tagline) setTagline(data.tagline);
    if (!mission.trim() && data?.mission) setMission(data.mission);
    if (data?.voice) setVoice(data.voice);
  };

  const launch = async () => {
    setError("");
    setLaunching(true);
    const moodObj = MOODS.find((m) => m.key === mood) || MOODS[2];
    const paletteChoice = moodObj.palettes[paletteIdx] || moodObj.palettes[0];
    const payload = {
      brand_name: brandName.trim(),
      tagline: tagline.trim(),
      mission: mission.trim(),
      voice: voice.trim(),
      mood,
      palette_choice: paletteChoice,
      font_pair: fontPair,
      homepage_preset: "default_template",
      overwrite_all: overwrite,
      logo_style: "horizontal_premium",
    };
    const { data, error: err, rawDetail } = await apiCall(() =>
      api.post(`/sites/${siteId}/design/launch`, payload)
    );
    setLaunching(false);
    if (err) { setError(rawDetail?.detail || err); return; }
    onLaunched?.(data?.job_id);
  };

  const canNext = () => {
    if (step === 0) return brandName.trim().length >= 2;
    if (step === 1) return true;
    if (step === 2) return true;
    if (step === 3) return true;
    return true;
  };

  const steps = [
    { key: "identity",    label: "Identité",    Icon: Sparkle },
    { key: "mood",        label: "Ambiance",    Icon: Palette },
    { key: "typography",  label: "Typographie", Icon: TextT },
    { key: "scope",       label: "Portée",      Icon: Target },
    { key: "launch",      label: "Lancement",   Icon: Rocket },
  ];

  return (
    <div className="max-w-3xl mx-auto" data-testid="brand-wizard">
      {/* Stepper */}
      <div className="bg-white border border-neutral-200 rounded-2xl p-2 flex gap-1 mb-6 overflow-x-auto">
        {steps.map((s, i) => (
          <div
            key={s.key}
            data-testid={`wizard-step-${s.key}`}
            className={`flex-1 h-10 px-3 rounded-xl text-xs font-medium flex items-center justify-center gap-1.5 whitespace-nowrap transition ${
              i < step ? "text-emerald-600" : i === step ? "bg-neutral-900 text-white" : "text-neutral-400"
            }`}
          >
            <s.Icon size={12} weight={i <= step ? "fill" : "duotone"} />
            {s.label}
            {i < step && <CheckCircle size={12} weight="fill" />}
          </div>
        ))}
      </div>

      <div className="bg-white border border-neutral-200 rounded-2xl p-8 min-h-[420px]">
        {llmStatus === "budget_exhausted" && (
          <div
            className="mb-6 rounded-xl border border-amber-300 bg-amber-50 p-4 flex items-start gap-3"
            data-testid="wizard-budget-banner"
          >
            <Warning size={20} weight="fill" className="text-amber-600 flex-shrink-0 mt-0.5" />
            <div className="flex-1 text-sm text-amber-900">
              <div className="font-semibold mb-0.5">Budget Universal Key épuisé</div>
              <div className="text-xs text-amber-800 leading-relaxed">
                Les suggestions IA et la génération complète ne peuvent pas s'exécuter tant que la clé n'est pas rechargée.
                Ouvre <strong>Profile → Universal Key → Add Balance</strong> (ou active l'auto top-up), puis reviens ici.
              </div>
            </div>
          </div>
        )}

        {step === 0 && (
          <Step title="Identité de marque" subtitle="2 min. Ces infos seront utilisées partout — logo, copy, SEO.">
            <div className="rounded-xl bg-gradient-to-br from-violet-50 to-indigo-50 border border-violet-200 p-4">
              <div className="flex items-start gap-3 flex-wrap">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-600 to-indigo-600 flex items-center justify-center shrink-0">
                  <MagicWand size={18} weight="fill" className="text-white" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-semibold text-violet-900">Pas d'inspiration ? Laisse Claude proposer</div>
                  <div className="text-[11px] text-violet-800/80 mt-0.5 leading-snug">
                    Il analyse ta niche + tes produits importés et te donne 3 noms + tagline + mission + voix en 10 secondes.
                  </div>
                </div>
                <button
                  onClick={fetchSuggestions}
                  disabled={suggesting || llmStatus === "budget_exhausted"}
                  data-testid="wizard-suggest-ai"
                  className="h-10 px-4 rounded-lg bg-gradient-to-r from-violet-600 to-indigo-600 hover:brightness-110 text-white text-sm font-medium flex items-center gap-2 shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {suggesting ? <ArrowClockwise size={14} className="animate-spin" /> : <Sparkle size={14} weight="fill" />}
                  {suggesting ? "Claude réfléchit…" : "✨ Suggestions IA"}
                </button>
              </div>
              {suggestError && (
                <div className="mt-3 text-xs text-red-700 bg-white/60 border border-red-200 rounded-lg p-2 flex items-center gap-2">
                  <XCircle size={12} weight="fill" /> {suggestError}
                </div>
              )}
              {nameSuggestions.length > 0 && (
                <div className="mt-3" data-testid="wizard-name-suggestions">
                  <div className="text-[10px] uppercase tracking-[0.2em] text-violet-700 mb-2">
                    Noms proposés — clique pour remplir
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {nameSuggestions.map((n) => (
                      <button
                        key={n}
                        onClick={() => setBrandName(n)}
                        data-testid={`wizard-name-chip-${n}`}
                        className={`h-8 px-3 rounded-full border text-sm font-medium transition ${
                          brandName === n
                            ? "bg-neutral-900 text-white border-neutral-900"
                            : "bg-white text-neutral-800 border-neutral-300 hover:border-neutral-900"
                        }`}
                      >
                        {n}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <Field label="Nom de la marque *">
              <input type="text" value={brandName} onChange={(e) => setBrandName(e.target.value)}
                data-testid="wizard-brand-name"
                placeholder="Ex. « Maison Clarelle » ou « Alvenar & Fils »"
                className="w-full h-11 px-4 rounded-lg border border-neutral-200 bg-white text-base focus:outline-none focus:border-neutral-900" />
              <div className="text-[11px] text-neutral-500 mt-1">
                Conseil premium : nom de famille + référence maison / atelier / &amp; fils.
              </div>
            </Field>
            <Field label="Tagline (promesse en 8 mots)">
              <input type="text" value={tagline} onChange={(e) => setTagline(e.target.value)}
                data-testid="wizard-tagline" maxLength={90}
                placeholder="Ex. « Le confort quotidien, simplement »"
                className="w-full h-11 px-4 rounded-lg border border-neutral-200 bg-white text-base" />
            </Field>
            <Field label="Mission (pourquoi cette marque existe ?)">
              <textarea value={mission} onChange={(e) => setMission(e.target.value)}
                data-testid="wizard-mission" rows={2} maxLength={280}
                placeholder="Ex. « Rendre l'autonomie retrouvée accessible à tous les seniors, sans jamais sacrifier le goût. »"
                className="w-full p-3 rounded-lg border border-neutral-200 bg-white text-sm resize-y" />
            </Field>
            <Field label="Voix de marque">
              <input type="text" value={voice} onChange={(e) => setVoice(e.target.value)}
                data-testid="wizard-voice"
                className="w-full h-11 px-4 rounded-lg border border-neutral-200 bg-white text-sm" />
            </Field>
          </Step>
        )}

        {step === 1 && (
          <Step title="Ambiance visuelle" subtitle="L'ambiance dicte la palette, le logo, et le ton des images IA.">
            <div className="grid grid-cols-2 gap-3">
              {MOODS.map((m) => (
                <button key={m.key} onClick={() => { setMood(m.key); setPaletteIdx(0); }}
                  data-testid={`wizard-mood-${m.key.toLowerCase()}`}
                  className={`text-left p-4 rounded-xl border-2 transition ${
                    mood === m.key ? "border-neutral-900 bg-neutral-50" : "border-neutral-200 hover:border-neutral-400"
                  }`}>
                  <div className="flex gap-1.5 mb-3">
                    {Object.values(m.palettes[0]).slice(0, 4).map((c, j) => (
                      <div key={j} className="w-7 h-7 rounded-full border border-neutral-200"
                        style={{ background: c }} />
                    ))}
                  </div>
                  <div className="text-sm font-semibold text-neutral-900">{m.label}</div>
                  <div className="text-[11px] text-neutral-500 mt-0.5 leading-snug">{m.desc}</div>
                </button>
              ))}
            </div>
          </Step>
        )}

        {step === 2 && (
          <Step title="Typographie" subtitle="Choisis une paire : serif premium pour les titres + sans-serif lisible pour le corps.">
            <div className="space-y-2">
              {FONT_PAIRS.map((fp) => (
                <button key={fp.label} onClick={() => setFontPair(fp)}
                  data-testid={`wizard-font-${fp.heading.toLowerCase().replace(/ /g, "-")}`}
                  className={`w-full text-left p-5 rounded-xl border-2 transition ${
                    fontPair.heading === fp.heading ? "border-neutral-900 bg-neutral-50" : "border-neutral-200 hover:border-neutral-400"
                  }`}>
                  <div className="text-3xl leading-none mb-2"
                    style={{ fontFamily: `"${fp.heading}", serif` }}>
                    Le confort retrouvé
                  </div>
                  <div className="text-sm text-neutral-700 mb-2"
                    style={{ fontFamily: `"${fp.body}", sans-serif` }}>
                    Des produits pensés pour accompagner le quotidien avec douceur et sécurité.
                  </div>
                  <div className="text-[11px] text-neutral-500 font-mono">{fp.label}</div>
                </button>
              ))}
            </div>
          </Step>
        )}

        {step === 3 && (
          <Step title="Portée de la génération" subtitle="Choisis comment l'IA traite ton contenu existant.">
            <div className="space-y-3">
              <button onClick={() => setOverwrite(false)}
                data-testid="wizard-scope-fill"
                className={`w-full text-left p-5 rounded-xl border-2 transition ${
                  !overwrite ? "border-neutral-900 bg-neutral-50" : "border-neutral-200 hover:border-neutral-400"
                }`}>
                <div className="flex items-center gap-3">
                  <Sparkle size={18} weight="fill" className="text-violet-600" />
                  <div className="flex-1">
                    <div className="text-sm font-semibold">Remplir uniquement ce qui manque</div>
                    <div className="text-xs text-neutral-500 mt-0.5">
                      Conserve tout le travail déjà fait (textes, images, palette) et complète uniquement les sections vides.
                    </div>
                  </div>
                </div>
              </button>
              <button onClick={() => setOverwrite(true)}
                data-testid="wizard-scope-overwrite"
                className={`w-full text-left p-5 rounded-xl border-2 transition ${
                  overwrite ? "border-neutral-900 bg-neutral-50" : "border-neutral-200 hover:border-neutral-400"
                }`}>
                <div className="flex items-center gap-3">
                  <Warning size={18} weight="fill" className="text-amber-600" />
                  <div className="flex-1">
                    <div className="text-sm font-semibold">Tout régénérer (clean slate)</div>
                    <div className="text-xs text-neutral-500 mt-0.5">
                      Écrase tous les contenus IA existants avec une nouvelle génération premium. Utile si tu refais le site.
                    </div>
                  </div>
                </div>
              </button>
            </div>

            <div className="mt-4 p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-xs text-emerald-900 flex items-start gap-2">
              <Package size={16} weight="duotone" className="flex-shrink-0 mt-0.5" />
              <div>
                <strong>{productsCount} produits</strong> importés seront enrichis avec :
                <ul className="mt-1 ml-4 list-disc space-y-0.5">
                  <li>Fiche narrative détaillée (titre, histoire, usage, bénéfices, FAQ)</li>
                  <li>3 images IA premium (lifestyle, studio, gros plan) + tes images fournisseur</li>
                  <li>2 images contextuelles dans les sections narrative</li>
                </ul>
              </div>
            </div>
          </Step>
        )}

        {step === 4 && (
          <Step title="Prêt à lancer ?" subtitle="Un dernier récapitulatif avant que l'IA démarre.">
            <Recap label="Marque" value={brandName} />
            <Recap label="Tagline" value={tagline || "(à générer)"} />
            <Recap label="Ambiance" value={`${mood} · ${Object.values(MOODS.find((m) => m.key === mood).palettes[0]).slice(0, 4).join(" / ")}`} />
            <Recap label="Typographie" value={`${fontPair.heading} × ${fontPair.body}`} />
            <Recap label="Scope" value={overwrite ? "Régénération complète" : "Remplir les trous uniquement"} />
            <Recap label="Produits à enrichir" value={`${productsCount}`} />

            {error && (
              <div className="mt-4 p-3 rounded-lg bg-red-50 border border-red-200 text-xs text-red-700 flex items-center gap-2">
                <XCircle size={14} weight="fill" /> {error}
              </div>
            )}
          </Step>
        )}
      </div>

      {/* Nav */}
      <div className="mt-4 flex items-center justify-between gap-3">
        <button onClick={step === 0 ? onExit : () => setStep(step - 1)}
          data-testid="wizard-back"
          className="h-10 px-4 rounded-lg border border-neutral-200 bg-white hover:bg-neutral-50 text-sm flex items-center gap-2 text-neutral-700">
          <ArrowLeft size={14} />
          {step === 0 ? "Mode avancé" : "Retour"}
        </button>
        {step < 4 ? (
          <button onClick={() => setStep(step + 1)}
            disabled={!canNext()}
            data-testid="wizard-next"
            className="h-10 px-5 rounded-lg bg-neutral-900 text-white hover:bg-neutral-800 text-sm flex items-center gap-2 disabled:opacity-50">
            Suivant <ArrowRight size={14} />
          </button>
        ) : (
          <button onClick={launch} disabled={launching || llmStatus === "budget_exhausted"}
            data-testid="wizard-launch"
            title={llmStatus === "budget_exhausted" ? "Recharge la Universal Key pour lancer" : ""}
            className="h-12 px-7 rounded-xl bg-gradient-to-r from-violet-600 to-indigo-600 text-white hover:brightness-110 text-base font-semibold flex items-center gap-2.5 shadow-xl disabled:opacity-60 disabled:cursor-not-allowed">
            {launching ? <ArrowClockwise size={16} className="animate-spin" /> : <Rocket size={16} weight="fill" />}
            {launching ? "Démarrage…" : llmStatus === "budget_exhausted" ? "Budget IA épuisé" : "⚡ Lancer la création complète"}
          </button>
        )}
      </div>
    </div>
  );
}

function Step({ title, subtitle, children }) {
  return (
    <div>
      <h2 className="text-2xl font-semibold text-neutral-900 mb-1">{title}</h2>
      <p className="text-sm text-neutral-500 mb-6">{subtitle}</p>
      <div className="space-y-4">{children}</div>
    </div>
  );
}

function Field({ label, children }) {
  return (
    <div>
      <div className="text-[11px] uppercase tracking-widest text-neutral-500 mb-1.5">{label}</div>
      {children}
    </div>
  );
}

function Recap({ label, value }) {
  return (
    <div className="flex items-center justify-between py-2 border-b border-neutral-100 last:border-b-0 gap-3">
      <span className="text-xs text-neutral-500 uppercase tracking-wide">{label}</span>
      <span className="text-sm font-medium text-neutral-900 text-right truncate max-w-[60%]">{value}</span>
    </div>
  );
}
