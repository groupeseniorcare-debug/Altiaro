import React, { useState, useEffect } from "react";
import { api, apiCall } from "../lib/api";
import Layout from "../components/Layout";
import { useAuth } from "../lib/auth";
import {
  CreditCard,
  Bank,
  CheckCircle,
  Warning,
  ArrowClockwise,
  ArrowRight,
  CaretRight,
  Receipt,
  Coins,
  Info,
  Trash,
  Buildings,
  PencilSimple,
} from "@phosphor-icons/react";

function formatEuro(v) {
  return `${(v || 0).toFixed(2).replace(".", ",")}€`;
}

export default function Billing() {
  const { user } = useAuth();
  const [card, setCard] = useState(null);
  const [iban, setIban] = useState(null);
  const [balance, setBalance] = useState(null);
  const [ledger, setLedger] = useState([]);
  const [company, setCompany] = useState(null);
  const [loading, setLoading] = useState(true);

  const isConcepteur = user?.role === "operator";

  const load = async () => {
    const [c, i, b, l, co] = await Promise.all([
      apiCall(() => api.get("/billing/card")),
      apiCall(() => api.get("/billing/iban")),
      apiCall(() => api.get("/billing/balance")),
      apiCall(() => api.get("/billing/ledger?limit=50")),
      apiCall(() => api.get("/billing/company")),
    ]);
    if (c.data) setCard(c.data);
    if (i.data) setIban(i.data);
    if (b.data) setBalance(b.data);
    if (l.data) setLedger(l.data);
    if (co.data) setCompany(co.data);
    setLoading(false);
  };

  useEffect(() => { load(); }, []);

  // When user returns from Mollie with ?setup=done, reload
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get("setup") === "done") {
      // Poll for up to 30s to catch the webhook
      let attempts = 0;
      const poll = setInterval(async () => {
        attempts += 1;
        const { data } = await apiCall(() => api.get("/billing/card"));
        if (data?.has_card) {
          setCard(data);
          clearInterval(poll);
          window.history.replaceState({}, "", "/billing");
        } else if (attempts > 15) {
          clearInterval(poll);
        }
      }, 2000);
    }
  }, []);

  const handleSetupCard = async () => {
    const { data, error } = await apiCall(() => api.post("/billing/card/setup", {}));
    if (error) { window.alert(error); return; }
    window.location.href = data.checkout_url;
  };

  const handleRemoveCard = async () => {
    if (!window.confirm("Retirer votre CB ? Les prélèvements hebdo seront suspendus.")) return;
    await apiCall(() => api.delete("/billing/card"));
    load();
  };

  if (loading) {
    return <Layout><div className="p-8 text-zinc-500">Chargement…</div></Layout>;
  }

  return (
    <Layout>
      <div className="p-6 md:p-12 max-w-5xl">
        <div className="mb-8">
          <div className="text-[11px] uppercase tracking-widest text-zinc-500 mb-2">
            {isConcepteur ? "Mon compte" : "Facturation · Admin"}
          </div>
          <h1 className="text-3xl font-semibold text-zinc-100">
            {isConcepteur ? "Compte" : "Mon compte & paiements"}
          </h1>
          <p className="text-zinc-400 mt-2 max-w-2xl">
            {isConcepteur
              ? "Infos société, carte bancaire pour les prélèvements Ads et IBAN pour recevoir tes versements."
              : "Une CB pour que nous prélevions "}
            {!isConcepteur && (
              <>
                <strong>50% des dépenses pub</strong> chaque lundi quand tes Ads tournent · Un RIB
                pour recevoir ta part <strong>le 1er et le 15</strong> de chaque mois.
              </>
            )}
          </p>
        </div>

        {/* Company section (Concepteur only) */}
        {isConcepteur && (
          <CompanySection company={company} onSaved={load} />
        )}

        {/* Balance hero */}
        {balance && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
            <BalanceCard
              testid="balance-net-due"
              label="Ta part à recevoir"
              value={formatEuro(Math.max(0, balance.net_due_to_concepteur))}
              sub={balance.net_due_to_concepteur > 0 ? "Versé aux 1er et 15" : "Rien pour le moment"}
              icon={Coins}
              highlight
            />
            <BalanceCard
              testid="balance-orders"
              label="Commandes encaissées"
              value={formatEuro(balance.order_share_total)}
              sub="50% des ventes (parts cumulées)"
              icon={Receipt}
            />
            <BalanceCard
              testid="balance-ad-debits"
              label="Dépenses pub prélevées"
              value={formatEuro(balance.paid_ad_debits_total + balance.pending_ad_debits_total)}
              sub={balance.pending_ad_debits_total > 0 ? `${formatEuro(balance.pending_ad_debits_total)} en attente` : "Réglées"}
              icon={Receipt}
            />
          </div>
        )}

        {/* Card + IBAN */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5 mb-8">
          <CardSection
            card={card}
            onSetup={handleSetupCard}
            onRemove={handleRemoveCard}
          />
          <IbanSection iban={iban} onChange={load} />
        </div>

        {/* Ledger */}
        <section className="bg-zinc-950 rounded-md border border-zinc-800 overflow-hidden" data-testid="ledger-section">
          <div className="px-5 py-4 border-b border-zinc-800 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Receipt size={18} weight="duotone" className="text-zinc-100" />
              <h2 className="font-heading text-sm font-semibold uppercase tracking-wider">
                Historique ({ledger.length})
              </h2>
            </div>
          </div>
          {ledger.length === 0 ? (
            <div className="px-5 py-12 text-center text-sm text-zinc-500">
              Aucun mouvement enregistré pour l'instant.
            </div>
          ) : (
            <div className="divide-y divide-[#F5F2EB]">
              {ledger.map((e) => (
                <LedgerRow key={e.id} entry={e} />
              ))}
            </div>
          )}
        </section>
      </div>
    </Layout>
  );
}


