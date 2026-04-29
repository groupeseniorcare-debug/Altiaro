import React from "react";
import PlatformLegalLayout from "../components/PlatformLegalLayout";
import { ALTIARO_COMPANY } from "../lib/altiaroLegal";

export default function PlatformLegalLivraison() {
  return (
    <PlatformLegalLayout title="Politique de livraison" eyebrow="Altiaro · Légal">
      <h2>Préambule</h2>
      <p>
        Altiaro est une plateforme SaaS qui héberge des boutiques en ligne créées et exploitées
        par des concepteurs indépendants. Chaque boutique hébergée définit, dans ses propres
        conditions générales, les modalités précises d'expédition (transporteurs, délais
        régionaux, frais de port). La présente politique décrit le cadre commun applicable.
      </p>

      <h2>1. Zones de livraison</h2>
      <p>
        Les boutiques hébergées sur la plateforme Altiaro livrent prioritairement en France
        métropolitaine, dans l'Union européenne et au Royaume-Uni. La liste exacte des pays
        desservis et les frais associés sont précisés sur chaque fiche produit avant validation
        de la commande, ainsi qu'à l'étape de paiement.
      </p>

      <h2>2. Délais de livraison</h2>
      <ul>
        <li>
          <strong>Préparation de commande</strong>&nbsp;: 1 à 3 jours ouvrés à compter de la
          confirmation de paiement.
        </li>
        <li>
          <strong>Expédition France métropolitaine</strong>&nbsp;: 3 à 7 jours ouvrés (standard),
          1 à 3 jours ouvrés (express, lorsque l'option est proposée).
        </li>
        <li>
          <strong>Expédition Union européenne</strong>&nbsp;: 5 à 12 jours ouvrés.
        </li>
        <li>
          <strong>Expédition Royaume-Uni</strong>&nbsp;: 7 à 14 jours ouvrés (formalités
          douanières post-Brexit prises en charge par le transporteur).
        </li>
      </ul>
      <p>
        Les délais indicatifs sont susceptibles d'évoluer pendant les périodes de forte
        activité (soldes, fêtes de fin d'année). Le délai contractuel maximum, conformément à
        l'article L216-2 du Code de la consommation, est de <strong>30 jours</strong> à compter
        de la conclusion du contrat, sauf accord exprès et écrit pour un délai différent.
      </p>

      <h2>3. Transporteurs</h2>
      <p>
        Les boutiques hébergées font appel à des transporteurs professionnels reconnus, tels
        que&nbsp;: La Poste / Colissimo, Mondial Relay, Chronopost, DPD, UPS et FedEx. Le
        transporteur retenu pour chaque commande est précisé sur la confirmation de
        commande et dans l'email de suivi d'expédition.
      </p>

      <h2>4. Frais de port</h2>
      <p>
        Les frais de port sont calculés en temps réel au moment du panier, en fonction du poids
        total, du volume, du pays de livraison et de l'option d'expédition retenue.
        L'utilisateur les visualise et les valide expressément avant le paiement.
      </p>
      <p>
        Certaines boutiques proposent la <strong>livraison gratuite</strong> au-delà d'un
        montant minimum d'achat ou pour des produits éligibles. Cette mention figure alors sur
        la fiche produit.
      </p>

      <h2>5. Suivi de commande</h2>
      <p>
        Dès l'expédition, le client reçoit un email contenant le numéro de suivi et un lien vers
        la page <em>Suivi de commande</em> de la boutique concernée. Cette page permet de suivre
        l'acheminement du colis en temps réel.
      </p>

      <h2>6. Retard, perte ou avarie</h2>
      <p>
        En cas de retard significatif (au-delà du délai contractuel maximum de 30 jours), de
        perte ou d'avarie constatée à la réception, le client peut&nbsp;: (i) contacter le
        service client de la boutique pour ouvrir une réclamation, et (ii) résoudre le contrat
        conformément à l'article L216-6 du Code de la consommation, dans les conditions prévues
        par cet article. Le remboursement intervient alors dans un délai maximum de 14 jours.
      </p>

      <h2>7. Réception et vérification</h2>
      <p>
        Le destinataire est invité à vérifier l'état du colis à la réception. En cas de colis
        endommagé, il doit émettre des réserves précises auprès du transporteur et notifier la
        boutique vendeuse dans les meilleurs délais (idéalement sous 48 heures), photos à l'appui.
      </p>

      <h2>8. Adresse de livraison incorrecte</h2>
      <p>
        Il appartient au client de vérifier l'exactitude de l'adresse de livraison saisie. Toute
        erreur ou omission entraînant un échec de livraison ou un retour à l'expéditeur peut
        donner lieu à une nouvelle facturation des frais de port pour réexpédition.
      </p>

      <h2>9. Contact</h2>
      <p>
        Pour toute question relative à la livraison d'une commande passée sur l'une des
        boutiques hébergées, contacter le service client de la boutique via sa page Contact.
        Pour toute question relative à la plateforme Altiaro elle-même&nbsp;:
        <br />
        Email&nbsp;:{" "}
        <a href={`mailto:${ALTIARO_COMPANY.email}`}>{ALTIARO_COMPANY.email}</a>
        <br />
        Adresse&nbsp;: {ALTIARO_COMPANY.adresse}
      </p>
    </PlatformLegalLayout>
  );
}
