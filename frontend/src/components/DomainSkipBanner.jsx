// Bandeau global persistent affiché sur toutes les pages d'un site
// si site.domain_skipped === true. Permet au concepteur de voir en
// permanence qu'un domaine reste obligatoire avant publication.
import React, { useEffect, useState } from "react";
import { Link, useParams, useLocation } from "react-router-dom";
import { api, apiCall } from "../lib/api";

export default function DomainSkipBanner() {
  const { id: siteId } = useParams();
  const location = useLocation();
  const [skipped, setSkipped] = useState(false);
  const [domain, setDomain] = useState("");

  useEffect(() => {
    if (!siteId) return;
    apiCall(() => api.get(`/sites/${siteId}`)).then(({ data }) => {
      if (!data) return;
      setSkipped(!!data.domain_skipped && !data.custom_domain);
      setDomain(data.custom_domain || "");
    });
  }, [siteId, location.pathname]);

  // Don't show on the Domains page itself (the page already has its own UI)
  if (!skipped || domain) return null;
  if (location.pathname.includes("/domains")) return null;

  return (
    <div
      className="bg-amber-50 border-b border-amber-200 px-4 py-2 text-sm text-amber-900 flex items-center justify-center gap-3"
      data-testid="domain-skip-banner"
      style={{ position: "sticky", top: 0, zIndex: 40 }}
    >
      <span>⚠️</span>
      <span>
        <strong>Domaine non configuré.</strong> Étape obligatoire avant la
        mise en ligne — pense à revenir l'ajouter.
      </span>
      <Link
        to={`/sites/${siteId}/domains`}
        className="underline font-medium hover:no-underline"
      >
        Configurer maintenant →
      </Link>
    </div>
  );
}
