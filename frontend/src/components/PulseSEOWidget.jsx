import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Sparkle, CalendarBlank, ChartLineUp, ArrowRight, TrendUp,
} from "@phosphor-icons/react";
import { api, apiCall } from "../lib/api";
import GSCConnectCard from "./GSCConnectCard";
import EeatHistoryPanel from "./EeatHistoryPanel";
import AeoReadinessPanel from "./AeoReadinessPanel";

/**
 * Widget "Pulse SEO" monochrome éditorial — affiche la performance éditoriale
 * et SEO vivante du site : articles publiés ce mois, keywords couverts,
 * score E-E-A-T moyen, date du prochain cluster, top articles récents.
 */
export default function PulseSEOWidget({ siteId }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const { data: res } = await apiCall(() => api.get(`/sites/${siteId}/seo/pulse`));
      if (!cancelled) {
        setData(res || null);
        setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [siteId]);

  const fmtDate = (iso) => {
    if (!iso) return "—";
    try {
      return new Date(iso).toLocaleDateString("fr-FR", { day: "numeric", month: "long" });
    } catch (_e) {
      return iso;
    }
  };

  if (loading) {
    return (
      <div
        data-testid="pulse-seo-loading"
        className="bg-white p-7 animate-pulse text-[12px] text-neutral-400"
        style={{ border: "1px solid #E5E5E5", borderRadius: "2px" }}
      >
        Pulse SEO — chargement…
      </div>
    );
  }
  if (!data) return null;

  const {
    articles_this_month = 0,
    articles_total = 0,
    keywords_covered = 0,
    keywords_total_informational = 0,
    coverage_pct = 0,
    avg_eeat_score = 0,
    recent_articles = [],
    next_cluster_at,
    avg_google_position,
  } = data;

  return (
    <div
      data-testid="pulse-seo-widget"
      className="bg-white overflow-hidden"
      style={{ border: "1px solid #E5E5E5", borderRadius: "2px" }}
    >
      {/* Header */}
      <div className="p-6 md:p-7 flex items-start justify-between gap-4 flex-wrap" style={{ borderBottom: "1px solid #E5E5E5" }}>
        <div>
          <div className="flex items-center gap-3 mb-2">
            <span className="h-px w-8" style={{ background: "#0A0A0A" }} />
            <span className="text-[10px] uppercase tracking-[0.35em] font-medium text-neutral-900">
              Pulse SEO
            </span>
          </div>
          <h3
            className="text-[22px] md:text-[26px] leading-[1.15] tracking-[-0.01em] text-neutral-900"
            style={{ fontFamily: "'Fraunces', Georgia, serif" }}
          >
            Votre moteur éditorial en temps réel.
          </h3>
        </div>
        <Link
          to={`/sites/${siteId}/blog-posts`}
          className="h-9 px-4 text-[12px] font-semibold text-white bg-neutral-900 hover:bg-black flex items-center gap-2 transition"
          style={{ borderRadius: "2px" }}
          data-testid="pulse-seo-manage"
        >
          Gérer le blog <ArrowRight size={13} weight="bold" />
        </Link>
      </div>

      {/* KPIs grid */}
      <div className="grid grid-cols-2 md:grid-cols-4" style={{ borderBottom: "1px solid #E5E5E5" }}>
        <Kpi
          label="Articles ce mois"
          value={articles_this_month}
          caption={`${articles_total} publiés au total`}
          data-testid="kpi-articles-month"
        />
        <Kpi
          label="Couverture keywords"
          value={`${coverage_pct}%`}
          caption={`${keywords_covered} / ${keywords_total_informational || "—"}`}
          progress={coverage_pct}
          borderLeft
          data-testid="kpi-coverage"
        />
        <Kpi
          label="Score E-E-A-T moyen"
          value={avg_eeat_score}
          caption="sur 100 · articles récents"
          progress={avg_eeat_score}
          borderLeft
          data-testid="kpi-eeat"
        />
        <Kpi
          label="Prochain cluster"
          value={next_cluster_at ? fmtDate(next_cluster_at) : "Désactivé"}
          caption={next_cluster_at ? "1 pilier + 4 satellites" : "Activer dans Le Journal"}
          borderLeft
          data-testid="kpi-next-cluster"
        />
      </div>

      {/* Recent articles with EEAT badges */}
      <div className="p-6 md:p-7">
        <div className="flex items-center justify-between mb-4">
          <div className="text-[10px] uppercase tracking-[0.35em] text-neutral-500">
            Top articles récents
          </div>
          <div className="text-[11px] text-neutral-400 flex items-center gap-1.5">
            <ChartLineUp size={12} weight="bold" /> E-E-A-T scoring
          </div>
        </div>
        {recent_articles.length === 0 ? (
          <div className="py-8 text-center">
            <Sparkle size={28} weight="duotone" className="mx-auto mb-2 text-neutral-300" />
            <div className="text-[13px] text-neutral-500">
              Aucun article encore publié.{" "}
              <Link to={`/sites/${siteId}/blog-posts`} className="underline text-neutral-900 font-medium">
                Lancez votre premier cluster
              </Link>
              .
            </div>
          </div>
        ) : (
          <ul className="divide-y" style={{ borderColor: "#E5E5E5" }}>
            {recent_articles.map((a) => (
              <li key={a.slug} className="py-3 flex items-center gap-4">
                <div className="flex-1 min-w-0">
                  <div className="text-[13.5px] text-neutral-900 font-medium truncate">
                    {a.title || "(sans titre)"}
                  </div>
                  <div className="text-[11px] text-neutral-500 mt-0.5 flex flex-wrap gap-x-2.5">
                    <span className="uppercase tracking-wider">{a.type}</span>
                    <span>·</span>
                    <span>{a.word_count || 0} mots</span>
                    {a.read_minutes ? <><span>·</span><span>{a.read_minutes} min</span></> : null}
                  </div>
                </div>
                <EeatBadge score={a.eeat_score} />
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* E-E-A-T history + badges */}
      <EeatHistoryPanel siteId={siteId} />

      {/* AEO Readiness */}
      <AeoReadinessPanel siteId={siteId} />

      {/* Google Search Console — connect / metrics band */}
      <GSCConnectCard siteId={siteId} />
    </div>
  );
}

function Kpi({ label, value, caption, progress, borderLeft }) {
  return (
    <div
      className="p-5 md:p-6"
      style={{ borderLeft: borderLeft ? "1px solid #E5E5E5" : "none" }}
    >
      <div className="text-[10px] uppercase tracking-[0.3em] text-neutral-500 mb-2.5">
        {label}
      </div>
      <div
        className="text-[28px] md:text-[32px] leading-none text-neutral-900"
        style={{ fontFamily: "'Fraunces', Georgia, serif" }}
      >
        {value}
      </div>
      {caption && (
        <div className="text-[11px] text-neutral-500 mt-2 line-clamp-1">{caption}</div>
      )}
      {typeof progress === "number" && (
        <div className="mt-3 h-1 bg-neutral-200 overflow-hidden" style={{ borderRadius: "1px" }}>
          <div
            className="h-full bg-neutral-900 transition-all duration-700"
            style={{ width: `${Math.max(2, Math.min(100, progress))}%` }}
          />
        </div>
      )}
    </div>
  );
}

function EeatBadge({ score }) {
  const s = Number(score) || 0;
  const tone = s >= 75 ? "ok" : s >= 55 ? "mid" : "low";
  const bg = tone === "ok" ? "#0A0A0A" : tone === "mid" ? "#F5F5F5" : "#FEF3C7";
  const fg = tone === "ok" ? "#FFFFFF" : tone === "mid" ? "#0A0A0A" : "#92400E";
  return (
    <div
      className="shrink-0 flex items-center gap-1.5 px-2.5 py-1 text-[11px] font-semibold tabular-nums"
      style={{ background: bg, color: fg, borderRadius: "2px" }}
      title="Score E-E-A-T estimé — longueur, structure, FAQ, listes, liens internes, méta SEO"
    >
      <TrendUp size={11} weight="bold" />
      {s}
    </div>
  );
}
