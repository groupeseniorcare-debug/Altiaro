import React from "react";
import {
  Storefront, Eye, Globe, CheckCircle, Link as LinkIcon,
} from "@phosphor-icons/react";

/**
 * Chantier 6 — Header cockpit épuré.
 * Affiche : nom + niche + pays primaire + statut + progression X/9 + 2 CTA
 * (Voir la boutique, Domaine). Rien d'autre. Les anciens boutons
 * `manage-products` / `nav-blog-posts` / `nav-seo-dashboard` sont supprimés :
 * on accède aux pages via les CTA des étapes du CockpitJourney.
 */
export default function SiteHeaderCompact({
  site,
  status,              // { completed_count, total_count, progress_pct } — peut être null
  domainStatus,
  onOpenDomainModal,
}) {
  if (!site) return null;

  const completed = status?.completed_count ?? 0;
  const total = status?.total_count ?? 9;
  const pct = status?.progress_pct ?? Math.round((completed / (total || 1)) * 100);

  const primaryCountry = (site.selected_countries || [])[0] || site.country || "—";

  return (
    <div
      className="bg-white rounded-xl border border-neutral-200 p-6 md:p-7 mb-8 animate-fade-up"
      data-testid="site-header-compact"
    >
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-6">
        {/* LEFT — identité */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-11 h-11 rounded-lg bg-neutral-200 flex items-center justify-center shrink-0">
              <Storefront size={22} weight="duotone" color="#B84B31" />
            </div>
            <span
              className={`text-[11px] uppercase tracking-widest px-2.5 py-1 rounded-full whitespace-nowrap ${
                site.status === "active"
                  ? "bg-emerald-500/10 text-emerald-700"
                  : site.status === "live"
                  ? "bg-[#E0F2FE] text-[#0369A1]"
                  : site.status === "approved"
                  ? "bg-emerald-100 text-emerald-800"
                  : site.status === "pending_review"
                  ? "bg-amber-100 text-amber-800"
                  : "bg-[#F5F5F4] text-neutral-500"
              }`}
              data-testid="site-status-badge"
            >
              {site.status}
            </span>
            <span className="text-[11px] text-neutral-500 whitespace-nowrap">
              Marché principal&nbsp;: <strong className="text-neutral-800">{primaryCountry}</strong>
            </span>
          </div>
          <h1 className="text-2xl md:text-3xl font-semibold text-neutral-900 truncate" data-testid="site-name">
            {site.name}
          </h1>
          {site.niche && (
            <p className="text-sm text-neutral-600 mt-1 truncate">{site.niche}</p>
          )}
          {site.domain && (
            <div className="flex items-center gap-1.5 text-xs text-neutral-600 mt-2">
              <LinkIcon size={13} /> {site.domain}
              {domainStatus?.custom_domain_verified && (
                <CheckCircle size={13} weight="fill" className="text-emerald-600" />
              )}
            </div>
          )}
        </div>

        {/* RIGHT — progress + CTA */}
        <div className="flex flex-col items-stretch md:items-end gap-3 md:min-w-[260px]">
          <div className="w-full" data-testid="journey-progress">
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-[11px] uppercase tracking-widest text-neutral-500">Avancement</span>
              <span className="text-xs font-semibold text-neutral-900 tabular-nums">
                {completed}/{total}
              </span>
            </div>
            <div className="h-2 rounded-full bg-neutral-100 overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-emerald-400 to-emerald-600 transition-all"
                style={{ width: `${pct}%` }}
              />
            </div>
          </div>
          <div className="flex gap-2 flex-wrap md:justify-end">
            <a
              href={`/shop/${site.id}`}
              target="_blank"
              rel="noreferrer"
              data-testid="view-storefront"
              className="h-9 px-3 rounded-lg bg-white border border-neutral-200 hover:border-neutral-900 text-neutral-900 text-xs font-medium flex items-center gap-1.5 transition"
            >
              <Eye size={14} /> Voir la boutique
            </a>
            <button
              type="button"
              onClick={onOpenDomainModal}
              data-testid="manage-domain"
              className="h-9 px-3 rounded-lg bg-white border border-neutral-200 hover:border-neutral-900 text-neutral-900 text-xs font-medium flex items-center gap-1.5 transition"
            >
              <Globe size={14} weight="duotone" /> Domaine
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
