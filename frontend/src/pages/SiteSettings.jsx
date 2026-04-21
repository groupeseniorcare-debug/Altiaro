import React, { useEffect, useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { api, apiCall } from "../lib/api";
import Layout from "../components/Layout";
import { ArrowLeft, FloppyDisk, Gear, Receipt, Truck, CreditCard, EnvelopeSimple } from "@phosphor-icons/react";
import { toast } from "sonner";

const TABS = [
  { id: "taxes", label: "Taxes", icon: Receipt },
  { id: "shipping", label: "Livraison", icon: Truck },
  { id: "payment_methods", label: "Paiement", icon: CreditCard },
  { id: "emails", label: "Emails", icon: EnvelopeSimple },
];

export default function SiteSettings() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [site, setSite] = useState(null);
  const [settings, setSettings] = useState(null);
  const [tab, setTab] = useState("taxes");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    apiCall(() => api.get(`/sites/${id}`)).then(({ data }) => data && setSite(data));
    apiCall(() => api.get(`/sites/${id}/settings`)).then(({ data }) => data && setSettings(data));
  }, [id]);

  const save = async () => {
    setSaving(true);
    const { error } = await apiCall(() =>
      api.put(`/sites/${id}/settings`, settings)
    );
    setSaving(false);
    if (error) toast.error(error);
    else toast.success("Paramètres enregistrés");
  };

  if (!settings || !site)
    return (
      <Layout><div className="p-10 text-neutral-600">Chargement…</div></Layout>
    );

  return (
    <Layout>
      <div className="p-8 md:p-12 max-w-[1400px] mx-auto w-full">
        <button
          onClick={() => navigate(`/sites/${id}`)}
          data-testid="settings-back"
          className="text-sm text-neutral-600 hover:text-neutral-900 flex items-center gap-1.5 mb-6"
        >
          <ArrowLeft size={14} /> Retour au cockpit
        </button>

        <div className="flex items-center gap-3 mb-8">
          <Gear size={28} weight="duotone" className="text-neutral-700" />
          <div>
            <h1 className="text-3xl font-semibold" style={{ fontFamily: "Fraunces, serif" }}>
              Paramètres de la boutique
            </h1>
            <div className="text-sm text-neutral-500 mt-1">{site.name}</div>
          </div>
        </div>

        <div className="flex gap-2 mb-6 border-b border-neutral-200">
          {TABS.map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              data-testid={`settings-tab-${t.id}`}
              className={`h-10 px-4 flex items-center gap-2 text-sm font-medium border-b-2 transition ${
                tab === t.id ? "border-neutral-900 text-neutral-900" : "border-transparent text-neutral-500 hover:text-neutral-800"
              }`}
            >
              <t.icon size={16} /> {t.label}
            </button>
          ))}
        </div>

        <div className="bg-white border border-neutral-200 rounded-2xl p-6 md:p-8">
          {tab === "taxes" && <TaxesPanel settings={settings} setSettings={setSettings} />}
          {tab === "shipping" && <ShippingPanel settings={settings} setSettings={setSettings} />}
          {tab === "payment_methods" && <PaymentPanel settings={settings} setSettings={setSettings} />}
          {tab === "emails" && <EmailsPanel settings={settings} setSettings={setSettings} />}
        </div>

        <div className="mt-6 flex justify-end">
          <button
            onClick={save}
            disabled={saving}
            data-testid="settings-save"
            className="h-11 px-5 rounded-xl bg-neutral-900 hover:bg-neutral-800 text-white font-medium flex items-center gap-2 disabled:opacity-60 transition active:scale-[0.98]"
          >
            <FloppyDisk size={16} weight="fill" />
            {saving ? "Enregistrement…" : "Enregistrer les modifications"}
          </button>
        </div>
      </div>
    </Layout>
  );
}

