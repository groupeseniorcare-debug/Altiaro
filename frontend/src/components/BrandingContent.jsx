import React, { useEffect, useMemo, useState } from "react";
import {
  ArrowClockwise, Sparkle, CheckCircle, Info, ArrowLeft, ArrowRight,
  ClipboardText, ChatCenteredText, Star, UserCircle, Phone, Scales, Rocket,
  Plus, Trash,
} from "@phosphor-icons/react";
import { api, apiCall } from "../lib/api";

/**
 * Branding content editor with per-page sub-tabs.
 * Each page (Hero, À propos, Bénéfices, FAQ, Témoignages, Contact, Pages légales)
 * has its own editable form + ✨ regen button.
 * All edits are persisted via PATCH /sites/{id}/design/section/{section}.
 */

const SUB_TABS = [
  { key: "hero",         label: "Hero",          Icon: Rocket },
  { key: "about",        label: "À propos",      Icon: UserCircle },
  { key: "benefits",     label: "Bénéfices",     Icon: CheckCircle },
  { key: "faq",          label: "FAQ",           Icon: ChatCenteredText },
  { key: "testimonials", label: "Témoignages",   Icon: Star },
  { key: "contact",      label: "Contact",       Icon: Phone },
  { key: "legal",        label: "Pages légales", Icon: Scales },
];

// Picks the FR value from an i18n dict, or returns the string as-is.
const pickFr = (v) => {
  if (v == null) return "";
  if (typeof v === "string") return v;
  if (typeof v === "object") return v.fr || v.en || Object.values(v)[0] || "";
  return String(v);
};
// Updates a value in-place, preserving the i18n structure if it was an object.
const setLang = (original, newFr) => {
  if (typeof original === "object" && original !== null && !Array.isArray(original)) {
    return { ...original, fr: newFr };
  }
  return newFr;
};

export default function BrandingContent({ siteId, design, onReload, onChange }) {
  const [sub, setSub] = useState("hero");

  // Notify parent on every section save so the live preview iframe can refresh.
  const bump = () => onChange?.();

  return (
    <div className="space-y-4" data-testid="content-tab">
      {/* Sub-tabs */}
      <div className="bg-white rounded-2xl border border-neutral-200 p-1.5 flex gap-1 overflow-x-auto">
        {SUB_TABS.map(({ key, label, Icon }) => (
          <button
            key={key}
            onClick={() => setSub(key)}
            data-testid={`subtab-${key}`}
            className={`h-10 px-4 rounded-xl text-sm font-medium flex items-center gap-2 whitespace-nowrap transition ${
              sub === key ? "bg-neutral-900 text-white" : "text-neutral-600 hover:bg-neutral-100"
            }`}
          >
            <Icon size={14} weight={sub === key ? "fill" : "duotone"} /> {label}
          </button>
        ))}
      </div>

      {sub === "hero" && (
        <HeroEditor siteId={siteId} design={design} onReload={onReload} onSaved={bump} />
      )}
      {sub === "about" && (
        <AboutEditor siteId={siteId} design={design} onReload={onReload} onSaved={bump} />
      )}
      {sub === "benefits" && (
        <BenefitsEditor siteId={siteId} design={design} onReload={onReload} onSaved={bump} />
      )}
      {sub === "faq" && (
        <FAQEditor siteId={siteId} design={design} onReload={onReload} onSaved={bump} />
      )}
      {sub === "testimonials" && (
        <TestimonialsEditor siteId={siteId} design={design} onReload={onReload} onSaved={bump} />
      )}
      {sub === "contact" && (
        <ContactEditor siteId={siteId} design={design} onReload={onReload} onSaved={bump} />
      )}
      {sub === "legal" && (
        <LegalEditor siteId={siteId} design={design} onReload={onReload} onSaved={bump} />
      )}
    </div>
  );
}

