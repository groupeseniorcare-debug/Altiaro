import React from "react";
import { BrowserRouter, Routes, Route, Navigate, useParams } from "react-router-dom";
import { AuthProvider, useAuth } from "./lib/auth";
import {
  CustomShopProvider,
  useCustomDomainBootstrap,
} from "./lib/shopSiteId";
import ScrollToTop from "./components/ScrollToTop";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Sites from "./pages/Sites";
import NewSite from "./pages/NewSite";
import SiteDetail from "./pages/SiteDetail";
import Finance from "./pages/Finance";
import AdminFinances from "./pages/AdminFinances";
import AdminLegalSettings from "./pages/AdminLegalSettings";
import SiteIntegrations from "./pages/SiteIntegrations";
import Users from "./pages/Users";
import NicheEngine from "./pages/Analyzer";
import NicheAnalysisDetail from "./pages/NicheAnalysisDetail";
import SiteProducts from "./pages/SiteProducts";
import SiteBlogPosts from "./pages/SiteBlogPosts";
import SiteSEO from "./pages/SiteSEO";
import SiteAliExpressImport from "./pages/SiteAliExpressImport";
import SitePricing from "./pages/SitePricing";
import SiteForecast from "./pages/SiteForecast";
import SiteUpsells from "./pages/SiteUpsells";
import SiteBranding from "./pages/SiteBranding";
import SitePages from "./pages/SitePages";
import SiteFulfillment from "./pages/SiteFulfillment";
import SiteAnalytics from "./pages/SiteAnalytics";
import SiteQA from "./pages/SiteQA";
import AdminGoogleMaster from "./pages/AdminGoogleMaster";
import Sourcing from "./pages/Sourcing";
import AdminIntegrations from "./pages/AdminIntegrations";
import AdminReview from "./pages/AdminReview";
import Empire from "./pages/Empire";
import Billing from "./pages/Billing";
import Orders from "./pages/Orders";
import AdminPayouts from "./pages/AdminPayouts";
import Domains from "./pages/Domains";
import SiteSettings from "./pages/SiteSettings";
import StorefrontRegister from "./pages/StorefrontRegister";
import StorefrontLogin from "./pages/StorefrontLogin";
import StorefrontAccount from "./pages/StorefrontAccount";
import StorefrontOrderDetail from "./pages/StorefrontOrderDetail";
import StorefrontTrack from "./pages/StorefrontTrack";
import StorefrontSearch from "./pages/StorefrontSearch";
import GoogleAds from "./pages/GoogleAds";
import AdminSiteGoogleAds from "./pages/AdminSiteGoogleAds";
import Opportunities from "./pages/Opportunities";
import QuickScan from "./pages/QuickScan";
import LaunchSite from "./pages/LaunchSite";
import ProductImagesReview from "./pages/ProductImagesReview";
import SiteTranslate from "./pages/SiteTranslate";
import Landing from "./pages/Landing";
// Legacy Legal page — remplacé par PlatformLegal*.jsx dans /legal/*
// import Legal from "./pages/Legal";
import PlatformLegalRetours from "./pages/PlatformLegalRetours";
import PlatformLegalLivraison from "./pages/PlatformLegalLivraison";
import PlatformLegalCgv from "./pages/PlatformLegalCgv";
import PlatformLegalConfidentialite from "./pages/PlatformLegalConfidentialite";
import PlatformLegalMentions from "./pages/PlatformLegalMentions";
import Signup from "./pages/Signup";
import VerifyEmail from "./pages/VerifyEmail";
import StorefrontHome from "./pages/StorefrontHome";
import StorefrontProduct from "./pages/StorefrontProduct";
import StorefrontCart from "./pages/StorefrontCart";
import StorefrontCheckout from "./pages/StorefrontCheckout";
import StorefrontConfirmation from "./pages/StorefrontConfirmation";
import {
  StorefrontCollections,
  StorefrontCollection,
} from "./pages/StorefrontCollection";
import {
  StorefrontBlog,
  StorefrontBlogPost,
} from "./pages/StorefrontBlog";
import StorefrontReview from "./pages/StorefrontReview";
import StorefrontAllProducts from "./pages/StorefrontAllProducts";
import StorefrontAccessoriesPage from "./pages/StorefrontAccessoriesPage";
import {
  StorefrontBuyerGuides,
  StorefrontBuyerGuide,
  StorefrontGlossary,
  StorefrontGlossaryTerm,
  StorefrontComparisons,
  StorefrontCompare,
  StorefrontTopLists,
  StorefrontTopList,
  StorefrontTeam,
  StorefrontTeamMember,
} from "./pages/StorefrontSEOContent";
import {
  StorefrontAbout,
  StorefrontFAQ,
  StorefrontContact,
  StorefrontCGV,
  StorefrontMentions,
  StorefrontConfidentialite,
  StorefrontCookies,
  StorefrontLivraison,
  StorefrontRetours,
  StorefrontMediation,
} from "./pages/StorefrontPages";
import { Toaster } from "./components/ui/sonner";

