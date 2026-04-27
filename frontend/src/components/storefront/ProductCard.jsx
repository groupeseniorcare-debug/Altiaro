/**
 * Lot G Fix 12 — ProductCard unifié, réutilisable sur :
 * - StorefrontHome (grille principale)
 * - StorefrontCollection (page collection)
 * - StorefrontSearch (résultats)
 * - CrossSellProducts (cross-sell sur fiche produit)
 * - UpsellsRecommendations (upsells)
 * - FeaturedProduct (mise en avant)
 *
 * Une seule source de vérité pour le rendu des cards = cohérence visuelle
 * absolue (image studio, prix, typo, ratio, hover) sur toutes les surfaces.
 *
 * Layout :
 *   Desktop (≥lg) : 3 colonnes (parent doit fournir grid-cols-3)
 *   Tablette (md..lg) : 2 colonnes
 *   Mobile (<md)  : 1 colonne pleine largeur
 *
 * Ce composant ne contient pas la grille — juste 1 card. Le parent
 * doit utiliser : `grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6`
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
  className = "",
  testId,
}) {
  if (!product) return null;
  const name = pickLang(product.name, lang) || product.name || "—";
  const price = product.price;
  const compareAt = product.compare_at_price;
  const currency = product.currency || "EUR";
  const rating = product.rating || product.aggregate_rating?.value;
  const reviewsCount = product.reviews_count || product.aggregate_rating?.count;
  const imageSrc = getPrimaryImage(product);
  const { primary, fontHeading, textMuted, textFaint } = designAccents(design);
  const url = `/shop/${siteId}/product/${product.id}`;

  return (
    <Link
      to={url}
      data-testid={testId || `product-card-${product.id}`}
      className={`group block ${className}`}
    >
      {/* IMAGE — aspect carré, fond ivoire, hover scale subtil */}
      <div className="aspect-square relative overflow-hidden bg-[#F5F2EB]">
        {imageSrc ? (
          <img
            src={imageSrc}
            alt={name}
            loading="lazy"
            className="absolute inset-0 w-full h-full object-cover transition-transform duration-700 ease-out group-hover:scale-[1.04]"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center" style={{ color: textFaint }}>
            <ShoppingBagOpen size={56} weight="thin" />
          </div>
        )}
        {/* Badge promo si compare_at > price */}
        {compareAt && compareAt > price && (
          <div className="absolute top-3 left-3 bg-white/90 backdrop-blur-sm px-3 py-1 text-[11px] uppercase tracking-[0.2em] text-neutral-900">
            -{Math.round(((compareAt - price) / compareAt) * 100)}%
          </div>
        )}
      </div>

      {/* INFOS — typo Cormorant titre + Manrope prix */}
      <div className="pt-5 px-1">
        <h3
          className="text-[18px] md:text-[19px] leading-[1.25] tracking-[-0.005em] mb-2 line-clamp-2"
          style={{ fontFamily: `"${fontHeading}", serif`, fontWeight: 400, color: "#1a1a1a" }}
        >
          {name}
        </h3>
        {/* Rating si disponible */}
        {rating && (
          <div className="flex items-center gap-1 mb-2 text-[12px]" style={{ color: textMuted }}>
            <Star size={12} weight="fill" style={{ color: primary }} />
            <span>{Number(rating).toFixed(1)}</span>
            {reviewsCount && <span className="opacity-60">· {reviewsCount}</span>}
          </div>
        )}
        {/* Prix */}
        <div className="flex items-baseline gap-2 mt-1">
          <span className="text-[15px] font-medium" style={{ color: "#1a1a1a" }}>
            {formatPrice(price, currency, lang)}
          </span>
          {compareAt && compareAt > price && (
            <span className="text-[13px] line-through" style={{ color: textFaint }}>
              {formatPrice(compareAt, currency, lang)}
            </span>
          )}
        </div>
      </div>
    </Link>
  );
}
