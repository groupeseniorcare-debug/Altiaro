import React, { useEffect, useState, useCallback, useImperativeHandle, forwardRef } from "react";
import { useNavigate } from "react-router-dom";
import { api, apiCall } from "../lib/api";
import {
  MagnifyingGlass,
  ShoppingCart,
  CheckCircle,
  Warning,
  ArrowClockwise,
  Package,
  Star,
  Info,
  LinkSimple,
  Truck,
  Trash,
  PencilSimple,
} from "@phosphor-icons/react";

const PROVIDER_LABEL = { cj: "CJ Dropshipping", aliexpress: "AliExpress" };

const COUNTRIES = [
  { code: "FR", flag: "🇫🇷", name: "France" },
  { code: "DE", flag: "🇩🇪", name: "Allemagne" },
  { code: "BE", flag: "🇧🇪", name: "Belgique" },
  { code: "NL", flag: "🇳🇱", name: "Pays-Bas" },
  { code: "CH", flag: "🇨🇭", name: "Suisse" },
  { code: "UK", flag: "🇬🇧", name: "Royaume-Uni" },
  { code: "ES", flag: "🇪🇸", name: "Espagne" },
  { code: "IT", flag: "🇮🇹", name: "Italie" },
];

/**
 * Shared sourcing engine used by Étape 2 (Sourcing) + Étape 3 (Upsells).
 * Exposes a ref with `prefillAndSearch(keyword)` so parents can trigger
 * a search from outside (e.g. IA chips on the Upsells page).
 */
