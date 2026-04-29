/**
 * Helpers pour la validation manuelle des étapes du cockpit.
 * Voir backend/routes/journey_gating.py::validate_step
 */
import { api, apiCall } from "./api";

/**
 * Marque l'étape comme manuellement validée par le concepteur.
 * Retourne `true` si succès, `false` sinon.
 */
export async function validateStep(siteId, stepKey) {
  if (!siteId || !stepKey) return false;
  const { data, error } = await apiCall(() =>
    api.post(`/sites/${siteId}/journey/validate-step`, { step_key: stepKey })
  );
  if (error || !data?.ok) return false;
  return true;
}

/**
 * Construit une fonction `onValidate` prête à être passée au
 * `<StepValidateCTA>`. Le composant call directement.
 */
export function buildOnValidate(siteId, stepKey, onSuccess) {
  return async () => {
    const ok = await validateStep(siteId, stepKey);
    if (ok && typeof onSuccess === "function") {
      try {
        await onSuccess();
      } catch (_) {
        /* on ignore l'erreur côté caller */
      }
    }
    return ok;
  };
}
