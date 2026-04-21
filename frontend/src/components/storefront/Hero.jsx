import React from "react";
import { ArrowRight, ShieldCheck } from "@phosphor-icons/react";
import { designText } from "./storefrontUtils";
import { t } from "../../lib/i18n";

export function Hero({ site, design, lang }) {
  const heroTitle = designText(design, "hero.title", lang) || t(lang, "shop_title");
  const heroSub = designText(design, "hero.subtitle", lang) || t(lang, "shop_subtitle");
  const heroCta = designText(design, "hero.cta_label", lang);
  const heroTrust = designText(design, "hero.trust_line", lang);
  const primary = design?.brand?.primary_color || "#B84B31";
  const fontHeading = design?.brand?.font_heading || "Fraunces";
  const bg = design?.brand?.background_color || "#FDFBF7";
  const textColor = design?.brand?.text_color || "#1C1917";

  return (
    <section
      className="relative overflow-hidden"
      style={{ background: bg, color: textColor }}
    >
      <div className="max-w-6xl mx-auto px-6 md:px-10 pt-20 md:pt-28 pb-16 md:pb-24 text-center">
        {(design?.brand?.tagline || site?.niche) && (
          <div
            className="text-[11px] uppercase tracking-[0.25em] mb-6 font-medium"
            style={{ color: primary }}
          >
            {design?.brand?.tagline || site?.niche}
          </div>
        )}
        <h1
          className="text-[40px] md:text-[64px] lg:text-[80px] font-semibold leading-[1.02] tracking-[-0.02em] max-w-4xl mx-auto"
          style={{ fontFamily: `"${fontHeading}", Georgia, serif` }}
        >
          {heroTitle}
        </h1>
        {heroSub && (
          <p
            className="text-lg md:text-xl mt-6 max-w-2xl mx-auto leading-relaxed"
            style={{ color: `${textColor}cc` }}
          >
            {heroSub}
          </p>
        )}
        <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-3">
          <a
            href="#products"
            data-testid="hero-cta"
            className="inline-flex items-center gap-2 h-14 px-8 rounded-full text-white font-medium transition-all hover:opacity-90 active:scale-[0.98] text-[15px]"
            style={{ background: primary }}
          >
            {heroCta || t(lang, "shop_now")}
            <ArrowRight size={16} weight="bold" />
          </a>
          {heroTrust && (
            <div
              className="inline-flex items-center gap-1.5 text-sm"
              style={{ color: `${textColor}99` }}
            >
              <ShieldCheck size={14} weight="fill" /> {heroTrust}
            </div>
          )}
        </div>
      </div>
      <div
        className="absolute inset-x-0 bottom-0 h-32 pointer-events-none"
        style={{ background: `linear-gradient(to bottom, transparent, ${bg})` }}
      />
    </section>
  );
}
