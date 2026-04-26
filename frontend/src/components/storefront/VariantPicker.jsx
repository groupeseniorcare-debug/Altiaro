import React, { useMemo } from "react";

/**
 * VariantPicker — sélecteur de variantes premium pour les fiches produit.
 *
 * Format d'entrée (variants[]) :
 *   { vid, sku, name, image, sell_price_eur, stock, properties: ["Gris", "L"] }
 *
 * Détection auto du nombre d'axes :
 *   - 1 axe   (couleur OU taille)  → pills cliquables
 *   - 2 axes  (couleur + taille)   → 2 grilles de pills (axe 1 + axe 2)
 *
 * Cross-axis stock : si l'utilisateur sélectionne une combinaison
 * (axis1=A, axis2=B) qui n'existe pas en stock, on affiche en grisé.
 */
export default function VariantPicker({ variants = [], selected, onSelect, lang = "fr" }) {
  const labels = LABELS[lang] || LABELS.fr;

  const cleaned = useMemo(
    () => (variants || []).filter((v) => v && (v.vid || v.sku) && Array.isArray(v.properties)),
    [variants]
  );
  // Si aucune variante OU une seule (cas dégénéré) → on n'affiche rien
  if (cleaned.length <= 1) return null;

  // Détection du nombre d'axes (max 2)
  const axisCount = Math.min(2, Math.max(...cleaned.map((v) => v.properties.length || 1), 1));

  // Listes de valeurs uniques par axe
  const axes = [];
  for (let i = 0; i < axisCount; i++) {
    const set = new Set();
    cleaned.forEach((v) => {
      const val = v.properties[i];
      if (val) set.add(val);
    });
    axes.push(Array.from(set));
  }

  const selectedProps = selected?.properties || [];

  // Helpers pour savoir si une valeur d'axe est dispo (≥1 variante en stock)
  // étant donné les sélections fixées sur les autres axes.
  const isAxisValueAvailable = (axisIdx, value) => {
    return cleaned.some((v) => {
      if (v.properties[axisIdx] !== value) return false;
      for (let i = 0; i < axisCount; i++) {
        if (i === axisIdx) continue;
        const fixed = selectedProps[i];
        if (fixed && v.properties[i] !== fixed) return false;
      }
      return (v.stock || 0) > 0 || v.stock == null;
    });
  };

  // Quand l'utilisateur clique sur une valeur, on cherche la variante exacte
  // qui matche avec les autres axes déjà sélectionnés (1ʳᵉ trouvée).
  const handleSelect = (axisIdx, value) => {
    // Construit la combinaison cible : nouvelle valeur sur axisIdx, anciennes ailleurs
    const target = [...selectedProps];
    target[axisIdx] = value;
    // 1) Match exact
    let match = cleaned.find((v) =>
      v.properties.every((p, i) => target[i] == null || p === target[i])
    );
    // 2) Si pas de match exact (combinaison out of stock), on bascule vers
    //    la 1ʳᵉ variante de cet axe (force l'autre axe à se réajuster).
    if (!match) {
      match = cleaned.find((v) => v.properties[axisIdx] === value);
    }
    if (match) onSelect?.(match);
  };

  return (
    <div className="space-y-5" data-testid="variant-picker">
      {axes.map((values, axisIdx) => (
        <div key={axisIdx} data-testid={`variant-axis-${axisIdx + 1}`}>
          <div className="text-[11px] uppercase tracking-[0.2em] text-neutral-500 mb-2 flex items-center gap-2">
            {axisIdx === 0 ? labels.axis1 : labels.axis2}
            {selectedProps[axisIdx] && (
              <span className="text-neutral-900 normal-case tracking-normal text-xs font-medium">
                · {selectedProps[axisIdx]}
              </span>
            )}
          </div>
          <div className="flex flex-wrap gap-2">
            {values.map((val) => {
              const active = selectedProps[axisIdx] === val;
              const available = isAxisValueAvailable(axisIdx, val);
              return (
                <button
                  key={val}
                  type="button"
                  onClick={() => handleSelect(axisIdx, val)}
                  disabled={!available}
                  data-testid={`variant-option-${axisIdx}-${val}`}
                  title={available ? val : `${val} — ${labels.outOfStock}`}
                  className={[
                    "h-10 px-4 rounded-full border text-sm font-medium transition",
                    active
                      ? "bg-neutral-900 text-white border-neutral-900"
                      : available
                        ? "bg-white text-neutral-900 border-neutral-300 hover:border-neutral-900"
                        : "bg-neutral-50 text-neutral-400 border-neutral-200 line-through cursor-not-allowed",
                  ].join(" ")}
                >
                  {val}
                </button>
              );
            })}
          </div>
        </div>
      ))}

      {selected?.stock != null && selected.stock <= 5 && selected.stock > 0 && (
        <div className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 inline-flex items-center gap-1.5">
          ⚠ {labels.lowStock.replace("{n}", selected.stock)}
        </div>
      )}
      {selected?.stock === 0 && (
        <div className="text-xs text-rose-700 bg-rose-50 border border-rose-200 rounded-lg px-3 py-2 inline-flex items-center gap-1.5">
          ✗ {labels.outOfStock}
        </div>
      )}
    </div>
  );
}

const LABELS = {
  fr: { axis1: "Choix",      axis2: "Taille",  outOfStock: "Indisponible",   lowStock: "Plus que {n} en stock" },
  en: { axis1: "Variant",    axis2: "Size",    outOfStock: "Out of stock",   lowStock: "Only {n} left in stock" },
  de: { axis1: "Variante",   axis2: "Größe",   outOfStock: "Nicht verfügbar",lowStock: "Nur noch {n} auf Lager" },
  nl: { axis1: "Variant",    axis2: "Maat",    outOfStock: "Niet beschikbaar",lowStock: "Nog {n} op voorraad" },
  it: { axis1: "Variante",   axis2: "Taglia",  outOfStock: "Non disponibile",lowStock: "Solo {n} disponibile" },
  es: { axis1: "Variante",   axis2: "Talla",   outOfStock: "Sin stock",      lowStock: "Solo quedan {n}" },
};
