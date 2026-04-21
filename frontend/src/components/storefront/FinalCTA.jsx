import React from "react";
import { ArrowRight } from "@phosphor-icons/react";
import { designText, designAccents } from "./storefrontUtils";
import { t } from "../../lib/i18n";

export function FinalCTA({ design, lang }) {
  const { primary, fontHeading } = designAccents(design);
  const heroTitle = designText(design, "hero.title", lang) || t(lang, "shop_title");
  const heroCta = designText(design, "hero.cta_label", lang);

  return (
    <section
      className="py-20 md:py-28 text-center"
      style={{ background: primary, color: "#ffffff" }}
    >
      <div className="max-w-3xl mx-auto px-6">
        <h2
          className="text-3xl md:text-5xl font-semibold mb-6"
          style={{ fontFamily: `"${fontHeading}", serif` }}
        >
          {design?.brand?.tagline || heroTitle}
        </h2>
        <a
          href="#products"
          className="inline-flex items-center gap-2 h-14 px-8 rounded-full bg-white font-medium transition-all hover:scale-[1.02] active:scale-[0.98] text-[15px]"
          style={{ color: primary }}
        >
          {heroCta || t(lang, "shop_now")} <ArrowRight size={16} weight="bold" />
        </a>
      </div>
    </section>
  );
}
