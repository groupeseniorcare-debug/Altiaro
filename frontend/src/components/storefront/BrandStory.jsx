/**
 * Phase 2.6 Tâche D — <BrandStory>
 *
 * Remplace l'ancienne section <FounderStory> qui parlait d'une personne
 * fictive ("Camille Lefèvre") par une section "Notre maison" qui présente
 * la marque comme entité (atelier, savoir-faire, ancrage géographique).
 *
 * Sources de données :
 *   design.brand.workshop_story = {
 *     eyebrow:    {fr,en,...} ex. "Notre maison" / "L'atelier"
 *     headline:   {fr,en,...} ex. "Une maison française, une exigence quotidienne"
 *     paragraph:  {fr,en,...} 2-3 phrases ton Aesop
 *     cta_label:  {fr,en,...} ex. "Découvrir notre histoire"
 *     cta_href:   "/about" (par défaut)
 *   }
 *   design.brand.workshop_image = URL Nano Banana (4:5 ou 16:9, atelier
 *   premium, packaging soigné, ambiance scandinave épurée).
 *
 * Si workshop_story absent → fallback statique générique adapté à la marque
 * (lit `design.brand.name`, `design.niche`). On évite tout nom fictif.
 */
import React from "react";
import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import { ArrowRight } from "@phosphor-icons/react";
import { pickLang } from "../../lib/i18n";
import { designAccents } from "./storefrontUtils";

const FALLBACK_IMAGE =
  "https://images.unsplash.com/photo-1556761175-5973dc0f32e7?w=1400&auto=format&fit=crop";

function pick(obj, lang, fallback) {
  if (!obj) return fallback;
  if (typeof obj === "string") return obj;
  return pickLang(obj, lang) || obj.fr || obj.en || fallback;
}

function buildFallback(design, lang) {
  const brandName = (design?.brand?.name || "Notre maison").trim();
  const fallback = {
    fr: {
      eyebrow: "Notre maison",
      headline: `${brandName}, une exigence française au quotidien.`,
      paragraph:
        "Chaque pièce est sélectionnée par notre comité produit, "
        + "vérifiée à l'arrivée dans notre centre logistique en France métropolitaine, "
        + "puis expédiée sous 72 heures. Notre garantie 2 ans et nos retours sous 14 jours "
        + "vous laissent le temps d'être pleinement satisfait.",
      cta: "Découvrir notre maison",
    },
    en: {
      eyebrow: "Our house",
      headline: `${brandName} — a quiet French standard for everyday life.`,
      paragraph:
        "Each piece is curated by our product board, inspected on arrival "
        + "at our logistics centre in metropolitan France, then shipped within 72 hours. "
        + "Our 2-year warranty and 14-day returns give you the time to be fully satisfied.",
      cta: "Discover our house",
    },
  };
  return fallback[lang] || fallback.fr;
}

export default function BrandStory({ story, image, lang = "fr", design, siteId }) {
  const { primary, accent, textMuted, fontHeading } = designAccents(design);

  const fb = buildFallback(design, lang);
  const eyebrow = pick(story?.eyebrow, lang, fb.eyebrow);
  const headline = pick(story?.headline, lang, fb.headline);
  const paragraph = pick(story?.paragraph, lang, fb.paragraph);
  const ctaLabel = pick(story?.cta_label, lang, fb.cta);
  const ctaHref = (story?.cta_href || "/about").trim();
  const imageUrl = image || story?.image || FALLBACK_IMAGE;

  // Internal link only on the storefront sub-tree
  const fullCtaHref = siteId && ctaHref.startsWith("/")
    ? `/shop/${siteId}${ctaHref === "/" ? "" : ctaHref}`
    : ctaHref;

  return (
    <section
      className="relative py-24 md:py-36 px-6 bg-white"
      data-testid="storefront-brand-story"
      id="brand-story"
    >
      <div className="max-w-7xl mx-auto mb-14 md:mb-20 flex items-center gap-4">
        <span className="h-px w-14" style={{ background: primary }} />
        <span
          className="text-[11px] uppercase tracking-[0.45em]"
          style={{ color: primary }}
        >
          {eyebrow}
        </span>
      </div>

      <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-12 gap-12 lg:gap-20 items-center">
        {/* Image atelier — Nano Banana ou fallback Unsplash neutre */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: 0.9 }}
          className="lg:col-span-6 relative"
        >
          <div
            className="aspect-[4/5] overflow-hidden"
            style={{ background: accent, borderRadius: "2px" }}
          >
            <img
              src={imageUrl}
              alt={pick(story?.eyebrow, lang, fb.eyebrow)}
              loading="lazy"
              className="w-full h-full object-cover"
            />
          </div>
          <div
            className="mt-5 flex items-center gap-3 text-[10px] uppercase tracking-[0.35em]"
            style={{ color: textMuted }}
          >
            <span className="h-px w-8" style={{ background: primary }} />
            <span>{lang === "en" ? "Behind the scenes" : "Coulisses"}</span>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: 0.9, delay: 0.2 }}
          className="lg:col-span-6"
        >
          <h2
            className="text-[34px] md:text-[44px] lg:text-[54px] leading-[1.1] tracking-tight font-light"
            style={{ fontFamily: `"${fontHeading}", serif`, color: primary }}
          >
            {headline}
          </h2>
          <p
            className="mt-6 md:mt-8 text-[15.5px] md:text-[16px] leading-[1.7] max-w-[58ch]"
            style={{ color: "#3A3A3A", fontWeight: 300 }}
          >
            {paragraph}
          </p>
          {fullCtaHref ? (
            <Link
              to={fullCtaHref}
              className="mt-8 inline-flex items-center gap-2 text-[13px] uppercase tracking-[0.28em] hover:gap-3 transition-all"
              style={{ color: primary, fontWeight: 500 }}
              data-testid="brand-story-cta"
            >
              {ctaLabel}
              <ArrowRight size={14} weight="bold" />
            </Link>
          ) : null}
        </motion.div>
      </div>
    </section>
  );
}
