import React, { useState } from "react";
import { ArrowRight, CheckCircle } from "@phosphor-icons/react";
import axios from "axios";
import { useParams } from "react-router-dom";
import { designAccents } from "./storefrontUtils";
import { t } from "../../lib/i18n";
import { useShopSiteId } from "../../lib/shopSiteId";

const BACKEND = "";

/**
 * NewsletterCTA — MONOCHROME. Gray card on white canvas, split layout with
 * a poised heading on the left and the email form on the right.
 */
export default function NewsletterCTA({ design, lang = "fr" }) {
  const siteId = useShopSiteId();
  const [email, setEmail] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const { primary, accent, divider, textMuted, fontHeading } = designAccents(design);

  const submit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await axios.post(`${BACKEND}/api/public/sites/${siteId}/contact`, {
        email, name: "Newsletter", message: "Inscription newsletter", source: "newsletter",
      }).catch(() => null);
      setSubmitted(true);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <section className="py-20 md:py-28 px-6 bg-white" data-testid="storefront-newsletter">
      <div className="max-w-6xl mx-auto">
        <div
          className="grid grid-cols-1 lg:grid-cols-2 items-center gap-10 lg:gap-16 p-10 md:p-14"
          style={{ background: accent, borderRadius: "2px" }}
        >
          <div>
            <div className="flex items-center gap-3 mb-5">
              <span className="h-px w-10" style={{ background: primary }} />
              <span className="text-[11px] uppercase tracking-[0.4em]" style={{ color: primary }}>
                {t(lang, "newsletter_eyebrow")}
              </span>
            </div>
            <h2
              className="text-[32px] md:text-[42px] leading-[1.05] tracking-[-0.02em]"
              style={{ fontFamily: `"${fontHeading}", serif`, color: primary }}
            >
              {t(lang, "newsletter_cta_heading_line1")}<br />{t(lang, "newsletter_cta_heading_line2")}
            </h2>
            <p className="mt-5 text-[14px] max-w-md" style={{ color: textMuted }}>
              {t(lang, "newsletter_cta_body")}
            </p>
          </div>
          <div>
            {submitted ? (
              <div
                className="flex items-center gap-3 bg-white px-6 py-5"
                style={{ borderRadius: "2px", color: primary }}
                data-testid="newsletter-success"
              >
                <CheckCircle size={20} weight="fill" style={{ color: "#047857" }} />
                <span className="text-[14px]">{t(lang, "newsletter_cta_success")}</span>
              </div>
            ) : (
              <form onSubmit={submit} className="flex flex-col gap-3">
                <div className="flex gap-2 bg-white p-1" style={{ borderRadius: "2px", border: `1px solid ${divider}` }}>
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="votre@email.com"
                    data-testid="newsletter-input"
                    className="flex-1 h-12 px-4 bg-transparent text-[14px] focus:outline-none"
                    style={{ color: primary }}
                  />
                  <button
                    type="submit"
                    disabled={submitting}
                    data-testid="newsletter-submit"
                    className="h-12 px-5 text-white text-[13px] font-medium flex items-center justify-center gap-2 disabled:opacity-60 transition-all hover:gap-3"
                    style={{ background: primary, borderRadius: "2px" }}
                  >
                    {submitting ? t(lang, "newsletter_sending") : <>{t(lang, "newsletter_subscribe")} <ArrowRight size={13} weight="bold" /></>}
                  </button>
                </div>
                <div className="text-[11px]" style={{ color: textMuted }}>
                  {t(lang, "newsletter_consent_short")}
                </div>
              </form>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
