import React from "react";
import { Star } from "@phosphor-icons/react";
import { designAccents } from "./storefrontUtils";

export function Testimonials({ design, lang }) {
  const items = design?.testimonials?.items || design?.testimonials;
  if (!items || items.length === 0) return null;
  const { primary, fontHeading } = designAccents(design);

  return (
    <section className="py-20 md:py-28" style={{ background: `${primary}08` }}>
      <div className="max-w-6xl mx-auto px-6 md:px-10">
        <div className="text-center mb-12">
          <div
            className="text-[11px] uppercase tracking-[0.25em] mb-3 font-medium"
            style={{ color: primary }}
          >
            Avis clients
          </div>
          <h2
            className="text-3xl md:text-4xl font-semibold"
            style={{ fontFamily: `"${fontHeading}", serif` }}
          >
            Ils en parlent mieux que nous
          </h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {items.slice(0, 6).map((tt, i) => {
            const text = typeof tt.text === "string"
              ? tt.text
              : (tt.quote?.[lang] || tt.quote?.fr || "");
            const loc = tt.location || tt.city || "";
            const rating = tt.rating || 5;
            return (
              <div
                key={i}
                className="bg-white rounded-2xl p-6 md:p-8 border border-[#E7E5E4]"
                data-testid={`testimonial-${i}`}
              >
                <div className="flex gap-0.5 mb-4" style={{ color: primary }}>
                  {Array.from({ length: rating }).map((_, j) => (
                    <Star key={j} size={16} weight="fill" />
                  ))}
                </div>
                <p className="text-[15px] leading-relaxed mb-5" style={{ color: "#44403C" }}>
                  &quot;{text}&quot;
                </p>
                <div className="text-sm font-medium text-[#1C1917]">{tt.name}</div>
                {loc && <div className="text-xs text-[#78716C]">{loc}</div>}
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
