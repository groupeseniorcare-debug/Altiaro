import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, apiCall } from "../lib/api";
import Layout from "../components/Layout";
import { Hourglass, CheckCircle, Storefront } from "@phosphor-icons/react";

export default function Validations() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    (async () => {
      const { data } = await apiCall(() => api.get("/validations"));
      setItems(data || []);
      setLoading(false);
    })();
  }, []);

  return (
    <Layout>
      <div className="p-8 md:p-12 max-w-[1400px]">
        <div className="mb-10 animate-fade-up">
          <div className="text-[11px] uppercase tracking-widest text-neutral-500 mb-2">Activité récente</div>
          <h1 className="text-3xl font-semibold text-neutral-900">Activité des concepteurs</h1>
          <p className="text-neutral-600 mt-2">
            Les 100 dernières étapes complétées par vos concepteurs. Auditez la qualité du travail et repérez les sites bientôt prêts à lancer.
          </p>
        </div>

        {loading ? (
          <div className="text-neutral-500">Chargement...</div>
        ) : items.length === 0 ? (
          <div className="bg-white rounded-xl border border-neutral-200 p-12 text-center">
            <div className="w-14 h-14 rounded-full bg-neutral-200 flex items-center justify-center mx-auto mb-5">
              <CheckCircle size={28} weight="duotone" color="#B84B31" />
            </div>
            <h3 className="text-lg font-semibold text-neutral-900 mb-2">Aucune activité pour l'instant</h3>
            <p className="text-neutral-600 max-w-md mx-auto">
              Dès qu'un concepteur valide une étape, elle s'affichera ici.
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {items.map((step, i) => (
              <button
                key={step.id}
                onClick={() => navigate(`/sites/${step.site_id}`)}
                data-testid={`validation-${step.id}`}
                className={`w-full flex items-center gap-5 text-left bg-white rounded-xl border border-neutral-200 p-5 hover:border-[#B84B31]/50 hover:shadow-sm transition-all duration-200 animate-fade-up-delay-${Math.min(i + 1, 4)}`}
              >
                <div className="w-11 h-11 rounded-lg bg-emerald-500/10 flex items-center justify-center flex-shrink-0">
                  <CheckCircle size={20} weight="duotone" color="#047857" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <Storefront size={14} color="#78716C" />
                    <span className="text-sm text-neutral-500 font-medium">{step.site?.name}</span>
                    <span className="text-xs text-neutral-500">· Phase {step.phase} · Étape #{step.number}</span>
                  </div>
                  <div className="font-heading font-semibold text-neutral-900">{step.title}</div>
                  <div className="text-sm text-neutral-600 mt-1 line-clamp-1">{step.summary}</div>
                </div>
                <div className="text-right">
                  <div className="text-[11px] uppercase tracking-widest text-emerald-400 font-semibold mb-1">Validée</div>
                  <div className="text-xs text-neutral-500">
                    {step.validated_at ? new Date(step.validated_at).toLocaleDateString("fr-FR") : "—"}
                  </div>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    </Layout>
  );
}
