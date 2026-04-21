import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { api, apiCall } from "../lib/api";
import { useAuth } from "../lib/auth";
import Layout from "../components/Layout";
import {
  ArrowLeft,
  Target,
  TrendUp,
  CurrencyEur,
  Package,
  Tag,
  Rocket,
  Sparkle,
} from "@phosphor-icons/react";

const COUNTRY_META = {
  FR: { flag: "🇫🇷", name: "France" },
  DE: { flag: "🇩🇪", name: "Allemagne" },
  CH: { flag: "🇨🇭", name: "Suisse" },
  BE: { flag: "🇧🇪", name: "Belgique+Lux" },
  UK: { flag: "🇬🇧", name: "Royaume-Uni" },
  NL: { flag: "🇳🇱", name: "Pays-Bas" },
};

const kdColor = (kd) => {
  if (kd < 30) return "text-[#166534] bg-[#DCF5E7]";
  if (kd < 50) return "text-[#854D0E] bg-amber-500/10";
  return "text-[#9F1239] bg-red-500/10";
};

export default function NicheDetail() {
  const { slug } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [niche, setNiche] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      const { data } = await apiCall(() => api.get(`/niches/${slug}`));
      setNiche(data);
      setLoading(false);
    })();
  }, [slug]);

  if (loading) {
    return (
      <Layout>
        <div className="p-8 text-neutral-500">Chargement…</div>
      </Layout>
    );
  }

  if (!niche) {
    return (
      <Layout>
        <div className="p-8">
          <div className="text-[#9F1239]">Niche introuvable.</div>
          <button
            onClick={() => navigate("/niches")}
            className="mt-4 text-neutral-900 hover:underline"
          >
            ← Retour au catalogue
          </button>
        </div>
      </Layout>
    );
  }

  const countries = ["FR", "DE", "CH", "BE", "UK", "NL"];

  const launchSite = () => {
    // Pre-fill new site form via query params
    const params = new URLSearchParams({
      niche_slug: niche.slug,
      niche: niche.name,
      name: `${niche.name} — Altiaro`,
    });
    navigate(`/sites/new?${params.toString()}`);
  };

  return (
    <Layout>
      <div className="p-8 md:p-12 max-w-6xl">
        <button
          onClick={() => navigate("/niches")}
          className="flex items-center gap-2 text-sm text-neutral-500 hover:text-neutral-900 mb-6 transition"
          data-testid="back-to-niches"
        >
          <ArrowLeft size={16} /> Retour au catalogue
        </button>

        <div className="flex items-start gap-6 mb-10 animate-fade-up">
          <div className="text-6xl">{niche.emoji}</div>
          <div className="flex-1">
            <div className="text-[11px] uppercase tracking-widest text-neutral-500 mb-2">
              Niche #{niche.rank} · {niche.category}
            </div>
            <h1 className="text-3xl font-semibold text-neutral-900">{niche.name}</h1>
            <p className="text-neutral-600 mt-2 text-lg italic">« {niche.tagline} »</p>
            <p className="text-neutral-600 mt-3 max-w-3xl">{niche.description}</p>

            <div className="flex items-center gap-2 mt-5">
              <span className="px-3 py-1.5 rounded-full text-xs font-medium bg-white border border-neutral-200">
                ECF {niche.ecf_score}/100
              </span>
              <span className="px-3 py-1.5 rounded-full text-xs font-medium bg-white border border-neutral-200">
                Marge {niche.margin_pct}%
              </span>
              <span className="px-3 py-1.5 rounded-full text-xs font-medium bg-white border border-neutral-200">
                Meilleur pays {COUNTRY_META[niche.best_country]?.flag} {niche.best_country}
              </span>
              {niche.hero && (
                <span className="inline-flex items-center gap-1 px-3 py-1.5 rounded-full text-xs font-medium bg-amber-500/10 text-[#854D0E]">
                  <Target size={12} weight="fill" /> HERO produit
                </span>
              )}
            </div>
          </div>

          {user?.role === "admin" && (
            <button
              onClick={launchSite}
              data-testid="launch-from-niche"
              className="h-12 px-5 rounded-xl bg-white hover:bg-[#993D26] text-black font-medium flex items-center gap-2 transition active:scale-[0.98]"
            >
              <Rocket size={18} weight="fill" /> Lancer un site
            </button>
          )}
        </div>

        {/* KPI Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-10">
          <Kpi icon={<CurrencyEur size={16} />} label="Prix d'achat" value={`${niche.buy_price_eur[0]}–${niche.buy_price_eur[1]}€`} />
          <Kpi icon={<Tag size={16} />} label="Prix de vente" value={`${niche.sell_price_eur[0]}–${niche.sell_price_eur[1]}€`} />
          <Kpi icon={<TrendUp size={16} />} label="Volume total / mois (6 pays)" value={(niche.total_volume_monthly || 0).toLocaleString("fr-FR")} />
          <Kpi icon={<Sparkle size={16} />} label="CPC moyen" value={`${niche.avg_cpc_eur}€`} />
        </div>

        {/* Country Metrics Table */}
        <div className="bg-white rounded-md border border-neutral-200 overflow-hidden mb-10">
          <div className="px-6 py-4 border-b border-neutral-200">
            <div className="text-lg font-semibold text-neutral-900">
              Analyse par pays — 6 marchés
            </div>
            <div className="text-sm text-neutral-500 mt-1">
              Les CPA sont calculés pour garantir ~40% de marge nette après pub.
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-sm" data-testid="country-metrics-table">
              <thead className="bg-white text-[11px] uppercase tracking-widest text-neutral-500">
                <tr>
                  <th className="text-left px-6 py-3 font-medium">Pays</th>
                  <th className="text-right px-6 py-3 font-medium">Volume/mois</th>
                  <th className="text-right px-6 py-3 font-medium">CPC</th>
                  <th className="text-right px-6 py-3 font-medium">KD (SEO)</th>
                  <th className="text-right px-6 py-3 font-medium">CPA cible</th>
                  <th className="text-left px-6 py-3 font-medium">Saisonnalité</th>
                </tr>
              </thead>
              <tbody>
                {countries.map((code) => {
                  const m = niche.country_metrics[code] || {};
                  const best = code === niche.best_country;
                  return (
                    <tr
                      key={code}
                      className={`border-t border-neutral-200 ${best ? "bg-white" : ""}`}
                      data-testid={`row-${code}`}
                    >
                      <td className="px-6 py-3.5">
                        <div className="flex items-center gap-2">
                          <span className="text-lg">{COUNTRY_META[code]?.flag}</span>
                          <span className="font-medium text-neutral-900">{COUNTRY_META[code]?.name}</span>
                          {best && (
                            <span className="text-[10px] uppercase tracking-wider text-neutral-900 font-semibold">
                              ★ Leader
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="px-6 py-3.5 text-right tabular-nums">{m.volume?.toLocaleString("fr-FR")}</td>
                      <td className="px-6 py-3.5 text-right tabular-nums">{m.cpc?.toFixed(2)}€</td>
                      <td className="px-6 py-3.5 text-right">
                        <span className={`inline-block px-2 py-0.5 rounded-md text-[11px] font-medium ${kdColor(m.kd)}`}>
                          {m.kd}
                        </span>
                      </td>
                      <td className="px-6 py-3.5 text-right tabular-nums">{m.cpa_target}€</td>
                      <td className="px-6 py-3.5 text-neutral-600">{m.seasonality}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Keywords + suppliers */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          <div className="bg-white rounded-md border border-neutral-200 p-6">
            <div className="flex items-center gap-2 mb-3">
              <TrendUp size={18} className="text-neutral-900" />
              <div className="font-heading text-lg font-semibold text-neutral-900">Mots-clés principaux</div>
            </div>
            <div className="flex flex-wrap gap-2">
              {niche.keywords?.map((kw) => (
                <span
                  key={kw}
                  className="px-3 py-1.5 rounded-full text-xs bg-white border border-neutral-200 text-neutral-600"
                >
                  {kw}
                </span>
              ))}
            </div>
          </div>

          <div className="bg-white rounded-md border border-neutral-200 p-6">
            <div className="flex items-center gap-2 mb-3">
              <Package size={18} className="text-neutral-900" />
              <div className="font-heading text-lg font-semibold text-neutral-900">Fournisseurs recommandés</div>
            </div>
            <ul className="space-y-2">
              {niche.suppliers?.map((s) => (
                <li key={s} className="flex items-start gap-2 text-sm text-neutral-600">
                  <span className="text-neutral-900 mt-0.5">•</span>
                  {s}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </Layout>
  );
}

function Kpi({ icon, label, value }) {
  return (
    <div className="bg-white rounded-xl border border-neutral-200 p-5">
      <div className="flex items-center gap-1.5 text-[11px] uppercase tracking-widest text-neutral-500">
        {icon}
        {label}
      </div>
      <div className="text-xl font-semibold text-neutral-900 mt-2 tabular-nums">
        {value}
      </div>
    </div>
  );
}
