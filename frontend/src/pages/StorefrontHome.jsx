import React, { useEffect, useState } from "react";
import axios from "axios";
import { motion } from "framer-motion";
import StorefrontLayout from "../components/StorefrontLayout";
import { t, pickLang } from "../lib/i18n";
import SEOHead from "../components/SEOHead";
import {
  BACKEND_URL,
  useSiteAndLang,
  designText,
  buildHreflangs,
} from "../components/storefront/storefrontUtils";
import { Hero } from "../components/storefront/Hero";
import { Benefits } from "../components/storefront/Benefits";
import { ProductGrid } from "../components/storefront/ProductGrid";
import { Testimonials } from "../components/storefront/Testimonials";
import { FAQSection } from "../components/storefront/FAQSection";
import { FinalCTA } from "../components/storefront/FinalCTA";
import ValuesSection from "../components/storefront/ValuesSection";
import FounderStory from "../components/storefront/FounderStory";
import PressLogos from "../components/storefront/PressLogos";
import NewsletterCTA from "../components/storefront/NewsletterCTA";
import CollectionsShowcase from "../components/storefront/CollectionsShowcase";
import BlogTeaser from "../components/storefront/BlogTeaser";
import BuyingGuide from "../components/storefront/BuyingGuide";
import LifestyleEditorial from "../components/storefront/LifestyleEditorial";
import FeaturedProduct from "../components/storefront/FeaturedProduct";
import InstagramGrid from "../components/storefront/InstagramGrid";
import Manifesto from "../components/storefront/Manifesto";
import BrandProcess from "../components/storefront/BrandProcess";

/* =========================================================
 * STOREFRONT HOME — Phase 4 : extrait de `pages/Storefront.jsx`
 * ========================================================= */
export default function StorefrontHome() {
  const { siteId, site, design, lang, setLang, availableLangs } = useSiteAndLang();
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    axios
      .get(`${BACKEND_URL}/api/public/sites/${siteId}/products`)
      .then(({ data }) => setProducts(data))
      .finally(() => setLoading(false));
  }, [siteId]);

  if (site?.error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#FDFBF7] text-[#78716C]">
        Boutique introuvable.
      </div>
    );
  }

  const heroTitle = designText(design, "hero.title", lang) || t(lang, "shop_title");
  const heroSub = designText(design, "hero.subtitle", lang) || t(lang, "shop_subtitle");
  const seoTitle =
    designText(design, "seo.title", lang) || `${site?.name || ""} · ${heroTitle}`;
  const seoDesc =
    designText(design, "seo.description", lang) || heroSub;
  const canonical =
    typeof window !== "undefined"
      ? `${window.location.origin}/shop/${siteId}`
      : undefined;
  const orgSchema = site
    ? {
        "@context": "https://schema.org",
        "@type": design?.contact?.address ? "LocalBusiness" : "OnlineStore",
        name: site.name,
        url: canonical,
        logo: design?.brand?.logo_url,
        image: design?.brand?.logo_url,
        description: seoDesc,
        areaServed: (site.selected_countries && site.selected_countries.length
          ? site.selected_countries
          : ["FR"]
        ).map((c) => ({ "@type": "Country", name: c })),
        knowsLanguage: ["fr-FR", "en"],
        sameAs: [
          design?.social?.facebook,
          design?.social?.instagram,
          design?.social?.youtube,
          design?.social?.linkedin,
          design?.social?.tiktok,
          design?.social?.pinterest,
        ].filter(Boolean),
        contactPoint: design?.contact?.support_phone
          ? [{
              "@type": "ContactPoint",
              contactType: "customer service",
              telephone: design.contact.support_phone,
              email: design?.contact?.support_email,
              areaServed: "FR",
              availableLanguage: ["French"],
            }]
          : undefined,
        address: design?.contact?.address
          ? {
              "@type": "PostalAddress",
              streetAddress: design.contact.address,
              addressCountry: "FR",
            }
          : undefined,
        openingHoursSpecification: design?.contact?.address && design?.contact?.support_hours
          ? [{
              "@type": "OpeningHoursSpecification",
              description: design.contact.support_hours,
            }]
          : undefined,
      }
    : null;
  const websiteSchema = site
    ? {
        "@context": "https://schema.org",
        "@type": "WebSite",
        name: site.name,
        url: canonical,
        potentialAction: {
          "@type": "SearchAction",
          target: `${canonical}?q={search_term_string}`,
          "query-input": "required name=search_term_string",
        },
      }
    : null;
  const itemListSchema = products?.length
    ? {
        "@context": "https://schema.org",
        "@type": "ItemList",
        itemListElement: products.slice(0, 12).map((p, idx) => ({
          "@type": "ListItem",
          position: idx + 1,
          url: `${canonical}/product/${p.id}`,
          name: pickLang(p.name, lang),
        })),
      }
    : null;
  const faqFromDesign = design?.faq?.items || design?.faq;
  const faqArray = Array.isArray(faqFromDesign) && faqFromDesign.length > 0
    ? faqFromDesign
    : [
        { question: "Sous quel délai serai-je livré ?", answer: "Les commandes sont expédiées sous 24h ouvrées. Réception sous 48 à 72h partout en France métropolitaine." },
        { question: "Puis-je retourner un produit ?", answer: "Oui, 14 jours à réception pour changer d'avis. Frais de retour à notre charge, remboursement sous 5 jours." },
        { question: "Comment contacter un conseiller ?", answer: "Par téléphone Lun–Ven 9h–18h ou par email, réponse moyenne en 2h ouvrées. Un vrai humain, jamais de chatbot." },
      ];
  const faqSchema = {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    speakable: {
      "@type": "SpeakableSpecification",
      cssSelector: ["[data-speakable='true']"],
    },
    mainEntity: faqArray.slice(0, 8).map((it) => {
      const q = typeof it.question === "string" ? it.question : (it.q?.[lang] || it.q?.fr || "");
      const a = typeof it.answer === "string" ? it.answer : (it.a?.[lang] || it.a?.fr || "");
      return { "@type": "Question", name: q, acceptedAnswer: { "@type": "Answer", text: a } };
    }),
  };

  return (
    <StorefrontLayout lang={lang} setLang={setLang} availableLangs={availableLangs} site={site} design={design}>
      <div data-testid="storefront-home">
        <SEOHead
          title={seoTitle}
          description={seoDesc}
          canonical={canonical}
          image={design?.brand?.logo_url}
          siteName={site?.name}
          langs={buildHreflangs(site, "")}
          schema={[orgSchema, websiteSchema, itemListSchema, faqSchema].filter(Boolean)}
        />
        <Hero site={site} design={design} lang={lang} products={products} />
        {renderHomepageSections({
          design, site, siteId, products, loading, lang,
        })}
      </div>
    </StorefrontLayout>
  );
}

