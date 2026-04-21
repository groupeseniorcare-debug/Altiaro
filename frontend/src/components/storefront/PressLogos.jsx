import React from "react";
import { Newspaper, Star } from "@phosphor-icons/react";

/**
 * Press logos / mentions — marques media citant la boutique.
 * design.press_mentions = [{name, logo_url?}]
 */
export default function PressLogos({ mentions, design }) {
  const list = mentions?.length ? mentions : [
    { name: "Notre Temps" }, { name: "60 Millions" }, { name: "Le Figaro" },
    { name: "France Info" }, { name: "Silver Eco" }, { name: "Capital" },
  ];
  const primary = design?.brand?.primary_color || "#1C1917";

  return (
    <section className="py-14 px-6 bg-white border-y border-neutral-100" data-testid="storefront-press">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center justify-center gap-2 mb-8">
          <Newspaper size={16} weight="duotone" className="text-neutral-500" />
          <div className="text-[11px] uppercase tracking-[0.2em] text-neutral-500">Ils parlent de nous</div>
        </div>
        <div className="grid grid-cols-3 md:grid-cols-6 gap-6 md:gap-10 items-center opacity-60 hover:opacity-100 transition-opacity">
          {list.slice(0, 6).map((m, i) => (
            <div key={i} className="text-center" data-testid={`press-${i}`}>
              {m.logo_url ? (
                <img src={m.logo_url} alt={m.name} className="h-10 mx-auto object-contain grayscale hover:grayscale-0 transition" />
              ) : (
                <div className="font-serif italic text-neutral-700 text-base md:text-lg">{m.name}</div>
              )}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
