import React, { useState } from "react";
import { useNavigate, Navigate, Link } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { Rocket, SignIn, Spinner } from "@phosphor-icons/react";
import { AltiaroLogo } from "../components/AltiaroLogo";
import CookieConsentBanner from "../components/storefront/CookieConsentBanner";

export default function Login() {
  const { user, login, error } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);

  if (user === null) return null;
  if (user) return <Navigate to="/" replace />;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    const res = await login(email, password);
    setSubmitting(false);
    if (res.ok) navigate("/");
    else if (res.code === "pending_email_verification") {
      navigate(`/verify-email?email=${encodeURIComponent(res.email)}`);
    }
  };

  const handleQuickLogin = async (quickEmail, quickPassword) => {
    setSubmitting(true);
    setEmail(quickEmail);
    setPassword(quickPassword);
    const res = await login(quickEmail, quickPassword);
    setSubmitting(false);
    if (res.ok) navigate("/");
    else if (res.code === "pending_email_verification") {
      navigate(`/verify-email?email=${encodeURIComponent(res.email)}`);
    }
  };

  return (
    <div className="min-h-screen flex items-stretch bg-white">
      <CookieConsentBanner />
      <div className="flex-1 hidden lg:block relative overflow-hidden">
        <div
          className="absolute inset-0 bg-cover bg-center"
          style={{
            backgroundImage:
              "url(https://images.unsplash.com/photo-1665760670979-708eb9626d73?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjA4Mzl8MHwxfHNlYXJjaHwxfHxhYnN0cmFjdCUyMGFyY2hpdGVjdHVyYWwlMjB3YXJtJTIwYmVpZ2UlMjBiYWNrZ3JvdW5kfGVufDB8fHx8MTc3NjY2NzE3N3ww&ixlib=rb-4.1.0&q=85)",
          }}
        />
        <div className="absolute inset-0 bg-gradient-to-br from-[#B84B31]/15 via-transparent to-[#1C1917]/40" />
        <div className="relative h-full flex flex-col justify-between p-12 text-white">
          <div className="flex items-center">
            <AltiaroLogo variant="horizontal" size={26} color="#FFFFFF" />
          </div>
          <div className="max-w-md">
            <h1 className="text-4xl font-heading font-semibold leading-tight mb-4">
              Votre usine à marques e-commerce.
            </h1>
            <p className="text-white/85 text-lg leading-relaxed">
              Un cockpit unique pour lancer, piloter et dupliquer vos boutiques — étape par
              étape, sous votre validation, jusqu'à la première vente.
            </p>
          </div>
        </div>
      </div>

      <div className="flex-1 flex items-center justify-center p-8">
        <div className="w-full max-w-md">
          <div className="mb-8">
            <div className="text-xs uppercase tracking-widest text-neutral-500 mb-2">
              Espace collaborateur
            </div>
            <h2 className="text-3xl font-heading font-semibold text-neutral-900 mb-2">
              Connexion
            </h2>
            <p className="text-neutral-600">Accédez à votre cockpit.</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5" data-testid="login-form">
            <div>
              <label className="block text-[13px] font-medium text-neutral-900 mb-1.5">
                Email professionnel
              </label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                data-testid="login-email"
                className="w-full h-12 px-4 rounded-xl border border-neutral-200 bg-white focus:outline-none focus:ring-2 focus:ring-zinc-500/30 focus:border-neutral-400 transition"
                placeholder="vous@conceptfactory.fr"
              />
            </div>
            <div>
              <label className="block text-[13px] font-medium text-neutral-900 mb-1.5">
                Mot de passe
              </label>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                data-testid="login-password"
                className="w-full h-12 px-4 rounded-xl border border-neutral-200 bg-white focus:outline-none focus:ring-2 focus:ring-zinc-500/30 focus:border-neutral-400 transition"
                placeholder="••••••••••"
              />
            </div>

            {error && (
              <div
                className="p-3.5 rounded-lg bg-red-500/10 text-red-400 text-sm"
                data-testid="login-error"
              >
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={submitting}
              data-testid="login-submit"
              className="w-full h-12 rounded-xl bg-neutral-900 hover:bg-neutral-800 text-white font-medium transition-all duration-200 disabled:opacity-60 flex items-center justify-center gap-2 active:scale-[0.98]"
            >
              {submitting ? (
                <>
                  <Spinner size={18} className="animate-spin" /> Connexion...
                </>
              ) : (
                <>
                  <SignIn size={18} /> Se connecter
                </>
              )}
            </button>
          </form>

          <div className="mt-6 grid grid-cols-2 gap-3">
            <button
              type="button"
              onClick={() => handleQuickLogin("admin@conceptfactory.fr", "Factory2026!")}
              disabled={submitting}
              data-testid="login-quick-admin"
              className="h-11 rounded-xl border border-neutral-200 bg-white hover:border-[#B84B31] hover:bg-neutral-100/40 text-sm font-medium text-neutral-900 transition-all duration-200 disabled:opacity-60 flex items-center justify-center gap-2"
            >
              <Rocket size={14} weight="fill" className="text-neutral-900" />
              Admin (demo)
            </button>
            <button
              type="button"
              onClick={() => handleQuickLogin("concepteur@conceptfactory.fr", "Concepteur2026!")}
              disabled={submitting}
              data-testid="login-quick-concepteur"
              className="h-11 rounded-xl border border-neutral-200 bg-white hover:border-[#7C3AED] hover:bg-neutral-100/40 text-sm font-medium text-neutral-900 transition-all duration-200 disabled:opacity-60 flex items-center justify-center gap-2"
            >
              <SignIn size={14} className="text-[#7C3AED]" />
              Concepteur (demo)
            </button>
          </div>

          <div className="mt-4 p-4 rounded-xl bg-neutral-200 border border-neutral-200">
            <div className="text-[11px] uppercase tracking-widest text-neutral-500 mb-1.5">
              Comptes de démonstration
            </div>
            <div className="font-mono text-[12px] text-neutral-600">
              admin@conceptfactory.fr · Factory2026!
            </div>
            <div className="font-mono text-[12px] text-neutral-600">
              concepteur@conceptfactory.fr · Concepteur2026!
            </div>
          </div>

          <div className="mt-6 text-sm text-neutral-500 text-center">
            Pas encore de compte ?{" "}
            <Link
              to="/signup"
              className="text-neutral-900 font-medium hover:underline"
              data-testid="login-signup-link"
            >
              Créer un compte Concepteur
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
