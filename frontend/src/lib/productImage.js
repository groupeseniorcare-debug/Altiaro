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
