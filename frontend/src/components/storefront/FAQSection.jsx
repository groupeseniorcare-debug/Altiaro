import React from "react";
import { designAccents } from "./storefrontUtils";
import { t } from "../../lib/i18n";

export function FAQSection({ design, lang }) {
  const { primary, accent, divider, textMuted, fontHeading } = designAccents(design);
  const items = design?.faq?.items || design?.faq;
  const list = Array.isArray(items) && items.length ? items : [
    { question: t(lang, "faq_delivery_q"),   answer: t(lang, "faq_delivery_a") },
    { question: t(lang, "faq_returns_q"),    answer: t(lang, "faq_returns_a") },
    { question: t(lang, "faq_contact_q"),    answer: t(lang, "faq_contact_a") },
    { question: t(lang, "faq_reimburse_q"),  answer: t(lang, "faq_reimburse_a") },
    { question: t(lang, "faq_install_q"),    answer: t(lang, "faq_install_a") },
    { question: t(lang, "faq_privacy_q"),    answer: t(lang, "faq_privacy_a") },
  ];

  return (
    <section className="py-24 md:py-36 px-6 bg-white" data-testid="storefront-faq" id="faq">
      <div className="max-w-5xl mx-auto grid grid-cols-1 lg:grid-cols-[auto_1fr] gap-12 lg:gap-20 items-start">
        {/* Sticky section title on the left */}
        <div className="lg:sticky lg:top-32 lg:w-64">
          <div className="flex items-center gap-3 mb-5">
            <span className="h-px w-10" style={{ background: primary }} />
            <span className="text-[11px] uppercase tracking-[0.4em]" style={{ color: primary }}>
              FAQ
            </span>
          </div>
          <h2
            className="text-[36px] md:text-[48px] leading-[1.02] tracking-[-0.02em]"
            style={{ fontFamily: `"${fontHeading}", serif`, color: primary }}
          >
            {t(lang, "faq_title_line1")}<br />{t(lang, "faq_title_line2")}
          </h2>
          <p className="mt-4 text-[13px]" style={{ color: textMuted }}>
            {t(lang, "faq_helper")}
          </p>
        </div>

        {/* Question list */}
        <div className="flex-1">
          <div style={{ borderTop: `1px solid ${divider}` }}>
            {list.map((it, i) => {
              const q = typeof it.question === "string" ? it.question : (it.q?.[lang] || it.q?.fr || "");
              const a = typeof it.answer === "string" ? it.answer : (it.a?.[lang] || it.a?.fr || "");
              return (
                <details
                  key={i}
                  className="group py-6"
                  style={{ borderBottom: `1px solid ${divider}` }}
                  data-testid={`faq-${i}`}
                >
                  <summary
                    className="cursor-pointer list-none flex items-center justify-between gap-6 text-[17px] md:text-[19px]"
                    style={{ fontFamily: `"${fontHeading}", serif`, color: primary }}
                  >
                    <span>{q}</span>
                    <span
                      className="w-9 h-9 rounded-full flex items-center justify-center shrink-0 text-lg group-open:rotate-45 transition-transform"
                      style={{ background: accent, color: primary }}
                    >
                      +
                    </span>
                  </summary>
                  <p className="text-[15px] mt-4 leading-relaxed pr-14" style={{ color: textMuted }}>
                    {a}
                  </p>
                </details>
              );
            })}
          </div>
        </div>
      </div>
    </section>
  );
}
