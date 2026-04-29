import React, { useEffect, useState, useCallback, useMemo } from "react";
import { Link, useParams, useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  ArrowRight,
  Eye,
  Globe,
  Storefront,
  ChartLineUp,
  Gear,
  CheckCircle,
  Warning,
  Sparkle,
  ShieldCheck,
} from "@phosphor-icons/react";
import { api, apiCall } from "../lib/api";
import { useAuth } from "../lib/auth";
import Layout from "../components/Layout";
import CockpitJourney from "../components/CockpitJourney";
import PostValidationBanner from "../components/cockpit/PostValidationBanner";
import DomainModal from "../components/cockpit/DomainModal";
import useMasterGoogleStatus from "../hooks/useMasterGoogleStatus";

/**
 * Cockpit Site — refonte UX 2026-04-29.
 * Layout 2 colonnes :
 *   - Sidebar gauche sticky (logo + nom + statut + score + liens rapides)
 *   - Colonne principale (Prochaine action + statut Google passif + 10 étapes)
 *
 * Aucune connexion Google n'est demandée au concepteur :
 *   le master OAuth Altiaro couvre GSC / GMC / Ads / GA4.
 */

const STATUS_TONES = {
  active: { label: "Actif", bg: "#E6F4EE", fg: "#0F6E4D" },
  live: { label: "En ligne", bg: "#E0F2FE", fg: "#0369A1" },
  approved: { label: "Approuvé", bg: "#E6F4EE", fg: "#0F6E4D" },
  pending_review: { label: "En revue", bg: "#FBEFD8", fg: "#B8862E" },
  draft: { label: "En cours", bg: "#F0EDE6", fg: "#6B6B6B" },
  default: { label: "En cours", bg: "#F0EDE6", fg: "#6B6B6B" },
};

const STEP_LINK = (siteId) => ({
  pricing: `/sites/${siteId}/pricing`,
  import: `/sites/${siteId}/sourcing`,
  upsells: `/sites/${siteId}/upsells`,
  forecast: `/sites/${siteId}/forecast`,
  branding: `/sites/${siteId}/branding?step=5`,
  domain: `/sites/${siteId}/domains?step=6`,
  translate: `/sites/${siteId}/translate?step=8`,
  pages: `/sites/${siteId}/pages`,
  content: `/sites/${siteId}/blog-posts?step=7`,
  seo: `/sites/${siteId}/seo`,
  qa: `/sites/${siteId}/qa`,
});

