import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import axios from "axios";
import { Star, CheckCircle, Warning } from "@phosphor-icons/react";
import StorefrontLayout, { fetchPublicSite } from "../components/StorefrontLayout";
import SEOHead from "../components/SEOHead";
import { useShopSiteId } from "../lib/shopSiteId";

const BACKEND_URL = "";

export default function StorefrontReview() {
  const siteId = useShopSiteId(); const { token } = useParams();
  const [site, setSite] = useState(null);
  const [design, setDesign] = useState(null);
  const [invitation, setInvitation] = useState(null);
  const [err, setErr] = useState("");
  const [form, setForm] = useState({ rating: 0, title: "", body: "" });
  const [submitted, setSubmitted] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [lang, setLang] = useState("fr");

  useEffect(() => {
    fetchPublicSite(siteId).then(setSite).catch(() => setSite({ error: true }));
    axios.get(`${BACKEND_URL}/api/public/sites/${siteId}/design`)
      .then(({ data }) => setDesign(data?.published ? data.design : null))
      .catch(() => setDesign(null));
    axios.get(`${BACKEND_URL}/api/public/reviews/invitation/${token}`)
      .then(({ data }) => setInvitation(data))
      .catch((e) => setErr(e?.response?.data?.detail || "Lien invalide."));
  }, [siteId, token]);

  const submit = async (e) => {
    e.preventDefault();
    if (!form.rating || !form.title.trim() || !form.body.trim()) return;
    setSubmitting(true);
    try {
      await axios.post(`${BACKEND_URL}/api/public/reviews/submit/${token}`, form);
      setSubmitted(true);
    } catch (ex) {
      setErr(ex?.response?.data?.detail || "Erreur à l'envoi. Réessayez.");
    }
    setSubmitting(false);
  };

  const primary = design?.brand?.primary_color || "#B84B31";
  const fontHeading = design?.brand?.font_heading || "Fraunces";

  return (
    <StorefrontLayout lang={lang} setLang={setLang} availableLangs={availableLangs} site={site} design={design}>
      <SEOHead title={`Laisser un avis · ${site?.name || ""}`} noindex robots="noindex, nofollow" />
      <section className="max-w-2xl mx-auto px-6 md:px-10 py-16 md:py-24" data-testid="review-page">
        {err ? (
          <div className="bg-rose-50 border border-rose-200 rounded-2xl p-8 text-center">
            <Warning size={40} weight="duotone" className="mx-auto mb-3 text-rose-500" />
            <h1 className="text-xl font-semibold text-rose-900 mb-2">Lien indisponible</h1>
            <p className="text-sm text-rose-700">{err}</p>
          </div>
        ) : submitted ? (
          <div className="bg-emerald-50 border border-emerald-200 rounded-3xl p-10 text-center" data-testid="review-submitted">
            <CheckCircle size={56} weight="duotone" className="mx-auto mb-4 text-emerald-600" />
            <h1 className="text-2xl md:text-3xl font-semibold mb-3" style={{ fontFamily: `${fontHeading}, serif` }}>
              Merci pour votre avis 🙏
            </h1>
            <p className="text-neutral-600 mb-6">
              Votre retour aidera d'autres familles à faire le bon choix. Nous lisons chaque avis attentivement.
            </p>
            <a href={`/shop/${siteId}`} className="inline-flex items-center gap-2 h-12 px-6 rounded-full text-white font-medium" style={{ background: primary }}>
              Retour à la boutique
            </a>
          </div>
        ) : invitation ? (
          <>
            <div className="text-[11px] uppercase tracking-[0.2em] text-neutral-500 mb-3">Laisser un avis vérifié</div>
            <h1 className="text-3xl md:text-4xl leading-tight text-neutral-900 mb-3" style={{ fontFamily: `${fontHeading}, serif` }}>
              Dites-nous ce que vous en avez pensé
            </h1>
            <p className="text-neutral-600 mb-8">
              Bonjour {invitation.customer_name || ""}, merci de partager votre expérience avec « {invitation.product?.name?.fr || invitation.product?.name} ».
            </p>
            <form onSubmit={submit} className="bg-white rounded-3xl border border-neutral-200 p-6 md:p-8 space-y-5">
              <div>
                <label className="block text-sm font-medium mb-2 text-neutral-900">Votre note *</label>
                <div className="flex gap-2" data-testid="review-stars">
                  {[1, 2, 3, 4, 5].map((n) => (
                    <button
                      key={n}
                      type="button"
                      onClick={() => setForm({ ...form, rating: n })}
                      data-testid={`star-${n}`}
                      className="transition hover:scale-110"
                    >
                      <Star
                        size={32}
                        weight={n <= form.rating ? "fill" : "regular"}
                        style={{ color: n <= form.rating ? "#F59E0B" : "#D6D3D1" }}
                      />
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium mb-2 text-neutral-900">Titre *</label>
                <input
                  value={form.title}
                  onChange={(e) => setForm({ ...form, title: e.target.value })}
                  required
                  maxLength={140}
                  placeholder="Résumez en une phrase"
                  data-testid="review-title"
                  className="w-full h-12 px-4 rounded-xl border border-neutral-200 focus:outline-none focus:ring-2 focus:ring-neutral-300"
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-2 text-neutral-900">Votre avis *</label>
                <textarea
                  value={form.body}
                  onChange={(e) => setForm({ ...form, body: e.target.value })}
                  required
                  rows={6}
                  maxLength={2000}
                  placeholder="Expliquez votre expérience : utilisation, confort, service, livraison…"
                  data-testid="review-body"
                  className="w-full px-4 py-3 rounded-xl border border-neutral-200 focus:outline-none focus:ring-2 focus:ring-neutral-300"
                />
              </div>

              <button
                type="submit"
                disabled={submitting || !form.rating || !form.title || !form.body}
                data-testid="review-submit"
                className="w-full h-12 rounded-full text-white font-medium disabled:opacity-50"
                style={{ background: primary }}
              >
                {submitting ? "Envoi…" : "Publier mon avis"}
              </button>
            </form>
          </>
        ) : (
          <div className="text-center text-neutral-500 py-20">Chargement…</div>
        )}
      </section>
    </StorefrontLayout>
  );
}
