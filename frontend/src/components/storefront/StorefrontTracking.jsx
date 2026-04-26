import React, { useEffect, useRef, useState } from "react";
import { useLocation, useParams } from "react-router-dom";

/**
 * Injects GA4 + Google Ads conversion tracking into the storefront — AND
 * persists events internally to /api/public/sites/{id}/track (Chantier 7).
 *
 * Reads from `site.design.tracking = { ga4_measurement_id, gads_conversion_id, gads_conversion_label }`.
 *
 * Fired events : page_view (auto), product_view, add_to_cart, begin_checkout, purchase.
 * Call the helpers exposed on window.altiaroTrack from product / cart / checkout pages.
 *
 * Even when NO GA4/Ads IDs are configured, the helpers still:
 *  1. Push events to `window.dataLayer` (GTM users)
 *  2. Send events to Altiaro's internal analytics endpoint (for the Dashboard)
 */

const SESSION_KEY = "altiaro.sess";
const SESSION_TTL_MIN = 30;

function getOrCreateSession() {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(SESSION_KEY);
    const now = Date.now();
    if (raw) {
      const parsed = JSON.parse(raw);
      if (parsed?.id && parsed?.updated_at && now - parsed.updated_at < SESSION_TTL_MIN * 60 * 1000) {
        parsed.updated_at = now;
        window.localStorage.setItem(SESSION_KEY, JSON.stringify(parsed));
        return parsed.id;
      }
    }
    const fresh = {
      id: `s-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`,
      updated_at: now,
    };
    window.localStorage.setItem(SESSION_KEY, JSON.stringify(fresh));
    return fresh.id;
  } catch (_) {
    // LS unavailable (privacy mode) → ephemeral session
    return `eph-${Math.random().toString(36).slice(2, 12)}`;
  }
}

function postEvent(siteId, payload) {
  if (!siteId || !payload?.event) return;
  const base = process.env.REACT_APP_BACKEND_URL || "";
  const url = `${base}/api/public/sites/${siteId}/track`;
  const body = JSON.stringify({
    session_id: getOrCreateSession(),
    lang: (document?.documentElement?.lang || "fr").slice(0, 2),
    path: window.location?.pathname || "",
    referrer: document?.referrer || "",
    ...payload,
  });
  try {
    // Prefer sendBeacon for "unload" reliability; fallback to fetch keepalive
    if (navigator?.sendBeacon) {
      const blob = new Blob([body], { type: "application/json" });
      if (navigator.sendBeacon(url, blob)) return;
    }
    fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body,
      keepalive: true,
      mode: "cors",
      credentials: "omit",
    }).catch(() => {});
  } catch (_) { /* no-op — tracking is best-effort */ }
}

