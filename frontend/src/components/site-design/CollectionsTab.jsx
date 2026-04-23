import React, { useEffect, useState } from "react";
import {
  ArrowClockwise, CheckCircle, PencilSimple, Plus, Sparkle, Stack, Trash,
} from "@phosphor-icons/react";
import { api, apiCall } from "../../lib/api";
import { Field } from "./shared";

export default function CollectionsTab({ siteId, onChange }) {
  const [collections, setCollections] = useState([]);
  const [products, setProducts] = useState([]);
  const [editing, setEditing] = useState(null);
  const [busy, setBusy] = useState(false);
  const [suggesting, setSuggesting] = useState(false);
  const [suggestions, setSuggestions] = useState(null);

  const reload = async () => {
    const [cRes, pRes] = await Promise.all([
      apiCall(() => api.get(`/sites/${siteId}/collections`)),
      apiCall(() => api.get(`/sites/${siteId}/products`)),
    ]);
    setCollections(Array.isArray(cRes.data) ? cRes.data : []);
    setProducts(Array.isArray(pRes.data) ? pRes.data.filter((p) => p.role !== "upsell") : []);
  };
  useEffect(() => { reload(); /* eslint-disable-next-line */ }, [siteId]);

  const aiSuggest = async () => {
    setSuggesting(true);
    const { data, error } = await apiCall(() => api.post(`/sites/${siteId}/collections/ai-suggest`, {}));
    setSuggesting(false);
    if (error) { window.alert(error); return; }
    setSuggestions(data?.suggestions || []);
  };

  const createFromSuggestion = async (s) => {
    const { error } = await apiCall(() =>
      api.post(`/sites/${siteId}/collections`, {
        name: s.name,
        description: s.description,
        product_ids: s.product_ids,
        featured: !!s.featured,
      })
    );
    if (error) { window.alert(error); return; }
    setSuggestions((prev) => (prev || []).filter((x) => x.name !== s.name));
    await reload();
    onChange?.();
  };

  const newCollection = () => setEditing({
    name: "Nouvelle collection", slug: "", description: "", cover_image: "",
    product_ids: [], featured: false,
  });

  const save = async () => {
    setBusy(true);
    const payload = {
      name: editing.name, slug: editing.slug || undefined,
      description: editing.description || "", cover_image: editing.cover_image || null,
      product_ids: editing.product_ids || [], featured: !!editing.featured,
    };
    const isEdit = !!editing.id;
    const { error } = await apiCall(() =>
      isEdit
        ? api.patch(`/sites/${siteId}/collections/${editing.id}`, payload)
        : api.post(`/sites/${siteId}/collections`, payload)
    );
    setBusy(false);
    if (error) { window.alert(error); return; }
    setEditing(null);
    await reload();
    onChange?.();
  };

  const del = async (id) => {
    if (!window.confirm("Supprimer cette collection ?")) return;
    const { error } = await apiCall(() => api.delete(`/sites/${siteId}/collections/${id}`));
    if (error) { window.alert(error); return; }
    await reload();
    onChange?.();
  };

  return (
    <div className="space-y-5" data-testid="collections-tab">
      {/* AI suggestion bar */}
      <div className="bg-gradient-to-br from-violet-50 to-indigo-50 border border-violet-200 rounded-2xl p-5">
        <div className="flex items-start gap-3 flex-wrap">
          <div className="w-10 h-10 rounded-xl bg-violet-600 flex items-center justify-center shrink-0">
            <Sparkle size={18} weight="fill" className="text-white" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-sm font-semibold text-violet-900">Laisser l'IA proposer des collections</div>
            <div className="text-xs text-violet-800/80 mt-0.5">
              Claude regroupe tes produits par usage/gamme et propose 3-5 collections clés en main.
              Tu choisis celles que tu gardes.
            </div>
          </div>
          <button
            onClick={aiSuggest}
            disabled={suggesting}
            data-testid="ai-collections-suggest"
            className="h-10 px-4 rounded-lg bg-violet-600 hover:bg-violet-700 text-white text-sm font-medium flex items-center gap-2 disabled:opacity-60"
          >
            {suggesting ? <ArrowClockwise size={14} className="animate-spin" /> : <Sparkle size={14} weight="fill" />}
            {suggesting ? "Analyse IA…" : "Proposer des collections IA"}
          </button>
        </div>
        {suggestions && suggestions.length > 0 && (
          <div className="mt-4 grid md:grid-cols-2 gap-3" data-testid="ai-suggestions-list">
            {suggestions.map((s) => (
              <div key={s.name} className="bg-white rounded-xl border border-violet-200 p-3">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <div className="font-semibold text-sm">{s.name} {s.featured && <span className="ml-1 text-[10px] bg-amber-100 text-amber-800 px-1.5 py-0.5 rounded-full">vedette</span>}</div>
                    <div className="text-[11px] text-neutral-500 mt-0.5">{s.description}</div>
                    <div className="text-[11px] text-violet-700 mt-1">{s.product_ids?.length || 0} produit(s) assigné(s)</div>
                  </div>
                  <button
                    onClick={() => createFromSuggestion(s)}
                    data-testid={`create-suggestion-${s.name}`}
                    className="h-8 px-3 rounded-lg bg-neutral-900 hover:bg-neutral-800 text-white text-xs font-medium flex items-center gap-1"
                  >
                    <Plus size={11} weight="bold" /> Créer
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
        {suggestions && suggestions.length === 0 && (
          <div className="mt-3 text-xs text-violet-700 italic">Toutes les suggestions ont été créées ou aucune proposée. Importe plus de produits pour de meilleures suggestions.</div>
        )}
      </div>

      <div className="bg-white border border-neutral-200 rounded-2xl p-5">
        <div className="flex items-center justify-between mb-4">
          <div>
            <div className="text-[11px] uppercase tracking-widest text-neutral-500">Collections</div>
            <div className="text-sm text-neutral-500">
              {collections.length} collection{collections.length > 1 ? "s" : ""} · visibles sur <code className="text-[11px] bg-neutral-100 px-1 rounded">/collections</code>
            </div>
          </div>
          <button onClick={newCollection}
            data-testid="new-collection"
            className="h-9 px-3 rounded-lg bg-neutral-900 text-white text-xs font-medium flex items-center gap-1.5">
            <Plus size={12} weight="bold" /> Nouvelle collection
          </button>
        </div>
        {collections.length === 0 ? (
          <div className="text-sm text-neutral-400 italic py-8 text-center">
            Aucune collection encore. Crée par exemple "Fauteuils releveurs", "Loupes & lecture", "Cuisine sénior"…
          </div>
        ) : (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-3">
            {collections.map((c) => (
              <div key={c.id} data-testid={`collection-${c.id}`}
                className="border border-neutral-200 rounded-xl overflow-hidden hover:border-neutral-900 transition bg-white">
                <div className="aspect-video bg-neutral-100 relative">
                  {c.cover_image ? (
                    <img src={c.cover_image} alt="" className="w-full h-full object-cover" />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-neutral-400">
                      <Stack size={32} weight="duotone" />
                    </div>
                  )}
                  {c.featured && (
                    <span className="absolute top-2 left-2 text-[10px] px-2 py-0.5 rounded-full bg-amber-100 text-amber-900 font-medium">vedette</span>
                  )}
                </div>
                <div className="p-3">
                  <div className="font-semibold text-neutral-900 text-sm">{c.name}</div>
                  <div className="text-xs text-neutral-500 mt-0.5">
                    {c.product_ids?.length || 0} produit{(c.product_ids?.length || 0) > 1 ? "s" : ""} · /{c.slug}
                  </div>
                  {c.description && <div className="text-xs text-neutral-600 mt-2 line-clamp-2">{c.description}</div>}
                  <div className="flex gap-2 mt-3">
                    <button onClick={() => setEditing({ ...c })}
                      data-testid={`edit-collection-${c.id}`}
                      className="flex-1 h-8 rounded-lg bg-neutral-900 hover:bg-neutral-800 text-white text-xs font-medium flex items-center justify-center gap-1">
                      <PencilSimple size={10} /> Éditer
                    </button>
                    <button onClick={() => del(c.id)}
                      data-testid={`delete-collection-${c.id}`}
                      className="w-8 h-8 rounded-lg border border-neutral-200 hover:border-red-300 text-neutral-500 hover:text-red-400 flex items-center justify-center">
                      <Trash size={11} />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {editing && (
        <CollectionEditor
          col={editing}
          products={products}
          onClose={() => setEditing(null)}
          onSave={save}
          onChange={(patch) => setEditing((e) => ({ ...e, ...patch }))}
          busy={busy}
        />
      )}
    </div>
  );
}

function CollectionEditor({ col, products, onClose, onSave, onChange, busy }) {
  const toggleProduct = (pid) => {
    const ids = col.product_ids || [];
    onChange({ product_ids: ids.includes(pid) ? ids.filter((x) => x !== pid) : [...ids, pid] });
  };
  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-neutral-900/40 p-4" onClick={onClose}>
      <div className="bg-white rounded-2xl max-w-3xl w-full max-h-[85vh] overflow-auto p-6" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-start justify-between mb-4">
          <div>
            <div className="text-[11px] uppercase tracking-widest text-neutral-500 mb-1">
              {col.id ? "Modifier la collection" : "Nouvelle collection"}
            </div>
            <h3 className="text-xl font-semibold" style={{ fontFamily: "'Fraunces', serif" }}>
              {col.name || "(sans nom)"}
            </h3>
          </div>
          <button onClick={onClose} className="w-8 h-8 rounded-lg hover:bg-neutral-100 text-neutral-500">✕</button>
        </div>
        <div className="grid md:grid-cols-2 gap-4 mb-5">
          <Field label="Nom">
            <input type="text" value={col.name} onChange={(e) => onChange({ name: e.target.value })}
              data-testid="col-name" maxLength={80}
              className="w-full h-10 px-3 rounded-lg border border-neutral-200 bg-white text-sm" />
          </Field>
          <Field label="Slug (URL)">
            <input type="text" value={col.slug || ""} onChange={(e) => onChange({ slug: e.target.value })}
              data-testid="col-slug" placeholder="auto-généré"
              className="w-full h-10 px-3 rounded-lg border border-neutral-200 bg-white text-sm font-mono" />
          </Field>
        </div>
        <Field label="Description">
          <textarea value={col.description || ""} onChange={(e) => onChange({ description: e.target.value })}
            data-testid="col-description" rows={3} maxLength={300}
            placeholder="Description courte affichée en haut de la collection…"
            className="w-full p-3 rounded-lg border border-neutral-200 bg-white text-sm resize-y mb-4" />
        </Field>
        <Field label="Image de couverture (URL)">
          <input type="text" value={col.cover_image || ""} onChange={(e) => onChange({ cover_image: e.target.value })}
            data-testid="col-cover" placeholder="https://…"
            className="w-full h-10 px-3 rounded-lg border border-neutral-200 bg-white text-sm mb-4" />
        </Field>
        <label className="flex items-center gap-2 text-sm text-neutral-700 mb-4">
          <input type="checkbox" checked={!!col.featured}
            onChange={(e) => onChange({ featured: e.target.checked })}
            data-testid="col-featured" />
          Mettre en vedette sur la page d'accueil
        </label>

        <div className="border-t border-neutral-100 pt-4 mb-2">
          <div className="text-[11px] uppercase tracking-widest text-neutral-500 mb-2">
            Produits dans cette collection ({(col.product_ids || []).length} / {products.length})
          </div>
          <div className="flex flex-wrap gap-2 max-h-60 overflow-auto">
            {products.length === 0 ? (
              <div className="text-sm text-neutral-400 italic">Importe des produits d'abord à l'étape 2.</div>
            ) : products.map((p) => {
              const active = (col.product_ids || []).includes(p.id);
              return (
                <button key={p.id} onClick={() => toggleProduct(p.id)}
                  data-testid={`col-product-${p.id}`}
                  className={`flex items-center gap-2 h-9 px-3 rounded-full border text-xs font-medium transition ${
                    active ? "bg-neutral-900 text-white border-neutral-900" : "bg-white border-neutral-200 hover:border-neutral-900 text-neutral-700"
                  }`}>
                  {p.images?.[0] && <img src={p.images[0]} alt="" className="w-5 h-5 rounded object-cover" />}
                  {(p.name?.fr || p.name?.en || "(sans nom)").slice(0, 40)}
                  {active && <CheckCircle size={10} weight="fill" />}
                </button>
              );
            })}
          </div>
        </div>
        <div className="flex justify-end gap-2 mt-5">
          <button onClick={onClose}
            className="h-10 px-4 rounded-lg bg-white border border-neutral-200 hover:border-neutral-400 text-sm">
            Annuler
          </button>
          <button onClick={onSave} disabled={busy || !col.name}
            data-testid="col-save"
            className="h-10 px-5 rounded-lg bg-neutral-900 hover:bg-neutral-800 text-white text-sm font-semibold flex items-center gap-2 disabled:opacity-60">
            {busy ? <ArrowClockwise size={14} className="animate-spin" /> : <CheckCircle size={14} weight="fill" />}
            Enregistrer
          </button>
        </div>
      </div>
    </div>
  );
}
