import React from "react";
import { Link, useParams } from "react-router-dom";
import {
  Question, ListChecks, Prohibit, PlayCircle, MagnifyingGlass,
  CheckCircle, XCircle,
} from "@phosphor-icons/react";
import { designAccents } from "./storefrontUtils";
import { t } from "../../lib/i18n";

/**
 * SEO/AEO enrichment blocks for Product pages.
 * Each block is rendered only if its source data is available.
 * These blocks are optimized for :
 *  - Google long-tail organic ranking
 *  - People Also Ask snippets
 *  - AI answer engine citation (ChatGPT, Perplexity, Claude)
 */

/* ---------- People Also Ask (PAA) ---------- */
export function PeopleAlsoAsk({ items, design, lang = "fr" }) {
  if (!items || items.length === 0) return null;
  const { primary, fontHeading } = designAccents(design);
  return (
    <section className="mb-20" data-testid="product-paa">
      <div className="flex items-end justify-between flex-wrap gap-3 mb-8">
        <div>
          <div className="text-[11px] uppercase tracking-[0.2em] text-neutral-500 mb-2">
            {t(lang, "faq_section_eyebrow")}
          </div>
          <h2
            className="text-3xl md:text-4xl font-semibold"
            style={{ fontFamily: `"${fontHeading}", serif`, color: "#1C1917" }}
          >
            {t(lang, "faq_section_title")}
          </h2>
        </div>
      </div>
      <div className="space-y-3 max-w-4xl">
        {items.map((it, i) => (
          <details
            key={i}
            data-testid={`paa-${i}`}
            className="bg-white rounded-2xl border border-[#E7E5E4] p-5 md:p-6 group open:shadow-sm transition"
          >
            <summary className="cursor-pointer list-none flex items-start justify-between gap-4">
              <div className="flex items-start gap-3">
                <Question size={18} weight="duotone" className="mt-1 shrink-0" style={{ color: primary }} />
                <span
                  className="font-semibold text-[16px] md:text-lg text-neutral-900 leading-snug"
                  style={{ fontFamily: `"${fontHeading}", serif` }}
                >
                  {it.question}
                </span>
              </div>
              <span
                className="w-7 h-7 rounded-full flex items-center justify-center text-sm group-open:rotate-45 transition-transform shrink-0 mt-0.5"
                style={{ background: `${primary}14`, color: primary }}
              >
                +
              </span>
            </summary>
            <p className="text-[15px] mt-4 pl-7 leading-[1.75] text-neutral-700">
              {it.answer}
            </p>
          </details>
        ))}
      </div>
    </section>
  );
}

