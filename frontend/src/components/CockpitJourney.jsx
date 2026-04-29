import React, { useEffect, useState, useCallback } from "react";
import { Link } from "react-router-dom";
import {
  CheckCircle, ArrowRight, CurrencyEur, ChartLineUp, Package, Stack,
  Sparkle, ShieldCheck, PaintBrush, Target, ClipboardText, Rocket, Warning, Lock,
  Globe, Translate,
} from "@phosphor-icons/react";
import { api, apiCall } from "../lib/api";

/**
 * Cockpit Journey — Chantier 1 (gating strict).
 *
 * Source de vérité unique : GET /api/sites/{id}/steps/status.
 * PAS DE VALIDATION MANUELLE — chaque étape est complétée automatiquement
 * par les données en DB (5 produits importés, design publié, etc.).
 *
 * L'utilisateur ne peut pas forcer le passage d'une étape : seule l'action
 * correspondante (importer, publier, générer) fait basculer le statut.
 */

const STEP_META = {
  pricing:   { Icon: CurrencyEur,    subtitle: "Claude analyse le marché et décide si la niche est viable dans chaque pays" },
  import:    { Icon: Package,        subtitle: "Recherche CJ + AliExpress · 5 produits minimum pour débloquer la suite" },
  upsells:   { Icon: Stack,          subtitle: "Accessoires et upgrades · 3 minimum pour débloquer le prévisionnel" },
  forecast:  { Icon: ChartLineUp,    subtitle: "CA prévisionnel, marge, ROAS calculés sur ton vrai catalogue" },
  branding:  { Icon: PaintBrush,     subtitle: "Nom, logo IA, palette · publie le design pour valider cette étape" },
  domain:    { Icon: Globe,          subtitle: "Choisis et achète ton nom de domaine (étape optionnelle, peut être skippée)" },
  translate: { Icon: Translate,      subtitle: "6 langues, hreflang automatique, JSON-LD localisé — au moins 1 traduction pour valider" },
  pages:     { Icon: ClipboardText,  subtitle: "Pages légales + about/FAQ/contact · auto-générées au launch" },
  content:   { Icon: Sparkle,        subtitle: "Blog SEO : 1 article pilier + 3 satellites minimum" },
  seo:       { Icon: Target,         subtitle: "Score SEO ≥70/100 + landings long-tail" },
  qa:        { Icon: ShieldCheck,    subtitle: "Checklist 16 points + bouton Mettre en ligne" },
};

// Mission Finalisation — `translate` ajouté en étape 7, route /sites/:id/translate
const STEP_LINKS = (siteId) => ({
  pricing:   `/sites/${siteId}/pricing`,
  import:    `/sites/${siteId}/sourcing`,
  upsells:   `/sites/${siteId}/upsells`,
  forecast:  `/sites/${siteId}/forecast`,
  branding:  `/sites/${siteId}/branding?step=5`,
  domain:    `/sites/${siteId}/domains?step=6`,
  translate: `/sites/${siteId}/translate?step=7`,
  pages:     `/sites/${siteId}/pages`,        // back-compat
  content:   `/sites/${siteId}/blog-posts?step=8`,
  seo:       `/sites/${siteId}/seo`,
  qa:        `/sites/${siteId}/qa`,
});

export default function CockpitJourney({ site, onRefresh }) {
  const [status, setStatus] = useState(null);
  const [llmStatus, setLlmStatus] = useState("ok");
  const [clearingLlm, setClearingLlm] = useState(false);

  const load = useCallback(async () => {
    const [s, h] = await Promise.all([
      apiCall(() => api.get(`/sites/${site.id}/steps/status`)),
      apiCall(() => api.get(`/platform/llm-status`)),
    ]);
    if (s.data) setStatus(s.data);
    setLlmStatus(h.data?.status || "ok");
  }, [site.id]);

  useEffect(() => { load(); }, [load]);

  const clearLlmFlag = async () => {
    setClearingLlm(true);
    const { data } = await apiCall(() => api.get(`/platform/llm-status?force=1`));
    if (data?.status === "budget_exhausted") {
      await apiCall(() => api.post(`/platform/llm-status/clear`));
    }
    setClearingLlm(false);
    setLlmStatus("ok");
    if (onRefresh) onRefresh();
  };

  if (!status) {
    return (
      <div className="bg-white border border-neutral-200 rounded-2xl p-6" data-testid="cockpit-journey">
        <div className="text-sm text-neutral-500">Chargement du parcours…</div>
      </div>
    );
  }

  const steps = status.steps || [];
  const links = STEP_LINKS(site.id);
  const completedCount = status.completed_count;
  // Lot D — totalCount dynamique (10 étapes maintenant que `domain` est inséré)
  const totalCount = (status.steps && status.steps.length) || status.total_count || 10;
  const pct = status.progress_pct;

  return (
    <div className="bg-white border border-neutral-200 rounded-2xl p-6" data-testid="cockpit-journey">
      {llmStatus === "budget_exhausted" && (
        <div
          className="mb-5 p-4 rounded-xl bg-amber-50 border border-amber-200 flex items-start gap-3"
          data-testid="llm-budget-banner"
        >
          <Warning size={20} weight="fill" className="text-amber-600 flex-shrink-0 mt-0.5" />
          <div className="flex-1 text-sm">
            <div className="font-semibold text-amber-900 mb-0.5">Clé IA à vérifier</div>
            <div className="text-amber-800 leading-relaxed">
              Ta dernière action IA a retourné « budget épuisé ». Le cockpit re-vérifie automatiquement toutes les minutes.
            </div>
          </div>
          <button
            onClick={clearLlmFlag}
            disabled={clearingLlm}
            data-testid="clear-llm-banner"
            className="h-9 px-3 rounded-lg bg-amber-600 hover:bg-amber-700 text-white text-xs font-medium disabled:opacity-60 whitespace-nowrap"
          >
            {clearingLlm ? "…" : "Re-vérifier maintenant"}
          </button>
        </div>
      )}

      <div className="flex items-center justify-between gap-3 mb-4 flex-wrap">
        <div>
          <div className="text-[11px] uppercase tracking-[0.2em] text-neutral-500 mb-1 flex items-center gap-2">
            <Rocket size={12} weight="bold" /> Parcours du site
          </div>
          <h2 className="text-xl font-semibold text-neutral-900" style={{ fontFamily: "'Fraunces', serif" }}>
            {completedCount === totalCount ? "Prêt à soumettre 🎯" : `${completedCount}/${totalCount} étapes complétées automatiquement`}
          </h2>
          <p className="text-[11px] text-neutral-500 mt-1">
            Les étapes se valident automatiquement selon les données. Aucune validation manuelle.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="text-2xl font-semibold text-neutral-900" style={{ fontFamily: "'Fraunces', serif" }}>
            {pct}%
          </div>
          <div className="w-32 h-2 rounded-full bg-neutral-100 overflow-hidden">
            <div
              className="h-full rounded-full transition-all duration-500"
              style={{ width: `${pct}%`, background: "#B84B31" }}
            />
          </div>
        </div>
      </div>

      <div className="space-y-2">
        {steps.map((s) => (
          <StepRow
            key={s.key}
            step={s}
            meta={STEP_META[s.key] || { Icon: CheckCircle, subtitle: "" }}
            href={links[s.key]}
          />
        ))}
      </div>
    </div>
  );
}

