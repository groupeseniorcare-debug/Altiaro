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
  ArrowsCounterClockwise,
  Headphones,
} from "@phosphor-icons/react";
import SEOHead from "../components/SEOHead";
import { getPrimaryImage, getProductGallery, getProductGalleryForColor } from "../lib/productImage";

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
import { ProductColorProvider } from "../lib/ProductColorContext";
import ProductReviews from "../components/storefront/ProductReviews";
import CrossSellProducts from "../components/storefront/CrossSellProducts";
import DeliveryPaymentInfo from "../components/storefront/DeliveryPaymentInfo";
import MobileStickyBuy from "../components/storefront/MobileStickyBuy";
import VariantPicker from "../components/storefront/VariantPicker";
import {
  LastUpdatedBadge,
} from "../components/storefront/ProductSEOBlocks";
import ProductUsps from "../components/storefront/ProductUsps";
import ProductHowTo from "../components/storefront/ProductHowTo";
import ProductEditorialCards from "../components/storefront/ProductEditorialCards";
import WideLifestyleBanner from "../components/storefront/WideLifestyleBanner";
import { useShopSiteId } from "../lib/shopSiteId";
import {
  isUuid,
  productCanonicalUrl,
  productPath,
  collectionPath,
  shopPath,
} from "../lib/shopUrls";

