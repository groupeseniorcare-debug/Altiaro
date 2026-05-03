import React, { useState, useEffect } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { api, apiCall } from "../lib/api";
import CommandPalette from "./CommandPalette";
import CommandMenu from "./CommandMenu";
import CopilotFab from "./CopilotFab";  // Unused — Copilot désactivé
import DomainSkipBanner from "./DomainSkipBanner";
import { List, X } from "@phosphor-icons/react";
import { AltiaroLogo } from "./AltiaroLogo";
import {
  House,
  SquaresFour,
  CheckSquare,
  ChartLineUp,
  Users,
  SignOut,
  Rocket,
  Target,
  Package,
  Globe,
  CreditCard,
  Bank,
  GoogleLogo,
  Fire,
  Plugs,
  Lightning,
} from "@phosphor-icons/react";

/**
 * Bloc 1 sous-chantier 2 — pastille budget LLM (admin only).
 * Lit /api/admin/llm-budget toutes les 5 min. Affiche état :
 *   - vert "OK"        si pct < 80% ou unknown
 *   - orange "≥80%"    si warning
 *   - rouge "≥95%"     si critical
 */
function LLMBudgetPill() {
  const [snap, setSnap] = useState(null);
  useEffect(() => {
    let cancelled = false;
    const tick = async () => {
      const { data } = await apiCall(() => api.get(`/admin/llm-budget`));
      if (!cancelled && data) setSnap(data);
      if (!cancelled) setTimeout(tick, 5 * 60 * 1000);  // 5 min
    };
    tick();
    return () => { cancelled = true; };
  }, []);
  if (!snap) return null;
  const lvl = snap.alert_level;
  const pct = snap.pct;
  const styles = {
    critical: { dot: "bg-red-500", border: "border-red-200", bg: "bg-red-50", txt: "text-red-700" },
    warning:  { dot: "bg-amber-500", border: "border-amber-200", bg: "bg-amber-50", txt: "text-amber-700" },
    ok:       { dot: "bg-emerald-500", border: "border-emerald-200", bg: "bg-emerald-50", txt: "text-emerald-700" },
    unknown:  { dot: "bg-neutral-400", border: "border-neutral-200", bg: "bg-neutral-50", txt: "text-neutral-600" },
  };
  const s = styles[lvl] || styles.unknown;
  const labelText = lvl === "unknown"
    ? "Budget IA · OK"
    : `Budget IA · ${pct?.toFixed(0)}%`;
  const tooltip = lvl === "unknown"
    ? "Aucune erreur de budget capturée. Le système est sain."
    : `${snap.used_usd}$ utilisés sur ${snap.max_usd}$. ${snap.days_remaining_in_month}j restants ce mois.`;
  return (
    <div
      data-testid="sidebar-llm-budget-pill"
      className={`flex items-center gap-2 px-2.5 py-1.5 mb-2 rounded-md border ${s.border} ${s.bg} ${s.txt} text-[11px] font-medium`}
      title={tooltip}
    >
      <Lightning size={11} weight="fill" className={s.dot.replace("bg-", "text-")} />
      <span className="flex-1 truncate">{labelText}</span>
      <span className={`w-1.5 h-1.5 rounded-full ${s.dot}`} />
    </div>
  );
}