export default function SiteDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const master = useMasterGoogleStatus();

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
      const j = journeyRes.data;
      setStatus({
        steps: j.steps,
        completed_count: j.progress?.complete ?? 0,
        total_count: j.progress?.total ?? 10,
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

  useEffect(() => {
    load();
  }, [load]);

  // ----- Dérive prochaine action -----
  const nextStep = useMemo(() => {
    const steps = status?.steps || [];
    if (!steps.length) return null;
    const current = steps.find((s) => s.status === "current");
    if (current) return current;
    const pending = steps.find(
      (s) => !s.completed && !s.blocked_by_previous,
    );
    return pending || null;
  }, [status]);

  // ----- Domain handlers -----
  const refreshDomain = async () => {
    const r = await apiCall(() => api.get(`/sites/${id}/domain`));
    if (r.data) setDomainStatus(r.data);
  };
  const handleSaveDomain = async () => {
    setDomainBusy(true);
    setDomainMsg(null);
    const { data, error } = await apiCall(() =>
      api.post(`/sites/${id}/domain`, { custom_domain: domainInput.trim() }),
    );
    setDomainBusy(false);
    if (error) return setDomainMsg({ kind: "err", text: error });
    setDomainStatus(data);
    setDomainMsg({
      kind: "ok",
      text: "Domaine enregistré. Configurez le CNAME puis cliquez Vérifier.",
    });
  };
  const handleVerifyDomain = async () => {
    setDomainBusy(true);
    setDomainMsg(null);
    const { data, error } = await apiCall(() =>
      api.post(`/sites/${id}/domain/verify`),
    );
    setDomainBusy(false);
    if (error) return setDomainMsg({ kind: "err", text: error });
    setDomainMsg({
      kind: data.verified ? "ok" : "warn",
      text: data.verified ? `✓ Vérifié · ${data.reason}` : data.reason,
    });
    await refreshDomain();
  };
  const handleClearDomain = async () => {
    if (
      !window.confirm(
        "Supprimer le domaine custom et revenir sur l'URL Altiaro ?",
      )
    )
      return;
    await apiCall(() => api.delete(`/sites/${id}/domain`));
    setDomainInput("");
    setDomainMsg(null);
    await refreshDomain();
  };

  if (loading)
    return (
      <Layout>
        <div className="p-8 md:p-12 text-neutral-500">
          Chargement du site…
        </div>
      </Layout>
    );
  if (!site)
    return (
      <Layout>
        <div className="p-8 md:p-12 text-red-500">Site introuvable.</div>
      </Layout>
    );

  const isAdmin = user?.role === "admin";
  const adminEmail = process.env.REACT_APP_ADMIN_EMAIL || "admin@altiaro.com";
  const allCompleted = status?.all_completed === true;

  const tone = STATUS_TONES[site.status] || STATUS_TONES.default;
  const score = Math.round(status?.progress_pct ?? 0);
  const completedCount = status?.completed_count ?? 0;
  const totalCount = status?.total_count ?? 10;

  const links = STEP_LINK(site.id);
  const nextHref = nextStep ? links[nextStep.key] : null;

  return (
    <Layout>
      <div
        className="min-h-full"
        style={{ background: "#F5F2EB" }}
        data-testid="site-detail-page"
      >
        <div className="max-w-[1320px] mx-auto px-5 md:px-10 py-6 md:py-10 w-full">
          {/* Back link */}
          <button
            onClick={() => navigate("/sites")}
            className="flex items-center gap-2 text-[12px] uppercase tracking-[0.2em] text-neutral-500 hover:text-neutral-900 mb-6 transition"
            data-testid="back-to-sites"
          >
            <ArrowLeft size={13} weight="regular" /> Retour aux sites
          </button>

          {allCompleted && (
            <div className="mb-8">
              <PostValidationBanner site={site} adminEmail={adminEmail} />
            </div>
          )}

          <div className="grid grid-cols-1 lg:grid-cols-[280px_1fr] gap-6 lg:gap-10">
            {/* ---------------- SIDEBAR ---------------- */}
            <aside className="lg:sticky lg:top-6 self-start space-y-5">
              <div
                className="bg-white p-6"
                style={{ border: "1px solid #E8E2D5", borderRadius: "4px" }}
              >
                <div className="flex items-center justify-center mb-4">
                  <div
                    className="w-20 h-20 flex items-center justify-center bg-[#FAF7F0]"
                    style={{ border: "1px solid #E8E2D5", borderRadius: "4px" }}
                  >
                    {site.design?.brand?.logo_url ? (
                      <img
                        src={site.design.brand.logo_url}
                        alt={site.name}
                        className="max-w-[64px] max-h-[64px] object-contain"
                      />
                    ) : (
                      <Storefront
                        size={32}
                        weight="duotone"
                        color="#8B6F47"
                      />
                    )}
                  </div>
                </div>
                <h1
                  className="text-[22px] leading-tight text-neutral-900 text-center mb-1"
                  style={{
                    fontFamily:
                      "'Cormorant Garamond', 'Cormorant', Georgia, serif",
                    fontWeight: 500,
                  }}
                  data-testid="site-name"
                >
                  {site.name}
                </h1>
                {site.niche && (
                  <p className="text-[12px] text-neutral-500 text-center mb-3 line-clamp-1">
                    {site.niche}
                  </p>
                )}
                {(site.custom_domain || site.domain) && (
                  <div className="flex items-center justify-center gap-1.5 text-[11.5px] text-neutral-600 mb-3">
                    <Globe size={11} />
                    <span className="truncate">
                      {site.custom_domain || site.domain}
                    </span>
                    {domainStatus?.custom_domain_verified && (
                      <CheckCircle
                        size={11}
                        weight="fill"
                        className="text-emerald-600"
                      />
                    )}
                  </div>
                )}
                <div className="flex justify-center">
                  <span
                    className="inline-flex items-center px-3 py-1 text-[10.5px] uppercase tracking-[0.18em]"
                    style={{
                      background: tone.bg,
                      color: tone.fg,
                      borderRadius: "2px",
                    }}
                    data-testid="site-status-badge"
                  >
                    {tone.label}
                  </span>
                </div>
              </div>

              {/* Score global */}
              <div
                className="bg-white p-6"
                style={{ border: "1px solid #E8E2D5", borderRadius: "4px" }}
                data-testid="site-score-card"
              >
                <div className="text-[10px] uppercase tracking-[0.3em] text-neutral-500 mb-3">
                  Score global
                </div>
                <div className="flex items-baseline gap-1.5 mb-3">
                  <span
                    className="text-[40px] leading-none text-neutral-900"
                    style={{
                      fontFamily:
                        "'Cormorant Garamond', 'Cormorant', Georgia, serif",
                      fontWeight: 500,
                    }}
                  >
                    {score}
                  </span>
                  <span className="text-[14px] text-neutral-500">/ 100</span>
                </div>
                <ScoreDots value={score} />
                <div className="mt-3 text-[11.5px] text-neutral-500">
                  {completedCount} / {totalCount} étapes validées
                </div>
              </div>

              {/* Liens rapides */}
              <div
                className="bg-white p-3"
                style={{ border: "1px solid #E8E2D5", borderRadius: "4px" }}
              >
                <div className="text-[10px] uppercase tracking-[0.3em] text-neutral-500 px-3 py-2">
                  Liens rapides
                </div>
                <SidebarLink
                  href={`/shop/${site.id}`}
                  external
                  Icon={Eye}
                  label="Voir le storefront"
                  testId="sidebar-storefront"
                />
                <SidebarLink
                  to={`/sites/${site.id}/analytics`}
                  Icon={ChartLineUp}
                  label="Analytics"
                  testId="sidebar-analytics"
                />
                <SidebarLink
                  to={`/sites/${site.id}/policy`}
                  Icon={Gear}
                  label="Réglages"
                  testId="sidebar-settings"
                />
                <SidebarButton
                  Icon={Globe}
                  label="Gérer le domaine"
                  onClick={() => setShowDomain(true)}
                  testId="sidebar-domain"
                />
              </div>
            </aside>

            {/* ---------------- MAIN ---------------- */}
            <main className="min-w-0 space-y-6">
              {/* Carte Prochaine action */}
              <NextActionCard
                nextStep={nextStep}
                href={nextHref}
                allCompleted={allCompleted}
                siteId={site.id}
              />

              {/* Statut Google passif (master OAuth) */}
              <MasterGoogleStatusBanner master={master} isAdmin={isAdmin} />

              {/* Les 10 étapes */}
              <CockpitJourney site={site} onRefresh={load} />

              {/* CTA bas de page */}
              <div className="flex flex-wrap gap-3 pt-2">
                <a
                  href={`/shop/${site.id}`}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-2 h-10 px-5 text-[12px] font-semibold text-white bg-neutral-900 hover:bg-black transition"
                  style={{ borderRadius: "2px" }}
                  data-testid="main-view-storefront"
                >
                  <Eye size={14} /> Voir le storefront
                </a>
                <Link
                  to={`/sites/${site.id}/qa`}
                  className="inline-flex items-center gap-2 h-10 px-5 text-[12px] font-semibold text-neutral-900 bg-white border border-neutral-200 hover:border-neutral-900 transition"
                  style={{ borderRadius: "2px" }}
                >
                  <ShieldCheck size={14} weight="regular" /> QA &amp; mise en ligne
                </Link>
              </div>
            </main>
          </div>
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
          onClose={() => {
            setShowDomain(false);
            setDomainMsg(null);
          }}
        />
      )}
    </Layout>
  );
}

