import React, { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { motion, useScroll, useTransform } from "framer-motion";
import { ArrowRight, ShieldCheck, Star, Truck } from "@phosphor-icons/react";
import { designText } from "./storefrontUtils";
import { t } from "../../lib/i18n";
import { sanitizeBrandText } from "../../lib/brandText";

/**
 * Hero — ultra-premium editorial hero, inspired by Aesop / Loro Piana.
 *
 * Features:
 *  • Near-full viewport height with generous vertical breathing room
 *  • Oversized serif title (up to 96px on desktop) with tight tracking
 *  • Soft parallax on the visual column as the page scrolls
 *  • Minimal eyebrow line (thin hairline + small caps label)
 *  • Editorial ratings / trust line in a single refined row
 *  • Subtle animated scroll indicator (vertical line + dot)
 *  • Graceful placeholder when the hero image is not yet set
 */
export function Hero({ site, design, lang, products }) {
  const { siteId } = useParams();
  const brand = design?.brand || {};
  const primary = brand.primary_color || brand.palette?.primary || "#1C1917";
  const accent = brand.accent_color || brand.palette?.accent || "#F5F2EB";
  const textColor = brand.text_color || brand.palette?.text || "#1C1917";
  const bg = brand.background_color || brand.palette?.background || "#FDFBF7";
  const fontHeading = brand.font_heading || "Fraunces";

  const brandLabel = sanitizeBrandText(brand.logo_text || brand.name || "", 40);
  const heroTitleRaw = designText(design, "hero.title", lang) || brandLabel || site?.name || t(lang, "shop_title");
  const heroTitle = sanitizeBrandText(heroTitleRaw, 60);
  const heroSub = designText(design, "hero.subtitle", lang)
    || "Des produits sélectionnés avec soin pour préserver votre autonomie, votre confort et votre sérénité au quotidien.";
  const heroCta = designText(design, "hero.cta_label", lang) || "Découvrir la collection";
  const heroCta2 = designText(design, "hero.cta_secondary_label", lang) || "Notre histoire";
  const eyebrowRaw = designText(design, "hero.eyebrow", lang) || brand.tagline || "La maison bienveillante";
  const eyebrow = sanitizeBrandText(eyebrowRaw, 60);
  const rating = design?.hero?.rating || { score: 4.8, count: 2143 };

  // First available product image becomes the hero visual if no explicit asset is set.
  const firstProductImg = (() => {
    if (!Array.isArray(products) || products.length === 0) return null;
    const featured = products.find((p) => p.featured && p.images?.[0]);
    return (featured || products.find((p) => p.images?.[0]))?.images?.[0] || null;
  })();
  const heroImage = designText(design, "hero.image", lang) || design?.hero?.image || firstProductImg || null;

  // Subtle parallax on scroll for the image column
  const ref = useRef(null);
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start end", "end start"] });
  const imgY = useTransform(scrollYProgress, [0, 1], [0, -80]);
  const copyY = useTransform(scrollYProgress, [0, 1], [0, -30]);

  // Hide the scroll indicator once the user has scrolled ~200px
  const [hintVisible, setHintVisible] = useState(true);
  useEffect(() => {
    const onScroll = () => setHintVisible(window.scrollY < 200);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <section
      ref={ref}
      className="relative overflow-hidden"
      style={{ background: bg, color: textColor }}
      data-testid="storefront-hero"
    >
      <div className="max-w-[1440px] mx-auto px-6 md:px-10 pt-16 md:pt-24 pb-24 md:pb-36 grid grid-cols-1 lg:grid-cols-[1.05fr_1fr] gap-10 lg:gap-20 items-center min-h-[calc(100vh-140px)]">
        {/* ---------- LEFT : Copy ---------- */}
        <motion.div style={{ y: copyY }} className="max-w-2xl order-2 lg:order-1">
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
            className="inline-flex items-center gap-3 mb-8"
            data-testid="hero-eyebrow"
          >
            <span className="h-px w-8" style={{ background: primary }} />
            <span className="text-[10px] uppercase tracking-[0.4em] font-medium" style={{ color: textColor }}>
              {eyebrow}
            </span>
          </motion.div>

          <motion.h1
            initial={{ opacity: 0, y: 28 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 1.1, ease: [0.22, 1, 0.36, 1], delay: 0.1 }}
            className="text-[52px] sm:text-[68px] md:text-[84px] lg:text-[96px] leading-[0.95] tracking-[-0.03em] font-normal"
            style={{ fontFamily: `"${fontHeading}", Georgia, serif`, color: textColor }}
            data-testid="hero-title"
          >
            {heroTitle}
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.9, delay: 0.3, ease: [0.22, 1, 0.36, 1] }}
            className="text-[17px] md:text-[19px] mt-8 leading-relaxed max-w-xl"
            style={{ color: `${textColor}b3` }}
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
              className="group inline-flex items-center gap-2.5 h-14 px-8 rounded-full text-white font-medium transition-all hover:gap-3.5 text-[14px] tracking-wide bg-neutral-900 hover:bg-neutral-800"
            >
              {heroCta}
              <ArrowRight size={15} weight="bold" className="transition-transform group-hover:translate-x-0.5" />
            </Link>
            <Link
              to={`/shop/${siteId}#story`}
              data-testid="hero-cta-secondary"
              className="relative inline-flex items-center gap-2 text-[14px] font-medium tracking-wide h-14 px-2 after:absolute after:left-2 after:right-2 after:bottom-3 after:h-px after:bg-current after:opacity-40 hover:after:opacity-100 after:transition-opacity"
              style={{ color: textColor }}
            >
              {heroCta2}
            </Link>
          </motion.div>

          {/* Trust strip — ultra-minimal single line with dot separators */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 1, delay: 0.8 }}
            className="mt-14 flex flex-wrap items-center gap-x-5 gap-y-3 text-[13px]"
            style={{ color: `${textColor}a0` }}
          >
            {rating?.score && (
              <div className="flex items-center gap-2" data-testid="hero-rating">
                <div className="flex" style={{ color: "#F5B800" }}>
                  {[...Array(5)].map((_, i) => (
                    <Star key={i} size={13} weight="fill" />
                  ))}
                </div>
                <span className="font-medium" style={{ color: textColor }}>
                  {rating.score}/5
                </span>
                <span>· {rating.count?.toLocaleString?.("fr-FR") || rating.count} avis</span>
              </div>
            )}
            <span className="opacity-30">·</span>
            <span className="flex items-center gap-1.5">
              <Truck size={13} weight="bold" /> Livraison offerte
            </span>
            <span className="opacity-30">·</span>
            <span className="flex items-center gap-1.5">
              <ShieldCheck size={13} weight="bold" /> Garantie 2 ans
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
            initial={{ opacity: 0, scale: 0.96 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 1.2, ease: [0.22, 1, 0.36, 1] }}
            className="relative aspect-[4/5] md:aspect-[5/6] rounded-[4px] overflow-hidden"
            style={{ background: accent }}
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
                style={{
                  background: `linear-gradient(135deg, ${accent} 0%, ${primary}15 60%, ${accent} 100%)`,
                }}
                data-testid="hero-image-placeholder"
              >
                <div
                  className="text-[160px] md:text-[220px] font-normal opacity-[0.06] select-none leading-none"
                  style={{ fontFamily: `"${fontHeading}", serif`, color: textColor }}
                >
                  {(heroTitle || "A").charAt(0).toUpperCase()}
                </div>
              </div>
            )}

            {/* Editorial caption card — bottom-left, glassmorphic */}
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.9, delay: 0.9 }}
              className="absolute left-6 bottom-6 md:left-8 md:bottom-8 bg-white/92 backdrop-blur-md rounded-[2px] px-4 py-3 max-w-[260px] shadow-[0_20px_60px_-30px_rgba(0,0,0,0.25)]"
              data-testid="hero-floating-card"
            >
              <div className="text-[9px] uppercase tracking-[0.32em] text-neutral-500 mb-1">
                Satisfait ou remboursé
              </div>
              <div className="text-[13px] text-neutral-900 leading-snug">
                14 jours pour changer d'avis — <span className="text-neutral-500">retour gratuit</span>
              </div>
            </motion.div>
          </motion.div>

          {/* vertical brand name — editorial Vogue-style caption on the right edge */}
          <div
            className="hidden lg:block absolute -right-12 top-8 text-[10px] uppercase tracking-[0.4em] origin-top-left rotate-90 whitespace-nowrap text-neutral-500"
            aria-hidden="true"
          >
            {brandLabel || "Collection"} — Édition {new Date().getFullYear()}
          </div>
        </motion.div>
      </div>

      {/* Scroll indicator — a thin animated vertical line with a dot travelling down */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: hintVisible ? 1 : 0, y: hintVisible ? 0 : 10 }}
        transition={{ duration: 0.6 }}
        className="hidden md:flex absolute bottom-8 left-1/2 -translate-x-1/2 flex-col items-center gap-3 pointer-events-none"
        aria-hidden="true"
      >
        <span className="text-[10px] uppercase tracking-[0.4em] text-neutral-500">
          Scroll
        </span>
        <div className="relative w-px h-14 overflow-hidden" style={{ background: "#E7E5E4" }}>
          <motion.div
            className="absolute left-0 right-0 top-0 h-4"
            style={{ background: primary }}
            animate={{ y: ["-16px", "56px"] }}
            transition={{ duration: 1.8, repeat: Infinity, ease: "easeInOut" }}
          />
        </div>
      </motion.div>
    </section>
  );
}
