import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import axios from "axios";
import { Sparkle } from "@phosphor-icons/react";
import { t } from "../../lib/i18n";
import { BACKEND_URL, designAccents } from "./storefrontUtils";
import ProductCard from "./ProductCard";
import { hasAiImage } from "../../lib/productImage";

/**
 * Upsells : accessoires complémentaires sélectionnés à l'étape 3 du cockpit
 * et associés au produit principal affiché (ou à ceux d'une commande passée).
 *
 * Phase 2.5 Tâche F — utilise `<ProductCard variant="default">`, exactement
 * le même composant que la Home (proportions, typos, CTA double, micro-anim).
 *
 * Source API :
 *   GET  /public/sites/{id}/products/{pid}/upsells      (fiche produit)
 *   POST /public/sites/{id}/upsells-for-products        (post-purchase)
 */
export default function UpsellsRecommendations({
  mode = "product",       // "product" | "post_purchase"
  productId = null,
  productIds = null,      // array for post_purchase
  title = null,
  subtitle = null,
  lang = "fr",
  design = null,
  onAddToCart = null,     // eslint-disable-line no-unused-vars
}) {
  const { siteId } = useParams();
  const { primary, fontHeading } = designAccents(design);
  const [items, setItems] = useState([]);

  useEffect(() => {
    if (!siteId) return;
    if (mode === "product" && productId) {
      axios
        .get(`${BACKEND_URL}/api/public/sites/${siteId}/products/${productId}/upsells?limit=6`)
        .then(({ data }) => {
          // Phase 2.5 Tâche F — filtre strict : ne garder que les produits
          // avec image IA premium (pas d'images AliExpress watermarkées).
          const arr = (Array.isArray(data) ? data : []).filter(hasAiImage);
          setItems(arr);
        })
        .catch(() => setItems([]));
    } else if (mode === "post_purchase" && productIds?.length) {
      axios
        .post(`${BACKEND_URL}/api/public/sites/${siteId}/upsells-for-products?limit=8`, {
          product_ids: productIds,
        })
        .then(({ data }) => {
          const arr = (Array.isArray(data) ? data : []).filter(hasAiImage);
          setItems(arr);
        })
        .catch(() => setItems([]));
    } else {
      setItems([]);
    }
  }, [siteId, mode, productId, JSON.stringify(productIds || [])]);

  if (!items.length) return null;

  const resolvedTitle =
    title ||
    (mode === "post_purchase"
      ? t(lang, "upsell_complete_order")
      : t(lang, "upsell_often_bought"));
  const resolvedSubtitle =
    subtitle ||
    (mode === "post_purchase"
      ? t(lang, "upsell_subtitle_post")
      : t(lang, "upsell_subtitle_related"));

  return (
    <section
      className="py-14 md:py-16 border-t"
      style={{ borderColor: "#E7E5E4" }}
      data-testid={`upsells-${mode}`}
    >
      <div className="flex items-end justify-between gap-4 mb-10 flex-wrap">
        <div>
          <div
            className="text-[11px] uppercase tracking-[0.2em] mb-3 flex items-center gap-2"
            style={{ color: primary }}
          >
            <Sparkle size={12} weight="fill" /> Recommandation
          </div>
          <h2
            className="text-3xl md:text-4xl"
            style={{ fontFamily: `"${fontHeading}", serif`, color: "#1C1917" }}
          >
            {resolvedTitle}
          </h2>
          <p className="text-sm text-neutral-500 mt-2 max-w-xl">{resolvedSubtitle}</p>
        </div>
      </div>

      <div
        className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5 md:gap-6"
        data-testid="upsells-carousel"
      >
        {items.slice(0, 3).map((p) => (
          <ProductCard
            key={p.id}
            product={p}
            siteId={siteId}
            lang={lang}
            design={design}
            variant="default"
            testId={`upsell-card-${p.id}`}
          />
        ))}
      </div>
    </section>
  );
}
