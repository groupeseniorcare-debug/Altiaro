import React, { useEffect, useState, useCallback } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import axios from "axios";
import {
  ArrowLeft, MapPin, Package, Star, ChatText, ArrowRight, Clock,
} from "@phosphor-icons/react";
import StorefrontLayout from "../components/StorefrontLayout";
import { useSiteAndLang } from "../components/storefront/storefrontUtils";
import OrderTimeline from "../components/storefront/OrderTimeline";
import { getToken, authHeaders } from "../lib/customerAuth";
import { pickLang } from "../lib/i18n";

const BACKEND = "";

const STATUS_BADGE = {
  pending_payment: { label: "En attente de paiement", color: "bg-amber-100 text-amber-800" },
  paid:            { label: "Payée",                  color: "bg-blue-100 text-blue-800" },
  shipped:         { label: "Expédiée",               color: "bg-indigo-100 text-indigo-800" },
  delivered:       { label: "Livrée",                 color: "bg-emerald-100 text-emerald-800" },
  cancelled:       { label: "Annulée",                color: "bg-neutral-100 text-neutral-600" },
  refunded:        { label: "Remboursée",             color: "bg-neutral-100 text-neutral-600" },
};

function formatDate(iso) {
  if (!iso) return "";
  try {
    return new Date(iso).toLocaleDateString("fr-FR", { day: "2-digit", month: "long", year: "numeric" });
  } catch { return ""; }
}

function money(v, currency = "EUR") {
  try {
    return new Intl.NumberFormat("fr-FR", { style: "currency", currency }).format(Number(v || 0));
  } catch {
    return `${Number(v || 0).toFixed(2)} €`;
  }
}

export default function StorefrontOrderDetail() {
  const { orderId } = useParams();
  const nav = useNavigate();
  const { siteId, site, design, lang, setLang, availableLangs } = useSiteAndLang();
  const [order, setOrder] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    if (!getToken(siteId)) {
      nav(`/shop/${siteId}/account/login`);
      return;
    }
    setLoading(true);
    try {
      const { data } = await axios.get(
        `${BACKEND}/api/public/sites/${siteId}/customers/orders/${orderId}`,
        { headers: authHeaders(siteId) }
      );
      setOrder(data);
    } catch (e) {
      setError(e?.response?.data?.detail || "Commande introuvable");
    } finally {
      setLoading(false);
    }
  }, [siteId, orderId, nav]);

  useEffect(() => { load(); }, [load]);

  if (!site) return null;

  const primary = design?.brand?.primary_color || site.design?.brand?.primary_color || "#B84B31";
  const headingFont = design?.brand?.font_heading || site.design?.brand?.font_heading || "Fraunces, serif";

  return (
    <StorefrontLayout site={site} design={design} lang={lang} setLang={setLang} availableLangs={availableLangs}>
      <div className="max-w-4xl mx-auto py-12 px-6">
        <Link
          to={`/shop/${siteId}/account`}
          className="inline-flex items-center gap-2 text-sm text-neutral-600 hover:text-neutral-900 mb-6"
          data-testid="back-to-account"
        >
          <ArrowLeft size={14} /> Mes commandes
        </Link>

        {loading ? (
          <div className="py-20 text-center text-neutral-500">Chargement de votre commande…</div>
        ) : error ? (
          <div className="bg-rose-50 border border-rose-200 text-rose-900 rounded-2xl p-6 text-sm" data-testid="order-error">
            {error}
          </div>
        ) : order ? (
          <OrderView order={order} primary={primary} headingFont={headingFont} siteId={siteId} />
        ) : null}
      </div>
    </StorefrontLayout>
  );
}

