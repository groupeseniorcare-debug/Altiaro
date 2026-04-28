import React, { useState } from "react";
import { useGeo } from "../../hooks/useGeo";

/**
 * Phase D' — Bandeau de bienvenue subtil affiché aux visiteurs détectés au
 * Royaume-Uni quand la langue/devise courante ne matche pas (ex. ils tombent
 * sur la version FR par défaut).
 *
 * 1:1 GBP/EUR : on affiche les prix en £ avec le même nombre que l'EUR.
 *
 * Fermable, persistance localStorage.
 */
const STORAGE_KEY = "altiaro_uk_banner_dismissed";

export default function UkWelcomeBanner({ currentLang }) {
  const geo = useGeo();
  const [dismissed, setDismissed] = useState(() => {
    try { return localStorage.getItem(STORAGE_KEY) === "1"; } catch (_e) { return false; }
  });

  if (!geo.loaded || dismissed) return null;
  if (geo.country !== "GB") return null;

  // Si la langue actuelle est déjà 'en' ET la devise détectée est GBP, pas besoin du bandeau.
  const langOk = currentLang === "en";
  if (langOk) return null;

  const handleDismiss = () => {
    try { localStorage.setItem(STORAGE_KEY, "1"); } catch (_e) { /* noop */ }
    setDismissed(true);
  };

  return (
    <div
      data-testid="uk-welcome-banner"
      className="bg-[#0B1F3A] text-white text-[12.5px] py-2.5 px-4 flex items-center justify-center gap-3 flex-wrap"
    >
      <span>
        🇬🇧 You're in the United Kingdom — prices in <strong>£ (GBP)</strong> with local delivery.
      </span>
      <button
        type="button"
        onClick={handleDismiss}
        data-testid="uk-welcome-dismiss"
        className="ml-2 text-white/70 hover:text-white text-[11px] underline"
      >
        Dismiss
      </button>
    </div>
  );
}
