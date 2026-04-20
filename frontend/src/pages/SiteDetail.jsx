import React, { useEffect, useState, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { api, apiCall } from "../lib/api";
import { useAuth } from "../lib/auth";
import Layout from "../components/Layout";
import StepPanel from "../components/StepPanel";
import {
  ArrowLeft,
  Lock,
  Clock,
  CheckCircle,
  XCircle,
  Storefront,
  Link as LinkIcon,
  Package,
  Eye,
} from "@phosphor-icons/react";

const STATUS_CONFIG = {
  locked: { label: "Verrouillée", icon: Lock, bg: "#F5F5F4", text: "#78716C" },
  in_progress: { label: "En cours", icon: Clock, bg: "#FEF3C7", text: "#B45309" },
  awaiting_validation: { label: "Complétée", icon: CheckCircle, bg: "#D1FAE5", text: "#047857" },
  validated: { label: "Validée", icon: CheckCircle, bg: "#D1FAE5", text: "#047857" },
  rejected: { label: "À refaire", icon: XCircle, bg: "#FFE4E6", text: "#BE123C" },
  blocked: { label: "Bloquée", icon: XCircle, bg: "#FFE4E6", text: "#BE123C" },
};

export default function SiteDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [site, setSite] = useState(null);
  const [steps, setSteps] = useState([]);
  const [selectedStep, setSelectedStep] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    const [siteRes, stepsRes] = await Promise.all([
      apiCall(() => api.get(`/sites/${id}`)),
      apiCall(() => api.get(`/sites/${id}/steps`)),
    ]);
    if (siteRes.data) setSite(siteRes.data);
    if (stepsRes.data) setSteps(stepsRes.data);
    setLoading(false);
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  const handleStepUpdate = (updated) => {
    setSteps((prev) => prev.map((s) => (s.id === updated.id ? updated : s)));
    setSelectedStep(updated);
    // also refresh to unlock next step
    load();
  };

  const handleClosePanel = () => {
    setSelectedStep(null);
    load();
  };

  if (loading) {
    return (
      <Layout>
        <div className="p-8 md:p-12 text-[#78716C]">Chargement du site...</div>
      </Layout>
    );
  }

  if (!site) {
    return (
      <Layout>
        <div className="p-8 md:p-12">
          <div className="text-[#BE123C]">Site introuvable.</div>
        </div>
      </Layout>
    );
  }

  // Group steps by phase
  const phaseGroups = {};
  steps.forEach((s) => {
    if (!phaseGroups[s.phase]) phaseGroups[s.phase] = { name: s.phase_name, steps: [] };
    phaseGroups[s.phase].steps.push(s);
  });

  const totalValidated = steps.filter((s) => s.status === "validated").length;
  const progress = steps.length ? Math.round((totalValidated / steps.length) * 100) : 0;

  return (
    <Layout>
      <div className="p-8 md:p-12 max-w-[1400px]">
        <button
          onClick={() => navigate("/sites")}
          className="flex items-center gap-2 text-sm text-[#78716C] hover:text-[#1C1917] mb-6 transition"
          data-testid="back-to-sites"
        >
          <ArrowLeft size={16} /> Retour aux sites
        </button>

        <div className="bg-white rounded-xl border border-[#E7E5E4] p-8 mb-8 animate-fade-up">
          <div className="flex items-start justify-between gap-8">
            <div className="flex-1">
              <div className="flex items-center gap-3 mb-3">
                <div className="w-11 h-11 rounded-lg bg-[#F5F2EB] flex items-center justify-center">
                  <Storefront size={22} weight="duotone" color="#B84B31" />
                </div>
                <span
                  className={`text-[11px] uppercase tracking-widest px-2.5 py-1 rounded-full ${
                    site.status === "active"
                      ? "bg-[#D1FAE5] text-[#047857]"
                      : site.status === "live"
                      ? "bg-[#E0F2FE] text-[#0369A1]"
                      : "bg-[#F5F5F4] text-[#78716C]"
                  }`}
                >
                  {site.status}
                </span>
              </div>
              <h1 className="font-heading text-4xl font-semibold text-[#1C1917] mb-2">{site.name}</h1>
              <p className="text-[#57534E] max-w-2xl">{site.niche}</p>
              <div className="flex flex-wrap gap-4 mt-4 text-sm">
                {site.domain && (
                  <div className="flex items-center gap-1.5 text-[#57534E]">
                    <LinkIcon size={14} /> {site.domain}
                  </div>
                )}
                {site.shopify_url && (
                  <a
                    href={site.shopify_url}
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-center gap-1.5 text-[#B84B31] hover:underline"
                    data-testid="site-shopify-link"
                  >
                    <LinkIcon size={14} /> Shopify admin
                  </a>
                )}
              </div>

              <div className="flex flex-wrap gap-2 mt-5">
                <button
                  onClick={() => navigate(`/sites/${id}/products`)}
                  data-testid="manage-products"
                  className="h-10 px-4 rounded-xl bg-[#1C1917] hover:bg-[#44403C] text-white text-sm font-medium flex items-center gap-2 transition"
                >
                  <Package size={16} weight="bold" /> Gérer les produits
                </button>
                <a
                  href={`/shop/${id}`}
                  target="_blank"
                  rel="noreferrer"
                  data-testid="view-storefront"
                  className="h-10 px-4 rounded-xl bg-white border border-[#E7E5E4] hover:border-[#B84B31] text-[#1C1917] text-sm font-medium flex items-center gap-2 transition"
                >
                  <Eye size={16} /> Voir la boutique
                </a>
              </div>
            </div>

            <div className="text-right">
              <div className="text-[11px] uppercase tracking-widest text-[#78716C] mb-1">Avancement</div>
              <div className="font-heading text-4xl font-semibold text-[#1C1917]">{progress}%</div>
              <div className="text-sm text-[#57534E] mt-1">
                {totalValidated} / {steps.length} étapes validées
              </div>
              <div className="w-48 h-2 bg-[#F5F2EB] rounded-full overflow-hidden mt-3">
                <div
                  className="h-full bg-[#B84B31] rounded-full transition-all duration-500"
                  style={{ width: `${progress}%` }}
                />
              </div>
            </div>
          </div>
        </div>

        <div className="space-y-10">
          {Object.entries(phaseGroups).map(([phase, group], pidx) => {
            const phaseValidated = group.steps.filter((s) => s.status === "validated").length;
            return (
              <div key={phase} data-testid={`phase-${phase}`}>
                <div className="flex items-baseline gap-3 mb-5">
                  <div className="w-8 h-8 rounded-lg bg-[#1C1917] text-white flex items-center justify-center font-heading font-semibold text-sm">
                    {phase}
                  </div>
                  <h2 className="font-heading text-xl font-semibold text-[#1C1917]">{group.name}</h2>
                  <div className="text-xs text-[#78716C] font-medium">
                    {phaseValidated}/{group.steps.length} validées
                  </div>
                </div>

                <div className="relative">
                  <div className="absolute left-[15px] top-6 bottom-6 w-px bg-[#E7E5E4]" />
                  <div className="space-y-3">
                    {group.steps.map((step) => {
                      const cfg = STATUS_CONFIG[step.status] || STATUS_CONFIG.locked;
                      const Icon = cfg.icon;
                      const clickable = step.status !== "locked";
                      return (
                        <button
                          key={step.id}
                          disabled={!clickable}
                          onClick={() => setSelectedStep(step)}
                          data-testid={`step-${step.number}`}
                          className={`w-full flex items-center gap-4 text-left rounded-xl border px-5 py-4 transition-all duration-200 ${
                            clickable
                              ? "bg-white border-[#E7E5E4] hover:border-[#B84B31]/50 hover:shadow-sm cursor-pointer"
                              : "bg-[#FAF7F2] border-[#F5F2EB] cursor-not-allowed opacity-70"
                          }`}
                        >
                          <div
                            className="relative z-10 w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0"
                            style={{ backgroundColor: cfg.bg }}
                          >
                            <Icon size={14} weight="bold" style={{ color: cfg.text }} />
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-baseline gap-2 mb-0.5">
                              <span className="text-xs font-mono text-[#78716C]">#{step.number}</span>
                              <span className="font-medium text-[#1C1917]">{step.title}</span>
                            </div>
                            <div className="text-sm text-[#78716C] truncate">{step.summary}</div>
                          </div>
                          <span
                            className="text-[10px] uppercase tracking-widest px-2 py-1 rounded-full whitespace-nowrap"
                            style={{ backgroundColor: cfg.bg, color: cfg.text }}
                          >
                            {cfg.label}
                          </span>
                        </button>
                      );
                    })}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {selectedStep && (
        <StepPanel
          step={selectedStep}
          site={site}
          isAdmin={user?.role === "admin"}
          onClose={handleClosePanel}
          onUpdate={handleStepUpdate}
        />
      )}
    </Layout>
  );
}
