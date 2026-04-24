import React from "react";
import { motion } from "framer-motion";
import { ShieldCheck, HandsClapping, Leaf, Tree } from "@phosphor-icons/react";
import { designAccents } from "./storefrontUtils";
import { t } from "../../lib/i18n";

const ICONS = { Leaf, HandsClapping, ShieldCheck, Tree };

/**
 * BrandProcess — editorial "Made by us" section. Explains how products are
 * selected, crafted and shipped. Monochrome: white canvas, black ink,
 * 4 gray cards with numbered kickers. No portrait, no stock photo of a woman.
 */
export default function BrandProcess({ design, lang = "fr" }) {
  const { primary, accent, textMuted, fontHeading } = designAccents(design);
  const defaultSteps = [
    { icon: "Leaf",          kicker: `01 · ${t(lang, "process_step_1_kicker")}`, title: t(lang, "process_step_1_title"), body: t(lang, "process_step_1_body") },
    { icon: "HandsClapping", kicker: `02 · ${t(lang, "process_step_2_kicker")}`, title: t(lang, "process_step_2_title"), body: t(lang, "process_step_2_body") },
    { icon: "ShieldCheck",   kicker: `03 · ${t(lang, "process_step_3_kicker")}`, title: t(lang, "process_step_3_title"), body: t(lang, "process_step_3_body") },
    { icon: "Tree",          kicker: `04 · ${t(lang, "process_step_4_kicker")}`, title: t(lang, "process_step_4_title"), body: t(lang, "process_step_4_body") },
  ];
  const steps = (design?.brand_process && design.brand_process.length === 4)
    ? design.brand_process : defaultSteps;

  return (
    <section
      className="py-24 md:py-36 px-6 bg-white"
      data-testid="storefront-brand-process"
      id="process"
    >
      <div className="max-w-7xl mx-auto">
        <div className="flex items-end justify-between flex-wrap gap-6 mb-14 md:mb-20">
          <div className="max-w-xl">
            <div className="flex items-center gap-3 mb-5">
              <span className="h-px w-10" style={{ background: primary }} />
              <span className="text-[11px] uppercase tracking-[0.4em]" style={{ color: primary }}>
                {t(lang, "process_eyebrow")}
              </span>
            </div>
            <h2
              className="text-[40px] md:text-[56px] lg:text-[64px] leading-[1.02] tracking-[-0.02em]"
              style={{ fontFamily: `"${fontHeading}", serif`, color: primary }}
            >
              {t(lang, "process_heading_line1")}<br />{t(lang, "process_heading_line2")}
            </h2>
            <p className="text-[15px] mt-6 max-w-lg leading-relaxed" style={{ color: textMuted }}>
              {t(lang, "process_subtitle")}
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6">
          {steps.slice(0, 4).map((s, i) => {
            const Icon = ICONS[s.icon] || ShieldCheck;
            return (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 24 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-60px" }}
                transition={{ duration: 0.6, delay: 0.08 * i }}
                className="p-8 md:p-10 flex flex-col"
                style={{ background: accent, borderRadius: "2px" }}
                data-testid={`process-${i}`}
              >
                <div
                  className="text-[11px] tabular-nums tracking-[0.3em] uppercase mb-8"
                  style={{ color: textMuted }}
                >
                  {s.kicker}
                </div>
                <Icon size={28} weight="thin" style={{ color: primary }} className="mb-5" />
                <div
                  className="text-[20px] md:text-[22px] leading-snug tracking-tight mb-3"
                  style={{ fontFamily: `"${fontHeading}", serif`, color: primary }}
                >
                  {s.title}
                </div>
                <p className="text-[14px] leading-relaxed" style={{ color: textMuted }}>
                  {s.body}
                </p>
              </motion.div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
