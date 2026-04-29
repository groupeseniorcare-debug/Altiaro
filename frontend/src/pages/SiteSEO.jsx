import React, { useEffect, useState, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import {
  ArrowLeft, ArrowClockwise, CheckCircle, Warning, XCircle, ChartLineUp,
  Sparkle, CaretDown, GoogleLogo, Storefront,
} from "@phosphor-icons/react";
import { api, apiCall } from "../lib/api";
import { useStepGuard } from "../lib/useStepGuard";
import SeoStudioPanel from "../components/SeoStudioPanel";
import GSCConnectCard from "../components/GSCConnectCard";
import NextStepCTA from "../components/NextStepCTA";

const scoreColor = (s) => {
  if (s == null) return { ring: "#a3a3a3", label: "À calculer", text: "text-neutral-500" };
  if (s >= 80) return { ring: "#10b981", label: "Excellent",  text: "text-emerald-700" };
  if (s >= 60) return { ring: "#f59e0b", label: "À améliorer", text: "text-amber-700" };
  if (s >= 35) return { ring: "#f97316", label: "Faible",     text: "text-orange-700" };
  return { ring: "#e11d48", label: "Critique", text: "text-rose-700" };
};

export default function SiteSEO() {
  const { id: siteId } = useParams();
  const { allowed, checking } = useStepGuard(siteId, "seo");
  const [audit, setAudit] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [autoStatus, setAutoStatus] = useState(null);
  const [gsc, setGsc] = useState({ status: null, metrics: null });
  const [merchant, setMerchant] = useState(null);
  const [busy, setBusy] = useState("");
  const [toast, setToast] = useState(null);

  const showToast = (kind, msg) => {
    setToast({ kind, msg });
    setTimeout(() => setToast(null), 5500);
  };

  const loadAll = useCallback(async (fromRefresh = false) => {
    if (fromRefresh) setRefreshing(true); else setLoading(true);
    const [a, st, gs, mc] = await Promise.all([
      apiCall(() => api.get(`/sites/${siteId}/seo/audit`)),
      apiCall(() => api.get(`/sites/${siteId}/automation/status`)),
      apiCall(() => api.get(`/sites/${siteId}/gsc/status`)),
      apiCall(() => api.get("/merchant/status")),
    ]);
    setAudit(a.data || null);
    setAutoStatus(st.data || null);
    setGsc({ status: gs.data || null, metrics: null });
    setMerchant(mc.data || null);

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

  if (checking || loading) {
    return (
      <div className="min-h-screen bg-[#FAF7F2] flex items-center justify-center">
        <div className="text-sm text-neutral-500">Chargement de votre référencement…</div>
      </div>
    );
  }
  if (!allowed) return null;

  // ----- Score & checks -----
  const score = audit?.score ?? autoStatus?.seo?.score ?? null;
  const sc = scoreColor(score);

  const checks = [
    { label: "Sitemap publié", ok: !!(audit?.dimensions?.structure?.sitemap_published ?? true) },
    { label: "JSON-LD complet (Organization, Product, FAQ)",
      ok: !!(audit?.dimensions?.structure?.jsonld_complete ?? true) },
    { label: "Hreflang multilingue",
      ok: !!(audit?.dimensions?.structure?.hreflang_ok ?? (autoStatus?.translation?.languages_active?.length > 1)) },
    { label: "IndexNow actif", ok: true },
    { label: "Google Search Console connecté", ok: !!gsc.status?.connected },
    { label: "Google Merchant Center connecté", ok: !!merchant?.connected },
  ];
  const greenCount = checks.filter((c) => c.ok).length;

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
            <h1 className="text-3xl md:text-4xl font-semibold text-neutral-900" style={{ fontFamily: "'Fraunces', serif" }}>
              Référencement automatisé
            </h1>
            <p className="text-sm text-neutral-500 mt-2 max-w-2xl">
              Votre site est optimisé pour Google, Bing et les IA (ChatGPT, Perplexity, Gemini)
              en continu. Vous n'avez rien à faire.
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

        {/* Bloc 1 — Score global + checks */}
        <div className="bg-white rounded-2xl border border-neutral-200 p-6 mb-6" data-testid="seo-score-card">
          <div className="flex items-center gap-6 flex-wrap">
            <ScoreRing score={score ?? 0} color={sc.ring} />
            <div className="flex-1 min-w-[260px]">
              <div className="text-[11px] uppercase tracking-[0.2em] text-neutral-500 mb-1">Score SEO global</div>
              <div className="text-[34px] leading-none text-neutral-900" style={{ fontFamily: "'Fraunces', serif" }}>
                {score == null ? "—" : `${score} / 100`}
              </div>
              <div className={`text-[13px] mt-1 ${sc.text}`}>{sc.label}</div>
              <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-2">
                {checks.map((c) => (
                  <div key={c.label} className="flex items-center gap-2 text-[13px] text-neutral-700"
                       data-testid={`seo-check-${c.ok ? "ok" : "ko"}`}>
                    {c.ok
                      ? <CheckCircle size={15} weight="fill" className="text-emerald-600" />
                      : <Warning size={15} weight="fill" className="text-amber-500" />}
                    <span>{c.label}</span>
                  </div>
                ))}
              </div>
              <div className="text-[11px] text-neutral-400 mt-3">
                {greenCount}/{checks.length} contrôles au vert
              </div>
            </div>
          </div>
        </div>

        {/* Bloc 2 — Connexions Google (2 cartes) */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
          {/* GSC */}
          <div className="bg-white rounded-2xl border border-neutral-200 overflow-hidden" data-testid="gsc-card">
            <div className="p-5">
              <div className="flex items-start gap-3">
                <GoogleLogo size={22} weight="bold" className="text-neutral-900 mt-0.5" />
                <div className="flex-1">
                  <div className="text-[15px] font-semibold text-neutral-900">Google Search Console</div>
                  <div className="text-[12px] text-neutral-500 mt-0.5">Position, clics, impressions Google</div>
                </div>
                {gsc.status?.connected && (
                  <span className="text-[10px] uppercase tracking-widest font-bold text-emerald-700 bg-emerald-50 border border-emerald-200 rounded-full px-2 py-0.5">
                    Connecté
                  </span>
                )}
              </div>
            </div>
            <GSCConnectCard siteId={siteId} />
          </div>

          {/* Merchant */}
          <div className="bg-white rounded-2xl border border-neutral-200 p-5" data-testid="merchant-card">
            <div className="flex items-start gap-3">
              <Storefront size={22} weight="duotone" className="text-neutral-900 mt-0.5" />
              <div className="flex-1">
                <div className="text-[15px] font-semibold text-neutral-900">Google Merchant Center</div>
                <div className="text-[12px] text-neutral-500 mt-0.5">Catalogue produits sur Google Shopping</div>
              </div>
              {merchant?.connected && (
                <span className="text-[10px] uppercase tracking-widest font-bold text-emerald-700 bg-emerald-50 border border-emerald-200 rounded-full px-2 py-0.5">
                  Connecté
                </span>
              )}
            </div>
            <div className="text-[12px] text-neutral-600 mt-4 leading-[1.55]">
              {merchant?.connected ? (
                <>
                  Compte marchand <strong>{merchant.merchant_id}</strong> connecté.
                  {merchant.last_sync_at && (
                    <span className="block text-neutral-400 mt-1">
                      Dernière synchro : {new Date(merchant.last_sync_at).toLocaleString("fr-FR")}
                    </span>
                  )}
                </>
              ) : (
                "Connectez Merchant Center depuis la page Admin · Intégrations pour publier vos produits sur Google Shopping."
              )}
            </div>
          </div>
        </div>

        {/* Bloc 3 — Performances 7j (depuis GSC) */}
        <div className="bg-white rounded-2xl border border-neutral-200 p-6 mb-6" data-testid="seo-perf">
          <div className="flex items-center gap-2 mb-4">
            <ChartLineUp size={18} weight="duotone" className="text-neutral-700" />
            <div className="text-[16px] font-semibold text-neutral-900">Vos performances (7 derniers jours)</div>
          </div>
          {gsc.metrics ? (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <Stat label="Impressions Google" value={(gsc.metrics.impressions ?? 0).toLocaleString("fr-FR")} />
              <Stat label="Clics" value={(gsc.metrics.clicks ?? 0).toLocaleString("fr-FR")} />
              <Stat label="Position moyenne" value={gsc.metrics.avg_position ? gsc.metrics.avg_position.toFixed(1) : "—"} />
              <Stat label="CTR" value={`${gsc.metrics.ctr ?? 0}%`} />
            </div>
          ) : gsc.status?.connected ? (
            <div className="text-[13px] text-neutral-500 italic">
              Métriques en cours de chargement…
            </div>
          ) : (
            <div className="text-[13px] text-neutral-600 leading-[1.6]">
              <strong>Connectez Google Search Console</strong> ci-dessus pour voir vos
              impressions, clics et position moyenne directement ici. Les données sont mises
              à jour toutes les 24 heures.
            </div>
          )}
        </div>

        {/* Mode avancé */}
        <details className="bg-white rounded-2xl border border-neutral-200 mb-6" data-testid="seo-advanced">
          <summary className="cursor-pointer p-5 flex items-center justify-between text-[14px] font-medium text-neutral-700 hover:bg-neutral-50 rounded-2xl">
            <span className="flex items-center gap-2">
              <Sparkle size={14} weight="bold" /> Mode avancé
              <span className="text-[11px] text-neutral-400 font-normal">(audit détaillé + actions manuelles)</span>
            </span>
            <CaretDown size={14} weight="bold" />
          </summary>
          <div className="px-5 pb-5 pt-0 space-y-4">
            <div className="border-t border-neutral-100 pt-4">
              <div className="flex flex-wrap gap-2 mb-4">
                <button
                  onClick={resubmitSitemap}
                  disabled={busy === "indexnow"}
                  data-testid="advanced-resubmit"
                  className="h-10 px-4 rounded-lg bg-neutral-900 hover:bg-neutral-800 text-white text-[13px] font-medium flex items-center gap-2 disabled:opacity-60"
                >
                  {busy === "indexnow" ? "Envoi…" : "Resoumettre le sitemap à IndexNow"}
                </button>
              </div>
            </div>

            {/* Recommandations issues de l'audit */}
            {audit?.recommendations?.length > 0 && (
              <div className="border-t border-neutral-100 pt-4">
                <div className="text-[12px] uppercase tracking-widest text-neutral-500 mb-3">
                  Pistes d'amélioration ({audit.recommendations.length})
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

            {/* SeoStudio (AEO / citations) */}
            <div className="border-t border-neutral-100 pt-4">
              <SeoStudioPanel siteId={siteId} />
            </div>
          </div>
        </details>

        <NextStepCTA siteId={siteId} currentKey="seo" />
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
            style={{ fontFamily: "'Fraunces', serif", fontSize: 28, fontWeight: 600 }}>
        {clamped}
      </text>
    </svg>
  );
}

function Stat({ label, value }) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-[0.2em] text-neutral-500 mb-1">{label}</div>
      <div className="text-[24px] leading-none text-neutral-900" style={{ fontFamily: "'Fraunces', Georgia, serif" }}>
        {value}
      </div>
    </div>
  );
}