/* ---------------- Sub-components ---------------- */

function ScoreDots({ value }) {
  const filled = Math.max(0, Math.min(10, Math.round(value / 10)));
  return (
    <div
      className="flex items-center gap-1.5"
      aria-label={`Score ${value} sur 100`}
    >
      {Array.from({ length: 10 }).map((_, i) => (
        <span
          key={i}
          className="w-2 h-2 rounded-full transition"
          style={{
            background: i < filled ? "#0F6E4D" : "#E8E2D5",
          }}
        />
      ))}
    </div>
  );
}

function SidebarLink({ to, href, external, Icon, label, testId }) {
  const cls =
    "flex items-center gap-3 px-3 py-2.5 text-[13px] text-neutral-700 hover:text-neutral-900 hover:bg-[#FAF7F0] transition rounded-[2px]";
  if (external) {
    return (
      <a
        href={href}
        target="_blank"
        rel="noreferrer"
        className={cls}
        data-testid={testId}
      >
        <Icon size={14} weight="regular" className="text-neutral-500" />
        <span className="flex-1">{label}</span>
        <ArrowRight size={12} className="text-neutral-400" />
      </a>
    );
  }
  return (
    <Link to={to} className={cls} data-testid={testId}>
      <Icon size={14} weight="regular" className="text-neutral-500" />
      <span className="flex-1">{label}</span>
      <ArrowRight size={12} className="text-neutral-400" />
    </Link>
  );
}

