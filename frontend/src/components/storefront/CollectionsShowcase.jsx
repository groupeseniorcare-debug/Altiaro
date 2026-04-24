import React from "react";
import { Link, useParams } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowRight } from "@phosphor-icons/react";
import { pickLang, t } from "../../lib/i18n";
import { designAccents } from "./storefrontUtils";

/**
 * CollectionsShowcase — MONOCHROME. White canvas, 3 tall editorial cards that use
 * a gray frame + image, with the title & CTA living BELOW the card (not on top
 * of the image). Cleaner, less photographic-heavy, closer to Jacquemus or Acne Studios.
 */
export default function CollectionsShowcase({ collections, lang = "fr", design }) {
  const { siteId } = useParams();
  const { primary, accent, divider, textMuted, textFaint, fontHeading } = designAccents(design);

  const list = collections?.length ? collections : [
    { slug: "mobilite", title: t(lang, "collections_fallback_1_title"), description: t(lang, "collections_fallback_1_desc"),
      image: "https://images.unsplash.com/photo-1586773860418-d37222d8fce3?w=900&auto=format&fit=crop" },
    { slug: "sommeil", title: t(lang, "collections_fallback_2_title"), description: t(lang, "collections_fallback_2_desc"),
      image: "https://images.unsplash.com/photo-1505693416388-ac5ce068fe85?w=900&auto=format&fit=crop" },
    { slug: "quotidien", title: t(lang, "collections_fallback_3_title"), description: t(lang, "collections_fallback_3_desc"),
      image: "https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?w=900&auto=format&fit=crop" },
  ];

  return (
    <section className="py-24 md:py-36 px-6 bg-white" data-testid="storefront-collections">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex items-end justify-between flex-wrap gap-6 mb-14 md:mb-20">
          <div>
            <div className="flex items-center gap-3 mb-5">
              <span className="h-px w-10" style={{ background: primary }} />
              <span className="text-[11px] uppercase tracking-[0.4em]" style={{ color: primary }}>
                {t(lang, "collections_eyebrow")}
              </span>
            </div>
            <h2
              className="text-[40px] md:text-[56px] lg:text-[64px] leading-[1.02] tracking-[-0.02em]"
              style={{ fontFamily: `"${fontHeading}", serif`, color: primary }}
            >
              {t(lang, "collections_heading_line1")}<br />{t(lang, "collections_heading_line2")}
            </h2>
          </div>
          <Link
            to={`/shop/${siteId}`}
            data-testid="collections-see-all"
            className="relative inline-flex items-center gap-2 text-[13px] font-medium tracking-wide after:absolute after:left-0 after:right-0 after:-bottom-1 after:h-px after:bg-current after:opacity-30 hover:after:opacity-100 after:transition-opacity"
            style={{ color: primary }}
          >
            {t(lang, "collections_see_all")} <ArrowRight size={13} weight="bold" />
          </Link>
        </div>

        {/* 3 editorial cards */}
        <div
          className="flex md:grid md:grid-cols-3 gap-4 md:gap-6 -mx-6 md:mx-0 px-6 md:px-0 overflow-x-auto md:overflow-visible snap-x snap-mandatory md:snap-none scroll-smooth pb-2 md:pb-0"
          data-testid="collections-carousel"
        >
          {list.slice(0, 3).map((c, i) => {
            const title = pickLang(c.title, lang) || c.title;
            const desc = pickLang(c.description, lang) || c.description;
            const href = c.slug
              ? `/shop/${siteId}/collection/${c.slug}`
              : (c.href?.startsWith("/") ? c.href : `/shop/${siteId}${c.href || ""}`);
            return (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-60px" }}
                transition={{ duration: 0.7, delay: 0.1 * i }}
                className="snap-center shrink-0 w-[85vw] md:w-auto"
              >
                <Link to={href} data-testid={`collection-${i}`} className="group block">
                  {/* Image inside a gray frame — image alone is highlighted, text stays outside */}
                  <div
                    className="relative overflow-hidden aspect-[4/5]"
                    style={{ background: accent, borderRadius: "2px" }}
                  >
                    {c.image ? (
                      <img
                        src={c.image}
                        alt={title}
                        loading="lazy"
                        className="absolute inset-0 w-full h-full object-cover transition-transform duration-[900ms] ease-out group-hover:scale-[1.04]"
                      />
                    ) : null}
                    <div
                      className="absolute top-5 left-5 text-[10px] uppercase tracking-[0.32em] px-2.5 py-1 bg-white"
                      style={{ color: primary, borderRadius: "2px" }}
                    >
                      {t(lang, "hero_collection")} {String(i + 1).padStart(2, "0")}
                    </div>
                  </div>
                  {/* Text lives BELOW the image, with a thin divider */}
                  <div className="mt-5 flex items-start justify-between gap-3 pt-5" style={{ borderTop: `1px solid ${divider}` }}>
                    <div className="flex-1 min-w-0">
                      <h3
                        className="text-[22px] md:text-[24px] leading-tight tracking-tight"
                        style={{ fontFamily: `"${fontHeading}", serif`, color: primary }}
                      >
                        {title}
                      </h3>
                      <p className="text-[13px] mt-2 line-clamp-2" style={{ color: textMuted }}>
                        {desc}
                      </p>
                    </div>
                    <ArrowRight
                      size={20}
                      weight="thin"
                      className="mt-1 shrink-0 transition-transform group-hover:translate-x-1"
                      style={{ color: textFaint }}
                    />
                  </div>
                </Link>
              </motion.div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
