/**
 * Phase 2.3 (Lot I I11) — "Comment l'utiliser" infographique.
 *
 * Affiche 3-4 étapes pas-à-pas du champ `product.how_to_steps`,
 * généré par Haiku via `services/product_content_ai.py::generate_product_how_to`.
 *
 * Style premium Aesop :
 *  - Cards verticales fond ivoire (#F5F2EB)
 *  - Icône Lucide en haut, label court Cormorant, description sans-serif
 *  - Numéro d'étape en chiffre romain léger
 *  - Bordures fines #E7E5E4
 *
 * Si `how_to_steps` est vide → composant masqué.
 *
 * Le JSON-LD HowTo est posé côté `StorefrontProduct.jsx` dans le tableau
 * `schema={...}` du composant `<SEOHead/>`.
 */
import React from "react";
import * as LucideIcons from "lucide-react";

const ROMAN = ["I", "II", "III", "IV", "V"];

function StepIcon({ name, color }) {
  const Cmp = (LucideIcons && LucideIcons[name]) || LucideIcons.ChevronsRight;
  return <Cmp size={26} strokeWidth={1.4} color={color || "#0A0A0A"} />;
}

export default function ProductHowTo({ steps, sectionTitle, design, lang = "fr" }) {
  if (!Array.isArray(steps) || steps.length < 3) return null;

  const accent = (design?.brand?.palette?.accent) || "#9F6E50";
  const fontHeading =
    design?.brand?.font_pair?.heading ||
    "'Cormorant Garamond', 'Cormorant', serif";

  // Phase 2.6 Tâche C — sectionTitle est passé par StorefrontProduct.jsx
  // depuis `product.how_to_steps_meta.section_title` (généré par Haiku
  // adaptatif selon `source_vision_lock.product_kind`). Fallback au libellé
  // statique "Comment l'utiliser" / "How to use it" si non généré.
  const fallbackTitle = lang === "en" ? "How to use it" : "Comment l'utiliser";
  const resolvedTitle =
    (typeof sectionTitle === "string" && sectionTitle.trim())
      ? sectionTitle.trim()
      : (sectionTitle && typeof sectionTitle === "object"
          ? (sectionTitle[lang] || sectionTitle.fr || sectionTitle.en || fallbackTitle)
          : fallbackTitle);
  const sectionEyebrow = "RITUEL";

  return (
    <section
      className="my-20 md:my-28"
      data-testid="product-how-to"
      aria-labelledby="howto-title"
    >
      <div className="text-center mb-12 md:mb-14">
        <div
          className="text-[10.5px] uppercase tracking-[0.45em] mb-3"
          style={{ color: "#9C8C7C" }}
        >
          {sectionEyebrow}
        </div>
        <h2
          id="howto-title"
          className="text-[34px] md:text-[44px] leading-[1.05] font-light"
          style={{ fontFamily: fontHeading, color: "#0A0A0A" }}
        >
          {resolvedTitle}
        </h2>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5 md:gap-6">
        {steps.slice(0, 4).map((s, i) => (
          <article
            key={i}
            className="relative p-7 md:p-8 transition-all hover:translate-y-[-2px]"
            style={{
              background: "#F5F2EB",
              border: "1px solid #E7E5E4",
              borderRadius: "2px",
            }}
            data-testid={`howto-step-${i}`}
          >
            <div className="flex items-start justify-between mb-5">
              <div
                className="text-[11px] uppercase tracking-[0.35em] tabular-nums"
                style={{ color: "#9C8C7C", fontFamily: fontHeading }}
              >
                {ROMAN[i] || (i + 1)}
              </div>
              <StepIcon name={s.icon} color={accent} />
            </div>

            <h3
              className="text-[20px] md:text-[22px] leading-[1.15] font-light mb-3"
              style={{ fontFamily: fontHeading, color: "#0A0A0A" }}
            >
              {s.title}
            </h3>

            <p
              className="text-[13.5px] leading-[1.65]"
              style={{ color: "#525252" }}
            >
              {s.description}
            </p>
          </article>
        ))}
      </div>
    </section>
  );
}
