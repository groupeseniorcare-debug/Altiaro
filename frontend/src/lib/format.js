/**
 * Helpers de formatage (fr-FR) — Phase 3.1 (2026-05-04)
 *
 * Objectif : unifier tous les rendus de prix / nombres / dates à travers le
 * cockpit, en utilisant les API natives `Intl.*` plutôt que des
 * concaténations manuelles (qui cassaient le rendu du « € » quand le
 * fichier JSX contenait des escape sequences literales `\u20ac`).
 */

const EUR_FMT_0 = new Intl.NumberFormat("fr-FR", {
  style: "currency",
  currency: "EUR",
  maximumFractionDigits: 0,
});

const EUR_FMT_2 = new Intl.NumberFormat("fr-FR", {
  style: "currency",
  currency: "EUR",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

/**
 * formatEUR(value, opts?) — retourne une string type "1 299 €" (avec espace
 * insécable + € UTF-8, géré nativement par Intl).
 *
 * @param {number|string} value
 * @param {object} [opts]  { decimals?: 0|2 }  par défaut 0
 */
export function formatEUR(value, opts = {}) {
  const n = typeof value === "string" ? Number(value) : value;
  if (n === null || n === undefined || Number.isNaN(n)) return "—";
  const decimals = opts.decimals ?? 0;
  const fmt = decimals === 2 ? EUR_FMT_2 : EUR_FMT_0;
  return fmt.format(n);
}

/**
 * formatNumber(value) — nombre brut formaté fr-FR (espace fines séparatrices).
 */
export function formatNumber(value, opts = {}) {
  const n = typeof value === "string" ? Number(value) : value;
  if (n === null || n === undefined || Number.isNaN(n)) return "—";
  return new Intl.NumberFormat("fr-FR", {
    maximumFractionDigits: opts.decimals ?? 0,
  }).format(n);
}

/**
 * formatDate(iso) — date courte fr-FR ("04/05/2026").
 */
export function formatDate(iso) {
  if (!iso) return "—";
  const d = iso instanceof Date ? iso : new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return new Intl.DateTimeFormat("fr-FR").format(d);
}

/**
 * formatDateTime(iso) — date+heure fr-FR ("04/05/2026 13:05").
 */
export function formatDateTime(iso) {
  if (!iso) return "—";
  const d = iso instanceof Date ? iso : new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return new Intl.DateTimeFormat("fr-FR", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(d);
}
