import React, { useEffect, useState, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { api, apiCall } from "../lib/api";
import { useAuth } from "../lib/auth";
import Layout from "../components/Layout";
import StepPanel from "../components/StepPanel";
import BlockOutputModal from "../components/BlockOutputModal";
import SiteQAPanel from "../components/SiteQAPanel";
import CockpitJourney from "../components/CockpitJourney";
import {
  ArrowLeft,
  Lock,
  Clock,
  CheckCircle,
  XCircle,
  Storefront,
  Link as LinkIcon,
  Package,
  Eye,
  Globe,
  ArrowClockwise,
  Warning,
  X as XIcon,
  Rocket,
  Sparkle,
  Gear,
} from "@phosphor-icons/react";

const COUNTRIES = [
  { code: "FR", name: "France", flag: "🇫🇷", lang: "fr", currency: "EUR" },
  { code: "DE", name: "Allemagne", flag: "🇩🇪", lang: "de", currency: "EUR" },
  { code: "CH", name: "Suisse", flag: "🇨🇭", lang: "fr", currency: "CHF" },
  { code: "BE", name: "Belgique", flag: "🇧🇪", lang: "fr", currency: "EUR" },
  { code: "UK", name: "Royaume-Uni", flag: "🇬🇧", lang: "en", currency: "GBP" },
  { code: "NL", name: "Pays-Bas", flag: "🇳🇱", lang: "nl", currency: "EUR" },
];

const STATUS_CONFIG = {
  locked: { label: "Verrouillée", icon: Lock, bg: "#F5F5F4", text: "#78716C" },
  in_progress: { label: "En cours", icon: Clock, bg: "#FEF3C7", text: "#B45309" },
  awaiting_validation: { label: "Complétée", icon: CheckCircle, bg: "#D1FAE5", text: "#047857" },
  validated: { label: "Validée", icon: CheckCircle, bg: "#D1FAE5", text: "#047857" },
  rejected: { label: "À refaire", icon: XCircle, bg: "#FFE4E6", text: "#BE123C" },
  blocked: { label: "Bloquée", icon: XCircle, bg: "#FFE4E6", text: "#BE123C" },
};

export default function SiteDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [site, setSite] = useState(null);
  const [steps, setSteps] = useState([]);
  const [selectedStep, setSelectedStep] = useState(null);
  const [loading, setLoading] = useState(true);
  const [domainStatus, setDomainStatus] = useState(null);
  const [showDomain, setShowDomain] = useState(false);
  const [domainInput, setDomainInput] = useState("");
  const [domainBusy, setDomainBusy] = useState(false);
  const [domainMsg, setDomainMsg] = useState(null);
  const [showScale, setShowScale] = useState(false);
  const [scaleResult, setScaleResult] = useState(null);
  const [scaling, setScaling] = useState(false);
  const [blockOutputs, setBlockOutputs] = useState({});
  const [executingBlock, setExecutingBlock] = useState(null);
  const [viewingBlockOutput, setViewingBlockOutput] = useState(null);

  const load = useCallback(async () => {
    const [siteRes, stepsRes, domRes, blocksRes] = await Promise.all([
      apiCall(() => api.get(`/sites/${id}`)),
      apiCall(() => api.get(`/sites/${id}/steps`)),
      apiCall(() => api.get(`/sites/${id}/domain`)),
      apiCall(() => api.get(`/sites/${id}/blocks/outputs-latest`)),
    ]);
    if (siteRes.data) setSite(siteRes.data);
    if (stepsRes.data) setSteps(stepsRes.data);
    if (domRes.data) {
      setDomainStatus(domRes.data);
      setDomainInput(domRes.data.custom_domain || "");
    }
    if (blocksRes.data) setBlockOutputs(blocksRes.data);
    setLoading(false);
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  const handleStepUpdate = (updated) => {
    setSteps((prev) => prev.map((s) => (s.id === updated.id ? updated : s)));
    setSelectedStep(updated);
    // also refresh to unlock next step
    load();
  };

  const handleClosePanel = () => {
    setSelectedStep(null);
    load();
  };

  const handleSaveDomain = async () => {
    setDomainBusy(true);
    setDomainMsg(null);
    const { data, error } = await apiCall(() =>
      api.post(`/sites/${id}/domain`, { custom_domain: domainInput.trim() })
    );
    setDomainBusy(false);
    if (error) {
      setDomainMsg({ kind: "err", text: error });
      return;
    }
    setDomainStatus(data);
    setDomainMsg({ kind: "ok", text: "Domaine enregistré. Configurez le CNAME puis cliquez Vérifier." });
  };

  const handleVerifyDomain = async () => {
    setDomainBusy(true);
    setDomainMsg(null);
    const { data, error } = await apiCall(() =>
      api.post(`/sites/${id}/domain/verify`)
    );
    setDomainBusy(false);
    if (error) {
      setDomainMsg({ kind: "err", text: error });
      return;
    }
    if (data.verified) {
      setDomainMsg({ kind: "ok", text: `✓ Vérifié · ${data.reason}` });
    } else {
      setDomainMsg({ kind: "warn", text: data.reason });
    }
    const refresh = await apiCall(() => api.get(`/sites/${id}/domain`));
    if (refresh.data) setDomainStatus(refresh.data);
  };

  const handleClearDomain = async () => {
    if (!window.confirm("Supprimer le domaine custom et revenir sur l'URL Altiaro ?")) return;
    await apiCall(() => api.delete(`/sites/${id}/domain`));
    setDomainInput("");
    setDomainMsg(null);
    const refresh = await apiCall(() => api.get(`/sites/${id}/domain`));
    if (refresh.data) setDomainStatus(refresh.data);
  };

  const handleScale = async (payload) => {
    setScaling(true);
    const { data, error } = await apiCall(() =>
      api.post(`/sites/${id}/scale`, payload)
    );
    setScaling(false);
    if (error) {
      window.alert(`Scale impossible : ${error}`);
      return;
    }
    setScaleResult(data);
  };

  const handleExecuteBlock = async (blockId) => {
    setExecutingBlock(blockId);
    const { data, error } = await apiCall(() =>
      api.post(`/sites/${id}/blocks/${blockId}/execute`, {})
    );
    setExecutingBlock(null);
    if (error) {
      window.alert(`Génération impossible : ${error}`);
      return;
    }
    setBlockOutputs((prev) => ({ ...prev, [blockId]: data }));
    setViewingBlockOutput(data);
  };

  if (loading) {
    return (
      <Layout>
        <div className="p-8 md:p-12 text-neutral-500">Chargement du site...</div>
      </Layout>
    );
  }

  if (!site) {
    return (
      <Layout>
        <div className="p-8 md:p-12">
          <div className="text-red-400">Site introuvable.</div>
        </div>
      </Layout>
    );
  }

        // Group steps by BLOCK, then by phase inside each block
  const blockGroups = {};
  steps.forEach((s) => {
    const blockId = s.block || "template";
    if (!blockGroups[blockId]) {
      blockGroups[blockId] = {
        id: blockId,
        name: s.block_name || blockId,
        emoji: s.block_emoji || "📦",
        order: s.block_order || 99,
        phases: {},
      };
    }
    const blk = blockGroups[blockId];
    if (!blk.phases[s.phase]) {
      blk.phases[s.phase] = { code: s.phase, name: s.phase_name, steps: [] };
    }
    blk.phases[s.phase].steps.push(s);
  });
  const sortedBlocks = Object.values(blockGroups).sort((a, b) => a.order - b.order);

  const totalValidated = steps.filter((s) => s.status === "validated").length;
  const progress = steps.length ? Math.round((totalValidated / steps.length) * 100) : 0;

  return (
    <Layout>
      <div className="p-8 md:p-12 max-w-[1600px] mx-auto w-full">
        <button
          onClick={() => navigate("/sites")}
          className="flex items-center gap-2 text-sm text-neutral-500 hover:text-neutral-900 mb-6 transition"
          data-testid="back-to-sites"
        >
          <ArrowLeft size={16} /> Retour aux sites
        </button>

        <div className="bg-white rounded-xl border border-neutral-200 p-8 mb-8 animate-fade-up">
          <div className="flex items-start justify-between gap-8">
            <div className="flex-1">
              <div className="flex items-center gap-3 mb-3">
                <div className="w-11 h-11 rounded-lg bg-neutral-200 flex items-center justify-center">
                  <Storefront size={22} weight="duotone" color="#B84B31" />
                </div>
                <span
                  className={`text-[11px] uppercase tracking-widest px-2.5 py-1 rounded-full ${
                    site.status === "active"
                      ? "bg-emerald-500/10 text-emerald-400"
                      : site.status === "live"
                      ? "bg-[#E0F2FE] text-[#0369A1]"
                      : "bg-[#F5F5F4] text-neutral-500"
                  }`}
                >
                  {site.status}
                </span>
              </div>
              <h1 className="text-3xl font-semibold text-neutral-900 mb-2">{site.name}</h1>
              <p className="text-neutral-600 max-w-2xl">{site.niche}</p>
              <div className="flex flex-wrap gap-4 mt-4 text-sm">
                {site.domain && (
                  <div className="flex items-center gap-1.5 text-neutral-600">
                    <LinkIcon size={14} /> {site.domain}
                  </div>
                )}
                {site.shopify_url && (
                  <a
                    href={site.shopify_url}
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-center gap-1.5 text-neutral-900 hover:underline"
                    data-testid="site-shopify-link"
                  >
                    <LinkIcon size={14} /> Shopify admin
                  </a>
                )}
              </div>

              <div className="flex flex-wrap gap-2 mt-5">
                <button
                  onClick={() => navigate(`/sites/${id}/products`)}
                  data-testid="manage-products"
                  className="h-10 px-4 rounded-xl bg-neutral-900 hover:bg-neutral-800 text-white text-sm font-medium flex items-center gap-2 transition"
                >
                  <Package size={16} weight="bold" /> Gérer les produits
                </button>
                <button
                  onClick={() => navigate(`/sites/${id}/blog-posts`)}
                  data-testid="nav-blog-posts"
                  className="h-10 px-4 rounded-xl bg-white border border-neutral-200 hover:border-neutral-900 text-neutral-900 text-sm font-medium flex items-center gap-2 transition"
                >
                  <Sparkle size={16} weight="duotone" /> Le Journal
                </button>
                <button
                  onClick={() => navigate(`/sites/${id}/seo`)}
                  data-testid="nav-seo-dashboard"
                  className="h-10 px-4 rounded-xl bg-white border border-neutral-200 hover:border-neutral-900 text-neutral-900 text-sm font-medium flex items-center gap-2 transition"
                >
                  <Sparkle size={16} weight="duotone" /> Santé SEO
                </button>
                <a
                  href={`/shop/${id}`}
                  target="_blank"
                  rel="noreferrer"
                  data-testid="view-storefront"
                  className="h-10 px-4 rounded-xl bg-white border border-neutral-200 hover:border-neutral-900 text-neutral-900 text-sm font-medium flex items-center gap-2 transition"
                >
                  <Eye size={16} /> Voir la boutique
                </a>
                <button
                  onClick={() => setShowDomain(true)}
                  data-testid="manage-domain"
                  className="h-10 px-4 rounded-xl bg-white border border-neutral-200 hover:border-neutral-900 text-neutral-900 text-sm font-medium flex items-center gap-2 transition"
                >
                  <Globe size={16} weight="duotone" />
                  Domaine
                  {domainStatus?.custom_domain_verified && (
                    <span className="text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400">
                      ✓
                    </span>
                  )}
                </button>
                <button
                  onClick={() => navigate(`/sites/${id}/policy`)}
                  data-testid="nav-settings"
                  className="h-10 px-4 rounded-xl bg-white border border-neutral-200 hover:border-neutral-900 text-neutral-900 text-sm font-medium flex items-center gap-2 transition"
                >
                  <Gear size={16} weight="duotone" /> Politique plateforme
                </button>
              </div>
            </div>

            <div className="text-right">
              <div className="text-[11px] uppercase tracking-widest text-neutral-500 mb-1">Statut</div>
              <div className="text-sm text-neutral-600 mt-1 max-w-[180px]">
                Le parcours ci-dessous pilote désormais l'avancement du site.
              </div>
            </div>
          </div>
        </div>

        <div className="mb-10">
          <CockpitJourney site={site} onRefresh={load} />
        </div>

        <div className="mb-10">
          <SiteQAPanel site={site} />
        </div>
      </div>

      {selectedStep && (
        <StepPanel
          step={selectedStep}
          site={site}
          isAdmin={user?.role === "admin"}
          onClose={handleClosePanel}
          onUpdate={handleStepUpdate}
        />
      )}

      {showDomain && (
        <DomainModal
          status={domainStatus}
          input={domainInput}
          setInput={setDomainInput}
          busy={domainBusy}
          msg={domainMsg}
          onSave={handleSaveDomain}
          onVerify={handleVerifyDomain}
          onClear={handleClearDomain}
          onClose={() => {
            setShowDomain(false);
            setDomainMsg(null);
          }}
        />
      )}

      {showScale && (
        <ScaleModal
          site={site}
          scaling={scaling}
          result={scaleResult}
          onClose={() => {
            setShowScale(false);
            setScaleResult(null);
          }}
          onConfirm={handleScale}
          onOpenSite={(sid) => {
            setShowScale(false);
            setScaleResult(null);
            navigate(`/sites/${sid}`);
          }}
        />
      )}

      {viewingBlockOutput && (
        <BlockOutputModal
          output={viewingBlockOutput}
          onClose={() => setViewingBlockOutput(null)}
        />
      )}
    </Layout>
  );
}

function DomainModal({ status, input, setInput, busy, msg, onSave, onVerify, onClear, onClose }) {
  const verified = status?.custom_domain_verified;
  const hasDomain = !!status?.custom_domain;
  const target = status?.cname_target || "";
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-neutral-900/40 p-4" onClick={onClose}>
      <div
        className="bg-white rounded-md w-full max-w-xl p-6 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
        data-testid="domain-modal"
      >
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-neutral-200 flex items-center justify-center">
              <Globe size={20} weight="duotone" className="text-neutral-900" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-neutral-900">Domaine custom</h2>
              <p className="text-xs text-neutral-500">Connecte ta boutique à ton propre nom de domaine.</p>
            </div>
          </div>
          <button onClick={onClose} className="w-8 h-8 rounded-lg hover:bg-neutral-200" data-testid="domain-modal-close">
            <XIcon size={16} className="mx-auto" />
          </button>
        </div>

        <label className="block text-xs font-medium text-neutral-600 mb-1.5">Nom de domaine</label>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="maboutique.fr"
          data-testid="domain-input"
          className="w-full h-11 px-3 rounded-lg border border-neutral-200 bg-white text-sm mb-3 focus:outline-none focus:border-neutral-400"
        />

        <div className="bg-neutral-100/40 rounded-lg border border-neutral-200 p-4 mb-4 text-sm">
          <div className="font-medium text-neutral-900 mb-2 flex items-center gap-2">
            <LinkIcon size={14} /> Configuration DNS requise
          </div>
          <div className="grid grid-cols-[80px_1fr] gap-y-1.5 gap-x-3 text-xs font-mono text-neutral-600">
            <span>Type</span><span className="text-neutral-900">CNAME</span>
            <span>Nom</span><span className="text-neutral-900">@ (ou www)</span>
            <span>Valeur</span>
            <span className="text-neutral-900 break-all">{target}</span>
            <span>TTL</span><span className="text-neutral-900">3600</span>
          </div>
          <p className="text-[11px] text-neutral-500 mt-2">
            Ajoute ce CNAME chez ton registrar (OVH, Gandi, Cloudflare…) puis clique "Vérifier".
            Propagation : 5 min à 24h.
          </p>
        </div>

        {msg && (
          <div
            className={`mb-3 p-2.5 rounded-lg text-xs flex gap-2 ${
              msg.kind === "ok"
                ? "bg-emerald-500/10 text-emerald-400"
                : msg.kind === "warn"
                ? "bg-amber-500/10 text-amber-300"
                : "bg-red-500/10 text-red-400"
            }`}
            data-testid="domain-msg"
          >
            {msg.kind === "ok" ? (
              <CheckCircle size={14} weight="fill" className="shrink-0 mt-0.5" />
            ) : (
              <Warning size={14} weight="fill" className="shrink-0 mt-0.5" />
            )}
            {msg.text}
          </div>
        )}

        <div className="flex items-center justify-between gap-2">
          <div>
            {hasDomain && (
              <button
                type="button"
                onClick={onClear}
                disabled={busy}
                data-testid="domain-clear"
                className="h-10 px-3 rounded-lg text-sm text-red-400 hover:bg-red-500/10 disabled:opacity-50"
              >
                Retirer
              </button>
            )}
          </div>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={onSave}
              disabled={busy || !input.trim()}
              data-testid="domain-save"
              className="h-10 px-4 rounded-lg bg-white border border-neutral-200 hover:border-[#B84B31] text-sm font-medium disabled:opacity-50"
            >
              Enregistrer
            </button>
            {hasDomain && (
              <button
                type="button"
                onClick={onVerify}
                disabled={busy}
                data-testid="domain-verify"
                className="h-10 px-4 rounded-lg bg-neutral-900 hover:bg-neutral-800 text-white text-sm font-medium disabled:opacity-50 flex items-center gap-2"
              >
                {busy ? (
                  <ArrowClockwise size={14} className="animate-spin" />
                ) : verified ? (
                  <CheckCircle size={14} weight="fill" />
                ) : (
                  <Globe size={14} weight="duotone" />
                )}
                {verified ? "Re-vérifier" : "Vérifier DNS"}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function ScaleModal({ site, scaling, result, onClose, onConfirm, onOpenSite }) {
  const alreadyCovered = new Set(site.selected_countries || []);
  const available = COUNTRIES.filter((c) => !alreadyCovered.has(c.code));

  const [selected, setSelected] = React.useState(available.map((c) => c.code));
  const [customDomains, setCustomDomains] = React.useState({});
  const [copyProducts, setCopyProducts] = React.useState(true);
  const [generateAds, setGenerateAds] = React.useState(true);
  const [tone, setTone] = React.useState("rassurant");

  const toggle = (code) =>
    setSelected((prev) =>
      prev.includes(code) ? prev.filter((c) => c !== code) : [...prev, code]
    );

  const totalBudget = selected.length * 30;
  const canConfirm = selected.length > 0 && !scaling && !result;

  const submit = () => {
    onConfirm({
      target_countries: selected,
      custom_domains: Object.fromEntries(
        Object.entries(customDomains).filter(([, v]) => v && v.trim())
      ),
      copy_products: copyProducts,
      generate_ads_copy: generateAds,
      tone,
    });
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-neutral-900/40 p-4"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-md w-full max-w-2xl p-6 shadow-2xl max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
        data-testid="scale-modal"
      >
        <div className="flex items-start justify-between mb-5">
          <div className="flex items-center gap-3">
            <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-[#B84B31] to-[#D97706] flex items-center justify-center">
              <Rocket size={20} weight="fill" className="text-neutral-900" />
            </div>
            <div>
              <h2 className="text-xl font-semibold text-neutral-900">
                Scaler sur 6 pays
              </h2>
              <p className="text-sm text-neutral-500">
                En 1 clic : un clone par pays, chacun avec sa langue, son budget, son domaine, et ses Ads Copy.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-lg hover:bg-neutral-200"
            data-testid="scale-modal-close"
          >
            <XIcon size={16} className="mx-auto" />
          </button>
        </div>

        {!result ? (
          <>
            {available.length === 0 ? (
              <div className="bg-amber-500/10 rounded-lg p-4 text-sm text-amber-300">
                Ce site couvre déjà les 6 marchés. Il n'y a plus rien à scaler.
              </div>
            ) : (
              <>
                <label className="block text-xs font-semibold text-neutral-600 mb-2 uppercase tracking-wider">
                  Pays cibles ({selected.length} sélectionnés)
                </label>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2 mb-5">
                  {available.map((c) => {
                    const active = selected.includes(c.code);
                    return (
                      <div
                        key={c.code}
                        className={`rounded-xl border p-3 transition cursor-pointer ${
                          active
                            ? "bg-neutral-100/40 border-[#B84B31]"
                            : "bg-white border-neutral-200 hover:border-neutral-300"
                        }`}
                        onClick={() => toggle(c.code)}
                        data-testid={`scale-country-${c.code}`}
                      >
                        <div className="flex items-center gap-3 mb-2">
                          <span className="text-2xl">{c.flag}</span>
                          <div className="flex-1">
                            <div className="font-medium text-sm text-neutral-900">
                              {c.name}
                            </div>
                            <div className="text-[11px] text-neutral-500 font-mono">
                              {c.lang.toUpperCase()} · {c.currency} · 30€/jour
                            </div>
                          </div>
                          <div
                            className={`w-5 h-5 rounded-full border-2 flex items-center justify-center ${
                              active
                                ? "bg-white border-[#B84B31]"
                                : "border-neutral-300"
                            }`}
                          >
                            {active && (
                              <CheckCircle size={14} weight="fill" className="text-neutral-900" />
                            )}
                          </div>
                        </div>
                        {active && (
                          <input
                            type="text"
                            placeholder={`Domaine custom (optionnel) — ex: shop.${c.code.toLowerCase()}`}
                            value={customDomains[c.code] || ""}
                            onChange={(e) => {
                              e.stopPropagation();
                              setCustomDomains((prev) => ({
                                ...prev,
                                [c.code]: e.target.value,
                              }));
                            }}
                            onClick={(e) => e.stopPropagation()}
                            data-testid={`scale-domain-${c.code}`}
                            className="w-full h-8 px-2 rounded border border-neutral-200 bg-white text-xs focus:outline-none focus:border-neutral-400"
                          />
                        )}
                      </div>
                    );
                  })}
                </div>

                <div className="bg-neutral-100/40 rounded-xl border border-neutral-200 p-4 mb-5 space-y-3">
                  <label className="flex items-center gap-2 text-sm cursor-pointer">
                    <input
                      type="checkbox"
                      checked={copyProducts}
                      onChange={(e) => setCopyProducts(e.target.checked)}
                      data-testid="scale-copy-products"
                      className="accent-[#B84B31]"
                    />
                    Cloner le catalogue produits (en statut <em className="mx-1">draft</em> pour revue)
                  </label>
                  <label className="flex items-center gap-2 text-sm cursor-pointer">
                    <input
                      type="checkbox"
                      checked={generateAds}
                      onChange={(e) => setGenerateAds(e.target.checked)}
                      data-testid="scale-generate-ads"
                      className="accent-[#B84B31]"
                    />
                    <Sparkle size={14} weight="fill" className="text-neutral-900" />
                    Générer les <strong>Ads Copy localisés</strong> en background (Claude 4.5, ~30s/pays)
                  </label>
                  {generateAds && (
                    <div className="pl-6">
                      <label className="block text-xs text-neutral-600 mb-1">Ton des annonces</label>
                      <select
                        value={tone}
                        onChange={(e) => setTone(e.target.value)}
                        data-testid="scale-tone"
                        className="h-9 px-2 rounded-lg border border-neutral-200 bg-white text-sm"
                      >
                        <option value="rassurant">Rassurant (senior-friendly)</option>
                        <option value="premium">Premium (haut de gamme)</option>
                        <option value="direct">Direct (promo / urgence)</option>
                      </select>
                    </div>
                  )}
                </div>

                <div className="bg-neutral-900 text-white rounded-xl p-4 mb-5 flex items-center justify-between">
                  <div>
                    <div className="text-[11px] uppercase tracking-widest text-neutral-900/60">
                      Récapitulatif
                    </div>
                    <div className="text-base font-semibold">
                      {selected.length} nouveau{selected.length > 1 ? "x" : ""} site{selected.length > 1 ? "s" : ""} créé{selected.length > 1 ? "s" : ""}
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-[11px] uppercase tracking-widest text-neutral-900/60">
                      Budget pub total
                    </div>
                    <div className="text-xl font-semibold">
                      {totalBudget}€<span className="text-sm text-neutral-900/60">/jour</span>
                    </div>
                  </div>
                </div>

                <div className="flex justify-end gap-2">
                  <button
                    type="button"
                    onClick={onClose}
                    disabled={scaling}
                    className="h-11 px-4 rounded-xl text-sm text-neutral-600 hover:bg-neutral-200"
                  >
                    Annuler
                  </button>
                  <button
                    type="button"
                    onClick={submit}
                    disabled={!canConfirm}
                    data-testid="scale-confirm"
                    className="h-11 px-5 rounded-xl bg-gradient-to-r from-[#B84B31] to-[#D97706] hover:from-[#993D26] hover:to-[#B45309] disabled:opacity-50 text-neutral-900 text-sm font-medium flex items-center gap-2 transition active:scale-[0.98]"
                  >
                    {scaling ? (
                      <>
                        <ArrowClockwise size={16} className="animate-spin" /> Création des clones…
                      </>
                    ) : (
                      <>
                        <Rocket size={16} weight="fill" /> Lancer sur {selected.length} pays
                      </>
                    )}
                  </button>
                </div>
              </>
            )}
          </>
        ) : (
          <ScaleResult result={result} onOpenSite={onOpenSite} onClose={onClose} />
        )}
      </div>
    </div>
  );
}

function ScaleResult({ result, onOpenSite, onClose }) {
  return (
    <div data-testid="scale-result">
      <div className="bg-emerald-500/10 border border-[#047857]/20 rounded-xl p-4 mb-5 flex items-start gap-3">
        <CheckCircle size={22} weight="fill" className="text-emerald-400 shrink-0 mt-0.5" />
        <div>
          <div className="text-base font-semibold text-emerald-400">
            {result.created.length} clone{result.created.length > 1 ? "s" : ""} créé{result.created.length > 1 ? "s" : ""} !
          </div>
          <div className="text-sm text-emerald-400">
            Budget total : <strong>{result.total_daily_budget_eur}€/jour</strong>
            {result.ads_copy_scheduled > 0 && (
              <> · <Sparkle size={12} weight="fill" className="inline" /> {result.ads_copy_scheduled} Ads Copy en génération (background)</>
            )}
          </div>
        </div>
      </div>

      <div className="space-y-2 mb-5">
        {result.created.map((s) => {
          const cc = s.selected_countries?.[0];
          const meta = COUNTRIES.find((c) => c.code === cc);
          return (
            <div
              key={s.id}
              className="bg-white border border-neutral-200 rounded-xl p-4 flex items-center gap-3 hover:border-[#B84B31]/40 transition cursor-pointer"
              onClick={() => onOpenSite(s.id)}
              data-testid={`scale-result-${cc}`}
            >
              <span className="text-2xl">{meta?.flag || "🌍"}</span>
              <div className="flex-1 min-w-0">
                <div className="font-medium text-sm text-neutral-900 truncate">{s.name}</div>
                <div className="text-xs text-neutral-500">
                  {meta?.name} · lang {s.primary_language?.toUpperCase()} · {s.products_cloned} produits
                  {s.custom_domain && (
                    <> · <LinkIcon size={10} className="inline" /> {s.custom_domain}</>
                  )}
                </div>
              </div>
              <div className="text-xs text-neutral-900 font-medium">
                Ouvrir →
              </div>
            </div>
          );
        })}
      </div>

      <div className="flex justify-end">
        <button
          type="button"
          onClick={onClose}
          className="h-10 px-4 rounded-xl bg-neutral-900 hover:bg-neutral-800 text-white text-sm font-medium"
          data-testid="scale-result-close"
        >
          Terminer
        </button>
      </div>
    </div>
  );
}

// BlockOutputModal moved to components/BlockOutputModal.jsx


