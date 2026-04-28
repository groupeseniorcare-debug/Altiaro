import React from "react";
import { useGeo, formatPrice } from "../../hooks/useGeo";

/**
 * <Price amount={10} /> → affiche `10,00 €` ou `£10.00` selon useGeo().
 * Parité 1:1 GBP/EUR (pas de conversion taux) — décision produit Altiaro.
 *
 * Props :
 *   - amount: number | string (montant numérique en EUR ou en GBP, identique)
 *   - currencyOverride: optionnel ('EUR' | 'GBP' | 'USD'), force la devise
 *   - className: classes Tailwind transmises au <span>
 */
export default function Price({ amount, currencyOverride, className, "data-testid": testId, ...rest }) {
  const geo = useGeo();
  const currency = currencyOverride || geo.currency || "EUR";
  const symbol = currencyOverride
    ? (currencyOverride === "GBP" ? "£" : currencyOverride === "USD" ? "$" : "€")
    : geo.currency_symbol;
  return (
    <span className={className} data-testid={testId || "price"} {...rest}>
      {formatPrice(amount, currency, symbol)}
    </span>
  );
}
