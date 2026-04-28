/**
 * Phase 2.5 — Tâche E.
 * Cartes Livraison + Paiement premium, alignées design Aesop / Hermès.
 *
 * Layout :
 *   - Desktop (≥ md) : 2 colonnes côte à côte.
 *   - Mobile (< md)  : empilées (1 colonne).
 *
 * Style :
 *   - Fond #FDFCF9 (blanc cassé très clair),
 *   - Bordure fine #E8E2D5 (ivoire),
 *   - Typo Cormorant pour le titre (hérite de `design.brand.font_heading`).
 *   - Sous-ligne sans-serif fine (tracking-tight, neutral-600).
 *   - Icônes Phosphor `weight="thin"` — sobres, monochromes, jamais criardes.
 *   - Padding généreux (p-5 md:p-6), alignement strict.
 *
 * Composant partagé → propagation auto à tous les storefronts.
 */
import React from "react";
import { Truck, CreditCard, Lock } from "@phosphor-icons/react";

function formatFrDate(date) {
  const days = ["dimanche", "lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi"];
  const months = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"];
  return `${days[date.getDay()]} ${date.getDate()} ${months[date.getMonth()]}`;
}

function computeDeliveryDate(from) {
  const d = new Date(from);
  let added = 0;
  while (added < 3) {
    d.setDate(d.getDate() + 1);
    const day = d.getDay();
    if (day !== 0 && day !== 6) added += 1;
  }
  return d;
}

