import React, { useEffect, useState, useMemo } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { api, apiCall } from "../lib/api";
import { useAuth } from "../lib/auth";
import Layout from "../components/Layout";
import {
  ArrowLeft,
  CheckCircle,
  XCircle,
  Warning,
  Sparkle,
  TrendUp,
  CurrencyEur,
  Target,
  Package,
  Rocket,
  Globe,
  Lightning,
} from "@phosphor-icons/react";

const COUNTRY_META = {
  FR: { flag: "🇫🇷", name: "France" },
  DE: { flag: "🇩🇪", name: "Allemagne" },
  CH: { flag: "🇨🇭", name: "Suisse" },
  BE: { flag: "🇧🇪", name: "Belgique+Lux" },
  UK: { flag: "🇬🇧", name: "Royaume-Uni" },
  NL: { flag: "🇳🇱", name: "Pays-Bas" },
};

const VERDICT_META = {
  GO:    { label: "GO",        bg: "#DCF5E7", text: "#166534", Icon: CheckCircle },
  MAYBE: { label: "À creuser", bg: "#FEF3C7", text: "#854D0E", Icon: Warning },
  NOGO:  { label: "Pass",      bg: "#FFE4E6", text: "#9F1239", Icon: XCircle },
};

const BUDGET_PER_COUNTRY = 30;

