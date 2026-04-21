import { useEffect } from "react";

/**
 * SEOHead — injects/updates <title>, meta tags, canonical, hreflang, Open Graph
 * and JSON-LD Schema.org without needing react-helmet.
 *
 * Props :
 *   title, description, canonical, image
 *   langs: [{code, href}]  → generates <link rel="alternate" hreflang=...>
 *   schema: object | array of objects → injected as <script type="application/ld+json">
 *   type: "website" | "product" (default "website")
 */
export default function SEOHead({
  title,
  description,
  canonical,
  image,
  langs,
  schema,
  type = "website",
  siteName,
  locale = "fr_FR",
  keywords,
  robots = "index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1",
  noindex = false,
}) {
  useEffect(() => {
    if (title) document.title = title;

    const setMeta = (name, content, attr = "name") => {
      if (content === null || content === undefined || content === "") {
        const existing = document.head.querySelector(`meta[${attr}="${name}"]`);
        if (existing) existing.remove();
        return;
      }
      let el = document.head.querySelector(`meta[${attr}="${name}"]`);
      if (!el) {
        el = document.createElement("meta");
        el.setAttribute(attr, name);
        document.head.appendChild(el);
      }
      el.setAttribute("content", content);
    };

    setMeta("description", description);
    setMeta("keywords", keywords);
    setMeta("robots", noindex ? "noindex, nofollow" : robots);
    setMeta("og:title", title, "property");
    setMeta("og:description", description, "property");
    setMeta("og:type", type, "property");
    setMeta("og:locale", locale, "property");
    if (siteName) setMeta("og:site_name", siteName, "property");
    if (canonical) setMeta("og:url", canonical, "property");
    if (image) setMeta("og:image", image, "property");
    if (image) setMeta("og:image:alt", title || "", "property");
    setMeta("twitter:card", image ? "summary_large_image" : "summary");
    setMeta("twitter:title", title);
    setMeta("twitter:description", description);
    if (image) setMeta("twitter:image", image);

    // canonical
    if (canonical) {
      let link = document.head.querySelector('link[rel="canonical"]');
      if (!link) {
        link = document.createElement("link");
        link.setAttribute("rel", "canonical");
        document.head.appendChild(link);
      }
      link.setAttribute("href", canonical);
    }

    // hreflang — cleanup previous managed links first
    document.head
      .querySelectorAll('link[rel="alternate"][data-cf-seo]')
      .forEach((n) => n.remove());
    if (Array.isArray(langs)) {
      langs.forEach(({ code, href }) => {
        if (!code || !href) return;
        const l = document.createElement("link");
        l.setAttribute("rel", "alternate");
        l.setAttribute("hreflang", code);
        l.setAttribute("href", href);
        l.setAttribute("data-cf-seo", "1");
        document.head.appendChild(l);
      });
      // x-default → first one
      if (langs[0]) {
        const l = document.createElement("link");
        l.setAttribute("rel", "alternate");
        l.setAttribute("hreflang", "x-default");
        l.setAttribute("href", langs[0].href);
        l.setAttribute("data-cf-seo", "1");
        document.head.appendChild(l);
      }
    }

    // JSON-LD Schema.org — also cleanup previous managed
    document.head
      .querySelectorAll('script[type="application/ld+json"][data-cf-seo]')
      .forEach((n) => n.remove());
    if (schema) {
      const arr = Array.isArray(schema) ? schema : [schema];
      arr.forEach((obj) => {
        if (!obj) return;
        const s = document.createElement("script");
        s.setAttribute("type", "application/ld+json");
        s.setAttribute("data-cf-seo", "1");
        s.textContent = JSON.stringify(obj);
        document.head.appendChild(s);
      });
    }
  }, [title, description, canonical, image, type, locale, siteName, keywords, robots, noindex, JSON.stringify(langs), JSON.stringify(schema)]);

  return null;
}
