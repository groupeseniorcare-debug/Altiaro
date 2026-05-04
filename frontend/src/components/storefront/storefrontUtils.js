import { useEffect, useState, useCallback } from "react";
import { useShopSiteId } from "../../lib/shopSiteId";
import { useParams, useSearchParams } from "react-router-dom";
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

/**
 * Phase 3 — Hook central du storefront : site + langue courante + available_langs
 * + primaryLang. Résout la langue au mount avec la priorité :
 *   1. ?lang=xx dans l'URL (si supportée)
 *   2. localStorage "cf_lang_<siteId>" (si supportée)
 *   3. primary_lang du site (si supportée) ← Fix 2026-05-04
 *      RATIONALE : un site premium orienté marchés FR doit s'afficher en FR
 *      à la première visite, même si le navigateur est en anglais. Le
 *      visiteur peut toujours basculer via le LanguageSwitcher (choix alors
 *      persisté en localStorage). navigator.language devient un fallback
 *      qui ne s'applique que si primary_lang n'est pas dans available_langs.
 *   4. navigator.language.slice(0,2) (si supportée)
 *   5. availableLangs[0] (fallback final)
 *
 * setLang() persiste en localStorage + sync query string + émet un event
 * `language_change` vers le tracker analytics (Chantier 7).
 */
function _detectInitialLang(urlLang, storageLang, availableLangs, primaryLang) {
  const supports = (lg) => !!lg && availableLangs.includes(lg);
  if (supports(urlLang)) return urlLang;
  if (supports(storageLang)) return storageLang;
  if (supports(primaryLang)) return primaryLang;
  if (typeof navigator !== "undefined") {
    const nav = (navigator.language || "fr").slice(0, 2).toLowerCase();
    if (supports(nav)) return nav;
  }
  return availableLangs[0] || "fr";
}

function _postLanguageChange(siteId, fromLang, toLang) {
  try {
    const base = process.env.REACT_APP_BACKEND_URL || "";
    const url = `${base}/api/public/sites/${siteId}/track`;
    const body = JSON.stringify({
      event: "page_view",   // fallback sémantique ALLOWED_EVENTS
      session_id: localStorage.getItem("altiaro.sess") ? JSON.parse(localStorage.getItem("altiaro.sess"))?.id : `lang-${Date.now()}`,
      path: window.location?.pathname || "",
      lang: toLang,
      meta: { language_change: true, from: fromLang, to: toLang },
    });
    if (navigator?.sendBeacon) {
      navigator.sendBeacon(url, new Blob([body], { type: "text/plain;charset=UTF-8" }));
    } else {
      fetch(url, { method: "POST", headers: { "Content-Type": "text/plain;charset=UTF-8" }, body, keepalive: true, mode: "cors", credentials: "omit" }).catch(() => {});
    }
  } catch (_) { /* best-effort */ }
}


