// Sprint Off-Page — Section "Marketing Off-Page" affichée à la fin de l'étape 9 SEO.
// 3 cartes : Pinterest / Annuaires / HARO. Chaque carte = toggle + stats live.
import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api, apiCall } from "../lib/api";

function Card({ title, subtitle, status, action, children, dataTestid }) {
  return (
    <div
      className="rounded-xl border border-neutral-200 bg-white p-5 flex flex-col gap-3"
      data-testid={dataTestid}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-base font-semibold text-neutral-900">{title}</div>
          <div className="text-sm text-neutral-600 mt-0.5">{subtitle}</div>
        </div>
        <div className={`text-xs font-medium px-2 py-1 rounded-full whitespace-nowrap ${status?.bg || "bg-neutral-100 text-neutral-700"}`}>
          {status?.label || "—"}
        </div>
      </div>
      {children}
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}

export default function MarketingOffPagePanel() {
  const { id: siteId } = useParams();
  const [pin, setPin] = useState(null);
  const [dirs, setDirs] = useState(null);
  const [haro, setHaro] = useState(null);
  const [busy, setBusy] = useState({});

  const reload = async () => {
    const [p, d, h] = await Promise.all([
      apiCall(() => api.get(`/sites/${siteId}/marketing/pinterest/status`)),
      apiCall(() => api.get(`/sites/${siteId}/marketing/directories/status`)),
      apiCall(() => api.get(`/sites/${siteId}/marketing/haro/status`)),
    ]);
    if (p.data) setPin(p.data);
    if (d.data) setDirs(d.data);
    if (h.data) setHaro(h.data);
  };
  useEffect(() => {
    if (siteId) reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [siteId]);

  const togglePinterest = async () => {
    setBusy((b) => ({ ...b, pin: true }));
    await apiCall(() => api.post(`/sites/${siteId}/marketing/pinterest/auto-publish`, {
      enabled: !pin?.site_auto_publish,
    }));
    setBusy((b) => ({ ...b, pin: false }));
    reload();
  };

  const submitDirs = async () => {
    setBusy((b) => ({ ...b, dirs: true }));
    await apiCall(() => api.post(`/sites/${siteId}/marketing/directories/auto-submit`));
    setBusy((b) => ({ ...b, dirs: false }));
    reload();
  };

  const toggleHaro = async () => {
    setBusy((b) => ({ ...b, haro: true }));
    await apiCall(() => api.post(`/sites/${siteId}/marketing/haro/activate`, {
      enabled: !haro?.enabled,
    }));
    setBusy((b) => ({ ...b, haro: false }));
    reload();
  };

  return (
    <div className="mt-8" data-testid="marketing-offpage">
      <div className="mb-4">
        <h2 className="text-lg font-semibold text-neutral-900">Marketing Off-Page</h2>
        <p className="text-sm text-neutral-600">
          Backlinks, presse, social. Active ce que tu veux, on s'occupe du reste.
        </p>
      </div>

      <div className="grid md:grid-cols-3 gap-4">
        {/* Pinterest */}
        <Card
          title="Pinterest auto-publication"
          subtitle="Boards par site + pins automatiques par produit"
          dataTestid="card-pinterest"
          status={
            pin?.app_credentials_configured
              ? (pin?.site_auto_publish
                  ? { label: "Activé", bg: "bg-emerald-100 text-emerald-800" }
                  : { label: "Désactivé", bg: "bg-neutral-100 text-neutral-700" })
              : { label: "Non configuré", bg: "bg-amber-100 text-amber-800" }
          }
          action={
            <button
              onClick={togglePinterest}
              disabled={busy.pin || !pin?.app_credentials_configured}
              className="h-9 px-4 rounded-lg bg-neutral-900 text-white text-sm font-medium hover:bg-neutral-800 disabled:opacity-50"
            >
              {pin?.site_auto_publish ? "Désactiver" : "Activer"}
            </button>
          }
        >
          <div className="text-xs text-neutral-500 space-y-1">
            <div>Pins publiés : <strong>{pin?.pins_published || 0}</strong></div>
            <div>OAuth plateforme : {pin?.platform_oauth_connected ? "✓" : "non connecté"}</div>
            {pin?.note && <div className="italic mt-2 text-amber-700">{pin.note}</div>}
          </div>
        </Card>

        {/* Annuaires */}
        <Card
          title="Annuaires Silver Economy"
          subtitle="Soumission automatisée à 20 annuaires (email + form)"
          dataTestid="card-directories"
          status={
            dirs?.summary && Object.keys(dirs.summary).length
              ? { label: `${(dirs.summary.submitted || 0)}/${dirs.total_directories || 20} envoyés`, bg: "bg-emerald-100 text-emerald-800" }
              : { label: "Non lancé", bg: "bg-neutral-100 text-neutral-700" }
          }
          action={
            <button
              onClick={submitDirs}
              disabled={busy.dirs}
              className="h-9 px-4 rounded-lg bg-neutral-900 text-white text-sm font-medium hover:bg-neutral-800 disabled:opacity-50"
            >
              {busy.dirs ? "Soumission en cours…" : "Soumettre aux 20 annuaires"}
            </button>
          }
        >
          {dirs?.summary && (
            <div className="text-xs text-neutral-500 grid grid-cols-2 gap-1">
              {Object.entries(dirs.summary).map(([k, v]) => (
                <div key={k}>{k}: <strong>{v}</strong></div>
              ))}
            </div>
          )}
        </Card>

        {/* HARO */}
        <Card
          title="HARO / Press Outreach"
          subtitle="Réponses presse automatisées sur ta niche"
          dataTestid="card-haro"
          status={
            haro?.enabled
              ? { label: "Activé", bg: "bg-emerald-100 text-emerald-800" }
              : { label: "Désactivé", bg: "bg-neutral-100 text-neutral-700" }
          }
          action={
            <button
              onClick={toggleHaro}
              disabled={busy.haro}
              className="h-9 px-4 rounded-lg bg-neutral-900 text-white text-sm font-medium hover:bg-neutral-800 disabled:opacity-50"
            >
              {haro?.enabled ? "Désactiver" : "Activer"}
            </button>
          }
        >
          <div className="text-xs text-neutral-500 space-y-1">
            <div>Réponses envoyées : <strong>{haro?.responses_sent || 0}</strong></div>
            <div>Backlinks captés : <strong>{haro?.backlinks_captured || 0}</strong></div>
            {haro?.keywords?.length > 0 && (
              <div>Mots-clés : <em>{haro.keywords.join(", ")}</em></div>
            )}
          </div>
        </Card>
      </div>
    </div>
  );
}
