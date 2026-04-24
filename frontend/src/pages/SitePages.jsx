import React, { useEffect, useMemo, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { ArrowLeft, ArrowRight, CheckCircle, Sparkle, ArrowClockwise, FileText, BookOpen, Phone, Scales, Truck, ArrowUUpLeft, Question } from "@phosphor-icons/react";
import { api, apiCall } from "../lib/api";
import {
  AboutEditor,
  FAQEditor,
  ContactEditor,
  LegalEditor,
} from "../components/BrandingContent";

/**
 * Étape 6 — Pages essentielles.
 * Rédige / édite les pages statiques non-produits (À propos, FAQ, Contact,
 * CGV, Mentions, Confidentialité, Cookies, Médiation, Livraison, Retours).
 * PAS de branding / design (= Étape 5).
 */
export default function SitePages() {
  const { id: siteId } = useParams();
  const [site, setSite] = useState(null);
  const [design, setDesign] = useState(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [genToast, setGenToast] = useState("");

  const reload = async () => {
    const [{ data: s }, { data: d }] = await Promise.all([
      apiCall(() => api.get(`/sites/${siteId}`)),
      apiCall(() => api.get(`/sites/${siteId}/design`)),
    ]);
    if (s) setSite(s);
    if (d) setDesign(d);
    setLoading(false);
  };

  // `reload` est stable dans la portée de ce composant et dépend uniquement de siteId.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { reload(); }, [siteId]);

  const generateAll = async () => {
    setGenerating(true);
    setGenToast("");
    const { data, error, rawDetail } = await apiCall(() =>
      api.post(`/sites/${siteId}/design/generate-pages`, {})
    );
    setGenerating(false);
    if (error) {
      setGenToast(rawDetail?.detail || error);
      return;
    }
    setGenToast(`✅ ${data?.generated_count || 0} pages rédigées`);
    await reload();
    setTimeout(() => setGenToast(""), 4000);
  };

  // Progress : which pages are already filled?
  const progress = useMemo(() => {
    const d = design || {};
    const pages = [
      { key: "about", label: "À propos", filled: !!((d.about?.headline || d.about?.paragraphs?.length) || (d.pages?.about?.body)) },
      { key: "faq", label: "FAQ", filled: Array.isArray(d.faq) && d.faq.length >= 3 },
      { key: "contact", label: "Contact", filled: !!((d.contact?.email || d.contact?.phone) || d.pages?.contact?.body) },
      { key: "livraison", label: "Livraison", filled: !!(d.pages?.livraison?.body || d.shipping_page?.body) },
      { key: "retours", label: "Retours", filled: !!(d.pages?.retours?.body || d.returns_page?.body) },
      { key: "cgv", label: "CGV", filled: !!d.legal?.cgv },
      { key: "mentions", label: "Mentions légales", filled: !!d.legal?.mentions_legales },
      { key: "confidentialite", label: "Confidentialité", filled: !!d.legal?.confidentialite },
      { key: "cookies", label: "Cookies", filled: !!d.legal?.cookies },
      { key: "mediation", label: "Médiation", filled: !!d.legal?.mediation },
    ];
    const done = pages.filter((p) => p.filled).length;
    return { pages, done, total: pages.length, pct: Math.round((done / pages.length) * 100) };
  }, [design]);

  if (loading) {
    return (
      <div className="min-h-screen bg-[#FAFAFA] flex items-center justify-center">
        <div className="text-sm text-neutral-500">Chargement…</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#FAFAFA]">
      <div className="max-w-[1100px] mx-auto px-6 md:px-10 py-8">
        <Link
          to={`/sites/${siteId}`}
          className="inline-flex items-center gap-2 text-sm text-neutral-600 hover:text-neutral-900 mb-6"
          data-testid="back-to-cockpit"
        >
          <ArrowLeft size={14} /> Retour au cockpit
        </Link>

        {/* Banner */}
        <div
          data-testid="step6-header"
          className="mb-6 bg-white p-6 md:p-7"
          style={{ border: "1px solid #E5E5E5", borderRadius: "4px" }}
        >
          <div className="flex items-start justify-between gap-6 flex-wrap">
            <div className="flex-1 min-w-0">
              <div className="text-[10px] uppercase tracking-[0.3em] text-neutral-500 mb-2 font-medium">
                Étape 6 — Pages essentielles
              </div>
              <div
                className="text-[26px] md:text-[32px] text-neutral-900 leading-tight"
                style={{ fontFamily: "'Fraunces', Georgia, serif" }}
              >
                Rédigez vos pages (hors produits)
              </div>
              <p className="text-[13px] text-neutral-600 mt-2 leading-[1.55] max-w-2xl">
                Toutes les pages non-produits nécessaires pour la conformité et
                la confiance client : À propos, FAQ, Contact, Livraison, Retours,
                et 5 pages légales. L'IA peut rédiger l'intégralité en 60-120 s.
              </p>
            </div>
          </div>

          {/* Progress bar */}
          <div className="mt-6" data-testid="pages-progress">
            <div className="flex items-center justify-between mb-2 text-[11px] uppercase tracking-[0.25em] text-neutral-500 font-medium">
              <span>Complétion des pages</span>
              <span className="tabular-nums text-neutral-900">{progress.done} / {progress.total}</span>
            </div>
            <div className="h-1.5 w-full overflow-hidden" style={{ background: "#F0F0F0", borderRadius: "999px" }}>
              <div
                className="h-full bg-neutral-900 transition-all"
                style={{ width: `${progress.pct}%`, borderRadius: "999px" }}
              />
            </div>
            <div className="mt-3 flex flex-wrap gap-1.5">
              {progress.pages.map((p) => (
                <span
                  key={p.key}
                  className={`inline-flex items-center gap-1 px-2 py-0.5 text-[10.5px] font-medium ${
                    p.filled ? "bg-emerald-50 text-emerald-700" : "bg-neutral-100 text-neutral-500"
                  }`}
                  style={{ borderRadius: "2px" }}
                  data-testid={`page-chip-${p.key}`}
                >
                  {p.filled ? <CheckCircle size={9} weight="fill" /> : <span className="w-1.5 h-1.5 rounded-full bg-neutral-300" />}
                  {p.label}
                </span>
              ))}
            </div>
          </div>

          {/* CTA */}
          <div className="mt-6 flex items-center gap-3 flex-wrap">
            <button
              onClick={generateAll}
              disabled={generating}
              data-testid="generate-all-pages"
              className="h-11 px-5 bg-neutral-900 hover:bg-black disabled:opacity-60 text-white text-[13px] font-semibold flex items-center gap-2"
              style={{ borderRadius: "2px" }}
            >
              {generating ? <ArrowClockwise size={14} className="animate-spin" /> : <Sparkle size={14} weight="fill" />}
              {generating ? "Rédaction IA en cours…" : progress.done === 0 ? "✨ Rédiger toutes les pages (IA)" : "Régénérer les pages manquantes (IA)"}
            </button>
            <Link
              to={`/sites/${siteId}/blog-posts?step=7`}
              data-testid="goto-step7"
              className="h-11 px-5 bg-white border text-[13px] font-medium text-neutral-900 flex items-center gap-2 hover:border-neutral-900 transition"
              style={{ borderColor: "#E5E5E5", borderRadius: "2px" }}
            >
              Étape suivante · Blog SEO <ArrowRight size={12} />
            </Link>
            {genToast && (
              <span className="text-[12px] text-emerald-700 font-medium" data-testid="gen-toast">{genToast}</span>
            )}
          </div>
        </div>

        {/* Editors */}
        <div className="space-y-10">
          <section data-testid="section-about">
            <SectionHeader Icon={UserIcon} title="À propos" subtitle="L'histoire de la marque, les valeurs, le fondateur." />
            <AboutEditor siteId={siteId} design={design} onReload={reload} onSaved={reload} />
          </section>

          <section data-testid="section-faq">
            <SectionHeader Icon={Question} title="FAQ" subtitle="Les 5-10 questions les plus fréquentes." />
            <FAQEditor siteId={siteId} design={design} onReload={reload} onSaved={reload} />
          </section>

          <section data-testid="section-contact">
            <SectionHeader Icon={Phone} title="Contact" subtitle="Email SAV, téléphone, horaires, adresse." />
            <ContactEditor siteId={siteId} design={design} onReload={reload} onSaved={reload} />
          </section>

          <section data-testid="section-legal">
            <SectionHeader Icon={Scales} title="Pages légales" subtitle="CGV, mentions, confidentialité, cookies, médiation." />
            <LegalEditor siteId={siteId} design={design} onReload={reload} onSaved={reload} />
          </section>

          {/* Livraison / Retours — quick links to policy page if separate */}
          <section data-testid="section-policy-links">
            <SectionHeader Icon={Truck} title="Livraison & Retours" subtitle="Politique de livraison, conditions de retour et remboursement." />
            <div
              className="p-5 bg-white text-[13px] text-neutral-600 leading-[1.6]"
              style={{ border: "1px solid #E5E5E5", borderRadius: "4px" }}
            >
              Les pages Livraison et Retours sont gérées depuis l'espace <Link to={`/sites/${siteId}/policy`} className="text-neutral-900 underline underline-offset-2 hover:opacity-70">politique commerciale</Link> (inclut délais, zones, frais et processus retour). L'IA les rédige également lors du bouton « Rédiger toutes les pages » ci-dessus.
            </div>
          </section>

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
                Prochaine étape : le blog SEO
              </div>
              <p className="text-[12.5px] text-neutral-500 mt-1">
                L'IA optimise votre contenu pour le référencement organique et les moteurs IA (Perplexity, ChatGPT).
              </p>
            </div>
            <Link
              to={`/sites/${siteId}/blog-posts?step=7`}
              data-testid="goto-step7-footer"
              className="h-11 px-5 bg-neutral-900 hover:bg-black text-white text-[13px] font-semibold flex items-center gap-2"
              style={{ borderRadius: "2px" }}
            >
              Étape 7 · Blog & SEO <ArrowRight size={13} weight="bold" />
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}

function UserIcon(props) {
  return <BookOpen {...props} />;
}

function SectionHeader({ Icon, title, subtitle }) {
  return (
    <div className="mb-4 flex items-start gap-4">
      <div
        className="shrink-0 w-9 h-9 flex items-center justify-center text-neutral-900"
        style={{ background: "#F5F5F5", borderRadius: "2px" }}
      >
        <Icon size={16} weight="duotone" />
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