function StepRow({ step, meta, href }) {
  const { Icon } = meta;
  // 2026-04-29 (refonte UX strict) — Source de vérité = `step.is_clickable`
  // exposé par le backend `/journey`. Plus de soft_unlocked.
  const isClickableField = typeof step.is_clickable === "boolean" ? step.is_clickable : null;
  const locked = isClickableField !== null
    ? !isClickableField
    : (step.blocked_by_previous && !step.completed);
  const done = step.completed;
  const isAnchor = href && href.startsWith("#");
  const Tag = isAnchor ? "a" : Link;
  const props = isAnchor ? { href } : { to: href };

  const pill = (
    <div
      className={`flex items-center gap-3 p-3 rounded-xl border transition-all ${
        done
          ? "bg-emerald-50/50 border-emerald-200 hover:border-emerald-300"
          : locked
          ? "bg-neutral-50 border-neutral-200 opacity-60 cursor-not-allowed"
          : "bg-white border-neutral-200 hover:border-neutral-400 hover:shadow-sm"
      }`}
      data-testid={`journey-step-${step.key}`}
      title={locked ? "Validez d'abord les étapes précédentes" : undefined}
    >
      <div className={`w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0 ${
        done
          ? "bg-emerald-500 text-white"
          : locked
          ? "bg-neutral-200 text-neutral-400"
          : "bg-neutral-100 text-neutral-600"
      }`}>
        {done ? <CheckCircle size={18} weight="fill" /> :
         locked ? <Lock size={16} weight="bold" /> :
         <Icon size={18} weight="duotone" />}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-baseline gap-2">
          <span className="text-[10px] uppercase tracking-widest text-neutral-400 font-bold">
            {String(step.order).padStart(2, "0")}
          </span>
          <div className={`text-sm font-medium truncate ${locked ? "text-neutral-500" : "text-neutral-900"}`}>
            {step.label}
          </div>
          {done && (
            <span
              className="text-[9px] uppercase tracking-widest bg-emerald-100 text-emerald-800 px-1.5 py-0.5 rounded whitespace-nowrap font-semibold"
              data-testid={`journey-done-${step.key}`}
            >
              {step.manual_validated ? "Validée manuellement" : "Auto-validée"}
            </span>
          )}
        </div>
        <div className="text-xs text-neutral-500 mt-0.5 truncate" title={step.reason}>
          {locked
            ? "Validez d'abord les étapes précédentes pour débloquer"
            : (step.subtitle || step.reason)}
        </div>
      </div>
      <div className="flex items-center gap-2 flex-shrink-0">
        {!locked && (
          <>
            <span className={`text-[11px] font-medium ${
              done ? "text-emerald-700" : "text-neutral-600"
            }`}>
              {done ? "Terminé" : "Ouvrir"}
            </span>
            <ArrowRight size={14} className="text-neutral-400" />
          </>
        )}
      </div>
    </div>
  );

  return (
    <div
      data-testid={`journey-row-${step.key}`}
      aria-disabled={locked ? "true" : undefined}
      tabIndex={locked ? -1 : undefined}
      title={locked ? "Validez d'abord l'étape précédente" : undefined}
    >
      {locked ? pill : <Tag {...props} className="block">{pill}</Tag>}
    </div>
  );
}