function SidebarButton({ Icon, label, onClick, testId }) {
  return (
    <button
      onClick={onClick}
      className="w-full flex items-center gap-3 px-3 py-2.5 text-[13px] text-neutral-700 hover:text-neutral-900 hover:bg-[#FAF7F0] transition rounded-[2px]"
      data-testid={testId}
    >
      <Icon size={14} weight="regular" className="text-neutral-500" />
      <span className="flex-1 text-left">{label}</span>
      <ArrowRight size={12} className="text-neutral-400" />
    </button>
  );
}

function NextActionCard({ nextStep, href, allCompleted, siteId }) {
  if (allCompleted) {
    return (
      <div
        className="bg-white p-6 md:p-8 transition hover:shadow-lg shadow-sm duration-200"
        style={{ border: "1px solid #E8E2D5", borderRadius: "4px" }}
        data-testid="next-action-card"
      >
        <div className="flex items-start gap-3 mb-3">
          <div
            className="w-10 h-10 flex items-center justify-center"
            style={{ background: "#E6F4EE", borderRadius: "4px" }}
          >
            <CheckCircle size={20} weight="fill" color="#0F6E4D" />
          </div>
          <div className="flex-1">
            <div className="text-[10px] uppercase tracking-[0.3em] text-neutral-500 mb-1">
              Prochaine action
            </div>
            <h2
              className="text-[24px] md:text-[26px] leading-tight text-neutral-900"
              style={{
                fontFamily:
                  "'Cormorant Garamond', 'Cormorant', Georgia, serif",
                fontWeight: 500,
              }}
            >
              Prêt à mettre en ligne
            </h2>
          </div>
        </div>
        <p className="text-[14px] text-neutral-600 leading-relaxed mb-5">
          Toutes les étapes sont validées. Lancez la checklist QA finale pour
          publier votre boutique.
        </p>
        <Link
          to={`/sites/${siteId}/qa`}
          className="inline-flex items-center gap-2 h-11 px-5 text-[13px] font-semibold text-white bg-neutral-900 hover:bg-black transition"
          style={{ borderRadius: "2px" }}
        >
          Lancer la checklist QA <ArrowRight size={13} weight="bold" />
        </Link>
      </div>
    );
  }

  if (!nextStep) {
    return (
      <div
        className="bg-white p-6"
        style={{ border: "1px solid #E8E2D5", borderRadius: "4px" }}
      >
        <div className="text-[12px] text-neutral-500">
          Le parcours se met à jour…
        </div>
      </div>
    );
  }

  const order = String(nextStep.order || "").padStart(2, "0");
  return (
    <div
      className="bg-white p-6 md:p-8 transition shadow-sm hover:shadow-lg duration-200"
      style={{ border: "1px solid #E8E2D5", borderRadius: "4px" }}
      data-testid="next-action-card"
    >
      <div className="flex items-start gap-3 mb-3">
        <div
          className="w-10 h-10 flex items-center justify-center"
          style={{ background: "#FBEFD8", borderRadius: "4px" }}
        >
          <Sparkle size={20} weight="duotone" color="#B8862E" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-[10px] uppercase tracking-[0.3em] text-neutral-500 mb-1">
            Prochaine action
          </div>
          <div className="flex flex-wrap items-baseline gap-3">
            <span
              className="text-[12px] uppercase tracking-[0.2em] text-neutral-400"
              style={{
                fontFamily:
                  "'Cormorant Garamond', 'Cormorant', Georgia, serif",
                fontStyle: "italic",
              }}
            >
              Étape {order}
            </span>
            <h2
              className="text-[24px] md:text-[28px] leading-tight text-neutral-900"
              style={{
                fontFamily:
                  "'Cormorant Garamond', 'Cormorant', Georgia, serif",
                fontWeight: 500,
              }}
            >
              {nextStep.label}
            </h2>
          </div>
        </div>
      </div>
      {nextStep.reason && (
        <p className="text-[14px] text-neutral-600 leading-relaxed mb-5 max-w-[640px]">
          {nextStep.reason}
        </p>
      )}
      {href && (
        <Link
          to={href}
          className="inline-flex items-center gap-2 h-11 px-5 text-[13px] font-semibold text-white bg-neutral-900 hover:bg-black transition"
          style={{ borderRadius: "2px" }}
          data-testid="next-action-cta"
        >
          Continuer <ArrowRight size={13} weight="bold" />
        </Link>
      )}
    </div>
  );
}

