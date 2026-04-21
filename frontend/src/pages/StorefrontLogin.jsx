import React, { useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import axios from "axios";
import { setSession } from "../lib/customerAuth";
import StorefrontLayout, { useSiteData } from "../components/StorefrontLayout";

const BACKEND = process.env.REACT_APP_BACKEND_URL;

export default function StorefrontLogin() {
  const { siteId } = useParams();
  const nav = useNavigate();
  const site = useSiteData(siteId);
  const [form, setForm] = useState({ email: "", password: "" });
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setErr("");
    try {
      const { data } = await axios.post(`${BACKEND}/api/public/sites/${siteId}/customers/login`, form);
      setSession(siteId, data.token, data.customer);
      nav(`/shop/${siteId}/account`);
    } catch (ex) {
      setErr(ex.response?.data?.detail || "Email ou mot de passe incorrect");
    }
    setLoading(false);
  };

  if (!site) return null;
  const primary = site.design?.brand?.primary_color || "#1C1917";

  return (
    <StorefrontLayout site={site}>
      <div className="max-w-md mx-auto py-16 px-6">
        <h1 className="text-3xl mb-6" style={{ fontFamily: site.design?.brand?.font_heading || "Fraunces, serif" }}>
          Me connecter
        </h1>
        {err && <div className="mb-4 p-3 rounded-lg bg-red-50 border border-red-200 text-sm text-red-700">{err}</div>}
        <form onSubmit={submit} className="space-y-4" data-testid="login-form">
          <input required type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })}
            placeholder="Email" data-testid="cust-login-email" className="w-full h-12 px-4 rounded-xl border border-neutral-300" />
          <input required type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })}
            placeholder="Mot de passe" data-testid="cust-login-password" className="w-full h-12 px-4 rounded-xl border border-neutral-300" />
          <button type="submit" disabled={loading} data-testid="cust-login-submit"
            style={{ background: primary }}
            className="w-full h-12 rounded-xl text-white font-medium disabled:opacity-60 transition active:scale-[0.98]">
            {loading ? "Connexion…" : "Se connecter"}
          </button>
        </form>
        <div className="mt-6 text-sm text-center text-neutral-600">
          Pas encore de compte ? <Link to={`/shop/${siteId}/account/register`} className="font-medium underline">Créer un compte</Link>
        </div>
      </div>
    </StorefrontLayout>
  );
}