export default function NicheAnalysisDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [doc, setDoc] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState(new Set());
  const [launching, setLaunching] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    (async () => {
      const { data } = await apiCall(() => api.get(`/niches/analyses/${id}`));
      setDoc(data);
      // Pre-select GO countries by default
      if (data?.analysis?.go_countries?.length) {
        setSelected(new Set(data.analysis.go_countries));
      }
      setLoading(false);
    })();
  }, [id]);

  const a = doc?.analysis;

  const totalBudget = useMemo(
    () => selected.size * (doc?.budget_per_country_eur || BUDGET_PER_COUNTRY),
    [selected, doc]
  );

  const totalVolumeSelected = useMemo(() => {
    if (!a) return 0;
    return Array.from(selected).reduce(
      (sum, c) => sum + (a.country_metrics?.[c]?.volume || 0),
      0
    );
  }, [selected, a]);

  const toggle = (code) => {
    const next = new Set(selected);
    next.has(code) ? next.delete(code) : next.add(code);
    setSelected(next);
  };

  const launchSite = async () => {
    if (!a || selected.size === 0) return;
    setLaunching(true);
    setError("");
    const payload = {
      name: `${a.name} — Silver`,
      niche: a.name,
      niche_slug: a.slug,
      analysis_id: doc.id,
      selected_countries: Array.from(selected),
      daily_budget_eur: totalBudget,
      notes: a.verdict_reasoning || "",
    };
    const { data, error: err } = await apiCall(() => api.post("/sites", payload));
    setLaunching(false);
    if (err) {
      setError(err);
      return;
    }
    navigate(`/sites/${data.id}`);
  };

  if (loading) {
    return (
      <Layout>
        <div className="p-8 text-[#78716C]">Chargement de l'analyse…</div>
      </Layout>
    );
  }
  if (!a) {
    return (
      <Layout>
        <div className="p-8 max-w-2xl">
          <div className="text-[#9F1239]">Analyse introuvable.</div>
          <button onClick={() => navigate("/niches")} className="mt-4 text-[#B84B31] hover:underline">
            ← Nouvelle analyse
          </button>
        </div>
      </Layout>
    );
  }

  const v = VERDICT_META[a.overall_verdict] || VERDICT_META.MAYBE;
  const countries = ["FR", "DE", "CH", "BE", "UK", "NL"];
  const canLaunch = !!user; // admin OR operator — both can now create sites from analysis

  return (
    <Layout>
      <div className="p-6 md:p-12 max-w-6xl mx-auto">
        <button
          onClick={() => navigate("/niches")}
          className="flex items-center gap-2 text-sm text-[#78716C] hover:text-[#1C1917] mb-6 transition"
          data-testid="back-to-niches"
        >
          <ArrowLeft size={16} /> Nouvelle analyse
        </button>

        {/* Hero summary */}
        <div className="flex items-start gap-6 mb-8 animate-fade-up">
          <div className="text-5xl md:text-6xl">{a.emoji || "📦"}</div>
          <div className="flex-1 min-w-0">
            <div className="text-[11px] uppercase tracking-widest text-[#78716C] mb-2 flex items-center gap-2">
              <Sparkle size={11} weight="fill" className="text-[#B84B31]" />
              Analyse IA · {a.category}
            </div>
            <h1 className="font-heading text-3xl md:text-4xl font-semibold text-[#1C1917]">
              {a.name}
            </h1>
            {a.tagline && (
              <p className="text-[#57534E] mt-2 text-lg italic">« {a.tagline} »</p>
            )}
          </div>

          <div
            className="hidden md:flex flex-col items-end p-5 rounded-2xl border"
            style={{ backgroundColor: v.bg, borderColor: v.text + "33" }}
            data-testid="verdict-badge"
          >
            <div className="flex items-center gap-1.5 text-[11px] uppercase tracking-widest" style={{ color: v.text }}>
              <v.Icon size={12} weight="fill" /> Verdict
            </div>
            <div className="font-heading text-3xl font-semibold mt-1" style={{ color: v.text }}>
              {v.label}
            </div>
          </div>
        </div>

        {/* Description + verdict reasoning */}
        <div className="bg-white rounded-2xl border border-[#E7E5E4] p-6 mb-6">
          <p className="text-[#1C1917] leading-relaxed">{a.description}</p>
          {a.verdict_reasoning && (
            <div className="mt-4 pt-4 border-t border-[#F5F2EB] flex items-start gap-2 text-sm text-[#57534E]">
              <Lightning size={16} weight="fill" className="text-[#B84B31] mt-0.5 flex-shrink-0" />
              <span>{a.verdict_reasoning}</span>
            </div>
          )}
        </div>

        {/* KPIs */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-8">
          <Kpi icon={<TrendUp size={14} />} label="Vol total/mois" value={(a.total_volume_monthly || 0).toLocaleString("fr-FR")} />
          <Kpi icon={<CurrencyEur size={14} />} label="CPC moyen" value={`${a.avg_cpc_eur}€`} />
          <Kpi icon={<Target size={14} />} label="ECF Score" value={`${a.ecf_score}/100`} />
          <Kpi icon={<Sparkle size={14} />} label="Marge" value={`${a.margin_pct}%`} />
          <Kpi icon={<Package size={14} />} label="Panier" value={`${a.aov_eur?.[0]}-${a.aov_eur?.[1]}€`} />
        </div>

        {/* Synthèse par marché + sélection */}
        <div className="mb-8">
          <div className="flex items-end justify-between mb-4">
            <div>
              <h2 className="font-heading text-2xl font-semibold text-[#1C1917] flex items-center gap-2">
                <Globe size={22} /> Synthèse par marché
              </h2>
              <p className="text-sm text-[#57534E] mt-1">
                Coche les marchés que tu veux lancer · {BUDGET_PER_COUNTRY}€/jour de pub par marché
              </p>
            </div>
            <div className="text-xs text-[#78716C]">{selected.size} marché(s) sélectionné(s)</div>
          </div>

          <div className="space-y-3" data-testid="countries-list">
            {countries.map((code) => {
              const m = a.country_metrics?.[code] || {};
              const synth = a.synthesis_per_country?.[code] || "";
              const cv = VERDICT_META[m.verdict] || VERDICT_META.MAYBE;
              const isSel = selected.has(code);
              const isLeader = code === a.best_country;
              return (
                <div
                  key={code}
                  className={`rounded-2xl border-2 p-5 transition-all duration-200 ${
                    isSel ? "border-[#B84B31] bg-[#FDF4E7]" : "border-[#E7E5E4] bg-white hover:border-[#B84B31]/30"
                  }`}
                  data-testid={`country-row-${code}`}
                >
                  <div className="flex items-start gap-4">
                    <button
                      onClick={() => toggle(code)}
                      data-testid={`toggle-${code}`}
                      className={`flex-shrink-0 w-6 h-6 rounded-md border-2 flex items-center justify-center transition ${
                        isSel
                          ? "bg-[#B84B31] border-[#B84B31] text-white"
                          : "border-[#D6D3D1] bg-white hover:border-[#B84B31]"
                      }`}
                    >
                      {isSel && <CheckCircle size={16} weight="fill" />}
                    </button>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-xl">{COUNTRY_META[code]?.flag}</span>
                        <span className="font-heading text-lg font-semibold text-[#1C1917]">
                          {COUNTRY_META[code]?.name}
                        </span>
                        {isLeader && (
                          <span className="text-[10px] uppercase tracking-wider text-[#B84B31] font-semibold">
                            ★ LEADER
                          </span>
                        )}
                        <span
                          className="ml-auto flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium"
                          style={{ backgroundColor: cv.bg, color: cv.text }}
                        >
                          <cv.Icon size={10} weight="fill" /> {cv.label}
                        </span>
                      </div>

                      <p className="text-sm text-[#57534E] mt-2 leading-relaxed">{synth}</p>

                      <div className="grid grid-cols-2 md:grid-cols-5 gap-x-6 gap-y-1.5 mt-3 pt-3 border-t border-[#F5F2EB]">
                        <MiniStat label="Volume" value={`${(m.volume || 0).toLocaleString("fr-FR")}/mois`} />
                        <MiniStat label="CPC" value={`${(m.cpc || 0).toFixed(2)}€`} />
                        <MiniStat label="KD" value={m.kd || "—"} />
                        <MiniStat label="CPA cible" value={`${m.cpa_target || 0}€`} />
                        <MiniStat label="Saison" value={m.seasonality || "—"} />
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Risks + opportunities */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
          {a.risks?.length > 0 && (
            <div className="bg-white rounded-2xl border border-[#E7E5E4] p-5">
              <div className="text-[11px] uppercase tracking-widest text-[#9F1239] mb-3 flex items-center gap-1.5">
                <Warning size={11} weight="fill" /> Risques identifiés
              </div>
              <ul className="space-y-2">
                {a.risks.map((r, i) => (
                  <li key={i} className="text-sm text-[#57534E] flex gap-2">
                    <span className="text-[#9F1239] mt-0.5">•</span> {r}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {a.opportunities?.length > 0 && (
            <div className="bg-white rounded-2xl border border-[#E7E5E4] p-5">
              <div className="text-[11px] uppercase tracking-widest text-[#166534] mb-3 flex items-center gap-1.5">
                <CheckCircle size={11} weight="fill" /> Opportunités
              </div>
              <ul className="space-y-2">
                {a.opportunities.map((r, i) => (
                  <li key={i} className="text-sm text-[#57534E] flex gap-2">
                    <span className="text-[#166534] mt-0.5">•</span> {r}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* Suppliers + keywords */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-24">
          <div className="bg-white rounded-2xl border border-[#E7E5E4] p-5">
            <div className="text-[11px] uppercase tracking-widest text-[#78716C] mb-3">Mots-clés</div>
            <div className="flex flex-wrap gap-2">
              {(a.keywords || []).map((k) => (
                <span key={k} className="px-2.5 py-1 rounded-full text-xs bg-[#FDFBF7] border border-[#E7E5E4] text-[#57534E]">
                  {k}
                </span>
              ))}
            </div>
          </div>
          <div className="bg-white rounded-2xl border border-[#E7E5E4] p-5">
            <div className="text-[11px] uppercase tracking-widest text-[#78716C] mb-3">Fournisseurs</div>
            <ul className="space-y-1.5">
              {(a.suppliers || []).map((s) => (
                <li key={s} className="text-sm text-[#57534E] flex gap-2">
                  <span className="text-[#B84B31]">•</span> {s}
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Sticky launch bar */}
        {canLaunch && (
          <div className="fixed bottom-0 left-0 md:left-[260px] right-0 bg-white border-t border-[#E7E5E4] shadow-[0_-4px_24px_rgba(0,0,0,0.06)] z-20" data-testid="launch-bar">
            <div className="max-w-6xl mx-auto px-4 md:px-6 py-3 md:py-4 flex items-center justify-between gap-3 flex-wrap">
              <div className="flex items-center gap-3 md:gap-6 flex-wrap">
                <div>
                  <div className="text-[10px] uppercase tracking-widest text-[#78716C]">Marchés</div>
                  <div className="font-heading text-xl font-semibold text-[#1C1917]">
                    {selected.size === 0 ? "Aucun" : Array.from(selected).join(" · ")}
                  </div>
                </div>
                <div className="h-10 w-px bg-[#E7E5E4]" />
                <div>
                  <div className="text-[10px] uppercase tracking-widest text-[#78716C]">Budget pub</div>
                  <div className="font-heading text-xl font-semibold text-[#1C1917] tabular-nums">
                    {totalBudget}€<span className="text-sm font-normal text-[#78716C]"> / jour</span>
                  </div>
                </div>
                <div className="h-10 w-px bg-[#E7E5E4] hidden md:block" />
                <div className="hidden md:block">
                  <div className="text-[10px] uppercase tracking-widest text-[#78716C]">Vol cumulé</div>
                  <div className="font-heading text-xl font-semibold text-[#1C1917] tabular-nums">
                    {totalVolumeSelected.toLocaleString("fr-FR")}<span className="text-sm font-normal text-[#78716C]"> /mois</span>
                  </div>
                </div>
              </div>
              {error && <div className="text-sm text-[#BE123C]">{error}</div>}
              <button
                onClick={launchSite}
                disabled={selected.size === 0 || launching}
                data-testid="launch-site-btn"
                className="h-12 px-6 rounded-xl bg-[#B84B31] hover:bg-[#993D26] text-white font-medium flex items-center gap-2 transition active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Rocket size={18} weight="fill" /> {launching ? "Création..." : `Lancer sur ${selected.size} marché${selected.size > 1 ? "s" : ""}`}
              </button>
            </div>
          </div>
        )}
      </div>
    </Layout>
  );
}

function Kpi({ icon, label, value }) {
  return (
    <div className="bg-white rounded-xl border border-[#E7E5E4] p-3.5">
      <div className="flex items-center gap-1 text-[10px] uppercase tracking-widest text-[#78716C]">
        {icon}{label}
      </div>
      <div className="font-heading text-lg font-semibold text-[#1C1917] mt-1 tabular-nums">
        {value}
      </div>
    </div>
  );
}

function MiniStat({ label, value }) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-wider text-[#78716C]">{label}</div>
      <div className="text-sm font-medium text-[#1C1917] tabular-nums mt-0.5">{value}</div>
    </div>
  );
}
