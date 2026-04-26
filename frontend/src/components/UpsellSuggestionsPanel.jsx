import React, { useEffect, useState, useCallback } from "react";
import { Sparkle, ArrowSquareOut, CheckCircle, X as XIcon, MagnifyingGlass, Tag, Lightbulb } from "@phosphor-icons/react";
import { toast } from "sonner";
import { api, apiCall } from "../lib/api";

/**
 * UpsellSuggestionsPanel — section "Suggestions IA" sur la page Upsells.
 *
 * Backend : POST /api/sites/:id/upsells/suggest         → génère 8-10 idées
 *           GET  /api/sites/:id/upsells/suggestions     → liste
 *           PATCH .../suggestions/:id                   → adopt | ignore
 *
 * Cards en grid 3 col desktop, 1 mobile.
 * Tabs : Toutes / Suggérées / Adoptées / Ignorées
 */

const CATEGORY_META = {
  accessoire: { label: "Accessoire", cls: "bg-amber-50  text-amber-800  border-amber-200" },
  garantie:   { label: "Garantie",   cls: "bg-emerald-50 text-emerald-800 border-emerald-200" },
  service:    { label: "Service",    cls: "bg-sky-50    text-sky-800    border-sky-200" },
  bundle:     { label: "Bundle",     cls: "bg-violet-50 text-violet-800 border-violet-200" },
};

const TABS = [
  { key: "all",       label: "Toutes" },
  { key: "suggested", label: "À évaluer" },
  { key: "adopted",   label: "Adoptées" },
  { key: "ignored",   label: "Ignorées" },
];

function aeSearchUrl(kw)  { return `https://fr.aliexpress.com/wholesale?SearchText=${encodeURIComponent(kw)}`; }
function cjSearchUrl(kw)  { return `https://www.cjdropshipping.com/list/search?searchKey=${encodeURIComponent(kw)}`; }

export default function UpsellSuggestionsPanel({ siteId, productsCount = 0 }) {
  const [items, setItems] = useState([]);
  const [counts, setCounts] = useState({ suggested: 0, adopted: 0, ignored: 0 });
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [tab, setTab] = useState("suggested");

  const load = useCallback(async () => {
    setLoading(true);
    const status = tab === "all" ? null : tab;
    const url = status
      ? `/sites/${siteId}/upsells/suggestions?status=${status}`
      : `/sites/${siteId}/upsells/suggestions`;
    const { data } = await apiCall(() => api.get(url));
    setItems(data?.items || []);
    setCounts(data?.counts || { suggested: 0, adopted: 0, ignored: 0 });
    setLoading(false);
  }, [siteId, tab]);

  useEffect(() => { if (siteId) load(); }, [siteId, load]);

  const handleGenerate = async () => {
    if (productsCount === 0) {
      toast.error("Aucun produit dans le catalogue", {
        description: "Importe d'abord des produits à l'étape 2 avant de générer des upsells.",
      });
      return;
    }
    setGenerating(true);
    const { data, error } = await apiCall(
      () => api.post(`/sites/${siteId}/upsells/suggest`),
      { timeout: 180000 }
    );
    setGenerating(false);
    if (error) {
      toast.error("Génération impossible", { description: error });
      return;
    }
    const n = data?.count || 0;
    toast.success(`${n} suggestion${n > 1 ? "s" : ""} générée${n > 1 ? "s" : ""} ✨`, {
      description: "Examine-les et adopte celles qui te plaisent.",
    });
    setTab("suggested");
    await load();
  };

  const handleStatusChange = async (id, newStatus) => {
    const prev = items;
    setItems((it) => it.map((x) => (x.id === id ? { ...x, status: newStatus } : x)));
    const { error } = await apiCall(() =>
      api.patch(`/sites/${siteId}/upsells/suggestions/${id}`, { status: newStatus })
    );
    if (error) {
      setItems(prev);
      toast.error("Mise à jour échouée", { description: error });
      return;
    }
    toast.success(newStatus === "adopted" ? "Adoptée ✓" : newStatus === "ignored" ? "Ignorée" : "Mise à jour");
    // Refresh counts
    const { data } = await apiCall(() => api.get(`/sites/${siteId}/upsells/suggestions`));
    setCounts(data?.counts || counts);
  };

  return (
    <section className="bg-white border border-neutral-200 rounded-2xl p-5 md:p-6" data-testid="upsell-suggestions-panel">
      <div className="flex items-start justify-between gap-4 flex-wrap mb-5">
        <div>
          <h2 className="text-base font-semibold text-neutral-900 flex items-center gap-2">
            <Lightbulb size={16} weight="duotone" className="text-amber-600" />
            Suggestions IA d'upsells
          </h2>
          <p className="text-xs text-neutral-500 mt-1 max-w-2xl">
            L'IA analyse ton catalogue et propose 8 à 10 upsells/accessoires pertinents pour augmenter le panier moyen.
            Tu décides quels les chercher, quels adopter, quels ignorer.
          </p>
        </div>
        <button
          onClick={handleGenerate}
          disabled={generating || productsCount === 0}
          data-testid="generate-upsell-suggestions"
          className="h-10 px-4 rounded-xl bg-neutral-900 hover:bg-neutral-800 text-white text-sm font-semibold inline-flex items-center gap-2 disabled:opacity-50 whitespace-nowrap"
        >
          <Sparkle size={14} weight={generating ? "regular" : "fill"} className={generating ? "animate-pulse" : ""} />
          {generating ? "Génération… (30-60 s)" : "Générer des suggestions"}
        </button>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-4 border-b border-neutral-200">
        {TABS.map((t) => {
          const cnt = t.key === "all"
            ? (counts.suggested + counts.adopted + counts.ignored)
            : (counts[t.key] || 0);
          return (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              data-testid={`upsell-tab-${t.key}`}
              className={`px-3 py-2 text-xs font-medium border-b-2 transition ${
                tab === t.key
                  ? "border-neutral-900 text-neutral-900"
                  : "border-transparent text-neutral-500 hover:text-neutral-900"
              }`}
            >
              {t.label} <span className="text-neutral-400">({cnt})</span>
            </button>
          );
        })}
      </div>

      {/* States */}
      {loading ? (
        <div className="text-sm text-neutral-500 py-8 text-center">Chargement…</div>
      ) : items.length === 0 ? (
        <EmptyState
          tab={tab}
          productsCount={productsCount}
          onGenerate={handleGenerate}
          generating={generating}
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4" data-testid="upsell-suggestions-grid">
          {items.map((it) => (
            <SuggestionCard key={it.id} suggestion={it} onChange={handleStatusChange} />
          ))}
        </div>
      )}
    </section>
  );
}

