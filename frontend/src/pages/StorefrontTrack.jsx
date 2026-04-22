import React, { useState } from "react";
import { useParams, Link } from "react-router-dom";
import axios from "axios";
import { MagnifyingGlass, ShieldCheck, Warning } from "@phosphor-icons/react";
import StorefrontLayout, { useSiteData } from "../components/StorefrontLayout";
import OrderTimeline from "../components/storefront/OrderTimeline";

const BACKEND = process.env.REACT_APP_BACKEND_URL;

const STATUS_LABEL = {
  pending_payment: "En attente de paiement",
  paid: "Payée",
  shipped: "Expédiée",
  delivered: "Livrée",
  cancelled: "Annulée",
  refunded: "Remboursée",
};

function formatDate(iso) {
  if (!iso) return "";
  try {
    return new Date(iso).toLocaleDateString("fr-FR", { day: "2-digit", month: "long", year: "numeric" });
  } catch { return ""; }
}

function money(v, currency = "EUR") {
  try { return new Intl.NumberFormat("fr-FR", { style: "currency", currency }).format(Number(v || 0)); }
  catch { return `${Number(v || 0).toFixed(2)} €`; }
}

export default function StorefrontTrack() {
  const { siteId } = useParams();
  const site = useSiteData(siteId);
  const [orderNumber, setOrderNumber] = useState("");
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [order, setOrder] = useState(null);
  const [error, setError] = useState("");

  const submit = async (e) => {
    e.preventDefault();
    if (!orderNumber.trim() || !email.trim()) return;
    setLoading(true);
    setError("");
    setOrder(null);
    try {
      const { data } = await axios.get(
        `${BACKEND}/api/public/sites/${siteId}/orders/${encodeURIComponent(orderNumber.trim())}`,
        { params: { email: email.trim() } }
      );
      setOrder(data);
    } catch (e) {
      setError(e?.response?.data?.detail || "Commande introuvable — vérifiez le numéro et l'email.");
    } finally {
      setLoading(false);
    }
  };

  if (!site) return null;
  const primary = site.design?.brand?.primary_color || "#B84B31";
  const headingFont = site.design?.brand?.font_heading || "Fraunces, serif";

  return (
    <StorefrontLayout site={site}>
      <div className="max-w-3xl mx-auto py-16 px-6">
        <div className="text-center mb-10">
          <div className="text-[11px] uppercase tracking-[0.2em] text-neutral-500 mb-3">Suivi de commande</div>
          <h1 className="text-4xl font-semibold text-neutral-900 mb-3" style={{ fontFamily: headingFont }}>
            Où en est ma commande ?
          </h1>
          <p className="text-sm text-neutral-600 max-w-lg mx-auto">
            Pas besoin de créer un compte — entrez votre numéro de commande et l'email utilisé lors de l'achat.
          </p>
        </div>

        {/* Form */}
        <form
          onSubmit={submit}
          className="bg-white border border-neutral-200 rounded-2xl p-6 md:p-8 shadow-sm"
          data-testid="track-form"
        >
          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <label className="block text-[11px] uppercase tracking-widest text-neutral-500 mb-2">Numéro de commande</label>
              <input
                type="text"
                value={orderNumber}
                onChange={(e) => setOrderNumber(e.target.value)}
                placeholder="ex: ALT-2026-04120"
                required
                data-testid="track-order-number"
                className="w-full h-12 px-4 rounded-xl border border-neutral-200 focus:outline-none focus:ring-2 focus:ring-neutral-300 text-sm"
              />
            </div>
            <div>
              <label className="block text-[11px] uppercase tracking-widest text-neutral-500 mb-2">Email de commande</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="marie@exemple.fr"
                required
                data-testid="track-email"
                className="w-full h-12 px-4 rounded-xl border border-neutral-200 focus:outline-none focus:ring-2 focus:ring-neutral-300 text-sm"
              />
            </div>
          </div>
          <button
            type="submit"
            disabled={loading || !orderNumber.trim() || !email.trim()}
            data-testid="track-submit"
            className="mt-5 h-12 px-6 rounded-full text-white text-sm font-medium flex items-center justify-center gap-2 transition hover:opacity-90 disabled:opacity-60 w-full md:w-auto"
            style={{ background: primary }}
          >
            <MagnifyingGlass size={16} weight="bold" />
            {loading ? "Recherche…" : "Suivre ma commande"}
          </button>
          <div className="mt-4 flex items-center gap-2 text-xs text-neutral-500">
            <ShieldCheck size={14} className="flex-shrink-0" />
            Vos informations ne sont utilisées que pour vérifier votre commande.
          </div>
        </form>

        {/* Error */}
        {error && (
          <div
            className="mt-6 rounded-2xl bg-rose-50 border border-rose-200 p-5 flex items-start gap-3"
            data-testid="track-error"
          >
            <Warning size={20} weight="fill" className="text-rose-600 flex-shrink-0 mt-0.5" />
            <div className="text-sm text-rose-900">{error}</div>
          </div>
        )}

        {/* Result */}
        {order && (
          <div className="mt-8 space-y-6" data-testid="track-result">
            <div className="bg-white border border-neutral-200 rounded-2xl p-6">
              <div className="flex items-start justify-between gap-3 flex-wrap mb-5">
                <div>
                  <div className="text-[11px] uppercase tracking-[0.2em] text-neutral-500 mb-1">Commande</div>
                  <div className="text-2xl font-semibold text-neutral-900" style={{ fontFamily: headingFont }}>
                    {order.order_number}
                  </div>
                  <div className="text-xs text-neutral-500 mt-1">
                    Passée le {formatDate(order.created_at)} · {money(order.total, order.currency || "EUR")}
                  </div>
                </div>
                <span className="text-xs font-medium px-3 py-1 rounded-full bg-neutral-100 text-neutral-800">
                  {STATUS_LABEL[order.status] || order.status}
                </span>
              </div>
              <OrderTimeline order={order} accent={primary} />
            </div>

            <div className="bg-[#FDFBF7] border border-neutral-200 rounded-2xl p-5">
              <div className="text-sm text-neutral-700 leading-relaxed">
                <strong className="text-neutral-900">Vous souhaitez accéder à tous les détails</strong> (articles, factures, adresses) ?{" "}
                <Link to={`/shop/${siteId}/account/login`} className="underline underline-offset-2" style={{ color: primary }}>
                  Connectez-vous à votre compte
                </Link>{" "}
                ou{" "}
                <Link to={`/shop/${siteId}/account/register`} className="underline underline-offset-2" style={{ color: primary }}>
                  créez-en un en 30 secondes
                </Link>
                .
              </div>
            </div>
          </div>
        )}
      </div>
    </StorefrontLayout>
  );
}