function BalanceCard({ testid, label, value, sub, icon: Icon, highlight }) {
  return (
    <div
      className={`rounded-md p-5 ${
        highlight ? "bg-gradient-to-br from-[#1C1917] to-[#44403C] text-white" : "bg-zinc-950 border border-zinc-800"
      }`}
      data-testid={testid}
    >
      <div className="flex items-center gap-2 mb-2">
        <Icon size={14} weight="duotone" className={highlight ? "text-white/80" : "text-zinc-100"} />
        <div className={`text-[10px] uppercase tracking-widest ${highlight ? "text-white/60" : "text-zinc-500"}`}>
          {label}
        </div>
      </div>
      <div className={`text-2xl font-semibold ${highlight ? "text-white" : "text-zinc-100"}`}>
        {value}
      </div>
      <div className={`text-xs mt-1.5 ${highlight ? "text-white/70" : "text-zinc-500"}`}>
        {sub}
      </div>
    </div>
  );
}


function CardSection({ card, onSetup, onRemove }) {
  const has = card?.has_card;
  const pending = card?.status === "pending";

  return (
    <section className="bg-zinc-950 rounded-md border border-zinc-800 p-5" data-testid="card-section">
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-zinc-800 flex items-center justify-center">
            <CreditCard size={20} weight="duotone" className="text-zinc-100" />
          </div>
          <div>
            <h2 className="text-base font-semibold text-zinc-100">Carte bancaire</h2>
            <p className="text-xs text-zinc-500">Prélèvement hebdo · 50% dépense pub</p>
          </div>
        </div>
        {has && (
          <span className="px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 text-[10px] uppercase tracking-wider font-semibold">
            Validée
          </span>
        )}
      </div>

      {has ? (
        <>
          <div className="bg-gradient-to-br from-[#1C1917] to-[#44403C] text-white rounded-xl p-5 mb-4">
            <div className="flex items-center justify-between mb-6">
              <CreditCard size={24} weight="duotone" className="text-white/80" />
              <span className="text-[10px] uppercase tracking-wider text-white/60">
                {card.card_brand || "Carte"} · {card.mode === "live" ? "LIVE" : "TEST"}
              </span>
            </div>
            <div className="font-mono text-lg tracking-widest">
              •••• •••• •••• {card.card_last4 || "••••"}
            </div>
            <div className="text-xs text-white/60 mt-2">
              Enregistrée le {card.setup_at ? new Date(card.setup_at).toLocaleDateString("fr-FR") : "—"}
            </div>
          </div>
          <button
            type="button"
            onClick={onRemove}
            data-testid="card-remove"
            className="w-full h-10 rounded-lg bg-zinc-950 border border-zinc-800 hover:border-[#BE123C] hover:text-red-400 text-sm text-zinc-400 transition flex items-center justify-center gap-2"
          >
            <Trash size={14} /> Retirer la carte
          </button>
        </>
      ) : pending ? (
        <div>
          <div className="bg-amber-500/10 rounded-xl p-4 text-sm text-amber-300 flex items-start gap-2 mb-3">
            <ArrowClockwise size={16} weight="fill" className="shrink-0 mt-0.5 animate-spin" />
            <div>
              Validation en cours… Reviens dans quelques instants.
            </div>
          </div>
          <button
            type="button"
            onClick={onSetup}
            data-testid="card-setup-retry"
            className="w-full h-10 rounded-lg bg-zinc-950 border border-zinc-800 hover:border-[#B84B31] text-sm text-zinc-400 transition"
          >
            Relancer la validation
          </button>
        </div>
      ) : (
        <>
          <div className="bg-zinc-900/40 rounded-xl p-4 mb-4 text-sm text-zinc-400 space-y-2">
            <div className="flex gap-2">
              <Info size={14} weight="fill" className="text-zinc-100 shrink-0 mt-0.5" />
              <div>
                Validation par un <strong>débit d'autorisation de 0,01€</strong> (remboursé). Aucun prélèvement
                tant que tes Google Ads ne tournent pas.
              </div>
            </div>
          </div>
          <button
            type="button"
            onClick={onSetup}
            data-testid="card-setup"
            className="w-full h-11 rounded-xl bg-white hover:bg-zinc-200 text-black text-sm font-medium flex items-center justify-center gap-2 transition active:scale-[0.98]"
          >
            Enregistrer ma CB <ArrowRight size={14} weight="bold" />
          </button>
        </>
      )}
    </section>
  );
}


