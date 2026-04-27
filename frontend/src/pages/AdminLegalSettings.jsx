import React, { useEffect, useState } from "react";
import { ShieldCheck, Buildings, FloppyDisk, Info } from "@phosphor-icons/react";
import { api, apiCall } from "../lib/api";
import { useAuth } from "../lib/auth";
import { Navigate } from "react-router-dom";

const FIELD_GROUPS = [
  {
    title: "Identité légale",
    icon: Buildings,
    fields: [
      { key: "siren",            label: "SIREN",                placeholder: "883 803 967" },
      { key: "siret",            label: "SIRET (siège)",        placeholder: "883 803 967 00016" },
      { key: "code_naf",         label: "Code APE / NAF",       placeholder: "4782Z" },
      { key: "forme_juridique",  label: "Forme juridique (publique)", placeholder: "Société" },
      { key: "date_creation",    label: "Date d'immatriculation", placeholder: "30/05/2020" },
      { key: "adresse",          label: "Adresse du siège",     placeholder: "4 IMP CLOS FLEURI, 42320 FARNAY, France", textarea: true },
      { key: "tva_intra",        label: "TVA intracommunautaire", placeholder: "Non applicable" },
      { key: "tva_mention_cgv",  label: "Mention TVA (CGV)",    placeholder: "TVA non applicable, art. 293 B du CGI" },
    ],
  },
  {
    title: "Plateforme Altiaro",
    icon: ShieldCheck,
    fields: [
      { key: "platform_nom",       label: "Nom commercial",   placeholder: "Altiaro" },
      { key: "platform_email",     label: "E-mail contact",   placeholder: "contact@altiaro.com" },
      { key: "platform_telephone", label: "Téléphone",        placeholder: "+33 6 95 18 17 03" },
      { key: "platform_site_web",  label: "Site web",         placeholder: "https://altiaro.com" },
    ],
  },
  {
    title: "Hébergement",
    icon: Info,
    fields: [
      { key: "hebergeur_nom",     label: "Hébergeur (nom)",     placeholder: "Emergent Labs" },
      { key: "hebergeur_adresse", label: "Hébergeur (adresse)", placeholder: "Infrastructure Kubernetes (Cloudflare devant)" },
    ],
  },
];

