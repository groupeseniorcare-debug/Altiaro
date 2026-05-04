import React, { useState, useMemo } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import {
  ArrowLeft,
  ArrowRight,
  Sparkle,
  ArrowClockwise,
  Info,
  CheckCircle,
  Clock,
  CaretDown,
  CaretUp,
} from "@phosphor-icons/react";
import useCockpitJourney from "../../hooks/useCockpitJourney";

/**
 * StepLayout — coquille unifiée « Luxury Minimal » pour chaque étape du cockpit.
 *
 * Props :
 *   siteId          (string, required)
 *   stepKey         (string, required) — ex. "pricing", "import", ...
 *   title           (string) — Titre display (Fraunces serif)
 *   subtitle        (string) — Une phrase quoi faire
 *   whatItDoes      (string | ReactNode) — Encart « À quoi ça sert ? » rétractable
 *   estimatedTime   (string) — ex. "~2 min"
 *   magicButton     ({ label, onClick, loading, disabled, icon? })
 *   secondaryActions([{ label, onClick, variant? }]) — optionnel
 *   children        (ReactNode) — Contenu principal de l'étape
 *
 * Layout :
 *   ┌─ Top bar : breadcrumb + progress (● ● ● ● ○ ○ ○ ○ ○ ○)
 *   ├─ Header  : Étape N/10 · Titre · subtitle · ~temps · statut · [À quoi ça sert ?]
 *   ├─ Body    : children (zone métier)
 *   └─ Footer  : [← Précédent]        [magic button]   [Continuer →]
 */

const STEP_ORDER = [
  "pricing",
  "import",
  "upsells",
  "forecast",
  "branding",
  "domain",
  "content",
  "translate",
  "seo",
  "qa",
];

const STEP_LINKS = (siteId) => ({
  pricing: `/sites/${siteId}/pricing`,
  import: `/sites/${siteId}/sourcing`,
  upsells: `/sites/${siteId}/upsells`,
  forecast: `/sites/${siteId}/forecast`,
  branding: `/sites/${siteId}/branding?step=5`,
  domain: `/sites/${siteId}/domains?step=6`,
  content: `/sites/${siteId}/blog-posts?step=7`,
  translate: `/sites/${siteId}/translate?step=8`,
  seo: `/sites/${siteId}/seo`,
  qa: `/sites/${siteId}#site-qa-panel`,
});

const STEP_LABELS = {
  pricing: "Pricing",
  import: "Import produits",
  upsells: "Upsells",
  forecast: "Prévisionnel",
  branding: "Identité de marque",
  domain: "Nom de domaine",
  content: "Contenu blog",
  translate: "Traduction",
  seo: "Score SEO",
  qa: "Validation finale",
};

