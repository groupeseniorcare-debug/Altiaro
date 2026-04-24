import React, { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { motion, useScroll, useTransform } from "framer-motion";
import { ArrowRight, ShieldCheck, Star, Truck } from "@phosphor-icons/react";
import { designText, designAccents } from "./storefrontUtils";
import { t } from "../../lib/i18n";
import { sanitizeBrandText } from "../../lib/brandText";

/**
 * Hero — MONOCHROME editorial magazine. Pure white, black ink, gray cards.
 *
 * Left column  : eyebrow, oversized serif title, subtitle, CTAs, trust strip
 * Right column : tall product image inside a gray panel with an editorial
 *                caption card, side chapter marker and a thin scroll indicator.
 */
export function Hero({ site, design, lang, products }) {
  const { siteId } = useParams();
  const { primary, accent, divider, textMuted, brandAccent, fontHeading } = designAccents(design);
  const brand = design?.brand || {};

  const brandLabel = sanitizeBrandText(brand.logo_text || brand.name || "", 40);
  const heroTitleRaw = designText(design, "hero.title", lang) || brandLabel || site?.name || t(lang, "shop_title");
  const heroTitle = sanitizeBrandText(heroTitleRaw, 60);
  const heroSub = designText(design, "hero.subtitle", lang)
    || "Des produits sélectionnés avec soin pour préserver votre autonomie, votre confort et votre sérénité au quotidien.";
  const heroCta = designText(design, "hero.cta_label", lang) || t(lang, "shop_now");
  const heroCta2 = designText(design, "hero.cta_secondary_label", lang) || t(lang, "nav_about");
  const eyebrowRaw = designText(design, "hero.eyebrow", lang) || brand.tagline || "La maison bienveillante";
  const eyebrow = sanitizeBrandText(eyebrowRaw, 60);
  const rating = design?.hero?.rating || { score: 4.8, count: 2143 };
  const chapterNumber = "01";
  const chapterLabel = "L'édition en cours";

  const firstProductImg = (() => {
    if (!Array.isArray(products) || products.length === 0) return null;
    const featured = products.find((p) => p.featured && p.images?.[0]);
    return (featured || products.find((p) => p.images?.[0]))?.images?.[0] || null;
  })();
  const heroImage = designText(design, "hero.image", lang) || design?.hero?.image || firstProductImg || null;

  const ref = useRef(null);
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start end", "end start"] });
  const imgY = useTransform(scrollYProgress, [0, 1], [0, -90]);
  const copyY = useTransform(scrollYProgress, [0, 1], [0, -40]);

  const [hintVisible, setHintVisible] = useState(true);
  useEffect(() => {
    const onScroll = () => setHintVisible(window.scrollY < 180);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <section
      ref={ref}
      className="relative overflow-hidden bg-white"
      style={{ color: primary }}
      data-testid="storefront-hero"
    >
      {/* Chapter marker — editorial magazine ribbon at the very top */}
      <div
        className="max-w-[1440px] mx-auto px-6 md:px-10 pt-8 flex items-center justify-between text-[11px] uppercase tracking-[0.35em]"
        style={{ color: textMuted }}
      >
        <div className="flex items-center gap-3">
          <span className="tabular-nums">{chapterNumber}</span>
          <span className="h-px w-12" style={{ background: divider }} />
          <span>{chapterLabel}</span>
        </div>
        <div className="hidden md:flex items-center gap-3">
          <span>{brandLabel || "Maison"}</span>
          <span>·</span>
          <span className="tabular-nums">{new Date().getFullYear()}</span>
        </div>
      </div>

      <div className="max-w-[1440px] mx-auto px-6 md:px-10 pt-10 md:pt-14 pb-24 md:pb-36 grid grid-cols-1 lg:grid-cols-[1.1fr_1fr] gap-10 lg:gap-20 items-center min-h-[calc(100vh-200px)]">
        {/* ---------- LEFT : Copy ---------- */}
        <motion.div style={{ y: copyY }} className="max-w-2xl order-2 lg:order-1">
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
            className="inline-flex items-center gap-3 mb-8"
            data-testid="hero-eyebrow"
          >
            <span className="h-px w-10" style={{ background: primary }} />
            <span className="text-[10px] uppercase tracking-[0.4em] font-medium" style={{ color: primary }}>
              {eyebrow}
            </span>
          </motion.div>

          <motion.h1
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 1.1, ease: [0.22, 1, 0.36, 1], delay: 0.1 }}
            className="text-[54px] sm:text-[72px] md:text-[92px] lg:text-[112px] leading-[0.92] tracking-[-0.035em] font-normal"
            style={{ fontFamily: `"${fontHeading}", Georgia, serif`, color: primary }}
            data-testid="hero-title"
          >
            {heroTitle}
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.9, delay: 0.3 }}
            className="text-[17px] md:text-[19px] mt-10 leading-[1.65] max-w-xl"
            style={{ color: textMuted }}
            data-testid="hero-subtitle"
          >
            {heroSub}
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.9, delay: 0.5 }}
            className="mt-10 flex flex-col sm:flex-row items-start sm:items-center gap-3"
          >
            <Link
              to={`/shop/${siteId}#products`}
              data-testid="hero-cta-primary"
              className="group inline-flex items-center gap-2.5 h-14 px-9 rounded-full text-white font-medium transition-all hover:gap-3.5 text-[14px] tracking-wide"
              style={{ background: primary }}
            >
              {heroCta}
              <ArrowRight size={15} weight="bold" className="transition-transform group-hover:translate-x-0.5" />
            </Link>
            <Link
              to={`/shop/${siteId}#story`}
              data-testid="hero-cta-secondary"
              className="relative inline-flex items-center gap-2 text-[14px] font-medium tracking-wide h-14 px-2 after:absolute after:left-2 after:right-2 after:bottom-3 after:h-px after:bg-current after:opacity-40 hover:after:opacity-100 after:transition-opacity"
              style={{ color: primary }}
            >
              {heroCta2}
            </Link>
          </motion.div>

          {/* Trust strip — black text, dot separators */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 1, delay: 0.8 }}
            className="mt-14 flex flex-wrap items-center gap-x-5 gap-y-3 text-[13px]"
            style={{ color: textMuted }}
          >
            {rating?.score && (
              <div className="flex items-center gap-2" data-testid="hero-rating">
                <div className="flex" style={{ color: "#F5B800" }}>
                  {[...Array(5)].map((_, i) => (
                    <Star key={i} size={13} weight="fill" />
                  ))}
                </div>
                <span className="font-medium" style={{ color: primary }}>
                  {rating.score}/5
                </span>
                <span>· {rating.count?.toLocaleString?.("fr-FR") || rating.count} avis</span>
              </div>
            )}
            <span className="opacity-30">·</span>
            <span className="flex items-center gap-1.5">
              <Truck size={13} weight="bold" /> {t(lang, "trust_free_shipping")}
            </span>
            <span className="opacity-30">·</span>
            <span className="flex items-center gap-1.5">
              <ShieldCheck size={13} weight="bold" /> {t(lang, "trust_warranty_2y")}
            </span>
          </motion.div>
        </motion.div>

        {/* ---------- RIGHT : Visual ---------- */}
        <motion.div
          style={{ y: imgY }}
          className="relative order-1 lg:order-2"
          data-testid="hero-image"
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.97 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 1.2, ease: [0.22, 1, 0.36, 1] }}
            className="relative aspect-[4/5] md:aspect-[5/6] overflow-hidden"
            style={{ background: accent, borderRadius: "2px" }}
          >
            {heroImage ? (
              <img
                src={heroImage}
                alt={heroTitle}
                className="w-full h-full object-cover"
                loading="eager"
                fetchPriority="high"
              />
            ) : (
              <div
                className="w-full h-full flex items-center justify-center"
                style={{ background: accent }}
                data-testid="hero-image-placeholder"
              >
                <div
                  className="text-[200px] md:text-[280px] font-normal opacity-[0.07] select-none leading-none"
                  style={{ fontFamily: `"${fontHeading}", serif`, color: primary }}
                >
                  {(heroTitle || "A").charAt(0).toUpperCase()}
                </div>
              </div>
            )}

            {/* Editorial caption card — premium gray */}
            <motion.div
              initial={{ opacity: 0, x: -16 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.9, delay: 0.9 }}
              className="absolute left-6 bottom-6 md:left-8 md:bottom-8 bg-white px-5 py-4 max-w-[280px] shadow-[0_24px_60px_-24px_rgba(0,0,0,0.25)]"
              style={{ borderRadius: "2px" }}
              data-testid="hero-floating-card"
            >
              <div className="text-[9px] uppercase tracking-[0.32em] mb-1.5" style={{ color: textMuted }}>
                Satisfait ou remboursé
              </div>
              <div className="text-[13px] leading-snug" style={{ color: primary }}>
                14 jours pour changer d'avis —{" "}
                <span style={{ color: textMuted }}>retour gratuit</span>
              </div>
            </motion.div>
          </motion.div>

          {/* Vertical chapter caption — Vogue-style magazine edge */}
          <div
            className="hidden lg:block absolute -right-14 top-8 text-[10px] uppercase tracking-[0.4em] origin-top-left rotate-90 whitespace-nowrap"
            style={{ color: textMuted }}
            aria-hidden="true"
          >
            {brandLabel || "Collection"} — Édition {new Date().getFullYear()}
          </div>
        </motion.div>
      </div>

      {/* Bottom ribbon — separator with refined marker line */}
      <div className="max-w-[1440px] mx-auto px-6 md:px-10 pb-4">
        <div className="h-px" style={{ background: divider }} />
      </div>

      {/* Scroll indicator */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: hintVisible ? 1 : 0, y: hintVisible ? 0 : 10 }}
        transition={{ duration: 0.5 }}
        className="hidden md:flex absolute bottom-10 left-1/2 -translate-x-1/2 flex-col items-center gap-3 pointer-events-none"
        aria-hidden="true"
      >
        <span className="text-[10px] uppercase tracking-[0.4em]" style={{ color: textMuted }}>
          Scroll
        </span>
        <div className="relative w-px h-14 overflow-hidden" style={{ background: divider }}>
          <motion.div
            className="absolute left-0 right-0 top-0 h-4"
            style={{ background: primary }}
            animate={{ y: ["-16px", "56px"] }}
            transition={{ duration: 1.8, repeat: Infinity, ease: "easeInOut" }}
          />
        </div>
      </motion.div>
      {/* brandAccent is intentionally unused here — reserved for other sections */}
      {false && <span style={{ background: brandAccent }} />}
    </section>
  );
}