export default function AdminLegalSettings() {
  const { user, loading } = useAuth();
  const [info, setInfo] = useState(null);
  const [meta, setMeta] = useState({ source: "constant", override_keys: [] });
  const [draft, setDraft] = useState({});
  const [saving, setSaving] = useState(false);
  const [savedAt, setSavedAt] = useState(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    if (loading) return;
    apiCall(() => api.get("/admin/legal-settings")).then(({ data, error }) => {
      if (error) { setErr(error); return; }
      setInfo(data?.info || {});
      setDraft(data?.info || {});
      setMeta({ source: data?.source, override_keys: data?.override_keys || [] });
    });
  }, [loading]);

  if (loading) return <div className="p-6 text-neutral-500">Chargement…</div>;
  if (!user) return <Navigate to="/login" replace />;
  if (user.role !== "admin") return <Navigate to="/dashboard" replace />;

  const handleSave = async () => {
    setSaving(true);
    setErr("");
    const payload = {};
    Object.keys(draft).forEach((k) => {
      if ((draft[k] ?? "") !== (info[k] ?? "")) payload[k] = draft[k] ?? "";
    });
    if (Object.keys(payload).length === 0) {
      setSavedAt(new Date());
      setSaving(false);
      return;
    }
    const { data, error } = await apiCall(() => api.put("/admin/legal-settings", payload));
    if (error) {
      setErr(error);
    } else {
      setInfo(data?.info || {});
      setDraft(data?.info || {});
      setSavedAt(new Date());
    }
    setSaving(false);
  };

  return (
    <div className="max-w-4xl mx-auto px-6 py-8" data-testid="admin-legal-settings">
      <div className="mb-8">
        <div className="text-[11px] uppercase tracking-[0.25em] text-neutral-500 mb-2">Administration</div>
        <h1 className="text-3xl font-semibold text-neutral-900">Paramètres légaux plateforme</h1>
        <p className="text-sm text-neutral-600 mt-2 max-w-2xl leading-relaxed">
          Ces informations sont propagées <strong>à toutes les boutiques</strong> de la plateforme :
          mentions légales, CGV, politique de confidentialité, politique de cookies, retours et livraison.
          Le nom commercial et les coordonnées de chaque boutique restent personnalisés par site,
          mais l'identité légale (SIRET, adresse, forme juridique) est unique pour toute la plateforme.
        </p>
        <div className="mt-3 inline-flex items-center gap-2 text-[12px] text-neutral-500">
          <Info size={13} />
          Source actuelle : <code className="px-1.5 py-0.5 bg-neutral-100 rounded">{meta.source}</code>
          {meta.override_keys.length > 0 && (
            <>· {meta.override_keys.length} surcharge(s) DB</>
          )}
        </div>
      </div>

      {err && (
        <div className="mb-4 p-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm">
          {err}
        </div>
      )}

      <div className="space-y-6">
        {FIELD_GROUPS.map((g) => (
          <div key={g.title} className="bg-white border border-neutral-200 rounded-xl p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-9 h-9 rounded-lg bg-neutral-100 flex items-center justify-center">
                <g.icon size={18} className="text-neutral-700" />
              </div>
              <h2 className="text-lg font-semibold text-neutral-900">{g.title}</h2>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {g.fields.map((f) => (
                <div key={f.key} className={f.textarea ? "md:col-span-2" : ""}>
                  <label htmlFor={`field-${f.key}`} className="block text-[12px] font-medium text-neutral-700 mb-1.5">
                    {f.label}
                  </label>
                  {f.textarea ? (
                    <textarea
                      id={`field-${f.key}`}
                      data-testid={`field-${f.key}`}
                      rows={2}
                      value={draft?.[f.key] ?? ""}
                      onChange={(e) => setDraft((d) => ({ ...d, [f.key]: e.target.value }))}
                      placeholder={f.placeholder}
                      className="w-full px-3 py-2 rounded-lg border border-neutral-300 text-sm focus:outline-none focus:border-neutral-900"
                    />
                  ) : (
                    <input
                      id={`field-${f.key}`}
                      data-testid={`field-${f.key}`}
                      type="text"
                      value={draft?.[f.key] ?? ""}
                      onChange={(e) => setDraft((d) => ({ ...d, [f.key]: e.target.value }))}
                      placeholder={f.placeholder}
                      className="w-full h-10 px-3 rounded-lg border border-neutral-300 text-sm focus:outline-none focus:border-neutral-900"
                    />
                  )}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      <div className="mt-6 flex items-center gap-3">
        <button
          onClick={handleSave}
          disabled={saving}
          data-testid="legal-save-btn"
          className="h-11 px-6 rounded-lg bg-neutral-900 text-white font-semibold text-sm inline-flex items-center gap-2 hover:bg-neutral-800 disabled:opacity-50"
        >
          <FloppyDisk size={15} weight="fill" />
          {saving ? "Enregistrement…" : "Enregistrer les modifications"}
        </button>
        {savedAt && (
          <span className="text-[12px] text-emerald-700">
            ✓ Enregistré à {savedAt.toLocaleTimeString("fr-FR")}
          </span>
        )}
      </div>

      <div className="mt-12 p-4 rounded-xl bg-amber-50 border border-amber-200 text-[13px] text-amber-900">
        <strong>Note importante (anonymisation)</strong> — En vertu de la consigne plateforme,
        aucun nom de personne physique (représentant légal au sens du KBIS) ne doit apparaître
        publiquement. Le « directeur de publication » exposé dans les mentions légales correspond
        au <strong>nom commercial du site</strong> (ex. « la Société Altea » pour le site Altea).
        L'identité réelle du représentant n'est jamais propagée aux boutiques.
      </div>
    </div>
  );
}
