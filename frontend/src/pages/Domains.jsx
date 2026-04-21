import React, { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
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
  Lightning,
  Info,
  CreditCard,
} from "@phosphor-icons/react";

const TLD_SUGGESTIONS = [".fr", ".com", ".shop", ".store", ".boutique", ".eu"];

const STATUS_LABEL = {
  pending_payment: { label: "Paiement en attente", color: "#D97706", bg: "#FEF3C7" },
  paid_pending_ovh: { label: "Paiement reçu · Achat OVH…", color: "#2563EB", bg: "#DBEAFE" },
  purchased: { label: "Acheté", color: "#047857", bg: "#D1FAE5" },
  dns_configured: { label: "Actif", color: "#047857", bg: "#D1FAE5" },
  payment_failed: { label: "Paiement échoué", color: "#BE123C", bg: "#FFE4E6" },
  ovh_purchase_failed: { label: "Achat OVH en erreur", color: "#BE123C", bg: "#FFE4E6" },
};

export default function Domains() {
  const { id: siteId } = useParams();
  const [search, setSearch] = useSearchParams();
  const navigate = useNavigate();
  const [site, setSite] = useState(null);
  const [base, setBase] = useState("");
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [buying, setBuying] = useState(null);
  const [mine, setMine] = useState([]);
  const [returnStatus, setReturnStatus] = useState(null); // {domain, status, ovh_error}

  const refreshMine = useCallback(async () => {
    const { data } = await apiCall(() => api.get("/domains"));
    if (data) setMine((data.domains || []).filter((d) => d.site_id === siteId));
  }, [siteId]);

  useEffect(() => {
    apiCall(() => api.get(`/sites/${siteId}`)).then(({ data }) => {
      if (data) {
        setSite(data);
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
    refreshMine();
  }, [siteId, refreshMine]);

  // Poll purchase status after Mollie redirect (?domain_payment=1&domain=xyz)
  useEffect(() => {
    const returnedDomain = search.get("domain");
    const isPayment = search.get("domain_payment") === "1";
    if (!isPayment || !returnedDomain) return;
    let attempts = 0;
    let cancelled = false;
    const poll = async () => {
      const { data } = await apiCall(() =>
        api.get(`/domains/${returnedDomain}/purchase-status`)
      );
      if (cancelled || !data) return;
      setReturnStatus(data);
      await refreshMine();
      const terminal = ["purchased", "dns_configured", "active",
        "payment_failed", "ovh_purchase_failed"].includes(data.status);
      attempts += 1;
      if (!terminal && attempts < 30) {
        setTimeout(poll, 2000);
      } else if (terminal) {
        // Clear query params after terminal state so refresh doesn't re-trigger
        setTimeout(() => {
          setSearch({}, { replace: true });
        }, 5000);
      }
    };
    poll();
    return () => { cancelled = true; };
  }, [search, refreshMine, setSearch]);

  const runSearch = async () => {
    const trimmed = (base || "").trim().toLowerCase();
    if (!trimmed) return;
    setLoading(true);
    setResults([]);
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

  const purchase = async (domain, priceEur) => {
    if (
      !window.confirm(
        `Tu vas être redirigé(e) vers Mollie pour payer ${priceEur}€ (TTC, 1 an) pour ${domain}.\n\nDès que le paiement est confirmé, l'achat OVH se déclenche automatiquement et le domaine est rattaché au site "${site?.name}".\n\nContinuer ?`
      )
    ) {
      return;
    }
    setBuying(domain);
    const { data, error: err } = await apiCall(() =>
      api.post("/domains/purchase", { domain, site_id: siteId })
    );
    setBuying(null);
    if (err || !data?.checkout_url) {
      window.alert("Erreur : " + (err || "pas d'URL Mollie reçue"));
      return;
    }
    // Redirect to Mollie
    window.location.href = data.checkout_url;
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
    refreshMine();
  };

  return (
    <Layout>
      <div className="p-8 md:p-12 max-w-[1100px]">
        <button
          onClick={() => navigate(`/sites/${siteId}`)}
          data-testid="domains-back"
          className="flex items-center gap-2 text-sm text-neutral-500 hover:text-neutral-900 mb-6 transition"
        >
          <ArrowLeft size={16} /> Retour au site
        </button>

        <div className="flex items-start gap-3 mb-6">
          <div className="w-11 h-11 rounded-lg bg-gradient-to-br from-neutral-800 to-neutral-950 flex items-center justify-center">
            <Globe size={22} weight="fill" color="#fff" />
          </div>
          <div>
            <div className="text-[11px] uppercase tracking-widest text-neutral-500 mb-1">
              Nom de domaine · OVH
            </div>
            <h1 className="text-3xl font-semibold text-neutral-900">
              Choisis ton nom de domaine
            </h1>
            <p className="text-neutral-600 mt-1">
              Paiement sécurisé via Mollie, DNS auto-configuré sur ta boutique.
              {site?.name && <> Site : <strong>{site.name}</strong></>}
            </p>
          </div>
        </div>

        {/* Return banner after Mollie redirect */}
        {returnStatus && (
          <div
            data-testid="domain-return-banner"
            className="rounded-xl border p-5 mb-6"
            style={{
              background: STATUS_LABEL[returnStatus.status]?.bg || "#FEF3C7",
              borderColor: STATUS_LABEL[returnStatus.status]?.color || "#D97706",
            }}
          >
            <div className="flex items-center gap-3">
              {returnStatus.status === "purchased" || returnStatus.status === "dns_configured" ? (
                <CheckCircle size={22} weight="fill" color={STATUS_LABEL[returnStatus.status].color} />
              ) : returnStatus.status?.includes("failed") ? (
                <XCircle size={22} weight="fill" color="#BE123C" />
              ) : (
                <ArrowClockwise size={22} className="animate-spin" color={STATUS_LABEL[returnStatus.status]?.color || "#D97706"} />
              )}
              <div>
                <div className="font-medium text-neutral-900">
                  {returnStatus.domain} —{" "}
                  <span style={{ color: STATUS_LABEL[returnStatus.status]?.color }}>
                    {STATUS_LABEL[returnStatus.status]?.label || returnStatus.status}
                  </span>
                </div>
                <div className="text-xs text-neutral-600 mt-1">
                  {returnStatus.status === "pending_payment" && "En attente de confirmation Mollie…"}
                  {returnStatus.status === "paid_pending_ovh" && "Paiement confirmé, OVH est en train d'acheter le domaine."}
                  {returnStatus.status === "purchased" && "Parfait ! Prochaine étape : configurer les DNS (bouton plus bas)."}
                  {returnStatus.status === "dns_configured" && "Ton site est accessible sur ce domaine 🎉"}
                  {returnStatus.status === "payment_failed" && "Le paiement Mollie n'a pas abouti. Tu peux réessayer ci-dessous."}
                  {returnStatus.status === "ovh_purchase_failed" && (
                    <>Le paiement est OK mais l'achat OVH a échoué : <strong>{returnStatus.ovh_error || "erreur inconnue"}</strong>. Contacte l'Admin pour remboursement ou relance manuelle.</>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Existing domains on this site */}
        {mine.length > 0 && (
          <div className="bg-white rounded-xl border border-[#D1FAE5] p-5 mb-6">
            <div className="flex items-center gap-2 mb-3">
              <CheckCircle size={18} weight="fill" className="text-emerald-400" />
              <div className="font-medium text-neutral-900">
                Domaines liés à ce site
              </div>
            </div>
            <div className="space-y-2">
              {mine.map((d) => {
                const statusMeta = STATUS_LABEL[d.status] || { label: d.status, color: "#78716C", bg: "#F5F2EB" };
                return (
                  <div
                    key={d.id}
                    data-testid={`domain-mine-${d.domain}`}
                    className="flex items-center justify-between bg-neutral-100/40 rounded-lg p-3"
                  >
                    <div className="flex items-center gap-3">
                      <Globe size={16} className="text-emerald-400" />
                      <div>
                        <div className="font-mono font-medium text-sm">{d.domain}</div>
                        <div className="text-xs text-neutral-500">
                          <span
                            className="inline-block px-2 py-0.5 rounded-full text-[10px] font-semibold mr-2"
                            style={{ background: statusMeta.bg, color: statusMeta.color }}
                          >
                            {statusMeta.label}
                          </span>
                          · {d.purchased_at?.slice(0, 10)}
                          {d.platform_price_eur && <> · {d.platform_price_eur}€</>}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {d.status === "purchased" && (
                        <button
                          onClick={() => configureDns(d.domain)}
                          data-testid={`dns-${d.domain}`}
                          className="h-8 px-3 rounded-lg bg-neutral-200 hover:bg-neutral-900 text-white text-xs font-medium"
                        >
                          Configurer DNS
                        </button>
                      )}
                      {d.status === "pending_payment" && d.mollie_checkout_url && (
                        <a
                          href={d.mollie_checkout_url}
                          data-testid={`pay-${d.domain}`}
                          className="h-8 px-3 rounded-lg bg-amber-500 hover:bg-amber-600 text-neutral-900 text-xs font-medium flex items-center gap-1"
                        >
                          <CreditCard size={12} weight="fill" /> Payer
                        </a>
                      )}
                      {(d.status === "dns_configured" || d.status === "active") && (
                        <span className="text-[10px] uppercase tracking-wider px-2 py-1 rounded-full bg-emerald-500/10 text-emerald-400 font-semibold">
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
                );
              })}
            </div>
          </div>
        )}

        {/* Search */}
        <div className="bg-white rounded-xl border border-neutral-200 p-5 mb-5">
          <label className="block text-xs font-semibold text-neutral-600 mb-1.5 uppercase tracking-wider">
            Nom souhaité (sans extension)
          </label>
          <div className="flex gap-2">
            <div className="flex-1 relative">
              <MagnifyingGlass
                size={16}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-neutral-500"
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
                className="w-full h-12 pl-10 pr-3 rounded-xl border border-neutral-200 bg-white text-sm focus:outline-none focus:border-[#2563EB]"
              />
            </div>
            <button
              onClick={runSearch}
              disabled={loading || !base.trim()}
              data-testid="domain-search-btn"
              className="h-12 px-5 rounded-xl bg-neutral-900 hover:bg-neutral-800 disabled:opacity-50 text-white text-sm font-medium flex items-center gap-2"
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
          <div className="text-[11px] text-neutral-500 mt-2">
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
                    isAvail ? "border-[#D1FAE5]" : "border-neutral-200 opacity-60"
                  }`}
                >
                  <div
                    className={`w-10 h-10 rounded-full flex items-center justify-center ${
                      isAvail ? "bg-emerald-500/10" : "bg-neutral-200"
                    }`}
                  >
                    {isAvail ? (
                      <CheckCircle size={20} weight="fill" className="text-emerald-400" />
                    ) : (
                      <XCircle size={20} weight="fill" className="text-neutral-500" />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="font-mono text-lg font-medium text-neutral-900">
                      {fullDomain}
                    </div>
                    <div className="text-xs text-neutral-500">
                      {r.error ? (
                        <span className="text-red-400">Erreur : {r.error}</span>
                      ) : isAvail ? (
                        <>
                          Disponible · Prix TTC année 1 :{" "}
                          <strong className="text-emerald-400">{price}€</strong>
                          <span className="text-neutral-400">
                            {" "}(coût OVH {r.data.ovh_price_ttc_eur}€ + frais plateforme {r.data.markup_eur}€)
                          </span>
                        </>
                      ) : (
                        "Déjà pris"
                      )}
                    </div>
                  </div>
                  {isAvail && (
                    <button
                      onClick={() => purchase(fullDomain, price)}
                      disabled={isBuying}
                      data-testid={`buy-${r.tld}`}
                      className="h-10 px-4 rounded-xl bg-neutral-900 hover:bg-neutral-800 text-white text-sm font-medium flex items-center gap-2 disabled:opacity-60"
                    >
                      {isBuying ? (
                        <>
                          <ArrowClockwise size={14} className="animate-spin" />
                          Redirection Mollie…
                        </>
                      ) : (
                        <>
                          <CreditCard size={14} weight="fill" /> Acheter {price}€
                        </>
                      )}
                    </button>
                  )}
                </div>
              );
            })}
          </div>
        )}

        <div className="mt-6 p-4 rounded-xl bg-neutral-100/40 border border-neutral-200">
          <div className="flex items-start gap-2">
            <Info size={16} className="text-[#2563EB] shrink-0 mt-0.5" />
            <div className="text-xs text-neutral-600 leading-relaxed">
              <strong>Comment ça marche :</strong> tu paies via Mollie (CB, iDEAL, Bancontact…), on achète le domaine chez OVH et on le configure pour pointer vers ta boutique. La propagation DNS prend 5 à 30 minutes. Renouvellement automatique chaque année au même prix.
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
}
