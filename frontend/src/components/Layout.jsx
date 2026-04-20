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
} from "@phosphor-icons/react";

export default function Layout({ children }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [mobileOpen, setMobileOpen] = useState(false);

  const links = [
    { to: "/", label: "Tableau de bord", icon: House, testId: "nav-dashboard" },
    { to: "/sites", label: "Sites", icon: SquaresFour, testId: "nav-sites" },
    { to: "/niches", label: "Niche Engine", icon: Target, testId: "nav-niches" },
    ...(user?.role === "admin"
      ? [
          { to: "/empire", label: "Empire", icon: Globe, testId: "nav-empire" },
          { to: "/orders", label: "Commandes", icon: Package, testId: "nav-orders" },
          { to: "/admin/payouts", label: "Virements", icon: Bank, testId: "nav-admin-payouts" },
          { to: "/validations", label: "Activité", icon: CheckSquare, testId: "nav-validations" },
          { to: "/finances", label: "Finances", icon: ChartLineUp, testId: "nav-finances" },
          { to: "/billing", label: "Paiements", icon: CreditCard, testId: "nav-billing" },
          { to: "/users", label: "Équipe", icon: Users, testId: "nav-users" },
        ]
      : [
          { to: "/billing", label: "Mon compte", icon: CreditCard, testId: "nav-billing" },
          { to: "/finances", label: "Mes paiements", icon: ChartLineUp, testId: "nav-finances" },
        ]),
  ];

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  return (
    <div className="min-h-screen flex bg-[#FDFBF7]">
      {/* Mobile hamburger */}
      <button
        onClick={() => setMobileOpen(true)}
        data-testid="mobile-menu-open"
        aria-label="Ouvrir le menu"
        className="fixed top-4 left-4 z-40 md:hidden w-11 h-11 rounded-xl bg-white border border-[#E7E5E4] shadow-sm flex items-center justify-center hover:bg-[#F5F2EB] transition"
      >
        <List size={20} />
      </button>

      {/* Mobile backdrop */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 md:hidden bg-black/40 backdrop-blur-sm"
          onClick={() => setMobileOpen(false)}
        />
      )}

      <aside
        className={`w-[260px] bg-[#F5F2EB] border-r border-[#E7E5E4] flex flex-col fixed h-screen z-50 transition-transform duration-300 md:translate-x-0 ${
          mobileOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"
        }`}
        data-testid="sidebar"
      >
        <div className="px-6 py-7 border-b border-[#E7E5E4]">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-lg bg-[#B84B31] flex items-center justify-center">
              <Rocket size={18} weight="fill" color="white" />
            </div>
            <div>
              <div className="font-heading font-semibold text-lg leading-tight text-[#1C1917]">
                Concept Factory
              </div>
              <div className="text-[11px] uppercase tracking-widest text-[#78716C]">
                E-commerce Machine
              </div>
            </div>
          </div>
        </div>

        <nav className="flex-1 px-3 py-5 space-y-1">
          <button
            onClick={() => setMobileOpen(false)}
            data-testid="mobile-menu-close"
            aria-label="Fermer"
            className="md:hidden absolute top-4 right-3 p-2 rounded-lg hover:bg-white/60"
          >
            <X size={20} />
          </button>
          {links.map(({ to, label, icon: Icon, testId }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              onClick={() => setMobileOpen(false)}
              data-testid={testId}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-[14.5px] transition-all duration-200 ${
                  isActive
                    ? "bg-white text-[#B84B31] font-medium shadow-sm"
                    : "text-[#57534E] hover:bg-white/60 hover:text-[#1C1917]"
                }`
              }
            >
              <Icon size={18} weight="regular" />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="p-3 border-t border-[#E7E5E4]">
          <div className="flex items-center gap-3 px-3 py-2.5">
            <div className="w-9 h-9 rounded-full bg-[#B84B31] text-white flex items-center justify-center font-heading font-semibold text-sm">
              {user?.name?.[0]?.toUpperCase() || "?"}
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-[13.5px] font-medium text-[#1C1917] truncate">{user?.name}</div>
              <div className="text-[11px] uppercase tracking-wider text-[#78716C]">
                {user?.role === "admin" ? "Administrateur" : "Concepteur"}
              </div>
            </div>
            <button
              onClick={handleLogout}
              data-testid="logout-button"
              className="p-2 rounded-lg text-[#78716C] hover:bg-white hover:text-[#B84B31] transition"
              title="Déconnexion"
            >
              <SignOut size={18} />
            </button>
          </div>
        </div>
      </aside>

      <main className="flex-1 md:ml-[260px] min-h-screen pt-14 md:pt-0">{children}</main>
      {user?.role === "admin" && <CommandPalette />}
      {user && <CopilotFab user={user} />}
    </div>
  );
}