function IbanSection({ iban, onChange }) {
  const has = iban?.has_iban;
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({ iban: "", bic: "", holder_name: "" });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  const submit = async () => {
    setBusy(true);
    setErr("");
    const { error } = await apiCall(() => api.post("/billing/iban", form));
    setBusy(false);
    if (error) { setErr(error); return; }
    setEditing(false);
    setForm({ iban: "", bic: "", holder_name: "" });
    onChange();
  };

  const handleDelete = async () => {
    if (!window.confirm("Retirer votre IBAN ? Vous ne pourrez plus recevoir de versements.")) return;
    await apiCall(() => api.delete("/billing/iban"));
    onChange();
  };

  return (
    <section className="bg-zinc-950 rounded-md border border-zinc-800 p-5" data-testid="iban-section">
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-zinc-800 flex items-center justify-center">
            <Bank size={20} weight="duotone" className="text-emerald-400" />
          </div>
          <div>
            <h2 className="text-base font-semibold text-zinc-100">Compte bancaire</h2>
            <p className="text-xs text-zinc-500">Versements · 1er et 15 de chaque mois</p>
          </div>
        </div>
        {has && !editing && (
          <span className="px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 text-[10px] uppercase tracking-wider font-semibold">
            Valide
          </span>
        )}
      </div>

      {has && !editing ? (
        <>
          <div className="bg-zinc-900/40 rounded-xl p-4 mb-4">
            <div className="text-xs text-zinc-500 mb-0.5">IBAN</div>
            <div className="font-mono text-sm text-zinc-100 mb-3" data-testid="iban-display">{iban.iban_masked}</div>
            <div className="grid grid-cols-2 gap-3 text-xs">
              <div>
                <div className="text-zinc-500">BIC</div>
                <div className="font-mono text-zinc-100">{iban.bic || "—"}</div>
              </div>
              <div>
                <div className="text-zinc-500">Titulaire</div>
                <div className="text-zinc-100">{iban.holder_name}</div>
              </div>
              <div>
                <div className="text-zinc-500">Banque</div>
                <div className="text-zinc-100 truncate">{iban.bank_name || "—"}</div>
              </div>
              <div>
                <div className="text-zinc-500">Pays</div>
                <div className="text-zinc-100">{iban.country}</div>
              </div>
            </div>
          </div>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => {
                setEditing(true);
                setForm({ iban: "", bic: iban.bic || "", holder_name: iban.holder_name || "" });
              }}
              data-testid="iban-edit"
              className="flex-1 h-10 rounded-lg bg-zinc-950 border border-zinc-800 hover:border-[#B84B31] text-sm"
            >
              Modifier
            </button>
            <button
              type="button"
              onClick={handleDelete}
              data-testid="iban-delete"
              className="w-10 h-10 rounded-lg bg-zinc-950 border border-zinc-800 hover:border-[#BE123C] hover:text-red-400 text-sm flex items-center justify-center"
            >
              <Trash size={14} />
            </button>
          </div>
        </>
      ) : (
        <div className="space-y-3">
          <div>
            <label className="block text-xs font-medium text-zinc-400 mb-1.5">IBAN</label>
            <input
              type="text"
              value={form.iban}
              onChange={(e) => setForm({ ...form, iban: e.target.value.toUpperCase() })}
              placeholder="FR76 3000 3000 0000 0000 0000 000"
              data-testid="iban-input"
              className="w-full h-11 px-3 rounded-lg border border-zinc-800 bg-zinc-950 text-sm font-mono focus:outline-none focus:border-zinc-500"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-zinc-400 mb-1.5">BIC (optionnel)</label>
              <input
                type="text"
                value={form.bic}
                onChange={(e) => setForm({ ...form, bic: e.target.value.toUpperCase() })}
                placeholder="BNPAFRPPXXX"
                data-testid="bic-input"
                className="w-full h-11 px-3 rounded-lg border border-zinc-800 bg-zinc-950 text-sm font-mono focus:outline-none focus:border-zinc-500"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-zinc-400 mb-1.5">Titulaire</label>
              <input
                type="text"
                value={form.holder_name}
                onChange={(e) => setForm({ ...form, holder_name: e.target.value })}
                placeholder="Marie Dupont"
                data-testid="holder-input"
                className="w-full h-11 px-3 rounded-lg border border-zinc-800 bg-zinc-950 text-sm focus:outline-none focus:border-zinc-500"
              />
            </div>
          </div>
          {err && (
            <div className="p-2.5 rounded-lg bg-red-500/10 text-red-400 text-xs flex gap-2">
              <Warning size={14} weight="fill" className="shrink-0 mt-0.5" />
              {err}
            </div>
          )}
          <div className="flex gap-2">
            {editing && has && (
              <button type="button" onClick={() => setEditing(false)} className="h-10 px-4 rounded-lg text-sm text-zinc-400">
                Annuler
              </button>
            )}
            <button
              type="button"
              onClick={submit}
              disabled={busy || !form.iban || !form.holder_name}
              data-testid="iban-save"
              className="flex-1 h-11 rounded-xl bg-[#047857] hover:bg-[#065F46] disabled:opacity-50 text-white text-sm font-medium flex items-center justify-center gap-2"
            >
              {busy ? <ArrowClockwise size={14} className="animate-spin" /> : <CheckCircle size={14} weight="fill" />}
              Enregistrer
            </button>
          </div>
        </div>
      )}
    </section>
  );
}


