import React, { useEffect, useState, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import {
  ArrowLeft, ArrowClockwise, CheckCircle, Warning, XCircle,
  MagnifyingGlass, Sparkle, TrendUp, Shield, ChartBar, Clock,
  Lightbulb, Robot,
} from "@phosphor-icons/react";
import { api, apiCall } from "../lib/api";
import SeoStudioPanel from "../components/SeoStudioPanel";

const DIMENSION_ORDER = ["catalog", "content", "structure", "trust", "aeo", "freshness"];

const SEVERITY = {
  critical: { label: "Critique", bg: "bg-rose-50", text: "text-rose-900", border: "border-rose-200", icon: XCircle, iconColor: "text-rose-600" },
  high:     { label: "Important", bg: "bg-amber-50", text: "text-amber-900", border: "border-amber-200", icon: Warning, iconColor: "text-amber-600" },
  medium:   { label: "À faire", bg: "bg-sky-50", text: "text-sky-900", border: "border-sky-200", icon: Lightbulb, iconColor: "text-sky-600" },
  low:      { label: "Optionnel", bg: "bg-neutral-50", text: "text-neutral-700", border: "border-neutral-200", icon: Lightbulb, iconColor: "text-neutral-500" },
};

const scoreColor = (s) => {
  if (s >= 80) return { ring: "#10b981", text: "text-emerald-700", bg: "bg-emerald-50", border: "border-emerald-200", label: "Excellent" };
  if (s >= 60) return { ring: "#f59e0b", text: "text-amber-700", bg: "bg-amber-50", border: "border-amber-200", label: "À améliorer" };
  if (s >= 35) return { ring: "#f97316", text: "text-orange-700", bg: "bg-orange-50", border: "border-orange-200", label: "Faible" };
  return { ring: "#e11d48", text: "text-rose-700", bg: "bg-rose-50", border: "border-rose-200", label: "Critique" };
};

export default function SiteSEO() {
  const { id: siteId } = useParams();
  const [audit, setAudit] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [tab, setTab] = useState("audit");

  const load = useCallback(async (fromRefresh = false) => {
    fromRefresh ? setRefreshing(true) : setLoading(true);
    const { data } = await apiCall(() => api.get(`/sites/${siteId}/seo-audit`));
    if (data) setAudit(data);
    setLoading(false);
    setRefreshing(false);
  }, [siteId]);

  useEffect(() => { load(); }, [load]);

  if (loading) {
    return (
      <div className="min-h-screen bg-[#F9FAFB]" data-testid="site-seo-skeleton" aria-busy="true">
        <div className="max-w-7xl mx-auto p-8">
          <div className="mb-8">
            <div className="h-3 w-24 bg-stone-200 rounded animate-pulse mb-2" />
            <div className="h-8 w-72 bg-stone-200 rounded animate-pulse" />
          </div>
          <div className="bg-white rounded-xl border border-neutral-200 p-8 mb-6">
            <div className="flex items-center gap-6 flex-wrap">
              <div className="w-32 h-32 rounded-full bg-stone-200 animate-pulse" />
              <div className="flex-1 min-w-[200px]">
                <div className="h-3 w-32 bg-stone-200 rounded animate-pulse mb-3" />
                <div className="h-6 w-60 bg-stone-200 rounded animate-pulse mb-2" />
                <div className="h-3 w-96 max-w-full bg-stone-200 rounded animate-pulse" />
              </div>
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="bg-white rounded-xl border border-neutral-200 p-6 h-32 animate-pulse" />
            ))}
          </div>
          <div className="bg-white rounded-xl border border-neutral-200 p-6 h-[400px] animate-pulse" />
        </div>
      </div>
    );
  }

  if (!audit) {
    return (
      <div className="min-h-screen bg-[#FAF7F2] flex items-center justify-center">
        <div className="text-rose-700">Impossible de charger l'audit SEO.</div>
      </div>
    );
  }

  const overallColor = scoreColor(audit.overall_score);

  return (
    <div className="min-h-screen bg-[#FAF7F2]">
      <div className="max-w-[1600px] mx-auto px-6 md:px-10 py-8">
        <Link
          to={`/sites/${siteId}`}
          className="inline-flex items-center gap-2 text-sm text-neutral-600 hover:text-neutral-900 mb-6"
          data-testid="seo-back-to-site"
        >
          <ArrowLeft size={14} /> Retour au cockpit
        </Link>

        <div className="flex items-end justify-between gap-4 mb-8 flex-wrap">
          <div>
            <div className="text-[11px] uppercase tracking-[0.2em] text-neutral-500 mb-2 flex items-center gap-2">
              <MagnifyingGlass size={12} weight="bold" /> Dashboard SEO / AEO
            </div>
            <h1 className="text-3xl md:text-4xl font-semibold text-neutral-900" style={{ fontFamily: "'Fraunces', serif" }}>
              Santé organique de {audit.site_name}
            </h1>
            <p className="text-sm text-neutral-500 mt-2">
              Audit multi-dimensions mis à jour {new Date(audit.audited_at).toLocaleString("fr-FR")}.
            </p>
          </div>
          <button
            onClick={() => load(true)}
            disabled={refreshing}
            data-testid="seo-refresh-btn"
            className="h-11 px-4 rounded-xl bg-white border border-neutral-200 hover:border-neutral-900 text-neutral-900 text-sm font-medium flex items-center gap-2 transition disabled:opacity-60"
          >
            <ArrowClockwise size={16} className={refreshing ? "animate-spin" : ""} />
            {refreshing ? "Analyse…" : "Rafraîchir l'audit"}
          </button>
        </div>

        {/* Tabs */}
        <div className="bg-white rounded-2xl border border-neutral-200 p-1.5 mb-6 inline-flex gap-1" data-testid="seo-tabs">
          <button
            onClick={() => setTab("audit")}
            data-testid="tab-audit"
            className={`h-10 px-4 rounded-xl text-sm font-medium flex items-center gap-2 transition ${
              tab === "audit" ? "bg-neutral-900 text-white" : "text-neutral-600 hover:bg-neutral-100"
            }`}
          >
            <ChartBar size={14} weight={tab === "audit" ? "fill" : "duotone"} /> Audit SEO
          </button>
          <button
            onClick={() => setTab("aeo")}
            data-testid="tab-aeo"
            className={`h-10 px-4 rounded-xl text-sm font-medium flex items-center gap-2 transition ${
              tab === "aeo" ? "bg-neutral-900 text-white" : "text-neutral-600 hover:bg-neutral-100"
            }`}
          >
            <Robot size={14} weight={tab === "aeo" ? "fill" : "duotone"} /> Studio AEO + mots-clés
          </button>
        </div>

        {tab === "aeo" && <SeoStudioPanel siteId={siteId} />}

        {tab === "audit" && (
          <>
            {/* Published banner */}
        {!audit.published && (
          <div className="mb-6 p-4 rounded-2xl bg-rose-50 border border-rose-200 flex items-start gap-3" data-testid="seo-not-published-banner">
            <XCircle size={20} weight="fill" className="text-rose-600 flex-shrink-0 mt-0.5" />
            <div>
              <div className="font-semibold text-rose-900 mb-1">Boutique non publiée</div>
              <div className="text-sm text-rose-800">
                Aucune de vos pages n'est accessible aux moteurs de recherche. Terminez la validation du prompt #17 pour publier.
              </div>
            </div>
          </div>
        )}

        {/* Overall score card */}
        <div className="bg-white rounded-2xl border border-neutral-200 p-8 mb-6" data-testid="seo-overall-card">
          <div className="flex items-center gap-8 flex-wrap">
            <GaugeRing score={audit.overall_score} color={overallColor.ring} size={180} />
            <div className="flex-1 min-w-[240px]">
              <div className="text-[11px] uppercase tracking-[0.2em] text-neutral-500 mb-2">Score global</div>
              <div className="flex items-baseline gap-3 mb-2">
                <div className="text-5xl font-semibold text-neutral-900" style={{ fontFamily: "'Fraunces', serif" }}>
                  {audit.overall_score}
                </div>
                <div className={`text-sm font-medium ${overallColor.text}`}>{overallColor.label}</div>
              </div>
              <p className="text-sm text-neutral-600 leading-relaxed max-w-lg">
                Moyenne pondérée des 6 dimensions SEO/AEO. Un score supérieur à 80 correspond à une boutique prête pour un ranking organique solide.
              </p>
            </div>
          </div>
        </div>

        {/* Dimensions grid */}
        <div className="mb-8">
          <div className="text-[11px] uppercase tracking-[0.2em] text-neutral-500 mb-3">Dimensions</div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4" data-testid="seo-dimensions-grid">
            {DIMENSION_ORDER.map((key) => {
              const d = audit.dimensions[key];
              if (!d) return null;
              const c = scoreColor(d.score);
              return (
                <div
                  key={key}
                  data-testid={`seo-dim-${key}`}
                  className={`rounded-2xl border ${c.border} ${c.bg} p-5 transition hover:shadow-sm`}
                >
                  <div className="flex items-start justify-between gap-3 mb-4">
                    <div className="font-medium text-neutral-900 text-sm leading-tight">{d.label}</div>
                    <DimensionIcon k={key} />
                  </div>
                  <div className="flex items-baseline gap-2 mb-3">
                    <div className={`text-3xl font-semibold ${c.text}`} style={{ fontFamily: "'Fraunces', serif" }}>
                      {d.score}
                    </div>
                    <div className="text-xs text-neutral-500">/ 100</div>
                  </div>
                  <ProgressBar value={d.score} color={c.ring} />
                </div>
              );
            })}
          </div>
        </div>

        {/* Coverage metrics */}
        <div className="bg-white rounded-2xl border border-neutral-200 p-6 mb-6" data-testid="seo-coverage-card">
          <div className="text-[11px] uppercase tracking-[0.2em] text-neutral-500 mb-4 flex items-center gap-2">
            <ChartBar size={12} weight="bold" /> Couverture
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Stat label="Produits actifs" value={audit.coverage.products_total} testId="cov-products-total" />
            <Stat label="Produits enrichis IA" value={`${audit.coverage.products_enriched}/${audit.coverage.products_total}`} testId="cov-products-enriched" />
            <Stat label="Avec avis" value={audit.coverage.products_with_reviews} testId="cov-products-reviews" />
            <Stat label="Avec bundles" value={audit.coverage.products_with_bundles} testId="cov-products-bundles" />
            <Stat label="Articles blog" value={audit.coverage.blog_posts} testId="cov-blog" />
            <Stat label="Collections" value={audit.coverage.collections} testId="cov-collections" />
            <Stat label="Avec image" value={audit.coverage.products_with_images} testId="cov-products-images" />
            <Stat label="Statut" value={audit.published ? "Publié" : "Brouillon"} highlight={audit.published ? "ok" : "warn"} testId="cov-published" />
          </div>
        </div>

        {/* Checks */}
        <div className="bg-white rounded-2xl border border-neutral-200 p-6 mb-6" data-testid="seo-checks-card">
          <div className="text-[11px] uppercase tracking-[0.2em] text-neutral-500 mb-4 flex items-center gap-2">
            <Shield size={12} weight="bold" /> Contrôles
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            {Object.entries(audit.checks).map(([k, v]) => (
              <div key={k} data-testid={`check-${k}`} className="flex items-center gap-2 text-sm">
                {v ? (
                  <CheckCircle size={16} weight="fill" className="text-emerald-600 flex-shrink-0" />
                ) : (
                  <XCircle size={16} weight="fill" className="text-rose-500 flex-shrink-0" />
                )}
                <span className={v ? "text-neutral-700" : "text-neutral-500"}>{CHECK_LABELS[k] || k}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Recommendations */}
        <div className="bg-white rounded-2xl border border-neutral-200 p-6" data-testid="seo-recommendations-card">
          <div className="text-[11px] uppercase tracking-[0.2em] text-neutral-500 mb-4 flex items-center gap-2">
            <Lightbulb size={12} weight="bold" /> Recommandations ({audit.recommendations.length})
          </div>
          {audit.recommendations.length === 0 ? (
            <div className="py-6 text-center">
              <CheckCircle size={32} weight="fill" className="mx-auto text-emerald-500 mb-2" />
              <div className="font-medium text-neutral-900">Aucune recommandation — boutique optimale</div>
              <div className="text-sm text-neutral-500 mt-1">
                Continuez à publier du contenu frais pour maintenir votre ranking.
              </div>
            </div>
          ) : (
            <div className="space-y-3" data-testid="seo-reco-list">
              {audit.recommendations.map((r, i) => {
                const s = SEVERITY[r.severity] || SEVERITY.medium;
                const Icon = s.icon;
                return (
                  <div
                    key={i}
                    data-testid={`seo-reco-${i}`}
                    className={`rounded-xl border ${s.border} ${s.bg} p-4 flex items-start gap-3`}
                  >
                    <Icon size={18} weight="fill" className={`${s.iconColor} flex-shrink-0 mt-0.5`} />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className={`text-[10px] uppercase tracking-widest font-bold ${s.text}`}>{s.label}</span>
                      </div>
                      <div className={`text-sm ${s.text} leading-relaxed`}>{r.text}</div>
                      {r.action && (
                        <div className="text-xs text-neutral-600 mt-2 flex items-center gap-1.5">
                          <Sparkle size={11} weight="bold" /> <span className="font-medium">Action :</span> {r.action}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
          </>
        )}
      </div>
    </div>
  );
}

const CHECK_LABELS = {
  published: "Boutique publiée",
  has_brand: "Brand book défini",
  has_logo: "Logo présent",
  has_tagline: "Baseline présente",
  legal_complete: "Pages légales complètes",
  about_done: "Page 'À propos' remplie",
  contact_done: "Page 'Contact' remplie",
  values_done: "Valeurs éditoriales",
  founder_done: "Histoire du fondateur",
};

function DimensionIcon({ k }) {
  const map = {
    catalog: Sparkle,
    content: Sparkle,
    structure: Shield,
    trust: Shield,
    aeo: TrendUp,
    freshness: Clock,
  };
  const Icon = map[k] || Sparkle;
  return <Icon size={18} weight="duotone" className="text-neutral-400 flex-shrink-0" />;
}

function ProgressBar({ value, color }) {
  return (
    <div className="h-1.5 rounded-full bg-neutral-200 overflow-hidden">
      <div
        className="h-full rounded-full transition-all duration-500"
        style={{ width: `${Math.max(0, Math.min(100, value))}%`, background: color }}
      />
    </div>
  );
}

function Stat({ label, value, highlight, testId }) {
  const hl = highlight === "ok" ? "text-emerald-700" : highlight === "warn" ? "text-amber-700" : "text-neutral-900";
  return (
    <div data-testid={testId}>
      <div className="text-[11px] uppercase tracking-widest text-neutral-500 mb-1">{label}</div>
      <div className={`text-xl font-semibold ${hl}`} style={{ fontFamily: "'Fraunces', serif" }}>
        {value}
      </div>
    </div>
  );
}

function GaugeRing({ score, color = "#10b981", size = 180 }) {
  const stroke = 14;
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const clamped = Math.max(0, Math.min(100, score));
  const dash = (clamped / 100) * c;

  return (
    <svg width={size} height={size} className="flex-shrink-0">
      <circle
        cx={size / 2}
        cy={size / 2}
        r={r}
        fill="none"
        stroke="#F5F2EB"
        strokeWidth={stroke}
      />
      <circle
        cx={size / 2}
        cy={size / 2}
        r={r}
        fill="none"
        stroke={color}
        strokeWidth={stroke}
        strokeLinecap="round"
        strokeDasharray={`${dash} ${c - dash}`}
        strokeDashoffset={c / 4}
        transform={`rotate(-90 ${size / 2} ${size / 2})`}
        style={{ transition: "stroke-dasharray 600ms ease-out, stroke 300ms ease-out" }}
      />
      <text
        x="50%"
        y="50%"
        dominantBaseline="central"
        textAnchor="middle"
        fill="#1C1917"
        style={{ fontFamily: "'Fraunces', serif", fontSize: 42, fontWeight: 600 }}
      >
        {clamped}
      </text>
    </svg>
  );
}
