import React, { useEffect, useState, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import {
  ArrowLeft, CheckCircle, Warning, XCircle, Sparkle, Rocket, ShieldCheck,
} from "@phosphor-icons/react";
import { api, apiCall } from "../lib/api";
import { useStepGuard } from "../lib/useStepGuard";

const STATUS_META = {
  ok:   { label: "OK",      color: "text-emerald-700", bg: "bg-emerald-50",  border: "border-emerald-200", icon: CheckCircle },
  warn: { label: "À voir",  color: "text-amber-800",   bg: "bg-amber-50",    border: "border-amber-200",   icon: Warning },
  fail: { label: "Bloquant", color: "text-rose-800",   bg: "bg-rose-50",     border: "border-rose-200",    icon: XCircle },
};

const CHECK_LABELS = {
  branding_complete:        "Identité de marque complète (logo, nom, couleur)",
  products_min:             "Catalogue produits suffisant (≥ 5)",
  all_products_have_images: "Visuels IA générés pour chaque produit",
  translations_min:         "Au moins 2 langues actives",
  json_ld_valid:            "Données structurées JSON-LD",
  sitemap_published:        "Sitemap XML accessible",
  domain_dns_ok:            "Domaine custom configuré",
  ssl_ok:                   "HTTPS / SSL actif",
  mollie_active:            "Paiement Mollie connecté",
  legal_pages:              "Pages légales (CGV, mentions, …)",
  blog_min_3:               "Au moins 3 articles publiés",
  landing_pages_min:        "Au moins 5 landing pages SEO",
  gsc_connected:            "Google Search Console connecté",
  merchant_connected:       "Google Merchant Center connecté",
  indexnow_recent:          "IndexNow notifié récemment",
  perf_ok:                  "Performances Lighthouse correctes",
};

export default function SiteQA() {
  const { id: siteId } = useParams();
  const { allowed, checking } = useStepGuard(siteId, "qa");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState(null);

  const showToast = (kind, msg) => {
    setToast({ kind, msg });
    setTimeout(() => setToast(null), 6000);
  };

  const load = useCallback(async () => {
    setLoading(true);
    const { data: d } = await apiCall(() => api.get(`/sites/${siteId}/qa/checklist`));
    if (d) setData(d);
    setLoading(false);
  }, [siteId]);

  useEffect(() => { if (siteId && allowed) load(); }, [siteId, allowed, load]);

  const goLive = async (force = false) => {
    if (!window.confirm(force ? "Confirmer la mise en ligne FORCÉE (admin) ?" : "Mettre votre boutique en ligne maintenant ?")) return;
    setBusy(true);
    const { data: d, error, rawDetail } = await apiCall(() =>
      api.post(`/sites/${siteId}/go-live${force ? "?force=true" : ""}`),
    );
    setBusy(false);
    if (error) {
      showToast("error", rawDetail?.detail || error);
      return;
    }
    showToast("ok", `Site mis en ligne ! Statut : ${d?.status}`);
    load();
  };

  if (checking || loading) {
    return (
      <div className="min-h-screen bg-[#FAF7F2] flex items-center justify-center" data-testid="site-qa-loading">
        <div className="text-sm text-neutral-500">Chargement de la checklist…</div>
      </div>
    );
  }
  if (!allowed) return null;

  const checks = data?.checks || [];
  const score = data?.score || 0;
  const ready = !!data?.ready;
  const ringColor = score >= 85 ? "#10b981" : score >= 70 ? "#f59e0b" : "#f43f5e";

  return (
    <div className="min-h-screen bg-[#FAF7F2]">
      <div className="max-w-[1200px] mx-auto px-6 md:px-10 py-10">
        <Link to={`/sites/${siteId}`} className="inline-flex items-center gap-2 text-sm text-neutral-600 hover:text-neutral-900 mb-6" data-testid="qa-back">
          <ArrowLeft size={14} /> Retour au cockpit
        </Link>

        <div className="mb-8 flex items-center justify-between gap-4 flex-wrap">
          <div>
            <div className="text-[11px] uppercase tracking-[0.2em] text-neutral-500 mb-2 flex items-center gap-2">
              <ShieldCheck size={12} weight="bold" /> Étape 10 · Validation finale
            </div>
            <h1 className="text-3xl md:text-4xl font-semibold text-neutral-900" style={{ fontFamily: "'Fraunces', serif" }}>
              Contrôle qualité & mise en ligne
            </h1>
            <p className="text-sm text-neutral-500 mt-2 max-w-2xl">
              16 vérifications automatiques garantissent que votre boutique est prête à recevoir
              ses premiers visiteurs. Tout doit être au vert (score ≥ 70) pour passer en production.
            </p>
          </div>

          <div className="flex items-center gap-4" data-testid="qa-score-box">
            <ScoreRing score={score} color={ringColor} />
            <button
              onClick={() => goLive(false)}
              disabled={!ready || busy}
              data-testid="qa-go-live"
              className="h-12 px-6 rounded-xl bg-gradient-to-br from-[#1C1917] to-[#44403C] hover:from-[#0A0A0A] text-white text-sm font-medium flex items-center gap-2 transition disabled:opacity-50"
            >
              <Rocket size={16} weight="fill" />
              {busy ? "Publication…" : "Mettre en ligne"}
            </button>
          </div>
        </div>

        {toast && (
          <div
            data-testid="qa-toast"
            className={`mb-6 rounded-xl border px-4 py-3 text-sm ${
              toast.kind === "ok"
                ? "border-emerald-200 bg-emerald-50 text-emerald-800"
                : "border-rose-200 bg-rose-50 text-rose-800"
            }`}
          >
            {toast.msg}
          </div>
        )}

        <div className="bg-white rounded-2xl border border-neutral-200 p-6" data-testid="qa-checklist">
          <div className="text-[11px] uppercase tracking-[0.2em] text-neutral-500 mb-5 flex items-center gap-2">
            <Sparkle size={12} weight="bold" /> Checklist ({checks.length} contrôles)
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {checks.map((c) => {
              const meta = STATUS_META[c.status] || STATUS_META.warn;
              const Icon = meta.icon;
              const fix = FIX_LINKS(siteId)[c.id];
              const showFix = c.status !== "ok" && fix;
              return (
                <div
                  key={c.id}
                  data-testid={`qa-check-${c.id}`}
                  className={`rounded-xl border ${meta.border} ${meta.bg} p-3 flex items-start gap-3`}
                >
                  <Icon size={18} weight="fill" className={`${meta.color} flex-shrink-0 mt-0.5`} />
                  <div className="min-w-0 flex-1">
                    <div className={`text-[13px] font-medium ${meta.color}`}>
                      {CHECK_LABELS[c.id] || c.label}
                    </div>
                    <div className="text-[11px] text-neutral-600 mt-0.5 truncate">
                      {c.detail}
                    </div>
                    {showFix && (
                      <Link
                        to={fix.to}
                        data-testid={`qa-fix-${c.id}`}
                        className={`inline-flex items-center gap-1 mt-2 text-[11.5px] font-semibold underline ${meta.color}`}
                      >
                        Corriger en 1 clic →
                      </Link>
                    )}
                  </div>
                  <span className={`text-[10px] uppercase tracking-widest font-bold ${meta.color}`}>
                    {meta.label}
                  </span>
                </div>
              );
            })}
          </div>

          {!ready && (
            <div className="mt-5 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-[13px] text-amber-800">
              Certains contrôles ne sont pas au vert. Corrigez-les avant la mise en ligne, ou
              demandez à un admin Altiaro un passage forcé.
            </div>
          )}
        </div>

        {/* Statut Google + bouton provisioning */}
        <GoogleProvisioningPanel siteId={siteId} ready={ready} />
      </div>
    </div>
  );
}

function GoogleProvisioningPanel({ siteId, ready }) {
  const [data, setData] = useState(null);
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState(null);
  const showToast = (kind, msg) => { setToast({ kind, msg }); setTimeout(() => setToast(null), 6500); };

  const load = async () => {
    const { data: d } = await apiCall(() => api.get(`/sites/${siteId}/automation/status`));
    // /automation/status doesn't include google_provisioning, fallback : query the site
    const { data: s } = await apiCall(() => api.get(`/sites/${siteId}`));
    setData(s?.google_provisioning || null);
  };
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [siteId]);

  const run = async (force = false) => {
    setBusy(true);
    const { data: d, error } = await apiCall(() =>
      api.post(`/sites/${siteId}/google-provisioning/run`, { force }),
    );
    setBusy(false);
    if (error) return showToast("error", error);
    setData(d || null);
    if (d?.reason === "master_oauth_not_done") {
      showToast("error", "Le compte maître Altiaro n'est pas connecté — va sur /admin/google/master-auth");
      return;
    }
    showToast("ok", `Provisioning ${d?.status || "lancé"} : ${(d?.services_ok || []).length}/4 services OK`);
  };

  const retry = async (service) => {
    setBusy(true);
    await apiCall(() =>
      api.post(`/sites/${siteId}/google-provisioning/retry`, { services: [service] }),
    );
    setBusy(false);
    load();
  };

  const services = [
    { key: "gsc",  label: "Search Console" },
    { key: "gmc",  label: "Merchant Center" },
    { key: "ads",  label: "Google Ads" },
    { key: "ga4",  label: "Analytics 4" },
  ];

  return (
    <div className="bg-white rounded-2xl border border-neutral-200 p-6 mt-6" data-testid="google-prov-panel">
      <div className="flex items-start justify-between gap-4 flex-wrap mb-4">
        <div>
          <div className="text-[11px] uppercase tracking-[0.2em] text-neutral-500 mb-1.5 flex items-center gap-2">
            <Sparkle size={12} weight="bold" /> Statut Google
          </div>
          <div className="text-[18px] font-semibold text-neutral-900">
            Provisioning automatique Google
          </div>
          <p className="text-[13px] text-neutral-600 mt-1.5 max-w-2xl leading-[1.55]">
            Altiaro provisionne Search Console, Merchant Center, Ads et GA4 en arrière-plan.
            Lancez manuellement le provisioning pour ce site (utile en démo / debug).
          </p>
        </div>
        <button
          onClick={() => run(true)}
          disabled={busy}
          data-testid="run-google-provisioning"
          className="h-11 px-5 rounded-xl bg-[#1C1917] hover:bg-[#0A0A0A] text-white text-sm font-semibold flex items-center gap-2 disabled:opacity-60"
        >
          <Sparkle size={14} weight="fill" />
          {busy ? "En cours…" : "Provisionner Google maintenant"}
        </button>
      </div>

      {toast && (
        <div className={`mb-4 rounded-xl border px-4 py-2.5 text-[12.5px] ${
          toast.kind === "ok" ? "border-emerald-200 bg-emerald-50 text-emerald-800"
                              : "border-rose-200 bg-rose-50 text-rose-800"
        }`}>{toast.msg}</div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {services.map((s) => {
          const r = (data || {})[s.key] || null;
          const ok = !!(r && r.ok);
          return (
            <div key={s.key} data-testid={`google-prov-${s.key}`}
                 className={`rounded-xl border ${ok ? "border-emerald-200 bg-emerald-50" : "border-neutral-200 bg-white"} p-3 flex items-start gap-3`}>
              {ok ? <CheckCircle size={18} weight="fill" className="text-emerald-600 mt-0.5" />
                  : <XCircle size={18} weight="fill" className="text-neutral-300 mt-0.5" />}
              <div className="flex-1 min-w-0">
                <div className={`text-[13px] font-medium ${ok ? "text-emerald-800" : "text-neutral-800"}`}>{s.label}</div>
                <div className="text-[11.5px] text-neutral-600 mt-0.5">
                  {ok
                    ? formatProvSuccess(s.key, r)
                    : (r?.error || r?.reason || (r?.warning) || "Pas encore provisionné")}
                </div>
                {!ok && data && (
                  <button
                    onClick={() => retry(s.key)}
                    disabled={busy}
                    className="mt-2 text-[11.5px] font-medium text-neutral-700 hover:text-neutral-900 underline disabled:opacity-60"
                    data-testid={`retry-${s.key}`}
                  >
                    Réessayer
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {data?.status === "completed" && (
        <div className="mt-4 text-[12px] text-emerald-700">
          ✅ Provisioning terminé · {data.services_ok?.length || 0}/4 services OK
        </div>
      )}
      {data?.status === "partial" && (
        <div className="mt-4 text-[12px] text-amber-700">
          ⚠️ Provisioning partiel · réessayez les services qui ont échoué.
        </div>
      )}
    </div>
  );
}

function formatProvSuccess(kind, r) {
  if (kind === "gsc") return `Site ajouté : ${r.site_url || "—"}`;
  if (kind === "gmc") return `Sub-account : ${r.merchant_id || "—"} (MCA ${r.mca_id || "—"})`;
  if (kind === "ads") return `Customer : ${r.ads_customer_id || "—"} sous MCC ${r.mcc_id || "—"}`;
  if (kind === "ga4") return `Property ${r.ga4_property_id || "—"} · ${r.ga4_measurement_id || ""}`;
  return "OK";
}

function ScoreRing({ score, color }) {
  const size = 80;
  const stroke = 8;
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const clamped = Math.max(0, Math.min(100, score));
  const dash = (clamped / 100) * c;
  return (
    <svg width={size} height={size} className="flex-shrink-0" data-testid="qa-score-ring">
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#F5F2EB" strokeWidth={stroke} />
      <circle
        cx={size / 2} cy={size / 2} r={r}
        fill="none" stroke={color} strokeWidth={stroke} strokeLinecap="round"
        strokeDasharray={`${dash} ${c - dash}`} strokeDashoffset={c / 4}
        transform={`rotate(-90 ${size / 2} ${size / 2})`}
      />
      <text
        x="50%" y="50%" dominantBaseline="central" textAnchor="middle"
        fill="#1C1917" style={{ fontFamily: "'Fraunces', serif", fontSize: 22, fontWeight: 600 }}
      >
        {clamped}
      </text>
    </svg>
  );
}
t. Corrigez-les avant la mise en ligne, ou
              demandez à un admin Altiaro un passage forcé.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function ScoreRing({ score, color }) {
  const size = 80;
  const stroke = 8;
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const clamped = Math.max(0, Math.min(100, score));
  const dash = (clamped / 100) * c;
  return (
    <svg width={size} height={size} className="flex-shrink-0" data-testid="qa-score-ring">
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#F5F2EB" strokeWidth={stroke} />
      <circle
        cx={size / 2} cy={size / 2} r={r}
        fill="none" stroke={color} strokeWidth={stroke} strokeLinecap="round"
        strokeDasharray={`${dash} ${c - dash}`} strokeDashoffset={c / 4}
        transform={`rotate(-90 ${size / 2} ${size / 2})`}
      />
      <text
        x="50%" y="50%" dominantBaseline="central" textAnchor="middle"
        fill="#1C1917" style={{ fontFamily: "'Fraunces', serif", fontSize: 22, fontWeight: 600 }}
      >
        {clamped}
      </text>
    </svg>
  );
}
