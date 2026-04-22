// Gestion du panier via localStorage, scopé par site_id.
// Stocke un tableau d'items {product_id, name, price, quantity, currency, image}.

const KEY = (siteId) => `cf_cart_${siteId}`;

export function readCart(siteId) {
  try {
    const raw = localStorage.getItem(KEY(siteId));
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function writeCart(siteId, items) {
  localStorage.setItem(KEY(siteId), JSON.stringify(items));
  // dispatch event so other tabs/components update
  window.dispatchEvent(new CustomEvent("cf_cart_updated", { detail: { siteId } }));
}

export function addToCart(siteId, product, lang = "fr", quantity = 1, opts = {}) {
  const items = readCart(siteId);
  const existing = items.find((i) => i.product_id === product.id);
  const name =
    typeof product.name === "string"
      ? product.name
      : product.name?.[lang] || product.name?.fr || "";
  const discountPct = Math.max(0, Math.min(Number(opts.discount_pct || 0), 50));
  const basePrice = Number(product.price) || 0;
  const effectivePrice = discountPct > 0
    ? Math.round(basePrice * (1 - discountPct / 100) * 100) / 100
    : basePrice;
  if (existing) {
    existing.quantity += quantity;
    // Keep best discount between previous and new
    if (discountPct > (existing.upsell_discount_pct || 0)) {
      existing.upsell_discount_pct = discountPct;
      existing.original_price = basePrice;
      existing.price = effectivePrice;
    }
  } else {
    items.push({
      product_id: product.id,
      name,
      price: effectivePrice,
      original_price: basePrice,
      upsell_discount_pct: discountPct,
      quantity,
      currency: product.currency || "EUR",
      image: product.images?.[0] || null,
    });
  }
  writeCart(siteId, items);
  return items;
}

export function updateQty(siteId, productId, qty) {
  const items = readCart(siteId);
  const idx = items.findIndex((i) => i.product_id === productId);
  if (idx === -1) return items;
  if (qty <= 0) {
    items.splice(idx, 1);
  } else {
    items[idx].quantity = qty;
  }
  writeCart(siteId, items);
  return items;
}

export function removeFromCart(siteId, productId) {
  const items = readCart(siteId).filter((i) => i.product_id !== productId);
  writeCart(siteId, items);
  return items;
}

export function clearCart(siteId) {
  localStorage.removeItem(KEY(siteId));
  window.dispatchEvent(new CustomEvent("cf_cart_updated", { detail: { siteId } }));
}

export function cartTotals(items) {
  const subtotal = items.reduce((s, i) => s + i.price * i.quantity, 0);
  const shipping_fee = subtotal >= 50 ? 0 : 4.9;
  const total = subtotal + shipping_fee;
  const itemsCount = items.reduce((s, i) => s + i.quantity, 0);
  return {
    subtotal: Math.round(subtotal * 100) / 100,
    shipping_fee,
    total: Math.round(total * 100) / 100,
    itemsCount,
  };
}
