import React from "react";
import { motion } from "framer-motion";
import { Star } from "@phosphor-icons/react";
import { designAccents } from "./storefrontUtils";

const DEFAULT = [
  { name: "Françoise D.", location: "Lyon · 72 ans", rating: 5, avatar: "https://images.unsplash.com/photo-1559124056-8895c0a1d6b8?w=200&h=200&auto=format&fit=facearea&facepad=3", text: "J'hésitais à commander en ligne à mon âge. Le conseiller a été patient, clair, et la livraison s'est parfaitement passée. Le produit correspond exactement à ce qui était décrit." },
  { name: "Marc & Jeannine L.", location: "Rennes · 78 ans", rating: 5, avatar: "https://images.unsplash.com/photo-1596495577886-d920f1fb7238?w=200&h=200&auto=format&fit=facearea&facepad=3", text: "Nous avons équipé la salle de bain de ma belle-mère. Tout est arrivé en 2 jours, bien emballé, avec des instructions lisibles. Un vrai soulagement." },
  { name: "Hélène P.", location: "Bordeaux · 65 ans", rating: 5, avatar: "https://images.unsplash.com/photo-1581579438747-104c53e7c9e2?w=200&h=200&auto=format&fit=facearea&facepad=3", text: "Service client exceptionnel. J'ai appelé pour un conseil avant d'acheter, on m'a rappelée et orientée sans rien essayer de me vendre. Je recommande vraiment." },
  { name: "Gérard M.", location: "Marseille · 80 ans", rating: 5, avatar: "https://images.unsplash.com/photo-1568602471122-7832951cc4c5?w=200&h=200&auto=format&fit=facearea&facepad=3", text: "Prix équitable, livraison rapide et un vrai suivi. C'est rare aujourd'hui d'être traité comme un client et pas comme un numéro." },
];

function Avatar({ src, name, size = 44, primary, accent, fontHeading }) {
  const [broken, setBroken] = React.useState(false);
  const initials = (name || "").split(" ").map((w) => w[0]).join("").slice(0, 2).toUpperCase();
  const showImg = src && !broken;
  return (
    <div
      className="rounded-full overflow-hidden flex items-center justify-center shrink-0"
      style={{ width: size, height: size, background: accent }}
    >
      {showImg ? (
        <img
          src={src}
          alt={name}
          loading="lazy"
          onError={() => setBroken(true)}
          className="w-full h-full object-cover"
        />
      ) : (
        <span
          className="font-semibold"
          style={{ color: primary, fontFamily: `"${fontHeading}", serif`, fontSize: size * 0.38 }}
        >
          {initials || "·"}
        </span>
      )}
    </div>
  );
}

export function Testimonials({ design, lang }) {
  const { primary, accent, divider, textMuted, textFaint, fontHeading } = designAccents(design);
  const items = design?.testimonials?.items || design?.testimonials;
  const list = Array.isArray(items) && items.length ? items : DEFAULT;
  const hero = list[0];
  const rest = list.slice(1, 4);

  const heroText = typeof hero.text === "string" ? hero.text : hero.quote?.[lang] || hero.quote?.fr || "";

  return (
    <section className="py-24 md:py-36 px-6 bg-white" data-testid="storefront-testimonials">
      <div className="max-w-7xl mx-auto">
        {/* Section header — aligned left, editorial */}
        <div className="flex items-end justify-between flex-wrap gap-6 mb-16 md:mb-20">
          <div>
            <div className="flex items-center gap-3 mb-5">
              <span className="h-px w-10" style={{ background: primary }} />
              <span className="text-[11px] uppercase tracking-[0.4em]" style={{ color: primary }}>
                Témoignages
              </span>
            </div>
            <h2
              className="text-[40px] md:text-[56px] lg:text-[64px] leading-[1.02] tracking-[-0.02em]"
              style={{ fontFamily: `"${fontHeading}", serif`, color: primary }}
            >
              Ils en parlent<br />mieux que nous.
            </h2>
          </div>
          <div className="flex items-center gap-2" style={{ color: textMuted }}>
            <div className="flex" style={{ color: "#F5B800" }}>
              {[...Array(5)].map((_, i) => <Star key={i} size={14} weight="fill" />)}
            </div>
            <span className="text-[13px] font-semibold" style={{ color: primary }}>4.8/5</span>
            <span className="text-[13px]">· 2 143 avis vérifiés</span>
          </div>
        </div>

        {/* Split layout — big hero card + 3 smaller gray cards */}
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-4 md:gap-6">
          <motion.figure
            initial={{ opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-80px" }}
            transition={{ duration: 0.7 }}
            className="lg:col-span-3 p-8 md:p-12 flex flex-col"
            style={{ background: accent, borderRadius: "2px" }}
          >
            <div className="flex mb-6" style={{ color: "#F5B800" }}>
              {[...Array(hero.rating || 5)].map((_, i) => <Star key={i} size={16} weight="fill" />)}
            </div>
            <blockquote
              className="text-[22px] md:text-[28px] leading-[1.35] flex-1"
              style={{ fontFamily: `"${fontHeading}", serif`, color: primary }}
            >
              <span className="text-[60px] opacity-20 mr-1 leading-none" aria-hidden="true">“</span>
              {heroText}
            </blockquote>
            <figcaption
              className="mt-8 pt-6 flex items-center gap-4"
              style={{ borderTop: `1px solid ${divider}` }}
            >
              <Avatar src={hero.avatar} name={hero.name} size={52} primary={primary} accent="#E5E5E5" fontHeading={fontHeading} />
              <div>
                <div className="text-[14px] font-semibold" style={{ color: primary }}>{hero.name}</div>
                <div
                  className="text-[11px] uppercase tracking-[0.2em] mt-1"
                  style={{ color: textFaint }}
                >
                  {hero.location}
                </div>
              </div>
            </figcaption>
          </motion.figure>

          <div className="lg:col-span-2 grid grid-cols-1 gap-4 md:gap-6">
            {rest.map((t, i) => {
              const text = typeof t.text === "string" ? t.text : t.quote?.[lang] || t.quote?.fr || "";
              return (
                <motion.figure
                  key={i}
                  initial={{ opacity: 0, y: 24 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true, margin: "-60px" }}
                  transition={{ duration: 0.6, delay: 0.1 * i }}
                  className="p-6 md:p-7"
                  style={{ background: accent, borderRadius: "2px" }}
                  data-testid={`testimonial-${i + 1}`}
                >
                  <div className="flex mb-3" style={{ color: "#F5B800" }}>
                    {[...Array(t.rating || 5)].map((_, j) => <Star key={j} size={13} weight="fill" />)}
                  </div>
                  <blockquote className="text-[14px] leading-relaxed line-clamp-4" style={{ color: primary }}>
                    {text}
                  </blockquote>
                  <figcaption className="mt-4 flex items-center gap-3">
                    <Avatar src={t.avatar} name={t.name} size={36} primary={primary} accent="#E5E5E5" fontHeading={fontHeading} />
                    <div>
                      <div className="text-[12.5px] font-semibold leading-tight" style={{ color: primary }}>{t.name}</div>
                      <div className="text-[11px] mt-0.5" style={{ color: textMuted }}>{t.location}</div>
                    </div>
                  </figcaption>
                </motion.figure>
              );
            })}
          </div>
        </div>
      </div>
    </section>
  );
}
