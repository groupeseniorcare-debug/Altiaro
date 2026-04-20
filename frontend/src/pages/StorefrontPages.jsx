import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import axios from "axios";
import StorefrontLayout, { fetchPublicSite } from "../components/StorefrontLayout";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

function useSiteDesign() {
  const { siteId } = useParams();
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
  return { siteId, site, design, lang, setLang };
}

function pickText(node, lang) {
  if (!node) return null;
  if (typeof node === "string") return node;
  return node[lang] || node.fr || Object.values(node)[0] || null;
}

function MarkdownLite({ md }) {
  if (!md) return null;
  // Ultra-simple markdown: # → h2, ## → h3, ** → bold, paragraphs
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
    .join("")
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  return <div className="prose max-w-none text-[15px]" dangerouslySetInnerHTML={{ __html: html }} />;
}

function LegalShell({ title, children, testId }) {
  const { site, design, lang, setLang } = useSiteDesign();
  const font = design?.brand?.font_heading || "Fraunces";
  return (
    <StorefrontLayout lang={lang} setLang={setLang} site={site} design={design}>
      <div className="max-w-3xl mx-auto px-6 py-16" data-testid={testId}>
        <h1 className="text-4xl font-semibold mb-8" style={{ fontFamily: `"${font}", serif` }}>
          {title}
        </h1>
        {children}
      </div>
    </StorefrontLayout>
  );
}

/* ---------- About ---------- */
export function StorefrontAbout() {
  const { site, design, lang, setLang } = useSiteDesign();
  const font = design?.brand?.font_heading || "Fraunces";
  const headline = pickText(design?.about?.headline, lang);
  const paragraphs = (design?.about?.paragraphs || []).map((p) => pickText(p, lang)).filter(Boolean);

  if (!design) {
    return (
      <StorefrontLayout lang={lang} setLang={setLang} site={site} design={design}>
        <div className="max-w-3xl mx-auto px-6 py-20 text-center text-[#78716C]">
          Cette page n'est pas encore disponible.
        </div>
      </StorefrontLayout>
    );
  }

  return (
    <StorefrontLayout lang={lang} setLang={setLang} site={site} design={design}>
      <div className="max-w-3xl mx-auto px-6 py-16" data-testid="page-about">
        <h1 className="text-4xl md:text-5xl font-semibold mb-6" style={{ fontFamily: `"${font}", serif` }}>
          {headline || "À propos"}
        </h1>
        <div className="space-y-5 text-[16px] leading-relaxed" style={{ color: "#44403C" }}>
          {paragraphs.map((p, i) => (
            <p key={i}>{p}</p>
          ))}
        </div>
      </div>
    </StorefrontLayout>
  );
}

