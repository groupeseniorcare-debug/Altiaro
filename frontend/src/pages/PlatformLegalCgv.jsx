import React from "react";
import PlatformLegalLayout from "../components/PlatformLegalLayout";
import { ALTIARO_COMPANY } from "../lib/altiaroLegal";

export default function PlatformLegalCgv() {
  return (
    <PlatformLegalLayout title="Conditions générales de vente" eyebrow="Altiaro · Légal">
      <h2>Article 1. Objet</h2>
      <p>
        Les présentes Conditions générales de vente (ci-après «&nbsp;CGV&nbsp;») ont pour objet
        de définir les modalités contractuelles applicables entre {ALTIARO_COMPANY.nom}
        (ci-après «&nbsp;Altiaro&nbsp;»), éditeur de la plateforme accessible à l'adresse
        {" "}
        <a href={ALTIARO_COMPANY.site_web}>{ALTIARO_COMPANY.site_web}</a>, et toute personne
        physique ou morale (ci-après «&nbsp;le Concepteur&nbsp;») souscrivant aux services de
        création et d'hébergement de boutiques en ligne proposés par Altiaro.
      </p>
      <p>
        Toute souscription à un service Altiaro implique l'acceptation pleine et entière des
        présentes CGV. Les CGV applicables sont celles en vigueur à la date de la souscription.
      </p>

      <h2>Article 2. Éditeur — Identité</h2>
      <ul>
        <li>Dénomination&nbsp;: {ALTIARO_COMPANY.nom}</li>
        <li>Forme juridique&nbsp;: {ALTIARO_COMPANY.forme_juridique}</li>
        <li>SIREN&nbsp;: {ALTIARO_COMPANY.siren}</li>
        <li>SIRET&nbsp;: {ALTIARO_COMPANY.siret}</li>
        <li>Code APE&nbsp;: {ALTIARO_COMPANY.code_naf}</li>
        <li>Activité&nbsp;: {ALTIARO_COMPANY.activite}</li>
        <li>{ALTIARO_COMPANY.rne_inscription}</li>
        <li>{ALTIARO_COMPANY.tva_mention_cgv}</li>
        <li>Siège social&nbsp;: {ALTIARO_COMPANY.adresse}</li>
        <li>
          Email&nbsp;:{" "}
          <a href={`mailto:${ALTIARO_COMPANY.email}`}>{ALTIARO_COMPANY.email}</a>
        </li>
        <li>Téléphone&nbsp;: {ALTIARO_COMPANY.telephone}</li>
      </ul>

      <h2>Article 3. Description des services</h2>
      <p>
        Altiaro met à la disposition des Concepteurs un environnement logiciel permettant la
        création, la personnalisation et l'exploitation d'une boutique en ligne, comprenant
        notamment&nbsp;: l'hébergement technique, des outils d'aide à la conception (génération
        de contenu, visuels, recommandations), des modules de paiement intégrés, des modules
        d'analyse de performance et des outils SEO/AEO.
      </p>

      <h2>Article 4. Souscription — Compte concepteur</h2>
      <p>
        L'accès aux services suppose la création d'un compte. Le Concepteur garantit l'exactitude
        des informations transmises lors de l'inscription et s'engage à les maintenir à jour. Il
        est responsable de la confidentialité de ses identifiants. Toute action effectuée via
        son compte est réputée être de son fait.
      </p>

      <h2>Article 5. Tarifs et facturation</h2>
      <p>
        Les tarifs des services sont indiqués sur la plateforme Altiaro et lors de la
        souscription. Conformément au statut fiscal de l'éditeur, la mention
        <strong> «&nbsp;{ALTIARO_COMPANY.tva_mention_cgv}&nbsp;»</strong> s'applique aux
        prestations facturées. Les prix sont exprimés en euros, sans TVA à ce titre.
      </p>
      <p>
        La facturation intervient selon la périodicité souscrite (mensuelle, annuelle ou à la
        prestation). Les factures sont adressées par voie électronique à l'adresse email
        renseignée par le Concepteur.
      </p>

      <h2>Article 6. Modalités de paiement</h2>
      <p>
        Le paiement est réalisé via les prestataires de paiement intégrés par Altiaro
        (notamment Mollie). En cas de défaut de paiement, et après mise en demeure restée
        infructueuse, Altiaro se réserve la faculté de suspendre l'accès aux services jusqu'à
        régularisation et, à défaut, de résilier le contrat de plein droit.
      </p>

      <h2>Article 7. Droit de rétractation</h2>
      <p>
        Conformément à l'article L221-28 1° du Code de la consommation, le droit de rétractation
        ne peut s'exercer pour les services pleinement exécutés avant la fin du délai de
        rétractation, lorsque cette exécution a commencé après accord préalable exprès du
        consommateur et renoncement exprès à son droit de rétractation.
      </p>

      <h2>Article 8. Obligations du Concepteur</h2>
      <ul>
        <li>Respecter les lois et règlements en vigueur, notamment ceux applicables au commerce électronique, à la consommation et à la protection des données personnelles ;</li>
        <li>Ne pas vendre de produits illicites, contrefaits, dangereux ou prohibés ;</li>
        <li>Disposer des droits et autorisations nécessaires sur les contenus mis en ligne ;</li>
        <li>Répondre des relations contractuelles avec ses propres clients (livraison, service après-vente, retours, médiation) ;</li>
        <li>Maintenir des conditions de vente et politiques (CGV, livraison, retours) accessibles depuis sa boutique.</li>
      </ul>

      <h2>Article 9. Propriété intellectuelle</h2>
      <p>
        La plateforme Altiaro, son architecture logicielle, ses interfaces graphiques, ses
        contenus éditoriaux ainsi que les marques associées sont la propriété exclusive de
        {" "}
        {ALTIARO_COMPANY.nom}. Toute reproduction ou utilisation non autorisée est strictement
        prohibée. Le Concepteur conserve l'entière propriété intellectuelle des contenus qu'il
        publie sur sa boutique.
      </p>

      <h2>Article 10. Données personnelles</h2>
      <p>
        Les modalités de traitement des données personnelles sont détaillées dans la
        <a href="/legal/confidentialite"> politique de confidentialité</a>, qui fait partie
        intégrante des présentes CGV.
      </p>

      <h2>Article 11. Disponibilité et maintenance</h2>
      <p>
        Altiaro met en œuvre les moyens raisonnables pour assurer la disponibilité des
        services, sans garantir une disponibilité ininterrompue. Des opérations de maintenance
        planifiées ou correctives peuvent entraîner des interruptions temporaires, qui seront,
        dans la mesure du possible, annoncées au préalable.
      </p>

      <h2>Article 12. Responsabilité</h2>
      <p>
        La responsabilité d'Altiaro est limitée aux dommages directs prouvés. Altiaro ne pourra
        être tenue responsable des dommages indirects, ni des conséquences d'un usage non
        conforme de la plateforme par le Concepteur ou par les clients de sa boutique.
      </p>

      <h2>Article 13. Résiliation</h2>
      <p>
        Le Concepteur peut résilier son abonnement à tout moment depuis son espace de gestion.
        Altiaro peut résilier le contrat en cas de manquement grave et persistant aux présentes
        CGV après mise en demeure restée infructueuse pendant 15 jours.
      </p>

      <h2>Article 14. Garanties légales</h2>
      <p>
        Lorsque l'utilisateur est un consommateur au sens du Code de la consommation, il
        bénéficie de plein droit&nbsp;: (i) de la garantie légale de conformité (articles L217-3
        à L217-20 du Code de la consommation) et (ii) de la garantie légale des vices cachés
        (articles 1641 à 1648 et 2232 du Code civil).
      </p>

      <h2>Article 15. Médiation</h2>
      <p>
        Conformément à l'article L612-1 du Code de la consommation, le consommateur peut
        recourir gratuitement à un médiateur de la consommation. Plus d'informations sur&nbsp;:
        {" "}
        <a
          href={ALTIARO_COMPANY.mediateur_url}
          target="_blank"
          rel="noreferrer noopener"
        >
          {ALTIARO_COMPANY.mediateur_url}
        </a>
        .
      </p>

      <h2>Article 16. Droit applicable et juridiction compétente</h2>
      <p>
        Les présentes CGV sont régies par le droit français. À défaut de résolution amiable,
        tout litige sera porté devant le tribunal compétent ({ALTIARO_COMPANY.juridiction}
        ), sous réserve des règles impératives applicables aux consommateurs en matière de
        compétence territoriale.
      </p>
    </PlatformLegalLayout>
  );
}
