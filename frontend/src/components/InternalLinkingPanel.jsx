import React, { useEffect, useState } from "react";
import { api, apiCall } from "../lib/api";
import { LinkSimple, ArrowRight, Warning } from "@phosphor-icons/react";

/**
 * Internal Linking panel — injection automatique de liens markdown internes
 * dans les articles de blog + descriptions produits. 100 % déterministe.
 */
export default function InternalLinkingPanel({ siteId }) {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [lastRun, setLastRun] = useState(null);

  const load = async () => {
    const { data } = await apiCall(() =>
      api.get(`/sites/${siteId}/internal-linking/stats`)
    );
    setStats(data || null);
    if (data?.last_run_stats) setLastRun(data.last_run_stats);
    setLoading(false);
  };

  useEffect(() => { load(); }, [siteId]);

  const runInject = async () => {
    if (!window.confirm(
      "Injecter automatiquement les liens internes ?\n\n" +
      "• Scanne les articles de blog et les fiches produits\n" +
      "• Ajoute jusqu'à 6 liens par article / 3 par produit\n" +
      "• Zéro coût LLM · ~2-3 s\n" +
      "• Opération réversible (les anciens liens restent)"
    )) return;
    setBusy(true);
    const { data: res, error, rawDetail } = await apiCall(() =>
      api.post(`/sites/${siteId}/internal-linking/auto-inject`, {
        max_links_per_post: 6,
        max_links_per_product: 3,
        dry_run: false,
      })
    );
    setBusy(false);
    if (error) {
      window.alert(rawDetail?.detail || error);
      return;
    }
    setLastRun(res);
    load();
  };

  if (loading || !stats) return null;

  return (
    <div
      data-testid="internal-linking-panel"
      className="p-6 md:p-7"
      style={{ borderTop: "1px solid #E5E5E5" }}
    >
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_1.4fr] gap-10">
        {/* Left — stats + CTA */}
        <div>
          <div className="flex items-center gap-3 mb-3">
            <span className="h-px w-8 bg-neutral-900" />
            <span className="text-[10px] uppercase tracking-[0.35em] text-neutral-900 font-medium">
              Maillage interne
            </span>
          </div>
          <div className="flex items-baseline gap-3">
            <div
              className="text-[52px] leading-none text-neutral-900 tabular-nums"
              style={{ fontFamily: "'Fraunces', Georgia, serif" }}
            >
              {stats.total_outgoing_internal_links || 0}
            </div>
            <div className="text-[12px] text-neutral-500">
              lien{(stats.total_outgoing_internal_links || 0) > 1 ? "s" : ""} internes détectés
            </div>
          </div>
          <p className="text-[13px] text-neutral-600 mt-3 leading-[1.55] max-w-sm">
            Le maillage interne est le signal #1 de Google et de SGE : il
            redistribue l'autorité, augmente la couverture crawl, et guide
            les moteurs IA vers les bonnes pages à citer.
          </p>

          <div className="mt-4 flex gap-4 text-[11.5px] text-neutral-500">
            <span><b className="text-neutral-900 tabular-nums">{stats.total_documents_scanned}</b> docs scannés</span>
            <span>·</span>
            <span><b className="text-neutral-900 tabular-nums">{stats.average_links_per_document}</b> liens / doc</span>
            <span>·</span>
            <span><b className="text-neutral-900 tabular-nums">{stats.unique_targets}</b> cibles uniques</span>
          </div>

          <button
            onClick={runInject}
            disabled={busy}
            data-testid="internal-linking-run"
            className="mt-6 h-11 px-5 bg-neutral-900 hover:bg-black disabled:opacity-60 text-white text-[12.5px] font-semibold flex items-center gap-2 transition"
            style={{ borderRadius: "2px" }}
          >
            <LinkSimple size={14} weight="bold" className={busy ? "animate-pulse" : ""} />
            {busy ? "Injection en cours…" : "Injecter le maillage interne"}
            {!busy && <ArrowRight size={13} weight="bold" />}
          </button>

          {lastRun && (
            <div className="mt-3 text-[11.5px] text-emerald-700 font-medium" data-testid="internal-linking-last-run">
              ✓ Dernier run : {lastRun.total_links_added || 0} lien(s) ajouté(s) ·{" "}
              {lastRun.blog_posts_updated || 0} article(s) · {lastRun.products_updated || 0} produit(s)
            </div>
          )}
        </div>

        {/* Right — orphans + top targets */}
        <div>
          <div className="text-[10px] uppercase tracking-[0.35em] text-neutral-500 mb-4">
            Pages orphelines ({stats.orphan_count})
          </div>
          {stats.orphan_count > 0 ? (
            <ul className="space-y-2 mb-6" data-testid="internal-linking-orphans">
              {stats.orphan_pages.slice(0, 5).map((o) => (
                <li key={o.url} className="flex items-start gap-3 text-[12.5px]">
                  <Warning size={14} weight="regular" className="text-amber-600 shrink-0 mt-[3px]" />
                  <div className="min-w-0 flex-1">
                    <div className="text-neutral-900 truncate">{o.keyword}</div>
                    <div className="text-[10.5px] text-neutral-400 uppercase tracking-wider mt-0.5">
                      {o.type} · {o.url}
                    </div>
                  </div>
                </li>
              ))}
              {stats.orphan_count > 5 && (
                <li className="text-[11px] text-neutral-400 pl-6">
                  + {stats.orphan_count - 5} autre{stats.orphan_count - 5 > 1 ? "s" : ""}
                </li>
              )}
            </ul>
          ) : (
            <div className="text-[12.5px] text-emerald-700 mb-6 flex items-center gap-2">
              <span className="inline-block w-2 h-2 rounded-full bg-emerald-600" /> Aucune page orpheline détectée.
            </div>
          )}

          {(stats.most_linked || []).length > 0 && (
            <>
              <div className="text-[10px] uppercase tracking-[0.35em] text-neutral-500 mb-3">
                Pages les plus citées
              </div>
              <ul className="space-y-1.5">
                {stats.most_linked.slice(0, 5).map((m) => (
                  <li key={m.url} className="flex items-center justify-between text-[12px] py-1">
                    <span className="text-neutral-700 truncate pr-3">{m.url}</span>
                    <span
                      className="text-[11px] font-semibold tabular-nums text-neutral-900 px-2 py-0.5"
                      style={{ background: "#F5F5F5", borderRadius: "2px" }}
                    >
                      {m.count}
                    </span>
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
