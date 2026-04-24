import React from "react";
import { Link } from "react-router-dom";
import { Rocket, ChartLineUp, Truck, EnvelopeSimple } from "@phosphor-icons/react";

/**
 * Chantier 6 — Bannière affichée quand les 9 étapes du CockpitJourney sont
 * toutes complètes (site validé / prêt à partir). Remplace visuellement le
 * parcours et oriente le concepteur vers les outils post-validation :
 *   - Dashboard analytics (Phase 2, route stub `/sites/:id/analytics`)
 *   - Demander une campagne Google Ads à l'admin
 *   - Commandes fournisseurs (ex-bouton du cockpit, désormais rangé ici)
 */
export default function PostValidationBanner({ site, adminEmail = "admin@altiaro.com" }) {
  if (!site) return null;

  const mailto = `mailto:${adminEmail}?subject=${encodeURIComponent(
    `[Altiaro] Lancer campagne Google Ads — ${site.name}`
  )}&body=${encodeURIComponent(
    `Bonjour,\n\nLe site "${site.name}" (id: ${site.id}) est validé.\nMerci de lancer les campagnes Google Ads sur les marchés : ${
      (site.selected_countries || []).join(", ") || "(à définir)"
    }.\n\nMerci.`
  )}`;

  return (
    <div
      className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-emerald-50 via-white to-emerald-50 border border-emerald-200 p-6 md:p-8 mb-8 animate-fade-up"
      data-testid="post-validation-banner"
    >
      <div
        className="absolute -top-8 -right-8 w-40 h-40 rounded-full bg-emerald-200/40 blur-3xl pointer-events-none"
        aria-hidden
      />
      <div className="relative flex flex-col md:flex-row md:items-center md:justify-between gap-5">
        <div className="flex items-start gap-4 flex-1 min-w-0">
          <div className="w-12 h-12 rounded-xl bg-emerald-600/10 flex items-center justify-center shrink-0">
            <Rocket size={24} weight="duotone" className="text-emerald-700" />
          </div>
          <div className="min-w-0">
            <div className="text-[11px] uppercase tracking-[0.2em] text-emerald-700 font-medium mb-1">
              Site validé
            </div>
            <h2
              className="text-xl md:text-2xl font-semibold text-neutral-900"
              style={{ fontFamily: "'Fraunces', serif" }}
            >
              🎉 Toutes les étapes sont complètes — passons au lancement
            </h2>
            <p className="text-sm text-neutral-600 mt-1.5 max-w-xl">
              Tu peux maintenant suivre les performances de{" "}
              <strong className="text-neutral-900">{site.name}</strong> et demander à l'équipe
              admin de lancer les campagnes Google Ads sur tes marchés.
            </p>
          </div>
        </div>

        <div className="flex flex-col gap-2 md:min-w-[240px] md:items-stretch">
          <Link
            to={`/sites/${site.id}/analytics`}
            data-testid="goto-analytics"
            className="h-10 px-4 rounded-xl bg-neutral-900 hover:bg-neutral-800 text-white text-sm font-medium flex items-center justify-center gap-2 transition"
          >
            <ChartLineUp size={16} weight="fill" /> Dashboard analytics
          </Link>
          <a
            href={mailto}
            data-testid="request-ads-campaign"
            className="h-10 px-4 rounded-xl bg-white border border-neutral-300 hover:border-neutral-900 text-neutral-900 text-sm font-medium flex items-center justify-center gap-2 transition"
          >
            <EnvelopeSimple size={16} weight="duotone" /> Demander campagne Ads
          </a>
          <Link
            to={`/sites/${site.id}/fulfillment`}
            data-testid="goto-fulfillment"
            className="h-9 px-3 rounded-xl bg-white/60 border border-emerald-200 hover:border-emerald-400 text-emerald-800 text-xs font-medium flex items-center justify-center gap-1.5 transition"
          >
            <Truck size={13} weight="duotone" /> Commandes fournisseurs
          </Link>
        </div>
      </div>
    </div>
  );
}
