import React, { useState } from "react";
import { useParams, Link } from "react-router-dom";
import {
  MagnifyingGlass, ArrowLeft, CheckCircle, Warning, DownloadSimple,
  Storefront, Sparkle,
} from "@phosphor-icons/react";
import { api, apiCall } from "../lib/api";

/**
 * Cockpit page — search AliExpress Dropshipping catalog and import products.
 * AliExpress is connected at the PLATFORM level (admin-only, once) — every
 * site inherits automatically, so the Concepteur never sees a "Connect" button.
 */
export default function SiteAliExpressImport() {
  const { id: siteId } = useParams();
  const [keyword, setKeyword] = useState("");
  const [page, setPage] = useState(1);
  const [results, setResults] = useState([]);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState("");
  const [importing, setImporting] = useState({}); // productId -> "loading" | "done" | "error"
  const [toast, setToast] = useState(null);
  const [needsReconnect, setNeedsReconnect] = useState(false);  // Phase 2.7.4

  const showToast = (type, msg) => {
    setToast({ type, msg });
    setTimeout(() => setToast(null), 4000);
  };

  // Phase 2.7.4 — surface a clean banner instead of opaque 502 errors when
  // the platform-level AE token is expired and refresh failed.
  const detectReconnectError = (err) => {
    const msg = typeof err === "string" ? err : JSON.stringify(err || "");
    return /AE_RECONNECT_REQUIRED|IllegalAccessToken|IllegalRefreshToken|expired/i.test(msg);
  };

  const search = async (e) => {
    e?.preventDefault?.();
    if (!keyword.trim()) return;
    setSearching(true);
    setError("");
    setNeedsReconnect(false);
    setResults([]);
    const { data, error: err } = await apiCall(() =>
      api.post("/aliexpress/products/search", {
        site_id: siteId,
        keyword: keyword.trim(),
        page,
        page_size: 20,
      })
    );
    setSearching(false);
    if (err) {
      if (detectReconnectError(err)) {
        setNeedsReconnect(true);
        setError("");
      } else {
        setError(typeof err === "string" ? err : "Erreur lors de la recherche.");
      }
      return;
    }
    // AliExpress response shape varies — we dig through the wrapper keys.
    const list = extractProductList(data);
    setResults(list);
    if (!list.length) setError("Aucun produit trouvé pour ce mot-clé.");
  };

  const importProduct = async (productId) => {
    setImporting((p) => ({ ...p, [productId]: "loading" }));
    const { data, error: err } = await apiCall(() =>
      api.post("/aliexpress/products/import", { site_id: siteId, product_id: productId })
    );
    if (err) {
      setImporting((p) => ({ ...p, [productId]: "error" }));
      if (detectReconnectError(err)) {
        setNeedsReconnect(true);
      } else {
        showToast("error", typeof err === "string" ? err : "Import échoué.");
      }
      return;
    }
    setImporting((p) => ({ ...p, [productId]: "done" }));
    showToast("ok", `« ${data?.name?.slice?.(0, 60) || "Produit"} » importé — l'IA enrichit la fiche en arrière-plan.`);
  };

  return (
    <div className="min-h-screen bg-[#FAF7F2]">
      <div className="max-w-[1600px] mx-auto px-6 md:px-10 py-8">
        <Link
          to={`/sites/${siteId}`}
          className="inline-flex items-center gap-2 text-sm text-neutral-600 hover:text-neutral-900 mb-6"
          data-testid="ali-back-to-site"
        >
          <ArrowLeft size={14} /> Retour au cockpit
        </Link>

        <div className="mb-8">
          <div className="text-[11px] uppercase tracking-[0.2em] text-neutral-500 mb-2 flex items-center gap-2">
            <Storefront size={12} weight="bold" /> Import produits · AliExpress Dropshipping
          </div>
          <h1 className="text-3xl md:text-4xl font-semibold text-neutral-900" style={{ fontFamily: "'Fraunces', serif" }}>
            Ajoutez des produits depuis AliExpress
          </h1>
          <p className="text-sm text-neutral-500 mt-2 max-w-2xl">
            Recherchez dans le catalogue Dropshipping AliExpress. Chaque produit importé est enrichi automatiquement par l'IA (titre SEO, description, FAQ) puis disponible dans votre catalogue.
          </p>
        </div>

        {/* Search bar */}
        <form onSubmit={search} className="bg-white border border-neutral-200 rounded-2xl p-5 mb-6 flex gap-2" data-testid="ali-search-form">
          <div className="flex-1 relative">
            <MagnifyingGlass size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-neutral-400" />
            <input
              type="text"
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
              placeholder="ex: fauteuil releveur, déambulateur léger, monte-escalier…"
              data-testid="ali-search-keyword"
              className="w-full h-11 pl-10 pr-3 rounded-xl border border-neutral-200 focus:outline-none focus:ring-2 focus:ring-neutral-300 text-sm"
            />
          </div>
          <button
            type="submit"
            disabled={searching || !keyword.trim()}
            data-testid="ali-search-submit"
            className="h-11 px-5 rounded-xl bg-neutral-900 hover:bg-neutral-800 text-white text-sm font-medium disabled:opacity-60 flex items-center gap-1.5"
          >
            <MagnifyingGlass size={14} weight="bold" /> {searching ? "Recherche…" : "Rechercher"}
          </button>
        </form>

        {/* Toast */}
        {toast && (
          <div
            data-testid="ali-toast"
            className={`mb-5 px-4 py-3 rounded-xl text-sm font-medium flex items-center gap-2 ${
              toast.type === "ok"
                ? "bg-emerald-50 text-emerald-900 border border-emerald-200"
                : "bg-rose-50 text-rose-900 border border-rose-200"
            }`}
          >
            {toast.type === "ok" ? <CheckCircle size={16} weight="fill" /> : <Warning size={16} weight="fill" />}
            {toast.msg}
          </div>
        )}

        {/* Phase 2.7.4 — banner clair quand AE doit être reconnecté */}
        {needsReconnect && (
          <div className="bg-amber-50 border border-amber-200 rounded-2xl p-5 mb-5 text-sm text-amber-950 flex items-start gap-3" data-testid="ali-reconnect-banner">
            <Warning size={18} weight="fill" className="text-amber-600 mt-0.5 flex-shrink-0" />
            <div className="flex-1">
              <div className="font-semibold mb-0.5">AliExpress doit être reconnecté</div>
              <div className="text-amber-900 leading-relaxed">
                Le jeton d'accès AliExpress de la plateforme a expiré (les tokens
                AliExpress Dropshipping durent 24-48 h). Un admin doit reconnecter
                l'intégration pour réactiver la recherche et l'import.
              </div>
              <div className="mt-3 flex gap-2">
                <a
                  href="/admin/integrations"
                  data-testid="ali-reconnect-cta"
                  className="inline-flex items-center gap-1.5 h-9 px-4 rounded-full bg-neutral-900 text-white text-xs font-medium hover:bg-neutral-800"
                >
                  → Admin · Intégrations
                </a>
                <a
                  href="/api/admin/aliexpress/authorize-url"
                  target="_blank" rel="noreferrer"
                  className="inline-flex items-center gap-1.5 h-9 px-4 rounded-full border border-amber-300 text-amber-950 text-xs font-medium hover:bg-amber-100"
                >
                  Reconnecter directement
                </a>
              </div>
            </div>
          </div>
        )}

        {/* Error */}
        {error && !results.length && !needsReconnect && (
          <div className="bg-rose-50 border border-rose-200 rounded-2xl p-5 text-sm text-rose-900 flex items-start gap-3" data-testid="ali-search-error">
            <Warning size={18} weight="fill" className="text-rose-600 mt-0.5 flex-shrink-0" />
            <div>{error}</div>
          </div>
        )}

        {/* Results grid */}
        {results.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4" data-testid="ali-results">
            {results.map((p) => (
              <ProductCard
                key={p.product_id}
                product={p}
                importState={importing[p.product_id]}
                onImport={() => importProduct(p.product_id)}
              />
            ))}
          </div>
        )}

        {searching && !results.length && (
          <div className="py-16 text-center text-neutral-500 text-sm">Recherche dans le catalogue AliExpress…</div>
        )}
      </div>
    </div>
  );
}

