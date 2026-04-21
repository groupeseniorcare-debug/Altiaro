import React, { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import Layout from "../components/Layout";
import { api, apiCall } from "../lib/api";
import {
  MagnifyingGlass,
  Sparkle,
  CheckCircle,
  Spinner,
  Clock,
  ArrowRight,
  Warning,
  Target,
  Globe,
  CaretRight,
} from "@phosphor-icons/react";

const PERSONAS = [
  { value: "tout_public", label: "Tout public", emoji: "🌍" },
  { value: "senior", label: "Senior 60+", emoji: "👴" },
  { value: "millennial", label: "Millennial 25-40", emoji: "👩‍💻" },
  { value: "famille", label: "Famille", emoji: "👨‍👩‍👧" },
  { value: "pro", label: "Pro / B2B", emoji: "💼" },
];

const COUNTRIES = [
  { code: "FR", name: "France", flag: "🇫🇷" },
  { code: "DE", name: "Allemagne", flag: "🇩🇪" },
  { code: "UK", name: "Royaume-Uni", flag: "🇬🇧" },
  { code: "CH", name: "Suisse", flag: "🇨🇭" },
  { code: "BE", name: "Belgique", flag: "🇧🇪" },
  { code: "NL", name: "Pays-Bas", flag: "🇳🇱" },
  { code: "IT", name: "Italie", flag: "🇮🇹" },
  { code: "ES", name: "Espagne", flag: "🇪🇸" },
];

const DEFAULT_COUNTRIES = ["FR", "DE", "UK", "CH", "BE", "NL"];

export default function Analyzer() {
  const [product, setProduct] = useState("");
  const [persona, setPersona] = useState("tout_public");
  const [countries, setCountries] = useState(DEFAULT_COUNTRIES);
  const [notes, setNotes] = useState("");
  const [job, setJob] = useState(null);
  const [error, setError] = useState("");
  const [history, setHistory] = useState([]);
  const pollingRef = useRef(null);
  const navigate = useNavigate();

  useEffect(() => {
    loadHistory();
    return () => pollingRef.current && clearInterval(pollingRef.current);
  }, []);

  const loadHistory = async () => {
    const { data } = await apiCall(() => api.get("/niches/analyses?limit=12"));
    if (data) setHistory(data);
  };

  const toggleCountry = (code) =>
    setCountries((c) => (c.includes(code) ? c.filter((x) => x !== code) : [...c, code]));

  const launch = async () => {
    const p = product.trim();
    if (!p || job?.status === "running" || job?.status === "pending") return;
    if (countries.length < 1) return setError("Sélectionne au moins 1 pays");
    setError("");

    const { data, error: err } = await apiCall(() =>
      api.post("/niches/analyze", { product: p, persona, countries, notes })
    );
    if (err) return setError(err);

    setJob({ ...data, step: 0, step_label: "Démarrage…", status: "pending" });
    pollJob(data.job_id);
  };

  const pollJob = (jobId) => {
    if (pollingRef.current) clearInterval(pollingRef.current);
    pollingRef.current = setInterval(async () => {
      const { data } = await apiCall(() => api.get(`/niches/analysis-jobs/${jobId}`));
      if (!data) return;
      setJob(data);
      if (data.status === "completed") {
        clearInterval(pollingRef.current);
        const aid = data.result?.analysis_id;
        if (aid) navigate(`/niches/analysis/${aid}`);
      } else if (data.status === "failed") {
        clearInterval(pollingRef.current);
        setError(data.error || "L'analyse a échoué. Réessaye.");
      }
    }, 3000);
  };

  const running = job && (job.status === "running" || job.status === "pending");

  return (
    <Layout>
      <div className="p-6 md:p-12 max-w-5xl mx-auto">
        {/* Hero */}
        <div className="mb-10">
          <div className="flex items-center gap-2 text-[11px] uppercase tracking-widest text-neutral-900 mb-3">
            <Sparkle size={12} weight="fill" /> Étude de marché IA · 8 marchés EU
          </div>
          <h1 className="text-2xl md:text-5xl font-semibold text-neutral-900 leading-[1.05]">
            Quel produit veux-tu lancer ?
          </h1>
          <p className="text-neutral-600 mt-3 max-w-2xl text-[17px]">
            Décris un produit e-commerce (n'importe quelle catégorie). L'IA analyse en profondeur
            sur 2-4 minutes : <strong>mots-clés natifs par langue</strong>, volumes Google, concurrence,
            prix pratiqués, cadre légal, fournisseurs pertinents. Verdict argumenté par pays.
          </p>
        </div>

        {/* Form */}
        <div className="bg-white rounded-md border border-neutral-200 p-6 mb-8 shadow-sm">
          <div className="relative mb-5">
            <MagnifyingGlass size={20} className="absolute left-5 top-1/2 -translate-y-1/2 text-neutral-500" />
            <input
              value={product}
              onChange={(e) => setProduct(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && launch()}
              placeholder="Ex: fauteuil releveur électrique, cafetière à grain compacte, support téléphone vélo…"
              data-testid="analyze-input"
              disabled={running}
              className="w-full h-16 pl-14 pr-4 rounded-xl border border-neutral-200 text-lg outline-none focus:border-[#B84B31] focus:ring-2 focus:ring-[#B84B31]/20 disabled:opacity-50"
            />
          </div>

          {/* Persona */}
          <div className="mb-5">
            <div className="text-[11px] uppercase tracking-widest text-neutral-500 mb-2">Persona cible</div>
            <div className="flex flex-wrap gap-2">
              {PERSONAS.map((p) => (
                <button
                  key={p.value}
                  onClick={() => setPersona(p.value)}
                  disabled={running}
                  data-testid={`persona-${p.value}`}
                  className={`h-10 px-4 rounded-full border text-sm transition ${
                    persona === p.value
                      ? "border-[#B84B31] bg-white/5 text-neutral-900"
                      : "border-neutral-200 text-neutral-600 hover:border-[#B84B31]/40"
                  }`}
                >
                  <span className="mr-1">{p.emoji}</span> {p.label}
                </button>
              ))}
            </div>
          </div>

          {/* Countries */}
          <div className="mb-5">
            <div className="text-[11px] uppercase tracking-widest text-neutral-500 mb-2">
              Pays à analyser ({countries.length} sélectionné{countries.length > 1 ? "s" : ""})
            </div>
            <div className="flex flex-wrap gap-2">
              {COUNTRIES.map((c) => (
                <button
                  key={c.code}
                  onClick={() => toggleCountry(c.code)}
                  disabled={running}
                  data-testid={`country-${c.code}`}
                  className={`h-9 px-3 rounded-lg border text-sm transition flex items-center gap-1.5 ${
                    countries.includes(c.code)
                      ? "border-[#B84B31] bg-white/5 text-neutral-900"
                      : "border-neutral-200 text-neutral-500 hover:border-[#B84B31]/40"
                  }`}
                >
                  <span>{c.flag}</span> {c.name}
                </button>
              ))}
            </div>
          </div>

          {/* Notes */}
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Notes optionnelles : positionnement, concurrent à analyser, saisonnalité à confirmer…"
            rows={2}
            disabled={running}
            data-testid="notes"
            className="w-full px-4 py-2.5 rounded-xl border border-neutral-200 text-sm outline-none focus:border-[#B84B31] mb-4"
          />

          {error && (
            <div className="text-sm text-red-400 bg-red-500/10 border border-[#FCA5A5] rounded-lg px-3 py-2 mb-3" data-testid="error">
              {error}
            </div>
          )}

          <button
            onClick={launch}
            disabled={running || !product.trim()}
            data-testid="analyze-btn"
            className="w-full h-12 rounded-xl bg-white hover:bg-[#44403C] text-black font-medium transition disabled:opacity-40 flex items-center justify-center gap-2"
          >
            {running ? (
              <><Spinner size={16} className="animate-spin" /> Analyse en cours…</>
            ) : (
              <><Sparkle size={14} weight="fill" /> Lancer l'analyse approfondie (2-4 min)</>
            )}
          </button>
        </div>

        {/* Progress */}
        {running && job && <ProgressPanel job={job} />}

        {/* History */}
        {!running && history.length > 0 && (
          <div>
            <h2 className="text-lg font-semibold text-neutral-900 mb-3">Analyses récentes</h2>
            <div className="space-y-2">
              {history.map((h) => (
                <button
                  key={h.id}
                  onClick={() => navigate(`/niches/analysis/${h.id}`)}
                  className="w-full bg-white rounded-xl border border-neutral-200 hover:border-[#B84B31] p-4 flex items-center gap-4 transition text-left"
                  data-testid={`history-${h.id}`}
                >
                  <div className="text-2xl">{h.analysis_summary?.emoji || "📦"}</div>
                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-neutral-900 truncate">
                      {h.analysis_summary?.name || h.product_input}
                    </div>
                    <div className="text-xs text-neutral-500 flex items-center gap-2 mt-0.5">
                      <span>{h.analysis_summary?.category}</span>
                      <span>·</span>
                      <span>{(h.analysis_summary?.total_volume_monthly || 0).toLocaleString("fr-FR")} rech/mois</span>
                      {h.analysis_summary?.go_countries?.length > 0 && (
                        <>
                          <span>·</span>
                          <span className="text-emerald-400 font-medium">
                            GO : {h.analysis_summary.go_countries.join(", ")}
                          </span>
                        </>
                      )}
                    </div>
                  </div>
                  <VerdictPill verdict={h.analysis_summary?.overall_verdict} />
                  <CaretRight size={16} className="text-[#A8A29E]" />
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </Layout>
  );
}

/* ---------- Progress Panel ---------- */
function ProgressPanel({ job }) {
  const STEPS = [
    "Extension keywords multi-langues",
    "Sizing marché par pays",
    "Analyse concurrentielle",
    "Cadre légal & opérationnel",
    "Synthèse stratégique & verdict",
  ];
  const current = job.step || 0;
  return (
    <div className="bg-white rounded-md border border-neutral-200 p-6 mb-8" data-testid="progress-panel">
      <div className="flex items-center gap-2 mb-4">
        <Spinner size={16} className="animate-spin text-neutral-900" />
        <div className="font-heading text-lg font-semibold text-neutral-900">
          Analyse en profondeur…
        </div>
      </div>
      <div className="space-y-2">
        {STEPS.map((label, idx) => {
          const stepNum = idx + 1;
          const done = current > stepNum || job.status === "completed";
          const active = current === stepNum && !done;
          return (
            <div
              key={idx}
              className={`flex items-center gap-3 py-2.5 px-3 rounded-lg border transition ${
                done ? "bg-[#DCF5E7] border-[#86EFAC]" : active ? "bg-amber-500/10 border-[#FDE68A]" : "bg-white border-neutral-200"
              }`}
              data-testid={`progress-step-${stepNum}`}
            >
              <div className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-semibold flex-shrink-0" style={{
                background: done ? "#047857" : active ? "#B84B31" : "#E7E5E4",
                color: done || active ? "white" : "#78716C",
              }}>
                {done ? <CheckCircle size={14} weight="fill" /> : active ? <Spinner size={12} className="animate-spin" /> : stepNum}
              </div>
              <div className="flex-1 text-sm font-medium text-neutral-900">
                {stepNum}. {label}
              </div>
              {active && <div className="text-xs text-[#854D0E]">En cours…</div>}
              {done && <div className="text-xs text-emerald-400">✓ Terminé</div>}
            </div>
          );
        })}
      </div>
      <div className="mt-4 text-xs text-neutral-500 flex items-center gap-1.5">
        <Clock size={12} /> Durée totale estimée : 2-4 min · Tu peux laisser cette page ouverte
      </div>
    </div>
  );
}

function VerdictPill({ verdict }) {
  const map = {
    GO: { bg: "#DCF5E7", fg: "#166534", label: "GO" },
    MAYBE: { bg: "#FEF3C7", fg: "#854D0E", label: "À creuser" },
    NOGO: { bg: "#FEE2E2", fg: "#B91C1C", label: "Pass" },
  };
  const s = map[verdict] || { bg: "#F5F2EB", fg: "#78716C", label: "—" };
  return (
    <span className="text-[11px] font-semibold px-2.5 py-1 rounded-full" style={{ background: s.bg, color: s.fg }}>
      {s.label}
    </span>
  );
}