// ==========================================================================
// Shared helpers
// ==========================================================================
function SectionCard({ title, testid, children, actions }) {
  return (
    <div className="bg-white border border-neutral-200 rounded-2xl p-5" data-testid={testid}>
      <div className="flex items-center justify-between gap-3 mb-4 flex-wrap">
        <div className="text-[11px] uppercase tracking-widest text-neutral-500">{title}</div>
        <div className="flex items-center gap-2">{actions}</div>
      </div>
      <div className="space-y-3">{children}</div>
    </div>
  );
}

function TextInput({ label, value, onChange, testid, placeholder, maxLength }) {
  return (
    <div>
      <div className="text-[11px] uppercase tracking-widest text-neutral-500 mb-1">{label}</div>
      <input
        type="text"
        value={value || ""}
        onChange={(e) => onChange(e.target.value)}
        data-testid={testid}
        maxLength={maxLength}
        placeholder={placeholder}
        className="w-full h-10 px-3 rounded-lg border border-neutral-200 bg-white text-sm focus:outline-none focus:border-neutral-900"
      />
    </div>
  );
}

function TextArea({ label, value, onChange, testid, placeholder, rows = 3, maxLength }) {
  return (
    <div>
      <div className="text-[11px] uppercase tracking-widest text-neutral-500 mb-1">{label}</div>
      <textarea
        value={value || ""}
        onChange={(e) => onChange(e.target.value)}
        data-testid={testid}
        rows={rows}
        maxLength={maxLength}
        placeholder={placeholder}
        className="w-full p-3 rounded-lg border border-neutral-200 bg-white text-sm focus:outline-none focus:border-neutral-900 resize-y"
      />
    </div>
  );
}

function PrimaryButton({ onClick, disabled, testid, children, Icon = CheckCircle, busyIcon = ArrowClockwise, busy }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      data-testid={testid}
      className="h-9 px-4 rounded-lg bg-neutral-900 hover:bg-neutral-800 text-white text-sm font-medium flex items-center gap-1.5 disabled:opacity-60"
    >
      {busy
        ? React.createElement(busyIcon, { size: 14, className: "animate-spin" })
        : React.createElement(Icon, { size: 14, weight: "fill" })}
      {children}
    </button>
  );
}

function AIButton({ onClick, busy, testid, label = "Régénérer IA" }) {
  return (
    <button
      onClick={onClick}
      disabled={busy}
      data-testid={testid}
      className="h-9 px-3 rounded-lg bg-violet-600 hover:bg-violet-700 text-white text-xs font-medium flex items-center gap-1.5 disabled:opacity-60"
    >
      {busy ? <ArrowClockwise size={12} className="animate-spin" /> : <Sparkle size={12} weight="fill" />}
      {busy ? "Génération…" : label}
    </button>
  );
}

/** Shared hook: save section, regenerate via Claude, drive busy states. */
function useSectionActions(siteId, section, onReload, onSaved) {
  const [saving, setSaving] = useState(false);
  const [regenerating, setRegenerating] = useState(false);
  const save = async (payload) => {
    setSaving(true);
    const { error, rawDetail } = await apiCall(() =>
      api.patch(`/sites/${siteId}/design/section/${section}`, payload)
    );
    setSaving(false);
    if (error) { window.alert(rawDetail?.detail || error); return false; }
    await onReload();
    onSaved?.();
    return true;
  };
  const regenerate = async (tweak = "") => {
    setRegenerating(true);
    const { error, rawDetail } = await apiCall(() =>
      api.post(`/sites/${siteId}/design/regenerate/${section}`, { tweak })
    );
    setRegenerating(false);
    if (error) { window.alert(rawDetail?.detail || error); return false; }
    await onReload();
    onSaved?.();
    return true;
  };
  return { saving, regenerating, save, regenerate };
}

