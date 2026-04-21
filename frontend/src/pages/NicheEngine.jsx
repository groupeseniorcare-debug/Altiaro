import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, apiCall } from "../lib/api";
import Layout from "../components/Layout";
import {
  Sparkle,
  MagnifyingGlass,
  ArrowRight,
  Target,
  TrendUp,
  CurrencyEur,
  Clock,
  CheckCircle,
  Warning,
  XCircle,
} from "@phosphor-icons/react";

const VERDICT_META = {
  GO:    { label: "GO",        bg: "#DCF5E7", text: "#166534", Icon: CheckCircle, desc: "Lance ce site sans hésiter" },
  MAYBE: { label: "À creuser", bg: "#FEF3C7", text: "#854D0E", Icon: Warning,     desc: "Potentiel OK, à affiner" },
  NOGO:  { label: "Pass",      bg: "#FFE4E6", text: "#9F1239", Icon: XCircle,     desc: "Marché trop difficile" },
};

const SUGGESTIONS = [
  "Fauteuil releveur électrique",
  "Coussin anti-escarres",
  "Lève-personne portable",
  "Rehausseur WC avec accoudoirs",
  "Téléphone senior grandes touches",
  "Pilulier électronique avec alertes",
];

export default function NicheEngine() {
  const [product, setProduct] = useState("");
  const [notes, setNotes] = useState("");
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState("");
  const [history, setHistory] = useState([]);
  const [catalog, setCatalog] = useState([]);
  const navigate = useNavigate();

  useEffect(() => {
    (async () => {
      const [h, c] = await Promise.all([
        apiCall(() => api.get("/niches/analyses?limit=6")),
        apiCall(() => api.get("/niches?limit=8")),
      ]);
      setHistory(h.data || []);
      setCatalog((c.data || []).slice(0, 8));
    })();
  }, []);

  const launch = async (p = product) => {
    const target = (p || "").trim();
    if (!target || analyzing) return;
    setAnalyzing(true);
    setError("");
    const { data, error: err } = await apiCall(() =>
      api.post("/niches/analyze", { product: target, notes }, { timeout: 120000 })
    );
    setAnalyzing(false);
    if (err) {
      setError(err);
      return;
    }
    navigate(`/niches/analysis/${data.id}`);
  };

  return (
    <Layout>
      <div className="p-6 md:p-12 max-w-5xl mx-auto">
        {/* Hero analyzer */}
        <div className="mb-10 animate-fade-up">
          <div className="flex items-center gap-2 text-[11px] uppercase tracking-widest text-neutral-900 mb-3">
            <Sparkle size={12} weight="fill" /> Analyse IA · 6 marchés EU
          </div>
          <h1 className="text-2xl md:text-5xl font-semibold text-neutral-900 leading-[1.05]">
            Quelle niche veux-tu attaquer ?
          </h1>
          <p className="text-neutral-600 mt-3 max-w-2xl text-[17px]">
            Décris un produit Silver Economy. L'IA analyse en ~30 secondes le volume de
            recherche, le CPC, la concurrence et la saisonnalité sur <strong>6 pays</strong>
            (FR · DE · CH · BE · UK · NL). Verdict GO / À creuser / Pass + synthèse par marché.
          </p>

          {/* Input */}
          <div className="mt-8">
            <div className="relative">
              <MagnifyingGlass size={20} className="absolute left-5 top-1/2 -translate-y-1/2 text-neutral-500" />
              <input
                value={product}
                onChange={(e) => setProduct(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && launch()}
                placeholder="Ex: Monte-escalier portable, pilulier électronique..."
                data-testid="analyze-input"
                className="w-full h-16 pl-14 pr-48 rounded-md border-2 border-neutral-200 bg-white focus:ring-4 focus:ring-[#B84B31]/15 focus:border-[#B84B31] outline-none text-[17px] transition shadow-sm"
              />
              <button
                onClick={() => launch()}
                disabled={analyzing || !product.trim()}
                data-testid="analyze-submit"
                className="absolute right-2 top-1/2 -translate-y-1/2 h-12 px-5 rounded-xl bg-white hover:bg-[#993D26] text-black font-medium flex items-center gap-2 transition active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {analyzing ? (
                  <>
                    <Clock size={16} className="animate-spin" weight="bold" /> Analyse...
                  </>
                ) : (
                  <>
                    <Sparkle size={16} weight="fill" /> Analyser
                  </>
                )}
              </button>
            </div>

            {/* Suggestion chips */}
            <div className="flex flex-wrap gap-2 mt-3" data-testid="suggestion-chips">
              <span className="text-xs text-neutral-500 py-1.5 pr-1">Idées :</span>
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => { setProduct(s); }}
                  className="px-3 py-1.5 rounded-full text-xs bg-white border border-neutral-200 hover:border-[#B84B31] hover:text-neutral-900 transition"
                >
                  {s}
                </button>
              ))}
            </div>

            {analyzing && (
              <div className="mt-4 p-4 rounded-xl bg-[#FDF4E7] border border-[#F5E0C3] flex items-start gap-3" data-testid="analyzing-bar">
                <Sparkle size={18} weight="fill" className="text-neutral-900 mt-0.5 animate-pulse" />
                <div className="flex-1">
                  <div className="font-medium text-neutral-900 text-sm">L'IA analyse 6 marchés en profondeur...</div>
                  <div className="text-xs text-neutral-500 mt-0.5">
                    Volume · CPC · Concurrence · Saisonnalité · Verdict par pays · ~30 secondes
                  </div>
                </div>
              </div>
            )}
            {error && (
              <div className="mt-4 p-3.5 rounded-xl bg-red-500/10 text-red-400 text-sm" data-testid="analyze-error">
                {error}
              </div>
            )}
          </div>
        </div>

        {/* History */}
        {history.length > 0 && (
          <section className="mb-12">
            <h2 className="text-[11px] uppercase tracking-widest text-neutral-500 mb-3">Tes analyses récentes</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3" data-testid="history-grid">
              {history.map((h) => {
                const s = h.analysis_summary || {};
                const v = VERDICT_META[s.overall_verdict] || VERDICT_META.MAYBE;
                return (
                  <button
                    key={h.id}
                    onClick={() => navigate(`/niches/analysis/${h.id}`)}
                    data-testid={`history-${h.id}`}
                    className="text-left bg-white rounded-xl border border-neutral-200 p-4 hover:border-[#B84B31] transition group"
                  >
                    <div className="flex items-center justify-between mb-1.5">
                      <div className="text-xl">{s.emoji || "📦"}</div>
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-medium" style={{ backgroundColor: v.bg, color: v.text }}>
                        {v.label}
                      </span>
                    </div>
                    <div className="font-medium text-neutral-900 text-sm group-hover:text-neutral-900 transition line-clamp-2">
                      {s.name || h.product_input}
                    </div>
                    <div className="text-[11px] text-neutral-500 mt-1 flex items-center gap-2">
                      <TrendUp size={10} /> {(s.total_volume_monthly || 0).toLocaleString("fr-FR")}/mois
                      {s.go_countries?.length > 0 && (
                        <span>· {s.go_countries.length} GO</span>
                      )}
                    </div>
                  </button>
                );
              })}
            </div>
          </section>
        )}

        {/* Inspiration catalog */}
        {catalog.length > 0 && (
          <section>
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-[11px] uppercase tracking-widest text-neutral-500">
                Niches recommandées par Altiora
              </h2>
              <div className="text-xs text-neutral-500">Basé sur 20 produits qualifiés</div>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3" data-testid="catalog-grid">
              {catalog.map((n) => (
                <button
                  key={n.slug}
                  onClick={() => {
                    setProduct(n.name);
                    setTimeout(() => launch(n.name), 50);
                  }}
                  data-testid={`catalog-${n.slug}`}
                  className="text-left bg-white rounded-xl border border-neutral-200 p-3.5 hover:border-[#B84B31] hover:shadow-sm transition group"
                >
                  <div className="flex items-center justify-between mb-1.5">
                    <div className="text-xl">{n.emoji}</div>
                    {n.hero && <Target size={12} weight="fill" className="text-neutral-900" />}
                  </div>
                  <div className="text-xs font-medium text-neutral-900 line-clamp-2 group-hover:text-neutral-900 transition">
                    {n.name}
                  </div>
                  <div className="text-[10px] text-neutral-500 mt-1 tabular-nums">
                    {(n.total_volume_monthly || 0).toLocaleString("fr-FR")}/mois · ECF {n.ecf_score}
                  </div>
                </button>
              ))}
            </div>
          </section>
        )}
      </div>
    </Layout>
  );
}
