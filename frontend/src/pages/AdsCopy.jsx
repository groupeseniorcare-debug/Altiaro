import React, { useEffect, useState, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { api, apiCall } from "../lib/api";
import Layout from "../components/Layout";
import {
  ArrowLeft,
  Sparkle,
  Copy,
  CheckCircle,
  DownloadSimple,
  Trash,
  Megaphone,
  ArrowClockwise,
  Warning,
} from "@phosphor-icons/react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const COUNTRIES = [
  { code: "FR", name: "France", flag: "🇫🇷", lang: "fr" },
  { code: "DE", name: "Allemagne", flag: "🇩🇪", lang: "de" },
  { code: "CH", name: "Suisse", flag: "🇨🇭", lang: "fr" },
  { code: "BE", name: "Belgique", flag: "🇧🇪", lang: "fr" },
  { code: "UK", name: "Royaume-Uni", flag: "🇬🇧", lang: "en" },
  { code: "NL", name: "Pays-Bas", flag: "🇳🇱", lang: "nl" },
];

const LANGS = [
  { code: "fr", label: "Français" },
  { code: "en", label: "English" },
  { code: "de", label: "Deutsch" },
  { code: "nl", label: "Nederlands" },
];

const TONES = [
  { code: "rassurant", label: "Rassurant (senior-friendly)" },
  { code: "premium", label: "Premium (haut de gamme)" },
  { code: "direct", label: "Direct (promo / urgence)" },
];

const HEADLINE_MAX = 30;
const DESCRIPTION_MAX = 90;

function CharBar({ value, max }) {
  const pct = Math.min(100, (value / max) * 100);
  const ok = value <= max;
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1 rounded-full bg-[#F5F2EB] overflow-hidden">
        <div
          className="h-full transition-all duration-300"
          style={{
            width: `${pct}%`,
            background: ok ? (pct > 85 ? "#D97706" : "#047857") : "#BE123C",
          }}
        />
      </div>
      <span
        className={`text-[10px] font-mono tabular-nums ${
          ok ? (pct > 85 ? "text-[#D97706]" : "text-[#57534E]") : "text-[#BE123C] font-bold"
        }`}
      >
        {value}/{max}
      </span>
    </div>
  );
}

function CopyPill({ text, children, testid }) {
  const [copied, setCopied] = useState(false);
  const onCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1200);
    } catch {}
  };
  return (
    <button
      type="button"
      onClick={onCopy}
      data-testid={testid}
      className="inline-flex items-center gap-1.5 text-[11px] text-[#78716C] hover:text-[#B84B31] transition"
    >
      {copied ? (
        <>
          <CheckCircle size={12} weight="fill" /> Copié
        </>
      ) : (
        <>
          <Copy size={12} /> {children || "Copier"}
        </>
      )}
    </button>
  );
}

