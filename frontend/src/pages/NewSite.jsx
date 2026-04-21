import React, { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { api, apiCall } from "../lib/api";
import { useAuth } from "../lib/auth";
import Layout from "../components/Layout";
import { ArrowLeft, Rocket, Spinner } from "@phosphor-icons/react";

export default function NewSite() {
  const [searchParams] = useSearchParams();
  const [form, setForm] = useState({
    name: searchParams.get("name") || "",
    niche: searchParams.get("niche") || "",
    niche_slug: searchParams.get("niche_slug") || "",
    domain: "",
    shopify_url: "",
    operator_id: "",
    notes: "",
  });
  const [users, setUsers] = useState([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const navigate = useNavigate();
  const { user } = useAuth();

  useEffect(() => {
    if (user?.role === "admin") {
      apiCall(() => api.get("/users")).then(({ data }) => setUsers(data || []));
    }
  }, [user]);

  const handleChange = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setError("");
    const payload = {
      name: form.name,
      niche: form.niche,
      niche_slug: form.niche_slug || null,
      domain: form.domain,
      shopify_url: form.shopify_url,
      operator_id: form.operator_id || null,
      notes: form.notes,
    };
    const { data, error: err } = await apiCall(() => api.post("/sites", payload));
    setSubmitting(false);
    if (err) {
      setError(err);
      return;
    }
    navigate(`/sites/${data.id}`);
  };

  return (
    <Layout>
      <div className="p-8 md:p-12 max-w-3xl">
        <button
          onClick={() => navigate("/sites")}
          className="flex items-center gap-2 text-sm text-[#78716C] hover:text-[#1C1917] mb-6 transition"
          data-testid="back-to-sites"
        >
          <ArrowLeft size={16} /> Retour aux sites
        </button>

        <div className="mb-10 animate-fade-up">
          <div className="text-[11px] uppercase tracking-widest text-[#78716C] mb-2">Nouveau projet</div>
          <h1 className="font-heading text-4xl font-semibold text-[#1C1917]">Lancer un nouveau site</h1>
          <p className="text-[#57534E] mt-2 max-w-xl">
            Remplissez les informations de base. Les 50 étapes du playbook seront
            automatiquement chargées et l'opérateur assigné pourra commencer la Phase A.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="bg-white rounded-xl border border-[#E7E5E4] p-8 space-y-6" data-testid="new-site-form">
          {form.niche_slug && (
            <div className="px-4 py-3 rounded-lg bg-[#FDF4E7] border border-[#F5E0C3] text-sm text-[#854D0E]" data-testid="niche-prefill-banner">
              🎯 Pré-rempli depuis le <strong>Niche Engine</strong> — niche « {form.niche} »
            </div>
          )}
          <div>
            <label className="block text-[13px] font-medium text-[#1C1917] mb-1.5">
              Nom de la marque *
            </label>
            <input
              required
              name="name"
              value={form.name}
              onChange={handleChange}
              placeholder="Ex : Luméa Confort"
              data-testid="new-site-name"
              className="w-full h-12 px-4 rounded-xl border border-[#E7E5E4] bg-white focus:outline-none focus:ring-2 focus:ring-[#B84B31]/30 focus:border-[#B84B31]"
            />
            <div className="text-xs text-[#78716C] mt-1">Utilisé pour substituer [NOM_MARQUE] dans tous les prompts.</div>
          </div>

          <div>
            <label className="block text-[13px] font-medium text-[#1C1917] mb-1.5">
              Niche ciblée *
            </label>
            <input
              required
              name="niche"
              value={form.niche}
              onChange={handleChange}
              placeholder="Ex : équipements de confort pour seniors (non-médicaux), max 20kg"
              data-testid="new-site-niche"
              className="w-full h-12 px-4 rounded-xl border border-[#E7E5E4] bg-white focus:outline-none focus:ring-2 focus:ring-[#B84B31]/30 focus:border-[#B84B31]"
            />
            <div className="text-xs text-[#78716C] mt-1">Substitue [NICHE] dans les prompts d'étude marché et SEO.</div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <div>
              <label className="block text-[13px] font-medium text-[#1C1917] mb-1.5">
                Nom de domaine (optionnel)
              </label>
              <input
                name="domain"
                value={form.domain}
                onChange={handleChange}
                placeholder="lumeaconfort.fr"
                data-testid="new-site-domain"
                className="w-full h-12 px-4 rounded-xl border border-[#E7E5E4] bg-white focus:outline-none focus:ring-2 focus:ring-[#B84B31]/30 focus:border-[#B84B31]"
              />
            </div>
            <div>
              <label className="block text-[13px] font-medium text-[#1C1917] mb-1.5">
                URL Shopify admin (optionnel)
              </label>
              <input
                name="shopify_url"
                value={form.shopify_url}
                onChange={handleChange}
                placeholder="https://xxx.myshopify.com"
                data-testid="new-site-shopify"
                className="w-full h-12 px-4 rounded-xl border border-[#E7E5E4] bg-white focus:outline-none focus:ring-2 focus:ring-[#B84B31]/30 focus:border-[#B84B31]"
              />
            </div>
          </div>

          {user?.role === "admin" && (
            <div>
              <label className="block text-[13px] font-medium text-[#1C1917] mb-1.5">
                Opérateur assigné
              </label>
              <select
                name="operator_id"
                value={form.operator_id}
                onChange={handleChange}
                data-testid="new-site-operator"
                className="w-full h-12 px-4 rounded-xl border border-[#E7E5E4] bg-white focus:outline-none focus:ring-2 focus:ring-[#B84B31]/30 focus:border-[#B84B31]"
              >
                <option value="">Aucun (admin uniquement)</option>
                {users.map((u) => (
                  <option key={u.id} value={u.id}>
                    {u.name} — {u.email} ({u.role})
                  </option>
                ))}
              </select>
              <div className="text-xs text-[#78716C] mt-1">Seul cet opérateur (et les admins) verra ce site.</div>
            </div>
          )}

          <div>
            <label className="block text-[13px] font-medium text-[#1C1917] mb-1.5">
              Notes internes (optionnel)
            </label>
            <textarea
              name="notes"
              value={form.notes}
              onChange={handleChange}
              rows={3}
              placeholder="Objectif CA, angle de marque, spécificités..."
              data-testid="new-site-notes"
              className="w-full px-4 py-3 rounded-xl border border-[#E7E5E4] bg-white focus:outline-none focus:ring-2 focus:ring-[#B84B31]/30 focus:border-[#B84B31] resize-none"
            />
          </div>

          {error && (
            <div className="p-3.5 rounded-lg bg-[#FFE4E6] text-[#BE123C] text-sm" data-testid="new-site-error">
              {error}
            </div>
          )}

          <div className="flex items-center justify-end gap-3 pt-4 border-t border-[#E7E5E4]">
            <button
              type="button"
              onClick={() => navigate("/sites")}
              data-testid="new-site-cancel"
              className="h-11 px-5 rounded-xl border border-[#E7E5E4] text-[#57534E] hover:bg-[#FDFBF7] transition"
            >
              Annuler
            </button>
            <button
              type="submit"
              disabled={submitting}
              data-testid="new-site-submit"
              className="h-11 px-5 rounded-xl bg-[#B84B31] hover:bg-[#993D26] text-white font-medium transition-all duration-200 flex items-center gap-2 active:scale-[0.98] disabled:opacity-60"
            >
              {submitting ? (
                <>
                  <Spinner size={18} className="animate-spin" /> Création...
                </>
              ) : (
                <>
                  <Rocket size={18} weight="fill" /> Créer le site et charger les 50 étapes
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </Layout>
  );
}
