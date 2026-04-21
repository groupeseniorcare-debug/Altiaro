import React, { useEffect, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import axios from "axios";
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
import {
  NarrativeSections,
  TechSpecs,
  ProductFAQ,
} from "../components/storefront/NarrativeProduct";

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

  return (
    <StorefrontLayout lang={lang} setLang={setLang} site={site} design={design}>
      <SEOHead
        title={seoTitle}
        description={seoDesc}
        canonical={canonical}
        image={design?.brand?.logo_url}
        langs={buildHreflangs(site, "")}
        schema={[orgSchema, websiteSchema].filter(Boolean)}
      />
      <Hero site={site} design={design} lang={lang} />
      <Benefits design={design} lang={lang} />
      <ProductGrid
        siteId={siteId}
        products={products}
        loading={loading}
        design={design}
        lang={lang}
      />
      <Testimonials design={design} lang={lang} />
      <FAQSection design={design} lang={lang} />
      <FinalCTA design={design} lang={lang} />
    </StorefrontLayout>
  );
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
      .then(({ data }) => setP(data))
      .catch(() => setP(null))
      .finally(() => setLoading(false));
  }, [siteId, productId]);

  const handleAdd = () => {
    addToCart(siteId, p, lang, qty);
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
        title={`${pickLang(p.name, lang)} · ${site?.name || ""}`}
        description={pickLang(p.description, lang) || pickLang(p.name, lang)}
        canonical={
          typeof window !== "undefined"
            ? `${window.location.origin}/shop/${siteId}/product/${p.id}`
            : undefined
        }
        image={p.images?.[0]}
        type="product"
        langs={buildHreflangs(site, `/product/${p.id}`)}
        schema={{
          "@context": "https://schema.org",
          "@type": "Product",
          name: pickLang(p.name, lang),
          description: pickLang(p.description, lang),
          image: p.images || [],
          sku: p.sku,
          brand: { "@type": "Brand", name: site?.name },
          offers: {
            "@type": "Offer",
            priceCurrency: p.currency || "EUR",
            price: p.price,
            availability:
              p.stock === null || p.stock > 0
                ? "https://schema.org/InStock"
                : "https://schema.org/OutOfStock",
            url:
              typeof window !== "undefined"
                ? `${window.location.origin}/shop/${siteId}/product/${p.id}`
                : undefined,
          },
        }}
      />
      <div className="max-w-7xl mx-auto px-6 md:px-10 py-6 md:py-10">
        <button
          onClick={() => navigate(`/shop/${siteId}`)}
          className="text-sm text-[#78716C] hover:text-[#1C1917] mb-6 inline-flex items-center gap-1"
          data-testid="back-to-shop"
        >
          ← {t(lang, "back_to_shop")}
        </button>

        {/* HERO PRODUCT (Apple-style split) */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-10 lg:gap-20 mb-16 md:mb-24 items-start">
          {/* Gallery */}
          <div className="sticky top-24">
            <div className="aspect-square bg-[#F5F2EB] rounded-2xl overflow-hidden mb-3">
              {p.images?.[0] ? (
                <img
                  src={p.images[0]}
                  alt={pickLang(p.name, lang)}
                  className="w-full h-full object-cover"
                />
              ) : (
                <div className="w-full h-full flex items-center justify-center text-[#D6D3D1]">
                  <ShoppingBagOpen size={80} weight="thin" />
                </div>
              )}
            </div>
            {p.images?.length > 1 && (
              <div className="grid grid-cols-4 gap-2">
                {p.images.slice(0, 4).map((img, i) => (
                  <div key={i} className="aspect-square bg-[#F5F2EB] rounded-lg overflow-hidden">
                    <img src={img} alt="" className="w-full h-full object-cover" loading="lazy" />
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Buy panel */}
          <div className="md:pt-4">
            {p.narrative?.headline && (
              <div
                className="text-[11px] uppercase tracking-[0.25em] mb-3 font-medium"
                style={{ color: primary }}
              >
                {site?.name}
              </div>
            )}
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

            <div className="flex items-baseline gap-3 mt-8" data-testid="product-price">
              <span className="text-3xl md:text-4xl font-semibold" style={{ color: primary }}>
                {formatPrice(p.price, p.currency, lang)}
              </span>
              {p.compare_at_price && p.compare_at_price > p.price && (
                <span className="text-xl text-[#A8A29E] line-through">
                  {formatPrice(p.compare_at_price, p.currency, lang)}
                </span>
              )}
            </div>

            <div className="mt-8 flex items-center gap-4">
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
                className="flex-1 h-12 rounded-full font-medium text-[15px] transition-all duration-200 active:scale-[0.98] text-white"
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

            <div className="mt-8 grid grid-cols-2 gap-3 text-sm">
              <div className="bg-[#FAF7F2] rounded-xl p-3 flex items-center gap-2">
                <ShieldCheck size={16} weight="fill" style={{ color: primary }} />
                <span className="text-[#57534E]">{t(lang, "secure_checkout")}</span>
              </div>
              <div className="bg-[#FAF7F2] rounded-xl p-3 flex items-center gap-2">
                <Truck size={16} weight="fill" style={{ color: primary }} />
                <span className="text-[#57534E]">{t(lang, "free_shipping_above")}</span>
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

        <NarrativeSections sections={p.narrative?.sections} design={design} />
        <TechSpecs specs={p.narrative?.tech_specs} design={design} />
        <ProductFAQ faq={p.narrative?.faq} design={design} />
      </div>

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
      const payload = {
        items: items.map((i) => ({
          product_id: i.product_id,
          name: i.name,
          price: i.price,
          quantity: i.quantity,
          currency: i.currency || "EUR",
          image: i.image,
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
    const fetchOrder = () => {
      axios
        .get(`${BACKEND_URL}/api/public/sites/${siteId}/orders/${orderNumber}`)
        .then(({ data }) => {
          if (cancelled) return;
          setOrder(data);
          attempts += 1;
          if (data.status === "pending_payment" && attempts < 20) {
            setTimeout(fetchOrder, 2000);
          }
        })
        .catch(() => setOrder(null));
    };
    fetchOrder();
    return () => { cancelled = true; };
  }, [siteId, orderNumber]);

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
