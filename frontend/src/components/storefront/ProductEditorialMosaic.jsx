import React from "react";
import { designAccents } from "./storefrontUtils";
import { useProductColor } from "../../lib/ProductColorContext";

/**
 * Editorial magazine-style mosaic — 4 asymmetric tiles built from the product
 * gallery. Used between the hero and the narrative sections so the product
 * page never feels text-heavy. Pure monochrome (white + #F5F5F5 frames).
 *
 * Requires `images` (>= 2). Gracefully hides itself otherwise.
 *
 * Lot H Fix 4 — variant-aware. Si un Context `<ProductColorProvider>` parent
 * fournit une couleur sélectionnée, on lit `product.generated_images_by_variant
 * [selectedColor]` pour assigner closeup / studio / lifestyle / in_use plutôt
 * que `styledImages` legacy. Le visiteur voit la mosaïque entière dans la
 * couleur qu'il a choisie.
 */
export default function ProductEditorialMosaic({ images = [], styledImages = [], productName, design, captions, product = null }) {
  const { primary, textMuted, fontHeading } = designAccents(design);
  const accent = "#F5F5F5";
  const { selectedColor, hasVariantImages } = useProductColor();

  // Lot H Fix 4 — pick the variant-specific styled images if available
  const variantStyledImages = React.useMemo(() => {
    if (product && hasVariantImages && selectedColor) {
      const arr = product.generated_images_by_variant?.[selectedColor];
      if (Array.isArray(arr) && arr.length) return arr;
    }
    return styledImages;
  }, [product, hasVariantImages, selectedColor, styledImages]);

  const pool = (images || []).filter(Boolean);
  if (pool.length < 2 && (!variantStyledImages || variantStyledImages.length < 2)) return null;

  // Smart assignment: prefer specific AI styles per tile when available.
  // Lot I Phase 2.2 — `studio_main` est l'alias canonique de `studio`
  // dans le nouveau pipeline 8-styles (cf. product_variant_pipeline.py).
  const STYLE_ALIASES = { studio: ["studio", "studio_main"], studio_main: ["studio_main", "studio"] };
  const byStyle = (name) => {
    const candidates = STYLE_ALIASES[name] || [name];
    for (const c of candidates) {
      const hit = (variantStyledImages || []).find((g) => g && g.style === c && g.url);
      if (hit) return hit.url;
    }
    return null;
  };
  const closeup = byStyle("closeup");
  const studio = byStyle("studio");
  const lifestyle = byStyle("lifestyle");
  const inUse = byStyle("in_use") || lifestyle;
  // Lot H — fallback : utiliser les images de la couleur sélectionnée en priorité
  const variantPool = (variantStyledImages || []).map((g) => g?.url).filter(Boolean);
  const finalPool = variantPool.length ? variantPool : pool;
  const fallback = (i) => finalPool[i % finalPool.length];
  // Tile 1 (big portrait, "Vu de près") = closeup
  // Tile 2 ("Dans le geste") = second closeup or in_use
  // Tile 3 ("En situation") = lifestyle or in_use
  // Tile 4 banner ("Détail") = studio
  const tile0 = closeup || fallback(0);
  const tile1 = (variantStyledImages || []).filter((g) => g.style === "closeup")[1]?.url
    || inUse
    || fallback(1);
  const tile2 = lifestyle || inUse || fallback(2);
  const tile3 = studio || fallback(3);
  const pick = (i) => [tile0, tile1, tile2, tile3][i] || fallback(i);

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
