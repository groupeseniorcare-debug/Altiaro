import React from "react";
import { motion } from "framer-motion";
import { designAccents } from "./storefrontUtils";
import { sanitizeBrandText } from "../../lib/brandText";
import { t, pickLang } from "../../lib/i18n";

/**
 * Manifesto — MONOCHROME editorial statement. White canvas, near-black ink.
 * Big serif headline centered, then a row of three gray cards that distill
 * the promise into concrete pillars.
 */
export default function Manifesto({ design, lang = "fr" }) {
  const { primary, accent, divider, textMuted, fontHeading } = designAccents(design);
  const brand = design?.brand || {};
  const brandName = sanitizeBrandText(brand.logo_text || brand.name || "", 40);
  const m = design?.manifesto || {};
  const eyebrow = sanitizeBrandText(pickLang(m.eyebrow, lang) || t(lang, "section_manifesto"), 40);
  const headline = sanitizeBrandText(
    pickLang(m.headline, lang)
      || pickLang(brand.tagline, lang)
      || t(lang, "manifesto_headline_default"),
    240,
  );
  const kicker = pickLang(m.kicker, lang)
    || t(lang, "manifesto_kicker_default").replace("{brand}", brandName || t(lang, "manifesto_fallback_brand"));

  // Three pillars — fall back to localized defaults if none were generated
  const defaultPillars = [
    { title: t(lang, "manifesto_card_1_title"), body: t(lang, "manifesto_card_1_body") },
    { title: t(lang, "manifesto_card_2_title"), body: t(lang, "manifesto_card_2_body") },
    { title: t(lang, "manifesto_card_3_title"), body: t(lang, "manifesto_card_3_body") },
  ];
  const pillars = Array.isArray(m.pillars) && m.pillars.length === 3 ? m.pillars : defaultPillars;

  return (
    <section
      className="relative py-24 md:py-40 px-6 bg-white overflow-hidden"
      data-testid="storefront-manifesto"
    >
      {/* Hairline from top, anchoring */}
      <div
        className="absolute top-0 left-1/2 -translate-x-1/2 w-[1px] h-16"
        style={{ background: `linear-gradient(to bottom, transparent, ${primary}40)` }}
        aria-hidden="true"
      />

      <div className="max-w-5xl mx-auto text-center">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.8 }}
          className="text-[11px] uppercase tracking-[0.45em] mb-10"
          style={{ color: textMuted }}
        >
          — {eyebrow} —
        </motion.div>

        <motion.h2
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.9, delay: 0.1 }}
          className="text-[34px] sm:text-[44px] md:text-[58px] lg:text-[68px] leading-[1.08] tracking-[-0.015em] font-normal"
          style={{ fontFamily: `"${fontHeading}", serif`, color: primary }}
        >
          {headline}
        </motion.h2>

        <motion.p
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.8, delay: 0.3 }}
          className="mt-10 md:mt-14 text-[15px] md:text-[17px] leading-[1.75] max-w-2xl mx-auto"
          style={{ color: textMuted }}
        >
          {kicker}
        </motion.p>
      </div>

      {/* Three gray pillar cards */}
      <div className="max-w-6xl mx-auto mt-20 md:mt-28 grid grid-cols-1 md:grid-cols-3 gap-4 md:gap-6">
        {pillars.slice(0, 3).map((p, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-60px" }}
            transition={{ duration: 0.7, delay: 0.1 * i }}
            className="relative p-8 md:p-10 rounded-[4px]"
            style={{ background: accent }}
            data-testid={`manifesto-pillar-${i}`}
          >
            <div
              className="text-[11px] tabular-nums tracking-[0.3em] uppercase mb-5"
              style={{ color: textMuted }}
            >
              {String(i + 1).padStart(2, "0")} / 03
            </div>
            <div
              className="text-[22px] md:text-[26px] leading-tight tracking-tight mb-4"
              style={{ fontFamily: `"${fontHeading}", serif`, color: primary }}
            >
              {sanitizeBrandText(p.title || "", 60)}
            </div>
            <div className="text-[14px] leading-relaxed" style={{ color: textMuted }}>
              {p.body || p.description || ""}
            </div>
            <div
              className="absolute left-8 right-8 md:left-10 md:right-10 top-16 h-px"
              style={{ background: divider, opacity: 0 }}
              aria-hidden="true"
            />
          </motion.div>
        ))}
      </div>
    </section>
  );
}
