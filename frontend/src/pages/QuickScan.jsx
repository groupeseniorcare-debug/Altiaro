import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, apiCall } from "../lib/api";
import Layout from "../components/Layout";
import {
  Lightning,
  CheckCircle,
  XCircle,
  Warning,
  ArrowClockwise,
  ArrowRight,
  Sparkle,
  Storefront,
  MagnifyingGlass,
  TrendUp,
  TrendDown,
  ArrowsLeftRight,
  Info,
} from "@phosphor-icons/react";

const COUNTRIES = [
  { code: "FR", label: "France 🇫🇷" },
  { code: "DE", label: "Allemagne 🇩🇪" },
  { code: "BE", label: "Belgique 🇧🇪" },
  { code: "NL", label: "Pays-Bas 🇳🇱" },
  { code: "UK", label: "Royaume-Uni 🇬🇧" },
  { code: "CH", label: "Suisse 🇨🇭" },
  { code: "ES", label: "Espagne 🇪🇸" },
  { code: "IT", label: "Italie 🇮🇹" },
];

const VERDICT_META = {
  GO: {
    label: "GO",
    fullLabel: "Lance-toi",
    color: "#047857",
    bg: "#D1FAE5",
    borderColor: "#A7F3D0",
    icon: CheckCircle,
    emoji: "✅",
  },
  GO_WITH_RESERVE: {
    label: "GO avec réserve",
    fullLabel: "Teste avec prudence",
    color: "#B45309",
    bg: "#FEF3C7",
    borderColor: "#FDE68A",
    icon: Warning,
    emoji: "🟡",
  },
  NO_GO: {
    label: "NO-GO",
    fullLabel: "Cherche une autre niche",
    color: "#BE123C",
    bg: "#FFE4E6",
    borderColor: "#FECDD3",
    icon: XCircle,
    emoji: "❌",
  },
};

const TREND_META = {
  growing: { icon: TrendUp, label: "En croissance", color: "#047857" },
  stable: { icon: ArrowsLeftRight, label: "Stable", color: "#78716C" },
  declining: { icon: TrendDown, label: "En déclin", color: "#BE123C" },
};

