import React, { useEffect, useRef, useState } from "react";
import { Cookie, X, ShieldCheck } from "@phosphor-icons/react";
import { Link } from "react-router-dom";
import axios from "axios";

const BACKEND_URL = "";  // proxied via ingress in prod
const STORAGE_KEY = "altiaro_consent_v1";

/**
 * Bloc 1 sous-chantier 3 — Bannière RGPD + politique cookies.
 *
 * Affichage : modal centrée mobile, bandeau bottom desktop. 3 actions : Accepter
 * tout / Refuser tout / Personnaliser. Personnaliser ouvre un panel granular
 * (essentiels [non décochables], analytics, marketing, personnalisation).
 *
 * Le choix est stocké en localStorage (`altiaro_consent_v1`) ET POSTé à
 * /api/public/sites/{site_id}/consent pour audit (best-effort, ne bloque pas
 * l'UI si le call échoue).
 *
 * Émet `window.dispatchEvent(new Event("altiaro:consent-updated"))` à chaque
 * choix pour que les autres composants (StorefrontTracking) re-évaluent leur
 * comportement (re-bootstrap de gtag uniquement si marketing=true).
 *
 * Accessibilité : focus trap simple, ESC ferme, ARIA labels propres.
 */

const DEFAULT_CONSENT = {
  essentiels: true,           // toujours ON, non décochable
  analytics: false,
  marketing: false,
  personnalisation: false,
  decided_at: null,
  version: 1,
};

function readConsent() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object") return null;
    return { ...DEFAULT_CONSENT, ...parsed };
  } catch {
    return null;
  }
}

function persistConsent(consent, siteId) {
  const final = {
    ...DEFAULT_CONSENT,
    ...consent,
    essentiels: true,
    decided_at: new Date().toISOString(),
    version: 1,
  };
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(final)); } catch {}
  // Best-effort audit POST (don't await, don't block UI)
  if (siteId) {
    axios.post(`${BACKEND_URL}/api/public/sites/${siteId}/consent`, final).catch(() => {});
  }
  // Notify other components (StorefrontTracking) so they re-evaluate
  try { window.dispatchEvent(new Event("altiaro:consent-updated")); } catch {}
  return final;
}

