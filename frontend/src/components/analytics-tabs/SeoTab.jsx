import React, { useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import {
  MagnifyingGlass, CircleNotch, CheckCircle, Warning, Article, Cursor, Eye, Target,
  Lightning, TrendUp, Sparkle, ClockClockwise, ChartBar, MegaphoneSimple,
} from "@phosphor-icons/react";
import { api, apiCall } from "../../lib/api";
import { useAuth } from "../../lib/auth";

function MiniCard({ icon: Icon, label, value, sub, tone = "neutral", testId }) {
  const tones = {
    ok:      "bg-emerald-50 border-emerald-200 text-emerald-800",
    warn:    "bg-amber-50 border-amber-200 text-amber-800",
    neutral: "bg-white border-neutral-200 text-neutral-800",
  };
  return (
    <div className={`rounded-xl border p-4 ${tones[tone] || tones.neutral}`} data-testid={testId}>
      <div className="flex items-center gap-2 text-[11px] uppercase tracking-widest opacity-70 mb-1">
        <Icon size={13} weight="duotone" /> {label}
      </div>
      <div className="text-lg font-semibold tabular-nums" style={{ fontFamily: "'Fraunces', serif" }}>{value}</div>
      {sub && <div className="text-[11px] opacity-70 mt-0.5">{sub}</div>}
    </div>
  );
}

function TrendBadge({ trend }) {
  const map = {
    montante: { label: "↑ Tendance", cls: "bg-emerald-50 text-emerald-700" },
    stable: { label: "→ Stable", cls: "bg-neutral-100 text-neutral-700" },
    descendante: { label: "↓ Baisse", cls: "bg-amber-50 text-amber-700" },
  };
  const t = map[trend] || map.stable;
  return <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium ${t.cls}`}>{t.label}</span>;
}

function timeAgo(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  const diff = (Date.now() - d.getTime()) / 1000;
  if (diff < 60) return "à l'instant";
  if (diff < 3600) return `il y a ${Math.floor(diff / 60)} min`;
  if (diff < 86400) return `il y a ${Math.floor(diff / 3600)}h`;
  return `il y a ${Math.floor(diff / 86400)}j`;
}

const CRON_LABELS = {
  blog_auto: "Nouvel article publié",
  emerging_keywords: "Mots-clés émergents détectés",
  content_refresh: "Article rafraîchi",
  internal_linking: "Liens internes ajoutés",
  gsc_alerts: "Check GSC",
  paa_faq: "FAQ produit enrichies",
  content_gap: "Gaps concurrents détectés",
  seo_weekly_report: "Rapport SEO hebdo",
};

export default function SeoTab({ siteId }) {
  const navigate = useNavigate();
  const { user } = useAuth() || {};
  const isAdmin = user?.role === "admin";
  const [gscStatus, setGscStatus] = useState(null);
  const [gscMetrics, setGscMetrics] = useState(null);
  const [blog, setBlog] = useState([]);
  const [emerging, setEmerging] = useState([]);
  const [gaps, setGaps] = useState([]);
  const [reports, setReports] = useState([]);
  const [automation, setAutomation] = useState([]);
  const [gadsConfig, setGadsConfig] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    const [gs, bp, ek, cg, rp, al, ga] = await Promise.all([
      apiCall(() => api.get(`/sites/${siteId}/gsc/status`)),
      apiCall(() => api.get(`/sites/${siteId}/blog-posts`)),
      apiCall(() => api.get(`/sites/${siteId}/seo/emerging-keywords?limit=10`)),
      apiCall(() => api.get(`/sites/${siteId}/seo/content-gaps?limit=5`)),
      apiCall(() => api.get(`/sites/${siteId}/seo/weekly-reports?limit=4`)),
      apiCall(() => api.get(`/sites/${siteId}/seo/automation-log?limit=10`)),
      apiCall(() => api.get(`/sites/${siteId}/google-ads/config`)),
    ]);
    if (!gs.error) setGscStatus(gs.data);
    if (!bp.error) {
      const arr = Array.isArray(bp.data) ? bp.data : (bp.data?.posts || []);
      setBlog(arr.slice(0, 5));
    }
    if (!ek.error) setEmerging(ek.data?.keywords || []);
    if (!cg.error) setGaps(cg.data?.gaps || []);
    if (!rp.error) setReports(rp.data?.reports || []);
    if (!al.error) setAutomation(al.data?.events || []);
    if (!ga.error) setGadsConfig(ga.data);
    setLoading(false);
  }, [siteId]);

  const loadGscMetrics = useCallback(async () => {
    const { data, error } = await apiCall(() => api.get(`/sites/${siteId}/gsc/metrics?days=28&limit=20`));
    if (!error) setGscMetrics(data);
  }, [siteId]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    if (gscStatus?.connected) loadGscMetrics();
  }, [gscStatus, loadGscMetrics]);

  const handleConnectGsc = async () => {
    const { data, error } = await apiCall(() => api.get(`/sites/${siteId}/gsc/connect`));
    if (error) return;
    const url = data?.auth_url || data?.url;
    if (url) window.location.href = url;
  };

  if (loading) {
    return (
      <div className="py-20 text-neutral-500 text-sm flex items-center justify-center gap-2">
        <CircleNotch size={16} className="animate-spin" /> Chargement SEO…
      </div>
    );
  }

  const gscConnected = !!gscStatus?.connected;
  const lastReport = reports[0];

  return (
    <div data-testid="seo-tab" className="space-y-6">
      {/* Statut stack SEO */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <MiniCard
          icon={gscConnected ? CheckCircle : Warning}
          label="Google Search Console"
          value={gscConnected ? "Connecté" : "À connecter"}
          sub={gscConnected ? (gscStatus?.property || "Propriété liée") : "Indispensable pour mesurer le SEO"}
          tone={gscConnected ? "ok" : "warn"}
          testId="seo-gsc-status"
        />
        <MiniCard
          icon={Target}
          label="IndexNow"
          value="Actif"
          sub="Ping auto Bing / Yandex à chaque publication"
          tone="ok"
          testId="seo-indexnow-status"
        />
        <MiniCard
          icon={Article}
          label="llms.txt / AEO"
          value="Généré"
          sub="Multi-langues, renouvelé à chaque build SEO"
          tone="ok"
          testId="seo-aeo-status"
        />
      </div>

      {/* Rapport SEO hebdo (Phase 6) */}
      {lastReport && (
        <div className="bg-gradient-to-br from-neutral-50 to-white rounded-xl border border-neutral-200 p-5" data-testid="seo-weekly-report">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-semibold text-neutral-900 flex items-center gap-2">
                <ChartBar size={14} weight="duotone" /> Rapport SEO de la semaine
              </h3>
              <p className="text-[11px] text-neutral-500">
                {new Date(lastReport.period_start).toLocaleDateString("fr-FR")} → {new Date(lastReport.period_end).toLocaleDateString("fr-FR")}
              </p>
            </div>
            <span className="text-[10px] uppercase tracking-widest text-neutral-400">Automatique</span>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div className="bg-white rounded-lg border border-neutral-200 p-3">
              <div className="text-[10px] uppercase tracking-wider text-neutral-500">Articles publiés</div>
              <div className="text-xl font-semibold text-neutral-900 tabular-nums">{lastReport.articles_published}</div>
            </div>
            <div className="bg-white rounded-lg border border-neutral-200 p-3">
              <div className="text-[10px] uppercase tracking-wider text-neutral-500">Kw émergents</div>
              <div className="text-xl font-semibold text-neutral-900 tabular-nums">{lastReport.emerging_keywords_detected}</div>
            </div>
            <div className="bg-white rounded-lg border border-neutral-200 p-3">
              <div className="text-[10px] uppercase tracking-wider text-neutral-500">Gaps ouverts</div>
              <div className="text-xl font-semibold text-neutral-900 tabular-nums">{lastReport.content_gaps_open}</div>
            </div>
            <div className="bg-white rounded-lg border border-neutral-200 p-3">
              <div className="text-[10px] uppercase tracking-wider text-neutral-500">Événements auto</div>
              <div className="text-xl font-semibold text-neutral-900 tabular-nums">{lastReport.automation_events}</div>
            </div>
          </div>
        </div>
      )}

      {/* Emerging keywords + Content gaps (2 colonnes) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Mots-clés émergents */}
        <div className="bg-white rounded-xl border border-neutral-200 overflow-hidden" data-testid="seo-emerging-keywords">
          <div className="p-5 border-b border-neutral-100">
            <h3 className="text-sm font-semibold text-neutral-900 flex items-center gap-2">
              <Sparkle size={14} weight="duotone" /> Mots-clés émergents
            </h3>
            <p className="text-[11px] text-neutral-500">Détectés chaque lundi (cron SEO auto)</p>
          </div>
          {emerging.length === 0 ? (
            <div className="py-8 px-5 text-center text-sm text-neutral-500" data-testid="seo-emerging-empty">
              Aucun mot-clé émergent détecté pour l'instant.
            </div>
          ) : (
            <ul className="divide-y divide-neutral-100 max-h-80 overflow-y-auto">
              {emerging.map((k) => (
                <li key={k.id} className="py-2.5 px-5 flex items-center justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <div className="text-sm text-neutral-900 truncate flex items-center gap-2">
                      {k.status === "new" && <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-500" />}
                      {k.keyword}
                    </div>
                    <div className="text-[11px] text-neutral-500">
                      ~{k.est_volume}/mois · {k.country} · {timeAgo(k.detected_at)}
                    </div>
                  </div>
                  <TrendBadge trend={k.trend} />
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Content gaps */}
        <div className="bg-white rounded-xl border border-neutral-200 overflow-hidden" data-testid="seo-content-gaps">
          <div className="p-5 border-b border-neutral-100">
            <h3 className="text-sm font-semibold text-neutral-900 flex items-center gap-2">
              <TrendUp size={14} weight="duotone" /> Content gaps à combler
            </h3>
            <p className="text-[11px] text-neutral-500">Sujets traités par les concurrents et pas par toi</p>
          </div>
          {gaps.length === 0 ? (
            <div className="py-8 px-5 text-center text-sm text-neutral-500" data-testid="seo-gaps-empty">
              Aucun gap détecté. Relance l'analyse le 15 du mois (cron auto).
            </div>
          ) : (
            <ul className="divide-y divide-neutral-100 max-h-80 overflow-y-auto">
              {gaps.map((g) => (
                <li key={g.id} className="py-2.5 px-5 flex items-center justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <div className="text-sm text-neutral-900 truncate">{g.topic}</div>
                    <div className="text-[11px] text-neutral-500">
                      {g.potential_traffic === "high" ? "🔥 " : ""}Trafic potentiel : {g.potential_traffic} · {g.country}
                    </div>
                  </div>
                  <button
                    onClick={() => navigate(`/sites/${siteId}/blog-posts?topic=${encodeURIComponent(g.topic)}`)}
                    className="inline-flex items-center gap-1 h-7 px-2.5 rounded-md border border-neutral-200 hover:bg-neutral-50 text-[11px] font-medium text-neutral-700 transition flex-shrink-0"
                  >
                    Publier
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {/* GSC metrics */}
      <div className="bg-white rounded-xl border border-neutral-200 overflow-hidden">
        <div className="p-5 border-b border-neutral-100 flex items-center justify-between">
          <div>
            <h3 className="text-sm font-semibold text-neutral-900 flex items-center gap-2">
              <MagnifyingGlass size={14} /> Top requêtes Google (28j)
            </h3>
            <p className="text-[11px] text-neutral-500">Mots-clés qui génèrent des impressions sur ton site</p>
          </div>
          {!gscConnected && (
            <button
              onClick={handleConnectGsc}
              className="inline-flex items-center gap-2 h-9 px-4 rounded-lg bg-neutral-900 hover:bg-neutral-800 text-white text-sm font-medium transition"
              data-testid="seo-connect-gsc"
            >
              Connecter GSC
            </button>
          )}
        </div>

        {!gscConnected ? (
          <div className="py-10 px-6 text-center text-sm text-neutral-500" data-testid="seo-gsc-empty">
            Connecte Google Search Console pour voir tes requêtes, impressions, clics et positions.
          </div>
        ) : !gscMetrics || (gscMetrics.queries?.length || 0) === 0 ? (
          <div className="py-10 px-6 text-center text-sm text-neutral-500">
            Pas encore de données remontées par GSC (généralement 48h après le 1<sup>er</sup> crawl).
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-[11px] uppercase tracking-widest text-neutral-500 bg-neutral-50 text-left">
                  <th className="py-3 px-4 font-medium">Requête</th>
                  <th className="py-3 px-4 text-right font-medium">Impressions</th>
                  <th className="py-3 px-4 text-right font-medium">Clics</th>
                  <th className="py-3 px-4 text-right font-medium">CTR</th>
                  <th className="py-3 px-4 text-right font-medium">Position</th>
                </tr>
              </thead>
              <tbody>
                {(gscMetrics.queries || []).map((q, i) => (
                  <tr key={`${q.keyword}-${i}`} className="border-t border-neutral-100">
                    <td className="py-3 px-4 text-neutral-900">{q.keyword || q.query}</td>
                    <td className="py-3 px-4 text-right tabular-nums"><Eye size={12} className="inline mr-1 opacity-50" />{q.impressions ?? "—"}</td>
                    <td className="py-3 px-4 text-right tabular-nums"><Cursor size={12} className="inline mr-1 opacity-50" />{q.clicks ?? "—"}</td>
                    <td className="py-3 px-4 text-right tabular-nums text-neutral-600">{q.ctr != null ? `${(q.ctr * 100).toFixed(1)}%` : "—"}</td>
                    <td className="py-3 px-4 text-right tabular-nums text-neutral-600">{q.position != null ? q.position.toFixed(1) : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Derniers articles blog */}
      <div className="bg-white rounded-xl border border-neutral-200 overflow-hidden">
        <div className="p-5 border-b border-neutral-100 flex items-center justify-between">
          <div>
            <h3 className="text-sm font-semibold text-neutral-900 flex items-center gap-2">
              <Article size={14} /> Derniers articles publiés
            </h3>
            <p className="text-[11px] text-neutral-500">Blog auto 3×/semaine · traductions 6 langues</p>
          </div>
          <button
            onClick={() => navigate(`/sites/${siteId}/blog-posts`)}
            className="inline-flex items-center gap-2 h-9 px-4 rounded-lg border border-neutral-200 hover:bg-neutral-50 text-sm font-medium text-neutral-700 transition"
            data-testid="seo-publish-article"
          >
            Publier un article
          </button>
        </div>
        {blog.length === 0 ? (
          <div className="py-10 px-6 text-center text-sm text-neutral-500" data-testid="seo-blog-empty">
            Aucun article publié pour le moment.
          </div>
        ) : (
          <ul className="divide-y divide-neutral-100">
            {blog.map((p) => {
              const dt = p.published_at || p.created_at;
              const title = (typeof p.title === "object") ? (p.title.fr || p.title.en || Object.values(p.title)[0]) : p.title;
              const langs = p.translated_langs || Object.keys(p.title || {});
              return (
                <li key={p.id || p.slug} className="py-3 px-5 flex items-center justify-between gap-4">
                  <div className="min-w-0">
                    <div className="text-sm font-medium text-neutral-900 truncate">{title}</div>
                    <div className="text-[11px] text-neutral-500">
                      {dt ? new Date(dt).toLocaleDateString("fr-FR") : "brouillon"}
                      {langs && langs.length > 0 ? ` · ${langs.length} langue${langs.length > 1 ? "s" : ""} (${langs.join(", ")})` : ""}
                      {p.source === "cron_blog_auto" && <span className="ml-2 inline-block px-1.5 py-0.5 rounded bg-violet-50 text-violet-700 text-[9px] uppercase tracking-wider">Auto</span>}
                    </div>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </div>

      {/* Campagnes Google Ads — Phase 7 */}
      <div className="bg-white rounded-xl border border-neutral-200 overflow-hidden" data-testid="seo-gads-block">
        <div className="p-5 border-b border-neutral-100 flex items-center justify-between">
          <div>
            <h3 className="text-sm font-semibold text-neutral-900 flex items-center gap-2">
              <MegaphoneSimple size={14} weight="duotone" /> Campagnes Google Ads
            </h3>
            <p className="text-[11px] text-neutral-500">Pixel natif + export assets pour campagne manuelle</p>
          </div>
          {isAdmin ? (
            <button
              onClick={() => navigate(`/admin/sites/${siteId}/google-ads`)}
              className="inline-flex items-center gap-2 h-9 px-4 rounded-lg bg-neutral-900 hover:bg-neutral-800 text-white text-sm font-medium transition"
              data-testid="seo-gads-manage"
            >
              Gérer dans l'admin
            </button>
          ) : (
            <span className="text-[11px] text-neutral-400">Admin-only</span>
          )}
        </div>
        <div className="px-5 py-4 flex items-center justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-2 text-sm">
            {gadsConfig?.enabled && gadsConfig?.conversion_id ? (
              <>
                <CheckCircle size={16} weight="fill" className="text-emerald-600" />
                <span className="text-neutral-900">
                  Pixel actif — conversions trackées
                  {gadsConfig.updated_at && (
                    <span className="text-neutral-500"> depuis le {new Date(gadsConfig.updated_at).toLocaleDateString("fr-FR")}</span>
                  )}
                </span>
              </>
            ) : (
              <>
                <Warning size={16} weight="duotone" className="text-amber-500" />
                <span className="text-neutral-700">
                  Pixel désactivé — {isAdmin ? "configure-le depuis l'admin" : "à configurer par l'admin"}
                </span>
              </>
            )}
          </div>
          {isAdmin && (
            <span className="text-[11px] text-neutral-500">
              CTA : <strong>Générer un export</strong> dans l'admin
            </span>
          )}
        </div>
      </div>

      {/* Historique automatisations */}
      <div className="bg-white rounded-xl border border-neutral-200 overflow-hidden" data-testid="seo-automation-log">
        <div className="p-5 border-b border-neutral-100">
          <h3 className="text-sm font-semibold text-neutral-900 flex items-center gap-2">
            <ClockClockwise size={14} weight="duotone" /> Historique des automatisations
          </h3>
          <p className="text-[11px] text-neutral-500">10 derniers événements crons SEO/AEO sur ce site</p>
        </div>
        {automation.length === 0 ? (
          <div className="py-8 px-5 text-center text-sm text-neutral-500">
            Aucune automatisation encore exécutée pour ce site.
          </div>
        ) : (
          <ul className="divide-y divide-neutral-100">
            {automation.map((e) => (
              <li key={e.id} className="py-2.5 px-5 flex items-center gap-3">
                <Lightning size={13} className="text-violet-500 flex-shrink-0" weight="fill" />
                <div className="min-w-0 flex-1">
                  <div className="text-sm text-neutral-800 truncate">
                    <span className="font-medium">{CRON_LABELS[e.cron] || e.cron}</span>
                    <span className="text-neutral-500"> — {e.summary}</span>
                  </div>
                  <div className="text-[11px] text-neutral-500">{timeAgo(e.created_at)}</div>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
