import React from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./lib/auth";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Sites from "./pages/Sites";
import NewSite from "./pages/NewSite";
import SiteDetail from "./pages/SiteDetail";
import Validations from "./pages/Validations";
import Finances from "./pages/Finance";
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
  StorefrontLivraison,
  StorefrontRetours,
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
            element={
              <ProtectedRoute adminOnly>
                <Validations />
              </ProtectedRoute>
            }
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
            path="/finances"
            element={
              <ProtectedRoute>
                <Finances />
              </ProtectedRoute>
            }
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
