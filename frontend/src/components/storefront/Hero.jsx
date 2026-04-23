import React from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowRight, ShieldCheck, Star, Truck, Phone } from "@phosphor-icons/react";
import { designText } from "./storefrontUtils";
import { t } from "../../lib/i18n";

/**
 * Hero premium avec image — split layout desktop, empilé en mobile.
 *  - Eyebrow (tagline / catégorie)
 *  - H1 avec titre principal
 *  - Sous-titre
 *  - 2 CTAs (primary → collection principale, secondary → histoire)
 *  - Trust row (avis, livraison, service, garantie)
 *  - Image hero à droite (fallback Unsplash silver-eco)
 *
 * Alimenté par :
 *  - design.hero.title / subtitle / cta_label / cta_secondary_label / image / eyebrow
 *  - design.hero.rating = { score, count }
 */
export function Hero({ site, design, lang }) {
  const { siteId } = useParams();
  const heroTitle = designText(design, "hero.title", lang)
    || site?.name
    || t(lang, "shop_title");
  const heroSub = designText(design, "hero.subtitle", lang)
    || "Des produits sélectionnés avec soin pour préserver votre autonomie, votre confort et votre sérénité au quotidien.";
  const heroCta = designText(design, "hero.cta_label", lang) || "Découvrir la collection";
  const heroCta2 = designText(design, "hero.cta_secondary_label", lang) || "Notre histoire";
  const eyebrow = designText(design, "hero.eyebrow", lang)
    || design?.brand?.tagline
    || site?.niche
    || "La maison bienveillante";
  const trustLine = designText(design, "hero.trust_line", lang) || "Conseillers humains · Lun–Ven 9h–18h";
  const heroImage = designText(design, "hero.image", lang)
    || design?.hero?.image
    || "https://images.unsplash.com/photo-1447452001602-7090c7ab2db3?w=1200&auto=format&fit=crop";

  const rating = design?.hero?.rating || { score: 4.8, count: 2143 };

  const primary = design?.brand?.primary_color || "#B84B31";
  const accent = design?.brand?.accent_color || "#F5F2EB";
  const fontHeading = design?.brand?.font_heading || "Fraunces";
  const bg = design?.brand?.background_color || "#FDFBF7";
  const textColor = design?.brand?.text_color || "#1C1917";

  return (
    <section
      className="relative overflow-hidden"
      style={{ background: bg, color: textColor }}
      data-testid="storefront-hero"
    >
      <div className="max-w-7xl mx-auto px-6 md:px-10 pt-14 md:pt-20 pb-12 md:pb-24 grid grid-cols-1 lg:grid-cols-[1.1fr_1fr] gap-10 lg:gap-16 items-center">
        {/* ---------- LEFT : Copy ---------- */}
        <div className="max-w-xl lg:max-w-none order-2 lg:order-1">
          <div
            className="inline-flex items-center gap-2 text-[11px] uppercase tracking-[0.25em] mb-5 font-medium px-3 py-1.5 rounded-full"
            style={{ background: `${primary}14`, color: primary }}
            data-testid="hero-eyebrow"
          >
            <span className="w-1.5 h-1.5 rounded-full" style={{ background: primary }} />
            {eyebrow}
          </div>

          <h1
            className="text-[42px] md:text-[56px] lg:text-[68px] font-semibold leading-[1.04] tracking-[-0.02em]"
            style={{ fontFamily: `"${fontHeading}", Georgia, serif` }}
            data-testid="hero-title"
          >
            {heroTitle}
          </h1>

          <p
            className="text-lg md:text-xl mt-6 leading-relaxed max-w-xl"
            style={{ color: `${textColor}cc` }}
            data-testid="hero-subtitle"
          >
            {heroSub}
          </p>

          <div className="mt-8 flex flex-col sm:flex-row items-start sm:items-center gap-3">
            <Link
              to={`/shop/${siteId}#collections`}
              data-testid="hero-cta-primary"
              className="inline-flex items-center gap-2 h-14 px-8 rounded-full text-white font-medium transition-all hover:opacity-90 active:scale-[0.98] text-[15px] shadow-sm"
              style={{ background: primary }}
            >
              {heroCta}
              <ArrowRight size={16} weight="bold" />
            </Link>
            <Link
              to={`/shop/${siteId}#story`}
              data-testid="hero-cta-secondary"
              className="inline-flex items-center gap-2 h-14 px-7 rounded-full border font-medium transition text-[15px] hover:bg-neutral-50"
              style={{ borderColor: "#E7E5E4", color: textColor }}
            >
              {heroCta2}
            </Link>
          </div>

          {/* Trust strip */}
          <div className="mt-10 flex flex-wrap items-center gap-x-8 gap-y-4">
            {rating?.score && (
              <div className="flex items-center gap-2" data-testid="hero-rating">
                <div className="flex" style={{ color: "#F59E0B" }}>
                  {[...Array(5)].map((_, i) => (
                    <Star key={i} size={16} weight="fill" />
                  ))}
                </div>
                <div className="text-sm">
                  <span className="font-semibold">{rating.score}/5</span>
                  <span className="text-neutral-500"> · {rating.count?.toLocaleString("fr-FR")} avis</span>
                </div>
              </div>
            )}
            <div className="flex items-center gap-2 text-sm" style={{ color: `${textColor}b3` }}>
              <Truck size={16} weight="bold" style={{ color: primary }} />
              Livraison offerte
            </div>
            <div className="flex items-center gap-2 text-sm" style={{ color: `${textColor}b3` }}>
              <ShieldCheck size={16} weight="bold" style={{ color: primary }} />
              Garantie 2 ans
            </div>
            <div className="flex items-center gap-2 text-sm" style={{ color: `${textColor}b3` }}>
              <Phone size={16} weight="bold" style={{ color: primary }} />
              {trustLine}
            </div>
          </div>
        </div>

        {/* ---------- RIGHT : Visual ---------- */}
        <div className="relative order-1 lg:order-2" data-testid="hero-image">
          <div
            className="relative aspect-[4/5] md:aspect-[5/6] rounded-[32px] overflow-hidden"
            style={{ background: accent }}
          >
            <img
              src={heroImage}
              alt={heroTitle}
              className="w-full h-full object-cover"
              loading="eager"
              fetchPriority="high"
            />
            {/* Floating trust card */}
            <div
              className="absolute bottom-5 left-5 right-5 md:bottom-8 md:left-8 md:right-auto md:max-w-[280px] bg-white/95 backdrop-blur rounded-2xl p-4 shadow-xl"
              data-testid="hero-floating-card"
            >
              <div className="flex items-center gap-3">
                <div
                  className="w-11 h-11 rounded-full flex items-center justify-center shrink-0"
                  style={{ background: `${primary}15`, color: primary }}
                >
                  <ShieldCheck size={22} weight="duotone" />
                </div>
                <div>
                  <div className="text-sm font-semibold text-neutral-900 leading-tight">
                    Satisfait ou remboursé
                  </div>
                  <div className="text-xs text-neutral-500 mt-0.5">
                    14 jours · retour gratuit
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Decorative accent */}
          <div
            className="absolute -top-8 -right-8 w-28 h-28 rounded-full opacity-40 blur-2xl -z-10 hidden md:block"
            style={{ background: primary }}
          />
        </div>
      </div>
    </section>
  );
}
