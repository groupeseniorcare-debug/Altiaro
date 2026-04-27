/**
 * Lot G Fix 12 — ProductCard unifié, source de vérité pour TOUTES les cards
 * produit du storefront (Home, Collection, Search, CrossSell, Upsells, Bundle...).
 *
 * Design : épuré premium type Apple Watch / Hermès — aspect-square, image en
 * vedette sur fond ivoire (`#F5F2EB`) avec coins légèrement arrondis, badge
 * featured + badge promo, hover scale subtil, titre en Cormorant et prix en
 * Manrope. Pas de CTA add-to-cart inline (clic → fiche produit, plus premium).
 *
 * Modes :
 *   variant="default"  → grille principale (Home, Collection, Search)
 *   variant="compact"  → mini-card (cross-sell, bundle, upsells dans sidebar)
 *
 * Usage parent :
 *   <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
 *     {products.map(p => <ProductCard key={p.id} product={p} siteId={siteId} ... />)}
 *   </div>
 *
 * Le composant n'inclut PAS de grid : c'est la responsabilité du parent.
 * Mobile edge-to-edge : passer `edgeToEdge` (radius 0, image full-width).
 */
import React from "react";
import { Link } from "react-router-dom";
import { ShoppingBagOpen, Star } from "@phosphor-icons/react";
import { pickLang } from "../../lib/i18n";
import { designAccents, formatPrice } from "./storefrontUtils";
import { getPrimaryImage } from "../../lib/productImage";

export default function ProductCard({
  product,
  siteId,
  lang = "fr",
  design,
  variant = "default", // "default" | "compact"
  edgeToEdge = false,  // true → no rounding (mobile edge-to-edge)
  showRating = true,
  showFeaturedBadge = true,
  showPromoBadge = true,
  className = "",
  testId,
  href, // override URL (pour cas spécial : non-cliquable, non-storefront, etc.)
}) {
  if (!product) return null;
  const name = pickLang(product.name, lang) || product.name || "—";
  const price = product.price;
  const compareAt = product.compare_at_price;
  const currency = product.currency || "EUR";
  const rating = product.rating || product.aggregate_rating?.value;
  const reviewsCount = product.reviews_count || product.aggregate_rating?.count;
  const imageSrc = getPrimaryImage(product);
  const isFeatured = !!product.featured;
  const hasPromo = !!compareAt && compareAt > price;
  const promoPct = hasPromo ? Math.round(((compareAt - price) / compareAt) * 100) : 0;

  const { primary, fontHeading, textMuted, textFaint } = designAccents(design);
  const url = href || `/shop/${siteId}/product/${product.id}`;

  const isCompact = variant === "compact";

  // Sizing tokens — compact = plus petit (cross-sell, bundle)
  const titleClass = isCompact
    ? "text-[14px] md:text-[15px] leading-tight tracking-tight line-clamp-2"
    : "text-[16px] md:text-[18px] leading-snug tracking-tight line-clamp-2";
  const priceClass = isCompact
    ? "text-[14px] md:text-[15px] font-semibold tabular-nums"
    : "text-[17px] md:text-[18px] font-semibold tabular-nums";
  const compareClass = isCompact ? "text-[12px] line-through" : "text-[13px] line-through";
  const imageRadius = edgeToEdge
    ? "rounded-none"
    : isCompact
    ? "rounded-xl"
    : "rounded-2xl";
  const wrapperPad = isCompact ? "pt-3" : "pt-4 md:pt-5";

  return (
    <Link
      to={url}
      data-testid={testId || `product-card-${product.id}`}
      className={`group block focus:outline-none focus-visible:ring-2 focus-visible:ring-neutral-400 focus-visible:ring-offset-2 ${className}`}
    >
      {/* IMAGE — aspect carré, fond ivoire, hover scale subtil */}
      <div className={`aspect-square relative overflow-hidden bg-[#F5F2EB] ${imageRadius}`}>
        {imageSrc ? (
          <img
            src={imageSrc}
            alt={name}
            loading="lazy"
            className="absolute inset-0 w-full h-full object-cover transition-transform duration-700 ease-out group-hover:scale-[1.04]"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center" style={{ color: textFaint }}>
            <ShoppingBagOpen size={isCompact ? 44 : 56} weight="thin" />
          </div>
        )}

        {/* Badge featured (top-left) */}
        {showFeaturedBadge && isFeatured && (
          <div
            className="absolute top-3 left-3 bg-white/95 backdrop-blur-sm px-2.5 py-1 text-[10px] uppercase tracking-[0.22em] font-semibold rounded-full flex items-center gap-1"
            style={{ color: primary }}
          >
            <Star size={9} weight="fill" style={{ color: "#F5B800" }} /> Phare
          </div>
        )}

        {/* Badge promo (top-right) */}
        {showPromoBadge && hasPromo && (
          <div
            className="absolute top-3 right-3 text-white text-[11px] font-semibold px-2 py-1 rounded-full tracking-tight"
            style={{ background: "#1C1917" }}
          >
            −{promoPct}%
          </div>
        )}
      </div>

      {/* INFOS — typo Cormorant titre + Manrope prix */}
      <div className={`${wrapperPad} px-1`}>
        <h3
          className={titleClass}
          style={{
            fontFamily: `"${fontHeading}", serif`,
            fontWeight: 500,
            color: "#1a1a1a",
          }}
        >
          {name}
        </h3>

        {/* Rating si disponible */}
        {showRating && rating && (
          <div
            className="flex items-center gap-1 mt-2 text-[12px]"
            style={{ color: textMuted }}
            data-testid={`product-rating-${product.id}`}
          >
            <Star size={12} weight="fill" style={{ color: "#F5B800" }} />
            <span className="font-medium">{Number(rating).toFixed(1)}</span>
            {reviewsCount ? (
              <span className="opacity-60">· {reviewsCount} avis</span>
            ) : null}
          </div>
        )}

        {/* Prix */}
        <div className="flex items-baseline gap-2 mt-2">
          <span className={priceClass} style={{ color: primary }}>
            {formatPrice(price, currency, lang)}
          </span>
          {hasPromo && (
            <span className={compareClass} style={{ color: textFaint }}>
              {formatPrice(compareAt, currency, lang)}
            </span>
          )}
        </div>
      </div>
    </Link>
  );
}
