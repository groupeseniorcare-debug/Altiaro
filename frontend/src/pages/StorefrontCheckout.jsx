import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import { ShieldCheck } from "@phosphor-icons/react";
import StorefrontLayout from "../components/StorefrontLayout";
import { t, COUNTRY_OPTIONS, countryLabel } from "../lib/i18n";
import {
  readCart,
  cartTotals,
  clearCart,
} from "../lib/cart";
import {
  BACKEND_URL,
  useSiteAndLang,
  formatPrice,
} from "../components/storefront/storefrontUtils";
import { Card, Field, Row } from "../components/storefront/storefrontFormUtils";

/* =========================================================
 * CHECKOUT — Phase 4 : extrait de `pages/Storefront.jsx`
 * (fix latent : `ShieldCheck` was used but not imported)
 * ========================================================= */
export default function StorefrontCheckout() {
  const { siteId, site, design, lang, setLang } = useSiteAndLang();
  const navigate = useNavigate();
  const [items] = useState(() => readCart(siteId));
  const [form, setForm] = useState({
    name: "",
    email: "",
    phone: "",
    line1: "",
    line2: "",
    city: "",
    postal_code: "",
    country_code: "FR",
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (items.length === 0) {
      navigate(`/shop/${siteId}/cart`);
    }
  }, [items.length, navigate, siteId]);

  const totals = cartTotals(items);
  const change = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      try { window.altiaroTrack?.beginCheckout?.(items, totals.total, lang); } catch (_) {}
      const payload = {
        items: items.map((i) => ({
          product_id: i.product_id,
          name: i.name,
          price: i.price,
          quantity: i.quantity,
          currency: i.currency || "EUR",
          image: i.image,
          upsell_discount_pct: i.upsell_discount_pct || 0,
        })),
        customer: { name: form.name, email: form.email, phone: form.phone },
        shipping_address: {
          line1: form.line1,
          line2: form.line2,
          city: form.city,
          postal_code: form.postal_code,
          country: countryLabel(form.country_code, "fr"),
          country_code: form.country_code,
        },
        language: lang,
      };
      const { data } = await axios.post(
        `${BACKEND_URL}/api/public/sites/${siteId}/orders`,
        payload
      );
      clearCart(siteId);
      try {
        const payRes = await axios.post(
          `${BACKEND_URL}/api/public/payments/create`,
          { order_number: data.order_number, site_id: siteId }
        );
        if (payRes.data?.checkout_url) {
          window.location.href = payRes.data.checkout_url;
          return;
        }
      } catch (payErr) {
        console.error("Mollie payment creation failed", payErr);
      }
      navigate(`/shop/${siteId}/confirmation?order=${data.order_number}`);
    } catch (err) {
      setError(err.response?.data?.detail || "Erreur lors de la commande");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <StorefrontLayout lang={lang} setLang={setLang} site={site} design={design}>
      <div className="max-w-5xl mx-auto px-6 py-12" data-testid="storefront-checkout">
        <h1 className="font-heading text-4xl font-semibold text-[#1C1917] mb-8">{t(lang, "checkout")}</h1>

        <form
          onSubmit={submit}
          className="grid grid-cols-1 lg:grid-cols-[1fr_380px] gap-8"
          data-testid="checkout-form"
        >
          <div className="space-y-6">
            <Card title={t(lang, "your_details")}>
              <Field label={t(lang, "full_name") + " *"} name="name" required onChange={change} value={form.name} />
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Field label={t(lang, "email") + " *"} name="email" type="email" required onChange={change} value={form.email} />
                <Field label={t(lang, "phone")} name="phone" onChange={change} value={form.phone} />
              </div>
            </Card>

            <Card title={t(lang, "shipping_address")}>
              <Field label={t(lang, "address_line1") + " *"} name="line1" required onChange={change} value={form.line1} />
              <Field label={t(lang, "address_line2")} name="line2" onChange={change} value={form.line2} />
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Field label={t(lang, "postal_code") + " *"} name="postal_code" required onChange={change} value={form.postal_code} />
                <Field label={t(lang, "city") + " *"} name="city" required onChange={change} value={form.city} />
              </div>
              <div>
                <label className="block text-[13px] font-medium text-[#1C1917] mb-1.5">
                  {t(lang, "country")} *
                </label>
                <select
                  name="country_code"
                  value={form.country_code}
                  onChange={change}
                  data-testid="country-select"
                  className="w-full h-12 px-4 rounded-xl border border-[#E7E5E4] bg-white focus:ring-2 focus:ring-[#B84B31]/30 focus:border-[#B84B31] outline-none"
                >
                  {COUNTRY_OPTIONS.map((c) => (
                    <option key={c.code} value={c.code}>
                      {countryLabel(c.code, lang)}
                    </option>
                  ))}
                </select>
              </div>
            </Card>

            {error && (
              <div className="p-3.5 rounded-lg bg-[#FFE4E6] text-[#BE123C] text-sm" data-testid="checkout-error">
                {error}
              </div>
            )}
          </div>

          <div className="bg-white rounded-2xl border border-[#E7E5E4] p-6 h-fit lg:sticky lg:top-24">
            <div className="font-heading text-lg font-semibold text-[#1C1917] mb-4">
              {items.reduce((a, b) => a + b.quantity, 0)} article(s)
            </div>
            <div className="space-y-2 max-h-60 overflow-y-auto mb-4">
              {items.map((it) => (
                <div key={it.product_id} className="flex justify-between text-sm">
                  <span className="text-[#57534E] truncate pr-2">
                    {it.quantity} × {it.name}
                  </span>
                  <span className="font-medium text-[#1C1917] whitespace-nowrap">
                    {formatPrice(it.price * it.quantity, "EUR", lang)}
                  </span>
                </div>
              ))}
            </div>
            <div className="h-px bg-[#E7E5E4] my-3" />
            <Row label={t(lang, "subtotal")} value={formatPrice(totals.subtotal, "EUR", lang)} />
            <Row
              label={t(lang, "shipping")}
              value={
                totals.shipping_fee === 0 ? (
                  <span className="text-[#047857] font-medium">{t(lang, "free")}</span>
                ) : (
                  formatPrice(totals.shipping_fee, "EUR", lang)
                )
              }
            />
            <div className="h-px bg-[#E7E5E4] my-3" />
            <Row
              label={<span className="font-medium">{t(lang, "total")}</span>}
              value={
                <span className="font-heading text-xl font-semibold">
                  {formatPrice(totals.total, "EUR", lang)}
                </span>
              }
            />

            <button
              type="submit"
              disabled={submitting}
              data-testid="place-order"
              className="w-full mt-5 h-12 rounded-full bg-[#B84B31] hover:bg-[#993D26] text-white font-medium text-[15px] transition active:scale-[0.98] disabled:opacity-60"
            >
              {submitting ? "…" : t(lang, "place_order")}
            </button>

            <div className="mt-3 flex items-center justify-center gap-1.5 text-[11px] text-[#78716C]">
              <ShieldCheck size={12} weight="bold" /> {t(lang, "secure_checkout")}
            </div>
          </div>
        </form>
      </div>
    </StorefrontLayout>
  );
}
