import React from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowRight, Clock } from "@phosphor-icons/react";
import { pickLang } from "../../lib/i18n";

/**
 * Blog / Journal teaser — 3 derniers articles mis en avant.
 * design.blog_posts = [{ slug, title, excerpt, image, category, read_minutes, published_at }]
 */
export default function BlogTeaser({ posts, lang = "fr", design }) {
  const { siteId } = useParams();
  const primary = design?.brand?.primary_color || "#B84B31";
  const accent = design?.brand?.accent_color || "#F5F2EB";
  const fontHeading = design?.brand?.font_heading || "Fraunces";

  const list = posts?.length
    ? posts
    : [
        {
          slug: "bien-choisir-fauteuil-releveur",
          category: "Guide d'achat",
          title: "Bien choisir son fauteuil releveur : le guide complet",
          excerpt: "Moteur, hauteur d'assise, position médicale… tout ce qu'il faut savoir avant d'acheter.",
          image: "https://images.unsplash.com/photo-1493663284031-b7e3aefcae8e?w=900&auto=format&fit=crop",
          read_minutes: 6,
        },
        {
          slug: "maintien-domicile-5-essentiels",
          category: "Maintien à domicile",
          title: "Maintien à domicile : les 5 équipements essentiels",
          excerpt: "Barres d'appui, détecteurs de chute, éclairages automatiques : notre sélection pour vivre sereinement chez soi.",
          image: "https://images.unsplash.com/photo-1579684385127-1ef15d508118?w=900&auto=format&fit=crop",
          read_minutes: 4,
        },
        {
          slug: "nuits-reparatrices-seniors",
          category: "Sommeil",
          title: "Retrouver des nuits réparatrices après 70 ans",
          excerpt: "Un matelas adapté change tout. On vous explique pourquoi et comment le choisir.",
          image: "https://images.unsplash.com/photo-1540518614846-7eded433c457?w=900&auto=format&fit=crop",
          read_minutes: 5,
        },
      ];

  return (
    <section className="py-20 md:py-28 px-6" data-testid="storefront-blog" style={{ background: accent }}>
      <div className="max-w-6xl mx-auto">
        <div className="flex items-end justify-between flex-wrap gap-4 mb-12">
          <div>
            <div className="text-[11px] uppercase tracking-[0.2em] text-neutral-500 mb-3">Le Journal</div>
            <h2 className="text-4xl md:text-5xl" style={{ fontFamily: `${fontHeading}, serif`, color: "#1C1917" }}>
              Nos guides et conseils
            </h2>
          </div>
          <Link
            to={`/shop/${siteId}/blog`}
            className="text-sm inline-flex items-center gap-1.5 hover:gap-2.5 transition-all"
            style={{ color: primary }}
            data-testid="blog-see-all"
          >
            Tous les articles <ArrowRight size={14} weight="bold" />
          </Link>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {list.slice(0, 3).map((p, i) => {
            const title = pickLang(p.title, lang) || p.title;
            const excerpt = pickLang(p.excerpt, lang) || p.excerpt;
            const category = pickLang(p.category, lang) || p.category;
            return (
              <Link
                key={i}
                to={`/shop/${siteId}/blog/${p.slug}`}
                data-testid={`blog-post-${i}`}
                className="group block bg-white rounded-3xl overflow-hidden hover:shadow-lg transition-shadow duration-500"
              >
                <div className="aspect-[5/3] bg-neutral-100 overflow-hidden">
                  {p.image && (
                    <img
                      src={p.image}
                      alt={title}
                      loading="lazy"
                      className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-105"
                    />
                  )}
                </div>
                <div className="p-7">
                  <div className="flex items-center gap-3 text-[11px] uppercase tracking-widest mb-3" style={{ color: primary }}>
                    <span>{category}</span>
                    {p.read_minutes && (
                      <span className="flex items-center gap-1 text-neutral-500">
                        <Clock size={12} weight="bold" />
                        {p.read_minutes} min
                      </span>
                    )}
                  </div>
                  <h3 className="text-xl leading-snug mb-3 text-neutral-900 group-hover:opacity-80 transition" style={{ fontFamily: `${fontHeading}, serif` }}>
                    {title}
                  </h3>
                  <p className="text-[14px] text-neutral-600 leading-relaxed line-clamp-2">{excerpt}</p>
                  <div className="mt-5 inline-flex items-center gap-1.5 text-sm font-medium group-hover:gap-2.5 transition-all" style={{ color: primary }}>
                    Lire l'article <ArrowRight size={14} weight="bold" />
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