function OrderView({ order, primary, headingFont, siteId }) {
  const badge = STATUS_BADGE[order.status] || { label: order.status, color: "bg-neutral-100 text-neutral-700" };
  const items = order.items || [];
  const addr = order.shipping_address || {};
  const currency = order.currency || "EUR";
  const invitations = order.review_invitations || [];
  const isDelivered = order.status === "delivered";

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white border border-neutral-200 rounded-2xl p-6" data-testid="order-header">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <div className="text-[11px] uppercase tracking-[0.2em] text-neutral-500 mb-1">Commande</div>
            <h1 className="text-3xl font-semibold text-neutral-900" style={{ fontFamily: headingFont }}>
              {order.order_number}
            </h1>
            <div className="text-sm text-neutral-500 mt-1 flex items-center gap-2">
              <Clock size={12} /> Passée le {formatDate(order.created_at)}
            </div>
          </div>
          <span className={`text-xs font-medium px-3 py-1 rounded-full ${badge.color}`} data-testid="order-status-badge">
            {badge.label}
          </span>
        </div>
      </div>

      {/* Timeline */}
      <section className="bg-white border border-neutral-200 rounded-2xl p-6">
        <div className="text-[11px] uppercase tracking-[0.2em] text-neutral-500 mb-5">Suivi de livraison</div>
        <OrderTimeline order={order} accent={primary} />
      </section>

      {/* Review invitations (when delivered) */}
      {isDelivered && invitations.length > 0 && (
        <section
          className="rounded-2xl p-6 border"
          style={{ background: primary + "0F", borderColor: primary + "33" }}
          data-testid="review-invitations"
        >
          <div className="flex items-start gap-3">
            <Star size={22} weight="fill" style={{ color: primary }} className="flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <div className="font-semibold text-neutral-900 mb-1">Partagez votre expérience</div>
              <div className="text-sm text-neutral-600 mb-4">
                Votre avis aide d'autres familles à faire le bon choix. 1 minute suffit.
              </div>
              <div className="flex flex-wrap gap-2">
                {invitations.map((inv) => (
                  <Link
                    key={inv.token}
                    to={`/shop/${siteId}/review/${inv.token}`}
                    data-testid={`review-link-${inv.product_id}`}
                    className="inline-flex items-center gap-2 h-10 px-4 rounded-full text-white text-sm font-medium transition hover:opacity-90"
                    style={{ background: primary }}
                  >
                    Laisser mon avis <ArrowRight size={14} weight="bold" />
                  </Link>
                ))}
              </div>
            </div>
          </div>
        </section>
      )}

      {/* Items */}
      <section className="bg-white border border-neutral-200 rounded-2xl p-6" data-testid="order-items">
        <div className="text-[11px] uppercase tracking-[0.2em] text-neutral-500 mb-4 flex items-center gap-2">
          <Package size={12} weight="bold" /> Articles commandés ({items.length})
        </div>
        <div className="divide-y divide-neutral-100">
          {items.map((it, i) => (
            <div key={i} className="flex items-center gap-4 py-4 first:pt-0 last:pb-0" data-testid={`order-item-${i}`}>
              <div className="w-16 h-16 rounded-xl bg-neutral-100 overflow-hidden flex-shrink-0">
                {it.product_image ? (
                  <img src={it.product_image} alt="" className="w-full h-full object-cover" loading="lazy" />
                ) : null}
              </div>
              <div className="flex-1 min-w-0">
                <div className="font-medium text-neutral-900 text-sm truncate">
                  {pickLang(it.product_name_current, "fr") || pickLang(it.name, "fr") || "—"}
                </div>
                <div className="text-xs text-neutral-500 mt-0.5">
                  Quantité : {it.quantity || 1} · {money(it.unit_price || it.price || 0, currency)} /unité
                </div>
              </div>
              <div className="text-sm font-semibold tabular-nums text-neutral-900">
                {money((it.unit_price || it.price || 0) * (it.quantity || 1), currency)}
              </div>
            </div>
          ))}
        </div>

        {/* Totals */}
        <div className="mt-5 pt-5 border-t border-neutral-100 space-y-1.5 text-sm">
          {typeof order.subtotal === "number" && (
            <Row label="Sous-total" value={money(order.subtotal, currency)} />
          )}
          {typeof order.shipping_cost === "number" && (
            <Row label="Livraison" value={order.shipping_cost ? money(order.shipping_cost, currency) : "Offerte"} />
          )}
          {typeof order.tax === "number" && order.tax > 0 && (
            <Row label="TVA" value={money(order.tax, currency)} />
          )}
          {typeof order.discount === "number" && order.discount > 0 && (
            <Row label="Remise" value={`− ${money(order.discount, currency)}`} />
          )}
          <div className="flex justify-between items-baseline pt-2 border-t border-neutral-100 mt-2">
            <span className="font-semibold text-neutral-900">Total</span>
            <span className="text-xl font-semibold tabular-nums text-neutral-900" style={{ fontFamily: headingFont }}>
              {money(order.total, currency)}
            </span>
          </div>
        </div>
      </section>

      {/* Shipping address */}
      {(addr.line1 || addr.address_line1) && (
        <section className="bg-white border border-neutral-200 rounded-2xl p-6" data-testid="order-shipping-address">
          <div className="text-[11px] uppercase tracking-[0.2em] text-neutral-500 mb-3 flex items-center gap-2">
            <MapPin size={12} weight="bold" /> Adresse de livraison
          </div>
          <div className="text-sm text-neutral-800 leading-relaxed">
            <div className="font-medium">{addr.full_name || `${addr.first_name || ""} ${addr.last_name || ""}`.trim() || order.customer?.name}</div>
            <div>{addr.line1 || addr.address_line1}</div>
            {(addr.line2 || addr.address_line2) && <div>{addr.line2 || addr.address_line2}</div>}
            <div>{[addr.postal_code, addr.city].filter(Boolean).join(" ")}</div>
            <div>{addr.country}</div>
            {addr.phone && <div className="text-neutral-500 mt-1 text-xs">Tél. {addr.phone}</div>}
          </div>
        </section>
      )}

      {/* Help box */}
      <div className="bg-[#FDFBF7] border border-neutral-200 rounded-2xl p-5 flex items-start gap-3">
        <ChatText size={18} weight="duotone" className="text-neutral-500 flex-shrink-0 mt-0.5" />
        <div className="text-sm">
          <div className="font-medium text-neutral-900 mb-1">Besoin d'aide sur cette commande ?</div>
          <div className="text-neutral-600">
            Notre équipe répond sous 24 h ouvrées.{" "}
            <Link to={`/shop/${siteId}/contact`} className="underline underline-offset-2" style={{ color: primary }}>
              Contacter le service client
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}

function Row({ label, value }) {
  return (
    <div className="flex justify-between">
      <span className="text-neutral-500">{label}</span>
      <span className="text-neutral-900 tabular-nums">{value}</span>
    </div>
  );
}
