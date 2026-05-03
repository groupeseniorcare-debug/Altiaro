import React, { useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import axios from "axios";
import { setSession } from "../lib/customerAuth";
import StorefrontLayout, { useSiteData } from "../components/StorefrontLayout";
import { useShopSiteId } from "../lib/shopSiteId";

const BACKEND = "";

export default function StorefrontRegister() {
  const siteId = useShopSiteId();
  const nav = useNavigate();
  const site = useSiteData(siteId);
  const [form, setForm] = useState({ email: "", password: "", first_name: "", last_name: "", phone: "" });
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setErr("");
    try {
      const { data } = await axios.post(`${BACKEND}/api/public/sites/${siteId}/customers/register`, form);
      setSession(siteId, data.token, data.customer);
      nav(`/shop/${siteId}/account`);
    } catch (ex) {
      setErr(ex.response?.data?.detail || "Erreur inscription");
    }
    setLoading(false);
  };

  if (!site) return null;
  const primary = site.design?.brand?.primary_color || "#1C1917";

  return (
    <StorefrontLayout site={site}>
      <div className="max-w-md mx-auto py-16 px-6">
        <h1 className="text-3xl mb-6" style={{ fontFamily: site.design?.brand?.font_heading || "Fraunces, serif" }}>
          Créer mon compte
        </h1>
        {err && <div className="mb-4 p-3 rounded-lg bg-red-50 border border-red-200 text-sm text-red-700">{err}</div>}
        <form onSubmit={submit} className="space-y-4" data-testid="register-form">
          <div className="grid grid-cols-2 gap-3">
            <input required value={form.first_name} onChange={(e) => setForm({ ...form, first_name: e.target.value })}
              placeholder="Prénom" data-testid="register-firstname" className="h-12 px-4 rounded-xl border border-neutral-300" />
            <input required value={form.last_name} onChange={(e) => setForm({ ...form, last_name: e.target.value })}
              placeholder="Nom" data-testid="register-lastname" className="h-12 px-4 rounded-xl border border-neutral-300" />
          </div>
          <input required type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })}
            placeholder="Email" data-testid="register-email" className="w-full h-12 px-4 rounded-xl border border-neutral-300" />
          <input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })}
            placeholder="Téléphone (optionnel)" data-testid="register-phone" className="w-full h-12 px-4 rounded-xl border border-neutral-300" />
          <input required type="password" minLength={8} value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })}
            placeholder="Mot de passe (8 caractères min.)" data-testid="register-password" className="w-full h-12 px-4 rounded-xl border border-neutral-300" />
          <button type="submit" disabled={loading} data-testid="register-submit"
            style={{ background: primary }}
            className="w-full h-12 rounded-xl text-white font-medium disabled:opacity-60 transition active:scale-[0.98]">
            {loading ? "Création…" : "Créer mon compte"}
          </button>
        </form>
        <div className="mt-6 text-sm text-center text-neutral-600">
          Déjà un compte ? <Link to={`/shop/${siteId}/account/login`} className="font-medium underline">Se connecter</Link>
        </div>
      </div>
    </StorefrontLayout>
  );
}
