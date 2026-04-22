import React, { useEffect, useState, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { api, apiCall } from "../lib/api";
import Layout from "../components/Layout";
import {
  ArrowLeft,
  MagnifyingGlass,
  ShoppingCart,
  CheckCircle,
  Warning,
  ArrowClockwise,
  Package,
  Star,
  Storefront,
  Info,
  LinkSimple,
  Truck,
} from "@phosphor-icons/react";

const PROVIDER_META = {
  cj: { label: "CJ Dropshipping", color: "#10B981", emoji: "📦" },
  aliexpress: { label: "AliExpress", color: "#F97316", emoji: "🧡" },
};

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

export default function Sourcing() {
  const { id: siteId } = useParams();
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

  const load = useCallback(async () => {
    const [sRes, provRes] = await Promise.all([
      apiCall(() => api.get(`/sites/${siteId}`)),
      apiCall(() => api.get(`/sourcing/providers`)),
    ]);
    if (sRes.data) {
      setSite(sRes.data);
      const c = (sRes.data.selected_countries || ["FR"])[0];
      setCountry(c);
    }
    if (provRes.data) setProviders(provRes.data.providers || []);
  }, [siteId]);

  useEffect(() => { load(); }, [load]);

  const runSearch = async () => {
    const kw = keyword.trim();
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
  };

  const handleImport = async (item) => {
    const key = `${item.provider}:${item.product_id}`;
    setImported((prev) => ({ ...prev, [key]: "busy" }));
    const rate = item.provider === "cj" ? 0.92 : 1;
    const costEur = Math.round(item.cost_usd * rate * 100) / 100;
    // Default retail price = cost × 2.5 (Concepteur will adjust after import based on his pricing study)
    const priceEur = Math.round(costEur * 2.5 * 100) / 100;
    const { data, error, rawDetail } = await apiCall(() =>
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
        },
        { timeout: 90000 }
      )
    );
    if (error) {
      setImported((prev) => ({ ...prev, [key]: "error" }));
      // Shipping-unavailable 422 carries a structured detail
      const detail = rawDetail;
      if (detail && typeof detail === "object" && detail.error === "shipping_unavailable") {
        window.alert(`❌ Import bloqué\n\n${detail.message}\n\nPays non couverts : ${detail.missing_countries.join(", ")}.`);
      } else {
        window.alert(`Import impossible : ${error}`);
      }
      return;
    }
    setImported((prev) => ({
      ...prev,
      [key]: "ok",
      [`${key}_id`]: data.product.id,
      [`${key}_langs`]: data.product.translated_langs || [],
    }));
  };

  const handleImportByUrl = async () => {
    const u = urlImport.trim();
    if (!u) return;
    setUrlImporting(true);
    const { data, error, rawDetail } = await apiCall(() =>
      api.post(`/sites/${siteId}/sourcing/import-by-url`, { url: u }, { timeout: 120000 })
    );
    setUrlImporting(false);
    if (error) {
      const detail = rawDetail;
      if (detail && typeof detail === "object" && detail.error === "shipping_unavailable") {
        window.alert(`❌ Import bloqué\n\n${detail.message}\n\nPays non couverts : ${detail.missing_countries.join(", ")}.`);
      } else {
        window.alert(`Import URL impossible : ${error}`);
      }
      return;
    }
    setUrlImport("");
    window.alert(`✓ Produit importé en draft : "${(data.product?.name?.fr || data.product?.name?.en || "").slice(0, 80)}"`);
    navigate(`/sites/${siteId}/products`);
  };

  const anyProviderEnabled = providers.some((p) => p.enabled);

  return (
    <Layout>
      <div className="p-8 md:p-12 max-w-[1400px] mx-auto w-full">
        <button
          onClick={() => navigate(`/sites/${siteId}`)}
          data-testid="back-to-site"
          className="flex items-center gap-2 text-sm text-[#78716C] hover:text-[#1C1917] mb-6 transition"
        >
          <ArrowLeft size={16} /> Retour au cockpit
        </button>

        <div className="flex items-center gap-3 mb-8">
          <div className="w-12 h-12 rounded-lg bg-[#B84B31]/10 flex items-center justify-center">
            <Package size={24} weight="duotone" color="#B84B31" />
          </div>
          <div>
            <div className="text-xs uppercase tracking-wider text-[#78716C] mb-1">
              Étape 2 · Import produits
            </div>
            <h1 className="font-heading text-3xl font-semibold text-[#1C1917]">
              Sourcing fournisseurs
            </h1>
            <p className="text-sm text-[#78716C] mt-1">
              Recherche sur <strong>CJ Dropshipping</strong> et <strong>AliExpress</strong>, ou importe un produit par URL.
              Destination : <strong>{site?.name || "…"}</strong>
            </p>
          </div>
        </div>

        {/* providers status */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-5">
          {providers.map((p) => (
            <div
              key={p.id}
              data-testid={`provider-status-${p.id}`}
              className={`p-4 rounded-xl border flex items-center gap-3 ${
                p.enabled ? "bg-white border-[#E7E5E4]" : "bg-[#FAF7F2] border-dashed border-[#E7E5E4]"
              }`}
            >
              <div
                className="w-10 h-10 rounded-lg flex items-center justify-center text-xl"
                style={{ backgroundColor: `${PROVIDER_META[p.id]?.color}22` }}
              >
                {PROVIDER_META[p.id]?.emoji}
              </div>
              <div className="flex-1">
                <div className="font-medium text-sm text-[#1C1917]">{p.name}</div>
                <div className="text-xs text-[#78716C] flex items-center gap-1.5">
                  {p.enabled ? (
                    <><CheckCircle size={12} weight="fill" className="text-[#10B981]" /> Connecté & opérationnel</>
                  ) : (
                    <>Non configuré</>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* ===== Import par URL ===== */}
        <div className="bg-white rounded-xl border border-[#E7E5E4] p-5 mb-4">
          <div className="flex items-start gap-3 mb-3">
            <div className="w-8 h-8 rounded-lg bg-[#FEF3C7] flex items-center justify-center">
              <LinkSimple size={16} weight="bold" color="#D97706" />
            </div>
            <div className="flex-1">
              <div className="text-sm font-semibold text-[#1C1917]">Import direct par URL</div>
              <div className="text-xs text-[#78716C]">
                Colle un lien produit CJ (<em>cjdropshipping.com/product/…</em>) ou AliExpress
                (<em>aliexpress.com/item/…</em>) pour l'importer sans passer par la recherche.
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
              className="flex-1 h-11 px-3 rounded-lg border border-[#E7E5E4] bg-white text-sm focus:outline-none focus:border-[#1C1917]"
            />
            <button
              onClick={handleImportByUrl}
              disabled={urlImporting || !urlImport.trim()}
              data-testid="sourcing-url-import-btn"
              className="h-11 px-5 rounded-lg bg-[#1C1917] hover:bg-[#44403C] disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-medium flex items-center gap-2 transition"
            >
              {urlImporting ? (
                <><ArrowClockwise size={14} className="animate-spin" /> Import…</>
              ) : (
                <><ShoppingCart size={14} weight="fill" /> Importer depuis URL</>
              )}
            </button>
          </div>
        </div>

        {/* ===== Recherche mot-clé ===== */}
        <div className="bg-white rounded-xl border border-[#E7E5E4] p-5 mb-6">
          <div className="flex flex-col md:flex-row md:items-end gap-3">
            <div className="flex-1">
              <label className="block text-xs font-semibold text-[#57534E] mb-1.5 uppercase tracking-wider">
                Mot-clé produit
              </label>
              <div className="relative">
                <MagnifyingGlass
                  size={16}
                  className="absolute left-3 top-1/2 -translate-y-1/2 text-[#78716C]"
                />
                <input
                  type="text"
                  value={keyword}
                  onChange={(e) => setKeyword(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && runSearch()}
                  placeholder="ex: fauteuil releveur, pilulier électronique, loupe grossissante…"
                  data-testid="sourcing-keyword"
                  className="w-full h-11 pl-10 pr-3 rounded-lg border border-[#E7E5E4] bg-white text-sm focus:outline-none focus:border-[#1C1917]"
                />
              </div>
              <div className="text-[11px] text-[#78716C] mt-1.5">
                Tape en français — on traduit automatiquement en anglais pour CJ/AliExpress avant la recherche.
              </div>
            </div>
            <div>
              <label className="block text-xs font-semibold text-[#57534E] mb-1.5 uppercase tracking-wider">
                Pays livraison
              </label>
              <select
                value={country}
                onChange={(e) => setCountry(e.target.value)}
                data-testid="sourcing-country"
                className="h-11 px-3 rounded-lg border border-[#E7E5E4] bg-white text-sm focus:outline-none focus:border-[#1C1917]"
              >
                {COUNTRIES.map((c) => (
                  <option key={c.code} value={c.code}>
                    {c.flag} {c.name}
                  </option>
                ))}
              </select>
            </div>
            <button
              onClick={runSearch}
              disabled={loading || !keyword.trim() || !anyProviderEnabled}
              data-testid="sourcing-search-btn"
              className="h-11 px-5 rounded-lg bg-[#1C1917] hover:bg-[#44403C] disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-medium flex items-center gap-2 transition"
            >
              {loading ? (
                <><ArrowClockwise size={14} className="animate-spin" /> Recherche…</>
              ) : (
                <><MagnifyingGlass size={14} weight="bold" /> Rechercher</>
              )}
            </button>
          </div>

          {/* provider toggles */}
          <div className="flex flex-wrap items-center gap-3 mt-4 pt-4 border-t border-[#F5F2EB]">
            <span className="text-xs text-[#78716C]">Providers :</span>
            {Object.entries(PROVIDER_META).map(([id, meta]) => {
              const active = selectedProviders[id];
              const enabled = providers.find((p) => p.id === id)?.enabled;
              return (
                <button
                  key={id}
                  type="button"
                  disabled={!enabled}
                  onClick={() =>
                    setSelectedProviders((prev) => ({ ...prev, [id]: !prev[id] }))
                  }
                  data-testid={`toggle-provider-${id}`}
                  className={`h-8 px-3 rounded-full text-xs font-medium transition flex items-center gap-1.5 ${
                    !enabled
                      ? "bg-[#F5F2EB] text-[#A8A29E] cursor-not-allowed"
                      : active
                      ? "text-white"
                      : "bg-white border border-[#E7E5E4] text-[#57534E] hover:border-[#1C1917]"
                  }`}
                  style={active && enabled ? { backgroundColor: meta.color } : {}}
                >
                  <span>{meta.emoji}</span>
                  {meta.label}
                  {active && enabled && <CheckCircle size={12} weight="fill" />}
                </button>
              );
            })}
          </div>

          {translatedKeyword && (
            <div className="mt-3 text-[11px] text-[#78716C]">
              Recherché en anglais : <strong className="text-[#1C1917] font-mono">{translatedKeyword}</strong>
            </div>
          )}
        </div>

        {/* errors */}
        {errors.length > 0 && (
          <div className="mb-5 space-y-2">
            {errors.map((e, i) => (
              <div
                key={i}
                data-testid={`sourcing-error-${e.provider}`}
                className="p-3 rounded-lg bg-[#FFE4E6] text-[#BE123C] text-xs flex items-start gap-2"
              >
                <Warning size={14} weight="fill" className="shrink-0 mt-0.5" />
                <div>
                  <strong>{PROVIDER_META[e.provider]?.label || e.provider}</strong> : {e.detail}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Empty states */}
        {!loading && results.length === 0 && keyword && errors.length === 0 && (
          <div className="bg-white border border-dashed border-[#E7E5E4] rounded-xl p-12 text-center">
            <Storefront size={32} weight="duotone" className="mx-auto text-[#A8A29E] mb-3" />
            <p className="text-[#78716C] text-sm">
              Aucun résultat. Essaie un autre mot-clé, ou colle directement l'URL d'un produit en haut de page.
            </p>
          </div>
        )}

        {!keyword && !loading && results.length === 0 && (
          <div className="bg-[#FAF7F2] border border-[#E7E5E4] rounded-xl p-8 text-center">
            <Info size={24} weight="duotone" className="mx-auto text-[#B84B31] mb-3" />
            <h3 className="font-heading text-lg font-semibold text-[#1C1917] mb-1">
              Comment ça marche ?
            </h3>
            <p className="text-sm text-[#78716C] max-w-2xl mx-auto">
              <strong>Option 1 :</strong> Tape un mot-clé français — on le traduit automatiquement en
              anglais et on cherche sur CJ + AliExpress en parallèle.<br/>
              <strong>Option 2 :</strong> Colle directement l'URL d'un produit CJ ou AliExpress ci-dessus.<br/>
              Dans les deux cas : import en 1 clic, <strong>titre + description traduits automatiquement par Claude</strong> dans la langue des pays de ton site, statut <em>draft</em>.
              Tu définiras ton prix de vente après import selon ton analyse concurrentielle.
            </p>
          </div>
        )}

        {/* Results */}
        {results.length > 0 && (
          <>
            <div className="flex items-center justify-between mb-4">
              <div className="text-sm text-[#57534E]">
                <strong>{results.length}</strong> résultat{results.length > 1 ? "s" : ""} trouvé
                {results.length > 1 ? "s" : ""}
              </div>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {results.map((r) => {
                const key = `${r.provider}:${r.product_id}`;
                const state = imported[key];
                const meta = PROVIDER_META[r.provider] || {};
                const rate = r.provider === "cj" ? 0.92 : 1;
                const costEur = (r.cost_usd * rate).toFixed(2);
                const shipEur = r.shipping_usd ? (r.shipping_usd * rate).toFixed(2) : null;
                return (
                  <div
                    key={key}
                    data-testid={`sourcing-result-${key}`}
                    className="bg-white rounded-xl border border-[#E7E5E4] overflow-hidden hover:shadow-md transition"
                  >
                    <div className="aspect-square bg-[#F5F2EB] relative overflow-hidden">
                      {r.image ? (
                        <img
                          src={r.image}
                          alt=""
                          className="w-full h-full object-cover"
                          loading="lazy"
                          onError={(e) => { e.currentTarget.style.display = "none"; }}
                        />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center">
                          <Package size={40} weight="duotone" color="#A8A29E" />
                        </div>
                      )}
                      <div
                        className="absolute top-2 left-2 text-[10px] uppercase tracking-wider px-2 py-1 rounded-full text-white font-medium"
                        style={{ backgroundColor: meta.color }}
                      >
                        {meta.emoji} {meta.label}
                      </div>
                    </div>
                    <div className="p-3">
                      <div className="text-sm font-medium text-[#1C1917] line-clamp-2 min-h-[2.5rem]">
                        {r.title}
                      </div>
                      {r.category && (
                        <div className="text-[11px] text-[#78716C] mt-0.5 truncate">{r.category}</div>
                      )}
                      {r.rating > 0 && (
                        <div className="flex items-center gap-1 mt-1 text-xs text-[#78716C]">
                          <Star size={12} weight="fill" className="text-[#F59E0B]" />
                          {r.rating}% · {r.orders} commandes
                        </div>
                      )}
                      <div className="grid grid-cols-2 gap-2 mt-3 mb-2">
                        <div className="bg-[#FAF7F2] rounded-lg p-2">
                          <div className="text-[10px] uppercase tracking-wider text-[#78716C]">
                            Coût HT
                          </div>
                          <div className="font-mono text-sm font-semibold text-[#1C1917]">
                            {costEur}€
                          </div>
                        </div>
                        <div className="bg-[#EFF6FF] rounded-lg p-2">
                          <div className="text-[10px] uppercase tracking-wider text-[#1E40AF] flex items-center gap-1">
                            <Truck size={10} /> Livraison
                          </div>
                          <div className="font-mono text-sm font-semibold text-[#1E40AF]">
                            {shipEur ? `${shipEur}€` : "—"}
                          </div>
                        </div>
                      </div>
                      <button
                        onClick={() => handleImport(r)}
                        disabled={state === "busy" || state === "ok"}
                        data-testid={`import-${key}`}
                        className={`w-full h-9 rounded-lg text-xs font-medium flex items-center justify-center gap-1.5 transition ${
                          state === "ok"
                            ? "bg-[#D1FAE5] text-[#047857]"
                            : state === "busy"
                            ? "bg-[#F5F2EB] text-[#78716C]"
                            : "bg-[#1C1917] hover:bg-[#44403C] text-white"
                        }`}
                      >
                        {state === "busy" && (<><ArrowClockwise size={12} className="animate-spin" /> Traduction…</>)}
                        {state === "ok" && (<><CheckCircle size={12} weight="fill" /> Importé + traduit</>)}
                        {!state && (<><ShoppingCart size={12} weight="fill" /> Importer (draft)</>)}
                        {state === "error" && (<><Warning size={12} weight="fill" /> Réessayer</>)}
                      </button>
                      {r.supplier_url && (
                        <a
                          href={r.supplier_url}
                          target="_blank"
                          rel="noreferrer"
                          className="block text-center text-[11px] text-[#78716C] hover:text-[#B84B31] mt-2"
                        >
                          Voir chez le fournisseur →
                        </a>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>

            <div className="mt-6 flex justify-end">
              <button
                onClick={() => navigate(`/sites/${siteId}/products`)}
                data-testid="goto-products"
                className="h-10 px-4 rounded-xl bg-white border border-[#E7E5E4] hover:border-[#B84B31] text-[#1C1917] text-sm font-medium flex items-center gap-2 transition"
              >
                <Package size={14} /> Voir le catalogue ({site?.name}) →
              </button>
            </div>
          </>
        )}
      </div>
    </Layout>
  );
}
