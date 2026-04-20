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
} from "@phosphor-icons/react";

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
  const [editing, setEditing] = useState(null); // null | {..product} — edit/create
  const backendUrl = process.env.REACT_APP_BACKEND_URL;

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

  if (loading) {
    return (
      <Layout>
        <div className="p-8 text-[#78716C]">Chargement…</div>
      </Layout>
    );
  }

  const shopUrl = `${backendUrl.replace(/\/$/, "")}/shop/${siteId}`;

  return (
    <Layout>
      <div className="p-8 md:p-12 max-w-7xl">
        <button
          onClick={() => navigate(`/sites/${siteId}`)}
          className="flex items-center gap-2 text-sm text-[#78716C] hover:text-[#1C1917] mb-6 transition"
          data-testid="back-to-site"
        >
          <ArrowLeft size={16} /> Retour au site
        </button>

        <div className="flex items-start justify-between gap-8 mb-10 animate-fade-up">
          <div>
            <div className="text-[11px] uppercase tracking-widest text-[#78716C] mb-2">
              {site?.name} · Catalogue
            </div>
            <h1 className="font-heading text-4xl font-semibold text-[#1C1917]">Produits</h1>
            <p className="text-[#57534E] mt-2 max-w-xl">
              Ajoute tes produits manuellement (l'import automatique DSers / CJ arrivera en Phase 4).
              Les fiches multilingues FR/EN/DE/NL sont publiées sur la boutique publique.
            </p>
          </div>
          <div className="flex gap-2">
            <a
              href={`/shop/${siteId}`}
              target="_blank"
              rel="noreferrer"
              data-testid="preview-shop"
              className="h-11 px-4 rounded-xl bg-white border border-[#E7E5E4] hover:border-[#B84B31] text-[#1C1917] text-sm font-medium flex items-center gap-2 transition"
            >
              <Eye size={16} /> Voir la boutique
            </a>
            <button
              onClick={() => setEditing(emptyProduct())}
              data-testid="add-product"
              className="h-11 px-4 rounded-xl bg-[#B84B31] hover:bg-[#993D26] text-white text-sm font-medium flex items-center gap-2 transition active:scale-[0.98]"
            >
              <Plus size={16} weight="bold" /> Nouveau produit
            </button>
          </div>
        </div>

        {products.length === 0 ? (
          <div className="bg-white rounded-2xl border border-[#E7E5E4] p-16 text-center">
            <Storefront size={48} weight="thin" className="mx-auto text-[#D6D3D1] mb-4" />
            <div className="text-[#78716C] mb-4">Aucun produit pour l'instant.</div>
            <button
              onClick={() => setEditing(emptyProduct())}
              className="inline-flex items-center gap-2 h-11 px-5 rounded-xl bg-[#B84B31] hover:bg-[#993D26] text-white text-sm font-medium transition"
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
                className="group bg-white rounded-xl border border-[#E7E5E4] overflow-hidden hover:shadow-md transition"
              >
                <div className="aspect-[4/3] bg-[#F5F2EB] relative">
                  {p.images?.[0] ? (
                    <img src={p.images[0]} alt={p.name?.fr} className="w-full h-full object-cover" />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-[#D6D3D1]">
                      <Storefront size={40} weight="thin" />
                    </div>
                  )}
                  {p.featured && (
                    <div className="absolute top-2 left-2 bg-[#B84B31] text-white text-[10px] uppercase tracking-widest px-2 py-0.5 rounded-full flex items-center gap-1">
                      <Star size={10} weight="fill" /> Phare
                    </div>
                  )}
                  <div className="absolute top-2 right-2">
                    <span
                      className={`text-[10px] uppercase tracking-widest px-2 py-0.5 rounded-full ${
                        p.status === "active"
                          ? "bg-[#D1FAE5] text-[#047857]"
                          : "bg-[#F5F5F4] text-[#78716C]"
                      }`}
                    >
                      {p.status}
                    </span>
                  </div>
                </div>
                <div className="p-4">
                  <div className="font-medium text-[#1C1917] truncate">
                    {p.name?.fr || "(sans nom)"}
                  </div>
                  <div className="text-sm text-[#57534E] mt-1">
                    {p.price}€ {p.compare_at_price ? `(avant ${p.compare_at_price}€)` : ""}
                  </div>
                  <div className="flex items-center gap-2 mt-3">
                    <button
                      onClick={() => setEditing(p)}
                      data-testid={`edit-${p.id}`}
                      className="flex-1 h-9 rounded-lg bg-[#FDFBF7] border border-[#E7E5E4] hover:border-[#B84B31] text-[13px] text-[#1C1917] flex items-center justify-center gap-1.5 transition"
                    >
                      <PencilSimple size={14} /> Éditer
                    </button>
                    <button
                      onClick={() => handleDelete(p)}
                      data-testid={`delete-${p.id}`}
                      className="h-9 w-9 rounded-lg border border-[#E7E5E4] hover:border-[#BE123C] hover:text-[#BE123C] text-[#78716C] flex items-center justify-center transition"
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
    </Layout>
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

  const setImage = (idx, url) => {
    const imgs = [...form.images];
    imgs[idx] = url;
    setForm({ ...form, images: imgs });
  };
  const addImage = () => setForm({ ...form, images: [...form.images, ""] });
  const removeImage = (idx) => {
    const imgs = form.images.filter((_, i) => i !== idx);
    setForm({ ...form, images: imgs.length ? imgs : [""] });
  };

  const submit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError("");
    const payload = {
      name: form.name,
      description: form.description,
      price: parseFloat(form.price) || 0,
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
      <div className="w-full max-w-2xl bg-[#FDFBF7] h-full overflow-y-auto shadow-2xl animate-slide-in-right">
        <div className="sticky top-0 bg-white border-b border-[#E7E5E4] px-6 py-4 flex items-center justify-between z-10">
          <div>
            <div className="text-[11px] uppercase tracking-widest text-[#78716C]">
              {isNew ? "Nouveau" : "Édition"}
            </div>
            <div className="font-heading text-lg font-semibold text-[#1C1917]">
              {form.name?.fr || "Produit"}
            </div>
          </div>
          <button onClick={onClose} className="p-2 rounded-lg hover:bg-[#F5F2EB]" data-testid="editor-close">
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
                      ? "bg-[#1C1917] text-white"
                      : "bg-white border border-[#E7E5E4] text-[#57534E] hover:border-[#B84B31]"
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
                <label className="block text-[13px] font-medium text-[#1C1917] mb-1.5">
                  Description ({activeLang.toUpperCase()})
                </label>
                <textarea
                  value={form.description[activeLang]}
                  onChange={(e) => setI18n("description", activeLang, e.target.value)}
                  rows={5}
                  data-testid={`desc-${activeLang}`}
                  className="w-full px-4 py-3 rounded-xl border border-[#E7E5E4] bg-white focus:ring-2 focus:ring-[#B84B31]/30 focus:border-[#B84B31] outline-none resize-none"
                />
              </div>
            </div>
          </div>

          {/* Price */}
          <div className="grid grid-cols-2 gap-4">
            <Field
              label="Prix (€) *"
              type="number"
              value={form.price}
              onChange={(v) => setForm({ ...form, price: v })}
              testId="price"
              required
            />
            <Field
              label="Prix barré (optionnel)"
              type="number"
              value={form.compare_at_price || ""}
              onChange={(v) => setForm({ ...form, compare_at_price: v })}
              testId="compare-price"
            />
          </div>

          {/* Images */}
          <div>
            <label className="block text-[13px] font-medium text-[#1C1917] mb-1.5">
              Images (URL)
            </label>
            <div className="space-y-2">
              {form.images.map((url, idx) => (
                <div key={idx} className="flex gap-2">
                  <input
                    value={url}
                    onChange={(e) => setImage(idx, e.target.value)}
                    placeholder="https://…"
                    data-testid={`image-${idx}`}
                    className="flex-1 h-11 px-4 rounded-xl border border-[#E7E5E4] bg-white focus:ring-2 focus:ring-[#B84B31]/30 focus:border-[#B84B31] outline-none"
                  />
                  {form.images.length > 1 && (
                    <button
                      type="button"
                      onClick={() => removeImage(idx)}
                      className="h-11 w-11 rounded-xl border border-[#E7E5E4] hover:border-[#BE123C] hover:text-[#BE123C] transition"
                    >
                      <Trash size={16} className="mx-auto" />
                    </button>
                  )}
                </div>
              ))}
              <button
                type="button"
                onClick={addImage}
                className="text-sm text-[#B84B31] hover:underline"
                data-testid="add-image"
              >
                + Ajouter une image
              </button>
            </div>
          </div>

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
              <label className="block text-[13px] font-medium text-[#1C1917] mb-1.5">Statut</label>
              <select
                value={form.status}
                onChange={(e) => setForm({ ...form, status: e.target.value })}
                data-testid="status"
                className="w-full h-11 px-4 rounded-xl border border-[#E7E5E4] bg-white outline-none"
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
              <span className="text-sm text-[#1C1917]">Produit phare (en haut de la boutique)</span>
            </label>
          </div>

          {error && (
            <div className="p-3 rounded-lg bg-[#FFE4E6] text-[#BE123C] text-sm" data-testid="editor-error">
              {error}
            </div>
          )}

          <div className="flex items-center justify-end gap-3 pt-4 border-t border-[#E7E5E4]">
            <button
              type="button"
              onClick={onClose}
              className="h-11 px-5 rounded-xl border border-[#E7E5E4] text-[#57534E] hover:bg-white transition"
            >
              Annuler
            </button>
            <button
              type="submit"
              disabled={saving}
              data-testid="save-product"
              className="h-11 px-5 rounded-xl bg-[#B84B31] hover:bg-[#993D26] text-white font-medium flex items-center gap-2 transition active:scale-[0.98] disabled:opacity-60"
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
      <label className="block text-[13px] font-medium text-[#1C1917] mb-1.5">{label}</label>
      <input
        type={type}
        value={value}
        step={type === "number" ? "0.01" : undefined}
        onChange={(e) => onChange(e.target.value)}
        required={required}
        data-testid={`field-${testId}`}
        className="w-full h-11 px-4 rounded-xl border border-[#E7E5E4] bg-white focus:ring-2 focus:ring-[#B84B31]/30 focus:border-[#B84B31] outline-none"
      />
    </div>
  );
}