// ==========================================================================
// Per-section editors
// ==========================================================================
function HeroEditor({ siteId, design, onReload, onSaved }) {
  const hero = design?.hero || {};
  const { saving, regenerating, save, regenerate } = useSectionActions(siteId, "hero", onReload, onSaved);
  const [form, setForm] = useState({});
  useEffect(() => {
    setForm({
      title: pickFr(hero.title),
      subtitle: pickFr(hero.subtitle),
      cta_label: pickFr(hero.cta_label),
      trust_line: pickFr(hero.trust_line),
    });
  }, [design]); // eslint-disable-line

  const handleSave = () => save({
    ...hero,
    title: setLang(hero.title, form.title),
    subtitle: setLang(hero.subtitle, form.subtitle),
    cta_label: setLang(hero.cta_label, form.cta_label),
    trust_line: setLang(hero.trust_line, form.trust_line),
  });

  return (
    <SectionCard
      title="Hero de la page d'accueil"
      testid="editor-hero"
      actions={<>
        <AIButton onClick={() => regenerate()} busy={regenerating} testid="regen-hero" />
        <PrimaryButton onClick={handleSave} busy={saving} testid="save-hero">Enregistrer</PrimaryButton>
      </>}
    >
      <TextInput label="Titre (5-8 mots)" value={form.title}
        onChange={(v) => setForm({ ...form, title: v })}
        testid="hero-title" maxLength={120} placeholder="Le confort au quotidien, simplement." />
      <TextArea label="Sous-titre" value={form.subtitle} rows={2}
        onChange={(v) => setForm({ ...form, subtitle: v })}
        testid="hero-subtitle" maxLength={240} />
      <div className="grid md:grid-cols-2 gap-3">
        <TextInput label="Libellé du CTA" value={form.cta_label}
          onChange={(v) => setForm({ ...form, cta_label: v })}
          testid="hero-cta" maxLength={40} placeholder="Découvrir" />
        <TextInput label="Trust line (livraison, SAV…)" value={form.trust_line}
          onChange={(v) => setForm({ ...form, trust_line: v })}
          testid="hero-trust" maxLength={140} placeholder="Livraison gratuite · Essai 14j" />
      </div>
    </SectionCard>
  );
}

function AboutEditor({ siteId, design, onReload, onSaved }) {
  const about = design?.about || {};
  const { saving, regenerating, save, regenerate } = useSectionActions(siteId, "about", onReload, onSaved);
  const [headline, setHeadline] = useState("");
  const [paragraphs, setParagraphs] = useState([""]);

  useEffect(() => {
    setHeadline(pickFr(about.headline || about.title));
    if (Array.isArray(about.paragraphs) && about.paragraphs.length) {
      setParagraphs(about.paragraphs.map(pickFr));
    } else if (about.content) {
      setParagraphs([pickFr(about.content)]);
    } else {
      setParagraphs([""]);
    }
  }, [design]); // eslint-disable-line

  const handleSave = () => {
    const paras = paragraphs.filter((p) => p.trim().length > 0);
    const out = {
      ...about,
      headline: setLang(about.headline, headline),
      paragraphs: paras.map((p, i) => setLang(about.paragraphs?.[i], p)),
    };
    return save(out);
  };

  return (
    <SectionCard
      title="Page À propos"
      testid="editor-about"
      actions={<>
        <AIButton onClick={() => regenerate()} busy={regenerating} testid="regen-about" />
        <PrimaryButton onClick={handleSave} busy={saving} testid="save-about">Enregistrer</PrimaryButton>
      </>}
    >
      <TextInput label="Titre de la page" value={headline} onChange={setHeadline}
        testid="about-headline" maxLength={120} />
      {paragraphs.map((p, i) => (
        <div key={i} className="flex gap-2 items-start">
          <div className="flex-1">
            <TextArea label={`Paragraphe ${i + 1}`} value={p}
              onChange={(v) => setParagraphs(paragraphs.map((x, j) => (i === j ? v : x)))}
              testid={`about-p-${i}`} rows={4} maxLength={800} />
          </div>
          {paragraphs.length > 1 && (
            <button onClick={() => setParagraphs(paragraphs.filter((_, j) => j !== i))}
              className="mt-6 w-9 h-9 rounded-lg border border-neutral-200 hover:border-red-300 text-neutral-500 hover:text-red-500 flex items-center justify-center"
              data-testid={`about-p-remove-${i}`}
              title="Supprimer ce paragraphe">
              <Trash size={12} />
            </button>
          )}
        </div>
      ))}
      <button onClick={() => setParagraphs([...paragraphs, ""])}
        data-testid="about-p-add"
        className="h-9 px-3 rounded-lg border border-dashed border-neutral-300 hover:border-neutral-900 text-xs text-neutral-600 flex items-center gap-1.5">
        <Plus size={12} weight="bold" /> Ajouter un paragraphe
      </button>
    </SectionCard>
  );
}

