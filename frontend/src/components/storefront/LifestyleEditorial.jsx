import React from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowRight } from "@phosphor-icons/react";
import { pickLang, t } from "../../lib/i18n";
import { useShopSiteId } from "../../lib/shopSiteId";

/**
 * Lifestyle editorial — section full-bleed avec grande image + texte éditorial superposé à côté.
 * Casse le rythme de la page et donne une dimension "marque" forte.
 *
 * design.editorial = { image, eyebrow, title, body, cta_label, cta_href }
 */
export default function LifestyleEditorial({ editorial, lang = "fr", design }) {
  const siteId = useShopSiteId();
  const primary = design?.brand?.primary_color || "#B84B31";
  const fontHeading = design?.brand?.font_heading || "Fraunces";

  const e = editorial || {};
  const image = e.image || "https://images.unsplash.com/photo-1551847677-dc82d764e1eb?w=1400&auto=format&fit=crop";
  const eyebrow = pickLang(e.eyebrow, lang) || e.eyebrow || t(lang, "section_editorial");
  const title = pickLang(e.title, lang) || e.title || t(lang, "editorial_fallback_title");
  const body = pickLang(e.body, lang) || e.body || t(lang, "editorial_fallback_body");
  const ctaLabel = pickLang(e.cta_label, lang) || e.cta_label || t(lang, "editorial_fallback_cta");
  const ctaHref = e.cta_href || `/shop/${siteId}#story`;

  return (
    <section className="relative py-0 md:py-0 bg-white" data-testid="storefront-editorial">
      <div className="max-w-7xl mx-auto px-0 md:px-10 py-16 md:py-24">
        <div className="grid grid-cols-1 md:grid-cols-[1.2fr_1fr] items-stretch rounded-none md:rounded-3xl overflow-hidden">
          {/* Image large */}
          <div className="relative aspect-[4/3] md:aspect-auto md:min-h-[520px]">
            <img
              src={image}
              alt={title}
              loading="lazy"
              className="absolute inset-0 w-full h-full object-cover"
            />
          </div>
          {/* Texte éditorial */}
          <div
            className="px-8 md:px-14 py-14 md:py-16 flex flex-col justify-center"
            style={{ background: "#1C1917", color: "#F5F2EB" }}
          >
            <div className="text-[11px] uppercase tracking-[0.25em] mb-4" style={{ color: primary }}>
              {eyebrow}
            </div>
            <h2
              className="text-3xl md:text-4xl leading-snug mb-6"
              style={{ fontFamily: `${fontHeading}, serif`, color: "#fff" }}
            >
              {title}
            </h2>
            <p className="text-base md:text-[17px] leading-relaxed text-white/80 mb-8">
              {body}
            </p>
            <Link
              to={ctaHref}
              data-testid="editorial-cta"
              className="inline-flex items-center gap-2 h-12 px-6 rounded-full bg-white text-neutral-900 text-sm font-medium w-fit hover:opacity-90 transition"
            >
              {ctaLabel} <ArrowRight size={14} weight="bold" />
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}
