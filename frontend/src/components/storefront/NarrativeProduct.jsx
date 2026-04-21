import React from "react";
import { CheckCircle } from "@phosphor-icons/react";
import { designAccents } from "./storefrontUtils";

export function NarrativeSections({ sections, design }) {
  if (!sections || sections.length === 0) return null;
  const { primary, fontHeading } = designAccents(design);

  return (
    <div className="space-y-16 md:space-y-24 mb-20">
      {sections.map((s, i) => (
        <section
          key={i}
          data-testid={`product-section-${i}`}
          className="grid grid-cols-1 md:grid-cols-12 gap-8 md:gap-12 items-start"
        >
          <div className="md:col-span-5">
            <div
              className="text-[11px] uppercase tracking-[0.25em] mb-3 font-medium"
              style={{ color: primary }}
            >
              {String(i + 1).padStart(2, "0")} · Section
            </div>
            <h2
              className="text-2xl md:text-3xl font-semibold leading-tight"
              style={{ fontFamily: `"${fontHeading}", serif` }}
            >
              {s.title}
            </h2>
          </div>
          <div className="md:col-span-7">
            <p className="text-[16px] md:text-[17px] leading-relaxed text-[#44403C]">
              {s.body}
            </p>
            {s.bullet_points?.length > 0 && (
              <ul className="mt-6 space-y-3">
                {s.bullet_points.map((bp, j) => (
                  <li key={j} className="flex items-start gap-3 text-[15px] text-[#57534E]">
                    <CheckCircle size={18} weight="fill" className="shrink-0 mt-0.5" style={{ color: primary }} />
                    <span>{bp}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </section>
      ))}
    </div>
  );
}

export function TechSpecs({ specs, design }) {
  if (!specs || specs.length === 0) return null;
  const { fontHeading } = designAccents(design);

  return (
    <section className="mb-20 bg-[#FAF7F2] rounded-3xl p-8 md:p-12">
      <h2
        className="text-2xl md:text-3xl font-semibold mb-8"
        style={{ fontFamily: `"${fontHeading}", serif` }}
      >
        Caractéristiques techniques
      </h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-4">
        {specs.map((spec, i) => (
          <div key={i} className="flex items-baseline justify-between border-b border-[#E7E5E4] pb-3">
            <span className="text-sm text-[#78716C]">{spec.label}</span>
            <span className="text-sm font-medium text-[#1C1917] text-right">{spec.value}</span>
          </div>
        ))}
      </div>
    </section>
  );
}

export function ProductFAQ({ faq, design }) {
  if (!faq || faq.length === 0) return null;
  const { primary, fontHeading } = designAccents(design);

  return (
    <section className="mb-20">
      <h2
        className="text-2xl md:text-3xl font-semibold mb-8"
        style={{ fontFamily: `"${fontHeading}", serif` }}
      >
        Questions sur ce produit
      </h2>
      <div className="space-y-3 max-w-3xl">
        {faq.map((it, i) => (
          <details
            key={i}
            data-testid={`product-faq-${i}`}
            className="bg-white rounded-xl border border-[#E7E5E4] p-5 group"
          >
            <summary className="cursor-pointer font-medium list-none flex items-center justify-between text-[#1C1917]">
              <span className="pr-4">{it.question}</span>
              <span
                className="w-6 h-6 rounded-full flex items-center justify-center text-xs group-open:rotate-45 transition-transform shrink-0"
                style={{ background: `${primary}14`, color: primary }}
              >
                +
              </span>
            </summary>
            <p className="text-[15px] mt-4 leading-relaxed text-[#57534E]">{it.answer}</p>
          </details>
        ))}
      </div>
    </section>
  );
}
