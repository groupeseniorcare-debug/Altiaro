import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { CheckCircle, Rocket, ArrowSquareOut } from "@phosphor-icons/react";
import Layout from "../components/Layout";
import StepLayout from "../components/cockpit/StepLayout";
import MagicJobProgress from "../components/cockpit/MagicJobProgress";
import { api, apiCall } from "../lib/api";

/**
 * Phase 3.2 — Étape 10 (qa) refonte clean.
 *
 * Health-check exhaustif (11 points) + GMC onboarding + mise en ligne, le
 * tout derrière un unique bouton magique. Si le site est déjà `live`, on
 * affiche un écran de victoire avec le lien storefront.
 */
export default function SiteQA() {
  const { id: siteId } = useParams();
  const base = `/sites/${siteId}/magic/launch`;
  const [site, setSite] = useState(null);

  useEffect(() => {
    apiCall(() => api.get(`/sites/${siteId}`)).then((r) => setSite(r.data));
  }, [siteId]);

  const isLive = site?.status === "live";
  const publicUrl = site?.custom_domain
    ? `https://${site.custom_domain}`
    : (site ? `${window.location.origin}/shop/${siteId}` : null);

  return (
    <Layout>
      <StepLayout
        siteId={siteId}
        stepKey="qa"
        title="Check final + Mise en ligne"
        subtitle="11 points de contrôle, GMC onboarding et bascule en production, le tout d'un seul clic."
        estimatedTime="~2-3 min"
        whatItDoes="Le moteur vérifie que ton site est prêt (9+ produits, 3+ upsells, 14+ articles, 6 langues, domaine + SSL actif, sitemap, JSON-LD, Mollie, GSC, score SEO ≥ 70). Si un seul point échoue → tu reçois la liste des étapes Cockpit à corriger. Si tout passe → GMC sub-merchant créé, identité légale / shipping / returns poussés, feed XML actif, site basculé en live et email de confirmation envoyé."
      >
        {isLive ? (
          <div className="max-w-3xl mx-auto py-10 text-center" data-testid="qa-victory">
            <div className="inline-flex items-center justify-center h-20 w-20 rounded-full bg-emerald-100 mb-5">
              <Rocket size={36} weight="fill" className="text-emerald-700" />
            </div>
            <h2 className="text-3xl md:text-4xl font-semibold text-neutral-900 mb-3" style={{ fontFamily: "'Fraunces', serif" }}>
              Ton site est en ligne
            </h2>
            <p className="text-sm text-neutral-600 max-w-xl mx-auto mb-6">
              {site?.went_live_at
                ? `Mise en ligne le ${new Date(site.went_live_at).toLocaleString("fr-FR")}.`
                : "Bravo ! Ta boutique est désormais publique."}
            </p>
            {publicUrl && (
              <a href={publicUrl} target="_blank" rel="noreferrer"
                 className="inline-flex items-center gap-2 h-12 px-6 rounded-xl bg-neutral-900 text-white font-medium text-sm hover:bg-neutral-800 transition"
                 data-testid="qa-open-storefront">
                <ArrowSquareOut size={16} weight="bold" /> Voir ma boutique
              </a>
            )}
            <div className="mt-6 text-sm text-neutral-500">
              <Link to={`/sites/${siteId}/analytics`} className="underline hover:text-neutral-900">Suivre les premières stats →</Link>
            </div>
          </div>
        ) : (
          <MagicJobProgress
            siteId={siteId}
            magicEndpoint={base}
            streamEndpoint={`${base}/stream`}
            statusEndpoint={`${base}/status`}
            magicButtonLabel="Lancer le check final + Mise en ligne"
            whenIdleHint="Le health-check tourne d'abord (read-only). Si tout est vert, le site est publié et GMC est configuré automatiquement."
            dryRun={false}
            onSuccess={() => apiCall(() => api.get(`/sites/${siteId}`)).then((r) => setSite(r.data))}
          />
        )}
      </StepLayout>
    </Layout>
  );
}
