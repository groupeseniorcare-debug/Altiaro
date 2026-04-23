import React, { useEffect, useState, useCallback } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { Command } from "cmdk";
import {
  Storefront, ChartLine, Lightning, Palette, MagnifyingGlass,
  Package, CurrencyEur, FileText, ArrowRight, Sparkle, Plus, House,
  Gear, Truck, ShoppingCart, Tag, Image as ImageIcon, NotePencil,
} from "@phosphor-icons/react";
import { api, apiCall } from "../lib/api";

/**
 * Global command palette — Cmd+K / Ctrl+K.
 * - Top-level : jump to core pages (Dashboard, Sites, Finance…)
 * - When a site is active (/sites/:id/...) : show step-1…step-9 jumps for that site
 * - Quick actions : create site, regenerate design, launch niche analysis, logout
 * - Fuzzy search across everything
 */
export default function CommandMenu() {
  const [open, setOpen] = useState(false);
  const [sites, setSites] = useState([]);
  const navigate = useNavigate();
  const location = useLocation();

  // Cmd+K / Ctrl+K toggle — listens at window level + ignores when typing in an input
  useEffect(() => {
    const down = (e) => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        e.stopPropagation();
        setOpen((v) => !v);
      }
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", down, true);
    document.addEventListener("keydown", down, true);
    return () => {
      window.removeEventListener("keydown", down, true);
      document.removeEventListener("keydown", down, true);
    };
  }, []);

  // Load user's sites lazily the first time the palette opens
  useEffect(() => {
    if (open && sites.length === 0) {
      apiCall(() => api.get("/sites")).then(({ data }) => {
        if (Array.isArray(data)) setSites(data);
      });
    }
  }, [open, sites.length]);

  const go = useCallback((path) => {
    setOpen(false);
    navigate(path);
  }, [navigate]);

  // Detect active site from URL path
  const siteMatch = location.pathname.match(/^\/sites\/([^/]+)/);
  const activeSiteId = siteMatch ? siteMatch[1] : null;
  const activeSite = sites.find((s) => s.id === activeSiteId);

  return (
    <>
      {/* Floating hint (bottom-right, desktop only) */}
      <button
        type="button"
        onClick={() => setOpen(true)}
        data-testid="cmdk-trigger"
        className="hidden md:flex fixed bottom-5 right-5 z-30 items-center gap-2 h-9 px-3 rounded-full bg-white/90 backdrop-blur border border-neutral-200 shadow-lg hover:shadow-xl text-neutral-500 hover:text-neutral-900 text-xs font-medium transition"
        aria-label="Ouvrir la palette de commandes"
      >
        <MagnifyingGlass size={12} />
        <span>Chercher…</span>
        <kbd className="px-1.5 py-0.5 rounded bg-neutral-100 border border-neutral-200 font-mono text-[10px]">⌘K</kbd>
      </button>

      {open && (
        <div
          className="fixed inset-0 z-[100] bg-black/50 backdrop-blur-sm flex items-start justify-center pt-[15vh]"
          onClick={() => setOpen(false)}
          data-testid="cmdk-overlay"
        >
          <Command
            label="Palette de commandes Altiaro"
            className="bg-white rounded-2xl shadow-2xl w-[92vw] max-w-xl border border-neutral-200 overflow-hidden animate-in fade-in slide-in-from-top-4"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center gap-2 px-4 border-b border-neutral-100">
              <MagnifyingGlass size={16} className="text-neutral-400" />
              <Command.Input
                autoFocus
                placeholder="Tape pour chercher un site, une étape, une action…"
                data-testid="cmdk-input"
                className="flex-1 h-12 outline-none text-sm bg-transparent"
              />
              <kbd className="text-[10px] px-1.5 py-0.5 bg-neutral-100 rounded border border-neutral-200 font-mono">esc</kbd>
            </div>

            <Command.List className="max-h-[60vh] overflow-y-auto p-2">
              <Command.Empty className="py-6 text-center text-sm text-neutral-400">
                Aucun résultat.
              </Command.Empty>

              {/* === Active site shortcuts === */}
              {activeSiteId && (
                <Command.Group
                  heading={activeSite ? `📍 Site actif : ${activeSite.name}` : "📍 Site actif"}
                  className="text-[10px] uppercase tracking-widest text-neutral-400 px-2 pb-1 pt-2 font-medium"
                >
                  <Row
                    icon={ChartLine} label="Cockpit du site"
                    onSelect={() => go(`/sites/${activeSiteId}`)}
                    testid="cmdk-site-cockpit" hint="Vue journey"
                  />
                  <Row
                    icon={Lightning} label="Étape 2 — Sourcing"
                    onSelect={() => go(`/sites/${activeSiteId}/sourcing`)}
                    testid="cmdk-step2" hint="Produits & fournisseurs"
                  />
                  <Row
                    icon={Package} label="Étape 3 — Produits & Upsells"
                    onSelect={() => go(`/sites/${activeSiteId}/products`)}
                    testid="cmdk-step3" hint="Catalogue"
                  />
                  <Row
                    icon={CurrencyEur} label="Étape 4 — Forecast P&L"
                    onSelect={() => go(`/sites/${activeSiteId}/forecast`)}
                    testid="cmdk-step4"
                  />
                  <Row
                    icon={Palette} label="Étape 5 — Studio de marque"
                    onSelect={() => go(`/sites/${activeSiteId}/design`)}
                    testid="cmdk-step5"
                  />
                  <Row
                    icon={MagnifyingGlass} label="Étape 6 — SEO / AEO"
                    onSelect={() => go(`/sites/${activeSiteId}/seo`)}
                    testid="cmdk-step6"
                  />
                  <Row
                    icon={NotePencil} label="Étape 7 — Journal / Blog"
                    onSelect={() => go(`/sites/${activeSiteId}/blog`)}
                    testid="cmdk-step7"
                  />
                  <Row
                    icon={Truck} label="Étape 8 — Fulfillment"
                    onSelect={() => go(`/sites/${activeSiteId}/fulfillment`)}
                    testid="cmdk-step8"
                  />
                  <Row
                    icon={Gear} label="Étape 9 — Réglages boutique"
                    onSelect={() => go(`/sites/${activeSiteId}/settings`)}
                    testid="cmdk-step9"
                  />
                  <Row
                    icon={Storefront} label="Voir le storefront public ↗"
                    onSelect={() => { setOpen(false); window.open(`/shop/${activeSiteId}`, "_blank"); }}
                    testid="cmdk-preview-shop"
                  />
                </Command.Group>
              )}

              {/* === Switch to another site === */}
              {sites.length > 0 && (
                <Command.Group
                  heading="🔄 Changer de site"
                  className="text-[10px] uppercase tracking-widest text-neutral-400 px-2 pb-1 pt-3 font-medium"
                >
                  {sites.slice(0, 10).map((s) => (
                    <Row
                      key={s.id}
                      icon={Storefront}
                      label={s.name || "(sans nom)"}
                      hint={s.niche ? s.niche.slice(0, 32) : "Site"}
                      onSelect={() => go(`/sites/${s.id}`)}
                      testid={`cmdk-site-${s.id}`}
                    />
                  ))}
                </Command.Group>
              )}

              {/* === Core navigation === */}
              <Command.Group
                heading="🧭 Navigation"
                className="text-[10px] uppercase tracking-widest text-neutral-400 px-2 pb-1 pt-3 font-medium"
              >
                <Row icon={House} label="Dashboard" onSelect={() => go("/")} testid="cmdk-dashboard" />
                <Row icon={Storefront} label="Mes sites" onSelect={() => go("/sites")} testid="cmdk-sites" />
                <Row icon={CurrencyEur} label="Finances" onSelect={() => go("/finance")} testid="cmdk-finance" />
                <Row icon={ChartLine} label="Analyses de niche" onSelect={() => go("/niches")} testid="cmdk-niches" />
                <Row icon={FileText} label="Validations" onSelect={() => go("/validations")} testid="cmdk-validations" />
              </Command.Group>

              {/* === Quick actions === */}
              <Command.Group
                heading="⚡ Actions rapides"
                className="text-[10px] uppercase tracking-widest text-neutral-400 px-2 pb-1 pt-3 font-medium"
              >
                <Row
                  icon={Plus} label="Créer un nouveau site"
                  onSelect={() => go("/sites/new")}
                  testid="cmdk-action-new-site"
                />
                <Row
                  icon={Sparkle} label="Lancer une analyse de niche"
                  onSelect={() => go("/niches/new")}
                  testid="cmdk-action-new-niche"
                />
                {activeSiteId && (
                  <>
                    <Row
                      icon={ImageIcon} label="Générer images IA (produit actif)"
                      hint="Nano Banana"
                      onSelect={() => go(`/sites/${activeSiteId}/products`)}
                      testid="cmdk-action-gen-images"
                    />
                    <Row
                      icon={Tag} label="Régénérer le design de la marque"
                      hint="Claude"
                      onSelect={() => go(`/sites/${activeSiteId}/design`)}
                      testid="cmdk-action-regen-design"
                    />
                    <Row
                      icon={ShoppingCart} label="Voir les commandes"
                      onSelect={() => go(`/sites/${activeSiteId}/orders`)}
                      testid="cmdk-action-orders"
                    />
                  </>
                )}
              </Command.Group>
            </Command.List>

            <div className="border-t border-neutral-100 px-3 py-2 flex items-center justify-between text-[10px] text-neutral-400">
              <span>↑↓ Naviguer · ↵ Ouvrir</span>
              <span className="font-mono">Altiaro · ⌘K</span>
            </div>
          </Command>
        </div>
      )}
    </>
  );
}

function Row({ icon: Icon, label, hint, onSelect, testid }) {
  return (
    <Command.Item
      onSelect={onSelect}
      data-testid={testid}
      className="flex items-center gap-3 px-3 py-2.5 rounded-lg cursor-pointer text-sm text-neutral-700 aria-selected:bg-neutral-100 aria-selected:text-neutral-900 hover:bg-neutral-50"
    >
      <Icon size={16} weight="duotone" className="text-neutral-500 shrink-0" />
      <span className="flex-1 truncate">{label}</span>
      {hint && <span className="text-[11px] text-neutral-400 truncate max-w-[180px]">{hint}</span>}
      <ArrowRight size={12} className="text-neutral-300" />
    </Command.Item>
  );
}
