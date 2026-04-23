import React, { useEffect, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import axios from "axios";
import { motion } from "framer-motion";
import StorefrontLayout from "../components/StorefrontLayout";
import { t, pickLang, COUNTRY_OPTIONS, countryLabel } from "../lib/i18n";
import {
  addToCart,
  readCart,
  updateQty,
  removeFromCart,
  cartTotals,
  clearCart,
} from "../lib/cart";
import {
  ArrowRight,
  CheckCircle,
  Trash,
  ShoppingBagOpen,
  ShieldCheck,
  Truck,
  Star,
} from "@phosphor-icons/react";
import SEOHead from "../components/SEOHead";

import {
  BACKEND_URL,
  useSiteAndLang,
  designText,
  formatPrice,
  designAccents,
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
import {
  NarrativeSections,
  TechSpecs,
  ProductFAQ,
} from "../components/storefront/NarrativeProduct";
import ProductGallery from "../components/storefront/ProductGallery";
import ProductReviews from "../components/storefront/ProductReviews";
import CrossSellProducts from "../components/storefront/CrossSellProducts";
import UpsellsRecommendations from "../components/storefront/UpsellsRecommendations";
import DeliveryEstimate from "../components/storefront/DeliveryEstimate";
import ProductBundle from "../components/storefront/ProductBundle";
import PaymentOptions from "../components/storefront/PaymentOptions";
import MobileStickyBuy from "../components/storefront/MobileStickyBuy";
import Manifesto from "../components/storefront/Manifesto";
import {
  PeopleAlsoAsk,
  BestForNotFor,
  UsageSteps,
  RelatedQueries,
  LastUpdatedBadge,
} from "../components/storefront/ProductSEOBlocks";

/* =========================================================
 * STOREFRONT HOME
 * ========================================================= */
export function StorefrontHome() {
  const { siteId, site, design, lang, setLang } = useSiteAndLang();
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
        "@type": "Organization",
        name: site.name,
        url: canonical,
        logo: design?.brand?.logo_url,
        description: seoDesc,
        sameAs: [
          design?.social?.facebook,
          design?.social?.instagram,
          design?.social?.youtube,
          design?.social?.linkedin,
        ].filter(Boolean),
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
    mainEntity: faqArray.slice(0, 8).map((it) => {
      const q = typeof it.question === "string" ? it.question : (it.q?.[lang] || it.q?.fr || "");
      const a = typeof it.answer === "string" ? it.answer : (it.a?.[lang] || it.a?.fr || "");
      return { "@type": "Question", name: q, acceptedAnswer: { "@type": "Answer", text: a } };
    }),
  };

  return (
    <StorefrontLayout lang={lang} setLang={setLang} site={site} design={design}>
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
  { key: "lifestyle_editorial", visible: false },
  { key: "founder_story",      visible: true },
  { key: "benefits",           visible: true },
  { key: "testimonials",       visible: true },
  { key: "featured_product",   visible: false },
  { key: "values",             visible: false },
  { key: "buying_guide",       visible: false },
  { key: "instagram",          visible: false },
  { key: "blog_teaser",        visible: false },
  { key: "faq",                visible: true },
  { key: "newsletter",         visible: true },
  { key: "final_cta",          visible: true },
];

function hasData(key, design, products) {
  switch (key) {
    // These always render with a premium fallback — so newly-launched sites look
    // complete from day 1, before the Concepteur has filled in their own data.
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
      return true;
    // These require real data — no fallback makes sense
    case "featured_product": return !!(products?.some((p) => p.featured));
    case "lifestyle_editorial": return !!(design?.editorial?.title || design?.editorial?.image);
    case "values": return !!(design?.values?.length);
    case "buying_guide": return !!(design?.buying_guide?.items?.length);
    case "instagram": return !!(design?.instagram?.posts?.length || design?.instagram?.handle);
    case "blog_teaser": return !!(design?.blog_posts?.length);
    default: return false;
  }
}

// MONOCHROME TEMPLATE — white canvas, black ink, gray cards. All sections sit on
// pure white. Rhythm is created by the cards themselves (bg-[#F5F5F5]) and by
// generous vertical spacing, not by cream/beige backgrounds.
const DARK_SECTIONS = new Set([]);
const GRAY_SECTIONS = new Set([]); // everything stays on white

function sectionWrapperClass() {
  return "bg-white";
}

function renderHomepageSections({ design, site, siteId, products, loading, lang }) {
  const cfg = Array.isArray(design?.homepage_sections) && design.homepage_sections.length
    ? design.homepage_sections
    : DEFAULT_HOMEPAGE_ORDER;
  // Hero is always rendered on top
  const list = cfg.filter((s) => s.key !== "hero");
  const visible = list.filter((s) => s.visible && hasData(s.key, design, products));
  return visible.map((s, idx) => {
    const inner = (() => {
      switch (s.key) {
        case "press_logos":
          return <PressLogos mentions={design?.press_mentions} design={design} />;
        case "manifesto":
          return <Manifesto design={design} lang={lang} />;
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
          return <NewsletterCTA design={design} />;
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

/* =========================================================
 * PRODUCT DETAIL
 * ========================================================= */
export function StorefrontProduct() {
  const { siteId, productId } = useParams();
  const { site, design, lang, setLang } = useSiteAndLang();
  const navigate = useNavigate();
  const [p, setP] = useState(null);
  const [loading, setLoading] = useState(true);
  const [added, setAdded] = useState(false);
  const [qty, setQty] = useState(1);

  const { primary, fontHeading } = designAccents(design);

  useEffect(() => {
    axios
      .get(`${BACKEND_URL}/api/public/sites/${siteId}/products/${productId}`)
      .then(({ data }) => {
        setP(data);
        // GA4 / Google Ads tracking
        try { window.altiaroTrack?.viewItem?.(data, lang); } catch (_) {}
      })
      .catch(() => setP(null))
      .finally(() => setLoading(false));
  }, [siteId, productId, lang]);

  const handleAdd = () => {
    addToCart(siteId, p, lang, qty);
    try { window.altiaroTrack?.addToCart?.(p, qty, lang); } catch (_) {}
    setAdded(true);
    // Auto-open the cart drawer to confirm
    window.dispatchEvent(new Event("cf_cart_open"));
    setTimeout(() => setAdded(false), 1500);
  };

  if (loading) {
    return (
      <StorefrontLayout lang={lang} setLang={setLang} site={site} design={design}>
        <div className="max-w-6xl mx-auto px-6 py-12 text-[#78716C]">…</div>
      </StorefrontLayout>
    );
  }
  if (!p) {
    return (
      <StorefrontLayout lang={lang} setLang={setLang} site={site} design={design}>
        <div className="max-w-6xl mx-auto px-6 py-12">
          <div className="text-[#9F1239]">404 · Produit introuvable.</div>
          <button onClick={() => navigate(`/shop/${siteId}`)} className="mt-4 text-[#B84B31]">
            ← {t(lang, "back_to_shop")}
          </button>
        </div>
      </StorefrontLayout>
    );
  }

  return (
    <StorefrontLayout lang={lang} setLang={setLang} site={site} design={design}>
      <SEOHead
        title={
          p.narrative?.seo?.title
          || `${pickLang(p.name, lang)} · ${site?.name || ""}`
        }
        description={
          p.narrative?.seo?.description
          || p.narrative?.subheadline
          || pickLang(p.description, lang)
          || pickLang(p.name, lang)
        }
        canonical={
          typeof window !== "undefined"
            ? `${window.location.origin}/shop/${siteId}/product/${p.id}`
            : undefined
        }
        image={p.images?.[0]}
        type="product"
        siteName={site?.name}
        keywords={
          p.narrative?.seo?.keywords?.join(", ")
          || [pickLang(p.name, lang), p.category, ...(p.tags || [])].filter(Boolean).join(", ")
        }
        langs={buildHreflangs(site, `/product/${p.id}`)}
        schema={[
          // Product schema (with offer, rating, reviews)
          {
            "@context": "https://schema.org",
            "@type": "Product",
            name: pickLang(p.name, lang),
            description: p.narrative?.subheadline || pickLang(p.description, lang),
            image: p.images || [],
            sku: p.sku,
            mpn: p.sku,
            brand: { "@type": "Brand", name: site?.name },
            category: p.category || undefined,
            aggregateRating: (p.rating?.count ?? 127) > 0 ? {
              "@type": "AggregateRating",
              ratingValue: (p.rating?.score ?? 4.8).toFixed(1),
              reviewCount: p.rating?.count ?? 127,
              bestRating: 5,
              worstRating: 1,
            } : undefined,
            review: (p.reviews || []).slice(0, 4).map((r) => ({
              "@type": "Review",
              author: { "@type": "Person", name: r.author },
              datePublished: r.date_iso || undefined,
              reviewRating: { "@type": "Rating", ratingValue: r.rating, bestRating: 5 },
              reviewBody: r.body,
              name: r.title,
            })),
            offers: {
              "@type": "Offer",
              priceCurrency: p.currency || "EUR",
              price: p.price,
              priceValidUntil: new Date(Date.now() + 365 * 24 * 3600 * 1000).toISOString().slice(0, 10),
              availability:
                p.stock === null || p.stock > 0
                  ? "https://schema.org/InStock"
                  : "https://schema.org/OutOfStock",
              itemCondition: "https://schema.org/NewCondition",
              url:
                typeof window !== "undefined"
                  ? `${window.location.origin}/shop/${siteId}/product/${p.id}`
                  : undefined,
              shippingDetails: {
                "@type": "OfferShippingDetails",
                shippingRate: { "@type": "MonetaryAmount", value: 0, currency: p.currency || "EUR" },
                shippingDestination: { "@type": "DefinedRegion", addressCountry: "FR" },
                deliveryTime: {
                  "@type": "ShippingDeliveryTime",
                  handlingTime: { "@type": "QuantitativeValue", minValue: 0, maxValue: 1, unitCode: "DAY" },
                  transitTime: { "@type": "QuantitativeValue", minValue: 2, maxValue: 3, unitCode: "DAY" },
                },
              },
              hasMerchantReturnPolicy: {
                "@type": "MerchantReturnPolicy",
                applicableCountry: "FR",
                returnPolicyCategory: "https://schema.org/MerchantReturnFiniteReturnWindow",
                merchantReturnDays: 14,
                returnMethod: "https://schema.org/ReturnByMail",
                returnFees: "https://schema.org/FreeReturn",
              },
            },
          },
          // Breadcrumb schema
          {
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            itemListElement: [
              { "@type": "ListItem", position: 1, name: "Accueil", item: `${window.location.origin}/shop/${siteId}` },
              { "@type": "ListItem", position: 2, name: "Collections", item: `${window.location.origin}/shop/${siteId}/collections` },
              p.category ? { "@type": "ListItem", position: 3, name: p.category, item: `${window.location.origin}/shop/${siteId}/collection/${p.category}` } : null,
              { "@type": "ListItem", position: p.category ? 4 : 3, name: pickLang(p.name, lang), item: `${window.location.origin}/shop/${siteId}/product/${p.id}` },
            ].filter(Boolean),
          },
          // FAQ schema (from product narrative FAQ + PAA)
          (p.narrative?.faq?.length || p.narrative?.seo?.people_also_ask?.length) ? {
            "@context": "https://schema.org",
            "@type": "FAQPage",
            mainEntity: [
              ...(p.narrative?.faq || []),
              ...(p.narrative?.seo?.people_also_ask || []),
            ].slice(0, 12).map((f) => ({
              "@type": "Question",
              name: f.question,
              acceptedAnswer: { "@type": "Answer", text: f.answer },
            })),
          } : null,
          // HowTo schema (from usage_steps)
          p.narrative?.seo?.usage_steps?.length ? {
            "@context": "https://schema.org",
            "@type": "HowTo",
            name: `Comment utiliser ${pickLang(p.name, lang)}`,
            description: `Guide pas à pas pour l'utilisation de ${pickLang(p.name, lang)}.`,
            totalTime: "PT5M",
            step: p.narrative.seo.usage_steps.map((s, idx) => ({
              "@type": "HowToStep",
              position: idx + 1,
              name: s.name,
              text: s.text,
            })),
          } : null,
        ].filter(Boolean)}
      />
      <div className="max-w-7xl mx-auto px-6 md:px-10 py-6 md:py-10">
        {/* Breadcrumb */}
        <nav className="text-[12px] text-neutral-500 mb-6" data-testid="product-breadcrumb">
          <Link to={`/shop/${siteId}`} className="hover:underline">Accueil</Link>
          <span className="mx-2">/</span>
          <Link to={`/shop/${siteId}/collections`} className="hover:underline">Collections</Link>
          {p.category && (
            <>
              <span className="mx-2">/</span>
              <Link to={`/shop/${siteId}/collection/${p.category}`} className="hover:underline capitalize">
                {p.category}
              </Link>
            </>
          )}
          <span className="mx-2">/</span>
          <span className="text-neutral-900">{pickLang(p.name, lang)}</span>
        </nav>

        {/* HERO PRODUCT */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-10 lg:gap-20 mb-16 md:mb-24 items-start">
          {/* Gallery */}
          <ProductGallery images={p.images || []} name={pickLang(p.name, lang)} design={design} />

          {/* Buy panel */}
          <div className="md:pt-4">
            <div
              className="text-[11px] uppercase tracking-[0.25em] mb-3 font-medium"
              style={{ color: primary }}
            >
              {site?.name}
            </div>
            <h1
              className="text-3xl md:text-5xl font-semibold text-[#1C1917] leading-[1.05] tracking-tight"
              style={{ fontFamily: `"${fontHeading}", Georgia, serif` }}
              data-testid="product-name"
            >
              {p.narrative?.headline || pickLang(p.name, lang)}
            </h1>
            {p.narrative?.subheadline && (
              <p className="text-lg mt-4 leading-relaxed text-[#57534E]">
                {p.narrative.subheadline}
              </p>
            )}

            {/* Rating + stock */}
            <div className="flex items-center gap-4 mt-5 text-sm">
              <div className="flex items-center gap-1.5">
                <div className="flex" style={{ color: "#F59E0B" }}>
                  {[...Array(5)].map((_, i) => (
                    <Star key={i} size={14} weight="fill" />
                  ))}
                </div>
                <span className="font-semibold">{(p.rating?.score ?? 4.8).toFixed(1)}</span>
                <span className="text-neutral-500">({p.rating?.count ?? 127} avis)</span>
              </div>
              <div className="w-px h-4 bg-neutral-200" />
              <div className="flex items-center gap-1.5 text-emerald-700">
                <span className="w-2 h-2 rounded-full bg-emerald-500" />
                {p.stock === null || (p.stock ?? 1) > 0 ? "En stock" : "Rupture"}
              </div>
            </div>

            {/* Price */}
            <div className="flex items-baseline gap-3 mt-8" data-testid="product-price">
              <span className="text-3xl md:text-4xl font-semibold" style={{ color: primary }}>
                {formatPrice(p.price, p.currency, lang)}
              </span>
              {p.compare_at_price && p.compare_at_price > p.price && (
                <>
                  <span className="text-xl text-[#A8A29E] line-through">
                    {formatPrice(p.compare_at_price, p.currency, lang)}
                  </span>
                  <span
                    className="text-white text-xs font-semibold px-2.5 py-1 rounded-full"
                    style={{ background: primary }}
                  >
                    -{Math.round((1 - p.price / p.compare_at_price) * 100)}%
                  </span>
                </>
              )}
            </div>
            <div className="text-xs text-neutral-500 mt-1">TVA incluse · livraison offerte dès 50 €</div>

            {/* Stock urgency (subtle, only if < 10) */}
            {typeof p.stock === "number" && p.stock > 0 && p.stock < 10 && (
              <div className="mt-4 flex items-center gap-2 text-sm" data-testid="stock-urgency">
                <span className="w-2 h-2 rounded-full animate-pulse" style={{ background: "#F59E0B" }} />
                <span className="text-amber-700 font-medium">Plus que {p.stock} en stock</span>
              </div>
            )}

            {/* Quantity + Add */}
            <div className="mt-6 flex items-center gap-4">
              <div className="flex items-center border border-[#E7E5E4] rounded-full overflow-hidden bg-white">
                <button
                  onClick={() => setQty(Math.max(1, qty - 1))}
                  data-testid="qty-minus"
                  className="w-12 h-12 hover:bg-[#FDFBF7] text-[#1C1917]"
                >
                  −
                </button>
                <div className="w-10 text-center font-medium" data-testid="qty-value">{qty}</div>
                <button
                  onClick={() => setQty(qty + 1)}
                  data-testid="qty-plus"
                  className="w-12 h-12 hover:bg-[#FDFBF7] text-[#1C1917]"
                >
                  +
                </button>
              </div>

              <button
                onClick={handleAdd}
                data-testid="add-to-cart"
                className="flex-1 h-14 rounded-full font-medium text-[15px] transition-all duration-200 active:scale-[0.98] text-white"
                style={{ background: added ? "#047857" : primary }}
              >
                {added ? (
                  <span className="flex items-center justify-center gap-2">
                    <CheckCircle size={18} weight="fill" /> {t(lang, "added_to_cart")}
                  </span>
                ) : (
                  t(lang, "add_to_cart")
                )}
              </button>
            </div>

            {/* Marketing elements — delivery estimate + payment options */}
            <div className="mt-6 space-y-3">
              <DeliveryEstimate design={design} />
              <PaymentOptions price={p.price} currency={p.currency} design={design} />
            </div>

            {/* Trust badges — condensed */}
            <div className="mt-6 grid grid-cols-2 gap-2 text-[13px]" data-testid="product-trust-badges">
              <div className="flex items-center gap-2 text-neutral-700">
                <ShieldCheck size={15} weight="fill" style={{ color: primary }} />
                Garantie 2 ans
              </div>
              <div className="flex items-center gap-2 text-neutral-700">
                <Truck size={15} weight="fill" style={{ color: primary }} />
                Livraison offerte
              </div>
              <div className="flex items-center gap-2 text-neutral-700">
                <CheckCircle size={15} weight="fill" style={{ color: primary }} />
                Retour gratuit 14j
              </div>
              <div className="flex items-center gap-2 text-neutral-700">
                <ShieldCheck size={15} weight="fill" style={{ color: primary }} />
                Paiement sécurisé
              </div>
            </div>

            {/* Fallback description if no narrative */}
            {!p.narrative && pickLang(p.description, lang) && (
              <p className="text-[15px] leading-relaxed text-[#57534E] mt-8 whitespace-pre-line">
                {pickLang(p.description, lang)}
              </p>
            )}
          </div>
        </div>

        <ProductBundle currentProduct={p} lang={lang} design={design} />

        <NarrativeSections sections={p.narrative?.sections} design={design} />
        <TechSpecs specs={p.narrative?.tech_specs} design={design} />
        <BestForNotFor best_for={p.narrative?.seo?.best_for} not_for={p.narrative?.seo?.not_for} design={design} />
        <UsageSteps steps={p.narrative?.seo?.usage_steps} productName={pickLang(p.name, lang)} design={design} />
        <ProductFAQ faq={p.narrative?.faq} design={design} />
        <PeopleAlsoAsk items={p.narrative?.seo?.people_also_ask} design={design} />
        <ProductReviews product={p} design={design} />
        <RelatedQueries queries={p.narrative?.seo?.related_queries} design={design} />
        <UpsellsRecommendations
          mode="product"
          productId={p.id}
          lang={lang}
          design={design}
          onAddToCart={(u) => { try { window.altiaroTrack?.addToCart?.(u, 1, lang); } catch (_) { /* noop */ } }}
        />
        <CrossSellProducts currentProduct={p} lang={lang} design={design} />
        <LastUpdatedBadge date={p.narrative?.enriched_at || p.updated_at} design={design} />
      </div>

      <MobileStickyBuy
        product={p}
        onAdd={handleAdd}
        qty={qty}
        added={added}
        design={design}
        lang={lang}
      />

      {/* Sticky mobile CTA */}
      <div className="md:hidden fixed bottom-0 inset-x-0 bg-white border-t border-[#E7E5E4] p-3 flex items-center gap-3 z-40">
        <div className="flex-1">
          <div className="text-xs text-[#78716C]">{pickLang(p.name, lang).slice(0, 25)}…</div>
          <div className="font-semibold" style={{ color: primary }}>
            {formatPrice(p.price, p.currency, lang)}
          </div>
        </div>
        <button
          onClick={handleAdd}
          className="h-11 px-5 rounded-full text-white text-sm font-medium"
          style={{ background: added ? "#047857" : primary }}
        >
          {added ? "Ajouté ✓" : "Ajouter"}
        </button>
      </div>
    </StorefrontLayout>
  );
}

/* =========================================================
 * CART
 * ========================================================= */
export function StorefrontCart() {
  const { siteId, site, design, lang, setLang } = useSiteAndLang();
  const navigate = useNavigate();
  const [items, setItems] = useState(() => readCart(siteId));

  useEffect(() => {
    const onUpdate = () => setItems(readCart(siteId));
    window.addEventListener("cf_cart_updated", onUpdate);
    return () => window.removeEventListener("cf_cart_updated", onUpdate);
  }, [siteId]);

  const totals = cartTotals(items);

  return (
    <StorefrontLayout lang={lang} setLang={setLang} site={site} design={design}>
      <div className="max-w-4xl mx-auto px-6 py-12">
        <h1 className="font-heading text-4xl font-semibold text-[#1C1917] mb-8">{t(lang, "cart")}</h1>

        {items.length === 0 ? (
          <div className="bg-white rounded-2xl border border-[#E7E5E4] p-16 text-center">
            <ShoppingBagOpen size={48} weight="thin" className="mx-auto text-[#D6D3D1] mb-4" />
            <div className="text-[#78716C] mb-6">{t(lang, "cart_empty")}</div>
            <Link
              to={`/shop/${siteId}`}
              data-testid="cart-empty-cta"
              className="inline-flex items-center gap-2 h-11 px-5 rounded-full bg-[#1C1917] hover:bg-[#44403C] text-white text-sm font-medium transition"
            >
              {t(lang, "cart_empty_cta")} <ArrowRight size={16} />
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-[1fr_380px] gap-8">
            <div className="space-y-3" data-testid="cart-items">
              {items.map((it) => (
                <div
                  key={it.product_id}
                  data-testid={`cart-item-${it.product_id}`}
                  className="flex items-center gap-4 bg-white rounded-xl border border-[#E7E5E4] p-4"
                >
                  <div className="w-20 h-20 rounded-lg bg-[#F5F2EB] overflow-hidden flex-shrink-0">
                    {it.image ? (
                      <img src={it.image} alt={it.name} className="w-full h-full object-cover" />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center text-[#D6D3D1]">
                        <ShoppingBagOpen size={28} weight="thin" />
                      </div>
                    )}
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-[#1C1917] truncate">{it.name}</div>
                    <div className="text-sm text-[#57534E] mt-1">
                      {formatPrice(it.price, it.currency, lang)}
                    </div>
                  </div>

                  <div className="flex items-center border border-[#E7E5E4] rounded-full overflow-hidden bg-white">
                    <button
                      onClick={() => {
                        setItems(updateQty(siteId, it.product_id, it.quantity - 1));
                      }}
                      className="w-9 h-9 hover:bg-[#FDFBF7]"
                    >
                      −
                    </button>
                    <div className="w-8 text-center text-sm">{it.quantity}</div>
                    <button
                      onClick={() => setItems(updateQty(siteId, it.product_id, it.quantity + 1))}
                      className="w-9 h-9 hover:bg-[#FDFBF7]"
                    >
                      +
                    </button>
                  </div>

                  <button
                    onClick={() => setItems(removeFromCart(siteId, it.product_id))}
                    data-testid={`remove-${it.product_id}`}
                    className="text-[#A8A29E] hover:text-[#BE123C] p-2"
                    title={t(lang, "remove")}
                  >
                    <Trash size={18} />
                  </button>
                </div>
              ))}
            </div>

            <div className="bg-white rounded-2xl border border-[#E7E5E4] p-6 h-fit">
              <div className="space-y-3 text-[15px]">
                <Row label={t(lang, "subtotal")} value={formatPrice(totals.subtotal, "EUR", lang)} />
                <Row
                  label={t(lang, "shipping")}
                  value={
                    totals.shipping_fee === 0 ? (
                      <span className="text-[#047857] font-medium">{t(lang, "free")}</span>
                    ) : (
                      formatPrice(totals.shipping_fee, "EUR", lang)
                    )
                  }
                />
                <div className="h-px bg-[#E7E5E4] my-3" />
                <Row
                  label={<span className="font-medium text-[#1C1917]">{t(lang, "total")}</span>}
                  value={
                    <span className="font-heading text-xl font-semibold text-[#1C1917]">
                      {formatPrice(totals.total, "EUR", lang)}
                    </span>
                  }
                />
              </div>

              <button
                onClick={() => navigate(`/shop/${siteId}/checkout`)}
                data-testid="go-to-checkout"
                className="w-full mt-5 h-12 rounded-full bg-[#B84B31] hover:bg-[#993D26] text-white font-medium text-[15px] transition active:scale-[0.98]"
              >
                {t(lang, "checkout")}
              </button>
              <Link
                to={`/shop/${siteId}`}
                className="block text-center mt-3 text-sm text-[#78716C] hover:text-[#1C1917]"
              >
                ← {t(lang, "continue_shopping")}
              </Link>
            </div>
          </div>
        )}
      </div>
    </StorefrontLayout>
  );
}

/* =========================================================
 * CHECKOUT
 * ========================================================= */
export function StorefrontCheckout() {
  const { siteId, site, design, lang, setLang } = useSiteAndLang();
  const navigate = useNavigate();
  const [items] = useState(() => readCart(siteId));
  const [form, setForm] = useState({
    name: "",
    email: "",
    phone: "",
    line1: "",
    line2: "",
    city: "",
    postal_code: "",
    country_code: "FR",
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (items.length === 0) {
      navigate(`/shop/${siteId}/cart`);
    }
  }, [items.length, navigate, siteId]);

  const totals = cartTotals(items);
  const change = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      // GA4 / Google Ads tracking
      try { window.altiaroTrack?.beginCheckout?.(items, totals.total, lang); } catch (_) {}
      const payload = {
        items: items.map((i) => ({
          product_id: i.product_id,
          name: i.name,
          price: i.price,
          quantity: i.quantity,
          currency: i.currency || "EUR",
          image: i.image,
          upsell_discount_pct: i.upsell_discount_pct || 0,
        })),
        customer: { name: form.name, email: form.email, phone: form.phone },
        shipping_address: {
          line1: form.line1,
          line2: form.line2,
          city: form.city,
          postal_code: form.postal_code,
          country: countryLabel(form.country_code, "fr"),
          country_code: form.country_code,
        },
        language: lang,
      };
      const { data } = await axios.post(
        `${BACKEND_URL}/api/public/sites/${siteId}/orders`,
        payload
      );
      clearCart(siteId);
      // Create Mollie payment and redirect to checkout URL
      try {
        const payRes = await axios.post(
          `${BACKEND_URL}/api/public/payments/create`,
          { order_number: data.order_number, site_id: siteId }
        );
        if (payRes.data?.checkout_url) {
          window.location.href = payRes.data.checkout_url;
          return;
        }
      } catch (payErr) {
        console.error("Mollie payment creation failed", payErr);
      }
      navigate(`/shop/${siteId}/confirmation?order=${data.order_number}`);
    } catch (err) {
      setError(err.response?.data?.detail || "Erreur lors de la commande");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <StorefrontLayout lang={lang} setLang={setLang} site={site} design={design}>
      <div className="max-w-5xl mx-auto px-6 py-12">
        <h1 className="font-heading text-4xl font-semibold text-[#1C1917] mb-8">{t(lang, "checkout")}</h1>

        <form
          onSubmit={submit}
          className="grid grid-cols-1 lg:grid-cols-[1fr_380px] gap-8"
          data-testid="checkout-form"
        >
          <div className="space-y-6">
            <Card title={t(lang, "your_details")}>
              <Field label={t(lang, "full_name") + " *"} name="name" required onChange={change} value={form.name} />
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Field label={t(lang, "email") + " *"} name="email" type="email" required onChange={change} value={form.email} />
                <Field label={t(lang, "phone")} name="phone" onChange={change} value={form.phone} />
              </div>
            </Card>

            <Card title={t(lang, "shipping_address")}>
              <Field label={t(lang, "address_line1") + " *"} name="line1" required onChange={change} value={form.line1} />
              <Field label={t(lang, "address_line2")} name="line2" onChange={change} value={form.line2} />
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Field label={t(lang, "postal_code") + " *"} name="postal_code" required onChange={change} value={form.postal_code} />
                <Field label={t(lang, "city") + " *"} name="city" required onChange={change} value={form.city} />
              </div>
              <div>
                <label className="block text-[13px] font-medium text-[#1C1917] mb-1.5">
                  {t(lang, "country")} *
                </label>
                <select
                  name="country_code"
                  value={form.country_code}
                  onChange={change}
                  data-testid="country-select"
                  className="w-full h-12 px-4 rounded-xl border border-[#E7E5E4] bg-white focus:ring-2 focus:ring-[#B84B31]/30 focus:border-[#B84B31] outline-none"
                >
                  {COUNTRY_OPTIONS.map((c) => (
                    <option key={c.code} value={c.code}>
                      {countryLabel(c.code, lang)}
                    </option>
                  ))}
                </select>
              </div>
            </Card>

            {error && (
              <div className="p-3.5 rounded-lg bg-[#FFE4E6] text-[#BE123C] text-sm" data-testid="checkout-error">
                {error}
              </div>
            )}
          </div>

          <div className="bg-white rounded-2xl border border-[#E7E5E4] p-6 h-fit lg:sticky lg:top-24">
            <div className="font-heading text-lg font-semibold text-[#1C1917] mb-4">
              {items.reduce((a, b) => a + b.quantity, 0)} article(s)
            </div>
            <div className="space-y-2 max-h-60 overflow-y-auto mb-4">
              {items.map((it) => (
                <div key={it.product_id} className="flex justify-between text-sm">
                  <span className="text-[#57534E] truncate pr-2">
                    {it.quantity} × {it.name}
                  </span>
                  <span className="font-medium text-[#1C1917] whitespace-nowrap">
                    {formatPrice(it.price * it.quantity, "EUR", lang)}
                  </span>
                </div>
              ))}
            </div>
            <div className="h-px bg-[#E7E5E4] my-3" />
            <Row label={t(lang, "subtotal")} value={formatPrice(totals.subtotal, "EUR", lang)} />
            <Row
              label={t(lang, "shipping")}
              value={
                totals.shipping_fee === 0 ? (
                  <span className="text-[#047857] font-medium">{t(lang, "free")}</span>
                ) : (
                  formatPrice(totals.shipping_fee, "EUR", lang)
                )
              }
            />
            <div className="h-px bg-[#E7E5E4] my-3" />
            <Row
              label={<span className="font-medium">{t(lang, "total")}</span>}
              value={
                <span className="font-heading text-xl font-semibold">
                  {formatPrice(totals.total, "EUR", lang)}
                </span>
              }
            />

            <button
              type="submit"
              disabled={submitting}
              data-testid="place-order"
              className="w-full mt-5 h-12 rounded-full bg-[#B84B31] hover:bg-[#993D26] text-white font-medium text-[15px] transition active:scale-[0.98] disabled:opacity-60"
            >
              {submitting ? "…" : t(lang, "place_order")}
            </button>

            <div className="mt-3 flex items-center justify-center gap-1.5 text-[11px] text-[#78716C]">
              <ShieldCheck size={12} weight="bold" /> {t(lang, "secure_checkout")}
            </div>
          </div>
        </form>
      </div>
    </StorefrontLayout>
  );
}

/* =========================================================
 * CONFIRMATION
 * ========================================================= */
export function StorefrontConfirmation() {
  const { siteId, site, design, lang, setLang } = useSiteAndLang();
  const [search] = useSearchParams();
  const orderNumber = search.get("order");
  const isSuccessPage = window.location.pathname.includes("/checkout/success");
  const [order, setOrder] = useState(null);

  useEffect(() => {
    if (!orderNumber) return;
    let cancelled = false;
    let attempts = 0;
    let fired = false;
    const fetchOrder = () => {
      axios
        .get(`${BACKEND_URL}/api/public/sites/${siteId}/orders/${orderNumber}`)
        .then(({ data }) => {
          if (cancelled) return;
          setOrder(data);
          // GA4 / Google Ads purchase event — fired once when status becomes 'paid'
          if (!fired && data?.status === "paid") {
            fired = true;
            try { window.altiaroTrack?.purchase?.(data, lang); } catch (_) {}
          }
          attempts += 1;
          if (data.status === "pending_payment" && attempts < 20) {
            setTimeout(fetchOrder, 2000);
          }
        })
        .catch(() => setOrder(null));
    };
    fetchOrder();
    return () => { cancelled = true; };
  }, [siteId, orderNumber, lang]);

  const paid = order?.status === "paid";
  const failed = order?.status === "failed" || order?.status === "expired" || order?.status === "cancelled";

  return (
    <StorefrontLayout lang={lang} setLang={setLang} site={site} design={design}>
      <div className="max-w-2xl mx-auto px-6 py-16 text-center">
        <div className={`w-16 h-16 rounded-full mx-auto flex items-center justify-center mb-6 ${
          paid ? "bg-[#D1FAE5]" : failed ? "bg-[#FFE4E6]" : "bg-[#FEF3C7]"
        }`}>
          <CheckCircle size={32} weight="fill" className={
            paid ? "text-[#047857]" : failed ? "text-[#BE123C]" : "text-[#D97706]"
          } />
        </div>
        <h1 className="font-heading text-4xl font-semibold text-[#1C1917] mb-3">
          {paid ? t(lang, "order_confirmed") : failed ? "Paiement échoué" : (isSuccessPage ? "Finalisation du paiement…" : t(lang, "order_confirmed"))}
        </h1>
        {orderNumber && (
          <div className="text-[#57534E] mb-8" data-testid="order-number">
            {t(lang, "order_number")} · <span className="font-mono font-medium">{orderNumber}</span>
          </div>
        )}
        <p className="text-[#57534E] max-w-lg mx-auto">{t(lang, "order_pending_pay")}</p>

        {order && (
          <div className="bg-white rounded-2xl border border-[#E7E5E4] p-6 mt-8 text-left">
            <div className="text-[11px] uppercase tracking-widest text-[#78716C] mb-3">Détail</div>
            {order.items.map((it, idx) => (
              <div key={idx} className="flex justify-between text-sm py-1.5">
                <span className="text-[#57534E]">
                  {it.quantity} × {it.name}
                </span>
                <span className="font-medium">{formatPrice(it.price * it.quantity, "EUR", lang)}</span>
              </div>
            ))}
            <div className="h-px bg-[#E7E5E4] my-3" />
            <div className="flex justify-between font-heading text-lg">
              <span>{t(lang, "total")}</span>
              <span>{formatPrice(order.total, "EUR", lang)}</span>
            </div>
          </div>
        )}

        <Link
          to={`/shop/${siteId}`}
          className="inline-block mt-10 text-[#B84B31] hover:underline font-medium"
          data-testid="back-to-shop-from-confirm"
        >
          ← {t(lang, "back_to_shop")}
        </Link>
      </div>

      {paid && order?.items?.length > 0 && (
        <div className="max-w-6xl mx-auto px-6 md:px-10 pb-16">
          <UpsellsRecommendations
            mode="post_purchase"
            productIds={order.items.map((it) => it.product_id).filter(Boolean)}
            lang={lang}
            design={design}
          />
        </div>
      )}
    </StorefrontLayout>
  );
}

/* --- shared small components (used by Checkout) --- */
function Card({ title, children }) {
  return (
    <div className="bg-white rounded-2xl border border-[#E7E5E4] p-6 space-y-4">
      <div className="font-heading text-lg font-semibold text-[#1C1917]">{title}</div>
      {children}
    </div>
  );
}

function Field({ label, name, type = "text", value, onChange, required }) {
  return (
    <div>
      <label className="block text-[13px] font-medium text-[#1C1917] mb-1.5">{label}</label>
      <input
        name={name}
        type={type}
        value={value}
        onChange={onChange}
        required={required}
        data-testid={`field-${name}`}
        className="w-full h-12 px-4 rounded-xl border border-[#E7E5E4] bg-white focus:ring-2 focus:ring-[#B84B31]/30 focus:border-[#B84B31] outline-none"
      />
    </div>
  );
}

function Row({ label, value }) {
  return (
    <div className="flex items-center justify-between text-sm">
      <span className="text-[#57534E]">{label}</span>
      <span className="text-[#1C1917]">{value}</span>
    </div>
  );
}
