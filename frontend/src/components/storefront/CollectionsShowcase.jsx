/**
 * Fix 7 — CollectionsShowcase 100% dynamique selon le nombre RÉEL de
 * collections du site (lue depuis l'API publique au mount).
 *
 * Logique :
 *   0 collection → la section ne s'affiche pas (return null)
 *   1 collection → carte unique premium "héro" pleine largeur
 *   2 collections → grille 2 colonnes desktop, 1 col mobile
 *   3 collections → grille 3 colonnes desktop, 1 col mobile
 *   4+ collections → grille 4 colonnes desktop, scroll horizontal mobile
 *
 * Plus aucun fallback Unsplash (Lot A2). Le composant lit l'image IA cover
 * de chaque collection depuis l'API.
 */
import React, { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import axios from "axios";
import { ArrowRight } from "@phosphor-icons/react";
import { pickLang, t } from "../../lib/i18n";
import { BACKEND_URL, designAccents } from "./storefrontUtils";

function CollectionCard({ c, primary, fontHeading, lang, siteId, big = false }) {
  const title = pickLang(c.title || c.name, lang) || c.title || c.name || c.slug;
  const description = pickLang(c.description, lang) || c.description || "";
  const image = c.image || c.cover_image || null;
  const aspect = big ? "aspect-[16/9] md:aspect-[21/9]" : "aspect-[4/5]";
  return (
    <Link
      to={`/shop/${siteId}/collection/${c.slug}`}
      data-testid={`collection-card-${c.slug}`}
      className="group block"
    >
      <div className={`relative overflow-hidden rounded-sm bg-[#F5F2EB] ${aspect}`}>
        {image && (
          <img
            src={image.startsWith("http") ? image : `${BACKEND_URL}${image}`}
            alt={title}
            loading="lazy"
            className="absolute inset-0 w-full h-full object-cover transition-transform duration-700 ease-out group-hover:scale-[1.04]"
          />
        )}
        {/* Overlay subtil pour la lisibilité du titre */}
        <div className="absolute inset-0 bg-gradient-to-t from-black/35 via-black/0 to-transparent pointer-events-none" />
        {/* Title en bas, premium minimal */}
        <div className="absolute inset-0 flex flex-col justify-end p-6 md:p-8 lg:p-10">
          <h3
            className={`text-white ${big ? "text-[42px] md:text-[64px] lg:text-[80px]" : "text-[28px] md:text-[34px]"} leading-[1.05] tracking-[-0.01em]`}
            style={{ fontFamily: `"${fontHeading}", serif`, fontWeight: 400 }}
          >
            {title}
          </h3>
          {description && (
            <p className={`mt-3 text-white/90 ${big ? "text-base md:text-lg max-w-2xl" : "text-sm"} font-light`}>
              {description.slice(0, big ? 220 : 90)}
            </p>
          )}
          <span className="mt-5 inline-flex items-center gap-2 text-white text-[12px] uppercase tracking-[0.3em] after:h-px after:bg-white/60 after:w-8 group-hover:after:w-12 after:transition-all">
            {big
              ? t(lang, "collections_cta_big") || "Découvrir nos références"
              : t(lang, "collections_cta") || "Découvrir"}
            <ArrowRight size={12} weight="bold" />
          </span>
        </div>
      </div>
    </Link>
  );
}

export default function CollectionsShowcase({ collections: legacyCollections, lang = "fr", design }) {
  const { siteId } = useParams();
  const { primary, fontHeading } = designAccents(design);
  const [collections, setCollections] = useState(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const r = await axios.get(`${BACKEND_URL}/api/public/sites/${siteId}/collections`);
        if (!cancelled && Array.isArray(r.data)) setCollections(r.data);
      } catch {
        if (!cancelled) setCollections(legacyCollections || []);
      }
    })();
    return () => { cancelled = true; };
  }, [siteId, legacyCollections]);

  if (collections === null) return null;
  if (!collections || collections.length === 0) return null;

  const count = collections.length;
  const heading2 = t(lang, "collections_heading_line2") || "Nos collections";

  let gridCls;
  if (count === 1) gridCls = "grid grid-cols-1";
  else if (count === 2) gridCls = "grid grid-cols-1 md:grid-cols-2 gap-6 md:gap-8";
  else if (count === 3) gridCls = "grid grid-cols-1 md:grid-cols-3 gap-6 md:gap-8";
  else gridCls = "grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 md:gap-8";

  return (
    <section className="py-20 md:py-32 px-6 bg-white" data-testid="storefront-collections">
      <div className="max-w-7xl mx-auto">
        <div className="mb-12 md:mb-16">
          <div className="flex items-center gap-3 mb-5">
            <span className="h-px w-10" style={{ background: primary }} />
            <span className="text-[11px] uppercase tracking-[0.4em]" style={{ color: primary }}>
              {t(lang, "collections_eyebrow") || "Nos sélections"}
            </span>
          </div>
          <h2
            className="text-[40px] md:text-[56px] lg:text-[64px] leading-[1.02] tracking-[-0.02em]"
            style={{ fontFamily: `"${fontHeading}", serif`, color: primary }}
          >
            {count === 1 ? t(lang, "collections_heading_single") || heading2 : heading2}
          </h2>
        </div>

        <div className={gridCls}>
          {collections.map((c) => (
            <CollectionCard
              key={c.slug}
              c={c}
              primary={primary}
              fontHeading={fontHeading}
              lang={lang}
              siteId={siteId}
              big={count === 1}
            />
          ))}
        </div>
      </div>
    </section>
  );
}
