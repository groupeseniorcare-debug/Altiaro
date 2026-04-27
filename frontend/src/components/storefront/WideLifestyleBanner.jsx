/**
 * Lot I (Phase 2.2) Fix I6 — Wide cinematic lifestyle banner (16:9).
 *
 * Affiche le style `wide_lifestyle` généré par
 * `services/product_variant_pipeline.py` en bandeau pleine largeur.
 *
 * Variant-aware : suit la couleur sélectionnée par le `<ProductColorContext>`
 * (Lot H Fix 4). Si la couleur n'a pas de wide_lifestyle généré, le bandeau
 * se masque proprement (pas de placeholder Unsplash).
 *
 * Placement recommandé : entre la sidebar produit (galerie + CTA) et les
 * sections éditoriales suivantes. Sert de respiration cinématographique.
 *
 * Composant partagé → propagation auto sur tous les sites futurs créés
 * via `launch.py`.
 */
import React from "react";
import { useProductColor } from "../../lib/ProductColorContext";
import { getStyleImageForColor } from "../../lib/productImage";
import { designAccents } from "./storefrontUtils";

export default function WideLifestyleBanner({ product, productName, design }) {
  const { selectedColor } = useProductColor();
  const { fontHeading } = designAccents(design);

  const url = React.useMemo(
    () => getStyleImageForColor(product, selectedColor, "wide_lifestyle"),
    [product, selectedColor],
  );

  // No generated wide_lifestyle for this color → hide the section gracefully
  if (!url) return null;

  return (
    <section
      className="my-16 md:my-24"
      data-testid="product-wide-lifestyle-banner"
      aria-label="Mise en scène de l'objet"
    >
      <div className="relative w-full overflow-hidden" style={{ borderRadius: "2px" }}>
        <div className="aspect-[16/9] w-full bg-stone-100">
          <img
            src={url}
            alt={`${productName || ""} en situation`}
            loading="lazy"
            className="w-full h-full object-cover transition-transform duration-[1600ms] ease-out hover:scale-[1.015]"
          />
        </div>

        {/* Subtle bottom-left caption — overlay minimaliste, pas de gradient noir */}
        <div className="absolute left-0 bottom-0 p-6 md:p-10 max-w-md">
          <span
            className="inline-block text-[10px] uppercase tracking-[0.4em] font-medium px-3 py-1 mb-2"
            style={{
              color: "#0A0A0A",
              background: "rgba(255,255,255,0.92)",
              backdropFilter: "blur(8px)",
            }}
          >
            En situation
          </span>
        </div>
      </div>

      {/* Hairline subtitle below for editorial context */}
      <p
        className="mt-5 text-[13px] md:text-[14px] leading-[1.6] text-neutral-500 max-w-xl mx-auto text-center px-6"
        style={{ fontFamily: `"${fontHeading}", Georgia, serif`, fontStyle: "italic" }}
      >
        Pensé pour s'intégrer naturellement, sans jamais évoquer le matériel médical.
      </p>
    </section>
  );
}
