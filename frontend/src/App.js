import React from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./lib/auth";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Sites from "./pages/Sites";
import NewSite from "./pages/NewSite";
import SiteDetail from "./pages/SiteDetail";
import Validations from "./pages/Validations";
import Finances from "./pages/Finances";
import Users from "./pages/Users";
import NicheEngine from "./pages/NicheEngine";
import NicheDetail from "./pages/NicheDetail";
import SiteProducts from "./pages/SiteProducts";
import {
  StorefrontHome,
  StorefrontProduct,
  StorefrontCart,
  StorefrontCheckout,
  StorefrontConfirmation,
} from "./pages/Storefront";

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

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            }
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
            path="/niches/:slug"
            element={
              <ProtectedRoute>
                <NicheDetail />
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

          {/* Public Storefront (no auth) */}
          <Route path="/shop/:siteId" element={<StorefrontHome />} />
          <Route path="/shop/:siteId/product/:productId" element={<StorefrontProduct />} />
          <Route path="/shop/:siteId/cart" element={<StorefrontCart />} />
          <Route path="/shop/:siteId/checkout" element={<StorefrontCheckout />} />
          <Route path="/shop/:siteId/confirmation" element={<StorefrontConfirmation />} />
          <Route
            path="/validations"
            element={
              <ProtectedRoute adminOnly>
                <Validations />
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