// ---------------------------------------------------------------------
// Homepage sections renderer — respects design.homepage_sections config.
// - Missing config → default order.
// - Section with no real data is silently skipped.
// ---------------------------------------------------------------------
const DEFAULT_HOMEPAGE_ORDER = [
  { key: "press_logos",        visible: true },
  { key: "manifesto",          visible: true },
  { key: "products",           visible: true },
  { key: "collections",        visible: true },
  { key: "brand_process",      visible: true },
  { key: "founder_story",      visible: true },
  { key: "benefits",           visible: true },
  { key: "testimonials",       visible: true },
  { key: "lifestyle_editorial", visible: false },
  { key: "featured_product",   visible: false },
  { key: "values",             visible: false },
  { key: "buying_guide",       visible: false },
  { key: "instagram",          visible: false },
  { key: "blog_teaser",        visible: false },
  { key: "faq",                visible: true },
  { key: "newsletter",         visible: true },
  { key: "final_cta",          visible: false },
];

function hasData(key, design, products) {
  switch (key) {
    case "benefits":
    case "testimonials":
    case "faq":
    case "newsletter":
    case "final_cta":
    case "products":
    case "press_logos":
    case "collections":
    case "founder_story":
    case "manifesto":
    case "brand_process":
      return true;
    case "featured_product": return !!(products?.some((p) => p.featured));
    case "lifestyle_editorial": return !!(design?.editorial?.title || design?.editorial?.image);
    case "values": return !!(design?.values?.length);
    case "buying_guide": return !!(design?.buying_guide?.items?.length);
    case "instagram": return !!(design?.instagram?.posts?.length || design?.instagram?.handle);
    case "blog_teaser": return !!(design?.blog_posts?.length);
    default: return false;
  }
}

function sectionWrapperClass() {
  return "bg-white";
}

function renderHomepageSections({ design, site, siteId, products, loading, lang }) {
  const cfg = Array.isArray(design?.homepage_sections) && design.homepage_sections.length
    ? design.homepage_sections
    : DEFAULT_HOMEPAGE_ORDER;
  const list = cfg.filter((s) => s.key !== "hero");
  const visible = list.filter((s) => s.visible && hasData(s.key, design, products));
  return visible.map((s, idx) => {
    const inner = (() => {
      switch (s.key) {
        case "press_logos":
          return <PressLogos mentions={design?.press_mentions} design={design} lang={lang} />;
        case "manifesto":
          return <Manifesto design={design} lang={lang} />;
        case "brand_process":
          return <BrandProcess design={design} lang={lang} />;
        case "benefits":
          return <Benefits design={design} lang={lang} />;
        case "collections":
          return <CollectionsShowcase collections={design?.collections} lang={lang} design={design} />;
        case "products":
          return <ProductGrid siteId={siteId} products={products} loading={loading} design={design} lang={lang} />;
        case "featured_product":
          return <FeaturedProduct products={products} design={design} lang={lang} />;
        case "lifestyle_editorial":
          return <LifestyleEditorial editorial={design?.editorial} lang={lang} design={design} />;
        case "values":
          return <ValuesSection values={design?.values} lang={lang} design={design} />;
        case "buying_guide":
          return <BuyingGuide guide={design?.buying_guide} design={design} />;
        case "testimonials":
          return <Testimonials design={design} lang={lang} />;
        case "founder_story":
          return <FounderStory story={design?.founder_story} lang={lang} design={design} />;
        case "instagram":
          return <InstagramGrid instagram={design?.instagram} design={design} />;
        case "blog_teaser":
          return <BlogTeaser posts={design?.blog_posts} lang={lang} design={design} />;
        case "faq":
          return <FAQSection design={design} lang={lang} />;
        case "newsletter":
          return <NewsletterCTA design={design} lang={lang} />;
        case "final_cta":
          return <FinalCTA design={design} lang={lang} />;
        default:
          return null;
      }
    })();
    if (!inner) return null;
    const anchorId = ({
      press_logos: "press",
      collections: "collections",
      products: "products",
      founder_story: "story",
      faq: "faq",
    })[s.key];
    return (
      <motion.div
        key={s.key}
        id={anchorId}
        initial={{ opacity: 0, y: 32 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, margin: "-80px" }}
        transition={{ duration: 0.5, ease: "easeOut" }}
        className={sectionWrapperClass(s.key, idx)}
      >
        {inner}
      </motion.div>
    );
  });
}
