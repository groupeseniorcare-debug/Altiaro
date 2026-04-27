import React, { useEffect, useMemo } from "react";
import { Check } from "@phosphor-icons/react";
import {
  colorFromName,
  isColorAxis,
  colorFromNameOrFallback,
  isLightColor,
} from "../../lib/colorMapping";
import { useProductColor } from "../../lib/ProductColorContext";

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
 *
 * Lot H Fix 1 — Filtre défensif côté front : si malgré le clean DB un axe
 * "ships_from" / "plug" remonte (ex: site pas encore migré), on ne l'affiche
 * pas. Plus jamais de "GERMANY" / "EU PLUG" présenté au client.
 *
 * Lot H Fix 5 — Swatches couleur visuels (cercles ~36-40px) avec mapping
 * nom → hex. Les autres axes (taille, modèle) gardent les pills rectangulaires.
 */

// Heuristique défensive : valeurs typiques qu'on ne veut JAMAIS afficher
// même si le filtre backend a raté (anciens sites pas encore migrés).
const PARASITIC_VALUE_PATTERNS = [
  /^(germany|france|china|italy|spain|usa|united kingdom|poland|czech|australia|japan|netherlands|belgium|russia|brazil|turkey|uae|mexico|canada|india|korea|portugal|austria|denmark|finland|norway|sweden|switzerland|ireland|greece)$/i,
  /^(allemagne|chine|italie|espagne|royaume-uni|pologne|tchequie|australie|japon|pays-bas|belgique|russie|bresil|turquie|emirats|mexique|inde|coree|portugal|autriche|danemark|finlande|norvege|suede|suisse|irlande|grece)$/i,
  /^(ships from|overseas|warehouse|entrepot|depot|domestic|global|worldwide)/i,
  /plug/i,
];

function isParasiticValue(v) {
  if (!v) return false;
  return PARASITIC_VALUE_PATTERNS.some((rx) => rx.test(String(v).trim()));
}

function isParasiticAxis(values) {
  if (!Array.isArray(values) || values.length === 0) return false;
  const parasitic = values.filter(isParasiticValue).length;
  return parasitic / values.length >= 0.8; // ≥80% parasites → axe à hide
}

