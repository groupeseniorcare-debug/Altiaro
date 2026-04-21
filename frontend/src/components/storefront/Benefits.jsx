import React from "react";
import { ShieldCheck } from "@phosphor-icons/react";
import { BENEFIT_ICON, designAccents } from "./storefrontUtils";

export function Benefits({ design, lang }) {
  const items = design?.benefits?.items || design?.benefits;
  if (!items || items.length === 0) return null;
  const { primary, fontHeading } = designAccents(design);

  return (
    <section className="max-w-6xl mx-auto px-6 md:px-10 py-16 md:py-24">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-8">
        {items.map((b, i) => {
          const title = typeof b.title === "string"
            ? b.title
            : (b.title?.[lang] || b.title?.fr || "");
          const desc = typeof b.description === "string"
            ? b.description
            : (b.desc?.[lang] || b.desc?.fr || b.description?.[lang] || "");
          const Icon = BENEFIT_ICON[b.icon] || ShieldCheck;
          return (
            <div key={i} className="text-center" data-testid={`benefit-${i}`}>
              <div
                className="w-16 h-16 mx-auto rounded-full flex items-center justify-center mb-5"
                style={{ background: `${primary}14`, color: primary }}
              >
                <Icon size={28} weight="duotone" />
              </div>
              <div
                className="font-semibold text-lg mb-2"
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
