/**
 * Lot B — Helper centralisé pour la priorité des images produit.
 *
 * Règle UNIVERSELLE applicable sur toutes les surfaces storefront
 * (cartes grille, hero, cross-sell, bundle, recherche, collection,
 *  page produit, miniatures email, etc.) :
 *
 *   1.  product.generated_images[0].url  (image IA premium, style "lifestyle"
 *                                          puis "studio" puis le 1er dispo)
 *   2.  product.images[0]                 (image AliExpress / fournisseur, fallback)
 *   3.  placeholder                        (dernier recours, vide ou data-uri)
 *
 * → Le visiteur voit toujours en priorité la version éditoriale IA premium,
 *   pas la version brute du fournisseur (qualité variable, watermark, etc.).
 *
 * Usage :
 *   import { getPrimaryImage, getProductGallery } from "@/lib/productImage";
 *   const src = getPrimaryImage(product);                  // string | null
 *   const all = getProductGallery(product);                // string[]  (IA d'abord, puis legacy)
 *
 * Le helper est tolérant aux schémas legacy :
 *   - generated_images peut être [{url, style}, ...] OU [string, ...]
 *   - images peut être [string, ...] OU [{url}, ...]
 */

// Lot C (utilisateur 2026-04-27) — STUDIO en première position : c'est l'image
// la plus fidèle au produit (cohérence visuelle commerciale max), affichée
// par défaut sur les cards de grille, fiches produit, hero, etc.
// Le storefront product page peut afficher la galerie complète via `getProductGallery()`.
const PREFERRED_STYLES = ["studio", "lifestyle", "closeup", "in_use", "detail"];

/**
 * Extrait l'URL d'un item generated_images (objet ou string).
 * @param {object|string} item
 * @returns {string|null}
 */
function _itemUrl(item) {
  if (!item) return null;
  if (typeof item === "string") return item;
  return item.url || item.image || item.src || null;
}

/**
 * Renvoie la 1ère image IA disponible, en privilégiant l'ordre
 * lifestyle → studio → closeup → in_use → detail → autre.
 * @param {Array} generated
 * @returns {string|null}
 */
function _firstAiImage(generated) {
  if (!Array.isArray(generated) || generated.length === 0) return null;
  // Recherche par style préféré
  for (const style of PREFERRED_STYLES) {
    const match = generated.find((g) => g && typeof g === "object" && g.style === style);
    if (match) {
      const url = _itemUrl(match);
      if (url) return url;
    }
  }
  // Fallback : premier disponible (peut être string OU objet sans style)
  for (const item of generated) {
    const url = _itemUrl(item);
    if (url) return url;
  }
  return null;
}

/**
 * Priorité officielle : IA premium → image fournisseur → null.
 * @param {object} product
 * @returns {string|null}
 */
export function getPrimaryImage(product) {
  if (!product || typeof product !== "object") return null;

  // 1. Image IA premium (priorité absolue, style éditorial)
  const aiUrl = _firstAiImage(product.generated_images);
  if (aiUrl) return aiUrl;

  // 2. Image fournisseur (ex AliExpress)
  const imgs = product.images;
  if (Array.isArray(imgs) && imgs.length > 0) {
    const url = _itemUrl(imgs[0]);
    if (url) return url;
  }

  // 3. Champ legacy direct
  if (typeof product.image_url === "string" && product.image_url) return product.image_url;
  if (typeof product.main_image === "string" && product.main_image) return product.main_image;
  if (typeof product.image === "string" && product.image) return product.image;

  return null;
}

/**
 * Galerie complète (toutes images, IA d'abord, puis legacy).
 * Utile pour la page produit où on veut afficher TOUTES les images.
 * @param {object} product
 * @returns {string[]}
 */
export function getProductGallery(product) {
  if (!product || typeof product !== "object") return [];
  const out = [];
  const seen = new Set();

  const push = (url) => {
    if (url && !seen.has(url)) {
      seen.add(url);
      out.push(url);
    }
  };

  // 1. Toutes les IA d'abord, dans l'ordre des styles préférés
  const generated = product.generated_images;
  if (Array.isArray(generated)) {
    // Order by preferred style
    for (const style of PREFERRED_STYLES) {
      for (const g of generated) {
        if (g && typeof g === "object" && g.style === style) push(_itemUrl(g));
      }
    }
    // Items sans style ou hors préférence
    for (const g of generated) {
      const u = _itemUrl(g);
      if (u && !seen.has(u)) push(u);
    }
  }

  // 2. Images fournisseur en backup (galerie complète)
  if (Array.isArray(product.images)) {
    for (const i of product.images) push(_itemUrl(i));
  }

  return out;
}

