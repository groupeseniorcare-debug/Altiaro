import React from "react";
import { Link, useLocation } from "react-router-dom";
import { ArrowLeft } from "@phosphor-icons/react";
import { ALTIARO_COMPANY, ALTIARO_LEGAL_LAST_UPDATE } from "../lib/altiaroLegal";
import "../styles/legal.css";

const SECTIONS = [
  { slug: "mentions", label: "Mentions légales", path: "/legal/mentions" },
  { slug: "cgv", label: "Conditions générales de vente", path: "/legal/cgv" },
  { slug: "confidentialite", label: "Politique de confidentialité", path: "/legal/confidentialite" },
  { slug: "livraison", label: "Politique de livraison", path: "/legal/livraison" },
  { slug: "retours", label: "Politique de retour", path: "/legal/retours" },
];

/**
 * Layout commun aux 5 pages légales plateforme Altiaro (`/legal/*`).
 * Distinct du layout des storefronts clients (qui vit sous /shop/:siteId/...).
 *
 * Charte premium :
 *  - Fond ivoire #F5F2EB
 *  - H1 Cormorant Garamond fin
 *  - Sidebar gauche listant les 5 sections, surlignant la courante
 *  - Texte juriste-pro lisible (corps Inter / sans-serif système)
 */
export default function PlatformLegalLayout({ title, eyebrow, children }) {
  const { pathname } = useLocation();

  return (
    <div className="min-h-screen" style={{ background: "#F5F2EB" }}>
      {/* Header plateforme — sobre */}
      <header
        className="border-b"
        style={{ borderColor: "#E8E2D5", background: "#FDFCF9" }}
      >
        <div className="max-w-6xl mx-auto px-6 md:px-10 py-5 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-3 group">
            <span
              className="text-[26px] leading-none tracking-[-0.01em] text-neutral-900"
              style={{ fontFamily: "'Cormorant Garamond', 'Cormorant', Georgia, serif", fontWeight: 500 }}
            >
              Altiaro
            </span>
          </Link>
          <Link
            to="/"
            className="hidden md:flex items-center gap-2 text-[12px] uppercase tracking-[0.2em] text-neutral-500 hover:text-neutral-900 transition"
          >
            <ArrowLeft size={13} weight="regular" /> Retour à l'accueil
          </Link>
        </div>
      </header>

      <div className="max-w-6xl mx-auto px-6 md:px-10 py-10 md:py-16">
        <div className="grid grid-cols-1 lg:grid-cols-[260px_1fr] gap-10 lg:gap-14">
          {/* Sidebar */}
          <aside className="lg:sticky lg:top-8 self-start">
            <div
              className="text-[10px] uppercase tracking-[0.3em] mb-4"
              style={{ color: "#8B8174" }}
            >
              Informations légales
            </div>
            <nav className="flex flex-col gap-1">
              {SECTIONS.map((s) => {
                const active = pathname === s.path;
                return (
                  <Link
                    key={s.slug}
                    to={s.path}
                    className={`px-3 py-2.5 text-[14px] leading-snug border-l-2 transition ${
                      active
                        ? "border-neutral-900 text-neutral-900 font-medium bg-white"
                        : "border-transparent text-neutral-600 hover:text-neutral-900 hover:bg-white/60"
                    }`}
                  >
                    {s.label}
                  </Link>
                );
              })}
            </nav>
          </aside>

          {/* Contenu */}
          <main className="min-w-0">
            <article
              className="bg-white p-8 md:p-12"
              style={{ border: "1px solid #E8E2D5", borderRadius: "2px" }}
            >
              {eyebrow && (
                <div
                  className="text-[10px] uppercase tracking-[0.35em] mb-4"
                  style={{ color: "#8B8174" }}
                >
                  {eyebrow}
                </div>
              )}
              <h1
                className="text-[36px] md:text-[44px] leading-[1.1] tracking-[-0.01em] text-neutral-900 mb-8"
                style={{
                  fontFamily: "'Cormorant Garamond', 'Cormorant', Georgia, serif",
                  fontWeight: 400,
                }}
              >
                {title}
              </h1>

              <div className="legal-content text-[15px] leading-[1.75] text-neutral-700">
                {children}
              </div>

              <div
                className="mt-10 pt-6 text-[12px] text-neutral-500"
                style={{ borderTop: "1px solid #E8E2D5" }}
              >
                Dernière mise à jour&nbsp;: {ALTIARO_LEGAL_LAST_UPDATE}.
              </div>
            </article>

            {/* Bloc société en pied — utile pour l'examinateur Google */}
            <div
              className="mt-6 p-6 text-[12.5px] leading-[1.7] text-neutral-600 grid grid-cols-1 md:grid-cols-2 gap-4"
              style={{ background: "#FDFCF9", border: "1px solid #E8E2D5", borderRadius: "2px" }}
            >
              <div>
                <div className="text-[10px] uppercase tracking-[0.3em] text-neutral-500 mb-2">
                  Éditeur
                </div>
                <div className="text-neutral-900 font-medium">{ALTIARO_COMPANY.nom}</div>
                <div>{ALTIARO_COMPANY.forme_juridique}</div>
                <div>SIREN&nbsp;{ALTIARO_COMPANY.siren}</div>
                <div>SIRET&nbsp;{ALTIARO_COMPANY.siret}</div>
                <div>APE&nbsp;{ALTIARO_COMPANY.code_naf}</div>
                <div>{ALTIARO_COMPANY.adresse}</div>
              </div>
              <div>
                <div className="text-[10px] uppercase tracking-[0.3em] text-neutral-500 mb-2">
                  Contact
                </div>
                <div>
                  Email&nbsp;:{" "}
                  <a
                    className="text-neutral-900 underline"
                    href={`mailto:${ALTIARO_COMPANY.email}`}
                  >
                    {ALTIARO_COMPANY.email}
                  </a>
                </div>
                <div>Téléphone&nbsp;: {ALTIARO_COMPANY.telephone}</div>
                <div>Directeur de publication&nbsp;: {ALTIARO_COMPANY.directeur_publication}</div>
                <div className="mt-2">
                  Hébergement&nbsp;: {ALTIARO_COMPANY.hebergeur_nom} —{" "}
                  {ALTIARO_COMPANY.hebergeur_adresse}
                </div>
              </div>
            </div>
          </main>
        </div>
      </div>

      {/* Pied de page sobre */}
      <footer
        className="mt-16 py-8 text-center text-[12px] text-neutral-500"
        style={{ borderTop: "1px solid #E8E2D5", background: "#FDFCF9" }}
      >
        © {new Date().getFullYear()} {ALTIARO_COMPANY.nom}. Tous droits réservés.
      </footer>
    </div>
  );
}
