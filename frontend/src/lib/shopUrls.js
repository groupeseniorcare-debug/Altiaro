/**
 * URL helpers for canonical storefront URLs.
 *
 * The storefront has two URL formats :
 *   - `/shop/{siteId}/...`   → legacy / platform (used in Cockpit previews)
 *   - `/...`                 → custom domain (altea-home.com/products/slug)
 *
 * Canonical URLs always use the slug (never UUIDs) and are absolute when
 * possible (for <link rel="canonical">, OpenGraph, sitemap, schema.org).
 *
 * `isCustomDomainHost(host)` is shared with `lib/shopSiteId.jsx`.
 */

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export function isUuid(s) {
  return typeof s === "string" && UUID_RE.test(s);
}

/**
 * Given the current window location, decide whether we're on a custom
 * domain (an Approximated-routed shop hostname) or the Altiaro platform.
 */
export function isCustomDomainHost(host) {
  if (!host) return false;
  const h = String(host).toLowerCase();
  if (h === "localhost" || h === "127.0.0.1") return false;
  return !/(^|\.)(altiaro\.com|emergentagent\.com|emergent\.sh|conceptfactory\.fr)$/i.test(h);
}

function hostFor(site) {
  // Prefer `custom_domain` (the concepteur-facing domain) when verified.
  if (site?.custom_domain && site?.custom_domain_verified) return site.custom_domain;
  if (site?.custom_domain) return site.custom_domain;
  return site?.domain || null;
}

/**
 * Build a RELATIVE URL for a product — respects the current runtime
 * (custom domain → slug only; platform → `/shop/:siteId/product/:slug`).
 */
export function productPath(siteId, product) {
  const slug = product?.slug || product?.id;
  if (!slug) return "#";
  const host = typeof window !== "undefined" ? window.location.hostname : "";
  if (isCustomDomainHost(host)) return `/products/${slug}`;
  return `/shop/${siteId}/product/${slug}`;
}

/** Same for a collection page. */
export function collectionPath(siteId, slug) {
  if (!slug) return "#";
  const host = typeof window !== "undefined" ? window.location.hostname : "";
  if (isCustomDomainHost(host)) return `/collection/${slug}`;
  return `/shop/${siteId}/collection/${slug}`;
}

/** Shop home. */
export function shopPath(siteId) {
  const host = typeof window !== "undefined" ? window.location.hostname : "";
  if (isCustomDomainHost(host)) return "/";
  return `/shop/${siteId}`;
}

/**
 * ABSOLUTE canonical URL for a product. Used in <link rel="canonical">,
 * og:url, sitemap and schema.org `url`.
 */
export function productCanonicalUrl(site, product, lang /* eslint-disable-line no-unused-vars */) {
  const slug = product?.slug || product?.id;
  if (!slug) return "";
  const host = hostFor(site);
  if (host) return `https://${host}/products/${slug}`;
  // Fallback — platform preview
  const origin = typeof window !== "undefined" ? window.location.origin : "";
  return `${origin}/shop/${site?.id}/product/${slug}`;
}

export function shopCanonicalUrl(site) {
  const host = hostFor(site);
  if (host) return `https://${host}/`;
  const origin = typeof window !== "undefined" ? window.location.origin : "";
  return `${origin}/shop/${site?.id}`;
}

export function collectionCanonicalUrl(site, slug) {
  if (!slug) return "";
  const host = hostFor(site);
  if (host) return `https://${host}/collection/${slug}`;
  const origin = typeof window !== "undefined" ? window.location.origin : "";
  return `${origin}/shop/${site?.id}/collection/${slug}`;
}
