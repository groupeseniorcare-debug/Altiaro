import React, { useState } from "react";
import { api, apiCall } from "../lib/api";
import {
  X,
  MagnifyingGlass,
  ArrowClockwise,
  Lightning,
  Copy,
  CheckCircle,
  Warning,
} from "@phosphor-icons/react";

const COUNTRIES = [
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

export default function KeywordFinder({ initialSeed = "", initialCountry = "FR", onClose }) {
  const [seed, setSeed] = useState(initialSeed);
  const [country, setCountry] = useState(initialCountry);
  const [ideas, setIdeas] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [copiedIdx, setCopiedIdx] = useState(null);
  const [selected, setSelected] = useState({});

  const run = async () => {
    if (!seed.trim()) return;
    setLoading(true);
    setError(null);
    setIdeas([]);
    const seeds = seed.split(",").map((s) => s.trim()).filter(Boolean);
    const { data, error: err } = await apiCall(() =>
      api.post("/keywords/ideas", { seed_keywords: seeds, country, limit: 80 })
    );
    setLoading(false);
    if (err) {
      setError(err);
      return;
    }
    setIdeas(data.ideas || []);
  };

  const copyKeyword = (kw, idx) => {
    navigator.clipboard?.writeText(kw);
    setCopiedIdx(idx);
    setTimeout(() => setCopiedIdx(null), 1000);
  };

  const toggleSelect = (kw) => {
    setSelected((s) => ({ ...s, [kw]: !s[kw] }));
  };

  const copyAllSelected = () => {
    const list = Object.keys(selected).filter((k) => selected[k]);
    if (list.length === 0) return;
    navigator.clipboard?.writeText(list.join(", "));
    setCopiedIdx("all");
    setTimeout(() => setCopiedIdx(null), 1500);
  };

  const selectedCount = Object.values(selected).filter(Boolean).length;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-2xl w-full max-w-4xl max-h-[90vh] flex flex-col shadow-2xl"
        onClick={(e) => e.stopPropagation()}
        data-testid="keyword-finder-modal"
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#E7E5E4]">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-[#4285F4] to-[#6D28D9] flex items-center justify-center">
              <MagnifyingGlass size={18} weight="bold" color="#fff" />
            </div>
            <div>
              <div className="font-heading font-semibold text-[#1C1917]">
                Recherche de mots-clés Google
              </div>
              <div className="text-xs text-[#78716C]">
                Volumes mensuels + competition + CPC réels
              </div>
            </div>
          </div>
          <button
            onClick={onClose}
            data-testid="kwfinder-close"
            className="w-8 h-8 rounded-lg hover:bg-[#F5F2EB] flex items-center justify-center"
          >
            <X size={16} />
          </button>
        </div>

        <div className="px-6 py-4 border-b border-[#F5F2EB] flex flex-col md:flex-row md:items-end gap-3">
          <div className="flex-1">
            <label className="block text-xs font-semibold text-[#57534E] mb-1.5 uppercase tracking-wider">
              Mots-clés seed (séparés par virgule)
            </label>
            <input
              type="text"
              value={seed}
              onChange={(e) => setSeed(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && run()}
              placeholder="fauteuil releveur, siège senior, fauteuil relaxation électrique"
              data-testid="kwfinder-seed"
              className="w-full h-11 px-3 rounded-lg border border-[#E7E5E4] bg-white text-sm focus:outline-none focus:border-[#6D28D9]"
              autoFocus
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-[#57534E] mb-1.5 uppercase tracking-wider">
              Pays
            </label>
            <select
              value={country}
              onChange={(e) => setCountry(e.target.value)}
              data-testid="kwfinder-country"
              className="h-11 px-3 rounded-lg border border-[#E7E5E4] bg-white text-sm focus:outline-none focus:border-[#6D28D9]"
            >
              {COUNTRIES.map((c) => (
                <option key={c.code} value={c.code}>
                  {c.flag} {c.name}
                </option>
              ))}
            </select>
          </div>
          <button
            onClick={run}
            disabled={loading || !seed.trim()}
            data-testid="kwfinder-run"
            className="h-11 px-5 rounded-lg bg-[#6D28D9] hover:bg-[#5B21B6] disabled:opacity-50 text-white text-sm font-medium flex items-center gap-2 transition"
          >
            {loading ? (
              <>
                <ArrowClockwise size={14} className="animate-spin" /> Google...
              </>
            ) : (
              <>
                <Lightning size={14} weight="fill" /> Générer
              </>
            )}
          </button>
        </div>

        {error && (
          <div className="mx-6 mt-4 p-3 rounded-lg bg-[#FFE4E6] text-[#BE123C] text-xs flex items-start gap-2">
            <Warning size={14} weight="fill" className="shrink-0 mt-0.5" />
            <div>{error}</div>
          </div>
        )}

        <div className="flex-1 overflow-y-auto px-6 py-4">
          {!loading && ideas.length === 0 && !error && (
            <div className="py-16 text-center text-sm text-[#78716C]">
              <MagnifyingGlass size={32} weight="duotone" className="mx-auto mb-3 text-[#A8A29E]" />
              Tape un mot-clé et clique "Générer" pour découvrir jusqu'à 80 idées enrichies par Google.
            </div>
          )}

          {ideas.length > 0 && (
            <>
              <div className="flex items-center justify-between mb-3">
                <div className="text-sm text-[#78716C]">
                  <strong className="text-[#1C1917]">{ideas.length}</strong> idées ·{" "}
                  <strong className="text-[#1C1917]">
                    {ideas
                      .reduce((a, b) => a + b.avg_monthly_searches, 0)
                      .toLocaleString("fr-FR")}
                  </strong>{" "}
                  recherches/mois cumulées
                </div>
                {selectedCount > 0 && (
                  <button
                    onClick={copyAllSelected}
                    data-testid="kwfinder-copy-all"
                    className="h-8 px-3 rounded-lg bg-[#1C1917] hover:bg-[#44403C] text-white text-xs font-medium flex items-center gap-1.5"
                  >
                    {copiedIdx === "all" ? (
                      <>
                        <CheckCircle size={12} weight="fill" /> Copié !
                      </>
                    ) : (
                      <>
                        <Copy size={12} /> Copier {selectedCount} mots
                      </>
                    )}
                  </button>
                )}
              </div>

              <div className="overflow-x-auto rounded-lg border border-[#E7E5E4]">
                <table className="w-full text-sm">
                  <thead className="bg-[#FAF7F2] border-b border-[#E7E5E4] sticky top-0">
                    <tr>
                      <th className="p-2 w-8"></th>
                      <th className="text-left p-2 text-[10px] font-semibold text-[#57534E] uppercase">
                        Mot-clé
                      </th>
                      <th className="text-right p-2 text-[10px] font-semibold text-[#57534E] uppercase">
                        Vol/mois
                      </th>
                      <th className="text-center p-2 text-[10px] font-semibold text-[#57534E] uppercase">
                        Compét.
                      </th>
                      <th className="text-right p-2 text-[10px] font-semibold text-[#57534E] uppercase">
                        CPC bas
                      </th>
                      <th className="text-right p-2 text-[10px] font-semibold text-[#57534E] uppercase">
                        CPC haut
                      </th>
                      <th className="p-2 w-8"></th>
                    </tr>
                  </thead>
                  <tbody>
                    {ideas.map((i, idx) => (
                      <tr
                        key={idx}
                        className="border-b border-[#F5F2EB] hover:bg-[#FAF7F2]/60 transition"
                      >
                        <td className="p-2 text-center">
                          <input
                            type="checkbox"
                            checked={!!selected[i.keyword]}
                            onChange={() => toggleSelect(i.keyword)}
                            data-testid={`kwfinder-select-${idx}`}
                            className="accent-[#6D28D9]"
                          />
                        </td>
                        <td className="p-2 font-medium text-[#1C1917]">{i.keyword}</td>
                        <td className="p-2 text-right font-mono font-semibold">
                          {i.avg_monthly_searches.toLocaleString("fr-FR")}
                        </td>
                        <td className="p-2 text-center">
                          <span
                            className="inline-block px-1.5 py-0.5 rounded-full text-[9px] uppercase tracking-wider font-semibold text-white"
                            style={{ backgroundColor: COMPETITION_COLOR[i.competition] }}
                          >
                            {i.competition}
                          </span>
                        </td>
                        <td className="p-2 text-right font-mono text-xs text-[#78716C]">
                          {i.cpc_low_eur.toFixed(2)}€
                        </td>
                        <td className="p-2 text-right font-mono text-xs">
                          {i.cpc_high_eur.toFixed(2)}€
                        </td>
                        <td className="p-2">
                          <button
                            onClick={() => copyKeyword(i.keyword, idx)}
                            data-testid={`kwfinder-copy-${idx}`}
                            className="w-7 h-7 rounded hover:bg-[#E7E5E4] flex items-center justify-center"
                            title="Copier"
                          >
                            {copiedIdx === idx ? (
                              <CheckCircle size={12} weight="fill" className="text-[#047857]" />
                            ) : (
                              <Copy size={12} className="text-[#78716C]" />
                            )}
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>

        <div className="px-6 py-3 border-t border-[#F5F2EB] text-[11px] text-[#78716C] bg-[#FAFAF9]">
          💡 Sélectionne les mots-clés pertinents pour ta niche et copie-les pour les utiliser dans
          ton <strong>SEO</strong> (meta title/description, pages produits) et tes <strong>Ads</strong>.
        </div>
      </div>
    </div>
  );
}