export default function AdsCopy() {
  const { id: siteId } = useParams();
  const navigate = useNavigate();
  const [site, setSite] = useState(null);
  const [campaigns, setCampaigns] = useState([]);
  const [selected, setSelected] = useState(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState("");

  const defaultCountry =
    site?.selected_countries?.[0] || "FR";

  const [form, setForm] = useState({
    country: "FR",
    language: "fr",
    tone: "rassurant",
    product_focus: "",
  });

  const load = useCallback(async () => {
    const [sRes, cRes] = await Promise.all([
      apiCall(() => api.get(`/sites/${siteId}`)),
      apiCall(() => api.get(`/sites/${siteId}/ads-copy`)),
    ]);
    if (sRes.data) {
      setSite(sRes.data);
      const firstCountry = sRes.data.selected_countries?.[0];
      if (firstCountry && !form.country) {
        const c = COUNTRIES.find((x) => x.code === firstCountry);
        if (c) setForm((f) => ({ ...f, country: c.code, language: c.lang }));
      }
    }
    if (cRes.data) {
      setCampaigns(cRes.data);
      if (!selected && cRes.data[0]) setSelected(cRes.data[0]);
    }
    setLoading(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [siteId]);

  useEffect(() => {
    load();
  }, [load]);

  const handleCountryChange = (code) => {
    const c = COUNTRIES.find((x) => x.code === code);
    setForm((f) => ({ ...f, country: code, language: c?.lang || f.language }));
  };

  const handleGenerate = async () => {
    setGenerating(true);
    setError("");
    const { data, error: err } = await apiCall(() =>
      api.post(`/sites/${siteId}/ads-copy/generate`, form)
    );
    setGenerating(false);
    if (err) {
      setError(err);
      return;
    }
    setCampaigns((prev) => [data, ...prev]);
    setSelected(data);
  };

  const handleDelete = async (c) => {
    if (!window.confirm(`Supprimer la campagne ${c.country} · ${c.language.toUpperCase()} ?`)) return;
    await apiCall(() => api.delete(`/sites/${siteId}/ads-copy/${c.id}`));
    setCampaigns((prev) => prev.filter((x) => x.id !== c.id));
    if (selected?.id === c.id) setSelected(null);
  };

  const handleExportCsv = (c) => {
    window.open(
      `${BACKEND_URL}/api/sites/${siteId}/ads-copy/${c.id}/export.csv`,
      "_blank"
    );
  };

  const handleCopyAll = async () => {
    if (!selected) return;
    const d = selected.data;
    const text = [
      "=== HEADLINES ===",
      ...d.headlines.map((h, i) => `${i + 1}. ${h} (${h.length})`),
      "",
      "=== DESCRIPTIONS ===",
      ...d.descriptions.map((x, i) => `${i + 1}. ${x} (${x.length})`),
      "",
      "=== KEYWORDS ===",
      ...d.keywords,
      "",
      "=== NEGATIVE KEYWORDS ===",
      ...d.negative_keywords,
      "",
      "=== SITELINKS ===",
      ...d.sitelinks.map((s) => `${s.title} | ${s.desc1} | ${s.desc2}`),
      "",
      "=== CALLOUTS ===",
      ...d.callouts,
    ].join("\n");
    try {
      await navigator.clipboard.writeText(text);
    } catch {}
  };

  if (loading) {
    return (
      <Layout>
        <div className="p-8 text-[#78716C]">Chargement…</div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="p-6 md:p-12 max-w-[1400px]">
        <button
          onClick={() => navigate(`/sites/${siteId}`)}
          className="flex items-center gap-2 text-sm text-[#78716C] hover:text-[#1C1917] mb-6 transition"
          data-testid="back-to-site"
        >
          <ArrowLeft size={16} /> Retour au site
        </button>

        <div className="flex items-start justify-between gap-8 mb-10 animate-fade-up flex-wrap">
          <div>
            <div className="text-[11px] uppercase tracking-widest text-[#78716C] mb-2">
              {site?.name} · Google Ads
            </div>
            <h1 className="font-heading text-4xl font-semibold text-[#1C1917]">
              Générateur Ads Copy
            </h1>
            <p className="text-[#57534E] mt-2 max-w-2xl">
              Génère instantanément les 15 titres, 4 descriptions, 25 mots-clés et
              extensions d'annonce pour une Responsive Search Ad. Propulsé par Claude 4.5.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-[340px_1fr] gap-6">
          {/* Left : Form + history */}
          <aside className="space-y-5">
            <div className="bg-white rounded-2xl border border-[#E7E5E4] p-5">
              <div className="flex items-center gap-2 mb-4">
                <Sparkle size={16} weight="fill" className="text-[#B84B31]" />
                <h2 className="font-heading text-lg font-semibold">Nouvelle campagne</h2>
              </div>

              <label className="block text-xs font-medium text-[#57534E] mb-1.5">Pays cible</label>
              <div className="grid grid-cols-3 gap-1.5 mb-4">
                {COUNTRIES.map((c) => {
                  const active = form.country === c.code;
                  const eligible = !site?.selected_countries?.length || site.selected_countries.includes(c.code);
                  return (
                    <button
                      key={c.code}
                      type="button"
                      onClick={() => handleCountryChange(c.code)}
                      disabled={!eligible}
                      data-testid={`country-${c.code}`}
                      className={`h-12 rounded-lg border text-sm flex flex-col items-center justify-center gap-0.5 transition ${
                        active
                          ? "bg-[#1C1917] text-neutral-900 border-[#1C1917]"
                          : eligible
                          ? "bg-white border-[#E7E5E4] hover:border-[#B84B31] text-[#1C1917]"
                          : "bg-[#FAF7F2] border-[#F5F2EB] text-[#A8A29E] cursor-not-allowed"
                      }`}
                      title={!eligible ? "Pas sélectionné pour ce site" : c.name}
                    >
                      <span className="text-base">{c.flag}</span>
                      <span className="text-[10px] font-mono">{c.code}</span>
                    </button>
                  );
                })}
              </div>

              <label className="block text-xs font-medium text-[#57534E] mb-1.5">Langue</label>
              <select
                value={form.language}
                onChange={(e) => setForm((f) => ({ ...f, language: e.target.value }))}
                data-testid="lang-select"
                className="w-full h-10 px-3 rounded-lg border border-[#E7E5E4] bg-white text-sm mb-4"
              >
                {LANGS.map((l) => (
                  <option key={l.code} value={l.code}>
                    {l.label}
                  </option>
                ))}
              </select>

              <label className="block text-xs font-medium text-[#57534E] mb-1.5">Ton</label>
              <select
                value={form.tone}
                onChange={(e) => setForm((f) => ({ ...f, tone: e.target.value }))}
                data-testid="tone-select"
                className="w-full h-10 px-3 rounded-lg border border-[#E7E5E4] bg-white text-sm mb-4"
              >
                {TONES.map((t) => (
                  <option key={t.code} value={t.code}>
                    {t.label}
                  </option>
                ))}
              </select>

              <label className="block text-xs font-medium text-[#57534E] mb-1.5">
                Focus produit (optionnel)
              </label>
              <input
                type="text"
                value={form.product_focus}
                onChange={(e) => setForm((f) => ({ ...f, product_focus: e.target.value }))}
                placeholder="ex: fauteuil releveur électrique 2 moteurs"
                data-testid="product-focus"
                className="w-full h-10 px-3 rounded-lg border border-[#E7E5E4] bg-white text-sm mb-4"
              />

              {error && (
                <div className="mb-3 p-2.5 rounded-lg bg-[#FFE4E6] text-[#BE123C] text-xs flex gap-2">
                  <Warning size={14} weight="fill" className="shrink-0 mt-0.5" />
                  {error}
                </div>
              )}

              <button
                type="button"
                onClick={handleGenerate}
                disabled={generating}
                data-testid="generate-ads"
                className="w-full h-11 rounded-xl bg-[#B84B31] hover:bg-[#993D26] disabled:opacity-60 text-neutral-900 text-sm font-medium flex items-center justify-center gap-2 transition active:scale-[0.98]"
              >
                {generating ? (
                  <>
                    <ArrowClockwise size={16} className="animate-spin" /> Génération en cours…
                  </>
                ) : (
                  <>
                    <Sparkle size={16} weight="fill" /> Générer la campagne
                  </>
                )}
              </button>
              <p className="text-[11px] text-[#78716C] mt-2 text-center">
                Claude Sonnet 4.5 · ~20s · respecte les 30/90 chars Google
              </p>
            </div>

            {/* History */}
            <div className="bg-white rounded-2xl border border-[#E7E5E4] p-5">
              <div className="flex items-center gap-2 mb-3">
                <Megaphone size={16} weight="duotone" className="text-[#57534E]" />
                <h2 className="font-heading text-sm font-semibold">
                  Historique ({campaigns.length})
                </h2>
              </div>
              {campaigns.length === 0 ? (
                <p className="text-xs text-[#78716C]">Aucune campagne encore générée.</p>
              ) : (
                <div className="space-y-1.5 max-h-[400px] overflow-y-auto">
                  {campaigns.map((c) => {
                    const flag = COUNTRIES.find((x) => x.code === c.country)?.flag || "🌍";
                    const active = selected?.id === c.id;
                    return (
                      <button
                        key={c.id}
                        type="button"
                        onClick={() => setSelected(c)}
                        data-testid={`campaign-${c.id}`}
                        className={`w-full text-left p-2.5 rounded-lg border text-sm flex items-center gap-2 transition ${
                          active
                            ? "bg-[#FAF7F2] border-[#B84B31]"
                            : "bg-white border-[#F5F2EB] hover:border-[#E7E5E4]"
                        }`}
                      >
                        <span className="text-lg">{flag}</span>
                        <div className="flex-1 min-w-0">
                          <div className="text-xs font-medium text-[#1C1917] truncate">
                            {c.country_name} · {c.language.toUpperCase()}
                          </div>
                          <div className="text-[10px] text-[#78716C] font-mono">
                            {new Date(c.created_at).toLocaleDateString()} · {c.tone}
                          </div>
                        </div>
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          </aside>

          {/* Right : Selected campaign display */}
          <main>
            {!selected ? (
              <div className="bg-white rounded-2xl border border-dashed border-[#E7E5E4] p-16 text-center">
                <Megaphone size={48} weight="duotone" className="mx-auto text-[#D6D3D1] mb-4" />
                <h3 className="font-heading text-xl font-semibold text-[#1C1917] mb-2">
                  Aucune campagne sélectionnée
                </h3>
                <p className="text-sm text-[#78716C] max-w-sm mx-auto">
                  Sélectionne un pays + une langue et clique "Générer la campagne" pour obtenir
                  ta première Responsive Search Ad.
                </p>
              </div>
            ) : (
              <CampaignDetail
                campaign={selected}
                onCopyAll={handleCopyAll}
                onExport={() => handleExportCsv(selected)}
                onDelete={() => handleDelete(selected)}
              />
            )}
          </main>
        </div>
      </div>
    </Layout>
  );
}

function CampaignDetail({ campaign, onCopyAll, onExport, onDelete }) {
  const d = campaign.data;
  const flag = COUNTRIES.find((x) => x.code === campaign.country)?.flag || "🌍";

  return (
    <div className="space-y-5 animate-fade-up" data-testid="campaign-detail">
      {/* Header */}
      <div className="bg-white rounded-2xl border border-[#E7E5E4] p-5 flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-3">
          <span className="text-3xl">{flag}</span>
          <div>
            <div className="font-heading text-xl font-semibold text-[#1C1917]">
              {campaign.country_name} · {campaign.language.toUpperCase()}
            </div>
            <div className="text-xs text-[#78716C]">
              Ton : {campaign.tone} · Généré le{" "}
              {new Date(campaign.created_at).toLocaleDateString()}
            </div>
          </div>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={onCopyAll}
            data-testid="copy-all"
            className="h-10 px-4 rounded-xl bg-white border border-[#E7E5E4] hover:border-[#B84B31] text-sm font-medium flex items-center gap-2 transition"
          >
            <Copy size={14} /> Tout copier
          </button>
          <button
            type="button"
            onClick={onExport}
            data-testid="export-csv"
            className="h-10 px-4 rounded-xl bg-[#1C1917] hover:bg-[#44403C] text-neutral-900 text-sm font-medium flex items-center gap-2 transition"
          >
            <DownloadSimple size={14} /> CSV Google Ads
          </button>
          <button
            type="button"
            onClick={onDelete}
            data-testid="delete-campaign"
            className="h-10 w-10 rounded-xl bg-white border border-[#E7E5E4] hover:border-[#BE123C] hover:text-[#BE123C] flex items-center justify-center transition"
            title="Supprimer"
          >
            <Trash size={14} />
          </button>
        </div>
      </div>

      {d.notes && (
        <div className="bg-[#FAF7F2] rounded-xl border border-[#E7E5E4] p-4 text-sm text-[#57534E]">
          <strong className="text-[#1C1917]">Angle :</strong> {d.notes}
        </div>
      )}

      {/* Headlines */}
      <Section title={`Headlines (${d.headlines.length}/15)`} testid="section-headlines">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
          {d.headlines.map((h, i) => (
            <div
              key={i}
              data-testid={`headline-${i}`}
              className="group bg-white rounded-lg border border-[#E7E5E4] p-3 hover:border-[#B84B31]/50 transition"
            >
              <div className="flex items-start justify-between gap-2 mb-1.5">
                <span className="text-xs text-[#78716C] font-mono">H{i + 1}</span>
                <CopyPill text={h} testid={`copy-headline-${i}`} />
              </div>
              <div
                className={`text-sm font-medium ${
                  h.length > HEADLINE_MAX ? "text-[#BE123C]" : "text-[#1C1917]"
                }`}
              >
                {h}
              </div>
              <div className="mt-1.5">
                <CharBar value={h.length} max={HEADLINE_MAX} />
              </div>
            </div>
          ))}
        </div>
      </Section>

      {/* Descriptions */}
      <Section title={`Descriptions (${d.descriptions.length}/4)`} testid="section-descriptions">
        <div className="space-y-2">
          {d.descriptions.map((x, i) => (
            <div
              key={i}
              data-testid={`description-${i}`}
              className="bg-white rounded-lg border border-[#E7E5E4] p-3 hover:border-[#B84B31]/50 transition"
            >
              <div className="flex items-start justify-between gap-2 mb-1.5">
                <span className="text-xs text-[#78716C] font-mono">D{i + 1}</span>
                <CopyPill text={x} testid={`copy-description-${i}`} />
              </div>
              <div
                className={`text-sm ${
                  x.length > DESCRIPTION_MAX ? "text-[#BE123C]" : "text-[#1C1917]"
                }`}
              >
                {x}
              </div>
              <div className="mt-1.5">
                <CharBar value={x.length} max={DESCRIPTION_MAX} />
              </div>
            </div>
          ))}
        </div>
      </Section>

      {/* Keywords */}
      <Section title={`Mots-clés (${d.keywords.length})`} testid="section-keywords">
        <div className="flex flex-wrap gap-1.5">
          {d.keywords.map((k, i) => (
            <span
              key={i}
              data-testid={`keyword-${i}`}
              className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-[#F5F2EB] text-[#57534E] text-xs font-mono"
            >
              {k}
              <CopyPill text={k} testid={`copy-keyword-${i}`}>
                {""}
              </CopyPill>
            </span>
          ))}
        </div>
      </Section>

      {/* Negative Keywords */}
      <Section
        title={`Mots-clés négatifs (${d.negative_keywords.length})`}
        testid="section-negative-keywords"
      >
        <div className="flex flex-wrap gap-1.5">
          {d.negative_keywords.map((k, i) => (
            <span
              key={i}
              data-testid={`negkeyword-${i}`}
              className="inline-flex items-center px-2.5 py-1 rounded-full bg-[#FFE4E6] text-[#BE123C] text-xs font-mono line-through"
            >
              -{k}
            </span>
          ))}
        </div>
      </Section>

      {/* Sitelinks */}
      <Section title={`Sitelinks (${d.sitelinks.length})`} testid="section-sitelinks">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
          {d.sitelinks.map((s, i) => (
            <div
              key={i}
              data-testid={`sitelink-${i}`}
              className="bg-white rounded-lg border border-[#E7E5E4] p-3"
            >
              <div className="flex items-start justify-between mb-1">
                <span className="text-xs text-[#78716C] font-mono">SL{i + 1}</span>
                <CopyPill
                  text={`${s.title} — ${s.desc1} — ${s.desc2}`}
                  testid={`copy-sitelink-${i}`}
                />
              </div>
              <div className="text-sm font-semibold text-[#B84B31]">{s.title}</div>
              <div className="text-xs text-[#57534E] mt-0.5">{s.desc1}</div>
              <div className="text-xs text-[#57534E]">{s.desc2}</div>
              {s.url_suffix && (
                <div className="text-[10px] text-[#78716C] font-mono mt-1">→ {s.url_suffix}</div>
              )}
            </div>
          ))}
        </div>
      </Section>

      {/* Callouts */}
      <Section title={`Callouts (${d.callouts.length})`} testid="section-callouts">
        <div className="flex flex-wrap gap-1.5">
          {d.callouts.map((c, i) => (
            <span
              key={i}
              data-testid={`callout-${i}`}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-[#D1FAE5] text-[#047857] text-xs font-medium"
            >
              ✓ {c}
            </span>
          ))}
        </div>
      </Section>
    </div>
  );
}

function Section({ title, testid, children }) {
  return (
    <section className="bg-white rounded-2xl border border-[#E7E5E4] p-5" data-testid={testid}>
      <h3 className="font-heading text-sm font-semibold text-[#1C1917] mb-3 uppercase tracking-wider">
        {title}
      </h3>
      {children}
    </section>
  );
}
