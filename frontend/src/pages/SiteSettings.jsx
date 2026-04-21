import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { api, apiCall } from "../lib/api";
import Layout from "../components/Layout";
import {
  ArrowLeft, ShieldCheck, Truck, CreditCard, Receipt,
  ArrowsClockwise, Clock, Lock,
} from "@phosphor-icons/react";

const COUNTRY_LABEL = {
  FR: "🇫🇷 France", BE: "🇧🇪 Belgique", LU: "🇱🇺 Luxembourg",
  DE: "🇩🇪 Allemagne", NL: "🇳🇱 Pays-Bas", CH: "🇨🇭 Suisse", UK: "🇬🇧 Royaume-Uni",
};

const METHOD_LABEL = {
  creditcard: "Carte bancaire (Visa, Mastercard, Amex)",
  bancontact: "Bancontact (Belgique)",
  ideal: "iDEAL (Pays-Bas)",
  applepay: "Apple Pay",
  googlepay: "Google Pay",
  paypal: "PayPal (via Mollie)",
};

export default function SiteSettings() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [site, setSite] = useState(null);
  const [policy, setPolicy] = useState(null);

  useEffect(() => {
    apiCall(() => api.get(`/sites/${id}`)).then(({ data }) => data && setSite(data));
    apiCall(() => api.get(`/platform/policy`)).then(({ data }) => data && setPolicy(data));
  }, [id]);

  if (!policy || !site)
    return <Layout><div className="p-10 text-neutral-600">Chargement…</div></Layout>;

  return (
    <Layout>
      <div className="p-8 md:p-12 max-w-[1200px] mx-auto w-full">
        <button
          onClick={() => navigate(`/sites/${id}`)}
          data-testid="settings-back"
          className="text-sm text-neutral-600 hover:text-neutral-900 flex items-center gap-1.5 mb-6"
        >
          <ArrowLeft size={14} /> Retour au cockpit
        </button>

        <div className="flex items-center gap-3 mb-3">
          <Lock size={28} weight="duotone" className="text-neutral-700" />
          <h1 className="text-3xl font-semibold" style={{ fontFamily: "Fraunces, serif" }}>
            Politique Altiaro appliquée à ce site
          </h1>
        </div>
        <p className="text-sm text-neutral-600 mb-10 max-w-3xl leading-relaxed">
          Pour garantir la cohérence de toutes les boutiques Altiaro, la politique commerciale
          (TVA, livraison, paiement, retour, garantie) est <strong>fixée au niveau plateforme</strong>
          et s'applique automatiquement à ton site <strong>« {site.name} »</strong>. Rien à configurer de ton côté.
        </p>

        <div className="space-y-6">
          <PolicyBlock
            icon={Receipt}
            title="TVA & fiscalité"
            sub="Taux appliqués automatiquement selon le pays de livraison"
          >
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
              {Object.entries(policy.taxes.rates_by_country).map(([c, rate]) => (
                <div key={c} className="p-3 rounded-xl bg-neutral-50 border border-neutral-200">
                  <div className="text-xs text-neutral-500">{COUNTRY_LABEL[c] || c}</div>
                  <div className="text-xl font-semibold mt-0.5">{rate}%</div>
                </div>
              ))}
            </div>
            <p className="text-xs text-neutral-500">{policy.taxes.explanation}</p>
          </PolicyBlock>

          <PolicyBlock
            icon={Truck}
            title={policy.shipping.label}
            sub="Altiaro prend en charge les frais de livraison sur tous les sites"
          >
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
              {Object.entries(policy.shipping.delivery_estimate).map(([c, eta]) => (
                <div key={c} className="p-3 rounded-xl bg-neutral-50 border border-neutral-200">
                  <div className="text-xs text-neutral-500">{COUNTRY_LABEL[c] || c}</div>
                  <div className="text-sm font-medium mt-0.5">{eta}</div>
                </div>
              ))}
            </div>
            <p className="text-xs text-neutral-500">{policy.shipping.explanation}</p>
          </PolicyBlock>

          <PolicyBlock
            icon={CreditCard}
            title={`Paiement — ${policy.payment.provider}`}
            sub="Même stack de paiement sur tous les sites Altiaro"
          >
            <div className="flex flex-wrap gap-2 mb-3">
              {policy.payment.methods_enabled.map((m) => (
                <span key={m} className="px-3 py-1.5 rounded-full bg-emerald-50 text-emerald-800 text-xs font-medium border border-emerald-200">
                  ✓ {METHOD_LABEL[m] || m}
                </span>
              ))}
            </div>
            <div className="text-sm text-neutral-700 mb-2">
              Virement bancaire B2B activé automatiquement à partir de <strong>{policy.payment.b2b_bank_transfer_min}€</strong> de panier.
            </div>
            <p className="text-xs text-neutral-500">{policy.payment.explanation}</p>
          </PolicyBlock>

          <PolicyBlock
            icon={ArrowsClockwise}
            title={policy.returns.label}
            sub="Frais de retour pris en charge par Altiaro"
          >
            <p className="text-xs text-neutral-500">{policy.returns.explanation}</p>
          </PolicyBlock>

          <PolicyBlock
            icon={ShieldCheck}
            title={policy.warranty.label}
            sub={`Garantie légale de ${policy.warranty.years} ans incluse sur tous les produits`}
          >
            <p className="text-xs text-neutral-500">{policy.warranty.explanation}</p>
          </PolicyBlock>

          <PolicyBlock
            icon={Clock}
            title="Service client"
            sub={`Réponse sous ${policy.customer_service.response_time_sla} · ${policy.customer_service.hours}`}
          >
            <div className="flex gap-2">
              {policy.customer_service.channels.map((ch) => (
                <span key={ch} className="px-3 py-1 rounded-full bg-neutral-100 text-neutral-700 text-xs capitalize">
                  {ch}
                </span>
              ))}
            </div>
          </PolicyBlock>
        </div>
      </div>
    </Layout>
  );
}

function PolicyBlock({ icon: Icon, title, sub, children }) {
  return (
    <div className="bg-white border border-neutral-200 rounded-2xl p-6">
      <div className="flex items-start gap-4 mb-4">
        <div className="w-11 h-11 rounded-xl bg-neutral-100 flex items-center justify-center shrink-0">
          <Icon size={22} weight="duotone" className="text-neutral-700" />
        </div>
        <div className="flex-1">
          <div className="text-lg font-semibold text-neutral-900">{title}</div>
          <div className="text-sm text-neutral-500 mt-0.5">{sub}</div>
        </div>
        <span className="text-[10px] uppercase tracking-widest text-neutral-400 font-medium">
          Non modifiable
        </span>
      </div>
      {children}
    </div>
  );
}