function EmptyState({ tab, productsCount, onGenerate, generating }) {
  if (productsCount === 0) {
    return (
      <div className="border-2 border-dashed border-neutral-200 rounded-xl p-8 text-center">
        <Tag size={28} weight="duotone" className="text-neutral-400 mx-auto mb-2" />
        <div className="text-sm font-medium text-neutral-900 mb-1">Catalogue vide</div>
        <div className="text-xs text-neutral-500 max-w-sm mx-auto">
          Importe d'abord des produits à l'étape 2 (Sourcing). L'IA s'appuie sur tes produits pour suggérer des upsells pertinents.
        </div>
      </div>
    );
  }
  if (tab === "all" || tab === "suggested") {
    return (
      <div className="border-2 border-dashed border-neutral-200 rounded-xl p-8 text-center">
        <Sparkle size={28} weight="duotone" className="text-neutral-400 mx-auto mb-2" />
        <div className="text-sm font-medium text-neutral-900 mb-1">
          Aucune suggestion encore.
        </div>
        <div className="text-xs text-neutral-500 max-w-md mx-auto mb-4">
          Clique sur « Générer des suggestions » pour obtenir 8-10 idées d'upsells basées sur ton catalogue actuel.
        </div>
        <button
          onClick={onGenerate}
          disabled={generating}
          className="h-9 px-4 rounded-lg bg-neutral-900 text-white text-xs font-semibold inline-flex items-center gap-1.5 disabled:opacity-50"
        >
          <Sparkle size={12} weight="fill" />
          {generating ? "Génération…" : "Générer maintenant"}
        </button>
      </div>
    );
  }
  return (
    <div className="border-2 border-dashed border-neutral-200 rounded-xl p-8 text-center">
      <div className="text-sm text-neutral-500">Aucune suggestion dans cet onglet pour l'instant.</div>
    </div>
  );
}

