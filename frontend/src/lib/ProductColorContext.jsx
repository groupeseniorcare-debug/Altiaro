/**
 * Lot H Fix 4 — Context React pour propager la couleur de variante sélectionnée.
 *
 * Permet à TOUS les composants storefront enfants de la fiche produit
 * (ProductGallery, ProductEditorialMosaic, LifestyleEditorial, NarrativeProduct,
 * ProductSEOBlocks, etc.) d'afficher des images cohérentes avec la couleur
 * choisie par le client.
 *
 * Architecture :
 *   StorefrontProduct
 *     └─ ProductColorProvider initialColor={defaultColorSlug}
 *          ├─ ProductGallery → consume + render images of selected color
 *          ├─ VariantPicker  → setSelectedColor(slug) on click
 *          ├─ ProductEditorialMosaic → consume
 *          ├─ LifestyleEditorial → consume
 *          └─ ...
 *
 * Si le produit n'a pas de `generated_images_by_variant`, le Provider
 * fonctionne quand même (selectedColor = null) et tous les composants
 * tomberont sur les images par défaut (`generated_images`).
 */
import React, { createContext, useContext, useMemo, useState, useCallback } from "react";
import { slugify } from "./slugify";

const ProductColorContext = createContext({
  selectedColor: null,           // slug normalisé (ex: "white", "brown")
  selectedColorLabel: null,      // label brut affiché (ex: "White", "Bleu Marine")
  setSelectedColor: () => {},    // (label) => void  — accepte le label brut, slugify en interne
  hasVariantImages: false,       // true si product.generated_images_by_variant existe et a ≥ 2 couleurs
  availableColors: [],           // [{slug, label}, ...]  liste ordonnée des couleurs avec images
});

export function ProductColorProvider({ children, product, initialColor = null }) {
  // Détecte les couleurs disponibles dans le produit
  const availableColors = useMemo(() => {
    const map = product?.generated_images_by_variant;
    if (!map || typeof map !== "object") return [];
    return Object.keys(map).map((slug) => {
      const imgs = map[slug];
      const label = (Array.isArray(imgs) && imgs[0]?.color_label) || (Array.isArray(imgs) && imgs[0]?.color) || slug;
      return { slug, label };
    });
  }, [product?.generated_images_by_variant]);

  const hasVariantImages = availableColors.length >= 2;

  // État : couleur sélectionnée (slug). Initial = première couleur disponible
  // (souvent la couleur par défaut du produit).
  const [selectedColor, setSelectedColorRaw] = useState(() => {
    if (initialColor) return slugify(initialColor);
    if (availableColors.length > 0) return availableColors[0].slug;
    return null;
  });

  // Helper : permet de passer un label brut (ex: "White") qui sera slugifié
  const setSelectedColor = useCallback((labelOrSlug) => {
    if (!labelOrSlug) {
      setSelectedColorRaw(null);
      return;
    }
    const slug = slugify(labelOrSlug);
    setSelectedColorRaw(slug);
  }, []);

  const selectedColorLabel = useMemo(() => {
    const m = availableColors.find((c) => c.slug === selectedColor);
    return m?.label || null;
  }, [selectedColor, availableColors]);

  const value = useMemo(
    () => ({
      selectedColor,
      selectedColorLabel,
      setSelectedColor,
      hasVariantImages,
      availableColors,
    }),
    [selectedColor, selectedColorLabel, setSelectedColor, hasVariantImages, availableColors]
  );

  return (
    <ProductColorContext.Provider value={value}>
      {children}
    </ProductColorContext.Provider>
  );
}

/**
 * Hook pour consommer le contexte. Si le contexte n'a pas de Provider parent,
 * retourne des valeurs neutres (selectedColor=null) → fallback aux images
 * par défaut sans crash.
 */
export function useProductColor() {
  return useContext(ProductColorContext);
}

export default ProductColorContext;
