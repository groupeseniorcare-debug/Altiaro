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
  GO: { label: "GO", color: "#10B981", bg: "rgba(16,185,129,0.08)", borderColor: "rgba(16,185,129,0.4)", icon: CheckCircle },
  GO_WITH_RESERVE: { label: "RESERVE", color: "#F59E0B", bg: "rgba(245,158,11,0.08)", borderColor: "rgba(245,158,11,0.4)", icon: Warning },
  NO_GO: { label: "NO-GO", color: "#EF4444", bg: "rgba(239,68,68,0.05)", borderColor: "rgba(239,68,68,0.25)", icon: XCircle },
  ERROR: { label: "ERR", color: "#71717A", bg: "rgba(63,63,70,0.3)", borderColor: "rgba(63,63,70,0.5)", icon: Warning },
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
      <div className="p-8 md:p-10 max-w-[1200px]">
        <div className="mb-8">
          <div className="text-[10px] uppercase tracking-[0.12em] text-zinc-500 font-medium mb-1.5">
            Lancer un site
          </div>
          <h1 className="text-3xl font-semibold text-zinc-100 tracking-tight">
            Quelle niche veux-tu tester ?
          </h1>
          <p className="text-zinc-500 text-sm mt-1 max-w-xl">
            Une seule idée, analysée en parallèle sur 6 marchés UE. Les cartes apparaissent au fur
            et à mesure — sélectionne celles qui valent le coup.
          </p>
        </div>

        {/* Step 1 — Input */}
        <div className="bg-zinc-950 rounded-md border border-zinc-900 p-5 mb-4" data-testid="launch-input">
          <div className="text-[10px] uppercase tracking-[0.12em] text-zinc-500 font-medium mb-2">
            01 · Ton idée
          </div>
          <div className="flex flex-col md:flex-row gap-2">
            <div className="flex-1 relative">
              <MagnifyingGlass
                size={16}
                className="absolute left-3.5 top-1/2 -translate-y-1/2 text-zinc-600"
              />
              <input
                type="text"
                value={product}
                onChange={(e) => setProduct(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && !loading && runMulti()}
                placeholder="fauteuil releveur électrique, monte-escalier, lit médicalisé…"
                data-testid="launch-product"
                disabled={loading}
                className="w-full h-11 pl-10 pr-4 rounded-md border border-zinc-800 bg-black text-zinc-100 text-sm placeholder:text-zinc-600 focus:outline-none focus:border-zinc-600 focus:ring-1 focus:ring-zinc-400 disabled:opacity-60"
              />
            </div>
            <button
              onClick={runMulti}
              disabled={loading || product.trim().length < 3}
              data-testid="launch-scan"
              className="h-11 px-4 rounded-md bg-white hover:bg-zinc-200 disabled:opacity-50 text-black font-medium text-sm flex items-center gap-1.5 transition-colors"
            >
              {loading ? (
                <>
                  <ArrowClockwise size={14} className="animate-spin" />
                  {scan?.progress ? (
                    <>Scan · {scan.progress.done}/{scan.progress.total}</>
                  ) : (
                    <>Analyse…</>
                  )}
                </>
              ) : (
                <>
                  <Lightning size={14} weight="fill" /> Analyser les 6 marchés
                </>
              )}
            </button>
          </div>
          {error && (
            <div
              className="mt-3 px-3 py-2 rounded-md bg-red-500/10 border border-red-500/20 text-red-400 text-xs"
              data-testid="launch-error"
            >
              {error}
            </div>
          )}
        </div>

        {/* Step 2 — Loading state */}
        {loading && (!scan || (scan.results || []).length === 0) && (
          <div className="bg-zinc-950 rounded-md border border-zinc-900 p-8 mb-4 text-center">
            <ArrowClockwise size={24} className="animate-spin mx-auto text-zinc-400 mb-3" />
            <div className="text-sm font-medium text-zinc-200">6 marchés en analyse parallèle</div>
            <div className="text-xs text-zinc-500 mt-1">
              Chaque marché met 10-15s · Claude + Google Ads
            </div>
          </div>
        )}

        {/* Step 2 bis — Results */}
        {scan && (scan.results || []).length > 0 && (
          <div className="mb-4">
            <div className="flex items-baseline justify-between mb-3">
              <div>
                <div className="text-[10px] uppercase tracking-[0.12em] text-zinc-500 font-medium">
                  02 · Résultats
                </div>
                <div className="text-sm text-zinc-300 mt-1 font-mono">
                  <span className="text-emerald-400">{scan.summary.go} GO</span>
                  <span className="text-zinc-700 mx-2">·</span>
                  <span className="text-amber-400">{scan.summary.go_with_reserve} RESERVE</span>
                  <span className="text-zinc-700 mx-2">·</span>
                  <span className="text-red-400">{scan.summary.no_go} NO-GO</span>
                  {scan.summary.error > 0 && (
                    <>
                      <span className="text-zinc-700 mx-2">·</span>
                      <span className="text-zinc-500">{scan.summary.error} err</span>
                    </>
                  )}
                  {loading && scan.progress && (
                    <span className="text-zinc-500 ml-3">
                      {scan.progress.done}/{scan.progress.total}
                    </span>
                  )}
                </div>
              </div>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3" data-testid="launch-results">
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
                    className="rounded-md border border-dashed border-zinc-800 p-5 flex flex-col items-center justify-center gap-2 min-h-[200px] bg-zinc-950"
                  >
                    <ArrowClockwise size={18} className="animate-spin text-zinc-500" />
                    <div className="text-[11px] text-zinc-500">Analyse en cours…</div>
                  </div>
                ))
              )}
            </div>
          </div>
        )}

        {/* Step 3 — Launch */}
        {scan && !loading && (scan.summary.go + scan.summary.go_with_reserve) > 0 && (
          <div className="bg-zinc-950 rounded-md border border-zinc-700 p-5" data-testid="launch-step3">
            <div className="text-[10px] uppercase tracking-[0.12em] text-zinc-300 font-medium mb-2">
              03 · Lance ton site
            </div>
            <input
              type="text"
              value={siteName}
              onChange={(e) => setSiteName(e.target.value)}
              placeholder={`Nom du site (par défaut : ${product})`}
              data-testid="launch-site-name"
              className="w-full h-10 px-3 rounded-md border border-zinc-800 bg-black text-zinc-100 text-sm placeholder:text-zinc-600 focus:outline-none focus:border-zinc-600 focus:ring-1 focus:ring-zinc-400 mb-3"
            />
            <div className="flex items-center justify-between gap-4 flex-wrap">
              <div className="text-xs text-zinc-500">
                {selectedCountries.length === 0 ? (
                  <span className="text-red-400">Sélectionne au moins 1 marché GO ↑</span>
                ) : (
                  <>
                    <span className="text-zinc-300 font-medium">{selectedCountries.length}</span>{" "}
                    marché{selectedCountries.length > 1 ? "s" : ""} ·{" "}
                    {selectedCountries.map((c) => COUNTRY_FLAG[c] || c).join(" ")}
                  </>
                )}
              </div>
              <button
                onClick={createSite}
                disabled={creating || selectedCountries.length === 0}
                data-testid="launch-create"
                className="h-9 px-4 rounded-md bg-white hover:bg-zinc-200 disabled:opacity-50 text-black font-medium text-sm flex items-center gap-1.5 transition-colors"
              >
                {creating ? (
                  <>
                    <ArrowClockwise size={14} className="animate-spin" /> Création…
                  </>
                ) : (
                  <>
                    <Rocket size={14} weight="fill" /> Créer &amp; lancer le studio
                    <ArrowRight size={12} weight="bold" />
                  </>
                )}
              </button>
            </div>
          </div>
        )}

        {/* Methodology */}
        {!scan && !loading && (
          <div className="p-4 rounded-md border border-zinc-900 bg-zinc-950">
            <div className="flex items-start gap-2.5">
              <Info size={14} className="text-zinc-600 shrink-0 mt-0.5" />
              <div className="text-[11px] text-zinc-500 leading-relaxed">
                <span className="text-zinc-300 font-medium">Comment ça marche</span> — Claude +
                Google Keyword Planner en parallèle sur 6 marchés (FR / DE / BE / NL / CH / IT). Un
                verdict par marché sur 3 critères obligatoires (prix ≥ 50€, volume ≥ 5 000/mois, CPA
                Ads ≤ 40%) + concurrence (soft ≤ 75/100, au-delà warning "concurrence élevée").
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
      className={`group relative rounded-md border p-4 transition-colors ${
        canSelect ? "cursor-pointer hover:border-zinc-600" : "cursor-not-allowed opacity-70"
      } ${selected ? "bg-zinc-900" : "bg-zinc-950"}`}
      style={{
        borderColor: selected ? meta.color : "#27272A",
      }}
    >
      {/* Selector */}
      {canSelect && (
        <div className="absolute top-3 right-3">
          <div
            className="w-5 h-5 rounded border flex items-center justify-center transition-colors"
            style={{
              background: selected ? meta.color : "transparent",
              borderColor: selected ? meta.color : "#3F3F46",
            }}
          >
            {selected && <CheckCircle size={12} weight="bold" color="#000000" />}
          </div>
        </div>
      )}

      {/* Header */}
      <div className="flex items-center gap-2.5 mb-4">
        <div className="text-2xl">{COUNTRY_FLAG[result.country] || "🌍"}</div>
        <div className="flex-1 min-w-0">
          <div className="font-medium text-zinc-100 text-sm">
            {result.country_name || result.country}
          </div>
          <div className="flex items-center gap-1 mt-0.5">
            <meta.icon size={10} weight="fill" color={meta.color} />
            <span className="text-[10px] font-semibold uppercase tracking-wider" style={{ color: meta.color }}>
              {meta.label}
              {result.score !== undefined && (
                <span className="text-zinc-600"> · {result.score}</span>
              )}
            </span>
          </div>
        </div>
      </div>

      {result.verdict === "ERROR" ? (
        <div className="text-[11px] text-red-400 bg-red-500/5 border border-red-500/20 p-2 rounded">
          {result.error || "Erreur inconnue"}
        </div>
      ) : (
        <>
          <div className="grid grid-cols-2 gap-x-3 gap-y-2.5 mb-3">
            <Stat label="Prix moyen" value={`${Math.round(m.avg_price_median || 0)}€`} />
            <Stat label="Volume/mois" value={fmtNum(m.volume_total)} />
            <Stat
              label="Concurrence"
              value={`${m.competition_weighted}/100`}
              warn={m.competition_weighted > 75}
            />
            <Stat
              label="CPA/prix"
              value={`${Math.round(m.acq_cost_pct || 0)}%`}
              warn={m.acq_cost_pct > 40}
            />
          </div>

          {result.competition_high && (
            <div className="flex items-start gap-1.5 text-[10px] text-amber-300 bg-amber-500/5 border border-amber-500/20 p-1.5 rounded mb-2">
              <Warning size={10} weight="fill" className="shrink-0 mt-0.5" />
              <span>Concurrence élevée · budget Ads ×2</span>
            </div>
          )}

          <div
            className="text-[11px] text-zinc-400 leading-relaxed mt-2"
            dangerouslySetInnerHTML={{
              __html: (result.reason || "").replace(
                /\*\*(.*?)\*\*/g,
                '<strong class="text-zinc-200 font-medium">$1</strong>'
              ),
            }}
          />

          {result.market?.top_competitors?.length > 0 && (
            <div className="flex items-center gap-1.5 mt-3 pt-3 border-t border-zinc-800">
              <Globe size={9} className="text-zinc-600 shrink-0" />
              <div className="text-[10px] text-zinc-500 truncate font-mono">
                {result.market.top_competitors.slice(0, 3).join(" · ")}
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
      <div className="text-[9px] text-zinc-500 uppercase tracking-wider font-medium">{label}</div>
      <div
        className={`text-xs font-mono font-semibold tabular-nums mt-0.5 ${
          warn ? "text-red-400" : "text-zinc-200"
        }`}
      >
        {value}
      </div>
    </div>
  );
}
