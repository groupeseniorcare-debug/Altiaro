import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { ArrowLeft, ArrowRight, CheckCircle, Storefront as StoreIcon, Rocket, Palette } from "@phosphor-icons/react";
import { api, apiCall } from "../lib/api";
import IdentityTab from "../components/site-design/IdentityTab";
import LivePreview from "../components/site-design/LivePreview";
import BrandWizard from "../components/BrandWizard";
import LaunchProgress from "../components/LaunchProgress";
import {
  HeroEditor,
  BenefitsEditor,
  TestimonialsEditor,
} from "../components/BrandingContent";
import HomepageSectionsEditor from "../components/HomepageSectionsEditor";

/**
 * Étape 5 — Identité & design.
 * Tout ce qui est VISUEL : marque, logo, palette, typo + homepage (hero,
 * sections, bénéfices, témoignages). PAS de pages légales (= Étape 6).
 */
export default function SiteBranding() {
  const { id: siteId } = useParams();
  const [site, setSite] = useState(null);
  const [design, setDesign] = useState(null);
  const [loading, setLoading] = useState(true);
  const [publishing, setPublishing] = useState(false);
  const [previewKey, setPreviewKey] = useState(Date.now());
  const [previewOpen, setPreviewOpen] = useState(true);
  const [mode, setMode] = useState("auto");
  const [launchJobId, setLaunchJobId] = useState(null);

  const reload = async () => {
    const [{ data: s }, { data: d }] = await Promise.all([
      apiCall(() => api.get(`/sites/${siteId}`)),
      apiCall(() => api.get(`/sites/${siteId}/design`)),
    ]);
    if (s) setSite(s);
    if (d) setDesign(d);
    setPreviewKey(Date.now());
    setLoading(false);
  };

  useEffect(() => { reload(); /* eslint-disable-next-line */ }, [siteId]);

  const togglePublish = async () => {
    setPublishing(true);
    const { error } = await apiCall(() =>
      api.patch(`/sites/${siteId}/design/publish`, { published: !design?.published })
    );
    setPublishing(false);
    if (error) return window.alert(error);
    await reload();
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#FAFAFA] flex items-center justify-center">
        <div className="text-sm text-neutral-500">Chargement…</div>
      </div>
    );
  }

  const hasDesign = !!design && (design.brand?.name || design.template_id);

  // Live-launch wizard (keep existing behaviour)
  if (mode === "wizard") {
    return (
      <BrandWizard
        siteId={siteId}
        onLaunch={(jobId) => { setLaunchJobId(jobId); setMode("auto"); }}
        onCancel={() => setMode("auto")}
      />
    );
  }
  if (launchJobId) {
    return (
      <LaunchProgress
        siteId={siteId}
        jobId={launchJobId}
        onDone={() => { setLaunchJobId(null); reload(); }}
      />
    );
  }

  return (
    <div className="min-h-screen bg-[#FAFAFA]">
      <div className="max-w-[1600px] mx-auto px-6 md:px-10 py-8">
        <Link
          to={`/sites/${siteId}`}
          className="inline-flex items-center gap-2 text-sm text-neutral-600 hover:text-neutral-900 mb-6"
          data-testid="back-to-cockpit"
        >
          <ArrowLeft size={14} /> Retour au cockpit
        </Link>

        {/* Banner */}
        <div
          data-testid="step5-header"
          className="mb-8 bg-white p-6 md:p-7"
          style={{ border: "1px solid #E5E5E5", borderRadius: "4px" }}
        >
          <div className="flex items-start justify-between gap-6 flex-wrap">
            <div className="flex-1 min-w-0">
              <div className="text-[10px] uppercase tracking-[0.3em] text-neutral-500 mb-2 font-medium">
                Étape 5 — Identité & design
              </div>
              <div
                className="text-[26px] md:text-[32px] text-neutral-900 leading-tight"
                style={{ fontFamily: "'Fraunces', Georgia, serif" }}
              >
                {site?.name || "Votre marque"}
              </div>
              <p className="text-[13px] text-neutral-600 mt-2 leading-[1.55] max-w-2xl">
                Nom commercial, baseline, voix éditoriale, logo IA, palette,
                typographie — puis la homepage (hero, sections, bénéfices,
                témoignages). Tout est vivant : chaque modification se reflète
                en temps réel dans l'aperçu à droite.
              </p>
              <div className="mt-4 flex items-center gap-3 flex-wrap">
                {hasDesign ? (
                  <span className="inline-flex items-center gap-1.5 text-[11px] font-medium text-emerald-700 bg-emerald-50 px-2.5 py-1" style={{ borderRadius: "2px" }}>
                    <CheckCircle size={11} weight="fill" /> Identité générée
                  </span>
                ) : (
                  <button
                    onClick={() => setMode("wizard")}
                    data-testid="relaunch-wizard"
                    className="h-10 px-4 bg-neutral-900 hover:bg-black text-white text-[13px] font-semibold flex items-center gap-2"
                    style={{ borderRadius: "2px" }}
                  >
                    <Rocket size={14} weight="fill" /> Générer mon site (IA)
                  </button>
                )}
                <Link
                  to={`/sites/${siteId}/pages?step=6`}
                  data-testid="goto-step6"
                  className="h-10 px-4 bg-white border text-[13px] font-medium text-neutral-900 flex items-center gap-2 hover:border-neutral-900 transition"
                  style={{ borderColor: "#E5E5E5", borderRadius: "2px" }}
                >
                  Étape suivante · Rédiger les pages <ArrowRight size={12} />
                </Link>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {hasDesign && (
                <button
                  onClick={togglePublish}
                  disabled={publishing}
                  data-testid="publish-btn"
                  className={`h-10 px-4 text-[13px] font-semibold flex items-center gap-2 disabled:opacity-60 ${
                    design?.published
                      ? "bg-emerald-600 hover:bg-emerald-700 text-white"
                      : "bg-neutral-900 hover:bg-black text-white"
                  }`}
                  style={{ borderRadius: "2px" }}
                >
                  {design?.published ? <><CheckCircle size={13} weight="fill" /> Publié</> : "Publier"}
                </button>
              )}
              <a
                href={`/shop/${siteId}`}
                target="_blank"
                rel="noreferrer"
                className="h-10 px-4 text-[13px] font-medium flex items-center gap-2 bg-white border text-neutral-900 hover:border-neutral-900"
                style={{ borderColor: "#E5E5E5", borderRadius: "2px" }}
                data-testid="preview-storefront"
              >
                <StoreIcon size={13} /> Voir storefront
              </a>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-[1fr_480px] gap-8">
          <div className="space-y-10">
            {/* Identité */}
            <section data-testid="section-identity">
              <SectionHeader
                number="1"
                title="Identité de marque"
                subtitle="Nom, baseline, voix, logo, couleurs, typographie."
              />
              <IdentityTab siteId={siteId} design={design} onReload={reload} onChange={() => setPreviewKey(Date.now())} />
            </section>

            {/* Homepage sections ordering */}
            <section data-testid="section-homepage">
              <SectionHeader
                number="2"
                title="Sections de la page d'accueil"
                subtitle="Choisissez les blocs et leur ordre sur la home."
              />
              <HomepageSectionsEditor siteId={siteId} onChange={() => setPreviewKey(Date.now())} />
            </section>

            {/* Hero editor */}
            <section data-testid="section-hero">
              <SectionHeader
                number="3"
                title="Hero (premier écran)"
                subtitle="Titre principal, sous-titre, CTA, visuel d'ouverture."
              />
              <HeroEditor siteId={siteId} design={design} onReload={reload} onSaved={() => setPreviewKey(Date.now())} />
            </section>

            {/* Benefits */}
            <section data-testid="section-benefits">
              <SectionHeader
                number="4"
                title="Bénéfices clés"
                subtitle="Les 3-4 promesses fortes affichées sous le hero."
              />
              <BenefitsEditor siteId={siteId} design={design} onReload={reload} onSaved={() => setPreviewKey(Date.now())} />
            </section>

            {/* Testimonials */}
            <section data-testid="section-testimonials">
              <SectionHeader
                number="5"
                title="Témoignages"
                subtitle="Social proof client sur la page d'accueil."
              />
              <TestimonialsEditor siteId={siteId} design={design} onReload={reload} onSaved={() => setPreviewKey(Date.now())} />
            </section>

            {/* Footer CTA */}
            <div
              data-testid="footer-cta"
              className="mt-10 p-6 flex items-center justify-between gap-4 flex-wrap bg-white"
              style={{ border: "1px solid #E5E5E5", borderRadius: "4px" }}
            >
              <div>
                <div
                  className="text-[19px] text-neutral-900"
                  style={{ fontFamily: "'Fraunces', Georgia, serif" }}
                >
                  Prochaine étape : vos pages essentielles
                </div>
                <p className="text-[12.5px] text-neutral-500 mt-1">À propos, FAQ, Contact, CGV, Livraison, Retours — en 1 clic avec l'IA.</p>
              </div>
              <Link
                to={`/sites/${siteId}/pages?step=6`}
                data-testid="goto-step6-footer"
                className="h-11 px-5 bg-neutral-900 hover:bg-black text-white text-[13px] font-semibold flex items-center gap-2"
                style={{ borderRadius: "2px" }}
              >
                Étape 6 · Rédiger les pages <ArrowRight size={13} weight="bold" />
              </Link>
            </div>
          </div>

          {/* Live preview */}
          <aside className="hidden lg:block">
            <div className="sticky top-6">
              <div className="text-[10px] uppercase tracking-[0.3em] text-neutral-500 mb-3 font-medium flex items-center gap-2">
                <Palette size={11} /> Aperçu en direct
              </div>
              <LivePreview siteId={siteId} previewKey={previewKey} />
            </div>
          </aside>
        </div>

        {!previewOpen && (
          <button
            onClick={() => setPreviewOpen(true)}
            className="fixed bottom-6 right-6 z-40 h-12 px-5 rounded-full bg-neutral-900 hover:bg-neutral-800 text-white text-sm font-medium flex items-center gap-2 shadow-xl"
          >
            <StoreIcon size={14} weight="fill" /> Aperçu live
          </button>
        )}
      </div>
    </div>
  );
}

function SectionHeader({ number, title, subtitle }) {
  return (
    <div className="mb-4 flex items-start gap-4">
      <div
        className="shrink-0 w-9 h-9 flex items-center justify-center text-[14px] font-semibold tabular-nums text-neutral-900"
        style={{ background: "#F5F5F5", borderRadius: "2px", fontFamily: "'Fraunces', Georgia, serif" }}
      >
        {number}
      </div>
      <div>
        <div
          className="text-[18px] text-neutral-900 leading-tight"
          style={{ fontFamily: "'Fraunces', Georgia, serif" }}
        >
          {title}
        </div>
        <p className="text-[12px] text-neutral-500 mt-0.5">{subtitle}</p>
      </div>
    </div>
  );
}
