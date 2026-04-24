import React from "react";
import { designAccents } from "./storefrontUtils";
import { t } from "../../lib/i18n";

/**
 * PressLogos — MONOCHROME horizontal ribbon. White canvas with a thin top
 * and bottom hairline. Press names are rendered in italic serif, grayscale.
 */
export default function PressLogos({ mentions, design, lang = "fr" }) {
  const { primary, divider, textMuted, fontHeading } = designAccents(design);
  const list = (mentions && mentions.length) ? mentions : [
    { name: "Le Figaro" }, { name: "Les Échos" }, { name: "Maison & Travaux" },
    { name: "Notre Temps" }, { name: "60 Millions de Consommateurs" }, { name: "Version Femina" },
  ];

  return (
    <section
      className="bg-white py-16 md:py-20 px-6"
      data-testid="storefront-press"
      id="press"
      style={{ borderTop: `1px solid ${divider}`, borderBottom: `1px solid ${divider}` }}
    >
      <div className="max-w-7xl mx-auto">
        <div
          className="text-center text-[10px] uppercase tracking-[0.5em] mb-8"
          style={{ color: textMuted }}
        >
          — {t(lang, "press_eyebrow")} —
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-x-8 gap-y-8 md:gap-y-6 items-center">
          {list.slice(0, 6).map((m, i) => (
            <div
              key={i}
              className="text-center text-[16px] md:text-[17px] italic opacity-70 hover:opacity-100 transition-opacity"
              style={{ fontFamily: `"${fontHeading}", serif`, color: primary }}
              data-testid={`press-${i}`}
            >
              {typeof m === "string" ? m : m.name}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
