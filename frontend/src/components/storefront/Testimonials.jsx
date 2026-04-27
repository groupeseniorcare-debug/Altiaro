/**
 * Lot G Fix 1 — Testimonials premium converti en Embla Carousel infini.
 *
 * - 6 portraits IA (Margot, Heinrich, Isabelle, Sylvain, Catherine, Roland)
 *   stockés dans `design.testimonials_premium` après run du pipeline +
 *   les scripts lotG_fix1_3more_portraits.py.
 * - Embla `loop: true` + `dragFree: true` + autoplay manuel via setInterval
 *   (scrollNext toutes les ~3.5 s, pause on hover).
 * - Cards 280×420 mobile / 320×480 desktop, full-bleed image, dark gradient
 *   en haut (étoiles) et en bas (citation + nom).
 * - Fallback : DEFAULT mocks Unsplash (FR uniquement). Section auto-skipped
 *   si lang ≠ fr et pas de testimonials premium en DB.
 */
import React, { useCallback, useEffect, useRef, useState } from "react";
import useEmblaCarousel from "embla-carousel-react";
import { Star, CaretLeft, CaretRight } from "@phosphor-icons/react";
import { designAccents } from "./storefrontUtils";
import { t } from "../../lib/i18n";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "";

function resolveImage(raw) {
  if (!raw) return null;
  if (raw.startsWith("http://") || raw.startsWith("https://")) return raw;
  if (raw.startsWith("/api/")) return `${BACKEND_URL}${raw}`;
  return raw;
}

const DEFAULT = [
  { name: "Françoise D.", location: "Lyon · 72 ans", role: "Cliente · 72 ans", rating: 5,
    image: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=600&h=900&fit=crop&crop=faces",
    text: "J'hésitais à commander en ligne à mon âge. Le conseiller a été patient, et la livraison s'est parfaitement passée." },
  { name: "Marc & Jeannine L.", location: "Rennes · 78 ans", role: "Couple · 78 ans", rating: 5,
    image: "https://images.unsplash.com/photo-1556911220-bff31c812dba?w=600&h=900&fit=crop&crop=faces",
    text: "Nous avons équipé la salle de bain de ma belle-mère. Tout est arrivé en 2 jours, bien emballé. Un vrai soulagement." },
  { name: "Hélène P.", location: "Bordeaux · 65 ans", role: "Cliente · 65 ans", rating: 5,
    image: "https://images.unsplash.com/photo-1580489944761-15a19d654956?w=600&h=900&fit=crop&crop=faces",
    text: "Service client exceptionnel. J'ai appelé pour un conseil, on m'a rappelée et orientée sans rien essayer de me vendre." },
  { name: "Gérard M.", location: "Marseille · 80 ans", role: "Client · 80 ans", rating: 5,
    image: "https://images.unsplash.com/photo-1541534401786-2077eed87a74?w=600&h=900&fit=crop&crop=faces",
    text: "Prix équitable, livraison rapide et un vrai suivi. C'est rare aujourd'hui d'être traité comme un client et pas un numéro." },
  { name: "Catherine V.", location: "Nantes · 68 ans", role: "Cliente · 68 ans", rating: 5,
    image: "https://images.unsplash.com/photo-1551836022-deb4988cc6c0?w=600&h=900&fit=crop&crop=faces",
    text: "La qualité des produits est au rendez-vous. J'apprécie la transparence sur les matériaux et les fabricants." },
  { name: "Thomas K.", location: "Paris · 45 ans", role: "Aidant familial", rating: 5,
    image: "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=600&h=900&fit=crop&crop=faces",
    text: "Une vraie tranquillité d'esprit pour accompagner mon père. Simple à mettre en place, interface claire." },
];

function ReviewCard({ item }) {
  const text = typeof item.text === "string" ? item.text : item.quote?.fr || "";
  const img = resolveImage(item.image || item.avatar || item.photo);
  return (
    <div
      className="flex-shrink-0 w-[280px] md:w-[320px] h-[420px] md:h-[480px] rounded-2xl overflow-hidden relative group/card"
      data-testid="review-card"
    >
      {img ? (
        <img
          src={img}
          alt={item.name}
          loading="lazy"
          className="absolute inset-0 w-full h-full object-cover transition-transform duration-700 group-hover/card:scale-105"
        />
      ) : (
        <div className="absolute inset-0" style={{ background: "linear-gradient(135deg, #1a1a1a, #3a3a3a)" }} />
      )}

      {/* Top gradient + stars */}
      <div className="absolute top-0 left-0 right-0 p-3 md:p-4 bg-gradient-to-b from-black/40 to-transparent">
        <div className="flex gap-0.5">
          {[...Array(item.rating || 5)].map((_, i) => (
            <Star key={i} size={11} weight="fill" className="text-white" />
          ))}
        </div>
      </div>

      {/* Bottom gradient + quote */}
      <div className="absolute bottom-0 left-0 right-0 p-5 pt-24 bg-gradient-to-t from-black/80 via-black/50 to-transparent">
        <p className="text-white/90 text-[13px] leading-[1.6] mb-4 line-clamp-3">
          &ldquo;{text}&rdquo;
        </p>
        <div>
          <p className="text-white font-semibold text-sm">{item.name}</p>
          <p className="text-white/60 mt-0.5 text-xs">{item.role || item.location}</p>
        </div>
      </div>
    </div>
  );
}

