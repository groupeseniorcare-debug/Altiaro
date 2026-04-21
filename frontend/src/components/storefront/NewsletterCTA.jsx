import React, { useState } from "react";
import { Envelope, ArrowRight, CheckCircle } from "@phosphor-icons/react";
import axios from "axios";
import { useParams } from "react-router-dom";

const BACKEND = process.env.REACT_APP_BACKEND_URL;

/**
 * Newsletter signup CTA before footer.
 */
export default function NewsletterCTA({ design }) {
  const { siteId } = useParams();
  const [email, setEmail] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const primary = design?.brand?.primary_color || "#1C1917";
  const accent = design?.brand?.accent_color || "#F5F2EB";
  const fontHeading = design?.brand?.font_heading || "Fraunces";

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
    <section className="py-20 md:py-24 px-6" data-testid="storefront-newsletter" style={{ background: primary }}>
      <div className="max-w-3xl mx-auto text-center text-white">
        <Envelope size={36} weight="duotone" className="mx-auto mb-4 opacity-80" />
        <h2 className="text-3xl md:text-4xl mb-4" style={{ fontFamily: `${fontHeading}, serif` }}>
          Nos conseils directement dans votre boîte mail
        </h2>
        <p className="text-white/80 mb-8 text-[15px] max-w-xl mx-auto">
          Chaque mois, nos guides pratiques, nos nouveautés et des offres exclusives.
          Pas de spam, une seule newsletter par mois, promis.
        </p>
        {submitted ? (
          <div className="inline-flex items-center gap-2 bg-white/10 backdrop-blur rounded-full px-5 py-3 text-sm" data-testid="newsletter-success">
            <CheckCircle size={16} weight="fill" color="#34D399" />
            Merci ! Vous recevrez notre prochaine newsletter dans quelques jours.
          </div>
        ) : (
          <form onSubmit={submit} className="flex flex-col sm:flex-row gap-3 max-w-md mx-auto">
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="votre@email.com"
              data-testid="newsletter-input"
              className="flex-1 h-12 px-5 rounded-full text-neutral-900 text-sm focus:outline-none focus:ring-2 focus:ring-white/50"
            />
            <button type="submit" disabled={submitting} data-testid="newsletter-submit"
              className="h-12 px-6 rounded-full bg-white text-neutral-900 font-medium flex items-center justify-center gap-2 disabled:opacity-60 transition hover:bg-white/90">
              {submitting ? "Envoi…" : <>Je m'inscris <ArrowRight size={14} weight="bold" /></>}
            </button>
          </form>
        )}
        <div className="text-xs text-white/60 mt-4">
          En vous inscrivant, vous acceptez notre politique de confidentialité. Désinscription en 1 clic.
        </div>
      </div>
    </section>
  );
}
