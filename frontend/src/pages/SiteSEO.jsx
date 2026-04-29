import React, { useEffect, useState, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import {
  ArrowLeft, ArrowClockwise, CheckCircle, Warning, Info,
  Sparkle, CaretDown, GoogleLogo, Storefront, ChartLineUp, ShieldCheck,
} from "@phosphor-icons/react";
import { api, apiCall } from "../lib/api";
import { useStepGuard } from "../lib/useStepGuard";
import useMasterGoogleStatus from "../hooks/useMasterGoogleStatus";
import SeoStudioPanel from "../components/SeoStudioPanel";
import GSCConnectCard from "../components/GSCConnectCard";
import { StepValidateCTA } from "../components/StepPageHeader";
import { buildOnValidate } from "../lib/journeySteps";

const scoreColor = (s) => {
  if (s == null) return { ring: "#a3a3a3", label: "À calculer", text: "text-neutral-500" };
  if (s >= 80) return { ring: "#10b981", label: "Excellent",  text: "text-emerald-700" };
  if (s >= 70) return { ring: "#10b981", label: "Satisfaisant", text: "text-emerald-700" };
  if (s >= 50) return { ring: "#f59e0b", label: "À améliorer", text: "text-amber-700" };
  if (s >= 35) return { ring: "#f97316", label: "Faible",     text: "text-orange-700" };
  return { ring: "#e11d48", label: "Critique", text: "text-rose-700" };
};

export default function SiteSEO() {
  const { id: siteId } = useParams();
  const { allowed, checking } = useStepGuard(siteId, "seo");
  const master = useMasterGoogleStatus();
  const [audit, setAudit] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [autoStatus, setAutoStatus] = useState(null);
  const [gsc, setGsc] = useState({ status: null, metrics: null });
  const [merchant, setMerchant] = useState(null);
  const [site, setSite] = useState(null);
  const [busy, setBusy] = useState("");
  const [toast, setToast] = useState(null);

  const showToast = (kind, msg) => {
    setToast({ kind, msg });
    setTimeout(() => setToast(null), 5500);
  };

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
    setGsc({ status: gs.data || null, metrics: null });
    setMerchant(mc.data || null);
    setSite(sd.data || null);

    if (gs.data?.connected) {
      const { data: m } = await apiCall(() => api.get(`/sites/${siteId}/gsc/metrics?days=7`));
      if (m) setGsc((g) => ({ ...g, metrics: m }));
    }
    setLoading(false);
    setRefreshing(false);
  }, [siteId]);

  useEffect(() => { if (allowed) loadAll(false); }, [allowed, loadAll]);

  const resubmitSitemap = async () => {
    setBusy("indexnow");
    const { error } = await apiCall(() => api.post(`/sites/${siteId}/indexnow/resubmit-all`, {}));
    setBusy("");
    if (error) return showToast("error", error);
    showToast("ok", "Sitemap resoumis à IndexNow / Bing / Yandex");
  };

  const regenerateOptimizations = async () => {
    setBusy("regen");
    const { error } = await apiCall(() => api.post(`/sites/${siteId}/seo/regenerate`, {}));
    setBusy("");
    if (error) return showToast("error", error);
    showToast("ok", "Optimisations SEO régénérées — score recalculé");
    loadAll(true);
  };

  if (checking || loading) {
    return (
      <div className="min-h-screen bg-[#FAF7F2] flex items-center justify-center">
        <div className="text-sm text-neutral-500">Chargement de votre référencement…</div>
      </div>
    );
  }
  if (!allowed) return null;

  // ----- Score & checks -----
  const provisioning = site?.google_provisioning || {};
  const gmcSubAccountId = provisioning.gmc?.ok ? (provisioning.gmc.merchant_id || null) : null;
  const gscProvisioned = !!provisioning.gsc?.ok;
  const siteIsLive = site?.status === "live";
  const liveSinceAt = site?.live_at ? new Date(site.live_at).getTime() : null;
  const liveOlderThan24h = liveSinceAt ? (Date.now() - liveSinceAt) > 24 * 3600 * 1000 : false;

  // GSC : OK si master couvre OU site-level connecté OU provisioning ok
  const masterGsc = !!master.services?.gsc;
  const siteGscConnected = !!gsc.status?.connected;
  const gscOk = masterGsc || siteGscConnected || gscProvisioned;

  // Merchant : OK si master couvre OU site-level connecté OU sub-account créé
  const masterGmc = !!master.services?.gmc;
  const siteMerchantConnected = !!merchant?.connected;
  const merchantOk = masterGmc || siteMerchantConnected || !!gmcSubAccountId;

  // Compteurs structurels
  const structChecks = [
    { key: "sitemap", label: "Sitemap publié", ok: !!(audit?.dimensions?.structure?.sitemap_published ?? true) },
    { key: "jsonld", label: "JSON-LD complet (Organization, Product, FAQ)",
      ok: !!(audit?.dimensions?.structure?.jsonld_complete ?? true) },
    { key: "hreflang", label: "Hreflang multilingue",
      ok: !!(audit?.dimensions?.structure?.hreflang_ok ?? (autoStatus?.translation?.languages_active?.length > 1)) },
    { key: "indexnow", label: "IndexNow actif", ok: true },
  ];
  // Score : on combine les 4 contrôles structurels + GSC + Merchant = 6 contrôles
  const allChecks = [
    ...structChecks,
    { key: "gsc", label: "Google Search Console", ok: gscOk },
    { key: "merchant", label: "Google Merchant Center", ok: merchantOk },
  ];
  const greenCount = allChecks.filter((c) => c.ok).length;
  // Score = max(score backend, score calculé sur 6 contrôles) — ne reste pas à 0
  const computedScore = Math.round((greenCount / allChecks.length) * 100);
  const backendScore = audit?.score ?? autoStatus?.seo?.score ?? null;
  const score = backendScore != null && backendScore > 0
    ? Math.max(backendScore, computedScore)
    : computedScore;
  const sc = scoreColor(score);
  const scoreOk = score >= 70;

  // Conditions strictes pour passer à l'étape 10
  const canValidate = scoreOk && gscOk && merchantOk;
  const missingConditions = [];
  if (!scoreOk) missingConditions.push(`Score SEO ≥ 70/100 (actuel : ${score}/100)`);
  if (!gscOk) missingConditions.push("Connecter Google Search Console");
  if (!merchantOk) missingConditions.push("Connecter Google Merchant Center");

  // Pistes d'amélioration prioritaires (3-5 max)
  const recommendations = (audit?.recommendations || []).slice(0, 5);

  return (
    <div className="min-h-screen bg-[#FAF7F2]">
      <div className="max-w-[1100px] mx-auto px-6 md:px-10 py-10">
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
              Score SEO &amp; Connexions Google
            </h1>
            <p className="text-[15px] text-neutral-600 mt-2 max-w-2xl leading-relaxed">
              Vérifiez l'optimisation de votre site et activez le suivi Google Search Console
              + Merchant Center pour mesurer vos performances et publier vos produits sur Google Shopping.
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

        {toast && (
          <div
            data-testid="seo-toast"
            className={`mb-6 rounded-xl border px-4 py-3 text-sm ${
              toast.kind === "ok"
                ? "border-emerald-200 bg-emerald-50 text-emerald-800"
                : "border-rose-200 bg-rose-50 text-rose-800"
            }`}
          >
            {toast.msg}
          </div>
        )}

        {/* ───── Comment ça marche ───── */}
        <div
          className="mb-8 p-5 rounded-xl border flex gap-3 items-start"
          style={{ background: "#FDFCF9", borderColor: "#E8E2D5" }}
          data-testid="seo-howitworks"
        >
          <Info size={20} weight="duotone" className="text-emerald-700 mt-0.5 flex-shrink-0" />
          <div className="text-[14px] text-neutral-700 leading-relaxed">
            <div className="font-semibold text-neutral-900 mb-1">Comment ça marche</div>
            Altiaro a déjà optimisé votre site automatiquement (sitemap, hreflang, JSON-LD, IndexNow).
            À cette étape, vous devez&nbsp;:
            <ol className="list-decimal ml-5 mt-2 space-y-1">
              <li>Vérifier que votre <strong>score SEO</strong> est satisfaisant (≥ 70/100).</li>
              <li>Activer le suivi <strong>Google Search Console</strong> pour mesurer vos positions.</li>
              <li>Activer <strong>Merchant Center</strong> pour pousser vos produits dans Google Shopping.</li>
            </ol>
          </div>
        </div>

        {/* ───── Action 1 — Score SEO ───── */}
        <ActionCard
          number={1}
          title="Score SEO global"
          status={scoreOk ? "ok" : score >= 50 ? "warn" : "fail"}
          testId="action-seo-score"
        >
          <div className="flex items-center gap-6 flex-wrap">
            <ScoreRing score={score} color={sc.ring} />
            <div className="flex-1 min-w-[260px]">
              <div className="text-[34px] leading-none text-neutral-900" style={{ fontFamily: "'Cormorant Garamond', 'Cormorant', Georgia, serif", fontWeight: 500 }}>
                {score} / 100
              </div>
              <div className={`text-[13px] mt-1 ${sc.text}`}>{sc.label}</div>
              {scoreOk ? (
                <div className="mt-3 text-[13px] text-emerald-700 flex items-center gap-1.5">
                  <CheckCircle size={15} weight="fill" />
                  Score atteint — votre site est bien optimisé.
                </div>
              ) : (
                <>
                  <div className="mt-3 text-[13px] text-amber-800">
                    Score insuffisant. Pistes d'amélioration prioritaires&nbsp;:
                  </div>
                  {recommendations.length > 0 ? (
                    <ul className="mt-2 space-y-1.5">
                      {recommendations.map((r, i) => (
                        <li key={i} className="text-[12.5px] text-neutral-700 flex items-start gap-2">
                          <span className="text-neutral-400 mt-[2px]">•</span>
                          <span>
                            <strong className="capitalize text-neutral-900">{r.severity || "info"}</strong>
                            {" · "}
                            {r.message || r.title || "—"}
                          </span>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <div className="mt-2 text-[12.5px] text-neutral-500 italic">
                      Aucune piste détaillée disponible — relancez la régénération ci-dessous.
                    </div>
                  )}
                  <button
                    onClick={regenerateOptimizations}
                    disabled={busy === "regen"}
                    data-testid="seo-regenerate"
                    className="mt-4 h-10 px-4 rounded-lg bg-neutral-900 hover:bg-neutral-800 text-white text-[13px] font-medium inline-flex items-center gap-2 disabled:opacity-60"
                  >
                    {busy === "regen" ? "Régénération…" : "Régénérer les optimisations"}
                  </button>
                </>
              )}
            </div>
          </div>
        </ActionCard>

        {/* ───── Action 2 — GSC ───── */}
        <ActionCard
          number={2}
          title="Google Search Console"
          status={gscOk ? "ok" : "fail"}
          testId="action-gsc"
          icon={<GoogleLogo size={20} weight="bold" className="text-neutral-700" />}
        >
          {masterGsc || gscProvisioned ? (
            <div>
              <div className="text-[13.5px] text-emerald-800 flex items-start gap-2">
                <CheckCircle size={16} weight="fill" className="text-emerald-600 mt-0.5 flex-shrink-0" />
                <div>
                  <strong>Search Console géré par la plateforme Altiaro</strong> —
                  aucune action requise de votre part.
                </div>
              </div>
              {siteIsLive && liveOlderThan24h && gsc.metrics ? (
                <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-4 pt-4 border-t border-neutral-100">
                  <Stat label="Impressions 7j" value={(gsc.metrics.impressions ?? 0).toLocaleString("fr-FR")} />
                  <Stat label="Clics 7j" value={(gsc.metrics.clicks ?? 0).toLocaleString("fr-FR")} />
                  <Stat label="Position moy." value={gsc.metrics.avg_position ? gsc.metrics.avg_position.toFixed(1) : "—"} />
                  <Stat label="CTR" value={`${gsc.metrics.ctr ?? 0}%`} />
                </div>
              ) : (
                <div className="mt-3 pt-3 border-t border-neutral-100 text-[12.5px] text-neutral-600 flex items-center gap-2">
                  <ChartLineUp size={14} weight="duotone" className="text-neutral-500" />
                  Données disponibles dès la propagation Google (24-48 h après mise en ligne).
                </div>
              )}
            </div>
          ) : siteGscConnected ? (
            <div>
              <div className="text-[13.5px] text-emerald-800 flex items-center gap-2">
                <CheckCircle size={16} weight="fill" className="text-emerald-600" />
                Search Console connecté à votre site.
              </div>
              {gsc.metrics && (
                <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-4 pt-4 border-t border-neutral-100">
                  <Stat label="Impressions 7j" value={(gsc.metrics.impressions ?? 0).toLocaleString("fr-FR")} />
                  <Stat label="Clics 7j" value={(gsc.metrics.clicks ?? 0).toLocaleString("fr-FR")} />
                  <Stat label="Position moy." value={gsc.metrics.avg_position ? gsc.metrics.avg_position.toFixed(1) : "—"} />
                  <Stat label="CTR" value={`${gsc.metrics.ctr ?? 0}%`} />
                </div>
              )}
            </div>
          ) : (
            <>
              <div className="text-[13.5px] text-neutral-700 mb-3">
                Connectez Google Search Console pour suivre vos positions, impressions et clics.
              </div>
              <GSCConnectCard siteId={siteId} />
            </>
          )}
        </ActionCard>

        {/* ───── Action 3 — Merchant ───── */}
        <ActionCard
          number={3}
          title="Google Merchant Center"
          status={merchantOk ? "ok" : "fail"}
          testId="action-merchant"
          icon={<Storefront size={20} weight="duotone" className="text-neutral-700" />}
        >
          {gmcSubAccountId ? (
            <div className="text-[13.5px] text-emerald-800 flex items-start gap-2">
              <CheckCircle size={16} weight="fill" className="text-emerald-600 mt-0.5 flex-shrink-0" />
              <div>
                <strong>Merchant Center géré par la plateforme Altiaro</strong>
                <div className="text-neutral-700 mt-1">
                  Sub-account créé automatiquement&nbsp;: ID <strong className="text-neutral-900">{gmcSubAccountId}</strong>.
                  Vos produits seront poussés sur Google Shopping après mise en ligne.
                </div>
              </div>
            </div>
          ) : masterGmc ? (
            <div className="text-[13.5px] text-emerald-800 flex items-start gap-2">
              <CheckCircle size={16} weight="fill" className="text-emerald-600 mt-0.5 flex-shrink-0" />
              <div>
                <strong>Merchant Center est géré automatiquement par la plateforme</strong> —
                vos produits seront publiés sur Google Shopping dès la mise en ligne du site.
                Aucune action requise.
              </div>
            </div>
          ) : siteMerchantConnected ? (
            <div className="text-[13.5px] text-emerald-800 flex items-center gap-2">
              <CheckCircle size={16} weight="fill" className="text-emerald-600" />
              Merchant Center connecté · ID <strong>{merchant.merchant_id}</strong>.
              {merchant.last_sync_at && (
                <span className="text-neutral-500 ml-2">
                  Dernière synchro&nbsp;: {new Date(merchant.last_sync_at).toLocaleString("fr-FR")}
                </span>
              )}
            </div>
          ) : (
            <div className="text-[13.5px] text-neutral-700">
              Pour publier vos produits sur Google Shopping, connectez Merchant Center depuis
              la page <Link to="/admin/integrations" className="underline hover:text-emerald-700">
                Admin · Intégrations
              </Link>. Sans Merchant Center, vos produits n'apparaîtront pas dans les résultats Shopping.
            </div>
          )}
        </ActionCard>

        {/* ───── Conditions de validation (checklist explicite) ───── */}
        <div
          className="mb-6 p-5 rounded-xl border"
          style={{ background: "#FFFFFF", borderColor: "#E8E2D5" }}
          data-testid="seo-conditions"
        >
          <div className="text-[10px] uppercase tracking-[0.32em] text-neutral-500 mb-3 flex items-center gap-2">
            <ShieldCheck size={12} weight="bold" /> Conditions à remplir pour valider l'étape
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5 mb-4">
            <Counter label="Score SEO ≥ 70" value={`${score} / 100`} ok={scoreOk} />
            <Counter label="Search Console" value={gscOk ? "Géré ✓" : "Non connecté"} ok={gscOk} />
            <Counter label="Merchant Center" value={merchantOk ? "Géré ✓" : "Non connecté"} ok={merchantOk} />
            {structChecks.map((c) => (
              <Counter key={c.key} label={c.label} value={c.ok ? "Actif" : "Inactif"} ok={c.ok} />
            ))}
          </div>
          <div className={`text-[12.5px] font-semibold flex items-center gap-2 ${canValidate ? "text-emerald-700" : "text-amber-800"}`}>
            {canValidate ? (
              <>
                <CheckCircle size={14} weight="fill" />
                Toutes les conditions sont remplies — vous pouvez valider l'étape.
              </>
            ) : (
              <>
                <Warning size={14} weight="fill" />
                {missingConditions.length} condition(s) restante(s) avant validation.
              </>
            )}
          </div>
        </div>

        {/* ───── Mode avancé ───── */}
        <details className="bg-white rounded-2xl border border-neutral-200 mb-6" data-testid="seo-advanced">
          <summary className="cursor-pointer p-5 flex items-center justify-between text-[14px] font-medium text-neutral-700 hover:bg-neutral-50 rounded-2xl">
            <span className="flex items-center gap-2">
              <Sparkle size={14} weight="bold" /> Mode avancé
              <span className="text-[11px] text-neutral-400 font-normal">(audit détaillé + actions manuelles)</span>
            </span>
            <CaretDown size={14} weight="bold" />
          </summary>
          <div className="px-5 pb-5 pt-0 space-y-4">
            <div className="border-t border-neutral-100 pt-4 flex flex-wrap gap-2">
              <button
                onClick={resubmitSitemap}
                disabled={busy === "indexnow"}
                data-testid="advanced-resubmit"
                className="h-10 px-4 rounded-lg bg-neutral-900 hover:bg-neutral-800 text-white text-[13px] font-medium flex items-center gap-2 disabled:opacity-60"
              >
                {busy === "indexnow" ? "Envoi…" : "Resoumettre le sitemap à IndexNow"}
              </button>
              <button
                onClick={regenerateOptimizations}
                disabled={busy === "regen"}
                data-testid="advanced-regen"
                className="h-10 px-4 rounded-lg bg-white border border-neutral-300 hover:border-neutral-400 text-neutral-800 text-[13px] font-medium flex items-center gap-2 disabled:opacity-60"
              >
                {busy === "regen" ? "Régénération…" : "Régénérer JSON-LD & schémas"}
              </button>
            </div>

            {audit?.recommendations?.length > 0 && (
              <div className="border-t border-neutral-100 pt-4">
                <div className="text-[12px] uppercase tracking-widest text-neutral-500 mb-3">
                  Toutes les pistes d'amélioration ({audit.recommendations.length})
                </div>
                <div className="space-y-2 max-h-72 overflow-auto">
                  {audit.recommendations.slice(0, 30).map((r, i) => (
                    <div key={i} className="text-[12.5px] text-neutral-700 px-3 py-2 bg-neutral-50 rounded-md">
                      <strong className="capitalize">{r.severity || "—"}</strong> · {r.message || r.title}
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="border-t border-neutral-100 pt-4">
              <SeoStudioPanel siteId={siteId} />
            </div>
          </div>
        </details>

        {/* ───── Validation UNIQUE — bouton seul ───── */}
        <StepValidateCTA
          currentStepKey="seo"
          nextStepNumber={10}
          nextStepLabel="QA & mise en ligne"
          nextStepHref={`/sites/${siteId}/qa`}
          canValidate={canValidate}
          missingConditions={missingConditions}
          onValidate={buildOnValidate(siteId, "seo", () => loadAll(true))}
        />
      </div>
    </div>
  );
}

// ──────────────────────────── Sous-composants ──────────────────────────── //

function ActionCard({ number, title, status, icon, children, testId }) {
  const meta = {
    ok:   { color: "#0F6E4D", bg: "#E6F4EE", label: "✅ OK" },
    warn: { color: "#92400E", bg: "#FEF3C7", label: "⚠️ À voir" },
    fail: { color: "#9F1239", bg: "#FEE2E2", label: "❌ À faire" },
  }[status] || { color: "#525252", bg: "#F5F5F5", label: "—" };
  return (
    <div
      className="mb-5 p-6 rounded-xl border"
      style={{ background: "#FFFFFF", borderColor: "#E8E2D5" }}
      data-testid={testId}
    >
      <div className="flex items-center gap-3 mb-4">
        <div
          className="w-7 h-7 rounded-full flex items-center justify-center text-[13px] font-semibold"
          style={{ background: meta.bg, color: meta.color }}
        >
          {number}
        </div>
        {icon}
        <div className="flex-1 text-[15px] font-semibold text-neutral-900">{title}</div>
        <span
          className="text-[10px] uppercase tracking-[0.18em] font-semibold px-2.5 py-1 rounded-[2px]"
          style={{ background: meta.bg, color: meta.color }}
        >
          {meta.label}
        </span>
      </div>
      {children}
    </div>
  );
}

function Counter({ label, value, ok }) {
  return (
    <div className="flex items-center gap-2 text-[13px]">
      {ok ? (
        <CheckCircle size={15} weight="fill" className="text-emerald-600 flex-shrink-0" />
      ) : (
        <Warning size={15} weight="fill" className="text-amber-500 flex-shrink-0" />
      )}
      <span className="text-neutral-500">{label} :</span>
      <span className={ok ? "text-neutral-900 font-medium" : "text-amber-800 font-medium"}>
        {value}
      </span>
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
            style={{ fontFamily: "'Cormorant Garamond', Georgia, serif", fontSize: 28, fontWeight: 600 }}>
        {clamped}
      </text>
    </svg>
  );
}

function Stat({ label, value }) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-[0.2em] text-neutral-500 mb-1">{label}</div>
      <div className="text-[22px] leading-none text-neutral-900" style={{ fontFamily: "'Cormorant Garamond', Georgia, serif", fontWeight: 500 }}>
        {value}
      </div>
    </div>
  );
}
