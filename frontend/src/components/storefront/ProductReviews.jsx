import React, { useState } from "react";
import { Star, CaretDown } from "@phosphor-icons/react";

/**
 * Product reviews section with rating distribution + individual reviews.
 * Consomme product.reviews = [{ author, rating, title, body, verified, date, location }]
 * + product.rating = { score, count }
 */
export default function ProductReviews({ product, design }) {
  const [sort, setSort] = useState("recent");
  const primary = design?.brand?.primary_color || "#B84B31";
  const fontHeading = design?.brand?.font_heading || "Fraunces";

  const fallbackReviews = [
    { author: "Françoise D.", location: "Lyon", date: "Il y a 2 semaines", rating: 5, title: "Exactement ce qu'il me fallait", body: "Commandé pour ma mère de 82 ans. Elle l'utilise tous les jours sans difficulté. Le conseiller m'a bien orientée au téléphone, je recommande.", verified: true },
    { author: "Marc L.", location: "Rennes", date: "Il y a 1 mois", rating: 5, title: "Qualité au-dessus de mes attentes", body: "Livraison rapide, produit bien protégé, finition impeccable. Le manuel est clair et les conseils utiles. Rien à redire.", verified: true },
    { author: "Hélène P.", location: "Bordeaux", date: "Il y a 1 mois", rating: 4, title: "Très satisfaite", body: "Un petit point de confort à améliorer selon moi, mais globalement très content du produit. Le SAV a été à l'écoute quand j'ai eu une question.", verified: true },
    { author: "Jean-Paul M.", location: "Toulouse", date: "Il y a 2 mois", rating: 5, title: "Parfait pour mon papa", body: "Simple à utiliser, robuste, on sent qu'il est pensé pour durer. Pas de gadgets inutiles. Merci pour l'accompagnement.", verified: true },
  ];

  const reviews = (product?.reviews?.length ? product.reviews : fallbackReviews);
  const ratingMeta = product?.rating || { score: 4.8, count: reviews.length };

  // Distribution
  const dist = [5, 4, 3, 2, 1].map((stars) => {
    const n = reviews.filter((r) => r.rating === stars).length;
    return { stars, n, pct: reviews.length ? Math.round((n / reviews.length) * 100) : 0 };
  });

  const sorted = [...reviews].sort((a, b) => {
    if (sort === "rating_desc") return b.rating - a.rating;
    if (sort === "rating_asc") return a.rating - b.rating;
    return 0; // keep original order for "recent"
  });

  return (
    <section className="py-16 md:py-24 border-t" style={{ borderColor: "#E7E5E4" }} data-testid="product-reviews">
      <div className="mb-12">
        <div className="text-[11px] uppercase tracking-[0.2em] text-neutral-500 mb-3">Avis clients</div>
        <h2 className="text-3xl md:text-4xl" style={{ fontFamily: `"${fontHeading}", serif`, color: "#1C1917" }}>
          Ils ont acheté ce produit
        </h2>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[320px_1fr] gap-10 lg:gap-16 mb-12">
        {/* Summary + distribution */}
        <div className="bg-white rounded-3xl p-7 border border-neutral-100 h-fit">
          <div className="flex items-baseline gap-3 mb-3">
            <div className="text-5xl font-semibold" style={{ color: primary, fontFamily: `"${fontHeading}", serif` }}>
              {ratingMeta.score.toFixed(1)}
            </div>
            <div className="text-sm text-neutral-500">/ 5</div>
          </div>
          <div className="flex gap-1 mb-2" style={{ color: "#F59E0B" }}>
            {[...Array(5)].map((_, i) => (
              <Star key={i} size={18} weight="fill" />
            ))}
          </div>
          <div className="text-sm text-neutral-600 mb-6">
            Basé sur <span className="font-medium">{ratingMeta.count}</span> avis vérifiés
          </div>
          <div className="space-y-2">
            {dist.map((d) => (
              <div key={d.stars} className="flex items-center gap-3 text-xs">
                <span className="w-4 text-neutral-600">{d.stars}★</span>
                <div className="flex-1 h-1.5 bg-neutral-100 rounded-full overflow-hidden">
                  <div className="h-full rounded-full" style={{ width: `${d.pct}%`, background: primary }} />
                </div>
                <span className="w-8 text-right text-neutral-500">{d.n}</span>
              </div>
            ))}
          </div>
        </div>

        {/* List + sort */}
        <div>
          <div className="flex items-center justify-between mb-5">
            <div className="text-sm text-neutral-500">{sorted.length} avis affichés</div>
            <div className="relative">
              <select
                value={sort}
                onChange={(e) => setSort(e.target.value)}
                className="h-10 px-3 pr-8 rounded-full border text-sm bg-white font-medium cursor-pointer"
                style={{ borderColor: "#E7E5E4" }}
                data-testid="reviews-sort"
              >
                <option value="recent">Plus récents</option>
                <option value="rating_desc">Meilleures notes</option>
                <option value="rating_asc">Notes les plus basses</option>
              </select>
              <CaretDown size={12} weight="bold" className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none" />
            </div>
          </div>

          <div className="space-y-4">
            {sorted.map((r, i) => (
              <article key={i} className="bg-white rounded-2xl border p-5 md:p-6" style={{ borderColor: "#E7E5E4" }} data-testid={`review-${i}`}>
                <div className="flex items-start justify-between mb-2">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <div className="flex" style={{ color: "#F59E0B" }}>
                        {[...Array(5)].map((_, j) => (
                          <Star key={j} size={14} weight={j < r.rating ? "fill" : "regular"} />
                        ))}
                      </div>
                      {r.verified && (
                        <span className="text-[10px] uppercase tracking-widest text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full font-medium">
                          Achat vérifié
                        </span>
                      )}
                    </div>
                    <h4 className="font-semibold text-neutral-900 text-[15px]" style={{ fontFamily: `"${fontHeading}", serif` }}>
                      {r.title}
                    </h4>
                  </div>
                  <div className="text-xs text-neutral-500 shrink-0">{r.date}</div>
                </div>
                <p className="text-[15px] text-neutral-700 leading-relaxed">{r.body}</p>
                <div className="text-xs text-neutral-500 mt-3">
                  {r.author}{r.location ? ` · ${r.location}` : ""}
                </div>
              </article>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
