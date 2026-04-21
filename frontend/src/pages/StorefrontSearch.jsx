import React, { useEffect, useState } from "react";
import { useParams, useSearchParams, Link, useNavigate } from "react-router-dom";
import axios from "axios";
import StorefrontLayout, { useSiteData } from "../components/StorefrontLayout";
import { MagnifyingGlass } from "@phosphor-icons/react";

const BACKEND = process.env.REACT_APP_BACKEND_URL;

export default function StorefrontSearch() {
  const { siteId } = useParams();
  const site = useSiteData(siteId);
  const [params] = useSearchParams();
  const nav = useNavigate();
  const q = params.get("q") || "";
  const [query, setQuery] = useState(q);
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!q || q.length < 2) { setResults([]); return; }
    setLoading(true);
    axios.get(`${BACKEND}/api/public/sites/${siteId}/storefront-search?q=${encodeURIComponent(q)}`)
      .then(({ data }) => setResults(data.products || []))
      .catch(() => setResults([]))
      .finally(() => setLoading(false));
  }, [q, siteId]);

  if (!site) return null;
  const primary = site.design?.brand?.primary_color || "#1C1917";

  return (
    <StorefrontLayout site={site}>
      <div className="max-w-5xl mx-auto py-12 px-6">
        <div className="text-xs uppercase tracking-widest text-neutral-500 mb-2">Recherche</div>
        <h1 className="text-3xl mb-6" style={{ fontFamily: site.design?.brand?.font_heading || "Fraunces, serif" }}>
          {q ? `Résultats pour « ${q} »` : "Rechercher un produit"}
        </h1>
        <form onSubmit={(e) => { e.preventDefault(); nav(`/shop/${siteId}/search?q=${encodeURIComponent(query)}`); }}
          className="flex gap-2 mb-10">
          <div className="flex-1 relative">
            <MagnifyingGlass size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-neutral-400" />
            <input autoFocus value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Fauteuil releveur, coussin anti-escarres…"
              data-testid="storefront-search-input"
              className="w-full h-12 pl-11 pr-4 rounded-xl border border-neutral-300 focus:outline-none focus:ring-2 focus:ring-neutral-400" />
          </div>
          <button type="submit" data-testid="storefront-search-submit"
            style={{ background: primary }}
            className="h-12 px-6 rounded-xl text-white font-medium">Rechercher</button>
        </form>

        {loading && <div className="text-neutral-500">Recherche en cours…</div>}
        {!loading && q && results.length === 0 && (
          <div className="text-center py-20 text-neutral-500">
            <div className="text-5xl mb-4">🔎</div>
            <p className="mb-2">Aucun résultat pour « <strong>{q}</strong> ».</p>
            <p className="text-sm">Essayez un terme plus court ou contactez notre équipe.</p>
          </div>
        )}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {results.map((p) => (
            <Link to={`/shop/${siteId}/product/${p.id}`} key={p.id} data-testid={`search-result-${p.id}`}
              className="group block bg-white border border-neutral-200 rounded-2xl overflow-hidden hover:border-neutral-900 transition">
              <div className="aspect-[4/3] bg-neutral-100 overflow-hidden">
                {p.images?.[0] && <img src={p.images[0]} alt={p.name} className="w-full h-full object-cover group-hover:scale-105 transition duration-700" />}
              </div>
              <div className="p-5">
                <h3 className="font-medium mb-1 line-clamp-2">{p.name}</h3>
                {p.short_description && <p className="text-xs text-neutral-500 line-clamp-2 mb-2">{p.short_description}</p>}
                <div className="font-semibold tabular-nums">{(p.price_eur || p.price || 0).toFixed(2)} €</div>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </StorefrontLayout>
  );
}
