import React, { useEffect, useState } from "react";
import {
  CheckCircle, XCircle, Warning, ArrowClockwise, PaperPlaneTilt, Flag,
  ShieldCheck, Hourglass,
} from "@phosphor-icons/react";
import { api, apiCall } from "../lib/api";

const STATUS_META = {
  draft:        { label: "Brouillon",               color: "bg-neutral-100 text-neutral-700 border-neutral-200", Icon: Hourglass },
  in_review:    { label: "En attente de validation",color: "bg-sky-50 text-sky-900 border-sky-200", Icon: Flag },
  changes_req:  { label: "Corrections demandées",   color: "bg-amber-50 text-amber-900 border-amber-200", Icon: Warning },
  approved:     { label: "Validé",                   color: "bg-emerald-50 text-emerald-900 border-emerald-200", Icon: CheckCircle },
  live:         { label: "En ligne · Ads actives",  color: "bg-emerald-100 text-emerald-900 border-emerald-300", Icon: ShieldCheck },
};

/**
 * Cockpit widget — Automated QA snapshot + Submit for validation flow.
 */
export default function SiteQAPanel({ site }) {
  const [qa, setQa] = useState(null);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [concepteurNote, setConcepteurNote] = useState("");
  const [showSubmitForm, setShowSubmitForm] = useState(false);

  const load = async () => {
    setLoading(true);
    const { data } = await apiCall(() => api.get(`/sites/${site.id}/qa-audit`));
    if (data) setQa(data);
    setLoading(false);
  };

  useEffect(() => { load(); /* eslint-disable-next-line */ }, [site.id, site.status]);

  const submit = async () => {
    setSubmitting(true);
    const { data, error } = await apiCall(() =>
      api.post(`/sites/${site.id}/submit`, { concepteur_note: concepteurNote })
    );
    setSubmitting(false);
    if (error) {
      window.alert(error);
      return;
    }
    setShowSubmitForm(false);
    setConcepteurNote("");
    window.location.reload();
  };

  const status = site.status || "draft";
  const meta = STATUS_META[status] || STATUS_META.draft;

  const canSubmit = ["draft", "changes_req"].includes(status) && qa && qa.ready_for_submission;
  const scoreColor = !qa ? "text-neutral-500"
    : qa.score >= 80 ? "text-emerald-700"
    : qa.score >= 60 ? "text-amber-700"
    : "text-rose-700";

  return (
    <div className="bg-white border border-neutral-200 rounded-2xl p-5" data-testid="site-qa-panel">
      <div className="flex items-center justify-between gap-3 mb-4 flex-wrap">
        <div className="flex items-center gap-2">
          <ShieldCheck size={18} weight="duotone" className="text-neutral-500" />
          <div className="text-sm font-semibold text-neutral-900">Contrôle qualité automatique</div>
        </div>
        <span className={`inline-flex items-center gap-1.5 h-7 px-3 rounded-full text-[11px] font-medium border ${meta.color}`} data-testid="site-status-badge">
          <meta.Icon size={12} weight="fill" /> {meta.label}
        </span>
      </div>

      {/* Last admin note */}
      {status === "changes_req" && site.last_review_note && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-3 mb-4 text-sm text-amber-900" data-testid="admin-review-note">
          <strong>Note Admin :</strong> {site.last_review_note}
        </div>
      )}

      {/* QA score + checks */}
      {loading ? (
        <div className="text-sm text-neutral-400">Analyse en cours…</div>
      ) : qa ? (
        <>
          <div className="flex items-center gap-4 mb-4">
            <div className={`text-4xl font-semibold ${scoreColor}`} style={{ fontFamily: "'Fraunces', serif" }}>
              {qa.score}
              <span className="text-xl text-neutral-400"> / 100</span>
            </div>
            <div className="flex-1 min-w-0">
              <div className="h-2 rounded-full bg-neutral-100 overflow-hidden">
                <div className={`h-full rounded-full ${qa.score >= 80 ? "bg-emerald-500" : qa.score >= 60 ? "bg-amber-500" : "bg-rose-500"}`} style={{ width: `${qa.score}%`, transition: "width 600ms" }} />
              </div>
              <div className="text-xs text-neutral-500 mt-1.5">
                {qa.passed}/{qa.total} contrôles passés
                {qa.blockers.length > 0 && (
                  <span className="text-rose-700 font-medium ml-2">· {qa.blockers.length} bloquant{qa.blockers.length > 1 ? "s" : ""}</span>
                )}
              </div>
            </div>
            <button onClick={load} className="h-8 w-8 rounded-lg bg-neutral-50 hover:bg-neutral-100 text-neutral-600 flex items-center justify-center" title="Relancer l'audit">
              <ArrowClockwise size={14} />
            </button>
          </div>

          {qa.blockers.length > 0 && (
            <div className="mb-4" data-testid="qa-blockers">
              <div className="text-[11px] uppercase tracking-widest text-rose-700 font-medium mb-2">À corriger avant soumission</div>
              <div className="space-y-1.5">
                {qa.blockers.map((b, i) => (
                  <div key={i} className="flex items-start gap-2 text-sm bg-rose-50 border border-rose-200 p-2 rounded-lg">
                    <XCircle size={14} weight="fill" className="text-rose-600 mt-0.5 flex-shrink-0" />
                    <div>
                      <div className="font-medium text-rose-900">{b.label}</div>
                      {b.detail && <div className="text-xs text-rose-700">{b.detail}</div>}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          <details className="mb-4" data-testid="qa-details">
            <summary className="text-xs text-neutral-600 cursor-pointer hover:text-neutral-900 mb-2">
              Voir les {qa.total} contrôles
            </summary>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-x-4 gap-y-1 text-[12px] mt-3">
              {qa.checks.map((c, i) => (
                <div key={i} className="flex items-center gap-1.5">
                  {c.pass ? (
                    <CheckCircle size={12} weight="fill" className="text-emerald-600 flex-shrink-0" />
                  ) : c.critical ? (
                    <XCircle size={12} weight="fill" className="text-rose-500 flex-shrink-0" />
                  ) : (
                    <Warning size={12} weight="fill" className="text-amber-500 flex-shrink-0" />
                  )}
                  <span className={c.pass ? "text-neutral-700" : "text-neutral-400"}>{c.label}</span>
                </div>
              ))}
            </div>
          </details>
        </>
      ) : null}

      {/* Submit CTA */}
      {["draft", "changes_req"].includes(status) && (
        <div className="pt-4 border-t border-neutral-100">
          {!showSubmitForm ? (
            <button
              onClick={() => setShowSubmitForm(true)}
              disabled={!canSubmit}
              data-testid="qa-submit-btn"
              className="h-10 px-4 rounded-xl bg-neutral-900 hover:bg-neutral-800 text-white text-sm font-medium flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
              title={canSubmit ? "" : "Corrige d'abord les bloquants"}
            >
              <PaperPlaneTilt size={14} weight="bold" />
              Soumettre à validation
            </button>
          ) : (
            <div data-testid="submit-form">
              <label className="block text-xs text-neutral-600 mb-1.5">Message pour l'Admin (optionnel)</label>
              <textarea
                value={concepteurNote}
                onChange={(e) => setConcepteurNote(e.target.value)}
                placeholder="Ex: Boutique ciblée sur les seniors, prix validés vs 3 concurrents, 12 produits + 8 upsells importés."
                rows={3}
                data-testid="submit-note"
                className="w-full rounded-xl border border-neutral-200 p-3 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-300 mb-3"
              />
              <div className="flex gap-2">
                <button onClick={submit} disabled={submitting} data-testid="submit-confirm" className="h-10 px-4 rounded-xl bg-neutral-900 hover:bg-neutral-800 text-white text-sm font-medium disabled:opacity-50">
                  {submitting ? "Envoi…" : "Confirmer la soumission"}
                </button>
                <button onClick={() => setShowSubmitForm(false)} disabled={submitting} className="h-10 px-4 rounded-xl text-sm text-neutral-600 hover:bg-neutral-100">
                  Annuler
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {status === "in_review" && (
        <div className="pt-4 border-t border-neutral-100 text-sm text-neutral-600 flex items-start gap-2" data-testid="in-review-notice">
          <Hourglass size={16} className="text-sky-500 flex-shrink-0 mt-0.5" />
          <div>
            Ton site a été soumis. L'Admin va l'examiner sous 24-48h ouvrées et te dira si c'est validé ou s'il faut corriger quelque chose.
          </div>
        </div>
      )}

      {status === "approved" && (
        <div className="pt-4 border-t border-neutral-100 bg-emerald-50 -mx-5 -mb-5 p-4 rounded-b-2xl flex items-start gap-2" data-testid="approved-notice">
          <CheckCircle size={18} weight="fill" className="text-emerald-600 flex-shrink-0 mt-0.5" />
          <div className="text-sm text-emerald-900">
            🎉 <strong>Site validé.</strong> L'Admin va lancer les campagnes Google Ads sur les marchés sélectionnés. Tu seras notifié dès que le trafic démarre.
          </div>
        </div>
      )}
    </div>
  );
}
