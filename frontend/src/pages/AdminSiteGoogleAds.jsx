import React, { useEffect, useState, useCallback } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { toast } from "sonner";
import {
  ArrowLeft, CheckCircle, Warning, CircleNotch, Download, Sparkle,
  FileText, Cursor, Copy, ArrowSquareOut,
} from "@phosphor-icons/react";
import Layout from "../components/Layout";
import { api, apiCall } from "../lib/api";
import { useAuth } from "../lib/auth";

const COUNTRY_OPTIONS = [
  { code: "FR", label: "🇫🇷 France" },
  { code: "BE", label: "🇧🇪 Belgique" },
  { code: "LU", label: "🇱🇺 Luxembourg" },
  { code: "DE", label: "🇩🇪 Allemagne" },
  { code: "AT", label: "🇦🇹 Autriche" },
  { code: "NL", label: "🇳🇱 Pays-Bas" },
  { code: "IT", label: "🇮🇹 Italie" },
  { code: "ES", label: "🇪🇸 Espagne" },
  { code: "PT", label: "🇵🇹 Portugal" },
  { code: "IE", label: "🇮🇪 Irlande" },
  { code: "FI", label: "🇫🇮 Finlande" },
];

const CAMPAIGN_TYPES = [
  { key: "search",   label: "Search uniquement" },
  { key: "shopping", label: "Shopping uniquement" },
  { key: "both",     label: "Search + Shopping (recommandé)" },
];