// ---------- Taxes ----------
function TaxesPanel({ settings, setSettings }) {
  const t = settings.taxes || {};
  const update = (k, v) => setSettings({ ...settings, taxes: { ...t, [k]: v } });
  const updateRate = (country, v) =>
    setSettings({
      ...settings,
      taxes: { ...t, rates_by_country: { ...(t.rates_by_country || {}), [country]: parseFloat(v) || 0 } },
    });
  return (
    <div className="space-y-6">
      <div>
        <label className="text-sm font-medium text-neutral-800 mb-2 block">Régime TVA</label>
        <select
          value={t.regime || "tva_standard"}
          onChange={(e) => update("regime", e.target.value)}
          data-testid="settings-tax-regime"
          className="w-full h-11 px-3 rounded-xl border border-neutral-300 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-neutral-400"
        >
          <option value="franchise">Franchise en base (micro-entreprise)</option>
          <option value="tva_standard">TVA standard par pays</option>
          <option value="oss">OSS One-Stop Shop (UE ≥ 10k€)</option>
        </select>
      </div>
      <div>
        <label className="text-sm font-medium text-neutral-800 mb-2 block">Taux de TVA applicables (%)</label>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {Object.entries(t.rates_by_country || {}).map(([country, rate]) => (
            <div key={country}>
              <div className="text-xs uppercase tracking-wider text-neutral-500 mb-1">{country}</div>
              <div className="relative">
                <input
                  type="number"
                  step="0.1"
                  value={rate}
                  onChange={(e) => updateRate(country, e.target.value)}
                  data-testid={`settings-tax-rate-${country}`}
                  className="w-full h-10 px-3 pr-7 rounded-lg border border-neutral-300 text-sm focus:outline-none focus:ring-1 focus:ring-neutral-400"
                />
                <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-neutral-500">%</span>
              </div>
            </div>
          ))}
        </div>
      </div>
      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={!!t.ioss_enabled}
          onChange={(e) => update("ioss_enabled", e.target.checked)}
          data-testid="settings-tax-ioss"
          className="w-4 h-4"
        />
        IOSS activé (import direct hors UE &lt; 150€)
      </label>
    </div>
  );
}

// ---------- Shipping ----------
function ShippingPanel({ settings, setSettings }) {
  const zones = settings.shipping?.zones || [];
  const updateZone = (idx, key, value) => {
    const next = [...zones];
    next[idx] = { ...next[idx], [key]: value };
    setSettings({ ...settings, shipping: { ...settings.shipping, zones: next } });
  };
  const addZone = () => {
    const next = [
      ...zones,
      {
        id: `zone-${zones.length + 1}`,
        name: "Nouvelle zone",
        countries: [],
        carrier: "",
        delivery_days: "",
        tiers: [{ max_kg: 30, price: 9.9 }],
        free_above: 99,
      },
    ];
    setSettings({ ...settings, shipping: { ...settings.shipping, zones: next } });
  };
  const removeZone = (idx) => {
    const next = zones.filter((_, i) => i !== idx);
    setSettings({ ...settings, shipping: { ...settings.shipping, zones: next } });
  };
  return (
    <div className="space-y-4">
      {zones.map((z, i) => (
        <div key={i} className="border border-neutral-200 rounded-xl p-5 space-y-3" data-testid={`settings-shipping-zone-${i}`}>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div>
              <label className="text-xs uppercase tracking-wider text-neutral-500 mb-1 block">Nom de la zone</label>
              <input value={z.name} onChange={(e) => updateZone(i, "name", e.target.value)}
                className="w-full h-10 px-3 rounded-lg border border-neutral-300 text-sm" />
            </div>
            <div>
              <label className="text-xs uppercase tracking-wider text-neutral-500 mb-1 block">Pays (séparés par virgule)</label>
              <input value={(z.countries || []).join(", ")}
                onChange={(e) => updateZone(i, "countries", e.target.value.split(",").map((s) => s.trim().toUpperCase()).filter(Boolean))}
                className="w-full h-10 px-3 rounded-lg border border-neutral-300 text-sm" />
            </div>
            <div>
              <label className="text-xs uppercase tracking-wider text-neutral-500 mb-1 block">Transporteur</label>
              <input value={z.carrier || ""} onChange={(e) => updateZone(i, "carrier", e.target.value)}
                className="w-full h-10 px-3 rounded-lg border border-neutral-300 text-sm" />
            </div>
            <div>
              <label className="text-xs uppercase tracking-wider text-neutral-500 mb-1 block">Délai (jours)</label>
              <input value={z.delivery_days || ""} onChange={(e) => updateZone(i, "delivery_days", e.target.value)}
                className="w-full h-10 px-3 rounded-lg border border-neutral-300 text-sm" />
            </div>
            <div>
              <label className="text-xs uppercase tracking-wider text-neutral-500 mb-1 block">Franco de port (€)</label>
              <input type="number" value={z.free_above || 0}
                onChange={(e) => updateZone(i, "free_above", parseFloat(e.target.value) || 0)}
                className="w-full h-10 px-3 rounded-lg border border-neutral-300 text-sm" />
            </div>
          </div>
          <div>
            <label className="text-xs uppercase tracking-wider text-neutral-500 mb-1 block">Paliers tarifaires (JSON)</label>
            <textarea rows={2} value={JSON.stringify(z.tiers || [])}
              onChange={(e) => {
                try { updateZone(i, "tiers", JSON.parse(e.target.value)); } catch {}
              }}
              className="w-full px-3 py-2 rounded-lg border border-neutral-300 text-xs font-mono" />
          </div>
          <button onClick={() => removeZone(i)} className="text-xs text-red-600 hover:underline">Supprimer cette zone</button>
        </div>
      ))}
      <button onClick={addZone} data-testid="settings-shipping-add"
        className="h-10 px-4 rounded-xl border border-dashed border-neutral-400 text-sm text-neutral-700 hover:bg-neutral-50">
        + Ajouter une zone
      </button>
    </div>
  );
}

