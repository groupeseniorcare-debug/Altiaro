import React from "react";
import { designAccents } from "./storefrontUtils";

/**
 * Editorial magazine-style mosaic — 4 asymmetric tiles built from the product
 * gallery. Used between the hero and the narrative sections so the product
 * page never feels text-heavy. Pure monochrome (white + #F5F5F5 frames).
 *
 * Requires `images` (>= 2). Gracefully hides itself otherwise.
 */
export default function ProductEditorialMosaic({ images = [], productName, design, captions }) {
  const { primary, textMuted, fontHeading } = designAccents(design);
  const accent = "#F5F5F5";
  const pool = (images || []).filter(Boolean);
  if (pool.length < 2) return null;

  const pick = (i) => pool[i % pool.length];

  const defaultCaptions = [
    { eyebrow: "Vu de près", title: "La matière, sans filtre.", body: "Textile dense, couture régulière, finitions minutieuses — chaque détail est pensé pour durer." },
    { eyebrow: "Dans le geste", title: "Conçu pour le quotidien.", body: "Une prise en main évidente, sans notice, sans apprentissage. La technologie reste discrète." },
    { eyebrow: "En situation", title: "Au cœur de la maison.", body: "Pensé pour s'intégrer naturellement dans le décor, sans jamais évoquer le matériel médical." },
    { eyebrow: "Détail", title: "La preuve par le détail.", body: "Les détails qui ne se voient pas sont ceux qui se ressentent le plus au quotidien." },
  ];
  const caps = (Array.isArray(captions) && captions.length >= 4) ? captions : defaultCaptions;

  return (
    <section
      className="mb-24 md:mb-32"
      data-testid="product-editorial-mosaic"
      aria-label="Galerie éditoriale du produit"
    >
      {/* Eyebrow */}
      <div className="flex items-center gap-3 mb-5">
        <span className="h-px w-8" style={{ background: primary }} />
        <span className="text-[10px] uppercase tracking-[0.4em]" style={{ color: primary }}>
          En images
        </span>
      </div>
      <h2
        className="text-[30px] md:text-[44px] leading-[1.05] tracking-[-0.015em] mb-10 md:mb-14 max-w-3xl"
        style={{ fontFamily: `"${fontHeading}", Georgia, serif`, color: primary }}
      >
        L'objet dans le détail.
      </h2>

      {/* Asymmetric mosaic — magazine feel */}
      <div className="grid grid-cols-12 gap-3 md:gap-4">
        {/* Tile 1 — large portrait */}
        <figure className="col-span-12 md:col-span-7 md:row-span-2">
          <div
            className="aspect-[4/5] md:aspect-[5/6] overflow-hidden"
            style={{ background: accent, borderRadius: "2px" }}
          >
            <img
              src={pick(0)}
              alt={`${productName} — ${caps[0].title}`}
              className="w-full h-full object-cover transition-transform duration-[1200ms] ease-out hover:scale-[1.02]"
              loading="lazy"
            />
          </div>
          <figcaption className="mt-4 max-w-md">
            <div className="text-[10px] uppercase tracking-[0.35em] mb-2" style={{ color: primary }}>
              {caps[0].eyebrow}
            </div>
            <div className="text-[20px] md:text-[24px] leading-[1.2]" style={{ fontFamily: `"${fontHeading}", serif`, color: primary }}>
              {caps[0].title}
            </div>
            <p className="text-[13.5px] mt-2 leading-[1.6]" style={{ color: textMuted }}>
              {caps[0].body}
            </p>
          </figcaption>
        </figure>

        {/* Tile 2 — landscape top right */}
        <figure className="col-span-12 md:col-span-5">
          <div
            className="aspect-[4/3] overflow-hidden"
            style={{ background: accent, borderRadius: "2px" }}
          >
            <img
              src={pick(1)}
              alt={`${productName} — ${caps[1].title}`}
              className="w-full h-full object-cover transition-transform duration-[1200ms] ease-out hover:scale-[1.02]"
              loading="lazy"
            />
          </div>
          <figcaption className="mt-4">
            <div className="text-[10px] uppercase tracking-[0.35em] mb-2" style={{ color: primary }}>
              {caps[1].eyebrow}
            </div>
            <div className="text-[18px] md:text-[20px] leading-[1.25]" style={{ fontFamily: `"${fontHeading}", serif`, color: primary }}>
              {caps[1].title}
            </div>
          </figcaption>
        </figure>

        {/* Tile 3 — quote / caption band (bottom right) */}
        <figure className="col-span-12 md:col-span-5 flex flex-col">
          <div
            className="aspect-[4/3] overflow-hidden"
            style={{ background: accent, borderRadius: "2px" }}
          >
            <img
              src={pick(2)}
              alt={`${productName} — ${caps[2].title}`}
              className="w-full h-full object-cover transition-transform duration-[1200ms] ease-out hover:scale-[1.02]"
              loading="lazy"
            />
          </div>
          <figcaption className="mt-4">
            <div className="text-[10px] uppercase tracking-[0.35em] mb-2" style={{ color: primary }}>
              {caps[2].eyebrow}
            </div>
            <div className="text-[18px] md:text-[20px] leading-[1.25]" style={{ fontFamily: `"${fontHeading}", serif`, color: primary }}>
              {caps[2].title}
            </div>
            <p className="text-[13.5px] mt-2 leading-[1.6]" style={{ color: textMuted }}>
              {caps[2].body}
            </p>
          </figcaption>
        </figure>
      </div>

      {/* Fourth wide banner */}
      <figure className="mt-4 md:mt-5" style={{ borderTop: `1px solid ${"#E5E5E5"}` }}>
        <div
          className="aspect-[21/9] overflow-hidden mt-5"
          style={{ background: accent, borderRadius: "2px" }}
        >
          <img
            src={pick(3)}
            alt={`${productName} — ${caps[3].title}`}
            className="w-full h-full object-cover transition-transform duration-[1600ms] ease-out hover:scale-[1.03]"
            loading="lazy"
          />
        </div>
        <figcaption className="mt-5 flex flex-wrap items-baseline justify-between gap-4">
          <div>
            <div className="text-[10px] uppercase tracking-[0.35em] mb-2" style={{ color: primary }}>
              {caps[3].eyebrow}
            </div>
            <div className="text-[22px] md:text-[28px] leading-[1.2]" style={{ fontFamily: `"${fontHeading}", serif`, color: primary }}>
              {caps[3].title}
            </div>
          </div>
          <p className="text-[13.5px] leading-[1.6] max-w-lg" style={{ color: textMuted }}>
            {caps[3].body}
          </p>
        </figcaption>
      </figure>
    </section>
  );
}
