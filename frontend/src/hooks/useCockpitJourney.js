import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api, apiCall } from "../lib/api";

/**
 * useCockpitJourney — hook réactif qui expose l'état du parcours cockpit
 * pour un site donné.
 *
 * API retournée :
 *   {
 *     loading:          true pendant le premier fetch
 *     steps:            [{ key, label, completed, manual_validated, reason, ... }, ...]
 *     currentStepKey:   key de l'étape courante (ou null)
 *     currentStepIndex: 1-based (ou 0 si inconnu)
 *     totalSteps:       10
 *     progressPct:      0..100
 *     allCompleted:     bool
 *     refetch:          () => Promise<void> — refresh manuel
 *     error:            string | null
 *   }
 *
 * Polling :
 *  - toutes les POLL_INTERVAL_MS (8 s) quand l'onglet a le focus
 *  - suspendu quand `document.visibilityState === 'hidden'` (réactivé au retour)
 *  - écoute l'évènement custom `cf_steps_changed` (déjà émis ailleurs dans l'app)
 *    pour déclencher un refresh instantané après une mutation côté UI
 *
 * Objectif : quand une étape bascule `completed: false → true` côté backend
 * (ex : cron APScheduler, validate-step POST, IA async…), l'UI se met à jour
 * dans les ≤ 8 s sans que l'user ait à recharger la page. Le bouton
 * « Continuer » devient alors actif automatiquement.
 */

const POLL_INTERVAL_MS = 8000;

export default function useCockpitJourney(siteId) {
  const [journey, setJourney] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const cancelledRef = useRef(false);
  const timerRef = useRef(null);

  const fetchOnce = useCallback(async () => {
    if (!siteId) return;
    const { data, error: err } = await apiCall(() => api.get(`/sites/${siteId}/journey`));
    if (cancelledRef.current) return;
    if (err) {
      setError(err);
    } else if (data) {
      setJourney(data);
      setError(null);
    }
    setLoading(false);
  }, [siteId]);

  // Initial fetch + polling avec gestion du focus onglet.
  useEffect(() => {
    cancelledRef.current = false;
    if (!siteId) {
      setLoading(false);
      return () => {};
    }

    // Fetch immédiat au mount / changement de site.
    fetchOnce();

    const tick = () => {
      if (document.visibilityState === "visible") {
        fetchOnce();
      }
    };
    timerRef.current = window.setInterval(tick, POLL_INTERVAL_MS);

    // Refresh immédiat au retour de focus (après un OAuth Google par exemple,
    // ou après un export vers un autre onglet).
    const onVisibilityChange = () => {
      if (document.visibilityState === "visible") {
        fetchOnce();
      }
    };
    document.addEventListener("visibilitychange", onVisibilityChange);

    // Écoute l'évènement custom émis par les composants qui mutent le site
    // (ProductImportPanel, BrandWizard, etc.) pour refresh instantané.
    const onStepsChanged = () => fetchOnce();
    window.addEventListener("cf_steps_changed", onStepsChanged);

    return () => {
      cancelledRef.current = true;
      if (timerRef.current) window.clearInterval(timerRef.current);
      document.removeEventListener("visibilitychange", onVisibilityChange);
      window.removeEventListener("cf_steps_changed", onStepsChanged);
    };
  }, [siteId, fetchOnce]);

  const derived = useMemo(() => {
    const steps = (journey && journey.steps) || [];
    const total = steps.length || 10;
    const completed = steps.filter((s) => s.completed).length;
    const currentKey = journey?.current_step || null;
    // 1-based index de l'étape courante (non complétée) ; si toutes sont OK,
    // renvoie `total` (on est à la fin).
    let currentIdx = steps.findIndex((s) => s.key === currentKey);
    if (currentIdx === -1) {
      currentIdx = steps.findIndex((s) => !s.completed);
      if (currentIdx === -1) currentIdx = total - 1;
    }
    return {
      steps,
      currentStepKey: currentKey || (steps[currentIdx] && steps[currentIdx].key) || null,
      currentStepIndex: currentIdx + 1,
      totalSteps: total,
      progressPct: total > 0 ? Math.round((completed / total) * 100) : 0,
      completedCount: completed,
      allCompleted: !!journey?.all_completed,
    };
  }, [journey]);

  const getStep = useCallback(
    (stepKey) => (derived.steps || []).find((s) => s.key === stepKey) || null,
    [derived.steps]
  );

  return {
    loading,
    error,
    ...derived,
    getStep,
    refetch: fetchOnce,
  };
}
