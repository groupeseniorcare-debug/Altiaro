import React, { useEffect, useState, useMemo } from "react";
import { useParams, useNavigate, useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import {
  ArrowLeft, ChartLineUp, CircleNotch, CheckCircle, PencilSimple,
} from "@phosphor-icons/react";
import { api, apiCall } from "../lib/api";
import Layout from "../components/Layout";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "../components/ui/tabs";
import { useAuth } from "../lib/auth";
import OverviewTab from "../components/analytics-tabs/OverviewTab";
import ProductsTab from "../components/analytics-tabs/ProductsTab";
import OrdersTab from "../components/analytics-tabs/OrdersTab";
import FinanceTab from "../components/analytics-tabs/FinanceTab";
import SeoTab from "../components/analytics-tabs/SeoTab";

/**
 * Phase 5 — Dashboard post-validation unifié.
 * Accessible uniquement si TOUS les 9 steps cockpit sont complete (journey.all_completed=true).
 * Sinon : redirect /sites/:id + toast.
 *
 * Layout à 5 onglets (overview / products / orders / finance / seo), URL-synced
 * via ?tab=xxx. Bouton "Modifier le site" en header qui ramène au cockpit.
 */
const VALID_TABS = ["overview", "products", "orders", "finance", "seo"];
const LIVE_POLL_MS = 15000;

export default function SiteAnalytics() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const { user } = useAuth() || {};
  const isAdmin = user?.role === "admin";

  const [site, setSite] = useState(null);
  const [live, setLive] = useState(null);
  const [gateChecked, setGateChecked] = useState(false);

  // Onglet actif depuis l'URL (fallback: overview)
  const urlTab = searchParams.get("tab");
  const activeTab = VALID_TABS.includes(urlTab) ? urlTab : "overview";
  const setActiveTab = (value) => {
    const next = new URLSearchParams(searchParams);
    if (value === "overview") next.delete("tab");
    else next.set("tab", value);
    setSearchParams(next, { replace: true });
  };

  // --- Gating : seul un site totalement validé peut accéder ici --- //
  useEffect(() => {
    let cancel = false;
    (async () => {
      const [siteRes, journeyRes] = await Promise.all([
        apiCall(() => api.get(`/sites/${id}`)),
        apiCall(() => api.get(`/sites/${id}/journey`)),
      ]);
      if (cancel) return;
      if (siteRes.data) setSite(siteRes.data);
      const validated = journeyRes.data?.all_completed === true;
      if (!validated) {
        toast.error("Ton site doit être validé (QA OK) avant d'accéder au dashboard.");
        navigate(`/sites/${id}`);
        return;
      }
      setGateChecked(true);
    })();
    return () => { cancel = true; };
  }, [id, navigate]);

  // --- Polling live (15s), uniquement sur Overview pour éviter le trafic inutile --- //
  useEffect(() => {
    if (!gateChecked || activeTab !== "overview") return;
    const tick = async () => {
      const { data } = await apiCall(() => api.get(`/sites/${id}/analytics/live`));
      if (data) setLive(data);
    };
    tick();
    const t = setInterval(tick, LIVE_POLL_MS);
    return () => clearInterval(t);
  }, [id, gateChecked, activeTab]);

  const adminEmail = process.env.REACT_APP_ADMIN_EMAIL || "admin@altiaro.com";
  const mailtoAds = useMemo(() => {
    if (!site) return "#";
    return `mailto:${adminEmail}?subject=${encodeURIComponent(
      `[Altiaro] Lancer campagne Google Ads — ${site.name}`
    )}&body=${encodeURIComponent(
      `Bonjour,\n\nLe site "${site.name}" (id: ${site.id}) est validé et je voudrais lancer les campagnes Google Ads sur les marchés : ${
        (site.selected_countries || []).join(", ") || "(à définir)"
      }.\n\nMerci.`
    )}`;
  }, [site, adminEmail]);

  if (!gateChecked) {
    return (
      <Layout>
        <div className="p-8 md:p-12 text-neutral-500 flex items-center gap-2">
          <CircleNotch size={16} className="animate-spin" /> Vérification de l'accès…
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="p-6 md:p-10 max-w-[1400px] mx-auto w-full">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-6" data-testid="analytics-header">
          <div className="flex items-start gap-3">
            <button
              onClick={() => navigate(`/sites/${id}`)}
              className="flex items-center gap-1.5 h-9 px-3 rounded-lg border border-neutral-200 hover:bg-neutral-50 text-sm font-medium text-neutral-700 transition mt-1"
              data-testid="back-to-cockpit"
              title="Retour au cockpit 9 étapes"
            >
              <ArrowLeft size={14} />
              <PencilSimple size={13} weight="duotone" />
              <span className="hidden sm:inline">Modifier le site</span>
            </button>
            <div>
              <div className="text-[11px] uppercase tracking-[0.2em] text-neutral-500 mb-1 flex items-center gap-2">
                <ChartLineUp size={12} weight="bold" /> Dashboard
                <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-emerald-50 text-emerald-700 rounded-full text-[10px] font-semibold">
                  <CheckCircle size={10} weight="fill" />
                  Site validé
                </span>
                {live && live.active_sessions > 0 && (
                  <span className="inline-flex items-center gap-1.5 px-2 py-0.5 bg-emerald-500/10 text-emerald-700 rounded-full text-[10px] font-semibold">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                    {live.active_sessions} actif{live.active_sessions > 1 ? "s" : ""}
                  </span>
                )}
              </div>
              <h1 className="text-2xl md:text-3xl font-semibold text-neutral-900" style={{ fontFamily: "'Fraunces', serif" }}>
                {site?.name || "Dashboard"}
              </h1>
              <p className="text-xs text-neutral-500 mt-1">
                Données internes Altiaro · indépendantes de GA4
              </p>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="inline-flex items-center gap-1 bg-neutral-100 p-1 rounded-lg mb-6 flex-wrap h-auto">
            <TabsTrigger value="overview"  data-testid="tab-overview"  className="h-9 px-4 rounded-md text-sm">
              Vue d'ensemble
            </TabsTrigger>
            <TabsTrigger value="products"  data-testid="tab-products"  className="h-9 px-4 rounded-md text-sm">
              Produits
            </TabsTrigger>
            <TabsTrigger value="orders"    data-testid="tab-orders"    className="h-9 px-4 rounded-md text-sm">
              Commandes
            </TabsTrigger>
            <TabsTrigger value="finance"   data-testid="tab-finance"   className="h-9 px-4 rounded-md text-sm">
              Finance
            </TabsTrigger>
            <TabsTrigger value="seo"       data-testid="tab-seo"       className="h-9 px-4 rounded-md text-sm">
              SEO / AEO
            </TabsTrigger>
          </TabsList>

          <TabsContent value="overview"  className="mt-0"><OverviewTab  siteId={id} site={site} mailtoAds={mailtoAds} /></TabsContent>
          <TabsContent value="products"  className="mt-0"><ProductsTab  siteId={id} /></TabsContent>
          <TabsContent value="orders"    className="mt-0"><OrdersTab    siteId={id} /></TabsContent>
          <TabsContent value="finance"   className="mt-0"><FinanceTab   siteId={id} isAdmin={isAdmin} /></TabsContent>
          <TabsContent value="seo"       className="mt-0"><SeoTab       siteId={id} /></TabsContent>
        </Tabs>
      </div>
    </Layout>
  );
}
