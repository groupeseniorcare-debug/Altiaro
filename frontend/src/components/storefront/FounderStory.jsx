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
 * FounderStory — editorial split layout with a tall photo on one side and a
 * poised blockquote on the other. Uses a hairline signature, small-caps role,
 * and a long-form quote with decorative guillemets.
 */
export default function FounderStory({ story, lang = "fr", design }) {
  const { fontHeading, primary, accent } = designAccents(design);
  const s = story || DEFAULT_STORY;

  const quote = pickLang(s.quote, lang) || s.quote || DEFAULT_STORY.quote;
  const role = pickLang(s.role, lang) || s.role || DEFAULT_STORY.role;
  const name = s.name || DEFAULT_STORY.name;
  const signature = s.signature || name;

  return (
    <section
      className="relative py-20 md:py-32 px-6 bg-white"
      data-testid="storefront-founder"
      id="story"
    >
      <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-12 gap-12 lg:gap-20 items-center">
        {/* Photo column — tall portrait, understated frame */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: 0.9, ease: [0.22, 1, 0.36, 1] }}
          className="lg:col-span-5 relative"
        >
          <div
            className="aspect-[4/5] rounded-[4px] overflow-hidden shadow-[0_40px_100px_-40px_rgba(0,0,0,0.25)]"
            style={{ background: accent }}
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
                <div className="text-center px-6">
                  <div
                    className="text-[120px] leading-none font-normal opacity-[0.08] select-none"
                    style={{ fontFamily: `"${fontHeading}", serif` }}
                  >
                    {name.charAt(0)}
                  </div>
                </div>
              </div>
            )}
          </div>
          {/* Caption under photo — minimal, editorial */}
          <div className="mt-5 flex items-center gap-3 text-[11px] uppercase tracking-[0.32em] text-neutral-500">
            <span className="h-px w-8" style={{ background: primary }} />
            <span>Portrait · {name}</span>
          </div>
        </motion.div>

        {/* Copy column — long-form, editorial rhythm */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: 0.9, delay: 0.2, ease: [0.22, 1, 0.36, 1] }}
          className="lg:col-span-7"
        >
          <div className="text-[10px] uppercase tracking-[0.45em] text-neutral-500 mb-6">
            — Notre histoire
          </div>
          <blockquote
            className="text-[26px] md:text-[34px] lg:text-[42px] leading-[1.18] tracking-tight text-neutral-900 font-normal"
            style={{ fontFamily: `"${fontHeading}", serif` }}
          >
            <span
              className="inline-block text-[80px] md:text-[110px] leading-none align-top mr-1 opacity-20 -translate-y-2"
              style={{ fontFamily: `"${fontHeading}", serif`, color: primary }}
              aria-hidden="true"
            >
              “
            </span>
            {quote}
          </blockquote>

          {/* Signature + role */}
          <div className="mt-10 flex items-end gap-5">
            <div
              className="text-2xl md:text-3xl italic"
              style={{ fontFamily: `"${fontHeading}", serif`, color: primary }}
            >
              {signature}
            </div>
            <div className="pb-1 flex items-center gap-3">
              <span className="h-px w-10" style={{ background: primary }} />
              <div>
                <div className="text-[14px] font-semibold text-neutral-900">{name}</div>
                <div className="text-[11px] uppercase tracking-[0.3em] text-neutral-500 mt-0.5">{role}</div>
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
