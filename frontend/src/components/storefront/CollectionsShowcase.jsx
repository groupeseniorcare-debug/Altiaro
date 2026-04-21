import React from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowRight } from "@phosphor-icons/react";
import { pickLang } from "../../lib/i18n";

/**
 * Collections showcase — 3 à 4 univers thématiques mis en avant.
 * Alimenté par design.collections = [{ title, description, image, slug|href }]
 * Fallback silver-eco par défaut.
 */
export default function CollectionsShowcase({ collections, lang = "fr", design }) {
  const { siteId } = useParams();
  const primary = design?.brand?.primary_color || "#B84B31";
  const accent = design?.brand?.accent_color || "#F5F2EB";
  const fontHeading = design?.brand?.font_heading || "Fraunces";

  const list = collections?.length
    ? collections
    : [
        {
          slug: "mobilite",
          title: "Mobilité & confort",
          description: "Fauteuils releveurs, déambulateurs, aides à la marche.",
          image: "https://images.unsplash.com/photo-1586773860418-d37222d8fce3?w=900&auto=format&fit=crop",
        },
        {
          slug: "sommeil",
          title: "Sommeil & récupération",
          description: "Matelas médicaux, lits électriques, linge adapté.",
          image: "https://images.unsplash.com/photo-1505693416388-ac5ce068fe85?w=900&auto=format&fit=crop",
        },
        {
          slug: "quotidien",
          title: "Quotidien serein",
          description: "Alarmes, éclairages, ustensiles ergonomiques.",
          image: "https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?w=900&auto=format&fit=crop",
        },
      ];

  return (
    <section className="py-20 md:py-28 px-6 bg-white" data-testid="storefront-collections">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-end justify-between flex-wrap gap-4 mb-12">
          <div>
            <div className="text-[11px] uppercase tracking-[0.2em] text-neutral-500 mb-3">Nos univers</div>
            <h2 className="text-4xl md:text-5xl" style={{ fontFamily: `${fontHeading}, serif`, color: "#1C1917" }}>
              Explorer par collection
            </h2>
          </div>
          <Link
            to={`/shop/${siteId}`}
            className="text-sm inline-flex items-center gap-1.5 hover:gap-2.5 transition-all"
            style={{ color: primary }}
            data-testid="collections-see-all"
          >
            Voir toute la boutique <ArrowRight size={14} weight="bold" />
          </Link>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-5 md:gap-6">
          {list.slice(0, 3).map((c, i) => {
            const title = pickLang(c.title, lang) || c.title;
            const desc = pickLang(c.description, lang) || c.description;
            const href = c.slug
              ? `/shop/${siteId}/collection/${c.slug}`
              : (c.href?.startsWith("/") ? c.href : `/shop/${siteId}${c.href || ""}`);
            return (
              <Link
                key={i}
                to={href}
                data-testid={`collection-${i}`}
                className="group relative block rounded-3xl overflow-hidden aspect-[4/5] md:aspect-[3/4]"
                style={{ background: accent }}
              >
                {c.image ? (
                  <img
                    src={c.image}
                    alt={title}
                    loading="lazy"
                    className="absolute inset-0 w-full h-full object-cover transition-transform duration-700 group-hover:scale-105"
                  />
                ) : null}
                <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-black/20 to-transparent" />
                <div className="absolute inset-0 p-7 md:p-8 flex flex-col justify-end text-white">
                  <div className="text-[10px] uppercase tracking-widest opacity-80 mb-2">Collection {i + 1 < 10 ? `0${i + 1}` : i + 1}</div>
                  <h3 className="text-2xl md:text-3xl leading-tight mb-2" style={{ fontFamily: `${fontHeading}, serif` }}>
                    {title}
                  </h3>
                  <p className="text-sm text-white/85 mb-4 line-clamp-2">{desc}</p>
                  <div className="inline-flex items-center gap-1.5 text-sm font-medium group-hover:gap-2.5 transition-all">
                    Découvrir <ArrowRight size={14} weight="bold" />
                  </div>
                </div>
              </Link>
            );
          })}
        </div>
      </div>
    </section>
  );
}
