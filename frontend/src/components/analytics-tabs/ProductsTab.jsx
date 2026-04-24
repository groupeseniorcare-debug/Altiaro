import React, { useEffect, useState, useCallback, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { Package, Plus, CircleNotch, CaretDown, CaretUp } from "@phosphor-icons/react";
import { api, apiCall } from "../../lib/api";

const RANGES = [
  { key: "7d", label: "7j" },
  { key: "30d", label: "30j" },
  { key: "90d", label: "90j" },
];

const SORTS = [
  { key: "revenue",   label: "CA" },
  { key: "purchases", label: "Achats" },
  { key: "views",     label: "Vues" },
  { key: "price",     label: "Prix" },
  { key: "title",     label: "Nom" },
];

export default function ProductsTab({ siteId }) {
  const navigate = useNavigate();
  const [range, setRange] = useState("30d");
  const [sortKey, setSortKey] = useState("revenue");
  const [sortDir, setSortDir] = useState("desc");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    const { data: d, error } = await apiCall(() => api.get(`/sites/${siteId}/analytics/products?range=${range}`));
    if (!error) setData(d);
    setLoading(false);
  }, [siteId, range]);

  useEffect(() => { load(); }, [load]);

  const products = useMemo(() => {
    const list = [...(data?.products || [])];
    list.sort((a, b) => {
      const va = a[sortKey] ?? 0;
      const vb = b[sortKey] ?? 0;
      if (typeof va === "string" || typeof vb === "string") {
        return sortDir === "asc" ? String(va).localeCompare(String(vb)) : String(vb).localeCompare(String(va));
      }
      return sortDir === "asc" ? va - vb : vb - va;
    });
    return list;
  }, [data, sortKey, sortDir]);

  const toggleSort = (key) => {
    if (sortKey === key) setSortDir(d => d === "asc" ? "desc" : "asc");
    else { setSortKey(key); setSortDir(key === "title" ? "asc" : "desc"); }
  };

  return (
    <div data-testid="products-tab">
      <div className="flex items-center justify-between gap-3 mb-5 flex-wrap">
        <div className="flex items-center gap-1 bg-neutral-100 p-1 rounded-lg">
          {RANGES.map((r) => (
            <button
              key={r.key}
              onClick={() => setRange(r.key)}
              className={`h-8 px-3 rounded-md text-xs font-medium transition ${
                range === r.key ? "bg-white text-neutral-900 shadow-sm" : "text-neutral-500 hover:text-neutral-900"
              }`}
              data-testid={`products-range-${r.key}`}
            >
              {r.label}
            </button>
          ))}
        </div>
        <button
          onClick={() => navigate(`/sites/${siteId}/sourcing`)}
          className="inline-flex items-center gap-2 h-9 px-4 rounded-lg bg-neutral-900 hover:bg-neutral-800 text-white text-sm font-medium transition"
          data-testid="btn-add-product"
        >
          <Plus size={14} weight="bold" /> Ajouter un produit
        </button>
      </div>

      <div className="bg-white rounded-xl border border-neutral-200 overflow-hidden">
        {loading ? (
          <div className="py-20 text-neutral-500 text-sm flex items-center justify-center gap-2">
            <CircleNotch size={16} className="animate-spin" /> Chargement des produits…
          </div>
        ) : products.length === 0 ? (
          <div className="py-16 px-6 text-center" data-testid="products-empty">
            <Package size={36} weight="duotone" className="mx-auto text-neutral-400 mb-3" />
            <h3 className="text-base font-semibold text-neutral-900 mb-1">Aucun produit importé</h3>
            <p className="text-sm text-neutral-500 max-w-md mx-auto mb-4">
              Commence par l'étape <strong>Import</strong> du cockpit pour sourcer tes premiers produits depuis AliExpress ou CJ Dropshipping.
            </p>
            <button
              onClick={() => navigate(`/sites/${siteId}/sourcing`)}
              className="inline-flex items-center gap-2 h-9 px-4 rounded-lg bg-neutral-900 hover:bg-neutral-800 text-white text-sm font-medium transition"
            >
              <Plus size={14} weight="bold" /> Ouvrir le sourcing
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-[11px] uppercase tracking-widest text-neutral-500 bg-neutral-50">
                  <th className="py-3 px-4 text-left font-medium">
                    <SortBtn label="Produit" active={sortKey === "title"} dir={sortDir} onClick={() => toggleSort("title")} />
                  </th>
                  <th className="py-3 px-4 text-right font-medium">
                    <SortBtn label="Prix" active={sortKey === "price"} dir={sortDir} onClick={() => toggleSort("price")} align="right" />
                  </th>
                  <th className="py-3 px-4 text-right font-medium">Stock</th>
                  <th className="py-3 px-4 text-right font-medium">
                    <SortBtn label="Vues" active={sortKey === "views"} dir={sortDir} onClick={() => toggleSort("views")} align="right" />
                  </th>
                  <th className="py-3 px-4 text-right font-medium">
                    <SortBtn label="Achats" active={sortKey === "purchases"} dir={sortDir} onClick={() => toggleSort("purchases")} align="right" />
                  </th>
                  <th className="py-3 px-4 text-right font-medium">
                    <SortBtn label="CA" active={sortKey === "revenue"} dir={sortDir} onClick={() => toggleSort("revenue")} align="right" />
                  </th>
                </tr>
              </thead>
              <tbody>
                {products.map((p) => (
                  <tr key={p.product_id} className="border-t border-neutral-100 hover:bg-neutral-50/60 transition">
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-3">
                        {p.image ? (
                          <img src={p.image} alt="" className="w-9 h-9 rounded-md object-cover bg-neutral-100 flex-shrink-0" />
                        ) : (
                          <div className="w-9 h-9 rounded-md bg-neutral-100 flex items-center justify-center flex-shrink-0">
                            <Package size={15} className="text-neutral-400" />
                          </div>
                        )}
                        <span className="text-neutral-900 line-clamp-1">{p.title || "—"}</span>
                      </div>
                    </td>
                    <td className="py-3 px-4 text-right tabular-nums text-neutral-900">{p.price ? `${p.price.toFixed(2)} €` : "—"}</td>
                    <td className="py-3 px-4 text-right tabular-nums text-neutral-500">{p.stock ?? "—"}</td>
                    <td className="py-3 px-4 text-right tabular-nums">{p.views}</td>
                    <td className="py-3 px-4 text-right tabular-nums">{p.purchases}</td>
                    <td className="py-3 px-4 text-right tabular-nums font-medium text-neutral-900">
                      {p.revenue ? `${p.revenue.toFixed(2)} €` : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

function SortBtn({ label, active, dir, onClick, align = "left" }) {
  return (
    <button
      onClick={onClick}
      className={`inline-flex items-center gap-0.5 ${align === "right" ? "ml-auto" : ""} ${active ? "text-neutral-900" : "text-neutral-500 hover:text-neutral-900"}`}
    >
      {label}
      {active && (dir === "asc" ? <CaretUp size={10} /> : <CaretDown size={10} />)}
    </button>
  );
}
