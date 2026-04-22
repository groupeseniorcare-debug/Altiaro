import React, { useEffect, useRef, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { ArrowLeft, Stack, Sparkle, ArrowClockwise, MagnifyingGlass } from "@phosphor-icons/react";
import { api, apiCall } from "../lib/api";
import SourcingPanel from "../components/SourcingPanel";

const MARGIN_META = {
  high:   { label: "Marge forte", color: "bg-emerald-100 text-emerald-800" },
  medium: { label: "Marge correcte", color: "bg-sky-100 text-sky-800" },
  low:    { label: "Marge faible", color: "bg-neutral-100 text-neutral-700" },
};

export default function SiteUpsells() {
  const { id: siteId } = useParams();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const panelRef = useRef(null);

  useEffect(() => {
    apiCall(() => api.get(`/sites/${siteId}/upsell-recommendations`)).then(({ data }) => {
      if (data && data.generated_at) setData(data);
    });
  }, [siteId]);

  const run = async () => {
    setLoading(true);
    const { data: res, error } = await apiCall(() =>
      api.post(`/sites/${siteId}/upsell-recommendations`, { site_id: siteId })
    );
    setLoading(false);
    if (error) { window.alert(error); return; }
    setData(res);
  };

  const pickSuggestion = (kw) => {
    panelRef.current?.prefillAndSearch(kw);
  };

  return (
    <div className="min-h-screen bg-[#FAF7F2]">
      <div className="max-w-6xl mx-auto px-6 md:px-10 py-8">
        <Link
          to={`/sites/${siteId}`}
          className="inline-flex items-center gap-2 text-sm text-neutral-600 hover:text-neutral-900 mb-6"
          data-testid="back-to-site"
        >
          <ArrowLeft size={14} /> Retour au cockpit
        </Link>

        <div className="mb-8">
          <div className="text-[11px] uppercase tracking-[0.2em] text-neutral-500 mb-2 flex items-center gap-2">
            <Stack size={12} weight="bold" /> Étape 3 · Upsells &amp; accessoires
          </div>
          <h1 className="text-3xl md:text-4xl font-semibold text-neutral-900" style={{ fontFamily: "'Fraunces', serif" }}>
            Augmente ton panier moyen
          </h1>
          <p className="text-sm text-neutral-500 mt-2 max-w-2xl">
            Claude analyse ton catalogue importé à l'étape 2 et te suggère des accessoires complémentaires.
            Clique sur une suggestion pour lancer la recherche CJ / AliExpress, ou importe directement par URL ci-dessous.
          </p>
        </div>

        {/* IA recommendations bar */}
        <div className="bg-white border border-neutral-200 rounded-2xl p-5 mb-6">
          <div className="flex items-start justify-between gap-4 flex-wrap mb-4">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-indigo-100 flex items-center justify-center">
                <Sparkle size={14} weight="fill" className="text-indigo-700" />
              </div>
              <div>
                <div className="text-sm font-semibold text-neutral-900">
                  Recommandations IA basées sur ton catalogue
                </div>
                <div className="text-xs text-neutral-500">
                  {data?.upsells?.length
                    ? `${data.upsells.length} suggestions · généré le ${new Date(data.generated_at).toLocaleString("fr-FR")}`
                    : "L'IA suggère 6 à 10 accessoires complémentaires à partir de tes produits déjà importés."}
                </div>
              </div>
            </div>
            <button
              onClick={run}
              disabled={loading}
              data-testid="upsells-run"
              className="h-10 px-4 rounded-lg bg-neutral-900 hover:bg-neutral-800 text-white text-xs font-medium flex items-center gap-2 disabled:opacity-60"
            >
              {loading ? <ArrowClockwise size={14} className="animate-spin" /> : <Sparkle size={14} weight="fill" />}
              {loading ? "Analyse IA…" : (data ? "Régénérer" : "Générer les suggestions IA")}
            </button>
          </div>

          {data?.upsells?.length > 0 ? (
            <div className="grid md:grid-cols-2 gap-3" data-testid="upsells-list">
              {data.upsells.map((u, i) => {
                const m = MARGIN_META[u.margin_impact] || MARGIN_META.medium;
                return (
                  <button
                    key={i}
                    onClick={() => pickSuggestion(u.keyword_ali)}
                    data-testid={`upsell-${i}`}
                    className="group text-left bg-[#FDFBF7] hover:bg-white border border-neutral-200 hover:border-neutral-900 rounded-xl p-4 transition"
                  >
                    <div className="flex items-start justify-between gap-2 mb-2">
                      <div className="min-w-0">
                        <div className="text-sm font-semibold text-neutral-900 line-clamp-1">{u.label_fr}</div>
                        <div className="text-[11px] text-neutral-500 mt-0.5">
                          À coupler avec : <strong>{u.pairs_with}</strong> · Cible <strong>{u.target_price_eur}€</strong>
                        </div>
                      </div>
                      <span className={`shrink-0 text-[10px] font-medium px-2 py-0.5 rounded-full whitespace-nowrap ${m.color}`}>
                        {m.label}
                      </span>
                    </div>
                    <div className="text-[11px] text-neutral-600 leading-relaxed mb-3 line-clamp-2">{u.rationale}</div>
                    <div className="flex items-center justify-between">
                      <div className="font-mono text-[11px] text-neutral-500 truncate">
                        {u.keyword_ali}
                      </div>
                      <div
                        data-testid={`upsell-search-${i}`}
                        className="text-[11px] font-medium text-neutral-900 flex items-center gap-1 group-hover:underline"
                      >
                        <MagnifyingGlass size={11} weight="bold" /> Chercher
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          ) : !loading ? (
            <div className="text-center py-6 text-sm text-neutral-500">
              Importe au moins 3 produits principaux à l'étape 2, puis clique sur « Générer les suggestions IA ».
            </div>
          ) : null}
        </div>

        {/* Same sourcing engine as Étape 2, but tagged as upsell */}
        <SourcingPanel
          ref={panelRef}
          siteId={siteId}
          context="upsell"
          emptyHint={{
            title: "Importe tes upsells",
            body: "Clique sur une suggestion IA au-dessus, cherche manuellement, ou colle un lien CJ / AliExpress. Les produits importés ici seront marqués comme upsells.",
          }}
        />
      </div>
    </div>
  );
}