// ---------- Payment ----------
function PaymentPanel({ settings, setSettings }) {
  const p = settings.payment_methods || {};
  const update = (k, v) => setSettings({ ...settings, payment_methods: { ...p, [k]: v } });
  const methods = [
    { k: "creditcard", label: "Carte bancaire (Visa, Mastercard, Amex)" },
    { k: "bancontact", label: "Bancontact (Belgique)" },
    { k: "ideal", label: "iDEAL (Pays-Bas)" },
    { k: "applepay", label: "Apple Pay" },
    { k: "googlepay", label: "Google Pay" },
    { k: "paypal", label: "PayPal (via Mollie)" },
  ];
  return (
    <div className="space-y-5">
      <div className="text-sm text-neutral-600 bg-neutral-50 p-4 rounded-xl">
        Les méthodes de paiement sont gérées par <strong>Mollie</strong> (déjà branché). Active/désactive selon ta cible.
      </div>
      <div className="space-y-2">
        {methods.map((m) => (
          <label key={m.k} className="flex items-center gap-3 p-3 rounded-xl border border-neutral-200 hover:border-neutral-400 cursor-pointer">
            <input type="checkbox" checked={!!p[m.k]} onChange={(e) => update(m.k, e.target.checked)}
              data-testid={`settings-payment-${m.k}`} className="w-4 h-4" />
            <span className="text-sm">{m.label}</span>
          </label>
        ))}
      </div>
      <div>
        <label className="text-sm font-medium text-neutral-800 mb-2 block">Virement bancaire B2B (seuil min)</label>
        <div className="relative max-w-xs">
          <input type="number" value={p.banktransfer_b2b_min || 0}
            onChange={(e) => update("banktransfer_b2b_min", parseFloat(e.target.value) || 0)}
            data-testid="settings-payment-b2b-min"
            className="w-full h-10 px-3 pr-10 rounded-lg border border-neutral-300 text-sm" />
          <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-neutral-500">€</span>
        </div>
        <div className="text-xs text-neutral-500 mt-1">Le virement apparaît au checkout si le panier dépasse ce montant. 0 = jamais.</div>
      </div>
    </div>
  );
}

// ---------- Emails ----------
function EmailsPanel({ settings, setSettings }) {
  const e = settings.emails || {};
  const update = (k, v) => setSettings({ ...settings, emails: { ...e, [k]: v } });
  const fields = [
    { k: "from_name", label: "Nom de l'expéditeur", placeholder: "Luméa Confort" },
    { k: "reply_to", label: "Email de réponse", placeholder: "contact@lumea.fr" },
    { k: "support_email", label: "Email support affiché (FAQ, footer)", placeholder: "support@lumea.fr" },
    { k: "support_phone", label: "Téléphone support", placeholder: "01 23 45 67 89" },
    { k: "signature", label: "Signature des emails", placeholder: "L'équipe {brand}" },
  ];
  return (
    <div className="space-y-4">
      {fields.map((f) => (
        <div key={f.k}>
          <label className="text-sm font-medium text-neutral-800 mb-1.5 block">{f.label}</label>
          <input value={e[f.k] || ""} placeholder={f.placeholder}
            onChange={(ev) => update(f.k, ev.target.value)}
            data-testid={`settings-email-${f.k}`}
            className="w-full h-11 px-3 rounded-xl border border-neutral-300 text-sm focus:outline-none focus:ring-1 focus:ring-neutral-400" />
        </div>
      ))}
    </div>
  );
}