function BenefitsEditor({ siteId, design, onReload, onSaved }) {
  const benefits = Array.isArray(design?.benefits) ? design.benefits : [];
  const { saving, regenerating, save, regenerate } = useSectionActions(siteId, "benefits", onReload, onSaved);
  const [items, setItems] = useState([]);
  useEffect(() => {
    setItems(benefits.map((b) => ({
      icon: b.icon || "ShieldCheck",
      title: pickFr(b.title || b.label),
      desc: pickFr(b.desc || b.description),
      _raw: b,
    })));
  }, [design]); // eslint-disable-line

  const update = (i, key, v) => setItems(items.map((it, j) => (i === j ? { ...it, [key]: v } : it)));
  const handleSave = () => {
    const out = items.filter((it) => it.title || it.desc).map((it) => ({
      ...(it._raw || {}),
      icon: it.icon,
      title: setLang(it._raw?.title || it._raw?.label, it.title),
      desc: setLang(it._raw?.desc || it._raw?.description, it.desc),
    }));
    return save(out);
  };

  return (
    <SectionCard
      title={`${items.length} bénéfices clés`}
      testid="editor-benefits"
      actions={<>
        <AIButton onClick={() => regenerate()} busy={regenerating} testid="regen-benefits" />
        <PrimaryButton onClick={handleSave} busy={saving} testid="save-benefits">Enregistrer</PrimaryButton>
      </>}
    >
      {items.map((it, i) => (
        <div key={i} className="p-4 rounded-xl bg-neutral-50 border border-neutral-100 space-y-2">
          <div className="grid md:grid-cols-[160px_1fr] gap-2">
            <TextInput label="Icône (Phosphor)" value={it.icon}
              onChange={(v) => update(i, "icon", v)}
              testid={`benefit-icon-${i}`} maxLength={40} placeholder="ShieldCheck" />
            <TextInput label={`Titre bénéfice ${i + 1}`} value={it.title}
              onChange={(v) => update(i, "title", v)}
              testid={`benefit-title-${i}`} maxLength={80} />
          </div>
          <TextArea label="Description" value={it.desc}
            onChange={(v) => update(i, "desc", v)}
            testid={`benefit-desc-${i}`} rows={2} maxLength={240} />
          <div className="flex justify-end">
            <button onClick={() => setItems(items.filter((_, j) => j !== i))}
              data-testid={`benefit-remove-${i}`}
              className="text-xs text-neutral-500 hover:text-red-500 flex items-center gap-1">
              <Trash size={10} /> Supprimer
            </button>
          </div>
        </div>
      ))}
      <button onClick={() => setItems([...items, { icon: "ShieldCheck", title: "", desc: "" }])}
        data-testid="benefit-add"
        className="w-full h-10 rounded-lg border border-dashed border-neutral-300 hover:border-neutral-900 text-xs text-neutral-600 flex items-center justify-center gap-1.5">
        <Plus size={12} weight="bold" /> Ajouter un bénéfice
      </button>
    </SectionCard>
  );
}

