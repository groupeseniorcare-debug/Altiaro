import React, { useEffect, useState, useRef, useCallback, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { api, apiCall } from "../lib/api";
import {
  MagnifyingGlass,
  Storefront,
  Package,
  Target,
  ShoppingBag,
  User,
  CornersOut,
  X,
} from "@phosphor-icons/react";

/**
 * Global command palette triggered by Cmd/Ctrl+K.
 * Searches sites, products, orders, niches, users.
 */
export default function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [cursor, setCursor] = useState(0);
  const inputRef = useRef(null);
  const navigate = useNavigate();

  // Global shortcut
  useEffect(() => {
    const onKey = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen((o) => !o);
      } else if (e.key === "Escape") {
        setOpen(false);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  useEffect(() => {
    if (open) {
      setQ("");
      setResults(null);
      setCursor(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [open]);

  // Debounced search
  useEffect(() => {
    if (!open) return;
    if (q.trim().length < 2) {
      setResults(null);
      return;
    }
    const t = setTimeout(async () => {
      setLoading(true);
      const { data } = await apiCall(() => api.get(`/admin/search?q=${encodeURIComponent(q)}&limit=5`));
      setLoading(false);
      if (data) {
        setResults(data);
        setCursor(0);
      }
    }, 180);
    return () => clearTimeout(t);
  }, [q, open]);

  // Flat list of all result items (for keyboard nav)
  const flat = useMemo(() => {
    if (!results) return [];
    const items = [];
    (results.sites || []).forEach((s) => items.push({
      kind: "site", id: s.id, label: s.name,
      sub: `${s.niche || ""} · ${s.status}`, icon: Storefront,
      href: `/sites/${s.id}`,
    }));
    (results.products || []).forEach((p) => items.push({
      kind: "product", id: p.id, label: p.name?.fr || p.name?.en || "(produit)",
      sub: `${p.price}${p.currency === "EUR" ? "€" : p.currency} · ${p.status}`, icon: Package,
      href: `/sites/${p.site_id}/products`,
      image: p.images?.[0],
    }));
    (results.orders || []).forEach((o) => items.push({
      kind: "order", id: o.id, label: o.order_number,
      sub: `${o.customer?.name} · ${o.total?.toFixed?.(2)}€ · ${o.status}`, icon: ShoppingBag,
      href: `/orders`,
    }));
    (results.niches || []).forEach((n) => items.push({
      kind: "niche", id: n.slug, label: `${n.emoji || ""} ${n.name}`,
      sub: `#${n.rank} · ${n.category} · ECF ${n.ecf_score}`, icon: Target,
      href: `/niches/${n.slug}`,
    }));
    (results.users || []).forEach((u) => items.push({
      kind: "user", id: u.id, label: u.name || u.email,
      sub: `${u.email} · ${u.role}`, icon: User,
      href: `/users`,
    }));
    return items;
  }, [results]);

  const handleSelect = useCallback((item) => {
    if (!item) return;
    setOpen(false);
    navigate(item.href);
  }, [navigate]);

  const onInputKey = (e) => {
    if (!flat.length) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setCursor((c) => Math.min(c + 1, flat.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setCursor((c) => Math.max(c - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      handleSelect(flat[cursor]);
    }
  };

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        data-testid="open-command-palette"
        aria-label="Recherche globale"
        className="fixed bottom-6 right-6 w-12 h-12 rounded-full bg-white hover:bg-[#44403C] text-black shadow-lg flex items-center justify-center transition z-30 hover:scale-105 active:scale-95"
        title="Recherche globale (⌘K)"
      >
        <MagnifyingGlass size={20} weight="bold" />
      </button>
    );
  }

  const groups = [
    ["sites",   "Sites",     Storefront],
    ["products","Produits",  Package],
    ["orders",  "Commandes", ShoppingBag],
    ["niches",  "Niches",    Target],
    ["users",   "Équipe",    User],
  ];

  let flatIdx = 0;

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center pt-24 px-4"
      data-testid="command-palette"
      onClick={() => setOpen(false)}
    >
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" />
      <div
        onClick={(e) => e.stopPropagation()}
        className="relative w-full max-w-xl bg-zinc-950 rounded-md shadow-2xl overflow-hidden border border-zinc-800 animate-fade-up"
      >
        {/* Input */}
        <div className="flex items-center gap-3 px-5 h-14 border-b border-zinc-800">
          <MagnifyingGlass size={18} className="text-zinc-500 flex-shrink-0" />
          <input
            ref={inputRef}
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={onInputKey}
            placeholder="Rechercher sites, produits, commandes, niches..."
            data-testid="command-palette-input"
            className="flex-1 h-full bg-transparent outline-none text-[15px] text-zinc-100 placeholder:text-[#A8A29E]"
          />
          <kbd className="hidden md:inline-flex items-center px-1.5 py-0.5 rounded border border-zinc-800 text-[10px] uppercase tracking-widest text-zinc-500 font-mono">
            ESC
          </kbd>
          <button
            onClick={() => setOpen(false)}
            className="p-1 rounded hover:bg-zinc-800 md:hidden"
            aria-label="Fermer"
          >
            <X size={16} />
          </button>
        </div>

        {/* Results */}
        <div className="max-h-[60vh] overflow-y-auto">
          {loading && (
            <div className="px-5 py-8 text-sm text-center text-zinc-500">Recherche...</div>
          )}

          {!loading && q.trim().length < 2 && (
            <Empty
              title="Commence à taper pour chercher"
              subtitle="Navigue vite dans ton catalogue avec ⌘K"
            />
          )}

          {!loading && q.trim().length >= 2 && results && flat.length === 0 && (
            <Empty title="Aucun résultat" subtitle={`Pour "${q}"`} />
          )}

          {!loading && results && flat.length > 0 && (
            <div className="py-2">
              {groups.map(([key, title, Icon]) => {
                const items = results[key] || [];
                if (!items.length) return null;
                return (
                  <div key={key}>
                    <div className="px-5 pt-3 pb-1 text-[10px] uppercase tracking-widest text-zinc-500 flex items-center gap-1.5">
                      <Icon size={11} /> {title} <span className="text-[#D6D3D1]">· {items.length}</span>
                    </div>
                    {items.map((r) => {
                      const item = flat[flatIdx];
                      const isCursor = flatIdx === cursor;
                      flatIdx++;
                      return (
                        <button
                          key={`${item.kind}-${item.id}`}
                          onClick={() => handleSelect(item)}
                          onMouseEnter={() => setCursor(flat.indexOf(item))}
                          data-testid={`cmd-result-${item.kind}-${item.id}`}
                          className={`w-full text-left px-5 py-2.5 flex items-center gap-3 transition ${
                            isCursor ? "bg-[#FDF4E7]" : "hover:bg-black"
                          }`}
                        >
                          <div className="w-8 h-8 rounded-lg bg-zinc-800 flex items-center justify-center flex-shrink-0 overflow-hidden">
                            {item.image ? (
                              <img src={item.image} alt="" className="w-full h-full object-cover" />
                            ) : (
                              <item.icon size={14} className="text-zinc-100" />
                            )}
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="text-[14px] font-medium text-zinc-100 truncate">
                              {item.label}
                            </div>
                            <div className="text-[12px] text-zinc-500 truncate">{item.sub}</div>
                          </div>
                          {isCursor && (
                            <CornersOut size={14} weight="bold" className="text-zinc-100" />
                          )}
                        </button>
                      );
                    })}
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-5 h-10 border-t border-zinc-800 bg-black">
          <div className="flex items-center gap-3 text-[11px] text-zinc-500">
            <span className="flex items-center gap-1">
              <KBD>↑</KBD> <KBD>↓</KBD> Naviguer
            </span>
            <span className="flex items-center gap-1">
              <KBD>↵</KBD> Ouvrir
            </span>
          </div>
          <div className="text-[11px] text-zinc-500">
            {results?.total ? `${results.total} résultat${results.total > 1 ? "s" : ""}` : ""}
          </div>
        </div>
      </div>
    </div>
  );
}

function KBD({ children }) {
  return (
    <kbd className="inline-flex items-center justify-center min-w-[18px] h-[18px] px-1 rounded border border-zinc-800 bg-zinc-950 text-[10px] font-mono text-zinc-400">
      {children}
    </kbd>
  );
}

function Empty({ title, subtitle }) {
  return (
    <div className="py-16 text-center">
      <MagnifyingGlass size={28} weight="thin" className="mx-auto text-[#D6D3D1] mb-3" />
      <div className="text-sm font-medium text-zinc-400">{title}</div>
      <div className="text-xs text-[#A8A29E] mt-0.5">{subtitle}</div>
    </div>
  );
}
