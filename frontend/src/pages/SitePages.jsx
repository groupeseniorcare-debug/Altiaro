/**
 * SitePages — DEPRECATED (Phase 1, 2026-05-04).
 *
 * L'étape Cockpit `pages` a été retirée de STEP_ORDER (Phase 0). La page
 * `/sites/:id/pages` est dépréciée et redirige automatiquement vers la page
 * branding du site.
 *
 * Toute la logique éditoriale (À propos, FAQ, Contact, CGV, Mentions,
 * Confidentialité, Cookies, Médiation, Livraison, Retours) reste accessible
 * dans `SiteBranding.jsx > onglet Avancé > section Pages essentielles` ;
 * voir aussi `components/BrandingContent.jsx`.
 *
 * Pourquoi conserver la route ? Pour ne pas casser les bookmarks / liens
 * directs / docs internes qui pointaient vers `/sites/:id/pages`.
 */
import React, { useEffect } from "react";
import { useParams, Navigate } from "react-router-dom";

export default function SitePages() {
  const { id: siteId } = useParams();

  useEffect(() => {
    // eslint-disable-next-line no-console
    console.warn(
      "[Altiaro] /sites/:id/pages est déprécié depuis 2026-05-04 (Phase 1). " +
      "L'étape Cockpit `pages` a été supprimée. Redirection vers /branding. " +
      "Mettez à jour vos liens internes."
    );
  }, []);

  return <Navigate to={`/sites/${siteId}/branding`} replace />;
}