export default function Layout({ children }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [mobileOpen, setMobileOpen] = useState(false);

  const isAdmin = user?.role === "admin";
  const links = isAdmin
    ? [
        { to: "/", label: "Tableau de bord", icon: House, testId: "nav-dashboard" },
        { to: "/sites/new", label: "Lancer un site", icon: Rocket, testId: "nav-launch" },
        { to: "/sites", label: "Sites", icon: SquaresFour, testId: "nav-sites" },
        { to: "/niches", label: "Analyseur", icon: Target, testId: "nav-niches" },
        { to: "/empire", label: "Empire", icon: Globe, testId: "nav-empire" },
        { to: "/orders", label: "Commandes", icon: Package, testId: "nav-orders" },
        { to: "/admin/payouts", label: "Virements", icon: Bank, testId: "nav-admin-payouts" },
        { to: "/admin/google-ads", label: "Google Ads", icon: GoogleLogo, testId: "nav-google-ads" },
        { to: "/admin/opportunities", label: "Opportunités", icon: Fire, testId: "nav-opportunities" },
        { to: "/admin/review", label: "Validations", icon: CheckSquare, testId: "nav-validations" },
        { to: "/admin/integrations", label: "Intégrations", icon: Plugs, testId: "nav-integrations" },
        { to: "/admin/finance", label: "Finance (Admin)", icon: ChartLineUp, testId: "nav-finances" },
        { to: "/billing", label: "Paiements", icon: CreditCard, testId: "nav-billing" },
        { to: "/users", label: "Équipe", icon: Users, testId: "nav-users" },
      ]
    : [
        { to: "/", label: "Dashboard", icon: House, testId: "nav-dashboard" },
        { to: "/sites", label: "Sites", icon: SquaresFour, testId: "nav-sites" },
        { to: "/sites/new", label: "Lancer un site", icon: Rocket, testId: "nav-launch" },
        { to: "/finance", label: "Finance", icon: ChartLineUp, testId: "nav-finances" },
        { to: "/billing", label: "Compte", icon: CreditCard, testId: "nav-billing" },
      ];

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  return (
    <div className="min-h-screen flex bg-neutral-50 text-neutral-900">
      {/* Mobile hamburger */}
      <button
        onClick={() => setMobileOpen(true)}
        data-testid="mobile-menu-open"
        aria-label="Ouvrir le menu"
        className="fixed top-4 left-4 z-40 md:hidden w-10 h-10 rounded-md bg-white border border-neutral-200 flex items-center justify-center hover:bg-neutral-100 transition"
      >
        <List size={18} className="text-neutral-700" />
      </button>

      {/* Mobile backdrop */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 md:hidden bg-neutral-900/40 backdrop-blur-sm"
          onClick={() => setMobileOpen(false)}
        />
      )}

      <aside
        className={`w-[240px] bg-white border-r border-neutral-200 flex flex-col fixed h-screen z-50 transition-transform duration-300 md:translate-x-0 ${
          mobileOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"
        }`}
        data-testid="sidebar"
      >
        <div className="px-5 py-5 border-b border-neutral-200">
          <div className="flex flex-col gap-1.5">
            <AltiaroLogo variant="horizontal" size={20} color="#0A0A0A" />
            <div className="text-[10px] uppercase tracking-[0.12em] text-neutral-500 font-medium pl-[22px]">
              E-commerce Machine
            </div>
          </div>
        </div>

        <nav className="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto scroll-thin">
          <button
            onClick={() => setMobileOpen(false)}
            data-testid="mobile-menu-close"
            aria-label="Fermer"
            className="md:hidden absolute top-4 right-3 p-2 rounded-md hover:bg-neutral-100 text-neutral-600"
          >
            <X size={18} />
          </button>
          {links.map(({ to, label, icon: Icon, testId }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              onClick={() => setMobileOpen(false)}
              data-testid={testId}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 rounded-md text-[13.5px] transition-colors duration-150 ${
                  isActive
                    ? "bg-neutral-100 text-neutral-900 font-medium"
                    : "text-neutral-600 hover:bg-neutral-100/50 hover:text-neutral-900"
                }`
              }
            >
              <Icon size={16} weight="regular" />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="p-3 border-t border-neutral-200">
          {isAdmin && <LLMBudgetPill />}
          <div className="flex items-center gap-3 px-2 py-2">
            <div className="w-8 h-8 rounded-md bg-neutral-100 text-neutral-700 flex items-center justify-center font-semibold text-xs border border-neutral-200">
              {user?.name?.[0]?.toUpperCase() || "?"}
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-[13px] font-medium text-neutral-900 truncate">{user?.name}</div>
              <div className="text-[10px] uppercase tracking-wider text-neutral-500 font-medium">
                {user?.role === "admin" ? "Administrateur" : "Concepteur"}
              </div>
            </div>
            <button
              onClick={handleLogout}
              data-testid="logout-button"
              className="p-1.5 rounded-md text-neutral-500 hover:bg-neutral-100 hover:text-neutral-900 transition-colors"
              title="Déconnexion"
            >
              <SignOut size={16} />
            </button>
          </div>
        </div>
      </aside>

      <main className="flex-1 md:ml-[240px] min-h-screen pt-14 md:pt-0 bg-neutral-50">
        <DomainSkipBanner />
        {children}
      </main>
      {user?.role === "admin" && <CommandPalette />}
      {user?.role && user.role !== "admin" && <CommandMenu />}
      {/* user.role might be 'operator', 'concepteur', 'user', etc. — anything non-admin shows the navigation palette. */}
    </div>
  );
}
