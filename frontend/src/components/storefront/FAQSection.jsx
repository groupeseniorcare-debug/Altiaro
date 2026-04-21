import React from "react";
import { designAccents } from "./storefrontUtils";

export function FAQSection({ design, lang }) {
  const items = design?.faq?.items || design?.faq;
  if (!items || items.length === 0) return null;
  const { primary, fontHeading } = designAccents(design);

  return (
    <section className="max-w-3xl mx-auto px-6 md:px-10 py-20 md:py-28">
      <div className="text-center mb-12">
        <div
          className="text-[11px] uppercase tracking-[0.25em] mb-3 font-medium"
          style={{ color: primary }}
        >
          FAQ
        </div>
        <h2
          className="text-3xl md:text-4xl font-semibold"
          style={{ fontFamily: `"${fontHeading}", serif` }}
        >
          Questions fréquentes
        </h2>
      </div>
      <div className="space-y-3">
        {items.map((it, i) => {
          const q = typeof it.question === "string"
            ? it.question
            : (it.q?.[lang] || it.q?.fr || "");
          const a = typeof it.answer === "string"
            ? it.answer
            : (it.a?.[lang] || it.a?.fr || "");
          return (
            <details
              key={i}
              className="bg-white rounded-xl border border-[#E7E5E4] p-5 group hover:border-[#D6D3D1] transition"
              data-testid={`faq-${i}`}
            >
              <summary className="cursor-pointer font-medium list-none flex items-center justify-between text-[#1C1917]">
                <span className="pr-4">{q}</span>
                <span
                  className="w-6 h-6 rounded-full flex items-center justify-center text-xs group-open:rotate-45 transition-transform shrink-0"
                  style={{ background: `${primary}14`, color: primary }}
                >
                  +
                </span>
              </summary>
              <p className="text-[15px] mt-4 leading-relaxed" style={{ color: "#57534E" }}>
                {a}
              </p>
            </details>
          );
        })}
      </div>
    </section>
  );
}