export default function CookieConsentBanner({ siteId }) {
  const [visible, setVisible] = useState(false);
  const [granular, setGranular] = useState(false);
  const [choices, setChoices] = useState(DEFAULT_CONSENT);
  const closeBtnRef = useRef(null);

  useEffect(() => {
    const existing = readConsent();
    if (!existing || !existing.decided_at) {
      // Show banner with a tiny delay so it doesn't flash on every page nav
      const t = setTimeout(() => setVisible(true), 600);
      return () => clearTimeout(t);
    }
  }, []);

  // ESC closes the granular panel (back to banner) ; another ESC dismisses
  // (treats as "Refuser tout") for keyboard accessibility.
  useEffect(() => {
    if (!visible) return;
    const onKey = (e) => {
      if (e.key === "Escape") {
        if (granular) setGranular(false);
        else handleRefuse();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [visible, granular]);

  // Focus trap — when banner opens, focus the first action button
  useEffect(() => {
    if (visible && closeBtnRef.current) {
      closeBtnRef.current.focus();
    }
  }, [visible]);

  const handleAcceptAll = () => {
    persistConsent({ analytics: true, marketing: true, personnalisation: true }, siteId);
    setVisible(false);
  };
  const handleRefuse = () => {
    persistConsent({ analytics: false, marketing: false, personnalisation: false }, siteId);
    setVisible(false);
  };
  const handleSavePreferences = () => {
    persistConsent(choices, siteId);
    setVisible(false);
  };

  if (!visible) return null;

  return (
    <>
      {/* Backdrop : visible on desktop only behind the bottom banner is unnecessary,
          but on mobile the banner is centered modal and needs the dim overlay. */}
      {granular && (
        <div
          className="fixed inset-0 z-[200] bg-neutral-900/60 backdrop-blur-sm"
          aria-hidden="true"
          onClick={() => setGranular(false)}
        />
      )}

      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="cookie-consent-title"
        aria-describedby="cookie-consent-desc"
        data-testid="cookie-consent-banner"
        className={`fixed z-[210] bg-white border border-neutral-200 shadow-2xl rounded-xl ${
          granular
            ? "inset-x-4 top-1/2 -translate-y-1/2 md:inset-x-auto md:left-1/2 md:right-auto md:-translate-x-1/2 md:w-[640px] md:max-h-[80vh] overflow-y-auto"
            : "bottom-4 left-4 right-4 md:left-1/2 md:-translate-x-1/2 md:right-auto md:bottom-6 md:w-[680px]"
        }`}
        style={{ fontFamily: "Manrope, system-ui, sans-serif" }}
      >
        {!granular ? (
          <div className="p-5 md:p-6">
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 rounded-lg bg-amber-50 border border-amber-200 flex items-center justify-center shrink-0">
                <Cookie size={20} weight="duotone" className="text-amber-700" />
              </div>
              <div className="flex-1 min-w-0">
                <h2
                  id="cookie-consent-title"
                  className="text-[15px] font-semibold text-neutral-900 mb-1"
                  style={{ fontFamily: "Cormorant Garamond, Fraunces, serif" }}
                >
                  Vos préférences cookies
                </h2>
                <p id="cookie-consent-desc" className="text-[13px] text-neutral-600 leading-relaxed">
                  Nous utilisons des cookies pour assurer le bon fonctionnement du site
                  (essentiels), mesurer la performance (analytics) et personnaliser nos
                  communications (marketing). Vous pouvez accepter, refuser ou personnaliser à tout moment.{" "}
                  <Link to={siteId ? `/shop/${siteId}/cookies` : `/cookies`} className="underline text-amber-800 hover:text-amber-900">
                    En savoir plus
                  </Link>
                </p>
              </div>
              <button
                onClick={handleRefuse}
                aria-label="Fermer (équivalent refuser tout)"
                className="ml-1 -mr-1 p-1 rounded text-neutral-400 hover:text-neutral-700"
              >
                <X size={16} />
              </button>
            </div>

            <div className="mt-4 flex flex-col-reverse md:flex-row gap-2 md:gap-3">
              <button
                onClick={() => setGranular(true)}
                data-testid="cookie-consent-customize"
                className="h-10 px-4 rounded-lg border border-neutral-300 text-neutral-700 text-[13px] font-medium hover:bg-neutral-50"
              >
                Personnaliser
              </button>
              <button
                onClick={handleRefuse}
                data-testid="cookie-consent-refuse"
                className="h-10 px-4 rounded-lg border border-neutral-300 text-neutral-700 text-[13px] font-medium hover:bg-neutral-50"
              >
                Refuser tout
              </button>
              <button
                ref={closeBtnRef}
                onClick={handleAcceptAll}
                data-testid="cookie-consent-accept"
                className="h-10 px-5 rounded-lg bg-neutral-900 text-white text-[13px] font-semibold hover:bg-neutral-800 inline-flex items-center justify-center gap-1.5 md:ml-auto"
              >
                <ShieldCheck size={14} weight="bold" /> Accepter tout
              </button>
            </div>
          </div>
        ) : (
          <div className="p-5 md:p-6">
            <div className="flex items-start justify-between mb-4">
              <h2
                className="text-[16px] font-semibold text-neutral-900"
                style={{ fontFamily: "Cormorant Garamond, Fraunces, serif" }}
              >
                Personnaliser vos cookies
              </h2>
              <button
                onClick={() => setGranular(false)}
                aria-label="Retour"
                className="p-1 rounded text-neutral-400 hover:text-neutral-700"
              >
                <X size={16} />
              </button>
            </div>
            <ul className="space-y-3 mb-5">
              {[
                { key: "essentiels", title: "Essentiels", desc: "Indispensables au fonctionnement (panier, session, sécurité). Toujours actifs.", locked: true },
                { key: "analytics", title: "Mesure d'audience", desc: "Statistiques anonymes pour améliorer le site (Google Analytics 4)." },
                { key: "marketing", title: "Marketing & publicité", desc: "Pixels Google Ads / Meta pour mesurer nos campagnes." },
                { key: "personnalisation", title: "Personnalisation", desc: "Mémoriser vos préférences (langue, devise, recommandations)." },
              ].map(({ key, title, desc, locked }) => (
                <li key={key} className="flex items-start gap-3 p-3 rounded-lg border border-neutral-200 bg-neutral-50/50">
                  <div className="flex-1 min-w-0">
                    <div className="text-[13.5px] font-medium text-neutral-900">{title}</div>
                    <div className="text-[12px] text-neutral-600 mt-0.5 leading-relaxed">{desc}</div>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer shrink-0 mt-1">
                    <input
                      type="checkbox"
                      checked={locked || choices[key]}
                      disabled={locked}
                      onChange={(e) => setChoices((c) => ({ ...c, [key]: e.target.checked }))}
                      data-testid={`cookie-toggle-${key}`}
                      className="sr-only peer"
                    />
                    <div className={`w-9 h-5 rounded-full transition ${locked ? "bg-emerald-500" : (choices[key] ? "bg-neutral-900" : "bg-neutral-300")} peer-focus:ring-2 peer-focus:ring-neutral-400`}>
                      <div className={`absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full transition-transform ${(locked || choices[key]) ? "translate-x-4" : ""}`} />
                    </div>
                  </label>
                </li>
              ))}
            </ul>
            <div className="flex flex-col-reverse md:flex-row gap-2 md:gap-3 md:justify-end">
              <button
                onClick={() => setGranular(false)}
                className="h-10 px-4 rounded-lg border border-neutral-300 text-neutral-700 text-[13px] font-medium hover:bg-neutral-50"
              >
                Annuler
              </button>
              <button
                onClick={handleSavePreferences}
                data-testid="cookie-consent-save"
                className="h-10 px-5 rounded-lg bg-neutral-900 text-white text-[13px] font-semibold hover:bg-neutral-800"
              >
                Enregistrer mes choix
              </button>
            </div>
          </div>
        )}
      </div>
    </>
  );
}
