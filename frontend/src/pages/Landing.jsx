import React, { useEffect } from "react";
import { Link } from "react-router-dom";
import { AltioraLogo } from "../components/AltioraLogo";
import {
  ArrowUpRight,
  Gauge,
  Sparkle,
  ShieldCheck,
  Lightning,
  Globe,
  ChartLineUp,
} from "@phosphor-icons/react";

/**
 * Public landing page for Altiora — discoverable by Google, Mollie,
 * partners. No auth required.
 */
export default function Landing() {
  useEffect(() => {
    document.title = "Altiora — La plateforme e-commerce des partenariats éclairés";
  }, []);

  return (
    <div className="min-h-screen bg-white text-neutral-900">
      {/* Nav */}
      <nav className="border-b border-neutral-200 bg-white/80 backdrop-blur sticky top-0 z-20">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link to="/" className="flex items-center" data-testid="landing-home-link">
            <AltioraLogo variant="horizontal" size={22} color="#0A0A0A" />
          </Link>
          <div className="flex items-center gap-6">
            <a
              href="#comment-ca-marche"
              className="text-sm font-medium text-neutral-600 hover:text-neutral-900 hidden sm:inline"
            >
              Comment ça marche
            </a>
            <a
              href="#partenariat"
              className="text-sm font-medium text-neutral-600 hover:text-neutral-900 hidden sm:inline"
            >
              Partenariat
            </a>
            <Link
              to="/login"
              data-testid="landing-cta-login"
              className="h-9 px-4 rounded-lg bg-neutral-900 text-white text-sm font-medium hover:bg-neutral-800 inline-flex items-center gap-1.5"
            >
              Accès plateforme
              <ArrowUpRight size={14} weight="bold" />
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="max-w-6xl mx-auto px-6 pt-24 pb-20 text-center">
        <div className="inline-flex items-center gap-2 h-7 px-3 rounded-full border border-neutral-200 text-[11px] uppercase tracking-widest text-neutral-600 mb-8">
          <Sparkle size={12} weight="fill" /> Altiora · Silver Economy e-commerce
        </div>
        <h1 className="text-5xl sm:text-6xl lg:text-7xl font-semibold tracking-tight leading-[1.05] mb-6">
          La plateforme e-commerce
          <br className="hidden sm:block" /> des partenariats éclairés.
        </h1>
        <p className="text-lg text-neutral-600 max-w-2xl mx-auto leading-relaxed mb-10">
          Altiora accompagne les entrepreneurs qui lancent des marques premium
          sur la Silver Economy. Analyse de niches, site e-commerce généré par
          IA, pilotage complet — partage 50/50 de la marge brute, sans frais
          fixes.
        </p>
        <div className="flex flex-wrap items-center justify-center gap-3">
          <Link
            to="/login"
            data-testid="landing-hero-cta"
            className="h-12 px-6 rounded-xl bg-neutral-900 text-white font-medium hover:bg-neutral-800 inline-flex items-center gap-2"
          >
            Devenir Concepteur
            <ArrowUpRight size={16} weight="bold" />
          </Link>
          <a
            href="#comment-ca-marche"
            className="h-12 px-6 rounded-xl border border-neutral-300 text-neutral-900 font-medium hover:bg-neutral-50 inline-flex items-center"
          >
            Comment ça marche
          </a>
        </div>

        {/* KPI band */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-6 mt-20 text-left max-w-3xl mx-auto">
          {[
            { n: "6", l: "Marchés européens" },
            { n: "< 2min", l: "Scan Go / No-Go" },
            { n: "50/50", l: "Marge brute partagée" },
            { n: "0€", l: "Frais fixes mensuels" },
          ].map((kpi) => (
            <div key={kpi.l} className="border-l border-neutral-200 pl-4">
              <div className="text-3xl font-semibold tabular-nums">{kpi.n}</div>
              <div className="text-xs text-neutral-500 mt-1">{kpi.l}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Comment ça marche */}
      <section id="comment-ca-marche" className="max-w-6xl mx-auto px-6 py-20 border-t border-neutral-200">
        <div className="text-[11px] uppercase tracking-widest text-neutral-500 mb-3">
          Comment ça marche
        </div>
        <h2 className="text-3xl sm:text-4xl font-semibold tracking-tight mb-14 max-w-2xl">
          De l'idée à la première commande — en 4 étapes guidées.
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {[
            {
              n: "01",
              icon: ChartLineUp,
              t: "Analyser",
              d: "Scan multi-marchés (FR, DE, IT, BE, CH, NL) avec volumes Google, concurrence, potentiel de marge.",
            },
            {
              n: "02",
              icon: Sparkle,
              t: "Construire",
              d: "Site e-commerce complet généré par IA en 7 sections. Palette, copy, images, légalité — tout est auto.",
            },
            {
              n: "03",
              icon: Globe,
              t: "Lancer",
              d: "Domaine custom (via OVH intégré), catalogue produits, paiements Mollie, expéditions — vous pilotez depuis le cockpit.",
            },
            {
              n: "04",
              icon: Gauge,
              t: "Récolter",
              d: "Virements automatiques les 1er et 15 du mois. 50% de la marge brute HT directement sur votre IBAN.",
            },
          ].map((step) => (
            <div
              key={step.n}
              className="border border-neutral-200 rounded-lg p-6 hover:border-neutral-400 transition"
            >
              <div className="flex items-center justify-between mb-6">
                <div className="text-[11px] uppercase tracking-widest text-neutral-500 tabular-nums">
                  {step.n}
                </div>
                <step.icon size={18} weight="duotone" className="text-neutral-900" />
              </div>
              <div className="text-lg font-semibold mb-2">{step.t}</div>
              <div className="text-sm text-neutral-600 leading-relaxed">{step.d}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Partenariat 50/50 */}
      <section id="partenariat" className="max-w-6xl mx-auto px-6 py-20 border-t border-neutral-200">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-start">
          <div>
            <div className="text-[11px] uppercase tracking-widest text-neutral-500 mb-3">
              Le partenariat Altiora
            </div>
            <h2 className="text-3xl sm:text-4xl font-semibold tracking-tight mb-6">
              Aligné avec vos intérêts. Par construction.
            </h2>
            <p className="text-neutral-600 leading-relaxed mb-6">
              Altiora ne facture aucun abonnement, aucun coût de setup, aucune
              commission fixe. Vous payez uniquement si vous vendez.
            </p>
            <p className="text-neutral-600 leading-relaxed">
              Pour chaque commande de vos sites, la marge brute hors taxes (prix
              de vente HT - coût d'achat HT - frais bancaires - TVA) est
              partagée équitablement : 50% pour vous, 50% pour Altiora.
            </p>
          </div>
          <div className="bg-neutral-50 border border-neutral-200 rounded-lg p-8">
            <div className="text-[11px] uppercase tracking-widest text-neutral-500 mb-4">
              Exemple concret · commande 1 199€ TTC
            </div>
            <div className="space-y-3 text-sm">
              {[
                ["Prix de vente TTC", "1 199,00 €", ""],
                ["TVA 20%", "− 199,83 €", "text-neutral-500"],
                ["Prix de vente HT", "999,17 €", "font-medium"],
                ["Coût d'achat HT", "− 420,00 €", "text-neutral-500"],
                ["Frais Mollie (1.8% + 0.25€)", "− 21,83 €", "text-neutral-500"],
                ["Marge brute HT", "557,34 €", "font-semibold text-neutral-900 border-t border-neutral-200 pt-3 mt-2"],
              ].map(([l, v, cls]) => (
                <div key={l} className={`flex justify-between ${cls}`}>
                  <span>{l}</span>
                  <span className="tabular-nums">{v}</span>
                </div>
              ))}
            </div>
            <div className="mt-5 pt-5 border-t border-neutral-300 flex justify-between items-baseline">
              <div>
                <div className="text-[11px] uppercase tracking-widest text-neutral-500">
                  Votre part (50%)
                </div>
                <div className="text-3xl font-semibold text-neutral-900">278,67 €</div>
              </div>
              <div className="text-right text-xs text-neutral-500">
                Versé aux <br />
                <span className="font-medium text-neutral-900">1er et 15</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Trust / sécurité */}
      <section className="max-w-6xl mx-auto px-6 py-20 border-t border-neutral-200">
        <div className="text-[11px] uppercase tracking-widest text-neutral-500 mb-3">
          Infrastructure
        </div>
        <h2 className="text-3xl sm:text-4xl font-semibold tracking-tight mb-10 max-w-2xl">
          Bâti sur les standards de l'e-commerce européen.
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {[
            {
              icon: ShieldCheck,
              t: "Paiements Mollie",
              d: "PCI-DSS Level 1. Cartes, SEPA, iDEAL, Bancontact. Remboursements en 1 clic.",
            },
            {
              icon: Lightning,
              t: "Sites haute-perf",
              d: "Rendu côté serveur, SEO multi-pays, hreflang, schema.org, sitemap XML. Noté 95+ Lighthouse.",
            },
            {
              icon: ShieldCheck,
              t: "RGPD by design",
              d: "Hébergement Europe, chiffrement en transit et au repos, droits RGPD sous 30 jours.",
            },
          ].map((f) => (
            <div key={f.t} className="border border-neutral-200 rounded-lg p-6">
              <f.icon size={22} weight="duotone" className="text-neutral-900 mb-4" />
              <div className="text-lg font-semibold mb-2">{f.t}</div>
              <div className="text-sm text-neutral-600 leading-relaxed">{f.d}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Final CTA */}
      <section className="max-w-6xl mx-auto px-6 py-24 border-t border-neutral-200 text-center">
        <h2 className="text-3xl sm:text-4xl font-semibold tracking-tight mb-4 max-w-2xl mx-auto">
          Prêt à lancer votre première marque ?
        </h2>
        <p className="text-neutral-600 mb-8">
          Inscription sur invitation pour garantir la qualité de l'accompagnement.
        </p>
        <div className="flex justify-center gap-3">
          <a
            href="mailto:contact@altiora.com"
            data-testid="landing-contact-cta"
            className="h-12 px-6 rounded-xl bg-neutral-900 text-white font-medium hover:bg-neutral-800 inline-flex items-center gap-2"
          >
            Demander un accès
            <ArrowUpRight size={16} weight="bold" />
          </a>
          <Link
            to="/login"
            className="h-12 px-6 rounded-xl border border-neutral-300 text-neutral-900 font-medium hover:bg-neutral-50 inline-flex items-center"
          >
            Je suis déjà Concepteur
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-neutral-200 bg-neutral-50">
        <div className="max-w-6xl mx-auto px-6 py-12 grid grid-cols-2 md:grid-cols-4 gap-8 text-sm">
          <div className="col-span-2">
            <AltioraLogo variant="horizontal" size={22} color="#0A0A0A" />
            <p className="text-neutral-500 mt-4 max-w-sm">
              La plateforme e-commerce des partenariats éclairés. <br />
              Édité par Robin Zuchiatti (entrepreneur individuel), exerçant sous
              le nom commercial Altiora.
            </p>
          </div>
          <div>
            <div className="text-[11px] uppercase tracking-widest text-neutral-500 mb-3">
              Plateforme
            </div>
            <div className="space-y-2 text-neutral-700">
              <Link to="/login" className="block hover:text-neutral-900">
                Connexion Concepteur
              </Link>
              <a href="mailto:contact@altiora.com" className="block hover:text-neutral-900">
                contact@altiora.com
              </a>
            </div>
          </div>
          <div>
            <div className="text-[11px] uppercase tracking-widest text-neutral-500 mb-3">
              Légal
            </div>
            <div className="space-y-2 text-neutral-700">
              <Link to="/mentions-legales" className="block hover:text-neutral-900" data-testid="footer-mentions">
                Mentions légales
              </Link>
              <Link to="/cgu" className="block hover:text-neutral-900" data-testid="footer-cgu">
                CGU
              </Link>
              <Link to="/confidentialite" className="block hover:text-neutral-900" data-testid="footer-confidentialite">
                Confidentialité
              </Link>
              <Link to="/cookies" className="block hover:text-neutral-900" data-testid="footer-cookies">
                Cookies
              </Link>
            </div>
          </div>
        </div>
        <div className="border-t border-neutral-200">
          <div className="max-w-6xl mx-auto px-6 py-6 text-xs text-neutral-500">
            © {new Date().getFullYear()} Altiora — SIREN 883 803 967 · TVA FR42883803967
          </div>
        </div>
      </footer>
    </div>
  );
}
