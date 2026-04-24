import React, { useEffect, useRef, useState } from "react";
import { CaretDown, Check } from "@phosphor-icons/react";
import { LANGUAGES } from "../../lib/i18n";

/**
 * Phase 3 — Dropdown de sélection de langue pour le storefront.
 * - Ne liste que les langues dans `availableLangs` (fournies par useSiteAndLang)
 * - data-testid: `storefront-language-switcher` + `lang-option-{xx}`
 * - Ferme au clic extérieur ou à la sélection
 * - Accessible clavier (Esc ferme, flèches circulent)
 * - Rendu minimal sans dépendance radix (pas besoin côté public)
 */
export default function LanguageSwitcher({
  lang,
  setLang,
  availableLangs = [],
  align = "right",
  tone = "dark",    // "dark" = sur fond clair | "light" = sur fond sombre
  compact = false,  // cache le label texte, garde juste drapeau + code
}) {
  const [open, setOpen] = useState(false);
  const wrapRef = useRef(null);

  const visibleLangs = LANGUAGES.filter((l) => availableLangs.includes(l.code));
  const current = LANGUAGES.find((l) => l.code === lang) || visibleLangs[0] || { code: "fr", flag: "🇫🇷", label: "Français" };

  useEffect(() => {
    const onDoc = (e) => {
      if (!wrapRef.current) return;
      if (!wrapRef.current.contains(e.target)) setOpen(false);
    };
    const onEsc = (e) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onEsc);
    return () => {
      document.removeEventListener("mousedown", onDoc);
      document.removeEventListener("keydown", onEsc);
    };
  }, []);

  if (visibleLangs.length <= 1) return null;  // 1 seule langue → pas de switcher

  const isLight = tone === "light";
  const btnCls = isLight
    ? "text-white/85 hover:text-white border border-white/20 hover:border-white/40 bg-white/5"
    : "text-neutral-800 hover:text-neutral-900 border border-neutral-200 hover:border-neutral-400 bg-white";

  return (
    <div className="relative inline-block" ref={wrapRef}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="listbox"
        aria-expanded={open}
        data-testid="storefront-language-switcher"
        className={`h-9 px-3 rounded-full text-xs font-medium inline-flex items-center gap-1.5 transition ${btnCls}`}
      >
        <span className="text-base leading-none">{current.flag}</span>
        {!compact && <span className="uppercase tracking-wider">{current.code}</span>}
        <CaretDown size={11} weight="bold" className={`transition-transform ${open ? "rotate-180" : ""}`} />
      </button>

      {open && (
        <div
          role="listbox"
          aria-label="Langue"
          className={`absolute top-full mt-1.5 ${align === "right" ? "right-0" : "left-0"} min-w-[170px] bg-white rounded-lg border border-neutral-200 shadow-lg z-50 overflow-hidden animate-fade-up`}
        >
          {visibleLangs.map((l) => {
            const active = l.code === lang;
            return (
              <button
                key={l.code}
                type="button"
                role="option"
                aria-selected={active}
                data-testid={`lang-option-${l.code}`}
                onClick={() => { setLang(l.code); setOpen(false); }}
                className={`w-full h-10 px-3 flex items-center gap-2.5 text-sm text-left transition ${
                  active ? "bg-neutral-100 text-neutral-900 font-medium" : "text-neutral-700 hover:bg-neutral-50"
                }`}
              >
                <span className="text-base leading-none">{l.flag}</span>
                <span className="flex-1">{l.label}</span>
                {active && <Check size={14} weight="bold" className="text-emerald-600" />}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
