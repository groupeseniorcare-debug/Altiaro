import React from "react";
import { BrowserRouter, Routes, Route, Navigate, useParams } from "react-router-dom";
import { AuthProvider, useAuth } from "./lib/auth";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Sites from "./pages/Sites";
import NewSite from "./pages/NewSite";
import SiteDetail from "./pages/SiteDetail";
import Finance from "./pages/Finance";
import AdminFinances from "./pages/AdminFinances";
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
import Opportunities from "./pages/Opportunities";
import QuickScan from "./pages/QuickScan";
import LaunchSite from "./pages/LaunchSite";
import Landing from "./pages/Landing";
import Legal from "./pages/Legal";
import Signup from "./pages/Signup";
import VerifyEmail from "./pages/VerifyEmail";
import {
  StorefrontHome,
  StorefrontProduct,
  StorefrontCart,
  StorefrontCheckout,
  StorefrontConfirmation,
} from "./pages/Storefront";
import {
  StorefrontCollections,
  StorefrontCollection,
} from "./pages/StorefrontCollection";
import {
  StorefrontBlog,
  StorefrontBlogPost,
} from "./pages/StorefrontBlog";
import StorefrontReview from "./pages/StorefrontReview";
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
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/signup" element={<Signup />} />
          <Route path="/verify-email" element={<VerifyEmail />} />
          {/* Public platform pages — no auth required, crawlable by Google */}
          <Route path="/mentions-legales" element={<Legal slug="mentions-legales" />} />
          <Route path="/cgu" element={<Legal slug="cgu" />} />
          <Route path="/confidentialite" element={<Legal slug="confidentialite" />} />
          <Route path="/cookies" element={<Legal slug="cookies" />} />
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
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
