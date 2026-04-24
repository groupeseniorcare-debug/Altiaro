import React, { useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import {
  MagnifyingGlass, CircleNotch, CheckCircle, Warning, Article, Cursor, Eye, Target,
} from "@phosphor-icons/react";
import { api, apiCall } from "../../lib/api";

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

export default function SeoTab({ siteId }) {
  const navigate = useNavigate();
  const [gscStatus, setGscStatus] = useState(null);
  const [gscMetrics, setGscMetrics] = useState(null);
  const [blog, setBlog] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    const [gs, bp] = await Promise.all([
      apiCall(() => api.get(`/sites/${siteId}/gsc/status`)),
      apiCall(() => api.get(`/sites/${siteId}/blog-posts`)),
    ]);
    if (!gs.error) setGscStatus(gs.data);
    if (!bp.error) {
      const arr = Array.isArray(bp.data) ? bp.data : (bp.data?.posts || []);
      setBlog(arr.slice(0, 5));
    }
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

      {/* GSC metrics ou CTA connexion */}
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
            <p className="text-[11px] text-neutral-500">Cluster SEO mensuel · traductions 6 langues</p>
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
                    </div>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
}
