import React, { useEffect, useState, useCallback } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { api, apiCall } from "../lib/api";
import Layout from "../components/Layout";
import {
  ArrowLeft,
  CheckCircle,
  Warning,
  ArrowClockwise,
  GoogleLogo,
  MagnifyingGlass,
  ChartBar,
  Lightning,
  TrendUp,
  LinkSimple,
  XCircle,
  CurrencyEur,
} from "@phosphor-icons/react";

const MARKETS = [
  { code: "FR", flag: "🇫🇷", name: "France" },
  { code: "DE", flag: "🇩🇪", name: "Allemagne" },
  { code: "BE", flag: "🇧🇪", name: "Belgique" },
  { code: "NL", flag: "🇳🇱", name: "Pays-Bas" },
  { code: "UK", flag: "🇬🇧", name: "Royaume-Uni" },
  { code: "CH", flag: "🇨🇭", name: "Suisse" },
  { code: "ES", flag: "🇪🇸", name: "Espagne" },
  { code: "IT", flag: "🇮🇹", name: "Italie" },
];

const COMPETITION_COLOR = {
  LOW: "#10B981",
  MEDIUM: "#F59E0B",
  HIGH: "#EF4444",
  UNKNOWN: "#78716C",
};

export default function GoogleAds() {
  const navigate = useNavigate();
  const [sp, setSp] = useSearchParams();
  const [status, setStatus] = useState(null);
  const [customers, setCustomers] = useState([]);
  const [selectedCid, setSelectedCid] = useState("");
  const [loginCidInput, setLoginCidInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState(null);

  // Keyword Planner state
  const [seed, setSeed] = useState("");
  const [country, setCountry] = useState("FR");
  const [ideas, setIdeas] = useState([]);
  const [kwLoading, setKwLoading] = useState(false);

  // Campaigns state
  const [campaigns, setCampaigns] = useState([]);
  const [campLoading, setCampLoading] = useState(false);
  const [days, setDays] = useState(30);

  const loadStatus = useCallback(async () => {
    const { data } = await apiCall(() => api.get("/google-ads/status"));
    if (data) {
      setStatus(data);
      if (data.login_customer_id) setLoginCidInput(data.login_customer_id);
    }
  }, []);

  const loadCustomers = useCallback(async () => {
    const { data, error } = await apiCall(() => api.get("/google-ads/customers"));
    if (error) {
      setMsg({ kind: "err", text: error });
      return;
    }
    setCustomers(data.customers || []);
    if (data.customers?.[0]) setSelectedCid(data.customers[0].customer_id);
  }, []);

  useEffect(() => {
    // Catch OAuth callback redirect
    const st = sp.get("status");
    if (st === "connected") {
      setMsg({ kind: "ok", text: "✅ Compte Google Ads connecté avec succès !" });
      sp.delete("status");
      setSp(sp);
    } else if (st === "error") {
      setMsg({ kind: "err", text: `❌ Échec de connexion : ${sp.get("reason") || "inconnu"}` });
      sp.delete("status");
      sp.delete("reason");
      setSp(sp);
    }
    loadStatus();
  }, [loadStatus, sp, setSp]);

  useEffect(() => {
    if (status?.connected) loadCustomers();
  }, [status?.connected, loadCustomers]);

  const handleConnect = async () => {
    setBusy(true);
    const { data, error } = await apiCall(() => api.get("/google-ads/oauth/start"));
    setBusy(false);
    if (error) {
      setMsg({ kind: "err", text: error });
      return;
    }
    // redirect user to Google consent
    window.location.href = data.authorization_url;
  };

  const handleDisconnect = async () => {
    if (!window.confirm("Déconnecter le compte Google Ads ?")) return;
    await apiCall(() => api.post("/google-ads/disconnect"));
    await loadStatus();
    setCustomers([]);
    setCampaigns([]);
    setIdeas([]);
  };

  const handleSaveLoginCid = async () => {
    setBusy(true);
    const { error } = await apiCall(() =>
      api.post("/google-ads/login-customer-id", { login_customer_id: loginCidInput })
    );
    setBusy(false);
    if (error) setMsg({ kind: "err", text: error });
    else {
      setMsg({ kind: "ok", text: "Login Customer ID enregistré." });
      loadStatus();
    }
  };

  const runKeywordIdeas = async () => {
    if (!selectedCid || !seed.trim()) return;
    setKwLoading(true);
    setIdeas([]);
    const seeds = seed.split(",").map((s) => s.trim()).filter(Boolean);
    const { data, error } = await apiCall(() =>
      api.post("/google-ads/keyword-ideas", {
        customer_id: selectedCid,
        seed_keywords: seeds,
        country,
        limit: 80,
      })
    );
    setKwLoading(false);
    if (error) {
      setMsg({ kind: "err", text: error });
      return;
    }
    setIdeas(data.ideas || []);
  };

  const runCampaigns = async () => {
    if (!selectedCid) return;
    setCampLoading(true);
    const { data, error } = await apiCall(() =>
      api.post("/google-ads/campaigns", { customer_id: selectedCid, days })
    );
    setCampLoading(false);
    if (error) {
      setMsg({ kind: "err", text: error });
      return;
    }
    setCampaigns(data.campaigns || []);
  };

  return (
    <Layout>
      <div className="p-8 md:p-12 max-w-[1400px]">
        <button
          onClick={() => navigate("/")}
          className="flex items-center gap-2 text-sm text-neutral-500 hover:text-neutral-900 mb-6 transition"
          data-testid="gads-back"
        >
          <ArrowLeft size={16} /> Retour au tableau de bord
        </button>

        <div className="flex items-start justify-between gap-8 mb-6">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <div className="w-11 h-11 rounded-lg bg-gradient-to-br from-[#4285F4] via-[#EA4335] to-[#FBBC05] flex items-center justify-center">
                <GoogleLogo size={22} weight="bold" color="#fff" />
              </div>
              <span className="text-[11px] uppercase tracking-widest text-neutral-500">
                Sprint 19 · Admin only
              </span>
            </div>
            <h1 className="text-3xl font-semibold text-neutral-900 mb-1">
              Google Ads Center
            </h1>
            <p className="text-neutral-600">
              Pilote tes campagnes + enrichis l'Analyseur avec les <strong>vrais volumes Google</strong>{" "}
              (Keyword Planner API).
            </p>
          </div>
        </div>

        {msg && (
          <div
            data-testid="gads-msg"
            className={`mb-5 p-3 rounded-lg text-sm flex items-start gap-2 ${
              msg.kind === "ok"
                ? "bg-emerald-500/10 text-emerald-400"
                : "bg-red-500/10 text-red-400"
            }`}
          >
            {msg.kind === "ok" ? (
              <CheckCircle size={16} weight="fill" />
            ) : (
              <Warning size={16} weight="fill" />
            )}
            <div className="flex-1">{msg.text}</div>
            <button onClick={() => setMsg(null)} className="text-xs">
              <XCircle size={14} />
            </button>
          </div>
        )}

        {/* ======= CONNECTION STATE ======= */}
        <div className="bg-white rounded-xl border border-neutral-200 p-6 mb-6">
          {!status?.config_ready ? (
            <div className="flex items-center gap-3 text-amber-300">
              <Warning size={20} weight="fill" />
              Variables serveur manquantes. Vérifie GOOGLE_ADS_DEVELOPER_TOKEN, CLIENT_ID, SECRET,
              REDIRECT_URI dans backend/.env.
            </div>
          ) : !status?.connected ? (
            <div className="flex items-center justify-between gap-4">
              <div>
                <div className="font-medium text-neutral-900 mb-1">Non connecté</div>
                <p className="text-sm text-neutral-500">
                  Connecte ton compte Google Ads pour activer le Keyword Planner et voir tes
                  campagnes. Tu seras redirigé vers Google pour autoriser.
                </p>
              </div>
              <button
                onClick={handleConnect}
                disabled={busy}
                data-testid="gads-connect"
                className="h-11 px-5 rounded-xl bg-[#4285F4] hover:bg-[#1C70E1] text-neutral-900 text-sm font-medium flex items-center gap-2 disabled:opacity-50 transition"
              >
                {busy ? (
                  <ArrowClockwise size={14} className="animate-spin" />
                ) : (
                  <GoogleLogo size={14} weight="bold" />
                )}
                Connecter Google Ads
              </button>
            </div>
          ) : (
            <div>
              <div className="flex items-center justify-between gap-4 mb-4">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <CheckCircle size={18} weight="fill" className="text-emerald-400" />
                    <div className="font-medium text-neutral-900">Compte connecté</div>
                  </div>
                  <p className="text-xs text-neutral-500">
                    Mis à jour : {status.updated_at?.slice(0, 16).replace("T", " ")}
                  </p>
                </div>
                <button
                  onClick={handleDisconnect}
                  data-testid="gads-disconnect"
                  className="h-9 px-3 rounded-lg text-xs text-red-400 hover:bg-red-500/10 transition"
                >
                  Déconnecter
                </button>
              </div>

              {/* Customer ID selector */}
              {customers.length > 0 && (
                <div className="mb-3">
                  <label className="block text-xs font-semibold text-neutral-600 mb-1.5 uppercase tracking-wider">
                    Compte Google Ads cible (Customer ID)
                  </label>
                  <div className="flex gap-2">
                    <select
                      value={selectedCid}
                      onChange={(e) => setSelectedCid(e.target.value)}
                      data-testid="gads-customer-select"
                      className="flex-1 h-11 px-3 rounded-lg border border-neutral-200 bg-white text-sm focus:outline-none focus:border-[#4285F4]"
                    >
                      {customers.map((c) => (
                        <option key={c.customer_id} value={c.customer_id}>
                          {c.customer_id_pretty} ({c.customer_id}){" "}
                          {status.preferred_customer_id === c.customer_id ? " · ✓ cible" : ""}
                        </option>
                      ))}
                    </select>
                    <button
                      onClick={async () => {
                        setBusy(true);
                        const { error } = await apiCall(() =>
                          api.post("/google-ads/preferred-customer-id", {
                            preferred_customer_id: selectedCid,
                          })
                        );
                        setBusy(false);
                        if (error) setMsg({ kind: "err", text: error });
                        else {
                          setMsg({ kind: "ok", text: "Compte cible enregistré. Les recherches utiliseront désormais ce compte." });
                          loadStatus();
                        }
                      }}
                      disabled={busy || !selectedCid}
                      data-testid="gads-save-preferred-cid"
                      className="h-11 px-4 rounded-lg bg-[#4285F4] hover:bg-[#1C70E1] text-neutral-900 text-xs font-medium disabled:opacity-50 whitespace-nowrap"
                    >
                      Définir comme cible
                    </button>
                  </div>
                  <p className="text-[11px] text-neutral-500 mt-1">
                    💡 Choisis le compte qui a des campagnes actives (pas un MCC). Requis pour le Keyword Planner.
                  </p>
                </div>
              )}

              {/* Login Customer ID (MCC) */}
              <div className="bg-neutral-100/40 rounded-lg p-3">
                <label className="block text-xs font-semibold text-neutral-600 mb-1.5 uppercase tracking-wider">
                  Login Customer ID (MCC) — optionnel
                </label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={loginCidInput}
                    onChange={(e) => setLoginCidInput(e.target.value.replace(/[^0-9-]/g, ""))}
                    placeholder="123-456-7890 (ton MCC, sans tirets OK)"
                    data-testid="gads-login-cid-input"
                    className="flex-1 h-10 px-3 rounded-lg border border-neutral-200 bg-white text-sm font-mono focus:outline-none focus:border-[#4285F4]"
                  />
                  <button
                    onClick={handleSaveLoginCid}
                    disabled={busy || !loginCidInput}
                    data-testid="gads-save-login-cid"
                    className="h-10 px-4 rounded-lg bg-neutral-900 hover:bg-neutral-800 text-white text-xs font-medium disabled:opacity-50"
                  >
                    Enregistrer
                  </button>
                </div>
                <p className="text-[11px] text-neutral-500 mt-1.5">
                  Nécessaire si ton compte Google Ads est accessible via un MCC. Trouve-le en haut à
                  droite dans Google Ads.
                </p>
              </div>
            </div>
          )}
        </div>

        {status?.connected && (
          <>
            {/* ======= KEYWORD PLANNER ======= */}
            <div className="bg-white rounded-xl border border-neutral-200 p-6 mb-6">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-9 h-9 rounded-lg bg-[#EDE9FE] flex items-center justify-center">
                  <MagnifyingGlass size={16} weight="bold" className="text-[#6D28D9]" />
                </div>
                <div>
                  <h2 className="text-lg font-semibold text-neutral-900">
                    Keyword Planner
                  </h2>
                  <p className="text-xs text-neutral-500">
                    Volumes réels Google + competition index + fourchette CPC
                  </p>
                </div>
              </div>

              <div className="flex flex-col md:flex-row md:items-end gap-3 mb-4">
                <div className="flex-1">
                  <label className="block text-xs font-semibold text-neutral-600 mb-1.5 uppercase tracking-wider">
                    Mots-clés seed (séparés par virgule)
                  </label>
                  <input
                    type="text"
                    value={seed}
                    onChange={(e) => setSeed(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && runKeywordIdeas()}
                    placeholder="fauteuil releveur, siège releveur senior, fauteuil relaxation électrique"
                    data-testid="gads-kw-seed"
                    className="w-full h-11 px-3 rounded-lg border border-neutral-200 bg-white text-sm focus:outline-none focus:border-[#6D28D9]"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-neutral-600 mb-1.5 uppercase tracking-wider">
                    Pays
                  </label>
                  <select
                    value={country}
                    onChange={(e) => setCountry(e.target.value)}
                    data-testid="gads-kw-country"
                    className="h-11 px-3 rounded-lg border border-neutral-200 bg-white text-sm focus:outline-none focus:border-[#6D28D9]"
                  >
                    {MARKETS.map((m) => (
                      <option key={m.code} value={m.code}>
                        {m.flag} {m.name}
                      </option>
                    ))}
                  </select>
                </div>
                <button
                  onClick={runKeywordIdeas}
                  disabled={kwLoading || !seed.trim() || !selectedCid}
                  data-testid="gads-kw-run"
                  className="h-11 px-5 rounded-lg bg-[#6D28D9] hover:bg-[#5B21B6] disabled:opacity-50 text-neutral-900 text-sm font-medium flex items-center gap-2 transition"
                >
                  {kwLoading ? (
                    <>
                      <ArrowClockwise size={14} className="animate-spin" /> Génération…
                    </>
                  ) : (
                    <>
                      <Lightning size={14} weight="fill" /> Générer
                    </>
                  )}
                </button>
              </div>

              {ideas.length > 0 && (
                <div className="overflow-x-auto rounded-lg border border-neutral-200" data-testid="gads-kw-table">
                  <table className="w-full text-sm">
                    <thead className="bg-neutral-100/40 border-b border-neutral-200">
                      <tr>
                        <th className="text-left p-2.5 text-xs font-semibold text-neutral-600 uppercase">Mot-clé</th>
                        <th className="text-right p-2.5 text-xs font-semibold text-neutral-600 uppercase">Volume/mois</th>
                        <th className="text-center p-2.5 text-xs font-semibold text-neutral-600 uppercase">Compétition</th>
                        <th className="text-right p-2.5 text-xs font-semibold text-neutral-600 uppercase">Index</th>
                        <th className="text-right p-2.5 text-xs font-semibold text-neutral-600 uppercase">CPC bas</th>
                        <th className="text-right p-2.5 text-xs font-semibold text-neutral-600 uppercase">CPC haut</th>
                      </tr>
                    </thead>
                    <tbody>
                      {ideas.map((i, idx) => (
                        <tr
                          key={idx}
                          className="border-b border-neutral-200 hover:bg-neutral-100/40/50"
                        >
                          <td className="p-2.5 font-medium text-neutral-900">{i.keyword}</td>
                          <td className="p-2.5 text-right font-mono font-semibold text-neutral-900">
                            {i.avg_monthly_searches.toLocaleString("fr-FR")}
                          </td>
                          <td className="p-2.5 text-center">
                            <span
                              className="inline-block px-2 py-0.5 rounded-full text-[10px] uppercase tracking-wider font-semibold text-neutral-900"
                              style={{ backgroundColor: COMPETITION_COLOR[i.competition] || "#78716C" }}
                            >
                              {i.competition}
                            </span>
                          </td>
                          <td className="p-2.5 text-right font-mono text-xs text-neutral-500">
                            {i.competition_index}/100
                          </td>
                          <td className="p-2.5 text-right font-mono text-xs text-neutral-500">
                            {i.low_top_of_page_bid_eur.toFixed(2)}€
                          </td>
                          <td className="p-2.5 text-right font-mono text-xs text-neutral-900">
                            {i.high_top_of_page_bid_eur.toFixed(2)}€
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            {/* ======= CAMPAIGNS ======= */}
            <div className="bg-white rounded-xl border border-neutral-200 p-6">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-lg bg-amber-500/10 flex items-center justify-center">
                    <ChartBar size={16} weight="bold" className="text-amber-300" />
                  </div>
                  <div>
                    <h2 className="text-lg font-semibold text-neutral-900">
                      Campagnes actives
                    </h2>
                    <p className="text-xs text-neutral-500">Lecture seule — performances agrégées</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <select
                    value={days}
                    onChange={(e) => setDays(parseInt(e.target.value))}
                    data-testid="gads-camp-days"
                    className="h-9 px-2 rounded-lg border border-neutral-200 text-xs bg-white"
                  >
                    <option value={7}>7 jours</option>
                    <option value={14}>14 jours</option>
                    <option value={30}>30 jours</option>
                  </select>
                  <button
                    onClick={runCampaigns}
                    disabled={campLoading || !selectedCid}
                    data-testid="gads-camp-run"
                    className="h-9 px-3 rounded-lg bg-neutral-900 hover:bg-neutral-800 text-white text-xs font-medium flex items-center gap-1.5 disabled:opacity-50"
                  >
                    {campLoading ? (
                      <ArrowClockwise size={12} className="animate-spin" />
                    ) : (
                      <TrendUp size={12} weight="fill" />
                    )}
                    Charger
                  </button>
                </div>
              </div>

              {campaigns.length === 0 && !campLoading && (
                <div className="py-8 text-center text-sm text-neutral-500">
                  Clique sur "Charger" pour afficher tes campagnes.
                </div>
              )}

              {campaigns.length > 0 && (
                <div className="overflow-x-auto rounded-lg border border-neutral-200" data-testid="gads-camp-table">
                  <table className="w-full text-sm">
                    <thead className="bg-neutral-100/40 border-b border-neutral-200">
                      <tr>
                        <th className="text-left p-2.5 text-xs font-semibold text-neutral-600 uppercase">Campagne</th>
                        <th className="text-left p-2.5 text-xs font-semibold text-neutral-600 uppercase">Status</th>
                        <th className="text-right p-2.5 text-xs font-semibold text-neutral-600 uppercase">Impressions</th>
                        <th className="text-right p-2.5 text-xs font-semibold text-neutral-600 uppercase">Clics</th>
                        <th className="text-right p-2.5 text-xs font-semibold text-neutral-600 uppercase">CTR</th>
                        <th className="text-right p-2.5 text-xs font-semibold text-neutral-600 uppercase">CPC moy.</th>
                        <th className="text-right p-2.5 text-xs font-semibold text-neutral-600 uppercase">Coût</th>
                        <th className="text-right p-2.5 text-xs font-semibold text-neutral-600 uppercase">Conv.</th>
                      </tr>
                    </thead>
                    <tbody>
                      {campaigns.map((c) => (
                        <tr
                          key={c.campaign_id}
                          className="border-b border-neutral-200 hover:bg-neutral-100/40/50"
                        >
                          <td className="p-2.5">
                            <div className="font-medium text-neutral-900">{c.name}</div>
                            <div className="text-[11px] text-neutral-500">{c.channel}</div>
                          </td>
                          <td className="p-2.5">
                            <span
                              className={`text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full font-semibold ${
                                c.status === "ENABLED"
                                  ? "bg-emerald-500/10 text-emerald-400"
                                  : "bg-[#F5F5F4] text-neutral-500"
                              }`}
                            >
                              {c.status}
                            </span>
                          </td>
                          <td className="p-2.5 text-right font-mono">{c.impressions.toLocaleString("fr-FR")}</td>
                          <td className="p-2.5 text-right font-mono">{c.clicks.toLocaleString("fr-FR")}</td>
                          <td className="p-2.5 text-right font-mono text-xs">{c.ctr.toFixed(2)}%</td>
                          <td className="p-2.5 text-right font-mono text-xs">
                            <CurrencyEur size={10} className="inline" />
                            {c.avg_cpc_eur.toFixed(2)}
                          </td>
                          <td className="p-2.5 text-right font-mono font-semibold">
                            {c.cost_eur.toFixed(2)}€
                          </td>
                          <td className="p-2.5 text-right font-mono">{c.conversions.toFixed(1)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </Layout>
  );
}
