import React, { useEffect, useState, useCallback } from "react";
import { Link } from "react-router-dom";
import {
  ArrowLeft, GoogleLogo, CheckCircle, Warning, XCircle, ArrowsClockwise,
  ShieldCheck, Sparkle, Plug, ArrowSquareOut,
} from "@phosphor-icons/react";
import { api, apiCall } from "../lib/api";

export default function AdminGoogleMaster() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState("");
  const [toast, setToast] = useState(null);

  const showToast = (kind, msg) => {
    setToast({ kind, msg });
    setTimeout(() => setToast(null), 6500);
  };

  const load = useCallback(async () => {
    setLoading(true);
    const { data: d } = await apiCall(() => api.get("/admin/google/master/dashboard"));
    setData(d || null);
    setLoading(false);
  }, []);
  useEffect(() => { load(); }, [load]);

  const startOAuth = async () => {
    setBusy("oauth");
    const { data: d, error } = await apiCall(() => api.get("/admin/google/master/start"));
    setBusy("");
    if (error) return showToast("error", error);
    if (d?.authorization_url) {
      window.location.href = d.authorization_url;
    }
  };

  const reDiscover = async () => {
    setBusy("discover");
    const { data: d, error } = await apiCall(() => api.post("/admin/google/master/discover", {}));
    setBusy("");
    if (error) return showToast("error", error);
    showToast("ok", "Découverte relancée. Données mises à jour.");
    load();
    return d;
  };

  const repostDns = async () => {
    setBusy("dns");
    const { error } = await apiCall(() =>
      api.post("/admin/google/dns-verification", { domain: "altiaro.com" }),
    );
    setBusy("");
    if (error) return showToast("error", error);
    showToast("ok", "TXT DNS reposté sur altiaro.com via OVH.");
    load();
  };

  const disconnect = async () => {
    if (!window.confirm("Déconnecter le compte maître Google ? Toutes les fonctions de provisioning seront désactivées.")) return;
    await apiCall(() => api.post("/admin/google/master/disconnect"));
    load();
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#FAF7F2] flex items-center justify-center">
        <div className="text-sm text-neutral-500">Chargement…</div>
      </div>
    );
  }
  const connected = !!data?.connected;

  return (
    <div className="min-h-screen bg-[#FAF7F2]">
      <div className="max-w-[1100px] mx-auto px-6 md:px-10 py-10">
        <Link to="/admin/integrations" className="inline-flex items-center gap-2 text-sm text-neutral-600 hover:text-neutral-900 mb-6">
          <ArrowLeft size={14} /> Intégrations
        </Link>

        <div className="mb-8">
          <div className="text-[11px] uppercase tracking-[0.2em] text-neutral-500 mb-2 flex items-center gap-2">
            <ShieldCheck size={12} weight="bold" /> Compte maître Altiaro
          </div>
          <h1 className="text-3xl md:text-4xl font-semibold text-neutral-900" style={{ fontFamily: "'Fraunces', serif" }}>
            Connexion Google maître
          </h1>
          <p className="text-sm text-neutral-500 mt-2 max-w-2xl">
            Une seule connexion OAuth pour toute la vie d'Altiaro. Tout le reste est
            découvert et configuré automatiquement (GA4, Merchant, Ads, Search Console,
            DNS altiaro.com via OVH).
          </p>
        </div>

        {toast && (
          <div className={`mb-6 rounded-xl border px-4 py-3 text-sm ${
            toast.kind === "ok"
              ? "border-emerald-200 bg-emerald-50 text-emerald-800"
              : "border-rose-200 bg-rose-50 text-rose-800"
          }`}>{toast.msg}</div>
        )}

        {/* Carte principale */}
        <div className="bg-white rounded-2xl border border-neutral-200 p-6 mb-6" data-testid="master-status-card">
          <div className="flex items-start justify-between gap-4 flex-wrap">
            <div className="flex items-start gap-3 min-w-[260px]">
              <GoogleLogo size={26} weight="bold" className="text-neutral-900 mt-1" />
              <div>
                <div className="text-[18px] font-semibold text-neutral-900">
                  {connected ? "Compte maître connecté" : "Compte maître non connecté"}
                </div>
                <div className="text-[13px] text-neutral-600 mt-1">
                  {connected ? (
                    <>
                      <strong>{data.google_email || "compte inconnu"}</strong>
                      {data.scopes?.length ? (
                        <span className="ml-2 text-neutral-500">· {data.scopes.length} scopes accordés</span>
                      ) : null}
                    </>
                  ) : (
                    "Cliquez ci-dessous pour autoriser Altiaro à appeler les API Google en votre nom."
                  )}
                </div>
              </div>
            </div>
            <div className="flex items-center gap-2 flex-wrap">
              {connected ? (
                <>
                  <button onClick={reDiscover} disabled={busy === "discover"} data-testid="rediscover"
                    className="h-10 px-4 rounded-xl bg-white border border-neutral-200 hover:border-neutral-400 text-neutral-700 text-sm font-medium flex items-center gap-2 disabled:opacity-60">
                    <ArrowsClockwise size={14} weight="bold" className={busy === "discover" ? "animate-spin" : ""} />
                    Re-découvrir
                  </button>
                  <button onClick={disconnect}
                    className="h-10 px-4 rounded-xl text-rose-700 text-sm hover:bg-rose-50">
                    Déconnecter
                  </button>
                </>
              ) : (
                <button onClick={startOAuth} disabled={busy === "oauth"} data-testid="connect-master"
                  className="h-12 px-6 rounded-xl bg-[#1C1917] hover:bg-[#0A0A0A] text-white font-semibold flex items-center gap-2 disabled:opacity-60">
                  <Plug size={16} weight="bold" />
                  {busy === "oauth" ? "Ouverture…" : "Connecter le compte maître Altiaro"}
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Récapitulatif des découvertes */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
          <Tile
            label="GA4 Account"
            ok={!!data?.ga4_master?.account_id}
            value={data?.ga4_master?.account_id ? `${data.ga4_master.display_name || "Altiaro"} (${data.ga4_master.account_id})` : null}
            empty="Lance Connecter le compte maître pour découvrir ton account GA4"
            extra={data?.ga4_master?.property_summaries?.length ? `${data.ga4_master.property_summaries.length} propriétés visibles` : null}
            testId="tile-ga4"
          />
          <Tile
            label="Merchant Center"
            ok={!!data?.gmc_master?.account_id}
            warn={!!data?.gmc_master && data.gmc_master.is_mca === false}
            value={data?.gmc_master?.account_id ? `ID ${data.gmc_master.account_id}${data.gmc_master.is_mca ? " · MCA actif" : " · Compte simple"}` : null}
            empty="Le master OAuth découvre le compte Merchant"
            extra={data?.gmc_master?.warning}
            testId="tile-gmc"
          />
          <Tile
            label="Google Ads MCC"
            ok={!!data?.ads_master?.mcc_id || !!data?.ads_mcc_env}
            value={(data?.ads_master?.mcc_id_human || data?.ads_mcc_env) ? `MCC ${data.ads_master?.mcc_id_human || data.ads_mcc_env}` : null}
            empty="MCC manquant — variable GOOGLE_ADS_LOGIN_CUSTOMER_ID"
            testId="tile-ads"
          />
          <Tile
            label="DNS altiaro.com"
            ok={!!data?.dns_verification?.records?.length}
            value={data?.dns_verification?.records?.length
              ? `TXT posé via OVH le ${(data.dns_verification.verified_at || "").split("T")[0]}`
              : null}
            empty="TXT non posé"
            extra={data?.dns_verification?.propagation_observed === false ? "⏳ Propagation en cours" : null}
            actionLabel={connected ? "Reposter TXT" : null}
            onAction={repostDns}
            actionBusy={busy === "dns"}
            testId="tile-dns"
          />
          <Tile
            label="Vérification altiaro.com chez Google"
            ok={!!(data?.altiaro_verification?.site_verification?.ok)}
            value={(data?.altiaro_verification?.site_verification?.ok)
              ? "altiaro.com confirmé auprès de Google"
              : null}
            empty="Pose le TXT puis clique Re-découvrir"
            extra={(data?.altiaro_verification?.site_verification?.error) || null}
            testId="tile-verify"
          />
          <Tile
            label="Search Console (master)"
            ok={!!(data?.altiaro_verification?.gsc_added?.ok)}
            value={(data?.altiaro_verification?.gsc_added?.ok)
              ? `sc-domain:altiaro.com ajouté`
              : null}
            empty="Sera ajouté après la vérification"
            extra={(data?.altiaro_verification?.gsc_added?.error) || null}
            testId="tile-gsc"
          />
        </div>

        {/* Architecture Google Ads multi-sites — explication produit */}
        <div
          className="bg-blue-50/60 border border-blue-200 rounded-2xl p-6 mb-6"
          data-testid="ads-architecture-info"
        >
          <div className="flex items-start gap-3">
            <div className="w-9 h-9 rounded-xl bg-blue-100 flex items-center justify-center flex-shrink-0">
              <ShieldCheck size={18} weight="duotone" className="text-blue-700" />
            </div>
            <div className="flex-1">
              <div className="text-[15px] font-semibold text-blue-900 mb-1.5">
                Architecture Google Ads multi-sites
              </div>
              <p className="text-[13px] text-blue-900/90 leading-[1.65]">
                Altiaro crée automatiquement <strong>1 sous-compte Google Ads par site lancé</strong>,
                rattaché à votre Manager Account (MCC) maître. Vous gérez tous les sites depuis
                un seul dashboard, mais chaque site a son budget, ses campagnes, ses conversions
                et ses audiences <strong>isolés</strong>.
              </p>
              <p className="text-[12.5px] text-blue-900/75 leading-[1.6] mt-2">
                C'est l'architecture standard utilisée par les agences e-commerce et les
                plateformes SaaS pour suivre la performance par boutique sans mélanger les
                données. <em>Note :</em> la création automatique de sous-clients nécessite un
                Developer Token Google Ads en accès « basic » ou « standard » (l'accès
                « explorer » par défaut ne permet que la lecture).
              </p>
            </div>
          </div>
        </div>

        {/* Conclusion */}
        {connected && (
          <div className="bg-gradient-to-br from-emerald-50 to-white border border-emerald-200 rounded-2xl p-6"
               data-testid="ready-banner">
            <div className="flex items-center gap-2 mb-2">
              <Sparkle size={18} weight="fill" className="text-emerald-600" />
              <div className="text-[16px] font-semibold text-emerald-800">L'usine est prête</div>
            </div>
            <p className="text-[13.5px] text-emerald-900 leading-[1.6]">
              Vous pouvez maintenant lancer des sites. À chaque Go-Live, Altiaro
              provisionnera automatiquement Search Console, Merchant Center, Google Ads
              et GA4 pour ce site, et injectera le tracking dans le storefront.
            </p>
          </div>
        )}

        {!connected && (
          <div className="bg-amber-50 border border-amber-200 rounded-2xl p-5 text-[13px] text-amber-900">
            <strong>Une seule action restante</strong> : cliquez « Connecter le compte
            maître Altiaro ». Tout le reste sera fait par Altiaro en arrière-plan
            (découverte GA4 / Merchant / Ads, vérification DNS, claim Search Console).
          </div>
        )}
      </div>
    </div>
  );
}

function Tile({ label, ok, warn, value, empty, extra, actionLabel, onAction, actionBusy, testId }) {
  const tone = ok && !warn ? "emerald" : warn ? "amber" : "neutral";
  const Icon = ok && !warn ? CheckCircle : warn ? Warning : XCircle;
  const colorMap = {
    emerald: "border-emerald-200 bg-emerald-50",
    amber:   "border-amber-200 bg-amber-50",
    neutral: "border-neutral-200 bg-white",
  };
  const iconColorMap = {
    emerald: "text-emerald-600",
    amber:   "text-amber-600",
    neutral: "text-neutral-300",
  };
  return (
    <div className={`rounded-2xl border ${colorMap[tone]} p-5`} data-testid={testId}>
      <div className="flex items-start gap-3">
        <Icon size={20} weight="fill" className={`flex-shrink-0 mt-0.5 ${iconColorMap[tone]}`} />
        <div className="min-w-0 flex-1">
          <div className="text-[11px] uppercase tracking-[0.2em] text-neutral-500 mb-1">{label}</div>
          <div className="text-[14px] font-medium text-neutral-900">
            {value || <span className="text-neutral-400 font-normal italic">{empty}</span>}
          </div>
          {extra && <div className="text-[12px] text-neutral-600 mt-1.5">{extra}</div>}
          {actionLabel && onAction && (
            <button
              onClick={onAction}
              disabled={actionBusy}
              className="mt-3 inline-flex items-center gap-1.5 text-[12px] font-medium text-neutral-700 hover:text-neutral-900 underline disabled:opacity-60"
            >
              <ArrowSquareOut size={12} weight="bold" />
              {actionBusy ? "En cours…" : actionLabel}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
