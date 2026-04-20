import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, apiCall } from "../lib/api";
import Layout from "../components/Layout";
import { Target, TrendUp, CurrencyEur, Sparkle, ArrowRight } from "@phosphor-icons/react";

const scoreBand = (score) => {
  if (score >= 85) return { label: "Excellent", bg: "bg-[#DCF5E7]", text: "text-[#166534]" };
  if (score >= 80) return { label: "Très bon", bg: "bg-[#FEF3C7]", text: "text-[#854D0E]" };
  return { label: "Bon", bg: "bg-[#FFE4E6]", text: "text-[#9F1239]" };
};

export default function NicheEngine() {
  const [niches, setNiches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all"); // all | hero | top10
  const navigate = useNavigate();

  useEffect(() => {
    (async () => {
      const { data } = await apiCall(() => api.get("/niches"));
      setNiches(data || []);
      setLoading(false);
    })();
  }, []);

  const filtered = niches.filter((n) => {
    if (filter === "hero") return n.hero;
    if (filter === "top10") return n.rank <= 10;
    return true;
  });

  return (
    <Layout>
      <div className="p-8 md:p-12 max-w-7xl">
        <div className="mb-8 animate-fade-up">
          <div className="text-[11px] uppercase tracking-widest text-[#78716C] mb-2">Niche Engine</div>
          <h1 className="font-heading text-4xl font-semibold text-[#1C1917]">
            Catalogue Silver Economy
          </h1>
          <p className="text-[#57534E] mt-2 max-w-2xl">
            20 niches × 6 pays. Volume de recherche, CPC, difficulté SEO et score ECF
            pré-calculés pour choisir rapidement ton prochain site rentable.
          </p>
        </div>

        <div className="flex items-center gap-2 mb-6" data-testid="niche-filters">
          {[
            { key: "all", label: "Toutes (20)" },
            { key: "top10", label: "Top 10" },
            { key: "hero", label: "HERO (gros AOV)" },
          ].map((f) => (
            <button
              key={f.key}
              onClick={() => setFilter(f.key)}
              data-testid={`filter-${f.key}`}
              className={`h-9 px-4 rounded-full text-sm transition ${
                filter === f.key
                  ? "bg-[#1C1917] text-white"
                  : "bg-white border border-[#E7E5E4] text-[#57534E] hover:border-[#B84B31]"
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>

        {loading ? (
          <div className="text-[#78716C]">Chargement du catalogue...</div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5" data-testid="niche-grid">
            {filtered.map((n) => {
              const band = scoreBand(n.ecf_score);
              return (
                <button
                  key={n.slug}
                  onClick={() => navigate(`/niches/${n.slug}`)}
                  data-testid={`niche-card-${n.slug}`}
                  className="group text-left bg-white rounded-2xl border border-[#E7E5E4] p-6 hover:border-[#B84B31] hover:shadow-md transition-all duration-200"
                >
                  <div className="flex items-start justify-between mb-3">
                    <div className="text-3xl">{n.emoji}</div>
                    <div className={`px-2.5 py-1 rounded-full text-[11px] font-medium ${band.bg} ${band.text}`}>
                      ECF {n.ecf_score}
                    </div>
                  </div>

                  <div className="text-[11px] uppercase tracking-widest text-[#78716C] mb-1">
                    #{n.rank} · {n.category}
                  </div>
                  <div className="font-heading text-lg font-semibold text-[#1C1917] mb-2 group-hover:text-[#B84B31] transition">
                    {n.name}
                  </div>
                  <p className="text-sm text-[#57534E] line-clamp-2 mb-4">{n.tagline}</p>

                  <div className="grid grid-cols-3 gap-2 pt-4 border-t border-[#F5F2EB]">
                    <div>
                      <div className="flex items-center gap-1 text-[10px] uppercase tracking-wider text-[#78716C]">
                        <TrendUp size={10} /> Vol/mois
                      </div>
                      <div className="font-medium text-[#1C1917] text-sm mt-0.5">
                        {(n.total_volume_monthly || 0).toLocaleString("fr-FR")}
                      </div>
                    </div>
                    <div>
                      <div className="flex items-center gap-1 text-[10px] uppercase tracking-wider text-[#78716C]">
                        <CurrencyEur size={10} /> Panier
                      </div>
                      <div className="font-medium text-[#1C1917] text-sm mt-0.5">
                        {n.aov_eur[0]}–{n.aov_eur[1]}€
                      </div>
                    </div>
                    <div>
                      <div className="flex items-center gap-1 text-[10px] uppercase tracking-wider text-[#78716C]">
                        <Sparkle size={10} /> Marge
                      </div>
                      <div className="font-medium text-[#1C1917] text-sm mt-0.5">{n.margin_pct}%</div>
                    </div>
                  </div>

                  {n.hero && (
                    <div className="mt-4 inline-flex items-center gap-1 px-2 py-1 rounded-md bg-[#FEF3C7] text-[#854D0E] text-[11px] font-medium">
                      <Target size={10} weight="fill" /> HERO produit
                    </div>
                  )}

                  <div className="mt-4 flex items-center gap-1.5 text-[13px] font-medium text-[#B84B31] opacity-0 group-hover:opacity-100 transition">
                    Analyser par pays <ArrowRight size={14} />
                  </div>
                </button>
              );
            })}
          </div>
        )}
      </div>
    </Layout>
  );
}