export function StorefrontProduct() {
  const siteId = useShopSiteId(); const { productId } = useParams();
  const { site, design, lang, setLang, availableLangs } = useSiteAndLang();
  const navigate = useNavigate();
  const [p, setP] = useState(null);
  const [loading, setLoading] = useState(true);
  const [added, setAdded] = useState(false);
  const [qty, setQty] = useState(1);
  // Variante sélectionnée par défaut = 1ʳᵉ avec stock > 0, sinon 1ʳᵉ tout court.
  const [selectedVariant, setSelectedVariant] = useState(null);

  const { fontHeading } = designAccents(design);

  useEffect(() => {
    axios
      .get(`${BACKEND_URL}/api/public/sites/${siteId}/products/${productId}`)
      .then(({ data }) => {
        setP(data);
        // --- SEO: 301-style redirect UUID → slug (window.history.replaceState) ---
        // The backend resolves both UUID and slug → canonical slug returned as
        // `data.slug`. If the URL still carries the UUID, rewrite it to the
        // slug form (same path shape). This avoids UUID-based URLs being
        // indexed by Google while preserving navigation state.
        try {
          if (data?.slug && productId && productId !== data.slug && isUuid(productId)) {
            const target = productPath(siteId, data);
            if (target && target !== "#" && target !== window.location.pathname) {
              window.history.replaceState({}, "", target);
            }
          }
        } catch (_) { /* noop */ }
        // Initialise selectedVariant si le produit a des variantes (>1 cas non dégénéré)
        const vs = Array.isArray(data?.variants) ? data.variants : [];
        if (vs.length > 1) {
          const firstInStock = vs.find((v) => (v.stock ?? 1) > 0) || vs[0];
          setSelectedVariant(firstInStock || null);
        }
        try { window.altiaroTrack?.viewItem?.(data, lang); } catch (_) { /* noop */ }
      })
      .catch(() => setP(null))
      .finally(() => setLoading(false));
  }, [siteId, productId, lang]);

  // --- Calcul prix / image / disponibilité en tenant compte de la variante ---
  // Markup ratio = price / cost_price_ht (les 2 sont en EUR HT côté doc).
  // Si la variante a un sell_price_eur (cost variant), on applique le même
  // ratio pour rester cohérent avec la stratégie de marge.
  const variantAdjustedPrice = (() => {
    if (!p || !selectedVariant?.sell_price_eur) return p?.price;
    const baseCost = Number(p.cost_price_ht || 0);
    const basePrice = Number(p.price || 0);
    if (!baseCost || !basePrice) return basePrice;
    const ratio = basePrice / baseCost;
    return Math.round(selectedVariant.sell_price_eur * ratio * 100) / 100;
  })();
  const variantImages = (() => {
    if (!p) return [];
    const generated = (p.generated_images || []).map((g) => g.url).filter(Boolean);
    const baseImgs = [...generated, ...(p.images || [])];
    if (selectedVariant?.image && !baseImgs.includes(selectedVariant.image)) {
      // Insère l'image variante en première position
      return [selectedVariant.image, ...baseImgs];
    }
    return baseImgs;
  })();
  const isVariantOutOfStock = selectedVariant?.stock === 0;

  // Phase 2.3 — Slug couleur sélectionnée (variant-aware) pour piocher
  // dans `generated_images_by_variant[colorSlug]` les images cohérentes.
  // Logique alignée sur backend `services/color_variant_images.slugify_color`.
  const selectedColorSlug = (() => {
    const props = selectedVariant?.properties;
    if (!Array.isArray(props) || !props[0]) return null;
    return String(props[0])
      .trim()
      .toLowerCase()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/[^a-z0-9]+/g, "_")
      .replace(/^_+|_+$/g, "");
  })();

  const handleAdd = () => {
    addToCart(siteId, p, lang, qty, {
      variant: selectedVariant || null,
      variant_price: selectedVariant ? variantAdjustedPrice : undefined,
    });
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

  // Canonical URL (slug-based, always absolute)
  const canonicalUrl = productCanonicalUrl(site, p, lang);
  const canonicalPath = (() => {
    try {
      const u = new URL(canonicalUrl);
      return u.pathname || `/products/${p.slug || p.id}`;
    } catch (_) {
      return `/products/${p.slug || p.id}`;
    }
  })();

  return (
    <ProductColorProvider product={p}>
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
        canonical={canonicalUrl || undefined}
        image={getPrimaryImage(p)}
        type="product"
        siteName={site?.name}
        keywords={
          p.narrative?.seo?.keywords?.join(", ")
          || [pickLang(p.name, lang), p.category, ...(p.tags || [])].filter(Boolean).join(", ")
        }
        langs={buildHreflangs(site, canonicalPath)}
        schema={[
          {
            "@context": "https://schema.org",
            "@type": "Product",
            name: pickLang(p.name, lang),
            description: p.narrative?.subheadline || pickLang(p.description, lang),
            image: getProductGallery(p).slice(0, 6),
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
              url: canonicalUrl || undefined,
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
              { "@type": "ListItem", position: 1, name: "Accueil", item: `${window.location.origin}${shopPath(siteId)}` },
              { "@type": "ListItem", position: 2, name: "Collections", item: `${window.location.origin}${shopPath(siteId).replace(/\/$/, "")}/collections` },
              p.category ? { "@type": "ListItem", position: 3, name: p.category, item: `${window.location.origin}${collectionPath(siteId, p.category)}` } : null,
              { "@type": "ListItem", position: p.category ? 4 : 3, name: pickLang(p.name, lang), item: canonicalUrl },
            ].filter(Boolean),
          },
          (() => {
            const faqList = (p.faq_product?.length ? p.faq_product : (p.narrative?.faq || [])).slice(0, 8);
            return faqList.length ? {
              "@context": "https://schema.org",
              "@type": "FAQPage",
              mainEntity: faqList.map((f) => ({
                "@type": "Question",
                name: f.question,
                acceptedAnswer: { "@type": "Answer", text: f.answer },
              })),
            } : null;
          })(),
          (p.how_to_steps?.length >= 3) ? {
            "@context": "https://schema.org",
            "@type": "HowTo",
            name: `Comment utiliser ${pickLang(p.name, lang)}`,
            description: `Guide pas à pas pour l'utilisation de ${pickLang(p.name, lang)}.`,
            totalTime: "PT5M",
            step: p.how_to_steps.map((s, idx) => ({
              "@type": "HowToStep",
              position: idx + 1,
              name: s.title,
              text: s.description,
            })),
          } : (p.narrative?.seo?.usage_steps?.length ? {
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
          } : null),
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

        <div className="max-w-7xl mx-auto px-6 md:px-10 pt-0 md:pt-12 pb-12">
          {/* Lot G Fix 3 — breadcrumb caché en mobile pour que l'image soit
              EDGE-TO-EDGE directement sous le header (premium type Apple).
              Sur desktop, breadcrumb premium classique au-dessus de la grid. */}
          <nav
            className="hidden md:block text-[11px] uppercase tracking-[0.25em] mb-10"
            style={{ color: "#737373" }}
            data-testid="product-breadcrumb"
          >
            <Link to={shopPath(siteId)} className="hover:opacity-60 transition">Accueil</Link>
            <span className="mx-2 opacity-50">/</span>
            <Link to={`${shopPath(siteId).replace(/\/$/, "")}/collections`} className="hover:opacity-60 transition">Collections</Link>
            {p.category && (
              <>
                <span className="mx-2 opacity-50">/</span>
                <Link to={collectionPath(siteId, p.category)} className="hover:opacity-60 transition capitalize">
                  {p.category}
                </Link>
              </>
            )}
            <span className="mx-2 opacity-50">/</span>
            <span style={{ color: "#0A0A0A" }}>{pickLang(p.name, lang)}</span>
          </nav>

          <div className="grid grid-cols-1 md:grid-cols-[1.1fr_1fr] gap-8 lg:gap-16 mb-24 md:mb-32 items-start">
            {/* Phase 2.6 Tâche B — Galerie STICKY desktop pour éliminer le
                vide blanc à gauche : l'image suit le scroll de la colonne
                droite (info produit) qui est plus longue. Mobile : flow
                normal edge-to-edge. */}
            <div className="-mx-6 md:mx-0 md:sticky md:top-24 md:self-start">
              <ProductGallery
                images={variantImages}
                name={pickLang(p.name, lang)}
                design={design}
                product={p}
                styledImages={p.generated_images}
              />
            </div>

            <div className="md:pt-2">
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
              {/* Lot I Fix I2 — Tagline IA (40-80 chars, Haiku 4.5) sous le titre.
                  Lecture stricte de `p.tagline`. Si absente, on retombe sur
                  narrative.subheadline (ancien comportement). Dict multi-lang
                  géré par pickLang défensif. */}
              {pickLang(p.tagline, lang) ? (
                <p
                  className="text-[15px] md:text-[17px] mt-5 leading-[1.6] italic"
                  style={{
                    color: "#525252",
                    fontFamily: `"${fontHeading}", Georgia, serif`,
                    fontWeight: 400,
                    letterSpacing: "0.005em",
                  }}
                  data-testid="product-tagline"
                >
                  {pickLang(p.tagline, lang)}
                </p>
              ) : p.narrative?.subheadline && (
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
                  {formatPrice(variantAdjustedPrice ?? p.price, p.currency, lang)}
                </span>
                {p.compare_at_price && p.compare_at_price > (variantAdjustedPrice ?? p.price) && (
                  <>
                    <span className="text-[18px] line-through tabular-nums" style={{ color: "#A3A3A3" }}>
                      {formatPrice(p.compare_at_price, p.currency, lang)}
                    </span>
                    <span
                      className="text-white text-[11px] font-semibold px-2.5 py-1 tracking-tight"
                      style={{ background: "#0A0A0A", borderRadius: "2px" }}
                    >
                      −{Math.round((1 - (variantAdjustedPrice ?? p.price) / p.compare_at_price) * 100)}%
                    </span>
                  </>
                )}
              </div>
              <div className="text-[11px] uppercase tracking-[0.25em]" style={{ color: "#737373" }}>
                TVA incluse · {t(lang, "delivery_free_short")}
              </div>

              {/* Sélecteur de variantes (couleur / taille) — affiché uniquement si > 1 variante */}
              {p.variants?.length > 1 && (
                <div className="mt-8" data-testid="product-variant-picker-section">
                  <VariantPicker
                    variants={p.variants}
                    selected={selectedVariant}
                    onSelect={setSelectedVariant}
                    lang={lang}
                  />
                </div>
              )}

              {/* Lot I Fix I3 — Les 4 USPs ALTEA hardcodés sont retirés de la
                  sidebar et remplacés par une section narrative pleine largeur
                  `<ProductUsps>` plus bas (lecture stricte de `p.usps` généré
                  par Haiku 4.5). Décision user 2026-04-27 : section
                  "Est-ce fait pour vous" supprimée, USPs amplifiés à la place.
                  Phase 2.3 : version COMPACTE (4 lignes condensées) au-dessus
                  du CTA pour visibilité immédiate des bénéfices clés. */}
              {Array.isArray(p.usps) && p.usps.length >= 3 && (
                <div
                  className="mt-7 mb-1 py-5 px-5"
                  style={{ background: "#FAF8F4", border: "1px solid #E7E5E4", borderRadius: "2px" }}
                  data-testid="product-usps-compact"
                >
                  <ul className="space-y-3">
                    {p.usps.slice(0, 4).map((u, i) => (
                      <li key={i} className="flex items-start gap-3">
                        <Check size={14} weight="bold" className="mt-1 shrink-0" style={{ color: "#9F6E50" }} />
                        <div className="min-w-0">
                          <div className="text-[13.5px] font-medium leading-tight" style={{ color: "#0A0A0A" }}>
                            {pickLang(u.title, lang)}
                          </div>
                          <div className="text-[12px] mt-0.5 leading-snug" style={{ color: "#737373" }}>
                            {pickLang(u.description, lang)}
                          </div>
                        </div>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

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
                  disabled={isVariantOutOfStock}
                  data-testid="add-to-cart"
                  className="flex-1 h-14 font-semibold text-[14px] tracking-wide transition-all active:scale-[0.98] text-white flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                  style={{ background: added ? "#047857" : "#0A0A0A", borderRadius: "2px" }}
                >
                  {isVariantOutOfStock ? (
                    <>{t(lang, "out_of_stock") || "Indisponible"}</>
                  ) : added ? (
                    <>
                      <CheckCircle size={16} weight="fill" /> {t(lang, "added_to_cart")}
                    </>
                  ) : (
                    <>{t(lang, "add_to_cart")}</>
                  )}
                </button>
              </div>

              <div className="mt-6">
                <DeliveryPaymentInfo price={p.price} currency={p.currency} design={design} lang={lang} />
              </div>

              <div className="mt-8 grid grid-cols-2 gap-2.5" data-testid="product-trust-badges">
                {[
                  { Icon: Truck,                  label: t(lang, "trust_free_shipping"), sub: "48–72 h" },
                  { Icon: ShieldCheck,            label: t(lang, "trust_warranty_2y"),   sub: "Pièces & MO" },
                  { Icon: ArrowsCounterClockwise, label: t(lang, "trust_returns_14d"),   sub: { fr: "Gratuit", en: "Free", de: "Kostenlos", nl: "Gratis", it: "Gratis", es: "Gratis" }[lang] || "Gratuit" },
                  { Icon: Headphones,             label: "Conseil dédié",                sub: "Lun–Sam 9h–19h" },
                ].map((b, i) => (
                  <div
                    key={i}
                    className="p-4 flex items-start gap-3 transition-all hover:translate-y-[-1px]"
                    style={{
                      background: "#F5F2EB",
                      border: "1px solid #E7E5E4",
                      borderRadius: "2px",
                    }}
                  >
                    <b.Icon size={18} weight="thin" className="mt-[2px] shrink-0" style={{ color: "#0A0A0A" }} />
                    <div className="min-w-0">
                      <div
                        className="text-[14px] leading-tight font-light"
                        style={{ fontFamily: fontHeading, color: "#0A0A0A" }}
                      >
                        {b.label}
                      </div>
                      <div className="text-[10.5px] mt-1 uppercase tracking-[0.18em]" style={{ color: "#9C8C7C" }}>
                        {b.sub}
                      </div>
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

          {/* ════════════════════════════════════════════════════════════
              Phase 2.6 — Trame officielle page produit (ordre strict).
              Sections supprimées : ProductBundle, UpsellsRecommendations,
              RelatedQueries, PeopleAlsoAsk, NarrativeSections, Mosaic.
              Décision user 2026-04-28.
              ════════════════════════════════════════════════════════════ */}

          {/* §2 — Image horizontale "En situation" (16:9 cinematic banner) */}
          <WideLifestyleBanner product={p} productName={pickLang(p.name, lang)} design={design} />

          {/* §3 — "Comment l'utiliser" — adaptive selon product_kind
              (HowTo classique pour fauteuils, "Comment l'utiliser au quotidien"
              pour blanket, "Trouver votre maintien" pour cushion, etc.).
              Le titre H2 est piloté par `p.how_to_steps_meta.section_title`
              (généré par Haiku adaptatif dans services/product_content_ai.py). */}
          <ProductHowTo
            steps={p.how_to_steps}
            sectionTitle={p.how_to_steps_meta?.section_title}
            design={design}
            lang={lang}
          />

          {/* §4 — 3 images avec titre + sous-titre (editorial cards) */}
          <ProductEditorialCards
            product={p}
            colorSlug={selectedColorSlug}
            design={design}
            lang={lang}
          />

          {/* §5 — Caractéristiques produit */}
          <TechSpecs specs={p.narrative?.tech_specs} design={design} />

          {/* §6 — "Ce qui rend ce produit singulier" : USPs pleine largeur */}
          <ProductUsps usps={p.usps} design={design} lang={lang} />
        </div>
      </div>

      {/* §7 — FAQ produit unique, CENTRÉE desktop (max-w-3xl ≈ 768px),
          pleine largeur mobile. Lit `p.faq_product` (priorité) → fallback
          legacy `p.narrative.faq`. JSON-LD FAQPage aligné UI ↔ SEO. */}
      <section className="bg-white" data-testid="product-faq-section-fullwidth">
        <div className="max-w-3xl mx-auto px-6 md:px-8">
          <ProductFAQ
            faq={p.faq_product?.length ? p.faq_product : p.narrative?.faq}
            design={design}
          />
        </div>
      </section>

      <div className="bg-white">
        <div className="max-w-7xl mx-auto px-6 md:px-10 pb-12">
          {/* §8 — Avis client avec photos (avatars + photos lifestyle).
              Phase 2.6 Tâche E : enrichis via `design.testimonials_premium`
              et `product.review_photos` (Nano Banana, scènes domestiques). */}
          <ProductReviews product={p} design={design} lang={lang} />

          {/* §9 — "Dans la même collection" (cross-sell, design Home unifié) */}
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
    </ProductColorProvider>
  );
}

export default StorefrontProduct;
