import React from "react";
import { pickLang } from "./storefrontUtils";

/**
 * Founder's story / manifesto section.
 * design.founder_story = { image, name, role, quote, signature }
 */
export default function FounderStory({ story, lang = "fr", design }) {
  const s = story || {
    image: null,
    name: "Camille Lefèvre",
    role: "Fondatrice",
    quote: "J'ai créé cette marque après avoir vu ma grand-mère lutter au quotidien. Chaque produit qu'on sélectionne, je le choisis comme si c'était pour elle.",
    signature: "Camille L.",
  };

  const accent = design?.brand?.accent_color || "#F5F2EB";
  const fontHeading = design?.brand?.font_heading || "Fraunces";
  const primary = design?.brand?.primary_color || "#1C1917";

  const quote = pickLang(s.quote, lang) || s.quote;
  const role = pickLang(s.role, lang) || s.role;

  return (
    <section className="py-20 md:py-28 px-6 bg-white" data-testid="storefront-founder">
      <div className="max-w-5xl mx-auto grid grid-cols-1 md:grid-cols-5 gap-10 md:gap-16 items-center">
        <div className="md:col-span-2 relative">
          <div className="aspect-[4/5] rounded-3xl overflow-hidden" style={{ background: accent }}>
            {s.image ? (
              <img src={s.image} alt={s.name} className="w-full h-full object-cover" />
            ) : (
              <div className="w-full h-full flex items-center justify-center">
                <div className="text-center px-6">
                  <div className="text-6xl mb-3 opacity-40">✍️</div>
                  <div className="text-xs uppercase tracking-widest text-neutral-500">Photo fondateur</div>
                </div>
              </div>
            )}
          </div>
        </div>
        <div className="md:col-span-3">
          <div className="text-[11px] uppercase tracking-[0.2em] text-neutral-500 mb-3">Notre histoire</div>
          <blockquote className="text-2xl md:text-3xl leading-snug mb-6"
            style={{ fontFamily: `${fontHeading}, serif`, color: "#1C1917" }}>
            <span style={{ color: primary }}>«</span> {quote} <span style={{ color: primary }}>»</span>
          </blockquote>
          <div className="flex items-center gap-3">
            <div className="h-px w-12" style={{ background: primary }} />
            <div>
              <div className="font-semibold text-neutral-900">{s.name}</div>
              <div className="text-sm text-neutral-500">{role}</div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
