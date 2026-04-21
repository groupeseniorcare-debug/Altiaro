import React from "react";
import { designAccents } from "./storefrontUtils";

export function FAQSection({ design, lang }) {
  const items = design?.faq?.items || design?.faq;
  const finalItems = Array.isArray(items) && items.length > 0 ? items : [
    { question: "Sous quel délai serai-je livré ?", answer: "Les commandes sont expédiées sous 24h ouvrées. Vous recevez votre colis en 48 à 72h partout en France métropolitaine, avec un numéro de suivi dès l'expédition." },
    { question: "Puis-je retourner un produit qui ne me convient pas ?", answer: "Oui, vous avez 14 jours à réception pour changer d'avis. Les frais de retour sont à notre charge et vous êtes remboursé sous 5 jours après réception." },
    { question: "Comment puis-je contacter un conseiller ?", answer: "Par téléphone du lundi au vendredi de 9h à 18h, ou par email 7j/7 — nous répondons en moyenne en 2h ouvrées. Pas de chatbot : un vrai humain à votre écoute." },
    { question: "Les produits sont-ils remboursés par la Sécurité sociale ?", answer: "Certains équipements sont pris en charge partiellement par la Sécu ou par votre mutuelle (LPPR). Demandez-nous un devis, nous vous aiderons à constituer le dossier." },
    { question: "Proposez-vous l'installation à domicile ?", answer: "Sur les produits volumineux (fauteuils releveurs, lits médicaux), un technicien peut se déplacer pour l'installation et la prise en main. Détail lors de la commande." },
    { question: "Mes données personnelles sont-elles protégées ?", answer: "Nous ne partageons jamais vos coordonnées avec des tiers à des fins commerciales. Nos serveurs sont hébergés en France, conforme RGPD." },
  ];
  const { primary, fontHeading } = designAccents(design);

  return (
    <section className="max-w-3xl mx-auto px-6 md:px-10 py-20 md:py-28">
      <div className="text-center mb-12">
        <div
          className="text-[11px] uppercase tracking-[0.25em] mb-3 font-medium"
          style={{ color: primary }}
        >
          FAQ
        </div>
        <h2
          className="text-3xl md:text-4xl font-semibold"
          style={{ fontFamily: `"${fontHeading}", serif` }}
        >
          Questions fréquentes
        </h2>
      </div>
      <div className="space-y-3">
        {finalItems.map((it, i) => {
          const q = typeof it.question === "string"
            ? it.question
            : (it.q?.[lang] || it.q?.fr || "");
          const a = typeof it.answer === "string"
            ? it.answer
            : (it.a?.[lang] || it.a?.fr || "");
          return (
            <details
              key={i}
              className="bg-white rounded-xl border border-[#E7E5E4] p-5 group hover:border-[#D6D3D1] transition"
              data-testid={`faq-${i}`}
            >
              <summary className="cursor-pointer font-medium list-none flex items-center justify-between text-[#1C1917]">
                <span className="pr-4">{q}</span>
                <span
                  className="w-6 h-6 rounded-full flex items-center justify-center text-xs group-open:rotate-45 transition-transform shrink-0"
                  style={{ background: `${primary}14`, color: primary }}
                >
                  +
                </span>
              </summary>
              <p className="text-[15px] mt-4 leading-relaxed" style={{ color: "#57534E" }}>
                {a}
              </p>
            </details>
          );
        })}
      </div>
    </section>
  );
}
