import React, { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import axios from "axios";
import StorefrontLayout, { fetchPublicSite } from "../components/StorefrontLayout";
import SEOHead from "../components/SEOHead";
import { useShopSiteId } from "../lib/shopSiteId";
import {
  Heart, Users, ShieldCheck, HandHeart, Leaf, Star,
  EnvelopeSimple, Phone, MapPin, Clock, CheckCircle,
  Truck, Package, ArrowCounterClockwise, CreditCard, ArrowRight,
} from "@phosphor-icons/react";

const BACKEND_URL = "";

function useSiteDesign() {
  const siteId = useShopSiteId();
  const [site, setSite] = useState(null);
  const [design, setDesign] = useState(null);
  const storageKey = `cf_lang_${siteId}`;
  const [lang, setLangState] = useState(() => localStorage.getItem(storageKey) || "fr");
  const setLang = (l) => {
    localStorage.setItem(storageKey, l);
    setLangState(l);
  };
  useEffect(() => {
    fetchPublicSite(siteId).then(setSite).catch(() => setSite({ error: true }));
    axios
      .get(`${BACKEND_URL}/api/public/sites/${siteId}/design`)
      .then(({ data }) => setDesign(data?.published ? data.design : null))
      .catch(() => setDesign(null));
  }, [siteId]);
  // Phase 0.5 — `availableLangs` was referenced inside StorefrontLayout but never
  // defined here ⇒ ReferenceError that crashed every CMS page (about/contact/legal/…).
  // Default to FR + any extra language the operator activated on this site.
  const availableLangs = (site?.selected_languages && site.selected_languages.length)
    ? site.selected_languages
    : ["fr"];
  return { siteId, site, design: design || {}, lang, setLang, availableLangs };
}

function pickText(node, lang) {
  if (!node) return null;
  if (typeof node === "string") return node;
  return node[lang] || node.fr || Object.values(node)[0] || null;
}

function MarkdownLite({ md }) {
  if (!md) return null;
  const html = md
    .split("\n\n")
    .map((block) => {
      const b = block.trim();
      if (b.startsWith("### ")) return `<h3 class="font-semibold text-lg mt-6 mb-2">${b.slice(4)}</h3>`;
      if (b.startsWith("## ")) return `<h2 class="font-semibold text-xl mt-8 mb-3">${b.slice(3)}</h2>`;
      if (b.startsWith("# ")) return `<h1 class="font-semibold text-3xl mt-2 mb-5">${b.slice(2)}</h1>`;
      if (b.startsWith("- ")) {
        const items = b.split("\n").map((l) => `<li>${l.replace(/^- /, "")}</li>`).join("");
        return `<ul class="list-disc pl-6 space-y-1 my-3">${items}</ul>`;
      }
      return `<p class="leading-relaxed my-3">${b.replace(/\n/g, "<br/>")}</p>`;
    })
    .join("");
  return <div className="prose max-w-none text-[15px]" dangerouslySetInnerHTML={{ __html: html }} />;
}

function PageHero({ eyebrow, title, subtitle, design }) {
  // Lot G Fix 13 — fond transparent (hérite du body) au lieu d'un bloc coloré.
  // Le H1 reste premium en serif anthracite, eyebrow accent primary du site.
  const fontHeading = design?.brand?.font_heading || "Fraunces";
  const primary = design?.brand?.primary_color || "#B84B31";
  return (
    <section className="border-b border-stone-200/60">
      <div className="max-w-4xl mx-auto px-6 md:px-10 py-14 md:py-20">
        {eyebrow && (
          <div className="text-[11px] uppercase tracking-[0.2em] mb-3 font-medium" style={{ color: primary }}>
            {eyebrow}
          </div>
        )}
        <h1
          className="text-4xl md:text-5xl lg:text-6xl leading-[1.05] tracking-tight text-neutral-900"
          style={{ fontFamily: `"${fontHeading}", serif` }}
        >
          {title}
        </h1>
        {subtitle && (
          <p className="text-[17px] text-neutral-600 mt-5 leading-relaxed max-w-2xl">
            {subtitle}
          </p>
        )}
      </div>
    </section>
  );
}

/* =========================================================
 * ABOUT — /about
 * ========================================================= */
export function StorefrontAbout() {
  const { site, design, lang, setLang, availableLangs } = useSiteDesign();
  const fontHeading = design?.brand?.font_heading || "Fraunces";
  const primary = design?.brand?.primary_color || "#B84B31";

  // Phase 0.5 — priorité au contenu premium généré par le pipeline étape 5
  // (`design.cms_pages.about` = {title, subtitle, body_md, highlights:[{title,body}]}).
  // Fallback : `design.pages.about` (ancien format split paragraphs), puis fallback hardcodé.
  const cmsAbout = design?.cms_pages?.about;
  const aiPage = design?.pages?.about || {};
  const hasCms = !!(cmsAbout && (cmsAbout.body_md || cmsAbout.title));

  const headline = (hasCms && cmsAbout.title)
    || aiPage.headline
    || pickText(design?.about?.headline, lang)
    || `L'histoire de ${site?.name || "notre boutique"}`;
  const subtitle = (hasCms && cmsAbout.subtitle)
    || `${site?.name || "Notre maison"} — pour que bien vieillir soit simple et digne.`;

  const aiParagraphs = Array.isArray(aiPage.paragraphs) ? aiPage.paragraphs.filter(Boolean) : [];
  const paragraphs = (design?.about?.paragraphs || []).map((p) => pickText(p, lang)).filter(Boolean);
  const fallbackParagraphs = [
    `Tout a commencé avec une question simple : « Pourquoi est-il si compliqué de trouver des produits de qualité, adaptés aux seniors, sans se perdre dans le jargon médical ou dans des catalogues impersonnels ? »`,
    `${site?.name || "Notre boutique"} est née de cette évidence. Nous sélectionnons chaque produit comme si c'était pour un membre de notre propre famille. Nos partenaires fabricants sont audités, nos ergothérapeutes valident les produits avant l'entrée en catalogue, et notre équipe de conseillers est joignable par téléphone — par de vrais humains, pas des robots.`,
    `Nous croyons qu'on peut vieillir dignement, sereinement, en gardant son autonomie. Et que cela doit être accessible à tous, simplement.`,
  ];
  const displayParagraphs = aiParagraphs.length ? aiParagraphs : (paragraphs.length > 0 ? paragraphs : fallbackParagraphs);

  // Highlights from CMS premium (3 cards)
  const cmsHighlights = (hasCms && Array.isArray(cmsAbout.highlights))
    ? cmsAbout.highlights.filter((h) => h && h.title)
    : [];

  const aiValues = Array.isArray(aiPage.values) ? aiPage.values.filter((v) => v && v.title) : [];
  // Map CMS highlights to the "pillars" structure if present, otherwise fall back to aiPage.values then to hardcoded defaults.
  const pillars = cmsHighlights.length
    ? cmsHighlights.map((h) => ({ icon: Heart, title: h.title, desc: h.body || "" }))
    : (aiValues.length ? aiValues.map((v) => ({
        icon: Heart, title: v.title, desc: v.description || "",
      })) : [
        { icon: Heart, title: "Bienveillance", desc: "Chaque produit est pensé pour préserver dignité, confort et autonomie." },
        { icon: ShieldCheck, title: "Exigence", desc: "Audits fournisseurs, tests ergothérapeutes, garantie 2 ans sur tout." },
        { icon: HandHeart, title: "Accompagnement", desc: "Notre support est disponible Lun–Ven 9h–18h, installation possible à domicile." },
        { icon: Leaf, title: "Responsabilité", desc: "Circuits courts privilégiés, emballages réduits, logistique optimisée." },
      ]);

  return (
    <StorefrontLayout lang={lang} setLang={setLang} availableLangs={availableLangs} site={site} design={design}>
      <SEOHead
        title={`À propos · ${site?.name || ""}`}
        description={`${site?.name || "Notre maison"} — Notre histoire, nos valeurs, notre équipe.`}
        schema={[
          {
            "@context": "https://schema.org",
            "@type": "AboutPage",
            name: `À propos · ${site?.name || ""}`,
            url: typeof window !== "undefined" ? window.location.href : "",
          },
          {
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            itemListElement: [
              { "@type": "ListItem", position: 1, name: "Accueil", item: `/shop/${site?.id || ""}` },
              { "@type": "ListItem", position: 2, name: "À propos", item: `/shop/${site?.id || ""}/about` },
            ],
          },
        ]}
      />
      <PageHero
        eyebrow="À propos"
        title={headline}
        subtitle={subtitle}
        design={design}
      />

      <article className="max-w-3xl mx-auto px-6 md:px-10 py-16 md:py-20 space-y-6 text-[17px] leading-relaxed text-neutral-700" data-testid="page-about">
        {hasCms && cmsAbout.body_md
          ? <MarkdownLite md={cmsAbout.body_md} />
          : displayParagraphs.map((p, i) => <p key={i}>{p}</p>)}
      </article>

      <section className="max-w-6xl mx-auto px-6 md:px-10 pb-20">
        <div className="text-center mb-12">
          <div className="text-[11px] uppercase tracking-[0.2em] text-neutral-500 mb-3">Nos valeurs</div>
          <h2 className="text-3xl md:text-4xl" style={{ fontFamily: `"${fontHeading}", serif` }}>
            Ce qui nous guide au quotidien
          </h2>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {pillars.map(({ icon: Icon, title, desc }, i) => (
            <div key={i} className="bg-white rounded-3xl p-7 border border-neutral-100">
              <div className="w-12 h-12 rounded-xl flex items-center justify-center mb-5" style={{ background: `${primary}14`, color: primary }}>
                <Icon size={24} weight="duotone" />
              </div>
              <div className="font-semibold text-neutral-900 mb-2">{title}</div>
              <div className="text-sm text-neutral-600 leading-relaxed">{desc}</div>
            </div>
          ))}
        </div>
      </section>

      <section className="py-16 md:py-20 px-6" style={{ background: "#1C1917", color: "#fff" }}>
        <div className="max-w-3xl mx-auto text-center">
          <Users size={36} weight="duotone" className="mx-auto mb-5 opacity-80" />
          <h2 className="text-3xl md:text-4xl mb-4" style={{ fontFamily: `"${fontHeading}", serif` }}>
            Besoin de parler à un humain ?
          </h2>
          <p className="text-white/80 mb-8 max-w-lg mx-auto">
            Nous ne sommes pas une marketplace. Chaque jour, une vraie équipe prend le temps de répondre à chaque message.
          </p>
          <Link to={`../contact`} relative="path" className="inline-flex items-center gap-2 h-12 px-7 rounded-full bg-white text-neutral-900 font-medium hover:opacity-90 transition">
            Nous contacter <ArrowRight size={14} weight="bold" />
          </Link>
        </div>
      </section>
    </StorefrontLayout>
  );
}

/* =========================================================
 * CONTACT — /contact
 * ========================================================= */
export function StorefrontContact() {
  const { siteId, site, design, lang, setLang, availableLangs } = useSiteDesign();
  const fontHeading = design?.brand?.font_heading || "Fraunces";
  const primary = design?.brand?.primary_color || "#B84B31";
  const [form, setForm] = useState({ name: "", email: "", phone: "", subject: "", message: "" });
  const [sent, setSent] = useState(false);
  const [sending, setSending] = useState(false);
  const [err, setErr] = useState("");
  const contact = design?.contact || {};
  // Phase 0.5 — priorité au contenu premium généré par le pipeline étape 5
  // (`design.cms_pages.contact` = {title, subtitle, intro_md, phone_label, phone_hours,
  // email_label, promise}). Fallback : `design.pages.contact` (ancien aiPage) puis hardcodé.
  const cmsContact = design?.cms_pages?.contact;
  const aiPage = design?.pages?.contact || {};
  const hasCms = !!(cmsContact && (cmsContact.intro_md || cmsContact.title));

  const contactEmail = contact.support_email || contact.email || "bonjour@boutique.fr";
  const contactPhone = contact.support_phone || contact.phone || "01 23 45 67 89";
  const contactHours = (hasCms && cmsContact.phone_hours)
    || pickText(contact.support_hours, lang)
    || contact.hours
    || "Lun–Ven · 9h–18h";
  const contactAddress = contact.address || "";
  const phoneLabel = (hasCms && cmsContact.phone_label) || "Par téléphone";
  const emailLabel = (hasCms && cmsContact.email_label) || "Par email";
  const emailPromise = (hasCms && cmsContact.promise)
    || "Réponse sous 2h ouvrées en moyenne.";

  const heroTitle = (hasCms && cmsContact.title) || aiPage.headline || "On vous écoute.";
  const heroSubtitle = (hasCms && cmsContact.subtitle)
    || aiPage.intro
    || "Une question, un conseil produit, un devis, un problème avec votre commande ? Nous vous répondons en moyenne sous 2h ouvrées.";

  const submit = async (e) => {
    e.preventDefault();
    setErr("");
    setSending(true);
    try {
      await axios.post(`${BACKEND_URL}/api/public/sites/${siteId}/contact`, form);
      setSent(true);
    } catch (ex) {
      setErr(ex?.response?.data?.detail || "Erreur lors de l'envoi. Réessayez.");
    }
    setSending(false);
  };

  return (
    <StorefrontLayout lang={lang} setLang={setLang} availableLangs={availableLangs} site={site} design={design}>
      <SEOHead
        title={`Contact · ${site?.name || ""}`}
        description="Contactez notre équipe par email, téléphone ou via le formulaire."
        schema={[
          {
            "@context": "https://schema.org",
            "@type": "ContactPage",
            name: `Contact · ${site?.name || ""}`,
            url: typeof window !== "undefined" ? window.location.href : "",
          },
          {
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            itemListElement: [
              { "@type": "ListItem", position: 1, name: "Accueil", item: `/shop/${site?.id || ""}` },
              { "@type": "ListItem", position: 2, name: "Contact", item: `/shop/${site?.id || ""}/contact` },
            ],
          },
        ]}
      />
      <PageHero
        eyebrow="Contact"
        title={heroTitle}
        subtitle={heroSubtitle}
        design={design}
      />

      {/* Premium intro markdown (only when CMS premium provided one) */}
      {hasCms && cmsContact.intro_md && (
        <section className="max-w-3xl mx-auto px-6 md:px-10 pt-12 md:pt-16 text-[16px] leading-relaxed text-neutral-700">
          <MarkdownLite md={cmsContact.intro_md} />
        </section>
      )}

      <section className="max-w-6xl mx-auto px-6 md:px-10 py-16 md:py-20 grid grid-cols-1 lg:grid-cols-[1fr_1.2fr] gap-12 lg:gap-20" data-testid="page-contact">
        {/* Infos */}
        <div className="space-y-8">
          <div>
            <div className="flex items-center gap-3 mb-3">
              <div className="w-11 h-11 rounded-xl flex items-center justify-center" style={{ background: `${primary}14`, color: primary }}>
                <EnvelopeSimple size={22} weight="duotone" />
              </div>
              <h3 className="text-lg font-semibold">{emailLabel}</h3>
            </div>
            <a href={`mailto:${contactEmail}`} className="text-[17px] font-medium hover:underline" style={{ color: primary }} data-testid="contact-info-email">
              {contactEmail}
            </a>
            <div className="text-sm text-neutral-500 mt-1">{emailPromise}</div>
          </div>

          <div>
            <div className="flex items-center gap-3 mb-3">
              <div className="w-11 h-11 rounded-xl flex items-center justify-center" style={{ background: `${primary}14`, color: primary }}>
                <Phone size={22} weight="duotone" />
              </div>
              <h3 className="text-lg font-semibold">{phoneLabel}</h3>
            </div>
            <a href={`tel:${contactPhone.replace(/\s/g, "")}`} className="text-[17px] font-medium hover:underline" style={{ color: primary }} data-testid="contact-info-phone">
              {contactPhone}
            </a>
            <div className="text-sm text-neutral-500 mt-1 flex items-center gap-1.5"><Clock size={14} /> {contactHours}</div>
          </div>

          {contactAddress && (
            <div>
              <div className="flex items-center gap-3 mb-3">
                <div className="w-11 h-11 rounded-xl flex items-center justify-center" style={{ background: `${primary}14`, color: primary }}>
                  <MapPin size={22} weight="duotone" />
                </div>
                <h3 className="text-lg font-semibold">Notre adresse</h3>
              </div>
              <div className="text-[15px] text-neutral-700">{contactAddress}</div>
            </div>
          )}

          <div className="bg-neutral-50 rounded-2xl p-5 border border-neutral-100">
            <div className="font-semibold mb-2 text-neutral-900">Un support attentif, pas un chatbot</div>
            <div className="text-sm text-neutral-600 leading-relaxed">
              Chez nous, on préfère prendre 5 minutes de plus pour vraiment comprendre votre besoin plutôt que de vous renvoyer vers une FAQ.
            </div>
          </div>
        </div>

        {/* Form */}
        <div>
          {sent ? (
            <div className="bg-white rounded-3xl border p-10 text-center" style={{ borderColor: "#E7E5E4" }} data-testid="contact-sent">
              <CheckCircle size={56} weight="duotone" style={{ color: primary }} className="mx-auto mb-4" />
              <h3 className="text-2xl font-semibold mb-3" style={{ fontFamily: `"${fontHeading}", serif` }}>Merci !</h3>
              <p className="text-neutral-600">Votre message a bien été reçu. Nous vous répondons sous 2h ouvrées.</p>
            </div>
          ) : (
            <form onSubmit={submit} className="bg-white rounded-3xl border p-6 md:p-8 space-y-4" style={{ borderColor: "#E7E5E4" }} data-testid="contact-form">
              <h3 className="text-2xl font-semibold mb-2" style={{ fontFamily: `"${fontHeading}", serif` }}>
                Écrivez-nous
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Input testId="contact-name" label="Nom *" value={form.name} onChange={(v) => setForm({ ...form, name: v })} required />
                <Input testId="contact-email" type="email" label="Email *" value={form.email} onChange={(v) => setForm({ ...form, email: v })} required />
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Input testId="contact-phone" label="Téléphone" value={form.phone} onChange={(v) => setForm({ ...form, phone: v })} />
                <Input testId="contact-subject" label="Sujet" value={form.subject} onChange={(v) => setForm({ ...form, subject: v })} />
              </div>
              <div>
                <label className="block text-[13px] font-medium mb-1.5 text-neutral-900">Message *</label>
                <textarea
                  value={form.message}
                  onChange={(e) => setForm({ ...form, message: e.target.value })}
                  rows={5}
                  required
                  data-testid="contact-message"
                  className="w-full px-4 py-3 rounded-xl border outline-none focus:ring-2 focus:ring-neutral-300"
                  style={{ borderColor: "#E7E5E4" }}
                />
              </div>
              {err && <div className="text-sm text-rose-700">{err}</div>}
              <button
                type="submit"
                disabled={sending}
                data-testid="contact-submit"
                className="h-12 px-6 rounded-full text-white font-medium disabled:opacity-60 w-full sm:w-auto"
                style={{ background: primary }}
              >
                {sending ? "Envoi…" : "Envoyer le message"}
              </button>
              <div className="text-xs text-neutral-500 mt-2">
                Vos données ne sont jamais partagées. Conformité RGPD.
              </div>
            </form>
          )}
        </div>
      </section>
    </StorefrontLayout>
  );
}

function Input({ label, value, onChange, type = "text", required, testId }) {
  return (
    <div>
      <label className="block text-[13px] font-medium mb-1.5 text-neutral-900">{label}</label>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        required={required}
        data-testid={testId}
        className="w-full h-12 px-4 rounded-xl border outline-none focus:ring-2 focus:ring-neutral-300"
        style={{ borderColor: "#E7E5E4" }}
      />
    </div>
  );
}

/* =========================================================
 * LIVRAISON — /livraison
 * ========================================================= */
export function StorefrontLivraison() {
  const { site, design, lang, setLang, availableLangs } = useSiteDesign();
  const fontHeading = design?.brand?.font_heading || "Fraunces";
  const primary = design?.brand?.primary_color || "#B84B31";
  const aiPage = design?.pages?.livraison || {};

  const zones = [
    { country: "France métropolitaine", delay: "48–72h", cost: "Offerte dès 50 €", carriers: "Colissimo, Chronopost, transporteur dédié" },
    { country: "Belgique & Luxembourg", delay: "3–5 jours", cost: "Offerte dès 80 €", carriers: "bpost, DPD" },
    { country: "Allemagne & Pays-Bas", delay: "4–6 jours", cost: "Offerte dès 100 €", carriers: "DHL, GLS" },
    { country: "Suisse", delay: "5–7 jours", cost: "Offerte dès 150 € (hors taxes)", carriers: "La Poste Suisse" },
    { country: "Royaume-Uni", delay: "5–8 jours", cost: "Offerte dès £90 (hors TVA import)", carriers: "DPD UK" },
  ];

  return (
    <StorefrontLayout lang={lang} setLang={setLang} availableLangs={availableLangs} site={site} design={design}>
      <SEOHead title={`Livraison & délais · ${site?.name || ""}`} description="Délais, coûts, suivi, installation à domicile : tout savoir sur la livraison." />
      <PageHero
        eyebrow="Livraison"
        title={aiPage.headline || "Livraison offerte dès 50 € d'achat."}
        subtitle={aiPage.intro || "Expédition sous 24h ouvrées. Réception en 48 à 72h en France. Suivi par SMS et email."}
        design={design}
      />

      <section className="max-w-4xl mx-auto px-6 md:px-10 py-16 md:py-20" data-testid="page-livraison">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5 mb-16">
          {[
            { Icon: Truck, title: "Expédition 24h", desc: "Toute commande passée avant 14h part le jour même (Lun-Ven)." },
            { Icon: Package, title: "Suivi en temps réel", desc: "Numéro de suivi par email + SMS dès l'expédition." },
            { Icon: HandHeart, title: "Installation possible", desc: "Sur fauteuils releveurs et lits médicaux, un technicien se déplace." },
          ].map(({ Icon, title, desc }, i) => (
            <div key={i} className="bg-white rounded-3xl p-6 border border-neutral-100">
              <div className="w-12 h-12 rounded-xl flex items-center justify-center mb-4" style={{ background: `${primary}14`, color: primary }}>
                <Icon size={24} weight="duotone" />
              </div>
              <div className="font-semibold mb-2 text-neutral-900">{title}</div>
              <div className="text-sm text-neutral-600 leading-relaxed">{desc}</div>
            </div>
          ))}
        </div>

        <h2 className="text-2xl md:text-3xl mb-6" style={{ fontFamily: `"${fontHeading}", serif` }}>
          Pays livrés & délais
        </h2>
        <div className="bg-white rounded-2xl border overflow-hidden" style={{ borderColor: "#E7E5E4" }}>
          <table className="w-full">
            <thead className="bg-neutral-50 text-xs uppercase tracking-widest text-neutral-500">
              <tr>
                <th className="px-5 py-3 text-left">Destination</th>
                <th className="px-5 py-3 text-left">Délai</th>
                <th className="px-5 py-3 text-left">Tarif</th>
                <th className="px-5 py-3 text-left hidden md:table-cell">Transporteur</th>
              </tr>
            </thead>
            <tbody>
              {zones.map((z, i) => (
                <tr key={i} className="border-t" style={{ borderColor: "#E7E5E4" }}>
                  <td className="px-5 py-4 font-medium text-neutral-900">{z.country}</td>
                  <td className="px-5 py-4 text-sm text-neutral-600">{z.delay}</td>
                  <td className="px-5 py-4 text-sm" style={{ color: primary }}>{z.cost}</td>
                  <td className="px-5 py-4 text-sm text-neutral-500 hidden md:table-cell">{z.carriers}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="mt-12 space-y-4 text-[16px] text-neutral-700 leading-relaxed">
          {Array.isArray(aiPage.notes) && aiPage.notes.length > 0 ? (
            aiPage.notes.map((n, i) => (
              <p key={i}>{n}</p>
            ))
          ) : (
            <>
              <h3 className="text-xl font-semibold text-neutral-900 mt-4" style={{ fontFamily: `"${fontHeading}", serif` }}>
                Pour les produits volumineux
              </h3>
              <p>
                Certains produits (fauteuils releveurs, lits médicaux, matelas XL) sont livrés par un transporteur dédié avec prise de rendez-vous. Vous êtes contacté 48h avant la livraison pour choisir un créneau horaire qui vous convient.
              </p>
              <p>
                Sur demande, un technicien peut aussi assurer l'installation, la mise en marche et une prise en main. Les frais sont communiqués lors de la commande.
              </p>

              <h3 className="text-xl font-semibold text-neutral-900 mt-8" style={{ fontFamily: `"${fontHeading}", serif` }}>
                Emballage & écologie
              </h3>
              <p>
                Nous utilisons des emballages recyclés et certifiés FSC. Nous minimisons les plastiques à usage unique : calage carton, ruban kraft, pas de polystyrène.
              </p>
            </>
          )}
        </div>
      </section>
    </StorefrontLayout>
  );
}

/* =========================================================
 * RETOURS — /retours
 * ========================================================= */
export function StorefrontRetours() {
  const { site, design, lang, setLang, availableLangs } = useSiteDesign();
  const fontHeading = design?.brand?.font_heading || "Fraunces";
  const primary = design?.brand?.primary_color || "#B84B31";
  const aiPage = design?.pages?.retours || {};

  const aiSteps = Array.isArray(aiPage.steps) ? aiPage.steps.filter((s) => s && s.title) : [];
  const steps = aiSteps.length
    ? aiSteps.map((s, i) => ({ n: i + 1, title: s.title, desc: s.description || "" }))
    : [
        { n: 1, title: "Contactez-nous", desc: "Par email ou téléphone. Pas de formulaire compliqué à remplir, on s'occupe de tout." },
        { n: 2, title: "Étiquette prépayée", desc: "Nous vous envoyons une étiquette de retour sous 24h. Imprimez-la ou demandez-nous une version papier." },
        { n: 3, title: "Déposez votre colis", desc: "En bureau de poste ou en relais colis. Le transport est à notre charge." },
        { n: 4, title: "Remboursement rapide", desc: "Sous 5 jours ouvrés après réception du colis, sur le moyen de paiement d'origine." },
      ];

  return (
    <StorefrontLayout lang={lang} setLang={setLang} availableLangs={availableLangs} site={site} design={design}>
      <SEOHead title={`Retours & remboursements · ${site?.name || ""}`} description="14 jours pour changer d'avis, retour gratuit, remboursement sous 5 jours." />
      <PageHero
        eyebrow="Retours & remboursements"
        title={aiPage.headline || "14 jours pour changer d'avis."}
        subtitle={aiPage.intro || "Si un produit ne vous convient pas, vous le retournez gratuitement. Nous vous remboursons intégralement dans les 5 jours."}
        design={design}
      />

      <section className="max-w-4xl mx-auto px-6 md:px-10 py-16 md:py-20" data-testid="page-retours">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5 mb-16">
          {[
            { Icon: ArrowCounterClockwise, title: "14 jours", desc: "Pour retourner un produit à compter de la réception." },
            { Icon: Truck, title: "Retour gratuit", desc: "Étiquette prépayée envoyée par email ou courrier." },
            { Icon: CreditCard, title: "Remboursé sous 5j", desc: "Sur votre moyen de paiement d'origine." },
          ].map(({ Icon, title, desc }, i) => (
            <div key={i} className="bg-white rounded-3xl p-6 border border-neutral-100 text-center">
              <div className="w-14 h-14 rounded-full mx-auto flex items-center justify-center mb-4" style={{ background: `${primary}14`, color: primary }}>
                <Icon size={28} weight="duotone" />
              </div>
              <div className="font-semibold mb-2 text-neutral-900">{title}</div>
              <div className="text-sm text-neutral-600 leading-relaxed">{desc}</div>
            </div>
          ))}
        </div>

        <h2 className="text-2xl md:text-3xl mb-8" style={{ fontFamily: `"${fontHeading}", serif` }}>
          Comment ça marche ?
        </h2>
        <ol className="space-y-5">
          {steps.map((s) => (
            <li key={s.n} className="flex gap-5 bg-white rounded-2xl p-6 border border-neutral-100">
              <div className="w-11 h-11 rounded-full flex items-center justify-center shrink-0 text-white font-semibold" style={{ background: primary }}>
                {s.n}
              </div>
              <div>
                <div className="font-semibold mb-1 text-neutral-900">{s.title}</div>
                <div className="text-sm text-neutral-600 leading-relaxed">{s.desc}</div>
              </div>
            </li>
          ))}
        </ol>

        <div className="mt-12 space-y-4 text-[16px] text-neutral-700 leading-relaxed">
          <h3 className="text-xl font-semibold text-neutral-900 mt-4" style={{ fontFamily: `"${fontHeading}", serif` }}>
            Garantie constructeur 2 ans
          </h3>
          <p>
            Au-delà des 14 jours de rétractation, tous nos produits bénéficient d'une garantie de 2 ans. En cas de défaut, nous reprenons le produit à nos frais et organisons le remplacement ou le remboursement selon le cas.
          </p>
          <h3 className="text-xl font-semibold text-neutral-900 mt-8" style={{ fontFamily: `"${fontHeading}", serif` }}>
            Produits non retournables
          </h3>
          <p>
            Pour des raisons d'hygiène, certains produits ne sont pas retournables s'ils ont été déballés : sous-vêtements techniques, dispositifs en contact direct avec la peau, produits d'incontinence. Ces restrictions sont clairement indiquées sur chaque fiche produit concernée.
          </p>
        </div>
      </section>
    </StorefrontLayout>
  );
}

/* =========================================================
 * FAQ page (kept as route target, minimal)
 * ========================================================= */
export function StorefrontFAQ() {
  const { site, design, lang, setLang, availableLangs } = useSiteDesign();
  const font = design?.brand?.font_heading || "Fraunces";
  const aiPage = design?.pages?.faq || {};
  const aiItems = Array.isArray(aiPage.items) ? aiPage.items.filter((f) => f && f.question) : [];
  const legacyFaq = design?.faq || [];
  // Normalize AI items into the existing {q, a} shape
  const items = aiItems.length
    ? aiItems.map((f) => ({ q: f.question, a: f.answer || "" }))
    : legacyFaq;
  return (
    <StorefrontLayout lang={lang} setLang={setLang} availableLangs={availableLangs} site={site} design={design}>
      <PageHero
        eyebrow="FAQ"
        title={aiPage.headline || "Questions fréquentes"}
        design={design}
      />
      <div className="max-w-3xl mx-auto px-6 py-16" data-testid="page-faq">
        {items.length === 0 ? (
          <div className="text-[#78716C]">Rendez-vous dans la FAQ sur la page d'accueil pour les réponses les plus consultées.</div>
        ) : (
          <div className="space-y-2">
            {items.map((it, i) => (
              <details key={i} className="bg-white rounded-xl border p-5 group" style={{ borderColor: "#E7E5E4" }}>
                <summary className="cursor-pointer font-medium list-none flex items-center justify-between">
                  <span>{pickText(it.q, lang)}</span>
                  <span className="text-xs opacity-50 group-open:rotate-180 transition">▼</span>
                </summary>
                <p className="text-sm mt-3" style={{ color: "#57534E" }}>{pickText(it.a, lang)}</p>
              </details>
            ))}
          </div>
        )}
      </div>
    </StorefrontLayout>
  );
}

/* =========================================================
 * Legal pages (CGV / Mentions / Confidentialité)
 * ========================================================= */
function LegalPage({ kind, title }) {
  const { siteId, site, design, lang, setLang, availableLangs } = useSiteDesign();
  // Bloc 2 — fetch the centralized template from the new /public/sites/{id}/legal/{slug}
  // endpoint. This includes mentions-légales, CGV, confidentialité, cookies,
  // retours et livraison avec les vraies infos KBIS Altiaro et le nom commercial du site.
  const [centralPage, setCentralPage] = useState(null);
  useEffect(() => {
    if (!siteId) return;
    let cancelled = false;
    axios
      .get(`${BACKEND_URL}/api/public/sites/${siteId}/legal/${kind}`)
      .then(({ data }) => { if (!cancelled) setCentralPage(data); })
      .catch(() => {});
    return () => { cancelled = true; };
  }, [siteId, kind]);

  // Legacy override : if the operator manually edited a page (`design.legal_pages.{kind}`),
  // it wins over the auto-generated central template (so concepteurs can still customize).
  const legacyPage = design?.legal_pages?.[kind];
  const md = (legacyPage && legacyPage.body_md)
    || (centralPage && centralPage.body_md)
    || null;
  // Last-resort fallback for /cookies (CNIL-compliant minimal text), used only
  // when neither the legacy nor the central endpoint returned content yet.
  const COOKIES_FALLBACK = `## Politique de cookies\n\nNous utilisons des cookies essentiels au fonctionnement, et avec votre consentement des cookies de mesure d'audience et marketing. Vous pouvez modifier vos choix à tout moment via la bannière.`;
  return (
    <StorefrontLayout lang={lang} setLang={setLang} availableLangs={availableLangs} site={site} design={design}>
      <PageHero eyebrow="Mentions légales" title={(centralPage && centralPage.title) || title} design={design} />
      <div className="max-w-3xl mx-auto px-6 py-16" data-testid={`page-${kind}`}>
        {md ? (
          <MarkdownLite md={md} />
        ) : kind === "cookies" ? (
          <MarkdownLite md={COOKIES_FALLBACK} />
        ) : (
          <div className="text-neutral-500">Cette page est en cours de génération. Réessayez dans quelques secondes.</div>
        )}
        {(centralPage && centralPage.updated) && (
          <p className="mt-12 text-xs text-neutral-400">Dernière mise à jour : {centralPage.updated}</p>
        )}
      </div>
    </StorefrontLayout>
  );
}

export const StorefrontCGV = () => <LegalPage kind="cgv" title="CGV — Conditions générales de vente" />;
export const StorefrontMentions = () => <LegalPage kind="mentions_legales" title="Mentions légales" />;
export const StorefrontConfidentialite = () => <LegalPage kind="confidentialite" title="Politique de confidentialité" />;
export const StorefrontCookies = () => <LegalPage kind="cookies" title="Politique de cookies" />;
export const StorefrontMediation = () => <LegalPage kind="mediation" title="Médiation de la consommation" />;
