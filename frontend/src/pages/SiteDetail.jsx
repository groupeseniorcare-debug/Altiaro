import React, { useEffect, useState, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { ArrowLeft } from "@phosphor-icons/react";
import { api, apiCall } from "../lib/api";
import { useAuth } from "../lib/auth";
import Layout from "../components/Layout";
import CockpitJourney from "../components/CockpitJourney";
import SiteHeaderCompact from "../components/cockpit/SiteHeaderCompact";
import PostValidationBanner from "../components/cockpit/PostValidationBanner";
import DomainModal from "../components/cockpit/DomainModal";
// Widgets post-étape 8 / post-étape 9 (gatés visuellement par progression)
import PulseSEOWidget from "../components/PulseSEOWidget";
import SEOCoachBell from "../components/SEOCoachBell";
import MerchantShoppingPanel from "../components/MerchantShoppingPanel";
import SiteQAPanel from "../components/SiteQAPanel";

/**
 * Chantier 6 — Cockpit ultra-épuré.
 * Règles (cf. brief) :
 *   - 1 header compact + CockpitJourney central. Point.
 *   - Widgets SEO/AEO/GMC/QA MASQUÉS tant que l'étape courante < 8.
 *   - `current_step` dérivé de GET /sites/:id/journey (single source of truth).
 *   - Site totalement validé → PostValidationBanner + sidebar complète.
 */
export default function SiteDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [site, setSite] = useState(null);
  const [status, setStatus] = useState(null);
  const [domainStatus, setDomainStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showDomain, setShowDomain] = useState(false);
  const [domainInput, setDomainInput] = useState("");
  const [domainBusy, setDomainBusy] = useState(false);
  const [domainMsg, setDomainMsg] = useState(null);

  const load = useCallback(async () => {
    const [siteRes, journeyRes, domRes] = await Promise.all([
      apiCall(() => api.get(`/sites/${id}`)),
      apiCall(() => api.get(`/sites/${id}/journey`)),
      apiCall(() => api.get(`/sites/${id}/domain`)),
    ]);
    if (siteRes.data) setSite(siteRes.data);
    if (journeyRes.data) {
      // Adapte la shape /journey vers celle attendue par le header compact
      const j = journeyRes.data;
      setStatus({
        steps: j.steps,
        completed_count: j.progress?.complete ?? 0,
        total_count: j.progress?.total ?? 9,
        progress_pct: j.progress?.pct ?? 0,
        all_completed: j.all_completed,
        current_step: j.current_step,
      });
    }
    if (domRes.data) {
      setDomainStatus(domRes.data);
      setDomainInput(domRes.data.custom_domain || "");
    }
    setLoading(false);
  }, [id]);

  useEffect(() => { load(); }, [load]);

  // ───── Gating visuel par progression ───── //
  const steps = status?.steps || [];
  // /journey expose status.current_step (slug) + all_completed. On dérive
  // currentStepIdx depuis l'ordre des steps renvoyés.
  const currentIdx = steps.findIndex((s) => s.status === "current");
  const currentStepIdx = currentIdx === -1 ? steps.length + 1 : currentIdx + 1;
  const canShowSeoSidebar = currentStepIdx >= 8;
  const canShowQa = currentStepIdx >= 9;
  const allCompleted = status?.all_completed === true;

  // ───── Domain modal handlers ───── //
  const refreshDomain = async () => {
    const r = await apiCall(() => api.get(`/sites/${id}/domain`));
    if (r.data) setDomainStatus(r.data);
  };
  const handleSaveDomain = async () => {
    setDomainBusy(true); setDomainMsg(null);
    const { data, error } = await apiCall(() =>
      api.post(`/sites/${id}/domain`, { custom_domain: domainInput.trim() })
    );
    setDomainBusy(false);
    if (error) return setDomainMsg({ kind: "err", text: error });
    setDomainStatus(data);
    setDomainMsg({ kind: "ok", text: "Domaine enregistré. Configurez le CNAME puis cliquez Vérifier." });
  };
  const handleVerifyDomain = async () => {
    setDomainBusy(true); setDomainMsg(null);
    const { data, error } = await apiCall(() => api.post(`/sites/${id}/domain/verify`));
    setDomainBusy(false);
    if (error) return setDomainMsg({ kind: "err", text: error });
    setDomainMsg({
      kind: data.verified ? "ok" : "warn",
      text: data.verified ? `✓ Vérifié · ${data.reason}` : data.reason,
    });
    await refreshDomain();
  };
  const handleClearDomain = async () => {
    if (!window.confirm("Supprimer le domaine custom et revenir sur l'URL Altiaro ?")) return;
    await apiCall(() => api.delete(`/sites/${id}/domain`));
    setDomainInput(""); setDomainMsg(null);
    await refreshDomain();
  };

  if (loading) return <Layout><div className="p-8 md:p-12 text-neutral-500">Chargement du site…</div></Layout>;
  if (!site) return <Layout><div className="p-8 md:p-12 text-red-500">Site introuvable.</div></Layout>;

  const isAdmin = user?.role === "admin";
  const adminEmail = process.env.REACT_APP_ADMIN_EMAIL || "admin@altiaro.com";

  return (
    <Layout>
      <div className="p-6 md:p-10 max-w-[1400px] mx-auto w-full">
        <button
          onClick={() => navigate("/sites")}
          className="flex items-center gap-2 text-sm text-neutral-500 hover:text-neutral-900 mb-5 transition"
          data-testid="back-to-sites"
        >
          <ArrowLeft size={16} /> Retour aux sites
        </button>

        <SiteHeaderCompact
          site={site}
          status={status}
          domainStatus={domainStatus}
          onOpenDomainModal={() => setShowDomain(true)}
        />

        {allCompleted && <PostValidationBanner site={site} adminEmail={adminEmail} />}

        <div className={`grid gap-6 ${canShowSeoSidebar ? "lg:grid-cols-[1fr_340px]" : "grid-cols-1"}`}>
          <div className="min-w-0">
            <CockpitJourney site={site} onRefresh={load} />
          </div>

          {canShowSeoSidebar && (
            <aside className="space-y-5" data-testid="cockpit-sidebar-seo">
              <div className="bg-white rounded-xl border border-neutral-200 p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[11px] uppercase tracking-widest text-neutral-500">Alertes SEO</span>
                  <SEOCoachBell siteId={id} />
                </div>
                <p className="text-xs text-neutral-500 leading-relaxed">
                  Ces outils apparaissent à partir de l'étape 8. Ils se mettent à jour en temps
                  réel avec tes actions sur les pages SEO et les contenus.
                </p>
              </div>
              <PulseSEOWidget siteId={id} compact />
              {isAdmin && <MerchantShoppingPanel siteId={id} isAdmin />}
              {canShowQa && <SiteQAPanel site={site} />}
            </aside>
          )}
        </div>
      </div>

      {showDomain && (
        <DomainModal
          status={domainStatus}
          input={domainInput}
          setInput={setDomainInput}
          busy={domainBusy}
          msg={domainMsg}
          onSave={handleSaveDomain}
          onVerify={handleVerifyDomain}
          onClear={handleClearDomain}
          onClose={() => { setShowDomain(false); setDomainMsg(null); }}
        />
      )}
    </Layout>
  );
}
