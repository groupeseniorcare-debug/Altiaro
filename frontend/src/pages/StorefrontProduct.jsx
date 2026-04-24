/**
 * Product detail page.
 *
 * Extracted from the original monolithic Storefront.jsx (April 2026 refactor).
 * Keeps the same named export, re-exported through Storefront.jsx for
 * App.js backwards compatibility.
 */
import React, { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import axios from "axios";
import StorefrontLayout from "../components/StorefrontLayout";
import { t, pickLang } from "../lib/i18n";
import { addToCart } from "../lib/cart";
import {
  CheckCircle,
  Check,
  ShieldCheck,
  Truck,
  Star,
} from "@phosphor-icons/react";
import SEOHead from "../components/SEOHead";

import {
  BACKEND_URL,
  useSiteAndLang,
  formatPrice,
  designAccents,
  buildHreflangs,
} from "../components/storefront/storefrontUtils";
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
import ProductEditorialMosaic from "../components/storefront/ProductEditorialMosaic";
import {
  PeopleAlsoAsk,
  BestForNotFor,
  UsageSteps,
  RelatedQueries,
  LastUpdatedBadge,
} from "../components/storefront/ProductSEOBlocks";

export function StorefrontProduct() {
  const { siteId, productId } = useParams();
  const { site, design, lang, setLang, availableLangs } = useSiteAndLang();
  const navigate = useNavigate();
  const [p, setP] = useState(null);
  const [loading, setLoading] = useState(true);
  const [added, setAdded] = useState(false);
  const [qty, setQty] = useState(1);

  const { fontHeading } = designAccents(design);

  useEffect(() => {
    axios
      .get(`${BACKEND_URL}/api/public/sites/${siteId}/products/${productId}`)
      .then(({ data }) => {
        setP(data);
        try { window.altiaroTrack?.viewItem?.(data, lang); } catch (_) { /* noop */ }
      })
      .catch(() => setP(null))
      .finally(() => setLoading(false));
  }, [siteId, productId, lang]);

  const handleAdd = () => {
    addToCart(siteId, p, lang, qty);
    try { window.altiaroTrack?.addToCart?.(p, qty, lang); } catch (_) { /* noop */ }
    setAdded(true);
    window.dispatchEvent(new Event("cf_cart_open"));
    setTimeout(() => setAdded(false), 1500);
  };

  if (loading) {
    return (
      <StorefrontLayout lang={lang} setLang={setLang} availableLangs={availableLangs} site={site} design={design}>
        <div className="max-w-6xl mx-auto px-6 py-12 text-[#78716C]">…</div>
      </StorefrontLayout>
    );
  }
  if (!p) {
    return (
      <StorefrontLayout lang={lang} setLang={setLang} availableLangs={availableLangs} site={site} design={design}>
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
    <StorefrontLayout lang={lang} setLang={setLang} availableLangs={availableLangs} site={site} design={design}>
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
      <div className="bg-white" data-testid="product-page-root">
        <div className="bg-white" style={{ borderBottom: "1px solid #E5E5E5" }}>
          <div className="max-w-7xl mx-auto px-6 md:px-10 py-3 flex items-center justify-between text-[11px] uppercase tracking-[0.3em]" style={{ color: "#737373" }}>
            <div className="flex items-center gap-4 flex-wrap">
              <span className="flex items-center gap-1.5"><Truck size={12} weight="bold" /> {t(lang, "delivery_free_short")}</span>
              <span className="opacity-40 hidden md:inline">·</span>
              <span className="hidden md:flex items-center gap-1.5"><ShieldCheck size={12} weight="bold" /> Garantie 2 ans</span>
              <span className="opacity-40 hidden md:inline">·</span>
              <span className="hidden md:flex items-center gap-1.5"><CheckCircle size={12} weight="bold" /> Retour 14 j</span>
            </div>
            <div className="hidden md:block">Réf. {p.sku || p.id?.slice(0, 8).toUpperCase()}</div>
          </div>
        </div>

        <div className="max-w-7xl mx-auto px-6 md:px-10 pt-8 md:pt-12 pb-12">
          <nav
            className="text-[11px] uppercase tracking-[0.25em] mb-10"
            style={{ color: "#737373" }}
            data-testid="product-breadcrumb"
          >
            <Link to={`/shop/${siteId}`} className="hover:opacity-60 transition">Accueil</Link>
            <span className="mx-2 opacity-50">/</span>
            <Link to={`/shop/${siteId}/collections`} className="hover:opacity-60 transition">Collections</Link>
            {p.category && (
              <>
                <span className="mx-2 opacity-50">/</span>
                <Link to={`/shop/${siteId}/collection/${p.category}`} className="hover:opacity-60 transition capitalize">
                  {p.category}
                </Link>
              </>
            )}
            <span className="mx-2 opacity-50">/</span>
            <span style={{ color: "#0A0A0A" }}>{pickLang(p.name, lang)}</span>
          </nav>

          <div className="grid grid-cols-1 md:grid-cols-[1.1fr_1fr] gap-8 lg:gap-16 mb-24 md:mb-32 items-start">
            <ProductGallery
              images={[
                ...((p.generated_images || []).map((g) => g.url).filter(Boolean)),
                ...(p.images || []),
              ]}
              name={pickLang(p.name, lang)}
              design={design}
            />

            <div className="md:pt-2 md:sticky md:top-28">
              <div className="flex items-center gap-3 mb-5">
                <span className="h-px w-8" style={{ background: "#0A0A0A" }} />
                <span className="text-[10px] uppercase tracking-[0.4em] font-medium" style={{ color: "#0A0A0A" }}>
                  {site?.name}{p.category ? ` · ${p.category}` : ""}
                </span>
              </div>

              <h1
                className="text-[36px] md:text-[48px] lg:text-[56px] leading-[1.02] tracking-[-0.02em] font-normal"
                style={{ fontFamily: `"${fontHeading}", Georgia, serif`, color: "#0A0A0A" }}
                data-testid="product-name"
              >
                {p.narrative?.headline || pickLang(p.name, lang)}
              </h1>
              {p.narrative?.subheadline && (
                <p className="text-[15px] md:text-[17px] mt-5 leading-[1.65]" style={{ color: "#525252" }}>
                  {p.narrative.subheadline}
                </p>
              )}

              <div className="flex items-center gap-4 mt-6 text-[13px]" style={{ color: "#525252" }}>
                <div className="flex items-center gap-1.5">
                  <div className="flex" style={{ color: "#F5B800" }}>
                    {[...Array(5)].map((_, i) => (<Star key={i} size={14} weight="fill" />))}
                  </div>
                  <span className="font-semibold" style={{ color: "#0A0A0A" }}>{(p.rating?.score ?? 4.8).toFixed(1)}</span>
                  <span>· {p.rating?.count ?? 127} {t(lang, "testimonials_verified_reviews")}</span>
                </div>
                <span className="w-px h-4" style={{ background: "#E5E5E5" }} />
                <div className="flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full" style={{ background: "#10B981" }} />
                  <span style={{ color: "#0A0A0A" }}>{p.stock === null || (p.stock ?? 1) > 0 ? "En stock" : "Rupture"}</span>
                </div>
              </div>

              <div
                className="mt-8 pt-8 pb-6 flex items-baseline gap-3 flex-wrap"
                style={{ borderTop: "1px solid #E5E5E5" }}
                data-testid="product-price"
              >
                <span className="text-[40px] md:text-[48px] font-semibold tabular-nums leading-none" style={{ color: "#0A0A0A" }}>
                  {formatPrice(p.price, p.currency, lang)}
                </span>
                {p.compare_at_price && p.compare_at_price > p.price && (
                  <>
                    <span className="text-[18px] line-through tabular-nums" style={{ color: "#A3A3A3" }}>
                      {formatPrice(p.compare_at_price, p.currency, lang)}
                    </span>
                    <span
                      className="text-white text-[11px] font-semibold px-2.5 py-1 tracking-tight"
                      style={{ background: "#0A0A0A", borderRadius: "2px" }}
                    >
                      −{Math.round((1 - p.price / p.compare_at_price) * 100)}%
                    </span>
                  </>
                )}
              </div>
              <div className="text-[11px] uppercase tracking-[0.25em]" style={{ color: "#737373" }}>
                TVA incluse · {t(lang, "delivery_free_short")}
              </div>

              {(() => {
                const highlights = (p.narrative?.benefits || p.highlights || [])
                  .map((h) => (typeof h === "string" ? h : pickLang(h, lang) || h?.fr))
                  .filter(Boolean).slice(0, 4);
                const list = highlights.length ? highlights : [
                  t(lang, "product_highlight_delivery_72h"),
                  t(lang, "product_highlight_warranty_2y"),
                  t(lang, "product_highlight_returns_14d"),
                  t(lang, "product_highlight_support_7d"),
                ];
                return (
                  <ul
                    className="mt-8 p-5 space-y-2.5"
                    style={{ background: "#F5F5F5", borderRadius: "2px" }}
                    data-testid="product-highlights"
                  >
                    {list.map((h, i) => (
                      <li key={i} className="flex items-start gap-2.5 text-[13.5px] leading-snug" style={{ color: "#262626" }}>
                        <Check size={14} weight="bold" className="mt-[3px] shrink-0" style={{ color: "#0A0A0A" }} />
                        <span>{h}</span>
                      </li>
                    ))}
                  </ul>
                );
              })()}

              {typeof p.stock === "number" && p.stock > 0 && p.stock < 10 && (
                <div
                  className="mt-5 flex items-center gap-2 text-[13px] px-4 py-2.5"
                  style={{ background: "#FEF3C7", color: "#92400E", borderRadius: "2px" }}
                  data-testid="stock-urgency"
                >
                  <span className="w-2 h-2 rounded-full animate-pulse" style={{ background: "#F59E0B" }} />
                  <span className="font-medium">Stock limité · plus que {p.stock} en réserve</span>
                </div>
              )}

              <div className="mt-6 flex items-center gap-3">
                <div
                  className="flex items-center overflow-hidden bg-white h-14"
                  style={{ border: "1px solid #E5E5E5", borderRadius: "2px" }}
                >
                  <button
                    onClick={() => setQty(Math.max(1, qty - 1))}
                    data-testid="qty-minus"
                    className="w-12 h-14 hover:bg-neutral-50 text-lg"
                    style={{ color: "#0A0A0A" }}
                    aria-label="Réduire"
                  >
                    −
                  </button>
                  <div
                    className="w-10 text-center font-semibold tabular-nums"
                    style={{ color: "#0A0A0A" }}
                    data-testid="qty-value"
                  >
                    {qty}
                  </div>
                  <button
                    onClick={() => setQty(qty + 1)}
                    data-testid="qty-plus"
                    className="w-12 h-14 hover:bg-neutral-50 text-lg"
                    style={{ color: "#0A0A0A" }}
                    aria-label="Augmenter"
                  >
                    +
                  </button>
                </div>

                <button
                  onClick={handleAdd}
                  data-testid="add-to-cart"
                  className="flex-1 h-14 font-semibold text-[14px] tracking-wide transition-all active:scale-[0.98] text-white flex items-center justify-center gap-2"
                  style={{ background: added ? "#047857" : "#0A0A0A", borderRadius: "2px" }}
                >
                  {added ? (
                    <>
                      <CheckCircle size={16} weight="fill" /> {t(lang, "added_to_cart")}
                    </>
                  ) : (
                    <>{t(lang, "add_to_cart")}</>
                  )}
                </button>
              </div>

              <div className="mt-6 space-y-3">
                <DeliveryEstimate design={design} />
                <PaymentOptions price={p.price} currency={p.currency} design={design} lang={lang} />
              </div>

              <div className="mt-8 grid grid-cols-2 gap-2.5" data-testid="product-trust-badges">
                {[
                  { Icon: Truck,       label: t(lang, "trust_free_shipping"), sub: "48–72 h" },
                  { Icon: ShieldCheck, label: t(lang, "trust_warranty_2y"),   sub: "Pièces & MO" },
                  { Icon: CheckCircle, label: t(lang, "trust_returns_14d"),   sub: { fr: "Gratuit", en: "Free", de: "Kostenlos", nl: "Gratis", it: "Gratis", es: "Gratis" }[lang] || "Gratuit" },
                  { Icon: Star,        label: "4.8 / 5",                      sub: `${p.rating?.count ?? 127} ${t(lang, "testimonials_verified_reviews")}` },
                ].map((b, i) => (
                  <div
                    key={i}
                    className="p-3.5 flex items-start gap-2.5"
                    style={{ background: "#F5F5F5", borderRadius: "2px" }}
                  >
                    <b.Icon size={16} weight="thin" className="mt-[2px] shrink-0" style={{ color: "#0A0A0A" }} />
                    <div className="min-w-0">
                      <div className="text-[12.5px] font-semibold leading-tight" style={{ color: "#0A0A0A" }}>{b.label}</div>
                      <div className="text-[11px] mt-0.5" style={{ color: "#737373" }}>{b.sub}</div>
                    </div>
                  </div>
                ))}
              </div>

              {!p.narrative && pickLang(p.description, lang) && (
                <p
                  className="text-[14.5px] leading-relaxed mt-10 whitespace-pre-line"
                  style={{ color: "#525252" }}
                >
                  {pickLang(p.description, lang)}
                </p>
              )}
            </div>
          </div>

          <ProductBundle currentProduct={p} lang={lang} design={design} />

          <ProductEditorialMosaic
            images={[...(p.generated_images || []).map(g => g.url).filter(Boolean), ...(p.images || [])]}
            styledImages={p.generated_images || []}
            productName={pickLang(p.name, lang)}
            design={design}
          />

          <NarrativeSections
            sections={p.narrative?.sections}
            design={design}
            productImages={[...(p.generated_images || []).map(g => g.url).filter(Boolean), ...(p.images || [])]}
          />
          <TechSpecs specs={p.narrative?.tech_specs} design={design} />
          <BestForNotFor best_for={p.narrative?.seo?.best_for} not_for={p.narrative?.seo?.not_for} design={design} />
          <UsageSteps steps={p.narrative?.seo?.usage_steps} productName={pickLang(p.name, lang)} design={design} />
          <ProductFAQ faq={p.narrative?.faq} design={design} />
          <PeopleAlsoAsk items={p.narrative?.seo?.people_also_ask} design={design} lang={lang} />
          <ProductReviews product={p} design={design} lang={lang} />
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
      </div>

      <MobileStickyBuy
        product={p}
        onAdd={handleAdd}
        qty={qty}
        added={added}
        design={design}
        lang={lang}
      />

      <div
        className="md:hidden fixed bottom-0 inset-x-0 bg-white p-3 flex items-center gap-3 z-40"
        style={{ borderTop: "1px solid #E5E5E5" }}
      >
        <div className="flex-1 min-w-0">
          <div className="text-[11px] uppercase tracking-[0.2em] truncate" style={{ color: "#737373" }}>
            {pickLang(p.name, lang).slice(0, 28)}…
          </div>
          <div className="font-semibold tabular-nums" style={{ color: "#0A0A0A" }}>
            {formatPrice(p.price, p.currency, lang)}
          </div>
        </div>
        <button
          onClick={handleAdd}
          className="h-11 px-5 text-white text-[13px] font-semibold"
          style={{ background: added ? "#047857" : "#0A0A0A", borderRadius: "2px" }}
        >
          {added ? "Ajouté ✓" : "Ajouter"}
        </button>
      </div>
    </StorefrontLayout>
  );
}

export default StorefrontProduct;
