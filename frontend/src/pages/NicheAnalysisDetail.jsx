import React, { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import Layout from "../components/Layout";
import { api, apiCall } from "../lib/api";
import {
  CaretLeft,
  CheckCircle,
  XCircle,
  Warning,
  TrendUp,
  CurrencyEur,
  ChartBar,
  Target,
  ShieldCheck,
  Truck,
  Storefront,
  Package,
  Sparkle,
  ArrowRight,
  Globe,
  ListChecks,
} from "@phosphor-icons/react";

const COUNTRY_FLAGS = {
  FR: "🇫🇷", DE: "🇩🇪", UK: "🇬🇧", CH: "🇨🇭", BE: "🇧🇪", NL: "🇳🇱", IT: "🇮🇹", ES: "🇪🇸",
};
const COUNTRY_NAMES = {
  FR: "France", DE: "Allemagne", UK: "Royaume-Uni", CH: "Suisse", BE: "Belgique", NL: "Pays-Bas",
  IT: "Italie", ES: "Espagne",
};

const fmtNum = (n) => (Number(n) || 0).toLocaleString("fr-FR");
const fmtEUR = (n) => new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR", maximumFractionDigits: 0 }).format(Number(n) || 0);

export default function AnalysisDetail() {
  const { id } = useParams();
  const [data, setData] = useState(null);
  const [selectedCountries, setSelectedCountries] = useState([]);
  const [activeTab, setActiveTab] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    (async () => {
      const { data: d } = await apiCall(() => api.get(`/niches/analyses/${id}`));
      if (d) {
        setData(d);
        const analysis = d.analysis || {};
        const go = analysis.go_countries || [];
        setSelectedCountries(go.length ? go : (analysis.countries || Object.keys(analysis.country_verdicts || {})));
        setActiveTab((analysis.countries || [])[0] || Object.keys(analysis.country_verdicts || {})[0]);
      }
    })();
  }, [id]);

  if (!data) {
    return <Layout><div className="p-8 text-[#78716C]">Chargement…</div></Layout>;
  }

  const a = data.analysis || {};
  const countries = a.countries || Object.keys(a.country_verdicts || {});
  const verdicts = a.country_verdicts || {};
  const sizing = a.country_sizing || {};
  const competitors = a.competitors_by_country || {};
  const legal = a.legal_ops_by_country || {};
  const keywords = a.keywords_by_country || {};
  const pricing = a.pricing_by_country || {};

  const toggle = (c) =>
    setSelectedCountries((s) => (s.includes(c) ? s.filter((x) => x !== c) : [...s, c]));

  const createSite = () => {
    if (selectedCountries.length === 0) return;
    const params = new URLSearchParams({
      name: a.name || data.product_input,
      niche: a.name || data.product_input,
      niche_slug: a.slug || "",
      analysis_id: data.id,
      countries: selectedCountries.join(","),
      daily_budget: "30",
    });
    navigate(`/sites/new?${params.toString()}`);
  };

  return (
    <Layout>
      <div className="p-6 md:p-10 max-w-6xl mx-auto">
        <button onClick={() => navigate("/niches")} data-testid="back-btn" className="text-sm text-[#78716C] hover:text-[#1C1917] flex items-center gap-1 mb-4">
          <CaretLeft size={14} /> Retour aux analyses
        </button>

        {/* Hero verdict */}
        <div className="bg-white rounded-2xl border border-[#E7E5E4] p-7 mb-6">
          <div className="flex items-start gap-5 flex-wrap">
            <div className="text-6xl">{a.emoji || "📦"}</div>
            <div className="flex-1 min-w-[280px]">
              <div className="text-[11px] uppercase tracking-widest text-[#78716C] mb-1">{a.category}</div>
              <h1 className="font-heading text-3xl md:text-4xl font-semibold text-[#1C1917]">{a.name || data.product_input}</h1>
              <p className="text-[#57534E] mt-2 max-w-2xl">{a.description}</p>
              {a.tagline && <p className="text-sm italic text-[#B84B31] mt-2">« {a.tagline} »</p>}
            </div>
            <div className="text-right">
              <VerdictBigPill verdict={a.overall_verdict} />
              <div className="text-xs text-[#78716C] mt-2">Score ECF : <span className="font-semibold text-[#1C1917]">{a.ecf_score || 0}/100</span></div>
            </div>
          </div>
          {a.verdict_reasoning && (
            <div className="mt-4 text-sm bg-[#FDFBF7] rounded-xl p-4 border border-[#E7E5E4]">
              <strong>Verdict :</strong> {a.verdict_reasoning}
            </div>
          )}
        </div>

        {/* Top KPIs */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
          <Kpi icon={TrendUp} label={`Volume total / mois (${countries.length} pays)`} value={fmtNum(a.total_volume_monthly)} color="#B84B31" />
          <Kpi icon={ChartBar} label="CPC moyen" value={`${a.avg_cpc_eur || 0} €`} color="#0E7490" />
          <Kpi icon={Globe} label="Pays GO" value={(a.go_countries || []).length + " / " + countries.length} color="#047857" />
          <Kpi icon={Target} label="Persona" value={(data.persona || "tout public").replace("_", " ")} color="#854D0E" />
        </div>

        {/* Launch strategy */}
        {a.launch_strategy && (
          <div className="bg-white rounded-2xl border border-[#E7E5E4] p-5 mb-6">
            <div className="flex items-center gap-2 mb-2">
              <Sparkle size={16} weight="fill" className="text-[#B84B31]" />
              <div className="font-heading font-semibold text-[#1C1917]">Stratégie de lancement recommandée</div>
            </div>
            <div className="flex items-center gap-2 mb-2 flex-wrap">
              {(a.launch_strategy.priority_order || []).map((c, i) => (
                <React.Fragment key={c}>
                  <span className="px-3 py-1.5 rounded-lg bg-[#B84B31]/10 text-[#B84B31] font-medium text-sm flex items-center gap-1.5">
                    {i + 1}. {COUNTRY_FLAGS[c] || "🌍"} {COUNTRY_NAMES[c] || c}
                  </span>
                  {i < (a.launch_strategy.priority_order?.length || 0) - 1 && <ArrowRight size={14} className="text-[#78716C]" />}
                </React.Fragment>
              ))}
            </div>
            <p className="text-sm text-[#57534E]">{a.launch_strategy.reasoning}</p>
          </div>
        )}

        {/* Country selector */}
        <div className="bg-white rounded-2xl border border-[#E7E5E4] p-5 mb-6 sticky top-4 z-10 shadow-sm">
          <div className="flex items-center justify-between gap-4 flex-wrap">
            <div>
              <div className="font-heading font-semibold text-[#1C1917]">
                Pays à lancer ({selectedCountries.length} sélectionné{selectedCountries.length > 1 ? "s" : ""})
              </div>
              <div className="text-xs text-[#78716C]">Les pays en verdict GO sont cochés par défaut</div>
            </div>
            <button
              onClick={createSite}
              disabled={selectedCountries.length === 0}
              data-testid="create-site-btn"
              className="h-11 px-5 rounded-xl bg-[#B84B31] hover:bg-[#A33E26] text-white text-sm font-medium flex items-center gap-2 transition disabled:opacity-40"
            >
              <Storefront size={16} weight="fill" /> Créer mon site sur ces pays
            </button>
          </div>
          <div className="flex flex-wrap gap-2 mt-3">
            {countries.map((c) => {
              const v = verdicts[c]?.verdict;
              const sel = selectedCountries.includes(c);
              return (
                <button
                  key={c}
                  onClick={() => toggle(c)}
                  data-testid={`toggle-${c}`}
                  className={`h-10 px-3 rounded-lg border text-sm flex items-center gap-2 transition ${
                    sel ? "border-[#B84B31] bg-[#B84B31]/5" : "border-[#E7E5E4] hover:border-[#B84B31]/40"
                  }`}
                >
                  <span>{COUNTRY_FLAGS[c]}</span>
                  <span className="font-medium">{COUNTRY_NAMES[c] || c}</span>
                  <VerdictSmall verdict={v} />
                </button>
              );
            })}
          </div>
        </div>

        {/* Country tabs */}
        <div className="bg-white rounded-2xl border border-[#E7E5E4] mb-6 overflow-hidden">
          <div className="border-b border-[#E7E5E4] flex overflow-x-auto">
            {countries.map((c) => (
              <button
                key={c}
                onClick={() => setActiveTab(c)}
                data-testid={`tab-${c}`}
                className={`px-5 py-3 text-sm font-medium border-b-2 transition whitespace-nowrap flex items-center gap-1.5 ${
                  activeTab === c ? "border-[#B84B31] text-[#1C1917]" : "border-transparent text-[#78716C] hover:text-[#1C1917]"
                }`}
              >
                <span>{COUNTRY_FLAGS[c]}</span> {COUNTRY_NAMES[c] || c}
                <VerdictSmall verdict={verdicts[c]?.verdict} />
              </button>
            ))}
          </div>
          {activeTab && (
            <CountryPanel
              code={activeTab}
              verdict={verdicts[activeTab]}
              sizing={sizing[activeTab]}
              competitors={competitors[activeTab] || []}
              legal={legal[activeTab]}
              keywords={keywords[activeTab]}
              pricing={pricing[activeTab]}
            />
          )}
        </div>

        {/* Risks & Opportunities */}
        <div className="grid md:grid-cols-2 gap-4 mb-6">
          {a.risks?.length > 0 && (
            <div className="bg-white rounded-2xl border border-[#E7E5E4] p-5">
              <div className="flex items-center gap-2 mb-3">
                <Warning size={16} weight="fill" className="text-[#BE123C]" />
                <div className="font-heading font-semibold text-[#1C1917]">Risques identifiés</div>
              </div>
              <ul className="space-y-2">
                {a.risks.map((r, i) => (
                  <li key={i} className="text-sm text-[#57534E] flex gap-2">
                    <span className="text-[#BE123C] mt-0.5">•</span> {r}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {a.opportunities?.length > 0 && (
            <div className="bg-white rounded-2xl border border-[#E7E5E4] p-5">
              <div className="flex items-center gap-2 mb-3">
                <Target size={16} weight="fill" className="text-[#047857]" />
                <div className="font-heading font-semibold text-[#1C1917]">Opportunités de différenciation</div>
              </div>
              <ul className="space-y-2">
                {a.opportunities.map((o, i) => (
                  <li key={i} className="text-sm text-[#57534E] flex gap-2">
                    <span className="text-[#047857] mt-0.5">•</span> {o}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* Suppliers */}
        {a.suppliers?.length > 0 && (
          <div className="bg-white rounded-2xl border border-[#E7E5E4] p-5 mb-6">
            <div className="flex items-center gap-2 mb-3">
              <Package size={16} weight="fill" className="text-[#B84B31]" />
              <div className="font-heading font-semibold text-[#1C1917]">Fournisseurs suggérés</div>
            </div>
            <div className="grid md:grid-cols-3 gap-3">
              {a.suppliers.map((s, i) => (
                <div key={i} className="border border-[#E7E5E4] rounded-xl p-3" data-testid={`supplier-${i}`}>
                  <div className="flex items-center justify-between mb-1">
                    <div className="font-semibold text-[#1C1917]">{s.name}</div>
                    <RelevancePill level={s.relevance} />
                  </div>
                  <div className="text-xs text-[#57534E]">{s.reasoning}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Positioning matrix */}
        {a.positioning_matrix?.white_space && (
          <div className="bg-gradient-to-br from-[#FEF3C7] to-[#FDFBF7] rounded-2xl border border-[#FDE68A] p-5 mb-6">
            <div className="flex items-center gap-2 mb-2">
              <Sparkle size={14} weight="fill" className="text-[#854D0E]" />
              <div className="font-heading font-semibold text-[#1C1917]">White space — positionnement libre</div>
            </div>
            <p className="text-sm text-[#57534E]">{a.positioning_matrix.white_space}</p>
          </div>
        )}
      </div>
    </Layout>
  );
}

function Kpi({ icon: Icon, label, value, color }) {
  return (
    <div className="bg-white rounded-xl border border-[#E7E5E4] p-4">
      <div className="flex items-center gap-2 text-[11px] uppercase tracking-widest text-[#78716C] mb-1">
        <Icon size={12} style={{ color }} /> {label}
      </div>
      <div className="font-heading text-xl font-semibold text-[#1C1917] tabular-nums">{value}</div>
    </div>
  );
}

function VerdictBigPill({ verdict }) {
  const map = {
    GO: { bg: "#DCF5E7", fg: "#047857", label: "GO · Lance-toi", icon: CheckCircle },
    MAYBE: { bg: "#FEF3C7", fg: "#854D0E", label: "À creuser", icon: Warning },
    NOGO: { bg: "#FEE2E2", fg: "#B91C1C", label: "Pass", icon: XCircle },
  };
  const s = map[verdict] || { bg: "#F5F2EB", fg: "#78716C", label: "—", icon: Warning };
  const Icon = s.icon;
  return (
    <div className="inline-flex items-center gap-1.5 px-4 py-2 rounded-full font-semibold" style={{ background: s.bg, color: s.fg }} data-testid="verdict-pill">
      <Icon size={16} weight="fill" /> {s.label}
    </div>
  );
}

function VerdictSmall({ verdict }) {
  if (!verdict) return null;
  const color = verdict === "GO" ? "#047857" : verdict === "MAYBE" ? "#854D0E" : "#B91C1C";
  const bg = verdict === "GO" ? "#DCF5E7" : verdict === "MAYBE" ? "#FEF3C7" : "#FEE2E2";
  return (
    <span className="text-[10px] font-bold px-1.5 py-0.5 rounded" style={{ background: bg, color }}>
      {verdict}
    </span>
  );
}

function RelevancePill({ level }) {
  const map = { high: { bg: "#DCF5E7", fg: "#047857", label: "Forte" },
                medium: { bg: "#FEF3C7", fg: "#854D0E", label: "Moyenne" },
                low: { bg: "#FEE2E2", fg: "#B91C1C", label: "Faible" } };
  const s = map[level] || map.medium;
  return <span className="text-[10px] font-bold px-2 py-0.5 rounded-full" style={{ background: s.bg, color: s.fg }}>{s.label}</span>;
}

/* ---------- Country detail panel ---------- */
function CountryPanel({ code, verdict, sizing, competitors, legal, keywords, pricing }) {
  return (
    <div className="p-6 space-y-6" data-testid={`panel-${code}`}>
      {/* Verdict */}
      {verdict && (
        <div className="flex items-start gap-3 bg-[#FDFBF7] rounded-xl p-4 border border-[#E7E5E4]">
          <div className="text-3xl">{COUNTRY_FLAGS[code]}</div>
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <div className="font-heading font-semibold text-[#1C1917]">{COUNTRY_NAMES[code] || code}</div>
              <VerdictSmall verdict={verdict.verdict} />
            </div>
            <p className="text-sm text-[#57534E]">{verdict.reasoning}</p>
          </div>
        </div>
      )}

      {/* Market sizing */}
      {sizing && (
        <Section title="Taille du marché" icon={TrendUp}>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
            <MiniKpi label="Volume/mois" value={fmtNum(sizing.monthly_search_volume)} />
            <MiniKpi label="CPC moyen" value={`${sizing.cpc_avg_eur || 0} €`} />
            <MiniKpi label="KD" value={`${sizing.kd || 0}/100`} />
            <MiniKpi label="AOV" value={fmtEUR(sizing.aov_eur)} />
            <MiniKpi label="Marché total/an" value={fmtEUR(sizing.market_size_annual_eur)} />
            <MiniKpi label="Croissance 3a" value={`${sizing.growth_3y_pct || 0}%/an`} />
            <MiniKpi label="Pénétration e-com" value={`${sizing.ecommerce_penetration_pct || 0}%`} />
            <MiniKpi label="Saisonnalité" value={sizing.seasonality || "—"} />
          </div>
          {sizing.commentary && <p className="text-sm text-[#57534E] italic">{sizing.commentary}</p>}
        </Section>
      )}

      {/* Pricing */}
      {pricing && (
        <Section title="Pricing recommandé" icon={CurrencyEur}>
          <div className="grid grid-cols-3 gap-3">
            <MiniKpi label="Prix de vente TTC" value={fmtEUR(pricing.sell_ttc_eur)} color="#B84B31" />
            <MiniKpi label="Prix d'achat HT cible" value={fmtEUR(pricing.cost_ht_target_eur)} />
            <MiniKpi label="Marge HT" value={`${pricing.margin_pct || 0}%`} color="#047857" />
          </div>
        </Section>
      )}

      {/* Keywords */}
      {keywords && (
        <Section title="Mots-clés stratégiques (langue native)" icon={Target}>
          <KeywordBlock label="Transactionnels (intent achat)" items={keywords.transactional} color="#B84B31" />
          <KeywordBlock label="Informationnels" items={keywords.informational} color="#0E7490" />
          <KeywordBlock label="Longue traîne" items={keywords.long_tail} color="#78716C" />
        </Section>
      )}

      {/* Competitors */}
      {competitors.length > 0 && (
        <Section title={`Concurrence (${competitors.length})`} icon={Storefront}>
          <div className="space-y-2">
            {competitors.map((c, i) => (
              <div key={i} className="border border-[#E7E5E4] rounded-lg p-3 flex gap-3 items-start" data-testid={`competitor-${i}`}>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-semibold text-[#1C1917]">{c.name}</span>
                    <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-[#F5F2EB] text-[#57534E] uppercase tracking-wider">{c.type}</span>
                    <span className="text-xs text-[#78716C]">· {c.price_range}</span>
                    {c.market_share_pct !== undefined && <span className="text-xs text-[#78716C]">· {c.market_share_pct}% PDM</span>}
                  </div>
                  <div className="text-xs text-[#57534E]">
                    <span className="text-[#047857]">✓ {c.strength}</span> · <span className="text-[#BE123C]">✗ {c.weakness}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* Legal */}
      {legal && (
        <Section title="Cadre légal & logistique" icon={ShieldCheck}>
          <div className="grid md:grid-cols-2 gap-3 text-sm">
            <LegalRow icon={ShieldCheck} label="Certifications" value={legal.mandatory_certifications?.join(", ") || "—"} />
            <LegalRow icon={ListChecks} label="Mentions obligatoires" value={legal.mandatory_mentions?.join(", ") || "—"} />
            <LegalRow icon={CurrencyEur} label="TVA" value={`${legal.vat_pct || 0}%`} />
            <LegalRow icon={Globe} label="Douanes (hors UE)" value={`${legal.customs_duty_pct_outside_eu || 0}%`} />
            <LegalRow icon={Truck} label="Transporteurs" value={legal.preferred_carriers?.join(", ") || "—"} />
            <LegalRow icon={Truck} label="Délai livraison" value={`${legal.expected_delivery_days || "—"} jours`} />
            <LegalRow icon={Globe} label="Langue SAV" value={legal.support_language || "—"} />
            <LegalRow icon={CurrencyEur} label="Paiements préférés" value={legal.preferred_payment_methods?.join(", ") || "—"} />
          </div>
          {legal.specific_regulations?.length > 0 && (
            <div className="mt-3 text-sm text-[#57534E]">
              <strong>Réglementation particulière :</strong> {legal.specific_regulations.join(" · ")}
            </div>
          )}
        </Section>
      )}
    </div>
  );
}

function Section({ title, icon: Icon, children }) {
  return (
    <div>
      <div className="flex items-center gap-2 mb-3">
        <Icon size={14} weight="fill" className="text-[#B84B31]" />
        <div className="font-heading font-semibold text-[#1C1917]">{title}</div>
      </div>
      {children}
    </div>
  );
}

function MiniKpi({ label, value, color }) {
  return (
    <div className="bg-[#FDFBF7] rounded-lg border border-[#E7E5E4] p-3">
      <div className="text-[10px] uppercase tracking-wider text-[#78716C]">{label}</div>
      <div className="font-heading font-semibold text-sm tabular-nums mt-0.5" style={{ color: color || "#1C1917" }}>{value}</div>
    </div>
  );
}

function KeywordBlock({ label, items, color }) {
  if (!items?.length) return null;
  return (
    <div className="mb-3">
      <div className="text-[11px] uppercase tracking-widest text-[#78716C] mb-1.5">{label}</div>
      <div className="flex flex-wrap gap-1.5">
        {items.map((k, i) => (
          <span key={i} className="text-xs px-2.5 py-1 rounded-full font-medium" style={{ background: `${color}15`, color }}>
            {k}
          </span>
        ))}
      </div>
    </div>
  );
}

function LegalRow({ icon: Icon, label, value }) {
  return (
    <div className="flex gap-2 items-start">
      <Icon size={13} className="text-[#78716C] flex-shrink-0 mt-0.5" />
      <div className="min-w-0 flex-1">
        <div className="text-[11px] uppercase tracking-wider text-[#78716C]">{label}</div>
        <div className="text-sm text-[#1C1917] break-words">{value}</div>
      </div>
    </div>
  );
}
