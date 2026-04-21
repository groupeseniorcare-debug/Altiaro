import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, apiCall } from "../lib/api";
import Layout from "../components/Layout";
import {
  ArrowClockwise,
  ArrowRight,
  CheckCircle,
  Globe,
  Info,
  Lightning,
  MagnifyingGlass,
  Rocket,
  Warning,
  XCircle,
} from "@phosphor-icons/react";

const COUNTRY_FLAG = {
  FR: "🇫🇷", DE: "🇩🇪", BE: "🇧🇪", NL: "🇳🇱", CH: "🇨🇭",
  IT: "🇮🇹", UK: "🇬🇧", ES: "🇪🇸",
};

const VERDICT_META = {
  GO: {
    label: "GO",
    color: "#047857",
    bg: "#D1FAE5",
    borderColor: "#A7F3D0",
    icon: CheckCircle,
  },
  GO_WITH_RESERVE: {
    label: "GO avec réserve",
    color: "#B45309",
    bg: "#FEF3C7",
    borderColor: "#FDE68A",
    icon: Warning,
  },
  NO_GO: {
    label: "NO-GO",
    color: "#BE123C",
    bg: "#FFE4E6",
    borderColor: "#FECDD3",
    icon: XCircle,
  },
  ERROR: {
    label: "Erreur",
    color: "#78716C",
    bg: "#F5F2EB",
    borderColor: "#E7E5E4",
    icon: Warning,
  },
};

const fmtNum = (n) =>
  Number(n || 0).toLocaleString("fr-FR").replace(",", " ");

