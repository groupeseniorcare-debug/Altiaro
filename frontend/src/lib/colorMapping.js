/**
 * Lot H Fix 5 — Color name → CSS hex mapping pour les swatches couleur.
 *
 * Mapping FR + EN (insensible à la casse + accents). Si la couleur n'est
 * pas reconnue → null (le composant affiche un cercle gris neutre + texte).
 *
 * Détection axe couleur : `isColorAxis(values)` retourne true si ≥50% des
 * valeurs distinctes sont reconnues comme couleurs (heuristique défensive).
 *
 * Utilisé par : `components/storefront/VariantPicker.jsx`.
 */

const COLOR_MAP = {
  // Noir / Black
  noir: "#1a1a1a",
  black: "#1a1a1a",
  jet: "#1a1a1a",
  // Blanc / White
  blanc: "#FFFFFF",
  white: "#FFFFFF",
  ivoire: "#FFFFF0",
  ivory: "#FFFFF0",
  creme: "#FFF8DC",
  cream: "#FFF8DC",
  ecru: "#F5F1E6",
  // Gris / Grey
  gris: "#808080",
  grey: "#808080",
  gray: "#808080",
  "gris clair": "#B8B8B8",
  "gris fonce": "#404040",
  "gris foncé": "#404040",
  "light grey": "#B8B8B8",
  "light gray": "#B8B8B8",
  "dark grey": "#404040",
  "dark gray": "#404040",
  charcoal: "#363636",
  anthracite: "#2D2D2D",
  // Beige / Sable
  beige: "#D4B896",
  sable: "#D4B896",
  sand: "#D4B896",
  taupe: "#8B7355",
  camel: "#C19A6B",
  // Marron / Brown / Chocolat
  marron: "#6B4423",
  brown: "#6B4423",
  chocolat: "#3D1F0F",
  chocolate: "#3D1F0F",
  cafe: "#4A2C1A",
  café: "#4A2C1A",
  coffee: "#4A2C1A",
  cognac: "#9F5F2E",
  caramel: "#A0522D",
  noisette: "#8E6F4E",
  hazelnut: "#8E6F4E",
  // Bleu / Blue
  bleu: "#1E3A8A",
  blue: "#1E3A8A",
  "bleu marine": "#0F2247",
  "marine": "#0F2247",
  navy: "#0F2247",
  "bleu nuit": "#0B1A36",
  "bleu ciel": "#7BB7E8",
  "sky blue": "#7BB7E8",
  "bleu canard": "#005F73",
  teal: "#005F73",
  turquoise: "#1AB8B8",
  cyan: "#22D3EE",
  // Rouge / Red
  rouge: "#B91C1C",
  red: "#B91C1C",
  bordeaux: "#580F1B",
  burgundy: "#580F1B",
  cerise: "#9C1A2C",
  carmin: "#960018",
  // Vert / Green
  vert: "#166534",
  green: "#166534",
  kaki: "#5F6B36",
  khaki: "#5F6B36",
  olive: "#7A8038",
  emeraude: "#0E6B57",
  emerald: "#0E6B57",
  menthe: "#9DD9C5",
  mint: "#9DD9C5",
  forest: "#0E4A29",
  "vert sapin": "#0E4A29",
  // Rose / Pink
  rose: "#F472B6",
  pink: "#F472B6",
  "rose pale": "#F8C5DD",
  "rose poudre": "#E9C2C2",
  fuchsia: "#D946EF",
  // Violet / Purple
  violet: "#7E22CE",
  purple: "#7E22CE",
  mauve: "#B894C5",
  lilas: "#C4A8D6",
  lilac: "#C4A8D6",
  prune: "#572150",
  plum: "#572150",
  // Jaune / Yellow / Or
  jaune: "#FCD34D",
  yellow: "#FCD34D",
  or: "#D4AF37",
  gold: "#D4AF37",
  moutarde: "#C7A23B",
  mustard: "#C7A23B",
  // Orange
  orange: "#F97316",
  terracotta: "#C2452D",
  "terre cuite": "#C2452D",
  rouille: "#B7410E",
  rust: "#B7410E",
  abricot: "#FBA678",
  apricot: "#FBA678",
  saumon: "#FA8072",
  salmon: "#FA8072",
  // Métaux
  argent: "#C0C0C0",
  silver: "#C0C0C0",
  bronze: "#CD7F32",
  cuivre: "#B87333",
  copper: "#B87333",
  platine: "#E5E4E2",
  platinum: "#E5E4E2",
  // Multi / pattern fallback (cercle multicolore)
  multicolore: "MULTI",
  multicolor: "MULTI",
  multi: "MULTI",
  "rainbow": "MULTI",
  "imprime": "PATTERN",
  "imprimé": "PATTERN",
  pattern: "PATTERN",
  motif: "PATTERN",
};

/**
 * Normalise une chaîne pour le lookup (lowercase + strip accents + trim).
 */
function normalizeName(name) {
  if (!name) return "";
  return String(name)
    .toLowerCase()
    .trim()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");
}

/**
 * Retourne le hex CSS d'une couleur par nom, ou null si non reconnue.
 *
 * @param {string} name - "Noir", "Black", "bleu marine", etc.
 * @returns {string|null} Hex CSS (`#1a1a1a`) ou null, ou la string spéciale `"MULTI"` / `"PATTERN"`.
 */
export function colorFromName(name) {
  const key = normalizeName(name);
  if (!key) return null;
  return COLOR_MAP[key] || null;
}

/**
 * Détermine si un axe est probablement un axe COULEUR.
 *
 * Heuristique : si ≥50% des valeurs distinctes sont reconnues comme couleurs,
 * c'est un axe couleur. Tolérant aux faux positifs sur des noms exotiques
 * ("Aubergine", "Saumon")  — on tombera juste sur null pour ceux-là.
 *
 * @param {string[]} values - Liste des valeurs distinctes de l'axe
 * @returns {boolean}
 */
export function isColorAxis(values) {
  if (!Array.isArray(values) || values.length === 0) return false;
  const matched = values.filter((v) => colorFromName(v) != null).length;
  return matched / values.length >= 0.5;
}

/**
 * Pour un nom de couleur, retourne soit un hex valide, soit un fallback
 * gris neutre (pour les couleurs non reconnues).
 */
export function colorFromNameOrFallback(name) {
  return colorFromName(name) || "#9CA3AF";
}

/**
 * Détermine si la couleur est claire (besoin d'un border visible) ou foncée.
 * Utile pour ajuster le `border` des swatches blancs/clairs.
 */
export function isLightColor(hex) {
  if (!hex || !hex.startsWith("#")) return false;
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  // Perceived luminance (ITU-R BT.601)
  const lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
  return lum >= 0.85;
}

export default colorFromName;
