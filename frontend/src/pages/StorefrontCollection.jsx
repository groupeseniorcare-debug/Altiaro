import React, { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import axios from "axios";
import {
  ShoppingBagOpen, Star, CaretDown, SlidersHorizontal, X as XIcon,
  ArrowRight, CheckCircle,
} from "@phosphor-icons/react";
import StorefrontLayout from "../components/StorefrontLayout";
import SEOHead from "../components/SEOHead";
import { pickLang, t } from "../lib/i18n";
import { useSiteAndLang, designAccents, formatPrice, buildHreflangs, BACKEND_URL } from "../components/storefront/storefrontUtils";

const SORT_OPTIONS = [
  { value: "featured", label: "Mis en avant" },
  { value: "newest", label: "Nouveautés" },
  { value: "price_asc", label: "Prix croissant" },
  { value: "price_desc", label: "Prix décroissant" },
  { value: "bestsellers", label: "Best-sellers" },
];

/* =========================================================
 * COLLECTIONS INDEX — /shop/:siteId/collections
 * ========================================================= */
export function StorefrontCollections() {
  const { siteId, site, design, lang, setLang } = useSiteAndLang();
  const [collections, setCollections] = useState([]);
  const { primary, fontHeading } = designAccents(design);

  useEffect(() => {
    axios.get(`${BACKEND_URL}/api/public/sites/${siteId}/collections`)
      .then(({ data }) => setCollections(data))
      .catch(() => setCollections([]));
  }, [siteId]);

  return (
    <StorefrontLayout lang={lang} setLang={setLang} site={site} design={design}>
      <SEOHead
        title={`Collections · ${site?.name || ""}`}
        description="Explorez nos univers produits."
        langs={buildHreflangs(site, "/collections")}
      />
      <section className="max-w-7xl mx-auto px-6 md:px-10 py-16 md:py-20" data-testid="collections-index">
        <div className="mb-12">
          <div className="text-[11px] uppercase tracking-[0.2em] text-neutral-500 mb-3">Nos univers</div>
          <h1 className="text-4xl md:text-6xl" style={{ fontFamily: `${fontHeading}, serif`, color: "#1C1917" }}>
            Explorer par collection
          </h1>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {collections.map((c, i) => (
            <Link
              key={c.slug || i}
              to={`/shop/${siteId}/collection/${c.slug}`}
              data-testid={`collection-card-${c.slug}`}
              className="group block bg-white rounded-3xl overflow-hidden border border-neutral-100 hover:shadow-lg transition-shadow duration-500"
            >
              <div className="aspect-[4/5] bg-neutral-100 relative overflow-hidden">
                {c.image && (
                  <img src={c.image} alt={c.title} className="absolute inset-0 w-full h-full object-cover transition-transform duration-700 group-hover:scale-105" />
                )}
                <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-black/10 to-transparent" />
                <div className="absolute bottom-5 left-5 right-5 text-white">
                  <h3 className="text-2xl md:text-3xl leading-tight mb-1" style={{ fontFamily: `${fontHeading}, serif` }}>
                    {pickLang(c.title, lang) || c.title}
                  </h3>
                  <div className="text-sm opacity-90">
                    {c.products_count} produit{c.products_count > 1 ? "s" : ""}
                  </div>
                </div>
              </div>
            </Link>
          ))}
        </div>
      </section>
    </StorefrontLayout>
  );
}

/* =========================================================
 * COLLECTION DETAIL — /shop/:siteId/collection/:slug
 * ========================================================= */
export function StorefrontCollection() {
  const { siteId, slug } = useParams();
  const { site, design, lang, setLang } = useSiteAndLang();
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  const [collection, setCollection] = useState(null);
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filtersOpen, setFiltersOpen] = useState(false);

  const { primary, fontHeading } = designAccents(design);

  // Filters state from URL
  const sort = searchParams.get("sort") || "featured";
  const minPrice = searchParams.get("min_price") || "";
  const maxPrice = searchParams.get("max_price") || "";
  const inStock = searchParams.get("in_stock") === "1";
  const onSale = searchParams.get("on_sale") === "1";
  const activeTags = searchParams.getAll("tag");

  /* Load collection meta */
  useEffect(() => {
    axios.get(`${BACKEND_URL}/api/public/sites/${siteId}/collections/${slug}`)
      .then(({ data }) => setCollection(data))
      .catch(() => setCollection(null));
  }, [siteId, slug]);

  /* Load filtered products */
  useEffect(() => {
    setLoading(true);
    const params = new URLSearchParams();
    params.set("collection", slug);
    if (sort) params.set("sort", sort);
    if (minPrice) params.set("min_price", minPrice);
    if (maxPrice) params.set("max_price", maxPrice);
    if (inStock) params.set("in_stock", "true");
    if (onSale) params.set("on_sale", "true");
    activeTags.forEach((tag) => params.append("tag", tag));

    axios.get(`${BACKEND_URL}/api/public/sites/${siteId}/products?${params.toString()}`)
      .then(({ data }) => setProducts(data))
      .catch(() => setProducts([]))
      .finally(() => setLoading(false));
  }, [siteId, slug, sort, minPrice, maxPrice, inStock, onSale, activeTags.join("|")]); // eslint-disable-line

  // Extract unique tags from products
  const availableTags = useMemo(() => {
    const tags = new Set();
    products.forEach((p) => (p.tags || []).forEach((tg) => tags.add(tg)));
    return Array.from(tags).sort();
  }, [products]);

  const hasProducts = products.length > 0;
  const showDemo = !loading && !hasProducts;

  const updateParam = (key, value) => {
    const next = new URLSearchParams(searchParams);
    if (value === "" || value == null || value === false) next.delete(key);
    else next.set(key, value === true ? "1" : value);
    setSearchParams(next);
  };

  const toggleTag = (tg) => {
    const next = new URLSearchParams(searchParams);
    const curr = next.getAll("tag");
    next.delete("tag");
    if (curr.includes(tg)) {
      curr.filter((x) => x !== tg).forEach((x) => next.append("tag", x));
    } else {
      [...curr, tg].forEach((x) => next.append("tag", x));
    }
    setSearchParams(next);
  };

  const clearFilters = () => {
    const next = new URLSearchParams();
    if (sort !== "featured") next.set("sort", sort);
    setSearchParams(next);
  };

  const activeFiltersCount =
    (minPrice ? 1 : 0) + (maxPrice ? 1 : 0) + (inStock ? 1 : 0) + (onSale ? 1 : 0) + activeTags.length;

  const title = pickLang(collection?.title, lang) || collection?.title || "Collection";
  const description = pickLang(collection?.description, lang) || collection?.description || "";
  const totalCount = collection?.products_count ?? products.length;

  /* SEO schemas */
  const canonical = typeof window !== "undefined" ? `${window.location.origin}/shop/${siteId}/collection/${slug}` : undefined;
  const breadcrumbSchema = {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: [
      { "@type": "ListItem", position: 1, name: "Accueil", item: `${window.location.origin}/shop/${siteId}` },
      { "@type": "ListItem", position: 2, name: "Collections", item: `${window.location.origin}/shop/${siteId}/collections` },
      { "@type": "ListItem", position: 3, name: title, item: canonical },
    ],
  };
  const itemListSchema = products.length ? {
    "@context": "https://schema.org",
    "@type": "ItemList",
    numberOfItems: products.length,
    itemListElement: products.slice(0, 24).map((p, i) => ({
      "@type": "ListItem",
      position: i + 1,
      url: `${canonical}/${p.id}`,
      name: pickLang(p.name, lang),
    })),
  } : null;

  return (
    <StorefrontLayout lang={lang} setLang={setLang} site={site} design={design}>
      <SEOHead
        title={`${title} · ${site?.name || ""}`}
        description={description || `Découvrez notre collection ${title}`}
        canonical={canonical}
        siteName={site?.name}
        keywords={`${title}, ${site?.niche || ""}, produits senior`}
        langs={buildHreflangs(site, `/collection/${slug}`)}
        schema={[breadcrumbSchema, itemListSchema].filter(Boolean)}
      />

      {/* ============ HERO BANNER MINIMAL ============ */}
      <section
        className="border-b"
        style={{ background: design?.brand?.accent_color || "#F5F2EB", borderColor: "#E7E5E4" }}
        data-testid="collection-hero"
      >
        <div className="max-w-7xl mx-auto px-6 md:px-10 py-12 md:py-16">
          <nav className="text-[12px] text-neutral-500 mb-6" data-testid="collection-breadcrumb">
            <Link to={`/shop/${siteId}`} className="hover:underline">Accueil</Link>
            <span className="mx-2">/</span>
            <Link to={`/shop/${siteId}/collections`} className="hover:underline">Collections</Link>
            <span className="mx-2">/</span>
            <span className="text-neutral-900">{title}</span>
          </nav>

          <div className="flex items-end justify-between gap-8 flex-wrap">
            <div className="max-w-2xl">
              <div className="text-[11px] uppercase tracking-[0.2em] text-neutral-500 mb-3">Collection</div>
              <h1
                className="text-4xl md:text-5xl lg:text-6xl leading-[1.05] tracking-tight text-neutral-900"
                style={{ fontFamily: `${fontHeading}, serif` }}
                data-testid="collection-title"
              >
                {title}
              </h1>
              {description && (
                <p className="text-[16px] md:text-[17px] text-neutral-600 mt-5 leading-relaxed">
                  {description}
                </p>
              )}
            </div>
            <div className="text-sm text-neutral-500">
              {totalCount} produit{totalCount > 1 ? "s" : ""}
            </div>
          </div>
        </div>
      </section>

      {/* ============ FILTER BAR HORIZONTAL ============ */}
      <section className="sticky top-[140px] lg:top-[88px] z-20 bg-white border-b" style={{ borderColor: "#E7E5E4" }} data-testid="collection-filters">
        <div className="max-w-7xl mx-auto px-6 md:px-10 py-3 flex items-center gap-2 md:gap-3 flex-wrap">
          {/* Mobile toggle */}
          <button
            type="button"
            onClick={() => setFiltersOpen(true)}
            data-testid="filters-open"
            className="lg:hidden inline-flex items-center gap-2 h-10 px-4 rounded-full border text-sm font-medium"
            style={{ borderColor: "#E7E5E4" }}
          >
            <SlidersHorizontal size={16} /> Filtres {activeFiltersCount > 0 && (
              <span className="ml-1 bg-neutral-900 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center">
                {activeFiltersCount}
              </span>
            )}
          </button>

          {/* Desktop pills */}
          <div className="hidden lg:flex items-center gap-3 flex-wrap">
            <PillSelect
              label="Prix"
              value={minPrice || maxPrice ? `${minPrice || 0} – ${maxPrice || "∞"} €` : "Prix"}
              active={!!(minPrice || maxPrice)}
            >
              <PriceRangePanel
                minPrice={minPrice}
                maxPrice={maxPrice}
                onChange={(k, v) => updateParam(k, v)}
                primary={primary}
              />
            </PillSelect>

            <PillToggle label="En stock" active={inStock} onChange={() => updateParam("in_stock", !inStock)} primary={primary} />
            <PillToggle label="En promo" active={onSale} onChange={() => updateParam("on_sale", !onSale)} primary={primary} />

            {availableTags.length > 0 && (
              <PillSelect
                label="Catégories"
                value={activeTags.length > 0 ? `Catégories (${activeTags.length})` : "Catégories"}
                active={activeTags.length > 0}
              >
                <div className="p-4 space-y-2 min-w-[220px]">
                  {availableTags.map((tg) => (
                    <label key={tg} className="flex items-center gap-2 cursor-pointer text-sm hover:text-neutral-900 text-neutral-600">
                      <input
                        type="checkbox"
                        checked={activeTags.includes(tg)}
                        onChange={() => toggleTag(tg)}
                        className="rounded"
                      />
                      {tg}
                    </label>
                  ))}
                </div>
              </PillSelect>
            )}

            {activeFiltersCount > 0 && (
              <button
                onClick={clearFilters}
                data-testid="filters-clear"
                className="text-sm text-neutral-600 hover:text-neutral-900 underline underline-offset-2 ml-2"
              >
                Effacer les filtres
              </button>
            )}
          </div>

          {/* Spacer then sort */}
          <div className="flex-1" />
          <label className="text-sm text-neutral-500 hidden md:inline">Trier :</label>
          <select
            value={sort}
            onChange={(e) => updateParam("sort", e.target.value)}
            data-testid="filters-sort"
            className="h-10 px-3 pr-8 rounded-full border text-sm bg-white font-medium cursor-pointer"
            style={{ borderColor: "#E7E5E4" }}
          >
            {SORT_OPTIONS.map((s) => (
              <option key={s.value} value={s.value}>{s.label}</option>
            ))}
          </select>
        </div>
      </section>

      {/* ============ MOBILE FILTERS DRAWER ============ */}
      {filtersOpen && (
        <div className="lg:hidden fixed inset-0 z-50" data-testid="filters-drawer">
          <div className="absolute inset-0 bg-black/50" onClick={() => setFiltersOpen(false)} />
          <div className="absolute bottom-0 left-0 right-0 bg-white rounded-t-3xl p-6 max-h-[85vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-5">
              <div className="font-semibold text-lg">Filtres</div>
              <button onClick={() => setFiltersOpen(false)} className="w-10 h-10 rounded-full hover:bg-neutral-50 flex items-center justify-center">
                <XIcon size={20} />
              </button>
            </div>

            <div className="space-y-6">
              <div>
                <div className="text-sm font-semibold mb-2">Prix</div>
                <PriceRangePanel
                  minPrice={minPrice}
                  maxPrice={maxPrice}
                  onChange={(k, v) => updateParam(k, v)}
                  primary={primary}
                />
              </div>

              <div className="flex gap-2">
                <PillToggle label="En stock" active={inStock} onChange={() => updateParam("in_stock", !inStock)} primary={primary} />
                <PillToggle label="En promo" active={onSale} onChange={() => updateParam("on_sale", !onSale)} primary={primary} />
              </div>

              {availableTags.length > 0 && (
                <div>
                  <div className="text-sm font-semibold mb-2">Catégories</div>
                  <div className="flex flex-wrap gap-2">
                    {availableTags.map((tg) => (
                      <button
                        key={tg}
                        onClick={() => toggleTag(tg)}
                        className={`px-3 py-1.5 rounded-full border text-sm transition ${activeTags.includes(tg) ? "text-white" : "bg-white"}`}
                        style={{
                          borderColor: activeTags.includes(tg) ? primary : "#E7E5E4",
                          background: activeTags.includes(tg) ? primary : undefined,
                        }}
                      >
                        {tg}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {activeFiltersCount > 0 && (
                <button onClick={clearFilters} className="text-sm underline text-neutral-600 w-full text-center">
                  Effacer tous les filtres
                </button>
              )}
            </div>

            <button
              onClick={() => setFiltersOpen(false)}
              className="mt-6 w-full h-12 rounded-full text-white font-medium"
              style={{ background: primary }}
            >
              Voir les produits
            </button>
          </div>
        </div>
      )}

      {/* ============ PRODUCT GRID ============ */}
      <section className="max-w-7xl mx-auto px-6 md:px-10 py-10 md:py-14" data-testid="collection-products">
        {loading ? (
          <div className="py-20 text-center text-neutral-500">Chargement…</div>
        ) : showDemo ? (
          <div className="py-16 text-center bg-white border border-dashed border-neutral-200 rounded-2xl">
            <ShoppingBagOpen size={48} weight="thin" className="mx-auto text-neutral-300 mb-4" />
            <div className="font-semibold text-lg mb-1 text-neutral-900">Aucun produit dans cette collection</div>
            <div className="text-neutral-500 text-sm mb-5">Les produits apparaîtront ici dès qu'ils seront importés.</div>
            <Link
              to={`/shop/${siteId}`}
              className="inline-flex items-center gap-2 h-11 px-5 rounded-full bg-neutral-900 text-white text-sm font-medium"
            >
              Voir toute la boutique <ArrowRight size={14} weight="bold" />
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5 md:gap-8" data-testid="collection-grid">
            {products.map((p) => (
              <Link
                key={p.id}
                to={`/shop/${siteId}/product/${p.id}`}
                data-testid={`collection-product-${p.id}`}
                className="group block"
              >
                <div className="aspect-square bg-[#F5F2EB] rounded-2xl overflow-hidden relative mb-4">
                  {p.images?.[0] ? (
                    <img src={p.images[0]} alt={pickLang(p.name, lang)} loading="lazy" className="w-full h-full object-cover group-hover:scale-[1.04] transition-transform duration-700 ease-out" />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-neutral-300">
                      <ShoppingBagOpen size={56} weight="thin" />
                    </div>
                  )}
                  {p.featured && (
                    <div className="absolute top-4 left-4 text-white text-[10px] uppercase tracking-widest font-semibold px-3 py-1.5 rounded-full backdrop-blur-sm flex items-center gap-1"
                         style={{ background: `${primary}dd` }}>
                      <Star size={10} weight="fill" /> Phare
                    </div>
                  )}
                  {p.compare_at_price && p.compare_at_price > p.price && (
                    <div className="absolute top-4 right-4 text-white text-[11px] font-semibold px-2.5 py-1 rounded-full" style={{ background: "#1C1917" }}>
                      -{Math.round((1 - p.price / p.compare_at_price) * 100)}%
                    </div>
                  )}
                </div>
                <div>
                  <div className="text-[15px] md:text-lg font-semibold leading-tight mb-1 group-hover:opacity-70 transition text-neutral-900"
                       style={{ fontFamily: `${fontHeading}, serif` }}>
                    {pickLang(p.name, lang)}
                  </div>
                  <div className="flex items-baseline gap-2 mt-2">
                    <span className="text-lg md:text-xl font-semibold" style={{ color: primary }}>
                      {formatPrice(p.price, p.currency, lang)}
                    </span>
                    {p.compare_at_price && p.compare_at_price > p.price && (
                      <span className="text-sm line-through text-neutral-400">
                        {formatPrice(p.compare_at_price, p.currency, lang)}
                      </span>
                    )}
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </section>

      {/* ============ SEO DESCRIPTION BLOCK EN BAS ============ */}
      <section className="max-w-4xl mx-auto px-6 md:px-10 py-16 md:py-20" data-testid="collection-seo-block">
        <div className="border-t pt-12" style={{ borderColor: "#E7E5E4" }}>
          <h2 className="text-2xl md:text-3xl mb-5" style={{ fontFamily: `${fontHeading}, serif` }}>
            {title} — Notre sélection
          </h2>
          <div className="prose prose-neutral max-w-none text-[16px] leading-relaxed text-neutral-700 space-y-4">
            {(collection?.seo_body?.[lang] || collection?.seo_body?.fr) ? (
              <div dangerouslySetInnerHTML={{ __html: collection.seo_body[lang] || collection.seo_body.fr }} />
            ) : (
              <>
                <p>
                  {description || `Retrouvez ici notre sélection de produits ${title.toLowerCase()}, choisis avec le plus grand soin pour répondre aux besoins réels des seniors et de leurs aidants.`}
                </p>
                <p>
                  Chaque article de cette collection est testé en conditions réelles, validé par nos partenaires ergothérapeutes, et accompagné d'un service client humain du lundi au vendredi de 9h à 18h.
                </p>
                <p>
                  <strong>Livraison offerte</strong> à partir de 50 € d'achat, <strong>garantie 2 ans</strong> incluse, <strong>retour gratuit sous 14 jours</strong> si le produit ne vous convient pas.
                </p>
              </>
            )}

            {/* Trust bullets SEO */}
            <ul className="grid grid-cols-1 sm:grid-cols-2 gap-2 not-prose mt-8 text-[15px]">
              <li className="flex items-center gap-2"><CheckCircle size={18} weight="fill" style={{ color: primary }} /> Livraison offerte en 48-72h</li>
              <li className="flex items-center gap-2"><CheckCircle size={18} weight="fill" style={{ color: primary }} /> Garantie 2 ans incluse</li>
              <li className="flex items-center gap-2"><CheckCircle size={18} weight="fill" style={{ color: primary }} /> Conseillers humains Lun–Ven</li>
              <li className="flex items-center gap-2"><CheckCircle size={18} weight="fill" style={{ color: primary }} /> Retour gratuit 14 jours</li>
            </ul>
          </div>
        </div>
      </section>
    </StorefrontLayout>
  );
}

/* =========================================================
 * Sub-components (pill filters)
 * ========================================================= */
function PillSelect({ label, value, active, children }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className={`inline-flex items-center gap-1.5 h-10 px-4 rounded-full border text-sm transition ${active ? "border-neutral-900 text-neutral-900 bg-neutral-50" : "bg-white text-neutral-700 hover:bg-neutral-50"}`}
        style={{ borderColor: active ? "#1C1917" : "#E7E5E4" }}
      >
        {value || label}
        <CaretDown size={12} weight="bold" className={`transition ${open ? "rotate-180" : ""}`} />
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-30" onClick={() => setOpen(false)} />
          <div className="absolute top-full left-0 mt-2 bg-white border rounded-2xl shadow-lg z-40" style={{ borderColor: "#E7E5E4" }}>
            {children}
          </div>
        </>
      )}
    </div>
  );
}

function PillToggle({ label, active, onChange, primary }) {
  return (
    <button
      type="button"
      onClick={onChange}
      className={`inline-flex items-center gap-1.5 h-10 px-4 rounded-full border text-sm transition ${active ? "text-white" : "bg-white text-neutral-700 hover:bg-neutral-50"}`}
      style={{
        background: active ? primary : undefined,
        borderColor: active ? primary : "#E7E5E4",
      }}
    >
      {active && <CheckCircle size={14} weight="fill" />}
      {label}
    </button>
  );
}

function PriceRangePanel({ minPrice, maxPrice, onChange, primary }) {
  const [localMin, setLocalMin] = useState(minPrice);
  const [localMax, setLocalMax] = useState(maxPrice);
  useEffect(() => { setLocalMin(minPrice); setLocalMax(maxPrice); }, [minPrice, maxPrice]);

  return (
    <div className="p-4 min-w-[260px]">
      <div className="grid grid-cols-2 gap-2 mb-3">
        <div>
          <label className="text-[11px] uppercase tracking-widest text-neutral-500 mb-1 block">Min</label>
          <input
            type="number"
            min={0}
            value={localMin}
            onChange={(e) => setLocalMin(e.target.value)}
            placeholder="0 €"
            className="w-full h-10 px-3 rounded-lg border text-sm"
            style={{ borderColor: "#E7E5E4" }}
          />
        </div>
        <div>
          <label className="text-[11px] uppercase tracking-widest text-neutral-500 mb-1 block">Max</label>
          <input
            type="number"
            min={0}
            value={localMax}
            onChange={(e) => setLocalMax(e.target.value)}
            placeholder="∞"
            className="w-full h-10 px-3 rounded-lg border text-sm"
            style={{ borderColor: "#E7E5E4" }}
          />
        </div>
      </div>
      <button
        type="button"
        onClick={() => {
          onChange("min_price", localMin || "");
          onChange("max_price", localMax || "");
        }}
        className="w-full h-10 rounded-full text-white text-sm font-medium"
        style={{ background: primary }}
      >
        Appliquer
      </button>
    </div>
  );
}
