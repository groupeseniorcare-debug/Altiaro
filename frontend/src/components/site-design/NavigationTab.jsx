import React, { useEffect, useState } from "react";
import {
  ArrowClockwise, CheckCircle, Image as ImageIcon, Plus, Sparkle, Stack,
  Trash, DotsSixVertical,
} from "@phosphor-icons/react";
import { api, apiCall } from "../../lib/api";
import { LINK_TYPES, detectLinkType } from "./constants";

export default function NavigationTab({ siteId, onChange }) {
  const [nav, setNav] = useState({ header: [], footer: [] });
  const [saving, setSaving] = useState(false);
  const [optimizing, setOptimizing] = useState(false);
  const [aiRationale, setAiRationale] = useState("");
  const [collections, setCollections] = useState([]);
  const [products, setProducts] = useState([]);

  useEffect(() => {
    apiCall(() => api.get(`/sites/${siteId}/navigation`)).then(({ data }) => {
      if (data) setNav(data);
    });
    apiCall(() => api.get(`/sites/${siteId}/collections`)).then(({ data }) => {
      if (Array.isArray(data)) setCollections(data);
    });
    apiCall(() => api.get(`/sites/${siteId}/products`)).then(({ data }) => {
      if (Array.isArray(data)) setProducts(data.filter((p) => p.status !== "deleted"));
    });
  }, [siteId]);

  const aiOptimize = async () => {
    if (!window.confirm("Laisser l'IA reconstruire ta navigation (header + footer) à partir de ton catalogue ? Tes liens actuels seront remplacés.")) return;
    setOptimizing(true);
    const { data, error } = await apiCall(() => api.post(`/sites/${siteId}/navigation/ai-optimize`, {}));
    setOptimizing(false);
    if (error) { window.alert(error); return; }
    if (data?.navigation) setNav(data.navigation);
    setAiRationale(data?.rationale || "");
    onChange?.();
  };

  const addItem = (where, template = {}) => {
    setNav((n) => ({
      ...n,
      [where]: [...n[where], { label: "Nouveau lien", href: "/", external: false, ...template }],
    }));
  };
  const updateItem = (where, idx, patch) => {
    setNav((n) => ({
      ...n,
      [where]: n[where].map((it, i) => (i === idx ? { ...it, ...patch } : it)),
    }));
  };
  const removeItem = (where, idx) => {
    setNav((n) => ({ ...n, [where]: n[where].filter((_, i) => i !== idx) }));
  };
  const moveItem = (where, idx, dir) => {
    setNav((n) => {
      const copy = [...n[where]];
      const ni = idx + dir;
      if (ni < 0 || ni >= copy.length) return n;
      [copy[idx], copy[ni]] = [copy[ni], copy[idx]];
      return { ...n, [where]: copy };
    });
  };
  const save = async () => {
    setSaving(true);
    const { error } = await apiCall(() => api.put(`/sites/${siteId}/navigation`, nav));
    setSaving(false);
    if (error) { window.alert(error); return; }
    window.alert("Navigation enregistrée");
    onChange?.();
  };

  return (
    <div className="space-y-5" data-testid="navigation-tab">
      <div className="bg-gradient-to-br from-violet-50 to-indigo-50 border border-violet-200 rounded-2xl p-5">
        <div className="flex items-start gap-3 flex-wrap">
          <div className="w-10 h-10 rounded-xl bg-violet-600 flex items-center justify-center shrink-0">
            <Sparkle size={18} weight="fill" className="text-white" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-sm font-semibold text-violet-900">Navigation optimisée par l'IA</div>
            <div className="text-xs text-violet-800/80 mt-0.5">
              Claude analyse ton catalogue, tes collections, tes upsells et ta niche pour bâtir une nav orientée conversion (max 5 items header, hiérarchie claire, libellés vendeurs).
            </div>
            {aiRationale && (
              <div className="mt-2 text-[11px] text-violet-800 bg-white/60 rounded-lg p-2 italic">
                <strong>Rationale IA :</strong> {aiRationale}
              </div>
            )}
          </div>
          <button
            onClick={aiOptimize}
            disabled={optimizing}
            data-testid="ai-nav-optimize"
            className="h-10 px-4 rounded-lg bg-violet-600 hover:bg-violet-700 text-white text-sm font-medium flex items-center gap-2 disabled:opacity-60"
          >
            {optimizing ? <ArrowClockwise size={14} className="animate-spin" /> : <Sparkle size={14} weight="fill" />}
            {optimizing ? "Optimisation…" : "Optimiser avec l'IA"}
          </button>
        </div>
      </div>
      {["header", "footer"].map((where) => (
        <div key={where} className="bg-white border border-neutral-200 rounded-2xl p-5">
          <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
            <div>
              <div className="text-[11px] uppercase tracking-widest text-neutral-500">
                Menu {where === "header" ? "principal (header)" : "pied de page"}
              </div>
              <div className="text-sm text-neutral-500">
                {nav[where].length} lien{nav[where].length > 1 ? "s" : ""} · glisse ↑↓ pour réordonner
              </div>
            </div>
            <div className="flex gap-2">
              <button onClick={() => addItem(where)}
                data-testid={`nav-add-${where}`}
                className="h-9 px-3 rounded-lg bg-neutral-900 text-white text-xs font-medium flex items-center gap-1.5">
                <Plus size={12} weight="bold" /> Lien simple
              </button>
              {where === "header" && (
                <button
                  onClick={() => addItem(where, {
                    label: "Nos produits", href: "/collections", type: "mega", children: [],
                  })}
                  data-testid="nav-add-mega"
                  className="h-9 px-3 rounded-lg bg-violet-600 hover:bg-violet-700 text-white text-xs font-medium flex items-center gap-1.5">
                  <Stack size={12} weight="bold" /> Mega menu
                </button>
              )}
            </div>
          </div>
          <div className="space-y-2">
            {nav[where].length === 0 && (
              <div className="text-sm text-neutral-400 italic py-4">Aucun lien. Clique sur Ajouter.</div>
            )}
            {nav[where].map((item, idx) => (
              <NavRow
                key={idx}
                item={item}
                where={where}
                idx={idx}
                collections={collections}
                products={products}
                onUpdate={(patch) => updateItem(where, idx, patch)}
                onRemove={() => removeItem(where, idx)}
                onMoveUp={() => moveItem(where, idx, -1)}
                onMoveDown={() => moveItem(where, idx, 1)}
              />
            ))}
          </div>
        </div>
      ))}
      <div className="sticky bottom-4 bg-neutral-900 text-white rounded-2xl p-4 flex items-center justify-between gap-3 shadow-xl z-30">
        <div className="text-sm opacity-70">Les changements s'appliquent au storefront après enregistrement.</div>
        <button onClick={save} disabled={saving}
          data-testid="save-navigation"
          className="h-10 px-5 rounded-lg bg-white text-neutral-900 hover:bg-neutral-100 text-sm font-semibold flex items-center gap-2 disabled:opacity-60">
          {saving ? <ArrowClockwise size={14} className="animate-spin" /> : <CheckCircle size={14} weight="fill" />}
          {saving ? "Enregistrement…" : "Enregistrer la navigation"}
        </button>
      </div>
    </div>
  );
}

