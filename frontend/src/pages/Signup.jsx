import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import { AltiaroLogo } from "../components/AltiaroLogo";
import { ArrowUpRight, Spinner, Eye, EyeSlash } from "@phosphor-icons/react";
import CookieConsentBanner from "../components/storefront/CookieConsentBanner";

function formatError(detail) {
  if (detail == null) return "Une erreur est survenue";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map((e) => e?.msg || "").filter(Boolean).join(" ");
  if (detail?.message) return detail.message;
  return String(detail);
}

export default function Signup() {
  const nav = useNavigate();
  const [form, setForm] = useState({ name: "", email: "", password: "", company_name: "" });
  const [show, setShow] = useState(false);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  const upd = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const submit = async (e) => {
    e.preventDefault();
    setErr("");
    setLoading(true);
    try {
      await api.post("/auth/signup", form);
      nav(`/verify-email?email=${encodeURIComponent(form.email.toLowerCase().trim())}`);
    } catch (e) {
      setErr(formatError(e.response?.data?.detail) || e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className="min-h-screen grid grid-cols-1 lg:grid-cols-2 bg-white"
      style={{ fontFamily: "'Inter', system-ui, sans-serif" }}
    >
      <CookieConsentBanner />
      {/* Brand panel (hidden on mobile) */}
      <div className="hidden lg:flex flex-col justify-between p-12 bg-neutral-900 text-white">
        <Link to="/" className="flex items-center" data-testid="signup-brand-link">
          <AltiaroLogo variant="horizontal" size={26} color="#FFFFFF" />
        </Link>
        <div>
          <div className="text-[11px] uppercase tracking-[0.14em] text-neutral-400 mb-4">
            Devenir Concepteur
          </div>
          <h2
            className="text-4xl xl:text-5xl leading-[1.05] tracking-tight font-medium"
            style={{ fontFamily: "'Fraunces', serif" }}
          >
            Lance ta première marque <span className="italic text-neutral-400">sans trésorerie.</span>
          </h2>
          <p className="text-white/85 mt-6 max-w-md leading-relaxed text-base">
            Aucun frais fixe. Aucun engagement. 50% de la marge brute directement
            sur ton IBAN, versée les 1er et 15 du mois.
          </p>
        </div>
        <div className="text-xs text-neutral-500">
          © {new Date().getFullYear()} Altiaro — SIREN 883 803 967
        </div>
      </div>

      {/* Form */}
      <div className="flex flex-col justify-center px-6 py-12 md:px-16">
        <div className="lg:hidden mb-8">
          <Link to="/" className="inline-flex items-center gap-2" data-testid="signup-brand-mobile">
            <AltiaroLogo variant="horizontal" size={22} color="#0A0A0A" />
          </Link>
        </div>

        <div className="max-w-md w-full mx-auto">
          <div className="text-[11px] uppercase tracking-[0.14em] text-neutral-500 mb-3">
            Inscription Concepteur
          </div>
          <h1 className="text-3xl sm:text-4xl font-semibold tracking-tight mb-2">
            Créez votre compte
          </h1>
          <p className="text-neutral-500 mb-8 text-sm">
            Un code de confirmation vous sera envoyé par email pour finaliser votre inscription.
          </p>

          <form onSubmit={submit} className="space-y-4" data-testid="signup-form">
            <Field label="Nom complet">
              <input
                type="text"
                value={form.name}
                onChange={upd("name")}
                required
                minLength={2}
                autoComplete="name"
                data-testid="signup-name"
                className="w-full h-11 px-4 rounded-lg border border-neutral-300 bg-white focus:border-neutral-900 focus:ring-2 focus:ring-neutral-900/10 outline-none transition"
              />
            </Field>

            <Field label="Email professionnel">
              <input
                type="email"
                value={form.email}
                onChange={upd("email")}
                required
                autoComplete="email"
                data-testid="signup-email"
                className="w-full h-11 px-4 rounded-lg border border-neutral-300 bg-white focus:border-neutral-900 focus:ring-2 focus:ring-neutral-900/10 outline-none transition"
              />
            </Field>

            <Field label="Société / enseigne (optionnel)">
              <input
                type="text"
                value={form.company_name}
                onChange={upd("company_name")}
                autoComplete="organization"
                data-testid="signup-company"
                className="w-full h-11 px-4 rounded-lg border border-neutral-300 bg-white focus:border-neutral-900 focus:ring-2 focus:ring-neutral-900/10 outline-none transition"
              />
            </Field>

            <Field label="Mot de passe">
              <div className="relative">
                <input
                  type={show ? "text" : "password"}
                  value={form.password}
                  onChange={upd("password")}
                  required
                  minLength={8}
                  autoComplete="new-password"
                  data-testid="signup-password"
                  className="w-full h-11 px-4 pr-11 rounded-lg border border-neutral-300 bg-white focus:border-neutral-900 focus:ring-2 focus:ring-neutral-900/10 outline-none transition"
                />
                <button
                  type="button"
                  onClick={() => setShow((s) => !s)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-neutral-500 hover:text-neutral-900"
                  tabIndex={-1}
                >
                  {show ? <EyeSlash size={16} /> : <Eye size={16} />}
                </button>
              </div>
              <div className="text-[11px] text-neutral-500 mt-1.5">
                Minimum 8 caractères dont au moins 1 lettre et 1 chiffre
              </div>
            </Field>

            {err && (
              <div
                className="text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg p-3"
                data-testid="signup-error"
              >
                {err}
              </div>
            )}

            <label className="flex items-start gap-3 text-xs text-neutral-600 pt-1">
              <input
                type="checkbox"
                required
                className="mt-0.5 accent-neutral-900"
                data-testid="signup-accept-terms"
              />
              <span>
                J'accepte les <Link to="/cgu" target="_blank" className="underline hover:text-neutral-900">CGU</Link> et la{" "}
                <Link to="/confidentialite" target="_blank" className="underline hover:text-neutral-900">politique de confidentialité</Link>.
              </span>
            </label>

            <button
              type="submit"
              disabled={loading}
              data-testid="signup-submit"
              className="w-full h-12 mt-2 rounded-xl bg-neutral-900 hover:bg-neutral-800 text-white font-medium flex items-center justify-center gap-2 disabled:opacity-60 active:scale-[0.98] transition"
            >
              {loading ? <Spinner size={16} className="animate-spin" /> : <ArrowUpRight size={14} weight="bold" />}
              {loading ? "Création…" : "Créer mon compte"}
            </button>

            <div className="text-sm text-neutral-500 text-center pt-4">
              Déjà un compte ?{" "}
              <Link to="/login" className="text-neutral-900 font-medium hover:underline" data-testid="signup-go-login">
                Se connecter
              </Link>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}

function Field({ label, children }) {
  return (
    <label className="block">
      <div className="text-xs uppercase tracking-widest text-neutral-500 mb-1.5">{label}</div>
      {children}
    </label>
  );
}
