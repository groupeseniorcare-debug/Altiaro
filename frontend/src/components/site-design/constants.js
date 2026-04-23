import { PaintBrush, List, Stack, ChatCenteredText } from "@phosphor-icons/react";

export const TABS = [
  { key: "identity", label: "Identité", Icon: PaintBrush },
  { key: "navigation", label: "Navigation", Icon: List },
  { key: "collections", label: "Collections", Icon: Stack },
  { key: "content", label: "Pages & contenu", Icon: ChatCenteredText },
];

export const FONT_PAIRS = [
  { heading: "Fraunces", body: "Inter", label: "Éditorial · chaleureux" },
  { heading: "Playfair Display", body: "Source Sans Pro", label: "Classique · premium" },
  { heading: "DM Serif Display", body: "DM Sans", label: "Moderne · élégant" },
  { heading: "Cormorant Garamond", body: "Lato", label: "Luxe · discret" },
  { heading: "Montserrat", body: "Open Sans", label: "Sobre · lisible" },
  { heading: "Lora", body: "Roboto", label: "Premium · accessible" },
];

export const PALETTE_PRESETS = [
  { name: "Sénior chaleureux", primary: "#B84B31", secondary: "#E9C46A", bg: "#FAF7F2", text: "#1C1917", accent: "#2A9D8F" },
  { name: "Médical rassurant",  primary: "#1D6A96", secondary: "#81C3D7", bg: "#F7FAFC", text: "#1E293B", accent: "#F59E0B" },
  { name: "Nature apaisant",    primary: "#2A9D8F", secondary: "#E9C46A", bg: "#F5F5F0", text: "#264653", accent: "#E76F51" },
  { name: "Luxe minimal",       primary: "#1A1A1A", secondary: "#C9A66B", bg: "#FFFFFF", text: "#1A1A1A", accent: "#8B0000" },
  { name: "Bien-être doux",     primary: "#D4A5A5", secondary: "#F5E6D3", bg: "#FDFBF7", text: "#3E2723", accent: "#8B7355" },
];

export const LINK_TYPES = [
  { value: "home",        label: "Accueil",              href: "/" },
  { value: "shop",        label: "Toute la boutique",    href: "/" },
  { value: "collections", label: "Toutes collections",   href: "/collections" },
  { value: "collection",  label: "Une collection…",      href: "" },
  { value: "product",     label: "Un produit…",          href: "" },
  { value: "blog",        label: "Journal / Blog",       href: "/blog" },
  { value: "about",       label: "À propos",             href: "/about" },
  { value: "contact",     label: "Contact",              href: "/contact" },
  { value: "faq",         label: "FAQ",                  href: "/faq" },
  { value: "search",      label: "Recherche",            href: "/search" },
  { value: "cgv",         label: "CGV",                  href: "/cgv" },
  { value: "mentions",    label: "Mentions légales",     href: "/mentions" },
  { value: "confidentialite", label: "Confidentialité",  href: "/confidentialite" },
  { value: "cookies",     label: "Cookies",              href: "/cookies" },
  { value: "livraison",   label: "Livraison",            href: "/livraison" },
  { value: "retours",     label: "Retours",              href: "/retours" },
  { value: "mediation",   label: "Médiation",            href: "/mediation" },
  { value: "url",         label: "URL personnalisée",    href: "" },
];

export function detectLinkType(href = "") {
  const h = (href || "").trim();
  if (/^https?:\/\//.test(h)) return "url";
  if (h === "/" || h === "") return "home";
  if (h === "/collections") return "collections";
  if (h.startsWith("/collections/")) return "collection";
  if (h.startsWith("/product/")) return "product";
  const known = ["blog", "about", "contact", "faq", "search", "cgv", "mentions", "confidentialite", "cookies", "livraison", "retours", "mediation"];
  for (const k of known) if (h === `/${k}`) return k;
  return "url";
}
