import React from "react";
import { ChatCircleDots, Package, HandHeart } from "@phosphor-icons/react";

/**
 * Guide d'achat — comment ça marche, 3 étapes claires.
 * design.buying_guide = { steps: [{icon, title, description}] }
 */
export default function BuyingGuide({ guide, design }) {
  const primary = design?.brand?.primary_color || "#B84B31";
  const fontHeading = design?.brand?.font_heading || "Fraunces";

  const steps = guide?.steps?.length
    ? guide.steps
    : [
        {
          icon: "ChatCircleDots",
          title: "1. On vous écoute",
          description: "Un conseiller prend le temps de comprendre votre besoin au téléphone ou par mail. Gratuit, sans engagement.",
        },
        {
          icon: "Package",
          title: "2. Livraison offerte",
          description: "Votre commande arrive chez vous sous 48-72h, avec un emballage soigné et les instructions claires.",
        },
        {
          icon: "HandHeart",
          title: "3. Accompagnement 30 jours",
          description: "Besoin d'aide pour installer ou utiliser ? On reste joignable. Retour gratuit si besoin sous 14 jours.",
        },
      ];

  const ICONS = { ChatCircleDots, Package, HandHeart };

  return (
    <section className="py-20 md:py-28 px-6 bg-white" data-testid="storefront-guide">
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-16">
          <div className="text-[11px] uppercase tracking-[0.2em] text-neutral-500 mb-3">Commander en 3 étapes</div>
          <h2 className="text-4xl md:text-5xl mb-4" style={{ fontFamily: `${fontHeading}, serif`, color: "#1C1917" }}>
            Un achat simple, sans stress
          </h2>
          <p className="text-neutral-600 max-w-xl mx-auto">
            Choisir un équipement pour soi ou un proche peut être intimidant. On simplifie tout.
          </p>
        </div>

        <div className="relative grid grid-cols-1 md:grid-cols-3 gap-8 md:gap-12">
          {/* Connector line (desktop) */}
          <div className="hidden md:block absolute top-9 left-[16.66%] right-[16.66%] h-px" style={{ background: `${primary}33` }} />

          {steps.map((s, i) => {
            const Icon = ICONS[s.icon] || HandHeart;
            return (
              <div key={i} className="relative text-center" data-testid={`guide-step-${i}`}>
                <div
                  className="w-[72px] h-[72px] rounded-full mx-auto flex items-center justify-center mb-6 relative z-10 bg-white border-2"
                  style={{ borderColor: primary, color: primary }}
                >
                  <Icon size={32} weight="duotone" />
                </div>
                <h3 className="text-xl font-semibold mb-3 text-neutral-900" style={{ fontFamily: `${fontHeading}, serif` }}>
                  {s.title}
                </h3>
                <p className="text-[15px] text-neutral-600 leading-relaxed max-w-xs mx-auto">{s.description}</p>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
