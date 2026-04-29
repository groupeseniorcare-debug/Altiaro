import React from "react";
import PlatformLegalLayout from "../components/PlatformLegalLayout";
import { ALTIARO_COMPANY } from "../lib/altiaroLegal";

export default function PlatformLegalConfidentialite() {
  return (
    <PlatformLegalLayout
      title="Politique de confidentialité"
      eyebrow="Altiaro · Légal"
    >
      <h2>Préambule</h2>
      <p>
        La présente politique décrit la manière dont {ALTIARO_COMPANY.nom} (ci-après
        «&nbsp;Altiaro&nbsp;») collecte, utilise, conserve et protège les données à caractère
        personnel des utilisateurs de la plateforme et des visiteurs des boutiques hébergées,
        conformément au Règlement (UE) 2016/679 (RGPD) et à la loi n° 78-17 du 6 janvier 1978
        modifiée (Informatique et Libertés).
      </p>

      <h2>1. Responsable de traitement</h2>
      <p>
        Le responsable de traitement est&nbsp;: {ALTIARO_COMPANY.nom}, {ALTIARO_COMPANY.adresse}.
        Pour toute question relative aux données personnelles&nbsp;:{" "}
        <a href={`mailto:${ALTIARO_COMPANY.dpo_email}`}>
          {ALTIARO_COMPANY.dpo_email}
        </a>
        .
      </p>
      <p>
        Lorsque le visiteur navigue sur une boutique hébergée par Altiaro, le concepteur
        indépendant qui exploite cette boutique est, le cas échéant, responsable de traitement
        conjoint pour les traitements liés à la commande, à la livraison et à la relation
        client. Altiaro agit en sous-traitant au sens de l'article 28 du RGPD pour les
        traitements liés à l'hébergement et aux outils logiciels.
      </p>

      <h2>2. Données collectées</h2>
      <ul>
        <li>
          <strong>Données de compte concepteur</strong>&nbsp;: nom, email, mot de passe haché,
          informations de facturation.
        </li>
        <li>
          <strong>Données de compte client (boutiques)</strong>&nbsp;: nom, email, adresse de
          livraison et de facturation, historique de commandes.
        </li>
        <li>
          <strong>Données de paiement</strong>&nbsp;: traitées directement par les prestataires
          de paiement agréés (Mollie). Altiaro ne stocke pas les numéros de carte bancaire.
        </li>
        <li>
          <strong>Données de navigation</strong>&nbsp;: adresses IP, identifiants techniques,
          journaux de connexion, statistiques d'usage.
        </li>
        <li>
          <strong>Cookies et traceurs</strong>&nbsp;: voir section 7.
        </li>
      </ul>

      <h2>3. Finalités et bases légales</h2>
      <table>
        <thead>
          <tr>
            <th>Finalité</th>
            <th>Base légale</th>
            <th>Conservation</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>Exécution du contrat de service (compte concepteur, facturation)</td>
            <td>Article 6.1.b RGPD — exécution contractuelle</td>
            <td>Durée du contrat + 5 ans (prescription civile)</td>
          </tr>
          <tr>
            <td>Gestion des commandes des boutiques</td>
            <td>Article 6.1.b RGPD — exécution contractuelle</td>
            <td>10 ans (obligations comptables — art. L123-22 C. com.)</td>
          </tr>
          <tr>
            <td>Marketing direct (newsletters)</td>
            <td>Article 6.1.a RGPD — consentement</td>
            <td>3 ans à compter du dernier contact</td>
          </tr>
          <tr>
            <td>Sécurité et prévention de la fraude</td>
            <td>Article 6.1.f RGPD — intérêts légitimes</td>
            <td>1 an</td>
          </tr>
          <tr>
            <td>Mesure d'audience anonymisée</td>
            <td>Article 6.1.f ou consentement (selon outil)</td>
            <td>13 mois maximum</td>
          </tr>
        </tbody>
      </table>

      <h2>4. Destinataires</h2>
      <p>
        Les données sont destinées aux équipes habilitées d'Altiaro, aux concepteurs
        responsables des boutiques (pour leurs propres clients) et aux sous-traitants
        techniques&nbsp;:
      </p>
      <ul>
        <li>Hébergement&nbsp;: {ALTIARO_COMPANY.hebergeur_nom}.</li>
        <li>Paiements&nbsp;: Mollie B.V., agréé PSP par la DNB (Pays-Bas).</li>
        <li>Email transactionnel&nbsp;: Resend, Inc.</li>
        <li>Outils Google (Search Console, Analytics, Merchant)&nbsp;: Google Ireland Limited.</li>
        <li>Sourcing produits&nbsp;: AliExpress / CJ Dropshipping selon paramétrage.</li>
      </ul>
      <p>
        Tous les sous-traitants sont liés par un contrat conforme à l'article 28 du RGPD.
      </p>

      <h2>5. Transferts hors UE</h2>
      <p>
        Certains prestataires (Google, AliExpress) peuvent traiter des données hors de l'Union
        européenne. Ces transferts sont encadrés soit par une décision d'adéquation de la
        Commission européenne (Data Privacy Framework pour les prestataires américains adhérents),
        soit par les clauses contractuelles types adoptées par la Commission européenne.
      </p>

      <h2>6. Sécurité</h2>
      <p>
        Altiaro met en œuvre les mesures techniques et organisationnelles appropriées&nbsp;:
        chiffrement des communications (TLS), hachage des mots de passe (bcrypt), contrôles
        d'accès par rôles, journalisation des actions sensibles, sauvegardes régulières.
      </p>

      <h2>7. Cookies et traceurs</h2>
      <p>
        La plateforme utilise des cookies strictement nécessaires au fonctionnement (session,
        sécurité), des cookies de mesure d'audience et, le cas échéant, des cookies marketing
        soumis à consentement. Le visiteur peut accepter, refuser ou paramétrer ces cookies
        depuis le bandeau de consentement.
      </p>

      <h2>8. Droits des personnes</h2>
      <p>
        Conformément aux articles 15 à 22 du RGPD, toute personne dispose des droits
        suivants&nbsp;: accès, rectification, effacement, limitation du traitement, opposition,
        portabilité, retrait du consentement à tout moment, et droit de définir des directives
        relatives au sort des données après décès.
      </p>
      <p>
        Pour exercer ces droits, écrire à&nbsp;:{" "}
        <a href={`mailto:${ALTIARO_COMPANY.dpo_email}`}>
          {ALTIARO_COMPANY.dpo_email}
        </a>
        . Une réponse est apportée dans un délai d'un mois à compter de la réception de la
        demande, prolongeable de deux mois en cas de complexité.
      </p>
      <p>
        En cas de désaccord persistant, toute personne peut introduire une réclamation auprès
        de la CNIL (3 place de Fontenoy — TSA 80715 — 75334 Paris Cedex 07 —{" "}
        <a href="https://www.cnil.fr" target="_blank" rel="noreferrer noopener">
          www.cnil.fr
        </a>
        ).
      </p>

      <h2>9. Mineurs</h2>
      <p>
        Les services Altiaro et les boutiques hébergées ne sont pas destinés aux mineurs de
        moins de 15 ans sans le consentement du titulaire de l'autorité parentale. En cas de
        collecte involontaire, la personne concernée peut demander la suppression immédiate
        des données.
      </p>

      <h2>10. Évolution de la politique</h2>
      <p>
        La présente politique peut être amenée à évoluer. Toute modification substantielle sera
        portée à la connaissance des utilisateurs par tout moyen approprié (email, bandeau).
      </p>
    </PlatformLegalLayout>
  );
}