export default function LaunchSite() {
  const navigate = useNavigate();
  const [product, setProduct] = useState("");
  const [siteName, setSiteName] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [scan, setScan] = useState(null);
  const [selected, setSelected] = useState({}); // { FR: true, DE: false, ... }
  const [creating, setCreating] = useState(false);

  const runMulti = async () => {
    const trimmed = product.trim();
    if (trimmed.length < 3) return;
    setLoading(true);
    setError(null);
    setScan(null);
    setSelected({});
    const { data, error: err } = await apiCall(() =>
      api.post("/quick-scan/multi", { product_or_niche: trimmed })
    );
    if (err || !data?.group_id) {
      setLoading(false);
      setError(err || "Impossible de démarrer le scan.");
      return;
    }
    // Poll for progressive results every 2.5s
    const groupId = data.group_id;
    let cancelled = false;
    let attempts = 0;
    const poll = async () => {
      if (cancelled) return;
      attempts += 1;
      const { data: progress, error: pErr } = await apiCall(() =>
        api.get(`/quick-scan/multi/${groupId}`)
      );
      if (cancelled) return;
      if (pErr) {
        setError(pErr);
        setLoading(false);
        return;
      }
      setScan(progress);
      // Presélectionne les GO/GO_WITH_RESERVE dès qu'ils apparaissent
      setSelected((prev) => {
        const next = { ...prev };
        (progress.results || []).forEach((r) => {
          if (next[r.country] === undefined && (r.verdict === "GO" || r.verdict === "GO_WITH_RESERVE")) {
            next[r.country] = true;
          }
        });
        return next;
      });
      if (progress.status === "done" || attempts > 60) {
        setLoading(false);
        return;
      }
      setTimeout(poll, 2500);
    };
    poll();
  };

  const selectedCountries = Object.keys(selected).filter((c) => selected[c]);

  const createSite = async () => {
    if (selectedCountries.length === 0) {
      setError("Sélectionne au moins 1 marché GO avant de lancer le site.");
      return;
    }
    setCreating(true);
    setError(null);
    const slug = (product || "")
      .toLowerCase()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-|-$/g, "")
      .slice(0, 40);
    const payload = {
      name: (siteName || product).trim(),
      niche: product.trim(),
      niche_slug: slug,
      selected_countries: selectedCountries,
      notes: `Lancé depuis scan multi-marché · ${selectedCountries.join(", ")} · scan #${scan?.group_id || ""}`,
    };
    const { data, error: err } = await apiCall(() => api.post("/sites", payload));
    setCreating(false);
    if (err) {
      setError(err);
      return;
    }
    navigate(`/sites/${data.id}/studio`);
  };

  return (
    <Layout>
      <div className="p-8 md:p-12 max-w-[1200px]">
        <div className="flex items-start gap-3 mb-8">
          <div className="w-11 h-11 rounded-lg bg-gradient-to-br from-[#F59E0B] to-[#EA580C] flex items-center justify-center">
            <Rocket size={22} weight="fill" color="#fff" />
          </div>
          <div>
            <div className="text-[11px] uppercase tracking-widest text-[#78716C] mb-1">
              Lancer un site · Analyse multi-marché
            </div>
            <h1 className="font-heading text-4xl font-semibold text-[#1C1917]">
              Quelle niche veux-tu tester ?
            </h1>
            <p className="text-[#57534E] mt-1">
              Une seule idée, analysée en parallèle sur 6 marchés UE. Tu sélectionnes ensuite
              ceux qui valent le coup et le site est prêt à être designé.
            </p>
          </div>
        </div>

        {/* Step 1 — Input */}
        <div className="bg-white rounded-2xl border border-[#E7E5E4] p-6 mb-6" data-testid="launch-input">
          <div className="text-xs uppercase tracking-widest text-[#EA580C] font-bold mb-3">
            Étape 1 · Ton idée
          </div>
          <label className="block text-xs font-semibold text-[#57534E] mb-1.5 uppercase tracking-wider">
            Produit ou niche
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
                onKeyDown={(e) => e.key === "Enter" && !loading && runMulti()}
                placeholder="ex: fauteuil releveur électrique, monte-escalier, lit médicalisé…"
                data-testid="launch-product"
                disabled={loading}
                className="w-full h-14 pl-11 pr-4 rounded-xl border border-[#E7E5E4] bg-white text-[15px] focus:outline-none focus:border-[#EA580C] focus:ring-2 focus:ring-[#EA580C]/20 disabled:opacity-60"
              />
            </div>
            <button
              onClick={runMulti}
              disabled={loading || product.trim().length < 3}
              data-testid="launch-scan"
              className="h-14 px-6 rounded-xl bg-gradient-to-r from-[#F59E0B] to-[#EA580C] hover:brightness-110 disabled:opacity-50 text-white font-medium text-sm flex items-center gap-2 shadow-sm"
            >
              {loading ? (
                <>
                  <ArrowClockwise size={16} className="animate-spin" />
                  {scan?.progress ? (
                    <>Scan… {scan.progress.done}/{scan.progress.total}</>
                  ) : (
                    <>Scan en cours…</>
                  )}
                </>
              ) : (
                <>
                  <Lightning size={16} weight="fill" /> Analyser les 6 marchés
                </>
              )}
            </button>
          </div>
          {error && (
            <div className="mt-3 p-3 rounded-lg bg-[#FFE4E6] text-[#BE123C] text-sm" data-testid="launch-error">
              {error}
            </div>
          )}
        </div>

        {/* Step 2 — Loading state */}
        {loading && (!scan || (scan.results || []).length === 0) && (
          <div className="bg-white rounded-2xl border border-[#E7E5E4] p-8 mb-6 text-center">
            <ArrowClockwise size={32} className="animate-spin mx-auto text-[#EA580C] mb-4" />
            <div className="font-medium text-[#1C1917]">6 marchés en cours d'analyse en parallèle…</div>
            <div className="text-sm text-[#78716C] mt-1">
              Chaque marché met 10-15s (Claude + Google Ads). Les cartes apparaîtront au fur et à mesure.
            </div>
          </div>
        )}

        {/* Step 2 bis — Results (partial or complete) */}
        {scan && (scan.results || []).length > 0 && (
          <div className="mb-6">
            <div className="flex items-baseline justify-between mb-4">
              <div>
                <div className="text-xs uppercase tracking-widest text-[#EA580C] font-bold">
                  Étape 2 · {loading ? "Résultats partiels" : "Résultats par marché"}
                </div>
                <div className="text-lg font-semibold text-[#1C1917] mt-1">
                  {scan.summary.go} GO · {scan.summary.go_with_reserve} GO avec réserve ·{" "}
                  {scan.summary.no_go} NO-GO
                  {scan.summary.error > 0 && <> · {scan.summary.error} erreur</>}
                  {loading && scan.progress && (
                    <span className="text-[#78716C] font-normal ml-2">
                      ({scan.progress.done}/{scan.progress.total} marchés analysés)
                    </span>
                  )}
                </div>
              </div>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4" data-testid="launch-results">
              {scan.results.map((r) => (
                <MarketCard
                  key={r.country}
                  result={r}
                  selected={!!selected[r.country]}
                  onToggle={() => {
                    if (r.verdict === "NO_GO" || r.verdict === "ERROR") return;
                    setSelected((s) => ({ ...s, [r.country]: !s[r.country] }));
                  }}
                />
              ))}
              {loading && scan.progress && scan.progress.done < scan.progress.total && (
                Array.from({ length: scan.progress.total - scan.progress.done }).map((_, i) => (
                  <div
                    key={`pending-${i}`}
                    className="rounded-2xl border-2 border-dashed border-[#E7E5E4] p-5 flex flex-col items-center justify-center gap-2 min-h-[200px] bg-[#FAF7F2]"
                  >
                    <ArrowClockwise size={22} className="animate-spin text-[#EA580C]" />
                    <div className="text-xs text-[#78716C]">Marché en cours…</div>
                  </div>
                ))
              )}
            </div>
          </div>
        )}

        {/* Step 3 — Launch */}
        {scan && !loading && (scan.summary.go + scan.summary.go_with_reserve) > 0 && (
          <div className="bg-white rounded-2xl border-2 border-[#EA580C]/20 p-6 mb-6" data-testid="launch-step3">
            <div className="text-xs uppercase tracking-widest text-[#EA580C] font-bold mb-3">
              Étape 3 · Lance ton site
            </div>
            <label className="block text-xs font-semibold text-[#57534E] mb-1.5 uppercase tracking-wider">
              Nom du site (optionnel — on utilisera ta niche sinon)
            </label>
            <input
              type="text"
              value={siteName}
              onChange={(e) => setSiteName(e.target.value)}
              placeholder={`ex: ${product} Confort, Luméa Senior…`}
              data-testid="launch-site-name"
              className="w-full h-12 px-4 rounded-xl border border-[#E7E5E4] bg-white text-[15px] focus:outline-none focus:border-[#EA580C] focus:ring-2 focus:ring-[#EA580C]/20 mb-4"
            />
            <div className="flex items-center justify-between gap-4 flex-wrap">
              <div className="text-sm text-[#57534E]">
                {selectedCountries.length === 0 ? (
                  <span className="text-[#BE123C]">Aucun marché sélectionné — coche au moins un GO ↑</span>
                ) : (
                  <>
                    <strong>{selectedCountries.length}</strong> marché
                    {selectedCountries.length > 1 ? "s" : ""} sélectionné
                    {selectedCountries.length > 1 ? "s" : ""} ·{" "}
                    {selectedCountries.map((c) => COUNTRY_FLAG[c] || c).join(" ")}
                  </>
                )}
              </div>
              <button
                onClick={createSite}
                disabled={creating || selectedCountries.length === 0}
                data-testid="launch-create"
                className="h-12 px-6 rounded-full bg-gradient-to-r from-[#F59E0B] to-[#EA580C] hover:brightness-110 disabled:opacity-50 text-white font-medium text-sm flex items-center gap-2 shadow-md"
              >
                {creating ? (
                  <>
                    <ArrowClockwise size={16} className="animate-spin" /> Création…
                  </>
                ) : (
                  <>
                    <Rocket size={16} weight="fill" /> Créer le site &amp; lancer le studio IA
                    <ArrowRight size={14} weight="bold" />
                  </>
                )}
              </button>
            </div>
          </div>
        )}

        {/* Methodology */}
        {!scan && !loading && (
          <div className="p-4 rounded-xl bg-[#FAF7F2] border border-[#E7E5E4]">
            <div className="flex items-start gap-3">
              <Info size={18} className="text-[#78716C] shrink-0 mt-0.5" />
              <div className="text-xs text-[#57534E] leading-relaxed">
                <strong>Comment ça marche</strong> — On interroge Claude + Google Keyword Planner en
                parallèle sur les 6 marchés (France, Allemagne, Belgique, Pays-Bas, Suisse, Italie).
                Un verdict GO/NO-GO par marché selon 3 critères obligatoires (prix ≥ 50€, volume ≥
                5 000/mois, CPA Ads ≤ 40%) + concurrence (soft ≤ 75/100, au-delà warning
                "concurrence élevée"). Tu sélectionnes les marchés rentables et le Prompt Studio
                génère le site en un clic.
              </div>
            </div>
          </div>
        )}
      </div>
    </Layout>
  );
}