function SuggestionCard({ suggestion: s, onChange }) {
  const cat = CATEGORY_META[s.category] || CATEGORY_META.accessoire;
  const kwAE = s.search_keywords_aliexpress?.[0] || s.name;
  const kwCJ = s.search_keywords_cj?.[0] || s.name;
  const isAdopted = s.status === "adopted";
  const isIgnored = s.status === "ignored";

  return (
    <article
      className={`border rounded-xl p-4 flex flex-col gap-3 transition ${
        isAdopted
          ? "border-emerald-300 bg-emerald-50/40"
          : isIgnored
            ? "border-neutral-200 bg-neutral-50/60 opacity-70"
            : "border-neutral-200 bg-white hover:border-neutral-300"
      }`}
      data-testid={`upsell-suggestion-${s.id}`}
    >
      <header className="flex items-start gap-2">
        <span className={`inline-flex items-center text-[10px] font-medium px-2 py-0.5 rounded uppercase tracking-widest border ${cat.cls}`}>
          {cat.label}
        </span>
        {s.estimated_price_eur ? (
          <span className="ml-auto text-sm font-semibold text-neutral-900 tabular-nums">
            ~{s.estimated_price_eur}€
          </span>
        ) : null}
      </header>
      <h3 className="text-sm font-semibold text-neutral-900 leading-snug" title={s.name}>
        {s.name}
      </h3>
      {s.description && (
        <p className="text-xs text-neutral-600 leading-relaxed line-clamp-3">{s.description}</p>
      )}
      {s.rationale && (
        <p className="text-[11px] text-neutral-500 italic leading-relaxed border-l-2 border-neutral-200 pl-2 line-clamp-2">
          <strong className="not-italic text-neutral-700">Pourquoi :</strong> {s.rationale}
        </p>
      )}

      {/* Search buttons */}
      <div className="flex gap-1.5">
        <a
          href={aeSearchUrl(kwAE)}
          target="_blank"
          rel="noopener noreferrer"
          className="flex-1 h-8 px-2 rounded-lg bg-orange-50 hover:bg-orange-100 text-orange-800 text-[11px] font-medium inline-flex items-center justify-center gap-1 border border-orange-200"
          data-testid={`upsell-search-ae-${s.id}`}
          title={`Chercher "${kwAE}" sur AliExpress`}
        >
          <MagnifyingGlass size={12} weight="bold" /> AliExpress <ArrowSquareOut size={10} weight="bold" />
        </a>
        <a
          href={cjSearchUrl(kwCJ)}
          target="_blank"
          rel="noopener noreferrer"
          className="flex-1 h-8 px-2 rounded-lg bg-sky-50 hover:bg-sky-100 text-sky-800 text-[11px] font-medium inline-flex items-center justify-center gap-1 border border-sky-200"
          data-testid={`upsell-search-cj-${s.id}`}
          title={`Chercher "${kwCJ}" sur CJ Dropshipping`}
        >
          <MagnifyingGlass size={12} weight="bold" /> CJ <ArrowSquareOut size={10} weight="bold" />
        </a>
      </div>

      {/* Adopt / Ignore */}
      <footer className="flex gap-1.5 mt-auto pt-1">
        {!isAdopted && (
          <button
            onClick={() => onChange(s.id, "adopted")}
            data-testid={`upsell-adopt-${s.id}`}
            className="flex-1 h-8 px-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-[11px] font-semibold inline-flex items-center justify-center gap-1"
          >
            <CheckCircle size={12} weight="fill" /> Adopter
          </button>
        )}
        {isAdopted && (
          <button
            onClick={() => onChange(s.id, "suggested")}
            className="flex-1 h-8 px-2 rounded-lg bg-emerald-100 text-emerald-900 text-[11px] font-semibold inline-flex items-center justify-center gap-1 border border-emerald-300"
          >
            <CheckCircle size={12} weight="fill" /> Adoptée
          </button>
        )}
        {!isIgnored ? (
          <button
            onClick={() => onChange(s.id, "ignored")}
            data-testid={`upsell-ignore-${s.id}`}
            className="h-8 w-8 rounded-lg bg-neutral-100 hover:bg-neutral-200 text-neutral-600 inline-flex items-center justify-center"
            title="Ignorer cette suggestion"
          >
            <XIcon size={12} weight="bold" />
          </button>
        ) : (
          <button
            onClick={() => onChange(s.id, "suggested")}
            className="h-8 px-2 rounded-lg bg-neutral-200 text-neutral-700 text-[11px] inline-flex items-center justify-center"
          >
            Restaurer
          </button>
        )}
      </footer>
    </article>
  );
}
