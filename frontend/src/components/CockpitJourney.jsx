import React, { useEffect, useState, useCallback } from "react";
import { Link } from "react-router-dom";
import {
  CheckCircle, Circle, ArrowRight, CurrencyEur, ChartLineUp, Package, Stack,
  Sparkle, ShieldCheck, PaintBrush, Target, ClipboardText, Rocket,
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

  const load = useCallback(async () => {
    const [p, f, u, q] = await Promise.all([
      apiCall(() => api.get(`/sites/${site.id}/pricing-analysis`)),
      apiCall(() => api.get(`/sites/${site.id}/financial-forecast`)),
      apiCall(() => api.get(`/sites/${site.id}/upsell-recommendations`)),
      apiCall(() => api.get(`/sites/${site.id}/qa-audit`)),
    ]);
    setPricing(p.data && p.data.generated_at ? p.data : null);
    setForecast(f.data && f.data.generated_at ? f.data : null);
    setUpsells(u.data && u.data.generated_at ? u.data : null);
    setQa(q.data || null);
  }, [site.id]);

  useEffect(() => { load(); }, [load]);

  const products = site.products_count || 0;
  const hasBrand = !!(site.design?.brand?.name || site.name);
  const hasLogo = !!(site.design?.brand?.logo_url || site.design?.brand?.logo);
  const hasAbout = !!(site.design?.about?.paragraphs || site.design?.about?.content);
  const blogCount = (site.design?.blog_posts || []).length;

  const steps = [
    {
      key: "pricing",
      n: 1,
      Icon: CurrencyEur,
      title: "Analyse concurrence & pricing",
      subtitle: "Claude analyse le marché et recommande tes fourchettes de prix",
      done: !!pricing,
      cta: pricing ? "Consulter l'analyse" : "Lancer l'analyse IA",
      to: `/sites/${site.id}/pricing`,
    },
    {
      key: "import",
      n: 2,
      Icon: Package,
      title: "Import du catalogue",
      subtitle: "Recherche CJ Dropshipping + AliExpress, import en 1 clic (IA enrichit les fiches)",
      done: products >= 5,
      cta: products > 0 ? `${products} produits importés` : "Rechercher & importer",
      to: `/sites/${site.id}/sourcing`,
    },
    {
      key: "upsells",
      n: 3,
      Icon: Stack,
      title: "Upsells & accessoires recommandés",
      subtitle: "L'IA te suggère 6-10 accessoires pertinents à importer",
      done: !!upsells,
      cta: upsells ? "Voir les recommandations" : "Générer les upsells IA",
      to: `/sites/${site.id}/upsells`,
      disabled: products < 3,
      disabledReason: "Importe d'abord 3+ produits principaux",
    },
    {
      key: "forecast",
      n: 4,
      Icon: ChartLineUp,
      title: "Étude financière 30 jours",
      subtitle: "CA prévisionnel, marge brute, ROAS avec ton vrai catalogue",
      done: !!forecast,
      cta: forecast ? `ROAS prévisionnel : ${forecast.projection?.roas}x` : "Calculer le prévisionnel",
      to: `/sites/${site.id}/forecast`,
      disabled: products < 1,
      disabledReason: "Importe au moins 1 produit",
    },
    {
      key: "branding",
      n: 5,
      Icon: PaintBrush,
      title: "Identité & branding",
      subtitle: "Nom final, logo IA, palette, baseline — injectés dans le template",
      done: hasBrand && hasLogo,
      cta: hasBrand && hasLogo ? "Branding configuré" : "Générer mon site (IA)",
      to: `/sites/${site.id}/design`,
    },
    {
      key: "pages",
      n: 6,
      Icon: ClipboardText,
      title: "Pages essentielles (À propos, Contact, CGV…)",
      subtitle: "Copywriting IA + tes infos légales",
      done: hasAbout,
      cta: hasAbout ? "Pages remplies" : "Compléter les pages",
      to: `/sites/${site.id}/design`,
    },
    {
      key: "content",
      n: 7,
      Icon: Sparkle,
      title: "Blog & contenu SEO",
      subtitle: "10 articles piliers + satellites générés par l'IA",
      done: blogCount >= 3,
      cta: blogCount > 0 ? `${blogCount} article${blogCount > 1 ? "s" : ""} publié${blogCount > 1 ? "s" : ""}` : "Générer les articles",
      to: `/sites/${site.id}/blog-posts`,
    },
    {
      key: "seo",
      n: 8,
      Icon: Target,
      title: "Santé SEO / AEO",
      subtitle: "Score multi-dimensions + recommandations actionnables",
      done: (site.design?.seo_score || 0) >= 70,
      cta: "Consulter le dashboard SEO",
      to: `/sites/${site.id}/seo`,
    },
    {
      key: "qa",
      n: 9,
      Icon: ShieldCheck,
      title: "QA automatique & soumission",
      subtitle: "13 contrôles qualité + envoi à la validation Admin",
      done: !!qa && qa.ready_for_submission,
      cta: qa ? `Score ${qa.score}/100 · ${qa.blockers?.length || 0} bloquant${(qa.blockers?.length || 0) !== 1 ? "s" : ""}` : "Lancer le QA",
      to: "#site-qa-panel",
      isAnchor: true,
    },
  ];

  const completedCount = steps.filter((s) => s.done).length;
  const pct = Math.round((completedCount / steps.length) * 100);

  return (
    <div className="bg-white border border-neutral-200 rounded-2xl p-6" data-testid="cockpit-journey">
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
        {steps.map((s) => <StepRow key={s.key} s={s} />)}
      </div>
    </div>
  );
}

function StepRow({ s }) {
  const Tag = s.isAnchor ? "a" : Link;
  const props = s.isAnchor ? { href: s.to } : { to: s.to };

  const inner = (
    <div
      className={`flex items-center gap-3 p-3 rounded-xl border transition-all ${
        s.done
          ? "bg-emerald-50/50 border-emerald-200 hover:border-emerald-300"
          : s.disabled
          ? "bg-neutral-50 border-neutral-200 opacity-60 cursor-not-allowed"
          : "bg-white border-neutral-200 hover:border-neutral-400 hover:shadow-sm"
      }`}
      data-testid={`journey-step-${s.key}`}
    >
      <div className={`w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0 ${
        s.done ? "bg-emerald-500 text-white" : "bg-neutral-100 text-neutral-600"
      }`}>
        {s.done ? <CheckCircle size={18} weight="fill" /> : <s.Icon size={18} weight="duotone" />}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-baseline gap-2">
          <span className="text-[10px] uppercase tracking-widest text-neutral-400 font-bold">{String(s.n).padStart(2, "0")}</span>
          <div className="text-sm font-medium text-neutral-900 truncate">{s.title}</div>
        </div>
        <div className="text-xs text-neutral-500 mt-0.5 truncate">
          {s.disabled ? s.disabledReason : s.subtitle}
        </div>
      </div>
      <div className="flex items-center gap-2 flex-shrink-0">
        <span className={`text-[11px] font-medium ${s.done ? "text-emerald-700" : "text-neutral-600"}`}>
          {s.cta}
        </span>
        {!s.disabled && <ArrowRight size={14} className="text-neutral-400" />}
      </div>
    </div>
  );

  if (s.disabled) return inner;
  return <Tag {...props} className="block">{inner}</Tag>;
}
