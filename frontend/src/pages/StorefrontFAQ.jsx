import React, { useEffect, useState } from "react";
import axios from "axios";
import { ChevronDown } from "lucide-react";
import StorefrontLayout from "../components/StorefrontLayout";
import SEOHead from "../components/SEOHead";
import { pickLang, t } from "../lib/i18n";
import { useShopSiteId } from "../lib/shopSiteId";
import { useSiteAndLang } from "../components/storefront/storefrontUtils";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

/**
 * Sprint 4 fix — page FAQ storefront (combat le 404 sur le link footer).
 *
 * Lit en priorité `design.faq.items` (renseigné par launch-auto / `_inject_faq`)
 * sinon `design.faq` (legacy array). Affiche chaque item dans un `<details>`
 * accessible et SEO-friendly + JSON-LD FAQPage.
 *
 * Compatible custom domain (useShopSiteId hydrate siteId depuis le host).
 */
export default function StorefrontFAQ() {
  const siteId = useShopSiteId();
  const { site: siteFromContext, design: designFromContext, lang, setLang, availableLangs } = useSiteAndLang();
  const [site, setSite] = useState(siteFromContext || null);
  const [openIdx, setOpenIdx] = useState(null);

  // useSiteAndLang hydrate le contexte — on le synchronise localement pour
  // pouvoir aussi tomber back sur un GET public direct si besoin.
  useEffect(() => {
    if (siteFromContext) { setSite(siteFromContext); return; }
    if (!siteId) return;
    axios
      .get(`${BACKEND_URL}/api/public/sites/${siteId}`)
      .then((r) => setSite(r.data || null))
      .catch(() => setSite(null));
  }, [siteId, siteFromContext]);

  if (!site) {
    return (
      <div style={{ padding: "4rem 1rem", textAlign: "center" }}>
        <p>{t(lang || "fr", "loading") || "Chargement…"}</p>
      </div>
    );
  }

  const design = designFromContext || site.design || {};
  const faqRaw = design.faq;
  let items = [];
  if (Array.isArray(faqRaw?.items)) items = faqRaw.items;
  else if (Array.isArray(faqRaw)) items = faqRaw;
  else if (faqRaw && typeof faqRaw === "object")
    items = Object.values(faqRaw).filter((x) => x && (x.q || x.question));

  const brand = site.name || "Boutique";
  const pageTitle = `FAQ · ${brand}`;
  const description =
    pickLang(design?.brand?.tagline, lang) ||
    `Questions fréquentes — ${brand}`;

  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    mainEntity: items
      .map((it) => {
        const q = pickLang(it.q || it.question, lang) || "";
        const a = pickLang(it.a || it.answer, lang) || "";
        if (!q || !a) return null;
        return {
          "@type": "Question",
          name: q,
          acceptedAnswer: { "@type": "Answer", text: a },
        };
      })
      .filter(Boolean),
  };

  return (
    <StorefrontLayout
      site={site}
      design={design}
      lang={lang}
      setLang={setLang}
      availableLangs={availableLangs || site.available_languages || ["fr", "en", "de", "nl", "it", "es"]}
    >
      <SEOHead
        title={pageTitle}
        description={description}
        canonical={typeof window !== "undefined" ? `${window.location.origin}${window.location.pathname}` : undefined}
        schema={jsonLd.mainEntity.length > 0 ? jsonLd : undefined}
      />

      <main className="max-w-3xl mx-auto px-4 py-12 lg:py-20" data-testid="storefront-faq-page">
        <header className="mb-10 lg:mb-14 text-center">
          <h1 className="text-4xl lg:text-5xl font-serif font-semibold text-stone-900 leading-tight mb-4">
            {t(lang, "faq_title") || "Questions fréquentes"}
          </h1>
          <p className="text-stone-600 text-lg">
            {t(lang, "faq_subtitle") ||
              "Tout ce que vous voulez savoir avant de commander."}
          </p>
        </header>

        {items.length === 0 ? (
          <p className="text-stone-500 text-center py-16" data-testid="faq-empty">
            {t(lang, "faq_empty") ||
              "Aucune question pour le moment. Contactez-nous, nous vous répondons sous 24h."}
          </p>
        ) : (
          <div className="divide-y divide-stone-200 border-y border-stone-200">
            {items.map((it, idx) => {
              const q = pickLang(it.q || it.question, lang) || "";
              const a = pickLang(it.a || it.answer, lang) || "";
              const isOpen = openIdx === idx;
              if (!q || !a) return null;
              return (
                <details
                  key={idx}
                  open={isOpen}
                  className="group py-5"
                  data-testid={`faq-item-${idx}`}
                  onToggle={(e) =>
                    setOpenIdx(e.currentTarget.open ? idx : null)
                  }
                >
                  <summary className="flex items-center justify-between cursor-pointer list-none">
                    <span className="text-base lg:text-lg font-medium text-stone-900 pr-4">
                      {q}
                    </span>
                    <ChevronDown
                      className={`w-5 h-5 text-stone-500 flex-shrink-0 transition-transform duration-200 ${
                        isOpen ? "rotate-180" : ""
                      }`}
                    />
                  </summary>
                  <div className="mt-4 text-stone-600 leading-relaxed whitespace-pre-line">
                    {a}
                  </div>
                </details>
              );
            })}
          </div>
        )}

        <section className="mt-16 p-8 bg-stone-50 rounded-2xl text-center">
          <h2 className="text-xl font-semibold text-stone-900 mb-2">
            {t(lang, "faq_more_questions") || "Une autre question ?"}
          </h2>
          <p className="text-stone-600 mb-4">
            {t(lang, "faq_contact_us") ||
              "Notre équipe vous répond sous 24h en jours ouvrés."}
          </p>
          <a
            href={`/shop/${siteId}/contact`}
            className="inline-block px-6 py-3 bg-stone-900 text-white rounded-full hover:bg-stone-700 transition"
          >
            {t(lang, "faq_contact_button") || "Nous contacter"}
          </a>
        </section>
      </main>
    </StorefrontLayout>
  );
}
