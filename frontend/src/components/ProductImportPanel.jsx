import React, { useEffect, useState, useCallback, useRef, useImperativeHandle, forwardRef } from "react";
import {
  MagnifyingGlass, LinkSimple, CheckCircle, XCircle, Warning, Globe,
  Info, ArrowClockwise, Package, Stack, X as XIcon,
} from "@phosphor-icons/react";
import { api, apiCall } from "../lib/api";

/**
 * ProductImportPanel — Chantier 2 & 4 (Altiaro).
 *
 * Composant unifié utilisé par :
 *   - /sites/:id/sourcing   (variant="main", étape 2)
 *   - /sites/:id/upsells    (variant="upsell", étape 3)
 *
 * Rendu :
 *   1. Encadré pédagogique
 *   2. 2 CTA externes (AliExpress + CJ) pré-remplis avec niche (+ "accessoires" si upsell)
 *   3. Champ "Coller URL produit" → preview backend → affichage checks → import
 *   4. Tableau produits du site avec colonne Couverture Pays
 *   5. (uniquement variant="main") bouton discret "Forcer passage sans couverture complète"
 *      + double confirmation modal
 *
 * Props :
 *   siteId       : string         — id du site
 *   variant      : "main"|"upsell"
 *   nicheHint    : string?        — niche/produit principal pour pré-remplir les liens
 *   targetCountries : string[]    — pays cibles du site (ex: ["FR","DE"])
 */
const FLAG_BY_CODE = {
  FR: "🇫🇷", DE: "🇩🇪", UK: "🇬🇧", GB: "🇬🇧", BE: "🇧🇪",
  NL: "🇳🇱", CH: "🇨🇭", IT: "🇮🇹", ES: "🇪🇸", LU: "🇱🇺",
};

const COUNTRY_NAME = {
  FR: "France", DE: "Allemagne", UK: "Royaume-Uni", GB: "Royaume-Uni",
  BE: "Belgique", NL: "Pays-Bas", CH: "Suisse", IT: "Italie", ES: "Espagne",
};

const flag = (cc) => FLAG_BY_CODE[cc?.toUpperCase()] || cc;

