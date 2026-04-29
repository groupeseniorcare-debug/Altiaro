import React, { useEffect, useState } from "react";
import { api, apiCall } from "../../lib/api";
import { GoogleLogo, CheckCircle, ArrowRight, SpinnerGap } from "@phosphor-icons/react";

/**
 * Panneau GSC multi-sites (admin).
 *
 * Permet à l'admin Altiaro de connecter Google Search Console **site par site**
 * sans avoir à naviguer dans chaque cockpit. Liste tous les sites + statut
 * GSC + bouton "Connecter" qui ouvre l'OAuth Google dans un nouvel onglet.
 */
export default function GscMultiSitePanel() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(null);

  const load = async () => {
    setLoading(true);
    const { data } = await apiCall(() => api.get("/admin/sites/gsc-status"));
    setRows((data && data.items) || []);
    setLoading(false);
  };
  useEffect(() => { load(); }, []);

  const connect = async (siteId) => {
    setBusy(siteId);
    const { data, error, rawDetail } = await apiCall(() =>
      api.get(`/sites/${siteId}/gsc/connect`),
    );
    setBusy(null);
    if (error) {
      window.alert(rawDetail?.detail || error);
      return;
    }
    if (data?.authorization_url) {
      window.open(data.authorization_url, "_blank", "noopener,noreferrer");
      // Refresh after 30s pour voir la card passer connected
      setTimeout(load, 30000);
    }
  };

  const disconnect = async (siteId) => {
    if (!window.confirm("Déconnecter GSC pour ce site ?")) return;
    await apiCall(() => api.post(`/sites/${siteId}/gsc/disconnect`));
    load();
  };

  return (
    <div
      className="bg-white border border-neutral-200 rounded-2xl p-5 mb-6"
      data-testid="gsc-multisite-panel"
    >
      <div className="flex items-start justify-between gap-4 flex-wrap mb-4">
        <div>
          <div className="flex items-center gap-2 text-[15px] font-semibold text-neutral-900">
            <GoogleLogo size={18} weight="bold" />
            Google Search Console — connexion multi-sites
          </div>
          <p className="text-[12px] text-neutral-600 mt-1.5 max-w-2xl leading-[1.55]">
            GSC se connecte <strong>site par site</strong> (chaque site a sa propre propriété
            Search Console). Connectez ici tous vos sites en quelques clics, sans avoir à
            naviguer dans chaque cockpit.
          </p>
        </div>
        <button
          onClick={load}
          disabled={loading}
          className="h-9 px-3 rounded-lg bg-white border border-neutral-200 hover:border-neutral-400 text-neutral-700 text-[13px] font-medium flex items-center gap-1.5 disabled:opacity-60"
          data-testid="gsc-refresh"
        >
          {loading ? <SpinnerGap size={12} weight="bold" className="animate-spin" /> : null}
          Rafraîchir
        </button>
      </div>

      {loading && rows.length === 0 ? (
        <div className="text-sm text-neutral-500 py-4 text-center">Chargement…</div>
      ) : rows.length === 0 ? (
        <div className="text-sm text-neutral-500 py-4 text-center">Aucun site disponible.</div>
      ) : (
        <div className="border border-neutral-100 rounded-xl overflow-hidden">
          <table className="w-full text-[13px]">
            <thead className="bg-neutral-50 text-[11px] uppercase tracking-widest text-neutral-500">
              <tr>
                <th className="text-left px-4 py-2.5 font-medium">Site</th>
                <th className="text-left px-4 py-2.5 font-medium">Domaine</th>
                <th className="text-left px-4 py-2.5 font-medium">Statut GSC</th>
                <th className="text-right px-4 py-2.5 font-medium">Action</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr
                  key={r.site_id}
                  data-testid={`gsc-row-${r.site_id}`}
                  className="border-t border-neutral-100"
                >
                  <td className="px-4 py-3 font-medium text-neutral-900">{r.name}</td>
                  <td className="px-4 py-3 text-neutral-600">
                    {r.public_url || r.custom_domain || (
                      <span className="text-neutral-400">— (pas de domaine)</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    {r.connected ? (
                      <span className="inline-flex items-center gap-1.5 text-emerald-700">
                        <CheckCircle size={14} weight="fill" />
                        Connecté
                        {r.property_url && (
                          <span className="text-[11px] text-neutral-500 ml-1.5">
                            ({r.property_url})
                          </span>
                        )}
                      </span>
                    ) : (
                      <span className="text-neutral-400">Non connecté</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-right">
                    {r.connected ? (
                      <button
                        onClick={() => disconnect(r.site_id)}
                        className="text-[12px] text-neutral-500 hover:text-rose-700"
                        data-testid={`gsc-disconnect-${r.site_id}`}
                      >
                        Déconnecter
                      </button>
                    ) : (
                      <button
                        onClick={() => connect(r.site_id)}
                        disabled={busy === r.site_id}
                        data-testid={`gsc-connect-${r.site_id}`}
                        className="h-9 px-3 rounded-lg bg-neutral-900 hover:bg-neutral-800 text-white text-[12px] font-medium inline-flex items-center gap-1.5 disabled:opacity-60"
                      >
                        {busy === r.site_id ? "Ouverture…" : "Connecter GSC"}
                        <ArrowRight size={11} weight="bold" />
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="mt-3 text-[11.5px] text-neutral-500">
        💡 Astuce : connecter GSC permet d'afficher la position moyenne, les clics et les
        impressions Google directement dans le cockpit SEO du site.
      </div>
    </div>
  );
}
