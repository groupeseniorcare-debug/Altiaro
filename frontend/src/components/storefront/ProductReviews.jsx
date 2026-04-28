import React, { useState } from "react";
import { Star, CaretDown } from "@phosphor-icons/react";
import { designAccents } from "./storefrontUtils";
import { t } from "../../lib/i18n";

/**
 * Product reviews — monochrome editorial.
 *
 * Phase 2.6 Tâche E — enrichi avec :
 *   - avatar (portrait IA Nano Banana) depuis `r.avatar_url` ou via mapping
 *     sur `design.testimonials_premium` quand `product.reviews` n'a pas
 *     d'avatars dédiés.
 *   - photo lifestyle "client" via `r.photo_url` (scène domestique
 *     Nano Banana, produit visible naturellement dans le décor).
 *
 * Source de données :
 *   - product.reviews (priorité) — chaque review = {author, location, date,
 *     rating, title, body, verified, avatar_url?, photo_url?}.
 *   - product.review_photos = [url, url, ...] — pool des 4-6 photos lifestyle
 *     générées par services/review_photos.py (utilisé en fallback si les
 *     reviews n'ont pas de photo individuelle).
 *   - design.testimonials_premium = [{name, avatar_url, ...}] — fallback
 *     pool d'avatars (3 portraits IA générés au lancement).
 */