function NavRow({ item, where, idx, collections, products, onUpdate, onRemove, onMoveUp, onMoveDown }) {
  const [expanded, setExpanded] = useState(false);
  const isMega = item.type === "mega";
  const linkType = detectLinkType(item.href);

  const applyLinkType = (type) => {
    const preset = LINK_TYPES.find((l) => l.value === type);
    if (!preset) return;
    if (type === "collection") {
      const first = collections[0];
      onUpdate({ href: first ? `/collections/${first.slug}` : "/collections/", external: false });
    } else if (type === "product") {
      const first = products[0];
      onUpdate({ href: first ? `/product/${first.id}` : "/product/", external: false });
    } else if (type === "url") {
      onUpdate({ href: "https://", external: true });
    } else {
      onUpdate({ href: preset.href, external: false });
    }
  };

  return (
    <div className="bg-neutral-50 rounded-xl border border-neutral-100">
      <div className="flex items-center gap-2 p-2 flex-wrap md:flex-nowrap">
        <DotsSixVertical size={16} className="text-neutral-400 hidden md:block" />
        {isMega && (
          <span className="text-[10px] px-2 py-0.5 rounded-full bg-violet-100 text-violet-700 font-medium whitespace-nowrap">
            Mega menu
          </span>
        )}
        <input
          type="text"
          value={item.label}
          onChange={(e) => onUpdate({ label: e.target.value })}
          data-testid={`nav-${where}-label-${idx}`}
          placeholder="Intitulé"
          className="flex-1 min-w-[140px] h-9 px-3 rounded border border-neutral-200 bg-white text-sm"
        />
        <select
          value={linkType}
          onChange={(e) => applyLinkType(e.target.value)}
          data-testid={`nav-${where}-type-${idx}`}
          className="h-9 px-2 rounded border border-neutral-200 bg-white text-xs w-40"
        >
          {LINK_TYPES.map((l) => (
            <option key={l.value} value={l.value}>{l.label}</option>
          ))}
        </select>
        {linkType === "collection" && (
          <select
            value={item.href}
            onChange={(e) => onUpdate({ href: e.target.value })}
            data-testid={`nav-${where}-collection-${idx}`}
            className="h-9 px-2 rounded border border-neutral-200 bg-white text-xs min-w-[140px]"
          >
            <option value="">— choisir —</option>
            {collections.map((c) => (
              <option key={c.id} value={`/collections/${c.slug}`}>{c.name}</option>
            ))}
          </select>
        )}
        {linkType === "product" && (
          <select
            value={item.href}
            onChange={(e) => onUpdate({ href: e.target.value })}
            data-testid={`nav-${where}-product-${idx}`}
            className="h-9 px-2 rounded border border-neutral-200 bg-white text-xs min-w-[160px]"
          >
            <option value="">— choisir —</option>
            {products.slice(0, 100).map((p) => (
              <option key={p.id} value={`/product/${p.id}`}>
                {p.name?.fr || p.name?.en || "(sans nom)"}
              </option>
            ))}
          </select>
        )}
        {linkType === "url" && (
          <input
            type="url"
            value={item.href}
            onChange={(e) => onUpdate({ href: e.target.value })}
            data-testid={`nav-${where}-href-${idx}`}
            placeholder="https://…"
            className="h-9 px-3 rounded border border-neutral-200 bg-white text-sm font-mono min-w-[160px]"
          />
        )}
        <div className="flex items-center gap-1 ml-auto">
          {isMega && (
            <button
              onClick={() => setExpanded((v) => !v)}
              data-testid={`nav-${where}-expand-${idx}`}
              className="w-7 h-7 rounded hover:bg-neutral-200 text-neutral-600 flex items-center justify-center text-xs"
              title="Éditer les vignettes"
            >
              {expanded ? "▾" : "▸"}
            </button>
          )}
          <button onClick={onMoveUp}
            className="w-7 h-7 rounded hover:bg-neutral-200 text-neutral-600 flex items-center justify-center text-xs"
            title="Monter">↑</button>
          <button onClick={onMoveDown}
            className="w-7 h-7 rounded hover:bg-neutral-200 text-neutral-600 flex items-center justify-center text-xs"
            title="Descendre">↓</button>
          <button onClick={onRemove}
            data-testid={`nav-${where}-delete-${idx}`}
            className="w-7 h-7 rounded hover:bg-red-100 text-red-500 flex items-center justify-center">
            <Trash size={12} />
          </button>
        </div>
      </div>
      {isMega && expanded && (
        <MegaMenuEditor
          item={item}
          onUpdate={onUpdate}
          collections={collections}
          products={products}
        />
      )}
    </div>
  );
}