function ProductCard({ product, importState, onImport }) {
  return (
    <div className="bg-white border border-neutral-200 rounded-2xl p-4 flex flex-col gap-3 hover:shadow-sm transition" data-testid={`ali-product-${product.product_id}`}>
      <div className="aspect-square bg-neutral-100 rounded-xl overflow-hidden">
        {product.image_url ? (
          <img src={product.image_url} alt="" loading="lazy" className="w-full h-full object-cover" />
        ) : null}
      </div>
      <div className="flex-1 min-h-0">
        <div className="text-sm font-medium text-neutral-900 line-clamp-2 leading-tight">{product.title}</div>
        <div className="mt-2 flex items-baseline gap-2">
          <span className="text-lg font-semibold text-neutral-900" style={{ fontFamily: "'Fraunces', serif" }}>
            {typeof product.price === "number" ? `${product.price.toFixed(2)} €` : product.price || "—"}
          </span>
          {product.orders ? <span className="text-[11px] text-neutral-500">{product.orders} ventes</span> : null}
        </div>
      </div>
      <button
        onClick={onImport}
        disabled={importState === "loading" || importState === "done"}
        data-testid={`ali-import-${product.product_id}`}
        className={`h-10 rounded-lg text-sm font-medium flex items-center justify-center gap-1.5 transition ${
          importState === "done"
            ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
            : importState === "error"
            ? "bg-rose-50 text-rose-700 border border-rose-200"
            : "bg-neutral-900 hover:bg-neutral-800 text-white"
        } disabled:cursor-default`}
      >
        {importState === "loading" && <Sparkle size={13} weight="fill" className="animate-pulse" />}
        {importState === "done" && <CheckCircle size={13} weight="fill" />}
        {importState === "error" && <Warning size={13} weight="fill" />}
        {!importState && <DownloadSimple size={13} weight="bold" />}
        {importState === "done" ? "Importé ✓" : importState === "loading" ? "Import…" : importState === "error" ? "Réessayer" : "Importer"}
      </button>
    </div>
  );
}