function ProtectedRoute({ children, adminOnly = false }) {
  const { user } = useAuth();
  if (user === null) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#FDFBF7]">
        <div className="text-[#78716C]">Chargement...</div>
      </div>
    );
  }
  if (!user) return <Navigate to="/login" replace />;
  if (adminOnly && user.role !== "admin") return <Navigate to="/" replace />;
  return children;
}

/**
 * Redirect helper pour l'ancienne URL `/sites/:id/design` → `/sites/:id/branding?tab=avance`.
 * Phase 2 : SiteDesign a été absorbé comme onglet "Avancé" de SiteBranding.
 * Un composant dédié (plutôt qu'un `<Navigate to="..">` relatif) est nécessaire
 * car le pattern relatif `../` ne résout pas correctement avec un param dynamique
 * en React Router v7 — il oublie le `:id` et retombe sur la home.
 */
function SiteDesignRedirect() {
  const { id } = useParams();
  return <Navigate to={`/sites/${id}/branding?tab=avance`} replace />;
}


function HomeRoute() {
  // Public landing when not authed, Dashboard when authed
  const { user } = useAuth();
  if (user === null) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-white">
        <div className="text-neutral-500">Chargement...</div>
      </div>
    );
  }
  if (!user) return <Landing />;
  return <Dashboard />;
}

function App() {
  const bootstrap = useCustomDomainBootstrap();
  if (bootstrap.mode === "loading") {
    return (
      <div style={{
        minHeight: "100vh", display: "flex",
        alignItems: "center", justifyContent: "center",
        background: "#fafaf9", fontFamily: "system-ui, -apple-system, sans-serif",
      }}>
        <div style={{ color: "#78716c", fontSize: 14 }}>Chargement…</div>
      </div>
    );
  }
  if (bootstrap.mode === "custom-domain") {
    return <CustomDomainApp bootstrap={bootstrap} />;
  }
  return <PlatformApp />;
}