const SourcingPanel = forwardRef(function SourcingPanel(
  { siteId, emptyHint = null, context = "catalog" },
  ref
) {
  const navigate = useNavigate();
  const [site, setSite] = useState(null);
  const [providers, setProviders] = useState([]);
  const [keyword, setKeyword] = useState("");
  const [country, setCountry] = useState("FR");
  const [selectedProviders, setSelectedProviders] = useState({ cj: true, aliexpress: true });
  const [results, setResults] = useState([]);
  const [errors, setErrors] = useState([]);
  const [loading, setLoading] = useState(false);
  const [translatedKeyword, setTranslatedKeyword] = useState("");
  const [imported, setImported] = useState({});
  const [urlImport, setUrlImport] = useState("");
  const [urlImporting, setUrlImporting] = useState(false);
  const [catalog, setCatalog] = useState([]);

  const load = useCallback(async () => {
    const [sRes, provRes, pRes] = await Promise.all([
      apiCall(() => api.get(`/sites/${siteId}`)),
      apiCall(() => api.get(`/sourcing/providers`)),
      apiCall(() => api.get(`/sites/${siteId}/products`)),
    ]);
    if (sRes.data) {
      setSite(sRes.data);
      const c = (sRes.data.selected_countries || ["FR"])[0];
      setCountry(c);
    }
    if (provRes.data) setProviders(provRes.data.providers || []);
    if (Array.isArray(pRes.data)) setCatalog(pRes.data);
  }, [siteId]);

  useEffect(() => { load(); }, [load]);

  const runSearch = useCallback(async (kwOverride) => {
    const kw = (kwOverride ?? keyword).trim();
    if (!kw) return;
    setLoading(true);
    setResults([]);
    setErrors([]);
    setTranslatedKeyword("");
    const wanted = Object.keys(selectedProviders).filter((k) => selectedProviders[k]);
    const { data, error } = await apiCall(() =>
      api.post(`/sourcing/search`, { keyword: kw, providers: wanted, country, size: 24 })
    );
    setLoading(false);
    if (error) { setErrors([{ provider: "api", detail: error }]); return; }
    setResults(data.results || []);
    setErrors(data.errors || []);
    if (data.translated_keyword && data.translated_keyword !== kw) {
      setTranslatedKeyword(data.translated_keyword);
    }
  }, [keyword, selectedProviders, country]);

  // Expose prefill-and-search to parent (used by Upsells IA chips)
  useImperativeHandle(ref, () => ({
    prefillAndSearch: (kw) => {
      setKeyword(kw);
      runSearch(kw);
      if (typeof window !== "undefined") {
        setTimeout(() => window.scrollTo({ top: 0, behavior: "smooth" }), 50);
      }
    },
  }), [runSearch]);

  const handleImport = async (item) => {
    const key = `${item.provider}:${item.product_id}`;
    setImported((prev) => ({ ...prev, [key]: "busy" }));
    const rate = item.provider === "cj" ? 0.92 : 1;
    const costEur = Math.round(item.cost_usd * rate * 100) / 100;
    const priceEur = Math.round(costEur * 2.5 * 100) / 100;
    const { error, rawDetail } = await apiCall(() =>
      api.post(
        `/sites/${siteId}/sourcing/import`,
        {
          provider: item.provider,
          product_id: item.product_id,
          title: item.title,
          image: item.image || "",
          price_eur: priceEur,
          cost_eur: costEur,
          supplier_url: item.supplier_url || "",
          sku: item.sku || "",
          role: context === "upsell" ? "upsell" : "main",
        },
        { timeout: 90000 }
      )
    );
    if (error) {
      setImported((prev) => ({ ...prev, [key]: "error" }));
      if (rawDetail?.error === "shipping_unavailable") {
        window.alert(`❌ Import bloqué\n\n${rawDetail.message}\n\nPays non couverts : ${rawDetail.missing_countries.join(", ")}.`);
      } else {
        window.alert(`Import impossible : ${error}`);
      }
      return;
    }
    setImported((prev) => ({ ...prev, [key]: "ok" }));
    load();
  };

  const handleImportByUrl = async () => {
    const u = urlImport.trim();
    if (!u) return;
    setUrlImporting(true);
    const { data, error, rawDetail } = await apiCall(() =>
      api.post(
        `/sites/${siteId}/sourcing/import-by-url`,
        { url: u, role: context === "upsell" ? "upsell" : "main" },
        { timeout: 120000 }
      )
    );
    setUrlImporting(false);
    if (error) {
      if (rawDetail?.error === "shipping_unavailable") {
        window.alert(`❌ Import bloqué\n\n${rawDetail.message}\n\nPays non couverts : ${rawDetail.missing_countries.join(", ")}.`);
      } else {
        window.alert(`Import URL impossible : ${error}`);
      }
      return;
    }
    setUrlImport("");
    window.alert(`✓ Produit importé et actif : "${(data.product?.name?.fr || data.product?.name?.en || "").slice(0, 80)}"`);
    load();
  };

  const handleRemoveImported = async (pid) => {
    if (!window.confirm("Supprimer ce produit du catalogue ?")) return;
    const { error } = await apiCall(() => api.delete(`/sites/${siteId}/products/${pid}`));
    if (error) { window.alert(error); return; }
    load();
  };

  const anyProviderEnabled = providers.some((p) => p.enabled);
  const isUpsell = context === "upsell";
  const visibleCatalog = isUpsell
    ? catalog.filter((p) => p.role === "upsell")
    : catalog.filter((p) => p.role !== "upsell");

  return (
    <>
      <p className="text-sm text-neutral-500 mb-5 max-w-2xl" data-testid="sourcing-destination">
        Destination : <strong>{site?.name || "…"}</strong> · {(site?.selected_countries || []).join(", ")}
      </p>

      {/* Providers status */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-5">
        {providers.map((p) => (
          <div
            key={p.id}
            data-testid={`provider-status-${p.id}`}
            className="p-3 rounded-xl border border-neutral-200 bg-white flex items-center justify-between"
          >
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-neutral-100 flex items-center justify-center">
                <Package size={14} weight="duotone" />
              </div>
              <div>
                <div className="text-sm font-medium text-neutral-900">{p.name}</div>
                <div className="text-xs text-neutral-500">
                  {p.enabled ? "Connecté & opérationnel" : "Non configuré"}
                </div>
              </div>
            </div>
            <div className={`text-[11px] font-medium px-2 py-0.5 rounded-full ${
              p.enabled ? "bg-emerald-50 text-emerald-700" : "bg-neutral-100 text-neutral-500"
            }`}>
              {p.enabled ? "OK" : "OFF"}
            </div>
          </div>
        ))}
      </div>

      {/* Import by URL */}
      <div className="bg-white rounded-2xl border border-neutral-200 p-5 mb-4">
        <div className="flex items-start gap-3 mb-3">
          <div className="w-8 h-8 rounded-lg bg-neutral-100 flex items-center justify-center">
            <LinkSimple size={14} weight="bold" />
          </div>
          <div className="flex-1">
            <div className="text-sm font-semibold text-neutral-900">Import direct par URL</div>
            <div className="text-xs text-neutral-500">
              Colle un lien produit CJ ou AliExpress pour l'importer sans passer par la recherche.
            </div>
          </div>
        </div>
        <div className="flex gap-2">
          <input
            type="url"
            value={urlImport}
            onChange={(e) => setUrlImport(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleImportByUrl()}
            placeholder="https://cjdropshipping.com/product/… ou https://www.aliexpress.com/item/…"
            data-testid="sourcing-url-input"
            className="flex-1 h-11 px-3 rounded-lg border border-neutral-200 bg-white text-sm focus:outline-none focus:border-neutral-900"
          />
          <button
            onClick={handleImportByUrl}
            disabled={urlImporting || !urlImport.trim()}
            data-testid="sourcing-url-import-btn"
            className="h-11 px-5 rounded-lg bg-neutral-900 hover:bg-neutral-800 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-medium flex items-center gap-2 transition"
          >
            {urlImporting ? (<><ArrowClockwise size={14} className="animate-spin" /> Import…</>) :
              (<><ShoppingCart size={14} weight="fill" /> Importer</>)}
          </button>
        </div>
      </div>

      {/* Search by keyword */}
      <div className="bg-white rounded-2xl border border-neutral-200 p-5 mb-6">
        <div className="flex flex-col md:flex-row md:items-end gap-3">
          <div className="flex-1">
            <label className="block text-xs font-semibold text-neutral-600 mb-1.5 uppercase tracking-wider">
              Mot-clé produit
            </label>
            <div className="relative">
              <MagnifyingGlass size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-neutral-500" />
              <input
                type="text"
                value={keyword}
                onChange={(e) => setKeyword(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && runSearch()}
                placeholder={isUpsell
                  ? "coussin ergonomique, garantie 2 ans, batterie rechange…"
                  : "fauteuil releveur, pilulier, loupe grossissante…"}
                data-testid="sourcing-keyword"
                className="w-full h-11 pl-10 pr-3 rounded-lg border border-neutral-200 bg-white text-sm focus:outline-none focus:border-neutral-900"
              />
            </div>
            <div className="text-[11px] text-neutral-500 mt-1.5">
              Tape en français — on traduit automatiquement en anglais pour CJ / AliExpress.
            </div>
          </div>
          <div>
            <label className="block text-xs font-semibold text-neutral-600 mb-1.5 uppercase tracking-wider">
              Pays livraison
            </label>
            <select
              value={country}
              onChange={(e) => setCountry(e.target.value)}
              data-testid="sourcing-country"
              className="h-11 px-3 rounded-lg border border-neutral-200 bg-white text-sm focus:outline-none focus:border-neutral-900"
            >
              {COUNTRIES.map((c) => (
                <option key={c.code} value={c.code}>{c.flag} {c.name}</option>
              ))}
            </select>
          </div>
          <button
            onClick={() => runSearch()}
            disabled={loading || !keyword.trim() || !anyProviderEnabled}
            data-testid="sourcing-search-btn"
            className="h-11 px-5 rounded-lg bg-neutral-900 hover:bg-neutral-800 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-medium flex items-center gap-2 transition"
          >
            {loading ? (<><ArrowClockwise size={14} className="animate-spin" /> Recherche…</>) :
              (<><MagnifyingGlass size={14} weight="bold" /> Rechercher</>)}
          </button>
        </div>

        <div className="flex flex-wrap items-center gap-2 mt-4 pt-4 border-t border-neutral-100">
          <span className="text-xs text-neutral-500">Providers :</span>
          {Object.entries(PROVIDER_LABEL).map(([id, label]) => {
            const active = selectedProviders[id];
            const enabled = providers.find((p) => p.id === id)?.enabled;
            return (
              <button
                key={id}
                type="button"
                disabled={!enabled}
                onClick={() => setSelectedProviders((prev) => ({ ...prev, [id]: !prev[id] }))}
                data-testid={`toggle-provider-${id}`}
                className={`h-8 px-3 rounded-full text-xs font-medium transition flex items-center gap-1.5 ${
                  !enabled
                    ? "bg-neutral-100 text-neutral-400 cursor-not-allowed"
                    : active
                    ? "bg-neutral-900 text-white"
                    : "bg-white border border-neutral-200 text-neutral-700 hover:border-neutral-900"
                }`}
              >
                {label}
                {active && enabled && <CheckCircle size={12} weight="fill" />}
              </button>
            );
          })}
        </div>

        {translatedKeyword && (
          <div className="mt-3 text-[11px] text-neutral-500">
            Recherché en anglais : <strong className="text-neutral-900 font-mono">{translatedKeyword}</strong>
          </div>
        )}
      </div>

      {errors.length > 0 && (
        <div className="mb-5 space-y-2">
          {errors.map((e, i) => (
            <div
              key={i}
              data-testid={`sourcing-error-${e.provider}`}
              className="p-3 rounded-lg bg-red-50 text-red-800 text-xs flex items-start gap-2 border border-red-200"
            >
              <Warning size={14} weight="fill" className="shrink-0 mt-0.5" />
              <div><strong>{PROVIDER_LABEL[e.provider] || e.provider}</strong> : {e.detail}</div>
            </div>
          ))}
        </div>
      )}

      {!loading && results.length === 0 && !keyword && (
        <div className="bg-white border border-dashed border-neutral-200 rounded-2xl p-10 text-center mb-6">
          <Info size={24} weight="duotone" className="mx-auto text-neutral-400 mb-3" />
          <h3 className="text-base font-semibold text-neutral-900 mb-1" style={{ fontFamily: "'Fraunces', serif" }}>
            {emptyHint?.title || "Deux façons d'importer"}
          </h3>
          <p className="text-sm text-neutral-500 max-w-xl mx-auto">
            {emptyHint?.body ||
              "Recherche par mot-clé (traduction auto FR→EN) ou colle l'URL d'un produit directement. Import en 1 clic, traduit par Claude, disponible immédiatement sur ton storefront."}
          </p>
        </div>
      )}

      {/* Search results */}
      {results.length > 0 && (
        <div className="mb-10">
          <div className="flex items-center justify-between mb-4">
            <div className="text-sm text-neutral-700">
              <strong>{results.length}</strong> résultat{results.length > 1 ? "s" : ""}
            </div>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {results.map((r) => {
              const key = `${r.provider}:${r.product_id}`;
              const state = imported[key];
              const rate = r.provider === "cj" ? 0.92 : 1;
              const costEur = (r.cost_usd * rate).toFixed(2);
              const shipEur = r.shipping_usd ? (r.shipping_usd * rate).toFixed(2) : null;
              return (
                <div
                  key={key}
                  data-testid={`sourcing-result-${key}`}
                  className="bg-white rounded-2xl border border-neutral-200 overflow-hidden hover:border-neutral-400 transition"
                >
                  <div className="aspect-square bg-neutral-100 relative overflow-hidden">
                    {r.image ? (
                      <img src={r.image} alt="" className="w-full h-full object-cover" loading="lazy"
                        onError={(e) => { e.currentTarget.style.display = "none"; }} />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center">
                        <Package size={40} weight="duotone" color="#A8A29E" />
                      </div>
                    )}
                    <div className="absolute top-2 left-2 text-[10px] uppercase tracking-wider px-2 py-1 rounded-full bg-white/90 border border-neutral-200 text-neutral-700 font-medium">
                      {PROVIDER_LABEL[r.provider]}
                    </div>
                  </div>
                  <div className="p-3">
                    <div className="text-sm font-medium text-neutral-900 line-clamp-2 min-h-[2.5rem]">{r.title}</div>
                    {r.rating > 0 && (
                      <div className="flex items-center gap-1 mt-1 text-xs text-neutral-500">
                        <Star size={12} weight="fill" className="text-amber-500" />
                        {r.rating}% · {r.orders} cmd
                      </div>
                    )}
                    <div className="grid grid-cols-2 gap-2 mt-3 mb-2">
                      <div className="bg-neutral-50 rounded-lg px-2 py-1.5">
                        <div className="text-[10px] uppercase tracking-wider text-neutral-500">Achat HT</div>
                        <div className="font-mono text-sm font-semibold text-neutral-900">{costEur}€</div>
                      </div>
                      <div className="bg-neutral-50 rounded-lg px-2 py-1.5">
                        <div className="text-[10px] uppercase tracking-wider text-neutral-500 flex items-center gap-0.5">
                          <Truck size={10} /> Livraison
                        </div>
                        <div className="font-mono text-sm font-semibold text-neutral-900">{shipEur ? `${shipEur}€` : "—"}</div>
                      </div>
                    </div>
                    <button
                      onClick={() => handleImport(r)}
                      disabled={state === "busy" || state === "ok"}
                      data-testid={`import-${key}`}
                      className={`w-full h-9 rounded-lg text-xs font-medium flex items-center justify-center gap-1.5 transition ${
                        state === "ok"
                          ? "bg-emerald-100 text-emerald-800"
                          : state === "busy"
                          ? "bg-neutral-100 text-neutral-600"
                          : "bg-neutral-900 hover:bg-neutral-800 text-white"
                      }`}
                    >
                      {state === "busy" && (<><ArrowClockwise size={12} className="animate-spin" /> Import…</>)}
                      {state === "ok" && (<><CheckCircle size={12} weight="fill" /> Importé</>)}
                      {!state && (<><ShoppingCart size={12} weight="fill" /> {isUpsell ? "Ajouter comme upsell" : "Importer"}</>)}
                      {state === "error" && (<><Warning size={12} weight="fill" /> Réessayer</>)}
                    </button>
                    {r.supplier_url && (
                      <a href={r.supplier_url} target="_blank" rel="noreferrer"
                        className="block text-center text-[11px] text-neutral-500 hover:text-neutral-900 mt-2">
                        Voir chez le fournisseur →
                      </a>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Already imported products for this role */}
      {visibleCatalog.length > 0 && (
        <div className="mt-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <div className="text-[11px] uppercase tracking-[0.2em] text-neutral-500 mb-1">
                {isUpsell ? "Upsells actifs" : "Catalogue actif"}
              </div>
              <h2 className="text-lg font-semibold text-neutral-900" style={{ fontFamily: "'Fraunces', serif" }}>
                {visibleCatalog.length} {isUpsell ? "upsell" : "produit"}{visibleCatalog.length > 1 ? "s" : ""}
                {isUpsell ? " dans ton catalogue" : " dans ta boutique"}
              </h2>
            </div>
            <button
              onClick={() => navigate(`/sites/${siteId}/products`)}
              data-testid="goto-products"
              className="h-9 px-4 rounded-lg bg-white border border-neutral-200 hover:border-neutral-900 text-neutral-900 text-xs font-medium flex items-center gap-2 transition"
            >
              Gérer le catalogue →
            </button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
            {visibleCatalog.map((p) => {
              const ship = p.shipping || {};
              const pct = p.cost_price_ht > 0 && p.price > 0
                ? (((p.price / 1.2) - p.cost_price_ht) / (p.price / 1.2)) * 100
                : 0;
              return (
                <div key={p.id}
                  data-testid={`imported-${p.id}`}
                  className="bg-white rounded-2xl border border-neutral-200 overflow-hidden hover:border-neutral-400 transition">
                  <div className="aspect-square bg-neutral-100 relative">
                    {p.images?.[0] ? (
                      <img src={p.images[0]} alt="" className="w-full h-full object-cover" loading="lazy"
                        onError={(e) => { e.currentTarget.style.display = "none"; }} />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center">
                        <Package size={32} weight="duotone" color="#A8A29E" />
                      </div>
                    )}
                    <div className={`absolute top-2 right-2 text-[10px] uppercase px-1.5 py-0.5 rounded-full font-medium ${
                      p.status === "active"
                        ? "bg-emerald-100 text-emerald-800"
                        : "bg-amber-100 text-amber-800"
                    }`}>
                      {p.status}
                    </div>
                    {p.role === "upsell" && (
                      <div className="absolute top-2 left-2 text-[10px] uppercase px-1.5 py-0.5 rounded-full font-medium bg-indigo-100 text-indigo-800">
                        upsell
                      </div>
                    )}
                  </div>
                  <div className="p-3">
                    <div className="text-xs font-medium text-neutral-900 line-clamp-2 min-h-[2rem]" title={p.name?.fr}>
                      {p.name?.fr || "(sans nom)"}
                    </div>
                    <div className="flex items-baseline gap-2 mt-2">
                      <span className="font-mono text-sm font-semibold text-neutral-900">{p.price?.toFixed(0)}€</span>
                      {p.cost_price_ht > 0 && (
                        <span className="text-[10px] text-neutral-500 font-mono">
                          achat {p.cost_price_ht.toFixed(0)}€ · {pct.toFixed(0)}%
                        </span>
                      )}
                    </div>
                    {Object.keys(ship).length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-2">
                        {Object.entries(ship).map(([cc, info]) => {
                          const status = info?.available;
                          return (
                            <span key={cc}
                              className={`text-[9px] px-1.5 py-0.5 rounded-full font-medium ${
                                status === true ? "bg-emerald-50 text-emerald-700" :
                                status === false ? "bg-red-50 text-red-700" :
                                "bg-neutral-100 text-neutral-600"
                              }`}>
                              {status === true ? "✓" : status === false ? "✗" : "?"} {cc}
                            </span>
                          );
                        })}
                      </div>
                    )}
                    <div className="flex gap-1 mt-3">
                      <button
                        onClick={() => navigate(`/sites/${siteId}/products?edit=${p.id}`)}
                        data-testid={`imported-edit-${p.id}`}
                        className="flex-1 h-8 rounded-lg bg-neutral-900 hover:bg-neutral-800 text-white text-[11px] font-medium flex items-center justify-center gap-1"
                      >
                        <PencilSimple size={10} /> Éditer
                      </button>
                      <button
                        onClick={() => handleRemoveImported(p.id)}
                        data-testid={`imported-delete-${p.id}`}
                        className="h-8 w-8 rounded-lg border border-neutral-200 hover:border-red-300 text-neutral-500 hover:text-red-400 flex items-center justify-center transition"
                        title="Supprimer"
                      >
                        <Trash size={11} />
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </>
  );
});

export default SourcingPanel;
