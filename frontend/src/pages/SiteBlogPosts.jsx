import React from "react";
import { useParams } from "react-router-dom";
import Layout from "../components/Layout";
import StepLayout from "../components/cockpit/StepLayout";
import MagicJobProgress from "../components/cockpit/MagicJobProgress";

/**
 * Phase 3.2 — Étape 7 (content) refonte clean.
 *
 * 1 seul bouton magique qui orchestre : audit kw + cluster + pilier + 8
 * satellites + 5 long-tail + 14 visuels hero + maillage interne + traduction
 * 5 langues + publication sitemap / IndexNow. Streaming SSE temps réel.
 */
export default function SiteBlogPosts() {
  const { id: siteId } = useParams();
  const base = `/sites/${siteId}/magic/content`;

  return (
    <Layout>
      <StepLayout
        siteId={siteId}
        stepKey="content"
        title="Contenu SEO automatisé"
        subtitle="1 pilier + 8 satellites + 5 long-tail + images + maillage + traduction, le tout en un clic."
        estimatedTime="~3-5 min"
        whatItDoes="Le moteur identifie 14 thèmes éditoriaux autour de ta niche, rédige un article pilier long (~2 000 mots, Sonnet), 8 satellites et 5 long-tail (Haiku, 800-1 200 mots), produit un visuel hero IA par article (Nano Banana), maille en interne et traduit l'ensemble dans 5 langues cibles. Coût estimé : ~2.50 $ / site."
      >
        <MagicJobProgress
          siteId={siteId}
          magicEndpoint={base}
          streamEndpoint={`${base}/stream`}
          statusEndpoint={`${base}/status`}
          magicButtonLabel="Générer le contenu SEO complet"
          whenIdleHint="Un seul clic déclenche la génération complète. Tu peux fermer l'onglet, tout tourne en arrière-plan."
          dryRun={false}
        />
      </StepLayout>
    </Layout>
  );
}