function FAQEditor({ siteId, design, onReload, onSaved }) {
  const faq = Array.isArray(design?.faq) ? design.faq : [];
  const { saving, regenerating, save, regenerate } = useSectionActions(siteId, "faq", onReload, onSaved);
  const [items, setItems] = useState([]);
  useEffect(() => {
    setItems(faq.map((q) => ({
      question: pickFr(q.question || q.q),
      answer: pickFr(q.answer || q.a),
      _raw: q,
    })));
  }, [design]); // eslint-disable-line

  const update = (i, key, v) => setItems(items.map((it, j) => (i === j ? { ...it, [key]: v } : it)));
  const handleSave = () => {
    const out = items.filter((it) => it.question).map((it) => ({
      ...(it._raw || {}),
      question: setLang(it._raw?.question || it._raw?.q, it.question),
      answer: setLang(it._raw?.answer || it._raw?.a, it.answer),
      q: undefined, a: undefined,
    })).map((o) => { delete o.q; delete o.a; return o; });
    return save(out);
  };

  return (
    <SectionCard
      title={`FAQ · ${items.length} questions`}
      testid="editor-faq"
      actions={<>
        <AIButton onClick={() => regenerate()} busy={regenerating} testid="regen-faq" />
        <PrimaryButton onClick={handleSave} busy={saving} testid="save-faq">Enregistrer</PrimaryButton>
      </>}
    >
      {items.map((it, i) => (
        <div key={i} className="p-4 rounded-xl bg-neutral-50 border border-neutral-100 space-y-2">
          <TextInput label={`Question ${i + 1}`} value={it.question}
            onChange={(v) => update(i, "question", v)}
            testid={`faq-q-${i}`} maxLength={200} />
          <TextArea label="Réponse" value={it.answer}
            onChange={(v) => update(i, "answer", v)}
            testid={`faq-a-${i}`} rows={3} maxLength={800} />
          <div className="flex justify-end">
            <button onClick={() => setItems(items.filter((_, j) => j !== i))}
              data-testid={`faq-remove-${i}`}
              className="text-xs text-neutral-500 hover:text-red-500 flex items-center gap-1">
              <Trash size={10} /> Supprimer
            </button>
          </div>
        </div>
      ))}
      <button onClick={() => setItems([...items, { question: "", answer: "" }])}
        data-testid="faq-add"
        className="w-full h-10 rounded-lg border border-dashed border-neutral-300 hover:border-neutral-900 text-xs text-neutral-600 flex items-center justify-center gap-1.5">
        <Plus size={12} weight="bold" /> Ajouter une question
      </button>
    </SectionCard>
  );
}