/* =========================================================
 * Market Card
 * ========================================================= */
function MarketCard({ result, selected, onToggle }) {
  const meta = VERDICT_META[result.verdict] || VERDICT_META.ERROR;
  const canSelect = result.verdict === "GO" || result.verdict === "GO_WITH_RESERVE";
  const m = result.metrics || {};

  return (
    <div
      onClick={onToggle}
      data-testid={`market-${result.country}`}
      className={`group relative rounded-2xl border-2 p-5 transition ${
        canSelect ? "cursor-pointer hover:shadow-md" : "cursor-not-allowed opacity-80"
      }`}
      style={{
        background: selected ? meta.bg : "#ffffff",
        borderColor: selected ? meta.color : meta.borderColor,
      }}
    >
      {/* Selector */}
      {canSelect && (
        <div className="absolute top-4 right-4">
          <div
            className={`w-6 h-6 rounded-md border-2 flex items-center justify-center transition ${
              selected ? "" : "bg-white"
            }`}
            style={{
              background: selected ? meta.color : "#ffffff",
              borderColor: meta.color,
            }}
          >
            {selected && <CheckCircle size={14} weight="bold" color="#ffffff" />}
          </div>
        </div>
      )}

      {/* Header */}
      <div className="flex items-center gap-3 mb-4">
        <div className="text-3xl">{COUNTRY_FLAG[result.country] || "🌍"}</div>
        <div className="flex-1 min-w-0">
          <div className="font-heading text-lg font-semibold text-[#1C1917]">
            {result.country_name || result.country}
          </div>
          <div className="flex items-center gap-1.5">
            <meta.icon size={12} weight="fill" color={meta.color} />
            <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: meta.color }}>
              {meta.label}
              {result.score !== undefined && <> · {result.score}/100</>}
            </span>
          </div>
        </div>
      </div>

      {result.verdict === "ERROR" ? (
        <div className="text-xs text-[#BE123C] bg-[#FFE4E6] p-2 rounded-lg">
          {result.error || "Erreur inconnue"}
        </div>
      ) : (
        <>
          {/* Metrics */}
          <div className="grid grid-cols-2 gap-2 mb-3">
            <Stat label="Prix moyen" value={`${Math.round(m.avg_price_median || 0)}€`} />
            <Stat label="Volume / mois" value={fmtNum(m.volume_total)} />
            <Stat
              label="Concurrence"
              value={`${m.competition_weighted}/100`}
              warn={m.competition_weighted > 75}
            />
            <Stat
              label="CPA / prix"
              value={`${Math.round(m.acq_cost_pct || 0)}%`}
              warn={m.acq_cost_pct > 40}
            />
          </div>

          {/* Competition high warning */}
          {result.competition_high && (
            <div className="flex items-start gap-1.5 text-[11px] text-[#B45309] bg-[#FEF3C7] p-2 rounded-lg mb-2">
              <Warning size={12} weight="fill" className="shrink-0 mt-0.5" />
              <span>Concurrence très élevée — budget Ads à prévoir ×2</span>
            </div>
          )}

          {/* Reason */}
          <div
            className="text-xs text-[#57534E] leading-relaxed mt-3"
            dangerouslySetInnerHTML={{
              __html: (result.reason || "").replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>'),
            }}
          />

          {/* Top competitors */}
          {result.market?.top_competitors?.length > 0 && (
            <div className="flex items-center gap-1.5 mt-3 pt-3 border-t border-[#E7E5E4]">
              <Globe size={10} className="text-[#78716C] shrink-0" />
              <div className="text-[10px] text-[#78716C] truncate">
                vs {result.market.top_competitors.slice(0, 3).join(" · ")}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function Stat({ label, value, warn = false }) {
  return (
    <div>
      <div className="text-[10px] text-[#78716C] uppercase tracking-wider">{label}</div>
      <div
        className="text-sm font-semibold font-mono"
        style={{ color: warn ? "#BE123C" : "#1C1917" }}
      >
        {value}
      </div>
    </div>
  );
}
