import React from "react";
import {
  Receipt, CreditCard, Truck, Package, CheckCircle, XCircle, ArrowCounterClockwise,
} from "@phosphor-icons/react";

/**
 * Visual timeline for order status. Auto-derives reached steps from `status`
 * and enriches each step's date from `status_history`.
 *
 * Shared component — used by /account/orders/:id AND /track (guest lookup).
 */
const STEPS = [
  { key: "pending_payment", label: "Commande reçue", icon: Receipt },
  { key: "paid",             label: "Paiement confirmé", icon: CreditCard },
  { key: "shipped",          label: "En acheminement",  icon: Truck },
  { key: "delivered",        label: "Livrée",           icon: Package },
];

const STATUS_INDEX = {
  pending_payment: 0,
  paid: 1,
  shipped: 2,
  delivered: 3,
};

const TERMINAL = {
  cancelled: { label: "Commande annulée", icon: XCircle, color: "#BE123C", bg: "#FFE4E6" },
  refunded:  { label: "Remboursée",       icon: ArrowCounterClockwise, color: "#78716C", bg: "#F5F5F4" },
};

function findDate(history, toStatus) {
  if (!Array.isArray(history)) return null;
  const e = history.find((h) => h.to === toStatus);
  return e ? e.at : null;
}

function formatDate(iso) {
  if (!iso) return "";
  try {
    return new Date(iso).toLocaleDateString("fr-FR", { day: "2-digit", month: "long", year: "numeric", hour: "2-digit", minute: "2-digit" });
  } catch {
    return "";
  }
}

export default function OrderTimeline({ order, accent = "#B84B31" }) {
  if (!order) return null;
  const current = order.status;

  // Terminal states — render a single info banner instead of the timeline.
  if (TERMINAL[current]) {
    const t = TERMINAL[current];
    const Icon = t.icon;
    return (
      <div
        className="flex items-center gap-3 rounded-2xl border p-5"
        style={{ background: t.bg, borderColor: t.color + "40" }}
        data-testid="order-timeline-terminal"
      >
        <Icon size={24} weight="fill" style={{ color: t.color }} />
        <div>
          <div className="text-sm font-semibold" style={{ color: t.color }}>{t.label}</div>
          <div className="text-xs mt-0.5" style={{ color: t.color + "CC" }}>
            Pour toute question, contactez le service client.
          </div>
        </div>
      </div>
    );
  }

  const currentIndex = STATUS_INDEX[current] ?? -1;

  return (
    <ol className="relative" data-testid="order-timeline">
      {/* vertical line */}
      <div className="absolute left-[15px] top-3 bottom-3 w-[2px] bg-neutral-200" aria-hidden />

      {STEPS.map((step, idx) => {
        const reached = idx <= currentIndex && currentIndex >= 0;
        const isCurrent = idx === currentIndex;
        const Icon = reached ? CheckCircle : step.icon;
        const dateKey = step.key === "pending_payment" ? order.created_at : findDate(order.status_history, step.key);

        return (
          <li key={step.key} className="relative pl-12 pb-6 last:pb-0" data-testid={`timeline-step-${step.key}`}>
            <div
              className="absolute left-0 top-0 w-8 h-8 rounded-full flex items-center justify-center transition"
              style={{
                background: reached ? accent : "#F5F2EB",
                color: reached ? "#FFFFFF" : "#A8A29E",
                boxShadow: isCurrent ? `0 0 0 4px ${accent}22` : undefined,
              }}
            >
              <Icon size={16} weight={reached ? "fill" : "bold"} />
            </div>
            <div className="pt-1">
              <div className={`text-sm font-medium ${reached ? "text-neutral-900" : "text-neutral-400"}`}>
                {step.label}
                {isCurrent && (
                  <span className="ml-2 text-[10px] uppercase tracking-widest font-bold" style={{ color: accent }}>
                    En cours
                  </span>
                )}
              </div>
              {dateKey && reached && (
                <div className="text-xs text-neutral-500 mt-0.5">{formatDate(dateKey)}</div>
              )}
              {step.key === "shipped" && reached && order.tracking_number && (
                <div className="mt-1 text-xs">
                  <span className="text-neutral-500">Suivi : </span>
                  <TrackingLink carrier={order.carrier} number={order.tracking_number} accent={accent} />
                </div>
              )}
            </div>
          </li>
        );
      })}
    </ol>
  );
}

function TrackingLink({ carrier, number, accent }) {
  const href = buildTrackingUrl(carrier, number);
  return href ? (
    <a
      href={href}
      target="_blank"
      rel="noreferrer"
      className="inline-flex items-center gap-1 font-mono text-[12px] underline underline-offset-2"
      style={{ color: accent }}
      data-testid="tracking-link"
    >
      {carrier ? `${carrier} · ` : ""}{number}
    </a>
  ) : (
    <span className="font-mono text-[12px] text-neutral-700">{carrier ? `${carrier} · ` : ""}{number}</span>
  );
}

function buildTrackingUrl(carrier, number) {
  if (!number) return "";
  const c = (carrier || "").toLowerCase();
  if (c.includes("coliss") || c.includes("laposte") || c.includes("la poste")) {
    return `https://www.laposte.fr/outils/suivre-vos-envois?code=${encodeURIComponent(number)}`;
  }
  if (c.includes("chronopost")) return `https://www.chronopost.fr/tracking-no-cms/suivi-page?listeNumerosLT=${encodeURIComponent(number)}`;
  if (c.includes("mondial") || c.includes("relay")) return `https://www.mondialrelay.fr/suivi-de-colis?numeroExpedition=${encodeURIComponent(number)}`;
  if (c.includes("dhl")) return `https://www.dhl.com/fr-fr/home/tracking/tracking-parcel.html?tracking-id=${encodeURIComponent(number)}`;
  if (c.includes("ups")) return `https://www.ups.com/track?tracknum=${encodeURIComponent(number)}`;
  if (c.includes("fedex")) return `https://www.fedex.com/fedextrack/?trknbr=${encodeURIComponent(number)}`;
  if (c.includes("gls")) return `https://gls-group.eu/FR/fr/suivi-colis?match=${encodeURIComponent(number)}`;
  return "";
}
