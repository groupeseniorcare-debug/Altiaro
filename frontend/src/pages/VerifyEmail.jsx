import React, { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { api } from "../lib/api";
import { AltiaroLogo } from "../components/AltiaroLogo";
import { Spinner, ArrowClockwise } from "@phosphor-icons/react";
import { useAuth } from "../lib/auth";
import CookieConsentBanner from "../components/storefront/CookieConsentBanner";

function formatError(detail) {
  if (detail == null) return "Une erreur est survenue";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map((e) => e?.msg || "").filter(Boolean).join(" ");
  if (detail?.message) return detail.message;
  return String(detail);
}

export default function VerifyEmail() {
  const [params] = useSearchParams();
  const email = params.get("email") || "";
  const nav = useNavigate();
  const { setUser } = useAuth();
  const [digits, setDigits] = useState(["", "", "", "", "", ""]);
  const [loading, setLoading] = useState(false);
  const [resending, setResending] = useState(false);
  const [err, setErr] = useState("");
  const [info, setInfo] = useState("");
  const [cooldown, setCooldown] = useState(0);
  const refs = useRef([]);

  useEffect(() => {
    refs.current[0]?.focus();
  }, []);

  useEffect(() => {
    if (cooldown <= 0) return;
    const id = setInterval(() => setCooldown((c) => c - 1), 1000);
    return () => clearInterval(id);
  }, [cooldown]);

  const code = digits.join("");

  const handleChange = (idx, val) => {
    const digit = val.replace(/\D/g, "").slice(-1);
    const next = [...digits];
    next[idx] = digit;
    setDigits(next);
    if (digit && idx < 5) refs.current[idx + 1]?.focus();
  };

  const handleKeyDown = (idx, e) => {
    if (e.key === "Backspace" && !digits[idx] && idx > 0) {
      refs.current[idx - 1]?.focus();
    }
    if (e.key === "ArrowLeft" && idx > 0) refs.current[idx - 1]?.focus();
    if (e.key === "ArrowRight" && idx < 5) refs.current[idx + 1]?.focus();
  };

  const handlePaste = (e) => {
    const pasted = (e.clipboardData.getData("text") || "").replace(/\D/g, "").slice(0, 6);
    if (!pasted) return;
    e.preventDefault();
    const next = Array(6).fill("");
    for (let i = 0; i < pasted.length; i++) next[i] = pasted[i];
    setDigits(next);
    refs.current[Math.min(pasted.length, 5)]?.focus();
  };

  const submit = async (e) => {
    e?.preventDefault?.();
    if (code.length !== 6) return;
    setErr("");
    setLoading(true);
    try {
      const { data } = await api.post("/auth/verify-email", { email, code });
      setUser(data);
      nav("/", { replace: true });
    } catch (e) {
      setErr(formatError(e.response?.data?.detail) || e.message);
    } finally {
      setLoading(false);
    }
  };

  // Auto-submit when all 6 digits filled
  useEffect(() => {
    if (code.length === 6 && !loading) submit();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [code]);

  const resend = async () => {
    if (cooldown > 0 || resending) return;
    setErr("");
    setInfo("");
    setResending(true);
    try {
      const { data } = await api.post("/auth/resend-code", { email });
      setInfo(data?.detail || "Un nouveau code vous a été envoyé.");
      setCooldown(60);
      setDigits(["", "", "", "", "", ""]);
      refs.current[0]?.focus();
    } catch (e) {
      setErr(formatError(e.response?.data?.detail) || e.message);
    } finally {
      setResending(false);
    }
  };

  return (
    <div
      className="min-h-screen bg-white flex flex-col items-center px-6"
      style={{ fontFamily: "'Inter', system-ui, sans-serif" }}
    >
      <CookieConsentBanner />
      <nav className="w-full max-w-6xl h-16 flex items-center justify-between border-b border-neutral-200">
        <Link to="/" className="flex items-center" data-testid="verify-home-link">
          <AltiaroLogo variant="horizontal" size={22} color="#0A0A0A" />
        </Link>
        <Link to="/login" className="text-sm text-neutral-600 hover:text-neutral-900">
          Se connecter
        </Link>
      </nav>

      <div className="flex-1 flex items-center justify-center w-full">
        <div className="max-w-md w-full py-12">
          <div className="text-[11px] uppercase tracking-[0.14em] text-neutral-500 mb-3">
            Vérification email
          </div>
          <h1 className="text-3xl sm:text-4xl font-semibold tracking-tight mb-2">
            Entrez votre code
          </h1>
          <p className="text-neutral-500 mb-8 text-sm leading-relaxed">
            Nous venons d'envoyer un code à 6 chiffres à{" "}
            <span className="text-neutral-900 font-medium">{email || "votre adresse email"}</span>.
            Code valable 15 minutes.
          </p>

          <form onSubmit={submit} data-testid="verify-form">
            <div className="flex items-center justify-between gap-2 mb-6" onPaste={handlePaste}>
              {digits.map((d, i) => (
                <input
                  key={i}
                  ref={(el) => (refs.current[i] = el)}
                  type="text"
                  inputMode="numeric"
                  maxLength={1}
                  value={d}
                  onChange={(e) => handleChange(i, e.target.value)}
                  onKeyDown={(e) => handleKeyDown(i, e)}
                  data-testid={`verify-digit-${i}`}
                  className="w-12 h-14 sm:w-14 sm:h-16 text-center text-2xl font-semibold font-mono tabular-nums border border-neutral-300 rounded-lg focus:border-neutral-900 focus:ring-2 focus:ring-neutral-900/10 outline-none transition"
                />
              ))}
            </div>

            {err && (
              <div
                className="text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg p-3 mb-4"
                data-testid="verify-error"
              >
                {err}
              </div>
            )}
            {info && (
              <div
                className="text-sm text-emerald-700 bg-emerald-50 border border-emerald-200 rounded-lg p-3 mb-4"
                data-testid="verify-info"
              >
                {info}
              </div>
            )}

            <button
              type="submit"
              disabled={loading || code.length !== 6}
              data-testid="verify-submit"
              className="w-full h-12 rounded-xl bg-neutral-900 hover:bg-neutral-800 text-white font-medium flex items-center justify-center gap-2 disabled:opacity-60 active:scale-[0.98] transition"
            >
              {loading && <Spinner size={16} className="animate-spin" />}
              {loading ? "Vérification…" : "Vérifier et activer mon compte"}
            </button>

            <div className="flex items-center justify-center gap-2 mt-6 text-sm text-neutral-500">
              <span>Vous n'avez rien reçu ?</span>
              <button
                type="button"
                onClick={resend}
                disabled={cooldown > 0 || resending}
                data-testid="verify-resend"
                className="inline-flex items-center gap-1 text-neutral-900 font-medium hover:underline disabled:text-neutral-400 disabled:no-underline"
              >
                <ArrowClockwise size={13} weight="bold" />
                {cooldown > 0 ? `Renvoyer (${cooldown}s)` : resending ? "Envoi…" : "Renvoyer un code"}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
