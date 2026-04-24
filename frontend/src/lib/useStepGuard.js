/**
 * useStepGuard — Chantier 1 (gating strict).
 *
 * Hook à appeler dans les pages des étapes cockpit pour rediriger l'utilisateur
 * si l'étape précédente n'est pas complétée.
 *
 * Usage dans une page (ex: SiteUpsells.jsx) :
 *   const { allowed, checking } = useStepGuard(siteId, "upsells");
 *   if (checking) return <LoadingSpinner />;
 *   if (!allowed) return null;  // redirect déjà déclenché
 *
 * Le hook utilise GET /api/sites/{id}/steps/can-access/{step_key} et, si bloqué,
 * déclenche un toast (via sonner) puis redirige vers la bonne étape.
 */
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { api, apiCall } from "./api";

const STEP_PATHS = {
  pricing:  (id) => `/sites/${id}/pricing`,
  import:   (id) => `/sites/${id}/sourcing`,
  upsells:  (id) => `/sites/${id}/upsells`,
  forecast: (id) => `/sites/${id}/forecast`,
  branding: (id) => `/sites/${id}/branding`,
  pages:    (id) => `/sites/${id}/pages`,
  content:  (id) => `/sites/${id}/blog-posts`,
  seo:      (id) => `/sites/${id}/seo`,
  qa:       (id) => `/sites/${id}`,
};

export function useStepGuard(siteId, stepKey) {
  const navigate = useNavigate();
  const [allowed, setAllowed] = useState(false);
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    if (!siteId || !stepKey) {
      setChecking(false);
      setAllowed(true);
      return;
    }
    let cancelled = false;
    (async () => {
      const { data, error } = await apiCall(() =>
        api.get(`/sites/${siteId}/steps/can-access/${stepKey}`)
      );
      if (cancelled) return;
      if (error) {
        // On fail-open : si l'API est KO, on n'empêche pas l'accès (le backend
        // appliquera ses propres gates HTTP 409 sur les endpoints sensibles).
        setAllowed(true);
        setChecking(false);
        return;
      }
      if (data?.allowed) {
        setAllowed(true);
      } else {
        const target = data?.redirect_to_step || "pricing";
        const reason = data?.reason || "Étape précédente à compléter";
        const detail = data?.redirect_reason || "";
        toast.warning(reason, {
          description: detail,
          duration: 5000,
        });
        const pathFn = STEP_PATHS[target] || STEP_PATHS.pricing;
        navigate(pathFn(siteId), { replace: true });
      }
      setChecking(false);
    })();
    return () => { cancelled = true; };
  }, [siteId, stepKey, navigate]);

  return { allowed, checking };
}