/**
 * Lot H Fix 4 — Galerie d'une COULEUR spécifique (variant-aware).
 *
 * Lit `product.generated_images_by_variant[colorSlug]` (généré par Lot H2/H3)
 * et retourne la galerie ordonnée pour cette couleur. Fallback sur la galerie
 * principale si la couleur n'a pas d'images dédiées.
 *
 * @param {object} product
 * @param {string} colorSlug - slug de la couleur sélectionnée (ex: "white", "brown")
 * @returns {string[]}
 */
export function getProductGalleryForColor(product, colorSlug) {
  if (!product || typeof product !== "object") return getProductGallery(product);
  const byVariant = product.generated_images_by_variant;
  if (!colorSlug || !byVariant || typeof byVariant !== "object") {
    return getProductGallery(product);
  }
  const variantImages = byVariant[colorSlug];
  if (!Array.isArray(variantImages) || variantImages.length === 0) {
    return getProductGallery(product);
  }
  const out = [];
  const seen = new Set();
  const push = (url) => {
    if (url && !seen.has(url)) {
      seen.add(url);
      out.push(url);
    }
  };
  // Order by preferred style
  for (const style of PREFERRED_STYLES) {
    for (const g of variantImages) {
      if (g && typeof g === "object" && g.style === style) push(_itemUrl(g));
    }
  }
  for (const g of variantImages) {
    const u = _itemUrl(g);
    if (u && !seen.has(u)) push(u);
  }
  // Fallback : ajoute les autres images du produit en queue (ex: photos AE backup)
  if (Array.isArray(product.images)) {
    for (const i of product.images) push(_itemUrl(i));
  }
  return out;
}

/**
 * Lot H Fix 4 — Image principale pour une couleur (variant-aware).
 *
 * Comme `getPrimaryImage()` mais en privilégiant la couleur sélectionnée.
 * @param {object} product
 * @param {string} colorSlug
 * @returns {string|null}
 */
export function getPrimaryImageForColor(product, colorSlug) {
  if (!colorSlug) return getPrimaryImage(product);
  const gallery = getProductGalleryForColor(product, colorSlug);
  return gallery[0] || getPrimaryImage(product);
}

/**
 * Lot H Fix 4 — Récupère l'image d'un STYLE spécifique pour une couleur donnée.
 * Utilisé par les composants editorial qui demandent "le shot lifestyle de la
 * couleur sélectionnée".
 *
 * @param {object} product
 * @param {string} colorSlug
 * @param {string} style - "studio" | "lifestyle" | "closeup" | ...
 * @returns {string|null}
 */
export function getStyleImageForColor(product, colorSlug, style) {
  const byVariant = product?.generated_images_by_variant;
  if (colorSlug && byVariant && Array.isArray(byVariant[colorSlug])) {
    const match = byVariant[colorSlug].find((g) => g && g.style === style);
    if (match && _itemUrl(match)) return _itemUrl(match);
  }
  // Fallback sur le générique du même style
  if (Array.isArray(product?.generated_images)) {
    const match = product.generated_images.find((g) => g && g.style === style);
    if (match && _itemUrl(match)) return _itemUrl(match);
  }
  return null;
}

/**
 * Fournit un placeholder neutre si aucune image disponible.
 * Utile pour les composants qui ne tolèrent pas un null.
 * @param {object} product
 * @param {string} fallbackUrl - URL externe à utiliser si null
 * @returns {string}
 */
export function getPrimaryImageOr(product, fallbackUrl = "") {
  return getPrimaryImage(product) || fallbackUrl;
}

/**
 * Helper pour déterminer si un produit a une image IA premium.
 * Utile pour afficher un badge "IA generated" ou pour le tri.
 * @param {object} product
 * @returns {boolean}
 */
export function hasAiImage(product) {
  return !!_firstAiImage(product?.generated_images);
}

const productImage = {
  getPrimaryImage,
  getProductGallery,
  getPrimaryImageOr,
  hasAiImage,
};

export default productImage;
