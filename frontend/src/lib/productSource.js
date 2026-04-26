/**
 * Helpers pour les produits importés depuis un fournisseur (AliExpress / CJ).
 * Source de vérité : `product.source = { provider: "aliexpress"|"cj", product_id: "..." }`
 *
 * Garde-fou : tolère aussi les anciens formats (string brut, champs manquants).
 */

const NORMALIZE_PROVIDER = {
  aliexpress: "aliexpress",
  ae: "aliexpress",
  cj: "cj",
  cjdropshipping: "cj",
  "cj-dropshipping": "cj",
};

/** Normalise le provider en clé canonique : "aliexpress" | "cj" | null */
export function normalizeProvider(source) {
  if (!source) return null;
  if (typeof source === "string") {
    return NORMALIZE_PROVIDER[source.toLowerCase()] || source.toLowerCase() || null;
  }
  if (typeof source === "object" && source.provider) {
    return NORMALIZE_PROVIDER[String(source.provider).toLowerCase()]
      || String(source.provider).toLowerCase();
  }
  return null;
}

/** Construit l'URL externe de la fiche produit d'origine. Retourne null si infaisable. */
export function getProductSourceUrl(source) {
  if (!source || typeof source !== "object") return null;
  const provider = normalizeProvider(source);
  const productId = source.product_id || source.productId || source.pid;
  if (!provider || !productId) return null;
  switch (provider) {
    case "aliexpress":
      return `https://fr.aliexpress.com/item/${productId}.html`;
    case "cj":
      return `https://www.cjdropshipping.com/product/-p-${productId}.html`;
    default:
      return null;
  }
}

/** Label affichable du fournisseur, ex: "AliExpress" / "CJ Dropshipping". */
export function getProviderLabel(source) {
  const provider = normalizeProvider(source);
  if (!provider) return null;
  const map = { aliexpress: "AliExpress", cj: "CJ Dropshipping" };
  return map[provider] || provider;
}

/** Couleur Tailwind associée au provider (badges UI homogènes). */
export function getProviderBadgeClasses(source) {
  const provider = normalizeProvider(source);
  if (provider === "aliexpress") {
    return "bg-orange-50 text-orange-800 border-orange-200";
  }
  if (provider === "cj") {
    return "bg-sky-50 text-sky-800 border-sky-200";
  }
  return "bg-neutral-50 text-neutral-700 border-neutral-200";
}
