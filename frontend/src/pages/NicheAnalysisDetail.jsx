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
    return <Layout><div className="p-8 text-neutral-500">Chargement…</div></Layout>;
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
        <button onClick={() => navigate("/niches")} data-testid="back-btn" className="text-sm text-neutral-500 hover:text-neutral-900 flex items-center gap-1 mb-4">
          <CaretLeft size={14} /> Retour aux analyses
        </button>

        {/* Hero verdict */}
        <div className="bg-white rounded-md border border-neutral-200 p-7 mb-6">
          <div className="flex items-start gap-5 flex-wrap">
            <div className="text-6xl">{a.emoji || "📦"}</div>
            <div className="flex-1 min-w-[280px]">
              <div className="text-[11px] uppercase tracking-widest text-neutral-500 mb-1">{a.category}</div>
              <h1 className="text-2xl md:text-4xl font-semibold text-neutral-900">{a.name || data.product_input}</h1>
              <p className="text-neutral-600 mt-2 max-w-2xl">{a.description}</p>
              {a.tagline && <p className="text-sm italic text-neutral-900 mt-2">« {a.tagline} »</p>}
            </div>
            <div className="text-right">
              <VerdictBigPill verdict={a.overall_verdict} />
              <div className="text-xs text-neutral-500 mt-2">Score ECF : <span className="font-semibold text-neutral-900">{a.ecf_score || 0}/100</span></div>
            </div>
          </div>
          {a.verdict_reasoning && (
            <div className="mt-4 text-sm bg-white rounded-xl p-4 border border-neutral-200">
              <strong>Verdict :</strong> {a.verdict_reasoning}
            </div>
          )}
          {a.google_verified && (
            <div
              data-testid="analysis-google-verified"
              className="mt-3 flex items-center gap-2 p-3 rounded-xl bg-gradient-to-r from-[#4285F4]/5 to-[#34A853]/5 border border-[#4285F4]/20 text-sm"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
                <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
                <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
                <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
              </svg>
              <span className="text-[#1A73E8] font-medium">
                ✓ Volumes et CPCs enrichis avec les données réelles Google Keyword Planner
              </span>
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
          <div className="bg-white rounded-md border border-neutral-200 p-5 mb-6">
            <div className="flex items-center gap-2 mb-2">
              <Sparkle size={16} weight="fill" className="text-neutral-900" />
              <div className="font-heading font-semibold text-neutral-900">Stratégie de lancement recommandée</div>
            </div>
            <div className="flex items-center gap-2 mb-2 flex-wrap">
              {(a.launch_strategy.priority_order || []).map((c, i) => (
                <React.Fragment key={c}>
                  <span className="px-3 py-1.5 rounded-lg bg-white/10 text-neutral-900 font-medium text-sm flex items-center gap-1.5">
                    {i + 1}. {COUNTRY_FLAGS[c] || "🌍"} {COUNTRY_NAMES[c] || c}
                  </span>
                  {i < (a.launch_strategy.priority_order?.length || 0) - 1 && <ArrowRight size={14} className="text-neutral-500" />}
                </React.Fragment>
              ))}
            </div>
            <p className="text-sm text-neutral-600">{a.launch_strategy.reasoning}</p>
          </div>
        )}

        {/* Country selector */}
        <div className="bg-white rounded-md border border-neutral-200 p-5 mb-6 sticky top-4 z-10 shadow-sm">
          <div className="flex items-center justify-between gap-4 flex-wrap">
            <div>
              <div className="font-heading font-semibold text-neutral-900">
                Pays à lancer ({selectedCountries.length} sélectionné{selectedCountries.length > 1 ? "s" : ""})
              </div>
              <div className="text-xs text-neutral-500">Les pays en verdict GO sont cochés par défaut</div>
            </div>
            <button
              onClick={createSite}
              disabled={selectedCountries.length === 0}
              data-testid="create-site-btn"
              className="h-11 px-5 rounded-xl bg-white hover:bg-[#A33E26] text-black text-sm font-medium flex items-center gap-2 transition disabled:opacity-40"
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
                    sel ? "border-[#B84B31] bg-white/5" : "border-neutral-200 hover:border-[#B84B31]/40"
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
        <div className="bg-white rounded-md border border-neutral-200 mb-6 overflow-hidden">
          <div className="border-b border-neutral-200 flex overflow-x-auto">
            {countries.map((c) => (
              <button
                key={c}
                onClick={() => setActiveTab(c)}
                data-testid={`tab-${c}`}
                className={`px-5 py-3 text-sm font-medium border-b-2 transition whitespace-nowrap flex items-center gap-1.5 ${
                  activeTab === c ? "border-[#B84B31] text-neutral-900" : "border-transparent text-neutral-500 hover:text-neutral-900"
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
            <div className="bg-white rounded-md border border-neutral-200 p-5">
              <div className="flex items-center gap-2 mb-3">
                <Warning size={16} weight="fill" className="text-red-400" />
                <div className="font-heading font-semibold text-neutral-900">Risques identifiés</div>
              </div>
              <ul className="space-y-2">
                {a.risks.map((r, i) => (
                  <li key={i} className="text-sm text-neutral-600 flex gap-2">
                    <span className="text-red-400 mt-0.5">•</span> {r}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {a.opportunities?.length > 0 && (
            <div className="bg-white rounded-md border border-neutral-200 p-5">
              <div className="flex items-center gap-2 mb-3">
                <Target size={16} weight="fill" className="text-emerald-400" />
                <div className="font-heading font-semibold text-neutral-900">Opportunités de différenciation</div>
              </div>
              <ul className="space-y-2">
                {a.opportunities.map((o, i) => (
                  <li key={i} className="text-sm text-neutral-600 flex gap-2">
                    <span className="text-emerald-400 mt-0.5">•</span> {o}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* Suppliers */}
        {a.suppliers?.length > 0 && (
          <div className="bg-white rounded-md border border-neutral-200 p-5 mb-6">
            <div className="flex items-center gap-2 mb-3">
              <Package size={16} weight="fill" className="text-neutral-900" />
              <div className="font-heading font-semibold text-neutral-900">Fournisseurs suggérés</div>
            </div>
            <div className="grid md:grid-cols-3 gap-3">
              {a.suppliers.map((s, i) => (
                <div key={i} className="border border-neutral-200 rounded-xl p-3" data-testid={`supplier-${i}`}>
                  <div className="flex items-center justify-between mb-1">
                    <div className="font-semibold text-neutral-900">{s.name}</div>
                    <RelevancePill level={s.relevance} />
                  </div>
                  <div className="text-xs text-neutral-600">{s.reasoning}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Positioning matrix */}
        {a.positioning_matrix?.white_space && (
          <div className="bg-gradient-to-br from-[#FEF3C7] to-[#FDFBF7] rounded-md border border-[#FDE68A] p-5 mb-6">
            <div className="flex items-center gap-2 mb-2">
              <Sparkle size={14} weight="fill" className="text-[#854D0E]" />
              <div className="font-heading font-semibold text-neutral-900">White space — positionnement libre</div>
            </div>
            <p className="text-sm text-neutral-600">{a.positioning_matrix.white_space}</p>
          </div>
        )}
      </div>
    </Layout>
  );
}

function Kpi({ icon: Icon, label, value, color }) {
  return (
    <div className="bg-white rounded-xl border border-neutral-200 p-4">
      <div className="flex items-center gap-2 text-[11px] uppercase tracking-widest text-neutral-500 mb-1">
        <Icon size={12} style={{ color }} /> {label}
      </div>
      <div className="text-lg font-semibold text-neutral-900 tabular-nums">{value}</div>
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
        <div className="flex items-start gap-3 bg-white rounded-xl p-4 border border-neutral-200">
          <div className="text-3xl">{COUNTRY_FLAGS[code]}</div>
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <div className="font-heading font-semibold text-neutral-900">{COUNTRY_NAMES[code] || code}</div>
              <VerdictSmall verdict={verdict.verdict} />
            </div>
            <p className="text-sm text-neutral-600">{verdict.reasoning}</p>
          </div>
        </div>
      )}

      {/* Market sizing */}
      {sizing && (
        <Section title="Taille du marché" icon={TrendUp}>
          {sizing.google_verified && (
            <div
              data-testid={`google-verified-${code}`}
              className="mb-3 inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-gradient-to-r from-[#4285F4]/10 to-[#34A853]/10 border border-[#4285F4]/30 text-xs font-medium text-[#1A73E8]"
            >
              <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
                <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
                <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
              </svg>
              Volumes vérifiés par Google Keyword Planner
            </div>
          )}
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
          {sizing.commentary && <p className="text-sm text-neutral-600 italic">{sizing.commentary}</p>}
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
              <div key={i} className="border border-neutral-200 rounded-lg p-3 flex gap-3 items-start" data-testid={`competitor-${i}`}>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-semibold text-neutral-900">{c.name}</span>
                    <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-neutral-200 text-neutral-600 uppercase tracking-wider">{c.type}</span>
                    <span className="text-xs text-neutral-500">· {c.price_range}</span>
                    {c.market_share_pct !== undefined && <span className="text-xs text-neutral-500">· {c.market_share_pct}% PDM</span>}
                  </div>
                  <div className="text-xs text-neutral-600">
                    <span className="text-emerald-400">✓ {c.strength}</span> · <span className="text-red-400">✗ {c.weakness}</span>
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
            <div className="mt-3 text-sm text-neutral-600">
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
        <Icon size={14} weight="fill" className="text-neutral-900" />
        <div className="font-heading font-semibold text-neutral-900">{title}</div>
      </div>
      {children}
    </div>
  );
}

function MiniKpi({ label, value, color }) {
  return (
    <div className="bg-white rounded-lg border border-neutral-200 p-3">
      <div className="text-[10px] uppercase tracking-wider text-neutral-500">{label}</div>
      <div className="font-heading font-semibold text-sm tabular-nums mt-0.5" style={{ color: color || "#1C1917" }}>{value}</div>
    </div>
  );
}

function KeywordBlock({ label, items, color }) {
  if (!items?.length) return null;
  return (
    <div className="mb-3">
      <div className="text-[11px] uppercase tracking-widest text-neutral-500 mb-1.5">{label}</div>
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
      <Icon size={13} className="text-neutral-500 flex-shrink-0 mt-0.5" />
      <div className="min-w-0 flex-1">
        <div className="text-[11px] uppercase tracking-wider text-neutral-500">{label}</div>
        <div className="text-sm text-neutral-900 break-words">{value}</div>
      </div>
    </div>
  );
}
