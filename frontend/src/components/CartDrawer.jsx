import React, { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { X, Trash, Plus, Minus, ShoppingBag, Truck, ShieldCheck, ArrowRight } from "@phosphor-icons/react";
import { readCart, cartTotals, removeFromCart, updateQty } from "../lib/cart";

/**
 * Slide-in cart drawer. Open via window.dispatchEvent(new Event('cf_cart_open'))
 */
export default function CartDrawer({ design }) {
  const { siteId } = useParams();
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState([]);

  useEffect(() => {
    const refresh = () => setItems(readCart(siteId));
    const openEvt = () => { refresh(); setOpen(true); };
    const closeEvt = () => setOpen(false);
    refresh();
    window.addEventListener("cf_cart_open", openEvt);
    window.addEventListener("cf_cart_close", closeEvt);
    window.addEventListener("cf_cart_updated", refresh);
    return () => {
      window.removeEventListener("cf_cart_open", openEvt);
      window.removeEventListener("cf_cart_close", closeEvt);
      window.removeEventListener("cf_cart_updated", refresh);
    };
  }, [siteId]);

  // Lock body scroll when open
  useEffect(() => {
    document.body.style.overflow = open ? "hidden" : "";
    return () => { document.body.style.overflow = ""; };
  }, [open]);

  const totals = cartTotals(items);
  const primary = design?.brand?.primary_color || "#1C1917";
  const accent = design?.brand?.accent_color || "#F5F2EB";
  const fontHeading = design?.brand?.font_heading || "Fraunces";

  const handleQty = (productId, newQty) => {
    if (newQty < 1) return;
    const updated = updateQty(siteId, productId, newQty);
    setItems(updated);
  };
  const handleRemove = (productId) => {
    const updated = removeFromCart(siteId, productId);
    setItems(updated);
  };

  if (!open) return null;

  return (
    <>
      <div
        onClick={() => setOpen(false)}
        className="fixed inset-0 bg-black/40 backdrop-blur-sm z-[998] animate-fade-in"
        data-testid="cart-drawer-overlay"
      />
      <aside
        className="fixed top-0 right-0 bottom-0 w-full sm:w-[460px] bg-white z-[999] shadow-2xl flex flex-col animate-slide-in-right"
        data-testid="cart-drawer"
      >
        <div className="flex items-center justify-between p-5 border-b border-neutral-200 shrink-0">
          <div className="flex items-center gap-2.5">
            <ShoppingBag size={22} weight="regular" />
            <h2 className="text-xl" style={{ fontFamily: `${fontHeading}, serif` }}>
              Mon panier
              <span className="ml-2 text-sm text-neutral-500 font-normal">
                ({totals.itemsCount} {totals.itemsCount > 1 ? "articles" : "article"})
              </span>
            </h2>
          </div>
          <button
            onClick={() => setOpen(false)}
            data-testid="cart-drawer-close"
            className="w-9 h-9 rounded-full hover:bg-neutral-100 flex items-center justify-center transition"
            aria-label="Fermer"
          >
            <X size={18} />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-5">
          {items.length === 0 ? (
            <div className="text-center py-16">
              <ShoppingBag size={48} weight="duotone" className="mx-auto mb-4 opacity-40" />
              <p className="text-neutral-600 mb-6">Votre panier est vide.</p>
              <button
                onClick={() => setOpen(false)}
                className="h-11 px-5 rounded-xl text-white text-sm font-medium"
                style={{ background: primary }}
              >
                Découvrir nos produits
              </button>
            </div>
          ) : (
            <div className="space-y-4">
              {items.map((it) => (
                <div key={it.product_id} className="flex gap-4" data-testid={`cart-drawer-item-${it.product_id}`}>
                  <div className="w-20 h-20 rounded-xl overflow-hidden bg-neutral-100 shrink-0">
                    {it.image && <img src={it.image} alt={it.name} className="w-full h-full object-cover" />}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex justify-between gap-2 mb-1">
                      <h3 className="text-sm font-medium line-clamp-2 pr-2">{it.name}</h3>
                      <button
                        onClick={() => handleRemove(it.product_id)}
                        data-testid={`cart-drawer-remove-${it.product_id}`}
                        className="text-neutral-400 hover:text-red-600 transition shrink-0"
                        aria-label="Retirer"
                      >
                        <Trash size={16} />
                      </button>
                    </div>
                    <div className="text-xs text-neutral-500 mb-2">{Number(it.price).toFixed(2)} €</div>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-0 border border-neutral-300 rounded-full h-8">
                        <button
                          onClick={() => handleQty(it.product_id, it.qty - 1)}
                          data-testid={`cart-drawer-qty-minus-${it.product_id}`}
                          className="w-8 h-8 flex items-center justify-center hover:bg-neutral-50"
                          disabled={it.qty <= 1}
                        >
                          <Minus size={12} />
                        </button>
                        <span className="w-8 text-center text-sm tabular-nums">{it.qty}</span>
                        <button
                          onClick={() => handleQty(it.product_id, it.qty + 1)}
                          data-testid={`cart-drawer-qty-plus-${it.product_id}`}
                          className="w-8 h-8 flex items-center justify-center hover:bg-neutral-50"
                        >
                          <Plus size={12} />
                        </button>
                      </div>
                      <div className="font-semibold tabular-nums text-sm">
                        {(it.price * it.qty).toFixed(2)} €
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {items.length > 0 && (
          <div className="border-t border-neutral-200 p-5 space-y-3 shrink-0 bg-white">
            <div className="flex items-center gap-2 text-xs text-emerald-700 font-medium" style={{ background: accent }} >
              <Truck size={14} weight="duotone" />
              <span className="py-1.5">Livraison offerte partout</span>
            </div>
            <div className="flex items-center gap-2 text-xs text-emerald-700 font-medium" style={{ background: accent }}>
              <ShieldCheck size={14} weight="duotone" />
              <span className="py-1.5">Retour gratuit sous 14 jours · Garantie 2 ans</span>
            </div>
            <div className="flex items-center justify-between pt-1">
              <span className="text-sm text-neutral-600">Sous-total</span>
              <span className="text-lg font-semibold tabular-nums">{totals.total.toFixed(2)} €</span>
            </div>
            <Link
              to={`/shop/${siteId}/checkout`}
              onClick={() => setOpen(false)}
              data-testid="cart-drawer-checkout"
              className="w-full h-12 rounded-xl flex items-center justify-center gap-2 text-white text-sm font-medium transition active:scale-[0.98]"
              style={{ background: primary }}
            >
              Passer commande <ArrowRight size={14} weight="bold" />
            </Link>
            <Link
              to={`/shop/${siteId}/cart`}
              onClick={() => setOpen(false)}
              className="block text-center text-xs text-neutral-500 hover:text-neutral-900 underline"
            >
              Voir le panier en détail
            </Link>
          </div>
        )}
      </aside>
    </>
  );
}
