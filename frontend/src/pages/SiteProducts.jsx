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
} from "@phosphor-icons/react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

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

  if (loading) {
    return (
      <Layout>
        <div className="p-8 text-zinc-500">Chargement…</div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="p-8 md:p-12 max-w-7xl">
        <button
          onClick={() => navigate(`/sites/${siteId}`)}
          className="flex items-center gap-2 text-sm text-zinc-500 hover:text-zinc-100 mb-6 transition"
          data-testid="back-to-site"
        >
          <ArrowLeft size={16} /> Retour au site
        </button>

        <div className="flex items-start justify-between gap-8 mb-10 animate-fade-up">
          <div>
            <div className="text-[11px] uppercase tracking-widest text-zinc-500 mb-2">
              {site?.name} · Catalogue
            </div>
            <h1 className="text-3xl font-semibold text-zinc-100">Produits</h1>
            <p className="text-zinc-400 mt-2 max-w-xl">
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
              className="h-11 px-4 rounded-xl bg-zinc-950 border border-zinc-800 hover:border-[#B84B31] text-zinc-100 text-sm font-medium flex items-center gap-2 transition"
            >
              <Eye size={16} /> Voir la boutique
            </a>
            <button
              onClick={() => setEditing(emptyProduct())}
              data-testid="add-product"
              className="h-11 px-4 rounded-xl bg-white hover:bg-zinc-200 text-black text-sm font-medium flex items-center gap-2 transition active:scale-[0.98]"
            >
              <Plus size={16} weight="bold" /> Nouveau produit
            </button>
          </div>
        </div>

        {/* Import from URL bar */}
        <div className="bg-zinc-950 rounded-md border border-zinc-800 p-5 mb-6" data-testid="import-url-bar">
          <div className="flex items-center gap-2 mb-2">
            <Sparkle size={16} weight="fill" className="text-zinc-100" />
            <div className="font-heading text-sm font-semibold text-zinc-100">
              Import rapide depuis une URL fournisseur
            </div>
            <div className="text-xs text-zinc-500">
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
              className="flex-1 h-11 px-4 rounded-xl border border-zinc-800 bg-black focus:ring-2 focus:ring-zinc-500/30 focus:border-zinc-500 outline-none text-sm"
            />
            <button
              onClick={handleImport}
              disabled={importing || !importUrl.trim()}
              data-testid="import-url-submit"
              className="h-11 px-5 rounded-xl bg-white hover:bg-zinc-200 text-black text-sm font-medium flex items-center gap-2 transition disabled:opacity-50"
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
          <div className="bg-zinc-950 rounded-md border border-zinc-800 p-16 text-center">
            <Storefront size={48} weight="thin" className="mx-auto text-zinc-700 mb-4" />
            <div className="text-zinc-500 mb-4">Aucun produit pour l'instant.</div>
            <button
              onClick={() => setEditing(emptyProduct())}
              className="inline-flex items-center gap-2 h-11 px-5 rounded-xl bg-white hover:bg-zinc-200 text-black text-sm font-medium transition"
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
                className="group bg-zinc-950 rounded-xl border border-zinc-800 overflow-hidden hover:shadow-md transition"
              >
                <div className="aspect-[4/3] bg-zinc-800 relative">
                  {p.images?.[0] ? (
                    <img src={p.images[0]} alt={p.name?.fr} className="w-full h-full object-cover" />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-zinc-700">
                      <Storefront size={40} weight="thin" />
                    </div>
                  )}
                  {p.featured && (
                    <div className="absolute top-2 left-2 bg-white text-black text-[10px] uppercase tracking-widest px-2 py-0.5 rounded-full flex items-center gap-1">
                      <Star size={10} weight="fill" /> Phare
                    </div>
                  )}
                  <div className="absolute top-2 right-2">
                    <span
                      className={`text-[10px] uppercase tracking-widest px-2 py-0.5 rounded-full ${
                        p.status === "active"
                          ? "bg-emerald-500/10 text-emerald-400"
                          : "bg-[#F5F5F4] text-zinc-500"
                      }`}
                    >
                      {p.status}
                    </span>
                  </div>
                </div>
                <div className="p-4">
                  <div className="font-medium text-zinc-100 truncate">
                    {p.name?.fr || "(sans nom)"}
                  </div>
                  <div className="text-sm text-zinc-400 mt-1">
                    {p.price}€ TTC {p.compare_at_price ? `(avant ${p.compare_at_price}€)` : ""}
                  </div>
                  {p.cost_price_ht > 0 && (
                    <div className="text-[11px] text-zinc-500 mt-0.5 flex items-center gap-1.5">
                      <span>Achat&nbsp;: {p.cost_price_ht}€ HT</span>
                      {(() => {
                        const ht = p.price / 1.2;
                        const m = ht - (p.cost_price_ht || 0);
                        const pct = ht > 0 ? (m / ht) * 100 : 0;
                        return (
                          <span
                            className="font-medium"
                            style={{ color: m <= 0 ? "#BE123C" : pct < 30 ? "#854D0E" : "#047857" }}
                          >
                            · Marge {m.toFixed(2)}€ ({pct.toFixed(0)}%)
                          </span>
                        );
                      })()}
                    </div>
                  )}
                  <div className="flex items-center gap-2 mt-3">
                    <button
                      onClick={() => setEditing(p)}
                      data-testid={`edit-${p.id}`}
                      className="flex-1 h-9 rounded-lg bg-black border border-zinc-800 hover:border-[#B84B31] text-[13px] text-zinc-100 flex items-center justify-center gap-1.5 transition"
                    >
                      <PencilSimple size={14} /> Éditer
                    </button>
                    {p.supplier_url && (
                      <button
                        onClick={() => handleResync(p)}
                        disabled={syncing === p.id}
                        data-testid={`resync-${p.id}`}
                        title="Re-vérifier le prix fournisseur"
                        className="h-9 w-9 rounded-lg border border-zinc-800 hover:border-[#B84B31] text-zinc-500 hover:text-zinc-100 flex items-center justify-center transition disabled:opacity-50"
                      >
                        <ArrowsClockwise size={14} className={syncing === p.id ? "animate-spin" : ""} />
                      </button>
                    )}
                    <button
                      onClick={() => handleDelete(p)}
                      data-testid={`delete-${p.id}`}
                      className="h-9 w-9 rounded-lg border border-zinc-800 hover:border-[#BE123C] hover:text-red-400 text-zinc-500 flex items-center justify-center transition"
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
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" />
      <div className="relative w-full max-w-lg bg-zinc-950 rounded-md shadow-2xl border border-zinc-800 overflow-hidden animate-fade-up" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between px-6 py-4 border-b border-zinc-800">
          <div>
            <div className="text-[11px] uppercase tracking-widest text-zinc-500">Re-sync fournisseur</div>
            <div className="text-base font-semibold text-zinc-100 truncate max-w-xs">
              {product.name?.fr || "Produit"}
            </div>
          </div>
          <button onClick={onClose} className="p-2 rounded-lg hover:bg-zinc-800"><X size={18} /></button>
        </div>

        <div className="p-6 space-y-4">
          <div className="flex items-center gap-2 text-xs text-zinc-500">
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
                  <div className="text-[10px] uppercase tracking-widest text-zinc-500">Ancien</div>
                  <div className="text-lg font-semibold text-zinc-100 mt-1 tabular-nums">{diff.price.old}€</div>
                </div>
                <div>
                  <div className="text-[10px] uppercase tracking-widest text-zinc-500">Nouveau</div>
                  <div className="text-lg font-semibold text-zinc-100 mt-1 tabular-nums">{diff.price.new}€</div>
                </div>
                <div>
                  <div className="text-[10px] uppercase tracking-widest text-zinc-500">Variation</div>
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

        <div className="px-6 py-4 bg-black border-t border-zinc-800 flex items-center justify-end gap-3">
          <button onClick={onClose} className="h-10 px-4 rounded-xl border border-zinc-800 bg-zinc-950 text-sm text-zinc-400 hover:bg-zinc-800 transition">
            Fermer
          </button>
          {priceChanged && (
            <button
              onClick={onApply}
              data-testid="apply-resync"
              className="h-10 px-4 rounded-xl bg-white hover:bg-zinc-200 text-black text-sm font-medium flex items-center gap-2 transition"
            >
              <CheckCircle size={14} weight="fill" /> Appliquer le nouveau prix
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

function ProductEditor({ siteId, initial, onClose, onSaved }) {
  const isNew = !initial.id;
  const [form, setForm] = useState(() => ({
    ...initial,
    name: { fr: "", en: "", de: "", nl: "", ...(initial.name || {}) },
    description: { fr: "", en: "", de: "", nl: "", ...(initial.description || {}) },
    images: initial.images?.length ? initial.images : [""],
  }));
  const [activeLang, setActiveLang] = useState("fr");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const setI18n = (field, lang, value) => {
    setForm((f) => ({ ...f, [field]: { ...f[field], [lang]: value } }));
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
      <div className="flex-1 bg-black/40" onClick={onClose} />
      <div className="w-full max-w-2xl bg-black h-full overflow-y-auto shadow-2xl animate-slide-in-right">
        <div className="sticky top-0 bg-zinc-950 border-b border-zinc-800 px-6 py-4 flex items-center justify-between z-10">
          <div>
            <div className="text-[11px] uppercase tracking-widest text-zinc-500">
              {isNew ? "Nouveau" : "Édition"}
            </div>
            <div className="text-base font-semibold text-zinc-100">
              {form.name?.fr || "Produit"}
            </div>
          </div>
          <button onClick={onClose} className="p-2 rounded-lg hover:bg-zinc-800" data-testid="editor-close">
            <X size={20} />
          </button>
        </div>

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
                      ? "bg-white text-white"
                      : "bg-zinc-950 border border-zinc-800 text-zinc-400 hover:border-[#B84B31]"
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
                <label className="block text-[13px] font-medium text-zinc-100 mb-1.5">
                  Description ({activeLang.toUpperCase()})
                </label>
                <textarea
                  value={form.description[activeLang]}
                  onChange={(e) => setI18n("description", activeLang, e.target.value)}
                  rows={5}
                  data-testid={`desc-${activeLang}`}
                  className="w-full px-4 py-3 rounded-xl border border-zinc-800 bg-zinc-950 focus:ring-2 focus:ring-zinc-500/30 focus:border-zinc-500 outline-none resize-none"
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
              <label className="block text-[13px] font-medium text-zinc-100 mb-1.5">Statut</label>
              <select
                value={form.status}
                onChange={(e) => setForm({ ...form, status: e.target.value })}
                data-testid="status"
                className="w-full h-11 px-4 rounded-xl border border-zinc-800 bg-zinc-950 outline-none"
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
              <span className="text-sm text-zinc-100">Produit phare (en haut de la boutique)</span>
            </label>
          </div>

          {error && (
            <div className="p-3 rounded-lg bg-red-500/10 text-red-400 text-sm" data-testid="editor-error">
              {error}
            </div>
          )}

          <div className="flex items-center justify-end gap-3 pt-4 border-t border-zinc-800">
            <button
              type="button"
              onClick={onClose}
              className="h-11 px-5 rounded-xl border border-zinc-800 text-zinc-400 hover:bg-zinc-950 transition"
            >
              Annuler
            </button>
            <button
              type="submit"
              disabled={saving}
              data-testid="save-product"
              className="h-11 px-5 rounded-xl bg-white hover:bg-zinc-200 text-black font-medium flex items-center gap-2 transition active:scale-[0.98] disabled:opacity-60"
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
      <label className="block text-[13px] font-medium text-zinc-100 mb-1.5">{label}</label>
      <input
        type={type}
        value={value}
        step={type === "number" ? "0.01" : undefined}
        onChange={(e) => onChange(e.target.value)}
        required={required}
        data-testid={`field-${testId}`}
        className="w-full h-11 px-4 rounded-xl border border-zinc-800 bg-zinc-950 focus:ring-2 focus:ring-zinc-500/30 focus:border-zinc-500 outline-none"
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
    <div className="h-11 px-3 rounded-xl border border-dashed border-zinc-800 bg-black flex items-center" data-testid="margin-preview">
      <div className="text-[11px] text-zinc-500 mr-2">Marge HT</div>
      <div className="font-heading tabular-nums text-sm font-semibold" style={{ color }}>
        {margin.toFixed(2)}€ ({marginPct.toFixed(0)}%)
      </div>
      <div className="text-[11px] text-zinc-500 ml-auto">
        50% Concepteur&nbsp;: <span className="font-medium text-zinc-100">{concepteur.toFixed(2)}€</span>
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
      <label className="block text-[13px] font-medium text-zinc-100 mb-1.5">
        Images <span className="text-zinc-500 font-normal">· La 1ère est l'image principale</span>
      </label>

      {/* Gallery */}
      {clean.length > 0 && (
        <div className="grid grid-cols-4 gap-2 mb-3">
          {clean.map((url, idx) => (
            <div
              key={`${url}-${idx}`}
              data-testid={`image-thumb-${idx}`}
              className="relative aspect-square rounded-lg overflow-hidden bg-zinc-800 border border-zinc-800 group"
            >
              <img src={url} alt="" className="w-full h-full object-cover" />
              {idx === 0 && (
                <div className="absolute top-1 left-1 bg-white text-black text-[9px] uppercase tracking-widest px-1.5 py-0.5 rounded-full">
                  Principale
                </div>
              )}
              <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 flex items-center justify-center gap-1 transition">
                {idx > 0 && (
                  <button
                    type="button"
                    onClick={() => move(idx, idx - 1)}
                    className="w-7 h-7 rounded-full bg-zinc-950 text-zinc-100 flex items-center justify-center text-xs hover:scale-110 transition"
                    title="Remonter"
                  >
                    ←
                  </button>
                )}
                {idx < clean.length - 1 && (
                  <button
                    type="button"
                    onClick={() => move(idx, idx + 1)}
                    className="w-7 h-7 rounded-full bg-zinc-950 text-zinc-100 flex items-center justify-center text-xs hover:scale-110 transition"
                    title="Descendre"
                  >
                    →
                  </button>
                )}
                <button
                  type="button"
                  onClick={() => remove(idx)}
                  data-testid={`remove-image-${idx}`}
                  className="w-7 h-7 rounded-full bg-zinc-950 text-red-400 flex items-center justify-center hover:scale-110 transition"
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
            : "border-zinc-800 bg-black hover:border-[#B84B31]/50"
        }`}
      >
        <UploadSimple size={24} weight="regular" className="mx-auto text-zinc-100 mb-2" />
        <div className="text-sm text-zinc-100">
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
          className="flex-1 h-10 px-3 rounded-lg border border-zinc-800 bg-zinc-950 focus:ring-2 focus:ring-zinc-500/30 focus:border-zinc-500 outline-none text-sm"
        />
        <button
          type="button"
          onClick={addFromUrl}
          data-testid="image-url-add"
          disabled={!urlInput.trim()}
          className="h-10 px-4 rounded-lg border border-zinc-800 bg-zinc-950 text-sm text-zinc-100 hover:border-[#B84B31] disabled:opacity-40"
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

