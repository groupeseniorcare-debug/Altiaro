import React from "react";
import { ShieldCheck, Truck, HandHeart, Star } from "@phosphor-icons/react";
import { BENEFIT_ICON, designAccents } from "./storefrontUtils";
import { pickLang } from "../../lib/i18n";

const DEFAULT_BENEFITS = [
  {
    icon: "Truck",
    title: "Livraison offerte",
    description: "Partout en France métropolitaine. Délai 48h-72h selon les produits.",
  },
  {
    icon: "ShieldCheck",
    title: "Garantie 2 ans",
    description: "Sérénité totale. En cas de problème, on reprend le produit à nos frais.",
  },
  {
    icon: "HandHeart",
    title: "Accompagnement humain",
    description: "Un vrai conseiller au téléphone, pas de robot. Du Lundi au Vendredi, 9h–18h.",
  },
  {
    icon: "Star",
    title: "4.8/5 · 2 143 avis",
    description: "La confiance de milliers de familles françaises depuis 2018.",
  },
];

const FALLBACK_ICONS = { Truck, ShieldCheck, HandHeart, Star };

/**
 * Benefits — editorial 4-column layout with numbered counters (01/02…) and hairline
 * dividers between items. The grid lives on whatever background the parent section
 * provides (grey for rhythm, see `GRAY_SECTIONS` in Storefront.jsx).
 */
export function Benefits({ design, lang }) {
  const items = design?.benefits?.items || design?.benefits;
  const finalItems = Array.isArray(items) && items.length > 0 ? items : DEFAULT_BENEFITS;
  const { fontHeading } = designAccents(design);

  return (
    <section className="max-w-7xl mx-auto px-6 md:px-10 py-20 md:py-28" data-testid="storefront-benefits">
      <div className="mb-12 md:mb-16 text-center max-w-xl mx-auto">
        <div className="text-[11px] uppercase tracking-[0.32em] text-neutral-500 mb-3">Pourquoi nous</div>
        <h2 className="text-3xl md:text-[40px] leading-tight tracking-tight text-neutral-900"
            style={{ fontFamily: `"${fontHeading}", serif` }}>
          Un engagement sans compromis
        </h2>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 border-t border-neutral-300/60">
        {finalItems.slice(0, 4).map((b, i) => {
          const title = typeof b.title === "string"
            ? b.title
            : (pickLang(b.title, lang) || b.title?.fr || "");
          const desc = typeof b.description === "string"
            ? b.description
            : (pickLang(b.description, lang) || pickLang(b.desc, lang) || b.description?.fr || "");
          const Icon = BENEFIT_ICON[b.icon] || FALLBACK_ICONS[b.icon] || ShieldCheck;
          return (
            <div
              key={i}
              data-testid={`benefit-${i}`}
              className={[
                "relative py-10 md:py-12 px-6 md:px-8",
                // hairline dividers — right on desktop, bottom on mobile
                "border-b border-neutral-300/60 md:border-b-0 md:border-r md:last:border-r-0",
                // last card on mobile no bottom
                "last:border-b-0",
              ].join(" ")}
            >
              <div className="text-[11px] tabular-nums tracking-widest text-neutral-400 mb-6">
                {String(i + 1).padStart(2, "0")}
              </div>
              <Icon size={34} weight="thin" className="text-neutral-900 mb-5" />
              <div
                className="text-xl md:text-[22px] leading-snug mb-3 text-neutral-900 tracking-tight"
                style={{ fontFamily: `"${fontHeading}", serif` }}
              >
                {title}
              </div>
              <p className="text-[14.5px] leading-relaxed text-neutral-600">
                {desc}
              </p>
            </div>
          );
        })}
      </div>
    </section>
  );
}
