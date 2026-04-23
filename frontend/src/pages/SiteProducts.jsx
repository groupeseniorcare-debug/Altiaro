import React, { useEffect, useState, useCallback } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { api, apiCall } from "../lib/api";
import Layout from "../components/Layout";
import {
  ArrowLeft,
  Plus,
  Storefront,
  PencilSimple,
  Trash,
  Eye,
  X,
  CheckCircle,
  Star,
  DownloadSimple,
  UploadSimple,
  Sparkle,
  Image as ImageIcon,
  ArrowsClockwise,
  Warning,
  TrendUp,
  Sparkle as SparkleIcon,
  Package,
} from "@phosphor-icons/react";

const BACKEND_URL = "";

const LANGS = [
  { code: "fr", label: "FR 🇫🇷" },
  { code: "en", label: "EN 🇬🇧" },
  { code: "de", label: "DE 🇩🇪" },
  { code: "nl", label: "NL 🇳🇱" },
];

const emptyProduct = () => ({
  name: { fr: "", en: "", de: "", nl: "" },
  description: { fr: "", en: "", de: "", nl: "" },
  price: 0,
  cost_price_ht: 0,
  compare_at_price: null,
  currency: "EUR",
  images: [""],
  stock: null,
  supplier_url: "",
  sku: "",
  status: "active",
  featured: false,
});