export default function StorefrontTracking({ site }) {
  const tracking = site?.design?.tracking || {};
  const ga4Id = tracking.ga4_measurement_id || "";
  const gadsId = tracking.gads_conversion_id || "";
  const gadsLabel = tracking.gads_conversion_label || "";
  const siteId = site?.id;
  const location = useLocation();
  const params = useParams();
  const lastPathRef = useRef(null);

  // Bloc 1 sous-chantier 3 — RGPD consent gate.
  // We refuse to load gtag/Google Ads pixel until the user has actively
  // accepted the "marketing" category through <CookieConsentBanner>.
  // localStorage key is the source of truth ; the banner also dispatches a
  // window event "altiaro:consent-updated" so this component re-evaluates
  // without a full page reload.
  const [marketingConsent, setMarketingConsent] = useState(() => {
    try {
      const raw = localStorage.getItem("altiaro_consent_v1");
      if (!raw) return false;
      return Boolean(JSON.parse(raw)?.marketing);
    } catch {
      return false;
    }
  });
  useEffect(() => {
    const onUpdate = () => {
      try {
        const raw = localStorage.getItem("altiaro_consent_v1");
        setMarketingConsent(Boolean(raw && JSON.parse(raw)?.marketing));
      } catch {
        setMarketingConsent(false);
      }
    };
    window.addEventListener("altiaro:consent-updated", onUpdate);
    return () => window.removeEventListener("altiaro:consent-updated", onUpdate);
  }, []);

  // ---- 1. gtag bootstrap (consent-gated) ---- //
  useEffect(() => {
    if (window.__altiaroTrackingLoaded) return;
    if (!marketingConsent) return;  // ⚠️ no-op until user opts in
    window.__altiaroTrackingLoaded = true;

    window.dataLayer = window.dataLayer || [];
    function gtag() { window.dataLayer.push(arguments); }
    window.gtag = gtag;
    gtag("js", new Date());

    const firstTagId = ga4Id || gadsId;
    if (firstTagId) {
      const s = document.createElement("script");
      s.async = true;
      s.src = `https://www.googletagmanager.com/gtag/js?id=${firstTagId}`;
      document.head.appendChild(s);
      if (ga4Id) gtag("config", ga4Id, { send_page_view: true });
      if (gadsId) gtag("config", gadsId);
    }

    // ---- 2. Public helper API ---- //
    // Each helper does TWO things : (a) push to gtag/dataLayer, (b) POST to
    // /api/public/sites/{id}/track so the Altiaro dashboard can rebuild the
    // funnel without depending on GA4 API quotas.
    window.altiaroTrack = {
      viewItem: (product, lang = "fr") => {
        try {
          gtag("event", "view_item", {
            currency: product.currency || "EUR",
            value: Number(product.price || 0),
            items: [{
              item_id: product.id,
              item_name: (product.name?.[lang] || product.name || "").toString(),
              price: Number(product.price || 0),
              quantity: 1,
            }],
          });
        } catch (_) {}
        postEvent(siteId, {
          event: "product_view",
          product_id: product.id,
          value: Number(product.price || 0) || null,
          currency: product.currency || "EUR",
          lang,
        });
      },
      addToCart: (product, quantity = 1, lang = "fr") => {
        try {
          gtag("event", "add_to_cart", {
            currency: product.currency || "EUR",
            value: Number(product.price || 0) * quantity,
            items: [{
              item_id: product.id,
              item_name: (product.name?.[lang] || product.name || "").toString(),
              price: Number(product.price || 0),
              quantity,
            }],
          });
        } catch (_) {}
        postEvent(siteId, {
          event: "add_to_cart",
          product_id: product.id,
          value: Number(product.price || 0) * quantity || null,
          currency: product.currency || "EUR",
          lang,
          meta: { quantity },
        });
      },
      upsellImpulse: (product, discountPct = 20, lang = "fr") => {
        try {
          const basePrice = Number(product.price || 0);
          const discounted = Math.round(basePrice * (1 - discountPct / 100) * 100) / 100;
          const itemName = (product.name?.[lang] || product.name || "").toString();
          gtag("event", "add_to_cart", {
            currency: product.currency || "EUR",
            value: discounted,
            items: [{
              item_id: product.id,
              item_name: itemName,
              price: discounted,
              discount: Math.round((basePrice - discounted) * 100) / 100,
              item_category: "upsell_impulse",
              quantity: 1,
            }],
          });
          gtag("event", "upsell_impulse", {
            currency: product.currency || "EUR",
            value: discounted,
            discount_pct: discountPct,
            item_id: product.id,
            item_name: itemName,
          });
        } catch (_) {}
        const base = Number(product.price || 0);
        const discounted = Math.round(base * (1 - discountPct / 100) * 100) / 100;
        postEvent(siteId, {
          event: "add_to_cart",
          product_id: product.id,
          value: discounted,
          currency: product.currency || "EUR",
          lang,
          meta: { upsell_impulse: true, discount_pct: discountPct },
        });
      },
      beginCheckout: (items, total, currencyOrLang = "EUR") => {
        // Backward compat: original signature was (items, total, lang) in some
        // callsites — detect a 2-letter code as lang, otherwise currency.
        const currency =
          typeof currencyOrLang === "string" && currencyOrLang.length === 3
            ? currencyOrLang
            : "EUR";
        try {
          gtag("event", "begin_checkout", {
            currency, value: Number(total || 0),
            items: (items || []).map(it => ({
              item_id: it.product_id || it.id,
              item_name: it.name || "",
              price: Number(it.unit_price || it.price || 0),
              quantity: it.quantity || 1,
            })),
          });
        } catch (_) {}
        postEvent(siteId, {
          event: "begin_checkout",
          value: Number(total || 0) || null,
          currency,
          meta: { items_count: (items || []).length },
        });
      },
      purchase: (order) => {
        try {
          gtag("event", "purchase", {
            transaction_id: order.order_number || order.id,
            currency: order.currency || "EUR",
            value: Number(order.total || 0),
            tax: Number(order.tax || 0),
            shipping: Number(order.shipping_cost || 0),
            items: (order.items || []).map(it => ({
              item_id: it.product_id,
              item_name: it.name || "",
              price: Number(it.unit_price || it.price || 0),
              quantity: it.quantity || 1,
            })),
          });
          if (gadsId && gadsLabel) {
            gtag("event", "conversion", {
              send_to: `${gadsId}/${gadsLabel}`,
              value: Number(order.total || 0),
              currency: order.currency || "EUR",
              transaction_id: order.order_number || order.id,
            });
          }
        } catch (_) {}
        postEvent(siteId, {
          event: "purchase",
          value: Number(order.total || 0) || null,
          currency: order.currency || "EUR",
          meta: {
            order_id: order.id,
            order_number: order.order_number,
            items_count: (order.items || []).length,
          },
        });
      },
    };
  }, [ga4Id, gadsId, gadsLabel, siteId]);

  // ---- 3. Auto page_view sur chaque navigation (react-router) ---- //
  useEffect(() => {
    if (!siteId) return;
    const path = location.pathname + location.search;
    if (lastPathRef.current === path) return;
    lastPathRef.current = path;
    postEvent(siteId, {
      event: "page_view",
      path: location.pathname,
      country: (params?.country || "").toUpperCase() || null,
    });
  }, [location.pathname, location.search, siteId, params]);

  return null;
}