function MasterGoogleStatusBanner({ master, isAdmin }) {
  if (master.loading) return null;
  if (master.connected) {
    return (
      <div
        className="flex items-start gap-3 p-4"
        style={{
          background: "#FDFCF9",
          border: "1px solid #E8E2D5",
          borderRadius: "4px",
        }}
        data-testid="master-google-status-connected"
      >
        <CheckCircle
          size={18}
          weight="fill"
          color="#0F6E4D"
          className="shrink-0 mt-0.5"
        />
        <div className="text-[13px] text-neutral-700 leading-relaxed">
          Référencement Google géré automatiquement par la plateforme
          {master.googleEmail ? (
            <span className="text-neutral-500"> · {master.googleEmail}</span>
          ) : null}
          .
        </div>
      </div>
    );
  }
  return (
    <div
      className="flex items-start gap-3 p-4"
      style={{
        background: "#FBEFD8",
        border: "1px solid #E8C97A",
        borderRadius: "4px",
      }}
      data-testid="master-google-status-missing"
    >
      <Warning
        size={18}
        weight="regular"
        color="#B8862E"
        className="shrink-0 mt-0.5"
      />
      <div className="flex-1 text-[13px] text-neutral-800 leading-relaxed">
        L'admin doit connecter le compte Google maître Altiaro pour activer
        automatiquement Search Console, Merchant Center, Ads et Analytics sur
        ce site.
        {isAdmin ? (
          <>
            {" "}
            <Link
              to="/admin/google/master-auth"
              className="underline font-medium text-neutral-900"
            >
              Ouvrir l'admin Google Master
            </Link>
            .
          </>
        ) : null}
      </div>
    </div>
  );
}
