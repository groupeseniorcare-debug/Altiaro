import React from "react";
import PlatformLegalLayout from "../components/PlatformLegalLayout";
import { ALTIARO_COMPANY } from "../lib/altiaroLegal";

export default function PlatformLegalMentions() {
  return (
    <PlatformLegalLayout title="Mentions légales" eyebrow="Altiaro · Légal">
      <h2>1. Éditeur du site</h2>
      <ul>
        <li>Dénomination&nbsp;: {ALTIARO_COMPANY.nom}</li>
        <li>Forme juridique&nbsp;: {ALTIARO_COMPANY.forme_juridique}</li>
        <li>SIREN&nbsp;: {ALTIARO_COMPANY.siren}</li>
        <li>SIRET&nbsp;: {ALTIARO_COMPANY.siret}</li>
        <li>Code APE&nbsp;: {ALTIARO_COMPANY.code_naf}</li>
        <li>Activité&nbsp;: {ALTIARO_COMPANY.activite}</li>
        <li>{ALTIARO_COMPANY.rne_inscription}</li>
        <li>TVA&nbsp;: {ALTIARO_COMPANY.tva_intra}</li>
        <li>{ALTIARO_COMPANY.tva_mention_cgv}</li>
        <li>Siège social&nbsp;: {ALTIARO_COMPANY.adresse}</li>
        <li>
          Email&nbsp;:{" "}
          <a href={`mailto:${ALTIARO_COMPANY.email}`}>{ALTIARO_COMPANY.email}</a>
        </li>
        <li>Téléphone&nbsp;: {ALTIARO_COMPANY.telephone}</li>
        <li>Directeur de la publication&nbsp;: {ALTIARO_COMPANY.directeur_publication}</li>
      </ul>

      <h2>2. Hébergement</h2>
      <p>
        La plateforme Altiaro est hébergée par&nbsp;: {ALTIARO_COMPANY.hebergeur_nom} —{" "}
        {ALTIARO_COMPANY.hebergeur_adresse}.
      </p>

      <h2>3. Activité</h2>
      <p>
        Altiaro est une plateforme SaaS qui permet à des concepteurs indépendants de créer,
        personnaliser et exploiter des boutiques en ligne premium. Altiaro fournit
        l'infrastructure, les outils logiciels (génération de contenu, visuels, SEO/AEO,
        paiement, analytique) et l'assistance technique. Les transactions commerciales
        réalisées sur les boutiques hébergées sont conclues entre les concepteurs et leurs
        clients respectifs.
      </p>

      <h2>4. Propriété intellectuelle</h2>
      <p>
        L'ensemble des éléments accessibles sur la plateforme Altiaro (textes, images,
        graphismes, logos, icônes, sons, logiciels) sont protégés par le droit français et
        international de la propriété intellectuelle. Sauf autorisation préalable et expresse
        d'Altiaro ou de leurs ayants droit respectifs, toute reproduction, représentation,
        modification, publication ou adaptation est interdite.
      </p>
      <p>
        Les marques et logos cités sur la plateforme à des fins illustratives ou techniques
        (Google, Mollie, Resend, AliExpress, etc.) sont la propriété de leurs détenteurs
        respectifs.
      </p>

      <h2>5. Liens hypertextes</h2>
      <p>
        La plateforme peut contenir des liens vers des sites tiers. Altiaro n'exerce aucun
        contrôle sur ces sites et décline toute responsabilité quant à leur contenu, leurs
        pratiques ou leur disponibilité.
      </p>

      <h2>6. Données personnelles</h2>
      <p>
        Le traitement des données personnelles est détaillé dans la{" "}
        <a href="/legal/confidentialite">politique de confidentialité</a>.
      </p>

      <h2>7. Cookies</h2>
      <p>
        Le paramétrage des cookies est exposé dans la{" "}
        <a href="/legal/confidentialite">politique de confidentialité</a>, section
        «&nbsp;Cookies et traceurs&nbsp;».
      </p>

      <h2>8. Droit applicable et juridiction</h2>
      <p>
        Les présentes mentions sont régies par le droit français. Toute contestation relative
        à leur interprétation ou à leur exécution relèvera, à défaut de règlement amiable, du
        tribunal compétent ({ALTIARO_COMPANY.juridiction}).
      </p>
    </PlatformLegalLayout>
  );
}
