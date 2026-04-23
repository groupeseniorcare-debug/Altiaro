import React, { useState } from "react";
import {
  ArrowClockwise, Sparkle, CheckCircle, Info, Image as ImageIcon,
  ClipboardText, ChatCenteredText, PaintBrush,
} from "@phosphor-icons/react";
import { api, apiCall } from "../lib/api";

const REGEN_SECTIONS = [
  { key: "hero", label: "Hero page d'accueil", Icon: Sparkle },
  { key: "about", label: "À propos", Icon: ClipboardText },
  { key: "benefits", label: "Bénéfices clés", Icon: CheckCircle },
  { key: "faq", label: "FAQ", Icon: ChatCenteredText },
  { key: "testimonials", label: "Témoignages", Icon: ChatCenteredText },
  { key: "contact", label: "Contact", Icon: ChatCenteredText },
];

/**
 * Branding content tab — hero, about, benefits, FAQ, testimonials, contact, legal.
 * Each section can be individually regenerated with Claude, and a global brief
 * can regenerate everything at once.
 */
export default function BrandingContent({ siteId, design, onReload }) {
  const [regenerating, setRegenerating] = useState(null);
  const [generating, setGenerating] = useState(false);
  const [tweak, setTweak] = useState("");
  const [seedingLegal, setSeedingLegal] = useState(false);

  const hero = design?.hero || {};
  const about = design?.about || {};
  const contact = design?.contact || {};
  const faq = design?.faq || [];
  const benefits = design?.benefits || [];
  const legalPages = design?.legal_pages || {};

  const regenSection = async (section) => {
    setRegenerating(section);
    const { data, error, rawDetail } = await apiCall(() =>
      api.post(`/sites/${siteId}/design/regenerate/${section}`, { tweak: "" })
    );
    setRegenerating(null);
    if (error) {
      const detail = rawDetail?.detail || error;
      window.alert(`Régénération échouée : ${detail}`);
      return;
    }
    await onReload();
  };

  const seedLegal = async () => {
    setSeedingLegal(true);
    const { error } = await apiCall(() => api.post(`/sites/${siteId}/design/seed-legal`, {}));
    setSeedingLegal(false);
    if (error) { window.alert(error); return; }
    await onReload();
  };

  const regenAll = async () => {
    if (!window.confirm("Régénérer tout le contenu (hero, about, FAQ, etc.) avec ce brief ?")) return;
    setGenerating(true);
    const { error } = await apiCall(() =>
      api.post(`/sites/${siteId}/design/generate`, { with_logo: false, tweak })
    );
    if (error) { setGenerating(false); window.alert(`Démarrage échoué : ${error}`); return; }
    setTweak("");
    const poll = async () => {
      const { data: s } = await apiCall(() => api.get(`/sites/${siteId}/design/generate/status`));
      if (s?.status === "running") { setTimeout(poll, 3000); return; }
      setGenerating(false);
      if (s?.status === "done") await onReload();
      if (s?.status === "failed") window.alert(`Échec : ${s?.error || ""}`);
    };
    setTimeout(poll, 3000);
  };

  return (
    <div className="space-y-5" data-testid="content-tab">
      {/* Regen buttons */}
      <div className="bg-white border border-neutral-200 rounded-2xl p-5">
        <div className="text-[11px] uppercase tracking-widest text-neutral-500 mb-3">Régénération par section</div>
        <div className="flex gap-2 flex-wrap">
          {REGEN_SECTIONS.map(({ key, label, Icon }) => (
            <button
              key={key}
              onClick={() => regenSection(key)}
              disabled={regenerating === key}
              data-testid={`regen-${key}`}
              className="h-9 px-3 rounded-lg bg-white border border-neutral-200 hover:border-neutral-900 text-xs font-medium text-neutral-700 flex items-center gap-1.5 disabled:opacity-60"
            >
              {regenerating === key ? <ArrowClockwise size={12} className="animate-spin" /> : <Icon size={12} weight="duotone" />}
              {regenerating === key ? "…" : label}
            </button>
          ))}
        </div>
      </div>

      {/* Hero */}
      {hero.title && (
        <Section title="Hero" testid="design-hero">
          <div className="text-xs text-neutral-500 mb-1">TITRE</div>
          <div className="text-xl font-semibold text-neutral-900" style={{ fontFamily: "'Fraunces', serif" }}>{hero.title}</div>
          {hero.subtitle && <div className="text-sm text-neutral-700 mt-2 leading-relaxed">{hero.subtitle}</div>}
          {hero.cta_label && <div className="mt-3 inline-block text-[11px] uppercase tracking-widest bg-neutral-100 px-2 py-1 rounded">CTA : {hero.cta_label}</div>}
        </Section>
      )}

      {/* Benefits */}
      {benefits.length > 0 && (
        <Section title={`${benefits.length} bénéfices clés`} testid="design-benefits">
          <div className="grid md:grid-cols-2 gap-3">
            {benefits.map((b, i) => (
              <div key={i} className="p-3 rounded-lg bg-neutral-50 border border-neutral-100">
                <div className="font-medium text-sm text-neutral-900">{b.title || b.label}</div>
                {b.description && <div className="text-xs text-neutral-600 mt-1">{b.description}</div>}
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* About */}
      {(about.paragraphs || about.content) && (
        <Section title="À propos" testid="design-about">
          {about.title && <div className="font-semibold mb-2">{about.title}</div>}
          {Array.isArray(about.paragraphs)
            ? about.paragraphs.map((p, i) => <p key={i} className="text-sm text-neutral-700 leading-relaxed mb-2">{p}</p>)
            : <p className="text-sm text-neutral-700 leading-relaxed">{about.content}</p>}
        </Section>
      )}

      {/* FAQ */}
      {faq.length > 0 && (
        <Section title={`FAQ · ${faq.length} questions`} testid="design-faq">
          <div className="space-y-2">
            {faq.map((q, i) => (
              <details key={i} className="group bg-neutral-50 rounded-lg border border-neutral-100 p-3">
                <summary className="cursor-pointer text-sm font-medium text-neutral-900">{q.question || q.q}</summary>
                <p className="text-sm text-neutral-700 mt-2">{q.answer || q.a}</p>
              </details>
            ))}
          </div>
        </Section>
      )}

      {/* Contact */}
      {(contact.email || contact.phone) && (
        <Section title="Contact" testid="design-contact">
          {contact.email && <div className="text-sm">Email : {contact.email}</div>}
          {contact.phone && <div className="text-sm">Tél : {contact.phone}</div>}
          {contact.address && <div className="text-sm">Adresse : {contact.address}</div>}
        </Section>
      )}

      {/* Legal */}
      <Section title="Pages légales" testid="design-legal">
        <div className="grid md:grid-cols-3 gap-3 text-sm">
          {[
            ["CGV", `/shop/${siteId}/cgv`],
            ["Mentions légales", `/shop/${siteId}/mentions`],
            ["Confidentialité", `/shop/${siteId}/confidentialite`],
          ].map(([label, href]) => (
            <a key={label} href={href} target="_blank" rel="noreferrer"
              className="block p-3 bg-neutral-50 hover:bg-neutral-100 rounded-lg border border-neutral-200 text-center">
              <div className="font-medium text-neutral-900">{label}</div>
              <div className="text-xs text-neutral-500 mt-0.5">Ouvrir ↗</div>
            </a>
          ))}
        </div>
        <div className="text-xs text-neutral-500 mt-3 flex items-start gap-2">
          <Info size={14} weight="duotone" className="flex-shrink-0 mt-0.5" />
          <span>Générées automatiquement depuis les infos société (Compte → infos société).</span>
        </div>
      </Section>

      {/* Brief + regen all */}
      <div className="bg-gradient-to-br from-amber-50 to-orange-50 border border-amber-200 rounded-2xl p-6">
        <div className="text-[11px] uppercase tracking-widest text-amber-700 mb-2 font-semibold">Régénérer tout le contenu avec un brief</div>
        <textarea
          value={tweak}
          onChange={(e) => setTweak(e.target.value)}
          placeholder="Ex. « ton plus chaleureux, mets l'accent sur l'installation offerte et la garantie 5 ans »"
          className="w-full min-h-[80px] p-3 rounded-lg border border-amber-300 bg-white text-sm resize-y"
          data-testid="design-brief"
        />
        <button
          onClick={regenAll}
          disabled={generating}
          data-testid="design-regen-all"
          className="mt-3 h-10 px-4 rounded-lg bg-amber-600 hover:bg-amber-700 text-white text-sm font-medium flex items-center gap-2 disabled:opacity-60"
        >
          {generating ? <ArrowClockwise size={14} className="animate-spin" /> : <Sparkle size={14} weight="fill" />}
          {generating ? "Régénération (60-90s)…" : "Régénérer avec ce brief"}
        </button>
      </div>
    </div>
  );
}

function Section({ title, children, testid }) {
  return (
    <div className="bg-white border border-neutral-200 rounded-2xl p-5" data-testid={testid}>
      <div className="text-[11px] uppercase tracking-widest text-neutral-500 mb-3">{title}</div>
      {children}
    </div>
  );
}
-6">
        <div className="text-[11px] uppercase tracking-widest text-amber-700 mb-2 font-semibold">Régénérer tout le contenu avec un brief</div>
        <textarea
          value={tweak}
          onChange={(e) => setTweak(e.target.value)}
          placeholder="Ex. « ton plus chaleureux, mets l'accent sur l'installation offerte et la garantie 5 ans »"
          className="w-full min-h-[80px] p-3 rounded-lg border border-amber-300 bg-white text-sm resize-y"
          data-testid="design-brief"
        />
        <button
          onClick={regenAll}
          disabled={generating}
          data-testid="design-regen-all"
          className="mt-3 h-10 px-4 rounded-lg bg-amber-600 hover:bg-amber-700 text-white text-sm font-medium flex items-center gap-2 disabled:opacity-60"
        >
          {generating ? <ArrowClockwise size={14} className="animate-spin" /> : <Sparkle size={14} weight="fill" />}
          {generating ? "Régénération (60-90s)…" : "Régénérer avec ce brief"}
        </button>
      </div>
    </div>
  );
}

function Section({ title, children, testid }) {
  return (
    <div className="bg-white border border-neutral-200 rounded-2xl p-5" data-testid={testid}>
      <div className="text-[11px] uppercase tracking-widest text-neutral-500 mb-3">{title}</div>
      {children}
    </div>
  );
}
