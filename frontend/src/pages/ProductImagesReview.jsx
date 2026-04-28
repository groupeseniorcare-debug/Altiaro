/**
 * Phase 2.7.3 — Panneau de revue des images IA + régénération ciblée.
 *
 * Le concepteur voit toutes les images générées pour ses produits, par
 * variante (couleur) × style (studio_main, lifestyle, closeup, in_use, …).
 * Un clic sur "Régénérer" ouvre un modal avec un champ texte libre
 * ("la personne doit être plus âgée…") qui sera ajouté au brief Nano Banana.
 *
 * Coût ~0,06$ par régénération (Nano Banana ~0,05$ + Gemini Vision QA ~0,008$).
 *
 * Branché en route dédiée `/sites/:id/images-review` (cockpit étape 5).
 */
import React, { useEffect, useMemo, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { ArrowLeft, ArrowsClockwise, CheckCircle, WarningCircle, X } from "@phosphor-icons/react";
import { api, apiCall } from "../lib/api";
import Layout from "../components/Layout";

const STYLE_LABELS = {
  studio_main:    "Studio principal (3/4)",
  studio_card:    "Studio carré (face)",
  side_profile:   "Profil 90°",
  lifestyle:      "Lifestyle intérieur",
  wide_lifestyle: "Lifestyle panoramique",
  closeup:        "Macro tissu",
  detail:         "Détail technique",
  in_use:         "En utilisation",
};

function pickName(p) {
  const n = p?.name;
  if (typeof n === "string") return n;
  if (n && typeof n === "object") return n.fr || n.en || Object.values(n)[0] || "Sans nom";
  return "Sans nom";
}

function imageUrl(img) {
  const raw = img?.url || "";
  if (!raw) return "";
  if (raw.startsWith("http") || raw.startsWith("data:")) return raw;
  return `${process.env.REACT_APP_BACKEND_URL || ""}${raw}`;
}

export default function ProductImagesReview() {
  const { id: siteId } = useParams();
  const navigate = useNavigate();
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState(null); // { product, variant_color, style, image }

  const load = async () => {
    setLoading(true);
    const { data } = await apiCall(() => api.get(`/sites/${siteId}/products`));
    setProducts(Array.isArray(data) ? data : (data?.items || []));
    setLoading(false);
  };

  useEffect(() => { load(); }, [siteId]);

  const productsWithImages = useMemo(
    () => (products || []).filter((p) => {
      const gibv = p?.generated_images_by_variant;
      return gibv && typeof gibv === "object" && Object.keys(gibv).length > 0;
    }),
    [products]
  );

  return (
    <Layout>
      <div className="p-6 md:p-10 max-w-[1400px] mx-auto w-full">
        <button
          onClick={() => navigate(`/sites/${siteId}`)}
          className="flex items-center gap-2 text-sm text-neutral-500 hover:text-neutral-900 mb-5 transition"
          data-testid="back-to-cockpit"
        >
          <ArrowLeft size={16} /> Retour au cockpit
        </button>

        <header className="mb-8">
          <div className="text-[11px] uppercase tracking-[0.2em] text-neutral-500 mb-2">Étape 5 · Images produits</div>
          <h1 className="text-3xl md:text-4xl font-light text-neutral-900 tracking-tight">
            Revoir et régénérer les visuels IA
          </h1>
          <p className="text-sm text-neutral-600 max-w-2xl mt-3 leading-relaxed">
            Pour chaque produit × variante × style, vous pouvez régénérer une image qui ne vous
            convient pas. L'IA reçoit votre précision (optionnelle) en plus du brief premium.
            <span className="ml-1 text-neutral-400">Coût ~0,06 $ par régénération.</span>
          </p>
        </header>

        {loading && (
          <div className="text-sm text-neutral-500">Chargement du catalogue…</div>
        )}

        {!loading && productsWithImages.length === 0 && (
          <div className="rounded-2xl border border-neutral-200 bg-white p-8 text-sm text-neutral-500">
            Aucune image IA générée pour le moment. Lancez d'abord la génération via l'étape 5
            du cockpit, puis revenez ici pour réviser.
          </div>
        )}

        <div className="space-y-10" data-testid="images-review-grid">
          {productsWithImages.map((p) => (
            <ProductBlock
              key={p.id}
              product={p}
              onPick={(variant, style, image) => setModal({ product: p, variant_color: variant, style, image })}
            />
          ))}
        </div>
      </div>

      {modal && (
        <RegenerateModal
          siteId={siteId}
          {...modal}
          onClose={() => setModal(null)}
          onDone={async () => { await load(); }}
        />
      )}
    </Layout>
  );
}

function ProductBlock({ product, onPick }) {
  const gibv = product.generated_images_by_variant || {};
  const variants = Object.keys(gibv);
  return (
    <section className="rounded-2xl border border-neutral-200 bg-white" data-testid={`product-block-${product.id}`}>
      <div className="px-5 md:px-6 py-4 border-b border-neutral-100">
        <div className="text-xs uppercase tracking-widest text-neutral-500">{product.sku || "—"}</div>
        <h2 className="text-lg font-semibold text-neutral-900 mt-0.5">{pickName(product)}</h2>
      </div>
      <div className="p-5 md:p-6 space-y-6">
        {variants.map((v) => (
          <div key={v}>
            <div className="text-[11px] uppercase tracking-[0.2em] text-neutral-500 mb-3">
              Variante <span className="text-neutral-900 font-medium">{v}</span>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
              {(gibv[v] || []).map((img, i) => (
                <button
                  key={`${v}-${img.style || i}`}
                  type="button"
                  onClick={() => onPick(v, img.style, img)}
                  data-testid={`thumb-${product.id}-${v}-${img.style}`}
                  className="group text-left"
                >
                  <div className="aspect-square overflow-hidden rounded-lg bg-neutral-50 border border-neutral-200 relative">
                    {img.url ? (
                      <img
                        src={imageUrl(img)}
                        alt={img.style}
                        className="w-full h-full object-cover group-hover:opacity-90 transition"
                        loading="lazy"
                      />
                    ) : null}
                    {img.qa_passed === true && (
                      <span className="absolute top-1.5 right-1.5 text-emerald-500 bg-white/95 rounded-full">
                        <CheckCircle size={16} weight="fill" />
                      </span>
                    )}
                    {img.qa_passed === false && (
                      <span className="absolute top-1.5 right-1.5 text-amber-500 bg-white/95 rounded-full">
                        <WarningCircle size={16} weight="fill" />
                      </span>
                    )}
                    <span className="absolute inset-x-0 bottom-0 bg-black/60 text-white text-[11px] px-2 py-1 opacity-0 group-hover:opacity-100 transition flex items-center gap-1">
                      <ArrowsClockwise size={11} weight="bold" /> Régénérer
                    </span>
                  </div>
                  <div className="text-[11px] text-neutral-500 mt-1.5 truncate">
                    {STYLE_LABELS[img.style] || img.style || "?"}
                  </div>
                </button>
              ))}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function RegenerateModal({ siteId, product, variant_color, style, image, onClose, onDone }) {
  const [addon, setAddon] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  const submit = async () => {
    setBusy(true); setError(""); setResult(null);
    const { data, error: err } = await apiCall(() =>
      api.post(`/sites/${siteId}/products/${product.id}/regenerate-image`, {
        variant_color,
        style,
        custom_prompt_addon: addon.trim() || null,
      })
    );
    setBusy(false);
    if (err) {
      setError(err);
      return;
    }
    setResult(data);
  };

  const close = async () => {
    if (result?.regenerated) await onDone();
    onClose();
  };

  return (
    <div
      className="fixed inset-0 bg-black/60 z-[80] flex items-center justify-center p-4"
      onClick={close}
      data-testid="regen-modal"
    >
      <div
        className="bg-white rounded-2xl shadow-xl w-full max-w-2xl max-h-[92vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-4 px-6 py-5 border-b border-neutral-100">
          <div>
            <div className="text-[11px] uppercase tracking-widest text-neutral-500">
              {pickName(product)} · {variant_color}
            </div>
            <h3 className="text-lg font-semibold mt-0.5">
              Régénérer · {STYLE_LABELS[style] || style}
            </h3>
          </div>
          <button onClick={close} className="text-neutral-400 hover:text-neutral-900" aria-label="Fermer">
            <X size={20} />
          </button>
        </div>

        <div className="grid md:grid-cols-2 gap-4 p-6">
          <div>
            <div className="text-xs uppercase tracking-widest text-neutral-500 mb-2">Image actuelle</div>
            <div className="aspect-square rounded-lg overflow-hidden bg-neutral-50 border border-neutral-200">
              {image?.url ? (
                <img src={imageUrl(image)} alt="" className="w-full h-full object-cover" />
              ) : null}
            </div>
          </div>

          <div>
            <div className="text-xs uppercase tracking-widest text-neutral-500 mb-2">
              {result?.regenerated ? "Nouvelle image" : "Aperçu après régénération"}
            </div>
            <div className="aspect-square rounded-lg overflow-hidden bg-neutral-50 border border-neutral-200 flex items-center justify-center">
              {busy ? (
                <div className="text-center text-sm text-neutral-500 px-4">
                  <ArrowsClockwise className="mx-auto animate-spin mb-2" size={28} />
                  Génération Nano Banana…<br/>
                  <span className="text-xs text-neutral-400">~15-20s + QA Vision</span>
                </div>
              ) : result?.regenerated ? (
                <img src={imageUrl(result.image)} alt="" className="w-full h-full object-cover" />
              ) : (
                <span className="text-xs text-neutral-400">— en attente —</span>
              )}
            </div>
            {result?.regenerated && (
              <div className="text-[11px] text-neutral-500 mt-1.5">
                {result.qa_passed ? "✓ QA Vision passé" : "⚠ QA Vision en alerte"}
                {typeof result.qa_attempt === "number" && ` · tentative ${result.qa_attempt + 1}`}
              </div>
            )}
          </div>
        </div>

        <div className="px-6 pb-6">
          <label className="block text-xs uppercase tracking-widest text-neutral-500 mb-2">
            Précisions (optionnel)
          </label>
          <textarea
            value={addon}
            onChange={(e) => setAddon(e.target.value)}
            placeholder="Ex: la personne doit être plus âgée avec des cheveux gris ; cadrage plus large ; pas de footrest étendu"
            rows={3}
            maxLength={400}
            data-testid="regen-addon"
            className="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-300"
          />
          <div className="text-[11px] text-neutral-400 mt-1">{addon.length}/400 — ajouté au brief par défaut</div>

          {error && (
            <div className="mt-3 p-3 rounded-lg bg-rose-50 border border-rose-200 text-sm text-rose-900" data-testid="regen-error">
              {error}
            </div>
          )}
          {result && !result.regenerated && (
            <div className="mt-3 p-3 rounded-lg bg-amber-50 border border-amber-200 text-sm text-amber-900" data-testid="regen-degraded">
              QA Vision a refusé les 3 tentatives ({result.reason}). Reformulez la précision et réessayez.
            </div>
          )}

          <div className="flex items-center justify-between gap-3 mt-5">
            <span className="text-xs text-neutral-500">~0,06 $ par régénération</span>
            <div className="flex gap-2">
              <button
                onClick={close}
                className="h-10 px-4 rounded-full text-sm font-medium border border-neutral-300 hover:bg-neutral-50"
              >
                {result?.regenerated ? "Garder" : "Annuler"}
              </button>
              <button
                onClick={submit}
                disabled={busy}
                data-testid="regen-submit"
                className="h-10 px-5 rounded-full text-sm font-medium text-white bg-neutral-900 hover:bg-neutral-800 disabled:opacity-60 inline-flex items-center gap-2"
              >
                <ArrowsClockwise size={14} weight="bold" />
                {busy ? "Régénération…" : (result?.regenerated ? "Régénérer encore" : "Régénérer")}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
