import React from "react";
import { motion } from "framer-motion";
import { ShieldCheck, Truck, HandHeart, Star } from "@phosphor-icons/react";
import { BENEFIT_ICON, designAccents } from "./storefrontUtils";
import { pickLang, t } from "../../lib/i18n";

// Headers / strings localisés au rendu (pas hardcodés) — cf. DICT[lang]
const DEFAULT_BENEFITS_BUILDER = (lang) => [
  { icon: "Truck",       title: t(lang, "trust_free_shipping"),    description: t(lang, "benefit_free_shipping_desc") },
  { icon: "ShieldCheck", title: t(lang, "trust_warranty_2y"),      description: t(lang, "benefit_warranty_desc") },
  { icon: "HandHeart",   title: t(lang, "trust_human_service"),    description: t(lang, "benefit_human_desc") },
  { icon: "Star",        title: "4.8/5 · 2 143",                   description: t(lang, "benefit_returns_desc") },
];

// Eyebrow + titre H2 par langue (chaînes trop spécifiques pour le DICT plat)
const BENEFITS_EYEBROW = {
  fr: "Notre engagement",     en: "Our commitment",        de: "Unser Versprechen",
  nl: "Onze belofte",         it: "Il nostro impegno",     es: "Nuestro compromiso",
};
const BENEFITS_HEADING = {
  fr: ["Aucun compromis,", "aucun raccourci."],
  en: ["No compromises,", "no shortcuts."],
  de: ["Keine Kompromisse,", "keine Abkürzungen."],
  nl: ["Geen compromissen,", "geen shortcuts."],
  it: ["Nessun compromesso,", "nessuna scorciatoia."],
  es: ["Sin concesiones,", "sin atajos."],
};

const FALLBACK_ICONS = { Truck, ShieldCheck, HandHeart, Star };

export function Benefits({ design, lang }) {
  const { primary, accent, divider, textMuted, fontHeading } = designAccents(design);
  const items = design?.benefits?.items || design?.benefits;
  const list = Array.isArray(items) && items.length ? items : DEFAULT_BENEFITS_BUILDER(lang);
  const eyebrow = BENEFITS_EYEBROW[lang] || BENEFITS_EYEBROW.fr;
  const [h1, h2] = BENEFITS_HEADING[lang] || BENEFITS_HEADING.fr;

  return (
    <section
      className="py-24 md:py-36 px-6 bg-white"
      data-testid="storefront-benefits"
    >
      <div className="max-w-7xl mx-auto">
        {/* Header aligned left */}
        <div className="mb-14 md:mb-20 max-w-xl">
          <div className="flex items-center gap-3 mb-5">
            <span className="h-px w-10" style={{ background: primary }} />
            <span className="text-[11px] uppercase tracking-[0.4em]" style={{ color: primary }}>
              {eyebrow}
            </span>
          </div>
          <h2
            className="text-[40px] md:text-[56px] lg:text-[64px] leading-[1.02] tracking-[-0.02em]"
            style={{ fontFamily: `"${fontHeading}", serif`, color: primary }}
          >
            {h1}<br />{h2}
          </h2>
        </div>

        {/* 4 gray pillar cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6">
          {list.slice(0, 4).map((b, i) => {
            const title = typeof b.title === "string" ? b.title : pickLang(b.title, lang) || b.title?.fr || "";
            const desc = typeof b.description === "string"
              ? b.description
              : pickLang(b.description, lang) || pickLang(b.desc, lang) || b.description?.fr || "";
            const Icon = BENEFIT_ICON[b.icon] || FALLBACK_ICONS[b.icon] || ShieldCheck;
            return (
              <motion.div
                key={i}
                data-testid={`benefit-${i}`}
                initial={{ opacity: 0, y: 24 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-60px" }}
                transition={{ duration: 0.6, delay: 0.08 * i }}
                className="p-8 md:p-10 flex flex-col"
                style={{ background: accent, borderRadius: "2px" }}
              >
                <div
                  className="text-[11px] tabular-nums tracking-[0.35em] uppercase mb-8"
                  style={{ color: textMuted }}
                >
                  {String(i + 1).padStart(2, "0")} / 04
                </div>
                <Icon size={30} weight="thin" style={{ color: primary }} className="mb-6" />
                <div
                  className="text-[20px] md:text-[22px] leading-snug tracking-tight mb-3"
                  style={{ fontFamily: `"${fontHeading}", serif`, color: primary }}
                >
                  {title}
                </div>
                <p className="text-[14px] leading-relaxed" style={{ color: textMuted }}>
                  {desc}
                </p>
              </motion.div>
            );
          })}
        </div>
        <span className="hidden" style={{ borderTop: `1px solid ${divider}` }} />
      </div>
    </section>
  );
}
