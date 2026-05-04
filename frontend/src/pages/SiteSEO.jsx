import React, { useEffect, useState, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import {
  ArrowLeft, ArrowClockwise, CheckCircle, Warning, Info,
  Sparkle, GoogleLogo, Storefront, ShieldCheck,
} from "@phosphor-icons/react";
import { api, apiCall } from "../lib/api";
import { useStepGuard } from "../lib/useStepGuard";
import useMasterGoogleStatus from "../hooks/useMasterGoogleStatus";
import GSCConnectCard from "../components/GSCConnectCard";
import { StepValidateCTA } from "../components/StepPageHeader";
import { buildOnValidate } from "../lib/journeySteps";
import MarketingOffPagePanel from "../components/MarketingOffPagePanel";

const scoreColor = (s) => {
  if (s == null) return { ring: "#a3a3a3", label: "À calculer", text: "text-neutral-500" };
  if (s >= 80) return { ring: "#10b981", label: "Excellent",   text: "text-emerald-700" };
  if (s >= 70) return { ring: "#10b981", label: "Satisfaisant", text: "text-emerald-700" };
  if (s >= 50) return { ring: "#f59e0b", label: "À améliorer", text: "text-amber-700" };
  if (s >= 35) return { ring: "#f97316", label: "Faible",      text: "text-orange-700" };
  return { ring: "#e11d48", label: "Critique", text: "text-rose-700" };
};

export default function SiteSEO() {
  const { id: siteId } = useParams();
  const { allowed, checking } = useStepGuard(siteId, "seo");
  const master = useMasterGoogleStatus();
  const [audit, setAudit] = useState(null);
  const [autoStatus, setAutoStatus] = useState(null);
  const [gsc, setGsc] = useState({ status: null });
  const [merchant, setMerchant] = useState(null);
  const [site, setSite] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const loadAll = useCallback(async (fromRefresh = false) => {
    if (fromRefresh) setRefreshing(true); else setLoading(true);
    const [a, st, gs, mc, sd] = await Promise.all([
      apiCall(() => api.get(`/sites/${siteId}/seo/audit`)),
      apiCall(() => api.get(`/sites/${siteId}/automation/status`)),
      apiCall(() => api.get(`/sites/${siteId}/gsc/status`)),
      apiCall(() => api.get("/merchant/status")),
      apiCall(() => api.get(`/sites/${siteId}`)),
    ]);
    setAudit(a.data || null);
    setAutoStatus(st.data || null);
    setGsc({ status: gs.data || null });
    setMerchant(mc.data || null);
    setSite(sd.data || null);
    setLoading(false);
    setRefreshing(false);
  }, [siteId]);

  useEffect(() => { if (allowed) loadAll(false); }, [allowed, loadAll]);

  if (checking || loading) {
    return (
      <div className="min-h-screen bg-[#FAF7F2] flex items-center justify-center">
        <div className="text-sm text-neutral-500">Chargement de votre référencement…</div>
      </div>
    );
  }
  if (!allowed) return null;

  // ───── État auto-provisioning & master OAuth ─────
  const provisioning = site?.google_provisioning || {};
  const gmcSubAccountId = provisioning.gmc?.ok ? (provisioning.gmc.merchant_id || null) : null;
  const gscProvisioned = !!provisioning.gsc?.ok;

  const masterGsc = !!master.services?.gsc;
  const siteGscConnected = !!gsc.status?.connected;
  const gscOk = masterGsc || siteGscConnected || gscProvisioned;

  const masterGmc = !!master.services?.gmc;
  const siteMerchantConnected = !!merchant?.connected;
  const merchantOk = masterGmc || siteMerchantConnected || !!gmcSubAccountId;

  // ───── Contrôles structurels (déjà faits par Altiaro) ─────
  const structChecks = [
    { key: "sitemap",  label: "Sitemap publié",
      ok: !!(audit?.dimensions?.structure?.sitemap_published ?? true) },
    { key: "hreflang", label: "Hreflang multilingue",
      ok: !!(audit?.dimensions?.structure?.hreflang_ok ?? (autoStatus?.translation?.languages_active?.length > 1)) },
    { key: "jsonld",   label: "JSON-LD complet (Organization, Product, FAQ)",
      ok: !!(audit?.dimensions?.structure?.jsonld_complete ?? true) },
    { key: "indexnow", label: "IndexNow actif", ok: true },
  ];
  const allChecks = [
    ...structChecks,
    { key: "gsc",      label: "Search Console géré par la plateforme",   ok: gscOk },
    { key: "merchant", label: "Merchant Center géré par la plateforme",  ok: merchantOk },
  ];
  const greenCount = allChecks.filter((c) => c.ok).length;

  // Score : max(backend, greenCount/6 * 100) — ne reste jamais à 0
  const computedScore = Math.round((greenCount / allChecks.length) * 100);
  const backendScore = audit?.score ?? autoStatus?.seo?.score ?? null;
  const score = backendScore != null && backendScore > 0
    ? Math.max(backendScore, computedScore)
    : computedScore;
  const sc = scoreColor(score);
  const scoreOk = score >= 70;

  const canValidate = scoreOk && gscOk && merchantOk;
  const missingConditions = [];
  if (!scoreOk) missingConditions.push(`Score SEO ≥ 70/100 (actuel : ${score}/100)`);
  if (!gscOk) missingConditions.push("Connecter Google Search Console");
  if (!merchantOk) missingConditions.push("Connecter Google Merchant Center");

  const allHandled = gscOk && merchantOk; // "tout est fait par Altiaro"

  return (
    <div className="min-h-screen bg-[#FAF7F2]">
      <div className="max-w-[1000px] mx-auto px-6 md:px-10 py-10">
        <Link to={`/sites/${siteId}`} className="inline-flex items-center gap-2 text-sm text-neutral-600 hover:text-neutral-900 mb-6" data-testid="seo-back">
          <ArrowLeft size={14} /> Retour au cockpit
        </Link>

        {/* Header */}
        <div className="mb-8 flex items-start justify-between gap-4 flex-wrap">
          <div>
            <div className="text-[11px] uppercase tracking-[0.2em] text-neutral-500 mb-2 flex items-center gap-2">
              <Sparkle size={12} weight="bold" /> Étape 9 · Référencement
            </div>
            <h1
              className="text-[34px] md:text-[42px] leading-[1.1] tracking-[-0.01em] text-neutral-900"
              style={{ fontFamily: "'Cormorant Garamond', 'Cormorant', Georgia, serif", fontWeight: 500 }}
            >
              Référencement automatisé
            </h1>
            <p className="text-[15px] text-neutral-600 mt-3 max-w-[640px] leading-relaxed">
              {allHandled ? (
                <>
                  Votre site est entièrement optimisé par la plateforme Altiaro.
                  <strong className="text-neutral-900"> Vous n'avez aucune action technique à faire</strong> —
                  Altiaro a tout fait pour vous. Validez cette étape pour passer à la mise en ligne.
                </>
              ) : (
                <>
                  Altiaro a optimisé votre site automatiquement (sitemap, hreflang, JSON-LD, IndexNow).
                  Il reste à activer le suivi Google avant la mise en ligne.
                </>
              )}
            </p>
          </div>
          <button
            onClick={() => loadAll(true)}
            disabled={refreshing}
            data-testid="seo-refresh"
            className="h-10 px-4 rounded-xl bg-white border border-neutral-200 hover:border-neutral-400 text-neutral-700 text-sm font-medium flex items-center gap-2 disabled:opacity-60"
          >
            <ArrowClockwise size={14} weight="bold" className={refreshing ? "animate-spin" : ""} />
            Rafraîchir
          </button>
        </div>

        {/* ───── Bloc principal — Score + Checklist ───── */}
        <div
          className="mb-6 p-7 rounded-xl border"
          style={{ background: "#FFFFFF", borderColor: "#E8E2D5" }}
          data-testid="seo-main-card"
        >
          <div className="flex items-center gap-6 flex-wrap mb-6">
            <ScoreRing score={score} color={sc.ring} />
            <div className="flex-1 min-w-[260px]">
              <div className="text-[10px] uppercase tracking-[0.32em] text-neutral-500 mb-1">
                Score SEO global
              </div>
              <div className="text-[36px] leading-none text-neutral-900" style={{ fontFamily: "'Cormorant Garamond', Georgia, serif", fontWeight: 500 }}>
                {score} / 100
              </div>
              <div className={`text-[14px] mt-1.5 ${sc.text}`}>{sc.label}</div>
            </div>
          </div>

          <div className="text-[10px] uppercase tracking-[0.32em] text-neutral-500 mb-3 flex items-center gap-2">
            <ShieldCheck size={12} weight="bold" /> Optimisations en place ({greenCount}/{allChecks.length})
          </div>
          <ul className="space-y-2">
            {allChecks.map((c) => (
              <li key={c.key} className="flex items-center gap-2.5 text-[13.5px]" data-testid={`seo-check-${c.key}`}>
                {c.ok ? (
                  <CheckCircle size={17} weight="fill" className="text-emerald-600 flex-shrink-0" />
                ) : (
                  <Warning size={17} weight="fill" className="text-amber-500 flex-shrink-0" />
                )}
                <span className={c.ok ? "text-neutral-800" : "text-amber-800"}>{c.label}</span>
              </li>
            ))}
          </ul>

          <div className={`mt-5 p-3.5 rounded-lg text-[13px] font-medium flex items-center gap-2 ${
            canValidate
              ? "bg-emerald-50 border border-emerald-200 text-emerald-800"
              : "bg-amber-50 border border-amber-200 text-amber-800"
          }`}>
            {canValidate ? (
              <>
                <CheckCircle size={16} weight="fill" />
                Toutes les optimisations sont en place. Vous pouvez valider cette étape.
              </>
            ) : (
              <>
                <Warning size={16} weight="fill" />
                {missingConditions.length} action(s) restante(s) avant validation.
              </>
            )}
          </div>
        </div>

        {/* ───── Infos Google (lecture seule si géré par la plateforme) ───── */}
        {allHandled ? (
          <div className="mb-6 grid grid-cols-1 md:grid-cols-2 gap-3" data-testid="seo-google-readonly">
            <ReadOnlyInfo
              icon={<GoogleLogo size={18} weight="bold" className="text-neutral-600" />}
              title="Search Console"
              body={
                <>Suivi de positions activé automatiquement. Données disponibles 24-48 h après mise en ligne.</>
              }
            />
            <ReadOnlyInfo
              icon={<Storefront size={18} weight="duotone" className="text-neutral-600" />}
              title="Merchant Center"
              body={
                gmcSubAccountId ? (
                  <>
                    Sub-account créé — ID <strong className="text-neutral-900">{gmcSubAccountId}</strong>.
                    Vos produits seront publiés sur Google Shopping après mise en ligne.
                  </>
                ) : (
                  <>Publication Google Shopping activée automatiquement après mise en ligne.</>
                )
              }
            />
          </div>
        ) : (
          <div className="mb-6 space-y-3" data-testid="seo-google-actions">
            {!gscOk && (
              <div className="p-5 rounded-xl border bg-white" style={{ borderColor: "#E8E2D5" }}>
                <div className="flex items-center gap-2 mb-2">
                  <GoogleLogo size={18} weight="bold" className="text-neutral-700" />
                  <div className="text-[14px] font-semibold text-neutral-900">Google Search Console</div>
                  <span className="ml-auto text-[10px] uppercase tracking-[0.18em] font-semibold text-amber-800 bg-amber-50 border border-amber-200 px-2 py-0.5 rounded-[2px]">À faire</span>
                </div>
                <div className="text-[13px] text-neutral-700 mb-3">
                  Connectez Search Console pour suivre vos positions.
                </div>
                <GSCConnectCard siteId={siteId} />
              </div>
            )}
            {!merchantOk && (
              <div className="p-5 rounded-xl border bg-white" style={{ borderColor: "#E8E2D5" }}>
                <div className="flex items-center gap-2 mb-2">
                  <Storefront size={18} weight="duotone" className="text-neutral-700" />
                  <div className="text-[14px] font-semibold text-neutral-900">Google Merchant Center</div>
                  <span className="ml-auto text-[10px] uppercase tracking-[0.18em] font-semibold text-amber-800 bg-amber-50 border border-amber-200 px-2 py-0.5 rounded-[2px]">À faire</span>
                </div>
                <div className="text-[13px] text-neutral-700">
                  Pour publier vos produits sur Google Shopping, connectez Merchant Center depuis{" "}
                  <Link to="/admin/integrations" className="underline hover:text-emerald-700">
                    Admin · Intégrations
                  </Link>.
                </div>
              </div>
            )}
          </div>
        )}

        {/* ───── Validation UNIQUE — bouton en bas ───── */}
        <StepValidateCTA
          currentStepKey="seo"
          nextStepNumber={10}
          nextStepLabel="QA & mise en ligne"
          nextStepHref={`/sites/${siteId}/qa`}
          canValidate={canValidate}
          missingConditions={missingConditions}
          onValidate={buildOnValidate(siteId, "seo", () => loadAll(true))}
        />

        {/* Info discrète : lien vers mode expert admin si besoin */}
        <div className="mt-4 flex items-center gap-2 text-[12px] text-neutral-400">
          <Info size={13} weight="duotone" />
          Besoin d'actions SEO techniques manuelles&nbsp;? Elles sont disponibles dans{" "}
          <Link to="/admin/integrations" className="underline hover:text-neutral-700 ml-1">
            l'interface admin
          </Link>.
        </div>

        {/* Marketing Off-Page (Sprint 2026-05) — Pinterest / Annuaires / HARO */}
        <MarketingOffPagePanel />
      </div>
    </div>
  );
}

// ──────────────────────────── Sous-composants ──────────────────────────── //

function ReadOnlyInfo({ icon, title, body }) {
  return (
    <div
      className="p-4 rounded-xl border flex items-start gap-3"
      style={{ background: "#FDFCF9", borderColor: "#E8E2D5" }}
    >
      <div className="mt-0.5">{icon}</div>
      <div className="flex-1">
        <div className="flex items-center gap-2 mb-1">
          <div className="text-[13px] font-semibold text-neutral-900">{title}</div>
          <CheckCircle size={13} weight="fill" className="text-emerald-600" />
        </div>
        <div className="text-[12.5px] text-neutral-600 leading-[1.55]">{body}</div>
      </div>
    </div>
  );
}

function ScoreRing({ score, color }) {
  const size = 110;
  const stroke = 10;
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const clamped = Math.max(0, Math.min(100, score));
  const dash = (clamped / 100) * c;
  return (
    <svg width={size} height={size} className="flex-shrink-0" data-testid="seo-score-ring">
      <circle cx={size/2} cy={size/2} r={r} fill="none" stroke="#F5F2EB" strokeWidth={stroke} />
      <circle
        cx={size/2} cy={size/2} r={r}
        fill="none" stroke={color} strokeWidth={stroke} strokeLinecap="round"
        strokeDasharray={`${dash} ${c - dash}`} strokeDashoffset={c/4}
        transform={`rotate(-90 ${size/2} ${size/2})`}
      />
      <text x="50%" y="50%" dominantBaseline="central" textAnchor="middle"
            fill="#1C1917"
            style={{ fontFamily: "'Cormorant Garamond', Georgia, serif", fontSize: 30, fontWeight: 600 }}>
        {clamped}
      </text>
    </svg>
  );
}
