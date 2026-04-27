/**
 * Fix 3 — Scroll restoration global pour la SPA Altiaro.
 *
 * React Router 7 ne reset pas automatiquement le scroll lors d'un changement
 * de route. Sans ce composant, la page produit s'ouvre parfois au scroll
 * position du clic (ex: bas de la home → fiche produit ouverte sur le
 * footer).
 *
 * Comportement :
 * - À chaque changement de pathname OU search → `window.scrollTo(0, 0)`
 * - Utilise `behavior: "instant"` pour éviter le smooth scroll qui flickers
 * - Ne reset PAS si seule la `hash` change (permet `#section-id` natif)
 *
 * Monté une seule fois au top de App.js (juste sous BrowserRouter).
 */
import { useEffect } from "react";
import { useLocation } from "react-router-dom";

export default function ScrollToTop() {
  const { pathname, search } = useLocation();

  useEffect(() => {
    // Use a small timeout to ensure layout has been painted (avoids race with
    // pages that load async data and resize the DOM during navigation).
    requestAnimationFrame(() => {
      window.scrollTo({ top: 0, left: 0, behavior: "instant" });
    });
  }, [pathname, search]);

  return null;
}
