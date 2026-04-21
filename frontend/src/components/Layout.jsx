import React, { useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../lib/auth";
import CommandPalette from "./CommandPalette";
import CopilotFab from "./CopilotFab";
import { List, X } from "@phosphor-icons/react";
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
} from "@phosphor-icons/react";

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
        { to: "/validations", label: "Activité", icon: CheckSquare, testId: "nav-validations" },
        { to: "/finances", label: "Finances", icon: ChartLineUp, testId: "nav-finances" },
        { to: "/billing", label: "Paiements", icon: CreditCard, testId: "nav-billing" },
        { to: "/users", label: "Équipe", icon: Users, testId: "nav-users" },
      ]
    : [
        { to: "/", label: "Dashboard", icon: House, testId: "nav-dashboard" },
        { to: "/sites", label: "Sites", icon: SquaresFour, testId: "nav-sites" },
        { to: "/sites/new", label: "Lancer un site", icon: Rocket, testId: "nav-launch" },
        { to: "/finances", label: "Finance", icon: ChartLineUp, testId: "nav-finances" },
        { to: "/billing", label: "Compte", icon: CreditCard, testId: "nav-billing" },
      ];

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  return (
    <div className="min-h-screen flex bg-black text-zinc-100">
      {/* Mobile hamburger */}
      <button
        onClick={() => setMobileOpen(true)}
        data-testid="mobile-menu-open"
        aria-label="Ouvrir le menu"
        className="fixed top-4 left-4 z-40 md:hidden w-10 h-10 rounded-md bg-zinc-950 border border-zinc-800 flex items-center justify-center hover:bg-zinc-900 transition"
      >
        <List size={18} className="text-zinc-300" />
      </button>

      {/* Mobile backdrop */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 md:hidden bg-black/70 backdrop-blur-sm"
          onClick={() => setMobileOpen(false)}
        />
      )}

      <aside
        className={`w-[240px] bg-black border-r border-zinc-900 flex flex-col fixed h-screen z-50 transition-transform duration-300 md:translate-x-0 ${
          mobileOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"
        }`}
        data-testid="sidebar"
      >
        <div className="px-5 py-5 border-b border-zinc-900">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-md bg-white flex items-center justify-center">
              <Rocket size={16} weight="fill" color="#000000" />
            </div>
            <div>
              <div className="font-semibold text-[15px] leading-tight text-zinc-100 tracking-tight">
                Concept Factory
              </div>
              <div className="text-[10px] uppercase tracking-[0.12em] text-zinc-500 font-medium">
                E-commerce Machine
              </div>
            </div>
          </div>
        </div>

        <nav className="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto scroll-thin">
          <button
            onClick={() => setMobileOpen(false)}
            data-testid="mobile-menu-close"
            aria-label="Fermer"
            className="md:hidden absolute top-4 right-3 p-2 rounded-md hover:bg-zinc-900 text-zinc-400"
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
                    ? "bg-zinc-900 text-zinc-100 font-medium"
                    : "text-zinc-400 hover:bg-zinc-900/50 hover:text-zinc-100"
                }`
              }
            >
              <Icon size={16} weight="regular" />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="p-3 border-t border-zinc-900">
          <div className="flex items-center gap-3 px-2 py-2">
            <div className="w-8 h-8 rounded-md bg-zinc-900 text-zinc-300 flex items-center justify-center font-semibold text-xs border border-zinc-800">
              {user?.name?.[0]?.toUpperCase() || "?"}
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-[13px] font-medium text-zinc-100 truncate">{user?.name}</div>
              <div className="text-[10px] uppercase tracking-wider text-zinc-500 font-medium">
                {user?.role === "admin" ? "Administrateur" : "Concepteur"}
              </div>
            </div>
            <button
              onClick={handleLogout}
              data-testid="logout-button"
              className="p-1.5 rounded-md text-zinc-500 hover:bg-zinc-900 hover:text-zinc-100 transition-colors"
              title="Déconnexion"
            >
              <SignOut size={16} />
            </button>
          </div>
        </div>
      </aside>

      <main className="flex-1 md:ml-[240px] min-h-screen pt-14 md:pt-0 bg-zinc-950/50">{children}</main>
      {user?.role === "admin" && <CommandPalette />}
      {user && <CopilotFab user={user} />}
    </div>
  );
}