export default function SiteProducts() {
  const { id: siteId } = useParams();
  const navigate = useNavigate();
  const [site, setSite] = useState(null);
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(null);
  const [importing, setImporting] = useState(false);
  const [importUrl, setImportUrl] = useState("");
  const [importError, setImportError] = useState("");
  const [syncing, setSyncing] = useState(null); // product.id currently syncing
  const [syncResult, setSyncResult] = useState(null); // {product, diff}
  const [enriching, setEnriching] = useState(null); // product.id being AI-enriched
  const [bundling, setBundling] = useState(false); // bulk bundles generation in progress
  const [aiToast, setAiToast] = useState(null);

  const load = useCallback(async () => {
    const [sRes, pRes] = await Promise.all([
      apiCall(() => api.get(`/sites/${siteId}`)),
      apiCall(() => api.get(`/sites/${siteId}/products`)),
    ]);
    if (sRes.data) setSite(sRes.data);
    if (pRes.data) setProducts(pRes.data);
    setLoading(false);
  }, [siteId]);

  useEffect(() => {
    load();
  }, [load]);

  const handleDelete = async (p) => {
    if (!window.confirm(`Supprimer « ${p.name?.fr || "Produit"} » ?`)) return;
    await apiCall(() => api.delete(`/sites/${siteId}/products/${p.id}`));
    load();
  };

  const handleImport = async () => {
    if (!importUrl.trim()) return;
    setImporting(true);
    setImportError("");
    const { data, error } = await apiCall(() =>
      api.post(`/sites/${siteId}/products/import`, { url: importUrl.trim() })
    );
    setImporting(false);
    if (error) {
      setImportError(error);
      return;
    }
    setImportUrl("");
    setEditing(data.draft);
  };

  const handleResync = async (p) => {
    setSyncing(p.id);
    const { data, error } = await apiCall(() =>
      api.post(`/sites/${siteId}/products/${p.id}/resync`)
    );
    setSyncing(null);
    if (error) {
      window.alert(`Re-sync impossible : ${error}`);
      return;
    }
    setSyncResult({ product: p, diff: data });
  };

  const handleApplyResync = async () => {
    if (!syncResult) return;
    const { product, diff } = syncResult;
    const updates = {};
    if (diff.price?.new && diff.price.new !== product.price) {
      updates.price = diff.price.new;
    }
    if (Object.keys(updates).length === 0) {
      setSyncResult(null);
      return;
    }
    await apiCall(() =>
      api.patch(`/sites/${siteId}/products/${product.id}`, updates)
    );
    setSyncResult(null);
    load();
  };

  const handleEnrichNarrative = async (p) => {
    setEnriching(p.id);
    setAiToast(null);
    // Kick async job
    const { data: kick, error: kickErr } = await apiCall(() =>
      api.post(`/products/${p.id}/enrich-narrative?force=true`)
    );
    if (kickErr) {
      setEnriching(null);
      setAiToast({ type: "error", msg: kickErr });
      setTimeout(() => setAiToast(null), 6000);
      return;
    }
    if (!kick?.job_id) {
      setEnriching(null);
      setAiToast({ type: "error", msg: "Impossible de lancer la génération IA." });
      return;
    }
    // Poll every 3 s, max 3 min
    let attempts = 0;
    const poll = async () => {
      attempts += 1;
      const { data: s } = await apiCall(() => api.get(`/products/${p.id}/enrich-narrative/status`));
      if (s?.status === "done") {
        setEnriching(null);
        setAiToast({ type: "ok", msg: `Narratif IA régénéré pour « ${p.name?.fr || "produit"} »` });
        setTimeout(() => setAiToast(null), 5000);
        load();
        return;
      }
      if (s?.status === "failed") {
        setEnriching(null);
        setAiToast({ type: "error", msg: s.error || "Échec de la génération IA." });
        setTimeout(() => setAiToast(null), 8000);
        return;
      }
      if (attempts < 60) { // 60 × 3 s = 3 min
        setTimeout(poll, 3000);
      } else {
        setEnriching(null);
        setAiToast({ type: "error", msg: "Timeout après 3 min — le job continue en arrière-plan, recharge la page plus tard." });
        setTimeout(() => setAiToast(null), 8000);
      }
    };
    setTimeout(poll, 3000);
  };

  const handleAutoBundles = async () => {
    setBundling(true);
    setAiToast(null);
    const { data, error } = await apiCall(() =>
      api.post(`/sites/${siteId}/bundles/auto-generate`)
    );
    setBundling(false);
    if (error) {
      setAiToast({ type: "error", msg: error });
    } else if (data?.status === "ok") {
      setAiToast({
        type: "ok",
        msg: `${data.products_updated} produits mis à jour avec ${data.total_links} liens cross-sell`
      });
      load();
    } else if (data?.status === "not_enough_products") {
      setAiToast({ type: "error", msg: "Il faut au moins 2 produits actifs pour générer des bundles." });
    } else {
      setAiToast({ type: "error", msg: "Budget LLM insuffisant. Rechargez votre Universal Key." });
    }
    setTimeout(() => setAiToast(null), 6000);
  };

  if (loading) {
    return (
      <Layout>
        <div className="p-8 text-neutral-500">Chargement…</div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="p-8 md:p-12 max-w-7xl">
        <button
          onClick={() => navigate(`/sites/${siteId}`)}
          className="flex items-center gap-2 text-sm text-neutral-500 hover:text-neutral-900 mb-6 transition"
          data-testid="back-to-site"
        >
          <ArrowLeft size={16} /> Retour au site
        </button>

        <div className="flex items-start justify-between gap-8 mb-10 animate-fade-up">
          <div>
            <div className="text-[11px] uppercase tracking-widest text-neutral-500 mb-2">
              {site?.name} · Catalogue
            </div>
            <h1 className="text-3xl font-semibold text-neutral-900">Produits</h1>
            <p className="text-neutral-600 mt-2 max-w-xl">
              Importe depuis une URL fournisseur ou crée tes produits à la main.
              Fiches multilingues FR/EN/DE/NL publiées sur la boutique publique.
            </p>
          </div>
          <div className="flex gap-2">
            <a
              href={`/shop/${siteId}`}
              target="_blank"
              rel="noreferrer"
              data-testid="preview-shop"
              className="h-11 px-4 rounded-xl bg-white border border-neutral-200 hover:border-[#B84B31] text-neutral-900 text-sm font-medium flex items-center gap-2 transition"
            >
              <Eye size={16} /> Voir la boutique
            </a>
            {products.length >= 2 && (
              <button
                onClick={handleAutoBundles}
                disabled={bundling}
                data-testid="auto-bundles"
                className="h-11 px-4 rounded-xl bg-white border border-neutral-200 hover:border-[#B84B31] text-neutral-900 text-sm font-medium flex items-center gap-2 transition disabled:opacity-60"
                title="L'IA analyse tout votre catalogue et génère les cross-sells pertinents pour chaque produit"
              >
                <Package size={16} weight="duotone" className={bundling ? "animate-pulse" : ""} />
                {bundling ? "Analyse IA…" : "Auto-bundles IA"}
              </button>
            )}
            <button
              onClick={() => setEditing(emptyProduct())}
              data-testid="add-product"
              className="h-11 px-4 rounded-xl bg-neutral-900 hover:bg-neutral-800 text-white text-sm font-medium flex items-center gap-2 transition active:scale-[0.98]"
            >
              <Plus size={16} weight="bold" /> Nouveau produit
            </button>
          </div>
        </div>

        {aiToast && (
          <div
            data-testid="ai-toast"
            className={`mb-5 px-4 py-3 rounded-xl text-sm font-medium flex items-center gap-2 ${
              aiToast.type === "ok"
                ? "bg-emerald-50 text-emerald-900 border border-emerald-200"
                : "bg-rose-50 text-rose-900 border border-rose-200"
            }`}
          >
            {aiToast.type === "ok" ? <CheckCircle size={16} weight="fill" /> : <Warning size={16} weight="fill" />}
            {aiToast.msg}
          </div>
        )}

        {/* Import from URL bar */}
        <div className="bg-white rounded-md border border-neutral-200 p-5 mb-6" data-testid="import-url-bar">
          <div className="flex items-center gap-2 mb-2">
            <Sparkle size={16} weight="fill" className="text-neutral-900" />
            <div className="font-heading text-sm font-semibold text-neutral-900">
              Import rapide depuis une URL fournisseur
            </div>
            <div className="text-xs text-neutral-500">
              · Shopify / WooCommerce / sites structurés (JSON-LD, Open Graph)
            </div>
          </div>
          <div className="flex gap-2">
            <input
              value={importUrl}
              onChange={(e) => setImportUrl(e.target.value)}
              placeholder="https://fournisseur.com/produits/..."
              data-testid="import-url-input"
              onKeyDown={(e) => e.key === "Enter" && handleImport()}
              className="flex-1 h-11 px-4 rounded-xl border border-neutral-200 bg-white focus:ring-2 focus:ring-zinc-500/30 focus:border-neutral-400 outline-none text-sm"
            />
            <button
              onClick={handleImport}
              disabled={importing || !importUrl.trim()}
              data-testid="import-url-submit"
              className="h-11 px-5 rounded-xl bg-neutral-900 hover:bg-neutral-800 text-white text-sm font-medium flex items-center gap-2 transition disabled:opacity-50"
            >
              {importing ? (
                "Analyse..."
              ) : (
                <>
                  <DownloadSimple size={16} weight="bold" /> Importer
                </>
              )}
            </button>
          </div>
          {importError && (
            <div className="mt-3 px-3 py-2 rounded-lg bg-red-500/10 text-red-400 text-sm" data-testid="import-error">
              {importError}
            </div>
          )}
        </div>

        {products.length === 0 ? (
          <div className="bg-white rounded-md border border-neutral-200 p-16 text-center">
            <Storefront size={48} weight="thin" className="mx-auto text-neutral-400 mb-4" />
            <div className="text-neutral-500 mb-4">Aucun produit pour l'instant.</div>
            <button
              onClick={() => setEditing(emptyProduct())}
              className="inline-flex items-center gap-2 h-11 px-5 rounded-xl bg-neutral-900 hover:bg-neutral-800 text-white text-sm font-medium transition"
            >
              <Plus size={16} weight="bold" /> Ajouter mon premier produit
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5" data-testid="admin-products-grid">
            {products.map((p) => (
              <div
                key={p.id}
                data-testid={`admin-product-${p.id}`}
                className="group bg-white rounded-xl border border-neutral-200 overflow-hidden hover:shadow-md transition"
              >
                <div className="aspect-[4/3] bg-neutral-200 relative">
                  {p.images?.[0] ? (
                    <img src={p.images[0]} alt={p.name?.fr} className="w-full h-full object-cover" />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-neutral-400">
                      <Storefront size={40} weight="thin" />
                    </div>
                  )}
                  {p.featured && (
                    <div className="absolute top-2 left-2 bg-neutral-900 text-white text-[10px] uppercase tracking-widest px-2 py-0.5 rounded-full flex items-center gap-1">
                      <Star size={10} weight="fill" /> Phare
                    </div>
                  )}
                  <div className="absolute top-2 right-2">
                    <span
                      className={`text-[10px] uppercase tracking-widest px-2 py-0.5 rounded-full ${
                        p.status === "active"
                          ? "bg-emerald-500/10 text-emerald-400"
                          : "bg-[#F5F5F4] text-neutral-500"
                      }`}
                    >
                      {p.status}
                    </span>
                  </div>
                </div>
                <div className="p-4">
                  <div className="font-medium text-neutral-900 line-clamp-2 min-h-[2.5rem]" title={p.name?.fr}>
                    {p.name?.fr || "(sans nom)"}
                  </div>
                  {/* Prices row */}
                  <div className="mt-3 grid grid-cols-2 gap-2">
                    <div className="bg-neutral-50 rounded-lg px-2.5 py-1.5">
                      <div className="text-[10px] uppercase tracking-widest text-neutral-500">Achat HT</div>
                      <div className="font-mono text-sm font-semibold text-neutral-900">
                        {p.cost_price_ht?.toFixed(2) || "—"}€
                      </div>
                    </div>
                    <div className="bg-amber-50 rounded-lg px-2.5 py-1.5">
                      <div className="text-[10px] uppercase tracking-widest text-amber-700">Vente TTC</div>
                      <div className="font-mono text-sm font-semibold text-amber-900">
                        {p.price?.toFixed(2) || "—"}€
                      </div>
                    </div>
                  </div>
                  {/* Margin */}
                  {p.cost_price_ht > 0 && p.price > 0 && (() => {
                    const ht = p.price / 1.2;
                    const m = ht - p.cost_price_ht;
                    const pct = ht > 0 ? (m / ht) * 100 : 0;
                    return (
                      <div className="mt-1.5 flex items-center justify-between text-[11px]">
                        <span className="text-neutral-500">Marge</span>
                        <span
                          className="font-semibold"
                          style={{ color: m <= 0 ? "#BE123C" : pct < 30 ? "#854D0E" : "#047857" }}
                        >
                          {m.toFixed(2)}€ · {pct.toFixed(0)}%
                        </span>
                      </div>
                    );
                  })()}
                  {/* Shipping status (informative only — CJ API can't reliably confirm country-level coverage) */}
                  {p.shipping && Object.keys(p.shipping).length > 0 && (
                    <div className="mt-2 pt-2 border-t border-neutral-100">
                      <div className="text-[10px] uppercase tracking-widest text-neutral-500 mb-1">Livraison</div>
                      <div className="flex flex-wrap gap-1">
                        {Object.entries(p.shipping).map(([cc, info]) => {
                          const status = info?.available;
                          return (
                            <span
                              key={cc}
                              title={status === true ? `${info.carrier} · ${info.delivery_days}j` :
                                     status === false ? "Non couvert par l'API freight" :
                                     "À vérifier sur la fiche CJ (lien dans l'édition)"}
                              className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${
                                status === true ? "bg-emerald-50 text-emerald-700" :
                                status === false ? "bg-red-50 text-red-700" :
                                "bg-neutral-100 text-neutral-600"
                              }`}
                            >
                              {status === true ? "✓" : status === false ? "✗" : "?"} {cc}
                            </span>
                          );
                        })}
                      </div>
                    </div>
                  )}
                  {/* Specs mini */}
                  {p.specs?.weight_kg && (
                    <div className="mt-2 text-[11px] text-neutral-500">
                      {p.specs.weight_kg}kg · {p.images?.length || 0} photos
                      {p.variants?.length > 1 ? ` · ${p.variants.length} variantes` : ""}
                    </div>
                  )}
                  {/* Warnings */}
                  {p.translation_status === "fallback_original" && (
                    <div className="mt-2 text-[10px] bg-amber-50 text-amber-700 px-2 py-1 rounded flex items-center gap-1">
                      <Warning size={10} weight="fill" /> Traduction IA à refaire
                    </div>
                  )}
                  {/* Actions (edit + delete only — IA & resync moved to side panel) */}
                  <div className="flex items-center gap-2 mt-3">
                    <button
                      onClick={() => setEditing(p)}
                      data-testid={`edit-${p.id}`}
                      className="flex-1 h-9 rounded-lg bg-neutral-900 hover:bg-neutral-800 text-[13px] text-white font-medium flex items-center justify-center gap-1.5 transition"
                    >
                      <PencilSimple size={14} /> Éditer
                    </button>
                    <button
                      onClick={() => handleDelete(p)}
                      data-testid={`delete-${p.id}`}
                      title="Supprimer ce produit"
                      className="h-9 w-9 rounded-lg border border-neutral-200 hover:border-[#BE123C] hover:text-red-400 text-neutral-500 flex items-center justify-center transition"
                    >
                      <Trash size={14} />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {editing && (
        <ProductEditor
          siteId={siteId}
          initial={editing}
          onClose={() => setEditing(null)}
          onSaved={() => {
            setEditing(null);
            load();
          }}
          onEnrichNarrative={() => handleEnrichNarrative(editing)}
          enriching={enriching === editing.id}
          onResync={() => handleResync(editing)}
          syncing={syncing === editing.id}
        />
      )}

      {syncResult && (
        <ResyncModal
          result={syncResult}
          onClose={() => setSyncResult(null)}
          onApply={handleApplyResync}
        />
      )}
    </Layout>
  );
}

function ResyncModal({ result, onClose, onApply }) {
  const { product, diff } = result;
  const priceChanged = diff.price?.diff && Math.abs(diff.price.diff) > 0.01;
  const bigIncrease = diff.price?.diff_pct > 10;
  const hasMargin = product.price && diff.price?.new
    ? ((product.price - diff.price.new) / product.price) * 100
    : null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" onClick={onClose} data-testid="resync-modal">
      <div className="absolute inset-0 bg-neutral-900/40 backdrop-blur-sm" />
      <div className="relative w-full max-w-lg bg-white rounded-md shadow-2xl border border-neutral-200 overflow-hidden animate-fade-up" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between px-6 py-4 border-b border-neutral-200">
          <div>
            <div className="text-[11px] uppercase tracking-widest text-neutral-500">Re-sync fournisseur</div>
            <div className="text-base font-semibold text-neutral-900 truncate max-w-xs">
              {product.name?.fr || "Produit"}
            </div>
          </div>
          <button onClick={onClose} className="p-2 rounded-lg hover:bg-neutral-200"><X size={18} /></button>
        </div>

        <div className="p-6 space-y-4">
          <div className="flex items-center gap-2 text-xs text-neutral-500">
            <ArrowsClockwise size={12} /> Source : {diff.source_host || "Fournisseur"}
          </div>

          {priceChanged ? (
            <div className={`p-4 rounded-xl border-2 ${bigIncrease ? "bg-red-500/10 border-[#FCA5A5]" : "bg-amber-500/10 border-[#FCD34D]"}`} data-testid="price-change-panel">
              <div className="flex items-center gap-2 mb-2">
                {bigIncrease ? (
                  <><Warning size={16} weight="fill" className="text-red-400" /><span className="text-sm font-medium text-red-400">Hausse significative du prix fournisseur</span></>
                ) : (
                  <><TrendUp size={16} weight="fill" className="text-[#854D0E]" /><span className="text-sm font-medium text-[#854D0E]">Prix fournisseur à jour</span></>
                )}
              </div>
              <div className="grid grid-cols-3 gap-3 text-center">
                <div>
                  <div className="text-[10px] uppercase tracking-widest text-neutral-500">Ancien</div>
                  <div className="text-lg font-semibold text-neutral-900 mt-1 tabular-nums">{diff.price.old}€</div>
                </div>
                <div>
                  <div className="text-[10px] uppercase tracking-widest text-neutral-500">Nouveau</div>
                  <div className="text-lg font-semibold text-neutral-900 mt-1 tabular-nums">{diff.price.new}€</div>
                </div>
                <div>
                  <div className="text-[10px] uppercase tracking-widest text-neutral-500">Variation</div>
                  <div className="text-lg font-semibold mt-1 tabular-nums" style={{ color: bigIncrease ? "#BE123C" : "#854D0E" }}>
                    {diff.price.diff > 0 ? "+" : ""}{diff.price.diff}€ ({diff.price.diff_pct > 0 ? "+" : ""}{diff.price.diff_pct}%)
                  </div>
                </div>
              </div>
              {hasMargin !== null && hasMargin < 30 && (
                <div className="mt-3 text-xs text-red-400 flex items-start gap-1.5">
                  <Warning size={12} weight="fill" className="mt-0.5 flex-shrink-0" />
                  Ta marge risque de descendre sous 30% à ce nouveau prix. Revois ton prix de vente.
                </div>
              )}
            </div>
          ) : (
            <div className="p-4 rounded-xl bg-[#DCF5E7] border-2 border-[#86EFAC] flex items-center gap-2" data-testid="no-change-panel">
              <CheckCircle size={16} weight="fill" className="text-[#166534]" />
              <span className="text-sm text-[#166534] font-medium">Aucun changement de prix détecté.</span>
            </div>
          )}

          {diff.has_new_images && (
            <div className="p-3 rounded-xl bg-[#DBEAFE] border border-[#93C5FD] text-sm text-[#1E40AF]">
              📸 {diff.fresh_images_count} images côté fournisseur (tu en as {diff.current_images_count}).
            </div>
          )}
        </div>

        <div className="px-6 py-4 bg-white border-t border-neutral-200 flex items-center justify-end gap-3">
          <button onClick={onClose} className="h-10 px-4 rounded-xl border border-neutral-200 bg-white text-sm text-neutral-600 hover:bg-neutral-200 transition">
            Fermer
          </button>
          {priceChanged && (
            <button
              onClick={onApply}
              data-testid="apply-resync"
              className="h-10 px-4 rounded-xl bg-neutral-900 hover:bg-neutral-800 text-white text-sm font-medium flex items-center gap-2 transition"
            >
              <CheckCircle size={14} weight="fill" /> Appliquer le nouveau prix
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

function ProductEditor({ siteId, initial, onClose, onSaved, onEnrichNarrative, enriching, onResync, syncing }) {
  const isNew = !initial.id;
  const hasSupplier = !!(initial.supplier_url && initial.source);
  const specs = initial.specs || {};
  const shipping = initial.shipping || {};
  const variants = initial.variants || [];
  const [form, setForm] = useState(() => ({
    ...initial,
    name: { fr: "", en: "", de: "", nl: "", ...(initial.name || {}) },
    description: { fr: "", en: "", de: "", nl: "", ...(initial.description || {}) },
    images: initial.images?.length ? initial.images : [""],
  }));
  const [activeLang, setActiveLang] = useState("fr");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [aiImgBusy, setAiImgBusy] = useState(false);
  const [aiImgStyle, setAiImgStyle] = useState("lifestyle");
  const [aiImgResult, setAiImgResult] = useState(null);

  const setI18n = (field, lang, value) => {
    setForm((f) => ({ ...f, [field]: { ...f[field], [lang]: value } }));
  };

  const genAiImage = async () => {
    if (isNew) { window.alert("Enregistre d'abord le produit."); return; }
    setAiImgBusy(true);
    setAiImgResult(null);
    const { data, error: err, rawDetail } = await apiCall(() =>
      api.post(`/products/${initial.id}/generate-image`, {
        style: aiImgStyle, tweak: "", replace_main: false,
      })
    );
    setAiImgBusy(false);
    if (err) { window.alert(rawDetail?.detail || err); return; }
    setAiImgResult(data);
    // Prepend the new image to the local form so it shows up immediately
    setForm((f) => ({ ...f, images: [data.url, ...(f.images || [])].filter(Boolean).slice(0, 10) }));
  };

  const genEditorialSet = async () => {
    if (isNew) { window.alert("Enregistre d'abord le produit."); return; }
    if (!window.confirm(
      "Générer 4 images IA éditoriales (closeup × 2, studio, lifestyle) ?\n\n" +
      "• Durée : environ 60 à 90 s au total\n" +
      "• Ces images alimentent la mosaïque éditoriale de la fiche produit"
    )) return;
    setAiImgBusy(true);
    setAiImgResult(null);
    const jobs = [
      { style: "closeup", tweak: "Détail macro de la texture du tissu, gros plan ultra-détaillé" },
      { style: "closeup", tweak: "Détail fonctionnel du produit (bouton, commande, mécanisme), gros plan cinématique" },
      { style: "lifestyle", tweak: "Scène de vie apaisée dans un intérieur épuré, lumière naturelle" },
      { style: "studio", tweak: "Vue produit 3/4 sur fond crème très clair, éclairage softbox éditorial" },
    ];
    let ok = 0, lastErr = null;
    for (const j of jobs) {
      const { data, error: err, rawDetail } = await apiCall(() =>
        api.post(`/products/${initial.id}/generate-image`, { ...j, replace_main: false })
      );
      if (err) { lastErr = rawDetail?.detail || err; break; }
      if (data?.url) ok += 1;
    }
    setAiImgBusy(false);
    if (lastErr) {
      window.alert(`Série interrompue après ${ok} image(s) : ${lastErr}`);
    } else {
      setAiImgResult({ message: `${ok} images éditoriales générées. Recharge la page produit pour les voir.` });
    }
  };

  const submit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError("");
    const payload = {
      name: form.name,
      description: form.description,
      price: parseFloat(form.price) || 0,
      cost_price_ht: parseFloat(form.cost_price_ht) || 0,
      compare_at_price: form.compare_at_price ? parseFloat(form.compare_at_price) : null,
      currency: form.currency || "EUR",
      images: form.images.filter(Boolean),
      stock: form.stock === "" || form.stock === null ? null : parseInt(form.stock, 10),
      supplier_url: form.supplier_url || "",
      sku: form.sku || "",
      status: form.status || "active",
      featured: !!form.featured,
    };
    const { error: err } = isNew
      ? await apiCall(() => api.post(`/sites/${siteId}/products`, payload))
      : await apiCall(() => api.patch(`/sites/${siteId}/products/${initial.id}`, payload));
    setSaving(false);
    if (err) setError(err);
    else onSaved();
  };

  return (
    <div className="fixed inset-0 z-50 flex" data-testid="product-editor">
      <div className="flex-1 bg-neutral-900/40" onClick={onClose} />
      <div className="w-full max-w-2xl bg-white h-full overflow-y-auto shadow-2xl animate-slide-in-right">
        <div className="sticky top-0 bg-white border-b border-neutral-200 px-6 py-4 flex items-center justify-between z-10">
          <div>
            <div className="text-[11px] uppercase tracking-widest text-neutral-500">
              {isNew ? "Nouveau" : "Édition"}
            </div>
            <div className="text-base font-semibold text-neutral-900 line-clamp-1">
              {form.name?.fr || "Produit"}
            </div>
          </div>
          <button onClick={onClose} className="p-2 rounded-lg hover:bg-neutral-200" data-testid="editor-close">
            <X size={20} />
          </button>
        </div>

        {/* Supplier actions bar (only for imported products) */}
        {!isNew && hasSupplier && (
          <div className="border-b border-neutral-200 bg-neutral-50 px-6 py-3 flex items-center gap-2 flex-wrap">
            <div className="text-[11px] uppercase tracking-widest text-neutral-500 mr-2">Actions fournisseur</div>
            <button
              type="button"
              onClick={onEnrichNarrative}
              disabled={enriching}
              data-testid="panel-enrich-ia"
              className={`h-8 px-3 rounded-lg border text-[12px] font-medium flex items-center gap-1.5 transition disabled:opacity-50 ${
                initial.narrative
                  ? "border-emerald-200 bg-white text-emerald-700 hover:border-emerald-400"
                  : "border-neutral-200 bg-white text-neutral-700 hover:border-neutral-900"
              }`}
            >
              <SparkleIcon size={12} weight={initial.narrative ? "fill" : "regular"} className={enriching ? "animate-pulse" : ""} />
              {enriching ? "Génération…" : initial.narrative ? "Régénérer IA" : "Générer IA"}
            </button>
            <div className="flex items-center gap-1">
              <select
                value={aiImgStyle}
                onChange={(e) => setAiImgStyle(e.target.value)}
                disabled={aiImgBusy}
                data-testid="ai-img-style"
                className="h-8 px-2 rounded-lg border border-neutral-200 bg-white text-[12px] font-medium text-neutral-700 focus:outline-none"
              >
                <option value="lifestyle">Lifestyle</option>
                <option value="studio">Studio</option>
                <option value="closeup">Gros plan</option>
                <option value="in_use">En usage</option>
              </select>
              <button
                type="button"
                onClick={genAiImage}
                disabled={aiImgBusy}
                data-testid="ai-img-generate"
                className="h-8 px-3 rounded-lg border border-violet-200 bg-violet-50 text-[12px] font-medium text-violet-700 hover:border-violet-400 flex items-center gap-1.5 transition disabled:opacity-50"
              >
                <SparkleIcon size={12} weight="fill" className={aiImgBusy ? "animate-pulse" : ""} />
                {aiImgBusy ? "Nano Banana…" : "Image IA"}
              </button>
              <button
                type="button"
                onClick={genEditorialSet}
                disabled={aiImgBusy}
                data-testid="ai-img-editorial-set"
                className="h-8 px-3 rounded-lg bg-neutral-900 text-[12px] font-semibold text-white hover:bg-neutral-800 flex items-center gap-1.5 transition disabled:opacity-50"
                title="Génère 4 images (2 gros plans + studio + lifestyle) pour la mosaïque éditoriale"
              >
                <SparkleIcon size={12} weight="fill" className={aiImgBusy ? "animate-pulse" : ""} />
                {aiImgBusy ? "Série…" : "Série éditoriale (4 img)"}
              </button>
            </div>
            <button
              type="button"
              onClick={onResync}
              disabled={syncing}
              data-testid="panel-resync"
              className="h-8 px-3 rounded-lg border border-neutral-200 bg-white text-[12px] font-medium text-neutral-700 hover:border-neutral-900 flex items-center gap-1.5 transition disabled:opacity-50"
            >
              <ArrowsClockwise size={12} className={syncing ? "animate-spin" : ""} />
              {syncing ? "Sync…" : "Vérifier prix fournisseur"}
            </button>
            {initial.supplier_url && (
              <a
                href={initial.supplier_url}
                target="_blank"
                rel="noreferrer"
                className="h-8 px-3 rounded-lg border border-neutral-200 bg-white text-[12px] font-medium text-neutral-700 hover:border-neutral-900 flex items-center gap-1.5 transition"
              >
                Voir fiche {(initial.source?.provider || "").toUpperCase()} ↗
              </a>
            )}
          </div>
        )}

        {/* Supplier data summary */}
        {!isNew && hasSupplier && (
          <div className="border-b border-neutral-200 px-6 py-4 bg-white" data-testid="supplier-panel">
            <div className="text-[11px] uppercase tracking-widest text-neutral-500 mb-2">Données fournisseur</div>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-2 text-xs">
              {specs.weight_kg && (
                <Info label="Poids" value={`${specs.weight_kg} kg`} />
              )}
              {specs.category && (
                <Info label="Catégorie" value={specs.category.split("/").slice(-1)[0]} />
              )}
              {specs.material && (
                <Info label="Matériau" value={specs.material} />
              )}
              {specs.packing && (
                <Info label="Emballage" value={specs.packing} />
              )}
              {specs.supplier_sku && (
                <Info label="SKU fournisseur" value={specs.supplier_sku} mono />
              )}
              {initial.suggested_sell_price_usd && (
                <Info label="Prix suggéré (USD)" value={`$${initial.suggested_sell_price_usd.toFixed(2)}`} />
              )}
              {variants.length > 0 && (
                <Info label="Variantes" value={`${variants.length}`} />
              )}
            </div>

            {/* Shipping per country — informational only (CJ API cannot reliably confirm country coverage) */}
            {Object.keys(shipping).length > 0 && (
              <div className="mt-3 pt-3 border-t border-neutral-100">
                <div className="text-[11px] uppercase tracking-widest text-neutral-500 mb-2 flex items-center gap-1">
                  Livraison par pays
                  <span className="text-[9px] normal-case tracking-normal text-neutral-400">(à vérifier sur CJ)</span>
                </div>
                <div className="space-y-1">
                  {Object.entries(shipping).map(([cc, info]) => {
                    const status = info?.available;
                    return (
                      <div
                        key={cc}
                        className={`flex items-center justify-between text-xs px-3 py-1.5 rounded-lg ${
                          status === true ? "bg-emerald-50" :
                          status === false ? "bg-red-50" :
                          "bg-neutral-50"
                        }`}
                        data-testid={`ship-${cc}`}
                      >
                        <div className="flex items-center gap-2">
                          <span className={
                            status === true ? "text-emerald-700" :
                            status === false ? "text-red-700" :
                            "text-neutral-500"
                          }>
                            {status === true ? "✓" : status === false ? "✗" : "?"}
                          </span>
                          <span className="font-semibold">{cc}</span>
                          {status === true && (
                            <span className="text-neutral-600">{info.carrier} · {info.delivery_days}j</span>
                          )}
                        </div>
                        {status === true && (
                          <span className="font-mono text-[11px] text-neutral-700">${info.price_usd?.toFixed(2)}</span>
                        )}
                        {status === null && (
                          <span className="text-[10px] text-neutral-500 font-medium">À vérifier sur la fiche CJ</span>
                        )}
                        {status === false && (
                          <span className="text-[10px] text-red-700 font-medium">Non couvert</span>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Variants list */}
            {variants.length > 1 && (
              <div className="mt-3 pt-3 border-t border-neutral-100">
                <div className="text-[11px] uppercase tracking-widest text-neutral-500 mb-2">
                  Variantes importées
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {variants.map((v) => (
                    <span
                      key={v.vid}
                      title={`${v.sku} · ${v.sell_price_usd || "—"}$`}
                      className="text-[11px] px-2 py-1 rounded-full bg-neutral-100 text-neutral-700"
                    >
                      {v.name || v.sku}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        <form onSubmit={submit} className="p-6 space-y-6">
          {/* Tabs i18n */}
          <div>
            <div className="flex items-center gap-1 mb-3" data-testid="lang-tabs">
              {LANGS.map((l) => (
                <button
                  key={l.code}
                  type="button"
                  onClick={() => setActiveLang(l.code)}
                  data-testid={`lang-tab-${l.code}`}
                  className={`h-8 px-3 rounded-full text-xs font-medium transition ${
                    activeLang === l.code
                      ? "bg-white text-neutral-900"
                      : "bg-white border border-neutral-200 text-neutral-600 hover:border-[#B84B31]"
                  }`}
                >
                  {l.label}
                </button>
              ))}
            </div>

            <div className="space-y-4">
              <Field
                label={`Nom (${activeLang.toUpperCase()}) ${activeLang === "fr" ? "*" : ""}`}
                value={form.name[activeLang]}
                onChange={(v) => setI18n("name", activeLang, v)}
                testId={`name-${activeLang}`}
                required={activeLang === "fr"}
              />
              <div>
                <label className="block text-[13px] font-medium text-neutral-900 mb-1.5">
                  Description ({activeLang.toUpperCase()})
                </label>
                <textarea
                  value={form.description[activeLang]}
                  onChange={(e) => setI18n("description", activeLang, e.target.value)}
                  rows={5}
                  data-testid={`desc-${activeLang}`}
                  className="w-full px-4 py-3 rounded-xl border border-neutral-200 bg-white focus:ring-2 focus:ring-zinc-500/30 focus:border-neutral-400 outline-none resize-none"
                />
              </div>
            </div>
          </div>

          {/* Price */}
          <div className="grid grid-cols-2 gap-4">
            <Field
              label="Prix de vente TTC (€) *"
              type="number"
              value={form.price}
              onChange={(v) => setForm({ ...form, price: v })}
              testId="price"
              required
            />
            <Field
              label="Prix barré TTC (optionnel)"
              type="number"
              value={form.compare_at_price || ""}
              onChange={(v) => setForm({ ...form, compare_at_price: v })}
              testId="compare-price"
            />
          </div>

          {/* Cost price HT + margin preview */}
          <div className="grid grid-cols-2 gap-4">
            <Field
              label="Prix d'achat HT fournisseur (€) *"
              type="number"
              value={form.cost_price_ht}
              onChange={(v) => setForm({ ...form, cost_price_ht: v })}
              testId="cost-price-ht"
              required
            />
            <MarginPreview price={form.price} costHt={form.cost_price_ht} />
          </div>

          {/* Images */}
          <ImagesField
            images={form.images}
            onChange={(imgs) => setForm({ ...form, images: imgs.length ? imgs : [""] })}
          />

          {/* Extras */}
          <div className="grid grid-cols-2 gap-4">
            <Field label="SKU" value={form.sku} onChange={(v) => setForm({ ...form, sku: v })} testId="sku" />
            <Field
              label="Stock (vide = illimité)"
              type="number"
              value={form.stock ?? ""}
              onChange={(v) => setForm({ ...form, stock: v })}
              testId="stock"
            />
          </div>

          <Field
            label="URL fournisseur (CJ / BigBuy / AliExpress)"
            value={form.supplier_url}
            onChange={(v) => setForm({ ...form, supplier_url: v })}
            testId="supplier-url"
          />

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-[13px] font-medium text-neutral-900 mb-1.5">Statut</label>
              <select
                value={form.status}
                onChange={(e) => setForm({ ...form, status: e.target.value })}
                data-testid="status"
                className="w-full h-11 px-4 rounded-xl border border-neutral-200 bg-white outline-none"
              >
                <option value="active">Actif (publié)</option>
                <option value="draft">Brouillon</option>
                <option value="archived">Archivé</option>
              </select>
            </div>
            <label className="flex items-center gap-2 pt-7 cursor-pointer" data-testid="featured-toggle">
              <input
                type="checkbox"
                checked={!!form.featured}
                onChange={(e) => setForm({ ...form, featured: e.target.checked })}
                className="w-4 h-4 accent-[#B84B31]"
              />
              <span className="text-sm text-neutral-900">Produit phare (en haut de la boutique)</span>
            </label>
          </div>

          {error && (
            <div className="p-3 rounded-lg bg-red-500/10 text-red-400 text-sm" data-testid="editor-error">
              {error}
            </div>
          )}

          {/* Narrative sections editor — detailed per-product storytelling */}
          {!isNew && (
            <NarrativeSectionsEditor productId={initial.id} narrative={initial.narrative} />
          )}

          <div className="flex items-center justify-end gap-3 pt-4 border-t border-neutral-200">
            <button
              type="button"
              onClick={onClose}
              className="h-11 px-5 rounded-xl border border-neutral-200 text-neutral-600 hover:bg-white transition"
            >
              Annuler
            </button>
            <button
              type="submit"
              disabled={saving}
              data-testid="save-product"
              className="h-11 px-5 rounded-xl bg-neutral-900 hover:bg-neutral-800 text-white font-medium flex items-center gap-2 transition active:scale-[0.98] disabled:opacity-60"
            >
              {saving ? "…" : (
                <>
                  <CheckCircle size={16} weight="fill" /> {isNew ? "Créer" : "Enregistrer"}
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function Field({ label, value, onChange, type = "text", required, testId }) {
  return (
    <div>
      <label className="block text-[13px] font-medium text-neutral-900 mb-1.5">{label}</label>
      <input
        type={type}
        value={value}
        step={type === "number" ? "0.01" : undefined}
        onChange={(e) => onChange(e.target.value)}
        required={required}
        data-testid={`field-${testId}`}
        className="w-full h-11 px-4 rounded-xl border border-neutral-200 bg-white focus:ring-2 focus:ring-zinc-500/30 focus:border-neutral-400 outline-none"
      />
    </div>
  );
}

function MarginPreview({ price, costHt, vatRate = 0.20 }) {
  const p = parseFloat(price) || 0;
  const c = parseFloat(costHt) || 0;
  const ht = p > 0 ? p / (1 + vatRate) : 0;
  const margin = ht - c;
  const marginPct = ht > 0 ? (margin / ht) * 100 : 0;
  const concepteur = margin > 0 ? margin * 0.5 : 0;
  const color = margin <= 0 ? "#BE123C" : marginPct < 30 ? "#854D0E" : "#047857";
  return (
    <div className="h-11 px-3 rounded-xl border border-dashed border-neutral-200 bg-white flex items-center" data-testid="margin-preview">
      <div className="text-[11px] text-neutral-500 mr-2">Marge HT</div>
      <div className="font-heading tabular-nums text-sm font-semibold" style={{ color }}>
        {margin.toFixed(2)}€ ({marginPct.toFixed(0)}%)
      </div>
      <div className="text-[11px] text-neutral-500 ml-auto">
        50% Concepteur&nbsp;: <span className="font-medium text-neutral-900">{concepteur.toFixed(2)}€</span>
      </div>
    </div>
  );
}

/* ================================================================
 * ImagesField — gallery with upload + URL dual mode, drag&drop reorder
 * ================================================================ */
function ImagesField({ images, onChange }) {
  const [uploading, setUploading] = useState(false);
  const [urlInput, setUrlInput] = useState("");
  const [error, setError] = useState("");
  const [dragOver, setDragOver] = useState(false);
  const fileRef = React.useRef(null);

  const clean = images.filter(Boolean);

  const handleFiles = async (files) => {
    if (!files || files.length === 0) return;
    setUploading(true);
    setError("");
    const uploaded = [];
    for (const file of Array.from(files)) {
      const fd = new FormData();
      fd.append("file", file);
      try {
        const res = await fetch(`${BACKEND_URL}/api/uploads/image`, {
          method: "POST",
          credentials: "include",
          body: fd,
        });
        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          setError(err.detail || `Upload échoué (HTTP ${res.status})`);
          continue;
        }
        const data = await res.json();
        uploaded.push(`${BACKEND_URL}${data.url}`);
      } catch (e) {
        setError("Erreur réseau durant l'upload.");
      }
    }
    setUploading(false);
    if (uploaded.length) {
      onChange([...clean, ...uploaded]);
    }
  };

  const addFromUrl = () => {
    if (!urlInput.trim()) return;
    onChange([...clean, urlInput.trim()]);
    setUrlInput("");
  };

  const remove = (idx) => {
    const next = clean.filter((_, i) => i !== idx);
    onChange(next);
  };

  const move = (from, to) => {
    if (from === to || to < 0 || to >= clean.length) return;
    const next = [...clean];
    const [m] = next.splice(from, 1);
    next.splice(to, 0, m);
    onChange(next);
  };

  return (
    <div data-testid="images-field">
      <label className="block text-[13px] font-medium text-neutral-900 mb-1.5">
        Images <span className="text-neutral-500 font-normal">· La 1ère est l'image principale</span>
      </label>

      {/* Gallery */}
      {clean.length > 0 && (
        <div className="grid grid-cols-4 gap-2 mb-3">
          {clean.map((url, idx) => (
            <div
              key={`${url}-${idx}`}
              data-testid={`image-thumb-${idx}`}
              className="relative aspect-square rounded-lg overflow-hidden bg-neutral-200 border border-neutral-200 group"
            >
              <img src={url} alt="" className="w-full h-full object-cover" />
              {idx === 0 && (
                <div className="absolute top-1 left-1 bg-neutral-900 text-white text-[9px] uppercase tracking-widest px-1.5 py-0.5 rounded-full">
                  Principale
                </div>
              )}
              <div className="absolute inset-0 bg-neutral-900/40 opacity-0 group-hover:opacity-100 flex items-center justify-center gap-1 transition">
                {idx > 0 && (
                  <button
                    type="button"
                    onClick={() => move(idx, idx - 1)}
                    className="w-7 h-7 rounded-full bg-white text-neutral-900 flex items-center justify-center text-xs hover:scale-110 transition"
                    title="Remonter"
                  >
                    ←
                  </button>
                )}
                {idx < clean.length - 1 && (
                  <button
                    type="button"
                    onClick={() => move(idx, idx + 1)}
                    className="w-7 h-7 rounded-full bg-white text-neutral-900 flex items-center justify-center text-xs hover:scale-110 transition"
                    title="Descendre"
                  >
                    →
                  </button>
                )}
                <button
                  type="button"
                  onClick={() => remove(idx)}
                  data-testid={`remove-image-${idx}`}
                  className="w-7 h-7 rounded-full bg-white text-red-400 flex items-center justify-center hover:scale-110 transition"
                  title="Supprimer"
                >
                  <Trash size={12} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Dropzone */}
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          handleFiles(e.dataTransfer.files);
        }}
        onClick={() => fileRef.current?.click()}
        data-testid="image-dropzone"
        className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition ${
          dragOver
            ? "border-[#B84B31] bg-[#FDF4E7]"
            : "border-neutral-200 bg-white hover:border-[#B84B31]/50"
        }`}
      >
        <UploadSimple size={24} weight="regular" className="mx-auto text-neutral-900 mb-2" />
        <div className="text-sm text-neutral-900">
          {uploading ? (
            "Upload en cours..."
          ) : (
            <>
              <span className="font-medium">Clique ou dépose</span> des images (.jpg, .png, .webp · max 8 Mo)
            </>
          )}
        </div>
        <input
          ref={fileRef}
          type="file"
          accept="image/*"
          multiple
          hidden
          onChange={(e) => handleFiles(e.target.files)}
          data-testid="image-file-input"
        />
      </div>

      {/* Alt : URL input */}
      <div className="flex gap-2 mt-3">
        <input
          value={urlInput}
          onChange={(e) => setUrlInput(e.target.value)}
          placeholder="...ou colle une URL d'image (https://...)"
          data-testid="image-url-input"
          onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), addFromUrl())}
          className="flex-1 h-10 px-3 rounded-lg border border-neutral-200 bg-white focus:ring-2 focus:ring-zinc-500/30 focus:border-neutral-400 outline-none text-sm"
        />
        <button
          type="button"
          onClick={addFromUrl}
          data-testid="image-url-add"
          disabled={!urlInput.trim()}
          className="h-10 px-4 rounded-lg border border-neutral-200 bg-white text-sm text-neutral-900 hover:border-[#B84B31] disabled:opacity-40"
        >
          <ImageIcon size={14} className="inline mr-1" /> Ajouter
        </button>
      </div>

      {error && (
        <div className="mt-2 text-sm text-red-400" data-testid="image-error">
          {error}
        </div>
      )}
    </div>
  );
}



function Info({ label, value, mono }) {
  return (
    <div className="bg-neutral-50 rounded-lg px-2.5 py-1.5">
      <div className="text-[10px] uppercase tracking-widest text-neutral-500 truncate">{label}</div>
      <div className={`text-[12px] font-semibold text-neutral-900 truncate ${mono ? "font-mono" : ""}`} title={value}>
        {value}
      </div>
    </div>
  );
}

// =====================================================================
// NarrativeSectionsEditor — per-product detailed sections with IA images
// =====================================================================
function NarrativeSectionsEditor({ productId, narrative }) {
  const sections = Array.isArray(narrative?.sections) ? narrative.sections : [];
  const [open, setOpen] = useState(sections.length > 0);
  const [busyIdx, setBusyIdx] = useState(null);
  const [style, setStyle] = useState("lifestyle");
  const [localSections, setLocalSections] = useState(sections);

  React.useEffect(() => {
    setLocalSections(Array.isArray(narrative?.sections) ? narrative.sections : []);
  }, [narrative]);

  const genImage = async (idx) => {
    setBusyIdx(idx);
    const { data, error: err, rawDetail } = await apiCall(() =>
      api.post(`/products/${productId}/generate-section-image`, {
        section_index: idx, style, tweak: "",
      })
    );
    setBusyIdx(null);
    if (err) { window.alert(rawDetail?.detail || err); return; }
    setLocalSections((prev) => prev.map((s, i) => (i === idx ? { ...s, image: data.url } : s)));
  };

  if (!localSections.length) {
    return (
      <div className="bg-violet-50/60 border border-violet-200 rounded-xl p-4 text-sm text-violet-900 flex items-start gap-2">
        <SparkleIcon size={16} weight="duotone" className="flex-shrink-0 mt-0.5" />
        <span>
          Pas de sections détaillées pour ce produit. Clique sur <strong>Générer IA</strong> ci-dessus
          pour créer automatiquement les textes narratifs (titre, histoire, usage, bénéfices, FAQ).
          Chaque section pourra ensuite recevoir une image IA dédiée.
        </span>
      </div>
    );
  }

  return (
    <div className="border border-neutral-200 rounded-xl overflow-hidden" data-testid="narrative-sections-editor">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between px-5 py-3 bg-neutral-50 hover:bg-neutral-100 transition text-left"
      >
        <div>
          <div className="text-sm font-semibold text-neutral-900">
            Sections détaillées de la fiche produit ({localSections.length})
          </div>
          <div className="text-xs text-neutral-500 mt-0.5">
            Ces blocs s'affichent sous la fiche produit. Génère une image IA par section.
          </div>
        </div>
        <span className="text-lg text-neutral-400">{open ? "−" : "+"}</span>
      </button>
      {open && (
        <div className="p-5 space-y-4">
          <div className="flex items-center gap-2 flex-wrap">
            <label className="text-xs text-neutral-500">Style d'image par défaut :</label>
            <select value={style} onChange={(e) => setStyle(e.target.value)}
              data-testid="narrative-img-style"
              className="h-8 px-2 rounded border border-neutral-200 bg-white text-xs">
              <option value="lifestyle">Lifestyle</option>
              <option value="studio">Studio</option>
              <option value="closeup">Gros plan</option>
              <option value="in_use">En usage</option>
            </select>
          </div>
          {localSections.map((s, i) => (
            <div key={i} className="border border-neutral-200 rounded-lg p-4 bg-white"
              data-testid={`narrative-section-${i}`}>
              <div className="flex items-start gap-4">
                <div className="flex-1 min-w-0">
                  <div className="text-[10px] uppercase tracking-widest text-neutral-400 mb-1">
                    Section {String(i + 1).padStart(2, "0")}
                  </div>
                  <div className="text-sm font-semibold text-neutral-900 mb-2">
                    {s.title || "(sans titre)"}
                  </div>
                  <div className="text-xs text-neutral-600 leading-relaxed line-clamp-4">
                    {s.body || "(pas de contenu)"}
                  </div>
                  {s.bullet_points?.length > 0 && (
                    <ul className="mt-2 space-y-1">
                      {s.bullet_points.slice(0, 3).map((bp, j) => (
                        <li key={j} className="text-[11px] text-neutral-500 flex gap-1.5">
                          <span className="text-emerald-600">✓</span>{bp}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
                <div className="w-28 shrink-0">
                  {s.image ? (
                    <div className="relative aspect-[4/3] rounded-lg overflow-hidden bg-neutral-100 border border-neutral-200">
                      <img src={s.image} alt="" className="w-full h-full object-cover" />
                    </div>
                  ) : (
                    <div className="aspect-[4/3] rounded-lg border border-dashed border-neutral-300 bg-neutral-50 flex items-center justify-center text-[10px] text-neutral-400">
                      Pas d'image
                    </div>
                  )}
                  <button
                    type="button"
                    onClick={() => genImage(i)}
                    disabled={busyIdx === i}
                    data-testid={`gen-section-img-${i}`}
                    className="mt-2 w-full h-8 px-2 rounded-lg bg-violet-600 hover:bg-violet-700 text-white text-[11px] font-semibold flex items-center justify-center gap-1 disabled:opacity-60"
                  >
                    {busyIdx === i ? (
                      <>Nano Banana…</>
                    ) : (
                      <>
                        <SparkleIcon size={10} weight="fill" />
                        {s.image ? "Re-générer" : "Image IA"}
                      </>
                    )}
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