function TrustCard({ Icon, eyebrow, title, sub, fontHeading }) {
  return (
    <div
      className="flex items-start gap-4 p-5 md:p-6 transition-all hover:-translate-y-[1px]"
      style={{
        background: "#FDFCF9",
        border: "1px solid #E8E2D5",
        borderRadius: "2px",
      }}
    >
      <div
        className="w-10 h-10 shrink-0 flex items-center justify-center"
        style={{
          border: "1px solid #E8E2D5",
          borderRadius: "2px",
          color: "#0A0A0A",
          background: "#FFFFFF",
        }}
      >
        <Icon size={18} weight="thin" />
      </div>
      <div className="min-w-0 flex-1">
        <div
          className="text-[10px] uppercase tracking-[0.24em] mb-1.5"
          style={{ color: "#9C8C7C" }}
        >
          {eyebrow}
        </div>
        <div
          className="text-[18px] md:text-[19px] leading-[1.15] tracking-tight font-light"
          style={{ fontFamily: fontHeading, color: "#0A0A0A" }}
        >
          {title}
        </div>
        {sub && (
          <div
            className="text-[12.5px] mt-1.5 leading-snug"
            style={{ color: "#6B6B6B", fontWeight: 300 }}
          >
            {sub}
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * Props :
 *   - price : nombre (pour calcul mensualité 3x)
 *   - currency : "EUR" / …
 *   - design : objet design du site (brand.font_heading)
 *   - lang : code langue (fr par défaut)
 */
export default function DeliveryPaymentInfo({ price = 0, currency = "EUR", design, lang = "fr" }) {
  const fontHeading = `"${design?.brand?.font_heading || "Cormorant Garamond"}", serif`;
  const date = computeDeliveryDate(new Date());
  const deliveryTitle = formatFrDate(date);

  const showInstallments = price >= 100;
  const symbol = currency === "EUR" ? "€" : currency;
  const installment = price ? (price / 3).toFixed(2).replace(".", ",") : "0,00";

  const deliverySub = {
    fr: "Livraison offerte · France métropolitaine · suivi par SMS",
    en: "Free delivery · Mainland France · SMS tracking",
    de: "Kostenlose Lieferung · Festland Frankreich · SMS-Tracking",
    nl: "Gratis levering · Franse vasteland · SMS-tracking",
    it: "Consegna gratuita · Francia metropolitana · tracciamento SMS",
    es: "Entrega gratuita · Francia metropolitana · seguimiento SMS",
  }[lang] || "Livraison offerte · France métropolitaine · suivi par SMS";

  const installmentsSub = {
    fr: `3 mensualités de ${installment} ${symbol} · sans frais, par carte bancaire`,
    en: `3 monthly payments of ${installment} ${symbol} · interest-free, by credit card`,
    de: `3 Monatsraten à ${installment} ${symbol} · zinsfrei, per Kreditkarte`,
    nl: `3 maandtermijnen van ${installment} ${symbol} · renteloos, per creditcard`,
    it: `3 rate mensili di ${installment} ${symbol} · senza interessi, con carta`,
    es: `3 cuotas mensuales de ${installment} ${symbol} · sin intereses, con tarjeta`,
  }[lang] || `3 mensualités de ${installment} ${symbol} · sans frais`;

  const secureSub = {
    fr: "Paiement 100 % sécurisé · données chiffrées SSL · sans frais cachés",
    en: "100% secure payment · SSL-encrypted · no hidden fees",
    de: "100 % sichere Zahlung · SSL-verschlüsselt · keine versteckten Gebühren",
    nl: "100% veilige betaling · SSL-versleuteld · geen verborgen kosten",
    it: "Pagamento 100% sicuro · crittografia SSL · nessun costo nascosto",
    es: "Pago 100% seguro · cifrado SSL · sin cargos ocultos",
  }[lang] || "Paiement 100 % sécurisé · données chiffrées SSL";

  const eyebrowDelivery = {
    fr: "Livraison", en: "Delivery", de: "Lieferung",
    nl: "Bezorging", it: "Consegna", es: "Entrega",
  }[lang] || "Livraison";

  const eyebrowPayment = {
    fr: "Paiement", en: "Payment", de: "Zahlung",
    nl: "Betaling", it: "Pagamento", es: "Pago",
  }[lang] || "Paiement";

  const titleDelivery = {
    fr: "Livraison offerte", en: "Free delivery", de: "Kostenlose Lieferung",
    nl: "Gratis levering", it: "Consegna gratuita", es: "Entrega gratuita",
  }[lang] || "Livraison offerte";

  const titleInstallments = {
    fr: "Paiement en 3 fois", en: "Pay in 3 instalments", de: "Zahlung in 3 Raten",
    nl: "Betalen in 3 termijnen", it: "Pagamento in 3 rate", es: "Pago en 3 veces",
  }[lang] || "Paiement en 3 fois";

  const titleSecure = {
    fr: "Paiement sécurisé", en: "Secure payment", de: "Sichere Zahlung",
    nl: "Veilige betaling", it: "Pagamento sicuro", es: "Pago seguro",
  }[lang] || "Paiement sécurisé";

  const estimatedLabel = {
    fr: "Livraison estimée",
    en: "Estimated delivery",
    de: "Voraussichtliche Lieferung",
    nl: "Geschatte levering",
    it: "Consegna prevista",
    es: "Entrega estimada",
  }[lang] || "Livraison estimée";

  // Sous-ligne delivery : date + ligne de contexte
  const deliveryDisplaySub = (
    <span>
      <span style={{ color: "#0A0A0A", fontWeight: 400 }}>
        {estimatedLabel} · {deliveryTitle}
      </span>
      <span className="block mt-1">{deliverySub}</span>
    </span>
  );

  return (
    <div
      className="grid grid-cols-1 md:grid-cols-2 gap-3"
      data-testid="delivery-payment-info"
    >
      <TrustCard
        Icon={Truck}
        eyebrow={eyebrowDelivery}
        title={titleDelivery}
        sub={deliveryDisplaySub}
        fontHeading={fontHeading}
      />
      {showInstallments ? (
        <TrustCard
          Icon={CreditCard}
          eyebrow={eyebrowPayment}
          title={titleInstallments}
          sub={installmentsSub}
          fontHeading={fontHeading}
        />
      ) : (
        <TrustCard
          Icon={Lock}
          eyebrow={eyebrowPayment}
          title={titleSecure}
          sub={secureSub}
          fontHeading={fontHeading}
        />
      )}
    </div>
  );
}