function MegaMenuEditor({ item, onUpdate, collections, products }) {
  const children = Array.isArray(item.children) ? item.children : [];
  const addChild = (template) => {
    onUpdate({ children: [...children, { label: "", href: "", image: "", ...template }] });
  };
  const updateChild = (i, patch) => {
    onUpdate({ children: children.map((c, j) => (j === i ? { ...c, ...patch } : c)) });
  };
  const removeChild = (i) => {
    onUpdate({ children: children.filter((_, j) => j !== i) });
  };
  const autoFromCollections = () => {
    const cards = collections.slice(0, 6).map((c) => ({
      label: c.name,
      href: `/collections/${c.slug}`,
      image: c.cover_image || "",
    }));
    onUpdate({ children: cards });
  };
  const autoFromProducts = () => {
    const cards = products
      .filter((p) => p.images?.length)
      .slice(0, 6)
      .map((p) => ({
        label: p.name?.fr || p.name?.en || "(sans nom)",
        href: `/product/${p.id}`,
        image: p.images?.[0] || "",
      }));
    onUpdate({ children: cards });
  };

  return (
    <div className="border-t border-neutral-200 p-3 bg-white rounded-b-xl">
      <div className="flex items-center justify-between mb-2 flex-wrap gap-2">
        <div className="text-[11px] uppercase tracking-widest text-neutral-500">
          Vignettes ({children.length}/6) · affichées au survol sur desktop, tap sur mobile
        </div>
        <div className="flex gap-1">
          <button onClick={autoFromCollections}
            data-testid="mega-auto-collections"
            className="h-7 px-2 rounded border border-violet-200 text-violet-700 hover:bg-violet-50 text-[11px]">
            ⚡ Auto-collections
          </button>
          <button onClick={autoFromProducts}
            data-testid="mega-auto-products"
            className="h-7 px-2 rounded border border-violet-200 text-violet-700 hover:bg-violet-50 text-[11px]">
            ⚡ Auto-produits
          </button>
          <button onClick={() => addChild({})}
            data-testid="mega-add-card"
            className="h-7 px-2 rounded bg-neutral-900 text-white text-[11px]">
            + Vignette
          </button>
        </div>
      </div>
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-2">
        {children.map((c, i) => (
          <div key={i} className="border border-neutral-200 rounded-lg p-2 bg-neutral-50">
            <div className="aspect-[4/3] rounded bg-white border border-neutral-200 mb-2 overflow-hidden flex items-center justify-center">
              {c.image ? (
                <img src={c.image} alt="" className="w-full h-full object-cover" />
              ) : (
                <ImageIcon size={24} weight="duotone" className="text-neutral-400" />
              )}
            </div>
            <input type="text" value={c.label}
              onChange={(e) => updateChild(i, { label: e.target.value })}
              placeholder="Libellé"
              data-testid={`mega-child-label-${i}`}
              className="w-full h-8 px-2 rounded border border-neutral-200 bg-white text-xs mb-1" />
            <input type="text" value={c.href}
              onChange={(e) => updateChild(i, { href: e.target.value })}
              placeholder="/collections/xxx ou /product/yyy"
              data-testid={`mega-child-href-${i}`}
              className="w-full h-8 px-2 rounded border border-neutral-200 bg-white text-xs font-mono mb-1" />
            <input type="text" value={c.image}
              onChange={(e) => updateChild(i, { image: e.target.value })}
              placeholder="URL image"
              data-testid={`mega-child-image-${i}`}
              className="w-full h-8 px-2 rounded border border-neutral-200 bg-white text-xs mb-1" />
            <div className="flex justify-end">
              <button onClick={() => removeChild(i)}
                data-testid={`mega-child-delete-${i}`}
                className="text-[11px] text-red-500 hover:underline flex items-center gap-1">
                <Trash size={10} /> Retirer
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
