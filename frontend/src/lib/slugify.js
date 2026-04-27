/**
 * Lot H — Slugify partagé (FR + EN, accents stripped, lowercase).
 * Mirroir Python `services/color_variant_images.py::slugify_color`.
 *
 * Usage : `slugify("Bleu Marine")` → `"bleu-marine"`.
 */
export function slugify(name) {
  if (!name) return "unknown";
  return String(name)
    .toLowerCase()
    .trim()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "") || "unknown";
}

export default slugify;