/* ---------- FAQ ---------- */
export function StorefrontFAQ() {
  const { site, design, lang, setLang } = useSiteDesign();
  const font = design?.brand?.font_heading || "Fraunces";
  const faq = design?.faq || [];
  return (
    <StorefrontLayout lang={lang} setLang={setLang} site={site} design={design}>
      <div className="max-w-3xl mx-auto px-6 py-16" data-testid="page-faq">
        <h1 className="text-4xl md:text-5xl font-semibold mb-8" style={{ fontFamily: `"${font}", serif` }}>
          Questions fréquentes
        </h1>
        {faq.length === 0 ? (
          <div className="text-[#78716C]">Pas encore de FAQ disponible.</div>
        ) : (
          <div className="space-y-2">
            {faq.map((it, i) => (
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

/* ---------- Contact ---------- */
export function StorefrontContact() {
  const { siteId, site, design, lang, setLang } = useSiteDesign();
  const font = design?.brand?.font_heading || "Fraunces";
  const primary = design?.brand?.primary_color || "#B84B31";
  const [form, setForm] = useState({ name: "", email: "", phone: "", subject: "", message: "" });
  const [sent, setSent] = useState(false);
  const [sending, setSending] = useState(false);
  const [err, setErr] = useState("");
  const contact = design?.contact || {};

  const submit = async (e) => {
    e.preventDefault();
    setErr("");
    setSending(true);
    try {
      await axios.post(`${BACKEND_URL}/api/public/sites/${siteId}/contact`, form);
      setSent(true);
    } catch (ex) {
      setErr(ex?.response?.data?.detail || "Erreur lors de l'envoi. Réessaye.");
    }
    setSending(false);
  };

  return (
    <StorefrontLayout lang={lang} setLang={setLang} site={site} design={design}>
      <div className="max-w-3xl mx-auto px-6 py-16 grid md:grid-cols-2 gap-10" data-testid="page-contact">
        <div>
          <h1 className="text-4xl font-semibold mb-4" style={{ fontFamily: `"${font}", serif` }}>
            {pickText(contact.headline, lang) || "Nous contacter"}
          </h1>
          <p className="text-[15px] leading-relaxed mb-6" style={{ color: "#57534E" }}>
            {pickText(contact.intro, lang) || "Notre équipe est à votre écoute."}
          </p>
          {contact.support_email && (
            <div className="text-sm mb-2">
              <span className="text-[#78716C]">Email : </span>
              <a href={`mailto:${contact.support_email}`} className="font-medium" style={{ color: primary }}>
                {contact.support_email}
              </a>
            </div>
          )}
          {contact.support_phone && (
            <div className="text-sm mb-2">
              <span className="text-[#78716C]">Téléphone : </span>
              <span className="font-medium">{contact.support_phone}</span>
            </div>
          )}
          {contact.support_hours && (
            <div className="text-sm text-[#78716C]">
              Horaires : {pickText(contact.support_hours, lang)}
            </div>
          )}
        </div>
        <div>
          {sent ? (
            <div className="bg-white rounded-2xl border p-6 text-center" style={{ borderColor: "#E7E5E4" }} data-testid="contact-sent">
              <div className="text-lg font-semibold mb-2">Merci !</div>
              <div className="text-sm" style={{ color: "#57534E" }}>
                Votre message a bien été reçu. Nous vous répondrons sous 48h.
              </div>
            </div>
          ) : (
            <form onSubmit={submit} className="space-y-3" data-testid="contact-form">
              <Input testId="contact-name" label="Nom *" value={form.name} onChange={(v) => setForm({ ...form, name: v })} required />
              <Input testId="contact-email" type="email" label="Email *" value={form.email} onChange={(v) => setForm({ ...form, email: v })} required />
              <Input testId="contact-phone" label="Téléphone" value={form.phone} onChange={(v) => setForm({ ...form, phone: v })} />
              <Input testId="contact-subject" label="Sujet" value={form.subject} onChange={(v) => setForm({ ...form, subject: v })} />
              <div>
                <label className="block text-[13px] font-medium mb-1">Message *</label>
                <textarea
                  value={form.message}
                  onChange={(e) => setForm({ ...form, message: e.target.value })}
                  rows={5}
                  required
                  data-testid="contact-message"
                  className="w-full px-4 py-3 rounded-xl border outline-none"
                  style={{ borderColor: "#E7E5E4" }}
                />
              </div>
              {err && <div className="text-sm text-[#BE123C]">{err}</div>}
              <button
                type="submit"
                disabled={sending}
                data-testid="contact-submit"
                className="h-11 px-5 rounded-xl text-white font-medium disabled:opacity-60"
                style={{ background: primary }}
              >
                {sending ? "Envoi…" : "Envoyer"}
              </button>
            </form>
          )}
        </div>
      </div>
    </StorefrontLayout>
  );
}

function Input({ label, value, onChange, type = "text", required, testId }) {
  return (
    <div>
      <label className="block text-[13px] font-medium mb-1">{label}</label>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        required={required}
        data-testid={testId}
        className="w-full h-11 px-4 rounded-xl border outline-none"
        style={{ borderColor: "#E7E5E4" }}
      />
    </div>
  );
}

/* ---------- Legal pages (CGV / Mentions / Confidentialité) ---------- */
function LegalPage({ kind }) {
  const { site, design, lang, setLang } = useSiteDesign();
  const page = design?.legal_pages?.[kind];
  const font = design?.brand?.font_heading || "Fraunces";
  return (
    <StorefrontLayout lang={lang} setLang={setLang} site={site} design={design}>
      <div className="max-w-3xl mx-auto px-6 py-16" data-testid={`page-${kind}`}>
        {page ? (
          <div style={{ fontFamily: `"${font}", serif` }}>
            <MarkdownLite md={page.body_md} />
          </div>
        ) : (
          <div className="text-[#78716C]">Cette page n'est pas encore générée.</div>
        )}
      </div>
    </StorefrontLayout>
  );
}

export const StorefrontCGV = () => <LegalPage kind="cgv" />;
export const StorefrontMentions = () => <LegalPage kind="mentions_legales" />;
export const StorefrontConfidentialite = () => <LegalPage kind="confidentialite" />;