export function useSiteAndLang() {
  const urlSiteId = useShopSiteId();
  const [searchParams, setSearchParams] = useSearchParams();
  const [site, setSite] = useState(null);
  const [design, setDesign] = useState(null);
  const [availableLangs, setAvailableLangs] = useState(["fr"]);
  const [primaryLang, setPrimaryLang] = useState("fr");
  const storageKey = `cf_lang_${urlSiteId}`;
  const urlLang = (searchParams.get("lang") || "").toLowerCase();
  const [lang, setLangState] = useState(() => {
    const stored = (typeof window !== "undefined" && localStorage.getItem(storageKey)) || null;
    // available/primary pas encore chargés — on prend ce qu'on peut
    return urlLang || stored || "fr";
  });

  // Fetch public site, design, i18n-config en parallèle
  useEffect(() => {
    let cancelled = false;
    fetchPublicSite(urlSiteId)
      .then((data) => {
        if (cancelled) return;
        setSite(data);
        const resolvedId = data?.id || urlSiteId;
        // design
        axios
          .get(`${BACKEND_URL}/api/public/sites/${resolvedId}/design`)
          .then(({ data: d }) => !cancelled && setDesign(d?.published ? d.design : null))
          .catch(() => !cancelled && setDesign(null));
        // i18n-config
        axios
          .get(`${BACKEND_URL}/api/public/sites/${resolvedId}/i18n-config`)
          .then(({ data: cfg }) => {
            if (cancelled) return;
            const avail = cfg?.available_langs || ["fr"];
            const prim = cfg?.primary_lang || "fr";
            setAvailableLangs(avail);
            setPrimaryLang(prim);
            // Re-compute initial lang now that we know what's available
            const stored = localStorage.getItem(storageKey) || null;
            const resolved = _detectInitialLang(urlLang, stored, avail, prim);
            setLangState(resolved);
            if (resolved && !urlLang) {
              // Sync URL to the resolved lang (not primary by default to keep clean URL)
              // Only touch URL if user explicitly stored a non-primary pref
              if (stored && stored !== prim && avail.includes(stored)) {
                setSearchParams((prev) => {
                  const next = new URLSearchParams(prev);
                  next.set("lang", stored);
                  return next;
                }, { replace: true });
              }
            }
          })
          .catch(() => { /* fallback silent */ });
      })
      .catch(() => !cancelled && setSite({ error: true }));
    return () => { cancelled = true; };
  }, [urlSiteId]);

  // Keep document lang attribute synced
  useEffect(() => {
    if (typeof document !== "undefined" && lang) {
      document.documentElement.lang = lang;
    }
  }, [lang]);

  // Inject <link rel="alternate" hreflang="xx"> dynamically (SEO)
  useEffect(() => {
    if (typeof document === "undefined" || !availableLangs?.length) return;
    // Remove our previous dynamic alternates
    document.querySelectorAll('link[data-altiaro-hreflang]').forEach((n) => n.remove());
    const origin = window.location.origin;
    const path = window.location.pathname;
    availableLangs.forEach((lg) => {
      const link = document.createElement("link");
      link.setAttribute("rel", "alternate");
      link.setAttribute("hreflang", lg);
      link.setAttribute("href", `${origin}${path}?lang=${lg}`);
      link.setAttribute("data-altiaro-hreflang", "1");
      document.head.appendChild(link);
    });
    // x-default → primary
    const xd = document.createElement("link");
    xd.setAttribute("rel", "alternate");
    xd.setAttribute("hreflang", "x-default");
    xd.setAttribute("href", `${origin}${path}?lang=${primaryLang}`);
    xd.setAttribute("data-altiaro-hreflang", "1");
    document.head.appendChild(xd);
  }, [availableLangs, primaryLang]);

  const setLang = useCallback((next) => {
    if (!next || !availableLangs.includes(next)) return;
    const prev = lang;
    localStorage.setItem(storageKey, next);
    setLangState(next);
    setSearchParams((p) => {
      const n = new URLSearchParams(p);
      n.set("lang", next);
      return n;
    }, { replace: true });
    const resolvedId = site?.id || urlSiteId;
    if (resolvedId && prev !== next) _postLanguageChange(resolvedId, prev, next);
  }, [lang, availableLangs, setSearchParams, storageKey, site, urlSiteId]);

  const resolvedId = site?.id || urlSiteId;
  return {
    siteId: resolvedId,
    urlSlug: urlSiteId,
    site,
    design,
    lang,
    setLang,
    availableLangs,
    primaryLang,
  };
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
  // The template has TWO modes, controlled by `design.template_mode`:
  //   • "monochrome" (default) — black-on-white editorial magazine, cards gray
  //   • "brand"                 — uses the site's brand palette (primary/accent)
  //
  // Both modes expose the same keys so every component can stay identical.
  const mode = (design?.template_mode === "brand") ? "brand" : "monochrome";
  const b = design?.brand || {};
  if (mode === "brand") {
    return {
      mode,
      primary: b.text_color || "#0A0A0A",
      accent: b.accent_color || b.background_color || "#F5F5F5",
      surface: b.background_color || "#FAFAFA",
      divider: "#E5E5E5",
      textMuted: "#737373",
      textFaint: "#A3A3A3",
      brandAccent: b.primary_color || "#0A0A0A",
      fontHeading: b.font_heading || "Fraunces",
      fontBody: b.font_body || "Inter",
    };
  }
  return {
    mode,
    primary: "#0A0A0A",
    accent: "#F5F5F5",
    surface: "#FAFAFA",
    divider: "#E5E5E5",
    textMuted: "#737373",
    textFaint: "#A3A3A3",
    brandAccent: b.primary_color || "#0A0A0A",
    fontHeading: b.font_heading || "Fraunces",
    fontBody: b.font_body || "Inter",
  };
}
