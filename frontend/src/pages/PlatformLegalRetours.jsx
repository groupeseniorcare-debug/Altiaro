import React from "react";
import PlatformLegalLayout from "../components/PlatformLegalLayout";
import { ALTIARO_COMPANY } from "../lib/altiaroLegal";

export default function PlatformLegalRetours() {
  return (
    <PlatformLegalLayout title="Politique de retour" eyebrow="Altiaro · Légal">
      <h2>Préambule</h2>
      <p>
        Altiaro est une plateforme SaaS qui héberge des boutiques en ligne créées et gérées par
        des concepteurs indépendants. Chaque boutique hébergée dispose de sa propre politique de
        retour, conforme aux dispositions du Code de la consommation, accessible depuis la fiche
        produit ainsi que depuis le pied de page de la boutique concernée.
      </p>
      <p>
        La présente politique décrit&nbsp;: (i) le cadre commun applicable aux achats effectués
        sur les boutiques hébergées par la plateforme Altiaro, et (ii) le régime applicable aux
        services Altiaro souscrits par les concepteurs.
      </p>

      <h2>1. Achats effectués sur une boutique hébergée par Altiaro</h2>
      <h3>1.1. Délai de rétractation</h3>
      <p>
        Conformément à l'article L221-18 du Code de la consommation, le consommateur dispose
        d'un <strong>délai de rétractation de 30 jours</strong> à compter de la réception du
        produit pour exercer son droit de retour, sans avoir à motiver sa décision ni à supporter
        d'autres coûts que ceux prévus aux articles L221-23 à L221-25 du même Code.
      </p>

      <h3>1.2. Conditions du retour</h3>
      <ul>
        <li>Le produit doit être retourné non utilisé, dans son emballage d'origine ;</li>
        <li>Tous les accessoires, notices et documents fournis doivent être joints ;</li>
        <li>
          Une copie de la confirmation de commande (numéro de commande commençant par
          <em> CF-XXXX</em>) doit accompagner l'envoi.
        </li>
      </ul>

      <h3>1.3. Frais de retour</h3>
      <p>
        Les frais de retour sont à la charge de l'acheteur, sauf en cas de défaut du produit, de
        non-conformité, ou d'erreur du marchand, auquel cas ils sont intégralement pris en
        charge par la boutique vendeuse.
      </p>

      <h3>1.4. Remboursement</h3>
      <p>
        Le remboursement intervient dans un délai maximum de <strong>14 jours</strong> à compter
        de la réception et de l'inspection du produit retourné, conformément à l'article L221-24
        du Code de la consommation. Le remboursement est effectué par le même moyen de paiement
        que celui utilisé lors de la commande, sauf accord exprès du consommateur.
      </p>

      <h3>1.5. Procédure</h3>
      <p>
        Pour initier une demande de retour, le consommateur contacte le service client de la
        boutique vendeuse via la page Contact de cette boutique (les coordonnées figurent dans
        les CGV de la boutique concernée).
      </p>

      <h3>1.6. Produits exclus du droit de rétractation</h3>
      <p>
        Conformément à l'article L221-28 du Code de la consommation, certains biens sont exclus
        du droit de rétractation, notamment&nbsp;: les biens confectionnés selon les
        spécifications du consommateur ou nettement personnalisés, les biens scellés ne pouvant
        être renvoyés pour des raisons d'hygiène ou de protection de la santé après ouverture,
        et les biens descellés après livraison ne pouvant être renvoyés.
      </p>

      <h2>2. Services Altiaro souscrits par les concepteurs</h2>
      <p>
        Les abonnements et frais de plateforme Altiaro souscrits par les concepteurs sont régis
        par les <a href="/legal/cgv">Conditions générales de vente Altiaro</a>. Conformément à
        l'article L221-28 1° du Code de la consommation, les services pleinement exécutés avant
        la fin du délai de rétractation, avec l'accord exprès préalable du concepteur, ne sont
        pas soumis à rétractation.
      </p>

      <h2>3. Médiation de la consommation</h2>
      <p>
        Conformément à l'article L612-1 du Code de la consommation, le consommateur peut, en cas
        de litige non résolu amiablement, recourir gratuitement à un médiateur de la
        consommation. Plus d'informations sur&nbsp;:{" "}
        <a
          href={ALTIARO_COMPANY.mediateur_url}
          target="_blank"
          rel="noreferrer noopener"
        >
          {ALTIARO_COMPANY.mediateur_url}
        </a>
        .
      </p>

      <h2>4. Droit applicable et juridiction</h2>
      <p>
        La présente politique est soumise au droit français. En cas de litige, et après échec
        d'une tentative de résolution amiable, le consommateur peut saisir, à son choix, l'une
        des juridictions territorialement compétentes en vertu du Code de procédure civile, ou
        la juridiction du lieu où il demeurait au moment de la conclusion du contrat ou de la
        survenance du fait dommageable.
      </p>

      <h2>5. Contact Altiaro</h2>
      <p>
        Pour toute question relative à la présente politique&nbsp;:
        <br />
        Email&nbsp;:{" "}
        <a href={`mailto:${ALTIARO_COMPANY.email}`}>{ALTIARO_COMPANY.email}</a>
        <br />
        Adresse&nbsp;: {ALTIARO_COMPANY.adresse}
      </p>
    </PlatformLegalLayout>
  );
}
