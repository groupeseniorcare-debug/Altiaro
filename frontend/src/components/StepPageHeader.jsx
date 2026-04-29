import React from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowLeft, ArrowRight, CheckCircle, Lock, Sparkle } from "@phosphor-icons/react";

/**
 * Header uniforme pour les pages d'étape du cockpit (étapes 1 → 10).
 *
 * Affiche :
 *   - Lien retour cockpit + breadcrumb
 *   - Titre H1 Cormorant Garamond + sous-titre
 *   - Barre de progression "X / 10 étapes complétées"
 *
 * Props :
 *   - siteId, siteName       : pour le breadcrumb
 *   - stepNumber (int)       : 1..10
 *   - stepLabel (string)
 *   - stepSubtitle (string)
 *   - completedCount / totalCount : pour la progress bar
 *   - completed (bool)       : étape elle-même validée ?
 *   - locked (bool)          : étape verrouillée par cascade ?
 */
export default function StepPageHeader({
  siteId,
  siteName,
  stepNumber,
  stepLabel,
  stepSubtitle,
  completedCount = 0,
  totalCount = 10,
  completed = false,
  locked = false,
}) {
  return (
    <div className="mb-8" data-testid="step-page-header">
      {/* Breadcrumb + back */}
      <div className="flex items-center gap-3 text-[12px] uppercase tracking-[0.2em] text-neutral-500 mb-4">
        <Link
          to={`/sites/${siteId}`}
          className="flex items-center gap-1.5 hover:text-neutral-900 transition"
          data-testid="header-back-cockpit"
        >
          <ArrowLeft size={13} weight="regular" /> Retour au cockpit
        </Link>
        <span className="text-neutral-300">·</span>
        <span className="text-neutral-400 truncate max-w-[200px]">{siteName || "Site"}</span>
        <span className="text-neutral-300">/</span>
        <span className="text-neutral-700 font-medium">Étape {stepNumber}</span>
      </div>

      {/* Title + status pill */}
      <div className="flex flex-wrap items-baseline gap-3 mb-2">
        <span
          className="text-[14px] uppercase tracking-[0.2em] text-neutral-400"
          style={{
            fontFamily: "'Cormorant Garamond', 'Cormorant', Georgia, serif",
            fontStyle: "italic",
          }}
        >
          Étape {String(stepNumber).padStart(2, "0")}
        </span>
        <h1
          className="text-[34px] md:text-[42px] leading-[1.1] tracking-[-0.01em] text-neutral-900"
          style={{
            fontFamily: "'Cormorant Garamond', 'Cormorant', Georgia, serif",
            fontWeight: 500,
          }}
        >
          {stepLabel}
        </h1>
        {completed && (
          <span
            className="inline-flex items-center gap-1.5 px-2.5 py-1 text-[10px] uppercase tracking-[0.18em] font-semibold"
            style={{
              background: "#E6F4EE",
              color: "#0F6E4D",
              borderRadius: "2px",
            }}
          >
            <CheckCircle size={12} weight="fill" /> Validée
          </span>
        )}
        {locked && !completed && (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 text-[10px] uppercase tracking-[0.18em] font-semibold bg-neutral-100 text-neutral-500 rounded-[2px]">
            <Lock size={12} weight="bold" /> Verrouillée
          </span>
        )}
      </div>

      {stepSubtitle && (
        <p className="text-[15px] text-neutral-600 leading-relaxed max-w-[640px]">
          {stepSubtitle}
        </p>
      )}

      {/* Progress bar */}
      <div className="mt-6 max-w-[480px]">
        <div className="flex items-center justify-between text-[11px] uppercase tracking-[0.2em] text-neutral-500 mb-1.5">
          <span>Progression</span>
          <span className="font-semibold text-neutral-700">
            {completedCount} / {totalCount} étapes
          </span>
        </div>
        <div className="h-1.5 bg-neutral-200 rounded-full overflow-hidden">
          <div
            className="h-full transition-all duration-500"
            style={{
              width: `${Math.min(100, (completedCount / totalCount) * 100)}%`,
              background: "#0F6E4D",
            }}
          />
        </div>
        <div className="flex items-center gap-1 mt-2">
          {Array.from({ length: totalCount }).map((_, i) => (
            <span
              key={i}
              className="h-1 flex-1 rounded-full"
              style={{
                background: i < completedCount ? "#0F6E4D" : "#E5E5E5",
              }}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

/**
 * Bouton "Valider et passer à l'étape suivante" — composant réutilisable.
 *
 * Props :
 *   - siteId, currentStepKey
 *   - nextStepNumber, nextStepLabel, nextStepHref
 *   - canValidate (bool)        : conditions remplies ?
 *   - missingConditions (array) : liste des conditions encore à remplir
 *   - onValidate (func async)   : callback API qui renvoie ok=true
 */
export function StepValidateCTA({
  currentStepKey: _currentStepKey,
  nextStepNumber,
  nextStepLabel,
  nextStepHref,
  canValidate = false,
  missingConditions = [],
  onValidate,
}) {
  const navigate = useNavigate();
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState(null);

  const handleClick = async () => {
    if (!canValidate || busy) return;
    setBusy(true);
    setError(null);
    try {
      const ok = onValidate ? await onValidate() : true;
      if (ok && nextStepHref) {
        navigate(nextStepHref);
      } else if (!ok) {
        setError("La validation a échoué — réessayez.");
      }
    } catch (e) {
      setError(e?.message || "Erreur lors de la validation");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div
      className="mt-10 p-6 md:p-7"
      style={{
        background: "#FFFFFF",
        border: "1px solid #E8E2D5",
        borderRadius: "4px",
      }}
      data-testid="step-validate-cta"
    >
      <div className="flex flex-wrap items-start gap-5 justify-between">
        <div className="flex-1 min-w-[260px]">
          <div className="text-[10px] uppercase tracking-[0.32em] text-neutral-500 mb-2">
            Validation de l'étape
          </div>
          {canValidate ? (
            <p className="text-[14px] text-neutral-700 leading-relaxed">
              Toutes les conditions sont remplies. Cliquez pour valider et
              passer à <strong className="text-neutral-900">{nextStepLabel || "l'étape suivante"}</strong>.
            </p>
          ) : (
            <>
              <p className="text-[13px] text-neutral-600 leading-relaxed mb-2">
                Pour passer à l'étape suivante, complétez :
              </p>
              <ul className="text-[13px] text-neutral-700 space-y-1">
                {missingConditions.map((c, idx) => (
                  <li key={idx} className="flex items-start gap-2">
                    <span className="text-neutral-400 mt-[2px]">•</span>
                    <span>{c}</span>
                  </li>
                ))}
              </ul>
            </>
          )}
          {error && (
            <p className="mt-2 text-[12px] text-rose-700">{error}</p>
          )}
        </div>
        <button
          onClick={handleClick}
          disabled={!canValidate || busy}
          className={`h-12 px-6 text-[13px] font-semibold inline-flex items-center gap-2 transition whitespace-nowrap ${
            canValidate && !busy
              ? "bg-neutral-900 hover:bg-black text-white shadow-sm hover:shadow"
              : "bg-neutral-100 text-neutral-400 cursor-not-allowed"
          }`}
          style={{ borderRadius: "2px" }}
          data-testid="step-validate-button"
          title={canValidate ? "" : missingConditions.join(" · ")}
        >
          {busy ? (
            "Validation…"
          ) : canValidate ? (
            <>
              <Sparkle size={14} weight="duotone" />
              Valider et passer à l'étape&nbsp;
              {nextStepNumber || "suivante"}
              <ArrowRight size={14} weight="bold" />
            </>
          ) : (
            <>
              <Lock size={13} weight="bold" />
              Conditions non remplies
            </>
          )}
        </button>
      </div>
    </div>
  );
}
