import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import { api } from "./api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null); // null=loading, false=not auth, object=auth
  const [error, setError] = useState("");

  const checkSession = useCallback(async () => {
    // Skip auth probe on public storefront routes to avoid noisy 401s
    if (typeof window !== "undefined" && window.location.pathname.startsWith("/shop/")) {
      setUser(false);
      return;
    }
    try {
      const { data } = await api.get("/auth/session");
      setUser(data?.user || false);
    } catch {
      setUser(false);
    }
  }, []);

  useEffect(() => {
    checkSession();
  }, [checkSession]);

  const login = async (email, password) => {
    setError("");
    try {
      const { data } = await api.post("/auth/login", { email, password });
      setUser(data);
      return { ok: true };
    } catch (e) {
      const detail = e.response?.data?.detail;
      // Pending email verification → redirect signal for the caller
      if (detail && typeof detail === "object" && detail.code === "pending_email_verification") {
        return { ok: false, code: "pending_email_verification", email: detail.email || email };
      }
      const msg = typeof detail === "string" ? detail : "Erreur de connexion";
      setError(msg);
      return { ok: false, error: msg };
    }
  };

  const logout = async () => {
    try {
      await api.post("/auth/logout");
    } catch {}
    setUser(false);
  };

  return (
    <AuthContext.Provider value={{ user, setUser, login, logout, error, setError, checkSession }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be inside AuthProvider");
  return ctx;
};