function LedgerRow({ entry }) {
  const cfg = {
    order_share: { label: "Part commande", color: "#047857", prefix: "+" },
    ad_debit: { label: "Prélèvement pub", color: "#BE123C", prefix: "-" },
    payout: { label: "Versement prévu", color: "#D97706", prefix: "→" },
  }[entry.type] || { label: entry.type, color: "#78716C", prefix: "" };
  const isPending = entry.status === "pending";
  return (
    <div className="px-5 py-3 flex items-center gap-4" data-testid={`ledger-${entry.id}`}>
      <div className="w-8 h-8 rounded-full flex items-center justify-center" style={{ background: cfg.color + "18" }}>
        <span className="font-semibold text-xs" style={{ color: cfg.color }}>{cfg.prefix}</span>
      </div>
      <div className="flex-1 min-w-0">
        <div className="text-sm text-zinc-100">
          {cfg.label}
          {entry.site_name && <span className="text-zinc-500"> · {entry.site_name}</span>}
          {entry.order_number && <span className="text-zinc-500 font-mono text-xs"> · {entry.order_number}</span>}
        </div>
        <div className="text-xs text-zinc-500 flex items-center gap-2">
          {new Date(entry.created_at).toLocaleString("fr-FR")}
          {isPending && (
            <span className="px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-300 text-[10px] uppercase tracking-wider">
              En attente
            </span>
          )}
        </div>
      </div>
      <div className="text-right">
        <div className="font-heading font-semibold" style={{ color: cfg.color }}>
          {cfg.prefix}{formatEuro(entry.amount)}
        </div>
      </div>
    </div>
  );
}


