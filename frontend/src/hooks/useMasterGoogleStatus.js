import { useEffect, useState } from "react";
import { api, apiCall } from "../lib/api";
import { useAuth } from "../lib/auth";

/**
 * Hook qui interroge `/admin/google/master/status` (Master OAuth Altiaro).
 *
 * Comportement :
 *  - Admin (rôle = admin) → appel réel → on dérive { connected, services }.
 *  - Operator / Concepteur → AUCUN appel réseau (économise les 403 en boucle
 *    qui polluaient les logs backend). On suppose `connected=true` (le master
 *    est forcément géré côté plateforme, le concepteur n'a pas à agir dessus).
 *    Cela permet de masquer tous les CTAs site-level redondants.
 *
 * Fix Phase 3.0 (2026-05-04) : ajout du guard `user.role === 'admin'` avant
 * l'appel réseau. Avant ce fix, chaque mount d'un composant consommant ce hook
 * (SiteDetail, SiteSEO, GSCConnectCard) émettait un GET qui revenait en 403
 * pour tous les concepteurs. Spam logs éliminé.
 *
 * Retour : { loading, connected, configured, googleEmail, services, forbidden }
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

const OPERATOR_ASSUME_CONNECTED = {
  loading: false,
  connected: true,
  configured: true,
  googleEmail: null,
  services: { gsc: true, gmc: true, ads: true, ga4: true },
  forbidden: true,
};

export default function useMasterGoogleStatus() {
  const { user } = useAuth();
  const isAdmin = user && user.role === "admin";

  const [state, setState] = useState(() =>
    isAdmin
      ? {
          loading: true,
          connected: false,
          configured: false,
          googleEmail: null,
          services: { gsc: false, gmc: false, ads: false, ga4: false },
          forbidden: false,
        }
      : OPERATOR_ASSUME_CONNECTED
  );

  useEffect(() => {
    // Concepteur / rôle non-admin : zéro call réseau, on assume "OK côté plateforme".
    if (!isAdmin) {
      setState(OPERATOR_ASSUME_CONNECTED);
      return () => {};
    }

    let cancelled = false;
    (async () => {
      const { data, error, rawDetail } = await apiCall(() =>
        api.get("/admin/google/master/status")
      );
      if (cancelled) return;
      // 403 inattendu côté admin → on retombe gracieusement sur "assume connected".
      const status = rawDetail?.status || rawDetail?.statusCode;
      if (error && (status === 403 || /admin/i.test(error || ""))) {
        setState(OPERATOR_ASSUME_CONNECTED);
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
      // Erreur réseau → on ne masque rien (legacy behaviour).
      setState((prev) => ({ ...prev, loading: false }));
    })();
    return () => {
      cancelled = true;
    };
  }, [isAdmin]);

  return state;
}
