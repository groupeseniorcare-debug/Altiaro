import React from "react";
import { Check } from "@phosphor-icons/react";
import { designAccents } from "./storefrontUtils";

export function NarrativeSections({ sections, design }) {
  const fallback = [
    {
      title: "Pensé pour un usage quotidien",
      body: "Nous avons conçu ce produit en collaboration avec des seniors et des ergothérapeutes. Le résultat : un objet pratique, robuste, qui se fond naturellement dans l'environnement du quotidien, sans jamais ressembler à du matériel médical froid.",
      bullet_points: [
        "Testé en conditions réelles par une équipe de 12 utilisateurs seniors",
        "Matériaux durables sélectionnés pour résister à des années d'usage",
        "Finitions soignées — rien ne dépasse, tout est pensé dans le détail",
      ],
    },
    {
      title: "Un service qui va au-delà du produit",
      body: "Chez nous, acheter ne s'arrête pas au paiement. Nous accompagnons chaque achat : livraison avec prise de rendez-vous possible, installation sur demande, accompagnement à la prise en main, SAV humain joignable sans attendre 20 minutes au téléphone.",
      bullet_points: [
        "Livraison offerte et suivie par SMS + email",
        "Installation possible à domicile (sur les produits volumineux)",
        "Garantie 2 ans + retour gratuit 14 jours",
      ],
    },
  ];
  const items = (Array.isArray(sections) && sections.length > 0) ? sections : fallback;
  const { primary, accent, divider, textMuted, fontHeading } = designAccents(design);

  return (
    <div className="space-y-20 md:space-y-28 mb-24" data-testid="product-narrative">
      {items.map((s, i) => {
        const hasImage = !!s.image;
        const imageLeft = i % 2 === 0;
        return (
          <section
            key={i}
            data-testid={`product-section-${i}`}
            className={`grid grid-cols-1 gap-10 md:gap-16 items-center ${hasImage ? "md:grid-cols-2" : "md:grid-cols-12"}`}
          >
            {hasImage && imageLeft && (
              <div className="md:order-1">
                <div
                  className="aspect-[4/3] overflow-hidden"
                  style={{ background: accent, borderRadius: "2px" }}
                >
                  <img src={s.image} alt={s.title || `Section ${i + 1}`} loading="lazy"
                    className="w-full h-full object-cover" />
                </div>
              </div>
            )}
            <div className={hasImage ? "md:order-2" : "md:col-span-5"}>
              <div className="flex items-center gap-3 mb-5">
                <span className="h-px w-8" style={{ background: primary }} />
                <span className="text-[10px] uppercase tracking-[0.35em] font-medium" style={{ color: primary }}>
                  {String(i + 1).padStart(2, "0")} · Chapitre
                </span>
              </div>
              <h2
                className="text-[30px] md:text-[44px] leading-[1.05] tracking-[-0.015em]"
                style={{ fontFamily: `"${fontHeading}", serif`, color: primary }}
              >
                {s.title}
              </h2>
              {hasImage && (
                <p className="mt-6 text-[15px] md:text-[16px] leading-[1.7]" style={{ color: textMuted }}>
                  {s.body}
                </p>
              )}
            </div>
            {!hasImage && (
              <div className="md:col-span-7">
                <p className="text-[16px] md:text-[17px] leading-[1.7]" style={{ color: textMuted }}>
                  {s.body}
                </p>
                {s.bullet_points?.length > 0 && (
                  <ul className="mt-8 p-6 space-y-3" style={{ background: accent, borderRadius: "2px" }}>
                    {s.bullet_points.map((bp, j) => (
                      <li key={j} className="flex items-start gap-3 text-[14px]" style={{ color: "#262626" }}>
                        <Check size={14} weight="bold" className="shrink-0 mt-[4px]" style={{ color: primary }} />
                        <span>{bp}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}
            {hasImage && !imageLeft && (
              <div className="md:order-1">
                <div
                  className="aspect-[4/3] overflow-hidden"
                  style={{ background: accent, borderRadius: "2px" }}
                >
                  <img src={s.image} alt={s.title || `Section ${i + 1}`} loading="lazy"
                    className="w-full h-full object-cover" />
                </div>
              </div>
            )}
          </section>
        );
      })}
      {/* divider kept in scope for interface parity */}
      {false && <span style={{ background: divider }} />}
    </div>
  );
}

export function TechSpecs({ specs, design }) {
  const fallback = [
    { label: "Dimensions", value: "80 × 85 × 105 cm (L×l×H)" },
    { label: "Poids", value: "12,5 kg" },
    { label: "Charge maximale", value: "130 kg" },
    { label: "Matériaux", value: "Acier renforcé, mousse haute densité, tissu anti-taches" },
    { label: "Garantie", value: "2 ans pièces et main d'œuvre" },
    { label: "Norme CE", value: "Oui, certifié UE" },
    { label: "Fabrication", value: "Assemblé en France" },
    { label: "Entretien", value: "Housse déhoussable, lavable à 30°" },
  ];
  const items = (Array.isArray(specs) && specs.length > 0) ? specs : fallback;
  const { primary, accent, textMuted, fontHeading } = designAccents(design);

  return (
    <section className="mb-24" data-testid="product-specs">
      <div className="flex items-end justify-between flex-wrap gap-4 mb-10">
        <div>
          <div className="flex items-center gap-3 mb-5">
            <span className="h-px w-8" style={{ background: primary }} />
            <span className="text-[10px] uppercase tracking-[0.4em]" style={{ color: primary }}>
              Fiche technique
            </span>
          </div>
          <h2
            className="text-[30px] md:text-[44px] leading-[1.05] tracking-[-0.015em]"
            style={{ fontFamily: `"${fontHeading}", serif`, color: primary }}
          >
            Caractéristiques précises
          </h2>
        </div>
        <div className="text-[11px] uppercase tracking-[0.3em]" style={{ color: textMuted }}>
          {items.length} caractéristique{items.length > 1 ? "s" : ""} vérifiée{items.length > 1 ? "s" : ""}
        </div>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 md:gap-4">
        {items.map((spec, i) => (
          <div
            key={i}
            className="p-6"
            style={{ background: accent, borderRadius: "2px" }}
            data-testid={`spec-${i}`}
          >
            <div className="text-[10px] uppercase tracking-[0.28em] mb-3" style={{ color: textMuted }}>
              {spec.label}
            </div>
            <div
              className="text-[16px] leading-snug"
              style={{ fontFamily: `"${fontHeading}", serif`, color: primary }}
            >
              {spec.value}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

export function ProductFAQ({ faq, design }) {
  const fallback = [
    { question: "Quel est le délai de livraison ?", answer: "Expédition sous 24h ouvrées (commandes avant 14h). Réception en 48 à 72h en France métropolitaine, avec prise de rendez-vous pour les gros volumes. Livraison offerte dès 50 € d'achat." },
    { question: "Est-ce que l'installation est incluse ?", answer: "Pour les produits volumineux, un technicien peut se déplacer pour l'installation et la prise en main. Ce service est optionnel et détaillé lors de la commande." },
    { question: "Puis-je le retourner si ça ne me convient pas ?", answer: "Oui, vous disposez de 14 jours à compter de la réception pour changer d'avis. Les frais de retour sont à notre charge (étiquette prépayée fournie). Remboursement intégral sous 5 jours ouvrés." },
    { question: "La garantie couvre quoi exactement ?", answer: "2 ans pièces et main d'œuvre, en cas de défaut de fabrication. Pour en bénéficier, il suffit de nous contacter avec votre numéro de commande : nous organisons le retour et le remplacement à nos frais." },
    { question: "Ce produit est-il remboursé par la Sécurité sociale ou la mutuelle ?", answer: "Certains équipements sont pris en charge partiellement au titre de la LPPR. Contactez-nous avec votre numéro de Sécu et votre mutuelle : nous établissons un devis et vous aidons à monter le dossier." },
  ];
  const items = (Array.isArray(faq) && faq.length > 0) ? faq : fallback;
  const { primary, accent, divider, textMuted, fontHeading } = designAccents(design);

  return (
    <section className="mb-24" data-testid="product-faq">
      <div className="flex items-center gap-3 mb-5">
        <span className="h-px w-8" style={{ background: primary }} />
        <span className="text-[10px] uppercase tracking-[0.4em]" style={{ color: primary }}>FAQ produit</span>
      </div>
      <h2
        className="text-[30px] md:text-[44px] leading-[1.05] tracking-[-0.015em] mb-10"
        style={{ fontFamily: `"${fontHeading}", serif`, color: primary }}
      >
        Tout ce que vous voulez savoir.
      </h2>
      <div className="max-w-3xl" style={{ borderTop: `1px solid ${divider}` }}>
        {items.map((it, i) => (
          <details
            key={i}
            data-testid={`product-faq-${i}`}
            className="group py-6"
            style={{ borderBottom: `1px solid ${divider}` }}
          >
            <summary
              className="cursor-pointer list-none flex items-center justify-between gap-5 text-[17px] md:text-[18px]"
              style={{ fontFamily: `"${fontHeading}", serif`, color: primary }}
            >
              <span>{it.question}</span>
              <span
                className="w-9 h-9 flex items-center justify-center shrink-0 text-lg group-open:rotate-45 transition-transform"
                style={{ background: accent, color: primary, borderRadius: "2px" }}
              >
                +
              </span>
            </summary>
            <p className="text-[15px] mt-4 leading-relaxed pr-14" style={{ color: textMuted }}>{it.answer}</p>
          </details>
        ))}
      </div>
    </section>
  );
}
