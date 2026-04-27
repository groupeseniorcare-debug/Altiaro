/**
 * Lot I (Phase 2.1) Fix I3 — ProductUsps amplifié.
 *
 * Remplace l'ex-section "Est-ce fait pour vous" (`<BestForNotFor>`) par
 * 4 cards verticales narratives — fond ivoire #F5F2EB, icône Lucide en haut,
 * titre Cormorant, description sans-serif. Lecture stricte de `product.usps`
 * généré par Haiku 4.5 dans `services/product_content_ai.py`.
 *
 * Si `product.usps` n'a pas exactement 4 items valides → la section ne
 * s'affiche pas (pas de fallback générique : seul l'IA produit-spécifique
 * mérite cette place narrative).
 *
 * Composant partagé → propagation auto sur tous les sites.
 */
import React from "react";
import { motion } from "framer-motion";
import * as LucideIcons from "lucide-react";
import { Sparkles } from "lucide-react";
import { designAccents } from "./storefrontUtils";

/**
 * Resolve a Lucide icon component by its PascalCase name.
 * Falls back to `Sparkles` when the name is unknown so the UI never breaks.
 */
function resolveLucideIcon(name) {
  if (!name) return Sparkles;
  const Icon = LucideIcons[name];
  return Icon || Sparkles;
}

export default function ProductUsps({ usps, design, lang = "fr" }) {
  const list = Array.isArray(usps) ? usps.filter((u) => u && u.title).slice(0, 4) : [];
  if (list.length < 4) return null;

  const { primary, fontHeading } = designAccents(design);

  return (
    <section
      className="py-20 md:py-28"
      data-testid="product-usps-narrative"
    >
      <div className="max-w-7xl mx-auto px-6">
        {/* Eyebrow + Title */}
        <div className="mb-12 md:mb-16 max-w-2xl">
          <div className="flex items-center gap-3 mb-5">
            <span className="h-px w-10" style={{ background: primary }} />
            <span
              className="text-[11px] uppercase tracking-[0.4em] font-medium"
              style={{ color: primary }}
            >
              Conçu avec exigence
            </span>
          </div>
          <h2
            className="text-[34px] md:text-[44px] lg:text-[52px] leading-[1.05] tracking-[-0.02em]"
            style={{
              fontFamily: `"${fontHeading}", Georgia, serif`,
              color: "#0A0A0A",
              fontWeight: 400,
            }}
          >
            Ce qui rend ce produit&nbsp;singulier.
          </h2>
        </div>

        {/* 4 vertical cards — ivory background, Lucide icon top */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 md:gap-5">
          {list.map((usp, i) => {
            const Icon = resolveLucideIcon(usp.icon);
            return (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 24 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-40px" }}
                transition={{ duration: 0.6, delay: i * 0.08, ease: [0.22, 1, 0.36, 1] }}
                className="bg-[#F5F2EB] p-7 md:p-8 flex flex-col"
                style={{ borderRadius: "2px", minHeight: "260px" }}
                data-testid={`product-usp-card-${i}`}
              >
                {/* Icon — large, hairline, top */}
                <div
                  className="w-12 h-12 mb-7 flex items-center justify-center"
                  style={{
                    background: "white",
                    borderRadius: "2px",
                    border: "1px solid #E7E5E4",
                  }}
                >
                  <Icon size={20} strokeWidth={1.5} color="#0A0A0A" aria-hidden="true" />
                </div>

                {/* Title — Cormorant, 1-2 lines */}
                <h3
                  className="text-[20px] md:text-[22px] leading-[1.2] mb-3 tracking-[-0.005em]"
                  style={{
                    fontFamily: `"${fontHeading}", Georgia, serif`,
                    color: "#0A0A0A",
                    fontWeight: 500,
                  }}
                >
                  {usp.title}
                </h3>

                {/* Description — sans-serif, calm */}
                <p className="text-[13.5px] leading-[1.65]" style={{ color: "#525252" }}>
                  {usp.description}
                </p>
              </motion.div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
