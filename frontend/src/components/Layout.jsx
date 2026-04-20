import React from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../lib/auth";
import {
  House,
  SquaresFour,
  CheckSquare,
  ChartLineUp,
  Users,
  SignOut,
  Rocket,
} from "@phosphor-icons/react";

export default function Layout({ children }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const links = [
    { to: "/", label: "Tableau de bord", icon: House, testId: "nav-dashboard" },
    { to: "/sites", label: "Sites", icon: SquaresFour, testId: "nav-sites" },
    ...(user?.role === "admin"
      ? [
          { to: "/validations", label: "Activité", icon: CheckSquare, testId: "nav-validations" },
          { to: "/finances", label: "Finances", icon: ChartLineUp, testId: "nav-finances" },
          { to: "/users", label: "Équipe", icon: Users, testId: "nav-users" },
        ]
      : [{ to: "/finances", label: "Mes paiements", icon: ChartLineUp, testId: "nav-finances" }]),
  ];

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  return (
    <div className="min-h-screen flex bg-[#FDFBF7]">
      <aside
        className="w-[260px] bg-[#F5F2EB] border-r border-[#E7E5E4] flex flex-col fixed h-screen"
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
          {links.map(({ to, label, icon: Icon, testId }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
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

      <main className="flex-1 ml-[260px] min-h-screen">{children}</main>
    </div>
  );
}