function TestimonialsEditor({ siteId, design, onReload, onSaved }) {
  const tests = Array.isArray(design?.testimonials) ? design.testimonials : [];
  const { saving, regenerating, save, regenerate } = useSectionActions(siteId, "testimonials", onReload, onSaved);
  const [items, setItems] = useState([]);
  useEffect(() => {
    setItems(tests.map((t) => ({
      name: t.name || "",
      city: t.city || "",
      age: t.age || "",
      rating: t.rating || 5,
      quote: pickFr(t.quote),
      _raw: t,
    })));
  }, [design]); // eslint-disable-line

  const update = (i, key, v) => setItems(items.map((it, j) => (i === j ? { ...it, [key]: v } : it)));
  const handleSave = () => {
    const out = items.filter((it) => it.name && it.quote).map((it) => ({
      ...(it._raw || {}),
      name: it.name,
      city: it.city,
      age: Number(it.age) || it._raw?.age || undefined,
      rating: Number(it.rating) || 5,
      quote: setLang(it._raw?.quote, it.quote),
    }));
    return save(out);
  };

  return (
    <SectionCard
      title={`Témoignages · ${items.length}`}
      testid="editor-testimonials"
      actions={<>
        <AIButton onClick={() => regenerate()} busy={regenerating} testid="regen-testimonials" />
        <PrimaryButton onClick={handleSave} busy={saving} testid="save-testimonials">Enregistrer</PrimaryButton>
      </>}
    >
      {items.map((it, i) => (
        <div key={i} className="p-4 rounded-xl bg-neutral-50 border border-neutral-100 space-y-2">
          <div className="grid md:grid-cols-3 gap-2">
            <TextInput label="Prénom" value={it.name}
              onChange={(v) => update(i, "name", v)} testid={`testim-name-${i}`} maxLength={60} />
            <TextInput label="Ville" value={it.city}
              onChange={(v) => update(i, "city", v)} testid={`testim-city-${i}`} maxLength={60} />
            <div className="grid grid-cols-2 gap-2">
              <TextInput label="Âge" value={it.age} onChange={(v) => update(i, "age", v)}
                testid={`testim-age-${i}`} maxLength={3} />
              <TextInput label="Note /5" value={it.rating} onChange={(v) => update(i, "rating", v)}
                testid={`testim-rating-${i}`} maxLength={1} />
            </div>
          </div>
          <TextArea label="Citation" value={it.quote}
            onChange={(v) => update(i, "quote", v)}
            testid={`testim-quote-${i}`} rows={2} maxLength={400} />
          <div className="flex justify-end">
            <button onClick={() => setItems(items.filter((_, j) => j !== i))}
              data-testid={`testim-remove-${i}`}
              className="text-xs text-neutral-500 hover:text-red-500 flex items-center gap-1">
              <Trash size={10} /> Supprimer
            </button>
          </div>
        </div>
      ))}
      <button onClick={() => setItems([...items, { name: "", city: "", age: 70, rating: 5, quote: "" }])}
        data-testid="testim-add"
        className="w-full h-10 rounded-lg border border-dashed border-neutral-300 hover:border-neutral-900 text-xs text-neutral-600 flex items-center justify-center gap-1.5">
        <Plus size={12} weight="bold" /> Ajouter un témoignage
      </button>
    </SectionCard>
  );
}

function ContactEditor({ siteId, design, onReload, onSaved }) {
  const contact = design?.contact || {};
  const { saving, regenerating, save, regenerate } = useSectionActions(siteId, "contact", onReload, onSaved);
  const [form, setForm] = useState({});
  useEffect(() => {
    setForm({
      headline: pickFr(contact.headline),
      intro: pickFr(contact.intro),
      email: contact.support_email || contact.email || "",
      phone: contact.support_phone || contact.phone || "",
      hours: pickFr(contact.support_hours || contact.hours),
      address: contact.address || "",
    });
  }, [design]); // eslint-disable-line

  const handleSave = () => save({
    ...contact,
    headline: setLang(contact.headline, form.headline),
    intro: setLang(contact.intro, form.intro),
    support_email: form.email, email: form.email,
    support_phone: form.phone, phone: form.phone,
    support_hours: setLang(contact.support_hours || contact.hours, form.hours),
    hours: form.hours,
    address: form.address,
  });

  return (
    <SectionCard
      title="Page Contact"
      testid="editor-contact"
      actions={<>
        <AIButton onClick={() => regenerate()} busy={regenerating} testid="regen-contact" />
        <PrimaryButton onClick={handleSave} busy={saving} testid="save-contact">Enregistrer</PrimaryButton>
      </>}
    >
      <TextInput label="Titre de la page" value={form.headline}
        onChange={(v) => setForm({ ...form, headline: v })}
        testid="contact-headline" maxLength={120} />
      <TextArea label="Intro" value={form.intro} rows={2}
        onChange={(v) => setForm({ ...form, intro: v })}
        testid="contact-intro" maxLength={300} />
      <div className="grid md:grid-cols-2 gap-3">
        <TextInput label="Email de contact" value={form.email}
          onChange={(v) => setForm({ ...form, email: v })}
          testid="contact-email" placeholder="contact@marque.fr" />
        <TextInput label="Téléphone" value={form.phone}
          onChange={(v) => setForm({ ...form, phone: v })}
          testid="contact-phone" placeholder="+33 1 80 50 60 70" />
      </div>
      <TextInput label="Horaires" value={form.hours}
        onChange={(v) => setForm({ ...form, hours: v })}
        testid="contact-hours" placeholder="Lun-Ven · 9h-19h" />
      <TextArea label="Adresse postale (optionnel)" value={form.address} rows={2}
        onChange={(v) => setForm({ ...form, address: v })}
        testid="contact-address" maxLength={200} />
    </SectionCard>
  );
}

