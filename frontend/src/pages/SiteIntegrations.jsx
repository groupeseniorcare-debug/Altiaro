import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import {
  GoogleLogo, ChartLineUp, ShoppingBag, Lightning,
  CheckCircle, Warning, ArrowSquareOut, SpinnerGap, Info,
} from "@phosphor-icons/react";
import { api, apiCall } from "../lib/api";

/**
 * Cockpit · Intégrations en 1 clic (Bloc 2 sous-phase 2D).
 *
 * 3 cards : Google Search Console · Google Merchant Center · IndexNow.
 *
 * Logic:
 *  - On mount : load status of each integration in parallel
 *  - "Connecter" button opens the OAuth authorization_url in a popup
 *  - Once connected : show contextual actions (submit sitemap, force sync,
 *    ping IndexNow)
 */

function StatusPill({ connected }) {
  if (connected) {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-medium bg-emerald-50 border border-emerald-200 text-emerald-700">
        <CheckCircle size={12} weight="fill" />
        Connecté
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-medium bg-neutral-100 border border-neutral-200 text-neutral-600">
      <Warning size={12} />
      Non connecté
    </span>
  );
}

function IntegrationCard({ icon: Icon, title, why, status, onConnect, onDisconnect, actions, loading, connected, ariaLabel }) {
  return (
    <div className="bg-white border border-neutral-200 rounded-xl p-6" data-testid={`integ-${ariaLabel}`}>
      <div className="flex items-start justify-between gap-4 mb-4">
        <div className="flex items-start gap-3">
          <div className="w-11 h-11 rounded-lg bg-neutral-100 flex items-center justify-center shrink-0">
            <Icon size={22} className="text-neutral-700" />
          </div>
          <div className="min-w-0">
            <h3 className="text-lg font-semibold text-neutral-900">{title}</h3>
            <p className="text-[13px] text-neutral-600 mt-0.5 leading-relaxed">{why}</p>
          </div>
        </div>
        <StatusPill connected={connected} />
      </div>
      <div className="flex flex-wrap items-center gap-2 mt-4 pt-4 border-t border-neutral-100">
        {!connected ? (
          <button
            onClick={onConnect}
            disabled={loading}
            data-testid={`integ-${ariaLabel}-connect`}
            className="h-10 px-4 rounded-lg bg-neutral-900 text-white text-sm font-semibold hover:bg-neutral-800 disabled:opacity-50 inline-flex items-center gap-2"
          >
            {loading ? <SpinnerGap size={14} className="animate-spin" /> : <ArrowSquareOut size={14} weight="bold" />}
            Connecter en 1 clic
          </button>
        ) : (
          <>
            {actions}
            <button
              onClick={onDisconnect}
              data-testid={`integ-${ariaLabel}-disconnect`}
              className="h-10 px-3 rounded-lg border border-neutral-200 text-neutral-600 text-sm hover:bg-neutral-50"
            >
              Déconnecter
            </button>
          </>
        )}
      </div>
      {status && status.account && (
        <div className="mt-3 text-[11px] text-neutral-500">
          Compte : <code className="px-1 py-0.5 bg-neutral-100 rounded">{status.account}</code>
        </div>
      )}
    </div>
  );
}

