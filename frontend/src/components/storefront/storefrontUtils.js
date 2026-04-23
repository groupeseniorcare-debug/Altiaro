import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import axios from "axios";
import { fetchPublicSite } from "../StorefrontLayout";
import {
  ShieldCheck, Truck, Clock, Heart, Star, Leaf, Package, Headset,
} from "@phosphor-icons/react";

export const BACKEND_URL = "";

// Icon name (from Prompt Studio schema) → Phosphor component
export const BENEFIT_ICON = {
  ShieldCheck, Truck, Clock, Heart, Star, Leaf, Package, Headset,
};

// Map selected_countries → storefront langs for hreflang
const LANG_BY_COUNTRY = {
  FR: "fr", BE: "fr", LU: "fr", CH: "fr",
  DE: "de", AT: "de",
  UK: "en", IE: "en",
  NL: "nl", IT: "it", ES: "es",
};

export function buildHreflangs(site, path) {
  const origin = typeof window !== "undefined" ? window.location.origin : "";
  const base = `${origin}/shop/${site?.id || ""}${path}`;
  const codes = Array.from(
    new Set((site?.selected_countries || ["FR"]).map((c) => LANG_BY_COUNTRY[(c || "").toUpperCase()] || "fr"))
  );
  return codes.map((c) => ({ code: c, href: `${base}?lang=${c}` }));
}

export function useSiteAndLang() {
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

export function designText(design, path, lang) {
  if (!design) return null;
  const parts = path.split(".");
  let node = design;
  for (const p of parts) {
    node = node?.[p];
    if (node === undefined || node === null) return null;
  }
  if (typeof node === "string") return node;
  if (typeof node === "object") return node[lang] || node.fr || Object.values(node)[0] || null;
  return null;
}

export function formatPrice(price, currency = "EUR", lang = "fr") {
  try {
    return new Intl.NumberFormat(lang === "en" ? "en-GB" : lang, {
      style: "currency",
      currency,
    }).format(price);
  } catch {
    return `${price} ${currency}`;
  }
}

export function designAccents(design) {
  // MONOCHROME TEMPLATE — force the storefront chrome to black/white/gray regardless
  // of the brand palette. The brand color is exposed as `brandAccent` for small
  // brand-specific accents only (rating stars remain gold, we expose one optional
  // hue for any micro-accent that *needs* to be brand-colored).
  return {
    primary: "#0A0A0A",           // main "ink" color (text, buttons)
    accent: "#F5F5F5",            // light gray surfaces
    surface: "#FAFAFA",           // softest gray
    divider: "#E5E5E5",           // hairline dividers
    textMuted: "#737373",         // secondary text
    textFaint: "#A3A3A3",         // captions
    brandAccent: design?.brand?.primary_color || "#0A0A0A",
    fontHeading: design?.brand?.font_heading || "Fraunces",
    fontBody: design?.brand?.font_body || "Inter",
  };
}
