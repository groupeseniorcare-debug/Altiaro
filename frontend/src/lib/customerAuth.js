// Storefront customer auth utilities (per-site JWT in localStorage)
const storageKey = (siteId) => `alt_cust_${siteId}`;

export function getToken(siteId) {
  try { return JSON.parse(localStorage.getItem(storageKey(siteId)) || "null")?.token || null; }
  catch { return null; }
}
export function getCustomer(siteId) {
  try { return JSON.parse(localStorage.getItem(storageKey(siteId)) || "null")?.customer || null; }
  catch { return null; }
}
export function setSession(siteId, token, customer) {
  localStorage.setItem(storageKey(siteId), JSON.stringify({ token, customer }));
  window.dispatchEvent(new CustomEvent("alt_cust_session", { detail: { siteId } }));
}
export function clearSession(siteId) {
  localStorage.removeItem(storageKey(siteId));
  window.dispatchEvent(new CustomEvent("alt_cust_session", { detail: { siteId } }));
}
export function authHeaders(siteId) {
  const t = getToken(siteId);
  return t ? { Authorization: `Bearer ${t}` } : {};
}
