import React, { useEffect, useState, useCallback } from "react";
import { Link } from "react-router-dom";
import {
  CheckCircle, Circle, ArrowRight, CurrencyEur, ChartLineUp, Package, Stack,
  Sparkle, ShieldCheck, PaintBrush, Target, ClipboardText, Rocket, Warning, Lock,
} from "@phosphor-icons/react";
import { api, apiCall } from "../lib/api";

/**
 * Cockpit Journey — linear 9-step guide that replaces the 50 prompts.
 * Each step links to its tool. Completion is derived from site data.
 */
export default function CockpitJourney({ site, onRefresh }) {
  const [pricing, setPricing] = useState(null);
  const [forecast, setForecast] = useState(null);
  const [upsells, setUpsells] = useState(null);
  const [qa, setQa] = useState(null);
  const [llmStatus, setLlmStatus] = useState("ok");
  const [clearingLlm, setClearingLlm] = useState(false);
  const [validated, setValidated] = useState([]);
  const [validatingStep, setValidatingStep] = useState(null);

  const load = useCallback(async () => {
    const [p, f, u, q, h, siteRes] = await Promise.all([
      apiCall(() => api.get(`/sites/${site.id}/pricing-analysis`)),
      apiCall(() => api.get(`/sites/${site.id}/financial-forecast`)),
      apiCall(() => api.get(`/sites/${site.id}/upsell-recommendations`)),
      apiCall(() => api.get(`/sites/${site.id}/qa-audit`)),
      apiCall(() => api.get(`/platform/llm-status`)),
      apiCall(() => api.get(`/sites/${site.id}`)),
    ]);
    setPricing(p.data && p.data.generated_at ? p.data : null);
    setForecast(f.data && f.data.generated_at ? f.data : null);
    setUpsells(u.data && u.data.generated_at ? u.data : null);
    setQa(q.data || null);
    setLlmStatus(h.data?.status || "ok");
    setValidated(siteRes.data?.journey_validated || []);
  }, [site.id]);

  useEffect(() => { load(); }, [load]);

  const clearLlmFlag = async () => {
    setClearingLlm(true);
    // 1) Ask the backend to re-probe the LLM (will auto-clear if the key works).
    const { data } = await apiCall(() => api.get(`/platform/llm-status?force=1`));
    // 2) If probe still says exhausted, fall back to manual override.
    if (data?.status === "budget_exhausted") {
      await apiCall(() => api.post(`/platform/llm-status/clear`));
    }
    setClearingLlm(false);
    setLlmStatus("ok");
  };

  const toggleStepValidation = async (stepKey, newValue) => {
    setValidatingStep(stepKey);
    const { data, error } = await apiCall(() =>
      api.post(`/sites/${site.id}/journey/validate-step`, { step: stepKey, validated: newValue })
    );
    setValidatingStep(null);
    if (error) { window.alert(error); return; }
    setValidated(data?.validated_steps || []);
    if (onRefresh) onRefresh();
  };

  const products = site.products_count || 0;
  const hasBrand = !!(site.design?.brand?.name || site.name);
  const hasLogo = !!(site.design?.brand?.logo_url || site.design?.brand?.logo);
  const hasAbout = !!(site.design?.about?.paragraphs || site.design?.about?.content);
  const blogCount = (site.design?.blog_posts || []).length;

  const isValidated = (key) => validated.includes(key);

  // Ordered gating: each step requires the previous one to be validated.
  const stepOrder = ["pricing", "import", "upsells", "forecast", "branding", "pages", "content", "seo", "qa"];
  const firstUnvalidatedIdx = stepOrder.findIndex((k) => !isValidated(k));
  // All steps up to and including firstUnvalidatedIdx are accessible; beyond = locked.
  const isLocked = (key) => {
    if (isValidated(key)) return false;
    const idx = stepOrder.indexOf(key);
    return idx > firstUnvalidatedIdx;
  };
  // "ready" = auto-heuristic signal that the data is in place (informational)
  const readyPricing = !!pricing;
  const readyImport = products >= 1;
  const readyUpsells = !!upsells;
  const readyForecast = !!forecast;
  const readyBranding = hasBrand && hasLogo;
  const readyPages = hasAbout;
  const readyContent = blogCount >= 1;
  const readySeo = (site.design?.seo_score || 0) >= 70;
  const readyQa = !!qa && qa.ready_for_submission;

  const steps = [
    {
      key: "pricing",
      n: 1,
      Icon: CurrencyEur,
      title: "Analyse concurrence & pricing",
      subtitle: "Claude analyse le marché et recommande tes fourchettes de prix",
      done: isValidated("pricing"),
      locked: isLocked("pricing"),
      ready: readyPricing,
      cta: pricing ? "Consulter l'analyse" : "Lancer l'analyse IA",
      to: `/sites/${site.id}/pricing`,
    },
    {
      key: "import",
      n: 2,
      Icon: Package,
      title: "Import du catalogue",
      subtitle: "Recherche CJ Dropshipping + AliExpress, import en 1 clic (IA enrichit les fiches)",
      done: isValidated("import"),
      locked: isLocked("import"),
      ready: readyImport,
      cta: products > 0 ? `${products} produit${products > 1 ? "s" : ""} importé${products > 1 ? "s" : ""}` : "Rechercher & importer",
      to: `/sites/${site.id}/sourcing`,
    },
    {
      key: "upsells",
      n: 3,
      Icon: Stack,
      title: "Upsells & accessoires recommandés",
      subtitle: "L'IA te suggère 6-10 accessoires pertinents à importer",
      done: isValidated("upsells"),
      locked: isLocked("upsells"),
      ready: readyUpsells,
      cta: upsells ? "Voir les recommandations" : "Générer les upsells IA",
      to: `/sites/${site.id}/upsells`,
    },
    {
      key: "forecast",
      n: 4,
      Icon: ChartLineUp,
      title: "Étude financière 30 jours",
      subtitle: "CA prévisionnel, marge brute, ROAS avec ton vrai catalogue",
      done: isValidated("forecast"),
      locked: isLocked("forecast"),
      ready: readyForecast,
      cta: forecast ? `ROAS prévisionnel : ${forecast.projection?.roas}x` : "Calculer le prévisionnel",
      to: `/sites/${site.id}/forecast`,
    },
    {
      key: "branding",
      n: 5,
      Icon: PaintBrush,
      title: "Identité & branding",
      subtitle: "Nom final, logo IA, palette, baseline — injectés dans le template",
      done: isValidated("branding"),
      locked: isLocked("branding"),
      ready: readyBranding,
      cta: hasBrand && hasLogo ? "Branding configuré" : "Générer mon site (IA)",
      to: `/sites/${site.id}/design`,
    },
    {
      key: "pages",
      n: 6,
      Icon: ClipboardText,
      title: "Pages essentielles (À propos, Contact, CGV…)",
      subtitle: "Copywriting IA + tes infos légales",
      done: isValidated("pages"),
      locked: isLocked("pages"),
      ready: readyPages,
      cta: hasAbout ? "Pages remplies" : "Compléter les pages",
      to: `/sites/${site.id}/design`,
    },
    {
      key: "content",
      n: 7,
      Icon: Sparkle,
      title: "Blog & contenu SEO",
      subtitle: "10 articles piliers + satellites générés par l'IA",
      done: isValidated("content"),
      locked: isLocked("content"),
      ready: readyContent,
      cta: blogCount > 0 ? `${blogCount} article${blogCount > 1 ? "s" : ""} publié${blogCount > 1 ? "s" : ""}` : "Générer les articles",
      to: `/sites/${site.id}/blog-posts`,
    },
    {
      key: "seo",
      n: 8,
      Icon: Target,
      title: "Santé SEO / AEO",
      subtitle: "Score multi-dimensions + recommandations actionnables",
      done: isValidated("seo"),
      locked: isLocked("seo"),
      ready: readySeo,
      cta: "Consulter le dashboard SEO",
      to: `/sites/${site.id}/seo`,
    },
    {
      key: "qa",
      n: 9,
      Icon: ShieldCheck,
      title: "QA automatique & soumission",
      subtitle: "13 contrôles qualité + envoi à la validation Admin",
      done: isValidated("qa"),
      locked: isLocked("qa"),
      ready: readyQa,
      cta: qa ? `Score ${qa.score}/100 · ${qa.blockers?.length || 0} bloquant${(qa.blockers?.length || 0) !== 1 ? "s" : ""}` : "Lancer le QA",
      to: "#site-qa-panel",
      isAnchor: true,
    },
  ];

  const completedCount = steps.filter((s) => s.done).length;
  const pct = Math.round((completedCount / steps.length) * 100);

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
              Ta dernière action IA a retourné « budget épuisé ». Le cockpit re-vérifie automatiquement toutes les minutes — si ta clé a été rechargée, la bannière disparaîtra seule à la prochaine action IA. Tu peux aussi la forcer maintenant.
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
            {completedCount === 9 ? "Prêt à soumettre 🎯" : `${completedCount}/9 étapes complétées`}
          </h2>
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
            s={s}
            onToggleValidate={toggleStepValidation}
            validating={validatingStep === s.key}
          />
        ))}
      </div>
    </div>
  );
}

