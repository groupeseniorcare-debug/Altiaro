import React, { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import axios from "axios";
import { CheckCircle } from "@phosphor-icons/react";
import StorefrontLayout from "../components/StorefrontLayout";
import { t } from "../lib/i18n";
import {
  BACKEND_URL,
  useSiteAndLang,
  formatPrice,
} from "../components/storefront/storefrontUtils";
import UpsellsRecommendations from "../components/storefront/UpsellsRecommendations";

/* =========================================================
 * CONFIRMATION — Phase 4 : extrait de `pages/Storefront.jsx`
 * (fix latent : `UpsellsRecommendations` was used but not imported)
 * ========================================================= */
export default function StorefrontConfirmation() {
  const { siteId, site, design, lang, setLang } = useSiteAndLang();
  const [search] = useSearchParams();
  const orderNumber = search.get("order");
  const isSuccessPage = window.location.pathname.includes("/checkout/success");
  const [order, setOrder] = useState(null);

  useEffect(() => {
    if (!orderNumber) return;
    let cancelled = false;
    let attempts = 0;
    let fired = false;
    const fetchOrder = () => {
      axios
        .get(`${BACKEND_URL}/api/public/sites/${siteId}/orders/${orderNumber}`)
        .then(({ data }) => {
          if (cancelled) return;
          setOrder(data);
          if (!fired && data?.status === "paid") {
            fired = true;
            try { window.altiaroTrack?.purchase?.(data, lang); } catch (_) {}
          }
          attempts += 1;
          if (data.status === "pending_payment" && attempts < 20) {
            setTimeout(fetchOrder, 2000);
          }
        })
        .catch(() => setOrder(null));
    };
    fetchOrder();
    return () => { cancelled = true; };
  }, [siteId, orderNumber, lang]);

  const paid = order?.status === "paid";
  const failed = order?.status === "failed" || order?.status === "expired" || order?.status === "cancelled";

  return (
    <StorefrontLayout lang={lang} setLang={setLang} site={site} design={design}>
      <div className="max-w-2xl mx-auto px-6 py-16 text-center" data-testid="storefront-confirmation">
        <div className={`w-16 h-16 rounded-full mx-auto flex items-center justify-center mb-6 ${
          paid ? "bg-[#D1FAE5]" : failed ? "bg-[#FFE4E6]" : "bg-[#FEF3C7]"
        }`}>
          <CheckCircle size={32} weight="fill" className={
            paid ? "text-[#047857]" : failed ? "text-[#BE123C]" : "text-[#D97706]"
          } />
        </div>
        <h1 className="font-heading text-4xl font-semibold text-[#1C1917] mb-3">
          {paid ? t(lang, "order_confirmed") : failed ? "Paiement échoué" : (isSuccessPage ? "Finalisation du paiement…" : t(lang, "order_confirmed"))}
        </h1>
        {orderNumber && (
          <div className="text-[#57534E] mb-8" data-testid="order-number">
            {t(lang, "order_number")} · <span className="font-mono font-medium">{orderNumber}</span>
          </div>
        )}
        <p className="text-[#57534E] max-w-lg mx-auto">{t(lang, "order_pending_pay")}</p>

        {order && (
          <div className="bg-white rounded-2xl border border-[#E7E5E4] p-6 mt-8 text-left">
            <div className="text-[11px] uppercase tracking-widest text-[#78716C] mb-3">Détail</div>
            {order.items.map((it, idx) => (
              <div key={idx} className="flex justify-between text-sm py-1.5">
                <span className="text-[#57534E]">
                  {it.quantity} × {it.name}
                </span>
                <span className="font-medium">{formatPrice(it.price * it.quantity, "EUR", lang)}</span>
              </div>
            ))}
            <div className="h-px bg-[#E7E5E4] my-3" />
            <div className="flex justify-between font-heading text-lg">
              <span>{t(lang, "total")}</span>
              <span>{formatPrice(order.total, "EUR", lang)}</span>
            </div>
          </div>
        )}

        <Link
          to={`/shop/${siteId}`}
          className="inline-block mt-10 text-[#B84B31] hover:underline font-medium"
          data-testid="back-to-shop-from-confirm"
        >
          ← {t(lang, "back_to_shop")}
        </Link>
      </div>

      {paid && order?.items?.length > 0 && (
        <div className="max-w-6xl mx-auto px-6 md:px-10 pb-16">
          <UpsellsRecommendations
            mode="post_purchase"
            productIds={order.items.map((it) => it.product_id).filter(Boolean)}
            lang={lang}
            design={design}
          />
        </div>
      )}
    </StorefrontLayout>
  );
}
