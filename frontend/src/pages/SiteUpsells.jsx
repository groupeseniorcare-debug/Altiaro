import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { ArrowLeft, Stack, Sparkle, ArrowClockwise, MagnifyingGlass } from "@phosphor-icons/react";
import { api, apiCall } from "../lib/api";

const MARGIN_META = {
  high:   { label: "Marge forte", color: "bg-emerald-100 text-emerald-800" },
  medium: { label: "Marge correcte", color: "bg-sky-100 text-sky-800" },
  low:    { label: "Marge faible", color: "bg-neutral-100 text-neutral-700" },
};

export default function SiteUpsells() {
  const { id: siteId } = useParams();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    apiCall(() => api.get(`/sites/${siteId}/upsell-recommendations`)).then(({ data }) => {
      if (data && data.generated_at) setData(data);
    });
  }, [siteId]);

  const run = async () => {
    setLoading(true);
    const { data, error } = await apiCall(() => api.post(`/sites/${siteId}/upsell-recommendations`, { site_id: siteId }));
    setLoading(false);
    if (error) { window.alert(error); return; }
    setData(data);
  };

  return (
    <div className="min-h-screen bg-[#FAF7F2]">
      <div className="max-w-5xl mx-auto px-6 md:px-10 py-8">
        <Link to={`/sites/${siteId}`} className="inline-flex items-center gap-2 text-sm text-neutral-600 hover:text-neutral-900 mb-6">
          <ArrowLeft size={14} /> Retour au cockpit
        </Link>

        <div className="mb-8">
          <div className="text-[11px] uppercase tracking-[0.2em] text-neutral-500 mb-2 flex items-center gap-2">
            <Stack size={12} weight="bold" /> Étape 3 · Upsells &amp; accessoires recommandés
          </div>
          <h1 className="text-3xl md:text-4xl font-semibold text-neutral-900" style={{ fontFamily: "'Fraunces', serif" }}>
            Augmente ton panier moyen
          </h1>
          <p className="text-sm text-neutral-500 mt-2 max-w-2xl">
            Claude analyse ton catalogue et te suggère 6 à 10 accessoires complémentaires. Chaque recommandation te donne un mot-clé prêt-à-l'emploi à rechercher sur AliExpress.
          </p>
        </div>

        <div className="flex justify-end mb-5">
          <button
            onClick={run}
            disabled={loading}
            data-testid="upsells-run"
            className="h-11 px-5 rounded-xl bg-neutral-900 hover:bg-neutral-800 text-white text-sm font-medium flex items-center gap-2 disabled:opacity-60"
          >
            {loading ? <ArrowClockwise size={14} className="animate-spin" /> : <Sparkle size={14} weight="fill" />}
            {loading ? "Analyse IA…" : (data ? "Régénérer" : "Générer les recommandations IA")}
          </button>
        </div>

        {data?.upsells?.length > 0 ? (
          <div className="grid md:grid-cols-2 gap-4" data-testid="upsells-list">
            {data.upsells.map((u, i) => {
              const m = MARGIN_META[u.margin_impact] || MARGIN_META.medium;
              const aliUrl = `/sites/${siteId}/aliexpress/import?q=${encodeURIComponent(u.keyword_ali)}`;
              return (
                <div key={i} className="bg-white border border-neutral-200 rounded-2xl p-5" data-testid={`upsell-${i}`}>
                  <div className="flex items-start justify-between gap-3 mb-3">
                    <div className="min-w-0">
                      <div className="font-semibold text-neutral-900">{u.label_fr}</div>
                      <div className="text-xs text-neutral-500 mt-0.5">À coupler avec : <strong>{u.pairs_with}</strong></div>
                    </div>
                    <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full whitespace-nowrap ${m.color}`}>{m.label}</span>
                  </div>

                  <div className="bg-[#FDFBF7] border border-neutral-100 rounded-xl p-3 mb-3">
                    <div className="text-[10px] uppercase tracking-widest text-neutral-500 mb-1">Recherche AliExpress</div>
                    <div className="font-mono text-sm text-neutral-900">{u.keyword_ali}</div>
                  </div>

                  <div className="text-xs text-neutral-600 leading-relaxed mb-3">{u.rationale}</div>

                  <div className="flex items-center justify-between gap-2">
                    <div className="text-sm">
                      <span className="text-neutral-500">Prix cible : </span>
                      <span className="font-semibold text-neutral-900">{u.target_price_eur}€</span>
                    </div>
                    <Link
                      to={aliUrl}
                      data-testid={`upsell-search-${i}`}
                      className="h-9 px-3 rounded-lg bg-neutral-900 hover:bg-neutral-800 text-white text-xs font-medium flex items-center gap-1.5"
                    >
                      <MagnifyingGlass size={12} weight="bold" /> Chercher sur AliExpress
                    </Link>
                  </div>
                </div>
              );
            })}
          </div>
        ) : !loading ? (
          <div className="bg-white border border-neutral-200 rounded-2xl p-10 text-center">
            <Stack size={36} weight="duotone" className="mx-auto text-neutral-400 mb-3" />
            <div className="font-medium text-neutral-900 mb-1">Aucune recommandation encore</div>
            <div className="text-sm text-neutral-500">Importe au moins 3 produits principaux, puis clique sur « Générer les recommandations IA ».</div>
          </div>
        ) : null}

        {data?.generated_at && (
          <div className="text-[11px] text-neutral-400 text-right mt-5">
            Généré le {new Date(data.generated_at).toLocaleString("fr-FR")}
          </div>
        )}
      </div>
    </div>
  );
}