function CustomDomainApp({ bootstrap }) {
  // Render storefront routes at the ROOT of the URL tree (no /shop/:siteId
  // prefix) since a dedicated hostname already identifies the shop.
  // `useShopSiteId()` falls back on CustomShopProvider's context.
  //
  // 2026-05-03 — also accept the legacy `/shop/:siteId/...` prefix because
  // every internal `<Link>` in the storefront still constructs URLs that way.
  // Both work; clean URLs (`/products/X`) are preferred for SEO.
  return (
    <AuthProvider>
      <CustomShopProvider
        siteId={bootstrap.siteId}
        host={bootstrap.host}
        siteName={bootstrap.siteName}
      >
        <BrowserRouter>
          <ScrollToTop />
          <Routes>
            {/* Storefront public — clean URLs (no /shop/:siteId prefix) */}
            <Route path="/" element={<StorefrontHome />} />
            <Route path="/search" element={<StorefrontSearch />} />
            <Route path="/track" element={<StorefrontTrack />} />
            <Route path="/collections" element={<StorefrontCollections />} />
            <Route path="/collection/:slug" element={<StorefrontCollection />} />
            <Route path="/product/:productId" element={<StorefrontProduct />} />
            <Route path="/products/:productId" element={<StorefrontProduct />} />
            <Route path="/cart" element={<StorefrontCart />} />
            <Route path="/checkout" element={<StorefrontCheckout />} />
            <Route path="/checkout/success" element={<StorefrontConfirmation />} />
            <Route path="/confirmation" element={<StorefrontConfirmation />} />
            <Route path="/about" element={<StorefrontAbout />} />
            <Route path="/faq" element={<StorefrontFAQ />} />
            <Route path="/contact" element={<StorefrontContact />} />
            <Route path="/cgv" element={<StorefrontCGV />} />
            <Route path="/mentions" element={<StorefrontMentions />} />
            <Route path="/confidentialite" element={<StorefrontConfidentialite />} />
            <Route path="/cookies" element={<StorefrontCookies />} />
            <Route path="/livraison" element={<StorefrontLivraison />} />
            <Route path="/retours" element={<StorefrontRetours />} />
            <Route path="/mediation" element={<StorefrontMediation />} />
            <Route path="/blog" element={<StorefrontBlog />} />
            <Route path="/blog/:slug" element={<StorefrontBlogPost />} />
            {/* Phase 3.3 Fix 1.3 + 1.4 — pages catalogue & accessoires dédiées */}
            <Route path="/products" element={<StorefrontAllProducts />} />
            <Route path="/accessories" element={<StorefrontAccessoriesPage />} />
            {/* Sprint 2/3 — SEO content (buyer guides, glossary, comparisons, top lists, team) */}
            <Route path="/buyer-guides" element={<StorefrontBuyerGuides />} />
            <Route path="/buyer-guides/:slug" element={<StorefrontBuyerGuide />} />
            <Route path="/glossary" element={<StorefrontGlossary />} />
            <Route path="/glossary/:slug" element={<StorefrontGlossaryTerm />} />
            <Route path="/compare" element={<StorefrontComparisons />} />
            <Route path="/compare/:slug" element={<StorefrontCompare />} />
            <Route path="/top" element={<StorefrontTopLists />} />
            <Route path="/top/:slug" element={<StorefrontTopList />} />
            <Route path="/team" element={<StorefrontTeam />} />
            <Route path="/team/:slug" element={<StorefrontTeamMember />} />
            <Route path="/account" element={<StorefrontAccount />} />
            <Route path="/account/login" element={<StorefrontLogin />} />
            <Route path="/account/register" element={<StorefrontRegister />} />
            <Route path="/account/orders/:orderId" element={<StorefrontOrderDetail />} />
            <Route path="/review/:token" element={<StorefrontReview />} />
            {/* Legal aliases (preserve platform-style paths) */}
            <Route path="/legal/cgv" element={<StorefrontCGV />} />
            <Route path="/legal/mentions" element={<StorefrontMentions />} />
            <Route path="/legal/confidentialite" element={<StorefrontConfidentialite />} />
            <Route path="/legal/cookies" element={<StorefrontCookies />} />
            <Route path="/legal/livraison" element={<StorefrontLivraison />} />
            <Route path="/legal/retours" element={<StorefrontRetours />} />
            <Route path="/legal/mediation" element={<StorefrontMediation />} />

            {/* Legacy `/shop/:siteId/...` paths — generated by all current
                <Link> components in the codebase. Kept functional so internal
                navigation works without touching 86 files. */}
            <Route path="/shop/:siteId" element={<StorefrontHome />} />
            <Route path="/shop/:siteId/search" element={<StorefrontSearch />} />
            <Route path="/shop/:siteId/track" element={<StorefrontTrack />} />
            <Route path="/shop/:siteId/collections" element={<StorefrontCollections />} />
            <Route path="/shop/:siteId/collection/:slug" element={<StorefrontCollection />} />
            <Route path="/shop/:siteId/product/:productId" element={<StorefrontProduct />} />
            {/* Fix 2026-05-04 (Sprint 4 Fix 3) — route alias pluriel, harmonisée
                avec productPath(). Évite le 404 qui redirigeait vers home. */}
            <Route path="/shop/:siteId/products/:productId" element={<StorefrontProduct />} />
            <Route path="/shop/:siteId/cart" element={<StorefrontCart />} />
            <Route path="/shop/:siteId/checkout" element={<StorefrontCheckout />} />
            <Route path="/shop/:siteId/checkout/success" element={<StorefrontConfirmation />} />
            <Route path="/shop/:siteId/confirmation" element={<StorefrontConfirmation />} />
            <Route path="/shop/:siteId/about" element={<StorefrontAbout />} />
            <Route path="/shop/:siteId/faq" element={<StorefrontFAQ />} />
            <Route path="/shop/:siteId/contact" element={<StorefrontContact />} />
            <Route path="/shop/:siteId/cgv" element={<StorefrontCGV />} />
            <Route path="/shop/:siteId/mentions" element={<StorefrontMentions />} />
            <Route path="/shop/:siteId/confidentialite" element={<StorefrontConfidentialite />} />
            <Route path="/shop/:siteId/cookies" element={<StorefrontCookies />} />
            <Route path="/shop/:siteId/livraison" element={<StorefrontLivraison />} />
            <Route path="/shop/:siteId/retours" element={<StorefrontRetours />} />
            <Route path="/shop/:siteId/mediation" element={<StorefrontMediation />} />
            <Route path="/shop/:siteId/blog" element={<StorefrontBlog />} />
            <Route path="/shop/:siteId/blog/:slug" element={<StorefrontBlogPost />} />
            <Route path="/shop/:siteId/account" element={<StorefrontAccount />} />
            <Route path="/shop/:siteId/account/login" element={<StorefrontLogin />} />
            <Route path="/shop/:siteId/account/register" element={<StorefrontRegister />} />
            <Route path="/shop/:siteId/account/orders/:orderId" element={<StorefrontOrderDetail />} />
            <Route path="/shop/:siteId/review/:token" element={<StorefrontReview />} />

            {/* Fallback → home */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </CustomShopProvider>
    </AuthProvider>
  );
}

function PlatformApp() {
  return (
    <AuthProvider>
      <BrowserRouter>
        {/* Fix 3 — Reset scroll to top on every route change (storefront + cockpit) */}
        <ScrollToTop />
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/signup" element={<Signup />} />
          <Route path="/verify-email" element={<VerifyEmail />} />
          {/* Legacy URLs → 301 vers la nouvelle structure /legal/* (canonique) */}
          <Route path="/mentions-legales" element={<Navigate to="/legal/mentions" replace />} />
          <Route path="/cgu" element={<Navigate to="/legal/cgv" replace />} />
          <Route path="/confidentialite" element={<Navigate to="/legal/confidentialite" replace />} />
          <Route path="/cookies" element={<Navigate to="/legal/confidentialite" replace />} />
          {/* Pages légales plateforme Altiaro — exigées par Google Merchant Center MCA.
              Côté prod (altiaro.com / Cloudflare Pages), ces URLs sont servies AVANT
              le SPA via les fichiers statiques `frontend/public/legal/{slug}/index.html`.
              Côté preview / dev, le SPA React prend le relais avec ces composants. */}
          <Route path="/legal" element={<Navigate to="/legal/mentions" replace />} />
          <Route path="/legal/retours" element={<PlatformLegalRetours />} />
          <Route path="/legal/livraison" element={<PlatformLegalLivraison />} />
          <Route path="/legal/cgv" element={<PlatformLegalCgv />} />
          <Route path="/legal/confidentialite" element={<PlatformLegalConfidentialite />} />
          <Route path="/legal/mentions" element={<PlatformLegalMentions />} />
          <Route
            path="/"
            element={<HomeRoute />}
          />
          <Route
            path="/sites"
            element={
              <ProtectedRoute>
                <Sites />
              </ProtectedRoute>
            }
          />
          <Route
            path="/sites/new"
            element={
              <ProtectedRoute>
                <LaunchSite />
              </ProtectedRoute>
            }
          />
          <Route
            path="/sites/new-manual"
            element={
              <ProtectedRoute adminOnly>
                <NewSite />
              </ProtectedRoute>
            }
          />
          <Route
            path="/niches"
            element={
              <ProtectedRoute>
                <NicheEngine />
              </ProtectedRoute>
            }
          />
          <Route
            path="/niches/analysis/:id"
            element={
              <ProtectedRoute>
                <NicheAnalysisDetail />
              </ProtectedRoute>
            }
          />
          <Route
            path="/sites/:id"
            element={
              <ProtectedRoute>
                <SiteDetail />
              </ProtectedRoute>
            }
          />
          <Route
            path="/sites/:id/products"
            element={
              <ProtectedRoute>
                <SiteProducts />
              </ProtectedRoute>
            }
          />
          <Route
            path="/sites/:id/blog-posts"
            element={
              <ProtectedRoute>
                <SiteBlogPosts />
              </ProtectedRoute>
            }
          />
          <Route
            path="/sites/:id/seo"
            element={
              <ProtectedRoute>
                <SiteSEO />
              </ProtectedRoute>
            }
          />
          <Route
            path="/sites/:id/aliexpress/import"
            element={
              <ProtectedRoute>
                <SiteAliExpressImport />
              </ProtectedRoute>
            }
          />
          <Route
            path="/sites/:id/pricing"
            element={
              <ProtectedRoute>
                <SitePricing />
              </ProtectedRoute>
            }
          />
          <Route
            path="/sites/:id/forecast"
            element={
              <ProtectedRoute>
                <SiteForecast />
              </ProtectedRoute>
            }
          />
          <Route
            path="/sites/:id/upsells"
            element={
              <ProtectedRoute>
                <SiteUpsells />
              </ProtectedRoute>
            }
          />
          <Route
            path="/sites/:id/design"
            element={
              <ProtectedRoute>
                <SiteDesignRedirect />
              </ProtectedRoute>
            }
          />
          <Route
            path="/sites/:id/branding"
            element={
              <ProtectedRoute>
                <SiteBranding />
              </ProtectedRoute>
            }
          />
          {/* Phase 2.7.3 — Revue & régénération ciblée des images IA (cockpit étape 5) */}
          <Route
            path="/sites/:id/images-review"
            element={
              <ProtectedRoute>
                <ProductImagesReview />
              </ProtectedRoute>
            }
          />
          {/* Phase 3 — Étape 7 cockpit : traduction multi-langue */}
          <Route
            path="/sites/:id/translate"
            element={
              <ProtectedRoute>
                <SiteTranslate />
              </ProtectedRoute>
            }
          />
          <Route
            path="/sites/:siteId/integrations"
            element={
              <ProtectedRoute>
                <SiteIntegrations />
              </ProtectedRoute>
            }
          />
          <Route
            path="/sites/:id/pages"
            element={
              <ProtectedRoute>
                <SitePages />
              </ProtectedRoute>
            }
          />
          <Route
            path="/sites/:id/sourcing"
            element={
              <ProtectedRoute>
                <Sourcing />
              </ProtectedRoute>
            }
          />
          <Route
            path="/sites/:id/fulfillment"
            element={
              <ProtectedRoute>
                <SiteFulfillment />
              </ProtectedRoute>
            }
          />
          <Route
            path="/sites/:id/analytics"
            element={
              <ProtectedRoute>
                <SiteAnalytics />
              </ProtectedRoute>
            }
          />
          <Route
            path="/sites/:id/qa"
            element={
              <ProtectedRoute>
                <SiteQA />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/google/master-auth"
            element={
              <ProtectedRoute>
                <AdminGoogleMaster />
              </ProtectedRoute>
            }
          />
          {/* Alias rétrocompat : les anciens emails/redirects pointent encore
              vers /admin/google-master. On redirige proprement côté client. */}
          <Route
            path="/admin/google-master"
            element={<Navigate to="/admin/google/master-auth" replace />}
          />
          <Route
            path="/admin/integrations"
            element={
              <ProtectedRoute adminOnly>
                <AdminIntegrations />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/review"
            element={
              <ProtectedRoute adminOnly>
                <AdminReview />
              </ProtectedRoute>
            }
          />
          <Route
            path="/sites/:id/domains"
            element={
              <ProtectedRoute>
                <Domains />
              </ProtectedRoute>
            }
          />
          <Route
            path="/sites/:id/policy"
            element={
              <ProtectedRoute>
                <SiteSettings />
              </ProtectedRoute>
            }
          />
          {/* Storefront public pages — customer accounts + search */}
          <Route path="/shop/:siteId/account/register" element={<StorefrontRegister />} />
          <Route path="/shop/:siteId/account/login" element={<StorefrontLogin />} />
          <Route path="/shop/:siteId/account/orders/:orderId" element={<StorefrontOrderDetail />} />
          <Route path="/shop/:siteId/account" element={<StorefrontAccount />} />
          <Route path="/shop/:siteId/track" element={<StorefrontTrack />} />
          <Route path="/shop/:siteId/search" element={<StorefrontSearch />} />

          {/* Public Storefront (no auth) */}
          <Route path="/shop/:siteId" element={<StorefrontHome />} />
          <Route path="/shop/:siteId/collections" element={<StorefrontCollections />} />
          <Route path="/shop/:siteId/collection/:slug" element={<StorefrontCollection />} />
          <Route path="/shop/:siteId/product/:productId" element={<StorefrontProduct />} />
          {/* Fix 2026-05-04 (Sprint 4 Fix 3) — alias pluriel harmonisé. */}
          <Route path="/shop/:siteId/products/:productId" element={<StorefrontProduct />} />
          <Route path="/shop/:siteId/cart" element={<StorefrontCart />} />
          <Route path="/shop/:siteId/checkout" element={<StorefrontCheckout />} />
          <Route path="/shop/:siteId/confirmation" element={<StorefrontConfirmation />} />
          <Route path="/shop/:siteId/checkout/success" element={<StorefrontConfirmation />} />
          <Route path="/shop/:siteId/about" element={<StorefrontAbout />} />
          <Route path="/shop/:siteId/faq" element={<StorefrontFAQ />} />
          <Route path="/shop/:siteId/contact" element={<StorefrontContact />} />
          <Route path="/shop/:siteId/livraison" element={<StorefrontLivraison />} />
          <Route path="/shop/:siteId/retours" element={<StorefrontRetours />} />
          <Route path="/shop/:siteId/blog" element={<StorefrontBlog />} />
          <Route path="/shop/:siteId/blog/:slug" element={<StorefrontBlogPost />} />
          {/* Phase 3.3 Fix 1.3 + 1.4 — pages catalogue & accessoires dédiées */}
          <Route path="/shop/:siteId/products" element={<StorefrontAllProducts />} />
          <Route path="/shop/:siteId/accessories" element={<StorefrontAccessoriesPage />} />
          {/* Phase 3.2 chantier E — SEO Sprint 2/3 pages (buyer-guides,
              glossary, comparisons, top lists, team) — identiques à celles
              déjà montées dans CustomDomainApp, ajoutées ici pour que le
              menu storefront fonctionne aussi en mode preview. */}
          <Route path="/shop/:siteId/buyer-guides" element={<StorefrontBuyerGuides />} />
          <Route path="/shop/:siteId/buyer-guides/:slug" element={<StorefrontBuyerGuide />} />
          <Route path="/shop/:siteId/glossary" element={<StorefrontGlossary />} />
          <Route path="/shop/:siteId/glossary/:slug" element={<StorefrontGlossaryTerm />} />
          <Route path="/shop/:siteId/compare" element={<StorefrontComparisons />} />
          <Route path="/shop/:siteId/compare/:slug" element={<StorefrontCompare />} />
          <Route path="/shop/:siteId/top" element={<StorefrontTopLists />} />
          <Route path="/shop/:siteId/top/:slug" element={<StorefrontTopList />} />
          <Route path="/shop/:siteId/team" element={<StorefrontTeam />} />
          <Route path="/shop/:siteId/team/:slug" element={<StorefrontTeamMember />} />
          {/* Legal aliases (même pattern que CustomDomainApp) */}
          <Route path="/shop/:siteId/legal/cgv" element={<StorefrontCGV />} />
          <Route path="/shop/:siteId/legal/mentions" element={<StorefrontMentions />} />
          <Route path="/shop/:siteId/legal/confidentialite" element={<StorefrontConfidentialite />} />
          <Route path="/shop/:siteId/legal/cookies" element={<StorefrontCookies />} />
          <Route path="/shop/:siteId/legal/livraison" element={<StorefrontLivraison />} />
          <Route path="/shop/:siteId/legal/retours" element={<StorefrontRetours />} />
          <Route path="/shop/:siteId/legal/mediation" element={<StorefrontMediation />} />
          <Route path="/shop/:siteId/review/:token" element={<StorefrontReview />} />
          <Route path="/shop/:siteId/cgv" element={<StorefrontCGV />} />
          <Route path="/shop/:siteId/mentions" element={<StorefrontMentions />} />
          <Route path="/shop/:siteId/confidentialite" element={<StorefrontConfidentialite />} />
          <Route path="/shop/:siteId/cookies" element={<StorefrontCookies />} />
          <Route path="/shop/:siteId/mediation" element={<StorefrontMediation />} />
          <Route
            path="/scan"
            element={
              <ProtectedRoute>
                <QuickScan />
              </ProtectedRoute>
            }
          />
          <Route
            path="/validations"
            element={<Navigate to="/admin/review" replace />}
          />
          <Route
            path="/orders"
            element={
              <ProtectedRoute adminOnly>
                <Orders />
              </ProtectedRoute>
            }
          />
          <Route
            path="/empire"
            element={
              <ProtectedRoute adminOnly>
                <Empire />
              </ProtectedRoute>
            }
          />
          <Route
            path="/billing"
            element={
              <ProtectedRoute>
                <Billing />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/payouts"
            element={
              <ProtectedRoute adminOnly>
                <AdminPayouts />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/google-ads"
            element={
              <ProtectedRoute adminOnly>
                <GoogleAds />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/sites/:id/google-ads"
            element={
              <ProtectedRoute adminOnly>
                <AdminSiteGoogleAds />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/opportunities"
            element={
              <ProtectedRoute adminOnly>
                <Opportunities />
              </ProtectedRoute>
            }
          />
          <Route
            path="/finance"
            element={
              <ProtectedRoute>
                <Finance />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/finance"
            element={
              <ProtectedRoute adminOnly>
                <AdminFinances />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/legal-settings"
            element={
              <ProtectedRoute adminOnly>
                <AdminLegalSettings />
              </ProtectedRoute>
            }
          />
          {/* Ancienne URL `/finances` — redirige vers `/finance` (côté concepteur). Les admins cliquent sur "Finance (Admin)" dans la nav qui pointe directement sur /admin/finance. */}
          <Route
            path="/finances"
            element={<Navigate to="/finance" replace />}
          />
          <Route
            path="/users"
            element={
              <ProtectedRoute adminOnly>
                <Users />
              </ProtectedRoute>
            }
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
        <Toaster richColors closeButton position="top-right" />
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