/* ---------- Best for / Not for ---------- */
export function BestForNotFor({ best_for, not_for, design }) {
  if ((!best_for || best_for.length === 0) && (!not_for || not_for.length === 0)) return null;
  const { primary, fontHeading } = designAccents(design);
  return (
    <section className="mb-20" data-testid="product-bestfor">
      <div className="mb-10">
        <div className="text-[11px] uppercase tracking-[0.2em] text-neutral-500 mb-2">
          Transparence
        </div>
        <h2
          className="text-3xl md:text-4xl font-semibold"
          style={{ fontFamily: `"${fontHeading}", serif`, color: "#1C1917" }}
        >
          Est-ce fait pour vous ?
        </h2>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5 md:gap-6">
        {best_for && best_for.length > 0 && (
          <div className="bg-[#F0FAF5] rounded-3xl p-7 border border-emerald-100">
            <div className="flex items-center gap-2 mb-5">
              <ListChecks size={20} weight="duotone" className="text-emerald-700" />
              <div className="font-semibold text-emerald-900">Idéal pour</div>
            </div>
            <ul className="space-y-3">
              {best_for.map((b, i) => (
                <li key={i} className="flex items-start gap-2.5 text-[15px] text-neutral-800 leading-snug">
                  <CheckCircle size={18} weight="fill" className="text-emerald-600 shrink-0 mt-0.5" />
                  {b}
                </li>
              ))}
            </ul>
          </div>
        )}
        {not_for && not_for.length > 0 && (
          <div className="bg-[#FDF4F2] rounded-3xl p-7 border border-rose-100">
            <div className="flex items-center gap-2 mb-5">
              <Prohibit size={20} weight="duotone" className="text-rose-700" />
              <div className="font-semibold text-rose-900">Moins adapté pour</div>
            </div>
            <ul className="space-y-3">
              {not_for.map((b, i) => (
                <li key={i} className="flex items-start gap-2.5 text-[15px] text-neutral-800 leading-snug">
                  <XCircle size={18} weight="fill" className="text-rose-500 shrink-0 mt-0.5" />
                  {b}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
      <div className="text-xs text-neutral-500 mt-4">
        Notre transparence est l'une de nos valeurs clés — un produit qui admet ses limites est un produit de confiance.
      </div>
    </section>
  );
}

/* ---------- Usage Steps (HowTo) ---------- */
export function UsageSteps({ steps, productName, design }) {
  if (!steps || steps.length === 0) return null;
  const { primary, fontHeading } = designAccents(design);
  return (
    <section className="mb-20" data-testid="product-howto">
      <div className="mb-10">
        <div className="text-[11px] uppercase tracking-[0.2em] text-neutral-500 mb-2">
          Prise en main
        </div>
        <h2
          className="text-3xl md:text-4xl font-semibold"
          style={{ fontFamily: `"${fontHeading}", serif`, color: "#1C1917" }}
        >
          Comment l'utiliser au quotidien
        </h2>
      </div>
      <ol className="space-y-4 max-w-4xl">
        {steps.map((s, i) => (
          <li
            key={i}
            className="flex gap-5 bg-white rounded-2xl p-5 md:p-6 border border-[#E7E5E4]"
            data-testid={`howto-step-${i}`}
          >
            <div
              className="w-11 h-11 rounded-full flex items-center justify-center shrink-0 font-semibold text-white"
              style={{ background: primary }}
            >
              {i + 1}
            </div>
            <div>
              <div
                className="font-semibold text-[16px] md:text-lg text-neutral-900 mb-1.5"
                style={{ fontFamily: `"${fontHeading}", serif` }}
              >
                {s.name}
              </div>
              <p className="text-[15px] text-neutral-600 leading-relaxed">{s.text}</p>
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}

/* ---------- Related Queries (internal linking) ---------- */
export function RelatedQueries({ queries, design }) {
  // Lot G Fix 8 — Le bloc "Recherches populaires" pollue la fin de fiche
  // produit (faible valeur conversion + pas premium). Retiré du rendu.
  // Code conservé pour réactivation future via `?showRelated=1` ou flag admin.
  return null;
  // eslint-disable-next-line no-unreachable
  const { siteId } = useParams();
  if (!queries || queries.length === 0) return null;
  const { primary, fontHeading } = designAccents(design);
  return (
    <section className="mb-20" data-testid="product-related-queries">
      <div className="mb-8">
        <div className="text-[11px] uppercase tracking-[0.2em] text-neutral-500 mb-2">
          Explorer plus loin
        </div>
        <h2
          className="text-2xl md:text-3xl font-semibold"
          style={{ fontFamily: `"${fontHeading}", serif`, color: "#1C1917" }}
        >
          Recherches populaires
        </h2>
      </div>
      <div className="flex flex-wrap gap-2">
        {queries.map((q, i) => (
          <Link
            key={i}
            to={`/shop/${siteId}/search?q=${encodeURIComponent(q)}`}
            data-testid={`related-query-${i}`}
            className="inline-flex items-center gap-2 h-10 px-4 rounded-full bg-[#F5F2EB] hover:bg-[#EFEBE2] transition text-[14px] text-neutral-800 border border-transparent hover:border-neutral-200"
          >
            <MagnifyingGlass size={14} weight="bold" style={{ color: primary }} />
            {q}
          </Link>
        ))}
      </div>
    </section>
  );
}

/* ---------- Last updated meta (E-E-A-T signal) ---------- */
export function LastUpdatedBadge({ date, design }) {
  if (!date) return null;
  const primary = design?.brand?.primary_color || "#B84B31";
  const d = new Date(date);
  if (isNaN(d.getTime())) return null;
  const formatted = d.toLocaleDateString("fr-FR", { day: "numeric", month: "long", year: "numeric" });
  return (
    <div className="text-xs text-neutral-500 flex items-center gap-2 mt-4" data-testid="last-updated">
      <PlayCircle size={12} weight="duotone" style={{ color: primary }} />
      Fiche mise à jour le <time dateTime={d.toISOString()}>{formatted}</time>
    </div>
  );
}