/**
 * AliExpress responses are nested under varying wrapper keys depending on method.
 * We probe the common ones and normalize to a flat list of {product_id, title, image_url, price, orders}.
 */
function extractProductList(raw) {
  if (!raw) return [];
  // Common wrappers
  const candidates = [
    raw,
    raw.aliexpress_ds_text_search_response,
    raw.aliexpress_affiliate_product_query_response,
    raw.result,
    raw.data,
  ].filter(Boolean);

  for (const c of candidates) {
    const products =
      c.products?.traffic_product_d_t_o ||
      c.products?.product ||
      c.result?.products ||
      c.result?.result?.products ||
      c.products ||
      null;
    if (Array.isArray(products)) {
      return products.map(normaliseProduct).filter((p) => p.product_id);
    }
  }
  return [];
}

function normaliseProduct(p) {
  const price = Number(p.sale_price || p.target_sale_price || p.min_price || p.price || 0);
  return {
    product_id: String(p.product_id || p.item_id || p.itemId || ""),
    title: p.product_title || p.subject || p.title || "",
    image_url: p.product_main_image_url || p.main_image_url || p.image_url || p.product_image_url || "",
    price: Number.isFinite(price) ? price : 0,
    orders: p.lastest_volume || p.orders || p.order_count || null,
  };
}