export default function SiteIntegrations() {
  const { siteId } = useParams();
  const [gscStatus, setGscStatus] = useState({ connected: false });
  const [merchantStatus, setMerchantStatus] = useState({ connected: false });
  const [indexnowState, setIndexnowState] = useState({ url: null, last_ping: null });
  const [loading, setLoading] = useState({ gsc: false, merchant: false, indexnow: false });
  const [pingResult, setPingResult] = useState(null);
  const [sitemapSubmitted, setSitemapSubmitted] = useState(false);

  const reloadAll = async () => {
    const [g, m] = await Promise.all([
      apiCall(() => api.get(`/sites/${siteId}/gsc/status`)),
      apiCall(() => api.get(`/sites/${siteId}/merchant/status`)),
    ]);
    if (g.data) setGscStatus(g.data);
    if (m.data) setMerchantStatus(m.data);
    // IndexNow: derive the public key URL from the platform constant
    setIndexnowState({
      url: `${window.location.origin}/api/public/sites/${siteId}/sitemap.xml`,
      last_ping: null,  // not stored yet
    });
  };

  useEffect(() => {
    if (!siteId) return;
    reloadAll();
  }, [siteId]);

  const connectGSC = async () => {
    setLoading((l) => ({ ...l, gsc: true }));
    const { data, error, rawDetail } = await apiCall(() => api.get(`/sites/${siteId}/gsc/connect`));
    setLoading((l) => ({ ...l, gsc: false }));
    if (error) { window.alert(rawDetail?.detail || error); return; }
    if (data?.authorization_url) {
      window.open(data.authorization_url, "_blank", "noopener,noreferrer");
    }
  };
  const disconnectGSC = async () => {
    if (!window.confirm("Déconnecter Google Search Console pour ce site ?")) return;
    await apiCall(() => api.post(`/sites/${siteId}/gsc/disconnect`));
    setGscStatus({ connected: false });
    reloadAll();
  };
  const submitSitemapToGSC = async () => {
    setLoading((l) => ({ ...l, gsc: true }));
    const { error, rawDetail } = await apiCall(() =>
      api.post(`/sites/${siteId}/gsc/submit-sitemap`)
    );
    setLoading((l) => ({ ...l, gsc: false }));
    if (error) {
      // L'endpoint peut ne pas exister encore — on le fait fallback noop
      window.alert("Submit sitemap : " + (rawDetail?.detail || error));
      return;
    }
    setSitemapSubmitted(true);
  };

  const connectMerchant = async () => {
    setLoading((l) => ({ ...l, merchant: true }));
    const { data, error, rawDetail } = await apiCall(() => api.get(`/merchant/oauth/start?site_id=${siteId}`));
    setLoading((l) => ({ ...l, merchant: false }));
    if (error) { window.alert(rawDetail?.detail || error); return; }
    if (data?.authorization_url) {
      window.open(data.authorization_url, "_blank", "noopener,noreferrer");
    }
  };
  const disconnectMerchant = async () => {
    if (!window.confirm("Déconnecter Google Merchant Center ?")) return;
    await apiCall(() => api.post(`/merchant/disconnect`));
    setMerchantStatus({ connected: false });
    reloadAll();
  };
  const forceMerchantSync = async () => {
    setLoading((l) => ({ ...l, merchant: true }));
    await apiCall(() => api.post(`/sites/${siteId}/merchant/sync`));
    setLoading((l) => ({ ...l, merchant: false }));
  };

  const pingIndexNow = async () => {
    setLoading((l) => ({ ...l, indexnow: true }));
    const { data, error } = await apiCall(() => api.post(`/sites/${siteId}/indexnow/resubmit-all`));
    setLoading((l) => ({ ...l, indexnow: false }));
    if (error) { setPingResult({ ok: false, msg: error }); return; }
    setPingResult({ ok: true, msg: `Ping envoyé : ${data?.urls_pinged || 0} URLs soumises à Bing.` });
  };

  return (
    <div className="max-w-4xl mx-auto px-6 py-8" data-testid="site-integrations-page">
      <div className="mb-8">
        <Link to={`/sites/${siteId}/branding`} className="text-[12px] text-neutral-500 hover:text-neutral-900 mb-3 inline-block">
          ← Retour au cockpit
        </Link>
        <div className="text-[11px] uppercase tracking-[0.25em] text-neutral-500 mb-2">Étape 8 · SEO & visibilité</div>
        <h1 className="text-3xl font-semibold text-neutral-900">Intégrations en 1 clic</h1>
        <p className="text-sm text-neutral-600 mt-2 max-w-2xl leading-relaxed">
          Connecte Google Search Console, Google Merchant Center et IndexNow en quelques secondes.
          Sans ces 3 outils, tu pars d'une feuille blanche aux yeux des moteurs de recherche.
        </p>
      </div>

      <div className="space-y-4">
        {/* === GSC === */}
        <IntegrationCard
          icon={ChartLineUp}
          title="Google Search Console"
          why="Indispensable pour que Google indexe ton site, mesurer tes positions, ton CTR organique, et soumettre ton sitemap."
          ariaLabel="gsc"
          connected={gscStatus.connected}
          status={gscStatus}
          loading={loading.gsc}
          onConnect={connectGSC}
          onDisconnect={disconnectGSC}
          actions={
            <button
              onClick={submitSitemapToGSC}
              data-testid="integ-gsc-submit-sitemap"
              className="h-10 px-4 rounded-lg bg-emerald-600 text-white text-sm font-semibold hover:bg-emerald-700 inline-flex items-center gap-2"
            >
              <Lightning size={14} weight="fill" />
              {sitemapSubmitted ? "Sitemap soumis ✓" : "Soumettre le sitemap à GSC"}
            </button>
          }
        />

        {/* === Merchant === */}
        <IntegrationCard
          icon={ShoppingBag}
          title="Google Merchant Center"
          why="Diffuse tes produits gratuitement dans Google Shopping organique (≈ 30% des clics e-commerce viennent de là)."
          ariaLabel="merchant"
          connected={merchantStatus.connected}
          status={merchantStatus}
          loading={loading.merchant}
          onConnect={connectMerchant}
          onDisconnect={disconnectMerchant}
          actions={
            <button
              onClick={forceMerchantSync}
              data-testid="integ-merchant-sync"
              className="h-10 px-4 rounded-lg bg-emerald-600 text-white text-sm font-semibold hover:bg-emerald-700 inline-flex items-center gap-2"
            >
              <Lightning size={14} weight="fill" />
              Forcer la synchro produits
            </button>
          }
        />

        {/* === IndexNow === */}
        <IntegrationCard
          icon={GoogleLogo}
          title="IndexNow (Bing & Yandex)"
          why="Pousse instantanément chaque nouvelle URL chez Bing et Yandex (~10% du trafic FR additionnel, gratuit, déjà configuré)."
          ariaLabel="indexnow"
          connected={true}  // toujours actif (clé .env)
          status={null}
          loading={loading.indexnow}
          onConnect={() => {}}
          onDisconnect={() => {}}
          actions={
            <>
              <button
                onClick={pingIndexNow}
                data-testid="integ-indexnow-ping"
                className="h-10 px-4 rounded-lg bg-emerald-600 text-white text-sm font-semibold hover:bg-emerald-700 inline-flex items-center gap-2"
              >
                <Lightning size={14} weight="fill" />
                Pinger Bing maintenant
              </button>
              {pingResult && (
                <span
                  className={`text-[12px] ${pingResult.ok ? "text-emerald-700" : "text-rose-700"}`}
                  data-testid="integ-indexnow-result"
                >
                  {pingResult.msg}
                </span>
              )}
            </>
          }
        />
      </div>

      <div className="mt-8 p-4 rounded-xl bg-blue-50 border border-blue-200 text-[13px] text-blue-900 flex items-start gap-3">
        <Info size={16} className="shrink-0 mt-0.5" />
        <div>
          <strong>Workflow recommandé</strong> — (1) Connecte GSC en cliquant sur le bouton ci-dessus
          et autorise via ton compte Google. (2) Soumets le sitemap. (3) Connecte Merchant
          Center et lance une synchro pour activer Google Shopping organique.
          (4) Active IndexNow (déjà fait). Le tout prend &lt; 5 minutes.
        </div>
      </div>
    </div>
  );
}
