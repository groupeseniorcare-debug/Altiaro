/**
 * Custom-domain storefront resolution.
 *
 * Le storefront a historiquement été conçu avec un prefix d'URL
 * `/shop/:siteId/...` où `:siteId` vient de `useParams()`.
 *
 * Pour les custom domains (altea-home.com, …) on veut que l'URL reste propre
 * (`altea-home.com/`, `altea-home.com/products/xxx`) sans ce prefix technique.
 * Solution : on résout le siteId via l'API
 * `/api/public/domains/resolve?host=<hostname>` au tout premier render d'App,
 * on le stocke dans un Context, et on expose `useShopSiteId()` qui retombe
 * sur ce Context si `useParams().siteId` n'est pas présent.
 *
 * Résultat : les composants storefront (~20 fichiers) passent simplement de
 * `const { siteId } = useParams();` à `const siteId = useShopSiteId();` —
 * même API, retours identiques sur les routes classiques /shop/:siteId/...
 */
import React, { createContext, useContext, useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";

const BACKEND_URL =
  (typeof process !== "undefined" && process.env && process.env.REACT_APP_BACKEND_URL) ||
  "";

const PLATFORM_HOST_RE =
  /(^|\.)(altiaro\.com|emergentagent\.com|emergent\.sh|conceptfactory\.fr|localhost)$/i;

const CustomShopContext = createContext(null);

/** True if we think the current hostname is a custom domain (not platform). */
export function hostnameIsCustomDomain(host) {
  if (!host) return false;
  const h = String(host).toLowerCase();
  if (h === "localhost" || h === "127.0.0.1") return false;
  return !PLATFORM_HOST_RE.test(h);
}

/**
 * Top-level React hook used by `App.js` to decide which routing mode to use.
 * Returns one of :
 *   - { mode: "loading" }                 → splash
 *   - { mode: "platform" }                → render the normal <Routes> tree
 *   - { mode: "custom-domain", siteId }   → render the storefront-only <Routes>
 */
export function useCustomDomainBootstrap() {
  const [state, setState] = useState(() => ({ mode: "loading" }));

  useEffect(() => {
    let cancelled = false;
    const host =
      typeof window !== "undefined" ? window.location.hostname : "";
    if (!hostnameIsCustomDomain(host)) {
      setState({ mode: "platform" });
      return () => {};
    }
    // Custom domain candidate → ask backend to resolve.
    const url = `${BACKEND_URL}/api/public/domains/resolve?host=${encodeURIComponent(host)}`;
    fetch(url, { credentials: "omit" })
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (cancelled) return;
        const siteId = data && data.site_id;
        if (siteId) {
          setState({
            mode: "custom-domain",
            siteId,
            siteName: data.site_name || "",
            host,
          });
        } else {
          // Unknown custom hostname — fallback to platform (will likely show
          // a 404 or platform landing; safer than crashing).
          setState({ mode: "platform" });
        }
      })
      .catch(() => {
        if (!cancelled) setState({ mode: "platform" });
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return state;
}

export function CustomShopProvider({ siteId, host, siteName, children }) {
  const value = useMemo(() => ({ siteId, host, siteName }), [siteId, host, siteName]);
  return <CustomShopContext.Provider value={value}>{children}</CustomShopContext.Provider>;
}

/**
 * Primary consumer hook. Drop-in replacement for
 * `const { siteId } = useParams();` inside storefront components.
 * Returns `null` when no siteId can be resolved.
 */
export function useShopSiteId() {
  const params = useParams();
  const ctx = useContext(CustomShopContext);
  return params?.siteId || ctx?.siteId || null;
}

export function useShopDomainContext() {
  return useContext(CustomShopContext);
}
