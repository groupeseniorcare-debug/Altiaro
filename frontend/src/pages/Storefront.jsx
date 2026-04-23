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
} from "@phosphor-icons/react";
import SEOHead from "../components/SEOHead";

import {
  BACKEND_URL,
  useSiteAndLang,
  designText,
  formatPrice,
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
    case "brand_process":
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
 * PRODUCT DETAIL — moved to pages/StorefrontProduct.jsx
 * (April 2026 refactor). Re-exported here for App.js backwards compat.
 * ========================================================= */
export { StorefrontProduct } from "./StorefrontProduct";


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
