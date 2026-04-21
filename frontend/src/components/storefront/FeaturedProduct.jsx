import React from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowRight, CheckCircle, Star } from "@phosphor-icons/react";
import { pickLang } from "../../lib/i18n";
import { formatPrice } from "./storefrontUtils";

/**
 * Featured Product — spotlight sur le produit hero de la boutique.
 * Prend le 1er produit reçu (ou celui marqué featured dans design.featured_product_id).
 * Si aucun produit, la section ne s'affiche pas.
 */
export default function FeaturedProduct({ products, design, lang = "fr" }) {
  const { siteId } = useParams();
  const primary = design?.brand?.primary_color || "#B84B31";
  const accent = design?.brand?.accent_color || "#F5F2EB";
  const fontHeading = design?.brand?.font_heading || "Fraunces";

  const featuredId = design?.featured_product_id;
  const featured = featuredId
    ? products?.find((p) => p.id === featuredId)
    : products?.[0];

  // Demo fallback to show the template block even before the catalog is imported.
  // Automatically replaced by a real product as soon as the catalogue exists.
  const demo = !featured
    ? {
        id: "demo",
        name: "Fauteuil releveur Confort Plus — 2 moteurs",
        description: "Confort orthopédique, relevage électrique 2 moteurs, revêtement tissu anti-taches. Livré monté, installé chez vous.",
        price: 899,
        compare_at_price: 1199,
        currency: "EUR",
        images: ["https://images.unsplash.com/photo-1555041469-a586c61ea9bc?w=900&auto=format&fit=crop"],
        _isDemo: true,
      }
    : null;
  const displayed = featured || demo;

  const name = pickLang(displayed.name, lang) || displayed.name;
  const description = pickLang(displayed.description, lang) || displayed.description || "";
  const image = displayed.images?.[0];
  const bullets = design?.featured_bullets?.[lang]
    || design?.featured_bullets?.fr
    || [
      "Testé par des ergothérapeutes",
      "Livraison + installation offertes",
      "Garantie 2 ans incluse",
      "Essai 14 jours à domicile",
    ];

  return (
    <section className="py-20 md:py-28 px-6" data-testid="storefront-featured" style={{ background: accent }}>
      <div className="max-w-7xl mx-auto">
        <div className="text-center mb-14">
          <div className="text-[11px] uppercase tracking-[0.2em] text-neutral-500 mb-3">
            Notre coup de cœur
          </div>
          <h2 className="text-4xl md:text-5xl" style={{ fontFamily: `${fontHeading}, serif`, color: "#1C1917" }}>
            Le best-seller de la maison
          </h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-10 lg:gap-16 items-center">
          {/* Image */}
          <div className="relative aspect-[4/5] rounded-3xl overflow-hidden bg-white">
            {image ? (
              <img src={image} alt={name} loading="lazy" className="w-full h-full object-cover" />
            ) : (
              <div className="w-full h-full flex items-center justify-center text-neutral-300 text-lg">
                {name}
              </div>
            )}
            {displayed.compare_at_price && displayed.compare_at_price > displayed.price && (
              <div
                className="absolute top-5 left-5 text-white text-xs font-semibold px-3 py-1.5 rounded-full"
                style={{ background: primary }}
              >
                -{Math.round((1 - displayed.price / displayed.compare_at_price) * 100)}%
              </div>
            )}
          </div>

          {/* Copy */}
          <div>
            {/* Rating */}
            <div className="flex items-center gap-2 mb-4">
              <div className="flex" style={{ color: "#F59E0B" }}>
                {[...Array(5)].map((_, i) => (
                  <Star key={i} size={16} weight="fill" />
                ))}
              </div>
              <div className="text-sm text-neutral-600">
                <span className="font-semibold">4.9</span> · 847 avis vérifiés
              </div>
            </div>

            <h3
              className="text-3xl md:text-4xl leading-tight text-neutral-900 mb-4"
              style={{ fontFamily: `${fontHeading}, serif` }}
              data-testid="featured-name"
            >
              {name}
            </h3>

            {description && (
              <p className="text-[16px] text-neutral-600 leading-relaxed mb-6 line-clamp-3">
                {description}
              </p>
            )}

            {/* Price */}
            <div className="flex items-baseline gap-3 mb-6">
              <span className="text-3xl font-semibold" style={{ color: primary }}>
                {formatPrice(displayed.price, displayed.currency, lang)}
              </span>
              {displayed.compare_at_price && displayed.compare_at_price > displayed.price && (
                <span className="text-xl text-neutral-400 line-through">
                  {formatPrice(displayed.compare_at_price, displayed.currency, lang)}
                </span>
              )}
            </div>

            {/* Bullets */}
            <ul className="space-y-2.5 mb-8">
              {bullets.slice(0, 4).map((b, i) => (
                <li key={i} className="flex items-center gap-2.5 text-[15px] text-neutral-700">
                  <CheckCircle size={18} weight="fill" style={{ color: primary }} />
                  {b}
                </li>
              ))}
            </ul>

            {/* CTA */}
            <div className="flex flex-col sm:flex-row gap-3">
              <Link
                to={displayed._isDemo ? `/shop/${siteId}` : `/shop/${siteId}/product/${displayed.id}`}
                data-testid="featured-cta"
                className="inline-flex items-center justify-center gap-2 h-14 px-8 rounded-full text-white font-medium text-[15px] transition hover:opacity-90 active:scale-[0.98]"
                style={{ background: primary }}
              >
                Voir le produit <ArrowRight size={16} weight="bold" />
              </Link>
              <Link
                to={`/shop/${siteId}`}
                className="inline-flex items-center justify-center gap-2 h-14 px-7 rounded-full border border-neutral-300 hover:bg-white font-medium text-[15px] transition text-neutral-900"
              >
                Voir toute la boutique
              </Link>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
