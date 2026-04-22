import React, { useEffect } from "react";

/**
 * Injects GA4 + Google Ads conversion tracking into the storefront.
 * Reads from `site.design.tracking = { ga4_measurement_id, gads_conversion_id, gads_conversion_label }`.
 *
 * Fired events : page_view (auto), view_item, add_to_cart, begin_checkout, purchase.
 * Call the helpers exposed on window.altiaroTrack from product / cart / checkout pages.
 *
 * Even when NO GA4/Ads IDs are configured, the helpers still push events to
 * `window.dataLayer` so Google Tag Manager users can pick them up.
 */
export default function StorefrontTracking({ site }) {
  const tracking = site?.design?.tracking || {};
  const ga4Id = tracking.ga4_measurement_id || "";
  const gadsId = tracking.gads_conversion_id || "";
  const gadsLabel = tracking.gads_conversion_label || "";

  useEffect(() => {
    if (window.__altiaroTrackingLoaded) return;
    window.__altiaroTrackingLoaded = true;

    // Always initialize the dataLayer + gtag stub so events can queue even
    // before gtag.js is loaded.
    window.dataLayer = window.dataLayer || [];
    function gtag() { window.dataLayer.push(arguments); }
    window.gtag = gtag;
    gtag("js", new Date());

    // Load gtag.js only if at least one ID is configured (saves ~40 KB otherwise).
    const firstTagId = ga4Id || gadsId;
    if (firstTagId) {
      const s = document.createElement("script");
      s.async = true;
      s.src = `https://www.googletagmanager.com/gtag/js?id=${firstTagId}`;
      document.head.appendChild(s);
      if (ga4Id) gtag("config", ga4Id, { send_page_view: true });
      if (gadsId) gtag("config", gadsId);
    }

    // Public helper exposed to the rest of the storefront. Always defined so
    // product/cart/checkout calls don't need to null-check; events always push
    // to dataLayer (GTM compatible) even without GA4/Ads IDs.
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
        } catch (e) { /* no-op */ }
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
        } catch (e) { /* no-op */ }
      },
      /**
       * Impulse-cart upsell click ("Ajouter avec -X%" inside the cart drawer).
       * Fires BOTH `add_to_cart` (with discounted value) and a custom
       * `upsell_impulse` event so marketers can segment high-intent carts.
       */
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
        } catch (e) { /* no-op */ }
      },
      beginCheckout: (items, total, currency = "EUR") => {
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
        } catch (e) { /* no-op */ }
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
          // Google Ads conversion (only if Ads conversion fully configured)
          if (gadsId && gadsLabel) {
            gtag("event", "conversion", {
              send_to: `${gadsId}/${gadsLabel}`,
              value: Number(order.total || 0),
              currency: order.currency || "EUR",
              transaction_id: order.order_number || order.id,
            });
          }
        } catch (e) { /* no-op */ }
      },
    };
  }, [ga4Id, gadsId, gadsLabel]);

  return null;
}
