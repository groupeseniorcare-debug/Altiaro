import React from "react";
import { motion } from "framer-motion";
import { ArrowRight } from "@phosphor-icons/react";
import { designText, designAccents } from "./storefrontUtils";
import { sanitizeBrandText } from "../../lib/brandText";
import { t } from "../../lib/i18n";

/**
 * FinalCTA — MONOCHROME closing statement. Pure white canvas with gray
 * surrounding frame cards, oversized serif headline and a black CTA pill.
 */
export function FinalCTA({ design, lang }) {
  const { primary, accent, divider, textMuted, fontHeading } = designAccents(design);
  const brand = design?.brand || {};
  const brandLabel = sanitizeBrandText(brand.logo_text || brand.name || "", 40);
  const hook = sanitizeBrandText(
    designText(design, "final_cta.headline", lang)
      || brand.tagline
      || designText(design, "hero.title", lang)
      || t(lang, "shop_title"),
    120,
  );
  const eyebrow = designText(design, "final_cta.eyebrow", lang) || brandLabel || "Commencez maintenant";
  const kicker = designText(design, "final_cta.kicker", lang)
    || t(lang, "final_cta_subtitle");
  const heroCta = designText(design, "hero.cta_label", lang) || t(lang, "shop_now");

  return (
    <section
      className="py-28 md:py-40 px-6 bg-white overflow-hidden"
      data-testid="storefront-final-cta"
    >
      <div className="max-w-6xl mx-auto">
        {/* Outer gray frame card that hosts the CTA */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: 0.9 }}
          className="p-10 md:p-20 text-center"
          style={{ background: accent, borderRadius: "2px" }}
        >
          <div className="flex items-center justify-center gap-3 mb-8" aria-hidden="true">
            <span className="h-px w-10" style={{ background: primary }} />
            <span className="text-[11px] uppercase tracking-[0.45em]" style={{ color: primary }}>
              {eyebrow}
            </span>
            <span className="h-px w-10" style={{ background: primary }} />
          </div>

          <h2
            className="text-[40px] sm:text-[56px] md:text-[76px] lg:text-[88px] leading-[0.98] tracking-[-0.03em]"
            style={{ fontFamily: `"${fontHeading}", serif`, color: primary }}
          >
            {hook}
          </h2>

          <p className="text-[15px] md:text-[17px] mt-8 max-w-xl mx-auto leading-relaxed"
             style={{ color: textMuted }}>
            {kicker}
          </p>

          <a
            href="#products"
            data-testid="final-cta-button"
            className="group inline-flex items-center gap-3 mt-12 h-14 px-10 rounded-full text-white font-medium hover:gap-4 transition-all text-[14px] tracking-wide"
            style={{ background: primary }}
          >
            {heroCta}
            <ArrowRight size={15} weight="bold" className="transition-transform group-hover:translate-x-0.5" />
          </a>
        </motion.div>
      </div>
      <span className="hidden" style={{ borderTop: `1px solid ${divider}` }} />
    </section>
  );
}