export default function ProductReviews({ product, design, lang = "fr" }) {
  const [sort, setSort] = useState("recent");
  const { primary, accent, divider, textMuted, textFaint, fontHeading } = designAccents(design);

  const fallbackReviews = [
    { author: "Françoise D.", location: "Lyon", date: "Il y a 2 semaines", rating: 5, title: "Exactement ce qu'il me fallait", body: "Commandé pour ma mère de 82 ans. Elle l'utilise tous les jours sans difficulté. Le conseiller m'a bien orientée au téléphone, je recommande.", verified: true },
    { author: "Marc L.", location: "Rennes", date: "Il y a 1 mois", rating: 5, title: "Qualité au-dessus de mes attentes", body: "Livraison rapide, produit bien protégé, finition impeccable. Le manuel est clair et les conseils utiles. Rien à redire.", verified: true },
    { author: "Hélène P.", location: "Bordeaux", date: "Il y a 1 mois", rating: 4, title: "Très satisfaite", body: "Un petit point de confort à améliorer selon moi, mais globalement très content du produit. Le SAV a été à l'écoute quand j'ai eu une question.", verified: true },
    { author: "Jean-Paul M.", location: "Toulouse", date: "Il y a 2 mois", rating: 5, title: "Parfait pour mon papa", body: "Simple à utiliser, robuste, on sent qu'il est pensé pour durer. Pas de gadgets inutiles. Merci pour l'accompagnement.", verified: true },
  ];

  // Reviews source — limit to 6 max (Phase 2.6 Tâche E)
  const baseReviews = (product?.reviews?.length ? product.reviews : fallbackReviews).slice(0, 6);

  // Avatar pool (testimonials_premium) — pour reviews sans avatar dédié
  const avatarPool = (design?.testimonials_premium || [])
    .map((t) => t?.avatar_url || t?.photo_url)
    .filter(Boolean);

  // Lifestyle photo pool (product.review_photos) — pour enrichir 1 review/2
  const photoPool = Array.isArray(product?.review_photos) ? product.review_photos : [];

  const reviews = baseReviews.map((r, i) => ({
    ...r,
    avatar_url: r.avatar_url || avatarPool[i % Math.max(1, avatarPool.length)] || null,
    // 1 photo lifestyle ~1 review sur 2 pour ne pas alourdir
    photo_url: r.photo_url || (i % 2 === 0 ? photoPool[Math.floor(i / 2) % Math.max(1, photoPool.length)] : null) || null,
  }));

  const ratingMeta = product?.rating || { score: 4.8, count: reviews.length };

  const dist = [5, 4, 3, 2, 1].map((stars) => {
    const n = reviews.filter((r) => r.rating === stars).length;
    return { stars, n, pct: reviews.length ? Math.round((n / reviews.length) * 100) : 0 };
  });

  const sorted = [...reviews].sort((a, b) => {
    if (sort === "rating_desc") return b.rating - a.rating;
    if (sort === "rating_asc") return a.rating - b.rating;
    return 0;
  });

  return (
    <section className="py-24 md:py-32" style={{ borderTop: `1px solid ${divider}` }} data-testid="product-reviews">
      <div className="mb-14 md:mb-20">
        <div className="flex items-center gap-3 mb-5">
          <span className="h-px w-8" style={{ background: primary }} />
          <span className="text-[10px] uppercase tracking-[0.4em]" style={{ color: primary }}>Avis clients</span>
        </div>
        <h2
          className="text-[30px] md:text-[48px] leading-[1.05] tracking-[-0.015em]"
          style={{ fontFamily: `"${fontHeading}", serif`, color: primary }}
        >
          Ils ont acheté ce produit.
        </h2>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[340px_1fr] gap-10 lg:gap-16">
        {/* Summary — grey card */}
        <div
          className="p-7 h-fit lg:sticky lg:top-28"
          style={{ background: accent, borderRadius: "2px" }}
        >
          <div className="flex items-baseline gap-3 mb-3">
            <div className="text-[60px] font-normal leading-none" style={{ color: primary, fontFamily: `"${fontHeading}", serif` }}>
              {ratingMeta.score.toFixed(1)}
            </div>
            <div className="text-[13px]" style={{ color: textMuted }}>/ 5</div>
          </div>
          <div className="flex gap-1 mb-3" style={{ color: "#F5B800" }}>
            {[...Array(5)].map((_, i) => <Star key={i} size={17} weight="fill" />)}
          </div>
          <div className="text-[13px] mb-7" style={{ color: textMuted }}>
            Basé sur <span className="font-semibold" style={{ color: primary }}>{ratingMeta.count}</span> {t(lang, "testimonials_verified_reviews")}
          </div>
          <div className="space-y-2.5">
            {dist.map((d) => (
              <div key={d.stars} className="flex items-center gap-3 text-[12px]">
                <span className="w-6 tabular-nums" style={{ color: primary }}>{d.stars}★</span>
                <div className="flex-1 h-1.5 overflow-hidden" style={{ background: "#E5E5E5", borderRadius: "2px" }}>
                  <div className="h-full" style={{ width: `${d.pct}%`, background: primary, borderRadius: "2px" }} />
                </div>
                <span className="w-8 text-right tabular-nums" style={{ color: textMuted }}>{d.n}</span>
              </div>
            ))}
          </div>
        </div>

        {/* List */}
        <div>
          <div className="flex items-center justify-between mb-6">
            <div className="text-[13px]" style={{ color: textMuted }}>{sorted.length} {t(lang, "testimonials_verified_reviews")}</div>
            <div className="relative">
              <select
                value={sort}
                onChange={(e) => setSort(e.target.value)}
                className="h-10 px-4 pr-9 text-[13px] bg-white font-medium cursor-pointer outline-none"
                style={{ border: `1px solid ${divider}`, color: primary, borderRadius: "2px" }}
                data-testid="reviews-sort"
              >
                <option value="recent">Plus récents</option>
                <option value="rating_desc">Meilleures notes</option>
                <option value="rating_asc">Notes les plus basses</option>
              </select>
              <CaretDown size={11} weight="bold" className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none" style={{ color: primary }} />
            </div>
          </div>

          <div style={{ borderTop: `1px solid ${divider}` }}>
            {sorted.map((r, i) => (
              <article
                key={i}
                className="py-7"
                style={{ borderBottom: `1px solid ${divider}` }}
                data-testid={`review-${i}`}
              >
                <div className="flex items-start gap-4 mb-3">
                  {/* Phase 2.6 Tâche E — Avatar IA rond, fallback initiale */}
                  {r.avatar_url ? (
                    <img
                      src={r.avatar_url}
                      alt={r.author}
                      loading="lazy"
                      className="w-12 h-12 rounded-full object-cover shrink-0 ring-1"
                      style={{ ringColor: divider }}
                    />
                  ) : (
                    <div
                      className="w-12 h-12 rounded-full flex items-center justify-center shrink-0 text-[16px]"
                      style={{ background: accent, color: primary, fontFamily: `"${fontHeading}", serif` }}
                    >
                      {(r.author || "?").charAt(0)}
                    </div>
                  )}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3 mb-2 flex-wrap">
                      <div className="flex" style={{ color: "#F5B800" }}>
                        {[...Array(5)].map((_, j) => (
                          <Star key={j} size={14} weight={j < r.rating ? "fill" : "regular"} />
                        ))}
                      </div>
                      {r.verified && (
                        <span
                          className="text-[10px] uppercase tracking-[0.25em] px-2 py-1 font-semibold"
                          style={{ background: accent, color: primary, borderRadius: "2px" }}
                        >
                          {t(lang, "review_verified_purchase")}
                        </span>
                      )}
                      <div className="text-[11px] uppercase tracking-[0.25em] ml-auto shrink-0" style={{ color: textFaint }}>{r.date}</div>
                    </div>
                    <h4 className="text-[17px] md:text-[19px] leading-snug" style={{ fontFamily: `"${fontHeading}", serif`, color: primary }}>
                      {r.title}
                    </h4>
                  </div>
                </div>
                <p className="text-[14.5px] leading-relaxed" style={{ color: textMuted }}>{r.body}</p>

                {/* Phase 2.6 Tâche E — Photo lifestyle "client" (Nano Banana,
                    scène domestique avec produit visible naturellement).
                    1 photo ~1 review sur 2 pour aérer la page. */}
                {r.photo_url ? (
                  <div className="mt-5 max-w-md">
                    <img
                      src={r.photo_url}
                      alt={`Photo client — ${r.author}`}
                      loading="lazy"
                      className="w-full aspect-[4/3] object-cover"
                      style={{ borderRadius: "2px", border: `1px solid ${divider}` }}
                    />
                  </div>
                ) : null}

                <div className="text-[12px] mt-4 flex items-center gap-2" style={{ color: textMuted }}>
                  <span className="font-semibold" style={{ color: primary }}>{r.author}</span>
                  {r.location && <><span className="opacity-40">·</span><span>{r.location}</span></>}
                </div>
              </article>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