function CompanySection({ company, onSaved }) {
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState(() => ({
    company_name: company?.company_name || "",
    company_legal_form: company?.company_legal_form || "",
    siret: company?.siret || "",
    vat_number: company?.vat_number || "",
    address_line1: company?.address_line1 || "",
    address_line2: company?.address_line2 || "",
    postal_code: company?.postal_code || "",
    city: company?.city || "",
    country_code: company?.country_code || "FR",
    phone: company?.phone || "",
  }));
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState("");

  useEffect(() => {
    if (!editing && company) {
      setForm({
        company_name: company.company_name || "",
        company_legal_form: company.company_legal_form || "",
        siret: company.siret || "",
        vat_number: company.vat_number || "",
        address_line1: company.address_line1 || "",
        address_line2: company.address_line2 || "",
        postal_code: company.postal_code || "",
        city: company.city || "",
        country_code: company.country_code || "FR",
        phone: company.phone || "",
      });
    }
  }, [company, editing]);

  const isEmpty = !company?.company_name && !company?.siret && !company?.address_line1;

  const save = async () => {
    setSaving(true);
    setErr("");
    const { error } = await apiCall(() => api.patch("/billing/company", form));
    setSaving(false);
    if (error) {
      setErr(error);
      return;
    }
    setEditing(false);
    onSaved?.();
  };

  return (
    <section
      className="bg-zinc-950 rounded-md border border-zinc-800 p-6 mb-6"
      data-testid="company-section"
    >
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Buildings size={18} weight="duotone" className="text-[#2563EB]" />
          <h2 className="font-heading text-sm font-semibold uppercase tracking-wider">
            Informations société
          </h2>
        </div>
        {!editing && (
          <button
            onClick={() => setEditing(true)}
            data-testid="company-edit"
            className="h-8 px-3 rounded-full border border-zinc-800 hover:bg-zinc-900/40 text-xs font-medium flex items-center gap-1.5"
          >
            <PencilSimple size={12} /> Modifier
          </button>
        )}
      </div>

      {!editing ? (
        isEmpty ? (
          <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-300 text-sm flex items-start gap-2">
            <Warning size={16} weight="fill" className="shrink-0 mt-0.5 text-amber-400" />
            <div>
              <strong>Société non renseignée.</strong> Ces infos apparaîtront sur tes factures
              plateforme et tes mentions légales. Clique sur <em>Modifier</em>.
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
            <Field label="Dénomination" value={`${company.company_name || "—"}${company.company_legal_form ? ` (${company.company_legal_form})` : ""}`} />
            <Field label="SIRET" value={company.siret || "—"} mono />
            <Field label="TVA intracom." value={company.vat_number || "—"} mono />
            <Field label="Téléphone" value={company.phone || "—"} />
            <Field
              label="Adresse"
              value={
                company.address_line1
                  ? `${company.address_line1}${company.address_line2 ? ", " + company.address_line2 : ""}, ${company.postal_code} ${company.city}, ${company.country_code}`
                  : "—"
              }
              wide
            />
          </div>
        )
      ) : (
        <div className="space-y-3">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <FormField label="Dénomination" required>
              <input
                value={form.company_name}
                onChange={(e) => setForm({ ...form, company_name: e.target.value })}
                data-testid="company-name"
                className="form-input"
              />
            </FormField>
            <FormField label="Forme juridique">
              <select
                value={form.company_legal_form}
                onChange={(e) => setForm({ ...form, company_legal_form: e.target.value })}
                data-testid="company-legal-form"
                className="form-input"
              >
                <option value="">—</option>
                <option>SARL</option>
                <option>SAS</option>
                <option>SASU</option>
                <option>EURL</option>
                <option>EI</option>
                <option>Micro-entreprise</option>
                <option>SCI</option>
                <option>SA</option>
              </select>
            </FormField>
            <FormField label="Téléphone">
              <input
                value={form.phone}
                onChange={(e) => setForm({ ...form, phone: e.target.value })}
                data-testid="company-phone"
                className="form-input"
              />
            </FormField>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <FormField label="SIRET (14 chiffres)">
              <input
                value={form.siret}
                onChange={(e) => setForm({ ...form, siret: e.target.value })}
                data-testid="company-siret"
                className="form-input font-mono"
                maxLength={17}
              />
            </FormField>
            <FormField label="TVA intracommunautaire">
              <input
                value={form.vat_number}
                onChange={(e) => setForm({ ...form, vat_number: e.target.value })}
                placeholder="FR12345678901"
                data-testid="company-vat"
                className="form-input font-mono"
              />
            </FormField>
          </div>
          <FormField label="Adresse (ligne 1)">
            <input
              value={form.address_line1}
              onChange={(e) => setForm({ ...form, address_line1: e.target.value })}
              data-testid="company-addr1"
              className="form-input"
            />
          </FormField>
          <FormField label="Adresse (ligne 2, optionnelle)">
            <input
              value={form.address_line2}
              onChange={(e) => setForm({ ...form, address_line2: e.target.value })}
              data-testid="company-addr2"
              className="form-input"
            />
          </FormField>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <FormField label="Code postal">
              <input
                value={form.postal_code}
                onChange={(e) => setForm({ ...form, postal_code: e.target.value })}
                data-testid="company-postal"
                className="form-input"
              />
            </FormField>
            <div className="md:col-span-2">
              <FormField label="Ville">
                <input
                  value={form.city}
                  onChange={(e) => setForm({ ...form, city: e.target.value })}
                  data-testid="company-city"
                  className="form-input"
                />
              </FormField>
            </div>
            <FormField label="Pays">
              <select
                value={form.country_code}
                onChange={(e) => setForm({ ...form, country_code: e.target.value })}
                data-testid="company-country"
                className="form-input"
              >
                <option value="FR">🇫🇷 France</option>
                <option value="BE">🇧🇪 Belgique</option>
                <option value="CH">🇨🇭 Suisse</option>
                <option value="LU">🇱🇺 Luxembourg</option>
                <option value="DE">🇩🇪 Allemagne</option>
                <option value="NL">🇳🇱 Pays-Bas</option>
                <option value="ES">🇪🇸 Espagne</option>
                <option value="IT">🇮🇹 Italie</option>
                <option value="UK">🇬🇧 Royaume-Uni</option>
              </select>
            </FormField>
          </div>

          {err && (
            <div className="p-2.5 rounded-lg bg-red-500/10 text-red-400 text-sm" data-testid="company-err">
              {err}
            </div>
          )}
          <div className="flex items-center gap-2 pt-2">
            <button
              onClick={save}
              disabled={saving || !form.company_name}
              data-testid="company-save"
              className="h-10 px-4 rounded-full bg-white hover:bg-zinc-200 disabled:opacity-50 text-black text-sm font-medium flex items-center gap-2"
            >
              {saving ? <ArrowClockwise size={14} className="animate-spin" /> : <CheckCircle size={14} weight="bold" />}
              Enregistrer
            </button>
            <button
              onClick={() => setEditing(false)}
              data-testid="company-cancel"
              className="h-10 px-4 rounded-full border border-zinc-800 hover:bg-zinc-900/40 text-sm font-medium"
            >
              Annuler
            </button>
          </div>
        </div>
      )}
      <style>{`.form-input { height:40px; padding:0 12px; border-radius:8px; border:1px solid #E7E5E4; background:white; font-size:14px; width:100%; outline:none; } .form-input:focus { border-color:#2563EB; box-shadow: 0 0 0 2px #2563EB22; }`}</style>
    </section>
  );
}

function Field({ label, value, mono = false, wide = false }) {
  return (
    <div className={wide ? "md:col-span-2" : ""}>
      <div className="text-[11px] uppercase tracking-widest text-zinc-500 mb-1">{label}</div>
      <div className={`text-zinc-100 ${mono ? "font-mono text-sm" : ""}`}>{value}</div>
    </div>
  );
}

function FormField({ label, required, children }) {
  return (
    <div>
      <label className="block text-[11px] uppercase tracking-widest text-zinc-500 font-medium mb-1">
        {label}
        {required && <span className="text-red-400 ml-1">*</span>}
      </label>
      {children}
    </div>
  );
}
