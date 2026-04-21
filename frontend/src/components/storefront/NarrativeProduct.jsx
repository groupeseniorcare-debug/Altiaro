import React from "react";
import { CheckCircle } from "@phosphor-icons/react";
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
  const { primary, fontHeading } = designAccents(design);

  return (
    <div className="space-y-16 md:space-y-24 mb-20" data-testid="product-narrative">
      {items.map((s, i) => (
        <section
          key={i}
          data-testid={`product-section-${i}`}
          className="grid grid-cols-1 md:grid-cols-12 gap-8 md:gap-12 items-start"
        >
          <div className="md:col-span-5">
            <div
              className="text-[11px] uppercase tracking-[0.25em] mb-3 font-medium"
              style={{ color: primary }}
            >
              {String(i + 1).padStart(2, "0")} · Section
            </div>
            <h2
              className="text-2xl md:text-3xl font-semibold leading-tight"
              style={{ fontFamily: `"${fontHeading}", serif` }}
            >
              {s.title}
            </h2>
          </div>
          <div className="md:col-span-7">
            <p className="text-[16px] md:text-[17px] leading-relaxed text-[#44403C]">
              {s.body}
            </p>
            {s.bullet_points?.length > 0 && (
              <ul className="mt-6 space-y-3">
                {s.bullet_points.map((bp, j) => (
                  <li key={j} className="flex items-start gap-3 text-[15px] text-[#57534E]">
                    <CheckCircle size={18} weight="fill" className="shrink-0 mt-0.5" style={{ color: primary }} />
                    <span>{bp}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </section>
      ))}
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
  const { fontHeading } = designAccents(design);

  return (
    <section className="mb-20 bg-[#FAF7F2] rounded-3xl p-8 md:p-12" data-testid="product-specs">
      <h2
        className="text-2xl md:text-3xl font-semibold mb-8"
        style={{ fontFamily: `"${fontHeading}", serif` }}
      >
        Caractéristiques techniques
      </h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-4">
        {items.map((spec, i) => (
          <div key={i} className="flex items-baseline justify-between border-b border-[#E7E5E4] pb-3">
            <span className="text-sm text-[#78716C]">{spec.label}</span>
            <span className="text-sm font-medium text-[#1C1917] text-right">{spec.value}</span>
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
  const { primary, fontHeading } = designAccents(design);

  return (
    <section className="mb-20" data-testid="product-faq">
      <h2
        className="text-2xl md:text-3xl font-semibold mb-8"
        style={{ fontFamily: `"${fontHeading}", serif` }}
      >
        Questions sur ce produit
      </h2>
      <div className="space-y-3 max-w-3xl">
        {items.map((it, i) => (
          <details
            key={i}
            data-testid={`product-faq-${i}`}
            className="bg-white rounded-xl border border-[#E7E5E4] p-5 group"
          >
            <summary className="cursor-pointer font-medium list-none flex items-center justify-between text-[#1C1917]">
              <span className="pr-4">{it.question}</span>
              <span
                className="w-6 h-6 rounded-full flex items-center justify-center text-xs group-open:rotate-45 transition-transform shrink-0"
                style={{ background: `${primary}14`, color: primary }}
              >
                +
              </span>
            </summary>
            <p className="text-[15px] mt-4 leading-relaxed text-[#57534E]">{it.answer}</p>
          </details>
        ))}
      </div>
    </section>
  );
}
