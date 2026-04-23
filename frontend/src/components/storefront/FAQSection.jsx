import React from "react";
import { designAccents } from "./storefrontUtils";

export function FAQSection({ design, lang }) {
  const { primary, accent, divider, textMuted, fontHeading } = designAccents(design);
  const items = design?.faq?.items || design?.faq;
  const list = Array.isArray(items) && items.length ? items : [
    { question: "Sous quel délai serai-je livré ?", answer: "Les commandes sont expédiées sous 24h ouvrées. Vous recevez votre colis en 48 à 72h partout en France métropolitaine, avec un numéro de suivi dès l'expédition." },
    { question: "Puis-je retourner un produit qui ne me convient pas ?", answer: "Oui, vous avez 14 jours à réception pour changer d'avis. Les frais de retour sont à notre charge et vous êtes remboursé sous 5 jours après réception." },
    { question: "Comment puis-je contacter un conseiller ?", answer: "Par téléphone du lundi au vendredi de 9h à 18h, ou par email 7j/7 — nous répondons en moyenne en 2h ouvrées. Pas de chatbot : un vrai humain à votre écoute." },
    { question: "Les produits sont-ils remboursés par la Sécurité sociale ?", answer: "Certains équipements sont pris en charge partiellement par la Sécu ou par votre mutuelle (LPPR). Demandez-nous un devis, nous vous aiderons à constituer le dossier." },
    { question: "Proposez-vous l'installation à domicile ?", answer: "Sur les produits volumineux (fauteuils releveurs, lits médicaux), un technicien peut se déplacer pour l'installation et la prise en main. Détail lors de la commande." },
    { question: "Mes données personnelles sont-elles protégées ?", answer: "Nous ne partageons jamais vos coordonnées avec des tiers à des fins commerciales. Nos serveurs sont hébergés en France, conforme RGPD." },
  ];

  return (
    <section className="py-24 md:py-36 px-6 bg-white" data-testid="storefront-faq" id="faq">
      <div className="max-w-5xl mx-auto grid grid-cols-1 lg:grid-cols-[auto_1fr] gap-12 lg:gap-20 items-start">
        {/* Sticky section title on the left */}
        <div className="lg:sticky lg:top-32 lg:w-64">
          <div className="flex items-center gap-3 mb-5">
            <span className="h-px w-10" style={{ background: primary }} />
            <span className="text-[11px] uppercase tracking-[0.4em]" style={{ color: primary }}>
              FAQ
            </span>
          </div>
          <h2
            className="text-[36px] md:text-[48px] leading-[1.02] tracking-[-0.02em]"
            style={{ fontFamily: `"${fontHeading}", serif`, color: primary }}
          >
            Questions<br />fréquentes.
          </h2>
          <p className="mt-4 text-[13px]" style={{ color: textMuted }}>
            Une question qui n'est pas ci-dessous ? Notre équipe répond en 2h ouvrées en moyenne.
          </p>
        </div>

        {/* Question list */}
        <div className="flex-1">
          <div style={{ borderTop: `1px solid ${divider}` }}>
            {list.map((it, i) => {
              const q = typeof it.question === "string" ? it.question : (it.q?.[lang] || it.q?.fr || "");
              const a = typeof it.answer === "string" ? it.answer : (it.a?.[lang] || it.a?.fr || "");
              return (
                <details
                  key={i}
                  className="group py-6"
                  style={{ borderBottom: `1px solid ${divider}` }}
                  data-testid={`faq-${i}`}
                >
                  <summary
                    className="cursor-pointer list-none flex items-center justify-between gap-6 text-[17px] md:text-[19px]"
                    style={{ fontFamily: `"${fontHeading}", serif`, color: primary }}
                  >
                    <span>{q}</span>
                    <span
                      className="w-9 h-9 rounded-full flex items-center justify-center shrink-0 text-lg group-open:rotate-45 transition-transform"
                      style={{ background: accent, color: primary }}
                    >
                      +
                    </span>
                  </summary>
                  <p className="text-[15px] mt-4 leading-relaxed pr-14" style={{ color: textMuted }}>
                    {a}
                  </p>
                </details>
              );
            })}
          </div>
        </div>
      </div>
    </section>
  );
}