export function Testimonials({ design, lang }) {
  const { primary, fontHeading } = designAccents(design);
  const premium = design?.testimonials_premium;
  const legacy = design?.testimonials?.items || design?.testimonials;
  const hasPremium = Array.isArray(premium) && premium.length > 0;
  const hasLegacy = !hasPremium && Array.isArray(legacy) && legacy.length > 0;
  const hasReal = hasPremium || hasLegacy;
  if (!hasReal && (lang || "fr") !== "fr") return null;

  const list = hasPremium
    ? premium.map((p) => ({
        name: p.name || "",
        location: p.city || p.location || (p.age ? `${p.age} ans` : ""),
        role: p.city && p.age ? `${p.city} · ${p.age} ans` : (p.role || p.location || ""),
        rating: p.rating || 5,
        image: p.image || p.avatar || p.photo,
        text: p.text || p.quote || "",
      }))
    : hasLegacy
    ? legacy
    : DEFAULT;

  // Embla setup — loop + dragFree + autoplay manuel
  const [emblaRef, emblaApi] = useEmblaCarousel({
    loop: true,
    align: "start",
    dragFree: true,
    skipSnaps: false,
    containScroll: false,
  });
  const [isHovered, setIsHovered] = useState(false);
  const intervalRef = useRef(null);

  const scrollPrev = useCallback(() => emblaApi && emblaApi.scrollPrev(), [emblaApi]);
  const scrollNext = useCallback(() => emblaApi && emblaApi.scrollNext(), [emblaApi]);

  // Autoplay : scroll vers la suite toutes les 3.8 s, pause au survol
  useEffect(() => {
    if (!emblaApi) return undefined;
    const start = () => {
      stop();
      intervalRef.current = setInterval(() => {
        if (!isHovered) emblaApi.scrollNext();
      }, 3800);
    };
    const stop = () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
    start();
    return stop;
  }, [emblaApi, isHovered]);

  return (
    <section className="py-24 md:py-36 bg-white overflow-hidden" data-testid="storefront-testimonials">
      <div className="max-w-7xl mx-auto px-6 mb-14 md:mb-16">
        <div className="flex items-end justify-between flex-wrap gap-6">
          <div>
            <div className="flex items-center gap-3 mb-5">
              <span className="h-px w-10" style={{ background: primary }} />
              <span className="text-[11px] uppercase tracking-[0.4em]" style={{ color: primary }}>
                {t(lang, "testimonials_eyebrow")}
              </span>
            </div>
            <h2
              className="text-[40px] md:text-[56px] lg:text-[64px] leading-[1.02] tracking-[-0.02em]"
              style={{ fontFamily: `"${fontHeading}", serif`, color: primary }}
            >
              {t(lang, "testimonials_heading_line1")}<br />{t(lang, "testimonials_heading_line2")}
            </h2>
          </div>
          <div className="flex items-center gap-2 text-neutral-500">
            <div className="flex" style={{ color: "#F5B800" }}>
              {[...Array(5)].map((_, i) => <Star key={i} size={14} weight="fill" />)}
            </div>
            <span className="text-[13px] font-semibold" style={{ color: primary }}>4.8/5</span>
            <span className="text-[13px]">· 2 143 {t(lang, "testimonials_verified_reviews")}</span>
          </div>
        </div>
      </div>

      {/* Embla carousel — full width, pause on hover, infinite loop */}
      <div
        className="relative"
        data-testid="reviews-carousel"
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
      >
        <div className="overflow-hidden" ref={emblaRef}>
          <div className="flex gap-5 md:gap-6 px-6 md:px-10">
            {list.map((it, i) => (
              <ReviewCard key={i} item={it} />
            ))}
          </div>
        </div>

        {/* Nav buttons (desktop only) */}
        <div className="hidden md:flex items-center justify-end gap-2 max-w-7xl mx-auto px-10 mt-8">
          <button
            type="button"
            onClick={scrollPrev}
            aria-label="Précédent"
            data-testid="reviews-prev"
            className="w-11 h-11 rounded-full border border-neutral-300 flex items-center justify-center hover:border-neutral-900 transition"
          >
            <CaretLeft size={16} weight="bold" />
          </button>
          <button
            type="button"
            onClick={scrollNext}
            aria-label="Suivant"
            data-testid="reviews-next"
            className="w-11 h-11 rounded-full border border-neutral-300 flex items-center justify-center hover:border-neutral-900 transition"
          >
            <CaretRight size={16} weight="bold" />
          </button>
        </div>
      </div>
    </section>
  );
}

export default Testimonials;
