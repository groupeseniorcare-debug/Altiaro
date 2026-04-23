import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, apiCall } from "../lib/api";
import { useAuth } from "../lib/auth";
import Layout from "../components/Layout";
import { Plus, Storefront, ArrowRight } from "@phosphor-icons/react";

export default function Sites() {
  const [sites, setSites] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";

  useEffect(() => {
    (async () => {
      const { data } = await apiCall(() => api.get("/sites"));
      setSites(data || []);
      setLoading(false);
    })();
  }, []);

  return (
    <Layout>
      <div className="p-8 md:p-12 max-w-[1400px]">
        <div className="flex items-start justify-between mb-10 animate-fade-up">
          <div>
            <div className="text-[11px] uppercase tracking-widest text-neutral-500 mb-2">Portefeuille</div>
            <h1 className="text-3xl font-semibold text-neutral-900">
              {isAdmin ? "Sites" : "Mes sites"}
            </h1>
            <p className="text-neutral-600 mt-2">
              {isAdmin
                ? "Gérez toutes vos marques et suivez leur progression."
                : "Tes boutiques. Lance-en une nouvelle depuis une analyse de niche."}
            </p>
          </div>
          <button
            onClick={() => navigate("/sites/new")}
            data-testid="create-site-btn"
            className="h-11 px-5 rounded-xl bg-neutral-900 hover:bg-neutral-800 text-white font-medium transition-all duration-200 flex items-center gap-2 active:scale-[0.98] shadow-sm"
          >
            <Plus size={18} weight="bold" /> {isAdmin ? "Lancer un site" : "Lancer ma boutique"}
          </button>
        </div>

        {loading ? (
          <div
            className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5"
            data-testid="sites-list-skeleton"
            aria-busy="true"
          >
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="bg-white rounded-xl border border-neutral-200 p-6">
                <div className="flex items-start justify-between mb-4">
                  <div className="w-10 h-10 rounded-lg bg-stone-200 animate-pulse" />
                  <div className="w-16 h-5 rounded-full bg-stone-200 animate-pulse" />
                </div>
                <div className="h-5 w-40 bg-stone-200 rounded animate-pulse mb-2" />
                <div className="h-4 w-56 bg-stone-200 rounded animate-pulse mb-5" />
                <div className="h-2 w-full bg-stone-200 rounded-full animate-pulse mb-3" />
                <div className="h-3 w-32 bg-stone-200 rounded animate-pulse mb-4" />
                <div className="pt-3 border-t border-neutral-200 flex justify-between">
                  <div className="h-3 w-40 bg-stone-200 rounded animate-pulse" />
                  <div className="h-3 w-4 bg-stone-200 rounded animate-pulse" />
                </div>
              </div>
            ))}
          </div>
        ) : sites.length === 0 ? (
          <div className="bg-white rounded-xl border border-neutral-200 p-12 text-center">
            <div className="w-14 h-14 rounded-full bg-neutral-200 flex items-center justify-center mx-auto mb-5">
              <Storefront size={28} weight="duotone" color="#B84B31" />
            </div>
            <h3 className="text-lg font-semibold text-neutral-900 mb-2">
              {isAdmin ? "Aucun site pour l'instant" : "Crée ta première boutique"}
            </h3>
            <p className="text-neutral-600 mb-6 max-w-md mx-auto">
              {isAdmin
                ? "Lancez votre première marque. Les 50 étapes du playbook seront automatiquement chargées."
                : "Commence par une analyse de niche deep. Dès qu'elle passe en GO, tu peux lancer la boutique en 1 clic."}
            </p>
            <button
              onClick={() => navigate(isAdmin ? "/sites/new" : "/niches")}
              data-testid="create-first-site"
              className="h-11 px-5 rounded-xl bg-neutral-900 hover:bg-neutral-800 text-white font-medium inline-flex items-center gap-2 transition"
            >
              <Plus size={18} weight="bold" />
              {isAdmin ? "Lancer mon premier site" : "Analyser une niche"}
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {sites.map((s, i) => (
              <div
                key={s.id}
                onClick={() => navigate(`/sites/${s.id}`)}
                data-testid={`site-card-${s.id}`}
                className={`bg-white rounded-xl border border-neutral-200 p-6 cursor-pointer hover:border-[#B84B31]/40 hover:shadow-md transition-all duration-250 animate-fade-up-delay-${Math.min(i + 1, 4)}`}
              >
                <div className="flex items-start justify-between mb-4">
                  <div className="w-10 h-10 rounded-lg bg-neutral-200 flex items-center justify-center">
                    <Storefront size={20} weight="duotone" color="#B84B31" />
                  </div>
                  <span
                    className={`text-[11px] uppercase tracking-widest px-2.5 py-1 rounded-full ${
                      s.status === "active"
                        ? "bg-emerald-500/10 text-emerald-400"
                        : s.status === "live"
                        ? "bg-[#E0F2FE] text-[#0369A1]"
                        : "bg-[#F5F5F4] text-neutral-500"
                    }`}
                  >
                    {s.status}
                  </span>
                </div>
                <h3 className="text-lg font-semibold text-neutral-900 mb-1">{s.name}</h3>
                <div className="text-sm text-neutral-500 mb-4 line-clamp-2">{s.niche}</div>

                <div className="mb-2 flex justify-between text-xs text-neutral-500">
                  <span>Avancement</span>
                  <span className="font-medium text-neutral-900">{s.progress_pct}%</span>
                </div>
                <div className="h-2 bg-neutral-200 rounded-full overflow-hidden mb-3">
                  <div
                    className="h-full bg-white rounded-full transition-all duration-500"
                    style={{ width: `${s.progress_pct}%` }}
                  />
                </div>
                <div className="text-xs text-neutral-600 mb-4">
                  {s.progress_validated}/{s.progress_total} étapes validées
                  {s.progress_pending > 0 && (
                    <span className="ml-2 text-[#0369A1]">· {s.progress_pending} en attente</span>
                  )}
                </div>

                <div className="flex items-center justify-between pt-3 border-t border-neutral-200">
                  <div className="text-xs text-neutral-500">
                    {s.current_step_title ? (
                      <>Étape {s.current_step_number}: {s.current_step_title.substring(0, 30)}...</>
                    ) : (
                      "Tous les prompts complétés 🎉"
                    )}
                  </div>
                  <ArrowRight size={16} className="text-neutral-900" />
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </Layout>
  );
}
