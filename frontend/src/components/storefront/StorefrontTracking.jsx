import React, { useEffect } from "react";

/**
 * Injects GA4 + Google Ads conversion tracking into the storefront.
 * Reads from `site.design.tracking = { ga4_measurement_id, gads_conversion_id, gads_conversion_label }`.
 *
 * Fired events : page_view (auto), view_item, add_to_cart, begin_checkout, purchase.
 * Call the helpers exposed on window.altiaroTrack from product / cart / checkout pages.
 */
export default function StorefrontTracking({ site }) {
  const tracking = site?.design?.tracking || {};
  const ga4Id = tracking.ga4_measurement_id || "";
  const gadsId = tracking.gads_conversion_id || "";
  const gadsLabel = tracking.gads_conversion_label || "";

  useEffect(() => {
    if (!ga4Id && !gadsId) return;
    if (window.__altiaroTrackingLoaded) return;
    window.__altiaroTrackingLoaded = true;

    const firstTagId = ga4Id || gadsId;

    // Load gtag.js
    const s = document.createElement("script");
    s.async = true;
    s.src = `https://www.googletagmanager.com/gtag/js?id=${firstTagId}`;
    document.head.appendChild(s);

    window.dataLayer = window.dataLayer || [];
    function gtag() { window.dataLayer.push(arguments); }
    window.gtag = gtag;
    gtag("js", new Date());

    if (ga4Id) gtag("config", ga4Id, { send_page_view: true });
    if (gadsId) gtag("config", gadsId);

    // Public helper exposed to the rest of the storefront
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
          // Google Ads conversion
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
