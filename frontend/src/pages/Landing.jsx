import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { AltiaroLogo } from "../components/AltiaroLogo";
import CookieConsentBanner from "../components/storefront/CookieConsentBanner";
import {
  ArrowUpRight,
  Gauge,
  Sparkle,
  ShieldCheck,
  Lightning,
  Globe,
  ChartLineUp,
  Check,
  X,
  Plus,
  Minus,
  ArrowRight,
} from "@phosphor-icons/react";

/**
 * Public landing page for Altiaro — served on altiaro.com.
 * No auth required — discoverable by Google, Mollie, partners.
 *
 * Design: monochrome (black on white), mixed serif (Fraunces, display) +
 * sans-serif (Inter, body). Distinctive, asymmetric, ultra-premium.
 */
export default function Landing() {
  useEffect(() => {
    document.title = "Altiaro — La plateforme e-commerce des partenariats éclairés";
  }, []);

  return (
    <div
      className="min-h-screen bg-white text-neutral-900"
      style={{ fontFamily: "'Inter', system-ui, sans-serif" }}
    >
      {/* ======================================================================
          NAV
      ====================================================================== */}
      <TopNav />

      {/* ======================================================================
          HERO — asymmetric, mixed typography, no gradient
      ====================================================================== */}
      <section className="border-b border-neutral-200">
        <div className="max-w-7xl mx-auto px-6 pt-20 pb-24 grid grid-cols-12 gap-8 items-end">
          <div className="col-span-12 lg:col-span-8">
            <div className="inline-flex items-center gap-2 h-7 px-3 rounded-full border border-neutral-300 text-[11px] uppercase tracking-[0.14em] text-neutral-600 mb-10">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
              Ouverture 2026 · Silver Economy e-commerce
            </div>
            <h1
              className="text-[48px] sm:text-[72px] lg:text-[96px] leading-[0.95] tracking-[-0.035em] font-medium"
              style={{ fontFamily: "'Fraunces', serif" }}
            >
              Construisons
              <br />
              votre marque.
              <br />
              <span className="italic text-neutral-500">Sans trésorerie.</span>
            </h1>
            <p className="text-lg text-neutral-600 max-w-xl mt-8 leading-relaxed">
              Altiaro accompagne les entrepreneurs qui lancent des marques e-commerce
              premium — analyse de niches multi-marchés, site généré par IA,
              pilotage complet, et <strong className="text-neutral-900">50% de la marge brute</strong> directement
              pour vous. <span className="text-neutral-900 underline decoration-neutral-300 underline-offset-4">Zéro frais fixes.</span>
            </p>
            <div className="flex flex-wrap items-center gap-3 mt-10">
              <Link
                to="/signup"
                data-testid="landing-hero-cta"
                className="h-12 px-6 rounded-full bg-neutral-900 text-white font-medium hover:bg-neutral-800 inline-flex items-center gap-2 text-sm tracking-tight"
              >
                Devenir Concepteur
                <ArrowUpRight size={14} weight="bold" />
              </Link>
              <a
                href="#methode"
                className="h-12 px-6 rounded-full border border-neutral-900 text-neutral-900 font-medium hover:bg-neutral-100 inline-flex items-center text-sm tracking-tight"
              >
                Notre méthode
              </a>
            </div>
          </div>

          {/* Right col — living KPIs card */}
          <div className="col-span-12 lg:col-span-4 lg:pl-12">
            <div className="border-l border-neutral-200 pl-8 space-y-8">
              {[
                { n: "6", l: "Marchés européens scannés en parallèle", f: "FR · DE · BE+LU · NL · CH · UK" },
                { n: "< 2min", l: "Analyse Go / No-Go d'une niche", f: "Scan multi-intention, volume Google, concurrence" },
                { n: "50/50", l: "Marge brute partagée", f: "Virements les 1er et 15 de chaque mois" },
                { n: "0€", l: "Frais fixes mensuels", f: "Commission uniquement sur la marge" },
              ].map((k, i) => (
                <div
                  key={k.l}
                  className="group"
                  style={{ animationDelay: `${i * 80}ms` }}
                >
                  <div
                    className="text-5xl tabular-nums tracking-tight font-medium"
                    style={{ fontFamily: "'Fraunces', serif" }}
                  >
                    {k.n}
                  </div>
                  <div className="text-sm text-neutral-900 mt-1.5 font-medium">{k.l}</div>
                  <div className="text-xs text-neutral-500 mt-1">{k.f}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ======================================================================
          POUR QUI — 3 personas with asymmetric sizes
      ====================================================================== */}
      <section className="border-b border-neutral-200 bg-neutral-50">
        <div className="max-w-7xl mx-auto px-6 py-24">
          <div className="grid grid-cols-12 gap-8 mb-16">
            <div className="col-span-12 lg:col-span-5">
              <div className="text-[11px] uppercase tracking-[0.14em] text-neutral-500 mb-4">
                Pour qui
              </div>
              <h2
                className="text-4xl sm:text-5xl tracking-tight leading-[1.05] font-medium"
                style={{ fontFamily: "'Fraunces', serif" }}
              >
                Conçu pour ceux qui veulent créer sans porter le risque.
              </h2>
            </div>
            <div className="col-span-12 lg:col-span-6 lg:col-start-7 flex items-end">
              <p className="text-neutral-600 leading-relaxed">
                Altiaro n'est pas pour tout le monde. Nous recrutons des
                partenaires qui ont le temps et le goût du commerce, pas
                nécessairement les 50 000 € qu'il faut pour lancer une marque
                seul.
              </p>
            </div>
          </div>

          <div className="grid grid-cols-12 gap-6">
            {[
              {
                n: "01",
                t: "Ex-dirigeants en transition",
                d: "Vous avez dirigé une PME, vous connaissez la vente et la relation client, vous voulez relancer une activité sans reprendre tout le capital à zéro.",
              },
              {
                n: "02",
                t: "Entrepreneurs sérieux",
                d: "Vous avez du temps, un IBAN, et l'envie de piloter une marque complète. Vous voulez tester 2-3 niches avant de vous engager sur une seule.",
              },
              {
                n: "03",
                t: "Indépendants du conseil",
                d: "Vous êtes déjà consultant / formateur / coach. Vous voulez diversifier en possédant une marque à votre nom, sans quitter votre activité actuelle.",
              },
            ].map((p) => (
              <div
                key={p.n}
                className="col-span-12 md:col-span-4 bg-white border border-neutral-200 rounded-lg p-8 hover:border-neutral-900 transition"
              >
                <div
                  className="text-4xl tabular-nums text-neutral-300 mb-6 font-medium"
                  style={{ fontFamily: "'Fraunces', serif" }}
                >
                  {p.n}
                </div>
                <div className="text-lg font-medium mb-3 tracking-tight">
                  {p.t}
                </div>
                <div className="text-sm text-neutral-600 leading-relaxed">{p.d}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ======================================================================
          LA MÉTHODE — 4 steps, timeline left-aligned
      ====================================================================== */}
      <section id="methode" className="border-b border-neutral-200">
        <div className="max-w-7xl mx-auto px-6 py-24">
          <div className="grid grid-cols-12 gap-8 mb-16">
            <div className="col-span-12 lg:col-span-6">
              <div className="text-[11px] uppercase tracking-[0.14em] text-neutral-500 mb-4">
                La méthode Altiaro
              </div>
              <h2
                className="text-4xl sm:text-5xl tracking-tight leading-[1.05] font-medium"
                style={{ fontFamily: "'Fraunces', serif" }}
              >
                De l'idée à la première commande. En 4 étapes guidées.
              </h2>
            </div>
          </div>

          <div className="grid grid-cols-12 gap-6">
            {[
              {
                n: "01",
                icon: ChartLineUp,
                t: "Analyser",
                d: "Scan Go/No-Go en 6 marchés (FR, DE, BE+LU, NL, CH, UK). Volumes Google, niveau de concurrence, potentiel de marge — tout en moins de 2 minutes.",
                time: "2 min",
              },
              {
                n: "02",
                icon: Sparkle,
                t: "Construire",
                d: "Site e-commerce complet généré par IA en 7 sections : identité, positionnement, hero, bénéfices, témoignages, FAQ. Palette et copy sur mesure.",
                time: "15 min",
              },
              {
                n: "03",
                icon: Globe,
                t: "Lancer",
                d: "Domaine custom via OVH intégré (14,99€), catalogue multi-langue, paiements Mollie, expéditions automatisées. Vous pilotez depuis le cockpit.",
                time: "1 jour",
              },
              {
                n: "04",
                icon: Gauge,
                t: "Récolter",
                d: "Virements SEPA automatiques les 1er et 15 du mois. 50% de la marge brute HT directement sur votre IBAN, sans avance de trésorerie.",
                time: "1er / 15",
              },
            ].map((step) => (
              <div
                key={step.n}
                className="col-span-12 md:col-span-6 lg:col-span-3 bg-white border border-neutral-200 rounded-lg p-7"
              >
                <div className="flex items-center justify-between mb-8">
                  <div
                    className="text-sm tabular-nums text-neutral-500 font-medium"
                    style={{ fontFamily: "'Fraunces', serif" }}
                  >
                    {step.n}
                  </div>
                  <step.icon size={20} weight="duotone" className="text-neutral-900" />
                </div>
                <div className="text-xl font-medium mb-3 tracking-tight">
                  {step.t}
                </div>
                <div className="text-sm text-neutral-600 leading-relaxed mb-6">
                  {step.d}
                </div>
                <div className="pt-5 border-t border-neutral-100 flex items-center justify-between text-[11px] uppercase tracking-widest text-neutral-500">
                  <span>Durée typique</span>
                  <span className="text-neutral-900 font-medium tabular-nums">{step.time}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ======================================================================
          PARTENARIAT 50/50 — visual calculator
      ====================================================================== */}
      <section id="partenariat" className="border-b border-neutral-200 bg-neutral-900 text-white">
        <div className="max-w-7xl mx-auto px-6 py-24 grid grid-cols-12 gap-8 items-start">
          <div className="col-span-12 lg:col-span-5">
            <div className="text-[11px] uppercase tracking-[0.14em] text-neutral-400 mb-4">
              Le partenariat
            </div>
            <h2
              className="text-4xl sm:text-5xl tracking-tight leading-[1.05] font-medium mb-8"
              style={{ fontFamily: "'Fraunces', serif" }}
            >
              Aligné avec vos intérêts. <span className="italic text-neutral-400">Par construction.</span>
            </h2>
            <p className="text-neutral-300 leading-relaxed mb-6 text-base">
              Nous ne facturons aucun abonnement, aucun coût de setup, aucune
              commission fixe. Vous ne payez que si vous vendez.
            </p>
            <p className="text-neutral-300 leading-relaxed text-base">
              Sur chaque commande, la marge brute hors taxes (prix de vente HT −
              coût d'achat HT − frais Mollie) est partagée équitablement. 50%
              pour vous. 50% pour Altiaro.
            </p>

            <div className="mt-10 pt-8 border-t border-white/10 flex flex-wrap gap-x-8 gap-y-4 text-sm">
              {[
                "Aucun abonnement mensuel",
                "Aucun setup fee",
                "Aucun minimum de volume",
                "Résiliation en 30 jours",
              ].map((x) => (
                <div key={x} className="flex items-center gap-2 text-neutral-200">
                  <Check size={14} weight="bold" className="text-emerald-400" />
                  {x}
                </div>
              ))}
            </div>
          </div>

          <div className="col-span-12 lg:col-span-6 lg:col-start-7">
            <div className="bg-white/5 border border-white/10 rounded-lg p-8 backdrop-blur">
              <div className="text-[11px] uppercase tracking-[0.14em] text-neutral-400 mb-6">
                Commande type · 1 199 € TTC
              </div>
              <div className="space-y-3 text-sm">
                {[
                  ["Prix de vente TTC", "1 199,00 €", "text-neutral-300"],
                  ["− TVA 20%", "− 199,83 €", "text-neutral-500"],
                  ["Prix de vente HT", "999,17 €", "text-neutral-200"],
                  ["− Coût d'achat HT", "− 420,00 €", "text-neutral-500"],
                  ["− Frais Mollie (1.8% + 0.25€)", "− 21,83 €", "text-neutral-500"],
                  ["Marge brute HT", "557,34 €", "text-white font-semibold pt-3 mt-2 border-t border-white/10 text-base"],
                ].map(([l, v, cls]) => (
                  <div key={l} className={`flex justify-between ${cls}`}>
                    <span>{l}</span>
                    <span className="tabular-nums">{v}</span>
                  </div>
                ))}
              </div>
              <div className="mt-6 pt-6 border-t border-white/20 flex justify-between items-baseline">
                <div>
                  <div className="text-[11px] uppercase tracking-[0.14em] text-emerald-400 mb-1">
                    Votre part — 50%
                  </div>
                  <div
                    className="text-5xl tabular-nums font-medium text-white"
                    style={{ fontFamily: "'Fraunces', serif" }}
                  >
                    278,67 €
                  </div>
                </div>
                <div className="text-right text-xs text-neutral-400">
                  Versé aux
                  <br />
                  <span className="font-medium text-white">1er et 15</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ======================================================================
          DIFFERENCIATION TABLE — vs Shopify / vs Agence
      ====================================================================== */}
      <section className="border-b border-neutral-200">
        <div className="max-w-7xl mx-auto px-6 py-24">
          <div className="grid grid-cols-12 gap-8 mb-16">
            <div className="col-span-12 lg:col-span-6">
              <div className="text-[11px] uppercase tracking-[0.14em] text-neutral-500 mb-4">
                Pourquoi pas ailleurs
              </div>
              <h2
                className="text-4xl sm:text-5xl tracking-tight leading-[1.05] font-medium"
                style={{ fontFamily: "'Fraunces', serif" }}
              >
                Shopify, Prestashop, agences, freelances. <span className="italic text-neutral-500">Et Altiaro.</span>
              </h2>
            </div>
            <div className="col-span-12 lg:col-span-6 flex items-end">
              <p className="text-neutral-600 leading-relaxed">
                On vous laisse juger par vous-même.
              </p>
            </div>
          </div>

          <div className="overflow-x-auto -mx-6 px-6">
            <table className="w-full border-collapse min-w-[720px]">
              <thead>
                <tr className="border-b-2 border-neutral-900">
                  <th className="py-4 text-left text-[11px] uppercase tracking-[0.14em] text-neutral-500 font-medium">
                    Critère
                  </th>
                  <th className="py-4 text-left text-[11px] uppercase tracking-[0.14em] text-neutral-500 font-medium">
                    Shopify / Prestashop
                  </th>
                  <th className="py-4 text-left text-[11px] uppercase tracking-[0.14em] text-neutral-500 font-medium">
                    Agence / freelance
                  </th>
                  <th className="py-4 text-left text-[11px] uppercase tracking-[0.14em] text-white font-medium bg-neutral-900 px-4">
                    Altiaro
                  </th>
                </tr>
              </thead>
              <tbody className="text-sm">
                {[
                  ["Coût initial", "39 €/mois", "5 000 – 20 000 €", "0 €"],
                  ["Time to market", "2 – 6 semaines (avec freelance)", "2 – 4 mois", "1 jour"],
                  ["Analyse de niche", "Non inclus (outils tiers)", "Rapport en 2 semaines, 2 000 €+", "Inclus, < 2 min"],
                  ["Génération site IA", "Non — thèmes à acheter", "Non — design manuel", "7 sections générées"],
                  ["Pages légales FR/RGPD", "À faire soi-même", "Pack à part, 500 € +", "Générées automatiquement"],
                  ["Multi-pays / hreflang", "Apps payantes", "Manuel", "Natif, 6 pays"],
                  ["Votre part sur la marge", "100% (vous portez le risque)", "100% (vous portez le risque)", "50%"],
                  ["Risque financier", "Élevé (cash flow, stocks, ads)", "Élevé (investissement amont)", "Nul"],
                ].map(([col, v1, v2, v3], i) => (
                  <tr key={col} className={i % 2 === 0 ? "bg-neutral-50" : "bg-white"}>
                    <td className="py-4 pr-6 font-medium text-neutral-900">{col}</td>
                    <td className="py-4 pr-6 text-neutral-600">{v1}</td>
                    <td className="py-4 pr-6 text-neutral-600">{v2}</td>
                    <td className="py-4 pr-6 bg-neutral-100 text-neutral-900 font-medium border-l-2 border-neutral-900 pl-4">{v3}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* ======================================================================
          TRUST — partner logos / infra
      ====================================================================== */}
      <section className="border-b border-neutral-200 bg-neutral-50">
        <div className="max-w-7xl mx-auto px-6 py-24">
          <div className="grid grid-cols-12 gap-8 mb-12">
            <div className="col-span-12 lg:col-span-6">
              <div className="text-[11px] uppercase tracking-[0.14em] text-neutral-500 mb-4">
                L'infrastructure
              </div>
              <h2
                className="text-4xl sm:text-5xl tracking-tight leading-[1.05] font-medium"
                style={{ fontFamily: "'Fraunces', serif" }}
              >
                Bâti sur les standards de l'e-commerce européen.
              </h2>
            </div>
          </div>

          <div className="grid grid-cols-12 gap-6">
            {[
              {
                icon: ShieldCheck,
                t: "Paiements Mollie",
                d: "PCI-DSS Level 1. Cartes, SEPA, iDEAL, Bancontact, Apple Pay. Remboursements en 1 clic depuis le cockpit.",
              },
              {
                icon: Globe,
                t: "Domaines OVH intégrés",
                d: "Achat + DNS + SSL automatisés (14,99 € TTC / an). Le leader européen de l'hébergement, datacenters Roubaix.",
              },
              {
                icon: Lightning,
                t: "SEO multi-pays",
                d: "Rendu côté serveur, hreflang, sitemap XML, schema.org, Open Graph, feed RSS Shopping. Note 95+ Lighthouse.",
              },
              {
                icon: Sparkle,
                t: "IA Claude Sonnet 4.5",
                d: "Génération copy, palette, structure, mentions légales. Traduction pro en 4 langues (FR, DE, NL, IT).",
              },
              {
                icon: ChartLineUp,
                t: "Google Ads + Keyword Planner",
                d: "Données de volumes et CPC directement depuis l'API Google, par pays. Shopping Ads via Merchant Center.",
              },
              {
                icon: ShieldCheck,
                t: "RGPD by design",
                d: "Hébergement Europe, chiffrement en transit et au repos, bannière cookies conforme, droits RGPD sous 30 jours.",
              },
            ].map((f) => (
              <div
                key={f.t}
                className="col-span-12 md:col-span-6 lg:col-span-4 bg-white border border-neutral-200 rounded-lg p-7"
              >
                <f.icon size={22} weight="duotone" className="text-neutral-900 mb-6" />
                <div className="text-lg font-medium mb-2 tracking-tight">{f.t}</div>
                <div className="text-sm text-neutral-600 leading-relaxed">{f.d}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ======================================================================
          FAQ
      ====================================================================== */}
      <FaqSection />

      {/* ======================================================================
          FINAL CTA
      ====================================================================== */}
      <section id="devenir-concepteur" className="border-b border-neutral-200">
        <div className="max-w-7xl mx-auto px-6 py-32 text-center">
          <div className="text-[11px] uppercase tracking-[0.14em] text-neutral-500 mb-6">
            Inscription en 30 secondes
          </div>
          <h2
            className="text-5xl sm:text-7xl tracking-[-0.03em] leading-[0.95] font-medium max-w-4xl mx-auto mb-10"
            style={{ fontFamily: "'Fraunces', serif" }}
          >
            Prêt à lancer votre première marque ?
          </h2>
          <p className="text-neutral-600 mb-12 max-w-xl mx-auto leading-relaxed">
            Créez votre compte Concepteur maintenant. Vérification par code email,
            accès immédiat au scan de niches et au générateur de sites.
          </p>
          <div className="flex flex-wrap justify-center gap-3">
            <Link
              to="/signup"
              data-testid="landing-contact-cta"
              className="h-12 px-7 rounded-full bg-neutral-900 text-white font-medium hover:bg-neutral-800 inline-flex items-center gap-2 text-sm tracking-tight"
            >
              Créer mon compte Concepteur
              <ArrowUpRight size={14} weight="bold" />
            </Link>
            <Link
              to="/login"
              className="h-12 px-7 rounded-full border border-neutral-900 text-neutral-900 font-medium hover:bg-neutral-100 inline-flex items-center text-sm tracking-tight"
            >
              Je suis déjà Concepteur
            </Link>
          </div>
        </div>
      </section>

      {/* ======================================================================
          FOOTER
      ====================================================================== */}
      <Footer />

      {/* ======================================================================
          RGPD — Bannière cookies plateforme (Bloc 3)
          Mounted sans `siteId` => le composant fallback sur /cookies platform.
          Le tracking analytics éventuel reste blocké tant que pas de consentement.
      ====================================================================== */}
      <CookieConsentBanner />
    </div>
  );
}

/* ========================================================================== */

function TopNav() {
  return (
    <nav className="border-b border-neutral-200 bg-white/90 backdrop-blur sticky top-0 z-30">
      <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
        <Link to="/" className="flex items-center" data-testid="landing-home-link">
          <AltiaroLogo variant="horizontal" size={22} color="#0A0A0A" />
        </Link>
        <div className="flex items-center gap-7">
          <a
            href="#methode"
            className="text-sm text-neutral-600 hover:text-neutral-900 hidden md:inline tracking-tight"
          >
            Méthode
          </a>
          <a
            href="#partenariat"
            className="text-sm text-neutral-600 hover:text-neutral-900 hidden md:inline tracking-tight"
          >
            Partenariat
          </a>
          <a
            href="#faq"
            className="text-sm text-neutral-600 hover:text-neutral-900 hidden md:inline tracking-tight"
          >
            FAQ
          </a>
          <Link
            to="/login"
            data-testid="landing-cta-login"
            className="h-9 px-4 rounded-full bg-neutral-900 text-white text-sm font-medium hover:bg-neutral-800 inline-flex items-center gap-1.5 tracking-tight"
          >
            Cockpit
            <ArrowRight size={12} weight="bold" />
          </Link>
        </div>
      </div>
    </nav>
  );
}

function FaqSection() {
  const faqs = [
    {
      q: "Combien me coûte Altiaro au démarrage ?",
      a: "Rien. Il n'y a ni abonnement mensuel, ni frais de setup, ni minimum de volume. Nous nous rémunérons uniquement sur les commandes, via le partage 50/50 de la marge brute. Les seuls débours optionnels : le domaine custom via OVH (14,99 € TTC / an) si vous en voulez un, et les publicités Google Ads que vous décidez éventuellement de lancer.",
    },
    {
      q: "Qui est propriétaire de la marque et du site ?",
      a: "Vous. Nous vous fournissons l'infrastructure technique, mais la marque, les visuels, le catalogue et la base clients vous appartiennent. Si vous résiliez, vous récupérez l'export complet de vos données en moins de 15 jours.",
    },
    {
      q: "Qui gère la TVA, les factures, la comptabilité ?",
      a: "Altiaro émet automatiquement les factures à vos clients finaux au format exigé par l'administration française. Vous recevez une synthèse mensuelle de votre chiffre d'affaires HT et de vos parts de marge, prêtes à transmettre à votre comptable. La TVA est collectée et reversée à l'État par Altiaro côté plateforme.",
    },
    {
      q: "Que se passe-t-il si une commande est remboursée ou litigée ?",
      a: "Les remboursements sont traités en 1 clic depuis le cockpit via Mollie. La marge brute ré-actualisée est ensuite débitée du solde à virer. Les litiges (chargebacks) sont pris en charge à 50/50 — c'est aligné avec notre partage.",
    },
    {
      q: "Dans combien de temps je peux lancer ?",
      a: "De l'inscription à la mise en ligne : 24 à 48 heures pour un profil sérieux. Le Quick Scan d'une niche prend < 2 min, la génération du site ~15 min, et la configuration du domaine + DNS + SSL ~24h (délai OVH). Vous pouvez commencer à vendre dès que le domaine est propagé.",
    },
    {
      q: "Est-ce que je peux tester plusieurs niches ?",
      a: "Oui. Vous pouvez ouvrir jusqu'à 3 sites en parallèle sur votre compte Concepteur. Nous recommandons d'en valider un avant de démultiplier pour ne pas disperser votre attention. Les sites sans chiffre d'affaires pendant 90 jours sont archivés automatiquement.",
    },
    {
      q: "Que faites-vous concrètement, vous, Altiaro ?",
      a: "Nous opérons toute la couche technique, juridique et intelligence : l'infrastructure (serveurs, domaines, SSL, paiements), l'IA qui génère votre site et votre copy, les pages légales conformes LCEN/RGPD, le SEO multi-pays, l'intégration Google Merchant Center pour le Shopping gratuit, les scans de niche, et le support de niveau 1. Vous pilotez le produit et la relation client.",
    },
    {
      q: "Comment je crée mon compte ?",
      a: "Cliquez sur \"Devenir Concepteur\" en haut de cette page. Inscription en 30 secondes : nom, email professionnel, mot de passe. Vous recevez un code à 6 chiffres par email pour activer votre compte, et vous êtes immédiatement dans le cockpit pour scanner votre première niche.",
    },
  ];
  const [openIdx, setOpenIdx] = useState(0);
  return (
    <section id="faq" className="border-b border-neutral-200">
      <div className="max-w-4xl mx-auto px-6 py-24">
        <div className="text-[11px] uppercase tracking-[0.14em] text-neutral-500 mb-4 text-center">
          Questions fréquentes
        </div>
        <h2
          className="text-4xl sm:text-5xl tracking-tight leading-[1.05] font-medium text-center mb-16"
          style={{ fontFamily: "'Fraunces', serif" }}
        >
          Les 8 questions qu'on nous pose en premier.
        </h2>
        <div className="space-y-0 border-t border-neutral-200">
          {faqs.map((f, i) => {
            const isOpen = openIdx === i;
            return (
              <div key={i} className="border-b border-neutral-200">
                <button
                  onClick={() => setOpenIdx(isOpen ? -1 : i)}
                  className="w-full py-6 flex items-start justify-between gap-6 text-left group"
                  data-testid={`faq-q-${i}`}
                >
                  <span className="text-lg font-medium text-neutral-900 tracking-tight group-hover:text-neutral-700 transition">
                    {f.q}
                  </span>
                  <span className="mt-1 flex-shrink-0 w-6 h-6 rounded-full border border-neutral-300 flex items-center justify-center text-neutral-600">
                    {isOpen ? <Minus size={10} weight="bold" /> : <Plus size={10} weight="bold" />}
                  </span>
                </button>
                {isOpen && (
                  <div className="pb-6 -mt-2 pr-12 text-neutral-600 leading-relaxed text-[15px]">
                    {f.a}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}

function Footer() {
  return (
    <footer className="bg-neutral-50">
      <div className="max-w-7xl mx-auto px-6 py-16 grid grid-cols-2 md:grid-cols-4 gap-10 text-sm">
        <div className="col-span-2">
          <AltiaroLogo variant="horizontal" size={22} color="#0A0A0A" />
          <p className="text-neutral-500 mt-5 max-w-sm leading-relaxed">
            La plateforme e-commerce des partenariats éclairés. Éditée par la
            Société Altiaro · SIRET 883 803 967 00016 · 4 IMP CLOS FLEURI,
            42320 FARNAY.
          </p>
        </div>
        <div>
          <div className="text-[11px] uppercase tracking-[0.14em] text-neutral-500 mb-4">
            Plateforme
          </div>
          <div className="space-y-2.5 text-neutral-700">
            <a href="#methode" className="block hover:text-neutral-900">Méthode</a>
            <a href="#partenariat" className="block hover:text-neutral-900">Partenariat 50/50</a>
            <a href="#faq" className="block hover:text-neutral-900">FAQ</a>
            <Link to="/login" className="block hover:text-neutral-900">Cockpit Concepteur</Link>
            <a href="mailto:contact@altiaro.com" className="block hover:text-neutral-900">contact@altiaro.com</a>
          </div>
        </div>
        <div>
          <div className="text-[11px] uppercase tracking-[0.14em] text-neutral-500 mb-4">
            Légal
          </div>
          <div className="space-y-2.5 text-neutral-700">
            <Link to="/mentions-legales" className="block hover:text-neutral-900" data-testid="footer-mentions">
              Mentions légales
            </Link>
            <Link to="/cgu" className="block hover:text-neutral-900" data-testid="footer-cgu">CGU</Link>
            <Link to="/confidentialite" className="block hover:text-neutral-900" data-testid="footer-confidentialite">
              Confidentialité
            </Link>
            <Link to="/cookies" className="block hover:text-neutral-900" data-testid="footer-cookies">Cookies</Link>
          </div>
        </div>
      </div>
      <div className="border-t border-neutral-200">
        <div className="max-w-7xl mx-auto px-6 py-6 flex flex-wrap gap-y-2 gap-x-6 text-xs text-neutral-500 justify-between">
          <div>© {new Date().getFullYear()} Altiaro — SIREN 883 803 967 · TVA FR42883803967</div>
          <div>Fait avec soin depuis Farnay · France</div>
        </div>
      </div>
    </footer>
  );
}