export default function ProductImportPanel({
  siteId,
  variant = "main",
  nicheHint = "",
  targetCountries = [],
}) {
  const isUpsell = variant === "upsell";
  const [products, setProducts] = useState([]);
  const [loadingProducts, setLoadingProducts] = useState(true);
  const [url, setUrl] = useState("");
  const [preview, setPreview] = useState(null);
  const [previewing, setPreviewing] = useState(false);
  const [importing, setImporting] = useState(false);
  const [previewError, setPreviewError] = useState("");
  const [showForcePartial, setShowForcePartial] = useState(false);
  const [forcePartialMeta, setForcePartialMeta] = useState(null);

  const loadProducts = useCallback(async () => {
    setLoadingProducts(true);
    const filter = isUpsell
      ? "?type=upsell,accessory"
      : "";
    const { data } = await apiCall(() =>
      api.get(`/sites/${siteId}/products${filter}`)
    );
    setLoadingProducts(false);
    if (!data) return;
    const items = Array.isArray(data) ? data : (data.products || data.items || []);
    if (isUpsell) {
      setProducts(
        items.filter(
          (p) =>
            p.type === "upsell" || p.type === "accessory" ||
            p.is_upsell === true || p.role === "upsell"
        )
      );
    } else {
      setProducts(items);
    }
  }, [siteId, isUpsell]);

  const loadForcePartial = useCallback(async () => {
    const { data } = await apiCall(() => api.get(`/sites/${siteId}`));
    if (data?.import_force_partial_meta) {
      setForcePartialMeta(data.import_force_partial_meta);
    } else {
      setForcePartialMeta(null);
    }
  }, [siteId]);

  useEffect(() => {
    loadProducts();
    if (!isUpsell) loadForcePartial();
  }, [loadProducts, loadForcePartial, isUpsell]);

  // --- Preview via backend ---
  const handlePreview = async () => {
    setPreviewError("");
    setPreview(null);
    const cleaned = url.trim();
    if (!cleaned) return;
    setPreviewing(true);
    const { data, error, rawDetail } = await apiCall(() =>
      api.post(`/sites/${siteId}/sourcing/preview-url`, { url: cleaned })
    );
    setPreviewing(false);
    if (error || !data) {
      const detail = rawDetail?.detail;
      if (typeof detail === "object" && detail?.error === "step_not_completed") {
        setPreviewError(detail.message || error || "Étape précédente non complétée.");
      } else {
        setPreviewError(
          typeof detail === "string" ? detail :
          error || "Impossible de prévisualiser cette URL (AliExpress/CJ indisponible ou URL invalide)."
        );
      }
      return;
    }
    setPreview(data);
  };

  const handleImport = async () => {
    if (!preview) return;
    setImporting(true);
    const payload = {
      url: preview.url,
      role: isUpsell ? "upsell" : "main",
      product_type: isUpsell ? "upsell" : "main",
      // On considère comme "livré" uniquement les pays où shipping.available=true
      shipping_countries: Object.entries(preview.shipping_by_country || {})
        .filter(([, v]) => v?.available)
        .map(([cc]) => cc),
    };
    const { data, error, rawDetail } = await apiCall(() =>
      api.post(`/sites/${siteId}/sourcing/import-by-url`, payload)
    );
    setImporting(false);
    if (error) {
      const detail = rawDetail?.detail;
      window.alert(typeof detail === "string" ? detail :
        (detail?.message || error || "Import échoué."));
      return;
    }
    setPreview(null);
    setUrl("");
    await loadProducts();
    if (!isUpsell) await loadForcePartial();
  };

  // --- External search links ---
  const searchTerm = (isUpsell ? `${nicheHint} accessoires` : nicheHint).trim() || "produits senior";
  const aeUrl = `https://fr.aliexpress.com/wholesale?SearchText=${encodeURIComponent(searchTerm)}`;
  const cjUrl = `https://cjdropshipping.com/search.html?searchType=1&keywords=${encodeURIComponent(searchTerm)}`;

  // --- Coverage aggregation for the whole catalog ---
  const coverageByCountry = React.useMemo(() => {
    const map = {};
    for (const cc of targetCountries) map[cc] = 0;
    for (const p of products) {
      for (const cc of (p.shipping_countries || [])) {
        if (map[cc] !== undefined) map[cc] += 1;
      }
    }
    return map;
  }, [products, targetCountries]);

  const missingCountries = targetCountries.filter((cc) => coverageByCountry[cc] === 0);

  return (
    <div className="space-y-6" data-testid={`product-import-${variant}`}>
      {/* 1. Encadré pédagogique */}
      <div
        className={`p-5 rounded-xl border ${
          isUpsell
            ? "bg-violet-50 border-violet-200"
            : "bg-sky-50 border-sky-200"
        }`}
        data-testid="import-edu-banner"
      >
        <div className="flex items-start gap-3">
          <Info
            size={22}
            weight="duotone"
            className={isUpsell ? "text-violet-600" : "text-sky-600"}
          />
          <div className="flex-1 text-sm">
            <div className={`font-semibold mb-1 ${isUpsell ? "text-violet-900" : "text-sky-900"}`}>
              {isUpsell ? "Règles Upsells & accessoires" : "Règles Import catalogue"}
            </div>
            {isUpsell ? (
              <ul className="text-violet-900/90 space-y-1 leading-relaxed">
                <li>• <strong>Upsells = accessoires complémentaires</strong> au produit principal. Ex. pour un fauteuil releveur : coussins ergonomiques, housse de protection, télécommande de rechange, repose-pieds.</li>
                <li>• Minimum <strong>3 upsells</strong> pour débloquer l'étape prévisionnel.</li>
                <li>• <strong>Livraison gratuite</strong> et <strong>livrable dans tous les pays</strong> que tu vends, comme pour l'import principal.</li>
              </ul>
            ) : (
              <ul className="text-sky-900/90 space-y-1 leading-relaxed">
                <li>• Importe <strong>uniquement des produits avec livraison gratuite</strong> — la livraison payante grignote ta marge.</li>
                <li>• Chaque produit doit être <strong>livrable dans tous les pays que tu vends</strong> ({targetCountries.map(flag).join(" ")}). Sinon tes clients ne pourront pas commander.</li>
                <li>• Minimum <strong>5 produits</strong> pour débloquer l'étape upsells.</li>
                <li>• Privilégie les produits à <strong>marge &gt; 50%</strong> pour absorber les coûts Ads.</li>
              </ul>
            )}
          </div>
        </div>
      </div>

      {/* 2. CTA externes */}
      <div className="grid md:grid-cols-2 gap-3">
        <a
          href={aeUrl}
          target="_blank"
          rel="noopener noreferrer"
          data-testid="cta-aliexpress"
          className="flex items-center gap-3 p-4 rounded-xl bg-white border border-neutral-200 hover:border-[#FF4747] hover:shadow-md transition group"
        >
          <div className="w-11 h-11 rounded-lg bg-[#FFF1F0] flex items-center justify-center flex-shrink-0">
            <MagnifyingGlass size={22} weight="duotone" color="#FF4747" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-sm font-semibold text-neutral-900 group-hover:text-[#FF4747]">
              Rechercher sur AliExpress
            </div>
            <div className="text-xs text-neutral-500 truncate">
              Recherche pré-remplie : «&nbsp;{searchTerm}&nbsp;»
            </div>
          </div>
        </a>

        <a
          href={cjUrl}
          target="_blank"
          rel="noopener noreferrer"
          data-testid="cta-cj"
          className="flex items-center gap-3 p-4 rounded-xl bg-white border border-neutral-200 hover:border-[#00A3FF] hover:shadow-md transition group"
        >
          <div className="w-11 h-11 rounded-lg bg-[#EFF8FF] flex items-center justify-center flex-shrink-0">
            <MagnifyingGlass size={22} weight="duotone" color="#00A3FF" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-sm font-semibold text-neutral-900 group-hover:text-[#00A3FF]">
              Rechercher sur CJ Dropshipping
            </div>
            <div className="text-xs text-neutral-500 truncate">
              Recherche pré-remplie : «&nbsp;{searchTerm}&nbsp;»
            </div>
          </div>
        </a>
      </div>

      {/* 3. Champ collage URL */}
      <div className="bg-white border border-neutral-200 rounded-xl p-5">
        <div className="flex items-center gap-2 mb-3">
          <LinkSimple size={18} weight="duotone" className="text-neutral-700" />
          <h3 className="text-sm font-semibold text-neutral-900">
            Coller l'URL d'un produit AliExpress ou CJ
          </h3>
        </div>
        <div className="flex flex-col md:flex-row gap-2">
          <input
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://fr.aliexpress.com/item/1005006…  ou  https://www.cjdropshipping.com/product/…"
            data-testid="import-url-input"
            className="flex-1 px-4 py-2.5 border border-neutral-300 rounded-lg text-sm focus:outline-none focus:border-neutral-900"
            onKeyDown={(e) => {
              if (e.key === "Enter" && url.trim() && !previewing) handlePreview();
            }}
          />
          <button
            onClick={handlePreview}
            disabled={previewing || !url.trim()}
            data-testid="import-url-preview-btn"
            className="h-[44px] px-5 rounded-lg bg-neutral-900 hover:bg-neutral-800 text-white text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap flex items-center gap-2"
          >
            {previewing ? <ArrowClockwise size={14} className="animate-spin" /> : null}
            {previewing ? "Analyse…" : "Prévisualiser"}
          </button>
        </div>
        {previewError && (
          <div
            data-testid="import-url-error"
            className="mt-3 p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-800 text-sm flex items-start gap-2"
          >
            <Warning size={16} weight="duotone" className="flex-shrink-0 mt-0.5" />
            <span>{previewError}</span>
          </div>
        )}

        {preview && (
          <PreviewCard
            preview={preview}
            targetCountries={targetCountries}
            onImport={handleImport}
            onCancel={() => { setPreview(null); setUrl(""); }}
            importing={importing}
            variant={variant}
          />
        )}
      </div>

      {/* 4. Tableau produits avec couverture pays */}
      <div className="bg-white border border-neutral-200 rounded-xl p-5">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-neutral-900 flex items-center gap-2">
            {isUpsell ? <Stack size={16} weight="duotone" /> : <Package size={16} weight="duotone" />}
            {isUpsell ? "Upsells & accessoires importés" : "Produits importés"}
            <span className="text-xs text-neutral-500 font-normal">({products.length})</span>
          </h3>
          {!isUpsell && targetCountries.length > 0 && (
            <div className="flex items-center gap-2 text-xs text-neutral-600">
              <Globe size={14} />
              Couverture :
              {targetCountries.map((cc) => (
                <span
                  key={cc}
                  title={`${COUNTRY_NAME[cc] || cc} : ${coverageByCountry[cc]} produits livrables`}
                  className={`inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded ${
                    coverageByCountry[cc] > 0
                      ? "bg-emerald-50 text-emerald-800"
                      : "bg-rose-50 text-rose-800"
                  }`}
                >
                  {flag(cc)} {coverageByCountry[cc] > 0 ? `✅ ${coverageByCountry[cc]}` : "❌ 0"}
                </span>
              ))}
            </div>
          )}
        </div>
        {loadingProducts ? (
          <div className="text-sm text-neutral-500 py-6 text-center">Chargement…</div>
        ) : products.length === 0 ? (
          <div className="text-sm text-neutral-500 py-6 text-center">
            {isUpsell ? "Aucun upsell pour l'instant. Colle une URL ci-dessus."
                      : "Aucun produit pour l'instant. Colle une URL ci-dessus ou recherche chez AE/CJ."}
          </div>
        ) : (
          <ProductsTable products={products} targetCountries={targetCountries} variant={variant} />
        )}
      </div>

      {/* 5. Bouton force-partial (import main uniquement) */}
      {!isUpsell && products.length >= 5 && missingCountries.length > 0 && !forcePartialMeta && (
        <div className="flex justify-end">
          <button
            onClick={() => setShowForcePartial(true)}
            data-testid="force-partial-btn"
            className="text-xs text-neutral-500 hover:text-rose-600 underline underline-offset-4 decoration-neutral-300 hover:decoration-rose-300"
          >
            Passer à l'étape suivante sans couvrir {missingCountries.map((cc) => COUNTRY_NAME[cc]).join(" / ")} →
          </button>
        </div>
      )}

      {forcePartialMeta && (
        <div
          data-testid="force-partial-banner"
          className="p-4 rounded-xl bg-amber-50 border border-amber-200 flex items-start gap-3"
        >
          <Warning size={20} weight="duotone" className="text-amber-700 flex-shrink-0 mt-0.5" />
          <div className="flex-1 text-sm">
            <div className="font-semibold text-amber-900 mb-0.5">
              Couverture partielle assumée
            </div>
            <div className="text-amber-800 leading-relaxed">
              Tu as accepté de lancer sans couvrir {(forcePartialMeta.missing_countries_at_time || []).map((cc) => COUNTRY_NAME[cc] || cc).join(", ")}.
              Tes clients dans ces pays ne pourront pas commander.
            </div>
          </div>
          <button
            onClick={async () => {
              await apiCall(() => api.post(`/sites/${siteId}/steps/import/revoke-force-partial`));
              await loadForcePartial();
            }}
            className="h-9 px-3 rounded-lg bg-white border border-amber-300 hover:bg-amber-100 text-xs text-amber-900 font-medium whitespace-nowrap"
          >
            Annuler
          </button>
        </div>
      )}

      {showForcePartial && (
        <ForcePartialModal
          missingCountries={missingCountries}
          onClose={() => setShowForcePartial(false)}
          onConfirmed={async () => {
            await apiCall(() => api.post(`/sites/${siteId}/steps/import/force-partial`));
            setShowForcePartial(false);
            await loadForcePartial();
          }}
        />
      )}
    </div>
  );
}

// ─── PreviewCard ─────────────────────────────────────
function PreviewCard({ preview, targetCountries, onImport, onCancel, importing, variant }) {
  const hasCoverageIssue = preview.missing_countries && preview.missing_countries.length > 0;
  return (
    <div
      data-testid="import-preview-card"
      className="mt-4 p-4 rounded-xl bg-neutral-50 border border-neutral-200"
    >
      <div className="flex gap-4 flex-col md:flex-row">
        {preview.primary_image && (
          <img
            src={preview.primary_image}
            alt={preview.title}
            className="w-full md:w-40 h-40 rounded-lg object-cover bg-white border border-neutral-200 flex-shrink-0"
          />
        )}
        <div className="flex-1 min-w-0">
          <div className="text-xs uppercase tracking-widest text-neutral-500 mb-1">
            {preview.provider} · {preview.product_id}
          </div>
          <h4 className="text-sm font-semibold text-neutral-900 mb-3 line-clamp-2">{preview.title}</h4>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
            <Stat label="Prix achat" value={`${preview.cost_eur}€`} />
            <Stat label="Livraison" value={preview.free_shipping ? "Gratuite" : `${preview.shipping_cost_eur}€`} tone={preview.free_shipping ? "success" : "warn"} />
            <Stat label="Prix suggéré" value={`${preview.suggested_price_eur}€`} />
            <Stat label="Marge" value={`${preview.margin_pct}%`} tone={preview.margin_pct >= 50 ? "success" : "warn"} />
          </div>

          {targetCountries.length > 0 && (
            <div className="mt-4 bg-white rounded-lg border border-neutral-200 p-3">
              <div className="text-xs uppercase tracking-widest text-neutral-500 mb-2">
                Livraison par pays cible
              </div>
              <div className="flex flex-wrap gap-2">
                {targetCountries.map((cc) => {
                  const s = (preview.shipping_by_country || {})[cc];
                  const ok = s?.available;
                  return (
                    <div
                      key={cc}
                      data-testid={`coverage-${cc}`}
                      className={`flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-medium ${
                        ok ? "bg-emerald-50 text-emerald-900" : "bg-rose-50 text-rose-900"
                      }`}
                    >
                      <span>{flag(cc)}</span>
                      <span>{COUNTRY_NAME[cc] || cc}</span>
                      {ok ? <CheckCircle size={12} weight="fill" /> : <XCircle size={12} weight="fill" />}
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Warnings */}
      {(preview.warnings || []).length > 0 && (
        <div className="mt-4 space-y-2">
          {preview.warnings.map((w, i) => (
            <div
              key={i}
              data-testid={`preview-warning-${i}`}
              className="p-3 rounded-lg bg-amber-50 border border-amber-200 text-sm text-amber-900 flex items-start gap-2"
            >
              <Warning size={16} weight="duotone" className="flex-shrink-0 mt-0.5" />
              <span>{w}</span>
            </div>
          ))}
        </div>
      )}

      <div className="mt-4 flex items-center gap-2 justify-end flex-wrap">
        {hasCoverageIssue && (
          <div className="text-xs text-amber-800 mr-auto" data-testid="preview-coverage-note">
            Ce produit peut être importé mais ne couvrira pas {preview.missing_countries.join(", ")}.
          </div>
        )}
        <button
          onClick={onCancel}
          className="h-9 px-4 rounded-lg bg-white border border-neutral-300 hover:bg-neutral-50 text-sm font-medium text-neutral-700"
        >
          Annuler
        </button>
        <button
          onClick={onImport}
          disabled={importing}
          data-testid="import-confirm-btn"
          className="h-9 px-4 rounded-lg bg-neutral-900 hover:bg-neutral-800 text-white text-sm font-medium disabled:opacity-50 flex items-center gap-2"
        >
          {importing && <ArrowClockwise size={14} className="animate-spin" />}
          {importing ? "Import en cours…" : (variant === "upsell" ? "Importer cet upsell" : "Importer ce produit")}
        </button>
      </div>
    </div>
  );
}

function Stat({ label, value, tone = "neutral" }) {
  const cls = {
    neutral: "bg-white border-neutral-200 text-neutral-900",
    success: "bg-emerald-50 border-emerald-200 text-emerald-900",
    warn:    "bg-amber-50 border-amber-200 text-amber-900",
  }[tone];
  return (
    <div className={`rounded-lg border px-3 py-2 ${cls}`}>
      <div className="text-[10px] uppercase tracking-widest opacity-70">{label}</div>
      <div className="text-sm font-semibold">{value}</div>
    </div>
  );
}

// ─── ProductsTable ───────────────────────────────────
function ProductsTable({ products, targetCountries, variant }) {
  return (
    <div className="overflow-x-auto -mx-5">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-[10px] uppercase tracking-widest text-neutral-500 border-b border-neutral-200">
            <th className="text-left px-5 py-2 font-medium">Produit</th>
            <th className="text-left px-3 py-2 font-medium">Prix</th>
            <th className="text-left px-3 py-2 font-medium">Marge</th>
            {targetCountries.length > 0 && (
              <th className="text-left px-3 py-2 font-medium">Couverture pays</th>
            )}
            <th className="text-left px-3 py-2 font-medium">Source</th>
          </tr>
        </thead>
        <tbody>
          {products.map((p) => {
            const shipCountries = (p.shipping_countries || []).map((c) => c.toUpperCase());
            return (
              <tr key={p.id} className="border-b border-neutral-100 hover:bg-neutral-50">
                <td className="px-5 py-2">
                  <div className="flex items-center gap-2">
                    {p.image_url && (
                      <img src={p.image_url} alt="" className="w-8 h-8 rounded object-cover flex-shrink-0" />
                    )}
                    <div className="max-w-[280px]">
                      <div className="text-[13px] font-medium text-neutral-900 truncate" title={p.name?.fr || p.name || p.title || "—"}>
                        {p.name?.fr || p.name || p.title || p.sku || "—"}
                      </div>
                      {p.sku && <div className="text-[10px] text-neutral-400 font-mono">{p.sku}</div>}
                    </div>
                  </div>
                </td>
                <td className="px-3 py-2 whitespace-nowrap">
                  {p.price ? `${p.price}€` : "—"}
                </td>
                <td className="px-3 py-2 whitespace-nowrap text-xs text-neutral-600">
                  {p.margin_pct ? `${p.margin_pct}%` : "—"}
                </td>
                {targetCountries.length > 0 && (
                  <td className="px-3 py-2">
                    <div className="flex items-center gap-1">
                      {targetCountries.map((cc) => {
                        const ok = shipCountries.includes(cc);
                        return (
                          <span
                            key={cc}
                            title={`${COUNTRY_NAME[cc] || cc} : ${ok ? "livrable" : "non livrable"}`}
                            className={`text-xs ${ok ? "text-emerald-700" : "text-rose-600"}`}
                          >
                            {flag(cc)}{ok ? "✅" : "❌"}
                          </span>
                        );
                      })}
                    </div>
                  </td>
                )}
                <td className="px-3 py-2 text-xs text-neutral-500">
                  {p.provider || p.source || (p.source_url?.includes("aliexpress") ? "AE" :
                   p.source_url?.includes("cjdrop") ? "CJ" : "—")}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// ─── ForcePartialModal ───────────────────────────────
function ForcePartialModal({ missingCountries, onClose, onConfirmed }) {
  const [step, setStep] = useState(1);
  const [typed, setTyped] = useState("");
  const expected = missingCountries.map((cc) => COUNTRY_NAME[cc] || cc).join(", ");
  const match = typed.trim().toLowerCase() === expected.toLowerCase();

  return (
    <div
      className="fixed inset-0 z-[100] bg-black/50 backdrop-blur-sm flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
        data-testid="force-partial-modal"
      >
        <div className="flex items-start justify-between mb-4">
          <h3 className="text-lg font-semibold text-neutral-900 flex items-center gap-2">
            <Warning size={22} weight="duotone" className="text-rose-600" />
            Couverture partielle
          </h3>
          <button onClick={onClose} className="w-8 h-8 rounded-lg hover:bg-neutral-100 flex items-center justify-center">
            <XIcon size={16} />
          </button>
        </div>

        {step === 1 && (
          <>
            <p className="text-sm text-neutral-700 mb-4 leading-relaxed">
              Tu vas passer à l'étape suivante <strong>sans couvrir</strong>&nbsp;:
            </p>
            <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 mb-4 text-sm">
              {missingCountries.map((cc) => (
                <div key={cc} className="font-medium text-rose-900">
                  {flag(cc)} {COUNTRY_NAME[cc] || cc}
                </div>
              ))}
            </div>
            <p className="text-sm text-neutral-700 mb-5 leading-relaxed">
              <strong>Conséquences&nbsp;:</strong> tous tes clients dans ces pays arriveront sur ton site,
              ajouteront des produits au panier, mais <strong>ne pourront pas finaliser leur commande</strong>
              (message d'erreur à l'étape paiement). Ton budget Ads ciblant ces pays sera dépensé en pure perte.
            </p>
            <div className="flex gap-2 justify-end">
              <button
                onClick={onClose}
                className="h-10 px-4 rounded-lg bg-white border border-neutral-300 hover:bg-neutral-50 text-sm font-medium"
              >
                Non, ajouter un produit
              </button>
              <button
                onClick={() => setStep(2)}
                data-testid="force-partial-step1-next"
                className="h-10 px-4 rounded-lg bg-rose-600 hover:bg-rose-700 text-white text-sm font-medium"
              >
                Continuer quand même →
              </button>
            </div>
          </>
        )}

        {step === 2 && (
          <>
            <p className="text-sm text-neutral-700 mb-4 leading-relaxed">
              Pour confirmer, tape le nom des pays manquants <strong>exactement</strong> :
            </p>
            <div className="p-3 rounded-lg bg-neutral-100 mb-3 font-mono text-sm text-neutral-700">
              {expected}
            </div>
            <input
              type="text"
              value={typed}
              onChange={(e) => setTyped(e.target.value)}
              placeholder="Tape ici…"
              data-testid="force-partial-confirm-input"
              className="w-full px-3 py-2 border border-neutral-300 rounded-lg text-sm focus:outline-none focus:border-neutral-900 mb-5"
              autoFocus
            />
            <div className="flex gap-2 justify-end">
              <button
                onClick={() => { setStep(1); setTyped(""); }}
                className="h-10 px-4 rounded-lg bg-white border border-neutral-300 hover:bg-neutral-50 text-sm font-medium"
              >
                Retour
              </button>
              <button
                onClick={onConfirmed}
                disabled={!match}
                data-testid="force-partial-confirm-btn"
                className="h-10 px-4 rounded-lg bg-rose-600 hover:bg-rose-700 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-medium"
              >
                Je confirme, passer à l'étape suivante
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