export default function StepLayout({
  siteId,
  stepKey,
  title,
  subtitle,
  whatItDoes,
  estimatedTime,
  magicButton,
  secondaryActions = [],
  children,
}) {
  const navigate = useNavigate();
  const [showWhatItDoes, setShowWhatItDoes] = useState(false);
  const { steps, currentStepKey, currentStepIndex, totalSteps, getStep } = useCockpitJourney(siteId);

  const stepIndex = STEP_ORDER.indexOf(stepKey) + 1; // 1-based
  const currentStep = getStep(stepKey);
  const isCompleted = !!(currentStep && currentStep.completed);
  const isCurrent = currentStepKey === stepKey;

  const prevStepKey = stepIndex > 1 ? STEP_ORDER[stepIndex - 2] : null;
  const nextStepKey = stepIndex < STEP_ORDER.length ? STEP_ORDER[stepIndex] : null;

  const prevStep = prevStepKey ? getStep(prevStepKey) : null;
  const nextStep = nextStepKey ? getStep(nextStepKey) : null;

  // Bouton « Continuer » actif uniquement si l'étape courante est complétée.
  const canContinue = isCompleted && !!nextStepKey;

  const progressDots = useMemo(() => {
    return STEP_ORDER.map((k, i) => {
      const s = (steps || []).find((x) => x.key === k);
      const done = s?.completed;
      const current = k === stepKey;
      return {
        key: k,
        done,
        current,
        index: i + 1,
      };
    });
  }, [steps, stepKey]);

  const statusBadge = isCompleted ? (
    <span className="inline-flex items-center gap-1.5 text-[11px] uppercase tracking-[0.18em] text-emerald-700 font-medium">
      <CheckCircle size={13} weight="fill" /> Complété
    </span>
  ) : isCurrent ? (
    <span className="inline-flex items-center gap-1.5 text-[11px] uppercase tracking-[0.18em] text-amber-700 font-medium">
      <Clock size={13} weight="fill" /> En cours
    </span>
  ) : (
    <span className="inline-flex items-center gap-1.5 text-[11px] uppercase tracking-[0.18em] text-neutral-400 font-medium">
      À faire
    </span>
  );

  return (
    <div className="min-h-screen bg-[#F5F2EB]" style={{ fontFamily: "'Inter', sans-serif" }}>
      {/* Top bar : breadcrumb compact + progress dots ------------------------ */}
      <div className="sticky top-0 z-20 backdrop-blur-md bg-[#F5F2EB]/80 border-b border-neutral-200/60">
        <div className="max-w-5xl mx-auto px-6 md:px-10 h-14 flex items-center justify-between">
          <Link
            to={`/sites/${siteId}`}
            className="inline-flex items-center gap-2 text-[13px] text-neutral-600 hover:text-neutral-900 transition"
          >
            <ArrowLeft size={14} /> Cockpit
          </Link>
          <div className="hidden md:flex items-center gap-1.5" data-testid="journey-progress-dots">
            {progressDots.map((d) => (
              <div
                key={d.key}
                title={`Étape ${d.index} · ${STEP_LABELS[d.key] || d.key}`}
                className={`h-1.5 w-5 rounded-full transition-all ${
                  d.current
                    ? "bg-neutral-900 w-8"
                    : d.done
                    ? "bg-emerald-500"
                    : "bg-neutral-300"
                }`}
              />
            ))}
          </div>
          <div className="text-[12px] text-neutral-500 tabular-nums" data-testid="journey-counter">
            {stepIndex}/{STEP_ORDER.length}
          </div>
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-6 md:px-10 py-10 md:py-14">
        {/* Header étape ---------------------------------------------------- */}
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, ease: "easeOut" }}
          className="mb-10"
          data-testid="step-header"
        >
          <div className="text-[11px] uppercase tracking-[0.28em] text-neutral-500 mb-3 flex items-center gap-3">
            <span>Étape {stepIndex} / {STEP_ORDER.length}</span>
            <span className="text-neutral-300">·</span>
            {statusBadge}
          </div>

          <h1
            className="text-4xl md:text-5xl font-normal text-neutral-900 leading-tight tracking-tight"
            style={{ fontFamily: "'Fraunces', serif", fontOpticalSizing: "auto" }}
          >
            {title}
          </h1>

          {subtitle && (
            <p className="text-[15px] text-neutral-600 mt-4 max-w-2xl leading-relaxed">
              {subtitle}
            </p>
          )}

          <div className="mt-5 flex items-center gap-4 text-[12px] text-neutral-500">
            {estimatedTime && (
              <span className="inline-flex items-center gap-1.5">
                <Clock size={13} /> {estimatedTime}
              </span>
            )}
            {whatItDoes && (
              <button
                type="button"
                onClick={() => setShowWhatItDoes((v) => !v)}
                className="inline-flex items-center gap-1.5 text-neutral-600 hover:text-neutral-900 transition"
                data-testid="what-it-does-toggle"
              >
                <Info size={13} /> À quoi ça sert ?
                {showWhatItDoes ? <CaretUp size={11} /> : <CaretDown size={11} />}
              </button>
            )}
          </div>

          <AnimatePresence initial={false}>
            {showWhatItDoes && whatItDoes && (
              <motion.div
                key="what-it-does-panel"
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.2, ease: "easeOut" }}
                className="overflow-hidden"
                style={{ pointerEvents: showWhatItDoes ? "auto" : "none" }}
              >
                <div
                  className="mt-5 p-5 rounded-2xl bg-white/60 border border-neutral-200 text-sm text-neutral-700 leading-relaxed max-w-3xl"
                  data-testid="what-it-does-body"
                  aria-hidden={!showWhatItDoes}
                >
                  {typeof whatItDoes === "string" ? (
                    <p>{whatItDoes}</p>
                  ) : (
                    whatItDoes
                  )}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>

        {/* Body ------------------------------------------------------------ */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.45, delay: 0.1 }}
          className="mb-14"
          data-testid="step-body"
        >
          {children}
        </motion.div>

        {/* Footer ---------------------------------------------------------- */}
        <div
          className="pt-8 border-t border-neutral-200/70 flex items-center justify-between gap-4"
          data-testid="step-footer"
        >
          <div className="flex-1">
            {prevStepKey && (
              <Link
                to={STEP_LINKS(siteId)[prevStepKey]}
                className="inline-flex items-center gap-2 text-[13px] text-neutral-600 hover:text-neutral-900 transition"
                data-testid="step-prev"
              >
                <ArrowLeft size={14} />
                Précédent · {STEP_LABELS[prevStepKey] || prevStepKey}
              </Link>
            )}
          </div>

          <div className="flex items-center gap-3">
            {secondaryActions.map((a, i) => (
              <button
                key={i}
                onClick={a.onClick}
                disabled={a.disabled || a.loading}
                className="h-11 px-4 rounded-xl border border-neutral-300 bg-white text-sm text-neutral-700 hover:bg-neutral-50 disabled:opacity-50"
              >
                {a.label}
              </button>
            ))}

            {magicButton && (
              <button
                onClick={magicButton.onClick}
                disabled={magicButton.disabled || magicButton.loading}
                data-testid="magic-button"
                className="h-11 px-6 rounded-xl bg-neutral-900 text-white text-sm font-medium flex items-center gap-2 hover:bg-neutral-800 transition disabled:opacity-60 disabled:cursor-not-allowed shadow-[0_2px_16px_-4px_rgba(0,0,0,0.25)]"
              >
                {magicButton.loading ? (
                  <ArrowClockwise size={14} className="animate-spin" />
                ) : magicButton.icon ? (
                  magicButton.icon
                ) : (
                  <Sparkle size={14} weight="fill" />
                )}
                {magicButton.label}
              </button>
            )}

            {nextStepKey && (
              <button
                onClick={() => navigate(STEP_LINKS(siteId)[nextStepKey])}
                disabled={!canContinue}
                data-testid="step-continue"
                className={`h-11 px-5 rounded-xl text-sm font-medium flex items-center gap-2 transition ${
                  canContinue
                    ? "bg-emerald-600 text-white hover:bg-emerald-700"
                    : "bg-neutral-200 text-neutral-400 cursor-not-allowed"
                }`}
                title={canContinue ? "" : "Complète cette étape pour continuer"}
              >
                Continuer · {STEP_LABELS[nextStepKey]}
                <ArrowRight size={14} />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