export default function AdminSiteGoogleAds() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth() || {};

  const [site, setSite] = useState(null);
  const [config, setConfig] = useState({ conversion_id: "", conversion_label: "", enabled: false });
  const [saving, setSaving] = useState(false);
  const [campaignType, setCampaignType] = useState("both");
  const [targetCountry, setTargetCountry] = useState("FR");
  const [generating, setGenerating] = useState(false);
  const [exports, setExports] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    const [siteRes, cfgRes, listRes] = await Promise.all([
      apiCall(() => api.get(`/sites/${id}`)),
      apiCall(() => api.get(`/sites/${id}/google-ads/config`)),
      apiCall(() => api.get(`/sites/${id}/google-ads/exports?limit=10`)),
    ]);
    if (siteRes.data) {
      setSite(siteRes.data);
      const sc = siteRes.data.selected_countries || siteRes.data.seo_countries || ["FR"];
      setTargetCountry(sc[0] || "FR");
    }
    if (cfgRes.data) {
      setConfig({
        conversion_id: cfgRes.data.conversion_id || "",
        conversion_label: cfgRes.data.conversion_label || "",
        enabled: !!cfgRes.data.enabled,
      });
    }
    if (listRes.data) setExports(listRes.data.exports || []);
    setLoading(false);
  }, [id]);

  useEffect(() => { load(); }, [load]);

  // Redirect if not admin
  useEffect(() => {
    if (user && user.role !== "admin") {
      toast.error("Accès réservé aux admins.");
      navigate(`/sites/${id}`);
    }
  }, [user, id, navigate]);

  const handleSave = async () => {
    setSaving(true);
    const { data, error, rawDetail } = await apiCall(() =>
      api.patch(`/sites/${id}/google-ads/config`, {
        conversion_id: config.conversion_id.trim() || null,
        conversion_label: config.conversion_label.trim() || null,
        enabled: config.enabled,
      })
    );
    setSaving(false);
    if (error) {
      toast.error(rawDetail?.detail || "Échec sauvegarde");
      return;
    }
    toast.success(config.enabled ? "Pixel activé" : "Configuration sauvegardée");
    if (data) {
      setConfig({
        conversion_id: data.conversion_id || "",
        conversion_label: data.conversion_label || "",
        enabled: !!data.enabled,
      });
    }
  };

  const handleGenerate = async () => {
    setGenerating(true);
    const { data, error, rawDetail } = await apiCall(() =>
      api.post(`/sites/${id}/google-ads/generate-export`, {
        campaign_type: campaignType,
        target_country: targetCountry,
      })
    );
    setGenerating(false);
    if (error) {
      toast.error(rawDetail?.detail || "Échec génération — réessaie dans quelques secondes");
      return;
    }
    toast.success(`Export généré : ${data.summary.campaigns_count} campagnes, ${data.summary.keywords_count} mots-clés`);
    // Reload history
    const list = await apiCall(() => api.get(`/sites/${id}/google-ads/exports?limit=10`));
    if (list.data) setExports(list.data.exports || []);
  };

  const backendUrl = (path) => `${process.env.REACT_APP_BACKEND_URL || ""}${path}`;

  if (loading) {
    return (
      <Layout>
        <div className="p-10 text-neutral-500 flex items-center gap-2">
          <CircleNotch size={16} className="animate-spin" /> Chargement…
        </div>
      </Layout>
    );
  }

  const siteCountries = site?.selected_countries || site?.seo_countries || ["FR"];

  return (
    <Layout>
      <div className="p-6 md:p-10 max-w-[1200px] mx-auto w-full" data-testid="admin-gads-page">
        {/* Header */}
        <div className="flex items-center gap-3 mb-6">
          <button
            onClick={() => navigate(`/sites/${id}/analytics?tab=seo`)}
            className="flex items-center gap-1.5 h-9 px-3 rounded-lg border border-neutral-200 hover:bg-neutral-50 text-sm font-medium text-neutral-700 transition"
          >
            <ArrowLeft size={14} /> Retour au dashboard
          </button>
          <div>
            <div className="text-[11px] uppercase tracking-widest text-neutral-500">Admin — Google Ads manuel</div>
            <h1 className="text-2xl font-semibold text-neutral-900" style={{ fontFamily: "'Fraunces', serif" }}>
              {site?.name || "Site"}
            </h1>
          </div>
        </div>

        {/* Section 1 — Configuration pixel */}
        <section className="bg-white rounded-xl border border-neutral-200 p-6 mb-6" data-testid="gads-section-config">
          <h2 className="text-lg font-semibold text-neutral-900 mb-1">Configuration pixel</h2>
          <p className="text-sm text-neutral-500 mb-5">
            Trouve ces valeurs dans Google Ads → <em>Outils & Paramètres</em> → <em>Conversions</em> → ton action → <em>Tag de suivi</em>.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            <div>
              <label className="block text-xs font-medium text-neutral-700 mb-1.5">Conversion ID</label>
              <input
                type="text"
                placeholder="AW-123456789"
                value={config.conversion_id}
                onChange={(e) => setConfig({ ...config, conversion_id: e.target.value })}
                data-testid="gads-conversion-id"
                className="w-full h-10 px-3 rounded-lg border border-neutral-300 focus:border-neutral-900 focus:outline-none text-sm font-mono"
              />
              <p className="text-[11px] text-neutral-500 mt-1">Format : AW- suivi de 6 à 12 chiffres</p>
            </div>
            <div>
              <label className="block text-xs font-medium text-neutral-700 mb-1.5">Conversion label</label>
              <input
                type="text"
                placeholder="abc_defGhi"
                value={config.conversion_label}
                onChange={(e) => setConfig({ ...config, conversion_label: e.target.value })}
                data-testid="gads-conversion-label"
                className="w-full h-10 px-3 rounded-lg border border-neutral-300 focus:border-neutral-900 focus:outline-none text-sm font-mono"
              />
              <p className="text-[11px] text-neutral-500 mt-1">String courte fournie par Google Ads</p>
            </div>
          </div>

          <label className="flex items-center gap-2 cursor-pointer mb-5">
            <input
              type="checkbox"
              checked={config.enabled}
              onChange={(e) => setConfig({ ...config, enabled: e.target.checked })}
              data-testid="gads-enabled-toggle"
              className="w-4 h-4 accent-neutral-900"
            />
            <span className="text-sm text-neutral-800 font-medium">Activer le pixel sur le storefront public</span>
            {config.enabled && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 text-[11px] font-medium">
                <CheckCircle size={11} weight="fill" /> Pixel actif
              </span>
            )}
          </label>

          <button
            onClick={handleSave}
            disabled={saving}
            data-testid="gads-save-config"
            className="inline-flex items-center gap-2 h-10 px-5 rounded-lg bg-neutral-900 hover:bg-neutral-800 text-white text-sm font-medium disabled:opacity-50"
          >
            {saving ? <CircleNotch size={14} className="animate-spin" /> : <CheckCircle size={14} />}
            Enregistrer
          </button>
        </section>

        {/* Section 2 — Export assets */}
        <section className="bg-white rounded-xl border border-neutral-200 p-6 mb-6" data-testid="gads-section-export">
          <h2 className="text-lg font-semibold text-neutral-900 mb-1 flex items-center gap-2">
            <Sparkle size={18} weight="duotone" /> Export assets pour campagne
          </h2>
          <p className="text-sm text-neutral-500 mb-5">
            Génère un kit CSV prêt à importer dans <strong>Google Ads Editor</strong> : 5 campagnes × 20 keywords × 15 headlines × 4 descriptions.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-5">
            <div>
              <label className="block text-xs font-medium text-neutral-700 mb-1.5">Type de campagne</label>
              <select
                value={campaignType}
                onChange={(e) => setCampaignType(e.target.value)}
                data-testid="gads-campaign-type"
                className="w-full h-10 px-3 rounded-lg border border-neutral-300 focus:border-neutral-900 focus:outline-none text-sm bg-white"
              >
                {CAMPAIGN_TYPES.map((t) => <option key={t.key} value={t.key}>{t.label}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-neutral-700 mb-1.5">Pays cible</label>
              <select
                value={targetCountry}
                onChange={(e) => setTargetCountry(e.target.value)}
                data-testid="gads-target-country"
                className="w-full h-10 px-3 rounded-lg border border-neutral-300 focus:border-neutral-900 focus:outline-none text-sm bg-white"
              >
                {COUNTRY_OPTIONS.filter(c => siteCountries.includes(c.code)).map((c) => (
                  <option key={c.code} value={c.code}>{c.label}</option>
                ))}
                {siteCountries.length === 0 && <option value="FR">🇫🇷 France</option>}
              </select>
            </div>
            <div className="flex items-end">
              <button
                onClick={handleGenerate}
                disabled={generating}
                data-testid="gads-generate"
                className="w-full inline-flex items-center justify-center gap-2 h-10 px-5 rounded-lg bg-neutral-900 hover:bg-neutral-800 text-white text-sm font-medium disabled:opacity-50"
              >
                {generating ? <><CircleNotch size={14} className="animate-spin" /> Génération (~60s)…</> : <><Sparkle size={14} weight="duotone" /> Générer l'export</>}
              </button>
            </div>
          </div>

          {generating && (
            <div className="bg-neutral-50 rounded-lg p-4 text-sm text-neutral-600">
              Claude génère 5 campagnes en parallèle (transactionnel, informationnel, local, brand, concurrents).
              Le process prend environ 60 secondes — tu peux laisser cet écran ouvert.
            </div>
          )}
        </section>

        {/* Section 3 — Historique */}
        <section className="bg-white rounded-xl border border-neutral-200 overflow-hidden" data-testid="gads-section-history">
          <div className="p-6 border-b border-neutral-100">
            <h2 className="text-lg font-semibold text-neutral-900 mb-1">Historique des exports</h2>
            <p className="text-sm text-neutral-500">Les 10 derniers exports générés pour ce site (conservés 30 jours)</p>
          </div>

          {exports.length === 0 ? (
            <div className="py-10 px-6 text-center text-sm text-neutral-500">
              Aucun export généré pour l'instant. Clique sur <strong>Générer l'export</strong> ci-dessus.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-[11px] uppercase tracking-widest text-neutral-500 bg-neutral-50 text-left">
                    <th className="py-3 px-6 font-medium">Date</th>
                    <th className="py-3 px-6 font-medium">Type</th>
                    <th className="py-3 px-6 font-medium">Pays</th>
                    <th className="py-3 px-6 font-medium">Stats</th>
                    <th className="py-3 px-6 font-medium text-right">Téléchargements</th>
                  </tr>
                </thead>
                <tbody>
                  {exports.map((e) => (
                    <tr key={e.id} className="border-t border-neutral-100" data-testid="gads-export-row">
                      <td className="py-3 px-6 text-neutral-700">{new Date(e.created_at).toLocaleString("fr-FR")}</td>
                      <td className="py-3 px-6 capitalize text-neutral-800">{e.campaign_type}</td>
                      <td className="py-3 px-6 text-neutral-700">{e.target_country}</td>
                      <td className="py-3 px-6 text-neutral-600 text-[12px]">
                        {e.summary?.campaigns_count || 0} camps · {e.summary?.keywords_count || 0} kw · {e.summary?.ads_count || 0} ads
                      </td>
                      <td className="py-3 px-6 text-right">
                        <div className="inline-flex items-center gap-2">
                          <a
                            href={backendUrl(e.files.keywords_csv)}
                            className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md border border-neutral-200 hover:bg-neutral-50 text-[12px] font-medium text-neutral-700"
                            download
                            data-testid="gads-download-kw"
                          >
                            <Download size={12} /> keywords.csv
                          </a>
                          <a
                            href={backendUrl(e.files.ads_csv)}
                            className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md border border-neutral-200 hover:bg-neutral-50 text-[12px] font-medium text-neutral-700"
                            download
                            data-testid="gads-download-ads"
                          >
                            <Download size={12} /> ads.csv
                          </a>
                          <a
                            href={backendUrl(e.files.guide_md)}
                            target="_blank"
                            rel="noreferrer"
                            className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md border border-neutral-200 hover:bg-neutral-50 text-[12px] font-medium text-neutral-700"
                            data-testid="gads-view-guide"
                          >
                            <FileText size={12} /> guide.md <ArrowSquareOut size={10} />
                          </a>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div>
    </Layout>
  );
}
