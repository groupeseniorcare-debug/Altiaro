import React from "react";
import { useParams } from "react-router-dom";
import Layout from "../components/Layout";
import StepLayout from "../components/cockpit/StepLayout";
import MagicJobProgress from "../components/cockpit/MagicJobProgress";

/**
 * Phase 3.2 — Étape 9 (seo) refonte clean.
 *
 * 1 seul bouton qui orchestre : audit SEO + GSC provisioning + IndexNow batch
 * + 20 annuaires Silver Eco + Featured.com + vérification JSON-LD.
 */
export default function SiteSEO() {
  const { id: siteId } = useParams();
  const base = `/sites/${siteId}/magic/seo`;

  return (
    <Layout>
      <StepLayout
        siteId={siteId}
        stepKey="seo"
        title="Optimisation SEO & indexation"
        subtitle="Audit complet, connexion Google Search Console, IndexNow, 20 annuaires Silver Eco et Featured.com en un clic."
        estimatedTime="~1-2 min"
        whatItDoes="Le moteur audite toutes tes pages, provisionne une propriété Google Search Console + soumet le sitemap, ping IndexNow sur l'ensemble du site, soumet la boutique aux 20 annuaires Silver Eco, pousse un pitch Featured.com (si clé configurée) et vérifie la cohérence canonical / hreflang / JSON-LD."
      >
        <MagicJobProgress
          siteId={siteId}
          magicEndpoint={base}
          streamEndpoint={`${base}/stream`}
          statusEndpoint={`${base}/status`}
          magicButtonLabel="Optimiser & indexer la boutique"
          whenIdleHint="Tout tourne en parallèle : connexions Google, ping moteurs, soumissions annuaires. Aucune action manuelle nécessaire."
          dryRun={false}
        />
      </StepLayout>
    </Layout>
  );
}
