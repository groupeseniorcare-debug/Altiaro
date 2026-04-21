import React from "react";
import { Truck, Lightning, MapPin } from "@phosphor-icons/react";

/**
 * Delivery estimate — affiche une date de livraison estimée à J+3 ouvrée.
 *
 * Fonctionnement :
 *  - Calcule la date de livraison en sautant les week-ends
 *  - Si commande avant 14h, le jour de commande compte comme J0 (expédition jour même)
 *  - Sinon, J0 = lendemain ouvré
 *
 * Design : carte grise premium, icône camion, texte épuré.
 */
export default function DeliveryEstimate({ design, compact = false }) {
  const primary = design?.brand?.primary_color || "#B84B31";
  const date = computeDeliveryDate(new Date());
  const formatted = formatFrDate(date);
  const cutoff = new Date();
  cutoff.setHours(14, 0, 0, 0);
  const now = new Date();
  const beforeCutoff = now < cutoff && now.getDay() >= 1 && now.getDay() <= 5;

  if (compact) {
    return (
      <div className="flex items-center gap-2 text-sm text-neutral-700" data-testid="delivery-estimate-compact">
        <Truck size={16} weight="fill" style={{ color: primary }} />
        <span>
          Livraison estimée le <span className="font-semibold text-neutral-900">{formatted}</span>
        </span>
      </div>
    );
  }

  return (
    <div
      className="bg-[#F5F2EB] rounded-2xl p-4 md:p-5 flex items-start gap-3"
      data-testid="delivery-estimate"
    >
      <div
        className="w-11 h-11 rounded-xl flex items-center justify-center shrink-0"
        style={{ background: "white", color: primary }}
      >
        <Truck size={22} weight="duotone" />
      </div>
      <div className="flex-1">
        <div className="text-sm text-neutral-600 mb-0.5">Livraison estimée</div>
        <div className="text-[16px] font-semibold text-neutral-900">
          {formatted}
        </div>
        {beforeCutoff ? (
          <div className="flex items-center gap-1.5 text-[13px] mt-1.5" style={{ color: primary }}>
            <Lightning size={13} weight="fill" />
            <span>Commandez avant 14h pour un envoi aujourd'hui</span>
          </div>
        ) : (
          <div className="flex items-center gap-1.5 text-[13px] text-neutral-500 mt-1.5">
            <MapPin size={13} weight="fill" />
            <span>France métropolitaine · suivi par SMS</span>
          </div>
        )}
      </div>
    </div>
  );
}

function computeDeliveryDate(from) {
  const d = new Date(from);
  // Add 3 working days (skip Sat/Sun)
  let added = 0;
  while (added < 3) {
    d.setDate(d.getDate() + 1);
    const day = d.getDay();
    if (day !== 0 && day !== 6) added += 1;
  }
  return d;
}

function formatFrDate(date) {
  const days = ["dimanche", "lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi"];
  const months = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"];
  return `${days[date.getDay()]} ${date.getDate()} ${months[date.getMonth()]}`;
}
