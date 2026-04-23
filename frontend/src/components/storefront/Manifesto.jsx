import React from "react";
import { motion } from "framer-motion";
import { designAccents } from "./storefrontUtils";
import { sanitizeBrandText } from "../../lib/brandText";

/**
 * Manifesto — editorial typographic statement section, inspired by Aesop /
 * Loro Piana. No image. Big oversized serif quote that whispers the brand's
 * conviction, supported by a short kicker paragraph and optional eyebrow.
 *
 * Renders with a premium default when `design.manifesto` is absent.
 */
export default function Manifesto({ design, lang = "fr" }) {
  const { fontHeading, primary } = designAccents(design);
  const brand = design?.brand || {};
  const brandName = sanitizeBrandText(brand.logo_text || brand.name || "", 40);
  const m = design?.manifesto || {};
  const eyebrow = sanitizeBrandText(m.eyebrow?.[lang] || m.eyebrow || "Manifeste", 40);
  const headline = sanitizeBrandText(
    m.headline?.[lang]
      || m.headline
      || brand.tagline?.[lang]
      || brand.tagline
      || "Bien vieillir chez soi n'est pas un luxe. C'est un droit.",
    240,
  );
  const kicker = m.kicker?.[lang]
    || m.kicker
    || `Chez ${brandName || "nous"}, chaque produit est choisi comme si c'était pour nos propres parents. Nous refusons la médiocrité. Nous refusons le paternalisme. Nous croyons qu'une belle vieillesse mérite de beaux objets.`;

  return (
    <section
      className="relative py-24 md:py-40 px-6 overflow-hidden"
      data-testid="storefront-manifesto"
    >
      {/* hair-thin brand accent line — anchors the section without dominating */}
      <div
        className="absolute top-0 left-1/2 -translate-x-1/2 w-[1px] h-16"
        style={{ background: `linear-gradient(to bottom, transparent, ${primary}40)` }}
        aria-hidden="true"
      />

      <div className="max-w-5xl mx-auto text-center">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
          className="text-[10px] md:text-[11px] uppercase tracking-[0.45em] text-neutral-500 mb-10"
        >
          — {eyebrow} —
        </motion.div>

        <motion.h2
          initial={{ opacity: 0, y: 40 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.9, ease: [0.22, 1, 0.36, 1], delay: 0.1 }}
          className="text-[34px] sm:text-[44px] md:text-[58px] lg:text-[68px] leading-[1.08] tracking-[-0.01em] text-neutral-900 font-normal"
          style={{ fontFamily: `"${fontHeading}", serif` }}
        >
          {headline}
        </motion.h2>

        <motion.p
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.8, delay: 0.3 }}
          className="mt-10 md:mt-14 text-[15px] md:text-[17px] leading-[1.75] text-neutral-600 max-w-2xl mx-auto"
        >
          {kicker}
        </motion.p>
      </div>
    </section>
  );
}
