import React, { useEffect, useState, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { api, apiCall } from "../lib/api";
import Layout from "../components/Layout";
import KeywordFinder from "../components/KeywordFinder";
import {
  ArrowLeft,
  CheckCircle,
  Circle,
  Rocket,
  ArrowRight,
  ArrowClockwise,
  Sparkle,
  Eye,
  Package,
  MagnifyingGlass,
  Globe,
  PencilSimple,
} from "@phosphor-icons/react";

const ACTION_BY_STEP = {
  product: { label: "Lancer l'analyse deep", icon: MagnifyingGlass, path: "/niches" },
  countries: { label: "Choisir les pays", icon: Globe, path: null },
  sourcing: { label: "Ouvrir le sourcing", icon: Package, path: "/sites/{id}/sourcing" },
  pricing: { label: "Gérer les produits & prix", icon: Package, path: "/sites/{id}/products" },
  positioning: { label: "Définir positionnement", icon: PencilSimple, path: "/sites/{id}/design" },
  identity: { label: "Générer design + logo IA", icon: Sparkle, path: "/sites/{id}/design" },
  seo: { label: "Recherche mots-clés Google", icon: MagnifyingGlass, action: "keywordFinder" },
  content: { label: "Vérifier le contenu", icon: Eye, path: "/sites/{id}/design" },
  legal: { label: "Vérifier pages légales", icon: Eye, path: "/sites/{id}/design" },
  publish: { label: "Publier la boutique", icon: Rocket, path: "/sites/{id}/design" },
};

export default function Wizard() {
  const { id: siteId } = useParams();
  const navigate = useNavigate();
  const [state, setState] = useState(null);
  const [site, setSite] = useState(null);
  const [loading, setLoading] = useState(true);
  const [marking, setMarking] = useState(null);
  const [showKeywordFinder, setShowKeywordFinder] = useState(false);

  const load = useCallback(async () => {
    const [wRes, sRes] = await Promise.all([
      apiCall(() => api.get(`/sites/${siteId}/wizard`)),
      apiCall(() => api.get(`/sites/${siteId}`)),
    ]);
    if (wRes.data) setState(wRes.data);
    if (sRes.data) setSite(sRes.data);
    setLoading(false);
  }, [siteId]);

  useEffect(() => {
    load();
  }, [load]);

  const mark = async (stepId, status = "done", advance = null) => {
    setMarking(stepId);
    await apiCall(() =>
      api.post(`/sites/${siteId}/wizard/step/${stepId}`, {
        status,
        advance_to: advance,
      })
    );
    setMarking(null);
    await load();
  };

  if (loading) {
    return (
      <Layout>
        <div className="p-12 text-zinc-500">Chargement du wizard…</div>
      </Layout>
    );
  }

  const defs = state?.definition || [];
  const steps = state?.steps || {};
  const percent = state?.progress?.percent || 0;
  const currentId = state?.current;

  return (
    <Layout>
      <div className="p-8 md:p-12 max-w-[1200px]">
        <button
          onClick={() => navigate(`/sites/${siteId}`)}
          className="flex items-center gap-2 text-sm text-zinc-500 hover:text-zinc-100 mb-6 transition"
          data-testid="wizard-back"
        >
          <ArrowLeft size={16} /> Retour au site
        </button>

        <div className="bg-gradient-to-br from-[#1C1917] via-[#44403C] to-[#7C3AED] rounded-md p-8 mb-8 text-white">
          <div className="flex items-start justify-between gap-6">
            <div>
              <div className="text-[11px] uppercase tracking-widest text-white/60 mb-2">
                Wizard de création · 10 étapes guidées
              </div>
              <h1 className="text-3xl font-semibold mb-2">
                Lance ta boutique, étape par étape
              </h1>
              <p className="text-white/80 max-w-2xl">
                Un flow structuré pour aller de l'idée au site publié. Chaque étape pré-remplit la
                suivante avec le contexte de ton analyse deep.
                {site && (
                  <>
                    {" "}
                    Site cible : <strong>{site.name}</strong>
                  </>
                )}
              </p>
            </div>
            <div className="text-right min-w-[180px]">
              <div className="text-[11px] uppercase tracking-widest text-white/60">Avancement</div>
              <div className="text-4xl font-semibold">{percent}%</div>
              <div className="text-sm text-white/70 mt-1">
                {state?.progress?.done} / {state?.progress?.total} étapes complétées
              </div>
              <div className="w-44 h-2 bg-zinc-950/20 rounded-full overflow-hidden mt-3 ml-auto">
                <div
                  className="h-full bg-zinc-950 rounded-full transition-all duration-500"
                  style={{ width: `${percent}%` }}
                />
              </div>
            </div>
          </div>
        </div>

        <div className="space-y-3">
          {defs.map((d, idx) => {
            const st = steps[d.id] || { status: "pending" };
            const done = st.status === "done";
            const isCurrent = currentId === d.id;
            const Action = ACTION_BY_STEP[d.id] || {};
            const actionPath = Action.path ? Action.path.replace("{id}", siteId) : null;
            const ActionIcon = Action.icon || ArrowRight;

            return (
              <div
                key={d.id}
                data-testid={`wizard-step-${d.id}`}
                className={`bg-zinc-950 rounded-xl border p-5 transition ${
                  done
                    ? "border-[#D1FAE5]"
                    : isCurrent
                    ? "border-[#7C3AED] shadow-md"
                    : "border-zinc-800"
                }`}
              >
                <div className="flex items-start gap-4">
                  <div className="flex flex-col items-center">
                    <div
                      className={`w-10 h-10 rounded-full flex items-center justify-center text-lg ${
                        done
                          ? "bg-emerald-500/10"
                          : isCurrent
                          ? "bg-[#EDE9FE]"
                          : "bg-zinc-800"
                      }`}
                    >
                      {done ? (
                        <CheckCircle size={22} weight="fill" className="text-emerald-400" />
                      ) : (
                        <span>{d.icon}</span>
                      )}
                    </div>
                    {idx < defs.length - 1 && (
                      <div className="w-px h-8 bg-[#E7E5E4] mt-1" />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs font-mono text-zinc-500">
                        Étape {idx + 1}/10
                      </span>
                      {done && (
                        <span className="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 font-medium">
                          ✓ Complétée
                        </span>
                      )}
                      {isCurrent && !done && (
                        <span className="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full bg-[#EDE9FE] text-[#6D28D9] font-medium">
                          En cours
                        </span>
                      )}
                    </div>
                    <h3 className="text-lg font-semibold text-zinc-100 mb-1">
                      {d.title}
                    </h3>
                    <p className="text-sm text-zinc-400">{d.desc}</p>
                  </div>
                  <div className="flex flex-col gap-2 items-end">
                    {actionPath && (
                      <button
                        onClick={() => navigate(actionPath)}
                        data-testid={`wizard-action-${d.id}`}
                        className="h-9 px-3 rounded-lg bg-white hover:bg-zinc-200 text-black text-xs font-medium flex items-center gap-1.5 transition whitespace-nowrap"
                      >
                        <ActionIcon size={12} weight="bold" /> {Action.label}
                      </button>
                    )}
                    {Action.action === "keywordFinder" && (
                      <button
                        onClick={() => setShowKeywordFinder(true)}
                        data-testid={`wizard-action-${d.id}`}
                        className="h-9 px-3 rounded-lg bg-gradient-to-r from-[#4285F4] to-[#6D28D9] hover:opacity-90 text-white text-xs font-medium flex items-center gap-1.5 transition whitespace-nowrap"
                      >
                        <ActionIcon size={12} weight="bold" /> {Action.label}
                      </button>
                    )}
                    {!done ? (
                      <button
                        onClick={() =>
                          mark(d.id, "done", defs[idx + 1]?.id || null)
                        }
                        disabled={marking === d.id}
                        data-testid={`wizard-mark-done-${d.id}`}
                        className="h-9 px-3 rounded-lg bg-zinc-950 border border-[#D1FAE5] hover:bg-emerald-500/10/40 text-emerald-400 text-xs font-medium flex items-center gap-1.5 transition disabled:opacity-60"
                      >
                        {marking === d.id ? (
                          <ArrowClockwise size={12} className="animate-spin" />
                        ) : (
                          <CheckCircle size={12} weight="fill" />
                        )}
                        Marquer fait
                      </button>
                    ) : (
                      <button
                        onClick={() => mark(d.id, "pending")}
                        disabled={marking === d.id}
                        data-testid={`wizard-reopen-${d.id}`}
                        className="h-9 px-3 rounded-lg bg-zinc-950 border border-zinc-800 hover:border-[#78716C] text-zinc-400 text-xs font-medium flex items-center gap-1.5 transition disabled:opacity-60"
                      >
                        <Circle size={12} /> Rouvrir
                      </button>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {percent === 100 && (
          <div className="mt-8 bg-gradient-to-r from-[#D1FAE5] to-[#A7F3D0] border border-[#047857]/20 rounded-xl p-6 flex items-start gap-4">
            <div className="w-12 h-12 rounded-full bg-[#047857] flex items-center justify-center shrink-0">
              <Rocket size={22} weight="fill" className="text-white" />
            </div>
            <div className="flex-1">
              <div className="text-lg font-semibold text-emerald-300 mb-1">
                🎉 Ta boutique est prête !
              </div>
              <p className="text-sm text-emerald-300">
                Les 10 étapes sont complétées. Tu peux maintenant ouvrir ta boutique en public ou
                brancher un domaine custom.
              </p>
              <div className="flex gap-2 mt-3">
                <a
                  href={`/shop/${siteId}`}
                  target="_blank"
                  rel="noreferrer"
                  data-testid="wizard-open-shop"
                  className="h-10 px-4 rounded-xl bg-[#047857] hover:bg-[#065F46] text-white text-sm font-medium flex items-center gap-2 transition"
                >
                  <Eye size={14} /> Voir la boutique
                </a>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Floating Keyword Finder button — always accessible */}
      <button
        onClick={() => setShowKeywordFinder(true)}
        data-testid="wizard-floating-kwfinder"
        title="Recherche de mots-clés Google"
        className="fixed bottom-24 right-6 h-12 px-4 rounded-full bg-gradient-to-r from-[#4285F4] to-[#6D28D9] text-white text-sm font-medium flex items-center gap-2 shadow-lg hover:shadow-xl transition z-40"
      >
        <MagnifyingGlass size={16} weight="bold" />
        Mots-clés Google
      </button>

      {showKeywordFinder && (
        <KeywordFinder
          initialSeed={site?.niche || ""}
          initialCountry={(site?.selected_countries || ["FR"])[0]}
          onClose={() => setShowKeywordFinder(false)}
        />
      )}
    </Layout>
  );
}
