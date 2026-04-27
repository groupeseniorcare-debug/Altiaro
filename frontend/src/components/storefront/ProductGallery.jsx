import React, { useEffect, useMemo, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ShoppingBagOpen, MagnifyingGlassPlus, X } from "@phosphor-icons/react";
import { useProductColor } from "../../lib/ProductColorContext";
import { getProductGalleryForColor } from "../../lib/productImage";

/**
 * Premium product gallery — image principale + vignettes + zoom modal.
 *
 * Lot H Fix 4 — variant-aware. Si le composant est wrappé par
 * `<ProductColorProvider product={...}>`, la galerie réagit au changement de
 * couleur sélectionnée et affiche les images de `generated_images_by_variant
 * [selectedColor]` avec un fade transition. Fallback transparent sur la
 * galerie classique si aucune variant image n'existe.
 *
 * Backward compat : si `product` n'est PAS passé en prop, le composant utilise
 * uniquement `images` (comportement legacy, aucune réactivité).
 */
export default function ProductGallery({
  images: imagesProp = [],
  name,
  design,
  styledImages = [],
  product = null, // Lot H — passer le produit complet pour activer la réactivité variant-aware
}) {
  const primary = "#0A0A0A";
  const accent = "#F5F5F5";
  const [idx, setIdx] = useState(0);
  const [zoomOpen, setZoomOpen] = useState(false);
  const { selectedColor, hasVariantImages } = useProductColor();

  // Calcule les images affichées : variant-aware si possible, sinon legacy prop
  const images = useMemo(() => {
    if (product && hasVariantImages && selectedColor) {
      const colorImages = getProductGalleryForColor(product, selectedColor);
      if (colorImages.length > 0) return colorImages;
    }
    return imagesProp;
  }, [product, hasVariantImages, selectedColor, imagesProp]);

  // Reset thumb index quand on change de couleur (la 1ère image n'est plus la même)
  useEffect(() => {
    setIdx(0);
  }, [selectedColor]);

  const hasImages = images && images.length > 0;
  const activeImg = hasImages ? images[idx] : null;

  // Map styled image URLs to their AI style for better alt text.
  // En mode variant-aware, on utilise `product.generated_images_by_variant[selectedColor]`,
  // sinon `styledImages` (passé en prop par StorefrontProduct).
  const styleByUrl = useMemo(() => {
    const out = {};
    if (product && selectedColor && product.generated_images_by_variant?.[selectedColor]) {
      product.generated_images_by_variant[selectedColor].forEach((g) => {
        if (g?.url) out[g.url] = g.style;
      });
    }
    (styledImages || []).forEach((g) => {
      if (g?.url && !out[g.url]) out[g.url] = g.style;
    });
    return out;
  }, [styledImages, product, selectedColor]);

  const styleLabel = {
    closeup: "gros plan détail",
    studio: "vue studio éditoriale",
    lifestyle: "mise en situation dans un intérieur",
    in_use: "en situation d'utilisation",
  };
  const altFor = (img, i) => {
    const style = styleByUrl[img];
    if (style && styleLabel[style]) return `${name} — ${styleLabel[style]}`;
    return `${name} — vue ${i + 1}`;
  };

  return (
    <div className="md:sticky md:top-24" data-testid="product-gallery" data-selected-color={selectedColor || ""}>
      {/* Main image */}
      <div
        className="aspect-square overflow-hidden relative group mb-3"
        style={{ background: accent, borderRadius: "2px" }}
      >
        {activeImg ? (
          <>
            {/* Lot H Fix 4 — fade transition entre les images de couleurs différentes */}
            <AnimatePresence mode="wait" initial={false}>
              <motion.img
                key={`${selectedColor || "default"}-${idx}`}
                src={activeImg}
                alt={altFor(activeImg, idx)}
                className="w-full h-full object-cover"
                loading={idx === 0 ? "eager" : "lazy"}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.32, ease: "easeOut" }}
              />
            </AnimatePresence>
            <button
              type="button"
              onClick={() => setZoomOpen(true)}
              className="absolute top-4 right-4 w-10 h-10 bg-white flex items-center justify-center opacity-0 group-hover:opacity-100 transition shadow-sm"
              style={{ color: primary, borderRadius: "2px" }}
              aria-label="Agrandir"
              data-testid="gallery-zoom"
            >
              <MagnifyingGlassPlus size={16} weight="regular" />
            </button>
          </>
        ) : (
          <div className="w-full h-full flex items-center justify-center" style={{ color: "#D4D4D4" }}>
            <ShoppingBagOpen size={80} weight="thin" />
          </div>
        )}
      </div>

      {/* Thumbnails */}
      {images.length > 1 && (
        <div className="grid grid-cols-5 gap-2" data-testid="gallery-thumbs">
          {images.slice(0, 5).map((img, i) => (
            <button
              key={`${selectedColor || "default"}-${i}`}
              type="button"
              onClick={() => setIdx(i)}
              data-testid={`gallery-thumb-${i}`}
              className="aspect-square overflow-hidden transition"
              style={{
                background: accent,
                borderRadius: "2px",
                border: `1.5px solid ${i === idx ? primary : "transparent"}`,
              }}
              aria-label={`Vue ${i + 1}`}
            >
              <img src={img} alt={altFor(img, i)} className="w-full h-full object-cover" loading="lazy" />
            </button>
          ))}
        </div>
      )}

      {/* Zoom modal */}
      {zoomOpen && activeImg && (
        <div
          className="fixed inset-0 z-50 bg-black/90 flex items-center justify-center p-6"
          onClick={() => setZoomOpen(false)}
          data-testid="gallery-zoom-modal"
        >
          <button
            type="button"
            onClick={() => setZoomOpen(false)}
            className="absolute top-5 right-5 w-11 h-11 rounded-full bg-white/10 text-white flex items-center justify-center hover:bg-white/20"
            aria-label="Fermer"
          >
            <X size={22} />
          </button>
          <img
            src={activeImg}
            alt={name}
            className="max-w-full max-h-full object-contain"
            style={{ borderRadius: "2px" }}
            onClick={(e) => e.stopPropagation()}
          />
        </div>
      )}
      {/* design prop kept for interface parity */}
      {false && <span style={{ background: design ? "" : "" }} />}
    </div>
  );
}