export default function VariantPicker({ variants = [], selected, onSelect, lang = "fr" }) {
  const labels = LABELS[lang] || LABELS.fr;
  // Lot H Fix 4 — publie la couleur sélectionnée vers le Context React pour que
  // ProductGallery + composants editorial puissent réagir au changement.
  const { setSelectedColor } = useProductColor();

  const cleaned = useMemo(
    () => (variants || []).filter((v) => v && (v.vid || v.sku) && Array.isArray(v.properties)),
    [variants]
  );

  // Lot H Fix 4 — TOUS les hooks doivent être appelés AVANT tout `return null`
  // conditionnel (Rules of Hooks). On calcule axes / visibleAxes / colorAxisIdx
  // de manière mémoïsée, puis on applique les `return null` plus bas.

  // Détection du nombre d'axes (max 2)
  const axisCount = Math.min(
    2,
    Math.max(...(cleaned.length ? cleaned.map((v) => v.properties.length || 1) : [1]), 1)
  );

  // Listes de valeurs uniques par axe
  const axes = useMemo(() => {
    const out = [];
    for (let i = 0; i < axisCount; i++) {
      const set = new Set();
      cleaned.forEach((v) => {
        const val = v.properties[i];
        if (val) set.add(val);
      });
      out.push(Array.from(set));
    }
    return out;
  }, [cleaned, axisCount]);

  // Lot H Fix 1 — détecte les axes parasites (ships_from, plug)
  // pour les masquer côté affichage (défense en profondeur).
  const visibleAxesIndices = useMemo(
    () => axes
      .map((vals, i) => ({ i, vals }))
      .filter(({ vals }) => !isParasiticAxis(vals))
      .map(({ i }) => i),
    [axes]
  );

  const selectedProps = selected?.properties || [];

  // Lot H Fix 4 — détecte automatiquement l'axe couleur et publie la couleur
  // sélectionnée dans le ProductColorContext (consommé par ProductGallery,
  // composants editorial, etc.). Sync à chaque changement de variante.
  const colorAxisIdx = useMemo(() => {
    for (const i of visibleAxesIndices) {
      if (isColorAxis(axes[i])) return i;
    }
    return -1;
  }, [visibleAxesIndices, axes]);

  useEffect(() => {
    if (colorAxisIdx < 0) return;
    const colorVal = selectedProps[colorAxisIdx];
    if (colorVal) setSelectedColor(colorVal);
  }, [selectedProps, colorAxisIdx, setSelectedColor]);

  // ─── EARLY RETURNS (après tous les hooks) ───────────────────────────────
  // Si aucune variante OU une seule (cas dégénéré) → on n'affiche rien
  if (cleaned.length <= 1) return null;
  // Si aucun axe visible (cas dégénéré, tous parasites) → rien à afficher.
  if (visibleAxesIndices.length === 0) return null;

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
      {visibleAxesIndices.map((axisIdx) => {
        const values = axes[axisIdx];
        const colorAxis = isColorAxis(values);
        const renderIdx = visibleAxesIndices.indexOf(axisIdx);
        const labelText = colorAxis
          ? labels.color
          : renderIdx === 0
          ? labels.axis1
          : labels.axis2;
        return (
          <div key={axisIdx} data-testid={`variant-axis-${axisIdx + 1}`} data-axis-kind={colorAxis ? "color" : "other"}>
            <div className="text-[11px] uppercase tracking-[0.2em] text-neutral-500 mb-2 flex items-center gap-2">
              {labelText}
              {selectedProps[axisIdx] && (
                <span className="text-neutral-900 normal-case tracking-normal text-xs font-medium">
                  · {selectedProps[axisIdx]}
                </span>
              )}
            </div>
            {colorAxis ? (
              // Lot H Fix 5 — swatches couleur cercles 36-40px (32 mobile)
              <div className="flex flex-wrap gap-2.5">
                {values.map((val) => {
                  const active = selectedProps[axisIdx] === val;
                  const available = isAxisValueAvailable(axisIdx, val);
                  const hex = colorFromName(val);
                  const swatchColor = colorFromNameOrFallback(val);
                  const isLight = isLightColor(swatchColor);
                  // Special markers for unrecognized cases
                  const isMulti = hex === "MULTI";
                  const isPattern = hex === "PATTERN";

                  return (
                    <button
                      key={val}
                      type="button"
                      onClick={() => handleSelect(axisIdx, val)}
                      disabled={!available}
                      data-testid={`variant-option-${axisIdx}-${val}`}
                      title={available ? val : `${val} — ${labels.outOfStock}`}
                      aria-label={`Couleur ${val}${active ? " (sélectionnée)" : ""}${!available ? " indisponible" : ""}`}
                      className={[
                        "relative w-9 h-9 md:w-10 md:h-10 rounded-full transition-all duration-200 outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-neutral-900",
                        active
                          ? "ring-2 ring-offset-2 ring-neutral-900 scale-110"
                          : available
                          ? "hover:scale-110 hover:ring-2 hover:ring-offset-1 hover:ring-neutral-300"
                          : "opacity-30 cursor-not-allowed",
                        isLight && !active ? "border border-neutral-300" : "",
                      ].join(" ")}
                      style={{
                        background: isMulti
                          ? "conic-gradient(#F97316, #FCD34D, #166534, #1E3A8A, #7E22CE, #B91C1C, #F97316)"
                          : isPattern
                          ? "repeating-linear-gradient(45deg, #C0C0C0, #C0C0C0 4px, #808080 4px, #808080 8px)"
                          : swatchColor,
                      }}
                    >
                      {active && (
                        <Check
                          size={16}
                          weight="bold"
                          className={isLight ? "text-neutral-900 mx-auto" : "text-white mx-auto"}
                        />
                      )}
                      {!available && (
                        <span
                          className="absolute inset-0 flex items-center justify-center pointer-events-none"
                          aria-hidden="true"
                        >
                          <span className="block w-full h-px bg-neutral-400 rotate-45" />
                        </span>
                      )}
                    </button>
                  );
                })}
              </div>
            ) : (
              // Axes non-couleur : pills rectangulaires (comportement initial)
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
            )}
          </div>
        );
      })}

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
  fr: { axis1: "Choix",      axis2: "Taille",  color: "Couleur",    outOfStock: "Indisponible",   lowStock: "Plus que {n} en stock" },
  en: { axis1: "Variant",    axis2: "Size",    color: "Color",      outOfStock: "Out of stock",   lowStock: "Only {n} left in stock" },
  de: { axis1: "Variante",   axis2: "Größe",   color: "Farbe",      outOfStock: "Nicht verfügbar",lowStock: "Nur noch {n} auf Lager" },
  nl: { axis1: "Variant",    axis2: "Maat",    color: "Kleur",      outOfStock: "Niet beschikbaar",lowStock: "Nog {n} op voorraad" },
  it: { axis1: "Variante",   axis2: "Taglia",  color: "Colore",     outOfStock: "Non disponibile",lowStock: "Solo {n} disponibile" },
  es: { axis1: "Variante",   axis2: "Talla",   color: "Color",      outOfStock: "Sin stock",      lowStock: "Solo quedan {n}" },
};
