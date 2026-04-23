import React from "react";
import { ArrowRight } from "@phosphor-icons/react";
import { designText, designAccents } from "./storefrontUtils";
import { sanitizeBrandText } from "../../lib/brandText";
import { t } from "../../lib/i18n";

/**
 * FinalCTA — editorial, full-bleed, deep-contrast call-to-action. Sits on the deep
 * neutral background defined at the storefront root (GRAY_SECTIONS / DARK_SECTIONS
 * wrapper) and uses an oversized serif hero line + a subtle hairline CTA.
 */
export function FinalCTA({ design, lang }) {
  const { primary, fontHeading } = designAccents(design);
  const brand = design?.brand || {};
  const brandLabel = sanitizeBrandText(brand.logo_text || brand.name || "", 40);
  const hook = sanitizeBrandText(
    brand.tagline ||
      designText(design, "final_cta.headline", lang) ||
      designText(design, "hero.title", lang) ||
      t(lang, "shop_title"),
    120,
  );
  const eyebrow = designText(design, "final_cta.eyebrow", lang) || brandLabel || "Prêt à vous sentir mieux ?";
  const kicker = designText(design, "final_cta.kicker", lang)
    || "Parcourez notre sélection. Livraison offerte, retour gratuit sous 14 jours.";
  const heroCta = designText(design, "hero.cta_label", lang) || t(lang, "shop_now");

  return (
    <section
      className="relative overflow-hidden py-24 md:py-36 px-6"
      data-testid="storefront-final-cta"
    >
      {/* Ambient accent glow derived from the brand primary — keeps the palette on-brand
          without re-tinting the whole section. */}
      <div
        className="pointer-events-none absolute inset-0 opacity-[0.18] blur-3xl"
        style={{
          background: `radial-gradient(circle at 30% 20%, ${primary}, transparent 55%), radial-gradient(circle at 70% 80%, ${primary}, transparent 55%)`,
        }}
      />
      <div className="relative max-w-4xl mx-auto text-center">
        <div className="text-[11px] uppercase tracking-[0.4em] text-neutral-500 mb-6">
          {eyebrow}
        </div>
        <h2
          className="text-4xl md:text-6xl lg:text-7xl leading-[1.05] tracking-tight text-neutral-900"
          style={{ fontFamily: `"${fontHeading}", serif` }}
        >
          {hook}
        </h2>
        <p className="text-base md:text-lg text-neutral-600 mt-6 max-w-xl mx-auto leading-relaxed">
          {kicker}
        </p>
        <a
          href="#products"
          data-testid="final-cta-button"
          className="group inline-flex items-center gap-3 mt-10 h-14 px-9 rounded-full bg-neutral-900 text-white font-medium transition-all hover:bg-neutral-800 hover:gap-4 text-[15px]"
        >
          {heroCta}
          <ArrowRight size={16} weight="bold" className="transition-transform group-hover:translate-x-0.5" />
        </a>
      </div>
    </section>
  );
}
