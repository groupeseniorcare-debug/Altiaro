import { useEffect, useState } from "react";
import { api, apiCall } from "../lib/api";

/**
 * Hook qui interroge `/admin/google/master/status` (Master OAuth Altiaro).
 *
 * Comportement :
 *  - Admin (rôle = admin) → reçoit la vraie réponse → on dérive { connected, services }.
 *  - Operator / Concepteur → 403 → on suppose `connected=true` (le master
 *    est forcément géré côté plateforme, le concepteur n'a pas à agir dessus).
 *    Cela permet de masquer tous les CTAs site-level redondants.
 *
 * Retour : { loading, connected, configured, googleEmail, services }
 *   services = { gsc, gmc, ads, ga4 } booléens.
 */
const SCOPE_TO_SERVICE = {
  "https://www.googleapis.com/auth/webmasters": "gsc",
  "https://www.googleapis.com/auth/webmasters.readonly": "gsc",
  "https://www.googleapis.com/auth/content": "gmc",
  "https://www.googleapis.com/auth/adwords": "ads",
  "https://www.googleapis.com/auth/analytics.edit": "ga4",
  "https://www.googleapis.com/auth/analytics.readonly": "ga4",
  "https://www.googleapis.com/auth/analytics": "ga4",
};

function servicesFromScopes(scopes) {
  const list = Array.isArray(scopes) ? scopes : [];
  const out = { gsc: false, gmc: false, ads: false, ga4: false };
  list.forEach((s) => {
    const k = SCOPE_TO_SERVICE[s];
    if (k) out[k] = true;
  });
  return out;
}

export default function useMasterGoogleStatus() {
  const [state, setState] = useState({
    loading: true,
    connected: false,
    configured: false,
    googleEmail: null,
    services: { gsc: false, gmc: false, ads: false, ga4: false },
    forbidden: false,
  });

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const { data, error, rawDetail } = await apiCall(() =>
        api.get("/admin/google/master/status")
      );
      if (cancelled) return;
      // 403 → on est concepteur, on assume "géré par la plateforme".
      const status = rawDetail?.status || rawDetail?.statusCode;
      if (error && (status === 403 || /admin/i.test(error || ""))) {
        setState({
          loading: false,
          connected: true,
          configured: true,
          googleEmail: null,
          services: { gsc: true, gmc: true, ads: true, ga4: true },
          forbidden: true,
        });
        return;
      }
      if (data) {
        setState({
          loading: false,
          connected: !!data.connected,
          configured: !!data.configured,
          googleEmail: data.google_email || null,
          services: servicesFromScopes(data.scopes || []),
          forbidden: false,
        });
        return;
      }
      // Erreur réseau ou autre → on ne masque rien (legacy behaviour).
      setState((prev) => ({ ...prev, loading: false }));
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return state;
}
