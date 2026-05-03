// Sprint 4 — Picture/WebP/AVIF helper.
// Rend <picture> avec sources WebP + AVIF via query param ?format=...&w=...
// qui sera servé par le backend FastAPI (/api/uploads/* supports conversion
// à la volée). En production sans conversion côté serveur, le navigateur
// retombe sur le fallback <img src> (original).

const DEFAULT_WIDTHS = [480, 1024, 1920];

function isAbsolute(url) {
  return typeof url === "string" && /^(https?:)?\/\//.test(url);
}

function apiRoot() {
  try {
    return (
      (typeof process !== "undefined" && process.env && process.env.REACT_APP_BACKEND_URL) ||
      (typeof window !== "undefined" && window.__REACT_APP_BACKEND_URL__) ||
      ""
    );
  } catch (_) {
    return "";
  }
}

function buildVariant(url, width, format) {
  if (!url) return "";
  // Only rewrite our own uploads; leave external CDN URLs intact.
  if (isAbsolute(url) && url.indexOf("/api/uploads/") === -1) return url;
  const sep = url.indexOf("?") >= 0 ? "&" : "?";
  const base = isAbsolute(url) ? url : apiRoot().replace(/\/$/, "") + url;
  return `${base}${sep}w=${width}${format ? `&format=${format}` : ""}`;
}

/** Returns a srcSet string for a given format ("webp"|"avif"|""). */
export function buildSrcSet(url, format = "", widths = DEFAULT_WIDTHS) {
  return widths.map((w) => `${buildVariant(url, w, format)} ${w}w`).join(", ");
}

/**
 * <PictureImg> — React component to render <picture> with WebP/AVIF sources +
 * a <img> fallback. Accepts an `alt` prop (required by SEO) and a `sizes` prop.
 */
export function PictureImg({
  src,
  alt = "",
  className = "",
  style,
  sizes = "(max-width: 768px) 100vw, 50vw",
  widths = DEFAULT_WIDTHS,
  loading = "lazy",
  decoding = "async",
  draggable,
  onClick,
}) {
  if (!src) return null;
  // Do not try to resize/transform external images (Shopify CDN, AliExpress…).
  const external = isAbsolute(src) && src.indexOf("/api/uploads/") === -1;
  if (external) {
    return (
      // eslint-disable-next-line jsx-a11y/alt-text
      <img
        src={src}
        alt={alt}
        className={className}
        style={style}
        loading={loading}
        decoding={decoding}
        draggable={draggable}
        onClick={onClick}
      />
    );
  }
  return (
    <picture>
      <source type="image/avif" srcSet={buildSrcSet(src, "avif", widths)} sizes={sizes} />
      <source type="image/webp" srcSet={buildSrcSet(src, "webp", widths)} sizes={sizes} />
      {/* Fallback original */}
      {/* eslint-disable-next-line jsx-a11y/alt-text */}
      <img
        src={src}
        alt={alt}
        className={className}
        style={style}
        loading={loading}
        decoding={decoding}
        draggable={draggable}
        onClick={onClick}
      />
    </picture>
  );
}

export default PictureImg;