function LegalEditor({ siteId, design, onReload, onSaved }) {
  const legal = design?.legal_pages || {};
  const [seeding, setSeeding] = useState(false);
  const seed = async () => {
    setSeeding(true);
    const { error } = await apiCall(() => api.post(`/sites/${siteId}/design/seed-legal`, {}));
    setSeeding(false);
    if (error) { window.alert(error); return; }
    await onReload();
    onSaved?.();
  };

  const pages = [
    ["CGV", "cgv", `/shop/${siteId}/cgv`],
    ["Mentions légales", "mentions_legales", `/shop/${siteId}/mentions`],
    ["Confidentialité", "confidentialite", `/shop/${siteId}/confidentialite`],
    ["Cookies", "cookies", `/shop/${siteId}/cookies`],
    ["Livraison & délais", "livraison", `/shop/${siteId}/livraison`],
    ["Retours & rétractation", "retours", `/shop/${siteId}/retours`],
    ["Médiation", "mediation", `/shop/${siteId}/mediation`],
  ];

  return (
    <SectionCard
      title="Pages légales"
      testid="editor-legal"
      actions={
        <PrimaryButton
          onClick={seed}
          busy={seeding}
          testid="seed-legal"
          Icon={Sparkle}
        >
          {Object.keys(legal).length ? "Régénérer depuis les infos société" : "Générer les pages légales"}
        </PrimaryButton>
      }
    >
      {Object.keys(legal).length === 0 && (
        <div className="p-3 rounded-lg bg-amber-50 border border-amber-200 text-xs text-amber-900 flex items-start gap-2">
          <Info size={14} weight="duotone" className="flex-shrink-0 mt-0.5" />
          <span>
            Aucune page légale encore générée. Clique sur <strong>Générer les pages légales</strong>.
            Elles sont rendues automatiquement à partir des infos société (Compte → infos société).
          </span>
        </div>
      )}
      <div className="grid md:grid-cols-3 gap-3 text-sm">
        {pages.map(([label, key, href]) => {
          const exists = !!legal[key]?.body_md;
          return (
            <a key={key}
              href={exists ? href : undefined}
              target={exists ? "_blank" : undefined}
              rel="noreferrer"
              onClick={(e) => { if (!exists) e.preventDefault(); }}
              data-testid={`legal-link-${key}`}
              className={`block p-4 rounded-xl border text-center ${
                exists
                  ? "bg-neutral-50 hover:bg-neutral-100 border-neutral-200 cursor-pointer"
                  : "bg-neutral-50/50 border-dashed border-neutral-300 opacity-60 cursor-not-allowed"
              }`}
            >
              <div className="font-medium text-neutral-900">{label}</div>
              <div className="text-xs text-neutral-500 mt-1">
                {exists ? `Ouvrir ↗` : "Non générée"}
              </div>
              {exists && (
                <div className="text-[10px] text-neutral-400 mt-1">
                  {(legal[key].body_md || "").length} caractères
                </div>
              )}
            </a>
          );
        })}
      </div>
      <div className="text-xs text-neutral-500 flex items-start gap-2 mt-2">
        <Info size={14} weight="duotone" className="flex-shrink-0 mt-0.5" />
        <span>Le contenu est généré depuis des modèles juridiques standards (FR). Régénère après chaque modification des infos société.</span>
      </div>
    </SectionCard>
  );
}
