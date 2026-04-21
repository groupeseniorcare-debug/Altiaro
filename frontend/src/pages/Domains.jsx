import React, { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api, apiCall } from "../lib/api";
import Layout from "../components/Layout";
import {
  ArrowLeft,
  Globe,
  MagnifyingGlass,
  ArrowClockwise,
  CheckCircle,
  XCircle,
  ShoppingCart,
  Warning,
  Lightning,
  Info,
} from "@phosphor-icons/react";

const TLD_SUGGESTIONS = [".fr", ".com", ".shop", ".store", ".boutique", ".eu"];

export default function Domains() {
  const { id: siteId } = useParams();
  const navigate = useNavigate();
  const [site, setSite] = useState(null);
  const [base, setBase] = useState("");
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [buying, setBuying] = useState(null);
  const [mine, setMine] = useState([]);

  useEffect(() => {
    apiCall(() => api.get(`/sites/${siteId}`)).then(({ data }) => {
      if (data) {
        setSite(data);
        // Auto-suggest from site name
        const slug = (data.name || "")
          .toLowerCase()
          .normalize("NFD")
          .replace(/[\u0300-\u036f]/g, "")
          .replace(/[^a-z0-9]+/g, "-")
          .replace(/^-|-$/g, "")
          .slice(0, 40);
        if (slug) setBase(slug);
      }
    });
    apiCall(() => api.get("/domains")).then(({ data }) => {
      if (data) setMine((data.domains || []).filter((d) => d.site_id === siteId));
    });
  }, [siteId]);

  const runSearch = async () => {
    const trimmed = (base || "").trim().toLowerCase();
    if (!trimmed) return;
    setLoading(true);
    setResults([]);
    setError(null);
    // Check each TLD in parallel
    const promises = TLD_SUGGESTIONS.map((tld) =>
      apiCall(() => api.post("/domains/check", { domain: `${trimmed}${tld}` }))
        .then(({ data, error: err }) => ({
          tld,
          data: data || null,
          error: err || null,
        }))
    );
    const all = await Promise.all(promises);
    setLoading(false);
    setResults(all);
  };

  const purchase = async (domain) => {
    if (
      !window.confirm(
        `Confirmer l'achat de ${domain} pour le site "${site?.name}" ?\n\nLe domaine sera automatiquement configuré pour pointer vers ta boutique.`
      )
    ) {
      return;
    }
    setBuying(domain);
    const { data, error: err } = await apiCall(() =>
      api.post("/domains/purchase", { domain, site_id: siteId })
    );
    setBuying(null);
    if (err) {
      window.alert("Erreur achat : " + err);
      return;
    }
    window.alert(
      `✅ ${domain} acheté !\n\nLa zone DNS sera configurée dans quelques minutes. Tu peux relancer la configuration depuis cette page.`
    );
    setMine((prev) => [data.domain_record, ...prev]);
  };

  const configureDns = async (domain) => {
    const { error: err } = await apiCall(() =>
      api.post(`/domains/${domain}/configure-dns`)
    );
    if (err) {
      if (err.includes("pas encore créée")) {
        window.alert(
          "⏳ La zone DNS OVH est en cours de création (5 à 15 min). Réessaie tout à l'heure."
        );
      } else {
        window.alert("Erreur : " + err);
      }
      return;
    }
    window.alert(`✅ DNS configuré pour ${domain} — la propagation peut prendre 5-30 min.`);
    apiCall(() => api.get("/domains")).then(({ data }) => {
      if (data) setMine((data.domains || []).filter((d) => d.site_id === siteId));
    });
  };

  return (
    <Layout>
      <div className="p-8 md:p-12 max-w-[1100px]">
        <button
          onClick={() => navigate(`/sites/${siteId}`)}
          data-testid="domains-back"
          className="flex items-center gap-2 text-sm text-[#78716C] hover:text-[#1C1917] mb-6 transition"
        >
          <ArrowLeft size={16} /> Retour au site
        </button>

        <div className="flex items-start gap-3 mb-6">
          <div className="w-11 h-11 rounded-lg bg-gradient-to-br from-[#2563EB] to-[#7C3AED] flex items-center justify-center">
            <Globe size={22} weight="fill" color="#fff" />
          </div>
          <div>
            <div className="text-[11px] uppercase tracking-widest text-[#78716C] mb-1">
              Nom de domaine · OVH
            </div>
            <h1 className="font-heading text-4xl font-semibold text-[#1C1917]">
              Choisis ton nom de domaine
            </h1>
            <p className="text-[#57534E] mt-1">
              Achat en 1 clic, DNS auto-configuré sur ta boutique.
              {site?.name && <> Site : <strong>{site.name}</strong></>}
            </p>
          </div>
        </div>

        {/* Existing domains on this site */}
        {mine.length > 0 && (
          <div className="bg-white rounded-xl border border-[#D1FAE5] p-5 mb-6">
            <div className="flex items-center gap-2 mb-3">
              <CheckCircle size={18} weight="fill" className="text-[#047857]" />
              <div className="font-medium text-[#1C1917]">
                Domaines liés à ce site
              </div>
            </div>
            <div className="space-y-2">
              {mine.map((d) => (
                <div
                  key={d.id}
                  data-testid={`domain-mine-${d.domain}`}
                  className="flex items-center justify-between bg-[#FAF7F2] rounded-lg p-3"
                >
                  <div className="flex items-center gap-3">
                    <Globe size={16} className="text-[#047857]" />
                    <div>
                      <div className="font-mono font-medium text-sm">{d.domain}</div>
                      <div className="text-xs text-[#78716C]">
                        Statut : <strong>{d.status}</strong> · Acheté le{" "}
                        {d.purchased_at?.slice(0, 10)}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {d.status === "purchased" && (
                      <button
                        onClick={() => configureDns(d.domain)}
                        data-testid={`dns-${d.domain}`}
                        className="h-8 px-3 rounded-lg bg-[#2563EB] hover:bg-[#1D4ED8] text-white text-xs font-medium"
                      >
                        Configurer DNS
                      </button>
                    )}
                    {d.status === "dns_configured" && (
                      <span className="text-[10px] uppercase tracking-wider px-2 py-1 rounded-full bg-[#D1FAE5] text-[#047857] font-semibold">
                        ✓ Actif
                      </span>
                    )}
                    <a
                      href={`https://${d.domain}`}
                      target="_blank"
                      rel="noreferrer"
                      className="text-xs text-[#2563EB] hover:underline"
                    >
                      Visiter →
                    </a>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Search */}
        <div className="bg-white rounded-xl border border-[#E7E5E4] p-5 mb-5">
          <label className="block text-xs font-semibold text-[#57534E] mb-1.5 uppercase tracking-wider">
            Nom souhaité (sans extension)
          </label>
          <div className="flex gap-2">
            <div className="flex-1 relative">
              <MagnifyingGlass
                size={16}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-[#78716C]"
              />
              <input
                type="text"
                value={base}
                onChange={(e) =>
                  setBase(e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, ""))
                }
                onKeyDown={(e) => e.key === "Enter" && runSearch()}
                placeholder="maboutique-senior"
                data-testid="domain-search-input"
                className="w-full h-12 pl-10 pr-3 rounded-xl border border-[#E7E5E4] bg-white text-sm focus:outline-none focus:border-[#2563EB]"
              />
            </div>
            <button
              onClick={runSearch}
              disabled={loading || !base.trim()}
              data-testid="domain-search-btn"
              className="h-12 px-5 rounded-xl bg-[#1C1917] hover:bg-[#44403C] disabled:opacity-50 text-white text-sm font-medium flex items-center gap-2"
            >
              {loading ? (
                <>
                  <ArrowClockwise size={14} className="animate-spin" /> Vérification…
                </>
              ) : (
                <>
                  <Lightning size={14} weight="fill" /> Vérifier
                </>
              )}
            </button>
          </div>
          <div className="text-[11px] text-[#78716C] mt-2">
            On vérifie la dispo sur {TLD_SUGGESTIONS.length} extensions en parallèle.
          </div>
        </div>

        {/* Results */}
        {results.length > 0 && (
          <div className="space-y-2">
            {results.map((r) => {
              const fullDomain = `${base}${r.tld}`;
              const isAvail = r.data?.available;
              const price = r.data?.platform_price_eur;
              const isBuying = buying === fullDomain;
              return (
                <div
                  key={r.tld}
                  data-testid={`domain-result-${r.tld}`}
                  className={`bg-white rounded-xl border p-4 flex items-center gap-4 transition ${
                    isAvail ? "border-[#D1FAE5]" : "border-[#E7E5E4] opacity-60"
                  }`}
                >
                  <div
                    className={`w-10 h-10 rounded-full flex items-center justify-center ${
                      isAvail ? "bg-[#D1FAE5]" : "bg-[#F5F2EB]"
                    }`}
                  >
                    {isAvail ? (
                      <CheckCircle size={20} weight="fill" className="text-[#047857]" />
                    ) : (
                      <XCircle size={20} weight="fill" className="text-[#78716C]" />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="font-mono text-lg font-medium text-[#1C1917]">
                      {fullDomain}
                    </div>
                    <div className="text-xs text-[#78716C]">
                      {r.error ? (
                        <span className="text-[#BE123C]">Erreur : {r.error}</span>
                      ) : isAvail ? (
                        <>
                          Disponible · Prix TTC année 1 :{" "}
                          <strong className="text-[#047857]">{price}€</strong>
                          <span className="text-[#A8A29E]">
                            {" "}(coût OVH {r.data.ovh_price_ttc_eur}€ + frais {r.data.markup_eur}€)
                          </span>
                        </>
                      ) : (
                        "Déjà pris"
                      )}
                    </div>
                  </div>
                  {isAvail && (
                    <button
                      onClick={() => purchase(fullDomain)}
                      disabled={isBuying}
                      data-testid={`buy-${r.tld}`}
                      className="h-10 px-4 rounded-xl bg-gradient-to-r from-[#2563EB] to-[#7C3AED] text-white text-sm font-medium flex items-center gap-2 disabled:opacity-60"
                    >
                      {isBuying ? (
                        <>
                          <ArrowClockwise size={14} className="animate-spin" />
                          Achat en cours…
                        </>
                      ) : (
                        <>
                          <ShoppingCart size={14} weight="fill" /> Acheter {price}€
                        </>
                      )}
                    </button>
                  )}
                </div>
              );
            })}
          </div>
        )}

        <div className="mt-6 p-4 rounded-xl bg-[#FAF7F2] border border-[#E7E5E4]">
          <div className="flex items-start gap-2">
            <Info size={16} className="text-[#2563EB] shrink-0 mt-0.5" />
            <div className="text-xs text-[#57534E] leading-relaxed">
              <strong>Comment ça marche :</strong> tu achètes le domaine en 1 clic, on le
              configure automatiquement pour qu'il pointe vers ta boutique. La propagation DNS
              prend en général 5 à 30 minutes. Renouvellement automatique chaque année au même prix.
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
}
