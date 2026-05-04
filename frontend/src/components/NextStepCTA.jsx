import React, { useEffect, useState, useCallback } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowRight, CheckCircle, Lock, Hourglass } from "@phosphor-icons/react";
import { api, apiCall } from "../lib/api";

/**
 * NextStepCTA — bouton "Étape suivante" injecté en bas de chaque écran
 * d'étape du cockpit (1..8).
 *
 * Source de vérité : GET /api/sites/{id}/steps/status (fallback sur /journey).
 *
 * États affichés :
 *   1. Chargement → rien
 *   2. Étape courante introuvable → rien (silencieux, n'bloque pas l'écran)
 *   3. Étape courante non complétée → encart neutre "complète cette étape pour
 *      débloquer la suivante"
 *   4. Étape courante complétée → bouton primary "Étape suivante : X →"
 *      (route vers STEP_LINKS[next.key] ou cockpit pour qa)
 *
 * Props :
 *   - siteId (string, required)
 *   - currentKey (string, required) : un des keys de STEP_LINKS ci-dessous
 */

const STEP_LINKS = (siteId) => ({
  pricing:   `/sites/${siteId}/pricing`,
  import:    `/sites/${siteId}/sourcing`,
  upsells:   `/sites/${siteId}/upsells`,
  forecast:  `/sites/${siteId}/forecast`,
  branding:  `/sites/${siteId}/branding?step=5`,
  domain:    `/sites/${siteId}/domains?step=6`,
  content:   `/sites/${siteId}/blog-posts?step=7`,
  translate: `/sites/${siteId}/translate?step=8`,
  seo:       `/sites/${siteId}/seo`,
  qa:        `/sites/${siteId}#site-qa-panel`,
});

const STEP_LABEL = {
  pricing:   "Pricing",
  import:    "Import des produits",
  upsells:   "Upsells & accessoires",
  forecast:  "Prévisionnel financier",
  branding:  "Identité de marque",
  domain:    "Nom de domaine",
  content:   "Contenu blog SEO",
  translate: "Traduction multilingue",
  seo:       "Score SEO",
  qa:        "Validation finale (QA)",
};

export default function NextStepCTA({ siteId, currentKey }) {
  const navigate = useNavigate();
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    const { data } = await apiCall(() => api.get(`/sites/${siteId}/steps/status`));
    setStatus(data);
    setLoading(false);
  }, [siteId]);

  useEffect(() => { if (siteId) load(); }, [siteId, load]);

  // Refresh quand un produit est importé / supprimé / suggestion adoptée etc.
  // Un autre composant (ex: ProductImportPanel) émet l'event après mutation,
  // ce qui bascule l'étape de "pending" → "complétée" en temps réel sans
  // exiger un reload page.
  useEffect(() => {
    if (!siteId) return;
    const handler = () => load();
    window.addEventListener("cf_steps_changed", handler);
    return () => window.removeEventListener("cf_steps_changed", handler);
  }, [siteId, load]);

  if (loading || !status) return null;

  const steps = status.steps || [];
  const order = ["pricing", "import", "upsells", "forecast", "branding", "domain", "content", "translate", "seo", "qa"];
  const current = steps.find((s) => s.key === currentKey);
  const idx = order.indexOf(currentKey);
  const nextKey = idx >= 0 && idx < order.length - 1 ? order[idx + 1] : null;
  const next = nextKey ? steps.find((s) => s.key === nextKey) : null;
  const links = STEP_LINKS(siteId);

  // Étape courante non détectée → on n'affiche rien (pas une erreur bloquante)
  if (!current) return null;

  // Étape déjà complétée → CTA primary
  if (current.completed) {
    if (!nextKey) {
      return (
        <div
          className="mt-12 mb-2 p-6 rounded-2xl bg-emerald-50 border border-emerald-200 flex items-center gap-4"
          data-testid="cta-step-completed-final"
        >
          <CheckCircle size={32} weight="fill" className="text-emerald-600 flex-shrink-0" />
          <div className="flex-1">
            <div className="text-sm font-semibold text-emerald-900">Toutes les étapes sont validées 🎉</div>
            <div className="text-xs text-emerald-800 mt-0.5">Tu peux soumettre ton site à la validation depuis le cockpit.</div>
          </div>
          <Link
            to={`/sites/${siteId}`}
            className="h-11 px-5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-semibold flex items-center gap-2 whitespace-nowrap"
            data-testid="cta-back-to-cockpit"
          >
            Retour au cockpit <ArrowRight size={16} weight="bold" />
          </Link>
        </div>
      );
    }
    const nextLabel = STEP_LABEL[nextKey] || nextKey;
    const nextHref = links[nextKey];
    const nextLocked = next && next.blocked_by_previous && !next.completed === false ? false : false;
    // (next ne peut pas être verrouillé puisque current.completed === true →
    // le gating accepte la suite ; mais on tolère le cas)
    return (
      <div
        className="mt-12 mb-2 p-6 rounded-2xl bg-white border-2 border-neutral-900 shadow-sm flex items-center gap-4"
        data-testid="cta-next-step"
      >
        <div className="w-12 h-12 rounded-xl bg-emerald-100 flex items-center justify-center flex-shrink-0">
          <CheckCircle size={26} weight="fill" className="text-emerald-600" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-[11px] uppercase tracking-[0.2em] text-emerald-700 font-semibold mb-0.5">
            Étape validée automatiquement
          </div>
          <div className="text-sm text-neutral-900">
            <span className="font-semibold">Prochaine étape :</span>{" "}
            <span>{nextLabel}</span>
          </div>
        </div>
        <button
          onClick={() => navigate(nextHref)}
          disabled={nextLocked}
          data-testid={`cta-goto-${nextKey}`}
          className="h-12 px-6 rounded-xl bg-neutral-900 hover:bg-neutral-800 text-white text-sm font-semibold flex items-center gap-2 disabled:opacity-50 whitespace-nowrap shadow-sm hover:shadow"
        >
          Passer à l'étape suivante <ArrowRight size={18} weight="bold" />
        </button>
      </div>
    );
  }

  // 2026-04-29 (refonte UX strict) — Plus de soft_unlocked. Une étape est
  // soit completed (vert ✅ + CTA suivant), soit current (encart neutre
  // "à compléter"), soit locked (cf. cascade côté CockpitJourney).

  // Étape pas encore complétée → encart neutre informatif (pas un blocage UI)
  return (
    <div
      className="mt-12 mb-2 p-5 rounded-2xl bg-neutral-50 border border-neutral-200 flex items-start gap-3"
      data-testid="cta-step-pending"
    >
      <Hourglass size={20} weight="duotone" className="text-neutral-500 flex-shrink-0 mt-0.5" />
      <div className="flex-1">
        <div className="text-sm font-medium text-neutral-900">
          Cette étape n'est pas encore validée
        </div>
        <div className="text-xs text-neutral-600 mt-0.5 leading-relaxed">
          {current.reason || "Complète l'action demandée ci-dessus pour débloquer l'étape suivante."}
          {nextKey && (
            <> Ensuite, tu pourras passer à <strong>{STEP_LABEL[nextKey] || nextKey}</strong>.</>
          )}
        </div>
      </div>
      {nextKey && (
        <span
          className="inline-flex items-center gap-1.5 text-[11px] uppercase tracking-widest text-neutral-400 font-medium px-3 py-1.5 rounded-lg bg-white border border-neutral-200 whitespace-nowrap"
        >
          <Lock size={12} weight="bold" /> Verrouillé
        </span>
      )}
    </div>
  );
}
