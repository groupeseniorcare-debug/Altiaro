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
    title: "4.8/5 (2 143 avis)",
    description: "La confiance de milliers de familles françaises depuis 2018.",
  },
];

const FALLBACK_ICONS = { Truck, ShieldCheck, HandHeart, Star };

export function Benefits({ design, lang }) {
  const items = design?.benefits?.items || design?.benefits;
  const finalItems = Array.isArray(items) && items.length > 0 ? items : DEFAULT_BENEFITS;
  const { primary, fontHeading } = designAccents(design);

  return (
    <section className="max-w-7xl mx-auto px-6 md:px-10 py-16 md:py-20" data-testid="storefront-benefits">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-8 lg:gap-12">
        {finalItems.map((b, i) => {
          const title = typeof b.title === "string"
            ? b.title
            : (pickLang(b.title, lang) || b.title?.fr || "");
          const desc = typeof b.description === "string"
            ? b.description
            : (pickLang(b.description, lang) || pickLang(b.desc, lang) || b.description?.fr || "");
          const Icon = BENEFIT_ICON[b.icon] || FALLBACK_ICONS[b.icon] || ShieldCheck;
          return (
            <div key={i} className="text-center" data-testid={`benefit-${i}`}>
              <div
                className="w-16 h-16 mx-auto rounded-full flex items-center justify-center mb-5"
                style={{ background: `${primary}14`, color: primary }}
              >
                <Icon size={28} weight="duotone" />
              </div>
              <div
                className="font-semibold text-lg mb-2 text-neutral-900"
                style={{ fontFamily: `"${fontHeading}", serif` }}
              >
                {title}
              </div>
              <div className="text-sm leading-relaxed" style={{ color: "#78716C" }}>
                {desc}
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
