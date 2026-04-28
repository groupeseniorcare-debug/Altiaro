import { useEffect, useState } from "react";
import { api } from "../lib/api";

/**
 * Phase D' — Détection pays/langue/devise.
 *
 * Cache localStorage (12h) pour éviter de spammer l'endpoint à chaque page.
 *
 * Retourne :
 *   { country, language, currency, currency_symbol, loaded }
 *
 * 1:1 EUR / GBP : si country = "GB", currency = "GBP" (même montant).
 */
const STORAGE_KEY = "altiaro_geo";
const TTL_MS = 12 * 3600 * 1000;

const DEFAULT = {
  country: null,
  language: "fr",
  currency: "EUR",
  currency_symbol: "€",
  loaded: false,
};

export function useGeo() {
  const [geo, setGeo] = useState(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return DEFAULT;
      const cached = JSON.parse(raw);
      if (cached.expires_at && cached.expires_at > Date.now()) {
        return { ...cached.payload, loaded: true };
      }
    } catch (_e) { /* noop */ }
    return DEFAULT;
  });

  useEffect(() => {
    if (geo.loaded) return;
    let cancelled = false;
    (async () => {
      try {
        const { data } = await api.get("/geo/detect");
        if (cancelled || !data) return;
        const payload = {
          country: data.country || null,
          language: data.language || "fr",
          currency: data.currency || "EUR",
          currency_symbol: data.currency_symbol || "€",
        };
        try {
          localStorage.setItem(
            STORAGE_KEY,
            JSON.stringify({ payload, expires_at: Date.now() + TTL_MS }),
          );
        } catch (_e) { /* noop */ }
        setGeo({ ...payload, loaded: true });
      } catch (_e) {
        setGeo({ ...DEFAULT, loaded: true });
      }
    })();
    return () => { cancelled = true; };
  }, [geo.loaded]);

  return geo;
}

/** Format un montant numérique selon la devise détectée (1:1 EUR/GBP). */
export function formatPrice(amount, currency = "EUR", symbol) {
  const n = typeof amount === "number" ? amount : parseFloat(amount) || 0;
  const sym = symbol || (currency === "GBP" ? "£" : currency === "USD" ? "$" : "€");
  if (currency === "GBP" || currency === "USD") {
    // £/$ avant le nombre, séparateur point, 2 décimales
    return `${sym}${n.toFixed(2)}`;
  }
  // €, format français : 10,00 €
  return `${n.toFixed(2).replace(".", ",")} ${sym}`;
}
