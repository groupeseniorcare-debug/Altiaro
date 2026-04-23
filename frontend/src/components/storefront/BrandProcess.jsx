import React from "react";
import { motion } from "framer-motion";
import { ShieldCheck, HandsClapping, Leaf, Tree } from "@phosphor-icons/react";
import { designAccents } from "./storefrontUtils";

const DEFAULT_STEPS = [
  {
    icon: "Leaf",
    kicker: "01 · Sélection",
    title: "Matières nobles, sans compromis",
    body: "Chaque tissu, chaque bois est validé par notre équipe avant la moindre production. Nous refusons les matières issues de filières opaques.",
  },
  {
    icon: "HandsClapping",
    kicker: "02 · Fabrication",
    title: "Ateliers européens, savoir-faire préservé",
    body: "Nos partenaires sont installés en France, Italie, Portugal. Des ateliers qui ont du sens — certifiés sur les conditions de travail et l'origine des matériaux.",
  },
  {
    icon: "ShieldCheck",
    kicker: "03 · Contrôle",
    title: "4 niveaux de contrôle qualité",
    body: "Chaque pièce est testée avant expédition : conformité, résistance, confort, finitions. Si elle ne passe pas, elle repart en atelier — pas chez vous.",
  },
  {
    icon: "Tree",
    kicker: "04 · Logistique",
    title: "Livraison maîtrisée, zéro surprise",
    body: "Expédition depuis notre entrepôt en Île-de-France, emballage 100% recyclable, installation à domicile sur les produits volumineux.",
  },
];

const ICONS = { Leaf, HandsClapping, ShieldCheck, Tree };

/**
 * BrandProcess — editorial "Made by us" section. Explains how products are
 * selected, crafted and shipped. Monochrome: white canvas, black ink,
 * 4 gray cards with numbered kickers. No portrait, no stock photo of a woman.
 */
export default function BrandProcess({ design, lang = "fr" }) {
  const { primary, accent, textMuted, fontHeading } = designAccents(design);
  const steps = (design?.brand_process && design.brand_process.length === 4)
    ? design.brand_process : DEFAULT_STEPS;

  return (
    <section
      className="py-24 md:py-36 px-6 bg-white"
      data-testid="storefront-brand-process"
      id="process"
    >
      <div className="max-w-7xl mx-auto">
        <div className="flex items-end justify-between flex-wrap gap-6 mb-14 md:mb-20">
          <div className="max-w-xl">
            <div className="flex items-center gap-3 mb-5">
              <span className="h-px w-10" style={{ background: primary }} />
              <span className="text-[11px] uppercase tracking-[0.4em]" style={{ color: primary }}>
                Notre fabrication
              </span>
            </div>
            <h2
              className="text-[40px] md:text-[56px] lg:text-[64px] leading-[1.02] tracking-[-0.02em]"
              style={{ fontFamily: `"${fontHeading}", serif`, color: primary }}
            >
              De la sélection<br />à votre porte.
            </h2>
            <p className="text-[15px] mt-6 max-w-lg leading-relaxed" style={{ color: textMuted }}>
              Nous contrôlons chaque étape — sélection des matières, fabrication, qualité, logistique.
              Pas de sous-traitance opaque, pas de raccourci.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6">
          {steps.slice(0, 4).map((s, i) => {
            const Icon = ICONS[s.icon] || ShieldCheck;
            return (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 24 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-60px" }}
                transition={{ duration: 0.6, delay: 0.08 * i }}
                className="p-8 md:p-10 flex flex-col"
                style={{ background: accent, borderRadius: "2px" }}
                data-testid={`process-${i}`}
              >
                <div
                  className="text-[11px] tabular-nums tracking-[0.3em] uppercase mb-8"
                  style={{ color: textMuted }}
                >
                  {s.kicker}
                </div>
                <Icon size={28} weight="thin" style={{ color: primary }} className="mb-5" />
                <div
                  className="text-[20px] md:text-[22px] leading-snug tracking-tight mb-3"
                  style={{ fontFamily: `"${fontHeading}", serif`, color: primary }}
                >
                  {s.title}
                </div>
                <p className="text-[14px] leading-relaxed" style={{ color: textMuted }}>
                  {s.body}
                </p>
              </motion.div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