function StepRow({ s, onToggleValidate, validating }) {
  const Tag = s.isAnchor ? "a" : Link;
  const props = s.isAnchor ? { href: s.to } : { to: s.to };

  const pill = (
    <div
      className={`flex items-center gap-3 p-3 rounded-xl border transition-all ${
        s.done
          ? "bg-emerald-50/50 border-emerald-200 hover:border-emerald-300"
          : s.locked
          ? "bg-neutral-50 border-neutral-200 opacity-60 cursor-not-allowed"
          : "bg-white border-neutral-200 hover:border-neutral-400 hover:shadow-sm"
      }`}
      data-testid={`journey-step-${s.key}`}
    >
      <div className={`w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0 ${
        s.done
          ? "bg-emerald-500 text-white"
          : s.locked
          ? "bg-neutral-200 text-neutral-400"
          : "bg-neutral-100 text-neutral-600"
      }`}>
        {s.done ? <CheckCircle size={18} weight="fill" /> :
         s.locked ? <Lock size={16} weight="bold" /> :
         <s.Icon size={18} weight="duotone" />}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-baseline gap-2">
          <span className="text-[10px] uppercase tracking-widest text-neutral-400 font-bold">{String(s.n).padStart(2, "0")}</span>
          <div className={`text-sm font-medium truncate ${s.locked ? "text-neutral-500" : "text-neutral-900"}`}>{s.title}</div>
          {s.ready && !s.done && !s.locked && (
            <span className="text-[9px] uppercase tracking-widest bg-amber-100 text-amber-800 px-1.5 py-0.5 rounded whitespace-nowrap font-semibold">
              Prêt à valider
            </span>
          )}
        </div>
        <div className="text-xs text-neutral-500 mt-0.5 truncate">
          {s.locked ? "Verrouillée — valide l'étape précédente d'abord" : s.subtitle}
        </div>
      </div>
      <div className="flex items-center gap-2 flex-shrink-0">
        {!s.locked && (
          <>
            <span className={`text-[11px] font-medium ${s.done ? "text-emerald-700" : "text-neutral-600"}`}>
              {s.cta}
            </span>
            <ArrowRight size={14} className="text-neutral-400" />
          </>
        )}
      </div>
    </div>
  );

  return (
    <div className="flex items-stretch gap-2" data-testid={`journey-row-${s.key}`}>
      <div className="flex-1 min-w-0">
        {s.locked ? pill : <Tag {...props} className="block">{pill}</Tag>}
      </div>
      {/* Manual validation toggle */}
      <button
        type="button"
        onClick={(e) => { e.stopPropagation(); onToggleValidate(s.key, !s.done); }}
        disabled={validating || (s.locked && !s.done)}
        data-testid={`validate-step-${s.key}`}
        title={
          s.locked && !s.done
            ? "Valide l'étape précédente pour débloquer"
            : s.done
            ? "Annuler la validation"
            : "Marquer cette étape comme validée"
        }
        className={`px-3 rounded-xl border text-xs font-medium transition whitespace-nowrap flex items-center gap-1.5 disabled:opacity-40 disabled:cursor-not-allowed ${
          s.done
            ? "bg-emerald-600 hover:bg-emerald-700 text-white border-emerald-600"
            : s.locked
            ? "bg-neutral-100 text-neutral-400 border-neutral-200"
            : s.ready
            ? "bg-amber-500 hover:bg-amber-600 text-white border-amber-500"
            : "bg-white hover:bg-neutral-50 text-neutral-700 border-neutral-300"
        }`}
      >
        {validating ? "…" : s.done ? (<><CheckCircle size={12} weight="fill" /> Validée</>) : s.locked ? (<><Lock size={10} weight="bold" /> Verrouillée</>) : "Valider"}
      </button>
    </div>
  );
}
