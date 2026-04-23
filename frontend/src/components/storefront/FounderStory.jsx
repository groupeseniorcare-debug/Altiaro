import React from "react";
import { motion } from "framer-motion";
import { pickLang } from "../../lib/i18n";
import { designAccents } from "./storefrontUtils";

const DEFAULT_STORY = {
  image: "https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=1400&auto=format&fit=crop",
  name: "Camille Lefèvre",
  role: "Fondatrice",
  quote:
    "J'ai créé cette maison après avoir accompagné ma grand-mère. Chaque produit sélectionné passe entre mes mains. Aucun compromis sur la qualité, le service ni la dignité.",
  signature: "Camille L.",
};

/**
 * FounderStory — MONOCHROME editorial split. Pure white canvas, gray image frame,
 * big blockquote with decorative serif guillemet.
 */
export default function FounderStory({ story, lang = "fr", design }) {
  const { primary, accent, divider, textMuted, fontHeading } = designAccents(design);
  const s = story || DEFAULT_STORY;
  const quote = pickLang(s.quote, lang) || s.quote || DEFAULT_STORY.quote;
  const role = pickLang(s.role, lang) || s.role || DEFAULT_STORY.role;
  const name = s.name || DEFAULT_STORY.name;
  const signature = s.signature || name;

  return (
    <section
      className="relative py-24 md:py-36 px-6 bg-white"
      data-testid="storefront-founder"
      id="story"
    >
      {/* Section label */}
      <div className="max-w-7xl mx-auto mb-14 md:mb-20 flex items-center gap-4">
        <span className="h-px w-14" style={{ background: primary }} />
        <span className="text-[11px] uppercase tracking-[0.45em]" style={{ color: primary }}>
          Notre histoire
        </span>
      </div>

      <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-12 gap-12 lg:gap-20 items-start">
        {/* Photo column */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: 0.9 }}
          className="lg:col-span-5 relative"
        >
          <div
            className="aspect-[4/5] overflow-hidden"
            style={{ background: accent, borderRadius: "2px" }}
          >
            {s.image ? (
              <img
                src={s.image}
                alt={name}
                loading="lazy"
                className="w-full h-full object-cover"
              />
            ) : (
              <div className="w-full h-full flex items-center justify-center">
                <div
                  className="text-[140px] leading-none font-normal opacity-[0.08] select-none"
                  style={{ fontFamily: `"${fontHeading}", serif`, color: primary }}
                >
                  {name.charAt(0)}
                </div>
              </div>
            )}
          </div>
          <div
            className="mt-5 flex items-center gap-3 text-[10px] uppercase tracking-[0.35em]"
            style={{ color: textMuted }}
          >
            <span className="h-px w-8" style={{ background: primary }} />
            <span>Portrait · {name}</span>
          </div>
        </motion.div>

        {/* Copy column */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: 0.9, delay: 0.2 }}
          className="lg:col-span-7"
        >
          <blockquote
            className="text-[28px] md:text-[36px] lg:text-[44px] leading-[1.2] tracking-tight font-normal"
            style={{ fontFamily: `"${fontHeading}", serif`, color: primary }}
          >
            <span
              className="inline-block text-[90px] md:text-[130px] leading-none align-top mr-1 opacity-[0.15] -translate-y-3"
              style={{ fontFamily: `"${fontHeading}", serif`, color: primary }}
              aria-hidden="true"
            >
              “
            </span>
            {quote}
          </blockquote>

          {/* Signature row — gray card wrap */}
          <div
            className="mt-12 p-6 md:p-7 rounded-[4px] flex flex-wrap items-end gap-6"
            style={{ background: accent }}
          >
            <div
              className="text-2xl md:text-3xl italic leading-none"
              style={{ fontFamily: `"${fontHeading}", serif`, color: primary }}
            >
              {signature}
            </div>
            <div className="flex items-center gap-4 pb-1">
              <span className="h-px w-10" style={{ background: primary }} />
              <div>
                <div className="text-[14px] font-semibold" style={{ color: primary }}>
                  {name}
                </div>
                <div
                  className="text-[10px] uppercase tracking-[0.3em] mt-1"
                  style={{ color: textMuted }}
                >
                  {role}
                </div>
              </div>
            </div>
          </div>
          <span className="hidden" style={{ background: divider }} />
        </motion.div>
      </div>
    </section>
  );
}