export default function QuickScan() {
  const navigate = useNavigate();
  const [product, setProduct] = useState("");
  const [country, setCountry] = useState("FR");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);
  const [history, setHistory] = useState([]);
  const [step, setStep] = useState(0); // 0 idle, 1 claude, 2 google, 3 verdict

  useEffect(() => {
    apiCall(() => api.get("/quick-scan/history?limit=10")).then(({ data }) => {
      if (data) setHistory(data.scans || []);
    });
  }, []);

  const run = async () => {
    if (!product.trim() || product.trim().length < 3) return;
    setLoading(true);
    setError(null);
    setResult(null);
    setStep(1);
    // Fake-progress the steps
    const t1 = setTimeout(() => setStep(2), 4000);
    const t2 = setTimeout(() => setStep(3), 10000);
    const { data, error: err } = await apiCall(() =>
      api.post("/quick-scan", { product_or_niche: product.trim(), country })
    );
    clearTimeout(t1);
    clearTimeout(t2);
    setStep(0);
    setLoading(false);
    if (err) {
      setError(err);
      return;
    }
    setResult(data);
    // Refresh history
    apiCall(() => api.get("/quick-scan/history?limit=10")).then(({ data: h }) => {
      if (h) setHistory(h.scans || []);
    });
  };

  return (
    <Layout>
      <div className="p-8 md:p-12 max-w-[1100px]">
        {/* Header */}
        <div className="flex items-start gap-3 mb-8">
          <div className="w-11 h-11 rounded-lg bg-gradient-to-br from-[#F59E0B] to-[#EA580C] flex items-center justify-center">
            <Lightning size={22} weight="fill" color="#fff" />
          </div>
          <div>
            <div className="text-[11px] uppercase tracking-widest text-[#78716C] mb-1">
              Scan Express · Go / No-Go
            </div>
            <h1 className="font-heading text-4xl font-semibold text-[#1C1917]">
              Ce produit vaut-il la peine d'être lancé ?
            </h1>
            <p className="text-[#57534E] mt-1">
              Scan en 30s : volumes Google, prix concurrents, concurrence et rentabilité Ads →
              verdict clair.
            </p>
          </div>
        </div>

        {/* Input form */}
        <div className="bg-white rounded-2xl border border-[#E7E5E4] p-6 mb-6">
          <label className="block text-xs font-semibold text-[#57534E] mb-1.5 uppercase tracking-wider">
            Produit ou niche à tester
          </label>
          <div className="flex flex-col md:flex-row gap-3">
            <div className="flex-1 relative">
              <MagnifyingGlass
                size={18}
                className="absolute left-4 top-1/2 -translate-y-1/2 text-[#78716C]"
              />
              <input
                type="text"
                value={product}
                onChange={(e) => setProduct(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && !loading && run()}
                placeholder="ex: fauteuil releveur électrique, chaussons ergonomiques seniors…"
                data-testid="qs-input"
                disabled={loading}
                className="w-full h-14 pl-11 pr-4 rounded-xl border border-[#E7E5E4] bg-white text-[15px] focus:outline-none focus:border-[#EA580C] focus:ring-2 focus:ring-[#EA580C]/20 disabled:opacity-60"
              />
            </div>
            <select
              value={country}
              onChange={(e) => setCountry(e.target.value)}
              disabled={loading}
              data-testid="qs-country"
              className="h-14 px-4 rounded-xl border border-[#E7E5E4] bg-white text-sm font-medium focus:outline-none focus:border-[#EA580C]"
            >
              {COUNTRIES.map((c) => (
                <option key={c.code} value={c.code}>
                  {c.label}
                </option>
              ))}
            </select>
            <button
              onClick={run}
              disabled={loading || product.trim().length < 3}
              data-testid="qs-run"
              className="h-14 px-6 rounded-xl bg-gradient-to-r from-[#F59E0B] to-[#EA580C] hover:brightness-110 disabled:opacity-50 text-white font-medium text-sm flex items-center gap-2 shadow-sm"
            >
              {loading ? (
                <>
                  <ArrowClockwise size={16} className="animate-spin" /> En cours…
                </>
              ) : (
                <>
                  <Lightning size={16} weight="fill" /> Lancer le scan
                </>
              )}
            </button>
          </div>
          {error && (
            <div
              className="mt-3 p-3 rounded-lg bg-[#FFE4E6] text-[#BE123C] text-sm"
              data-testid="qs-error"
            >
              {error}
            </div>
          )}
        </div>

        {/* Loading steps */}
        {loading && (
          <div className="bg-white rounded-2xl border border-[#E7E5E4] p-6 mb-6">
            <LoadingSteps step={step} />
          </div>
        )}

        {/* Result */}
        {result && !loading && <ScanResult result={result} onLaunchSite={() => navigate("/sites/new")} />}

        {/* History */}
        {!loading && !result && history.length > 0 && (
          <div className="bg-white rounded-2xl border border-[#E7E5E4] p-6">
            <div className="text-xs uppercase tracking-widest text-[#78716C] font-semibold mb-4">
              Tes derniers scans
            </div>
            <div className="space-y-2">
              {history.slice(0, 10).map((h) => {
                const meta = VERDICT_META[h.verdict] || VERDICT_META.NO_GO;
                return (
                  <button
                    key={h.id}
                    onClick={() => setResult(h)}
                    data-testid={`history-${h.id}`}
                    className="w-full flex items-center gap-3 p-3 rounded-xl hover:bg-[#FAF7F2] transition text-left"
                  >
                    <div
                      className="w-9 h-9 rounded-lg flex items-center justify-center shrink-0"
                      style={{ background: meta.bg }}
                    >
                      <meta.icon size={18} weight="fill" color={meta.color} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="font-medium text-[#1C1917] truncate">{h.product_or_niche}</div>
                      <div className="text-xs text-[#78716C]">
                        {h.country} · Score {h.score}/100 ·{" "}
                        {h.created_at?.slice(0, 10)}
                      </div>
                    </div>
                    <span
                      className="text-xs font-semibold uppercase tracking-wider px-2.5 py-1 rounded-full"
                      style={{ background: meta.bg, color: meta.color }}
                    >
                      {meta.label}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* Methodology footer */}
        {!loading && !result && (
          <div className="mt-6 p-4 rounded-xl bg-[#FAF7F2] border border-[#E7E5E4]">
            <div className="flex items-start gap-3">
              <Info size={18} className="text-[#78716C] shrink-0 mt-0.5" />
              <div className="text-xs text-[#57534E] leading-relaxed">
                <strong>Méthodologie</strong> — 4 critères obligatoires : prix moyen ≥ 50€,
                volume total (produit + 3 variantes) ≥ 5 000/mois, concurrence Google ≤ 66/100,
                coût d'acquisition Ads estimé ≤ 40% du prix (hypothèse conversion 2%). Les red
                flags (déclin du marché, saturation, réglementation) peuvent forcer un NO-GO
                malgré un bon score.
              </div>
            </div>
          </div>
        )}
      </div>
    </Layout>
  );
}

/* =========================================================
 * Loading steps animation
 * ========================================================= */
function LoadingSteps({ step }) {
  const steps = [
    { n: 1, label: "Analyse IA : variantes de mots-clés + prix concurrents" },
    { n: 2, label: "Google Keyword Planner : volumes réels & CPC" },
    { n: 3, label: "Calcul du verdict Go/No-Go" },
  ];
  return (
    <div className="space-y-3">
      {steps.map((s) => {
        const done = s.n < step;
        const active = s.n === step;
        return (
          <div key={s.n} className="flex items-center gap-3">
            <div
              className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 transition ${
                done
                  ? "bg-[#D1FAE5] text-[#047857]"
                  : active
                    ? "bg-[#FEF3C7]"
                    : "bg-[#F5F2EB] text-[#A8A29E]"
              }`}
            >
              {done ? (
                <CheckCircle size={18} weight="fill" />
              ) : active ? (
                <ArrowClockwise size={16} className="animate-spin text-[#B45309]" />
              ) : (
                <span className="text-xs font-semibold">{s.n}</span>
              )}
            </div>
            <div
              className={`text-sm ${
                done ? "text-[#057857] font-medium" : active ? "text-[#1C1917] font-medium" : "text-[#78716C]"
              }`}
            >
              {s.label}
            </div>
          </div>
        );
      })}
    </div>
  );
}

/* =========================================================
 * Scan result card
 * ========================================================= */
function ScanResult({ result, onLaunchSite }) {
  const meta = VERDICT_META[result.verdict] || VERDICT_META.NO_GO;
  const trendMeta = TREND_META[result.market?.trend] || TREND_META.stable;
  const TrendIcon = trendMeta.icon;
  const m = result.metrics;

  return (
    <div className="space-y-6" data-testid="qs-result">
      {/* Verdict hero */}
      <div
        className="rounded-2xl border-2 p-8"
        style={{
          background: meta.bg,
          borderColor: meta.borderColor,
        }}
        data-testid={`verdict-${result.verdict}`}
      >
        <div className="flex items-start gap-5">
          <div
            className="w-16 h-16 rounded-full flex items-center justify-center shrink-0"
            style={{ background: "#ffffff", boxShadow: `0 2px 12px ${meta.color}33` }}
          >
            <meta.icon size={36} weight="fill" color={meta.color} />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-baseline gap-3 flex-wrap">
              <div
                className="text-3xl md:text-4xl font-semibold tracking-tight"
                style={{ color: meta.color, fontFamily: 'Georgia, serif' }}
              >
                {meta.fullLabel}
              </div>
              <div
                className="text-xs font-bold uppercase tracking-widest px-2.5 py-1 rounded-full"
                style={{ background: "#ffffff", color: meta.color }}
              >
                {meta.label} · {result.score}/100
              </div>
            </div>
            <p className="mt-3 text-[15px] leading-relaxed text-[#1C1917]"
               dangerouslySetInnerHTML={{
                 __html: (result.reason || "").replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>'),
               }}
            />
            <div
              className="mt-4 p-3 rounded-xl bg-white/60 text-sm leading-relaxed"
              style={{ color: "#44403C" }}
            >
              <strong style={{ color: meta.color }}>Recommandation : </strong>
              {result.recommendation}
            </div>
            {result.verdict === "GO" && (
              <button
                onClick={onLaunchSite}
                data-testid="qs-launch-site"
                className="mt-5 inline-flex items-center gap-2 h-11 px-5 rounded-full text-white font-medium transition hover:brightness-110"
                style={{ background: meta.color }}
              >
                <Storefront size={16} weight="fill" /> Lancer un site sur cette niche{" "}
                <ArrowRight size={14} weight="bold" />
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Data source banner */}
      {result.data_source !== "google_ads" && (
        <div className="flex items-center gap-2 p-3 rounded-xl bg-[#FEF3C7] border border-[#FDE68A] text-[#B45309] text-xs">
          <Warning size={14} weight="fill" />
          <span>
            Volumes estimés par l'IA (Google Keyword Planner non disponible pour ce compte). Les
            tendances restent fiables, mais reconnecte un compte Google Ads pour des chiffres
            exacts.
          </span>
        </div>
      )}

      {/* 4 metric tiles */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4" data-testid="qs-metrics">
        <MetricTile
          label="Prix moyen concurrents"
          value={`${Math.round(m.avg_price_median)}€`}
          sub={`min ${Math.round(m.avg_price_min)}€ · max ${Math.round(m.avg_price_max)}€`}
          color="#1C1917"
        />
        <MetricTile
          label="Volume total / mois"
          value={Number(m.volume_total).toLocaleString("fr-FR").replace(",", " ")}
          sub="mot-clé principal + 3 variantes"
          color="#2563EB"
        />
        <MetricTile
          label="Concurrence Google"
          value={`${m.competition_weighted}/100`}
          sub={
            m.competition_weighted <= 33
              ? "Faible"
              : m.competition_weighted <= 66
                ? "Modérée"
                : "Élevée"
          }
          color={m.competition_weighted <= 66 ? "#047857" : "#BE123C"}
        />
        <MetricTile
          label="Coût acquisition Ads"
          value={`${m.acq_cost_pct}%`}
          sub={`CPA ~${Math.round(m.estimated_cpa_eur)}€ · CPC ${m.cpc_weighted_eur}€`}
          color={m.acq_cost_pct <= 40 ? "#047857" : "#BE123C"}
        />
      </div>

      {/* Checklist + keywords split */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Checklist */}
        <div className="bg-white rounded-2xl border border-[#E7E5E4] p-6">
          <div className="text-xs uppercase tracking-widest text-[#78716C] font-semibold mb-4">
            Critères obligatoires
          </div>
          <div className="space-y-3" data-testid="qs-checklist">
            {result.checklist.map((c, i) => (
              <div key={i} className="flex items-start gap-3">
                <div
                  className={`w-6 h-6 rounded-full flex items-center justify-center shrink-0 mt-0.5 ${
                    c.status === "pass" ? "bg-[#D1FAE5]" : "bg-[#FFE4E6]"
                  }`}
                >
                  {c.status === "pass" ? (
                    <CheckCircle size={14} weight="fill" className="text-[#047857]" />
                  ) : (
                    <XCircle size={14} weight="fill" className="text-[#BE123C]" />
                  )}
                </div>
                <div className="flex-1">
                  <div className="text-sm font-medium text-[#1C1917]">{c.label}</div>
                  <div
                    className={`text-xs font-mono ${
                      c.status === "pass" ? "text-[#047857]" : "text-[#BE123C]"
                    }`}
                  >
                    {c.value}
                  </div>
                </div>
              </div>
            ))}
          </div>
          {result.red_flags?.length > 0 && (
            <div className="mt-5 pt-5 border-t border-[#E7E5E4]">
              <div className="text-xs uppercase tracking-widest text-[#BE123C] font-semibold mb-3">
                Red flags
              </div>
              <ul className="space-y-2">
                {result.red_flags.map((r, i) => (
                  <li key={i} className="flex items-start gap-2 text-[13px] text-[#57534E]">
                    <Warning size={14} weight="fill" className="text-[#BE123C] shrink-0 mt-0.5" />
                    <span>{r}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* Keywords */}
        <div className="bg-white rounded-2xl border border-[#E7E5E4] p-6">
          <div className="text-xs uppercase tracking-widest text-[#78716C] font-semibold mb-4">
            Mots-clés stratégiques
          </div>
          <div className="space-y-2" data-testid="qs-keywords">
            {result.keywords?.slice(0, 6).map((k, i) => (
              <div
                key={i}
                className="flex items-center justify-between p-3 rounded-xl bg-[#FAF7F2]"
              >
                <div className="min-w-0 flex-1">
                  <div className="font-medium text-[#1C1917] text-sm truncate">{k.keyword}</div>
                  <div className="text-xs text-[#78716C] mt-0.5">
                    Concurrence {k.competition_index}/100 · CPC {k.cpc_eur}€
                  </div>
                </div>
                <div className="text-right shrink-0 ml-3">
                  <div className="font-mono text-sm font-semibold text-[#1C1917]">
                    {Number(k.volume).toLocaleString("fr-FR").replace(",", " ")}
                  </div>
                  <div className="text-[10px] text-[#78716C] uppercase tracking-wider">
                    rech/mois
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Market insights */}
      <div className="bg-white rounded-2xl border border-[#E7E5E4] p-6">
        <div className="text-xs uppercase tracking-widest text-[#78716C] font-semibold mb-4">
          Paysage marché
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <div className="text-[11px] uppercase tracking-widest text-[#78716C] mb-2">
              Tendance 12 mois
            </div>
            <div className="flex items-center gap-2">
              <TrendIcon size={18} weight="fill" style={{ color: trendMeta.color }} />
              <span className="font-medium" style={{ color: trendMeta.color }}>
                {trendMeta.label}
              </span>
            </div>
          </div>
          <div>
            <div className="text-[11px] uppercase tracking-widest text-[#78716C] mb-2">
              Saturation SERP
            </div>
            <div className="flex items-center gap-2">
              {result.market?.is_saturated ? (
                <>
                  <XCircle size={18} weight="fill" className="text-[#BE123C]" />
                  <span className="font-medium text-[#BE123C]">Saturé</span>
                </>
              ) : (
                <>
                  <CheckCircle size={18} weight="fill" className="text-[#047857]" />
                  <span className="font-medium text-[#047857]">Place à prendre</span>
                </>
              )}
            </div>
          </div>
          <div>
            <div className="text-[11px] uppercase tracking-widest text-[#78716C] mb-2">
              Top concurrents
            </div>
            <div className="flex flex-wrap gap-1.5">
              {(result.market?.top_competitors || []).slice(0, 5).map((c, i) => (
                <a
                  key={i}
                  href={`https://${c}`}
                  target="_blank"
                  rel="noreferrer"
                  className="text-[11px] font-mono px-2 py-1 rounded-md bg-[#FAF7F2] border border-[#E7E5E4] text-[#44403C] hover:bg-[#F5F2EB] hover:text-[#1C1917] transition"
                >
                  {c}
                </a>
              ))}
            </div>
          </div>
        </div>
        {result.market?.regulatory_notes && (
          <div className="mt-4 p-3 rounded-xl bg-[#FEF3C7] border border-[#FDE68A] text-[#B45309] text-sm flex items-start gap-2">
            <Sparkle size={14} weight="fill" className="shrink-0 mt-0.5" />
            <span><strong>À savoir :</strong> {result.market.regulatory_notes}</span>
          </div>
        )}
      </div>
    </div>
  );
}

function MetricTile({ label, value, sub, color }) {
  return (
    <div className="bg-white rounded-2xl border border-[#E7E5E4] p-5">
      <div className="text-[11px] uppercase tracking-widest text-[#78716C] mb-2">{label}</div>
      <div
        className="text-2xl font-semibold leading-tight"
        style={{ color, fontFamily: 'Georgia, serif' }}
      >
        {value}
      </div>
      {sub && <div className="text-xs text-[#78716C] mt-1.5">{sub}</div>}
    </div>
  );
}
