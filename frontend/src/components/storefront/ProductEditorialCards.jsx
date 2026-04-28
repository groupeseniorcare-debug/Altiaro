/**
 * Phase 2.5 (Tâche A) — Bloc editorial produit restauré en version allégée.
 *
 * 1 hero vertical (image pleine largeur + titre + 1-2 phrases)
 * + 3 cards horizontales (image + titre court + 1 phrase)
 *
 * Lit `product.editorial_cards` généré par
 * `services/product_content_ai.py::generate_product_editorial_cards` (Haiku).
 * Chaque bloc a un `image_style` qui pointe vers une image IA de la variante
 * courante (pipeline 8-styles) : on passe par `getImageByStyleForColor()`.
 *
 * Filtre `qa_passed === false` appliqué en amont dans `productImage.js`.
 *
 * Si `editorial_cards` manquant ou corrompu → composant masqué.
 */
import React from "react";

function _itemUrl(item) {
  if (!item) return null;
  if (typeof item === "string") return item;
  if (item.qa_passed === false) return null;
  return item.url || item.image || item.src || null;
}

function pickImageByStyle(product, colorSlug, style) {
  if (!product) return null;
  const pool =
    (colorSlug && product.generated_images_by_variant?.[colorSlug]) ||
    product.generated_images ||
    [];
  const match = pool.find((i) => i && (i.style === style) && _itemUrl(i));
  if (match) return _itemUrl(match);
  // fallback to another style with same family priority
  const families = {
    wide_lifestyle: ["wide_lifestyle", "lifestyle", "context_room"],
    lifestyle:       ["lifestyle", "wide_lifestyle", "on_sofa", "on_bed", "context_room"],
    closeup:         ["closeup", "texture_closeup", "detail"],
    detail:          ["detail", "closeup", "texture_closeup"],
    in_use:          ["in_use", "lifestyle"],
    side_profile:    ["side_profile", "alt_angle", "detail"],
    texture_closeup: ["texture_closeup", "closeup", "detail"],
    folded_display:  ["folded_display", "studio_main", "stacked"],
    on_sofa:         ["on_sofa", "lifestyle", "on_bed"],
    on_bed:          ["on_bed", "on_sofa", "lifestyle"],
    on_chair:        ["on_chair", "lifestyle"],
    stacked:         ["stacked", "detail"],
    context_room:    ["context_room", "wide_lifestyle", "lifestyle"],
  };
  for (const alt of families[style] || []) {
    const a = pool.find((i) => i && i.style === alt && _itemUrl(i));
    if (a) return _itemUrl(a);
  }
  // ultimate fallback : any generated image or source image
  const any = pool.find((i) => _itemUrl(i));
  if (any) return _itemUrl(any);
  return (product.images && product.images[0]) || null;
}

export default function ProductEditorialCards({ product, colorSlug, design }) {
  const ed = product?.editorial_cards;
  if (!ed || !ed.hero || !Array.isArray(ed.cards) || ed.cards.length < 2) return null;

  const fontHeading =
    design?.brand?.font_pair?.heading ||
    "'Cormorant Garamond', 'Cormorant', serif";
  const accent = design?.brand?.palette?.accent || "#9F6E50";

  const heroImg = pickImageByStyle(product, colorSlug, ed.hero.image_style || "wide_lifestyle");

  return (
    <section
      className="my-16 md:my-24"
      data-testid="product-editorial-cards"
      aria-labelledby="editorial-hero-title"
    >
      {/* Hero — 1 big vertical image + title + desc */}
      {heroImg && (
        <div className="relative overflow-hidden mb-16 md:mb-20" style={{ borderRadius: "2px" }}>
          <div
            className="w-full"
            style={{
              aspectRatio: "16 / 9",
              background: `#F5F2EB url(${heroImg}) center/cover no-repeat`,
              minHeight: 380,
            }}
            role="img"
            aria-label={ed.hero.title}
          />
          <div className="mt-10 md:mt-12 max-w-3xl">
            <div
              className="text-[10.5px] uppercase tracking-[0.45em] mb-3"
              style={{ color: "#9C8C7C" }}
            >
              Éditorial
            </div>
            <h2
              id="editorial-hero-title"
              className="text-[30px] md:text-[42px] leading-[1.08] font-light mb-4"
              style={{ fontFamily: fontHeading, color: "#0A0A0A" }}
            >
              {ed.hero.title}
            </h2>
            {ed.hero.description && (
              <p
                className="text-[15px] md:text-[16.5px] leading-[1.65]"
                style={{ color: "#525252" }}
              >
                {ed.hero.description}
              </p>
            )}
          </div>
        </div>
      )}

      {/* 3 cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 md:gap-7">
        {ed.cards.slice(0, 3).map((c, i) => {
          const img = pickImageByStyle(product, colorSlug, c.image_style || "detail");
          return (
            <article
              key={i}
              className="group"
              data-testid={`editorial-card-${i}`}
            >
              {img && (
                <div
                  className="w-full mb-6 transition-opacity group-hover:opacity-95"
                  style={{
                    aspectRatio: "4 / 5",
                    background: `#F5F2EB url(${img}) center/cover no-repeat`,
                    borderRadius: "2px",
                  }}
                  role="img"
                  aria-label={c.title}
                />
              )}
              <div className="px-1">
                <div
                  className="w-6 h-px mb-4"
                  style={{ background: accent, opacity: 0.6 }}
                />
                <h3
                  className="text-[20px] md:text-[22px] leading-[1.2] font-light mb-3"
                  style={{ fontFamily: fontHeading, color: "#0A0A0A" }}
                >
                  {c.title}
                </h3>
                <p
                  className="text-[13.5px] leading-[1.65]"
                  style={{ color: "#525252" }}
                >
                  {c.description}
                </p>
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}
