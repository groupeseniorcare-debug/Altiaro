// Sprint admin — widget Health intégrations.
// Affiché dans /admin et /admin/integrations.
import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, apiCall } from "../lib/api";

export default function IntegrationsHealthWidget() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  const reload = async () => {
    setLoading(true);
    const { data: d } = await apiCall(() => api.get("/admin/integrations/health"));
    if (d) setData(d);
    setLoading(false);
  };
  useEffect(() => { reload(); /* eslint-disable-next-line */ }, []);

  return (
    <div className="rounded-xl border border-neutral-200 bg-white p-5" data-testid="integrations-health">
      <div className="flex items-center justify-between mb-4">
        <div>
          <div className="text-base font-semibold text-neutral-900">Health intégrations</div>
          <div className="text-xs text-neutral-500">Dernière vérif : {data?.checked_at?.slice(11,19) || "…"}</div>
        </div>
        <button
          onClick={reload}
          disabled={loading}
          className="h-8 px-3 rounded-md border border-neutral-300 text-sm hover:bg-neutral-100 disabled:opacity-50"
        >
          {loading ? "…" : "Refresh"}
        </button>
      </div>
      <div className="divide-y divide-neutral-100">
        {(data?.items || []).map((it) => (
          <div key={it.slug} className="flex items-center justify-between py-2.5" data-testid={`int-${it.slug}`}>
            <div className="flex items-center gap-3 min-w-0">
              <span className={`inline-block w-2 h-2 rounded-full ${it.ok ? "bg-emerald-500" : "bg-rose-500"}`} />
              <span className="text-sm font-medium text-neutral-900">{it.label}</span>
              <span className="text-xs text-neutral-500 truncate">
                {it.ok ? "OK" : (it.detail?.reason || it.detail?.error || "KO")}
              </span>
            </div>
            {!it.ok && (
              <Link
                to={it.reconnect_url || "/admin/integrations"}
                className="text-xs h-7 px-3 rounded-md bg-neutral-900 text-white hover:bg-neutral-800 inline-flex items-center"
              >
                Reconnecter
              </Link>
            )}
          </div>
        ))}
        {!loading && (!data?.items || data.items.length === 0) && (
          <div className="text-sm text-neutral-500 py-2">Aucune intégration trouvée.</div>
        )}
      </div>
    </div>
  );
}
