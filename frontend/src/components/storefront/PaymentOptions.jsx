import React from "react";
import { CreditCard, Lock } from "@phosphor-icons/react";
import { t } from "../../lib/i18n";

/**
 * Payment options — affichage épuré des moyens de paiement + 3× sans frais.
 * Card grise premium, texte concis, logos monochromes.
 */
export default function PaymentOptions({ price, currency = "EUR", design, lang = "fr" }) {
  const primary = design?.brand?.primary_color || "#B84B31";
  const showInstallments = price >= 100;
  const installment = price ? (price / 3).toFixed(2).replace(".", ",") : "0,00";
  const symbol = currency === "EUR" ? "€" : currency;

  return (
    <div className="bg-[#F5F2EB] rounded-2xl p-4 md:p-5" data-testid="payment-options">
      {showInstallments ? (
        <div className="flex items-start gap-3">
          <div
            className="w-11 h-11 rounded-xl flex items-center justify-center shrink-0"
            style={{ background: "white", color: primary }}
          >
            <CreditCard size={22} weight="duotone" />
          </div>
          <div className="flex-1">
            <div className="text-[16px] font-semibold text-neutral-900">
              ou <span style={{ color: primary }}>3 × {installment} {symbol}</span> sans frais
            </div>
            <div className="text-[13px] text-neutral-500 mt-0.5">
              Paiement en 3 fois par carte bancaire
            </div>
          </div>
        </div>
      ) : (
        <div className="flex items-center gap-2 text-sm text-neutral-700">
          <Lock size={14} weight="fill" style={{ color: primary }} />
          <span>Paiement 100% sécurisé · données chiffrées SSL</span>
        </div>
      )}

      {/* Payment method badges */}
      <div className="flex items-center gap-1.5 flex-wrap mt-4 pt-4 border-t border-white/60" data-testid="payment-methods">
        {t(lang, "payment_methods_short").split(",").map((raw) => {
          const m = raw.trim();
          if (!m) return null;
          return (
            <span
              key={m}
              className="px-2 py-1 rounded bg-white text-neutral-700 text-[10.5px] font-medium uppercase tracking-wider"
            >
              {m}
            </span>
          );
        })}
      </div>
    </div>
  );
}
